import asyncio
from types import SimpleNamespace

import pytest
from test_native_context import BUILTINS, CONFIG, INPUTS, SandboxFixture

from yassa import native_execution
from yassa.records import canonical, digest


@pytest.mark.parametrize("problem", ["none", "timeout", "setup", "collector", "eval"])
def test_public_adapter_boundaries_with_controlled_clock(tmp_path, monkeypatch, problem):
    now = [0.0]

    class ClockedSandbox(SandboxFixture):
        async def exec(self, command, **kwargs):
            if problem == "setup" and command[:2] == ["codex", "--version"]:
                now[0] += 2
                raise RuntimeError("injected setup failure")
            if command[0] == "sh" and "native" in command:
                assert kwargs["timeout"] == 30 and kwargs["timeout_retry"] is False
                now[0] += 30.025 if problem == "timeout" else 7
                result = await super().exec(command, **kwargs)
                if problem == "timeout":
                    raise TimeoutError()
                return result
            now[0] += 1
            return await super().exec(command, **kwargs)

    fixture = ClockedSandbox(problem)
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
    auth = tmp_path / "auth.json"
    auth.write_bytes(canonical({"auth_mode": "chatgpt", "tokens": {"fixture": "synthetic"}}))
    root = tmp_path / "run"

    def fake_eval(task, **kwargs):
        assert kwargs["retry_on_error"] == 0 and kwargs["time_limit"] == 210
        now[0] += 3  # Framework setup, intentionally not separately attributed.
        if problem == "eval":
            raise RuntimeError("injected evaluation failure")
        state = SimpleNamespace(output=None, metadata={}, completed=False)
        error = None
        try:
            asyncio.run(task.solver(state, None))
        except Exception as caught:
            error = SimpleNamespace(message=str(caught))
        now[0] += 5  # Framework cleanup/logging; not inferred as cleanup timing.
        log = root / "attempts/fixture/inspect/fixture.eval"
        log.parent.mkdir()
        log.write_bytes(b"offline fixture")
        return [
            SimpleNamespace(
                samples=[SimpleNamespace(error=error)],
                error=None,
                status="error" if error else "success",
                location=str(log),
            )
        ]

    monkeypatch.setattr(native_execution, "eval", fake_eval)
    monkeypatch.setattr(native_execution, "sandbox", lambda: fixture)
    monkeypatch.setattr(native_execution, "RUNTIME", runtime)
    result = native_execution.execute_native(
        root,
        "fixture",
        "Use $local.",
        INPUTS,
        image="fixture",
        auth_path=auth,
        config=CONFIG,
        timeout=30,
        clock=lambda: now[0],
    )
    timing = result["lifecycle"]["phases"]
    assert timing["evaluation"]["duration_seconds"] == now[0]
    assert timing["sandbox_cleanup"]["duration_seconds"] is None
    assert timing["sandbox_provisioning"]["status"] == "unavailable"
    assert (root / "attempts/fixture/lifecycle.json").is_file()
    if problem in {"setup", "eval"}:
        assert result["status"] == "harness_failure"
        assert timing["native_command"]["status"] == "unavailable"
        assert "duration_seconds" not in result
        assert timing["capture_acceptance"]["status"] == "unavailable"
    else:
        duration = 30.025 if problem == "timeout" else 7
        assert result["duration_seconds"] == pytest.approx(duration)
        assert timing["native_command"]["duration_seconds"] == pytest.approx(duration)
        assert timing["native_command"]["status"] == (
            "budget_exhausted" if problem == "timeout" else "completed"
        )
        assert timing["capture_acceptance"]["status"] == (
            "failed" if problem == "collector" else "completed"
        )
        assert (
            timing["adapter_setup"]["end_offset_seconds"]
            == timing["native_command"]["start_offset_seconds"]
        )
        assert (
            timing["native_command"]["end_offset_seconds"]
            == timing["capture_acceptance"]["start_offset_seconds"]
        )
