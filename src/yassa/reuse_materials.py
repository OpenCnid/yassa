"""Fresh synthetic histories for one brief under unchanged reconciliation-v2 rules.

The version names the recipe, not an independent task family or a sampled brief.
Frozen generated bundles belong outside the repository.
"""

import random
from collections import defaultdict

from .native_checkers import check
from .native_contracts import FileMaterials, validate_materials
from .reconciliation import input_identity, read_events, read_policy
from .reconciliation_templates import make_case, verify_probes
from .records import digest, identity

VERSION = "reconciliation-reuse-suite-v1"
PROFILES = ("compact", "interaction", "bulk")


def history_fingerprint(case, paths):
    """Conservative renamed-history screen in addition to exact semantic identity.

    Ignore literal event/account names but retain per-event revisions, currency,
    amount and state. This deliberately rejects some different tasks too; it is a
    construction screen, not a claim to decide arbitrary task equivalence.
    """
    policy = read_policy(case.files[paths[2]])
    sides = []
    for path in paths[:2]:
        events = defaultdict(set)
        for event, revision, _, currency, amount, state in read_events(case.files[path], policy):
            events[event].add((revision, currency, amount, state))
        sides.append(sorted(sorted(history) for history in events.values()))
    return identity([policy, sides])


def verify_history(task, material, historical):
    validate_materials(task, material)
    old_semantic, old_histories, old_rows = set(), set(), []
    for source in historical:
        if source.task_id != task.id:
            old_rows.append(
                {
                    "task_id": source.task_id,
                    "comparison": "different task contract",
                    "cases": len(source.development + source.evaluation),
                }
            )
            continue
        validate_materials(task, source)
        for case in source.development + source.evaluation:
            semantic = identity(input_identity(case.files, task.checker_inputs))
            history = history_fingerprint(case, task.checker_inputs)
            old_semantic.add(semantic)
            old_histories.add(history)
            old_rows.append(
                {
                    "task_id": source.task_id,
                    "case": case.id,
                    "semantic_id": semantic,
                    "history_id": history,
                }
            )
    if not old_semantic:
        raise ValueError(
            "reuse recipe requires historical reconciliation-v2 material for duplicate checks"
        )
    semantic_ids, history_ids, records = set(), set(), []
    for split, cases in (
        ("development", material.development),
        ("evaluation", material.evaluation),
    ):
        for case in cases:
            semantic = identity(input_identity(case.files, task.checker_inputs))
            history = history_fingerprint(case, task.checker_inputs)
            if semantic in old_semantic | semantic_ids or history in old_histories | history_ids:
                raise ValueError("duplicate semantic or renamed history in new/historical split")
            semantic_ids.add(semantic)
            history_ids.add(history)
            records.append(
                {
                    "split": split,
                    "case": case.id,
                    "semantic_id": semantic,
                    "history_id": history,
                    "file_sha256": {n: digest(t.encode()) for n, t in case.files.items()},
                }
            )
    return {
        "new": records,
        "historical": old_rows,
        "screen": (
            "exact semantic identity and conservative name-independent event-history fingerprint"
        ),
    }


def _construct(task, seed, name, split, profile):
    rng = random.Random(seed)
    # Policies vary by case; currency labels have no external financial meaning.
    policy = {
        "currencies": {
            "USD": {"scale": 2, "tolerance_minor": rng.randint(1, 5)},
            "JPY": {"scale": 0, "tolerance_minor": rng.randint(0, 2)},
            "KWD": {"scale": 3, "tolerance_minor": rng.randint(1, 7)},
        }
    }
    names = [f"{name}-acct-{n}" for n in range(rng.randint(4, 8))] + [
        " Case ",
        "case",
        'cafÃ©,"line\nitem',
    ]

    def amount(minor, currency):
        scale = policy["currencies"][currency]["scale"]
        sign = "-" if minor < 0 else ""
        n = abs(minor)
        return sign + (f"{n // 10**scale}.{n % 10**scale:0{scale}d}" if scale else str(n))

    count = (
        rng.randint(4, 8)
        if profile == "compact"
        else rng.randint(12, 18)
        if profile == "interaction"
        else rng.randint(58, 64)
    )
    sides = []
    for _side in range(2):
        rows = []
        for n in range(count):
            event = (
                f"{name}-event-{n}"  # Deliberately shared across sides; histories are independent.
            )
            revisions = sorted(
                rng.sample(
                    range(1, 40), rng.randint(1, 2) if profile == "compact" else rng.randint(2, 3)
                )
            )
            for revision in revisions:
                currency = rng.choice(list(policy["currencies"]))
                rows.append(
                    (
                        event,
                        revision,
                        rng.choice(names),
                        currency,
                        amount(rng.randint(-500000, 500000), currency),
                        "void" if rng.random() < 0.18 else "posted",
                    )
                )
            if n % 7 == 0:
                rows.append(rows[-1])
        sides.append(rows)
    # Distinct witness histories expose exact boundaries without changing semantics.
    left, right = sides
    n = rng.randint(10001, 99999)
    tol = policy["currencies"]["USD"]["tolerance_minor"]
    key = rng.choice(names)
    left.extend(
        [
            ("w-rekey", 2, names[0], "JPY", str(n), "posted"),
            ("w-rekey", 10, key, "USD", amount(n, "USD"), "posted"),
            ("w-rekey", 10, key, "USD", amount(n, "USD"), "posted"),
            ("w-void", 1, names[1], "USD", amount(n + 11, "USD"), "posted"),
            ("w-void", 13, names[2], "KWD", amount(n - 13, "KWD"), "void"),
            ("w-zero", 1, name + "-zero", "USD", "0", "posted"),
            ("w-boundary", 1, name + "-tolerance", "USD", amount(n, "USD"), "posted"),
            (
                "w-large",
                1,
                name + "-large",
                "USD",
                amount(9007199254740993 + rng.randint(1, 9999), "USD"),
                "posted",
            ),
        ]
    )
    right.extend(
        [
            ("w-boundary", 1, name + "-tolerance", "USD", amount(n - tol, "USD"), "posted"),
            ("w-rekey", 1, key, "USD", amount(n + 1, "USD"), "posted"),
        ]
    )
    for rows in sides:
        rng.shuffle(rows)
    case = make_case(task, name, f"{split}-{profile}", *sides, policy)
    return case, {
        "case": name,
        "split": split,
        "profile": profile,
        "seed": seed,
        "lineage": f"{VERSION}/{split}/{profile}/{name}",
        "rows": sum(map(len, sides)),
        "selection": "eligible and retained; no subject outcomes observed",
    }


def generate_reuse_suite(task, seed, historical):
    if task.checker != "reconciliation-v2":
        raise ValueError("reuse recipe requires reconciliation-v2")
    development, evaluation, ledger = [], [], []
    for split, count, output in (("development", 1, development), ("evaluation", 2, evaluation)):
        for profile in PROFILES:
            for n in range(1, count + 1):
                name = f"reuse-{split}-{profile}-{n}"
                case_seed = int(identity([VERSION, seed, name])[:16], 16)
                case, record = _construct(
                    task, case_seed, name, split, profile if split == "evaluation" else "compact"
                )
                output.append(case)
                ledger.append(record)
    material = FileMaterials(
        schema_version=2,
        task_id=task.id,
        brief=task.requirements,
        authorship="Yassa agent-authored deterministic synthetic recipe",
        source=VERSION,
        synthetic=True,
        assumptions=(
            "One constructed brief with shared template ancestry; "
            "seeds are not independent briefs.",
            "Equal weighting of six cases: two per compact/interaction/bulk profile; "
            "no production-frequency claim.",
            "Discovery study informed recipe selection; preparation authors see validation cases.",
        ),
        development=development,
        evaluation=evaluation,
    )
    split_check = verify_history(task, material, historical)
    probes = verify_probes(task, material, check)
    return material, {
        "version": VERSION,
        "seed": seed,
        "authorship": material.authorship,
        "contract": task.checker,
        "contract_sha256": digest(task.requirements.encode()),
        "ancestry": (
            "reconciliation-event-suite-v1 rule families; "
            "freshly constructed event histories and values"
        ),
        "independent_briefs": 1,
        "profile_weights": {p: "1/3" for p in PROFILES},
        "selection_ledger": ledger,
        "splits": split_check,
        "verification": probes,
    }
