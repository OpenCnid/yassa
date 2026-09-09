"""User-described work to reviewed native studies through reusable product operations."""

from pathlib import Path

from .app import external_root, procedure_files, runtime_versions
from .evidence import inventory, read_regular, safe_name, write_new
from .general_contracts import (
    CaseBatch,
    ConditionProposal,
    ExecutionSettings,
    ExpertReview,
    GeneralRequest,
    MaterialSource,
    ReviewFindings,
    StudyProposal,
    TaskProposal,
)
from .guided_preparation import _read_draft
from .native_contracts import (
    FileBinding,
    FileMaterials,
    NativeStudyV2,
    TaskContract,
    check_task,
    make_native_plan,
    resolve_sources,
    validate_materials,
)
from .native_runner import checker_identity
from .preparation_evidence import PreparationManifest, load_preparation, study_identity
from .preparation_model import (
    CASE_INSTRUCTIONS,
    REVIEW_INSTRUCTIONS,
    TASK_INSTRUCTIONS,
    PreparationCalls,
)
from .records import canonical, digest, parse_json


def _resolve(value, base):
    if "documents" in value:
        if type(value["documents"]) is not list:
            raise ValueError("documents must be an array")
        value["documents"] = [
            MaterialSource.model_validate(d).model_dump(mode="json") for d in value["documents"]
        ]
    if value.get("execution") is not None:
        value["execution"] = ExecutionSettings.model_validate(value["execution"]).model_dump(
            mode="json"
        )
    for name in ("expert_proposal", "expert_review"):
        if value.get(name) is not None:
            value[name] = FileBinding.model_validate(value[name]).model_dump(mode="json")
    for doc in value.get("documents", []):
        path = Path(doc["file"]["path"])
        doc["file"]["path"] = str(path if path.is_absolute() else base / path)
    for name in ("expert_proposal", "expert_review"):
        if value.get(name):
            path = Path(value[name]["path"])
            value[name]["path"] = str(path if path.is_absolute() else base / path)
    for source in (value.get("execution") or {}).get("sources", []):
        path = Path(source["path"])
        source["path"] = str(path if path.is_absolute() else base / path)
    return value


def readiness(request):
    missing = []

    def need(field, prompt):
        missing.append({"field": field, "prompt": prompt})

    if request.evidence != "descriptive":
        need(
            "evidence",
            "Define a descriptive trial or wait for broader analysis support; this request "
            "cannot be silently downgraded.",
        )
    if (
        request.comparison != "builder"
        or request.activation != "explicit"
        or request.clarification != "preparation-only"
    ):
        need(
            "comparison/activation/clarification",
            "The native route currently measures builders and explicit package use, with "
            "preparation outside treatment. Revise the selected condition or retain this "
            "unsupported request.",
        )
    if request.execution is None:
        need(
            "execution",
            "Which subject model, builder variants and maximum attempts/deadlines should "
            "this trial use?",
        )
    if request.preparation is None and not (request.expert_proposal and request.expert_review):
        need(
            "preparation",
            "Choose preparation/review models and call, output-token and time limits, or "
            "supply a reviewed expert proposal.",
        )
    if "user-supplied" in request.routes and not {"development", "evaluation"} <= {
        d.split for d in request.documents
    }:
        need(
            "documents",
            "Identify supplied development and held-out materials, with source/access "
            "information; otherwise select prepared materials.",
        )
    if request.scope == "synthetic-fixture" and any(not d.synthetic for d in request.documents):
        need(
            "scope",
            "The supplied source metadata includes real material; select user-defined "
            "scope or provide synthetic sources.",
        )
    if request.preparation:
        required = (0 if request.expert_proposal else 1 + 2 * len(request.routes)) + (
            0 if request.expert_review else 1
        )
        if request.preparation.max_calls < required:
            need(
                "preparation.max_calls",
                f"A complete round reserves {required} preparation calls; raise the cap or "
                f"reduce the selected routes.",
            )
    if request.execution:
        settings = request.execution
        builds = len(request.routes) * sum(a.builds for a in settings.arms)
        uses = builds * request.evaluation_cases * settings.consumer_repeats
        if settings.consumer_baseline:
            uses += (
                len(request.routes) * request.evaluation_cases * settings.consumer_baseline.repeats
            )
        seconds = (
            builds * settings.admission.build_timeout_seconds
            + uses * settings.admission.consumer_timeout_seconds
        )
        if (
            builds + uses > settings.admission.max_attempts
            or seconds > settings.admission.max_scheduled_seconds
        ):
            need(
                "execution.admission",
                f"The selected study reserves {builds + uses} attempts "
                f"and {seconds} native seconds. Change its allocation or caps before preparation.",
            )
    return missing


def task_contract(request, proposal):
    if proposal.questions or not all(
        (proposal.intended_use, proposal.requirements, proposal.rubric, proposal.case_plan)
    ):
        raise ValueError("task proposal is incomplete or has unresolved questions")
    return TaskContract(
        schema_version=1,
        id=request.id,
        requirements=proposal.requirements,
        package_name=request.id,
        package_path="output/package",
        result_path="output/result.json",
        brief_path="input/brief.json",
        checker="json-predicates-v1",
        checker_inputs=proposal.input_paths,
        rubric=proposal.rubric,
        build_prompt="Build a reusable skill for the complete task contract in the brief.",
        consumer_prompt=proposal.requirements,
    )


def prepare_task(request, documents, calls):
    """Task synthesis cannot see supplied development or protected evaluation sources."""
    return calls.call(
        "task",
        TASK_INSTRUCTIONS,
        {
            "request": request.request,
            "intended_use": request.intended_use,
            "answers": request.answers,
            "scope": request.scope,
            "specification_sources": [d for d in documents if d["split"] == "specification"],
        },
        TaskProposal,
    )


def prepare_cases(request, task, documents, calls, route, split):
    """Each split is a fresh model context with only its own declared source inputs."""
    return calls.call(
        route + "-" + split,
        CASE_INSTRUCTIONS,
        {
            "request": request.request,
            "answers": request.answers,
            "task": task.model_dump(mode="json"),
            "route": route,
            "split": split,
            "seed": request.seed,
            "count": getattr(request, split + "_cases"),
            "sources": [
                d
                for d in documents
                if d["split"] == "specification"
                or (route == "user-supplied" and d["split"] == split)
            ],
        },
        CaseBatch,
    )


def verify_proposal(request, proposal):
    """Reusable, effect-free reference, split, provenance and checker calibration gate."""
    task = task_contract(request, proposal.task)
    if sorted(c.route for c in proposal.conditions) != sorted(request.routes):
        raise ValueError("proposal conditions differ from the selected routes")
    documents = {d.id: d for d in request.documents}
    materials, verification = {}, {}
    for condition in proposal.conditions:
        route = condition.route
        sources_used = set()
        probes = []
        for split in ("development", "evaluation"):
            batch = getattr(condition, split)
            if len(batch.cases) != getattr(request, split + "_cases"):
                raise ValueError(f"{route}/{split}: case count differs from request")
            cases = {c.id: c for c in batch.cases}
            if set(batch.origins) != set(cases):
                raise ValueError(
                    "every case needs a source lineage entry, including synthetic cases"
                )
            for case in batch.cases:
                if set(case.files) != set(task.checker_inputs):
                    raise ValueError("case files must exactly match declared JSON input paths")
                origins = batch.origins[case.id]
                if len(set(origins)) != len(origins) or not set(origins) <= documents.keys():
                    raise ValueError("unknown or duplicate case source")
                if any(documents[s].split not in {"specification", split} for s in origins):
                    raise ValueError("case source crosses a protected split")
                if route == "user-supplied" and not any(
                    documents[s].split == split for s in origins
                ):
                    raise ValueError("supplied cases must derive from supplied split material")
                if route == "yassa-prepared" and any(
                    documents[s].split != "specification" for s in origins
                ):
                    raise ValueError("prepared cases cannot reuse supplied case sources")
                sources_used.update(origins)
            passing = set()
            for probe in batch.probes:
                if probe.case_id not in cases:
                    raise ValueError("calibration probe names an unknown case")
                verdict = check_task(task, canonical(probe.output), cases[probe.case_id])
                failed = {name for name, passed in verdict["components"].items() if not passed}
                if bool(verdict["value"]) != probe.accept or failed != set(probe.fails):
                    raise ValueError(
                        f"calibration mismatch: {route}/{probe.case_id}: {probe.rationale}"
                    )
                if probe.accept:
                    passing.add(probe.case_id)
                probes.append(
                    {
                        **probe.model_dump(mode="json"),
                        "observed": verdict,
                        "output_sha256": digest(canonical(probe.output)),
                    }
                )
            if passing != cases.keys():
                raise ValueError("every case requires a legitimate passing calibration probe")
        # The witness is checked against predicates, never used as an exact answer oracle.
        material = FileMaterials(
            schema_version=2,
            task_id=task.id,
            brief=task.requirements,
            authorship=condition.authorship,
            source="Prepared/adapted sources and selection: see pinned preparation record",
            synthetic=route == "yassa-prepared"
            or all(documents[s].synthetic for s in sources_used),
            assumptions=proposal.task.assumptions,
            development=condition.development.cases,
            evaluation=condition.evaluation.cases,
        )
        validate_materials(task, material)
        killed = {name for p in probes for name in p["fails"]}
        if not {c.id for c in task.rubric.assertions} <= killed:
            raise ValueError("negative calibration must exercise every score criterion")
        materials[route] = material
        verification[route] = {
            "references": [
                {"case": c.id, "verdict": check_task(task, canonical(c.expected), c)}
                for c in material.development + material.evaluation
            ],
            "probes": probes,
            "source_ids": sorted(sources_used),
            "selection": {
                s: getattr(condition, s).selection for s in ("development", "evaluation")
            },
            "scope": "Witness feasibility under predicates; semantic coverage also "
            "requires independent review.",
        }
    return task, materials, verification


def review_proposal(request, proposal, documents, calls):
    # Exclude treatment labels and proposer commentary from the independent review.
    task = proposal.task.model_dump(mode="json", exclude={"facts", "inferences", "assumptions"})
    return calls.call(
        "review",
        REVIEW_INSTRUCTIONS,
        {
            "request": request.request,
            "intended_use": request.intended_use,
            "answers": request.answers,
            "scope": request.scope,
            "documents": documents,
            "task": task,
            "proposed_assumptions": proposal.task.assumptions,
            "conditions": [c.model_dump(mode="json") for c in proposal.conditions],
        },
        ReviewFindings,
        review=True,
    )


def _compile(request, proposal, task, materials, files):
    conditions = []
    for route, material in materials.items():
        name = "materials/" + route + ".json"
        files[name] = canonical(material.model_dump(mode="json"))
        if route == "user-supplied":
            conditions.append(
                {
                    "id": route,
                    "route": route,
                    "source_path": name,
                    "source_sha256": digest(files[name]),
                }
            )
        else:
            conditions.append(
                {
                    "id": route,
                    "route": route,
                    "generator": "reviewed-files-v1",
                    "request": request.request,
                    "seed": request.seed,
                    "evaluation_cases": len(material.evaluation),
                    "materials": {"path": name, "sha256": digest(files[name])},
                }
            )
    settings = request.execution.model_dump(mode="json", exclude={"control_rationale"})
    study = NativeStudyV2(
        schema_version=2,
        id=request.id,
        question=request.request,
        scope=request.scope,
        runtime="native-codex-cli",
        task=task,
        conditions=conditions,
        **settings,
    )
    resolve_sources(study, Path.cwd())
    plan = make_native_plan(study, materials, "preparation-review")
    return study, plan


def _review(request, proposal, questions, status, validation, files):
    lines = [
        "# General study preparation review",
        "",
        f"Status: **{status}**.",
        "",
        request.request,
        "",
        "This is a descriptive builder-to-consumer study with explicit skill use. "
        "Preparation is outside the measured treatment.",
        "",
    ]
    if questions:
        lines += ["## Next questions", ""]
        lines += [f"- {q['prompt']} (`{q['field']}`)" for q in questions[:2]]
    if proposal:
        lines += [
            "",
            "## Task and rubric",
            "",
            proposal.task.requirements or "Unresolved.",
            "",
            f"Intended use: {proposal.task.intended_use or 'unresolved'}.",
        ]
        for name in ("facts", "inferences", "assumptions"):
            lines += ["", "## " + name.capitalize(), ""]
            lines += ["- " + text for text in getattr(proposal.task, name)] or ["None recorded."]
        if proposal.task.rubric:
            lines += ["", "All score criteria must pass; component scores remain separate.", ""]
            lines += [f"- {c.id}: {c.description}" for c in proposal.task.rubric.assertions]
            lines += ["", "Limits: " + proposal.task.rubric.limitations]
    lines += ["", "## Sources and case boundaries", ""]
    lines += [
        f"- {d.id}: {d.split}; {d.origin}; version {d.version}; access: {d.access}; "
        f"license: {d.license}; authorship: {d.authorship}; synthetic: {d.synthetic}."
        for d in request.documents
    ] or ["No supplied sources. Cases are constructed scenarios."]
    lines += [
        "",
        "Task synthesis sees specification sources. Development and evaluation "
        "construction use separate contexts. Subjects receive only their assigned inputs; "
        "preparation records and protected rubric remain in controller evidence.",
        "",
        "Routine proposed settings: synthetic scope unless selected otherwise, seed "
        f"{request.seed}, {request.development_cases} development and {request.evaluation_cases} "
        "evaluation cases per route. Counts describe constructed cases, not representative "
        "sampling.",
    ]
    if request.execution:
        lines += ["", "## Controls and resources", ""]
        lines += [
            f"- {name}: {rationale}"
            for name, rationale in request.execution.control_rationale.items()
        ]
        lines += [
            "",
            f"Subject model: {request.execution.model}; effort: "
            f"{request.execution.reasoning_effort}.",
        ]
    if validation.get("plan"):
        plan = validation["plan"]
        lines += [
            "",
            f"Native reservation: {plan['reserved_attempts']} attempts; "
            f"{plan['reserved_native_seconds']} command seconds. Setup/export excluded.",
        ]
    if request.preparation:
        s = request.preparation
        lines += [
            "",
            f"Preparation cap per round: {s.max_calls} calls, "
            f"{s.max_output_tokens} output tokens and {s.timeout_seconds} seconds per call. "
            "Input tokens, provider billing and setup overhead are not capped. "
            f"Preparer: {s.model}; reviewer: {s.reviewer_model}.",
        ]
    if validation.get("review"):
        lines += ["", "## Independent preparation review", "", validation["review"]["assessment"]]
        lines += ["- " + issue for issue in validation["review"]["issues"]]
    lines += [
        "",
        "## Evidence and next operation",
        "",
        "Review the task, rubric, witnesses, calibration and source adaptations before "
        "native freeze. "
        "A new answer or correction uses study-revise and preserves this round. "
        "Ready studies use native-prepare/native-execute or native-run; verify and native-rescore "
        "operate on the recorded run. No subjects are launched by preparation.",
        "",
    ]
    lines += [f"- [{name}]({name})" for name in sorted(files) if not name.startswith("preparer/")]
    return ("\n".join(lines) + "\n").encode("utf-8")


def prepare_general(input_path: Path, destination: Path, previous: Path | None = None) -> Path:
    destination = external_root(destination)
    if destination.exists():
        raise ValueError("draft destination must be new")
    raw = read_regular(input_path)
    patch = parse_json(raw)
    if type(patch) is not dict:
        raise ValueError("preparation input must be a JSON object")
    patch = _resolve(patch, input_path.resolve().parent)
    files, number = {}, 0
    if previous:
        state, files = _read_draft(previous)
        if state.get("preparation_kind") != "general":
            raise ValueError("general revision requires a general draft")
        value = _resolve(state["request"], previous.resolve())
        value.update(patch)
        number = state["round"] + 1
        files[f"history/{number:03d}-answers.json"] = raw
    else:
        value = patch
        files["history/000-request.json"] = raw
    request = GeneralRequest.model_validate(value)
    if request.execution:
        resolve_sources(request.execution, input_path.resolve().parent)
    normalized = request.model_dump(mode="json")
    documents = []
    for index, doc in enumerate(request.documents):
        body = read_regular(Path(doc.file.path))
        if digest(body) != doc.file.sha256 or len(body) > 1_000_000:
            raise ValueError(f"document pin mismatch or exceeds 1 MB: {doc.id}")
        content = body.decode("utf-8")
        name = f"history/{number:03d}-source-{doc.id}.txt"
        files[name] = body
        normalized["documents"][index]["file"]["path"] = name
        documents.append(
            {
                **doc.model_dump(mode="json", exclude={"file"}),
                "sha256": digest(body),
                "content": content,
            }
        )
    expert = {}
    for key in ("expert_proposal", "expert_review"):
        binding = getattr(request, key)
        if binding:
            body = read_regular(Path(binding.path))
            if digest(body) != binding.sha256:
                raise ValueError(f"{key} pin mismatch")
            name = f"history/{number:03d}-{key}.json"
            files[name] = body
            normalized[key]["path"] = name
            expert[key] = body
    if len(files) > 450 or sum(map(len, files.values())) > 10_000_000:
        raise ValueError("input/history evidence exceeds 450 files or 10 MB before preparation")
    # Snapshot inputs before any effectful call, including failed attempts.
    destination.mkdir(parents=True, exist_ok=False)
    for name, body in files.items():
        write_new(destination / name, body)
    questions = readiness(request)
    proposal, study, validation = None, None, {}
    if not questions:
        calls = PreparationCalls(request.preparation, destination / f"calls/{number:03d}")
        try:
            if request.expert_proposal:
                proposal = StudyProposal.model_validate(parse_json(expert["expert_proposal"]))
            else:
                task = prepare_task(request, documents, calls)
                proposal = StudyProposal(task=task)
                if not task.questions:
                    task_contract(request, task)
                    conditions = []
                    for route in request.routes:
                        batches = {
                            split: prepare_cases(request, task, documents, calls, route, split)
                            for split in ("development", "evaluation")
                        }
                        conditions.append(
                            ConditionProposal(
                                route=route,
                                authorship="Yassa preparation via " + request.preparation.model,
                                **batches,
                            )
                        )
                    proposal = StudyProposal(task=task, conditions=conditions)
            files["proposal.json"] = canonical(proposal.model_dump(mode="json"))
            questions = [q.model_dump(mode="json") for q in proposal.task.questions]
            if not questions:
                task, materials, calibration = verify_proposal(request, proposal)
                validation["conditions"] = calibration
                if request.expert_review:
                    review = ExpertReview.model_validate(parse_json(expert["expert_review"]))
                    if review.proposal_sha256 != digest(expert["expert_proposal"]):
                        raise ValueError("expert review does not bind the supplied proposal bytes")
                else:
                    review = review_proposal(request, proposal, documents, calls)
                validation["review"] = review.model_dump(mode="json")
                questions = [{"field": "review", "prompt": issue} for issue in review.issues]
                if not questions:
                    study, plan = _compile(request, proposal, task, materials, files)
                    validation["plan"] = plan
                    checker, checker_files = checker_identity(task)
                    validation["checker"] = checker
                    files.update({"checker/" + name: body for name, body in checker_files.items()})
        except ValueError as error:
            study = None
            questions = [{"field": "preparation", "prompt": str(error)}]
            validation["failure"] = str(error)
        validation["calls_made"] = calls.count
    status = "ready_for_freeze" if study else "needs_input"
    files["draft.json"] = canonical(
        {
            "schema_version": 2,
            "preparation_kind": "general",
            "round": number,
            "request": normalized,
            "status": status,
            "questions": questions[:2],
            "remaining_fields": [q["field"] for q in questions],
        }
    )
    files[f"history/{number:03d}-state.json"] = files["draft.json"]
    validation["runtime"] = runtime_versions()
    code = procedure_files()
    validation["preparer"] = {name: digest(body) for name, body in code.items()}
    files["validation.json"] = canonical(validation)
    files.update({"preparer/" + name: body for name, body in code.items()})
    files[f"history/{number:03d}-code.json"] = canonical(
        {name: body.decode("utf-8") for name, body in code.items()}
    )
    # Record all newly written model logs and previous histories in the review manifest.
    aliases = []
    for index, item in enumerate(inventory(destination)):
        name = item["path"]
        if name.startswith("calls/"):
            # Original logs stay in the draft; portable aliases retain their exact bytes.
            name = f"history/{number:03d}-calls/{index:03d}.json"
            aliases.append(
                {"original_path": item["path"], "preserved_as": name, "sha256": item["sha256"]}
            )
        files[name] = read_regular(destination / item["path"])
    if aliases:
        files[f"history/{number:03d}-call-paths.json"] = canonical(aliases)
    files["review.md"] = _review(request, proposal, questions, status, validation, files)
    files[f"history/{number:03d}-review.txt"] = files["review.md"]
    files[f"history/{number:03d}-validation.json"] = files["validation.json"]
    if proposal:
        files[f"history/{number:03d}-proposal.json"] = files["proposal.json"]
    if len(files) > 500 or sum(map(len, files.values())) > 20_000_000:
        raise ValueError(
            "preparation evidence exceeds 500 files or 20 MB; attempts remain preserved"
        )
    for name, body in files.items():
        safe_name(name)
        if not (destination / name).exists():
            write_new(destination / name, body)
    if study:
        manifest = PreparationManifest(
            schema_version=1,
            study_identity=study_identity(study),
            files={name: digest(body) for name, body in files.items()},
        )
        body = canonical(manifest.model_dump(mode="json"))
        write_new(destination / "preparation.json", body)
        exported = study.model_dump(mode="json")
        exported["preparation"] = {"path": "preparation.json", "sha256": digest(body)}
        write_new(destination / "study.json", canonical(exported))
        load_preparation(NativeStudyV2.model_validate(exported), destination)
    write_new(
        destination / "draft-seal.json",
        canonical({"schema_version": 1, "files": inventory(destination)}),
    )
    return destination / "review.md"
