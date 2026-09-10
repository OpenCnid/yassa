"""Freeze, reconstruct and score code artifacts through supported Yassa commands."""

import re
import subprocess

from .app import external_root, procedure_files, runtime_versions
from .artifact_contracts import ArtifactRequest, artifact_plan, read_bundle
from .artifact_testing import compare_cases, test_artifact
from .control import managed, native_call, same_or_new, start_control, verify_execution_freeze
from .evidence import (
    EvidenceStore,
    inventory,
    read_regular,
    safe_name,
    seal_run,
    verify_run,
    write_new,
)
from .native_capture import recorded_native_files
from .native_contracts import resolve_sources
from .native_execution import RUNTIME, execute_native
from .native_resources import usage_evidence
from .records import canonical, digest, identity, parse_json


def prepare_artifact(path, root):
    raw = read_regular(path)
    request = ArtifactRequest.model_validate(parse_json(raw))
    base = path.resolve().parent
    bundles = {n: read_bundle(getattr(request, n), base) for n in ("public", "reference", "tests")}
    sources = resolve_sources(request, base)
    subprocess.run(
        ["docker", "image", "inspect", request.role.image], capture_output=True, check=True
    )
    root = external_root(root)
    root.mkdir(parents=True, exist_ok=False)
    store = EvidenceStore(root)
    config = read_regular(RUNTIME / "config.toml").decode()
    for key, value in (
        ("model", request.role.model),
        ("model_reasoning_effort", request.role.reasoning_effort),
    ):
        config = re.sub(r"^" + key + r" = .*$", f'{key} = "{value}"', config, flags=re.M)
    body = {
        "run_kind": "artifact-study-v1",
        "request": request.model_dump(mode="json"),
        "request_id": store.put({"request.json": raw}),
        "procedure_id": store.put(procedure_files()),
        "runtime": runtime_versions(),
        "bundles": {n: store.put(b) for n, b in bundles.items()},
        "sources": {
            s.id: store.put(sources[s.id][0], executable=s.executable) for s in request.sources
        },
        "config_id": store.put({"config.toml": config.encode()}),
        "runtime_files_id": store.put(
            {p.name: read_regular(p) for p in sorted(RUNTIME.iterdir()) if p.is_file()}
        ),
        "limits": {
            "hard_token_cap": None,
            "hard_spend_cap": None,
            "automatic_retries": 0,
            "setup_export_in_deadline": False,
            "test_timeout_seconds": request.test_timeout_seconds,
        },
    }
    reference = test_artifact(
        root / "reference-test",
        request.role.image,
        bundles["reference"],
        bundles["tests"],
        request.test_timeout_seconds,
    )
    if (
        reference["status"] != "tested"
        or reference.get("exit_code") not in (0, 1)
        or not reference["cases"]
        or "error" in reference["cases"].values()
    ):
        raise ValueError(
            "reference oracle did not collect and run; preserved reference-test evidence"
        )
    body["reference_result_id"] = store.put_json(reference, "result.json")
    write_new(root / "study.json", canonical({"id": identity(body), **body}))
    plan = artifact_plan(request)
    write_new(root / "plan.json", canonical(plan))
    reference_passed = sum(v == "pass" for v in reference["cases"].values())
    write_new(
        root / "review.md",
        (
            f"# Artifact reconstruction review\n\n{request.question}\n\n{request.provenance}\n\n"
            f"{plan['reserved_attempts']} fresh native attempts; "
            f"{plan['reserved_seconds']} reserved seconds. "
            f"Model {request.role.model}, {request.role.reasoning_effort}; "
            "identical image and deadline in every arm. "
            "Only public files and declared treatments enter each native sandbox. "
            "Reference source and tests "
            "are frozen separately and never provided to builders. Delivery: output/project/.\n\n"
            + "\n".join(f"- {a.id}: {a.rationale}" for a in request.arms)
            + f"\n\nOriginal reference: {reference_passed}/{len(reference['cases'])} tests passed. "
            "All collected reference cases remain in the denominator. "
            "Skipped/missing/failed cases do not pass. Tests measure shipped-suite compatibility, "
            "not proof of the entire mathematical specification. Infrastructure failures remain "
            "missing. No test feedback or artifact repair is fed to builders.\n\n"
            "One fixed artifact is not a sample of independent tasks. Root deadlines include "
            "child work, but do not cap tokens, spend or setup/export. Testing runs offline "
            "without credentials, candidate install hooks or host mounts. Test files are "
            "read-only; Python in-process tamper "
            "resistance is not established.\n"
        ).encode(),
    )
    write_new(root / "freeze-seal.json", canonical({"files": inventory(root)}))
    return root / "review.md"


def load_artifact(root):
    frozen = parse_json(read_regular(root / "study.json"))
    if frozen.get("run_kind") != "artifact-study-v1" or frozen.get("id") != identity(
        {k: v for k, v in frozen.items() if k != "id"}
    ):
        raise ValueError("invalid artifact freeze")
    request = ArtifactRequest.model_validate(frozen["request"])
    plan = parse_json(read_regular(root / "plan.json"))
    if plan != artifact_plan(request):
        raise ValueError("artifact plan mismatch")
    return frozen, request, plan


def artifact_input(store, frozen, request, arm):
    files = {"input/" + n: b for n, b in store.get(frozen["bundles"]["public"]).items()}
    modes = []
    for sid in arm.sources:
        files.update(
            {".agents/skills/" + n: b for n, b in store.get(frozen["sources"][sid]).items()}
        )
        modes.extend(
            ".agents/skills/" + n
            for n in next(s for s in request.sources if s.id == sid).executable
        )
    prompt = request.prompt + (
        "\n\nDeliver the complete project in /work/output/project/, "
        "using src/ for the Python package. Only that directory is submitted for evaluation. "
        "Keep your own tests and notes there if useful. Dependencies are preinstalled; "
        "no internet is available. Complete the task without questions. "
        f"Your execution deadline is {request.role.timeout_seconds} seconds; "
        "leave time to finish and save files."
    )
    if arm.invocation:
        prompt = arm.invocation + "\n\n" + prompt
    return prompt, files, tuple(modes)


@managed("artifact")
def execute_artifact(root, auth_path):
    verify_execution_freeze(root)
    frozen, request, plan = load_artifact(root)
    store = EvidenceStore(root)
    if (
        store.get(frozen["procedure_id"]) != procedure_files()
        or frozen["runtime"] != runtime_versions()
    ):
        raise ValueError("artifact procedure/dependencies changed since freeze")
    if store.get(frozen["runtime_files_id"]) != {
        p.name: read_regular(p) for p in sorted(RUNTIME.iterdir()) if p.is_file()
    }:
        raise ValueError("artifact native runtime changed since freeze")
    if not auth_path or not auth_path.is_file():
        raise ValueError("artifact execution requires --auth-file")
    start_control()
    results = {}
    for trial in plan["trials"]:
        arm = next(a for a in request.arms if a.id == trial["arm"])
        prompt, files, modes = artifact_input(store, frozen, request, arm)
        same_or_new(
            root / "bindings" / (trial["id"] + ".json"),
            canonical(
                {
                    "trial": trial,
                    "prompt_id": store.put({"prompt.txt": prompt.encode()}),
                    "input_files": {n: digest(b) for n, b in files.items()},
                }
            ),
        )
        print(f"Running {trial['id']} ({arm.id})", flush=True)
        results[trial["id"]] = native_call(
            execute_native,
            root,
            trial["id"],
            prompt,
            files,
            role="artifact-build",
            image=request.role.image,
            auth_path=auth_path,
            config=store.get(frozen["config_id"])["config.toml"],
            timeout=request.role.timeout_seconds,
            executable=modes,
        )
        print(f"Finished {trial['id']}: {results[trial['id']]['status']}", flush=True)
    same_or_new(
        root / "results.json",
        canonical({"study_id": frozen["id"], "plan_id": plan["id"], "trials": results}),
    )
    seal_run(root)
    return root / "results.json"


def score_artifact(root, label):
    safe_name(label)
    if "/" in label:
        raise ValueError("score label must be one component")
    seal = verify_run(root)
    frozen, request, plan = load_artifact(root)
    store = EvidenceStore(root)
    if (
        store.get(frozen["procedure_id"]) != procedure_files()
        or frozen["runtime"] != runtime_versions()
    ):
        raise ValueError("use the frozen procedure and dependencies to score artifacts")
    result = parse_json(read_regular(root / "results.json"))
    if (
        result["study_id"] != frozen["id"]
        or result["plan_id"] != plan["id"]
        or set(result["trials"]) != {t["id"] for t in plan["trials"]}
    ):
        raise ValueError("incomplete artifact results")
    destination = root / "interpretations" / label
    destination.mkdir(parents=True, exist_ok=False)
    reference = store.json(frozen["reference_result_id"], "result.json")
    scores = []
    for trial in plan["trials"]:
        attempt = result["trials"][trial["id"]]
        files = recorded_native_files(store, attempt)
        project = {
            n.removeprefix("output/project/"): b
            for n, b in files.items()
            if n.startswith("output/project/")
        }
        try:
            usage = usage_evidence(files)
        except ValueError as error:
            usage = {"unavailable": str(error)}
        row = {
            **trial,
            "execution_status": attempt["status"],
            "output_id": attempt.get("output_id"),
            "seconds": attempt.get("duration_seconds"),
            "usage": usage,
            "passed": None,
            "total": len(reference["cases"]),
        }
        if attempt["status"] in {"completed", "budget_exhausted"}:
            if project and not attempt.get("rejected_paths"):
                tested = test_artifact(
                    destination / trial["id"],
                    request.role.image,
                    project,
                    store.get(frozen["bundles"]["tests"]),
                    request.test_timeout_seconds,
                )
                row["test_status"] = tested["status"]
                if tested["status"] != "harness_failure":
                    row.update(compare_cases(reference["cases"], tested["cases"]))
            else:
                row.update(
                    compare_cases(reference["cases"], {}),
                    test_status="missing_or_rejected_artifact",
                )
        scores.append(row)
    write_new(
        destination / "scores.json",
        canonical(
            {"run_seal": seal, "study_id": frozen["id"], "scores": scores, "reference": reference}
        ),
    )
    lines = [
        "# Artifact reconstruction result",
        "",
        request.question,
        "",
        "| Arm | Repeat | Shipped tests passed | Execution | Native seconds |",
        "| --- | ---: | ---: | --- | ---: |",
    ]
    lines += [
        f"| {s['arm']} | {s['repeat']} | "
        f"{s['passed'] if s['passed'] is not None else 'missing'}/{s['total']} | "
        f"{s['execution_status']} | {s['seconds']} |"
        for s in scores
    ]
    lines += [
        "",
        f"Original reference: {sum(v == 'pass' for v in reference['cases'].values())}"
        f"/{len(reference['cases'])}.",
        "",
        "Each row is one fixed-artifact attempt, not an independent set of sampled tasks. "
        "These scores measure compatibility with the pinned shipped tests. Known reference "
        "failures remain visible; passing the suite does not prove mathematical correctness. "
        "Missing infrastructure outcomes are not scored as failures. No test feedback was "
        "provided to builders. Native usage is root-inclusive; setup/export and offline testing "
        "are outside the native deadline. Token and spend caps are unavailable.",
        "",
        "[Scores, per-test outcomes and resources](scores.json)",
        "",
        "[Frozen allocation and boundaries](../../review.md)",
        "",
    ]
    write_new(destination / "report.md", "\n".join(lines).encode())
    return destination / "report.md"
