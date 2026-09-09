"""Versioned, descriptive resource interpretation of sealed native v2 evidence.

Never rescores outputs or changes a previous interpretation. Time means native
command start to return/cancellation, not time to first correct output.
"""

import math
from collections import Counter
from pathlib import Path
from statistics import mean

from .evidence import EvidenceStore, read_regular, verify_run, write_new
from .native import native_usage
from .native_capture import recorded_native_files
from .records import canonical, digest, parse_json

VERSION = "native-resource-interpretation-v1"


def usage_evidence(files: dict[str, bytes]) -> dict:
    """Deduplicate response records within a root; retain session/child lineage."""
    sessions, calls = [], {}
    for path, data in sorted(files.items()):
        if not path.startswith("sessions/"):
            continue
        rows = [parse_json(line) for line in data.splitlines() if line.strip()]
        meta = [r["payload"] for r in rows if r.get("type") == "session_meta"]
        if len(meta) != 1:
            raise ValueError("missing or ambiguous session metadata")
        source = meta[0].get("source")
        parent = (
            source.get("subagent", {}).get("thread_spawn", {}).get("parent_thread_id")
            if isinstance(source, dict)
            else None
        )
        session = {"path": path, "id": meta[0]["id"], "parent": parent, "response_ids": []}
        for row in rows:
            if row.get("type") != "token_usage_record":
                continue
            payload = row["payload"]
            rid, usage = payload["response_id"], payload["usage"]
            if any(type(v) is not int or v < 0 for v in usage.values()):
                raise ValueError("invalid native token usage")
            if rid in calls and calls[rid] != usage:
                raise ValueError("conflicting duplicate response usage")
            calls[rid] = usage
            session["response_ids"].append(rid)
        session["response_ids"] = sorted(set(session["response_ids"]))
        sessions.append(session)
    ids = [s["id"] for s in sessions]
    if not sessions or len(ids) != len(set(ids)) or sum(s["parent"] is None for s in sessions) != 1:
        raise ValueError("expected one root and distinct recorded sessions")
    if any(s["parent"] is not None and s["parent"] not in ids for s in sessions):
        raise ValueError("missing recorded parent session")
    if not calls:
        raise ValueError("native response usage unavailable")
    totals = {
        k: sum(u.get(k, 0) for u in calls.values())
        for k in sorted({k for u in calls.values() for k in u})
    }
    legacy = native_usage(files)
    if totals != legacy["totals"] or len(calls) != legacy["native_usage_records"]:
        raise ValueError("native usage reconciliation failed")
    return {
        "sessions": sessions,
        "responses": calls,
        "totals": totals,
        "native_usage_records": len(calls),
        "tool_calls": legacy["tool_calls"],
        "accounting": "root inclusive; each response ID once; session totals are not added",
    }


def complete_mean(values):
    return mean(values) if values and all(v is not None for v in values) else None


def coverage(rows):
    consumers = [r for r in rows if r["role"] == "consume"]
    return {
        "planned": len(rows),
        "launched": sum(r["launched"] for r in rows),
        "correctness_planned": len(consumers),
        "passed": sum(r["value"] == 1 for r in consumers),
        "failed": sum(r["value"] == 0 for r in consumers),
        "missing": sum(r["value"] is None for r in consumers),
        "timeouts": sum(r["native_status"] == "budget_exhausted" for r in rows),
        "timeout_status_unavailable": sum(
            r["launched"] and r["native_status"] is None for r in rows
        ),
        "duration_unavailable": sum(r["seconds"] is None for r in rows),
        "usage_unavailable": sum(r["launched"] and r["usage"].get("totals") is None for r in rows),
    }


def interpret_resources(plan, results, raw, scores, usage, *, horizons=(1, 5, 20, 50), primary=20):
    if (
        not horizons
        or len(set(horizons)) != len(horizons)
        or primary not in horizons
        or any(type(h) is not int or h < 1 for h in horizons)
    ):
        raise ValueError("declare distinct positive reuse horizons including the primary")
    trials = plan["trials"]
    ids = {t["id"] for t in trials}
    if len(ids) != len(trials) or set(results) - ids or set(raw) - ids or set(usage) - ids:
        raise ValueError("mismatched attempt allocation")
    parents = {t["id"]: t for t in trials if t["role"] == "build"}
    if any(t["parent"] is not None and t["parent"] not in parents for t in trials):
        raise ValueError("unknown build parent")
    score_map = {s["id"]: s for s in scores}
    if len(score_map) != len(scores) or set(score_map) - {
        t["id"] for t in trials if t["role"] == "consume"
    }:
        raise ValueError("mismatched scores")
    rows, seen_responses = [], set()
    for t in trials:
        rid = t["id"]
        result, attempt, score = results.get(rid, {}), raw.get(rid), score_map.get(rid)
        issues = []
        launched = result.get("launched", attempt is not None)
        if bool(launched) != (attempt is not None):
            issues.append("launch/raw evidence mismatch")
        if attempt is not None and attempt.get("resource_catalog_status") is False:
            issues.append("recorded catalog acceptance unavailable or failed")
        seconds = attempt.get("duration_seconds") if attempt is not None else None
        if seconds is not None and (
            type(seconds) not in (float, int) or not math.isfinite(seconds) or seconds < 0
        ):
            raise ValueError("invalid native duration")
        if result.get("duration_seconds") != seconds:
            issues.append("result/raw duration mismatch")
        if score:
            if any(
                score.get(k) != t[k]
                for k in ("condition", "arm", "build", "case", "repeat", "parent")
            ):
                raise ValueError("score lineage mismatch")
            if score.get("value") is not None and (
                type(score["value"]) is not int or score["value"] not in (0, 1)
            ):
                raise ValueError("invalid correctness score")
            if score.get("status") != result.get("status"):
                issues.append("score/result status mismatch")
        tokens = usage.get(rid, {"unavailable": "no recorded response usage"})
        response_ids = set(tokens.get("responses", {}))
        if seen_responses & response_ids:
            raise ValueError("response ID reused across root attempts")
        seen_responses.update(response_ids)
        native_status = (attempt or {}).get("native_status", (attempt or {}).get("status"))
        rows.append(
            {
                **t,
                "launched": bool(launched),
                "status": result.get("status", "missing_result"),
                "native_status": native_status,
                "seconds": seconds,
                "value": score.get("value") if score else None,
                "usage": tokens,
                "issues": issues,
                "lifecycle": (attempt or {}).get(
                    "lifecycle", {"unavailable": "not recorded by this adapter version"}
                ),
            }
        )
    builds, baselines = [], []

    def use_summary(selected):
        cases = []
        for case in sorted({r["case"] for r in selected}):
            members = [r for r in selected if r["case"] == case]
            cases.append(
                {
                    "case": case,
                    "group": members[0]["group"],
                    "seconds": complete_mean([r["seconds"] for r in members]),
                    "coverage": coverage(members),
                    "attempt_ids": [r["id"] for r in members],
                }
            )
        return {
            "seconds": complete_mean([c["seconds"] for c in cases]),
            "coverage": coverage(selected),
            "cases": cases,
        }

    for condition in sorted({r["condition"] for r in rows}):
        selected = [
            r
            for r in rows
            if r["condition"] == condition and r["role"] == "consume" and r["parent"] is None
        ]
        if selected:
            if (
                any(r["build"] is not None for r in selected)
                or len({r["arm"] for r in selected}) != 1
            ):
                raise ValueError("baseline must have null build/parent lineage")
            summary = use_summary(selected)
            baselines.append(
                {
                    "condition": condition,
                    "arm": selected[0]["arm"],
                    "build": None,
                    "parent": None,
                    "build_seconds": 0,
                    **summary,
                    "curves": {
                        str(h): h * summary["seconds"] if summary["seconds"] is not None else None
                        for h in horizons
                    },
                }
            )
        baseline = baselines[-1] if selected else None
        baseline_rows = selected
        for build in [r for r in rows if r["role"] == "build" and r["condition"] == condition]:
            consumers = [r for r in rows if r["parent"] == build["id"]]
            if any(
                (r["condition"], r["arm"], r["build"]) != (condition, build["arm"], build["build"])
                for r in consumers
            ):
                raise ValueError("consumer parent lineage mismatch")
            summary = use_summary(consumers)
            b, t = build["seconds"], summary["seconds"]
            reasons = []
            if build["status"] != "package_ready":
                reasons.append("package not accepted")
            if not consumers or any(r["value"] != 1 for r in consumers):
                reasons.append("incorrect or missing package uses")
            if baseline is None or not baseline_rows or any(r["value"] != 1 for r in baseline_rows):
                reasons.append("incorrect or missing baseline uses")
            if any(
                r["issues"] or (r["launched"] and r["native_status"] is None)
                for r in [build, *consumers, *baseline_rows]
            ):
                reasons.append("unreconciled attempt evidence")
            if b is None or t is None or baseline is None or baseline["seconds"] is None:
                reasons.append("incomplete durations")
            paired = []
            for case in summary["cases"]:
                other = next(
                    (c for c in (baseline or {}).get("cases", []) if c["case"] == case["case"]),
                    None,
                )
                paired.append(
                    {
                        "case": case["case"],
                        "package_seconds": case["seconds"],
                        "baseline_seconds": other["seconds"] if other else None,
                        "difference_seconds": case["seconds"] - other["seconds"]
                        if other and case["seconds"] is not None and other["seconds"] is not None
                        else None,
                        "baseline_attempt_ids": other["attempt_ids"] if other else [],
                    }
                )
            if baseline and {c["case"] for c in summary["cases"]} != {
                c["case"] for c in baseline["cases"]
            }:
                reasons.append("case coverage mismatch")
            saving = (
                baseline["seconds"] - t
                if baseline and baseline["seconds"] is not None and t is not None
                else None
            )
            crossover = b / saving if not reasons and saving is not None and saving > 0 else None
            builds.append(
                {
                    "id": build["id"],
                    "condition": condition,
                    "arm": build["arm"],
                    "build": build["build"],
                    "build_seconds": b,
                    "build_status": build["status"],
                    "build_native_status": build["native_status"],
                    **summary,
                    "paired_cases": paired,
                    "qualification_reasons": reasons,
                    "qualified": not reasons,
                    "crossover_uses": crossover,
                    "crossover_status": "unqualified"
                    if reasons
                    else "finite"
                    if crossover is not None
                    else "no_positive_saving",
                    "curves": {
                        str(h): b + h * t if b is not None and t is not None else None
                        for h in horizons
                    },
                    "baseline_differences": {
                        str(h): b + h * t - baseline["curves"][str(h)]
                        if b is not None
                        and t is not None
                        and baseline
                        and baseline["seconds"] is not None
                        else None
                        for h in horizons
                    },
                }
            )
    arms = []
    for condition, arm in sorted({(b["condition"], b["arm"]) for b in builds}):
        selected = [b for b in builds if (b["condition"], b["arm"]) == (condition, arm)]
        arms.append(
            {
                "condition": condition,
                "arm": arm,
                "independent_builds": len(selected),
                "qualified_builds": sum(b["qualified"] for b in selected),
                "build_timeouts": sum(
                    b["build_native_status"] == "budget_exhausted" for b in selected
                ),
                "consumer_coverage": coverage(
                    [
                        r
                        for r in rows
                        if r["role"] == "consume" and (r["condition"], r["arm"]) == (condition, arm)
                    ]
                ),
                "curves": {
                    str(h): {
                        "mean": complete_mean([b["curves"][str(h)] for b in selected]),
                        "range": [
                            min(b["curves"][str(h)] for b in selected),
                            max(b["curves"][str(h)] for b in selected),
                        ]
                        if all(b["curves"][str(h)] is not None for b in selected)
                        else None,
                    }
                    for h in horizons
                },
                "baseline_differences": {
                    str(h): complete_mean([b["baseline_differences"][str(h)] for b in selected])
                    for h in horizons
                },
            }
        )
    research = []
    for role, condition, arm in sorted({(r["role"], r["condition"], r["arm"]) for r in rows}):
        selected = [
            r for r in rows if (r["role"], r["condition"], r["arm"]) == (role, condition, arm)
        ]
        totals = Counter()
        for row in selected:
            totals.update(row["usage"].get("totals", {}))
        research.append(
            {
                "role": role,
                "condition": condition,
                "arm": arm,
                "coverage": coverage(selected),
                "statuses": dict(Counter(r["status"] for r in selected)),
                "observed_native_seconds": sum(
                    r["seconds"] for r in selected if r["seconds"] is not None
                ),
                "recorded_token_totals": dict(totals),
            }
        )
    return {
        "version": VERSION,
        "plan_id": plan["id"],
        "primary_horizon": primary,
        "horizons": list(horizons),
        "attempts": rows,
        "builds": builds,
        "baselines": baselines,
        "arms": arms,
        "research": research,
        "observed_research_native_seconds": sum(
            r["seconds"] for r in rows if r["seconds"] is not None
        ),
        "limits": [
            "Descriptive extrapolation B + H*T; repeats within case, then equal cases and builds.",
            "Baseline evidence is shared, not independent for each package contrast.",
            "Missing durations suppress complete means; observed sums are partial expenditure.",
            "Wrong work retains consumed resources and never qualifies a crossover.",
            "Input includes cache; output includes reasoning; children belong to roots.",
            "Recorded usage can omit aborted requests; unavailable is not zero. No dollar metric.",
        ],
    }


def write_resource_interpretation(root: Path, source_label: str, destination: Path) -> Path:
    from .app import external_root, procedure_files
    from .evidence import safe_name
    from .native_runner import load_native_v2

    safe_name(source_label)
    if "/" in source_label:
        raise ValueError("score label must be one path component")
    destination = external_root(destination)
    if destination.is_relative_to(root.resolve()):
        raise ValueError("resource interpretation must be outside the preserved run")
    seal = verify_run(root)
    frozen, plan, study, _ = load_native_v2(root)
    score_bytes = read_regular(root / "interpretations" / source_label / "scores.json")
    score_record = parse_json(score_bytes)
    if any(
        score_record.get(k) != v
        for k, v in {"run_seal": seal, "study_id": frozen["id"], "plan_id": plan["id"]}.items()
    ):
        raise ValueError("score interpretation identity mismatch")
    result_record = parse_json(read_regular(root / "results.json"))
    if result_record.get("study_id") != frozen["id"] or result_record.get("plan_id") != plan["id"]:
        raise ValueError("result identity mismatch")
    raw, usage = {}, {}
    store = EvidenceStore(root)
    for trial in plan["trials"]:
        rid = trial["id"]
        path = root / "attempts" / rid / "result.json"
        if path.is_file():
            raw[rid] = parse_json(read_regular(path))
            raw[rid]["resource_catalog_status"] = all(
                raw[rid].get(key) and store.json(raw[rid][key], "check.json").get("passed") is True
                for key in ("preflight_check_id", "catalog_check_id")
            )
        try:
            usage[rid] = usage_evidence(recorded_native_files(store, raw.get(rid, {})))
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            usage[rid] = {"unavailable": str(error)}
    scenarios = study.resource_scenarios
    report = interpret_resources(
        plan,
        result_record["trials"],
        raw,
        score_record["scores"],
        usage,
        **({"horizons": scenarios.horizons, "primary": scenarios.primary} if scenarios else {}),
    )
    report.update(
        run_seal=seal,
        score_sha256=digest(score_bytes),
        scorer=score_record["scorer"],
        scenario_origin="frozen study" if scenarios else "post hoc default scenarios",
        interpreter_files={n: digest(b) for n, b in procedure_files().items()},
    )
    destination.mkdir(parents=True, exist_ok=False)
    write_new(destination / "resources.json", canonical(report))
    lines = [
        "# Descriptive package resource interpretation",
        "",
        f"Version: `{VERSION}`. Plan: `{plan['id']}`.",
        "",
        f"Observed research native time: {report['observed_research_native_seconds']:.3f} seconds. "
        "Partial sums retain missingness in resources.json.",
        "",
        "| Condition | Arm | Build | Build seconds | Mean use seconds | Consumer timeouts | "
        "Crossover uses | Qualification |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for b in report["builds"]:
        lines.append(
            f"| {b['condition']} | {b['arm']} | {b['build']} | {b['build_seconds']} "
            f"({b['build_native_status']}) | {b['seconds']} | {b['coverage']['timeouts']} | "
            f"{b['crossover_uses']} | {b['crossover_status']}: "
            f"{', '.join(b['qualification_reasons'])} |"
        )
    lines += [
        "",
        "All attempts, baseline zero-build curves, equal-build arm means/ranges, paired cases, "
        "usage and missingness are in [resources.json](resources.json).",
        "",
        *[f"- {v}" for v in report["limits"]],
    ]
    write_new(destination / "report.md", ("\n".join(lines) + "\n").encode())
    return destination / "report.md"
