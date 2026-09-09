"""Configurable native v2 orchestration; task semantics live in contracts/checkers."""

import re
import subprocess
from pathlib import Path

from .app import external_root, procedure_files, runtime_versions
from .evidence import (
    EvidenceStore,
    inventory,
    read_regular,
    reject_links,
    safe_name,
    seal_run,
    verify_run,
    write_new,
)
from .native import native_package, native_usage
from .native_capture import recorded_native_files
from .native_checkers import check
from .native_contracts import (
    FileMaterials,
    NativeStudyV2,
    TaskContract,
    builder_files,
    make_native_plan,
    prepare_files,
    resolve_sources,
    validate_materials,
)
from .native_execution import RUNTIME, execute_native
from .preparation_evidence import load_preparation
from .records import canonical, digest, identity, parse_json

MISSING = {"harness_failure", "cli_failure", "dependency_missing"}
STATUSES = MISSING | {
    "completed",
    "budget_exhausted",
    "build_failed",
    "package_ready",
    "dependency_failed",
}


def checker_identity(task: TaskContract) -> tuple[dict, dict[str, bytes]]:
    procedure = procedure_files()
    files = {
        name: procedure[name]
        for name in ("native_checkers.py", "scoring.py", "records.py", "study.py")
    }
    return {
        "method": "deterministic",
        "version": task.checker,
        "id": identity({name: digest(data) for name, data in files.items()}),
    }, files


def common_prompt(task: TaskContract, role: str, *, complete_facts: bool = False) -> str:
    if role == "build":
        return (
            task.build_prompt + "\n\n"
            f"Read the brief and development examples at /work/{task.brief_path}. "
            f"Create a reusable native Codex skill named {task.package_name}. "
            f"Write the complete package under /work/{task.package_path}/ "
            "with SKILL.md at its root. "
            "It must work after installation elsewhere without build-workspace dependencies. "
            "Use only supplied inputs and checks you devise. Write notes outside the package. "
            "Complete one package without asking questions. Native subagents share this trial's "
            "filesystem and deadline. Python 3, PyYAML and Node are installed; "
            "shell network is disabled."
        )
    if complete_facts:
        facts = (
            ""
            if task.requirements in task.consumer_prompt
            else "\n\nTask requirements:\n" + task.requirements
        )
        return (
            task.consumer_prompt + facts + "\n\n"
            f"Write the required JSON to /work/{task.result_path}. "
            "Complete the work without asking questions. Python 3 and Node are available."
        )
    return (
        task.consumer_prompt + "\n\n"
        f"Use ${task.package_name}. Write the required JSON to /work/{task.result_path}. "
        "Complete the work without asking questions. Python 3 and Node are available."
    )


def prepare_native_v2(study_path: Path, root: Path, image: str) -> Path:
    root = external_root(root)
    original_request = read_regular(study_path)
    study = NativeStudyV2.model_validate(parse_json(original_request))
    preparation = load_preparation(study, study_path.resolve().parent)
    if preparation is not None:
        validation = parse_json(preparation["validation.json"])
        if validation.get("checker") != checker_identity(study.task)[0]:
            raise ValueError(
                "checker changed since preparation review; create a new draft revision"
            )
    prepared = {
        c.id: prepare_files(study.task, c, study_path.resolve().parent) for c in study.conditions
    }
    if study.scope == "synthetic-fixture" and any(
        not item[0].synthetic for item in prepared.values()
    ):
        raise ValueError("synthetic-fixture scope requires synthetic materials")
    make_native_plan(study, {key: value[0] for key, value in prepared.items()}, "preflight")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ValueError("pin the native runtime by its local Docker image SHA-256 identity")
    sources = resolve_sources(study, study_path.resolve().parent)
    subprocess.run(["docker", "image", "inspect", image], capture_output=True, check=True)
    root.mkdir(parents=True, exist_ok=False)
    store = EvidenceStore(root)
    frozen_conditions = []
    for condition in study.conditions:
        materials, provenance, original = prepared[condition.id]
        original_id = store.put({"original.json": original})
        frozen_conditions.append(
            {
                "id": condition.id,
                "original_id": original_id,
                "derived_from": original_id,
                "materials_id": store.put_json(materials.model_dump(mode="json"), "materials.json"),
                "provenance": provenance,
            }
        )
    config = read_regular(RUNTIME / "config.toml").decode("utf-8")
    config = re.sub(r"^model = .*$", f'model = "{study.model}"', config, flags=re.M)
    config = re.sub(
        r"^model_reasoning_effort = .*$",
        f'model_reasoning_effort = "{study.reasoning_effort}"',
        config,
        flags=re.M,
    )
    frozen_sources = {
        s.id: {
            "artifact_id": store.put(sources[s.id][0], executable=s.executable),
            "source_path": sources[s.id][1],
            "profile": "explicit file allowlist; exact byte pins and declared modes",
        }
        for s in study.sources
    }
    body = {
        "schema_version": 2,
        "study": study.model_dump(mode="json"),
        "request_id": store.put({"original.json": original_request}),
        "conditions": frozen_conditions,
        "sources": frozen_sources,
        "procedure_id": store.put(procedure_files()),
        "runtime_files_id": store.put(
            {p.name: read_regular(p) for p in sorted(RUNTIME.iterdir()) if p.is_file()}
        ),
        "config_id": store.put({"config.toml": config.encode("utf-8")}),
        "runtime": {"image": image, "codex": "0.153.4", **runtime_versions()},
        "scorer": checker_identity(study.task)[0],
        "design": {
            "retries": 0,
            "analysis": "descriptive; conditions and independent builds remain separate",
            "consumer_context": (
                "complete task requirements and current case files for every consumer; "
                "package consumers additionally receive and explicitly invoke their parent package"
                if study.consumer_baseline
                else "current case files and the exact parent package only"
            ),
            "limitations": [
                "Prepared cases are deterministic synthetic fixtures; "
                "task coverage is declared, not inferred.",
                "Repeated uses of one package are not independent builder measurements.",
                "Native subagents share the attempt boundary and deadline; "
                "their usage belongs to the treatment.",
                "No hard token or spend cap; deadlines exclude setup/export, "
                "and billing cost is unavailable.",
                "Model aliases are not immutable model-weight pins; "
                "no inferential or cross-vendor claim.",
            ],
        },
    }
    if preparation is not None:
        body["preparation_id"] = store.put(preparation)
    frozen = {"id": identity(body), **body}
    write_new(root / "study.json", canonical(frozen))
    plan = make_native_plan(study, {key: value[0] for key, value in prepared.items()}, frozen["id"])
    write_new(root / "plan.json", canonical(plan))
    freeze = {"schema_version": 2, "files": inventory(root)}
    write_new(root / "freeze-seal.json", canonical({"id": identity(freeze), **freeze}))
    return root


def load_native_v2(root: Path):
    frozen = parse_json(read_regular(root / "study.json"))
    if (
        frozen.get("schema_version") != 2
        or identity({k: v for k, v in frozen.items() if k != "id"}) != frozen["id"]
    ):
        raise ValueError("invalid native v2 frozen study")
    study = NativeStudyV2.model_validate(frozen["study"])
    store = EvidenceStore(root)
    materials = {
        c["id"]: FileMaterials.model_validate(store.json(c["materials_id"], "materials.json"))
        for c in frozen["conditions"]
    }
    if set(materials) != {c.id for c in study.conditions}:
        raise ValueError("frozen condition mismatch")
    for material in materials.values():
        validate_materials(study.task, material)
    plan = parse_json(read_regular(root / "plan.json"))
    if plan != make_native_plan(study, materials, frozen["id"]):
        raise ValueError("frozen native plan mismatch")
    return frozen, plan, study, materials


def executable_paths(store: EvidenceStore, artifact_id: str) -> tuple[str, ...]:
    manifest = parse_json(read_regular(store.root / "artifacts" / artifact_id / "manifest.json"))
    return tuple(x["path"] for x in manifest["files"] if x["executable"])


def execute_native_v2(root: Path, auth_path: Path) -> Path:
    freeze = parse_json(read_regular(root / "freeze-seal.json"))
    if (
        identity({k: v for k, v in freeze.items() if k != "id"}) != freeze["id"]
        or [x for x in inventory(root) if x["path"] != "freeze-seal.json"] != freeze["files"]
    ):
        raise ValueError("frozen evidence changed or execution already started; use a new run")
    frozen, plan, study, materials = load_native_v2(root)
    store = EvidenceStore(root)
    if store.get(frozen["procedure_id"]) != procedure_files():
        raise ValueError("implementation changed after freeze")
    if any(frozen["runtime"][name] != value for name, value in runtime_versions().items()):
        raise ValueError("runtime dependencies changed after freeze")
    runtime_files = {p.name: read_regular(p) for p in sorted(RUNTIME.iterdir()) if p.is_file()}
    if store.get(frozen["runtime_files_id"]) != runtime_files:
        raise ValueError("runtime files changed after freeze")
    arms = {a.id: a for a in study.arms}
    results = {}
    common = {}
    for trial in plan["trials"]:
        material = materials[trial["condition"]]
        parent = results.get(trial["parent"])
        if parent and parent["status"] != "package_ready":
            results[trial["id"]] = {
                "status": "dependency_missing"
                if parent["status"] in MISSING
                else "dependency_failed",
                "parent": trial["parent"],
                "reason": parent["status"],
                "launched": False,
            }
            continue
        key = (trial["condition"], trial["role"], trial["case"])
        if key not in common:
            if trial["role"] == "build":
                inputs = builder_files(study.task, material)
            else:
                case = next(c for c in material.evaluation if c.id == trial["case"])
                inputs = {n: text.encode("utf-8") for n, text in case.files.items()}
            prompt = common_prompt(
                study.task, trial["role"], complete_facts=study.consumer_baseline is not None
            )
            common[key] = (inputs, prompt, store.put({"prompt.txt": prompt.encode(), **inputs}))
        inputs, prompt, common_id = common[key]
        files = dict(inputs)
        modes = []
        treatment = []
        if trial["role"] == "build":
            arm = arms[trial["arm"]]
            if arm.invocation:
                prompt = arm.invocation + "\n\n" + prompt
            for source in arm.sources:
                artifact = frozen["sources"][source]["artifact_id"]
                treatment.append(artifact)
                files.update(
                    {".agents/skills/" + n: data for n, data in store.get(artifact).items()}
                )
                modes.extend(".agents/skills/" + n for n in executable_paths(store, artifact))
            timeout = study.admission.build_timeout_seconds
        else:
            if parent:
                artifact = parent["package_id"]
                treatment.append(artifact)
                prefix = f".agents/skills/{study.task.package_name}/"
                files.update({prefix + n: data for n, data in store.get(artifact).items()})
                modes.extend(prefix + n for n in executable_paths(store, artifact))
                if study.consumer_baseline:
                    prompt = f"Use ${study.task.package_name}.\n\n" + prompt
            timeout = study.admission.consumer_timeout_seconds
        binding = {
            "schema_version": 2,
            "study_id": frozen["id"],
            "plan_id": plan["id"],
            "trial": trial,
            "common_id": common_id,
            "treatment_ids": treatment,
            "prompt_sha256": digest(prompt.encode()),
            "input_files": {n: digest(b) for n, b in files.items()},
            "executable": sorted(modes),
        }
        # Store bindings outside attempt directories; the adapter owns their creation.
        write_new(root / "bindings" / f"{trial['id']}.json", canonical(binding))
        print(f"Running {trial['id']}", flush=True)
        result = execute_native(
            root,
            trial["id"],
            prompt,
            files,
            image=frozen["runtime"]["image"],
            auth_path=auth_path,
            config=store.get(frozen["config_id"])["config.toml"],
            timeout=timeout,
            executable=tuple(modes),
        )
        result = {**result, "common_id": common_id, "parent": trial["parent"], "launched": True}
        if (
            trial["role"] == "build"
            and result.get("output_id")
            and result["status"] in {"completed", "budget_exhausted"}
        ):
            try:
                if result.get("rejected_paths"):
                    raise ValueError("export contained non-regular or oversized paths")
                result["package_id"] = native_package(
                    store.get(result["output_id"]),
                    store,
                    result["output_id"],
                    package_name=study.task.package_name,
                    package_path=study.task.package_path,
                )
                result["status"] = "package_ready"
            except (ValueError, UnicodeError, RecursionError) as error:
                result.update(status="build_failed", reason=str(error))
        elif trial["role"] == "build" and result["status"] == "completed":
            result.update(status="build_failed", reason="no recorded package output")
        results[trial["id"]] = result
        print(f"Finished {trial['id']}: {result['status']}", flush=True)
    write_new(
        root / "results.json",
        canonical(
            {
                "schema_version": 2,
                "study_id": frozen["id"],
                "plan_id": plan["id"],
                "trials": results,
            }
        ),
    )
    seal_run(root)
    return rescore_native_v2(root, "original")


def rescore_native_v2(root: Path, label: str, reason: str | None = None) -> Path:
    safe_name(label)
    if "/" in label:
        raise ValueError("interpretation label must be one path component")
    seal = verify_run(root)
    frozen, plan, study, materials = load_native_v2(root)
    record = parse_json(read_regular(root / "results.json"))
    results = record["trials"]
    if (
        record.get("schema_version") != 2
        or record.get("study_id") != frozen["id"]
        or record.get("plan_id") != plan["id"]
        or set(results) != {t["id"] for t in plan["trials"]}
    ):
        raise ValueError("incomplete or mismatched native results")
    store = EvidenceStore(root)
    scorer, scorer_files = checker_identity(study.task)
    if scorer != frozen["scorer"] and not reason:
        raise ValueError("scorer changed; record --reason for a new interpretation")
    scores, usage = [], {}
    for trial in plan["trials"]:
        result = results[trial["id"]]
        if result["status"] not in STATUSES:
            raise ValueError("unknown native result status")
        files = recorded_native_files(store, result)
        if files:
            try:
                usage[trial["id"]] = native_usage(files)
            except (ValueError, UnicodeError, KeyError, TypeError) as error:
                usage[trial["id"]] = {"unavailable": str(error)}
        if trial["role"] == "build":
            continue
        if result["status"] in MISSING:
            verdict = {
                "value": None,
                "components": {},
                "reason": result.get("reason") or result["status"],
            }
        elif result["status"] == "dependency_failed":
            verdict = {
                "value": 0,
                "components": {},
                "reason": result.get("reason") or "upstream build failed",
            }
        elif result.get("rejected_paths"):
            verdict = {"value": 0, "components": {}, "reason": "export contained rejected paths"}
        else:
            case = next(
                c for c in materials[trial["condition"]].evaluation if c.id == trial["case"]
            )
            verdict = check(
                study.task.checker, files.get(study.task.result_path, b""), case.expected
            )
        scores.append(
            {
                **trial,
                **verdict,
                "status": result["status"],
                "output_id": result.get("output_id"),
                "package_id": results.get(trial["parent"], {}).get("package_id"),
            }
        )
    score_record = {
        "schema_version": 2,
        "run_seal": seal,
        "study_id": frozen["id"],
        "plan_id": plan["id"],
        "scorer": scorer,
        "revision_reason": reason,
        "scores": scores,
    }
    summary = []
    for condition in study.conditions:
        for arm in study.arms:
            for build in range(1, arm.builds + 1):
                selected = [
                    s
                    for s in scores
                    if s["condition"] == condition.id and s["arm"] == arm.id and s["build"] == build
                ]
                values = [s["value"] for s in selected if s["value"] is not None]
                summary.append(
                    {
                        "condition": condition.id,
                        "arm": arm.id,
                        "build": build,
                        "passed": sum(values),
                        "scored": len(values),
                        "planned": len(selected),
                        "missing": len(selected) - len(values),
                    }
                )
    baseline_summary = []
    if study.consumer_baseline:
        for condition in study.conditions:
            selected = [
                s
                for s in scores
                if s["condition"] == condition.id and s["arm"] == study.consumer_baseline.id
            ]
            values = [s["value"] for s in selected if s["value"] is not None]
            baseline_summary.append(
                {
                    "condition": condition.id,
                    "arm": study.consumer_baseline.id,
                    "passed": sum(values),
                    "scored": len(values),
                    "planned": len(selected),
                    "missing": len(selected) - len(values),
                }
            )
    by_case = []
    for condition in study.conditions:
        for case in materials[condition.id].evaluation:
            for arm in [a.id for a in study.arms] + (
                [study.consumer_baseline.id] if study.consumer_baseline else []
            ):
                selected = [
                    s
                    for s in scores
                    if s["condition"] == condition.id and s["case"] == case.id and s["arm"] == arm
                ]
                values = [s["value"] for s in selected if s["value"] is not None]
                by_case.append(
                    {
                        "condition": condition.id,
                        "case": case.id,
                        "group": case.group,
                        "arm": arm,
                        "passed": sum(values),
                        "scored": len(values),
                        "planned": len(selected),
                        "missing": len(selected) - len(values),
                    }
                )
    destination = root / "interpretations" / label
    reject_links(destination)
    destination.mkdir(parents=True, exist_ok=False)
    write_new(destination / "scores.json", canonical(score_record))
    write_new(destination / "usage.json", canonical(usage))
    analysis = {"schema_version": 2, "by_build": summary, "by_case": by_case}
    if study.consumer_baseline:
        analysis["by_baseline"] = baseline_summary
    write_new(destination / "analysis.json", canonical(analysis))
    for name, data in scorer_files.items():
        write_new(destination / "scorer" / name, data)
    lines = [
        "# Native study result",
        "",
        study.question,
        "",
        f"Task `{study.task.id}`; checker `{study.task.checker}`; scope `{study.scope}`. "
        f"Model `{study.model}`, reasoning `{study.reasoning_effort}`, "
        f"Codex `{frozen['runtime']['codex']}`, "
        f"Inspect `{frozen['runtime']['inspect_ai']}`.",
        "",
        f"Plan: {plan['reserved_attempts']} maximum native attempts and "
        f"{plan['reserved_native_seconds']} native command seconds (setup/export excluded). "
        f"{study.consumer_repeats} fresh consumer repeats per package/case; no harness retries.",
        "",
        "Each build below is an independent attempt; "
        "identical package bytes may share an artifact ID. "
        + frozen["design"]["consumer_context"]
        + ". Built-in skills remain present.",
        "",
        "| Condition | Arm | Build | Passed | Scored | Planned | Missing |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    lines += [
        f"| {s['condition']} | {s['arm']} | {s['build']} | {s['passed']} | "
        f"{s['scored']} | {s['planned']} | {s['missing']} |"
        for s in summary
    ]
    if study.consumer_baseline:
        lines += [
            "",
            "## Consumer baseline",
            "",
            f"`{study.consumer_baseline.id}` receives no generated package and has no build "
            f"parent. It has {study.consumer_baseline.repeats} fresh repeat(s) per case, "
            "independent of builder allocation. All consumers receive the same task "
            "requirements and case files; package invocation is an explicit treatment difference.",
            "",
            "| Condition | Arm | Passed | Scored | Planned | Missing |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
        lines += [
            f"| {s['condition']} | {s['arm']} | {s['passed']} | {s['scored']} | "
            f"{s['planned']} | {s['missing']} |"
            for s in baseline_summary
        ]
    lines += [
        "",
        "## Case coverage",
        "",
        "Counts below describe the fixed cases, pooling package uses within each builder "
        "arm. They are not additional independent builds. Full success or failure across "
        "these cases can reveal score saturation; it does not establish equivalence or "
        "performance on a broader workload.",
        "",
        "| Condition | Case | Arm | Passed | Scored | Planned | Missing |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    lines += [
        f"| {s['condition']} | {s['case']} | {s['arm']} | {s['passed']} | {s['scored']} | "
        f"{s['planned']} | {s['missing']} |"
        for s in by_case
    ]
    lines += [
        "",
        "## Attempt evidence",
        "",
        "| Attempt | Result | Native status | Seconds | Input tokens | Output tokens |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for trial in plan["trials"]:
        result = results[trial["id"]]
        attempt = root / "attempts" / trial["id"] / "result.json"
        native = parse_json(read_regular(attempt)) if attempt.is_file() else {}
        native_status = native.get("native_status", native.get("status", "not launched"))
        totals = usage.get(trial["id"], {}).get("totals", {})
        lines.append(
            f"| {trial['id']} | {result['status']} | {native_status} | "
            f"{result.get('duration_seconds', 0):.1f} | "
            f"{totals.get('input_tokens', 'unavailable')} | "
            f"{totals.get('output_tokens', 'unavailable')} |"
        )
    lines += [
        "",
        "Build deadlines and package readiness remain separate; "
        "usable deadline outputs may proceed. Input usage includes cached tokens. "
        "Native response IDs deduplicate parent/subagent usage; "
        "aborted calls can leave unreported usage. Dollar cost is unavailable.",
        "",
        "## Preparation and limits",
        "",
    ]
    for condition in frozen["conditions"]:
        provenance = condition["provenance"]
        lines.append(
            f"- `{condition['id']}`: {provenance['route']}; {provenance['verification']}. "
            f"[Original](../../artifacts/{condition['original_id']}/files/original.json), "
            f"[prepared materials](../../artifacts/{condition['materials_id']}"
            "/files/materials.json)."
        )
    lines += [f"- {item}" for item in frozen["design"]["limitations"]]
    lines += [
        "",
        "## Preserved evidence",
        "",
        f"Run seal: `{seal}`.",
        "",
        "- [Frozen study and source pins](../../study.json)",
        "- [Plan](../../plan.json)",
        "- [Results and lineage](../../results.json)",
        "- [Scores](scores.json)",
        "- [Per-build counts](analysis.json)",
        "- [Native usage](usage.json)",
    ]
    if frozen.get("preparation_id"):
        lines.append(
            f"- [Preparation review and original requests]"
            f"(../../artifacts/{frozen['preparation_id']}/files/review.md)"
        )
    for trial in plan["trials"]:
        result = results[trial["id"]]
        if result.get("launched"):
            lines.append(f"- [{trial['id']} binding](../../bindings/{trial['id']}.json)")
        if result.get("inspect_log"):
            lines.append(f"- [{trial['id']} Inspect log](../../{result['inspect_log']})")
        if result.get("package_id"):
            lines.append(
                f"- [{trial['id']} package](../../artifacts/{result['package_id']}/files/SKILL.md)"
            )
        for key, file in (
            ("preflight_check_id", "check.json"),
            ("expected_catalog_id", "catalog.json"),
            ("catalog_check_id", "check.json"),
            ("native_logs_id", "archive.json"),
        ):
            if result.get(key):
                lines.append(f"- [{trial['id']} {key}](../../artifacts/{result[key]}/files/{file})")
        for phase, capture in result.get("captures", {}).items():
            lines.append(
                f"- [{trial['id']} {phase} capture]"
                f"(../../artifacts/{capture['archive_id']}/files/archive.json)"
            )
    report = destination / "report.md"
    write_new(report, ("\n".join(lines) + "\n").encode("utf-8"))
    return report
