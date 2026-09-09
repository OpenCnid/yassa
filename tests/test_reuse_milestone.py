import copy
import csv
import io
import shutil

import pytest
from test_guided_preparation import complete, draft_at

from yassa.evidence import EvidenceStore, verify_run, write_new
from yassa.guided_preparation import prepare_draft
from yassa.native import execute_native_study, prepare_native, rescore_native
from yassa.native_contracts import FileMaterials, NativeStudyV2, make_native_plan
from yassa.native_resources import write_resource_interpretation
from yassa.preparation_evidence import load_preparation
from yassa.preparation_templates import FEATURES, generate_suite, task_contract
from yassa.records import canonical, digest, parse_json
from yassa.reuse_materials import generate_reuse_suite, verify_history


def reuse_request(tmp_path):
    task = task_contract("reconciliation-v2")
    historical = generate_suite(task, 73029, FEATURES[task.checker])
    path = tmp_path / "historical.json"
    path.write_bytes(canonical(historical.model_dump(mode="json")))
    value = complete("reconciliation-v2")
    value.update(
        material_recipe="reconciliation-reuse-suite-v1",
        historical_materials=[{"path": str(path), "sha256": digest(path.read_bytes())}],
        arms=[{"id": "control", "builds": 3}, {"id": "check", "builds": 3}],
        consumer_baseline={"id": "no-package", "repeats": 2},
        scheduling="case-repeat-blocks-v1",
        resource_scenarios={"horizons": [1, 5, 20, 50], "primary": 20},
        admission={
            "max_attempts": 90,
            "max_scheduled_seconds": 11160,
            "build_timeout_seconds": 600,
            "consumer_timeout_seconds": 90,
        },
    )
    value["control_rationale"]["no-package"] = "Fresh session with complete task facts."
    return value, task, historical


def test_recipe_preserves_contract_references_profiles_and_fault_probes(tmp_path):
    _, task, historical = reuse_request(tmp_path)
    material, recipe = generate_reuse_suite(task, 84091, [historical])
    again, record = generate_reuse_suite(task, 84091, [historical])
    assert canonical(recipe) == canonical(record) and material == again
    assert material.brief == task.requirements
    assert len(material.development) == 3 and len(material.evaluation) == 6
    assert recipe["independent_briefs"] == 1
    assert all(
        len([c for c in material.evaluation if c.group.endswith(p)]) == 2
        for p in ("compact", "interaction", "bulk")
    )
    assert all(
        300 <= r["rows"] <= 404 for r in recipe["selection_ledger"] if r["profile"] == "bulk"
    )
    assert all(p["expected"] == p["observed"] for p in recipe["verification"]["probes"])
    assert all(recipe["verification"]["fault_detection"].values())
    assert (
        any(
            p["expected"] == 1
            for p in recipe["verification"]["probes"]
            if p["probe"] == "strict-tolerance"
        )
        is False
    )  # Each case deliberately includes a boundary.
    changed, _ = generate_reuse_suite(task, 84092, [historical, material])
    assert changed != material


def test_historical_screen_rejects_renamed_reordered_reused_histories(tmp_path):
    _, task, historical = reuse_request(tmp_path)
    material, _ = generate_reuse_suite(task, 84091, [historical])
    changed = copy.deepcopy(material.model_dump(mode="json"))
    case = changed["evaluation"][0]
    for path in task.checker_inputs[:2]:
        rows = list(csv.reader(io.StringIO(case["files"][path])))
        for row in rows[1:]:
            row[0] = "renamed-" + row[0]
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerows([rows[0], *reversed(rows[1:])])
        case["files"][path] = stream.getvalue()
    with pytest.raises(ValueError, match="duplicate"):
        verify_history(task, FileMaterials.model_validate(changed), [material])


def test_freeze_block_order_admission_and_portable_preparation(tmp_path):
    value, _, _ = reuse_request(tmp_path)
    root = draft_at(tmp_path, value)
    study = NativeStudyV2.model_validate(parse_json((root / "study.json").read_bytes()))
    assert load_preparation(study, root)
    plan = parse_json((root / "validation.json").read_bytes())["plan"]
    assert (plan["reserved_attempts"], plan["reserved_native_seconds"]) == (90, 11160)
    assert len(plan["ordering"]["blocks"]) == 12
    builds = {t["id"] for t in plan["trials"][:6]}
    assert len(builds) == 6
    for block in plan["ordering"]["blocks"]:
        members = [t for t in plan["trials"] if t["id"] in block["trial_ids"]]
        assert len(members) == 7
        assert {t["parent"] for t in members} == builds | {None}
        baseline = next(t for t in members if t["parent"] is None)
        assert baseline["build"] is None
        assert len({(t["condition"], t["case"], t["repeat"]) for t in members}) == 1
    for counts in plan["ordering"]["arm_position_counts"].values():
        assert all(max(v) - min(v) <= 2 for v in counts.values())
    material = FileMaterials.model_validate(
        parse_json((root / "materials/prepared.json").read_bytes())
    )
    assert plan == make_native_plan(study, {"prepared": material}, "preparation-review")
    unblocked = NativeStudyV2.model_validate({**study.model_dump(mode="json"), "scheduling": None})
    legacy = make_native_plan(unblocked, {"prepared": material}, "preparation-review")
    assert sorted(legacy["trials"], key=lambda t: t["id"]) == sorted(
        plan["trials"], key=lambda t: t["id"]
    )
    assert "scheduling" not in unblocked.model_dump(mode="json")
    moved = tmp_path / "moved"
    shutil.copytree(root, moved)
    assert load_preparation(study, moved)
    answers = tmp_path / "answers.json"
    answers.write_bytes(canonical({"seed": 84092}))
    revised = prepare_draft(answers, tmp_path / "revised", moved)
    assert (
        parse_json((revised.parent / "validation.json").read_bytes())["generator"]["version"]
        == "reconciliation-reuse-suite-v1"
    )


@pytest.mark.parametrize("field,value", [("max_attempts", 89), ("max_scheduled_seconds", 11159)])
def test_full_allocation_is_admitted_before_freezing(tmp_path, field, value):
    request, _, _ = reuse_request(tmp_path)
    request["admission"][field] = value
    with pytest.raises(ValueError, match=field):
        draft_at(tmp_path, request)
    assert not (tmp_path / "draft").exists()


def test_blocked_builds_keep_baselines_full_denominators_and_relocated_resources(
    tmp_path, monkeypatch
):
    value, _, _ = reuse_request(tmp_path)
    review = draft_at(tmp_path, value)
    monkeypatch.setattr("yassa.native_runner.subprocess.run", lambda *a, **kw: None)
    root = prepare_native(review / "study.json", tmp_path / "run", None, "sha256:" + "a" * 64)
    plan = parse_json((root / "plan.json").read_bytes())
    frozen = parse_json((root / "study.json").read_bytes())
    store = EvidenceStore(root)
    material = store.json(frozen["conditions"][0]["materials_id"], "materials.json")
    trials = {t["id"]: t for t in plan["trials"]}
    seen = []

    def adapter(root, rid, prompt, files, **kwargs):
        t = trials[rid]
        seen.append(rid)
        # Build failures and infrastructure failures keep their distinct denominators.
        status = "harness_failure" if t["arm"] == "check" else "completed"
        result = {"status": status, "duration_seconds": 4, "rejected_paths": []}
        if t["role"] == "consume":
            assert t["parent"] is None and t["build"] is None
            case = next(c for c in material["evaluation"] if c["id"] == t["case"])
            assert files == {n: s.encode() for n, s in case["files"].items()}
            assert "reconciliation-reuse-suite-v1" not in prompt
            result["output_id"] = store.put({"output/answer.json": canonical(case["expected"])})
        write_new(root / "attempts" / rid / "result.json", canonical(result))
        return result

    monkeypatch.setattr("yassa.native_runner.execute_native", adapter)
    report = execute_native_study(root, tmp_path / "unused-auth")
    scores = parse_json((report.parent / "scores.json").read_bytes())["scores"]
    assert len(seen) == 18 and len(scores) == 84
    assert [sum(s["value"] == v for s in scores) for v in (0, 1, None)] == [36, 12, 36]
    assert seen == [t["id"] for t in plan["trials"] if t["role"] == "build" or t["parent"] is None]
    original_seal = verify_run(root)
    output = write_resource_interpretation(root, "original", tmp_path / "resources")
    resource_bytes = (output.parent / "resources.json").read_bytes()
    resources = parse_json(resource_bytes)
    assert all(not b["qualified"] and b["crossover_uses"] is None for b in resources["builds"])
    assert resources["observed_research_native_seconds"] == 72
    assert len(resources["attempts"]) == 90
    moved = tmp_path / "relocated-run"
    shutil.copytree(root, moved)
    relocated = rescore_native(moved, "relocated")
    assert (relocated.parent / "scores.json").read_bytes() == (
        report.parent / "scores.json"
    ).read_bytes()
    other = write_resource_interpretation(moved, "original", tmp_path / "relocated-resources")
    assert (other.parent / "resources.json").read_bytes() == resource_bytes
    assert verify_run(root) == original_seal
    with pytest.raises(FileExistsError):
        write_resource_interpretation(root, "original", output.parent)
