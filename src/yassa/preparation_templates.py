"""Bounded, explicit task recipes; no natural-language rule inference or model calls."""

import copy
import csv
import io
import json
import random

from . import reconciliation, reconciliation_templates
from .native_checkers import RECONCILIATION_CONTRACT, check, reconciliation_candidate
from .native_contracts import FileMaterials, TaskContract, validate_materials
from .records import canonical, digest
from .scoring import CONTRACT

VERSION = "guided-file-suite-v1"
FEATURES = {
    "account-totals-v1": (
        "normalization",
        "signed-amounts",
        "cancellation",
        "duplicates",
        "empty",
        "integer-bounds",
    ),
    "reconciliation-v1": (
        "duplicates",
        "identifiers",
        "one-sided",
        "cancellation",
        "empty",
        "csv-quoting",
    ),
    "reconciliation-v2": reconciliation_templates.FEATURES,
}


def task_contract(family: str) -> TaskContract:
    if family not in FEATURES:
        raise ValueError(f"unsupported preparation family: {family}")
    totals = family == "account-totals-v1"
    paths = ("input/rows.json",) if totals else ("input/left.csv", "input/right.csv")
    if family == "reconciliation-v2":
        paths += ("input/policy.json",)
    requirements = (
        "Read UTF-8 JSON with exactly a rows array. Each row has exactly account and cents. "
        "Accounts contain 1-80 ASCII letters, digits, underscores, hyphens or spaces and "
        "at least one non-space character. Cents are integers from -1000000000 to 1000000000. "
        + CONTRACT
        if totals
        else reconciliation.CONTRACT
        if family == "reconciliation-v2"
        else RECONCILIATION_CONTRACT
    )
    return TaskContract(
        schema_version=1,
        id=family,
        requirements=requirements,
        package_name="account-totals" if totals else "ledger-reconciliation",
        package_path="output/package",
        result_path="output/answer.json",
        brief_path="input/task.json",
        build_prompt="Build a reusable skill for the task and examples.",
        # Consumers receive all task facts independently of the generated package.
        consumer_prompt="Process " + ", ".join("/work/" + p for p in paths) + ". " + requirements,
        checker=family,
        checker_inputs=paths,
    )


def template_description(family: str) -> dict:
    task = task_contract(family)
    return {
        "family": family,
        "requirements": task.requirements,
        "contract_sha256": digest(task.requirements.encode("utf-8")),
        "features": FEATURES[family],
        "meaning": "Explicit synthetic task rules; selecting a family does not accept them.",
    }


def generate_suite(task: TaskContract, seed: int, features: tuple[str, ...]) -> FileMaterials:
    if (
        not features
        or len(set(features)) != len(features)
        or not set(features) <= set(FEATURES[task.checker])
    ):
        raise ValueError("features must be distinct members of the selected template")
    rng = random.Random(seed)
    amount = rng.randint(200, 5000)

    def case(name, group, left, right=None):
        if task.checker == "account-totals-v1":
            table = {}
            for account, cents in left:
                key = account.strip(" ").lower()
                row = table.setdefault(key, {"account": key, "net_cents": 0, "count": 0})
                row["net_cents"] += cents
                row["count"] += 1
            files = {
                task.checker_inputs[0]: canonical(
                    {"rows": [{"account": a, "cents": c} for a, c in left]}
                ).decode("utf-8")
            }
            expected = {"totals": list(table.values())}
        else:

            def csv_text(rows):
                stream = io.StringIO(newline="")
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(["id", "cents"])
                writer.writerows(rows)
                return stream.getvalue()

            files = dict(zip(task.checker_inputs, (csv_text(left), csv_text(right)), strict=True))
            expected = reconciliation_candidate(left, right)
        return {"id": name, "group": group, "files": files, "expected": expected}

    if task.checker == "reconciliation-v2":
        development, evaluation = reconciliation_templates.generate_cases(task, seed, features)
    elif task.checker == "account-totals-v1":
        samples = {
            "normalization": [(" Fund_A ", amount), ("fund_a", 13), ("FUND-B", 9)],
            "signed-amounts": [("debit", -amount), ("debit", 17), ("credit", 31)],
            "cancellation": [("cancel", amount), ("CANCEL", -amount), ("zero", 0)],
            "duplicates": [("repeat", amount), ("repeat", amount), ("repeat", -7)],
            "empty": [],
            "integer-bounds": [("large", 1_000_000_000)] * 3 + [("low", -1_000_000_000)],
        }
        development = [
            case("dev-basic", "development-basic", [(" Shop ", 100), ("shop", -25)]),
            case("dev-separate", "development-separate", [("Rent", -80), ("Cash", 80)]),
        ]
        evaluation = [case("heldout-" + f, "evaluation-" + f, samples[f]) for f in features]
    else:
        samples = {
            "duplicates": ([("repeat", amount), ("repeat", -7)], [("repeat", 9)] * 2),
            "identifiers": ([("Case", amount), (" case ", 4)], [("case", 11), ("Case", 5)]),
            "one-sided": ([("left", -amount)], [("right", 23), ("zero", 0)]),
            "cancellation": ([("cancel", amount), ("cancel", -amount)], [("zero", 0)]),
            "empty": ([], []),
            "csv-quoting": (
                [("comma,id", amount), ('quote"id', -9)],
                [("line\nid", 8), ("café", 4)],
            ),
        }
        development = [
            case("dev-basic", "development-basic", [("shop", 100), ("shop", -25)], [("shop", 50)]),
            case("dev-separate", "development-separate", [("rent", -80)], [("cash", 80)]),
        ]
        evaluation = [case("heldout-" + f, "evaluation-" + f, *samples[f]) for f in features]
    material = FileMaterials(
        schema_version=2,
        task_id=task.id,
        brief="Build a reusable skill implementing the complete declared contract.",
        authorship="yassa deterministic synthetic generator",
        source=template_version(task.checker),
        synthetic=True,
        assumptions=(
            "Invented scenarios and accepted task rules; no claim of real-work coverage.",
            "Groups identify constructed scenarios, not independent sampled domains or briefs.",
        ),
        development=development,
        evaluation=evaluation,
    )
    validate_materials(task, material)
    return material


def template_version(family: str) -> str:
    return reconciliation_templates.VERSION if family == "reconciliation-v2" else VERSION


def verify_checker(task: TaskContract, material: FileMaterials) -> dict:
    """Verify references with an oracle and probe accepted alternatives and wrong outputs."""
    if task.checker not in FEATURES:
        raise ValueError("guided preparation requires an independent semantic oracle")
    validate_materials(task, material)
    if task.checker == "reconciliation-v2":
        return reconciliation_templates.verify_probes(task, material, check)
    records = []
    key = "totals" if task.checker == "account-totals-v1" else "balances"
    number = "net_cents" if key == "totals" else "delta_cents"
    for case in material.development + material.evaluation:
        alternative = copy.deepcopy(case.expected)
        alternative[key].reverse()
        probes = [
            ("reference", canonical(case.expected), 1),
            ("order-and-whitespace", json.dumps(alternative, indent=3).encode("utf-8"), 1),
            ("missing-schema", b"{}", 0),
            ("extra-field", canonical({**case.expected, "extra": 0}), 0),
        ]
        if case.expected[key]:
            for label, replacement in (
                ("wrong-value", case.expected[key][0][number] + 1),
                ("boolean-amount", True),
            ):
                wrong = copy.deepcopy(case.expected)
                wrong[key][0][number] = replacement
                probes.append((label, canonical(wrong), 0))
            missing = copy.deepcopy(case.expected)
            missing[key].pop()
            probes.append(("missing-record", canonical(missing), 0))
            duplicate = copy.deepcopy(case.expected)
            duplicate[key].append(duplicate[key][0])
            probes.append(("duplicate-record", canonical(duplicate), 0))
        else:
            extra = (
                {"account": "extra", "net_cents": 0, "count": 1}
                if key == "totals"
                else {"id": "extra", "left_cents": 0, "right_cents": 0, "delta_cents": 0}
            )
            probes.append(("invented-record", canonical({key: [extra]}), 0))
        for label, work, expected in probes:
            verdict = check(task.checker, work, case.expected)["value"]
            if verdict != expected:
                raise ValueError(f"checker calibration failed: {case.id}/{label}")
            records.append(
                {
                    "case": case.id,
                    "probe": label,
                    "work_sha256": digest(work),
                    "expected": expected,
                    "observed": verdict,
                }
            )
    return {
        "version": "guided-checker-verification-v1",
        "checker": task.checker,
        "references": "all recomputed by independent oracle",
        "splits": "disjoint IDs/groups and unique semantic inputs checked",
        "probes": records,
    }
