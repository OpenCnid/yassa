import copy
import csv
import io
import json
import shutil

import pytest
from test_guided_preparation import IMAGE, complete, draft_at

from yassa.evidence import EvidenceStore, verify_run, write_new
from yassa.native import execute_native_study, prepare_native, rescore_native
from yassa.native_checkers import check, input_identity, oracle
from yassa.native_contracts import FileMaterials, NativeStudyV2, builder_files, validate_materials
from yassa.native_runner import checker_identity
from yassa.preparation_templates import FEATURES, generate_suite, task_contract, verify_checker
from yassa.reconciliation import read_events, read_policy
from yassa.reconciliation_templates import FAULTS, make_case
from yassa.records import canonical, parse_json

TASK = task_contract("reconciliation-v2")
POLICY = {
    "currencies": {
        "USD": {"scale": 2, "tolerance_minor": 2},
        "JPY": {"scale": 0, "tolerance_minor": 0},
    }
}


def row(event, revision, name, amount, currency="USD", state="posted"):
    return event, revision, name, currency, amount, state


def example(left, right=(), policy=None):
    return make_case(TASK, "example", "example-group", left, right, policy or POLICY)


def test_hand_calculated_revision_currency_precision_presence_and_status():
    case = example(
        [
            row("a", 10, "new", "90071992547409.93"),
            row("a", 2, "old", "99"),
            row("a", "010", "new", "90071992547409.93"),
            row("b", 1, "new", "-0.01"),
            row("j", 1, "new", "3", "JPY"),
            row("v", 1, "gone", "8"),
            row("v", 2, "gone", "0", state="void"),
            row("zero", 1, "left-zero", "-0.0"),
        ],
        [row("a", 1, "new", "90071992547409.90"), row("z", 1, "right-zero", "0")],
    )
    expected = {
        "balances": [
            dict(
                id="left-zero",
                currency="USD",
                left_minor=0,
                right_minor=0,
                delta_minor=0,
                left_count=1,
                right_count=0,
                status="left_only",
            ),
            dict(
                id="new",
                currency="JPY",
                left_minor=3,
                right_minor=0,
                delta_minor=3,
                left_count=1,
                right_count=0,
                status="left_only",
            ),
            dict(
                id="new",
                currency="USD",
                left_minor=9007199254740992,
                right_minor=9007199254740990,
                delta_minor=2,
                left_count=2,
                right_count=1,
                status="matched",
            ),
            dict(
                id="right-zero",
                currency="USD",
                left_minor=0,
                right_minor=0,
                delta_minor=0,
                left_count=0,
                right_count=1,
                status="right_only",
            ),
        ]
    }
    assert oracle(TASK.checker, case["files"], TASK.checker_inputs) == expected
    assert check(TASK.checker, canonical(case["expected"]), expected)["value"] == 1


@pytest.mark.parametrize(
    "amount,status",
    [("0.01", "matched"), ("0.02", "matched"), ("-0.02", "matched"), ("-0.03", "mismatch")],
)
def test_inclusive_absolute_tolerance(amount, status):
    case = example([row("a", 1, "x", amount)], [row("b", 1, "x", "0")])
    assert (
        oracle(TASK.checker, case["files"], TASK.checker_inputs)["balances"][0]["status"] == status
    )


def test_policy_is_input_not_external_currency_convention():
    policy = {"currencies": {"USD": {"scale": 3, "tolerance_minor": 4}}}
    case = example([row("a", 1, "x", "1.004")], [row("b", 1, "x", "1")], policy)
    actual = oracle(TASK.checker, case["files"], TASK.checker_inputs)["balances"][0]
    assert (actual["left_minor"], actual["delta_minor"], actual["status"]) == (1004, 4, "matched")


@pytest.mark.parametrize(
    "left,right",
    [
        ([], []),
        ([row("v", 1, "x", "0", state="void")], []),
        ([row("v", 1, "x", "1"), row("v", 2, "y", "2", state="void")], []),
    ],
)
def test_empty_and_all_voided_inputs(left, right):
    case = example(left, right)
    assert oracle(TASK.checker, case["files"], TASK.checker_inputs) == {"balances": []}
    assert check(TASK.checker, b'{ "balances" : [] }', case["expected"])["value"] == 1


@pytest.mark.parametrize(
    "bad",
    [
        row("", 1, "x", "1"),
        row("a", 0, "x", "1"),
        row("a", 1000000001, "x", "1"),
        row("a", 1, "", "1"),
        row("a", 1, "x", "1e2"),
        row("a", 1, "x", "+1"),
        row("a", 1, "x", "0.001"),
        row("a", 1, "x", "1.0", "JPY"),
        row("a", 1, "x", "1", "EUR"),
        row("a", 1, "x", "1", state="VOID"),
        row("a", 1, "x", " 1"),
        row("a", 1, "x", "0.001", state="void"),
    ],
)
def test_invalid_input_is_a_preparation_error(bad):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["event_id", "revision", "id", "currency", "amount", "state"])
    writer.writerow(bad)
    with pytest.raises(ValueError):
        read_events(stream.getvalue(), POLICY["currencies"])


@pytest.mark.parametrize(
    "rule",
    [
        {"scale": True, "tolerance_minor": 1},
        {"scale": 2, "tolerance_minor": -1},
        {"scale": 4, "tolerance_minor": 1},
        {"scale": 2, "tolerance_minor": True},
        {"scale": 2, "tolerance_minor": 1, "extra": 0},
    ],
)
def test_invalid_policy_rejected(rule):
    with pytest.raises(ValueError):
        read_policy(canonical({"currencies": {"USD": rule}}))


def test_conflicting_repeats_rejected_even_in_obsolete_history():
    case = example([row("a", 1, "x", "1"), row("a", 1, "y", "1"), row("a", 2, "x", "2")])
    with pytest.raises(ValueError, match="conflicting"):
        oracle(TASK.checker, case["files"], TASK.checker_inputs)


def test_legitimate_output_order_keys_escapes_and_wrong_components():
    case = example([row("a", 1, ' café,"\n', "0.29"), row("b", 1, "other", "1")])
    expected = case["expected"]
    alternative = {
        "balances": [dict(reversed(list(r.items()))) for r in reversed(expected["balances"])]
    }
    for ensure_ascii in (True, False):
        assert (
            check(
                TASK.checker,
                json.dumps(alternative, ensure_ascii=ensure_ascii, indent=2).encode(),
                expected,
            )["value"]
            == 1
        )
    for field, component in (
        ("delta_minor", "amounts"),
        ("left_count", "counts"),
        ("status", "statuses"),
    ):
        wrong = copy.deepcopy(expected)
        wrong["balances"][0][field] = (
            "matched" if field == "status" else wrong["balances"][0][field] + 1
        )
        verdict = check(TASK.checker, canonical(wrong), expected)
        assert verdict["value"] == 0 and verdict["components"][component] is False
        assert verdict["components"]["schema"] is True
    for bad in (True, 29.0, "29"):
        wrong = copy.deepcopy(expected)
        wrong["balances"][0]["left_minor"] = bad
        assert check(TASK.checker, canonical(wrong), expected)["components"] == {"schema": False}
    with pytest.raises(ValueError):
        check(TASK.checker, b"{}", {"balances": [{}]})


def test_semantic_split_rejects_reordering_and_equivalent_duplicate_spellings():
    material = generate_suite(TASK, 51, FEATURES[TASK.checker])
    value = material.model_dump(mode="json")
    source = value["development"][0]
    replacement = copy.deepcopy(source)
    replacement.update(id="different", group="different-group")
    for path in TASK.checker_inputs[:2]:
        rows = list(csv.reader(io.StringIO(replacement["files"][path], newline="")))
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerows(rows[:1] + rows[:0:-1] + rows[1:2])
        replacement["files"][path] = stream.getvalue()
    assert input_identity(
        TASK.checker, replacement["files"], TASK.checker_inputs
    ) == input_identity(TASK.checker, source["files"], TASK.checker_inputs)
    value["evaluation"][0] = replacement
    with pytest.raises(ValueError, match="duplicate semantic"):
        validate_materials(TASK, FileMaterials.model_validate(value))


def test_constructed_coverage_independent_oracle_fault_panel_and_separation():
    for seed in (1, 11, 73029, 90210):
        material = generate_suite(TASK, seed, FEATURES[TASK.checker])
        validation = verify_checker(TASK, material)
        evaluation = {c.id for c in material.evaluation}
        assert set(validation["fault_detection"]) == set(FAULTS)
        assert all(evaluation & set(cases) for cases in validation["fault_detection"].values())
        assert all(p["expected"] == p["observed"] for p in validation["probes"])
        public = builder_files(TASK, material)
        assert set(public) == {TASK.brief_path}
        assert all(
            c.id.encode() not in canonical({p: b.decode() for p, b in public.items()})
            for c in material.evaluation
        )
    _, checker_files = checker_identity(TASK)
    assert "reconciliation.py" in checker_files
    assert "reconciliation_templates.py" not in checker_files


def test_event_study_freeze_baseline_context_components_and_relocated_rescore(
    tmp_path, monkeypatch
):
    value = complete("reconciliation-v2")
    value["consumer_baseline"] = {"id": "no-package", "repeats": 1}
    value["control_rationale"]["no-package"] = "Discover whether cases reach the baseline ceiling."
    draft = draft_at(tmp_path, value)
    monkeypatch.setattr("yassa.native_runner.subprocess.run", lambda *a, **kw: None)
    root = prepare_native(draft / "study.json", tmp_path / "run", None, IMAGE)
    frozen = parse_json((root / "study.json").read_bytes())
    study = NativeStudyV2.model_validate(frozen["study"])
    store = EvidenceStore(root)
    evidence = store.get(frozen["preparation_id"])
    assert "preparer/reconciliation_templates.py" in evidence
    assert "checker/reconciliation.py" in evidence
    trials = {t["id"]: t for t in parse_json((root / "plan.json").read_bytes())["trials"]}

    def adapter(root, attempt_id, prompt, files, **kwargs):
        trial = trials[attempt_id]
        assert not any("preparer/" in n or "checker/" in n or "materials/" in n for n in files)
        if trial["role"] == "build":
            assert set(files) == {study.task.brief_path}
            brief = parse_json(files[study.task.brief_path])
            assert set(brief) == {"brief", "contract", "development"}
            output = {
                study.task.package_path + "/SKILL.md": (
                    f"---\nname: {study.task.package_name}\ndescription: Test fixture only.\n---\n"
                ).encode()
            }
        else:
            assert study.task.requirements in prompt
            data = {p: b.decode() for p, b in files.items() if p.startswith("input/")}
            assert set(data) == set(TASK.checker_inputs)
            if trial["parent"] is None:
                assert set(files) == set(data) and trial["build"] is None
            output = {
                study.task.result_path: canonical(oracle(TASK.checker, data, TASK.checker_inputs))
            }
        result = {
            "status": "completed",
            "duration_seconds": 1,
            "rejected_paths": [],
            "output_id": store.put(output),
        }
        write_new(root / "attempts" / attempt_id / "result.json", canonical(result))
        return result

    monkeypatch.setattr("yassa.native_runner.execute_native", adapter)
    report = execute_native_study(root, tmp_path / "unused-auth")
    scores = parse_json((report.parent / "scores.json").read_bytes())["scores"]
    assert len(scores) == 56 and all(s["value"] == 1 for s in scores)
    assert all(s["components"]["statuses"] for s in scores)
    analysis = parse_json((report.parent / "analysis.json").read_bytes())
    assert len(analysis["by_build"]) == 3 and len(analysis["by_baseline"]) == 1
    relocated = tmp_path / "relocated"
    shutil.copytree(root, relocated)
    assert verify_run(root) == verify_run(relocated)
    repeat = rescore_native(relocated, "repeat")
    assert (repeat.parent / "scores.json").read_bytes() == (
        report.parent / "scores.json"
    ).read_bytes()
