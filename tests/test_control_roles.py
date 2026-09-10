"""Supported CLI composition with deterministic adapter doubles and explicit faults."""

import shutil
import sys

import pytest
from test_execution_roles import direct_request, grade_request, solve

from yassa.app import main
from yassa.control import cancel, control_status, read_json, resource_status
from yassa.direct_runner import prepare_direct, rescore_direct
from yassa.evidence import verify_run, write_new
from yassa.grading import report_grades
from yassa.records import canonical, parse_json


def cli(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["yassa", *map(str, args)])
    return main()


def test_cli_direct_cancel_resume_and_external_grade_retry_share_budget(tmp_path, monkeypatch):
    resources = tmp_path / "resources"
    assert (
        cli(
            monkeypatch,
            "resource-init",
            resources,
            "--max-attempts",
            20,
            "--max-scheduled-seconds",
            600,
        )
        == 0
    )
    path = tmp_path / "direct.json"
    path.write_bytes(canonical(direct_request(tmp_path)))
    root = prepare_direct(path, tmp_path / "direct").parent
    seen = []

    def api(directory, role, messages, stage):
        payload = parse_json(messages[1].text)
        seen.append((stage, directory))
        if "rubric" in payload:
            correct = "totals" in payload["submitted_output"]
            response = {
                "components": {c["id"]: correct for c in payload["rubric"]},
                "rationale": "Recorded format predicate.",
            }
            status = "provider_failure" if len(seen) == 9 else "completed"
        else:
            response, status = solve(payload["files"]), "completed"
            if len(seen) == 1:
                cancel(root, "exercise cancellation while active")
        result = {
            "status": status,
            "completion": canonical(response).decode(),
            "duration_seconds": 1,
            "usage": {"input_tokens": 7, "output_tokens": 3},
        }
        write_new(directory / "request.json", canonical(payload))
        write_new(directory / "result.json", canonical(result))
        return result

    monkeypatch.setattr("yassa.direct_runner.call_api", api)
    monkeypatch.setattr("yassa.grading.call_api", api)
    assert cli(monkeypatch, "direct-execute", root, "--resources", resources) == 3
    assert len(seen) == 1
    assert cli(monkeypatch, "run-status", root) == 0
    assert cli(monkeypatch, "direct-execute", root, "--resources", resources, "--resume") == 0
    assert len(seen) == 8
    scores = (root / "interpretations/original/scores.json").read_bytes()
    assert all(s["value"] == 1 for s in parse_json(scores)["scores"])
    source_seal = verify_run(root)
    grading, request = tmp_path / "grading", tmp_path / "grading-request.json"
    request.write_bytes(canonical(grade_request()))
    assert cli(monkeypatch, "grade-prepare", root, request, "--grade-dir", grading) == 0
    assert (
        cli(
            monkeypatch,
            "grade-execute",
            grading,
            "--resources",
            resources,
            "--infrastructure-retries",
            1,
        )
        == 3
    )
    assert len(seen) == 9  # Failed calibration has not released any source work.
    assert (
        cli(
            monkeypatch,
            "grade-execute",
            grading,
            "--resources",
            resources,
            "--resume",
            "--retry",
            "work-0001",
            "--reason",
            "simulated provider outage",
        )
        == 0
    )
    assert len(seen) == 19 and len({path for _, path in seen}) == 19
    assert (grading / "calls/0001/result.json").exists()
    assert (grading / "calls/0001-retry-1/result.json").exists()
    grades = read_json(grading / "interpretations/original/scores.json")
    assert grades["summary"]["planned"] == grades["summary"]["passed"] == 8
    state = resource_status(resources)
    assert state["remaining_attempts"] == 1
    assert state["remaining_scheduled_seconds"] == 30
    assert {key: value["attempts"] for key, value in state["by_role"].items()} == {
        "calibration": 3,
        "direct": 8,
        "grading": 8,
    }
    assert cli(monkeypatch, "resource-status", resources) == 0
    assert cli(monkeypatch, "run-report", grading) == 0
    assert control_status(grading)["planned"] == 8
    assert verify_run(root) == source_seal
    assert (root / "interpretations/original/scores.json").read_bytes() == scores
    moved = tmp_path / "relocated-grading"
    shutil.copytree(grading, moved)
    report_grades(moved, "replay")
    assert (moved / "interpretations/replay/scores.json").read_bytes() == (
        grading / "interpretations/original/scores.json"
    ).read_bytes()
    rescore_direct(root, "replay")
    assert (root / "interpretations/replay/scores.json").read_bytes() == scores


def test_preparation_charges_shared_budget_before_model_call(tmp_path, monkeypatch):
    from test_general_preparation import request

    from yassa.control import resource_init
    from yassa.general_contracts import GeneralRequest, TaskProposal
    from yassa.preparation_model import PreparationCalls

    settings = GeneralRequest.model_validate(request()).preparation
    resources = tmp_path / "resources"
    resource_init(resources, {"max_attempts": 1, "max_scheduled_seconds": settings.timeout_seconds})
    calls = PreparationCalls(settings, tmp_path / "calls", resources=resources)
    seen = []

    def adapter(self, stage, instructions, payload, schema, **kwargs):
        self.count += 1
        seen.append(stage)
        write_new(
            self.root / f"{self.count:02d}" / "response.json",
            canonical({"usage": {"input_tokens": 17, "output_tokens": 9}}),
        )
        raise ValueError("invalid proposal retained")

    monkeypatch.setattr(PreparationCalls, "_call", adapter)
    import pytest

    with pytest.raises(ValueError, match="invalid proposal"):
        calls.call("prepare-task", "instructions", {}, TaskProposal)
    with pytest.raises(ValueError, match="exhausted"):
        calls.call("prepare-task", "instructions", {}, TaskProposal)
    assert seen == ["prepare-task"] and calls.count == 1
    state = resource_status(resources)
    assert state["by_role"]["preparation"]["attempts"] == 1
    assert state["attempts"][0]["outcome"]["usage"]["output_tokens"] == 9


@pytest.mark.parametrize("lost_return", [False, True])
def test_native_resume_reuses_package_and_keeps_missing_dependency_denominators(
    tmp_path, monkeypatch, lost_return
):
    from test_native_v2 import freeze, prepared, request

    from yassa.evidence import EvidenceStore
    from yassa.native import execute_native_study, rescore_native

    value = request("totals")
    value["arms"] = value["arms"][:1]
    value["arms"][0]["builds"] = 1
    value["consumer_repeats"] = 1
    root = freeze(tmp_path, monkeypatch, value)
    study, materials = prepared(value)
    trials = {t["id"]: t for t in read_json(root / "plan.json")["trials"]}
    store, seen = EvidenceStore(root), []

    def adapter(root, aid, prompt, files, **kwargs):
        trial = trials[aid]
        seen.append(aid)
        if trial["role"] == "build":
            output = {
                study.task.package_path + "/SKILL.md": (
                    f"---\nname: {study.task.package_name}\ndescription: Complete task.\n---\n"
                    + aid
                ).encode()
            }
            status = "budget_exhausted"
        else:
            case = next(
                c for c in materials[trial["condition"]].evaluation if c.id == trial["case"]
            )
            assert (
                trial["parent"].encode()
                in files[f".agents/skills/{study.task.package_name}/SKILL.md"]
            )
            output = {study.task.result_path: canonical(case.expected)}
            status = "completed"
        result = {
            "id": aid,
            "status": status,
            "output_id": store.put(output),
            "rejected_paths": [],
            "duration_seconds": 1,
        }
        if len(seen) == 1 and lost_return:
            write_new(root / "attempts" / aid / "partial.log", b"partial native evidence")
            raise SystemExit("no adapter return")
        write_new(root / "attempts" / aid / "result.json", canonical(result))
        if len(seen) == 1:
            raise SystemExit("crash between adapter and controller return")
        return result

    monkeypatch.setattr("yassa.native_runner.execute_native", adapter)
    import pytest

    with pytest.raises(SystemExit):
        execute_native_study(root, tmp_path / "unused-auth")
    disposition = (
        {"mark_missing": [seen[0]], "reason": "uncertain build retained as missing"}
        if lost_return
        else {}
    )
    report = execute_native_study(root, tmp_path / "unused-auth", resume=True, **disposition)
    assert len(seen) == len(set(seen)) == (4 if lost_return else 6)
    scores = (report.parent / "scores.json").read_bytes()
    assert len(parse_json(scores)["scores"]) == 4
    assert sum(row["value"] == 1 for row in parse_json(scores)["scores"]) == (
        2 if lost_return else 4
    )
    assert sum(row["status"] == "dependency_missing" for row in parse_json(scores)["scores"]) == (
        2 if lost_return else 0
    )
    assert len(
        {
            r["package_id"]
            for r in read_json(root / "results.json")["trials"].values()
            if "package_id" in r
        }
    ) == (1 if lost_return else 2)
    replay = rescore_native(root, "repeat")
    assert (replay.parent / "scores.json").read_bytes() == scores
