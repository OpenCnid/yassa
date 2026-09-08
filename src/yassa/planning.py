"""Pure fixed-plan enumeration. Builds and their dependent uses stay distinct."""

from .records import identity
from .study import Materials, Study


def make_plan(study: Study, materials: dict[str, Materials], study_id: str) -> dict:
    trials = []

    def add(role, condition, arm, case=None, build=None, repeat=None, parent=None):
        dimensions = {
            "role": role,
            "condition": condition.id,
            "arm": arm.id,
            "case": case.id if case else None,
            "group": case.group if case else None,
            "build": build,
            "repeat": repeat,
            "parent_build": parent,
        }
        trial_id = role + "-" + identity(dimensions)[:20]
        trials.append({"id": trial_id, **dimensions})
        return trial_id

    for condition in study.conditions:
        for arm in study.arms:
            if "direct" in study.kinds:
                for case in materials[condition.id].evaluation:
                    for repeat in range(1, study.execution_repeats + 1):
                        add("direct", condition, arm, case=case, repeat=repeat)
            if "builder" in study.kinds:
                for build in range(1, study.builds_per_arm + 1):
                    parent = add("build", condition, arm, build=build)
                    for case in materials[condition.id].evaluation:
                        for repeat in range(1, study.execution_repeats + 1):
                            add(
                                "consumer",
                                condition,
                                arm,
                                case=case,
                                build=build,
                                repeat=repeat,
                                parent=parent,
                            )
    phases = {"direct": 0, "build": 1, "consumer": 2}
    trials.sort(
        key=lambda trial: (phases[trial["role"]], identity([study.schedule_seed, trial["id"]]))
    )
    # Conservative admission includes every permitted infrastructure retry, before any calls.
    reserved_attempts = len(trials) * (1 + study.limits.infrastructure_retries)
    if reserved_attempts > study.limits.max_attempts:
        raise ValueError(
            f"plan reserves {reserved_attempts} attempts, exceeding max_attempts "
            f"{study.limits.max_attempts}"
        )
    body = {
        "schema_version": 1,
        "planner": "fixed-plan-v1",
        "study_id": study_id,
        "schedule": "direct then build then consumer; seeded hash order within each phase",
        "seed": study.schedule_seed,
        "trials": trials,
        "reserved_attempts": reserved_attempts,
        "denominator": "all planned direct/consumer uses; failed builds contribute zero; "
        "infrastructure failures remain missing; no missing-value imputation",
        "selection": "first non-infrastructure attempt; no task-failure retries",
    }
    return {"id": identity(body), **body}
