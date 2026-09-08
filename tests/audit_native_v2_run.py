"""Read-only live v2 evidence audit: uv run python tests/audit_native_v2_run.py RUN."""

import json
import sys
from pathlib import Path

import yaml
from inspect_ai.log import read_eval_log

from yassa.evidence import EvidenceStore, read_regular, verify_run
from yassa.native import native_usage
from yassa.native_contracts import FileMaterials, NativeStudyV2, builder_files
from yassa.native_runner import common_prompt
from yassa.records import digest, identity, parse_json


def audit(root: Path) -> dict:
    seal = verify_run(root)
    store = EvidenceStore(root)
    frozen = parse_json(read_regular(root / "study.json"))
    study = NativeStudyV2.model_validate(frozen["study"])
    plan = parse_json(read_regular(root / "plan.json"))
    results = parse_json(read_regular(root / "results.json"))["trials"]
    materials = {
        c["id"]: FileMaterials.model_validate(store.json(c["materials_id"], "materials.json"))
        for c in frozen["conditions"]
    }
    common, root_sessions, builtins, observations = {}, set(), set(), []

    def modes(artifact):
        manifest = parse_json(read_regular(root / "artifacts" / artifact / "manifest.json"))
        return {entry["path"] for entry in manifest["files"] if entry["executable"]}

    for trial in plan["trials"]:
        result = results[trial["id"]]
        assert result.get("launched") and result.get("output_id"), trial["id"]
        inputs, outputs = store.get(result["input_id"]), store.get(result["output_id"])
        binding = parse_json(read_regular(root / "bindings" / f"{trial['id']}.json"))
        assert binding["trial"] == trial
        assert binding["study_id"] == frozen["id"] and binding["plan_id"] == plan["id"]
        prompt = common_prompt(study.task, trial["role"])
        material = materials[trial["condition"]]
        treatment, expected_modes, required_reads = {}, set(), []
        treatment_ids = []
        if trial["role"] == "build":
            public = builder_files(study.task, material)
            arm = next(a for a in study.arms if a.id == trial["arm"])
            actual_prompt = arm.invocation + "\n\n" + prompt if arm.invocation else prompt
            for source in arm.sources:
                artifact = frozen["sources"][source]["artifact_id"]
                treatment_ids.append(artifact)
                treatment.update({".agents/skills/" + n: b for n, b in store.get(artifact).items()})
                expected_modes.update(".agents/skills/" + n for n in modes(artifact))
                for name in store.get(artifact):
                    if name.endswith("/SKILL.md") and "$" + name.split("/")[0] in arm.invocation:
                        required_reads.append(".agents/skills/" + name)
        else:
            case = next(c for c in material.evaluation if c.id == trial["case"])
            public = {n: text.encode("utf-8") for n, text in case.files.items()}
            artifact = results[trial["parent"]]["package_id"]
            treatment_ids.append(artifact)
            prefix = f".agents/skills/{study.task.package_name}/"
            treatment = {prefix + n: b for n, b in store.get(artifact).items()}
            expected_modes = {prefix + n for n in modes(artifact)}
            required_reads.append(prefix + "SKILL.md")
            actual_prompt = prompt
        assert inputs == {"prompt.txt": actual_prompt.encode(), **public, **treatment}
        assert store.get(binding["common_id"]) == {"prompt.txt": prompt.encode(), **public}
        assert binding["treatment_ids"] == treatment_ids
        assert binding["input_files"] == {n: digest(b) for n, b in {**public, **treatment}.items()}
        assert binding["prompt_sha256"] == digest(actual_prompt.encode())
        assert set(binding["executable"]) == expected_modes
        key = (trial["condition"], trial["role"], trial["case"])
        assert key not in common or common[key] == binding["common_id"]
        common[key] = binding["common_id"]
        boundary = parse_json(result["boundary"]["stdout"])
        assert len(boundary) == 12 and all(boundary.values())
        log = read_eval_log(root / result["inspect_log"], resolve_attachments=True)
        assert log.status == "success" and len(log.samples) == 1
        sample = log.samples[0]
        assert sample.input == actual_prompt and not sample.target
        assert sample.metadata["native_launch"]["input_id"] == result["input_id"]
        assert sample.output.completion == outputs["final.txt"].decode("utf-8")
        events = [parse_json(line) for line in outputs["events.jsonl"].splitlines()]
        threads = [e["thread_id"] for e in events if e["type"] == "thread.started"]
        assert len(threads) == 1 and threads[0] not in root_sessions
        root_sessions.add(threads[0])
        builtin = {
            n: b
            for n, b in outputs.items()
            if n.startswith("builtin-skills/") and "__pycache__" not in n
        }
        builtins.add(identity({n: digest(b) for n, b in builtin.items()}))
        expected_skills = set()
        for files, prefix in ((builtin, "builtin-skills/"), (treatment, ".agents/skills/")):
            names = {n.removeprefix(prefix).split("/")[0] for n in files if n.endswith("/SKILL.md")}
            for name in names:
                metadata = (
                    yaml.safe_load(files.get(f"{prefix}{name}/agents/openai.yaml", b"{}")) or {}
                )
                if metadata.get("policy", {}).get("allow_implicit_invocation", True):
                    expected_skills.add(name)
        sessions = [
            parse_json(line)
            for n, b in outputs.items()
            if n.startswith("sessions/")
            for line in b.splitlines()
        ]
        contexts = [row["payload"] for row in sessions if row["type"] == "turn_context"]
        assert contexts
        for context in contexts:
            assert context["cwd"] == "/work"
            assert context["active_permission_profile"]["id"] == "trial"
            assert context["sandbox_policy"]["network_access"] is False
            assert context["approval_policy"] == "never"
        root_context = next(c for c in contexts if c["turn_id"] == c["root_turn_id"])
        assert root_context["model"] == study.model
        assert root_context["effort"] == study.reasoning_effort
        catalogs = [
            c["text"]
            for row in sessions
            if row["type"] == "response_item" and row["payload"].get("role") == "developer"
            for c in row["payload"].get("content", [])
            if "<skills_instructions>" in c.get("text", "")
        ]
        assert catalogs
        names = {
            line[2:].split(":", 1)[0]
            for line in catalogs[0].splitlines()
            if line.startswith("- ") and "(file:" in line
        }
        assert names == expected_skills, (trial["id"], names, expected_skills)
        reads = [
            e["item"]
            for e in events
            if e["type"] == "item.completed"
            and e.get("item", {}).get("type") == "command_execution"
            and e["item"].get("exit_code") == 0
        ]
        for path in required_reads:
            assert any(
                path in item["command"] and item.get("aggregated_output") for item in reads
            ), (trial["id"], path)
        usage = native_usage(outputs)
        assert usage["native_usage_records"] > 0
        observations.append(
            {
                "trial": trial["id"],
                "status": result["status"],
                "sessions": len(usage["sessions"]),
                "responses": usage["native_usage_records"],
            }
        )
    assert len(builtins) == 1
    return {
        "run_seal": seal,
        "audited_attempts": len(observations),
        "unique_root_sessions": len(root_sessions),
        "common_groups": len(common),
        "builtin_snapshot": next(iter(builtins)),
        "observations": observations,
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path(sys.argv[1]).resolve()), indent=2))
