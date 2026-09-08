"""Deterministic checker v1. It reads recorded JSON, never submitted code."""

from collections import Counter
from typing import Any

from .records import parse_json

SCORER_VERSION = "account-totals-v1"
CONTRACT = (
    "Return only a JSON object with one key, totals, containing an array of objects. "
    "Each object has exactly account, net_cents, and count. Normalize account names by "
    "stripping leading/trailing ASCII spaces and lowercasing. Include every input row, "
    "including negative amounts, zero amounts, and duplicate rows. For each normalized "
    "account, net_cents is the integer sum of cents and count is the integer row count. "
    "Include zero-sum accounts. Output account names must be normalized and unique; "
    "array order, whitespace, and JSON object key order do not matter. Empty input "
    "requires an empty totals array. No extra fields or prose. Booleans are not integers."
)


def reference_totals(rows: list[dict]) -> list[dict]:
    """Independent controller oracle used to validate reference candidates at freeze."""
    names = [row["account"].strip(" ").lower() for row in rows]
    counts = Counter(names)
    return [
        {
            "account": name,
            "net_cents": sum(
                row["cents"] for row, account in zip(rows, names, strict=True) if account == name
            ),
            "count": counts[name],
        }
        for name in sorted(counts)
    ]


def _table(value: Any) -> dict[str, tuple[int, int]]:
    if type(value) is not dict or set(value) != {"totals"} or type(value["totals"]) is not list:
        raise ValueError("expected exactly a totals array")
    result = {}
    for row in value["totals"]:
        if type(row) is not dict or set(row) != {"account", "net_cents", "count"}:
            raise ValueError("each total needs exactly account, net_cents, count")
        name = row["account"]
        if type(name) is not str or not name or name != name.strip(" ").lower():
            raise ValueError("account names must be nonempty and normalized")
        if name in result:
            raise ValueError("duplicate account total")
        if type(row["net_cents"]) is not int or type(row["count"]) is not int or row["count"] < 1:
            raise ValueError("net_cents/count must be integers and count must be positive")
        result[name] = (row["net_cents"], row["count"])
    return result


def check_work(work: bytes, expected: list[dict]) -> dict:
    target = _table({"totals": expected})
    try:
        actual = _table(parse_json(work))
    except (ValueError, UnicodeError, RecursionError) as error:
        return {
            "value": 0,
            "components": {"schema": False, "accounts": False, "net_cents": False, "counts": False},
            "reason": str(error),
        }
    components = {
        "schema": True,
        "accounts": set(actual) == set(target),
        "net_cents": set(actual) == set(target)
        and all(actual[name][0] == total[0] for name, total in target.items()),
        "counts": set(actual) == set(target)
        and all(actual[name][1] == total[1] for name, total in target.items()),
    }
    return {
        "value": int(all(components.values())),
        "components": components,
        "reason": "all required checks passed"
        if all(components.values())
        else "incorrect " + ", ".join(key for key, ok in components.items() if not ok),
    }
