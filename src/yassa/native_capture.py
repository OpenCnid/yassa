"""Bounded native evidence archives; recorded paths are data, never extraction targets."""

import base64

from .evidence import EvidenceStore
from .records import canonical, digest, parse_json

CHUNK_BYTES = 8_000_000


def archive_files(store: EvidenceStore, files: dict[str, bytes], *, executable=()) -> str:
    """Keep even nonportable names losslessly inside an indexed, content-addressed archive."""
    blobs, entries, locations = {}, [], {}
    for name, data in sorted(files.items()):
        chunks = []
        for offset in range(0, len(data), CHUNK_BYTES):
            chunk = data[offset : offset + CHUNK_BYTES]
            key = digest(chunk)
            path = locations.setdefault(key, f"chunks/{len(locations):06}.bin")
            blobs[path] = chunk
            chunks.append(path)
        entries.append(
            {
                "path": name,
                "size": len(data),
                "sha256": digest(data),
                "executable": name in executable,
                "chunks": chunks,
            }
        )
    return store.put({"archive.json": canonical({"schema_version": 1, "files": entries}), **blobs})


def read_archive(store: EvidenceStore, artifact: str) -> dict[str, bytes]:
    blobs = store.get(artifact)
    manifest = parse_json(blobs["archive.json"])
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported native archive")
    files = {}
    for entry in manifest["files"]:
        data = b"".join(blobs[name] for name in entry["chunks"])
        if entry["path"] in files or len(data) != entry["size"] or digest(data) != entry["sha256"]:
            raise ValueError("invalid native archive entry")
        files[entry["path"]] = data
    return files


def reject_secrets(files: dict[str, bytes], secrets: tuple[bytes, ...]) -> None:
    if any(secret in body for secret in secrets for body in files.values()):
        raise ValueError("credential appeared in capture; capture withheld")


def preserve_export(store: EvidenceStore, raw: bytes, secrets: tuple[bytes, ...]) -> tuple:
    """Decode and screen credentials, then archive before portable-path validation."""
    data = parse_json(raw)
    files = {name: base64.b64decode(value, validate=True) for name, value in data["files"].items()}
    reject_secrets({"raw": raw}, secrets)
    reject_secrets(files, secrets)
    archive = archive_files(store, {"export.json": raw})
    return archive, files, data


def recorded_native_files(store: EvidenceStore, result: dict) -> dict[str, bytes]:
    """Keep usage available when output acceptance failed after transcript capture."""
    if result.get("output_id"):
        return store.get(result["output_id"])
    files = store.get(result["transcript_id"]) if result.get("transcript_id") else {}
    if result.get("native_logs_id"):
        files.update(read_archive(store, result["native_logs_id"]))
    return files
