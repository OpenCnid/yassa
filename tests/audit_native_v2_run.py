"""Read-only live v2 evidence audit: uv run python tests/audit_native_v2_run.py RUN."""

import json
import sys
from pathlib import Path

import yaml
from inspect_ai.log import read_eval_log

from yassa.evidence import EvidenceStore, read_regular, verify_run
from yassa.native import native_usage
from yassa.native_contracts import builder_files
from yassa.native_runner import MISSING, common_prompt, load_native_v2
from yassa.records import digest, identity, parse_json


def audit_unlaunched(root: Path, trial: dict, result: dict, results: dict) -> None:
    """Only a failed build can explain an unlaunched planned package use."""
    assert trial["role"] == "consume" and trial["parent"] in results
    parent = results[trial["parent"]]
    assert parent["status"] != "package_ready" and trial["build"] is not None
    assert result == {
        "status": "dependency_missing" if parent["status"] in MISSING else "dependency_failed",
        "parent": trial["parent"],
        "reason": parent["status"],
        "launched": False,
    }
    assert not (root / "attempts" / trial["id"]).exists()
    assert not (root / "bindings" / f"{trial['id']}.json").exists()


def audit_catalog(trial: str, names: set[str], expected: set[str]) -> list[dict]:
    """Retain every catalog violation so a failed audit can describe its full scope."""
    if names == expected:
        return []
    return [
        {
            "trial": trial,
            "check": "declared_skill_catalog",
            "unexpected": sorted(names - expected),
            "missing": sorted(expected - names),
        }
    ]


def audit_verdict(gaps: list, violations: list) -> str:
    return "failed" if violations else "qualified" if gaps else "pass"


def audit(root: Path) -> dict:
    seal = verify_run(root)
    store = EvidenceStore(root)
    frozen, plan, study, materials = load_native_v2(root)
    results = parse_json(read_regular(root / "results.json"))["trials"]
    assert set(results) == {t["id"] for t in plan["trials"]}
    common, root_sessions, builtins, observations = {}, set(), set(), []
    gaps, unlaunched, violations = [], [], []

    def modes(artifact):
        manifest = parse_json(read_regular(root / "artifacts" / artifact / "manifest.json"))
        return {entry["path"] for entry in manifest["files"] if entry["executable"]}

    for trial in plan["trials"]:
        result = results[trial["id"]]
        if not result.get("launched"):
            audit_unlaunched(root, trial, result, results)
            unlaunched.append({"trial": trial["id"], **result})
            continue
        inputs = store.get(result["input_id"])
        binding = parse_json(read_regular(root / "bindings" / f"{trial['id']}.json"))
        assert binding["trial"] == trial
        assert binding["study_id"] == frozen["id"] and binding["plan_id"] == plan["id"]
        prompt = common_prompt(
            study.task, trial["role"], complete_facts=study.consumer_baseline is not None
        )
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
            actual_prompt = prompt
            if trial["parent"]:
                artifact = results[trial["parent"]]["package_id"]
                treatment_ids.append(artifact)
                prefix = f".agents/skills/{study.task.package_name}/"
                treatment = {prefix + n: b for n, b in store.get(artifact).items()}
                expected_modes = {prefix + n for n in modes(artifact)}
                required_reads.append(prefix + "SKILL.md")
                if study.consumer_baseline:
                    actual_prompt = f"Use ${study.task.package_name}.\n\n" + prompt
            else:
                assert study.consumer_baseline and trial["arm"] == study.consumer_baseline.id
                assert trial["build"] is None
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
        if not result.get("output_id"):
            native = parse_json(read_regular(root / "attempts" / trial["id"] / "result.json"))
            assert native["status"] == result["status"] == "harness_failure"
            assert sample.error and sample.error.message == native["error"]
            assert all(result[key] == value for key, value in native.items())
            gaps.append(
                {
                    "trial": trial["id"],
                    "status": result["status"],
                    "error": native["error"],
                    "native_exit_code": native.get("exit_code"),
                    "native_seconds": native.get("duration_seconds"),
                    "verified": ["launch inputs", "binding", "boundary probe", "Inspect error"],
                    "unavailable": ["output bytes", "native transcript", "root session", "usage"],
                }
            )
            continue
        outputs = store.get(result["output_id"])
        assert not sample.error
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
        for index, catalog in enumerate(catalogs):
            names = {
                line[2:].split(":", 1)[0]
                for line in catalog.splitlines()
                if line.startswith("- ") and "(file:" in line
            }
            violations.extend(
                {**violation, "catalog_index": index}
                for violation in audit_catalog(trial["id"], names, expected_skills)
            )
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
        "verdict": audit_verdict(gaps, violations),
        "run_seal": seal,
        "audited_attempts": len(observations),
        "planned_attempts": len(plan["trials"]),
        "launched_attempts": len(observations) + len(gaps),
        "evidence_gaps": gaps,
        "violations": violations,
        "unlaunched_dependencies": unlaunched,
        "unique_root_sessions": len(root_sessions),
        "common_groups": len(common),
        "builtin_snapshot": next(iter(builtins)),
        "observations": observations,
    }


if __name__ == "__main__":
    result = audit(Path(sys.argv[1]).resolve())
    print(json.dumps(result, indent=2))
    if result["verdict"] == "failed":
        raise SystemExit(1)
