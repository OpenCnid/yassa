"""Opt-in authenticated integration evidence; never collected as a pytest test.

uv run --locked python tests/run_native_context_probe.py --run-dir NEW_EXTERNAL_DIR
    --auth-file SAVED_AUTH --image sha256:PIN
"""

import argparse
from pathlib import Path

from inspect_ai.log import read_eval_log

from yassa.app import external_root, procedure_files
from yassa.evidence import EvidenceStore, read_regular, seal_run, verify_run, write_new
from yassa.native import native_usage
from yassa.native_capture import read_archive
from yassa.native_execution import RUNTIME, execute_native
from yassa.records import canonical, digest, identity, parse_json

SKILL = b"""---
name: catalog-probe
description: Read the declared integer fixture and record the assigned summary.
---
Read /work/input/values.json. For the root role write /work/output/root.json
containing exactly {"sum": SUM_OF_VALUES}. For the child role write
/work/output/child.json containing exactly {"count": NUMBER_OF_VALUES}.
Use integer arithmetic and write only the assigned file. Do not install skills,
plugins or dependencies. Do not edit inputs, configuration or other outputs.
"""
PROMPTS = {
    "root-child": """Use $catalog-probe for a small runtime integration check.
Read its SKILL.md. Spawn exactly one native subagent with a fresh task: read
$catalog-probe's SKILL.md and perform its child role. Use the inherited model
and permissions; the child must not spawn further agents. While it works,
independently perform the skill's root role. Wait for the child to finish and
confirm both assigned output files exist. Finish with a short completion message.
""",
    "root-only": """Read /work/input/values.json and write /work/output/root.json
containing exactly {"sum": SUM_OF_VALUES}, using integer arithmetic. Do not
spawn subagents or install any skills, plugins or dependencies. Finish with a
short completion message.
""",
}


def run(root: Path, auth: Path, image: str) -> dict:
    root = external_root(root)
    root.mkdir(parents=True, exist_ok=False)
    store = EvidenceStore(root)
    runtime = {p.name: read_regular(p) for p in RUNTIME.iterdir() if p.is_file()}
    config = runtime["config.toml"]
    trials = []
    for name, prompt in PROMPTS.items():
        files = {"input/values.json": canonical({"values": [11, -4, 2]})}
        if name == "root-child":
            files[".agents/skills/catalog-probe/SKILL.md"] = SKILL
        trials.append(
            {
                "id": name,
                "prompt": prompt,
                "files": files,
                "timeout": 180 if name == "root-child" else 60,
            }
        )
    plan = {
        "scope": "runtime integration only; no Dovetail comparison or retries",
        "authorization": "User approved authenticated root/subagent catalog verification.",
        "image": image,
        "procedure_id": store.put(procedure_files()),
        "runtime_id": store.put(runtime),
        "reserved_attempts": 2,
        "reserved_native_seconds": 240,
        "expected_root_sessions": 2,
        "expected_child_sessions": 1,
        "trials": [
            {
                "id": t["id"],
                "timeout": t["timeout"],
                "prompt": t["prompt"],
                "input_id": store.put(t["files"]),
            }
            for t in trials
        ],
    }
    plan["id"] = identity(plan)
    write_new(root / "plan.json", canonical(plan))
    results = {}
    for trial in trials:
        assert store.get(plan["procedure_id"]) == procedure_files()
        assert store.get(plan["runtime_id"]) == {
            p.name: read_regular(p) for p in RUNTIME.iterdir() if p.is_file()
        }
        print("Running " + trial["id"], flush=True)
        results[trial["id"]] = execute_native(
            root,
            trial["id"],
            trial["prompt"],
            trial["files"],
            image=image,
            auth_path=auth,
            config=config,
            timeout=trial["timeout"],
        )
        print("Finished " + trial["id"] + ": " + results[trial["id"]]["status"], flush=True)
    write_new(root / "results.json", canonical(results))
    seal = seal_run(root)
    destination = root / "interpretations/verified"
    checks, roots, usage = {}, set(), {}
    for trial in trials:
        name, result = trial["id"], results[trial["id"]]
        failures = []
        if result["status"] != "completed":
            failures.append(result.get("error") or result["status"])
        if not failures:
            output = store.get(result["output_id"])
            if store.get(result["input_id"]) != {
                "prompt.txt": trial["prompt"].encode(),
                **trial["files"],
            }:
                failures.append("launch inputs differ from the plan")
            catalog = store.json(result["catalog_check_id"], "check.json")
            sessions = catalog["sessions"]
            expected_count = 2 if name == "root-child" else 1
            if not catalog["passed"] or len(sessions) != expected_count:
                failures.append("incorrect root/child catalog or session count")
            for session in sessions:
                if session["source"] == "exec":
                    if session["id"] in roots:
                        failures.append("root session reused")
                    roots.add(session["id"])
            if parse_json(output.get("output/root.json", b"null")) != {"sum": 9}:
                failures.append("root result incorrect")
            if name == "root-child" and parse_json(output.get("output/child.json", b"null")) != {
                "count": 3
            }:
                failures.append("child result incorrect")
            for path, data in output.items():
                if not path.startswith("sessions/"):
                    continue
                rows = [parse_json(line) for line in data.splitlines()]
                contexts = [r["payload"] for r in rows if r["type"] == "turn_context"]
                if not contexts or any(
                    c["cwd"] != "/work"
                    or c["active_permission_profile"]["id"] != "trial"
                    or c["sandbox_policy"]["network_access"] is not False
                    or c["approval_policy"] != "never"
                    for c in contexts
                ):
                    failures.append("native session permission context differs")
            log = read_eval_log(root / result["inspect_log"])
            if log.status != "success" or log.samples[0].error:
                failures.append("Inspect log failed")
            raw = read_archive(store, result["captures"]["output"]["archive_id"])["export.json"]
            if not parse_json(raw)["files"] or not read_archive(store, result["native_logs_id"]):
                failures.append("raw capture missing")
            usage[name] = native_usage(output)
            if usage[name]["native_usage_records"] < expected_count:
                failures.append("authenticated native response evidence missing")
        checks[name] = {
            "passed": not failures,
            "failures": failures,
            "catalog_check_id": result.get("catalog_check_id"),
        }
    report = {
        "passed": all(c["passed"] for c in checks.values()),
        "checks": checks,
        "run_seal": seal,
        "plan_id": plan["id"],
        "unique_roots": len(roots),
        "native_seconds": sum(r.get("duration_seconds", 0) for r in results.values()),
        "usage": usage,
        "auditor_sha256": digest(read_regular(Path(__file__))),
    }
    write_new(destination / "check.json", canonical(report))
    write_new(destination / "auditor.py", read_regular(Path(__file__)))
    assert verify_run(root) == seal
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--auth-file", type=Path, required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    report = run(args.run_dir, args.auth_file, args.image)
    print(canonical(report).decode())
    if not report["passed"]:
        raise SystemExit(1)
