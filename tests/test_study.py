import copy
from pathlib import Path

import pytest

from yassa.app import load_frozen, prepare
from yassa.planning import make_plan
from yassa.prepare import generate_materials, intake, prepare_condition
from yassa.records import canonical, digest, parse_json
from yassa.study import Materials, Study


def test_intake_does_not_interview_complete_study(study_data):
    assert intake(study_data)["questions"] == []
    assert len(intake({})["questions"]) == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 2),
        ("runtime", "native-codex"),
        ("runtime", "openai"),
        ("scoring", "model-graded"),
        ("analysis", "paired-t-test"),
        ("scope", "real-user-work"),
        ("unknown_setting", True),
        ("execution_repeats", True),
    ],
)
def test_unsupported_settings_fail_before_any_run(field, value, study_data, write_study, tmp_path):
    study_data[field] = value
    with pytest.raises(ValueError):
        prepare(write_study(study_data), tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_generated_cases_and_plan_are_reproducible(study_data):
    study = Study.model_validate(study_data)
    prepared = study.conditions[1]
    assert generate_materials(prepared) == generate_materials(prepared)
    materials = {
        condition.id: prepare_condition(condition, Path.cwd())[0] for condition in study.conditions
    }
    plan = make_plan(study, materials, "frozen-study-id")
    assert plan == make_plan(study, materials, "frozen-study-id")
    # 2 conditions * 3 arms * (3 direct + 1 build + 3 consumers).
    assert len(plan["trials"]) == 42
    assert plan["reserved_attempts"] == 84
    assert len({trial["id"] for trial in plan["trials"]}) == 42
    assert sum(trial["role"] == "build" for trial in plan["trials"]) == 6


def test_budget_rejection_launches_nothing(study_data, write_study, tmp_path):
    study_data["limits"]["max_attempts"] = 83
    with pytest.raises(ValueError, match="reserves 84"):
        prepare(write_study(), tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_supplied_bytes_and_derivation_preserved(write_study, tmp_path):
    from yassa.evidence import EvidenceStore

    root = prepare(write_study(), tmp_path / "run")
    frozen, _, _, _ = load_frozen(root)
    store = EvidenceStore(root)
    supplied = frozen["conditions"][0]
    original = store.get(supplied["original_id"])["original.json"]
    assert digest(original) == supplied["provenance"]["original_sha256"]
    assert supplied["derived_from"] == supplied["original_id"]
    assert supplied["provenance"]["route"] == "user-supplied"
    assert frozen["conditions"][1]["provenance"]["route"] == "yassa-prepared"
    assert frozen["conditions"][1]["provenance"]["seed"] == 73019


def test_modified_supplied_source_rejected(study_data, write_study, tmp_path):
    study_data["conditions"][0]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source hash mismatch"):
        prepare(write_study(), tmp_path / "run")


def test_bad_reference_rejected(study_data, write_study, tmp_path):
    from pathlib import Path

    material = parse_json(Path(study_data["conditions"][0]["source_path"]).read_bytes())
    material["evaluation"][0]["expected"][0]["net_cents"] += 1
    source = tmp_path / "bad-reference.json"
    source.write_bytes(canonical(material))
    study_data["conditions"][0].update(
        source_path=str(source), source_sha256=digest(source.read_bytes())
    )
    with pytest.raises(ValueError, match="invalid reference"):
        prepare(write_study(), tmp_path / "run")


@pytest.mark.parametrize("overlap", ["group", "id", "input", "equivalent-input"])
def test_heldout_split_validation(study_data, overlap):
    condition = Study.model_validate(study_data).conditions[1]
    materials = generate_materials(condition)
    if overlap in {"input", "equivalent-input"}:
        materials["evaluation"][0]["rows"] = copy.deepcopy(materials["development"][0]["rows"])
        if overlap == "equivalent-input":
            materials["evaluation"][0]["rows"].reverse()
            for row in materials["evaluation"][0]["rows"]:
                row["account"] = row["account"].upper().strip()
    else:
        materials["evaluation"][0][overlap] = materials["development"][0][overlap]
    with pytest.raises(ValueError):
        Materials.model_validate(materials)
