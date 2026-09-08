"""Both fixture preparation routes converge on the same validated materials."""

import random
from pathlib import Path

from .evidence import read_regular
from .records import canonical, digest, parse_json
from .scoring import check_work, reference_totals
from .study import Condition, Materials

GENERATOR_VERSION = "synthetic-account-totals-v1"


def intake(request: dict) -> dict:
    """Focused readiness feedback for the limited synthetic template."""
    questions = []
    if not request.get("question"):
        questions.append("What comparison should this trial help you make?")
    if request.get("scope") != "synthetic-fixture":
        questions.append("May this trial use explicitly invented account-total rules and cases?")
    if not request.get("conditions") and len(questions) < 2:
        questions.append("Will you supply synthetic materials, or should Yassa prepare them?")
    return {
        "status": "needs_input" if questions else "ready_for_validation",
        "questions": questions[:2],
        "supported_template": "account-totals-v1",
    }


def generate_materials(condition: Condition) -> dict:
    rng = random.Random(condition.seed)

    def case(case_id: str, group: str, rows: list[dict]) -> dict:
        # Generator's answer candidate uses a separate incremental implementation.
        totals = {}
        for row in rows:
            name = row["account"].strip().lower()
            total = totals.setdefault(name, {"account": name, "net_cents": 0, "count": 0})
            total["net_cents"] += row["cents"]
            total["count"] += 1
        return {"id": case_id, "group": group, "rows": rows, "expected": list(totals.values())}

    development = [
        case(
            "dev-example",
            "development",
            [{"account": " Shop ", "cents": 100}, {"account": "shop", "cents": -25}],
        )
    ]
    evaluation = []
    for index in range(condition.evaluation_cases):
        amount = rng.randint(200, 5000)
        rows = [
            {"account": f" Account_{index} ", "cents": amount},
            {"account": f"account_{index}", "cents": -rng.randint(1, amount)},
            {"account": "RESERVE", "cents": 0},
        ]
        evaluation.append(case(f"heldout-{index + 1}", f"evaluation-{index + 1}", rows))
    return {
        "schema_version": 1,
        "brief": "Build reusable instructions for the declared account-total contract.",
        "authorship": "yassa deterministic synthetic generator",
        "source": GENERATOR_VERSION,
        "synthetic": True,
        "assumptions": [
            "Invented ledger scenarios; no representation of real user work.",
            "The account-totals-v1 contract defines all scenario rules.",
        ],
        "development": development,
        "evaluation": evaluation,
    }


def prepare_condition(condition: Condition, study_directory: Path) -> tuple[Materials, dict, bytes]:
    if condition.route == "user-supplied":
        source = Path(condition.source_path)
        if not source.is_absolute():
            source = study_directory / source
        original = read_regular(source)
        if digest(original) != condition.source_sha256:
            raise ValueError(f"source hash mismatch for condition {condition.id}")
        material = parse_json(original)
        provenance = {
            "route": condition.route,
            "source_path": str(source.absolute()),
            "original_sha256": digest(original),
            "preparation": "validated-copy-v1",
        }
    else:
        original = canonical(condition.model_dump(mode="json"))
        material = generate_materials(condition)
        provenance = {
            "route": condition.route,
            "request": condition.request,
            "generator": GENERATOR_VERSION,
            "model": None,
            "seed": condition.seed,
            "parameters": {"evaluation_cases": condition.evaluation_cases},
            "selection": "all generated cases; no outcome-based selection",
            "original_sha256": digest(original),
        }
    materials = Materials.model_validate(material)
    for case in materials.development + materials.evaluation:
        rows = [row.model_dump() for row in case.rows]
        verdict = check_work(
            canonical({"totals": [total.model_dump() for total in case.expected]}),
            reference_totals(rows),
        )
        if not verdict["value"]:
            raise ValueError(f"invalid reference for {condition.id}/{case.id}: {verdict['reason']}")
    provenance.update(
        {
            "authorship": materials.authorship,
            "source": materials.source,
            "synthetic": materials.synthetic,
            "assumptions": materials.assumptions,
            "verification": "independent deterministic oracle; all cases checked",
        }
    )
    return materials, provenance, original
