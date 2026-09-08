"""Versioned JSON encoding shared by the controller's records."""

import hashlib
import json
from typing import Any


def canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(value: Any) -> str:
    return digest(canonical(value))


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(data: str | bytes) -> Any:
    def invalid_constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON number: {value}")

    return json.loads(data, object_pairs_hook=_unique_object, parse_constant=invalid_constant)
