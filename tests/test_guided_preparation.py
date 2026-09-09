import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

from yassa.app import main
from yassa.evidence import EvidenceStore, verify_run, write_new
from yassa.guided_preparation import StudyDraft, prepare_draft, readiness
from yassa.native import execute_native_study, prepare_native, rescore_native
from yassa.native_checkers import oracle
from yassa.native_contracts import (
    NativeStudyV2,
    builder_files,
    make_native_plan,
    prepare_files,
)
from yassa.preparation_evidence import load_preparation
from yassa.preparation_templates import (
    FEATURES,
    generate_suite,
    task_contract,
    template_description,
    verify_checker,
)
from yassa.records import canonical, digest, parse_json

STUDIES = Path(__file__).resolve().parents[1] / "studies"
IMAGE = "sha256:" + "a" * 64


def complete(family="reconciliation-v1"):
    return {
        "request": "Compare a common builder request with explicit checking on reconciliation.",
        "intended_use": "Understand errors on constructed file-processing scenarios.",
        "family": family,
        "scope": "synthetic-fixture",
        "accepted_contract_sha256": template_description(family)["contract_sha256"],
        "seed": 17,
        "model": "test-model",
        "reasoning_effort": "high",
        "arms": [
            {"id": "control", "builds": 2},
            {"id": "check", "builds": 1, "invocation": "Check edge cases before finishing."},
        ],
        "control_rationale": {
            "control": "Common builder request.",
            "check": "Contribution of explicitly requesting checks.",
        },
        "consumer_repeats": 2,
        "schedule_seed": 5,
        "admission": {
            "max_attempts": 100,
            "max_scheduled_seconds": 6000,
            "build_timeout_seconds": 60,
            "consumer_timeout_seconds": 30,
        },
    }


def draft_at(tmp_path, value=None, name="draft"):
    request = tmp_path / f"{name}-request.json"
    request.write_bytes(canonical(value or complete()))
    return prepare_draft(request, tmp_path / name).parent


def add_supplied(value, tmp_path, family="reconciliation"):
    # Preserve deliberate CRLF and whitespace rather than only parsed content.
    material = parse_json((STUDIES / f"native-{family}-supplied-v2.json").read_bytes())
    source = tmp_path / "supplied.json"
    raw = json.dumps(material, indent=3).replace("\n", "\r\n").encode("utf-8")
    source.write_bytes(raw)
    value.update(
        routes=["user-supplied", "yassa-prepared"],
        first_dovetail_study=True,
        supplied=[{"id": "supplied", "source": {"path": source.name, "sha256": digest(raw)}}],
    )
    return source, raw


def test_rough_request_focused_questions_and_immutable_answers(tmp_path):
    rough = {
        "request": "Can a builder help me reconcile files?",
        "facts": ["IDs matter."],
        "unresolved": ["Should differently cased IDs match?"],
    }
    root = draft_at(tmp_path, rough)
    state = parse_json((root / "draft.json").read_bytes())
    assert state["status"] == "needs_input"
    assert len(state["questions"]) == 2
    assert state["request"]["family"] is None
    assert not (root / "study.json").exists()
    original = (root / "draft-seal.json").read_bytes()
    answers = complete()
    answers.pop("request")
    answers.update(
        unresolved=[], facts=["IDs are case-sensitive."], assumptions=["Invented ledgers."]
    )
    path = tmp_path / "answers.json"
    path.write_bytes(canonical(answers))
    revised = prepare_draft(path, tmp_path / "revised", root).parent
    assert (root / "draft-seal.json").read_bytes() == original
    assert (revised / "history/000-request.json").read_bytes() == canonical(rough)
    assert (revised / "history/001-answers.json").read_bytes() == canonical(answers)
    assert parse_json((revised / "draft.json").read_bytes())["questions"] == []
    assert (revised / "study.json").is_file()


@pytest.mark.parametrize("family", FEATURES)
def test_complete_request_shared_contracts_checker_evidence_and_determinism(tmp_path, family):
    root = draft_at(tmp_path, complete(family))
    study = NativeStudyV2.model_validate(parse_json((root / "study.json").read_bytes()))
    material, provenance, original = prepare_files(study.task, study.conditions[0], root)
    assert provenance["route"] == "yassa-prepared"
    assert original == (root / "materials/prepared.json").read_bytes()
    cases = len(FEATURES[family])
    assert len(material.development) == (3 if family == "reconciliation-v2" else 2)
    assert len(material.evaluation) == cases
    verification = parse_json((root / "validation.json").read_bytes())
    probes = verification["conditions"]["prepared"]["probes"]
    assert all(p["expected"] == p["observed"] for p in probes)
    assert {p["expected"] for p in probes} == {0, 1}
    plan = make_native_plan(study, {"prepared": material}, "review")
    assert plan["reserved_attempts"] == 3 + 6 * cases
    assert plan["reserved_native_seconds"] == 180 + 180 * cases
    builder = canonical({n: b.decode() for n, b in builder_files(study.task, material).items()})
    assert all(c.id.encode() not in builder for c in material.evaluation)
    assert study.task.requirements in study.task.consumer_prompt
    assert load_preparation(study, root)["history/000-request.json"] == canonical(complete(family))
    again = draft_at(tmp_path, complete(family), "again")
    for name in ("study.json", "materials/prepared.json", "validation.json", "preparation.json"):
        assert (root / name).read_bytes() == (again / name).read_bytes()


@pytest.mark.parametrize(
    "change,field",
    [
        ({"accepted_contract_sha256": None}, "accepted_contract_sha256"),
        ({"family": "account-totals-v1"}, "accepted_contract_sha256"),
        ({"unresolved": ["Case sensitivity is unknown."]}, "unresolved/proposals"),
        ({"proposals": ["Drop negative rows?"]}, "unresolved/proposals"),
        ({"evidence": "broader-comparison"}, "evidence"),
        ({"first_dovetail_study": True}, "routes"),
        ({"admission": None}, "admission/consumer_repeats/schedule_seed"),
        ({"control_rationale": {}}, "arms/control_rationale"),
    ],
)
def test_material_choices_never_silently_resolved(tmp_path, change, field):
    value = complete()
    value.update(change)
    assert field in {q["field"] for q in readiness(StudyDraft.model_validate(value))}
    root = draft_at(tmp_path, value)
    assert not (root / "study.json").exists()


def test_supplied_originals_survive_removal_relocation_and_revision(tmp_path):
    value = complete()
    source, raw = add_supplied(value, tmp_path)
    value["accepted_contract_sha256"] = None
    root = draft_at(tmp_path, value)
    source.unlink()
    relocated = tmp_path / "moved-draft"
    shutil.move(root, relocated)
    answers = tmp_path / "answers.json"
    answers.write_bytes(
        canonical(
            {
                "accepted_contract_sha256": template_description("reconciliation-v1")[
                    "contract_sha256"
                ]
            }
        )
    )
    revised = prepare_draft(answers, tmp_path / "ready", relocated).parent
    study = NativeStudyV2.model_validate(parse_json((revised / "study.json").read_bytes()))
    assert {c.route for c in study.conditions} == {"user-supplied", "yassa-prepared"}
    assert prepare_files(study.task, study.conditions[0], revised)[2] == raw
    assert load_preparation(study, revised)["history/000-supplied-supplied.json"] == raw


@pytest.mark.parametrize("field,limit", [("max_attempts", 38), ("max_scheduled_seconds", 1259)])
def test_budget_rejection_creates_no_draft(tmp_path, field, limit):
    value = complete()
    value["admission"][field] = limit
    with pytest.raises(ValueError, match=field):
        draft_at(tmp_path, value)
    assert not (tmp_path / "draft").exists()


def test_bad_supplied_reference_and_overlap_rejected(tmp_path):
    for problem in ("reference", "split"):
        value = complete()
        source, _ = add_supplied(value, tmp_path)
        raw = parse_json(source.read_bytes())
        if problem == "reference":
            raw["evaluation"][0]["expected"]["balances"][0]["delta_cents"] += 1
        else:
            raw["evaluation"][0].update(
                files=raw["development"][0]["files"], expected=raw["development"][0]["expected"]
            )
        source.write_bytes(canonical(raw))
        value["supplied"][0]["source"]["sha256"] = digest(source.read_bytes())
        with pytest.raises(ValueError):
            draft_at(tmp_path, value)
        assert not (tmp_path / "draft").exists()


@pytest.mark.parametrize("target", ["review.md", "validation.json", "materials/prepared.json"])
def test_changed_preparation_rejected_before_image_lookup(tmp_path, monkeypatch, target):
    root = draft_at(tmp_path)
    (root / target).write_bytes(b"changed")
    calls = []
    monkeypatch.setattr("yassa.native_runner.subprocess.run", lambda *a, **kw: calls.append(a))
    with pytest.raises(ValueError, match="preparation evidence changed"):
        prepare_native(root / "study.json", tmp_path / "run", None, IMAGE)
    assert not calls and not (tmp_path / "run").exists()
    answers = tmp_path / "answers.json"
    answers.write_bytes(b"{}")
    with pytest.raises(ValueError, match="draft changed"):
        prepare_draft(answers, tmp_path / "revision", root)


def test_stale_study_or_missing_preparation_cannot_use_review(tmp_path):
    root = draft_at(tmp_path)
    raw = parse_json((root / "study.json").read_bytes())
    changed = copy.deepcopy(raw)
    changed["arms"][0]["builds"] = 1
    with pytest.raises(ValueError, match="study changed"):
        load_preparation(NativeStudyV2.model_validate(changed), root)
    raw["preparation"] = None
    with pytest.raises(ValueError, match="require a pinned preparation"):
        load_preparation(NativeStudyV2.model_validate(raw), root)


def test_checker_verification_detects_faulty_checker_and_rejects_exact_json(monkeypatch):
    task = task_contract("reconciliation-v1")
    material = generate_suite(task, 3, FEATURES[task.checker])
    monkeypatch.setattr("yassa.preparation_templates.check", lambda *a: {"value": 1})
    with pytest.raises(ValueError, match="calibration failed"):
        verify_checker(task, material)
    with pytest.raises(ValueError, match="semantic oracle"):
        verify_checker(task.model_copy(update={"checker": "json-exact-v1"}), material)


def test_feature_coverage_is_observable_and_seeded():
    task = task_contract("reconciliation-v1")
    material = generate_suite(task, 1, FEATURES[task.checker])
    cases = {c.id: c for c in material.evaluation}
    assert cases["heldout-empty"].expected == {"balances": []}
    assert {r["id"] for r in cases["heldout-identifiers"].expected["balances"]} == {
        "Case",
        " case ",
        "case",
    }
    assert '"line\nid"' in cases["heldout-csv-quoting"].files[task.checker_inputs[1]]
    assert material != generate_suite(task, 2, FEATURES[task.checker])
    selected = generate_suite(task, 1, ("one-sided",))
    assert [c.id for c in selected.evaluation] == ["heldout-one-sided"]


def test_guided_study_native_adapter_boundary_report_and_relocated_rescore(tmp_path, monkeypatch):
    value = complete()
    _, raw_original = add_supplied(value, tmp_path)
    draft = draft_at(tmp_path, value)
    monkeypatch.setattr("yassa.native_runner.subprocess.run", lambda *a, **kw: None)
    root = prepare_native(draft / "study.json", tmp_path / "run", None, IMAGE)
    frozen = parse_json((root / "study.json").read_bytes())
    study = NativeStudyV2.model_validate(frozen["study"])
    store = EvidenceStore(root)
    evidence = store.get(frozen["preparation_id"])
    assert evidence["history/000-supplied-supplied.json"] == raw_original
    plan = parse_json((root / "plan.json").read_bytes())
    trials = {t["id"]: t for t in plan["trials"]}

    def adapter(root, attempt_id, prompt, files, **kwargs):
        trial = trials[attempt_id]
        assert not any("history/" in n or "review.md" in n or "validation.json" in n for n in files)
        if trial["role"] == "build":
            brief = parse_json(files[study.task.brief_path])
            assert set(brief) == {"brief", "contract", "development"}
            assert "evaluation" not in brief
            package = f"---\nname: {study.task.package_name}\ndescription: Test package.\n---\n"
            output = {study.task.package_path + "/SKILL.md": package.encode()}
        else:
            assert study.task.requirements in prompt
            data = {n: b.decode() for n, b in files.items() if n.startswith("input/")}
            output = {
                study.task.result_path: canonical(
                    oracle(study.task.checker, data, study.task.checker_inputs)
                )
            }
        result = {
            "status": "completed",
            "output_id": store.put(output),
            "rejected_paths": [],
            "duration_seconds": 1,
        }
        write_new(root / "attempts" / attempt_id / "result.json", canonical(result))
        return result

    monkeypatch.setattr("yassa.native_runner.execute_native", adapter)
    report = execute_native_study(root, tmp_path / "unused-auth")
    assert "Preparation review" in report.read_text()
    scores = parse_json((report.parent / "scores.json").read_bytes())["scores"]
    assert len(scores) == 48 and all(s["value"] == 1 for s in scores)
    assert {s["condition"] for s in scores} == {"supplied", "prepared"}
    moved = tmp_path / "relocated-run"
    shutil.copytree(root, moved)
    assert verify_run(moved) == verify_run(root)
    repeat = rescore_native(moved, "repeat")
    assert (repeat.parent / "scores.json").read_bytes() == (
        report.parent / "scores.json"
    ).read_bytes()


def test_cli_and_malformed_path_input(tmp_path, monkeypatch, capsys):
    request = tmp_path / "request.json"
    request.write_bytes(canonical(complete()))
    monkeypatch.setattr(
        sys, "argv", ["yassa", "study-draft", str(request), "--draft-dir", str(tmp_path / "draft")]
    )
    assert main() == 0
    assert "review.md" in capsys.readouterr().out
    request.write_bytes(b'{"request":"reconcile","supplied":[{}]}')
    assert main() == 2
    assert "yassa:" in capsys.readouterr().err


def test_supplied_only_does_not_generate_or_require_seed(tmp_path):
    value = complete()
    add_supplied(value, tmp_path)
    value.update(routes=["user-supplied"], first_dovetail_study=False, seed=None)
    root = draft_at(tmp_path, value)
    study = NativeStudyV2.model_validate(parse_json((root / "study.json").read_bytes()))
    assert len(study.conditions) == 1 and study.conditions[0].route == "user-supplied"
    assert not (root / "materials/prepared.json").exists()


def test_documented_examples_are_complete_and_preserve_both_routes(tmp_path):
    first = prepare_draft(STUDIES / "preparation-request.json", tmp_path / "first").parent
    second = prepare_draft(STUDIES / "preparation-answers.json", tmp_path / "second", first).parent
    verification = parse_json((second / "validation.json").read_bytes())
    assert verification["plan"]["reserved_attempts"] == 54
    assert verification["plan"]["reserved_native_seconds"] == 1800
    assert set(verification["conditions"]) == {"supplied", "prepared"}


def test_source_pin_mismatch_prevents_ready_draft(tmp_path):
    value = complete()
    source = tmp_path / "skills/helper"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_bytes(b"external fixture package")
    value["sources"] = [{"id": "helper", "path": "skills", "files": {"helper/SKILL.md": "0" * 64}}]
    value["arms"][1]["sources"] = ["helper"]
    with pytest.raises(ValueError, match="source pin mismatch"):
        draft_at(tmp_path, value)
    assert not (tmp_path / "draft").exists()


def test_changed_checker_requires_new_review_before_freeze(tmp_path, monkeypatch):
    root = draft_at(tmp_path)
    monkeypatch.setattr(
        "yassa.native_runner.checker_identity", lambda task: ({"id": "changed"}, {})
    )
    with pytest.raises(ValueError, match="checker changed"):
        prepare_native(root / "study.json", tmp_path / "run", None, IMAGE)
    assert not (tmp_path / "run").exists()


def test_reviewed_material_count_and_pin_are_enforced(tmp_path):
    root = draft_at(tmp_path)
    study = NativeStudyV2.model_validate(parse_json((root / "study.json").read_bytes()))
    condition = study.conditions[0]
    with pytest.raises(ValueError, match="case count"):
        prepare_files(study.task, condition.model_copy(update={"evaluation_cases": 1}), root)
    (root / "materials/prepared.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="source hash mismatch"):
        prepare_files(study.task, condition, root)
