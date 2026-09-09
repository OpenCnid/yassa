import shutil
import subprocess
import sys

import pytest

from yassa.evidence import EvidenceStore, freeze_package, read_regular, verify_run, write_new
from yassa.records import canonical


@pytest.mark.parametrize(
    "name",
    [
        "../outside.txt",
        "/absolute.txt",
        "C:/drive.txt",
        "x\\escape.txt",
        "x:stream",
        "CON.txt",
        "refs/../escape.txt",
        "./alias.txt",
        "folder//alias.txt",
        "trailing.",
        "trailing ",
        "refs/CON .txt",
        "refs/LPT1 .log",
        "refs/ leading.txt",
        "refs/tab\tname.txt",
    ],
)
def test_package_path_escape_rejected(tmp_path, name):
    store = EvidenceStore(tmp_path)
    with pytest.raises(ValueError):
        freeze_package(canonical({"files": {"SKILL.md": "skill", name: "bad"}}), store)


@pytest.mark.parametrize(
    "files",
    [
        {"SKILL.md": "a", "skill.md": "b"},
        {"SKILL.md": "a", "refs": "file", "refs/rules.txt": "child"},
        {"SKILL.md": "a", "script.py": "raise Exception()"},
        {"SKILL.md": ""},
        {"notes.txt": "No skill submitted"},
    ],
)
def test_unsupported_packages_rejected(tmp_path, files):
    with pytest.raises(ValueError):
        freeze_package(canonical({"files": files}), EvidenceStore(tmp_path))


def test_bundle_identity_survives_relocation_and_detects_tampering(tmp_path):
    store = EvidenceStore(tmp_path / "first")
    artifact = store.put({"SKILL.md": b"a\r\nb\n", "refs/rules.json": b"{}"})
    relocated = tmp_path / "second"
    shutil.copytree(store.root, relocated)
    assert EvidenceStore(relocated).get(artifact) == store.get(artifact)
    (relocated / "artifacts" / artifact / "files/SKILL.md").write_bytes(b"modified")
    with pytest.raises(ValueError, match="content mismatch"):
        EvidenceStore(relocated).get(artifact)


def test_native_check_files_with_internal_spaces_survive_export_and_relocation(tmp_path):
    files = {
        "output/package/SKILL.md": b"---\nname: sample\ndescription: Example.\n---\n",
        "output/check-evidence/generated-24/left ledger.csv": b"id,cents\nleft,17\n",
        "output/check-evidence/generated-24/right ledger.csv": b"id,cents\nright,9\n",
        "output/check evidence/run checks.py": b"print('fixture')\n",
        "sessions/session.jsonl": b"{}\n",
    }
    executable = ["output/check evidence/run checks.py"]
    store = EvidenceStore(tmp_path / "original")
    artifact = store.put(files, executable=executable)
    relocated = tmp_path / "relocated"
    shutil.copytree(store.root, relocated)
    assert EvidenceStore(relocated).get(artifact) == files
    assert EvidenceStore(relocated).put(files, executable=executable) == artifact


def test_never_overwrites_evidence(tmp_path):
    path = tmp_path / "record.json"
    write_new(path, b"original")
    with pytest.raises(FileExistsError):
        write_new(path, b"replacement")
    assert path.read_bytes() == b"original"


def test_rejects_link_sources(tmp_path):
    target = tmp_path / "real"
    target.mkdir()
    (target / "data.json").write_bytes(b"{}")
    link = tmp_path / "linked"
    if sys.platform == "win32":
        # NTFS junctions need no developer-mode symlink privilege. No deletion or moving.
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True
        )
    else:
        link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="links/reparse"):
        read_regular(link / "data.json")


def test_incomplete_run_is_not_scoreable(tmp_path):
    write_new(tmp_path / "study.json", b"{}")
    with pytest.raises(ValueError, match="incomplete/unsealed"):
        verify_run(tmp_path)
