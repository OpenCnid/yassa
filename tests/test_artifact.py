"""Artifact-specific data isolation, fixed scoring denominator and product lifecycle."""

from pathlib import Path

import pytest

from yassa import artifact_runner as runner
from yassa.artifact_contracts import ArtifactRequest, artifact_plan
from yassa.artifact_testing import compare_cases, junit_cases
from yassa.evidence import EvidenceStore, verify_run, write_new
from yassa.records import canonical, digest, parse_json


def request_at(tmp_path):
    bundles = {
        "public": {"spec.md": b"Implement addition."},
        "reference": {"src/toy.py": b"def add(a,b): return a+b\n"},
        "tests": {"tests/test_toy.py": b"from toy import add\n", "pyproject.toml": b""},
    }
    data = {
        "schema_version": 1,
        "id": "toy",
        "question": "Can skills help?",
        "prompt": "Implement the supplied spec.",
        "provenance": "Synthetic acceptance fixture.",
        "role": {
            "adapter": "native-codex-cli",
            "model": "gpt-6-astra",
            "image": "sha256:" + "a" * 64,
            "reasoning_effort": "xhigh",
            "timeout_seconds": 30,
        },
        "arms": [{"id": "plain", "rationale": "Common request."}],
        "repeats": 1,
        "schedule_seed": 17,
        "max_attempts": 1,
        "max_scheduled_seconds": 30,
        "test_timeout_seconds": 10,
    }
    for name, files in bundles.items():
        path = tmp_path / name
        for n, body in files.items():
            write_new(path / n, body)
        data[name] = {"path": str(path), "files": {n: digest(b) for n, b in files.items()}}
    return data


def test_allocation_and_protected_overlap(tmp_path):
    data = request_at(tmp_path)
    assert artifact_plan(ArtifactRequest.model_validate(data))["reserved_seconds"] == 30
    data["max_attempts"] = 0
    with pytest.raises(ValueError):
        ArtifactRequest.model_validate(data)
    data["max_attempts"] = 1
    data["public"]["files"]["spec.md"] = next(iter(data["reference"]["files"].values()))
    with pytest.raises(ValueError, match="overlap"):
        ArtifactRequest.model_validate(data)


def test_junit_keeps_failures_skips_and_missing_in_denominator():
    raw = (
        b'<testsuites><testsuite><testcase classname="t" name="a"/>'
        b'<testcase classname="t" name="b"><skipped/></testcase>'
        b'<testcase classname="t" name="c"><failure/></testcase></testsuite></testsuites>'
    )
    candidate = junit_cases(raw)
    score = compare_cases(
        {"t::a": "pass", "t::b": "pass", "t::c": "failure", "t::d": "pass"}, candidate
    )
    assert score["passed"] == 1 and score["total"] == 4
    assert score["cases"]["t::d"] == "missing"
    with pytest.raises(ValueError, match="duplicate"):
        junit_cases(b'<testsuite><testcase name="a"/><testcase name="a"/></testsuite>')
    with pytest.raises(ValueError):
        junit_cases(b"<!DOCTYPE a><testsuite/>")


def test_artifact_lifecycle_and_subject_allowlist(tmp_path, monkeypatch):
    data = request_at(tmp_path)
    source = tmp_path / "skills"
    skill = b"---\nname: toy\ndescription: Implement toy tasks.\n---\nThink carefully.\n"
    write_new(source / "toy/SKILL.md", skill)
    data["sources"] = [
        {"id": "skill", "path": str(source), "files": {"toy/SKILL.md": digest(skill)}}
    ]
    data["arms"].append(
        {
            "id": "skilled",
            "rationale": "Treatment.",
            "sources": ["skill"],
            "invocation": "Use $toy.",
        }
    )
    data.update(max_attempts=2, max_scheduled_seconds=60)
    request = tmp_path / "request.json"
    write_new(request, canonical(data))
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: None)

    def fake_tests(destination, image, project, tests, timeout):
        assert "tests/test_toy.py" in tests
        destination.mkdir()
        return {"status": "tested", "exit_code": 0, "cases": {"t::a": "pass"}}

    monkeypatch.setattr(runner, "test_artifact", fake_tests)
    root = tmp_path / "run"
    runner.prepare_artifact(request, root)
    seen = []

    def fake_native(root, aid, prompt, files, **kwargs):
        assert "input/spec.md" in files
        assert all(n.startswith(("input/", ".agents/skills/")) for n in files)
        assert not any(n.endswith(("toy.py", "test_toy.py", "pyproject.toml")) for n in files)
        seen.append(set(files))
        record = {
            "status": "completed",
            "duration_seconds": 1,
            "output_id": EvidenceStore(root).put({"output/project/src/toy.py": b"pass"}),
        }
        write_new(root / "attempts" / aid / "result.json", canonical(record))
        return record

    monkeypatch.setattr(runner, "execute_native", fake_native)
    auth = tmp_path / "auth.json"
    write_new(auth, b"placeholder")
    runner.execute_artifact(root, auth)
    verify_run(root)
    assert sorted(map(len, seen)) == [1, 2]
    report = runner.score_artifact(root, "original")
    scores = parse_json((report.parent / "scores.json").read_bytes())["scores"]
    assert len(scores) == 2 and all(s["passed"] == 1 for s in scores)
    with pytest.raises(FileExistsError):
        runner.score_artifact(root, "original")


def test_pin_drift_rejected_before_freeze(tmp_path, monkeypatch):
    data = request_at(tmp_path)
    Path(data["public"]["path"], "spec.md").write_bytes(b"changed")
    path = tmp_path / "request.json"
    write_new(path, canonical(data))
    with pytest.raises(ValueError, match="pin mismatch"):
        runner.prepare_artifact(path, tmp_path / "run")
    assert not (tmp_path / "run").exists()
