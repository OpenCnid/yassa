"""Opt-in, outcome-independent allocation ordering; trial identities are unchanged."""

from collections import Counter, defaultdict

from .records import identity


def block_schedule(trials, seed):
    def ordered(values, label):
        return sorted(values, key=lambda v: identity([seed, label, v]))

    builds = [t for t in trials if t["role"] == "build"]
    queues = {}
    for t in builds:
        queues.setdefault(t["arm"], []).append(t)
    queues = {a: ordered(q, "builds") for a, q in queues.items()}
    build_order = []
    round_number = 0
    while any(queues.values()):
        for arm in ordered(list(queues), ["build-round", round_number]):
            if queues[arm]:
                build_order.append(queues[arm].pop())
        round_number += 1
    blocks = defaultdict(list)
    for t in trials:
        if t["role"] == "consume":
            blocks[t["condition"], t["case"], t["repeat"]].append(t)
    counts, frozen_blocks, output = {}, [], list(build_order)
    for key in ordered(list(blocks), "blocks"):
        members = blocks[key]
        arms = Counter(t["arm"] for t in members)
        signature = identity([key[0], sorted(arms.items())])
        positions = counts.setdefault(signature, {a: [0] * len(members) for a in arms})
        # Seeded interleaved ring and every rotation. Greedily choose the rotation
        # minimizing accumulated squared arm-position counts; ties are seeded.
        ring = []
        for n in range(max(arms.values())):
            ring.extend(a for a in ordered(list(arms), ["ring", signature]) if arms[a] > n)
        candidates = [ring[n:] + ring[:n] for n in range(len(ring))]

        def imbalance(order, positions=positions):
            return sum(2 * positions[a][p] + 1 for p, a in enumerate(order))

        chosen = min(candidates, key=lambda order: (imbalance(order), identity([seed, key, order])))
        available = {
            a: ordered([t for t in members if t["arm"] == a], ["members", key]) for a in arms
        }
        block = []
        for p, arm in enumerate(chosen):
            positions[arm][p] += 1
            block.append(available[arm].pop())
        frozen_blocks.append(
            {
                "condition": key[0],
                "case": key[1],
                "repeat": key[2],
                "trial_ids": [t["id"] for t in block],
                "arms": chosen,
            }
        )
        output.extend(block)
    return output, {
        "version": "case-repeat-blocks-v1",
        "seed": seed,
        "build_order": [t["id"] for t in build_order],
        "blocks": frozen_blocks,
        "arm_position_counts": counts,
        "balance_method": (
            "seeded interleaved ring rotations; greedy squared position counts; no outcome input"
        ),
        "execution": "serial; full admitted allocation retained on dependency failure",
    }
