"""Native version dispatch and the preserved v1 builder fixture and readers."""

import json
import random
import re
import subprocess
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import Field, StrictInt, model_validator

from .app import external_root, procedure_files, runtime_versions, scorer_identity
from .control import (
    control_link,
    managed,
    native_call,
    result_path,
    same_or_new,
    selected_result,
    start_control,
    verify_execution_freeze,
)
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
from .native_execution import RUNTIME, execute_native
from .prepare import prepare_condition
from .records import canonical, digest, identity, parse_json
from .scoring import CONTRACT, check_work
from .study import Condition, Materials, Record, Slug


class NativeStudy(Record):
    schema_version: Literal[1]
    id: Slug
    question: str
    scope: Literal["synthetic-fixture"]
    runtime: Literal["native-codex-cli"]
    model: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_.-]+$")]
    reasoning_effort: Literal["low", "medium", "high", "xhigh"]
    source_skills: Annotated[tuple[Slug, ...], Field(min_length=1, max_length=12)]
    conditions: Annotated[tuple[Condition, ...], Field(min_length=2, max_length=2)]
    schedule_seed: StrictInt
    build_timeout_seconds: Annotated[StrictInt, Field(ge=30, le=600)]
    consumer_timeout_seconds: Annotated[StrictInt, Field(ge=30, le=300)]

    @model_validator(mode="after")
    def distinct(self):
        if {c.route for c in self.conditions} != {"user-supplied", "yassa-prepared"}:
            raise ValueError("native fixture requires both input preparation conditions")
        if len({c.id for c in self.conditions}) != len(self.conditions):
            raise ValueError("duplicate condition")
        if len(set(self.source_skills)) != len(self.source_skills):
            raise ValueError("duplicate source skill")
        if "better-skill-creator" not in self.source_skills:
            raise ValueError("Dovetail fixture invokes better-skill-creator")
        return self


SOURCE_DIRS = {"agents", "references", "scripts", "assets", "eval-viewer"}
SOURCE_FILES = {"SKILL.md", "README.md", "LICENSE", "LICENSE.txt", "NOTICE", "requirements.txt"}


def snapshot_source(source: Path, names: tuple[str, ...]) -> tuple[dict[str, bytes], dict]:
    """Explicit runtime distribution profile; no tests, caches or personal configuration."""
    files = {}
    excluded = []
    for name in names:
        directory = source / name
        read_regular(directory / "SKILL.md")
        for path in sorted(directory.rglob("*")):
            relative = path.relative_to(directory)
            if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
                continue
            if relative.parts[0] not in SOURCE_DIRS and relative.as_posix() not in SOURCE_FILES:
                if path.is_file():
                    excluded.append(f"{name}/{relative.as_posix()}")
                continue
            if path.is_file():
                key = safe_name(f"{name}/{relative.as_posix()}")
                files[key] = read_regular(path)
    return files, {
        "source": str(source.resolve()),
        "pin": "exact included file bytes via SHA-256 bundle identity; upstream commit unknown",
        "profile": "installed Codex-oriented Dovetail runtime subset v1",
        "included_directories": sorted(SOURCE_DIRS),
        "included_root_files": sorted(SOURCE_FILES),
        "excluded": excluded,
        "implicit_exclusions": ["dotfiles/directories", "__pycache__", "empty directories"],
        "script_modes": "normalized non-executable; invoke with the declared interpreter",
        "modifications": "none to included file bytes",
    }


def prepare_native(study_path: Path, root: Path, source: Path | None, image: str) -> Path:
    version = parse_json(read_regular(study_path)).get("schema_version")
    if version == 2:
        from .native_runner import prepare_native_v2

        if source is not None:
            raise ValueError("native v2 uses pinned study sources; omit --dovetail-dir")
        return prepare_native_v2(study_path, root, image)
    if version != 1:
        raise ValueError("unsupported native study schema_version")
    if source is None:
        raise ValueError("native v1 requires --dovetail-dir")
    root = external_root(root)
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ValueError("pin the native runtime by its local Docker image SHA-256 identity")
    subprocess.run(["docker", "image", "inspect", image], capture_output=True, check=True)
    study = NativeStudy.model_validate(parse_json(read_regular(study_path)))
    conditions = [prepare_condition(c, study_path.resolve().parent) for c in study.conditions]
    source_files, provenance = snapshot_source(source, study.source_skills)
    root.mkdir(parents=True, exist_ok=False)
    store = EvidenceStore(root)
    config = (RUNTIME / "config.toml").read_text(encoding="utf-8")
    config = re.sub(r"^model = .*$", f'model = "{study.model}"', config, flags=re.M)
    config = re.sub(
        r"^model_reasoning_effort = .*$",
        f'model_reasoning_effort = "{study.reasoning_effort}"',
        config,
        flags=re.M,
    )
    frozen_conditions = []
    for condition, (materials, prepared_provenance, original) in zip(
        study.conditions, conditions, strict=True
    ):
        frozen_conditions.append(
            {
                "id": condition.id,
                "materials_id": store.put_json(materials.model_dump(mode="json"), "materials.json"),
                "original_id": store.put({"original.json": original}),
                "provenance": prepared_provenance,
            }
        )
    frozen = {
        "schema_version": 1,
        "study": study.model_dump(mode="json"),
        "request_id": store.put({"original.json": read_regular(study_path)}),
        "conditions": frozen_conditions,
        "source_id": store.put(source_files),
        "source_provenance": provenance,
        "procedure_id": store.put(procedure_files()),
        "runtime_files_id": store.put(
            {p.name: read_regular(p) for p in sorted(RUNTIME.iterdir()) if p.is_file()}
        ),
        "config_id": store.put({"config.toml": config.encode()}),
        "runtime": {"image": image, "codex": "0.153.4", **runtime_versions()},
        "scorer": scorer_identity()[0],
        "design": {
            "arms": ["without-dovetail", "with-dovetail"],
            "builds_per_arm_condition": 1,
            "consumers_per_package": "one fresh native process/container per held-out case",
            "treatment": "native installed runtime subset plus explicit "
            "better-skill-creator invocation at build time",
            "baseline": "Codex's pinned built-in skills; no external skills",
            "consumer_context": "frozen generated account-totals package and current rows only",
            "retries": 0,
            "internal_evaluation": "native subagents allowed within the same "
            "trial boundary and wall time",
            "limitations": [
                "Synthetic smoke test; one build per arm/condition cannot estimate "
                "a population effect.",
                "Prepared cases are deterministic generated fixtures, "
                "not model-prepared user workloads.",
                "External nested model CLIs and downloads cannot run "
                "through the command network boundary.",
                "Provider model alias is recorded, not an immutable model-weight snapshot.",
                "No dollar-cost or token-budget enforcement; "
                "enforce wall time and collect native usage.",
            ],
        },
    }
    frozen = {"id": identity(frozen), **frozen}
    write_new(root / "study.json", canonical(frozen))
    builds, consumers = [], []
    for condition, (materials, _, _) in zip(study.conditions, conditions, strict=True):
        for arm in frozen["design"]["arms"]:
            build = f"{condition.id}-{arm}-build"
            builds.append(
                {
                    "id": build,
                    "role": "build",
                    "condition": condition.id,
                    "arm": arm,
                    "parent": None,
                    "case": None,
                }
            )
            for case in materials.evaluation:
                consumers.append(
                    {
                        "id": f"{condition.id}-{arm}-{case.id}",
                        "role": "consume",
                        "condition": condition.id,
                        "arm": arm,
                        "parent": build,
                        "case": case.id,
                    }
                )
    rng = random.Random(study.schedule_seed)
    rng.shuffle(builds)
    rng.shuffle(consumers)
    plan = {
        "study_id": frozen["id"],
        "trials": builds + consumers,
        "max_native_attempts": len(builds) + len(consumers),
    }
    write_new(root / "plan.json", canonical({"id": identity(plan), **plan}))
    body = {"files": inventory(root)}
    write_new(root / "freeze-seal.json", canonical({"id": identity(body), **body}))
    return root


def build_input(materials: Materials) -> bytes:
    return canonical(
        {
            "brief": materials.brief,
            "contract": CONTRACT,
            "development": [c.model_dump(mode="json") for c in materials.development],
        }
    )


BUILD_PROMPT = (
    "Create a reusable native Codex skill named account-totals for the exact task in "
    "/work/input/brief.json. Write the complete package to /work/output/account-totals/ "
    "with SKILL.md at its root; you may include scripts, resources and agents/openai.yaml. "
    "The finished skill must work when installed elsewhere with no build-workspace dependencies. "
    "Use only the supplied brief and development examples, plus checks you devise. "
    "This is a small bounded one-shot fixture: "
    "produce one finished package without asking questions. "
    "Native subagents are allowed within this trial's shared filesystem and time budget. "
    "Python 3, PyYAML and Node are installed; shell network is disabled. "
    "Write any build notes outside the package, under /work/output/."
)
CONSUMER_PROMPT = (
    "Use $account-totals to process the rows in /work/input/case.json. "
    "Write the result JSON required by that skill to /work/output/result.json. "
    "Complete the work without asking questions. Python 3 and Node are available."
)


def native_package(
    exported: dict[str, bytes],
    store: EvidenceStore,
    output_id: str,
    *,
    package_name: str = "account-totals",
    package_path: str = "output/account-totals",
) -> str:
    prefix = safe_name(package_path) + "/"
    files = {
        name.removeprefix(prefix): data
        for name, data in exported.items()
        if name.startswith(prefix)
    }
    if "SKILL.md" not in files or len(files) > 100 or sum(map(len, files.values())) > 5_000_000:
        raise ValueError(f"missing or oversized {package_name} package")
    text = files["SKILL.md"].decode("utf-8")
    frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, flags=re.S)
    if frontmatter is None:
        raise ValueError("native skill needs YAML frontmatter")
    try:
        metadata = yaml.safe_load(frontmatter[1])
    except yaml.YAMLError as error:
        raise ValueError("invalid native frontmatter") from error
    if not isinstance(metadata, dict) or metadata.get("name") != package_name:
        raise ValueError(f"native skill name must be {package_name}")
    if not isinstance(metadata.get("description"), str) or not metadata["description"].strip():
        raise ValueError("native skill needs YAML frontmatter and a description")
    manifest = parse_json(read_regular(store.root / "artifacts" / output_id / "manifest.json"))
    modes = [
        x["path"].removeprefix(prefix)
        for x in manifest["files"]
        if x["executable"] and x["path"].startswith(prefix)
    ]
    return store.put(files, executable=modes)


@managed("native")
def execute_native_study(root: Path, auth_path: Path) -> Path:
    version = parse_json(read_regular(root / "study.json")).get("schema_version")
    if version == 2:
        from .native_runner import execute_native_v2

        return execute_native_v2(root, auth_path)
    if version != 1:
        raise ValueError("unsupported native evidence schema_version")
    verify_execution_freeze(root)
    frozen = parse_json(read_regular(root / "study.json"))
    plan = parse_json(read_regular(root / "plan.json"))
    store = EvidenceStore(root)
    if store.get(frozen["procedure_id"]) != procedure_files():
        raise ValueError("implementation changed after freeze")
    runtime_files = {p.name: read_regular(p) for p in sorted(RUNTIME.iterdir()) if p.is_file()}
    if store.get(frozen["runtime_files_id"]) != runtime_files:
        raise ValueError("runtime files changed after freeze")
    study = NativeStudy.model_validate(frozen["study"])
    materials = {
        c["id"]: Materials.model_validate(store.json(c["materials_id"], "materials.json"))
        for c in frozen["conditions"]
    }
    start_control()
    results = {}
    for trial in plan["trials"]:
        print(f"Running {trial['id']}", flush=True)
        material = materials[trial["condition"]]
        modes = ()
        parent = results.get(trial["parent"])
        if parent and parent["status"] != "package_ready":
            missing = parent["status"] in {"harness_failure", "cli_failure", "dependency_missing"}
            results[trial["id"]] = {
                "status": "dependency_missing" if missing else "dependency_failed",
                "parent": trial["parent"],
                "reason": parent["status"],
            }
            continue
        if trial["role"] == "build":
            files = {"input/brief.json": build_input(material)}
            prompt = BUILD_PROMPT
            if trial["arm"] == "with-dovetail":
                prompt = (
                    "Use $better-skill-creator and its applicable Dovetail dependencies.\n\n"
                    + prompt
                )
                files.update(
                    {".agents/skills/" + n: b for n, b in store.get(frozen["source_id"]).items()}
                )
            timeout = study.build_timeout_seconds
        else:
            case = next(c for c in material.evaluation if c.id == trial["case"])
            files = {"input/case.json": canonical({"rows": [r.model_dump() for r in case.rows]})}
            files.update(
                {
                    ".agents/skills/account-totals/" + n: b
                    for n, b in store.get(parent["package_id"]).items()
                }
            )
            manifest = parse_json(
                read_regular(root / "artifacts" / parent["package_id"] / "manifest.json")
            )
            modes = tuple(
                ".agents/skills/account-totals/" + x["path"]
                for x in manifest["files"]
                if x["executable"]
            )
            prompt = CONSUMER_PROMPT
            timeout = study.consumer_timeout_seconds
        result = native_call(
            execute_native,
            root,
            trial["id"],
            prompt,
            files,
            role=trial["role"],
            image=frozen["runtime"]["image"],
            auth_path=auth_path,
            config=store.get(frozen["config_id"])["config.toml"],
            timeout=timeout,
            executable=modes,
        )
        result["common_sha256"] = digest(
            build_input(material) if trial["role"] == "build" else files["input/case.json"]
        )
        if (
            trial["role"] == "build"
            and result.get("output_id")
            and result["status"] in {"completed", "budget_exhausted"}
        ):
            try:
                if result["rejected_paths"]:
                    raise ValueError("export contained non-regular or oversized paths")
                result["package_id"] = native_package(
                    store.get(result["output_id"]), store, result["output_id"]
                )
                result["status"] = "package_ready"
            except ValueError as error:
                result.update(status="build_failed", reason=str(error))
        results[trial["id"]] = result
        print(f"Finished {trial['id']}: {result['status']}", flush=True)
    same_or_new(root / "results.json", canonical({"trials": results}))
    seal_run(root)
    return rescore_native(root, "original")


def native_usage(files: dict[str, bytes]) -> dict:
    sessions = []
    calls = {}
    tool_calls = 0
    for name, data in files.items():
        if not name.startswith("sessions/"):
            continue
        usage = None
        for line in data.decode("utf-8").splitlines():
            row = json.loads(line)
            payload = row.get("payload", {})
            if row["type"] == "event_msg" and payload.get("type") == "token_count":
                info = payload.get("info")
                if info:
                    usage = info["total_token_usage"]
            if row["type"] == "token_usage_record":
                calls[payload["response_id"]] = payload["usage"]
            if row["type"] == "response_item" and payload.get("type") in {
                "function_call",
                "custom_tool_call",
            }:
                tool_calls += 1
        sessions.append({"path": name, "usage": usage})
    known = list(calls.values())
    totals = {key: sum(s.get(key, 0) for s in known) for key in {k for s in known for k in s}}
    return {
        "sessions": sessions,
        "totals": totals,
        "native_usage_records": len(calls),
        "tool_calls": tool_calls,
        "cost_usd": None,
        "accounting": "sum of native token_usage_record usage, deduplicated by response_id; "
        "cache tokens included in input tokens",
    }


def rescore_native(root: Path, label: str, reason: str | None = None) -> Path:
    version = parse_json(read_regular(root / "study.json")).get("schema_version")
    if version == 2:
        from .native_runner import rescore_native_v2

        return rescore_native_v2(root, label, reason)
    if version != 1:
        raise ValueError("unsupported native evidence schema_version")
    safe_name(label)
    if "/" in label:
        raise ValueError("interpretation label must be one path component")
    seal = verify_run(root)
    frozen = parse_json(read_regular(root / "study.json"))
    plan = parse_json(read_regular(root / "plan.json"))
    results = parse_json(read_regular(root / "results.json"))["trials"]
    store = EvidenceStore(root)
    scorer, scorer_files = scorer_identity()
    if scorer != frozen["scorer"] and not reason:
        raise ValueError("scorer changed; record --reason for a new interpretation")
    materials = {
        c["id"]: Materials.model_validate(store.json(c["materials_id"], "materials.json"))
        for c in frozen["conditions"]
    }
    scores = []
    usage = {}
    for trial in plan["trials"]:
        result = results[trial["id"]]
        files = recorded_native_files(store, result)
        if files:
            try:
                usage[trial["id"]] = native_usage(files)
            except (ValueError, UnicodeError, KeyError, TypeError) as error:
                usage[trial["id"]] = {"unavailable": str(error)}
        if trial["role"] == "build":
            continue
        case = next(c for c in materials[trial["condition"]].evaluation if c.id == trial["case"])
        if result["status"] in {"harness_failure", "cli_failure", "dependency_missing"}:
            verdict = {
                "value": None,
                "reason": result.get("error") or result["status"],
                "components": {},
            }
        else:
            verdict = check_work(
                files.get("output/result.json", b""), [t.model_dump() for t in case.expected]
            )
        scores.append(
            {**trial, "status": result["status"], "output_id": result.get("output_id"), **verdict}
        )
    record = {
        "run_seal": seal,
        "study_id": frozen["id"],
        "scorer": scorer,
        "revision_reason": reason,
        "scores": scores,
    }
    destination = root / "interpretations" / label
    destination.mkdir(parents=True, exist_ok=False)
    write_new(destination / "scores.json", canonical(record))
    write_new(destination / "usage.json", canonical(usage))
    for name, data in scorer_files.items():
        write_new(destination / "scorer" / name, data)
    lines = [
        "# Native Codex with and without Dovetail: fixture result",
        "",
        frozen["study"]["question"],
        "",
        f"Model: `{frozen['study']['model']}`; "
        f"reasoning `{frozen['study']['reasoning_effort']}`; "
        f"native CLI `{frozen['runtime']['codex']}`; "
        f"Inspect `{frozen['runtime']['inspect_ai']}`. "
        "Real saved-auth Codex calls, not simulated subject output.",
        "",
        "One build per arm and condition. Consumers receive only the generated package "
        "and current case. Built-in Codex skills are present in both arms.",
        "",
        "| Condition | Builder arm | Passed | Scored | Missing |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for condition in frozen["conditions"]:
        for arm in frozen["design"]["arms"]:
            selected = [s for s in scores if s["condition"] == condition["id"] and s["arm"] == arm]
            values = [s["value"] for s in selected if s["value"] is not None]
            lines.append(
                f"| {condition['id']} | {arm} | {sum(values)} | {len(values)} | "
                f"{len(selected) - len(values)} |"
            )
    lines += [
        "",
        "## Build and resource evidence",
        "",
        "| Attempt | Result | Native status | Seconds | Input tokens | Output tokens | Sessions |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for trial in plan["trials"]:
        result = results[trial["id"]]
        u = usage.get(trial["id"], {})
        total = u.get("totals", {})
        attempt_path = result_path(
            root, trial["id"], root / "attempts" / trial["id"] / "result.json"
        )
        native_status = (
            selected_result(root, trial["id"], attempt_path)["status"]
            if attempt_path.is_file()
            else "not launched"
        )
        seconds = result.get("duration_seconds")
        duration = f"{seconds:.1f}" if seconds is not None else "unavailable"
        lines.append(
            f"| {trial['id']} | {result['status']} | {native_status} | "
            f"{duration} | "
            f"{total.get('input_tokens', 'unavailable')} | "
            f"{total.get('output_tokens', 'unavailable')} | {len(u.get('sessions', []))} |"
        )
    lines += [
        "",
        "Input tokens include cached input. Usage sums native response records "
        "deduplicated by response ID; dollar cost is unavailable. "
        "Native Codex owns inference; Inspect owns each fresh sandbox/sample and records "
        "the result. Inspect's inert model makes zero subject calls.",
        "A package can be accepted after a build reaches its deadline. The native status "
        "above preserves that exhaustion separately from package readiness. "
        "Interrupted provider calls may consume tokens not returned in native records.",
        "",
        "## Interpretation limits",
        "",
    ]
    lines += [f"- {s}" for s in frozen["design"]["limitations"]]
    lines += [
        "- Equal success on these small cases does not establish equal skill quality "
        "or no Dovetail effect.",
        "",
        "## Preserved evidence",
        "",
        f"Run seal: `{seal}`.",
        "",
        "- [Frozen study and source provenance](../../study.json)",
        "- [Frozen execution plan](../../plan.json)",
        "- [Trial/package lineage](../../results.json)",
        "- [Deterministic scores](scores.json)",
        "- [Native usage](usage.json)",
        "",
    ]
    for trial in plan["trials"]:
        result = results[trial["id"]]
        if result.get("inspect_log"):
            lines.append(f"- [{trial['id']} Inspect log](../../{result['inspect_log']})")
        if result.get("package_id"):
            lines.append(
                f"- [{trial['id']} package](../../artifacts/{result['package_id']}/files/SKILL.md)"
            )
    report = destination / "report.md"
    lines.append(control_link(root))
    write_new(report, ("\n".join(lines) + "\n").encode())
    return report
