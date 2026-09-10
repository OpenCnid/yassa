"""Direct studies reuse a pinned reviewed task, with explicit host and treatment roles."""

import re
from typing import Annotated, Literal

from pydantic import Field, StrictInt, model_validator

from .native_contracts import FileBinding, SourceBinding, Text, paths_valid
from .records import identity
from .role_api import ApiRole
from .study import Record, Slug


class NativeRole(Record):
    adapter: Literal["native-codex-cli"]
    model: Annotated[str, Field(pattern=r"^gpt-[a-zA-Z0-9_.-]+$")]
    image: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    reasoning_effort: Literal["low", "medium", "high", "xhigh"]
    timeout_seconds: Annotated[StrictInt, Field(ge=30, le=300)]


class DirectArm(Record):
    id: Slug
    sources: tuple[Slug, ...] = ()
    invocation: Annotated[str, Field(max_length=20_000)] = ""
    rationale: Text


class DirectRequest(Record):
    schema_version: Literal[1]
    id: Slug
    question: Text
    task_source: FileBinding
    role: NativeRole | ApiRole
    sources: tuple[SourceBinding, ...] = ()
    arms: Annotated[tuple[DirectArm, ...], Field(min_length=1, max_length=8)]
    repeats: Annotated[StrictInt, Field(ge=1, le=20)]
    schedule_seed: StrictInt
    max_attempts: Annotated[StrictInt, Field(ge=1, le=2000)]
    max_scheduled_seconds: Annotated[StrictInt, Field(ge=1)]

    @model_validator(mode="after")
    def treatments(self):
        if len({a.id for a in self.arms}) != len(self.arms):
            raise ValueError("duplicate direct arm ID")
        if len({s.id for s in self.sources}) != len(self.sources):
            raise ValueError("duplicate direct source ID")
        sources, used = {s.id: s for s in self.sources}, set()
        for arm in self.arms:
            if len(set(arm.sources)) != len(arm.sources) or not set(arm.sources) <= sources.keys():
                raise ValueError("direct arm sources must be distinct declared pins")
            used.update(arm.sources)
            paths_valid(
                [".agents/skills/" + n for sid in arm.sources for n in sources[sid].files],
                ".agents/skills",
            )
            if arm.sources and not arm.invocation:
                raise ValueError(
                    "direct skills require an explicit invocation; activation is not measured"
                )
        if used != sources.keys():
            raise ValueError("unused direct source")
        if self.role.adapter == "inspect-api" and any(
            s.executable or any(not re.search(r"\.(md|txt|json)$", n) for n in s.files)
            for s in self.sources
        ):
            raise ValueError(
                "closed API direct studies support text packs only; no executable packages"
            )
        return self


def direct_plan(request, materials):
    count = sum(len(m.evaluation) for m in materials.values()) * len(request.arms) * request.repeats
    seconds = count * request.role.timeout_seconds
    if count > request.max_attempts or seconds > request.max_scheduled_seconds:
        raise ValueError(
            f"direct allocation reserves {count} attempts and {seconds} seconds, exceeding caps"
        )
    trials = []
    for condition, material in materials.items():
        for case in material.evaluation:
            for repeat in range(1, request.repeats + 1):
                for arm in request.arms:
                    trial = {
                        "condition": condition,
                        "case": case.id,
                        "group": case.group,
                        "repeat": repeat,
                        "arm": arm.id,
                        "role": "direct",
                        "parent": None,
                        "build": None,
                    }
                    trials.append({"id": "direct-" + identity(trial)[:20], **trial})
    trials.sort(
        key=lambda t: (
            identity([request.schedule_seed, t["condition"], t["case"], t["repeat"]]),
            identity([request.schedule_seed, t["id"]]),
        )
    )
    body = {
        "schema_version": 1,
        "planner": "direct-case-repeat-v1",
        "trials": trials,
        "reserved_attempts": count,
        "reserved_seconds": seconds,
        "automatic_retries": 0,
        "scope": "descriptive fixed cases; repeats are not new tasks",
    }
    return {"id": identity(body), **body}
