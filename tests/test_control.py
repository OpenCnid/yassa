"""Operational fault scenarios; no credentials or live model calls."""

import copy
import shutil
import subprocess
import sys

import pytest

from yassa.control import (
    CURRENT,
    Controller,
    ResourceLimits,
    cancel,
    control_status,
    locked,
    managed,
    read_json,
    reserve,
    resource_init,
    resource_status,
)
from yassa.evidence import EvidenceStore, inventory, seal_run, verify_run, write_new
from yassa.records import canonical


def freeze(root, count=3):
    root.mkdir()
    write_new(
        root / "plan.json",
        canonical(
            {
                "trials": [
                    {"id": f"trial-{i}", "role": "direct", "parent": None} for i in range(count)
                ]
            }
        ),
    )
    write_new(root / "freeze-seal.json", canonical({"files": inventory(root)}))
    return root


def budget(root, attempts=10, seconds=100):
    resource_init(root, {"max_attempts": attempts, "max_scheduled_seconds": seconds})
    return root


@managed("test")
def execute(root, adapter):
    outcomes = []
    for trial in read_json(root / "plan.json")["trials"]:
        outcomes.append(
            CURRENT.get().call(
                trial["id"],
                "direct",
                "inspect-api",
                10,
                {"input": trial["id"]},
                root / "attempts" / trial["id"],
                adapter,
            )
        )
    seal_run(root)
    return outcomes


def completed(directory, aid, status="completed"):
    directory.mkdir(parents=True)
    write_new(directory / "inspect.json", canonical({"status": "success", "attempt": aid}))
    result = {
        "status": status,
        "completion": "{}",
        "duration_seconds": 1,
        "usage": {"input_tokens": 2, "output_tokens": 3},
        "id": aid,
    }
    write_new(directory / "result.json", canonical(result))
    return result


def test_cancellation_settles_active_work_and_resume_reuses_exact_evidence(tmp_path):
    root, resources = freeze(tmp_path / "run"), budget(tmp_path / "budget")
    seen = []

    def adapter(directory, aid):
        seen.append(aid)
        cancel(root, "stop during this bounded call")
        return completed(directory, aid)

    report = execute(root, adapter, resources=resources)
    assert "cancelled" in report.read_text()
    assert seen == ["trial-0"]
    original = (root / "attempts/trial-0/result.json").read_bytes()
    assert [t["execution_status"] for t in control_status(root)["trials"]] == [
        "completed",
        "not_launched",
        "not_launched",
    ]
    assert resource_status(resources)["remaining_attempts"] == 9

    def rest(directory, aid):
        seen.append(aid)
        return completed(directory, aid)

    outcomes = execute(root, rest, resources=resources, resume=True)
    assert len(outcomes) == 3 and len(seen) == len(set(seen)) == 3
    assert (root / "attempts/trial-0/result.json").read_bytes() == original
    assert len(list((root / "control/cancellations").glob("*.json"))) == 1
    assert resource_status(resources)["remaining_attempts"] == 7
    assert verify_run(root)
    moved = tmp_path / "moved"
    shutil.copytree(root, moved)
    assert verify_run(moved) == verify_run(root)
    assert control_status(moved) == control_status(root)


def test_inflight_reservation_blocks_other_run_before_it_can_launch(tmp_path):
    root = freeze(tmp_path / "first", 1)
    other = freeze(tmp_path / "second", 1)
    resources = budget(tmp_path / "resources", attempts=1)
    launched = []

    def adapter(directory, aid):
        # Independent controller, same shared ledger while the first call is in flight.
        controller = Controller(other, "test", resources, False, (), (), None, 0)
        with pytest.raises(ValueError, match="exhausted"):
            controller.call(
                "other",
                "grading",
                "inspect-api",
                10,
                {},
                other / "calls/1",
                lambda *a: launched.append("over-budget"),
            )
        launched.append("first")
        return completed(directory, aid)

    execute(root, adapter, resources=resources)
    assert launched == ["first"]
    state = resource_status(resources)
    assert state["remaining_attempts"] == 0
    assert state["by_role"]["direct"]["reported_seconds"] == 1


@pytest.mark.parametrize("attempts,seconds", [(1, 100), (10, 19)])
def test_exhaustion_keeps_partial_work_and_planned_denominator(tmp_path, attempts, seconds):
    root = freeze(tmp_path / "run")
    resources = budget(tmp_path / "resources", attempts, seconds)
    report = execute(root, completed, resources=resources)
    assert "exhausted" in report.read_text()
    state = control_status(root)
    assert state["planned"] == 3 and state["attempts_reserved"] == 1
    assert not state["sealed"]
    with pytest.raises(ValueError, match="incomplete/unsealed"):
        verify_run(root)
    execute(root, completed, resources=resources, resume=True)
    assert control_status(root)["attempts_reserved"] == 1


def test_crash_after_adapter_return_recovers_without_an_extra_chance(tmp_path):
    root = freeze(tmp_path / "run")
    resources = budget(tmp_path / "resources")

    def crash(directory, aid):
        completed(directory, aid)
        raise SystemExit("process died after durable adapter return")

    with pytest.raises(SystemExit):
        execute(root, crash, resources=resources)
    assert control_status(root)["attempts"][0]["status"] == "uncertain"
    seen = []

    def adapter(directory, aid):
        seen.append(aid)
        return completed(directory, aid)

    execute(root, adapter, resources=resources, resume=True)
    assert seen == ["trial-1", "trial-2"]
    commit = read_json(root / "control/attempts/trial-0/completion.json")
    assert commit["recovered_return"]
    assert resource_status(resources)["remaining_attempts"] == 7


@pytest.mark.parametrize("decision", ["retry", "mark_missing"])
def test_uncertain_launch_requires_explicit_decision_and_retains_partial_logs(tmp_path, decision):
    root, resources = freeze(tmp_path / "run"), budget(tmp_path / "budget")

    def crash(directory, aid):
        directory.mkdir(parents=True)
        write_new(directory / "partial-inspect.json", b'{"status":"started"}')
        raise SystemExit()

    with pytest.raises(SystemExit):
        execute(root, crash, resources=resources, infrastructure_retries=1)
    report = execute(root, completed, resources=resources, resume=True)
    assert "uncertain launch trial-0" in report.read_text()
    assert control_status(root)["attempts_reserved"] == 1
    result = execute(
        root,
        completed,
        resources=resources,
        resume=True,
        **{decision: ["trial-0"]},
        reason="explicit infrastructure disposition",
    )
    assert (root / "attempts/trial-0/partial-inspect.json").read_bytes() == b'{"status":"started"}'
    state = control_status(root)
    if decision == "retry":
        retried = next(a for a in state["attempts"] if a["number"] == 2)
        assert retried["retry_of"] == "trial-0" and retried["attempt"] == "trial-0-retry-1"
        assert retried["directory"] == "attempts/trial-0-retry-1"
        assert len(state["attempts"]) == 4
        assert resource_status(resources)["remaining_attempts"] == 6
    else:
        assert result[0]["uncertain"] and result[0]["status"] == "harness_failure"
        assert len(state["attempts"]) == 3
    assert verify_run(root)


def test_wrong_answer_cannot_receive_an_infrastructure_retry(tmp_path):
    root, resources = freeze(tmp_path / "run"), budget(tmp_path / "budget")

    def wrong(directory, aid):
        cancel(root, "pause after wrong answer")
        return completed(directory, aid)  # {} is recorded completed work, not infrastructure.

    execute(root, wrong, resources=resources, infrastructure_retries=1)
    with pytest.raises(ValueError, match="only infrastructure"):
        execute(root, completed, resources=resources, resume=True, retry=["trial-0"], reason="redo")
    assert resource_status(resources)["remaining_attempts"] == 9


def test_infrastructure_retry_allowance_is_frozen_and_failed_attempts_stay(tmp_path):
    root, resources = freeze(tmp_path / "run"), budget(tmp_path / "budget")
    report = execute(
        root,
        lambda d, a: completed(d, a, "provider_failure"),
        resources=resources,
        infrastructure_retries=1,
    )
    assert "infrastructure failure" in report.read_text()
    with pytest.raises(ValueError, match="policy changed"):
        execute(root, completed, resources=resources, resume=True, infrastructure_retries=2)
    execute(root, completed, resources=resources, resume=True, retry=["trial-0"], reason="outage")
    assert read_json(root / "attempts/trial-0/result.json")["status"] == "provider_failure"
    assert resource_status(resources)["remaining_attempts"] == 6


@pytest.mark.parametrize("path", ["plan.json", "attempts/trial-0/inspect.json"])
def test_recovery_rejects_changed_frozen_or_committed_evidence(tmp_path, path):
    root = freeze(tmp_path / "run")

    def pause(directory, aid):
        cancel(root, "pause")
        return completed(directory, aid)

    execute(root, pause)
    (root / path).write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        execute(root, completed, resume=True)
    assert not (root / "attempts/trial-1").exists()


def test_resource_reservation_reconciliation_is_idempotent_and_pinned(tmp_path):
    resources = budget(tmp_path / "budget")
    request = {"run": "one", "role": "build", "seconds": 10}
    reserve(resources, "abc", request)
    reserve(resources, "abc", copy.deepcopy(request))
    assert resource_status(resources)["remaining_attempts"] == 9
    with pytest.raises(ValueError, match="binding mismatch"):
        reserve(resources, "abc", {**request, "seconds": 1})
    with pytest.raises(ValueError):
        ResourceLimits.model_validate(
            {"max_attempts": 1, "max_scheduled_seconds": 10, "max_spend_usd": 1}
        )


def test_os_lock_rejects_second_process_and_releases_after_process_death(tmp_path):
    path = tmp_path / "lock"
    with locked(path):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from pathlib import Path; from yassa.control import locked; "
                "c=locked(Path(__import__('sys').argv[1])); c.__enter__()",
                str(path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0 and "another controller" in result.stderr
    marker = tmp_path / "acquired"
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import time,sys; from pathlib import Path; from yassa.control import locked; "
            "c=locked(Path(sys.argv[1])); c.__enter__(); Path(sys.argv[2]).touch(); time.sleep(30)",
            str(path),
            str(marker),
        ]
    )
    try:
        import time

        until = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < until:
            time.sleep(0.02)
        assert marker.exists()
        process.kill()
        process.wait(timeout=10)
        with locked(path):
            pass
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)


def test_recovery_checks_referenced_artifact_bytes(tmp_path):
    root = freeze(tmp_path / "run")

    def pause(directory, aid):
        result = completed(directory, aid)
        result["output_id"] = EvidenceStore(root).put({"output.json": b"{}"})
        cancel(root, "pause")
        return result

    execute(root, pause)
    target = next((root / "artifacts").glob("*/files/output.json"))
    target.write_bytes(b"[]")
    with pytest.raises(ValueError, match="content mismatch"):
        execute(root, completed, resume=True)


def test_late_completed_return_rejects_retry_even_before_controller_commit(tmp_path):
    root, resources = freeze(tmp_path / "run", 1), budget(tmp_path / "resources")

    def crash(directory, aid):
        completed(directory, aid)
        raise SystemExit()

    with pytest.raises(SystemExit):
        execute(root, crash, resources=resources, infrastructure_retries=1)
    with pytest.raises(ValueError, match="extra chance"):
        execute(
            root,
            completed,
            resources=resources,
            resume=True,
            retry=["trial-0"],
            reason="unknown local return",
        )
    assert resource_status(resources)["remaining_attempts"] == 9
    assert not (root / "attempts/trial-0-retry-1").exists()


def test_stale_relocated_copy_cannot_retry_a_settled_shared_reservation(tmp_path):
    root, resources = freeze(tmp_path / "run", 1), budget(tmp_path / "resources")
    stale = tmp_path / "stale-copy"

    def adapter(directory, aid):
        shutil.copytree(root, stale, ignore=shutil.ignore_patterns("control.lock"))
        return completed(directory, aid)

    execute(root, adapter, resources=resources, infrastructure_retries=1)
    report = execute(
        stale,
        completed,
        resources=resources,
        resume=True,
        retry=["trial-0"],
        reason="stale local evidence",
    )
    assert "restore its original local evidence" in report.read_text()
    assert resource_status(resources)["remaining_attempts"] == 9
    assert not (stale / "attempts/trial-0-retry-1").exists()


@pytest.mark.parametrize("seconds", [float("nan"), float("inf"), 0])
def test_admission_rejects_unbounded_or_invalid_deadlines(tmp_path, seconds):
    root = freeze(tmp_path / "run", 1)
    controller = Controller(root, "test", None, False, (), (), None, 0)
    with pytest.raises(ValueError, match="positive bounded deadline"):
        controller.call("bad", "direct", "inspect-api", seconds, {}, root / "calls/bad", completed)
    assert not (root / "calls").exists()


def test_saved_retry_policy_cannot_be_edited_to_grant_more_attempts(tmp_path):
    root = freeze(tmp_path / "run")

    def pause(directory, aid):
        cancel(root, "pause")
        return completed(directory, aid)

    execute(root, pause)
    path = root / "control/run.json"
    policy = read_json(path)
    policy["retry_limit"] = 10
    path.write_bytes(canonical(policy))
    with pytest.raises(ValueError, match="policy identity changed"):
        execute(root, completed, resume=True)
    assert not (root / "attempts/trial-1").exists()
