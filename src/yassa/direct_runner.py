"""Pinned tasks to direct native/API attempts and replayable deterministic reports."""

import re
import subprocess
from pathlib import Path

from inspect_ai.model import ChatMessageSystem, ChatMessageUser

from .app import external_root, procedure_files, runtime_versions
from .direct_contracts import DirectRequest, direct_plan
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
from .native_contracts import (
    FileMaterials,
    NativeStudyV2,
    TaskContract,
    check_task,
    prepare_files,
    resolve_sources,
)
from .native_execution import RUNTIME, execute_native
from .native_resources import usage_evidence
from .native_runner import checker_identity, common_prompt
from .preparation_evidence import load_preparation
from .records import canonical, digest, identity, parse_json
from .role_api import api_identity, call_api


def prepare_direct(path, root):
    request_raw = read_regular(path)
    request = DirectRequest.model_validate(parse_json(request_raw))
    base = path.resolve().parent
    source = Path(request.task_source.path)
    source = source if source.is_absolute() else base / source
    raw = read_regular(source)
    if digest(raw) != request.task_source.sha256:
        raise ValueError("task source pin mismatch")
    task_study = NativeStudyV2.model_validate(parse_json(raw))
    preparation = load_preparation(task_study, source.resolve().parent)
    if (
        preparation
        and parse_json(preparation["validation.json"]).get("checker")
        != checker_identity(task_study.task)[0]
    ):
        raise ValueError("checker changed since task preparation; revise the task first")
    prepared = {
        c.id: prepare_files(task_study.task, c, source.resolve().parent)
        for c in task_study.conditions
    }
    materials = {name: item[0] for name, item in prepared.items()}
    if task_study.scope == "synthetic-fixture" and any(not m.synthetic for m in materials.values()):
        raise ValueError("synthetic task scope requires synthetic materials")
    plan = direct_plan(request, materials)
    sources = resolve_sources(request, base)
    native = request.role.adapter == "native-codex-cli"
    if not native:
        for files, _ in sources.values():
            for body in files.values():
                body.decode("utf-8")
        for arm in request.arms:
            pack_bytes = sum(len(b) for sid in arm.sources for b in sources[sid][0].values())
            if (
                pack_bytes
                + max(
                    sum(len(t.encode()) for t in case.files.values())
                    for material in materials.values()
                    for case in material.evaluation
                )
                > 5_000_000
            ):
                raise ValueError("closed API input and treatment bundle exceeds 5 MB")
    if native:
        subprocess.run(
            ["docker", "image", "inspect", request.role.image], capture_output=True, check=True
        )
    root = external_root(root)
    root.mkdir(parents=True, exist_ok=False)
    store = EvidenceStore(root)
    body = {
        "schema_version": 1,
        "run_kind": "direct-study-v1",
        "request": request.model_dump(mode="json"),
        "request_id": store.put({"request.json": request_raw}),
        "task_source_id": store.put({"study.json": raw}),
        "task": task_study.task.model_dump(mode="json"),
        "scope": task_study.scope,
        "procedure_id": store.put(procedure_files()),
        "runtime": runtime_versions(),
        "scorer": checker_identity(task_study.task)[0],
        "conditions": [
            {
                "id": name,
                "materials_id": store.put_json(material.model_dump(mode="json"), "materials.json"),
                "original_id": store.put({"original.json": original}),
                "provenance": provenance,
            }
            for name, (material, provenance, original) in prepared.items()
        ],
        "sources": {
            s.id: store.put(sources[s.id][0], executable=s.executable) for s in request.sources
        },
        "subject_identity": {"provider": "openai", "family": "gpt", "model": request.role.model}
        if native
        else api_identity(request.role.model),
        "boundaries": (
            "fresh Inspect Docker/Codex attempt; existing native permission probes "
            "and catalog acceptance"
        )
        if native
        else (
            "fresh Inspect API sample; declared messages only, no tools, filesystem, "
            "network tool or native skill discovery"
        ),
        "limits": {
            "hard_input_token_cap": None,
            "hard_spend_cap": None,
            "hard_output_token_cap": None if native else request.role.max_output_tokens,
            "setup_export_included": False,
            "automatic_retries": 0,
        },
    }
    if preparation:
        body["preparation_id"] = store.put(preparation)
    if native:
        config = read_regular(RUNTIME / "config.toml").decode()
        config = re.sub(r"^model = .*$", f'model = "{request.role.model}"', config, flags=re.M)
        config = re.sub(
            r"^model_reasoning_effort = .*$",
            f'model_reasoning_effort = "{request.role.reasoning_effort}"',
            config,
            flags=re.M,
        )
        body["config_id"] = store.put({"config.toml": config.encode()})
        body["runtime_files_id"] = store.put(
            {p.name: read_regular(p) for p in sorted(RUNTIME.iterdir()) if p.is_file()}
        )
    write_new(root / "study.json", canonical({"id": identity(body), **body}))
    write_new(root / "plan.json", canonical(plan))
    write_new(
        root / "review.md",
        (
            f"# Direct study review\n\n{request.question}\n\n"
            f"Host: {request.role.adapter}; model: {request.role.model}. {body['boundaries']}.\n\n"
            f"{plan['reserved_attempts']} fresh direct attempts, "
            f"{plan['reserved_seconds']} reserved seconds. "
            "No builds or generated-package parents. No automatic retries. "
            "Setup/export, input tokens and spend are not hard capped.\n\n"
            + "\n".join(f"- {a.id}: {a.rationale}" for a in request.arms)
            + "\n\nThe pinned source supplies only the task and material conditions; "
            "its builder allocation and treatments are not executed. "
            "Supplied/prepared routes, public requirements, witnesses and protected rubrics "
            "retain their source provenance.\n"
        ).encode(),
    )
    write_new(root / "freeze-seal.json", canonical({"files": inventory(root)}))
    return root / "review.md"


def load_direct(root):
    frozen = parse_json(read_regular(root / "study.json"))
    if frozen.get("run_kind") != "direct-study-v1" or identity(
        {k: v for k, v in frozen.items() if k != "id"}
    ) != frozen.get("id"):
        raise ValueError("invalid direct frozen study")
    request = DirectRequest.model_validate(frozen["request"])
    store = EvidenceStore(root)
    materials = {
        c["id"]: FileMaterials.model_validate(store.json(c["materials_id"], "materials.json"))
        for c in frozen["conditions"]
    }
    plan = parse_json(read_regular(root / "plan.json"))
    if plan != direct_plan(request, materials):
        raise ValueError("direct plan mismatch")
    return frozen, request, TaskContract.model_validate(frozen["task"]), materials, plan


def execute_direct(root, auth_path=None):
    freeze = parse_json(read_regular(root / "freeze-seal.json"))
    if [x for x in inventory(root) if x["path"] != "freeze-seal.json"] != freeze["files"]:
        raise ValueError("direct freeze changed or execution already started")
    frozen, request, task, materials, plan = load_direct(root)
    store = EvidenceStore(root)
    if (
        store.get(frozen["procedure_id"]) != procedure_files()
        or frozen["runtime"] != runtime_versions()
    ):
        raise ValueError("direct procedure or dependencies changed after freeze")
    native = request.role.adapter == "native-codex-cli"
    if native:
        if auth_path is None:
            raise ValueError("native direct execution requires --auth-file")
        if store.get(frozen["runtime_files_id"]) != {
            p.name: read_regular(p) for p in sorted(RUNTIME.iterdir()) if p.is_file()
        }:
            raise ValueError("native runtime files changed after direct freeze")
    arms = {a.id: a for a in request.arms}
    results = {}
    for trial in plan["trials"]:
        arm = arms[trial["arm"]]
        case = next(c for c in materials[trial["condition"]].evaluation if c.id == trial["case"])
        files = {n: t.encode() for n, t in case.files.items()}
        common = (
            common_prompt(task, "consume", complete_facts=True)
            if native
            else (
                task.requirements
                + "\nReturn only the required JSON output. Declared input files and text skill "
                "resources are provided as data in the user message. No tools are available."
            )
        )
        common_id = store.put({"prompt.txt": common.encode(), **files})
        prompt = arm.invocation + "\n\n" + common if arm.invocation else common
        treatment_ids, modes = [], []
        for sid in arm.sources:
            artifact = frozen["sources"][sid]
            treatment_ids.append(artifact)
            files.update({".agents/skills/" + n: body for n, body in store.get(artifact).items()})
            source = next(s for s in request.sources if s.id == sid)
            modes.extend(".agents/skills/" + n for n in source.executable)
        binding = {
            "trial": trial,
            "common_id": common_id,
            "treatment_ids": treatment_ids,
            "prompt_sha256": digest(prompt.encode()),
            "input_files": {n: digest(b) for n, b in files.items()},
        }
        write_new(root / "bindings" / (trial["id"] + ".json"), canonical(binding))
        print("Running " + trial["id"], flush=True)
        if native:
            result = execute_native(
                root,
                trial["id"],
                prompt,
                files,
                image=request.role.image,
                auth_path=auth_path,
                config=store.get(frozen["config_id"])["config.toml"],
                timeout=request.role.timeout_seconds,
                executable=tuple(modes),
            )
        else:
            result = call_api(
                root / "attempts" / trial["id"],
                request.role,
                [
                    ChatMessageSystem(content=prompt),
                    ChatMessageUser(
                        content=canonical(
                            {"files": {n: b.decode() for n, b in files.items()}}
                        ).decode()
                    ),
                ],
                trial["id"],
            )
            if result["completion"] is not None:
                result["output_id"] = store.put({task.result_path: result["completion"].encode()})
        results[trial["id"]] = {**result, "launched": True, "common_id": common_id}
        print("Finished " + trial["id"] + ": " + result["status"], flush=True)
    write_new(
        root / "results.json",
        canonical({"study_id": frozen["id"], "plan_id": plan["id"], "trials": results}),
    )
    seal_run(root)
    return rescore_direct(root, "original")


def rescore_direct(root, label, reason=None):
    safe_name(label)
    if "/" in label:
        raise ValueError("interpretation label must be one component")
    seal = verify_run(root)
    frozen, request, task, materials, plan = load_direct(root)
    record = parse_json(read_regular(root / "results.json"))
    results = record["trials"]
    if (
        record["study_id"] != frozen["id"]
        or record["plan_id"] != plan["id"]
        or set(results) != {t["id"] for t in plan["trials"]}
    ):
        raise ValueError("incomplete or mismatched direct results")
    scorer, code = checker_identity(task)
    if scorer != frozen["scorer"] and not reason:
        raise ValueError("direct scorer changed; supply --reason for the new interpretation")
    store, scores, resources = EvidenceStore(root), [], []
    for trial in plan["trials"]:
        result = results[trial["id"]]
        if result["status"] not in {
            "completed",
            "budget_exhausted",
            "cli_failure",
            "harness_failure",
            "provider_failure",
        }:
            raise ValueError("unknown direct attempt status")
        files = recorded_native_files(store, result)
        case = next(c for c in materials[trial["condition"]].evaluation if c.id == trial["case"])
        if result["status"] in {"cli_failure", "harness_failure", "provider_failure"}:
            verdict = {"value": None, "components": {}, "reason": result["status"]}
        elif result.get("rejected_paths"):
            verdict = {"value": 0, "components": {}, "reason": "rejected output paths"}
        else:
            verdict = check_task(task, files.get(task.result_path, b""), case)
        scores.append(
            {
                **trial,
                **verdict,
                "status": result["status"],
                "output_id": result.get("output_id"),
                "package_id": None,
            }
        )
        if request.role.adapter == "native-codex-cli":
            try:
                usage = usage_evidence(files)
            except ValueError as error:
                usage = {"unavailable": str(error)}
        else:
            usage = result.get("usage")
        resources.append(
            {
                "id": trial["id"],
                "role": "direct",
                "status": result["status"],
                "seconds": result.get("duration_seconds"),
                "usage": usage,
            }
        )
    summary = []
    for condition in materials:
        for arm in request.arms:
            rows = [s for s in scores if s["condition"] == condition and s["arm"] == arm.id]
            values = [s["value"] for s in rows if s["value"] is not None]
            summary.append(
                {
                    "condition": condition,
                    "arm": arm.id,
                    "passed": sum(values),
                    "scored": len(values),
                    "planned": len(rows),
                    "missing": len(rows) - len(values),
                }
            )
    destination = root / "interpretations" / label
    destination.mkdir(parents=True, exist_ok=False)
    write_new(
        destination / "scores.json",
        canonical(
            {
                "schema_version": 1,
                "run_seal": seal,
                "study_id": frozen["id"],
                "plan_id": plan["id"],
                "scorer": scorer,
                "revision_reason": reason,
                "scores": scores,
            }
        ),
    )
    write_new(destination / "analysis.json", canonical({"by_arm": summary}))
    write_new(
        destination / "resources.json",
        canonical({"limits": frozen["limits"], "attempts": resources}),
    )
    for name, body in code.items():
        write_new(destination / "scorer" / name, body)
    lines = [
        "# Direct study result",
        "",
        request.question,
        "",
        f"Host: {request.role.adapter}; model: {request.role.model}. Scope: {frozen['scope']}.",
        "",
        frozen["boundaries"] + ".",
        "",
        f"{plan['reserved_attempts']} planned direct attempts; "
        "no builds or generated-package parents. Every attempt receives the same public "
        "task facts and its current case, plus only its declared treatment. "
        "Repeated executions are not independent sampled tasks. "
        "Infrastructure failures remain missing.",
        "",
        "| Condition | Arm | Passed | Scored | Planned | Missing |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    lines += [
        f"| {s['condition']} | {s['arm']} | {s['passed']} | {s['scored']} | "
        f"{s['planned']} | {s['missing']} |"
        for s in summary
    ]
    if task.rubric:
        lines += [
            "",
            "Scores establish declared JSON predicate compliance only. " + task.rubric.limitations,
        ]
    lines += [
        "",
        "These fixed-case descriptive outcomes do not establish transfer, automatic "
        "activation, equivalence, or a general ranking. Host differences remain part of "
        "the execution conditions. Input tokens, spend and setup/export overhead are not "
        "hard capped; unavailable usage is not zero.",
        "",
        "- [Frozen study](../../study.json)",
        "- [Plan](../../plan.json)",
        "- [Scores](scores.json)",
        "- [Counts](analysis.json)",
        "- [Resource records](resources.json)",
    ]
    for trial in plan["trials"]:
        lines.append(f"- [{trial['id']} binding](../../bindings/{trial['id']}.json)")
        lines.append(f"- [{trial['id']} result](../../attempts/{trial['id']}/result.json)")
    write_new(destination / "report.md", ("\n".join(lines) + "\n").encode())
    return destination / "report.md"
