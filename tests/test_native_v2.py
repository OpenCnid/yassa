import copy
import json
import os
import shutil
from collections import defaultdict
from pathlib import Path

import pytest

from yassa.evidence import EvidenceStore, seal_run, verify_run, write_new
from yassa.native import execute_native_study, prepare_native, rescore_native
from yassa.native_checkers import check, oracle
from yassa.native_contracts import (
    FileMaterials,
    NativeStudyV2,
    builder_files,
    make_native_plan,
    prepare_files,
    validate_materials,
)
from yassa.records import canonical, digest, parse_json

STUDIES = Path(__file__).resolve().parents[1] / "studies"
IMAGE = "sha256:" + "a" * 64


def request(name="reconciliation"):
    value = parse_json((STUDIES / f"native-{name}-v2.json").read_bytes())
    value["conditions"][0]["source_path"] = str(STUDIES / value["conditions"][0]["source_path"])
    return value


def prepared(value):
    study = NativeStudyV2.model_validate(value)
    materials = {c.id: prepare_files(study.task, c, STUDIES)[0] for c in study.conditions}
    return study, materials


def freeze(tmp_path, monkeypatch, value=None):
    monkeypatch.setattr("yassa.native_runner.subprocess.run", lambda *args, **kwargs: None)
    path = tmp_path / "request.json"
    path.write_bytes(canonical(value or request()))
    return prepare_native(path, tmp_path / "run", None, IMAGE)


@pytest.mark.parametrize("name", ["totals", "reconciliation"])
def test_shared_file_contract_and_plan(name):
    study, materials = prepared(request(name))
    plan = make_native_plan(study, materials, "frozen")
    assert plan == make_native_plan(study, materials, "frozen")
    assert plan["reserved_attempts"] == 30
    assert plan["reserved_native_seconds"] == 2520
    trials = plan["trials"]
    assert len({t["id"] for t in trials}) == 30
    assert all(t["role"] == "build" for t in trials[:6])
    assert all(t["role"] == "consume" for t in trials[6:])
    builds = {t["id"]: t for t in trials[:6]}
    for use in trials[6:]:
        parent = builds[use["parent"]]
        assert (use["arm"], use["condition"], use["build"]) == (
            parent["arm"],
            parent["condition"],
            parent["build"],
        )
        assert use["repeat"] in (1, 2)
    for material in materials.values():
        common = builder_files(study.task, material)
        body = parse_json(common[study.task.brief_path])
        assert set(body) == {"brief", "contract", "development"}
        assert all(case.id.encode() not in canonical(body) for case in material.evaluation)


@pytest.mark.parametrize("field,limit", [("max_attempts", 29), ("max_scheduled_seconds", 2519)])
def test_admission_happens_before_image_check_or_run_creation(tmp_path, monkeypatch, field, limit):
    value = request()
    value["admission"][field] = limit
    path = tmp_path / "request.json"
    path.write_bytes(canonical(value))
    calls = []
    monkeypatch.setattr("yassa.native_runner.subprocess.run", lambda *a, **kw: calls.append(a))
    with pytest.raises(ValueError, match=field):
        prepare_native(path, tmp_path / "run", None, IMAGE)
    assert not calls
    assert not (tmp_path / "run").exists()


def test_admission_rejects_before_enumerating_trials(monkeypatch):
    value = request()
    value["admission"]["max_attempts"] = 29
    study, materials = prepared(value)

    def unexpected_identity(value):
        pytest.fail("over-budget plan must not enumerate or hash trial identities")

    monkeypatch.setattr("yassa.native_contracts.identity", unexpected_identity)
    with pytest.raises(ValueError, match="max_attempts"):
        make_native_plan(study, materials, "frozen")


def test_rendered_builder_file_count_includes_brief():
    study, materials = prepared(request())
    raw = materials["prepared"].model_dump(mode="json")
    raw["builder_files"] = {f"input/file-{i}.txt": "data" for i in range(100)}
    with pytest.raises(ValueError, match="100 files"):
        validate_materials(study.task, FileMaterials.model_validate(raw))


@pytest.mark.parametrize(
    "change",
    [
        {"brief_path": "input/../secret"},
        {"brief_path": "input/boundary.txt"},
        {"package_path": "output/answer.json/skill"},
        {"result_path": "/home/runtime/result.json"},
        {"package_name": "boundary"},
        {"checker": "unregistered"},
        {"checker_inputs": ["input/left.csv"]},
        {"checker_inputs": ["input/left.csv", "input/LEFT.csv"]},
    ],
)
def test_invalid_task_boundaries(change):
    value = request()
    value["task"].update(change)
    with pytest.raises(ValueError):
        NativeStudyV2.model_validate(value)


def test_materials_reject_collision_bad_reference_and_relabelled_input():
    study, materials = prepared(request())
    raw = materials["prepared"].model_dump(mode="json")
    variants = []
    collision = copy.deepcopy(raw)
    collision["builder_files"] = {study.task.brief_path.upper(): "collision"}
    variants.append(collision)
    bad = copy.deepcopy(raw)
    bad["evaluation"][0]["expected"]["balances"][0]["delta_cents"] += 1
    variants.append(bad)
    duplicate = copy.deepcopy(raw)
    duplicate["evaluation"][0].update(
        files=duplicate["development"][0]["files"], expected=duplicate["development"][0]["expected"]
    )
    variants.append(duplicate)
    reversed_rows = copy.deepcopy(raw)
    reversed_rows["evaluation"][0].update(
        files={
            name: "\n".join([text.splitlines()[0], *reversed(text.splitlines()[1:])]) + "\n"
            for name, text in raw["development"][0]["files"].items()
        },
        expected=raw["development"][0]["expected"],
    )
    variants.append(reversed_rows)
    for value in variants:
        with pytest.raises(ValueError):
            validate_materials(study.task, FileMaterials.model_validate(value))


def test_reconciliation_checker_alternatives_and_plausible_errors():
    files = {
        "input/l.csv": 'id,cents\r\n"comma,id",10\r\n"comma,id",-10\r\nCase,-7\r\n',
        "input/r.csv": 'id,cents\n"comma,id",4\ncase,9\nZERO,0\n',
    }
    expected = oracle("reconciliation-v1", files, tuple(files))
    valid = {"balances": list(reversed(expected["balances"]))}
    assert check("reconciliation-v1", json.dumps(valid, indent=3).encode(), expected)["value"] == 1
    wrong = []
    missing_zero = copy.deepcopy(valid)
    missing_zero["balances"] = [r for r in missing_zero["balances"] if r["id"] != "ZERO"]
    wrong.append(missing_zero)
    duplicate = copy.deepcopy(valid)
    duplicate["balances"].append(duplicate["balances"][0])
    wrong.append(duplicate)
    for field, value in [("delta_cents", 7), ("left_cents", True), ("id", "renamed")]:
        altered = copy.deepcopy(valid)
        altered["balances"][0][field] = value
        wrong.append(altered)
    extra = copy.deepcopy(valid)
    extra["explanation"] = "done"
    wrong.append(extra)
    for value in wrong:
        assert check("reconciliation-v1", canonical(value), expected)["value"] == 0
    for work in (b"", b"{} trailing", b'{"balances":[],"balances":[]}', b"\xff"):
        assert check("reconciliation-v1", work, expected)["value"] == 0
    assert check("reconciliation-v1", b'{"balances":[]}', {"balances": []})["value"] == 1


@pytest.mark.parametrize(
    "text", ["id,amount\na,1\n", "id,cents\na,1.2\n", "id,cents\n,2\n", "id,cents\na,1,2\n"]
)
def test_reconciliation_input_validation(text):
    with pytest.raises(ValueError):
        oracle("reconciliation-v1", {"a": text, "b": "id,cents\n"}, ("a", "b"))


def source_arm(tmp_path, value):
    source = tmp_path / "external-skills"
    (source / "helper" / "scripts").mkdir(parents=True)
    bodies = {
        "helper/SKILL.md": b"---\r\nname: helper\r\ndescription: Check work.\r\n---\r\n",
        "helper/scripts/check.py": b"print('check')\n",
    }
    for name, body in bodies.items():
        (source / name).write_bytes(body)
    (source / "helper" / ".env").write_text("must not be transferred")
    value["sources"] = [
        {
            "id": "source",
            "path": str(source),
            "files": {n: digest(b) for n, b in bodies.items()},
            "executable": ["helper/scripts/check.py"],
        }
    ]
    value["arms"][1].update(sources=["source"], invocation="Use $helper.")
    return bodies


@pytest.mark.parametrize("name", ["totals", "reconciliation"])
def test_runner_exact_common_inputs_lineage_boundaries_and_rescore(tmp_path, monkeypatch, name):
    value = request(name)
    source_bodies = source_arm(tmp_path, value)
    root = freeze(tmp_path, monkeypatch, value)
    frozen = parse_json((root / "study.json").read_bytes())
    plan = parse_json((root / "plan.json").read_bytes())
    study, materials = prepared(value)
    store = EvidenceStore(root)
    trials = {t["id"]: t for t in plan["trials"]}
    calls = []

    def adapter(root, attempt_id, prompt, files, **kwargs):
        trial = trials[attempt_id]
        calls.append(trial)
        assert all(n.startswith(("input/", ".agents/skills/")) for n in files)
        if trial["role"] == "build":
            assert {n: b for n, b in files.items() if n.startswith("input/")} == builder_files(
                study.task, materials[trial["condition"]]
            )
            if trial["arm"] == "explicit-checks":
                assert prompt.startswith("Use $helper.\n\n")
                assert {
                    n.removeprefix(".agents/skills/"): b
                    for n, b in files.items()
                    if n.startswith(".agents/")
                } == source_bodies
                assert kwargs["executable"] == (".agents/skills/helper/scripts/check.py",)
            else:
                assert not any(n.startswith(".agents/") for n in files)
            package = (
                f"---\nname: {study.task.package_name}\ndescription: Run task.\n---\n{attempt_id}\n"
            )
            output = {
                study.task.package_path + "/SKILL.md": package.encode(),
                study.task.package_path + "/scripts/run.py": b"print('fixture')\n",
                "output/build-notes.md": b"not part of the package",
            }
            output_id = store.put(output, executable=[study.task.package_path + "/scripts/run.py"])
            status = "budget_exhausted"  # A complete package remains usable after a deadline.
        else:
            case = next(
                c for c in materials[trial["condition"]].evaluation if c.id == trial["case"]
            )
            assert {n: b for n, b in files.items() if n.startswith("input/")} == {
                n: s.encode() for n, s in case.files.items()
            }
            prefix = f".agents/skills/{study.task.package_name}/"
            assert set(n for n in files if n.startswith(".agents/")) == {
                prefix + "SKILL.md",
                prefix + "scripts/run.py",
            }
            assert trial["parent"].encode() in files[prefix + "SKILL.md"]
            assert kwargs["executable"] == (prefix + "scripts/run.py",)
            output_id = store.put({study.task.result_path: canonical(case.expected)})
            status = "completed"
        result = {
            "status": status,
            "output_id": output_id,
            "rejected_paths": [],
            "duration_seconds": 1,
        }
        write_new(root / "attempts" / attempt_id / "result.json", canonical(result))
        return result

    monkeypatch.setattr("yassa.native_runner.execute_native", adapter)
    report = execute_native_study(root, tmp_path / "unused-auth")
    assert len(calls) == 30
    assert verify_run(root)
    scores = parse_json((report.parent / "scores.json").read_bytes())["scores"]
    assert len(scores) == 24 and all(s["value"] == 1 for s in scores)
    assert "budget_exhausted" in report.read_text()
    groups = defaultdict(set)
    for trial in plan["trials"]:
        binding = parse_json((root / "bindings" / f"{trial['id']}.json").read_bytes())
        groups[(trial["condition"], trial["role"], trial["case"])].add(binding["common_id"])
        assert binding["study_id"] == frozen["id"] and binding["plan_id"] == plan["id"]
    assert all(len(ids) == 1 for ids in groups.values())
    repeat = rescore_native(root, "repeat")
    assert (report.parent / "scores.json").read_bytes() == (
        repeat.parent / "scores.json"
    ).read_bytes()
    relocated = tmp_path / "relocated"
    shutil.copytree(root, relocated)
    assert verify_run(relocated) == verify_run(root)
    assert rescore_native(relocated, "relocated").is_file()
    with pytest.raises(ValueError, match="already started"):
        execute_native_study(root, tmp_path / "unused-auth")


def test_failures_keep_planned_denominators_and_skip_dependents(tmp_path, monkeypatch):
    root = freeze(tmp_path, monkeypatch)
    store = EvidenceStore(root)
    calls = []
    plan = parse_json((root / "plan.json").read_bytes())
    by_id = {t["id"]: t for t in plan["trials"]}

    def adapter(root, attempt_id, *args, **kwargs):
        calls.append(attempt_id)
        trial = by_id[attempt_id]
        assert trial["role"] == "build"
        if trial["arm"] == "explicit-checks":
            return {"status": "harness_failure", "error": "fixture infrastructure failure"}
        return {
            "status": "completed",
            "output_id": store.put({"output/package/SKILL.md": b"invalid"}),
        }

    monkeypatch.setattr("yassa.native_runner.execute_native", adapter)
    report = execute_native_study(root, tmp_path / "unused-auth")
    scores = parse_json((report.parent / "scores.json").read_bytes())["scores"]
    assert len(calls) == 6
    assert len(scores) == 24
    assert sum(s["value"] == 0 for s in scores) == 16
    assert sum(s["value"] is None for s in scores) == 8
    assert {s["status"] for s in scores} == {"dependency_missing", "dependency_failed"}


def test_pinned_source_mismatch_fails_before_freeze(tmp_path, monkeypatch):
    value = request()
    source_arm(tmp_path, value)
    value["sources"][0]["files"]["helper/SKILL.md"] = "0" * 64
    with pytest.raises(ValueError, match="source pin mismatch"):
        freeze(tmp_path, monkeypatch, value)
    assert not (tmp_path / "run").exists()


def test_new_json_task_requires_no_orchestration_edits(tmp_path, monkeypatch):
    value = request()
    value["task"].update(
        id="lookup-v1",
        checker="json-exact-v1",
        checker_inputs=[],
        requirements="Return the supplied lookup's value as JSON.",
    )
    material = {
        "schema_version": 2,
        "task_id": "lookup-v1",
        "brief": "Perform a lookup.",
        "authorship": "test author",
        "source": "test",
        "synthetic": True,
        "assumptions": [],
        "development": [
            {
                "id": "dev",
                "group": "dev",
                "files": {"input/data.txt": "a"},
                "expected": {"value": 1},
            }
        ],
        "evaluation": [
            {
                "id": "eval",
                "group": "eval",
                "files": {"input/data.txt": "b"},
                "expected": {"value": 2},
            }
        ],
    }
    source = tmp_path / "supplied.json"
    source.write_bytes(canonical(material))
    value["conditions"] = [
        {
            "id": "only-supplied",
            "route": "user-supplied",
            "source_path": str(source),
            "source_sha256": digest(source.read_bytes()),
        }
    ]
    value["arms"] = [{"id": "single", "builds": 1}]
    value["consumer_repeats"] = 1
    root = freeze(tmp_path, monkeypatch, value)
    frozen = parse_json((root / "study.json").read_bytes())
    assert (
        "semantic correctness supplied by author"
        in frozen["conditions"][0]["provenance"]["verification"]
    )
    assert check("json-exact-v1", b'{ "value": 2 }', {"value": 2})["value"] == 1
    assert check("json-exact-v1", b'{"value": true}', {"value": 1})["value"] == 0
    assert check("json-exact-v1", b'{"value": 2.0}', {"value": 2})["value"] == 0

    def adapter(root, attempt_id, prompt, files, **kwargs):
        store = EvidenceStore(root)
        if attempt_id.startswith("build-"):
            body = f"---\nname: {value['task']['package_name']}\ndescription: Lookup.\n---\n"
            output = {value["task"]["package_path"] + "/SKILL.md": body.encode()}
        else:
            assert files["input/data.txt"] == b"b"
            output = {value["task"]["result_path"]: b'{"value":2}'}
        return {"status": "completed", "output_id": store.put(output), "rejected_paths": []}

    monkeypatch.setattr("yassa.native_runner.execute_native", adapter)
    report = execute_native_study(root, tmp_path / "unused-auth")
    scores = parse_json((report.parent / "scores.json").read_bytes())["scores"]
    assert len(scores) == 1 and scores[0]["value"] == 1


def test_freeze_rejects_changed_dependencies_before_launch(tmp_path, monkeypatch):
    root = freeze(tmp_path, monkeypatch)
    monkeypatch.setattr("yassa.native_runner.runtime_versions", lambda: {"python": "changed"})
    with pytest.raises(ValueError, match="dependencies changed"):
        execute_native_study(root, tmp_path / "unused-auth")


def test_incomplete_sealed_result_is_not_rescorable(tmp_path, monkeypatch):
    root = freeze(tmp_path, monkeypatch)
    frozen = parse_json((root / "study.json").read_bytes())
    plan = parse_json((root / "plan.json").read_bytes())
    write_new(
        root / "results.json",
        canonical(
            {"schema_version": 2, "study_id": frozen["id"], "plan_id": plan["id"], "trials": {}}
        ),
    )
    seal_run(root)
    with pytest.raises(ValueError, match="incomplete"):
        rescore_native(root, "bad")


def test_collector_rejects_symlink_export_root(tmp_path):
    from yassa.native_execution import COLLECT

    output = tmp_path / "output"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "result.json").write_text("protected")
    try:
        os.symlink(outside, output, target_is_directory=True)
    except OSError:
        pytest.skip("creating symlinks is unavailable on this host")
    export = tmp_path / "export.json"
    script = COLLECT.replace('"/work/output"', repr(str(output)))
    script = script.replace('"/home/runtime/codex/sessions"', repr(str(tmp_path / "sessions")))
    script = script.replace(
        '"/home/runtime/codex/skills/.system"', repr(str(tmp_path / "builtins"))
    )
    script = script.replace('"/home/runtime/export.json"', repr(str(export)))
    exec(compile(script, "collector-test", "exec"), {})
    result = parse_json(export.read_bytes())
    assert result["files"] == {}
    assert result["rejected"] == [str(output)]
