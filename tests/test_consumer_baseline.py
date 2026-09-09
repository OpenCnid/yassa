"""Baseline allocation, complete public facts, failures and portable evidence."""

import shutil
from collections import defaultdict

import pytest
from test_guided_preparation import complete, draft_at
from test_native_v2 import IMAGE, STUDIES, freeze, prepared, request

from yassa.evidence import EvidenceStore, verify_run, write_new
from yassa.guided_preparation import StudyDraft, prepare_draft, readiness
from yassa.native import execute_native_study, prepare_native, rescore_native
from yassa.native_contracts import NativeStudyV2, make_native_plan
from yassa.preparation_evidence import load_preparation, study_identity
from yassa.records import canonical, digest, identity, parse_json


def baseline_request():
    value = request()
    value["consumer_baseline"] = {"id": "unassisted", "repeats": 3}
    value["admission"].update(max_attempts=42, max_scheduled_seconds=3240)
    return value


def test_baseline_allocation_is_independent_of_builds_and_package_repeats():
    study, materials = prepared(baseline_request())
    plan = make_native_plan(study, materials, "frozen")
    assert (plan["reserved_attempts"], plan["reserved_native_seconds"]) == (42, 3240)
    direct = [t for t in plan["trials"] if t["arm"] == "unassisted"]
    assert len(direct) == 12
    assert all(t["parent"] is None and t["build"] is None for t in direct)
    assert all(t["role"] == "consume" for t in direct)
    assert {t["repeat"] for t in direct} == {1, 2, 3}
    assert all(t["role"] == "build" for t in plan["trials"][:6])
    changed = baseline_request()
    changed["arms"][0]["builds"] = 1
    changed["consumer_repeats"] = 1
    study, materials = prepared(changed)
    again = make_native_plan(study, materials, "frozen")
    assert direct == [t for t in again["trials"] if t["arm"] == "unassisted"]


@pytest.mark.parametrize("field,limit", [("max_attempts", 41), ("max_scheduled_seconds", 3239)])
def test_baseline_admission_before_any_docker_or_artifact(tmp_path, monkeypatch, field, limit):
    value = baseline_request()
    value["admission"][field] = limit
    calls = []
    monkeypatch.setattr("yassa.native_runner.subprocess.run", lambda *a, **kw: calls.append(a))
    path = tmp_path / "request.json"
    path.write_bytes(canonical(value))
    with pytest.raises(ValueError, match=field):
        prepare_native(path, tmp_path / "run", None, IMAGE)
    assert not calls and not (tmp_path / "run").exists()


@pytest.mark.parametrize(
    "baseline",
    [
        {"id": "control", "repeats": 1},
        {"id": "unassisted", "repeats": 0},
        {"id": "unassisted", "repeats": True},
        {"id": "unassisted", "repeats": 21},
        {"id": "unassisted", "repeats": 1, "sources": ["hidden"]},
        {"id": "unassisted", "repeats": 1, "builds": 1},
    ],
)
def test_baseline_rejects_ambiguous_or_treated_controls(baseline):
    value = baseline_request()
    value["consumer_baseline"] = baseline
    with pytest.raises(ValueError):
        NativeStudyV2.model_validate(value)


@pytest.mark.parametrize("failed_builders", [False, True])
def test_baseline_execution_context_failures_reporting_and_relocation(
    tmp_path, monkeypatch, failed_builders
):
    value = baseline_request()
    root = freeze(tmp_path, monkeypatch, value)
    store = EvidenceStore(root)
    study, materials = prepared(value)
    plan = parse_json((root / "plan.json").read_bytes())
    trials = {t["id"]: t for t in plan["trials"]}
    seen = []
    common = defaultdict(set)

    def adapter(root, attempt_id, prompt, files, **kwargs):
        trial = trials[attempt_id]
        seen.append(trial)
        status, output = "completed", {}
        if trial["role"] == "build":
            if failed_builders:
                status = "harness_failure" if trial["arm"] == "explicit-checks" else "completed"
            else:
                output[study.task.package_path + "/SKILL.md"] = (
                    f"---\nname: {study.task.package_name}\ndescription: Process ledgers.\n---\n"
                    + attempt_id
                ).encode()
        else:
            case = next(
                c for c in materials[trial["condition"]].evaluation if c.id == trial["case"]
            )
            binding = parse_json((root / "bindings" / f"{attempt_id}.json").read_bytes())
            public = {n: t.encode() for n, t in case.files.items()}
            assert {n: b for n, b in files.items() if n.startswith("input/")} == public
            shared = store.get(binding["common_id"])
            assert shared == {"prompt.txt": shared["prompt.txt"], **public}
            assert study.task.requirements in shared["prompt.txt"].decode()
            common[trial["condition"], trial["case"]].add(binding["common_id"])
            if trial["parent"] is None:
                assert files == public and not binding["treatment_ids"]
                assert kwargs["executable"] == () and binding["executable"] == []
                assert prompt.encode() == shared["prompt.txt"]
                assert f"Use ${study.task.package_name}" not in prompt
                if trial["repeat"] == 1:
                    output[study.task.result_path] = canonical(case.expected)
                elif trial["repeat"] == 2:
                    output[study.task.result_path] = b"{}"
                else:
                    status = "cli_failure"
            else:
                assert not failed_builders
                assert (
                    prompt == f"Use ${study.task.package_name}.\n\n" + shared["prompt.txt"].decode()
                )
                assert len(binding["treatment_ids"]) == 1
                assert (
                    trial["parent"].encode()
                    in files[f".agents/skills/{study.task.package_name}/SKILL.md"]
                )
                output[study.task.result_path] = canonical(case.expected)
        result = {"status": status, "duration_seconds": 1, "rejected_paths": []}
        if output:
            result["output_id"] = store.put(output)
        write_new(root / "attempts" / attempt_id / "result.json", canonical(result))
        return result

    monkeypatch.setattr("yassa.native_runner.execute_native", adapter)
    report = execute_native_study(root, tmp_path / "unused-auth")
    assert verify_run(root)
    assert len(seen) == (18 if failed_builders else 42)
    assert all(len(ids) == 1 for ids in common.values())
    scores = parse_json((report.parent / "scores.json").read_bytes())["scores"]
    direct = [s for s in scores if s["arm"] == "unassisted"]
    assert len(direct) == 12
    assert all(s["package_id"] is None and s["parent"] is None for s in direct)
    assert [sum(s["value"] == v for s in direct) for v in (1, 0, None)] == [4, 4, 4]
    assisted = [s for s in scores if s["arm"] != "unassisted"]
    if failed_builders:
        assert [sum(s["value"] == v for s in assisted) for v in (0, None)] == [16, 8]
    else:
        assert all(s["value"] == 1 for s in assisted)
    analysis = parse_json((report.parent / "analysis.json").read_bytes())
    assert len(analysis["by_build"]) == 6
    assert not any(s["arm"] == "unassisted" for s in analysis["by_build"])
    assert len(analysis["by_baseline"]) == 2
    assert all(
        (s["passed"], s["scored"], s["planned"], s["missing"]) == (2, 4, 6, 2)
        for s in analysis["by_baseline"]
    )
    assert len(analysis["by_case"]) == 12
    assert "no build parent" in report.read_text(encoding="utf-8")
    relocated = tmp_path / "relocated"
    shutil.copytree(root, relocated)
    again = rescore_native(relocated, "relocated")
    assert (again.parent / "scores.json").read_bytes() == (
        report.parent / "scores.json"
    ).read_bytes()


def test_guided_baseline_requires_rationale_and_pins_control(tmp_path):
    value = complete()
    value["consumer_baseline"] = {"id": "unassisted", "repeats": 1}
    assert "arms/control_rationale" in {r["field"] for r in readiness(StudyDraft(**value))}
    value["control_rationale"]["unassisted"] = "Check whether package assistance changes outcomes."
    root = draft_at(tmp_path, value)
    study = NativeStudyV2.model_validate(parse_json((root / "study.json").read_bytes()))
    assert load_preparation(study, root)
    assert "no build or generated package" in (root / "review.md").read_text()
    assert parse_json((root / "validation.json").read_bytes())["plan"]["reserved_attempts"] == 45
    changed = study.model_dump(mode="json")
    changed["consumer_baseline"]["repeats"] = 2
    with pytest.raises(ValueError, match="study changed"):
        load_preparation(NativeStudyV2.model_validate(changed), root)


def test_pre_baseline_preparation_identity_stays_compatible():
    study, _ = prepared(request())
    old = study.model_dump(mode="json", exclude={"preparation", "consumer_baseline"})
    assert study_identity(study) == identity(old)


@pytest.mark.parametrize(
    "study_name,attempts,seconds,baselines",
    [("reconciliation-pilot", 58, 7800, 10), ("reconciliation-sensitivity", 68, 10200, 12)],
)
def test_pilot_preparation_pins_supplied_work_coverage_controls_and_budget(
    tmp_path, study_name, attempts, seconds, baselines
):
    pending = prepare_draft(STUDIES / f"{study_name}-request.json", tmp_path / "pending")
    assert not (pending.parent / "study.json").exists()
    # A fixture source tests binding mechanics; it is not Dovetail evidence.
    source = tmp_path / "fixture-source"
    (source / "helper").mkdir(parents=True)
    body = b"---\nname: helper\ndescription: Fixture.\n---\n"
    (source / "helper/SKILL.md").write_bytes(body)
    answers = {
        "sources": [
            {"id": "fixture", "path": str(source), "files": {"helper/SKILL.md": digest(body)}}
        ],
        "arms": [
            {"id": "common-request", "builds": 2},
            {"id": "dovetail", "builds": 2, "sources": ["fixture"], "invocation": "Use $helper."},
        ],
        "unresolved": [],
    }
    path = tmp_path / "answers.json"
    path.write_bytes(canonical(answers))
    review = prepare_draft(path, tmp_path / "ready", pending.parent)
    validation = parse_json((review.parent / "validation.json").read_bytes())
    plan = validation["plan"]
    assert (plan["reserved_attempts"], plan["reserved_native_seconds"]) == (attempts, seconds)
    assert len([t for t in plan["trials"] if t["role"] == "build"]) == 8
    assert len([t for t in plan["trials"] if t["arm"] == "no-package"]) == baselines
    assert all(
        p["expected"] == p["observed"]
        for c in validation["conditions"].values()
        for p in c["probes"]
    )
    assert (review.parent / "history/000-supplied-supplied.json").read_bytes() == (
        STUDIES / f"{study_name}-supplied.json"
    ).read_bytes()
    changed = dict(
        answers,
        admission={
            "max_attempts": attempts - 1,
            "max_scheduled_seconds": seconds,
            "build_timeout_seconds": 600,
            "consumer_timeout_seconds": 60,
        },
    )
    path.write_bytes(canonical(changed))
    with pytest.raises(ValueError, match="max_attempts"):
        prepare_draft(path, tmp_path / "over-budget", pending.parent)
