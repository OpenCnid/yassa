"""Single-writer local evidence. Hashes detect changes; they are not OS permissions."""

import os
import re
import stat
from pathlib import Path, PurePosixPath

from .records import canonical, digest, identity, parse_json


def safe_name(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError(f"unsafe artifact path: {name!r}")
    parts = name.split("/")
    reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    if PurePosixPath(name).is_absolute() or any(
        part in {"", ".", ".."}
        or part.startswith(" ")
        or part.endswith((".", " "))
        or not re.fullmatch(r"[A-Za-z0-9_. -]+", part)
        or part.split(".")[0].rstrip(" ").upper() in reserved
        for part in parts
    ):
        raise ValueError(f"unsafe artifact path: {name!r}")
    return name


def reject_links(path: Path) -> None:
    for part in [path, *path.parents]:
        if part.is_symlink() or (
            part.exists()
            and getattr(part.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise ValueError(f"links/reparse points are unsupported: {part}")


def read_regular(path: Path, max_bytes: int = 20_000_000) -> bytes:
    reject_links(path)
    if not path.is_file() or path.stat().st_size > max_bytes:
        raise ValueError(f"not a bounded regular file: {path}")
    with path.open("rb") as file:
        data = file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"file grew beyond size limit: {path}")
    return data


def write_new(path: Path, data: bytes) -> None:
    reject_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Existing records are never overwritten. A crash before sealing is incomplete evidence.
    with path.open("xb") as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())


class EvidenceStore:
    def __init__(self, root: Path):
        self.root = root

    def put(self, files: dict[str, bytes], *, executable=()) -> str:
        if not files:
            raise ValueError("empty evidence bundle")
        names = [safe_name(name) for name in files]
        if not set(executable).issubset(files):
            raise ValueError("executable metadata names an absent file")
        if len({name.casefold() for name in names}) != len(names):
            raise ValueError("case-colliding artifact paths")
        for name in names:
            if any(other.casefold().startswith(name.casefold() + "/") for other in names):
                raise ValueError("artifact file/directory collision")
        manifest = {
            "schema_version": 1,
            "files": [
                {
                    "path": name,
                    "sha256": digest(files[name]),
                    "size": len(files[name]),
                    "executable": name in executable,
                }
                for name in sorted(names)
            ],
        }
        artifact_id = identity(manifest)
        target = self.root / "artifacts" / artifact_id
        if target.exists():
            self.get(artifact_id)
            return artifact_id
        for name in sorted(names):
            write_new(target / "files" / name, files[name])
        write_new(target / "manifest.json", canonical(manifest))
        return artifact_id

    def put_json(self, data: dict, name: str = "record.json") -> str:
        return self.put({name: canonical(data)})

    def get(self, artifact_id: str) -> dict[str, bytes]:
        if not re.fullmatch("[0-9a-f]{64}", artifact_id):
            raise ValueError("invalid artifact identity")
        target = self.root / "artifacts" / artifact_id
        manifest = parse_json(read_regular(target / "manifest.json"))
        if manifest.get("schema_version") != 1 or identity(manifest) != artifact_id:
            raise ValueError("artifact manifest identity mismatch")
        result = {}
        for entry in manifest["files"]:
            name = safe_name(entry["path"])
            data = read_regular(target / "files" / name)
            if len(data) != entry["size"] or digest(data) != entry["sha256"]:
                raise ValueError(f"artifact content mismatch: {artifact_id}/{name}")
            result[name] = data
        actual = {
            path.relative_to(target / "files").as_posix()
            for path in (target / "files").rglob("*")
            if path.is_file()
        }
        if actual != set(result):
            raise ValueError("unmanifested artifact files")
        return result

    def json(self, artifact_id: str, name: str = "record.json") -> dict:
        return parse_json(self.get(artifact_id)[name])


def freeze_package(completion: bytes, store: EvidenceStore) -> str:
    package = parse_json(completion)
    if type(package) is not dict or set(package) != {"files"} or type(package["files"]) is not dict:
        raise ValueError("package must be a JSON object containing exactly files")
    files = package["files"]
    if not 1 <= len(files) <= 30 or sum(len(str(text)) for text in files.values()) > 1_000_000:
        raise ValueError("package exceeds the supported text profile")
    if not isinstance(files.get("SKILL.md"), str) or not files["SKILL.md"].strip():
        raise ValueError("package requires nonempty SKILL.md")
    for name, content in files.items():
        safe_name(name)
        if Path(name).suffix.lower() not in {".md", ".json", ".txt"} or type(content) is not str:
            raise ValueError("simulated API packages support UTF-8 text resources only")
    return store.put({name: content.encode("utf-8") for name, content in files.items()})


def inventory(root: Path) -> list[dict]:
    entries = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative == "run-seal.json" or relative.split("/")[0] == "interpretations":
            continue
        reject_links(path)
        if path.is_file():
            entries.append(
                {
                    "path": relative,
                    "sha256": digest(read_regular(path)),
                    "size": path.stat().st_size,
                }
            )
    return entries


def seal_run(root: Path) -> str:
    body = {"schema_version": 1, "files": inventory(root)}
    seal_id = identity(body)
    write_new(root / "run-seal.json", canonical({**body, "id": seal_id}))
    return seal_id


def verify_run(root: Path) -> str:
    if not (root / "run-seal.json").exists():
        raise ValueError("run is incomplete/unsealed; automatic crash recovery is unsupported")
    seal = parse_json(read_regular(root / "run-seal.json"))
    body = {key: value for key, value in seal.items() if key != "id"}
    if body.get("schema_version") != 1 or identity(body) != seal.get("id"):
        raise ValueError("invalid run seal")
    if inventory(root) != seal["files"]:
        raise ValueError("run evidence has changed since sealing")
    return seal["id"]
