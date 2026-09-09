"""Portable preparation evidence, pinned to the study reviewed before execution."""

from pathlib import Path
from typing import Literal

from pydantic import model_validator

from .evidence import read_regular, safe_name
from .native_contracts import NativeStudyV2, paths_valid
from .records import digest, identity, parse_json
from .study import Hash, Record


class PreparationManifest(Record):
    schema_version: Literal[1]
    study_identity: Hash
    files: dict[str, Hash]

    @model_validator(mode="after")
    def paths(self):
        paths_valid(["preparation/" + name for name in self.files], "preparation")
        return self


def study_identity(study: NativeStudyV2) -> str:
    excluded = {"preparation"}
    # Preserve identities of reviews made before the optional baseline existed.
    if study.consumer_baseline is None:
        excluded.add("consumer_baseline")
    return identity(study.model_dump(mode="json", exclude=excluded))


def load_preparation(study: NativeStudyV2, base: Path) -> dict[str, bytes] | None:
    if study.preparation is None:
        if any(c.generator == "reviewed-files-v1" for c in study.conditions):
            raise ValueError("reviewed materials require a pinned preparation record")
        return None
    path = Path(study.preparation.path)
    path = path if path.is_absolute() else base / path
    raw = read_regular(path)
    if digest(raw) != study.preparation.sha256:
        raise ValueError("preparation record hash mismatch")
    manifest = PreparationManifest.model_validate(parse_json(raw))
    if manifest.study_identity != study_identity(study):
        raise ValueError("study changed since preparation review; create a new draft revision")
    required = {"draft.json", "review.md", "validation.json", "history/000-request.json"}
    if not required <= manifest.files.keys() or len(manifest.files) > 500:
        raise ValueError("incomplete or oversized preparation record")
    files = {"preparation.json": raw}
    for name, pin in manifest.files.items():
        safe_name(name)
        if name.casefold() == "preparation.json":
            raise ValueError("reserved preparation record path")
        body = read_regular(path.parent / name)
        if digest(body) != pin:
            raise ValueError(f"preparation evidence changed: {name}")
        files[name] = body
        if sum(map(len, files.values())) > 20_000_000:
            raise ValueError("preparation evidence exceeds 20 MB")
    return files
