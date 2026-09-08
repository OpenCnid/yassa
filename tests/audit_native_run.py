"""Read-only native evidence audit. Usage: uv run python tests/audit_native_run.py RUN."""

import json
import sys
from pathlib import Path

import yaml
from inspect_ai.log import read_eval_log

from yassa.evidence import EvidenceStore, verify_run
from yassa.native import native_usage


def audit(root: Path) -> dict:
    seal = verify_run(root)
    store = EvidenceStore(root)
    frozen = json.loads((root / "study.json").read_text(encoding="utf-8"))
    plan = json.loads((root / "plan.json").read_text(encoding="utf-8"))
    results = json.loads((root / "results.json").read_text(encoding="utf-8"))["trials"]
    source = store.get(frozen["source_id"])
    source_skills = set()
    for name in frozen["study"]["source_skills"]:
        metadata = yaml.safe_load(source.get(f"{name}/agents/openai.yaml", b"{}")) or {}
        if metadata.get("policy", {}).get("allow_implicit_invocation", True):
            source_skills.add(name)
    common = {}
    thread_ids = set()
    builtin_sets = set()
    observations = []
    for trial in plan["trials"]:
        result = results[trial["id"]]
        assert result.get("output_id"), f"missing native evidence: {trial['id']}"
        inputs = store.get(result["input_id"])
        outputs = store.get(result["output_id"])
        input_name = "input/brief.json" if trial["role"] == "build" else "input/case.json"
        key = (trial["condition"], trial["role"], trial["case"])
        if key in common:
            assert common[key] == inputs[input_name]
        common[key] = inputs[input_name]
        if trial["role"] == "build":
            assert set(json.loads(inputs[input_name])) == {"brief", "contract", "development"}
            installed = {
                n.removeprefix(".agents/skills/"): b
                for n, b in inputs.items()
                if n.startswith(".agents/skills/")
            }
            assert installed == (source if trial["arm"] == "with-dovetail" else {})
        else:
            assert set(json.loads(inputs[input_name])) == {"rows"}
            parent_package = store.get(results[trial["parent"]]["package_id"])
            installed = {
                n.removeprefix(".agents/skills/account-totals/"): b
                for n, b in inputs.items()
                if n.startswith(".agents/skills/")
            }
            assert installed == parent_package
        boundary = json.loads(result["boundary"]["stdout"])
        assert len(boundary) == 12 and all(boundary.values())
        log = read_eval_log(root / result["inspect_log"], resolve_attachments=True)
        assert log.status == "success" and len(log.samples) == 1
        assert log.samples[0].input == inputs["prompt.txt"].decode("utf-8")
        assert not log.samples[0].target
        assert log.samples[0].output.completion == outputs["final.txt"].decode("utf-8")
        events = [json.loads(line) for line in outputs["events.jsonl"].splitlines()]
        started = [e["thread_id"] for e in events if e["type"] == "thread.started"]
        assert len(started) == 1 and started[0] not in thread_ids
        thread_ids.add(started[0])
        builtin = {
            n: b
            for n, b in outputs.items()
            if n.startswith("builtin-skills/") and "__pycache__" not in n
        }
        from yassa.records import digest, identity

        builtin_sets.add(identity({n: digest(b) for n, b in builtin.items()}))
        builtin_names = {n.split("/")[1] for n in builtin if n.endswith("/SKILL.md")}
        builtin_names = {
            name
            for name in builtin_names
            if (
                yaml.safe_load(builtin.get(f"builtin-skills/{name}/agents/openai.yaml", b"{}"))
                or {}
            )
            .get("policy", {})
            .get("allow_implicit_invocation", True)
        }
        expected_skills = builtin_names.copy()
        if trial["role"] == "consume":
            expected_skills.add("account-totals")
            required_read = "/work/.agents/skills/account-totals/SKILL.md"
        elif trial["arm"] == "with-dovetail":
            expected_skills |= source_skills
            required_read = "/work/.agents/skills/better-skill-creator/SKILL.md"
        else:
            required_read = None
        session_rows = [
            json.loads(line)
            for name, data in outputs.items()
            if name.startswith("sessions/")
            for line in data.splitlines()
        ]
        contexts = [r["payload"] for r in session_rows if r["type"] == "turn_context"]
        assert contexts
        for context in contexts:
            assert context["cwd"] == "/work"
            assert context["active_permission_profile"]["id"] == "trial"
            assert context["sandbox_policy"]["network_access"] is False
            assert context["approval_policy"] == "never"
        root_context = next(c for c in contexts if c["turn_id"] == c["root_turn_id"])
        assert root_context["model"] == frozen["study"]["model"]
        assert root_context["effort"] == frozen["study"]["reasoning_effort"]
        catalogs = [
            c["text"]
            for r in session_rows
            if r["type"] == "response_item" and r["payload"].get("role") == "developer"
            for c in r["payload"].get("content", [])
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
        if required_read:
            assert any(
                required_read in e["command"] and e.get("aggregated_output") for e in reads
            ), f"no recorded skill read: {trial['id']}"
        usage = native_usage(outputs)
        assert usage["native_usage_records"] > 0
        observations.append(
            {
                "trial": trial["id"],
                "status": result["status"],
                "native_sessions": len(usage["sessions"]),
                "model_responses": usage["native_usage_records"],
            }
        )
    assert len(builtin_sets) == 1, "native built-in files changed between trials"
    return {
        "run_seal": seal,
        "audited_attempts": len(observations),
        "unique_root_threads": len(thread_ids),
        "builtin_snapshot": next(iter(builtin_sets)),
        "observations": observations,
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path(sys.argv[1]).resolve()), indent=2))
