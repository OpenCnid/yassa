import base64
from pathlib import Path
from types import SimpleNamespace

import pytest

from yassa import native_execution
from yassa.evidence import EvidenceStore, seal_run, verify_run
from yassa.native_capture import archive_files, preserve_export, read_archive, recorded_native_files
from yassa.native_context import check_prompt, check_sessions, expected_catalog, validate_features
from yassa.records import canonical, digest, parse_json

BUILTINS = {"builtin-skills/builtin/SKILL.md": b"---\nname: builtin\ndescription: Built in.\n---\n"}
INPUTS = {
    ".agents/skills/local/SKILL.md": b"---\nname: local\ndescription: >\n  Local\n  fixture.\n---\n"
}
CONFIG = b"[features]\nplugins=false\nremote_plugin=false\napps=false\n"
FEATURES = "plugins stable false\nremote_plugin stable false\napps stable false\n"
CATALOG = """<skills_instructions>
### Skill roots
- `r0` = `/home/runtime/codex/skills/.system`
- `r7` = `/work/.agents/skills`
### Available skills
- builtin: Built in. (file: r0/builtin/SKILL.md)
- local: Local fixture. (file: r7/local/SKILL.md)
</skills_instructions>"""
EXTRA = "\n- plugin:extra: Unexpected skill. (file: /home/runtime/codex/plugins/extra/SKILL.md)"


def session(identifier, catalog=CATALOG, *, parent=None):
    source = (
        "exec" if parent is None else {"subagent": {"thread_spawn": {"parent_thread_id": parent}}}
    )
    return b"".join(
        canonical(row)
        for row in [
            {"type": "session_meta", "payload": {"id": identifier, "source": source}},
            {
                "type": "response_item",
                "payload": {"role": "developer", "content": [{"text": catalog}]},
            },
        ]
    )


def test_catalog_accepts_aliases_and_folded_descriptions_but_rejects_substitution():
    expected = expected_catalog(BUILTINS, INPUTS)

    def prompt(text):
        return canonical([{"role": "developer", "content": [{"text": text}]}])

    assert check_prompt(prompt(CATALOG), expected)["passed"]
    for text in [
        CATALOG + EXTRA,
        CATALOG.replace("Local fixture.", "Changed instructions."),
        CATALOG.replace("/work/.agents/skills", "/work/other"),
        CATALOG.replace("- local: Local fixture. (file: r7/local/SKILL.md)", ""),
    ]:
        assert not check_prompt(prompt(text), expected)["passed"]
    assert not check_prompt(canonical([]), expected)["passed"]


def test_all_child_catalogs_and_missing_session_evidence_are_checked():
    expected = expected_catalog(BUILTINS, INPUTS)
    files = {
        "sessions/root.jsonl": session("root"),
        "sessions/child.jsonl": session("child", parent="root"),
    }
    assert check_sessions(files, expected)["passed"]
    files["sessions/child.jsonl"] = session("child", CATALOG + EXTRA, parent="root")
    check = check_sessions(files, expected)
    assert not check["passed"]
    child = next(s for s in check["sessions"] if s["id"] == "child")
    assert child["catalogs"][0]["unexpected"][0]["name"] == "plugin:extra"
    for data in [
        b'{"partial":',
        session("child", "no catalog", parent="root"),
        session("child", parent="absent"),
        session("root"),
    ]:
        assert not check_sessions({**files, "sessions/child.jsonl": data}, expected)["passed"]


def test_feature_configuration_and_effective_values_both_must_disable_plugins():
    validate_features(CONFIG, FEATURES)
    for config, effective in [
        (b"[features]\n", FEATURES),
        (CONFIG, ""),
        (CONFIG, FEATURES.replace("plugins stable false", "plugins stable true")),
    ]:
        with pytest.raises(ValueError, match="explicitly disabled"):
            validate_features(config, effective)


def test_archive_retains_nonportable_names_modes_and_large_blobs_after_relocation(tmp_path):
    import shutil

    store = EvidenceStore(tmp_path / "original")
    files = {
        "output/CON.txt": b"device-like Linux filename",
        "output/../untrusted": b"path data",
        "output/caf\u00e9.py": b"x" * 8_000_001,
    }
    artifact = archive_files(store, files, executable=["output/caf\u00e9.py"])
    seal = seal_run(store.root)
    shutil.copytree(store.root, tmp_path / "relocated")
    moved = EvidenceStore(tmp_path / "relocated")
    assert read_archive(moved, artifact) == files
    assert moved.put(moved.get(artifact)) == artifact
    assert verify_run(moved.root) == seal
    manifest = parse_json(moved.get(artifact)["archive.json"])
    assert next(e for e in manifest["files"] if e["path"] == "output/caf\u00e9.py")["executable"]
    assert not (store.root / "untrusted").exists()


def test_encoded_credentials_are_withheld_before_raw_archive_storage(tmp_path):
    secret = b"synthetic-credential-" * 5
    raw = canonical(
        {"files": {"output/x": base64.b64encode(secret).decode()}, "executable": [], "rejected": []}
    )
    with pytest.raises(ValueError, match="withheld"):
        preserve_export(EvidenceStore(tmp_path), raw, (secret,))
    assert not (tmp_path / "artifacts").exists()


class SandboxFixture:
    def __init__(self, problem):
        self.problem, self.started = problem, False
        self.files = {}

    async def write_file(self, name, data):
        self.files[name] = data

    async def read_file(self, name, text=True):
        if name not in self.files:
            raise FileNotFoundError(name)
        data = self.files[name]
        return data.decode() if text and isinstance(data, bytes) else data

    async def exec(self, command, **kwargs):
        stdout, stderr, code = "", "", 0
        if command[:2] == ["codex", "--version"]:
            stdout = "codex-cli 0.153.4\n"
        elif command[:3] == ["codex", "features", "list"]:
            stdout = FEATURES
        elif command[:2] == ["codex", "sandbox"]:
            stdout = canonical({str(n): True for n in range(12)}).decode()
        elif command[0] == "sh" and "codex debug" in command[-1]:
            text = CATALOG + EXTRA if self.problem == "preflight" else CATALOG
            self.files["/home/runtime/prompt-input.json"] = canonical(
                [{"role": "developer", "content": [{"text": text}]}]
            )
        elif command[0] == "sh" and "native" in command:
            self.started = True
            for name in ["events.jsonl", "stderr.txt", "final.txt"]:
                self.files["/home/runtime/" + name] = b"recorded native log\n"
            if self.problem == "credential":
                self.files["/home/runtime/events.jsonl"] = b"synthetic-secret-" * 4
        elif command[:2] == ["python3", "-c"]:
            output = "INCLUDE_OUTPUT = True" in command[-1]
            files = dict(BUILTINS)
            if self.started:
                files.update(
                    {
                        "sessions/root.jsonl": session("root"),
                        "sessions/child.jsonl": session(
                            "child",
                            CATALOG + EXTRA if self.problem == "child" else CATALOG,
                            parent="root",
                        ),
                    }
                )
            if output:
                if self.problem == "collector":
                    return SimpleNamespace(
                        success=False, returncode=1, stdout="", stderr="injected collection failure"
                    )
                path = "output/CON.txt" if self.problem == "path" else "output/result.json"
                files[path] = b'{"ok":true}'
            self.files["/home/runtime/export.json"] = canonical(
                {
                    "files": {n: base64.b64encode(b).decode() for n, b in files.items()},
                    "executable": [],
                    "rejected": [],
                }
            )
        return SimpleNamespace(success=code == 0, returncode=code, stdout=stdout, stderr=stderr)


@pytest.mark.parametrize(
    "problem", ["none", "preflight", "child", "path", "collector", "credential"]
)
def test_inspect_native_acceptance_preserves_failure_evidence(tmp_path, monkeypatch, problem):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "boundary_probe.py").write_bytes(b"fixture")
    (runtime / "builtin-skills.json").write_bytes(
        canonical(
            {
                "schema_version": 1,
                "files": {
                    n.removeprefix("builtin-skills/"): digest(b) for n, b in BUILTINS.items()
                },
            }
        )
    )
    auth = tmp_path / "fixture-auth.json"
    auth.write_bytes(
        canonical({"auth_mode": "chatgpt", "tokens": {"fixture": "synthetic-secret-" * 4}})
    )
    sandbox = SandboxFixture(problem)
    monkeypatch.setattr(native_execution, "RUNTIME", runtime)
    monkeypatch.setattr(native_execution, "sandbox", lambda: sandbox)
    monkeypatch.setattr(native_execution, "SandboxEnvironmentSpec", lambda *args: None)
    root = tmp_path / "run"
    result = native_execution.execute_native(
        root,
        "fixture",
        "Use $local.",
        INPUTS,
        image="fixture-only",
        auth_path=auth,
        config=CONFIG,
        timeout=30,
    )
    store = EvidenceStore(root)
    assert result["status"] == ("completed" if problem == "none" else "harness_failure")
    assert Path(root / result["inspect_log"]).is_file()
    assert bool(result["native_started"]) == (problem != "preflight")
    assert result["preflight_id"]
    if problem == "preflight":
        assert not sandbox.started and not result.get("output_id")
        assert not store.json(result["preflight_check_id"], "check.json")["passed"]
    else:
        if problem != "credential":
            assert read_archive(store, result["native_logs_id"])["events.jsonl"]
        else:
            assert not result.get("native_logs_id")
            assert all(
                b"synthetic-secret-" * 4 not in p.read_bytes()
                for p in root.rglob("*")
                if p.is_file()
            )
        assert "sessions/child.jsonl" in store.get(result["transcript_id"])
        assert "sessions/child.jsonl" in recorded_native_files(store, result)
        assert store.json(result["catalog_check_id"], "check.json")["passed"] == (
            problem != "child"
        )
        if problem == "child":
            assert result["output_id"] and result["native_status"] == "completed"
        if problem == "path":
            raw = read_archive(store, result["captures"]["output"]["archive_id"])["export.json"]
            assert "output/CON.txt" in parse_json(raw)["files"]
            assert not result.get("output_id")
