"""Pure study schema and validation; no filesystem, framework, or provider I/O."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

Slug = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,47}$")]
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Row(Record):
    account: Annotated[str, Field(pattern=r"^[ A-Za-z0-9_-]{1,80}$")]
    cents: Annotated[StrictInt, Field(ge=-1_000_000_000, le=1_000_000_000)]

    @model_validator(mode="after")
    def nonempty_account(self):
        if not self.account.strip():
            raise ValueError("account must contain a non-space character")
        return self


class Total(Record):
    account: str
    net_cents: StrictInt
    count: Annotated[StrictInt, Field(ge=1)]


class Case(Record):
    id: Slug
    group: Slug
    rows: Annotated[tuple[Row, ...], Field(max_length=1000)]
    expected: tuple[Total, ...]


class Materials(Record):
    schema_version: Literal[1]
    brief: Annotated[str, Field(min_length=1, max_length=20_000)]
    authorship: str
    source: str
    synthetic: Literal[True]
    assumptions: tuple[str, ...]
    development: Annotated[tuple[Case, ...], Field(min_length=1, max_length=50)]
    evaluation: Annotated[tuple[Case, ...], Field(min_length=1, max_length=50)]

    @model_validator(mode="after")
    def disjoint_split(self):
        cases = self.development + self.evaluation
        if len({case.id for case in cases}) != len(cases):
            raise ValueError("case IDs must be unique across the split")
        if {case.group for case in self.development} & {case.group for case in self.evaluation}:
            raise ValueError("development and evaluation groups must be disjoint")
        # Re-labeling an identical input must not bypass the held-out split.
        inputs = [
            tuple(sorted((row.account.strip(" ").lower(), row.cents) for row in case.rows))
            for case in cases
        ]
        if len(set(inputs)) != len(inputs):
            raise ValueError("duplicate case inputs across the split")
        return self


class Condition(Record):
    id: Slug
    route: Literal["user-supplied", "yassa-prepared"]
    source_path: str | None = None
    source_sha256: Hash | None = None
    request: str | None = None
    seed: StrictInt | None = None
    evaluation_cases: Annotated[StrictInt, Field(ge=1, le=20)] = 3

    @model_validator(mode="after")
    def route_inputs(self):
        if self.route == "user-supplied":
            if not self.source_path or not self.source_sha256:
                raise ValueError("supplied materials need a source_path and byte SHA-256")
            if self.request is not None or self.seed is not None:
                raise ValueError("supplied conditions cannot silently generate material")
        else:
            if not self.request or self.seed is None:
                raise ValueError("prepared conditions need a request and explicit seed")
            if self.source_path is not None or self.source_sha256 is not None:
                raise ValueError("prepared fixture conditions do not accept source paths")
        return self


class Arm(Record):
    id: Slug
    fixture_behavior: Literal["complete", "positive-only", "invalid", "refusal"]
    infrastructure_failures: Annotated[StrictInt, Field(ge=0, le=2)] = 0


class Limits(Record):
    max_attempts: Annotated[StrictInt, Field(ge=1, le=1000)] = 100
    infrastructure_retries: Annotated[StrictInt, Field(ge=0, le=2)] = 1
    max_output_tokens: Annotated[StrictInt, Field(ge=1, le=32_000)] = 4096
    time_limit_seconds: Annotated[StrictInt, Field(ge=1, le=300)] = 30


class Study(Record):
    schema_version: Literal[1]
    id: Slug
    question: Annotated[str, Field(min_length=1, max_length=5000)]
    scope: Literal["synthetic-fixture"]
    runtime: Literal["simulated-api"]
    task_contract: Literal["account-totals-v1"]
    scoring: Literal["deterministic"]
    analysis: Literal["descriptive"]
    kinds: Annotated[tuple[Literal["direct", "builder"], ...], Field(min_length=1)]
    arms: Annotated[tuple[Arm, ...], Field(min_length=1, max_length=8)]
    conditions: Annotated[tuple[Condition, ...], Field(min_length=1, max_length=8)]
    builds_per_arm: Annotated[StrictInt, Field(ge=1, le=10)] = 1
    execution_repeats: Annotated[StrictInt, Field(ge=1, le=10)] = 1
    schedule_seed: StrictInt
    limits: Limits

    @model_validator(mode="after")
    def distinct_dimensions(self):
        for label, values in (
            ("arms", [x.id for x in self.arms]),
            ("conditions", [x.id for x in self.conditions]),
            ("kinds", list(self.kinds)),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{label} must be unique")
        return self
