import copy

import pytest

from yassa.native_resources import interpret_resources, usage_evidence
from yassa.records import canonical


def fixture():
    trials, results, raw, scores = [], {}, {}, []
    for build, cost in ((1, 100), (2, 200)):
        t = dict(
            id=f"b{build}",
            role="build",
            condition="prepared",
            arm="package",
            build=build,
            parent=None,
            case=None,
            group=None,
            repeat=None,
        )
        trials.append(t)
        raw[t["id"]] = dict(status="completed", duration_seconds=cost)
        results[t["id"]] = dict(status="package_ready", launched=True, duration_seconds=cost)
    # Unequal repeat counts expose accidental use-weighting: case means are 10/30;
    # baseline 30/50; equal-case saving 20, B=100 => crossover 5 uses.
    for build in (1, 2, None):
        for case, count, time in (("compact", 1, 10), ("bulk", 3, 30)):
            for repeat in range(count):
                rid = f"u{build}-{case}-{repeat}"
                t = dict(
                    id=rid,
                    role="consume",
                    condition="prepared",
                    arm="baseline" if build is None else "package",
                    build=build,
                    parent=f"b{build}" if build else None,
                    case=case,
                    group=case,
                    repeat=repeat + 1,
                )
                trials.append(t)
                duration = time + (20 if build is None else 0)
                raw[rid] = dict(status="completed", duration_seconds=duration)
                results[rid] = dict(raw[rid], launched=True)
                scores.append(dict(t, value=1, status="completed"))
    return dict(
        plan={"id": "frozen", "trials": trials}, results=results, raw=raw, scores=scores, usage={}
    )


def test_equal_case_and_build_weights_and_separate_research_expenditure():
    report = interpret_resources(**fixture())
    a, b = report["builds"]
    assert (a["seconds"], b["seconds"]) == (20, 20)
    assert (a["crossover_uses"], b["crossover_uses"]) == (5, 10)
    assert a["curves"]["20"] == 500
    assert report["arms"][0]["curves"]["20"] == {"mean": 550, "range": [500, 600]}
    assert report["observed_research_native_seconds"] == 680
    assert report["baselines"][0]["build_seconds"] == 0
    assert report["baselines"][0]["build"] is None
    assert report["baselines"][0]["curves"]["20"] == 800
    assert all(c["difference_seconds"] == -20 for c in a["paired_cases"])
    assert report["research"][0]["coverage"]["usage_unavailable"] > 0


@pytest.mark.parametrize(
    "problem",
    ["wrong", "missing", "failed-build", "missing-duration", "mismatch", "baseline-wrong"],
)
def test_bad_or_missing_work_never_produces_qualified_crossover(problem):
    data = fixture()
    score = data["scores"][-1] if problem == "baseline-wrong" else data["scores"][0]
    rid = score["id"]
    if problem in {"wrong", "baseline-wrong"}:
        score["value"] = 0
    elif problem == "missing":
        data["scores"].remove(score)
    elif problem == "failed-build":
        data["results"]["b1"]["status"] = "build_failed"
    elif problem == "missing-duration":
        data["raw"][rid].pop("duration_seconds")
        data["results"][rid].pop("duration_seconds")
    else:
        data["results"][rid]["duration_seconds"] += 1
    b = interpret_resources(**data)["builds"][0]
    assert not b["qualified"] and b["crossover_uses"] is None
    if problem == "missing-duration":
        assert b["seconds"] is None and b["curves"]["20"] is None
    else:
        assert b["curves"]["20"] == 500


def test_timeout_output_can_qualify_but_keeps_status_and_overshoot():
    data = fixture()
    data["raw"]["b1"].update(status="budget_exhausted", duration_seconds=100.03)
    data["results"]["b1"]["duration_seconds"] = 100.03
    report = interpret_resources(**data)
    assert report["builds"][0]["qualified"]
    assert report["builds"][0]["build_native_status"] == "budget_exhausted"
    assert report["builds"][0]["crossover_uses"] == pytest.approx(5.0015)
    assert report["research"][0]["coverage"]["timeouts"] == 1


def test_no_positive_saving_has_no_crossover():
    data = fixture()
    for t in data["plan"]["trials"]:
        if t["role"] == "consume" and t["parent"] is not None:
            data["raw"][t["id"]]["duration_seconds"] += 25
            data["results"][t["id"]]["duration_seconds"] += 25
    assert interpret_resources(**data)["builds"][0]["crossover_status"] == "no_positive_saving"


def test_usage_deduplicates_root_child_responses_without_adding_cache_or_reasoning():
    usage = {
        "input_tokens": 100,
        "cached_input_tokens": 80,
        "output_tokens": 20,
        "reasoning_output_tokens": 10,
    }

    def session(name, parent, responses):
        source = {"subagent": {"thread_spawn": {"parent_thread_id": parent}}} if parent else "exec"
        return b"".join(
            canonical(r)
            for r in [
                {"type": "session_meta", "payload": {"id": name, "source": source}},
                *[
                    {"type": "token_usage_record", "payload": {"response_id": r, "usage": usage}}
                    for r in responses
                ],
            ]
        )

    files = {
        "sessions/root": session("root", None, ["a", "b"]),
        "sessions/child": session("child", "root", ["b", "c"]),
    }
    report = usage_evidence(files)
    assert report["native_usage_records"] == 3
    assert report["totals"]["input_tokens"] == 300
    assert report["totals"]["output_tokens"] == 60
    assert report["sessions"][0]["parent"] == "root"
    data = fixture()
    data["usage"] = {"b1": report, "b2": copy.deepcopy(report)}
    with pytest.raises(ValueError, match="across root"):
        interpret_resources(**data)
