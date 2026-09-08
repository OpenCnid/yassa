import copy
import re

import pytest
from inspect_ai.log import read_eval_log

import yassa.app as app
from yassa.app import execute, load_frozen, prepare, rescore
from yassa.evidence import EvidenceStore, inventory, verify_run
from yassa.records import canonical, digest, parse_json


def read(path):
    return parse_json(path.read_bytes())


def test_both_routes_complete_with_explicit_failed_build_denominators(completed_run):
    summary = read(completed_run / "interpretations/original/analysis.json")
    scores = read(completed_run / "interpretations/original/scores.json")["scores"]
    assert summary["attempts"] == 36
    assert summary["builds"] == {"build_failed": 2, "package_ready": 4}
    assert len(scores) == 36
    assert sum(score["status"] == "dependency_failed" for score in scores) == 6
    assert {row["condition"] for row in summary["rows"]} == {"supplied", "prepared"}
    assert all(row["planned"] == 3 for row in summary["rows"])
    for row in summary["rows"]:
        if row["arm"] == "fixture-complete":
            assert row["successes"] == 3
        elif row["arm"] == "fixture-invalid":
            assert row["successes"] == 0
        else:
            assert row["successes"] == (1 if row["condition"] == "supplied" else 0)
    for score in scores:
        if score["status"] == "dependency_failed":
            assert score["attempt_id"] is None and score["output_id"] is None
            assert score["value"] == 0
    assert summary["usage"]["model_tokens"] is None
    assert summary["usage"]["cost_usd"] is None


def test_exact_inputs_packages_and_fresh_context_reach_inspect(completed_run):
    frozen, plan, _, materials = load_frozen(completed_run)
    store = EvidenceStore(completed_run)
    results = read(completed_run / "results.json")["trials"]
    common_hashes = {}
    sample_uuids = set()
    for trial in plan["trials"]:
        result = results[trial["id"]]
        if result["selected_attempt"] is None:
            continue
        attempt = read(completed_run / "attempts" / result["selected_attempt"] / "result.json")
        context = store.json(attempt["binding_id"], "binding.json")
        payload = parse_json(context["messages"][1]["content"])
        common = parse_json(payload["common"])
        key = (trial["condition"], trial["role"], trial["case"])
        common_hashes.setdefault(key, set()).add(context["common_sha256"])
        assert digest(payload["common"].encode()) == context["common_sha256"]
        assert context["study_id"] == frozen["id"] and context["plan_id"] == plan["id"]
        assert context["tools"] == [] and context["host_added_context"] == []
        assert context["subject_filesystem"] is None and context["subject_network"] is None
        assert "AGENTS.md" not in payload["common"] and ".codex" not in payload["common"]
        assert set(payload) == {"common", "treatment"}
        if trial["role"] == "consumer":
            parent = results[trial["parent_build"]]
            assert context["treatment_id"] == parent["package_id"]
            assert context["parent_attempt"] == parent["selected_attempt"]
        assert {name: text.encode() for name, text in payload["treatment"].items()} == store.get(
            context["treatment_id"]
        )
        if trial["role"] == "build":
            assert set(common) == {"stage", "contract", "brief", "development", "submission"}
            for case in materials[trial["condition"]].evaluation:
                assert f'"id":"{case.id}"' not in payload["common"]
            assert common["development"] == [
                case.model_dump(mode="json") for case in materials[trial["condition"]].development
            ]
        else:
            assert set(common) == {"stage", "contract", "rows"}
            case = next(
                case
                for case in materials[trial["condition"]].evaluation
                if case.id == trial["case"]
            )
            assert common["rows"] == [row.model_dump() for row in case.rows]
        # Check the actual framework boundary, not only our intended binding.
        # Inspect deduplicates event payloads into attachments inside .eval logs.
        log = read_eval_log(
            str(completed_run / attempt["inspect"]["log"]), resolve_attachments=True
        )
        sample = log.samples[0]
        assert not sample.target and not sample.files and sample.sandbox is None
        assert [(message.role, message.text) for message in sample.input] == [
            (message["role"], message["content"]) for message in context["messages"]
        ]
        assert len(sample.messages) == 3  # two initial messages, one fresh response
        model_events = [event for event in sample.events if event.event == "model"]
        assert len(model_events) == 1 and model_events[0].tools == []
        event = model_events[0]
        assert [(message.role, message.text) for message in event.input] == [
            (message["role"], message["content"]) for message in context["messages"]
        ]
        assert event.call.request["tools"] == []
        assert [
            (message["role"], message["content"]) for message in event.call.request["messages"]
        ] == [(message["role"], message["content"]) for message in context["messages"]]
        assert sample.uuid not in sample_uuids
        sample_uuids.add(sample.uuid)
    assert all(len(values) == 1 for values in common_hashes.values())


def test_rescore_preserves_evidence_and_is_byte_identical(completed_run, monkeypatch):
    before = inventory(completed_run)
    original = (completed_run / "interpretations/original/scores.json").read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("rescoring must never launch a subject")

    monkeypatch.setattr(app, "execute_attempt", forbidden)
    report = rescore(completed_run, "repeat-score")
    assert report.with_name("scores.json").read_bytes() == original
    assert inventory(completed_run) == before
    assert verify_run(completed_run)
    with pytest.raises(FileExistsError):
        rescore(completed_run, "repeat-score")
    assert (completed_run / "interpretations/original/scores.json").read_bytes() == original


def test_changed_scorer_requires_reason_and_preserves_original(completed_run, monkeypatch):
    original = (completed_run / "interpretations/original/scores.json").read_bytes()
    old_identity, sources = app.scorer_identity()
    monkeypatch.setattr(app, "scorer_identity", lambda: ({**old_identity, "id": "f" * 64}, sources))
    monkeypatch.setattr(
        app,
        "check_work",
        lambda *_: {
            "value": 0,
            "components": {},
            "reason": "deliberately changed checker test double",
        },
    )
    with pytest.raises(ValueError, match="scorer changed"):
        rescore(completed_run, "unexplained")
    report = rescore(completed_run, "corrected", "test-only changed checker behavior")
    revised = read(report.with_name("scores.json"))
    assert revised["revision_reason"] == "test-only changed checker behavior"
    assert all(score["value"] == 0 for score in revised["scores"])
    assert (completed_run / "interpretations/original/scores.json").read_bytes() == original


def test_report_links_resolve(completed_run):
    report = completed_run / "interpretations/original/report.md"
    for link in re.findall(r"\]\(([^)]+)\)", report.read_text(encoding="utf-8")):
        assert (report.parent / link).is_file(), link


def test_sealed_tampering_detected(completed_run, tmp_path):
    import shutil

    relocated = tmp_path / "copy"
    shutil.copytree(completed_run, relocated)
    assert verify_run(relocated) == verify_run(completed_run)
    rescore(relocated, "relocated")
    with (relocated / "plan.json").open("ab") as file:
        file.write(b" ")
    with pytest.raises(ValueError, match="changed since sealing"):
        rescore(relocated, "tampered")


def run_small(study_data, write_study, tmp_path, *, failures=0, retries=1, tokens=4096):
    data = copy.deepcopy(study_data)
    data["conditions"] = [data["conditions"][1]]
    data["conditions"][0]["evaluation_cases"] = 1
    data["arms"] = [
        {"id": "fixture-fault", "fixture_behavior": "complete", "infrastructure_failures": failures}
    ]
    data["limits"].update(infrastructure_retries=retries, max_output_tokens=tokens)
    root = prepare(write_study(data), tmp_path / "run")
    execute(root)
    return root


def test_infrastructure_retry_retains_first_attempt(study_data, write_study, tmp_path):
    root = run_small(study_data, write_study, tmp_path, failures=1)
    selections = read(root / "results.json")
    assert len(selections["attempts"]) == 5  # direct+build: failure then retry; consumer: once
    attempts = [
        read(root / "attempts" / attempt / "result.json") for attempt in selections["attempts"]
    ]
    failures = [attempt for attempt in attempts if attempt["status"] == "infrastructure_failure"]
    assert len(failures) == 2
    for failed in failures:
        assert (root / failed["inspect"]["log"]).is_file()
        assert any(attempt["retry_of"] == failed["id"] for attempt in attempts)
    scores = read(root / "interpretations/original/scores.json")["scores"]
    assert all(score["value"] == 1 for score in scores)


def test_exhausted_infrastructure_stays_missing(study_data, write_study, tmp_path):
    root = run_small(study_data, write_study, tmp_path, failures=2, retries=0)
    scores = read(root / "interpretations/original/scores.json")["scores"]
    assert {score["status"] for score in scores} == {"infrastructure_failure", "dependency_missing"}
    assert all(score["value"] is None for score in scores)
    summary = read(root / "interpretations/original/analysis.json")
    assert sum(row["missing"] for row in summary["rows"]) == 2
    assert sum(row["task_failures"] for row in summary["rows"]) == 0
    assert sum(row["planned"] for row in summary["rows"]) == 2


def test_output_cap_retains_failed_work_without_retry(study_data, write_study, tmp_path):
    root = run_small(study_data, write_study, tmp_path, tokens=1)
    selections = read(root / "results.json")
    assert len(selections["attempts"]) == 2
    for attempt_id in selections["attempts"]:
        attempt = read(root / "attempts" / attempt_id / "result.json")
        assert attempt["status"] == "budget_exhausted"
        assert attempt["usage"]["simulated_output_units"] <= 1
        assert attempt["usage"]["provider_calls"] == 1
    assert all(
        score["value"] == 0
        for score in read(root / "interpretations/original/scores.json")["scores"]
    )


def test_changed_frozen_plan_rejected_without_launch(write_study, tmp_path):
    root = prepare(write_study(), tmp_path / "run")
    (root / "plan.json").write_bytes(canonical({"tampered": True}))
    with pytest.raises(ValueError, match="prepared evidence changed"):
        execute(root)
    assert not (root / "attempts").exists()


def test_runtime_change_rejected_without_launch(write_study, tmp_path, monkeypatch):
    root = prepare(write_study(), tmp_path / "run")
    versions = app.runtime_versions()
    monkeypatch.setattr(app, "runtime_versions", lambda: {**versions, "inspect_ai": "changed"})
    with pytest.raises(ValueError, match="runtime dependencies changed"):
        execute(root)
    assert not (root / "attempts").exists()


def test_inspect_time_limit_is_observed(study_data, write_study, tmp_path, monkeypatch):
    import asyncio

    from yassa.simulation import FixtureAPI

    original = FixtureAPI.generate

    async def delayed(self, *args, **kwargs):
        await asyncio.sleep(2)
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(FixtureAPI, "generate", delayed)
    study_data["kinds"] = ["direct"]
    study_data["limits"]["time_limit_seconds"] = 1
    root = run_small(study_data, write_study, tmp_path)
    attempt_id = read(root / "results.json")["attempts"][0]
    attempt = read(root / "attempts" / attempt_id / "result.json")
    assert attempt["status"] == "budget_exhausted"
    assert attempt["limit"]["type"] == "time"
