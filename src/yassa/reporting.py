"""Descriptive counts and rendering from explicit recorded score selections."""

from collections import Counter


def summarize(scores: list[dict], results: dict, attempts: list[dict]) -> dict:
    groups = {}
    for score in scores:
        key = (score["condition"], score["role"], score["arm"])
        row = groups.setdefault(
            key,
            {
                "condition": key[0],
                "role": key[1],
                "arm": key[2],
                "planned": 0,
                "executed": 0,
                "successes": 0,
                "task_failures": 0,
                "dependency_failures": 0,
                "missing": 0,
            },
        )
        row["planned"] += 1
        row["executed"] += score["attempt_id"] is not None
        row["successes"] += score["value"] == 1
        row["task_failures"] += score["value"] == 0 and score["status"] != "dependency_failed"
        row["dependency_failures"] += score["status"] == "dependency_failed"
        row["missing"] += score["value"] is None
    build_counts = Counter(
        result["status"] for result in results.values() if result["role"] == "build"
    )
    durations = [attempt["usage"]["duration_seconds"] for attempt in attempts]
    return {
        "method": "descriptive-v1",
        "rows": [groups[key] for key in sorted(groups)],
        "builds": dict(sorted(build_counts.items())),
        "attempts": len(attempts),
        "attempt_statuses": dict(Counter(attempt["status"] for attempt in attempts)),
        "usage": {
            "provider_calls": sum(a["usage"]["provider_calls"] for a in attempts),
            "internal_calls": sum(a["usage"]["internal_calls"] for a in attempts),
            "tool_calls": sum(a["usage"]["tool_calls"] for a in attempts),
            "duration_seconds": round(sum(d or 0 for d in durations), 6),
            "missing_durations": sum(d is None for d in durations),
            "model_tokens": None,
            "cost_usd": None,
        },
        "aggregation": "Separate preparation conditions and execution roles; no pooled estimate",
        "uncertainty": "Not estimated; fixed synthetic fixtures and deterministic simulated actors",
    }


def render_report(
    frozen: dict,
    plan: dict,
    score_record: dict,
    summary: dict,
    results: dict,
    attempts: list[dict],
) -> str:
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")

    lines = [
        "# Yassa synthetic fixture report",
        "",
        "**Simulation only.** These results test the harness; they do not measure Dovetail "
        "or any real builder, model, or native CLI skill-loading behavior.",
        "",
        cell(frozen["study"]["question"]),
        "",
        "The checker requires every account total and row count to be correct. "
        "Each row reports confirmed successes out of all planned uses. Failed builds "
        "contribute zero for their planned consumers. Infrastructure failures remain "
        "explicitly missing and are not imputed as incorrect work.",
        "",
        "| Input condition | Stage | Arm | Success / planned | Executed uses | Task failures "
        "| Failed dependencies | Missing |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    routes = {c["id"]: c["route"] for c in frozen["study"]["conditions"]}
    for row in summary["rows"]:
        lines.append(
            f"| {cell(row['condition'])} ({routes[row['condition']]}) | {row['role']} | "
            f"{cell(row['arm'])} | {row['successes']} / {row['planned']} | "
            f"{row['executed']} | {row['task_failures']} | "
            f"{row['dependency_failures']} | {row['missing']} |"
        )
    lines += [
        "",
        f"Build dispositions: {cell(summary['builds'])}. "
        f"Actual attempts, including retries: {summary['attempts']}; "
        f"reserved maximum: {plan['reserved_attempts']}.",
        "",
        f"Resource use: {summary['usage']['provider_calls']} simulated provider calls, "
        f"{summary['usage']['tool_calls']} tool calls, "
        f"{summary['usage']['internal_calls']} internal calls, "
        f"{summary['usage']['duration_seconds']:.3f} recorded attempt seconds. "
        "Model token counts and monetary costs are unavailable/not applicable to this simulation. "
        "The configured output cap uses UTF-8 byte units in the fixture provider; "
        "Inspect enforces the per-sample time limit. "
        "These are not live-provider budget measurements.",
        "",
        "All scenario rules are synthetic. Prepared cases use the recorded seed and "
        "generator; supplied fixture originals are preserved byte for byte. Preparation "
        "conditions have separate results; differences between them do not estimate preparation's "
        "effect. Repeats and downstream uses of one build are not independent builder samples. "
        "No confidence interval, equivalence claim, or population ranking is supported.",
        "",
        f"Study revision: `{frozen['id']}`. Plan: `{plan['id']}`. "
        f"Scorer: `{score_record['scorer']['version']}` / `{score_record['scorer']['id']}`.",
        "",
        "Evidence: [frozen study](../../study.json), [plan](../../plan.json), "
        "[run selection](../../results.json), [run seal](../../run-seal.json), "
        "[scores](scores.json), [analysis](analysis.json). "
        "Attempt records below link to input bindings, submitted work, and original Inspect logs.",
        "",
        "## Conditions",
        "",
    ]
    for condition in frozen["conditions"]:
        lines += [
            f"- **{cell(condition['id'])}**: {cell(condition['provenance']['route'])}; "
            "[verified cases]"
            f"(../../artifacts/{condition['materials_id']}/files/materials.json), "
            f"[original input](../../artifacts/{condition['original_id']}/files/original.json)."
        ]
    lines += [
        "",
        "## Recorded uses",
        "",
        "| Trial | Execution status | Score | Selected attempt | Work | Check result |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for score in score_record["scores"]:
        attempt = (
            f"[record](../../attempts/{score['attempt_id']}/result.json)"
            if score["attempt_id"]
            else "none (dependency disposition)"
        )
        work = (
            f"[response](../../artifacts/{score['output_id']}/files/response.txt)"
            if score["output_id"]
            else "none"
        )
        lines.append(
            f"| {score['trial_id']} | {score['status']} | "
            f"{score['value'] if score['value'] is not None else 'missing'} | {attempt} | {work} | "
            f"{cell(score['reason'])} |"
        )
    lines += [
        "",
        "## Builds",
        "",
        "| Trial | Disposition | Frozen package | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for trial_id, result in results.items():
        if result["role"] != "build":
            continue
        package = (
            f"[manifest](../../artifacts/{result['package_id']}/manifest.json)"
            if result["package_id"]
            else "none"
        )
        lines.append(
            f"| {trial_id} | {result['status']} | {package} | {cell(result['reason'] or '')} |"
        )
    lines += [
        "",
        "## Attempt evidence, including retries",
        "",
        "| Attempt | Status | Input binding | Inspect log |",
        "| --- | --- | --- | --- |",
    ]
    for attempt in attempts:
        lines.append(
            f"| [record](../../attempts/{attempt['id']}/result.json) | {attempt['status']} | "
            f"[binding](../../artifacts/{attempt['binding_id']}/files/binding.json) | "
            f"[log](../../{attempt['inspect']['log']}) |"
        )
    lines += [
        "",
        "Regenerate this interpretation without model calls with "
        "`uv run yassa rescore RUN_DIRECTORY --label another-score`. "
        "Use `uv run yassa verify RUN_DIRECTORY` to check sealed evidence. "
        "Existing attempts, scores, and reports are never overwritten.",
        "",
    ]
    return "\n".join(lines)
