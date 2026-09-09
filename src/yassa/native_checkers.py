"""Versioned controller-only checkers; submitted files are data, never executed."""

import csv
import io
import re
from collections import defaultdict

from . import reconciliation
from .records import canonical, parse_json
from .scoring import check_work, reference_totals
from .study import Row

CHECKERS = {"account-totals-v1", "reconciliation-v1", "reconciliation-v2", "json-exact-v1"}
RECONCILIATION_CONTRACT = (
    "Read two UTF-8 CSV files with exactly the columns id,cents. IDs are nonempty "
    "case-sensitive strings; do not trim or normalize them. Cents are signed integers. "
    "Sum duplicate IDs separately on each side. Return only JSON with one key, balances, "
    "an array containing exactly one object per ID in the union of both files, including "
    "zero balances. Each object has exactly id, left_cents, right_cents, delta_cents; "
    "delta_cents is left minus right. Missing sides are zero. All amounts must be JSON "
    "integers, never booleans. Array order, JSON key order and whitespace do not matter. "
    "Empty files with headers yield an empty balances array. No extra fields or prose."
)


def csv_rows(text: str) -> list[tuple[str, int]]:
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames != ["id", "cents"]:
        raise ValueError("CSV requires exactly the header id,cents")
    rows = []
    for row in reader:
        if set(row) != {"id", "cents"} or not row["id"] or row["cents"] is None:
            raise ValueError("invalid reconciliation row")
        if not re.fullmatch(r"-?[0-9]+", row["cents"]):
            raise ValueError("CSV cents must be signed integers")
        rows.append((row["id"], int(row["cents"])))
    return rows


def oracle(checker: str, files: dict[str, str], input_paths: tuple[str, ...]):
    """Validate specialized inputs and independently recompute reference candidates."""
    if checker == "reconciliation-v2":
        return reconciliation.oracle(files, input_paths)
    if checker == "account-totals-v1":
        value = parse_json(files[input_paths[0]])
        if type(value) is not dict or set(value) != {"rows"} or type(value["rows"]) is not list:
            raise ValueError("account totals requires exactly a rows array")
        rows = [Row.model_validate(row).model_dump() for row in value["rows"]]
        return {"totals": reference_totals(rows)}
    if checker == "reconciliation-v1":
        sides = [csv_rows(files[path]) for path in input_paths]
        ids = sorted({name for side in sides for name, _ in side})
        balances = []
        for name in ids:
            left, right = [sum(amount for key, amount in side if key == name) for side in sides]
            balances.append(
                {"id": name, "left_cents": left, "right_cents": right, "delta_cents": left - right}
            )
        return {"balances": balances}
    if checker == "json-exact-v1":
        return None
    raise ValueError(f"unsupported checker: {checker}")


def input_identity(checker: str, files: dict[str, str], input_paths: tuple[str, ...]):
    """Do not let row ordering or account spelling bypass fixture held-out splits."""
    if checker == "reconciliation-v2":
        return reconciliation.input_identity(files, input_paths)
    if checker == "account-totals-v1":
        rows = parse_json(files[input_paths[0]])["rows"]
        return sorted((r["account"].strip(" ").lower(), r["cents"]) for r in rows)
    if checker == "reconciliation-v1":
        return [sorted(csv_rows(files[p])) for p in input_paths]
    return files


def _balances(value) -> dict:
    if type(value) is not dict or set(value) != {"balances"} or type(value["balances"]) is not list:
        raise ValueError("expected exactly a balances array")
    table = {}
    for row in value["balances"]:
        if type(row) is not dict or set(row) != {"id", "left_cents", "right_cents", "delta_cents"}:
            raise ValueError("invalid balance fields")
        name = row["id"]
        if type(name) is not str or not name or name in table:
            raise ValueError("balance IDs must be nonempty and unique")
        amounts = tuple(row[k] for k in ("left_cents", "right_cents", "delta_cents"))
        if any(type(x) is not int for x in amounts):
            raise ValueError("balance amounts must be integers")
        table[name] = amounts
    return table


def check(checker: str, work: bytes, expected) -> dict:
    if checker == "reconciliation-v2":
        return reconciliation.check(work, expected)
    if checker == "account-totals-v1":
        if type(expected) is not dict or set(expected) != {"totals"}:
            raise ValueError("account reference requires exactly totals")
        return check_work(work, expected["totals"])
    if checker not in CHECKERS:
        raise ValueError(f"unsupported checker: {checker}")
    # Validate the protected target outside the subject-output error handler.
    target = _balances(expected) if checker == "reconciliation-v1" else canonical(expected)
    try:
        actual = parse_json(work)
        actual = _balances(actual) if checker == "reconciliation-v1" else canonical(actual)
        correct = actual == target
        return {
            "value": int(correct),
            "components": {"schema": True, "values": correct},
            "reason": "all required checks passed" if correct else "incorrect values",
        }
    except (ValueError, UnicodeError, RecursionError) as error:
        return {"value": 0, "components": {"schema": False}, "reason": str(error)}


def reconciliation_candidate(left: list[tuple[str, int]], right: list[tuple[str, int]]) -> dict:
    """Generator implementation separate from the summation/filter oracle above."""
    table = defaultdict(lambda: [0, 0])
    for side, rows in enumerate((left, right)):
        for name, amount in rows:
            table[name][side] += amount
    return {
        "balances": [
            {"id": name, "left_cents": a, "right_cents": b, "delta_cents": a - b}
            for name, (a, b) in table.items()
        ]
    }
