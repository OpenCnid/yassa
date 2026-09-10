"""Spec-only native reconstruction studies with a separate, pinned pytest oracle."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StrictInt, model_validator

from .direct_contracts import DirectArm, NativeRole
from .evidence import read_regular
from .native_contracts import SourceBinding, Text, paths_valid
from .records import digest, identity
from .study import Hash, Record, Slug


class ArtifactBundle(Record):
    path: str
    files: Annotated[dict[str, Hash], Field(min_length=1, max_length=500)]

    @model_validator(mode="after")
    def names(self):
        paths_valid(["input/" + n for n in self.files], "input")
        return self


class ArtifactRole(NativeRole):
    timeout_seconds: Annotated[StrictInt, Field(ge=30, le=3600)]


class ArtifactRequest(Record):
    schema_version: Literal[1]
    id: Slug
    question: Text
    prompt: Text
    provenance: Text
    public: ArtifactBundle
    reference: ArtifactBundle
    tests: ArtifactBundle
    role: ArtifactRole
    sources: tuple[SourceBinding, ...] = ()
    arms: Annotated[tuple[DirectArm, ...], Field(min_length=1, max_length=8)]
    repeats: Annotated[StrictInt, Field(ge=1, le=20)]
    schedule_seed: StrictInt
    max_attempts: Annotated[StrictInt, Field(ge=1, le=160)]
    max_scheduled_seconds: Annotated[StrictInt, Field(ge=1)]
    test_timeout_seconds: Annotated[StrictInt, Field(ge=10, le=600)]

    @model_validator(mode="after")
    def boundaries(self):
        if len({a.id for a in self.arms}) != len(self.arms):
            raise ValueError("duplicate artifact arm")
        sources = {s.id: s for s in self.sources}
        if len(sources) != len(self.sources):
            raise ValueError("duplicate artifact source")
        used = set()
        for arm in self.arms:
            if len(set(arm.sources)) != len(arm.sources) or not set(arm.sources) <= sources.keys():
                raise ValueError("artifact arm must name distinct declared sources")
            if arm.sources and not arm.invocation:
                raise ValueError("artifact treatment requires an explicit invocation")
            used.update(arm.sources)
            paths_valid(
                [".agents/skills/" + n for sid in arm.sources for n in sources[sid].files],
                ".agents/skills",
            )
        if used != sources.keys():
            raise ValueError("unused artifact source")
        if "pyproject.toml" not in self.tests.files or not any(
            n.startswith("tests/test_") and n.endswith(".py") for n in self.tests.files
        ):
            raise ValueError("pytest oracle requires pyproject.toml and tests/test_*.py")
        if any(n != "pyproject.toml" and not n.startswith("tests/") for n in self.tests.files):
            raise ValueError("oracle files must be pytest configuration or tests")
        if set(self.public.files.values()) & (
            set(self.reference.files.values()) | set(self.tests.files.values())
        ):
            raise ValueError("public bytes overlap protected source/tests")
        artifact_plan(self)
        return self


def artifact_plan(request):
    trials = []
    for repeat in range(1, request.repeats + 1):
        for arm in request.arms:
            row = {"arm": arm.id, "repeat": repeat, "role": "artifact-build"}
            trials.append({"id": "artifact-" + identity(row)[:20], **row})
    trials.sort(key=lambda t: identity([request.schedule_seed, t["id"]]))
    seconds = len(trials) * request.role.timeout_seconds
    if len(trials) > request.max_attempts or seconds > request.max_scheduled_seconds:
        raise ValueError("artifact allocation exceeds caps")
    body = {"trials": trials, "reserved_attempts": len(trials), "reserved_seconds": seconds}
    return {"id": identity(body), **body}


def read_bundle(bundle, base):
    directory = Path(bundle.path)
    directory = directory if directory.is_absolute() else base / directory
    files = {n: read_regular(directory / n) for n in bundle.files}
    if sum(map(len, files.values())) > 20_000_000:
        raise ValueError("artifact input bundle exceeds 20 MB")
    if any(digest(b) != bundle.files[n] for n, b in files.items()):
        raise ValueError("artifact input pin mismatch")
    return files
