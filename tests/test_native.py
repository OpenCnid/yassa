import json

import pytest

from yassa.evidence import EvidenceStore
from yassa.native import NativeStudy, build_input, native_package, native_usage, snapshot_source
from yassa.prepare import prepare_condition
from yassa.records import canonical
from yassa.study import Condition


def test_native_build_input_keeps_evaluation_out(tmp_path):
    materials, _, _ = prepare_condition(
        Condition(id="prepared", route="yassa-prepared", request="fixture", seed=21), tmp_path
    )
    body = json.loads(build_input(materials))
    assert set(body) == {"brief", "contract", "development"}
    assert body["development"] == [c.model_dump(mode="json") for c in materials.development]
    for case in materials.evaluation:
        assert case.id not in build_input(materials).decode()
        assert case.rows[0].account not in build_input(materials).decode()


def test_source_snapshot_is_explicit_and_byte_preserving(tmp_path):
    skill = tmp_path / "better-skill-creator"
    for name, content in {
        "SKILL.md": b"test\r\n",
        "scripts/tool.py": b"print('unchanged')\n",
        "tests/fixtures/other-skill/SKILL.md": b"never discover",
        ".env": b"not a source file",
        "scripts/__pycache__/tool.pyc": b"cache",
    }.items():
        path = skill / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    files, provenance = snapshot_source(tmp_path, ("better-skill-creator",))
    assert files == {
        "better-skill-creator/SKILL.md": b"test\r\n",
        "better-skill-creator/scripts/tool.py": b"print('unchanged')\n",
    }
    assert "better-skill-creator/tests/fixtures/other-skill/SKILL.md" in provenance["excluded"]


def test_native_package_accepts_multiline_yaml_crlf_and_preserves_mode(tmp_path):
    store = EvidenceStore(tmp_path)
    exported = {
        "output/account-totals/SKILL.md": (
            b'---\r\nname: "account-totals"\r\ndescription: >\r\n  Calculate totals.\r\n---\r\n'
        ),
        "output/account-totals/scripts/run.py": b"print(1)\n",
        "output/notes.md": b"not in package",
    }
    source_id = store.put(exported, executable=["output/account-totals/scripts/run.py"])
    package_id = native_package(exported, store, source_id)
    assert set(store.get(package_id)) == {"SKILL.md", "scripts/run.py"}
    manifest = json.loads((tmp_path / "artifacts" / package_id / "manifest.json").read_text())
    assert manifest["files"][1]["executable"] is True


@pytest.mark.parametrize(
    "body",
    [
        b"missing header",
        b"---\nname: wrong\ndescription: valid\n---\n",
        b"---\nname: account-totals\ndescription: false\n---\n",
        b"---\nname: account-totals\ndescription: ''\n---\n",
    ],
)
def test_native_package_rejects_invalid_loading_contract(tmp_path, body):
    store = EvidenceStore(tmp_path)
    files = {"output/account-totals/SKILL.md": body}
    artifact = store.put(files)
    with pytest.raises(ValueError):
        native_package(files, store, artifact)


def test_usage_deduplicates_responses_across_parent_child_logs():
    first = {
        "type": "token_usage_record",
        "payload": {
            "response_id": "first",
            "usage": {"input_tokens": 100, "output_tokens": 5},
        },
    }
    second = {
        "type": "token_usage_record",
        "payload": {
            "response_id": "second",
            "usage": {"input_tokens": 40, "output_tokens": 2},
        },
    }
    result = native_usage(
        {
            "sessions/parent.jsonl": canonical(first) + canonical(second),
            "sessions/child.jsonl": canonical(second),
        }
    )
    assert result["totals"] == {"input_tokens": 140, "output_tokens": 7}
    assert result["native_usage_records"] == 2
    assert len(result["sessions"]) == 2


def test_native_study_rejects_missing_preparation_route():
    data = {
        "schema_version": 1,
        "id": "native-test",
        "question": "fixture",
        "scope": "synthetic-fixture",
        "runtime": "native-codex-cli",
        "model": "gpt-6-astra",
        "reasoning_effort": "xhigh",
        "source_skills": ["better-skill-creator"],
        "conditions": [
            {"id": "a", "route": "yassa-prepared", "request": "a", "seed": 1},
            {"id": "b", "route": "yassa-prepared", "request": "b", "seed": 2},
        ],
        "schedule_seed": 1,
        "build_timeout_seconds": 60,
        "consumer_timeout_seconds": 30,
    }
    with pytest.raises(ValueError, match="both input preparation"):
        NativeStudy.model_validate(data)


def test_native_failure_denominators_and_rescoring(tmp_path, monkeypatch):
    from pathlib import Path

    from yassa.evidence import seal_run, write_new
    from yassa.native import prepare_native, rescore_native

    source = tmp_path / "source"
    template = Path(__file__).parents[1] / "studies/native-codex-fixture.json"
    request = json.loads(template.read_text())
    for name in request["source_skills"]:
        directory = source / name
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text("fixture source, not an evaluated package")
    monkeypatch.setattr("yassa.native.subprocess.run", lambda *a, **kw: None)
    root = prepare_native(template, tmp_path / "run", source, "sha256:" + "a" * 64)
    frozen = json.loads((root / "study.json").read_text())
    plan = json.loads((root / "plan.json").read_text())
    store = EvidenceStore(root)
    materials = {
        c["id"]: store.json(c["materials_id"], "materials.json") for c in frozen["conditions"]
    }
    results = {}
    for trial in plan["trials"]:
        if trial["role"] == "build":
            results[trial["id"]] = {"status": "build_failed"}
        elif trial["arm"] == "without-dovetail":
            results[trial["id"]] = {"status": "dependency_failed"}
        elif trial["condition"] == "supplied":
            results[trial["id"]] = {"status": "dependency_missing"}
        else:
            case = next(c for c in materials["prepared"]["evaluation"] if c["id"] == trial["case"])
            results[trial["id"]] = {
                "status": "completed",
                "output_id": store.put(
                    {"output/result.json": canonical({"totals": case["expected"]})}
                ),
            }
    write_new(root / "results.json", canonical({"trials": results}))
    seal_run(root)
    first = rescore_native(root, "first")
    second = rescore_native(root, "second")
    assert (first.parent / "scores.json").read_bytes() == (
        second.parent / "scores.json"
    ).read_bytes()
    scores = json.loads((first.parent / "scores.json").read_text())["scores"]
    assert len(scores) == 12
    assert sum(s["value"] == 1 for s in scores) == 3
    assert sum(s["value"] == 0 for s in scores) == 6
    assert sum(s["value"] is None for s in scores) == 3
    assert "| supplied | with-dovetail | 0 | 0 | 3 |" in first.read_text()
