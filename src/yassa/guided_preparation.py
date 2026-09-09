"""Immutable preparation rounds converging on the native v2 runner's contracts."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictInt, model_validator

from .app import external_root
from .evidence import inventory, read_regular, safe_name, write_new
from .native_contracts import (
    Admission,
    ConsumerBaseline,
    FileBinding,
    FileMaterials,
    NativeArm,
    NativeStudyV2,
    ReuseScenarios,
    SourceBinding,
    Text,
    make_native_plan,
    resolve_sources,
    validate_materials,
)
from .preparation_evidence import PreparationManifest, load_preparation, study_identity
from .preparation_templates import (
    FEATURES,
    generate_suite,
    task_contract,
    template_description,
    template_version,
    verify_checker,
)
from .records import canonical, digest, parse_json
from .study import Hash, Record, Slug


class SuppliedMaterials(Record):
    id: Slug
    source: FileBinding


class StudyDraft(Record):
    schema_version: Literal[1] = 1
    id: Slug = "guided-study"
    request: Text
    intended_use: Text | None = None
    family: Literal["account-totals-v1", "reconciliation-v1", "reconciliation-v2"] | None = None
    scope: Literal["synthetic-fixture", "user-defined"] | None = None
    accepted_contract_sha256: Hash | None = None
    facts: tuple[Text, ...] = ()
    inferences: tuple[Text, ...] = ()
    assumptions: tuple[Text, ...] = ()
    proposals: tuple[Text, ...] = ()
    unresolved: tuple[Text, ...] = ()
    evidence: Literal["descriptive", "broader-comparison"] = "descriptive"
    first_dovetail_study: StrictBool = False
    routes: tuple[Literal["user-supplied", "yassa-prepared"], ...] = ("yassa-prepared",)
    supplied: tuple[SuppliedMaterials, ...] = ()
    features: tuple[str, ...] | None = None
    material_recipe: Literal["reconciliation-reuse-suite-v1"] | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    historical_materials: tuple[FileBinding, ...] = Field(default=(), exclude_if=lambda v: not v)
    seed: StrictInt | None = None
    sources: tuple[SourceBinding, ...] = ()
    arms: tuple[NativeArm, ...] = ()
    control_rationale: dict[Slug, Text] = Field(default_factory=dict)
    consumer_baseline: ConsumerBaseline | None = None
    model: str | None = None
    reasoning_effort: Literal["low", "medium", "high", "xhigh"] | None = None
    consumer_repeats: Annotated[StrictInt, Field(ge=1, le=20)] | None = None
    schedule_seed: StrictInt | None = None
    scheduling: Literal["case-repeat-blocks-v1"] | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    resource_scenarios: ReuseScenarios | None = Field(default=None, exclude_if=lambda v: v is None)
    admission: Admission | None = None

    @model_validator(mode="after")
    def distinct(self):
        if self.material_recipe and (
            self.family != "reconciliation-v2"
            or self.routes != ("yassa-prepared",)
            or self.features is not None
        ):
            raise ValueError(
                "reuse recipe requires only prepared reconciliation-v2 and all six cases"
            )
        if self.historical_materials and not self.material_recipe:
            raise ValueError("historical material checks require a versioned recipe")
        if not self.routes or len(set(self.routes)) != len(self.routes):
            raise ValueError("choose distinct preparation routes")
        if len({s.id for s in self.supplied}) != len(self.supplied):
            raise ValueError("duplicate supplied condition ID")
        if any(s.id == "prepared" for s in self.supplied):
            raise ValueError("prepared is reserved for the generated condition")
        if self.supplied and "user-supplied" not in self.routes:
            raise ValueError("supplied originals require the user-supplied route")
        if self.features is not None and self.family is not None:
            if (
                not self.features
                or len(set(self.features)) != len(self.features)
                or not set(self.features) <= set(FEATURES[self.family])
            ):
                raise ValueError("features must be distinct members of the selected template")
        return self


def readiness(draft: StudyDraft) -> list[dict]:
    missing = []

    def need(field, prompt):
        missing.append({"field": field, "prompt": prompt})

    if draft.material_recipe and not draft.historical_materials:
        need(
            "historical_materials", "Pin historical material bundles for semantic duplicate checks."
        )

    if not draft.intended_use:
        need("intended_use", "What decision should this result inform, and whose work matters?")
    if draft.family is None:
        need(
            "family",
            "Which task fits: account totals, simple reconciliation, or event reconciliation?",
        )
    if draft.scope is None:
        need("scope", "Should this describe invented scenarios or supplied real-work materials?")
    if (
        draft.family
        and draft.accepted_contract_sha256 != template_description(draft.family)["contract_sha256"]
    ):
        need(
            "accepted_contract_sha256",
            "Do the displayed rules define correctness for this trial? "
            "Record their hash only after resolving any conflict with your requirements.",
        )
    if draft.unresolved or draft.proposals:
        need(
            "unresolved/proposals",
            "Resolve the listed correctness choices and proposals, "
            "or revise the scope to explicitly synthetic work.",
        )
    if draft.evidence != "descriptive":
        need(
            "evidence",
            "This implementation supports descriptive trials. Define a separately "
            "identified descriptive pilot, or use a broader study design outside this preparer.",
        )
    if draft.first_dovetail_study and set(draft.routes) != {"user-supplied", "yassa-prepared"}:
        need("routes", "The first Dovetail study requires both supplied and prepared conditions.")
    if "user-supplied" in draft.routes and not draft.supplied:
        need(
            "supplied", "Identify and pin the original supplied file materials for this condition."
        )
    if "yassa-prepared" in draft.routes and draft.seed is None:
        need("seed", "Choose a seed for reproducible synthetic case construction.")
    controls = {a.id for a in draft.arms}
    if draft.consumer_baseline:
        controls.add(draft.consumer_baseline.id)
    if not draft.arms or set(draft.control_rationale) != controls:
        need(
            "arms/control_rationale",
            "Choose the builder arms, independent builds per arm, and "
            "what each control or treatment, including any consumer baseline, lets you "
            "interpret. External packs need file pins.",
        )
    if not draft.model or draft.reasoning_effort is None:
        need("model/reasoning_effort", "Choose the native subject model and reasoning effort.")
    if draft.admission is None or draft.consumer_repeats is None or draft.schedule_seed is None:
        need(
            "admission/consumer_repeats/schedule_seed",
            "Set attempt and scheduled-time caps, "
            "build/use deadlines, consumer repeats and an ordering seed; review the plan.",
        )
    return missing


def _paths(value: dict, base: Path) -> dict:
    """Resolve only newly supplied paths relative to that round's input file."""
    for key, schema in (
        ("supplied", SuppliedMaterials),
        ("sources", SourceBinding),
        ("historical_materials", FileBinding),
    ):
        if key in value:
            if type(value[key]) is not list:
                raise ValueError(f"{key} must be an array")
            value[key] = [
                schema.model_validate(item).model_dump(mode="json") for item in value[key]
            ]
    for item in value.get("supplied", []):
        path = Path(item["source"]["path"])
        item["source"]["path"] = str(path if path.is_absolute() else base / path)
    for item in value.get("sources", []):
        path = Path(item["path"])
        item["path"] = str(path if path.is_absolute() else base / path)
    for item in value.get("historical_materials", []):
        path = Path(item["path"])
        item["path"] = str(path if path.is_absolute() else base / path)
    return value


def _read_draft(root: Path) -> tuple[dict, dict[str, bytes]]:
    seal = parse_json(read_regular(root / "draft-seal.json"))
    actual = [item for item in inventory(root) if item["path"] != "draft-seal.json"]
    if seal != {"schema_version": 1, "files": actual}:
        raise ValueError("draft changed or incomplete; preserve it and start a new draft")
    state = parse_json(read_regular(root / "draft.json"))
    history = {
        item["path"]: read_regular(root / item["path"])
        for item in actual
        if item["path"].startswith("history/")
    }
    return state, history


def _review(draft, missing, template, materials, plan, validation) -> bytes:
    lines = [
        "# Study preparation review",
        "",
        f"Status: **{'needs input' if missing else 'ready for native freeze'}**.",
        "",
        draft.request,
        "",
        f"Intended use: {draft.intended_use or 'unresolved'}",
        "",
        "Free-text facts are retained as preparation evidence. They are not automatically "
        "translated into task semantics; the displayed contract must resolve correctness.",
    ]
    if missing:
        lines += ["", "## Next questions", ""]
        lines += [f"- `{q['field']}`: {q['prompt']}" for q in missing[:2]]
        lines += ["", "Remaining readiness fields: " + ", ".join(q["field"] for q in missing) + "."]
    for label in ("facts", "inferences", "assumptions", "proposals", "unresolved"):
        lines += ["", "## " + label.capitalize(), ""]
        lines += [f"- {s}" for s in getattr(draft, label)] or ["None recorded."]
    lines += ["", "## Task and scope", "", f"Scope: {draft.scope or 'unresolved'}."]
    if template:
        lines += [
            "",
            template["requirements"],
            "",
            f"Contract choice: `{template['contract_sha256']}`.",
            "",
            "Synthetic features: " + ", ".join(draft.features or template["features"]) + "."
            if "yassa-prepared" in draft.routes
            else "No synthetic generation selected.",
        ]
    else:
        for family in FEATURES:
            description = template_description(family)
            lines += [
                "",
                f"### {family}",
                "",
                description["requirements"],
                "",
                f"Contract choice: `{description['contract_sha256']}`.",
            ]
    lines += [
        "",
        "## Controls and resources",
        "",
        f"Model: {draft.model or 'unresolved'}; "
        f"reasoning: {draft.reasoning_effort or 'unresolved'}.",
        "",
    ]
    lines += [
        f"- {a.id}: {a.builds} independent build(s) per condition. "
        f"{draft.control_rationale.get(a.id, 'Rationale unresolved.')} "
        f"Sources: {', '.join(a.sources) or 'none'}; "
        f"invocation: {a.invocation or '(common request)'}"
        for a in draft.arms
    ]
    if draft.consumer_baseline:
        baseline = draft.consumer_baseline
        lines += [
            f"- {baseline.id}: {baseline.repeats} fresh execution(s) per case, no build or "
            "generated package. "
            + draft.control_rationale.get(baseline.id, "Rationale unresolved."),
            "",
            "Every consumer receives the same complete task requirements and current input "
            "files. Package consumers additionally receive and explicitly invoke their "
            "assigned package. Built-in skills remain present in all sessions.",
        ]
    if plan:
        lines += [
            "",
            f"Reserves {plan['reserved_attempts']} attempts and "
            f"{plan['reserved_native_seconds']} native command seconds; "
            f"{draft.consumer_repeats} consumer repeat(s) per case/package.",
        ]
    if draft.admission:
        lines += [
            "",
            "Selected limits: " + canonical(draft.admission.model_dump()).decode().strip(),
        ]
    lines += ["", "## Materials and checking", ""]
    for condition, material in materials.items():
        lines += [
            f"- {condition}: development examples: {len(material.development)}; "
            f"held-out cases: {len(material.evaluation)}. Authorship: {material.authorship}. "
            f"Synthetic: {material.synthetic}. [Materials](materials/{condition}.json)."
        ]
        lines += [f"  Assumption: {s}" for s in material.assumptions]
    if validation:
        lines += [
            "",
            "All references were independently recomputed; split checks and checker "
            "acceptance/rejection probes passed. [Verification record](validation.json).",
        ]
    lines += [
        "",
        "## Interpretation and limits",
        "",
        "The routine starting choices are a descriptive trial, Yassa-prepared inputs and "
        "all listed template features unless explicitly changed. No build counts, model or "
        "deadlines are inferred from earlier experiments. Synthetic scenarios describe only "
        "constructed work; scenario groups do not establish independent briefs or domains. "
        "Repeated package uses are not independent builder observations. Both preparation "
        "routes remain separate conditions when selected.",
        "",
        "Native deadlines exclude sandbox setup and export. Hard token/spend caps and dollar "
        "estimates are unavailable. This preparation makes no model calls and launches no "
        "subjects. The existing native commands freeze and execute the reviewed study.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def prepare_draft(input_path: Path, destination: Path, previous: Path | None = None) -> Path:
    """Create a new immutable round. A complete request needs no additional interview."""
    initial = parse_json(read_regular(input_path))
    prior = _read_draft(previous)[0] if previous else {}
    if (type(initial) is dict and initial.get("schema_version") == 2) or prior.get(
        "preparation_kind"
    ) == "general":
        from .general_preparation import prepare_general

        return prepare_general(input_path, destination, previous)
    destination = external_root(destination)
    raw = read_regular(input_path)
    patch = parse_json(raw)
    if type(patch) is not dict:
        raise ValueError("preparation input must be a JSON object")
    patch = _paths(patch, input_path.resolve().parent)
    if previous:
        state, files = _read_draft(previous)
        value = _paths(state["request"], previous.resolve())
        value.update(patch)  # Answers replace top-level fields; no implicit merge of decisions.
        number = state["round"] + 1
        files[f"history/{number:03d}-answers.json"] = raw
    else:
        value, files, number = patch, {"history/000-request.json": raw}, 0
    draft = StudyDraft.model_validate(value)
    missing = readiness(draft)
    template = template_description(draft.family) if draft.family else None
    task = task_contract(draft.family) if draft.family else None
    materials, validation, conditions, origins = {}, {}, [], []
    # Snapshot supplied originals even while other correctness choices remain unresolved.
    normalized = draft.model_dump(mode="json")
    historical = []
    for index, binding in enumerate(draft.historical_materials):
        original = read_regular(Path(binding.path))
        if digest(original) != binding.sha256:
            raise ValueError("historical material hash mismatch")
        historical.append(FileMaterials.model_validate(parse_json(original)))
        name = f"history/{number:03d}-historical-{index}.json"
        files[name] = original
        normalized["historical_materials"][index]["path"] = name
    for supplied, entry in zip(draft.supplied, normalized["supplied"], strict=True):
        original = read_regular(Path(supplied.source.path))
        if digest(original) != supplied.source.sha256:
            raise ValueError(f"source hash mismatch: {supplied.id}")
        name = f"history/{number:03d}-supplied-{supplied.id}.json"
        files[name] = original
        entry["source"]["path"] = name
        origins.append(
            {
                "condition": supplied.id,
                "read_from": supplied.source.path,
                "sha256": digest(original),
                "preserved_as": name,
            }
        )
        conditions.append(
            {
                "id": supplied.id,
                "route": "user-supplied",
                "source_path": name,
                "source_sha256": digest(original),
            }
        )
        if task:
            material = FileMaterials.model_validate(parse_json(original))
            validate_materials(task, material)
            materials[supplied.id] = material
    if origins:
        files[f"history/{number:03d}-sources.json"] = canonical(origins)
    study, plan = None, None
    if not missing:
        if "yassa-prepared" in draft.routes:
            if draft.material_recipe:
                from .reuse_materials import generate_reuse_suite

                material, recipe = generate_reuse_suite(task, draft.seed, historical)
                files["material-recipe.json"] = canonical(recipe)
            else:
                material = generate_suite(
                    task, draft.seed, draft.features or FEATURES[draft.family]
                )
            materials["prepared"] = material
            body = canonical(material.model_dump(mode="json"))
            conditions.append(
                {
                    "id": "prepared",
                    "route": "yassa-prepared",
                    "generator": "reviewed-files-v1",
                    "request": draft.request,
                    "seed": draft.seed,
                    "evaluation_cases": len(material.evaluation),
                    "materials": {"path": "materials/prepared.json", "sha256": digest(body)},
                }
            )
        if draft.scope == "synthetic-fixture" and any(not m.synthetic for m in materials.values()):
            raise ValueError("synthetic-fixture scope requires synthetic materials")
        study = NativeStudyV2(
            schema_version=2,
            id=draft.id,
            question=draft.request,
            scope=draft.scope,
            runtime="native-codex-cli",
            task=task,
            sources=draft.sources,
            arms=draft.arms,
            consumer_baseline=draft.consumer_baseline,
            conditions=conditions,
            model=draft.model,
            reasoning_effort=draft.reasoning_effort,
            consumer_repeats=draft.consumer_repeats,
            schedule_seed=draft.schedule_seed,
            scheduling=draft.scheduling,
            resource_scenarios=draft.resource_scenarios,
            admission=draft.admission,
        )
        resolve_sources(study, input_path.resolve().parent)
        plan = make_native_plan(study, materials, "preparation-review")
        from .native_runner import checker_identity

        checker, checker_files = checker_identity(task)
        files.update({"checker/" + name: body for name, body in checker_files.items()})
        preparer = {
            name: read_regular(Path(__file__).parent / name)
            for name in (
                "guided_preparation.py",
                "preparation_templates.py",
                "preparation_evidence.py",
                "native_contracts.py",
            )
        }
        if task.checker == "reconciliation-v2":
            preparer["reconciliation_templates.py"] = read_regular(
                Path(__file__).parent / "reconciliation_templates.py"
            )
        if draft.material_recipe:
            preparer["reuse_materials.py"] = read_regular(
                Path(__file__).parent / "reuse_materials.py"
            )
        if draft.scheduling:
            preparer["native_scheduling.py"] = read_regular(
                Path(__file__).parent / "native_scheduling.py"
            )
        files.update({"preparer/" + name: body for name, body in preparer.items()})

        validation = {
            "checker": checker,
            "generator": {
                "version": draft.material_recipe or template_version(task.checker),
                "code": {name: digest(body) for name, body in preparer.items()},
            },
            "model": None,
            "seed": draft.seed,
            "features": (draft.features or FEATURES[draft.family])
            if "yassa-prepared" in draft.routes
            else [],
            "selection": "all declared supplied cases retained; prior author selection unknown. "
            "All selected synthetic scenarios generated without observing subject outcomes.",
            "conditions": {name: verify_checker(task, m) for name, m in materials.items()},
            "plan": plan,
        }
        if draft.material_recipe:
            validation["recipe"] = parse_json(files["material-recipe.json"])
    for name, material in materials.items():
        files[f"materials/{name}.json"] = canonical(material.model_dump(mode="json"))
    status = "needs_input" if missing else "ready_for_freeze"
    files["draft.json"] = canonical(
        {
            "schema_version": 1,
            "round": number,
            "request": normalized,
            "status": status,
            "questions": missing[:2],
            "remaining_fields": [q["field"] for q in missing],
        }
    )
    files[f"history/{number:03d}-state.json"] = files["draft.json"]
    files["review.md"] = _review(draft, missing, template, materials, plan, validation)
    files["review.md"] += (
        "\n## Preparation records\n\n"
        "- [Current decisions and readiness](draft.json)\n"
        + "\n".join(f"- [{name}]({name})" for name in files if name.startswith("history/"))
        + "\n"
    ).encode("utf-8")
    files["validation.json"] = canonical(validation)
    if study:
        manifest = PreparationManifest(
            schema_version=1,
            study_identity=study_identity(study),
            files={name: digest(body) for name, body in files.items()},
        )
        files["preparation.json"] = canonical(manifest.model_dump(mode="json"))
        exported = study.model_dump(mode="json")
        exported["preparation"] = {
            "path": "preparation.json",
            "sha256": digest(files["preparation.json"]),
        }
        files["study.json"] = canonical(exported)
    if len(files) > 500 or sum(map(len, files.values())) > 20_000_000:
        raise ValueError(
            "draft evidence exceeds 500 files or 20 MB; start a separately linked study"
        )
    for name in files:
        safe_name(name)
    destination.mkdir(parents=True, exist_ok=False)
    for name, body in files.items():
        write_new(destination / name, body)
    if study:
        load_preparation(NativeStudyV2.model_validate(exported), destination)
    write_new(
        destination / "draft-seal.json",
        canonical({"schema_version": 1, "files": inventory(destination)}),
    )
    return destination / "review.md"
