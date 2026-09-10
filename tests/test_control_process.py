"""Actual Inspect fixture CLI, cancellation and OS process-death recovery. No live calls."""

import subprocess
import sys
import time

from yassa.app import prepare
from yassa.control import cancel, control_status, resource_init, resource_status
from yassa.evidence import verify_run
from yassa.records import canonical, parse_json


def wait_until(predicate, process):
    deadline = time.monotonic() + 60
    while not predicate():
        if process.poll() is not None or time.monotonic() >= deadline:
            raise AssertionError("fixture process ended or failed to reach the durable checkpoint")
        time.sleep(0.01)


def command(root, *args):
    return [sys.executable, "-m", "yassa.app", *map(str, args), str(root)]


def test_cli_process_cancellation_kill_and_restart_preserve_inspect_work(tmp_path, study_data):
    study_data["kinds"] = ["direct"]
    study_data["arms"] = study_data["arms"][:1]
    study_data["conditions"] = study_data["conditions"][1:]
    study_data["limits"]["infrastructure_retries"] = 0
    source = tmp_path / "fixture.json"
    source.write_bytes(canonical(study_data))
    root = prepare(source, tmp_path / "run")
    ledger = tmp_path / "resources"
    resource_init(ledger, {"max_attempts": 3, "max_scheduled_seconds": 90})
    base = command(root, "execute") + ["--resources", str(ledger)]
    process = subprocess.Popen(base, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        wait_until(lambda: bool(list((root / "control/attempts").glob("*/launch.json"))), process)
        cancel(root, "process acceptance: settle current Inspect sample")
        stdout, stderr = process.communicate(timeout=90)
        assert process.returncode == 3, stdout + stderr
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    (tmp_path / "cancel-console.txt").write_text(stdout + stderr, encoding="utf-8")
    before = control_status(root)
    assert before["attempts_reserved"] == 1
    first = before["attempts"][0]
    first_result = root / first["directory"] / "result.json"
    original = first_result.read_bytes()
    assert parse_json(original)["inspect"]["status"] == "success"

    process = subprocess.Popen(
        base + ["--resume"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        wait_until(
            lambda: len(list((root / "control/attempts").glob("*/launch.json"))) >= 2, process
        )
        process.kill()
        stdout, stderr = process.communicate(timeout=30)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    (tmp_path / "kill-console.txt").write_text(stdout + stderr, encoding="utf-8")
    recovered = subprocess.run(base + ["--resume"], capture_output=True, text=True, timeout=90)
    (tmp_path / "recovery-console.txt").write_text(
        recovered.stdout + recovered.stderr, encoding="utf-8"
    )
    assert recovered.returncode in {0, 3}, recovered.stdout + recovered.stderr
    if recovered.returncode == 3:
        uncertain = [
            a["logical"] for a in control_status(root)["attempts"] if a["status"] == "uncertain"
        ]
        assert uncertain
        args = base + [
            "--resume",
            "--reason",
            "acceptance process kill: preserve uncertain work as missing",
        ]
        for logical in uncertain:
            args.extend(["--mark-missing", logical])
        recovered = subprocess.run(args, capture_output=True, text=True, timeout=90)
        (tmp_path / "disposition-console.txt").write_text(
            recovered.stdout + recovered.stderr, encoding="utf-8"
        )
        assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert first_result.read_bytes() == original
    assert control_status(root)["attempts_reserved"] == 3
    assert resource_status(ledger)["remaining_attempts"] == 0
    assert verify_run(root)
    score_path = root / "interpretations/original/scores.json"
    scores = score_path.read_bytes()
    assert len(parse_json(scores)["scores"]) == 3
    replay = subprocess.run(
        command(root, "rescore") + ["--label", "replay"], capture_output=True, text=True, timeout=60
    )
    assert replay.returncode == 0, replay.stdout + replay.stderr
    assert (root / "interpretations/replay/scores.json").read_bytes() == scores
