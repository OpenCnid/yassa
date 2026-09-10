"""CLI and single-controller composition of the first complete fixture path."""

import argparse
import importlib.metadata
import platform
import sys
from pathlib import Path

from pydantic import ValidationError

from . import __version__
from .contexts import binding, common_input
from .evidence import (
    EvidenceStore,
    freeze_package,
    inventory,
    read_regular,
    reject_links,
    safe_name,
    seal_run,
    verify_run,
    write_new,
)
from .execution import execute_attempt
from .planning import make_plan
from .prepare import intake, prepare_condition
from .records import canonical, digest, identity, parse_json
from .reporting import render_report, summarize
from .scoring import SCORER_VERSION, check_work
from .simulation import MODEL_NAME, treatment_files
from .study import Materials, Study


def procedure_files() -> dict[str, bytes]:
    package = Path(__file__).parent
    return {path.name: read_regular(path) for path in sorted(package.glob("*.py"))}


def scorer_identity() -> tuple[dict, dict[str, bytes]]:
    files = procedure_files()
    sources = {name: files[name] for name in ("scoring.py", "records.py")}
    return {
        "version": SCORER_VERSION,
        "method": "deterministic",
        "id": identity({name: digest(data) for name, data in sources.items()}),
    }, sources


def external_root(path: Path) -> Path:
    reject_links(path)
    target = path.resolve()
    # Reject the source checkout and any other Git checkout ancestor of the run root.
    if any((parent / ".git").exists() for parent in [target, *target.parents]):
        raise ValueError("run evidence must live outside a Git/source repository")
    return target


def runtime_versions() -> dict:
    return {
        "python": platform.python_version(),
        "inspect_ai": importlib.metadata.version("inspect-ai"),
        "pydantic": importlib.metadata.version("pydantic"),
        "dependencies": dict(
            sorted(
                (distribution.metadata["Name"], distribution.version)
                for distribution in importlib.metadata.distributions()
            )
        ),
    }


def prepare(study_path: Path, run_root: Path) -> Path:
    root = external_root(run_root)
    raw_request = read_regular(study_path)
    study = Study.model_validate(parse_json(raw_request))
    prepared = {
        condition.id: prepare_condition(condition, study_path.absolute().parent)
        for condition in study.conditions
    }
    # Validate budget arithmetic before creating evidence or releasing any calls.
    make_plan(study, {key: value[0] for key, value in prepared.items()}, "preflight")
    root.mkdir(parents=True, exist_ok=False)
    store = EvidenceStore(root)
    request_id = store.put({"original.json": raw_request})
    source_id = store.put(procedure_files())
    conditions = []
    for condition in study.conditions:
        materials, provenance, original = prepared[condition.id]
        original_id = store.put({"original.json": original})
        material_id = store.put_json(materials.model_dump(mode="json"), "materials.json")
        conditions.append(
            {
                "id": condition.id,
                "original_id": original_id,
                "materials_id": material_id,
                "provenance": provenance,
                "derived_from": original_id,
            }
        )
    sources = {arm.id: store.put(treatment_files(arm.fixture_behavior)) for arm in study.arms}
    scorer, _ = scorer_identity()
    frozen = {
        "schema_version": 1,
        "study": study.model_dump(mode="json"),
        "request_id": request_id,
        "conditions": conditions,
        "treatments": sources,
        "procedure_id": source_id,
        "scorer": scorer,
        "runtime": {
            "route": "simulated-api",
            "model": MODEL_NAME,
            "simulation": True,
            "yassa": __version__,
            **runtime_versions(),
            "platform": platform.platform(),
            "native_cli": "unsupported",
            "loading": "explicit text package",
            "network": "no subject network or tools",
            "model_calls_per_attempt": 1,
        },
        "source_policy": "Yassa-owned fixture treatments only; external builders unsupported",
    }
    frozen = {"id": identity(frozen), **frozen}
    write_new(root / "study.json", canonical(frozen))
    plan = make_plan(study, {key: value[0] for key, value in prepared.items()}, frozen["id"])
    write_new(root / "plan.json", canonical(plan))
    body = {"schema_version": 1, "files": inventory(root)}
    write_new(root / "freeze-seal.json", canonical({"id": identity(body), **body}))
    return root


def load_frozen(root: Path) -> tuple[dict, dict, Study, dict[str, Materials]]:
    frozen = parse_json(read_regular(root / "study.json"))
    plan = parse_json(read_regular(root / "plan.json"))
    if identity({key: value for key, value in frozen.items() if key != "id"}) != frozen["id"]:
        raise ValueError("frozen study identity mismatch")
    study = Study.model_validate(frozen["study"])
    store = EvidenceStore(root)
    materials = {
        condition["id"]: Materials.model_validate(
            store.json(condition["materials_id"], "materials.json")
        )
        for condition in frozen["conditions"]
    }
    if plan != make_plan(study, materials, frozen["id"]):
        raise ValueError("frozen plan mismatch")
    return frozen, plan, study, materials


def execute(root: Path) -> Path:
    root = root.resolve()
    freeze = parse_json(read_regular(root / "freeze-seal.json"))
    body = {key: value for key, value in freeze.items() if key != "id"}
    current = [entry for entry in inventory(root) if entry["path"] != "freeze-seal.json"]
    if identity(body) != freeze["id"] or current != freeze["files"]:
        raise ValueError(
            "prepared evidence changed or execution already started; automatic resume "
            "is unsupported. Preserve this run and use a new run directory."
        )
    frozen, plan, study, materials = load_frozen(root)
    store = EvidenceStore(root)
    if store.get(frozen["procedure_id"]) != procedure_files():
        raise ValueError("implementation changed after freeze; prepare a new revision")
    if any(frozen["runtime"][name] != value for name, value in runtime_versions().items()):
        raise ValueError("runtime dependencies changed after freeze; prepare a new revision")
    arms = {arm.id: arm for arm in study.arms}
    common = {}  # One rendered common segment per matched condition/case/stage.
    for trial in plan["trials"]:
        key = (trial["condition"], trial["role"] == "build", trial["case"])
        if key not in common:
            material = materials[trial["condition"]]
            case = next((case for case in material.evaluation if case.id == trial["case"]), None)
            common[key] = common_input(trial["role"], material, case)
    results = {}
    attempts = []
    for trial in plan["trials"]:
        parent = results.get(trial["parent_build"])
        result = {
            "trial_id": trial["id"],
            "role": trial["role"],
            "selected_attempt": None,
            "package_id": None,
            "output_id": None,
            "reason": None,
        }
        if parent and parent["status"] != "package_ready":
            result.update(
                status="dependency_missing"
                if parent["status"] in {"infrastructure_failure", "harness_failure"}
                else "dependency_failed",
                reason=f"upstream build {parent['trial_id']}: {parent['status']}",
            )
            results[trial["id"]] = result
            continue
        treatment_id = parent["package_id"] if parent else frozen["treatments"][trial["arm"]]
        context = binding(
            trial,
            common[(trial["condition"], trial["role"] == "build", trial["case"])],
            store.get(treatment_id),
            treatment_id,
            frozen["id"],
            plan["id"],
            parent["selected_attempt"] if parent else None,
        )
        for attempt_number in range(1, study.limits.infrastructure_retries + 2):
            # Fault injection is a declared fixture setting. Consumers share an unmodified runtime.
            failures = 0 if parent else arms[trial["arm"]].infrastructure_failures
            attempt = execute_attempt(root, trial, context, study.limits, attempt_number, failures)
            attempts.append(attempt)
            if attempt["status"] != "infrastructure_failure":
                break
        result.update(
            selected_attempt=attempt["id"],
            output_id=attempt["output_id"],
            status=attempt["status"],
            reason=attempt["error"],
        )
        if trial["role"] == "build" and attempt["status"] in {"completed", "budget_exhausted"}:
            try:
                result["package_id"] = freeze_package(
                    store.get(attempt["output_id"])["response.txt"], store
                )
                result["status"] = "package_ready"
            except (ValueError, UnicodeError, RecursionError) as error:
                result.update(status="build_failed", reason=str(error))
        results[trial["id"]] = result
    write_new(
        root / "results.json",
        canonical(
            {
                "schema_version": 1,
                "study_id": frozen["id"],
                "plan_id": plan["id"],
                "trials": results,
                "attempts": [attempt["id"] for attempt in attempts],
            }
        ),
    )
    seal_run(root)
    return rescore(root, "original")


def rescore(root: Path, label: str, reason: str | None = None) -> Path:
    safe_name(label)
    if "/" in label:
        raise ValueError("interpretation label must be a single path component")
    seal_id = verify_run(root)
    frozen, plan, _, materials = load_frozen(root)
    store = EvidenceStore(root)
    scorer, sources = scorer_identity()
    if scorer != frozen["scorer"] and not reason:
        raise ValueError("scorer changed; supply --reason to record a new scoring interpretation")
    selections = parse_json(read_regular(root / "results.json"))
    results = selections["trials"]
    scores = []
    for trial in plan["trials"]:
        if trial["role"] == "build":
            continue
        result = results[trial["id"]]
        record = {
            "trial_id": trial["id"],
            "condition": trial["condition"],
            "arm": trial["arm"],
            "role": trial["role"],
            "case": trial["case"],
            "group": trial["group"],
            "build": trial["build"],
            "repeat": trial["repeat"],
            "parent_build": trial["parent_build"],
            "attempt_id": result["selected_attempt"],
            "output_id": result["output_id"],
            "status": result["status"],
        }
        if result["status"] == "dependency_failed":
            verdict = {"value": 0, "components": {}, "reason": result["reason"]}
        elif result["status"] in {
            "dependency_missing",
            "infrastructure_failure",
            "harness_failure",
        }:
            verdict = {"value": None, "components": {}, "reason": result["reason"]}
        else:
            case = next(
                case
                for case in materials[trial["condition"]].evaluation
                if case.id == trial["case"]
            )
            verdict = check_work(
                store.get(result["output_id"])["response.txt"],
                [total.model_dump() for total in case.expected],
            )
        scores.append({**record, **verdict})
    score_record = {
        "schema_version": 1,
        "run_seal": seal_id,
        "study_id": frozen["id"],
        "plan_id": plan["id"],
        "scorer": scorer,
        "revision_reason": reason,
        "scores": scores,
    }
    attempt_records = [
        parse_json(read_regular(root / "attempts" / attempt / "result.json"))
        for attempt in selections["attempts"]
    ]
    summary = summarize(scores, results, attempt_records)
    destination = root / "interpretations" / label
    reject_links(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for name, content in sources.items():
        write_new(destination / "scorer" / name, content)
    write_new(destination / "scores.json", canonical(score_record))
    write_new(destination / "analysis.json", canonical(summary))
    write_new(
        destination / "report.md",
        render_report(frozen, plan, score_record, summary, results, attempt_records).encode(),
    )
    return destination / "report.md"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Yassa: traceable simulated fixtures and configurable native studies"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "run"):
        command = commands.add_parser(name)
        command.add_argument("study", type=Path)
        command.add_argument("--run-dir", required=True, type=Path)
    for name in ("execute", "rescore", "verify"):
        command = commands.add_parser(name)
        command.add_argument("run_dir", type=Path)
        if name == "rescore":
            command.add_argument("--label", required=True)
            command.add_argument("--reason")
    command = commands.add_parser("intake")
    command.add_argument("request", type=Path)
    command = commands.add_parser("study-schema", help="print a general preparation JSON schema")
    command.add_argument(
        "kind", choices=("request", "task", "cases", "proposal", "review", "native")
    )
    command = commands.add_parser("study-draft", help="develop a rough request into a native study")
    command.add_argument("request", type=Path)
    command.add_argument("--draft-dir", required=True, type=Path)
    command.add_argument("--auth-file", type=Path, help="native preparation only; never frozen")
    command = commands.add_parser("direct-prepare", help="freeze a direct study on a pinned task")
    command.add_argument("request", type=Path)
    command.add_argument("--run-dir", required=True, type=Path)
    command = commands.add_parser(
        "direct-execute", help="execute a frozen native or API direct study"
    )
    command.add_argument("run_dir", type=Path)
    command.add_argument("--auth-file", type=Path)
    command = commands.add_parser(
        "direct-rescore", help="score recorded direct work without model calls"
    )
    command.add_argument("run_dir", type=Path)
    command.add_argument("--label", required=True)
    command.add_argument("--reason")
    command = commands.add_parser("study-revise", help="record answers in a new preparation round")
    command.add_argument("previous", type=Path)
    command.add_argument("answers", type=Path)
    command.add_argument("--draft-dir", required=True, type=Path)
    command.add_argument("--auth-file", type=Path, help="native preparation only; never frozen")
    command = commands.add_parser(
        "role-schema", help="print direct-study or external grading schemas"
    )
    command.add_argument("kind", choices=("direct", "grading"))
    command = commands.add_parser("grade-prepare", help="freeze external grading of recorded work")
    command.add_argument("run_dir", type=Path)
    command.add_argument("request", type=Path)
    command.add_argument("--grade-dir", required=True, type=Path)
    command = commands.add_parser("grade-execute", help="calibrate and grade frozen recorded work")
    command.add_argument("grade_dir", type=Path)
    command = commands.add_parser("grade-report", help="replay recorded judgments without calls")
    command.add_argument("grade_dir", type=Path)
    command.add_argument("--label", required=True)
    for name in ("native-prepare", "native-run"):
        command = commands.add_parser(name)
        command.add_argument("study", type=Path)
        command.add_argument("--run-dir", required=True, type=Path)
        command.add_argument("--dovetail-dir", type=Path, help="legacy native v1 only")
        command.add_argument("--image", required=True)
        if name == "native-run":
            command.add_argument("--auth-file", required=True, type=Path)
    command = commands.add_parser("native-execute")
    command.add_argument("run_dir", type=Path)
    command.add_argument("--auth-file", required=True, type=Path)
    command = commands.add_parser("native-rescore")
    command.add_argument("run_dir", type=Path)
    command.add_argument("--label", required=True)
    command.add_argument("--reason")
    command = commands.add_parser(
        "native-resources", help="write a separate offline resource interpretation"
    )
    command.add_argument("run_dir", type=Path)
    command.add_argument("--scores", required=True, help="existing score interpretation label")
    command.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "study-schema":
            from .general_contracts import (
                CaseBatch,
                ExpertReview,
                GeneralRequest,
                StudyProposal,
                TaskProposal,
            )
            from .native_contracts import NativeStudyV2

            schemas = {
                "request": GeneralRequest,
                "task": TaskProposal,
                "cases": CaseBatch,
                "proposal": StudyProposal,
                "review": ExpertReview,
                "native": NativeStudyV2,
            }
            output = canonical(schemas[args.kind].model_json_schema()).decode().strip()
        elif args.command in {"study-draft", "study-revise"}:
            from .guided_preparation import prepare_draft

            output = (
                prepare_draft(args.request, args.draft_dir, auth_path=args.auth_file)
                if args.command == "study-draft"
                else prepare_draft(
                    args.answers, args.draft_dir, args.previous, auth_path=args.auth_file
                )
            )
        elif args.command == "role-schema":
            from .direct_contracts import DirectRequest
            from .grading import GradeRequest

            schema = DirectRequest if args.kind == "direct" else GradeRequest
            output = canonical(schema.model_json_schema()).decode().strip()
        elif args.command.startswith("grade-"):
            from .grading import execute_grades, prepare_grades, report_grades

            if args.command == "grade-prepare":
                output = prepare_grades(args.run_dir.resolve(), args.request, args.grade_dir)
            elif args.command == "grade-execute":
                output = execute_grades(args.grade_dir.resolve())
            else:
                output = report_grades(args.grade_dir.resolve(), args.label)
        elif args.command.startswith("direct-"):
            from .direct_runner import execute_direct, prepare_direct, rescore_direct

            if args.command == "direct-prepare":
                output = prepare_direct(args.request, args.run_dir)
            elif args.command == "direct-execute":
                output = execute_direct(args.run_dir.resolve(), args.auth_file)
            else:
                output = rescore_direct(args.run_dir.resolve(), args.label, args.reason)
        elif args.command.startswith("native-"):
            from .native import execute_native_study, prepare_native, rescore_native

            if args.command in {"native-prepare", "native-run"}:
                root = prepare_native(args.study, args.run_dir, args.dovetail_dir, args.image)
                output = (
                    execute_native_study(root, args.auth_file)
                    if args.command == "native-run"
                    else root / "plan.json"
                )
            elif args.command == "native-resources":
                from .native_resources import write_resource_interpretation

                output = write_resource_interpretation(
                    args.run_dir.resolve(), args.scores, args.output_dir
                )
            elif args.command == "native-execute":
                output = execute_native_study(args.run_dir.resolve(), args.auth_file)
            else:
                output = rescore_native(args.run_dir.resolve(), args.label, args.reason)
        elif args.command in {"prepare", "run"}:
            root = prepare(args.study, args.run_dir)
            output = execute(root) if args.command == "run" else root / "plan.json"
        elif args.command == "execute":
            output = execute(args.run_dir)
        elif args.command == "rescore":
            output = rescore(args.run_dir.resolve(), args.label, args.reason)
        elif args.command == "verify":
            output = f"Verified sealed run {verify_run(args.run_dir.resolve())}"
        else:
            output = canonical(intake(parse_json(read_regular(args.request)))).decode().strip()
        print(output)
        return 0
    except (ValueError, OSError, ValidationError) as error:
        print(f"yassa: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
