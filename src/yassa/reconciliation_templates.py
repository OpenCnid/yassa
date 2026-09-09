"""Synthetic event-reconciliation recipes and deliberately faulty candidate solvers.

Never installed in subject contexts. This constructor is independent of the
protected sort/filter/Decimal oracle in reconciliation.py.
"""

import copy
import csv
import io
import json
import random
from collections import defaultdict

from .records import canonical, digest

VERSION = "reconciliation-event-suite-v1"
FEATURES = (
    "revision-order",
    "void-and-rekey",
    "currency-precision",
    "tolerance-boundary",
    "presence-and-zero",
    "literal-csv",
    "combined-rules",
    "bulk-interactions",
)
FAULTS = (
    "sum-history",
    "lexical-revision",
    "void-before-latest",
    "global-event-ids",
    "merge-currencies",
    "float-amounts",
    "strict-tolerance",
    "zero-means-absent",
    "count-repeats",
    "normalize-ids",
    "reverse-delta",
)


def candidate(left, right, policy, fault=None):
    """Streaming candidate; input tuples retain their textual decimal amounts."""
    table = defaultdict(lambda: [0, 0, 0, 0])
    global_seen = set()
    for side, rows in enumerate((left, right)):
        versions = {}
        for event, revision, name, currency, amount, state in rows:
            if fault == "void-before-latest" and state == "void":
                continue
            rank = str(revision) if fault == "lexical-revision" else int(revision)
            if event not in versions or rank > versions[event][0]:
                versions[event] = (rank, (event, revision, name, currency, amount, state))
        selected = rows if fault == "sum-history" else [r for _, r in versions.values()]
        if fault == "count-repeats":
            selected = [r for r in rows if int(r[1]) == int(versions[r[0]][1][1])]
        for event, _, name, currency, amount, state in selected:
            if state == "void":
                continue
            if fault == "global-event-ids" and event in global_seen:
                continue
            global_seen.add(event)
            scale = policy["currencies"][currency]["scale"]
            digits = amount.lstrip("-").split(".")
            minor = int(digits[0]) * 10**scale
            minor += int(digits[1].ljust(scale, "0")) if len(digits) == 2 else 0
            minor *= -1 if amount.startswith("-") else 1
            if fault == "float-amounts":
                minor = int(float(amount) * 10**scale)
            if fault == "normalize-ids":
                name = name.strip().casefold()
            if fault == "merge-currencies":
                currency = next(iter(policy["currencies"]))
            row = table[name, currency]
            row[side] += minor
            row[2 + side] += 1
    balances = []
    for (name, currency), (a, b, ac, bc) in table.items():
        delta = b - a if fault == "reverse-delta" else a - b
        tolerance = policy["currencies"][currency]["tolerance_minor"]
        close = abs(delta) < tolerance if fault == "strict-tolerance" else abs(delta) <= tolerance
        present_left, present_right = (a != 0, b != 0) if fault == "zero-means-absent" else (ac, bc)
        if not present_left and not present_right:
            continue
        status = (
            "right_only"
            if not present_left
            else "left_only"
            if not present_right
            else "matched"
            if close
            else "mismatch"
        )
        balances.append(
            dict(
                id=name,
                currency=currency,
                left_minor=a,
                right_minor=b,
                delta_minor=delta,
                left_count=ac,
                right_count=bc,
                status=status,
            )
        )
    return {"balances": balances}


def make_case(task, name, group, left, right, policy):
    def csv_text(rows):
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["event_id", "revision", "id", "currency", "amount", "state"])
        writer.writerows(rows)
        return stream.getvalue()

    return {
        "id": name,
        "group": group,
        "files": dict(
            zip(
                task.checker_inputs,
                (
                    csv_text(left),
                    csv_text(right),
                    canonical(policy).decode("utf-8"),
                ),
                strict=True,
            )
        ),
        "expected": candidate(left, right, policy),
    }


def generate_cases(task, seed, features):
    rng = random.Random(seed)
    n = rng.randint(200, 900)
    policy = {
        "currencies": {
            "USD": {"scale": 2, "tolerance_minor": 2},
            "JPY": {"scale": 0, "tolerance_minor": 0},
            "KWD": {"scale": 3, "tolerance_minor": 3},
        }
    }

    def e(event, revision, name, amount, currency="USD", state="posted"):
        return (event, revision, name, currency, str(amount), state)

    development = [
        make_case(
            task,
            "dev-revisions",
            "development-revisions",
            [
                e("dev-a", 1, "old", "8.00"),
                e("dev-a", 3, "new", "1.25"),
                e("dev-a", 3, "new", "01.25"),
                e("dev-b", 1, "new", "-0.25"),
            ],
            [e("dev-a", 1, "new", "1.02")],
            policy,
        ),
        make_case(
            task,
            "dev-void-zero",
            "development-void-zero",
            [
                e("dev-v", 1, "removed", "7"),
                e("dev-v", 2, "removed", "0", state="void"),
                e("dev-z", 1, "zero", "0"),
            ],
            [],
            policy,
        ),
        make_case(
            task,
            "dev-currencies",
            "development-currencies",
            [
                e("dev-j", 1, "shared", "3", "JPY"),
                e("dev-k", 1, "shared", "-0.009", "KWD"),
            ],
            [e("dev-r", 1, "shared", "3", "JPY"), e("dev-s", 1, "shared", "0", "KWD")],
            policy,
        ),
    ]
    samples = {
        "revision-order": (
            [
                e("same", 10, "current", f"{n}.01"),
                e("same", 2, "obsolete", "900.00"),
                e("same", 10, "current", f"{n}.01"),
                e("other", 1, "current", "-0.01"),
            ],
            [e("same", 1, "current", n), e("repeat", 1, "current", "0")],
        ),
        "void-and-rekey": (
            [
                e("gone", 1, "ghost", "99"),
                e("gone", 11, "ghost", "0", state="void"),
                e("gone", 2, "ghost", "5"),
                e("move", 1, "old-key", "30"),
                e("move", 4, "new-key", "0.007", "KWD"),
                e("back", 1, "back", "0", state="void"),
                e("back", 3, "back", "-2"),
            ],
            [e("r", 1, "new-key", "0.010", "KWD")],
        ),
        "currency-precision": (
            [
                e("usd", 1, "multi", "90071992547409.93"),
                e("jpy", 1, "multi", "9007199254740993", "JPY"),
                e("kwd", 1, "multi", "-9007199254740.993", "KWD"),
                e("small", 1, "fraction", "0.29"),
            ],
            [
                e("r-usd", 1, "multi", "90071992547409.91"),
                e("r-kwd", 1, "multi", "-9007199254740.990", "KWD"),
            ],
        ),
        "tolerance-boundary": (
            [
                e("exact", 1, "exact", "0.02"),
                e("outside", 1, "outside", "-0.03"),
                e("inside", 1, "inside", "0.001", "KWD"),
                e("negative", 1, "negative", "-0.003", "KWD"),
            ],
            [
                e("r1", 1, "exact", "0"),
                e("r2", 1, "outside", "0"),
                e("r3", 1, "inside", "0", "KWD"),
                e("r4", 1, "negative", "0", "KWD"),
            ],
        ),
        "presence-and-zero": (
            [
                e("a", 1, "cancel", n),
                e("b", 1, "cancel", -n),
                e("z", 1, "one-sided-zero", "-0.00"),
                e("both", 1, "both-zero", "0"),
                e("v", 2, "void-only", "0", state="void"),
            ],
            [
                e("c", 1, "cancel", "0"),
                e("d", 1, "both-zero", "0"),
                e("right", 1, "right-zero", "0"),
            ],
        ),
        "literal-csv": (
            [
                e('event,"\n', 1, 'Case,"\n', "0.29"),
                e("lower", 1, " case ", "-0.10"),
                e("accent", 1, "café", "2"),
                e("decomposed", 1, "cafe\u0301", "-2"),
            ],
            [e('event,"\n', 1, 'Case,"\n', "0.27"), e("lower", 1, "case", "0.10")],
        ),
    }
    # Interactions mix the same declared rules with fresh keys and unsorted histories.
    combined_left, combined_right = [], []
    for feature in ("revision-order", "void-and-rekey", "tolerance-boundary", "presence-and-zero"):
        for destination, side in zip(
            (combined_left, combined_right), samples[feature], strict=True
        ):
            destination.extend(
                (feature + ":" + ev, rev, feature + ":" + name, cur, amt, state)
                for ev, rev, name, cur, amt, state in side
            )
    rng.shuffle(combined_left)
    rng.shuffle(combined_right)
    samples["combined-rules"] = combined_left, combined_right
    bulk_left, bulk_right = [], []
    for i in range(96):
        currency = ("USD", "JPY", "KWD")[i % 3]
        scale = policy["currencies"][currency]["scale"]
        amount = f"{n + i}." + "1" * scale if scale else str(n + i)
        final = e(
            f"event-{i}",
            10,
            f"bucket-{i % 24}",
            amount,
            currency,
            "void" if i % 7 == 0 else "posted",
        )
        bulk_left.extend([e(f"event-{i}", 2, f"obsolete-{i}", "999", currency), final, final])
        bulk_right.append(e(f"event-{i}", 1, f"bucket-{i % 24}", amount, currency))
        if i % 5 == 0:
            bulk_left.append(e(f"cancel-{i}", 1, f"bucket-{i % 24}", "-" + amount, currency))
    rng.shuffle(bulk_left)
    rng.shuffle(bulk_right)
    samples["bulk-interactions"] = bulk_left, bulk_right
    evaluation = [
        make_case(task, "heldout-" + f, "evaluation-" + f, *samples[f], policy) for f in features
    ]
    return development, evaluation


def verify_probes(task, material, check):
    records = []
    for case in material.development + material.evaluation:
        alternative = {
            "balances": [
                dict(reversed(list(r.items()))) for r in reversed(case.expected["balances"])
            ]
        }
        probes = [
            ("reference", canonical(case.expected), 1),
            (
                "order-whitespace-unicode",
                json.dumps(alternative, ensure_ascii=False, indent=2).encode(),
                1,
            ),
            ("missing-schema", b"{}", 0),
            ("extra-field", canonical({**case.expected, "extra": 0}), 0),
            ("duplicate-json-key", b'{"balances":[],"balances":[]}', 0),
        ]
        if case.expected["balances"]:
            for field in (
                "left_minor",
                "right_minor",
                "delta_minor",
                "left_count",
                "right_count",
                "status",
            ):
                wrong = copy.deepcopy(case.expected)
                wrong["balances"][0][field] = (
                    ("mismatch" if wrong["balances"][0][field] != "mismatch" else "matched")
                    if field == "status"
                    else wrong["balances"][0][field] + 1
                )
                probes.append(("wrong-" + field, canonical(wrong), 0))
            for label, replacement in (("boolean", True), ("float", 1.0), ("numeric-string", "1")):
                wrong = copy.deepcopy(case.expected)
                wrong["balances"][0]["left_minor"] = replacement
                probes.append((label, canonical(wrong), 0))
            rows = case.expected["balances"]
            probes.extend(
                [
                    ("missing-record", canonical({"balances": rows[1:]}), 0),
                    ("duplicate-record", canonical({"balances": rows + rows[:1]}), 0),
                ]
            )
        else:
            probes.append(
                (
                    "invented-record",
                    canonical(
                        {
                            "balances": [
                                {
                                    "id": "invented",
                                    "currency": "USD",
                                    "left_minor": 0,
                                    "right_minor": 0,
                                    "delta_minor": 0,
                                    "left_count": 1,
                                    "right_count": 0,
                                    "status": "left_only",
                                }
                            ]
                        }
                    ),
                    0,
                )
            )
        sides = [
            list(csv.reader(io.StringIO(case.files[p], newline="")))[1:]
            for p in task.checker_inputs[:2]
        ]
        policy = json.loads(case.files[task.checker_inputs[2]])
        for fault in FAULTS:
            wrong = candidate(*sides, policy, fault)
            # A fault can be observationally equivalent on a case; record that,
            # never invent a rejection or count it as detected coverage.
            equivalent = sorted(
                wrong["balances"], key=lambda r: (r["id"], r["currency"])
            ) == sorted(case.expected["balances"], key=lambda r: (r["id"], r["currency"]))
            probes.append((fault, canonical(wrong), int(equivalent)))
        for label, work, expected in probes:
            observed = check(task.checker, work, case.expected)["value"]
            if observed != expected:
                raise ValueError(f"checker calibration failed: {case.id}/{label}")
            records.append(
                {
                    "case": case.id,
                    "probe": label,
                    "work_sha256": digest(work),
                    "expected": expected,
                    "observed": observed,
                    "work_utf8": work.decode("utf-8"),
                }
            )
    return {
        "version": "reconciliation-v2-checker-verification-v1",
        "checker": task.checker,
        "references": "all recomputed by independent Decimal/sort/filter oracle",
        "splits": "disjoint IDs/groups and unique semantic inputs checked",
        "probes": records,
        "fault_detection": {
            fault: [p["case"] for p in records if p["probe"] == fault and p["expected"] == 0]
            for fault in FAULTS
        },
    }
