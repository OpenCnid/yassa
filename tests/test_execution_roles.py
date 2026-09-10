"""Actual Inspect API tasks with simulated providers; no live vendor evidence."""

import copy
import shutil
import sys
from types import SimpleNamespace

import pytest
from inspect_ai.model import GenerateConfig, ModelAPI, ModelOutput, get_model, modelapi
from test_native_v2 import IMAGE
from test_native_v2 import request as native_request

from yassa.app import main
from yassa.direct_contracts import DirectRequest
from yassa.direct_runner import execute_direct, load_direct, prepare_direct, rescore_direct
from yassa.evidence import EvidenceStore, verify_run, write_new
from yassa.grading import GradeRequest, execute_grades, prepare_grades, report_grades
from yassa.records import canonical, digest, parse_json
from yassa.role_api import ApiRole, api_identity


def solve(files):
    rows = parse_json(files["input/ledger.json"])["rows"]
    totals = {}
    for row in rows:
        name = row["account"].strip(" ").lower()
        item = totals.setdefault(name, {"account": name, "net_cents": 0, "count": 0})
        item["net_cents"] += row["cents"]
        item["count"] += 1
    return {"totals": list(totals.values())}


class RoleFixture(ModelAPI):
    seen = []
    mode = None

    def __init__(self, model_name, base_url=None, api_key=None, config=None):
        super().__init__(model_name, config=config or GenerateConfig())

    async def generate(self, input, tools, tool_choice, config):
        assert len(input) == 2 and not tools
        assert config.max_retries == 0 and config.max_tokens == 2000
        payload = parse_json(input[1].text)
        self.seen.append(payload)
        if "rubric" in payload:
            assert set(payload) == {
                "rubric",
                "task_requirements",
                "input_files",
                "submitted_output",
            }
            assert "secret-arm" not in canonical(payload).decode()
            correct = "totals" in payload["submitted_output"]
            if self.mode == "calibration":
                correct = not correct
            if self.mode == "malformed" and len(self.seen) > 2:
                return ModelOutput.from_content(self.model_name, "{")
            result = {
                "components": {c["id"]: correct for c in payload["rubric"]},
                "rationale": "Simulated recorded format judgment.",
            }
        else:
            assert set(payload) == {"files"}
            assert "input/task.json" not in payload["files"]
            result = solve(payload["files"])
        return ModelOutput.from_content(self.model_name, canonical(result).decode())


@modelapi(name="yassa_role_test")
def role_fixture():
    return RoleFixture


@pytest.fixture(autouse=True)
def simulated(monkeypatch):
    RoleFixture.seen, RoleFixture.mode = [], None
    monkeypatch.setattr(
        "yassa.role_api.get_model",
        lambda model, **kw: get_model("yassa_role_test/fixture", memoize=False),
    )
    monkeypatch.setattr(
        "yassa.direct_runner.subprocess", SimpleNamespace(run=lambda *a, **kw: None)
    )


def direct_request(tmp_path, native=False):
    source = tmp_path / "task.json"
    source.write_bytes(canonical(native_request("totals")))
    role = (
        {
            "adapter": "native-codex-cli",
            "model": "gpt-test",
            "image": IMAGE,
            "reasoning_effort": "low",
            "timeout_seconds": 30,
        }
        if native
        else {
            "adapter": "inspect-api",
            "model": "openai/gpt-test",
            "max_output_tokens": 2000,
            "timeout_seconds": 30,
        }
    )
    return {
        "schema_version": 1,
        "id": "direct-test",
        "question": "Compare declared direct conditions.",
        "task_source": {"path": str(source), "sha256": digest(source.read_bytes())},
        "role": role,
        "arms": [
            {"id": "secret-arm", "rationale": "Unassisted direct work"},
            {
                "id": "checked",
                "invocation": "Check the complete output.",
                "rationale": "Prompt variation",
            },
        ],
        "repeats": 1,
        "schedule_seed": 0,
        "max_attempts": 8,
        "max_scheduled_seconds": 240,
    }


def direct_run(tmp_path, monkeypatch, native=False):
    value = direct_request(tmp_path, native)
    path = tmp_path / "direct.json"
    path.write_bytes(canonical(value))
    root = prepare_direct(path, tmp_path / "direct").parent
    frozen, request, task, materials, plan = load_direct(root)
    common = {}

    def adapter(root, rid, prompt, files, **kwargs):
        trial = next(t for t in plan["trials"] if t["id"] == rid)
        assert trial["role"] == "direct" and trial["parent"] is None and trial["build"] is None
        assert kwargs["timeout"] == 30
        assert set(files) == {"input/ledger.json"}
        assert task.requirements in prompt and "$ledger-totals" not in prompt
        binding = parse_json((root / "bindings" / (rid + ".json")).read_bytes())
        common.setdefault((trial["condition"], trial["case"]), set()).add(binding["common_id"])
        output = solve(files)
        result = {
            "status": "completed",
            "output_id": EvidenceStore(root).put({task.result_path: canonical(output)}),
            "duration_seconds": 1,
        }
        write_new(root / "attempts" / rid / "result.json", canonical(result))
        return result

    monkeypatch.setattr("yassa.direct_runner.execute_native", adapter)
    report = execute_direct(root, tmp_path / "unused-auth")
    assert all(len(s) == 1 for s in common.values())
    return root, report


@pytest.mark.parametrize("native", [False, True])
def test_direct_context_scoring_and_relocation(tmp_path, monkeypatch, native):
    root, report = direct_run(tmp_path, monkeypatch, native)
    scores = parse_json((report.parent / "scores.json").read_bytes())["scores"]
    assert len(scores) == 8 and all(s["value"] == 1 for s in scores)
    assert all(
        s["build"] is None and s["parent"] is None and s["package_id"] is None for s in scores
    )
    assert len(RoleFixture.seen) == (0 if native else 8)
    original = (report.parent / "scores.json").read_bytes()
    relocated = tmp_path / "relocated"
    shutil.copytree(root, relocated)
    assert verify_run(relocated) == verify_run(root)
    replay = rescore_direct(relocated, "repeat")
    assert (replay.parent / "scores.json").read_bytes() == original
    with pytest.raises(ValueError, match="already started"):
        execute_direct(root)


def grade_request():
    return {
        "schema_version": 1,
        "id": "grade",
        "role": {
            "adapter": "inspect-api",
            "model": "anthropic/claude-test",
            "max_output_tokens": 2000,
            "timeout_seconds": 30,
        },
        "criteria": [{"id": "format", "description": "The output is an object containing totals."}],
        "calibration": [
            {
                "id": "good",
                "input_files": {},
                "submitted_output": '{"totals": []}',
                "expected": {"format": True},
                "rationale": "Valid minimal format",
            },
            {
                "id": "bad",
                "input_files": {},
                "submitted_output": "{}",
                "expected": {"format": False},
                "rationale": "Missing the required property",
            },
        ],
        "scope": "A bounded format dimension, separate from arithmetic correctness.",
        "max_calls": 10,
        "max_scheduled_seconds": 300,
    }


@pytest.mark.parametrize("failure", [None, "calibration", "malformed"])
def test_external_grading_blinding_gate_missingness_and_offline_replay(
    tmp_path, monkeypatch, failure
):
    root, source_report = direct_run(tmp_path, monkeypatch, native=True)
    original = (source_report.parent / "scores.json").read_bytes()
    source_seal = verify_run(root)
    path = tmp_path / "grade-request.json"
    path.write_bytes(canonical(grade_request()))
    destination = prepare_grades(root, path, tmp_path / "grades").parent
    RoleFixture.mode = failure
    report = execute_grades(destination)
    scores = parse_json((report.parent / "scores.json").read_bytes())
    assert scores["summary"]["planned"] == 8
    assert scores["summary"]["missing"] == (0 if failure is None else 8)
    assert len(RoleFixture.seen) == (2 if failure == "calibration" else 10)
    assert verify_run(root) == source_seal
    assert (source_report.parent / "scores.json").read_bytes() == original
    relocated = tmp_path / "relocated-grades"
    shutil.copytree(destination, relocated)
    replay = report_grades(relocated, "repeat")
    assert (replay.parent / "scores.json").read_bytes() == (
        report.parent / "scores.json"
    ).read_bytes()


def test_admission_identity_and_calibration_rejections(tmp_path, monkeypatch):
    value = direct_request(tmp_path)
    value["max_attempts"] = 7
    path = tmp_path / "request.json"
    path.write_bytes(canonical(value))
    with pytest.raises(ValueError, match="exceeding caps"):
        prepare_direct(path, tmp_path / "blocked")
    assert not (tmp_path / "blocked").exists()
    for model in ["openrouter/anthropic/claude", "anthropic/gpt-test", "custom/reviewer"]:
        with pytest.raises(ValueError):
            api_identity(model)
    for model in ["openai/gpt-test", "anthropic/claude-test", "google/gemini-test"]:
        assert ApiRole(adapter="inspect-api", model=model, max_output_tokens=100, timeout_seconds=1)
    grade = grade_request()
    grade["calibration"][1]["expected"]["format"] = True
    with pytest.raises(ValueError, match="successful and failing"):
        GradeRequest.model_validate(grade)
    packed = copy.deepcopy(value)
    packed["arms"][0]["sources"] = ["absent"]
    with pytest.raises(ValueError, match="declared pins"):
        DirectRequest.model_validate(packed)


def test_same_family_grading_refused_before_calls(tmp_path, monkeypatch):
    root, _ = direct_run(tmp_path, monkeypatch, native=True)
    value = grade_request()
    value["role"]["model"] = "openai/gpt-other"
    path = tmp_path / "grade.json"
    path.write_bytes(canonical(value))
    with pytest.raises(ValueError, match="different vendor/model family"):
        prepare_grades(root, path, tmp_path / "blocked")
    assert not RoleFixture.seen and not (tmp_path / "blocked").exists()


def test_public_role_commands(tmp_path, monkeypatch, capsys):
    for kind in ("direct", "grading"):
        monkeypatch.setattr(sys, "argv", ["yassa", "role-schema", kind])
        assert main() == 0
        assert parse_json(capsys.readouterr().out)["type"] == "object"


def test_direct_pinned_native_skill_and_failed_work(tmp_path, monkeypatch):
    value = direct_request(tmp_path, native=True)
    pack = tmp_path / "external-pack"
    skill = b"---\nname: checker\ndescription: Check supplied totals.\n---\nCheck every row.\n"
    write_new(pack / "checker/SKILL.md", skill)
    value["sources"] = [
        {"id": "pinned", "path": str(pack), "files": {"checker/SKILL.md": digest(skill)}}
    ]
    value["arms"][1].update(sources=["pinned"], invocation="Use $checker.")
    path = tmp_path / "direct-request.json"
    path.write_bytes(canonical(value))
    root = prepare_direct(path, tmp_path / "treated").parent
    _, _, task, _, plan = load_direct(root)

    def adapter(root, rid, prompt, files, **kwargs):
        trial = next(t for t in plan["trials"] if t["id"] == rid)
        if trial["arm"] == "checked":
            assert files[".agents/skills/checker/SKILL.md"] == skill
            assert prompt.startswith("Use $checker.")
            status, output = "completed", b"{}"
        else:
            assert set(files) == {"input/ledger.json"}
            status, output = "harness_failure", b"{}"
        result = {
            "status": status,
            "output_id": EvidenceStore(root).put({task.result_path: output}),
        }
        write_new(root / "attempts" / rid / "result.json", canonical(result))
        return result

    monkeypatch.setattr("yassa.direct_runner.execute_native", adapter)
    report = execute_direct(root, tmp_path / "unused-auth")
    rows = parse_json((report.parent / "scores.json").read_bytes())["scores"]
    assert sum(s["value"] == 0 for s in rows) == 4
    assert sum(s["value"] is None for s in rows) == 4
    value["role"] = {
        "adapter": "inspect-api",
        "model": "anthropic/claude-test",
        "max_output_tokens": 2000,
        "timeout_seconds": 30,
    }
    value["sources"][0]["executable"] = ["checker/SKILL.md"]
    with pytest.raises(ValueError, match="text packs only"):
        DirectRequest.model_validate(value)


def test_cli_direct_to_grading_report(tmp_path, monkeypatch, capsys):
    value = direct_request(tmp_path)
    path = tmp_path / "direct-request.json"
    path.write_bytes(canonical(value))
    root, grades = tmp_path / "run", tmp_path / "grades"
    request_path = tmp_path / "grade-request.json"
    request_path.write_bytes(canonical(grade_request()))

    def cli(*args):
        monkeypatch.setattr(sys, "argv", ["yassa", *map(str, args)])
        assert main() == 0, capsys.readouterr().err
        capsys.readouterr()

    cli("direct-prepare", path, "--run-dir", root)
    cli("direct-execute", root)
    cli("verify", root)
    cli("direct-rescore", root, "--label", "repeat")
    # Independent reviewer stage has fresh contexts; simulated provider call trace reset.
    RoleFixture.seen = []
    cli("grade-prepare", root, request_path, "--grade-dir", grades)
    cli("grade-execute", grades)
    cli("verify", grades)
    cli("grade-report", grades, "--label", "repeat")
    assert len(RoleFixture.seen) == 10
    assert (grades / "interpretations/original/scores.json").read_bytes() == (
        grades / "interpretations/repeat/scores.json"
    ).read_bytes()
