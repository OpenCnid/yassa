"""Native v2 study and UTF-8 file contracts, independent of Inspect execution."""

import csv
import io
import random
import re
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, StrictInt, model_validator

from .evidence import read_regular, safe_name
from .native_checkers import check, input_identity, oracle, reconciliation_candidate
from .prepare import generate_materials
from .records import canonical, digest, identity, parse_json
from .study import Condition, Hash, Record, Slug

Text = Annotated[str, Field(min_length=1, max_length=20_000)]
Checker = Literal["account-totals-v1", "reconciliation-v1", "json-exact-v1"]


def paths_valid(names, prefix: str) -> None:
    names = list(names)
    for name in names:
        safe_name(name)
        if not name.startswith(prefix + "/"):
            raise ValueError(f"path must be under {prefix}/")
        if name.casefold() == "input/boundary.txt" or name.casefold().startswith(
            "input/boundary.txt/"
        ):
            raise ValueError("reserved boundary probe path")
    lowered = [name.casefold() for name in names]
    if len(set(lowered)) != len(lowered):
        raise ValueError("case-colliding paths")
    if any(b.startswith(a + "/") for a in lowered for b in lowered):
        raise ValueError("file/directory path collision")


def files_valid(files: dict[str, str]) -> None:
    paths_valid(files, "input")
    if len(files) > 100 or sum(len(value.encode("utf-8")) for value in files.values()) > 5_000_000:
        raise ValueError("input file bundle exceeds 100 files or 5 MB")


class TaskContract(Record):
    schema_version: Literal[1]
    id: Slug
    requirements: Text
    package_name: Slug
    package_path: str
    result_path: str
    brief_path: str
    build_prompt: Text
    consumer_prompt: Text
    checker: Checker
    checker_inputs: tuple[str, ...]

    @model_validator(mode="after")
    def boundaries(self):
        paths_valid([self.package_path, self.result_path], "output")
        paths_valid([self.brief_path], "input")
        paths_valid(self.checker_inputs, "input")
        count = {"account-totals-v1": 1, "reconciliation-v1": 2, "json-exact-v1": 0}[self.checker]
        if len(self.checker_inputs) != count:
            raise ValueError(f"{self.checker} needs {count} checker input paths")
        if self.package_name == "boundary":
            raise ValueError("reserved native skill name")
        return self


class FileCase(Record):
    id: Slug
    group: Slug
    files: dict[str, str]
    expected: Any

    @model_validator(mode="after")
    def valid_files(self):
        if not self.files:
            raise ValueError("a case requires input files")
        files_valid(self.files)
        canonical(self.expected)
        return self


class FileMaterials(Record):
    schema_version: Literal[2]
    task_id: Slug
    brief: Text
    authorship: str
    source: str
    synthetic: bool
    assumptions: tuple[str, ...]
    builder_files: dict[str, str] = Field(default_factory=dict)
    development: Annotated[tuple[FileCase, ...], Field(min_length=1, max_length=50)]
    evaluation: Annotated[tuple[FileCase, ...], Field(min_length=1, max_length=50)]

    @model_validator(mode="after")
    def split(self):
        files_valid(self.builder_files)
        cases = self.development + self.evaluation
        if len({case.id for case in cases}) != len(cases):
            raise ValueError("case IDs must be unique across the split")
        if {case.group for case in self.development} & {case.group for case in self.evaluation}:
            raise ValueError("development and evaluation groups must be disjoint")
        if len({identity(case.files) for case in cases}) != len(cases):
            raise ValueError("duplicate case inputs across the split")
        return self


class NativeCondition(Condition):
    generator: Literal["account-totals-v1", "reconciliation-v1"] | None = None

    @model_validator(mode="after")
    def preparation(self):
        if (self.route == "yassa-prepared") != (self.generator is not None):
            raise ValueError("prepared conditions require a generator; supplied ones forbid it")
        return self


class SourceBinding(Record):
    id: Slug
    path: str
    files: Annotated[dict[str, Hash], Field(min_length=1, max_length=500)]
    executable: tuple[str, ...] = ()

    @model_validator(mode="after")
    def pinned_files(self):
        paths_valid([".agents/skills/" + n for n in self.files], ".agents/skills")
        skills = set()
        for name in self.files:
            parts = name.split("/")
            if (
                len(parts) < 2
                or parts[0] == "boundary"
                or not re.fullmatch(r"[a-z][a-z0-9-]{0,47}", parts[0])
            ):
                raise ValueError("source paths require an unreserved skill directory")
            skills.add(parts[0])
        if any(f"{skill}/SKILL.md" not in self.files for skill in skills):
            raise ValueError("each source skill needs a pinned SKILL.md")
        if (
            len(set(self.executable)) != len(self.executable)
            or not set(self.executable) <= self.files.keys()
        ):
            raise ValueError("executable source paths must be distinct declared files")
        return self


class NativeArm(Record):
    id: Slug
    sources: tuple[Slug, ...] = ()
    invocation: Annotated[str, Field(max_length=20_000)] = ""
    builds: Annotated[StrictInt, Field(ge=1, le=20)]


class Admission(Record):
    max_attempts: Annotated[StrictInt, Field(ge=1, le=2000)]
    max_scheduled_seconds: Annotated[StrictInt, Field(ge=1)]
    build_timeout_seconds: Annotated[StrictInt, Field(ge=30, le=600)]
    consumer_timeout_seconds: Annotated[StrictInt, Field(ge=30, le=300)]


class NativeStudyV2(Record):
    schema_version: Literal[2]
    id: Slug
    question: Text
    scope: Literal["synthetic-fixture", "user-defined"]
    runtime: Literal["native-codex-cli"]
    model: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_.-]+$")]
    reasoning_effort: Literal["low", "medium", "high", "xhigh"]
    task: TaskContract
    sources: tuple[SourceBinding, ...] = ()
    arms: Annotated[tuple[NativeArm, ...], Field(min_length=1, max_length=8)]
    conditions: Annotated[tuple[NativeCondition, ...], Field(min_length=1, max_length=8)]
    consumer_repeats: Annotated[StrictInt, Field(ge=1, le=20)]
    schedule_seed: StrictInt
    admission: Admission

    @model_validator(mode="after")
    def dimensions(self):
        for values in (self.sources, self.arms, self.conditions):
            if len({item.id for item in values}) != len(values):
                raise ValueError("duplicate source, arm or condition ID")
        sources = {s.id: s for s in self.sources}
        used = set()
        for arm in self.arms:
            if len(set(arm.sources)) != len(arm.sources) or not set(arm.sources) <= sources.keys():
                raise ValueError("arm sources must be distinct declared bindings")
            used.update(arm.sources)
            names = [name for sid in arm.sources for name in sources[sid].files]
            paths_valid([".agents/skills/" + name for name in names], ".agents/skills")
        if used != sources.keys():
            raise ValueError("unused source binding")
        for condition in self.conditions:
            if condition.generator and condition.generator != self.task.checker:
                raise ValueError("fixture generator must match the task checker")
        return self


def builder_files(task: TaskContract, materials: FileMaterials) -> dict[str, bytes]:
    files = {name: text.encode("utf-8") for name, text in materials.builder_files.items()}
    paths_valid([*files, task.brief_path], "input")
    files[task.brief_path] = canonical(
        {
            "brief": materials.brief,
            "contract": task.requirements,
            "development": [case.model_dump(mode="json") for case in materials.development],
        }
    )
    if len(files) > 100 or sum(map(len, files.values())) > 5_000_000:
        raise ValueError("rendered builder inputs exceed 100 files or 5 MB")
    return files


def validate_materials(task: TaskContract, materials: FileMaterials) -> None:
    if materials.task_id != task.id:
        raise ValueError("materials task ID does not match contract")
    builder_files(task, materials)
    seen = set()
    for case in materials.development + materials.evaluation:
        if not set(task.checker_inputs) <= case.files.keys():
            raise ValueError("missing checker input file")
        target = oracle(task.checker, case.files, task.checker_inputs)
        verdict = check(
            task.checker, canonical(case.expected), case.expected if target is None else target
        )
        if not verdict["value"]:
            raise ValueError(f"invalid reference for {case.id}: {verdict['reason']}")
        signature = identity(input_identity(task.checker, case.files, task.checker_inputs))
        if signature in seen:
            raise ValueError("duplicate semantic case inputs across the split")
        seen.add(signature)


def generate_files(task: TaskContract, condition: NativeCondition) -> dict:
    if condition.generator == "account-totals-v1":
        material = generate_materials(condition)
        material["schema_version"] = 2
        material["task_id"] = task.id
        for split in ("development", "evaluation"):
            material[split] = [
                {
                    "id": case["id"],
                    "group": case["group"],
                    "files": {task.checker_inputs[0]: canonical({"rows": case["rows"]}).decode()},
                    "expected": {"totals": case["expected"]},
                }
                for case in material[split]
            ]
        return material
    rng = random.Random(condition.seed)

    def case(name, group, left, right):
        def csv_text(rows):
            stream = io.StringIO(newline="")
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["id", "cents"])
            writer.writerows(rows)
            return stream.getvalue()

        return {
            "id": name,
            "group": group,
            "files": dict(zip(task.checker_inputs, (csv_text(left), csv_text(right)), strict=True)),
            "expected": reconciliation_candidate(left, right),
        }

    development = [
        case("dev-example", "development", [("shop", 100), ("shop", -25)], [("shop", 50)])
    ]
    evaluation = []
    for i in range(condition.evaluation_cases):
        amount = rng.randint(200, 5000)
        evaluation.append(
            case(
                f"heldout-{i + 1}",
                f"evaluation-{i + 1}",
                [(f"item-{i}", amount), (f"item-{i}", -amount), ("LEFT", -17)],
                [(f"item-{i}", 20), ("right,quoted", 13), ("right,quoted", -3), ("ZERO", 0)],
            )
        )
    return {
        "schema_version": 2,
        "task_id": task.id,
        "brief": "Build a reusable skill for the declared reconciliation contract.",
        "authorship": "yassa deterministic synthetic generator",
        "source": "synthetic-reconciliation-v1",
        "synthetic": True,
        "assumptions": ["Invented ledger pairs; no representation of real work."],
        "development": development,
        "evaluation": evaluation,
    }


def prepare_files(task: TaskContract, condition: NativeCondition, base: Path):
    if condition.route == "user-supplied":
        source = Path(condition.source_path)
        source = source if source.is_absolute() else base / source
        original = read_regular(source)
        if digest(original) != condition.source_sha256:
            raise ValueError(f"source hash mismatch for condition {condition.id}")
        value = parse_json(original)
        provenance = {"source_path": str(source.resolve()), "preparation": "validated-file-copy-v2"}
    else:
        original = canonical(condition.model_dump(mode="json"))
        value = generate_files(task, condition)
        provenance = {
            "generator": condition.generator,
            "generator_contract": 1,
            "request": condition.request,
            "seed": condition.seed,
            "model": None,
            "parameters": {"evaluation_cases": condition.evaluation_cases},
            "selection": "all generated cases; no outcome-based selection",
        }
    materials = FileMaterials.model_validate(value)
    validate_materials(task, materials)
    provenance.update(
        {
            "route": condition.route,
            "original_sha256": digest(original),
            "authorship": materials.authorship,
            "source": materials.source,
            "synthetic": materials.synthetic,
            "assumptions": materials.assumptions,
            "verification": "independent deterministic oracle; all cases checked"
            if task.checker != "json-exact-v1"
            else "reference JSON validated; semantic correctness supplied by author",
        }
    )
    return materials, provenance, original


def make_native_plan(
    study: NativeStudyV2, materials: dict[str, FileMaterials], study_id: str
) -> dict:
    # Admit algebraically before expanding potentially large build/case/repeat products.
    build_count = len(study.conditions) * sum(arm.builds for arm in study.arms)
    uses = sum(
        len(materials[c.id].evaluation)
        * sum(arm.builds for arm in study.arms)
        * study.consumer_repeats
        for c in study.conditions
    )
    attempts = build_count + uses
    seconds = (
        build_count * study.admission.build_timeout_seconds
        + uses * study.admission.consumer_timeout_seconds
    )
    if attempts > study.admission.max_attempts:
        raise ValueError(f"plan reserves {attempts} attempts, exceeding max_attempts")
    if seconds > study.admission.max_scheduled_seconds:
        raise ValueError(f"plan reserves {seconds} native seconds, exceeding max_scheduled_seconds")
    trials = []
    for condition in study.conditions:
        for arm in study.arms:
            for build in range(1, arm.builds + 1):
                dimensions = {"condition": condition.id, "arm": arm.id, "build": build}
                parent = "build-" + identity(dimensions)[:20]
                trials.append(
                    {
                        "id": parent,
                        **dimensions,
                        "role": "build",
                        "parent": None,
                        "case": None,
                        "group": None,
                        "repeat": None,
                    }
                )
                for case in materials[condition.id].evaluation:
                    for repeat in range(1, study.consumer_repeats + 1):
                        use = {
                            **dimensions,
                            "role": "consume",
                            "parent": parent,
                            "case": case.id,
                            "group": case.group,
                            "repeat": repeat,
                        }
                        trials.append({"id": "consume-" + identity(use)[:20], **use})
    trials.sort(key=lambda t: (t["role"] != "build", identity([study.schedule_seed, t["id"]])))
    body = {
        "schema_version": 2,
        "planner": "native-fixed-plan-v2",
        "study_id": study_id,
        "trials": trials,
        "reserved_attempts": len(trials),
        "reserved_native_seconds": seconds,
        "schedule": "all builds then consumers; seeded hash order within each phase",
        "admission": "whole plan admitted before execution; no truncation or harness retries",
        "denominator": "all planned uses; failed builds zero; infrastructure failures missing",
        "time_scope": "native command deadlines; sandbox setup and export excluded",
    }
    return {"id": identity(body), **body}
