"""Public preparation records shared by guided model operations and expert imports."""

from typing import Annotated, Any, Literal

from pydantic import Field, StrictBool, StrictInt, model_validator

from .json_rubric import JsonRubric
from .native_contracts import (
    Admission,
    ConsumerBaseline,
    FileBinding,
    FileCase,
    NativeArm,
    SourceBinding,
    Text,
    paths_valid,
)
from .study import Hash, Record, Slug


class PreparationSettings(Record):
    model: Text
    reviewer_model: Text
    max_calls: Annotated[StrictInt, Field(ge=1, le=12)]
    max_output_tokens: Annotated[StrictInt, Field(ge=100, le=32000)]
    timeout_seconds: Annotated[StrictInt, Field(ge=1, le=300)]


class NativePreparationSettings(Record):
    runtime: Literal["native-codex-cli"]
    image: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    model: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_.-]+$")]
    reviewer_model: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_.-]+$")]
    reasoning_effort: Literal["low", "medium", "high", "xhigh"]
    max_calls: Annotated[StrictInt, Field(ge=1, le=12)]
    max_output_bytes: Annotated[StrictInt, Field(ge=100, le=1_000_000)]
    timeout_seconds: Annotated[StrictInt, Field(ge=30, le=300)]


class ExecutionSettings(Record):
    model: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_.-]+$")]
    reasoning_effort: Literal["low", "medium", "high", "xhigh"]
    sources: tuple[SourceBinding, ...] = ()
    arms: Annotated[tuple[NativeArm, ...], Field(min_length=1, max_length=8)]
    control_rationale: dict[Slug, Text]
    consumer_baseline: ConsumerBaseline | None = None
    consumer_repeats: Annotated[StrictInt, Field(ge=1, le=20)]
    schedule_seed: StrictInt
    admission: Admission

    @model_validator(mode="after")
    def rationales(self):
        ids = {a.id for a in self.arms}
        if len(ids) != len(self.arms) or len({s.id for s in self.sources}) != len(self.sources):
            raise ValueError("duplicate source or arm ID")
        sources = {s.id: s for s in self.sources}
        used = set()
        for arm in self.arms:
            if len(set(arm.sources)) != len(arm.sources) or not set(arm.sources) <= sources.keys():
                raise ValueError("arm sources must be distinct declared bindings")
            used.update(arm.sources)
            paths_valid(
                [".agents/skills/" + name for sid in arm.sources for name in sources[sid].files],
                ".agents/skills",
            )
        if used != sources.keys():
            raise ValueError("unused source binding")
        if self.consumer_baseline:
            if self.consumer_baseline.id in ids:
                raise ValueError("consumer baseline ID must differ from builder arm IDs")
            ids.add(self.consumer_baseline.id)
        if set(self.control_rationale) != ids:
            raise ValueError("every arm/baseline requires an interpretation rationale")
        return self


class MaterialSource(Record):
    id: Slug
    file: FileBinding
    split: Literal["specification", "development", "evaluation"]
    description: Text
    origin: Text
    version: Text
    access: Text
    license: Text
    authorship: Text
    synthetic: StrictBool


class GeneralRequest(Record):
    schema_version: Literal[2]
    id: Slug = "prepared-study"
    request: Text
    intended_use: Text | None = None
    answers: tuple[Text, ...] = ()
    scope: Literal["synthetic-fixture", "user-defined"] = "synthetic-fixture"
    evidence: Literal["descriptive", "broader-comparison"] = "descriptive"
    comparison: Literal["builder", "direct"] = "builder"
    activation: Literal["explicit", "automatic"] = "explicit"
    clarification: Literal["preparation-only", "measured"] = "preparation-only"
    routes: tuple[Literal["user-supplied", "yassa-prepared"], ...] = ("yassa-prepared",)
    documents: Annotated[tuple[MaterialSource, ...], Field(max_length=20)] = ()
    seed: StrictInt = 0
    development_cases: Annotated[StrictInt, Field(ge=1, le=10)] = 2
    evaluation_cases: Annotated[StrictInt, Field(ge=1, le=10)] = 3
    preparation: PreparationSettings | NativePreparationSettings | None = None
    execution: ExecutionSettings | None = None
    expert_proposal: FileBinding | None = None
    expert_review: FileBinding | None = None

    @model_validator(mode="after")
    def distinct(self):
        if not self.routes or len(set(self.routes)) != len(self.routes):
            raise ValueError("preparation routes must be distinct and nonempty")
        if len({d.id for d in self.documents}) != len(self.documents):
            raise ValueError("duplicate document ID")
        if self.expert_review and not self.expert_proposal:
            raise ValueError("expert review requires a pinned expert proposal")
        return self


class Question(Record):
    field: Text
    prompt: Text


class TaskProposal(Record):
    questions: Annotated[tuple[Question, ...], Field(max_length=2)] = ()
    intended_use: Text | None = None
    facts: tuple[Text, ...] = ()
    inferences: tuple[Text, ...] = ()
    assumptions: tuple[Text, ...] = ()
    requirements: Text | None = None
    rubric: JsonRubric | None = None
    input_paths: tuple[str, ...] = ()
    case_plan: Text | None = None


class Calibration(Record):
    case_id: Slug
    output: Any
    accept: StrictBool
    rationale: Text
    fails: tuple[Slug, ...] = ()


class CaseBatch(Record):
    cases: Annotated[tuple[FileCase, ...], Field(min_length=1, max_length=10)]
    origins: dict[Slug, tuple[Slug, ...]]
    probes: Annotated[tuple[Calibration, ...], Field(min_length=2, max_length=200)]
    selection: Text


class ConditionProposal(Record):
    route: Literal["user-supplied", "yassa-prepared"]
    authorship: Text
    development: CaseBatch
    evaluation: CaseBatch


class StudyProposal(Record):
    task: TaskProposal
    conditions: Annotated[tuple[ConditionProposal, ...], Field(max_length=2)] = ()


class ReviewFindings(Record):
    issues: tuple[Text, ...]
    assessment: Text


class ExpertReview(ReviewFindings):
    proposal_sha256: Hash
    reviewer: Text
    method: Text
