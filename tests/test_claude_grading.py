"""Claude CLI boundary and grading dispatch checks; no live model requests."""

import copy
import shlex
from types import SimpleNamespace

import pytest
from inspect_ai.model import ChatMessageSystem, ChatMessageUser

from yassa import role_claude
from yassa.evidence import verify_run
from yassa.grading import execute_grades, prepare_grades, report_grades
from yassa.records import canonical, parse_json

MODEL = "claude-sonnet-5"
SECRET = "fixture-private-access-" * 4
REFRESHED = "fixture-new-access-" * 4


def role():
    return role_claude.ClaudeGradeRole(
        adapter="native-claude-code",
        model="anthropic/" + MODEL,
        image="sha256:" + "a" * 64,
        max_output_tokens=2000,
        timeout_seconds=30,
        reasoning_effort="medium",
    )


def auth(secret=SECRET):
    return canonical(
        {
            "claudeAiOauth": {
                "accessToken": secret,
                "refreshToken": "fixture-refresh-" * 4,
                "scopes": ["user:inference"],
            }
        }
    )


def events():
    return [
        {
            "type": "system",
            "subtype": "init",
            "model": MODEL,
            "session_id": "fresh",
            "tools": ["StructuredOutput"],
            "mcp_servers": [],
            "plugins": [],
            "skills": [],
        },
        {
            "type": "assistant",
            "message": {
                "model": MODEL,
                "content": [
                    {
                        "type": "tool_use",
                        "id": "valid-submission",
                        "name": "StructuredOutput",
                        "input": {"components": {"format": True}, "rationale": "Evidence."},
                    }
                ],
            },
        },
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": '{"components":{"format":true},"rationale":"Evidence."}',
            "structured_output": {"components": {"format": True}, "rationale": "Evidence."},
            "modelUsage": {MODEL: {"inputTokens": 10, "outputTokens": 20}},
            "usage": {"input_tokens": 10, "output_tokens": 20},
            "num_turns": 2,
        },
    ]


@pytest.mark.parametrize(
    "problem",
    [
        "tools",
        "metadata",
        "model",
        "retry",
        "tool-call",
        "terminal",
        "turns",
        "background",
        "missing-submission",
        "mismatched-submission",
        "duplicate-submission",
    ],
)
def test_closed_capture_rejects_uncontrolled_work(problem):
    data = events()
    if problem == "tools":
        data[0]["tools"] = ["Read"]
    elif problem == "metadata":
        del data[0]["plugins"]
    elif problem == "model":
        data[1]["message"]["model"] = "claude-other"
    elif problem == "retry":
        data.insert(1, {"type": "system", "subtype": "api_retry"})
    elif problem == "tool-call":
        data[1]["message"]["content"] = [{"type": "tool_use", "name": "Read"}]
    elif problem == "turns":
        data[-1]["num_turns"] = 3
    elif problem == "background":
        data[-1]["modelUsage"]["claude-haiku-fixture"] = {"outputTokens": 12}
    elif problem == "missing-submission":
        del data[-1]["structured_output"]
    elif problem == "mismatched-submission":
        data[-1]["structured_output"]["components"]["format"] = False
    elif problem == "duplicate-submission":
        data[1]["message"]["content"].append(copy.deepcopy(data[1]["message"]["content"][0]))
    else:
        data[-1]["subtype"] = "error_max_turns"
    with pytest.raises(ValueError):
        role_claude.parse_capture(b"\n".join(map(canonical, data)), role())


class SandboxFixture:
    def __init__(self, problem):
        self.problem, self.files = problem, {}

    async def write_file(self, name, data):
        self.files[name] = data

    async def read_file(self, name, text=True):
        return self.files[name]

    async def exec(self, argv, **kwargs):
        stdout = ""
        if argv == ["claude", "--version"]:
            stdout = role_claude.VERSION + " (Claude Code)"
        elif argv[0] == "sh":
            command = shlex.split(argv[-1])
            assert command[command.index("--tools") + 1] == ""
            assert all(
                flag in command
                for flag in [
                    "--safe-mode",
                    "--restricted",
                    "--strict-mcp-config",
                    "--no-session-persistence",
                ]
            )
            assert "--bare" not in command and "CLAUDE_CODE_MAX_RETRIES=0" in command
            assert "CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1" in command
            assert kwargs["timeout"] == 30 and kwargs["timeout_retry"] is False
            data = events()
            if self.problem == "context":
                data[0]["skills"] = ["unrelated"]
            self.files["/home/runtime/events.jsonl"] = b"\n".join(map(canonical, data))
            self.files["/home/runtime/stderr.txt"] = b""
            if self.problem in {"refresh", "secret"}:
                self.files["/home/claude/.claude/.credentials.json"] = auth(REFRESHED)
            if self.problem == "secret":
                self.files["/home/runtime/stderr.txt"] = REFRESHED.encode()
            if self.problem == "timeout":
                raise TimeoutError()
        return SimpleNamespace(success=True, returncode=0, stdout=stdout, stderr="")


@pytest.mark.parametrize("problem", ["none", "context", "refresh", "secret", "timeout"])
def test_actual_inspect_claude_capture_and_private_refresh(tmp_path, monkeypatch, problem):
    sb = SandboxFixture(problem)
    monkeypatch.setattr(role_claude, "sandbox", lambda: sb)
    monkeypatch.setattr(role_claude, "SandboxEnvironmentSpec", lambda *args: None)
    credential = tmp_path / "auth.json"
    credential.write_bytes(auth())
    destination = tmp_path / "call"
    result = role_claude.call_claude(
        destination,
        role(),
        [
            ChatMessageSystem(content="Grade the output."),
            ChatMessageUser(content="Submitted evidence."),
        ],
        "calibration",
        credential,
        {"type": "object"},
    )
    expected = (
        "budget_exhausted"
        if problem == "timeout"
        else "harness_failure"
        if problem in {"context", "secret"}
        else "completed"
    )
    assert result["status"] == expected
    assert result["native_started"] and result["inspect_model_calls"] == 0
    assert credential.read_bytes() == (auth(REFRESHED) if problem == "refresh" else auth())
    assert bool(result["completion"]) == (expected == "completed")
    if problem == "context":
        assert result["usage"]["input_tokens"] == 10
        assert result["model_usage"][MODEL]["outputTokens"] == 20
    assert (destination / "events.jsonl").exists() == (problem != "secret")
    for p in destination.rglob("*"):
        if p.is_file():
            assert (
                SECRET.encode() not in p.read_bytes() and REFRESHED.encode() not in p.read_bytes()
            )


def test_refresh_refuses_concurrent_login_change(tmp_path):
    path = tmp_path / "auth.json"
    path.write_bytes(auth("concurrent-login"))
    with pytest.raises(ValueError, match="concurrently"):
        role_claude.persist_refresh(path, auth(), auth(REFRESHED))
    assert path.read_bytes() == auth("concurrent-login")


@pytest.mark.parametrize("problem", [None, "no-allowance", "no-failed-validation", "other-error"])
def test_one_explicit_schema_repair_preserves_both_submissions(problem):
    data = events()
    bad = copy.deepcopy(data[1])
    bad["message"]["content"][0].update(id="invalid-submission", input={"wrapper": {}})
    feedback = {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "invalid-submission",
                    "is_error": True,
                    "content": "Output does not match required schema: missing components",
                }
            ]
        },
    }
    if problem == "no-failed-validation":
        feedback["message"]["content"][0]["is_error"] = False
    elif problem == "other-error":
        feedback["message"]["content"][0]["content"] = "A semantic judgment was wrong"
    data[1:1] = [bad, feedback]
    data[-1]["num_turns"] = 3
    config = role().model_copy(update={"max_output_repairs": 0 if problem == "no-allowance" else 1})
    raw = b"\n".join(map(canonical, data))
    if problem:
        with pytest.raises(ValueError):
            role_claude.parse_capture(raw, config)
    else:
        result = role_claude.parse_capture(raw, config)
        assert result["output_repairs"] == 1
        assert parse_json(result["completion"])["components"] == {"format": True}


def test_native_grader_public_freeze_execution_and_replay(tmp_path, monkeypatch):
    from test_execution_roles import direct_run, grade_request

    monkeypatch.setattr(
        "yassa.direct_runner.subprocess", SimpleNamespace(run=lambda *a, **kw: None)
    )
    source, _ = direct_run(tmp_path, monkeypatch, native=True)
    original_seal = verify_run(source)
    request = grade_request()
    request["role"] = role().model_dump(mode="json")
    request_path = tmp_path / "grading-request.json"
    request_path.write_bytes(canonical(request))
    monkeypatch.setattr("yassa.grading.admit_claude", lambda role: role_claude.runtime_files())
    root = prepare_grades(source, request_path, tmp_path / "grades").parent
    with pytest.raises(ValueError, match="auth-file"):
        execute_grades(root)
    assert not (root / "calls").exists()
    seen = []

    def adapter(directory, role, messages, stage, auth_path, response_schema):
        assert auth_path == tmp_path / "private-auth"
        assert response_schema["properties"]["components"]["required"] == ["format"]
        payload = parse_json(messages[1].text)
        assert set(payload) == {"rubric", "task_requirements", "input_files", "submitted_output"}
        seen.append(copy.deepcopy(payload))
        result = {
            "status": "completed",
            "completion": canonical(
                {
                    "components": {"format": "totals" in payload["submitted_output"]},
                    "rationale": "Recorded format judgment.",
                }
            ).decode(),
        }
        directory.mkdir(parents=True)
        (directory / "result.json").write_bytes(canonical(result))
        return result

    monkeypatch.setattr("yassa.grading.call_claude", adapter)
    report = execute_grades(root, tmp_path / "private-auth")
    assert len(seen) == 10
    assert parse_json((report.parent / "scores.json").read_bytes())["summary"]["missing"] == 0
    replay = report_grades(root, "repeat")
    assert (report.parent / "scores.json").read_bytes() == (
        replay.parent / "scores.json"
    ).read_bytes()
    assert verify_run(source) == original_seal
