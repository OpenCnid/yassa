"""Controller-only reconciliation-v2 oracle and semantic output checker.

The reference oracle uses sorting, Decimal and per-key filtering. Synthetic
candidates use streaming dictionaries and integer string conversion elsewhere.
"""

import csv
import io
import re
from decimal import Decimal, localcontext
from itertools import groupby

from .records import parse_json

CONTRACT = (
    "Reconcile two UTF-8 CSV files and one JSON policy file. CSV headers are exactly "
    "event_id,revision,id,currency,amount,state in that order. All rows are valid. "
    "event_id and id are nonempty literal case-sensitive strings: never trim or normalize "
    "them; CSV quoting, Unicode and embedded newlines are allowed. revision has 1-10 "
    "base-10 digits and is a positive integer at most 1000000000. currency is an exact "
    "key in the policy. state is "
    'posted or void. The policy is exactly {"currencies":{CODE:{"scale":S,'
    '"tolerance_minor":T},...}}; CODE is three uppercase ASCII letters, S is an integer '
    "from 0 to 3 and T is a nonnegative integer at most 1000000. These are synthetic "
    "per-case rules, not external currency conventions. amount is a signed decimal "
    "string matching -?[0-9]+(\\.[0-9]+)? with at most 18 integral digits and at most S "
    "fractional digits (no fraction for S=0); convert exactly to integer minor units, "
    "without rounding or floating-point loss. Validate this format even for void rows. "
    "Within EACH side separately, select the greatest numeric revision for each event_id "
    "before grouping or filtering state. Identical repeats of an event/revision count once; "
    "repeats agree in id, currency, numeric amount and state. Conflicting repeats do not "
    "occur. Different event IDs with equal contents are distinct events. A latest void "
    "removes that event completely; never fall back to an older posted row. A revision "
    "may change id or currency; only the latest row supplies them. Sum remaining posted "
    "events by the composite (id,currency), separately per side; never convert currencies. "
    "Return only JSON with exactly a balances array. Include one object per key present "
    "among remaining events on either side, even if its sum is zero. Each object has "
    "exactly id,currency,left_minor,right_minor,delta_minor,left_count,right_count,status. "
    "Counts are numbers of remaining events, not CSV rows. Missing sides have amount and "
    "count zero. delta_minor is left minus right. Status is left_only or right_only when "
    "only that side has events, even at zero or within tolerance; otherwise matched when "
    "abs(delta_minor)<=T for that currency, and mismatch otherwise. All amounts and counts "
    "must be JSON integers, never booleans. Empty or entirely voided inputs yield an empty "
    "balances array. Array order, object key order, JSON escaping and whitespace do not "
    "matter. No duplicate keys, extra fields or prose."
)
HEADER = ["event_id", "revision", "id", "currency", "amount", "state"]
AMOUNTS = ("left_minor", "right_minor", "delta_minor")
COUNTS = ("left_count", "right_count")
STATUSES = {"left_only", "right_only", "matched", "mismatch"}


def read_policy(text: str) -> dict:
    value = parse_json(text)
    if (
        type(value) is not dict
        or set(value) != {"currencies"}
        or type(value["currencies"]) is not dict
        or not value["currencies"]
    ):
        raise ValueError("policy requires exactly a nonempty currencies object")
    for code, rule in value["currencies"].items():
        if not re.fullmatch(r"[A-Z]{3}", code):
            raise ValueError("currency codes require three uppercase ASCII letters")
        if (
            type(rule) is not dict
            or set(rule) != {"scale", "tolerance_minor"}
            or type(rule["scale"]) is not int
            or not 0 <= rule["scale"] <= 3
            or type(rule["tolerance_minor"]) is not int
            or not 0 <= rule["tolerance_minor"] <= 1_000_000
        ):
            raise ValueError("invalid currency scale or tolerance")
    return value["currencies"]


def read_events(text: str, policy: dict) -> list[tuple]:
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        if next(reader, None) != HEADER:
            raise ValueError("invalid reconciliation-v2 CSV header")
        events = []
        revisions = {}
        for row in reader:
            if len(row) != 6:
                raise ValueError("invalid event fields")
            event, revision, name, currency, amount, state = row
            if (
                not event
                or not name
                or not re.fullmatch(r"[0-9]{1,10}", revision)
                or not 1 <= int(revision) <= 1_000_000_000
                or currency not in policy
                or state not in {"posted", "void"}
            ):
                raise ValueError("invalid event identity, revision, currency or state")
            scale = policy[currency]["scale"]
            if not re.fullmatch(r"-?[0-9]{1,18}(?:\.[0-9]+)?", amount):
                raise ValueError("invalid decimal amount")
            if "." in amount and (scale == 0 or len(amount.split(".")[1]) > scale):
                raise ValueError("amount exceeds declared precision")
            with localcontext() as context:
                context.prec = 30
                minor = int(Decimal(amount) * (10**scale))
            item = (event, int(revision), name, currency, minor, state)
            key = item[:2]
            if key in revisions and revisions[key] != item:
                raise ValueError("conflicting repeated event revision")
            revisions[key] = item
            events.append(item)
    except csv.Error as error:
        raise ValueError("malformed event CSV") from error
    return events


def input_identity(files: dict[str, str], paths: tuple[str, ...]):
    policy = read_policy(files[paths[2]])
    # Ignore ordering and equivalent duplicate spellings, but retain obsolete
    # revisions: interpreting those rows is part of the work being tested.
    return [policy, *[sorted(set(read_events(files[p], policy))) for p in paths[:2]]]


def oracle(files: dict[str, str], paths: tuple[str, ...]) -> dict:
    policy = read_policy(files[paths[2]])
    sides = []
    for path in paths[:2]:
        ordered = sorted(set(read_events(files[path], policy)))
        latest = [list(group)[-1] for _, group in groupby(ordered, key=lambda row: row[0])]
        sides.append([row for row in latest if row[5] == "posted"])
    keys = sorted({row[2:4] for side in sides for row in side})
    balances = []
    for name, currency in keys:
        left, right = [[r[4] for r in side if r[2:4] == (name, currency)] for side in sides]
        a, b = sum(left), sum(right)
        status = (
            "right_only"
            if not left
            else "left_only"
            if not right
            else "matched"
            if abs(a - b) <= policy[currency]["tolerance_minor"]
            else "mismatch"
        )
        balances.append(
            dict(
                id=name,
                currency=currency,
                left_minor=a,
                right_minor=b,
                delta_minor=a - b,
                left_count=len(left),
                right_count=len(right),
                status=status,
            )
        )
    return {"balances": balances}


def balance_table(value) -> dict:
    if type(value) is not dict or set(value) != {"balances"} or type(value["balances"]) is not list:
        raise ValueError("expected exactly a balances array")
    table = {}
    fields = {"id", "currency", "status", *AMOUNTS, *COUNTS}
    for row in value["balances"]:
        if type(row) is not dict or set(row) != fields:
            raise ValueError("invalid reconciliation-v2 balance fields")
        if (
            type(row["id"]) is not str
            or not row["id"]
            or type(row["currency"]) is not str
            or not re.fullmatch(r"[A-Z]{3}", row["currency"])
            or type(row["status"]) is not str
            or row["status"] not in STATUSES
            or any(type(row[k]) is not int for k in (*AMOUNTS, *COUNTS))
            or any(row[k] < 0 for k in COUNTS)
            or row["left_count"] + row["right_count"] == 0
        ):
            raise ValueError("invalid balance identifiers, integer amounts, counts or status")
        key = row["id"], row["currency"]
        if key in table:
            raise ValueError("duplicate balance key")
        table[key] = row
    return table


def check(work: bytes, expected) -> dict:
    target = balance_table(expected)
    try:
        actual = balance_table(parse_json(work))
    except (ValueError, UnicodeError, RecursionError) as error:
        return {"value": 0, "components": {"schema": False}, "reason": str(error)}
    keys = actual.keys() == target.keys()
    components = {"schema": True, "keys": keys}
    for name, fields in (("amounts", AMOUNTS), ("counts", COUNTS), ("statuses", ("status",))):
        components[name] = keys and all(
            actual[key][field] == row[field] for key, row in target.items() for field in fields
        )
    correct = all(components.values())
    return {
        "value": int(correct),
        "components": components,
        "reason": "all required checks passed"
        if correct
        else "incorrect " + ", ".join(name for name, passed in components.items() if not passed),
    }
