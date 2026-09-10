"""Closed Claude Code grading in fresh Inspect containers using saved CLI OAuth."""

import os
import shlex
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Annotated, Literal

from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.solver import solver
from inspect_ai.util import ComposeConfig, ComposeService, SandboxEnvironmentSpec, sandbox
from pydantic import Field, StrictInt

from .evidence import read_regular, write_new
from .native_capture import reject_secrets
from .records import canonical, parse_json
from .role_api import api_identity
from .study import Record

VERSION = "2.1.267"
RUNTIME = Path(__file__).parent / "_claude_runtime"
if not RUNTIME.is_dir():
    RUNTIME = Path(__file__).resolve().parents[2] / "runtime" / "claude"


class ClaudeGradeRole(Record):
    adapter: Literal["native-claude-code"]
    model: Annotated[str, Field(pattern=r"^anthropic/claude-[a-zA-Z0-9_.-]+$")]
    image: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    max_output_tokens: Annotated[StrictInt, Field(ge=100, le=32000)]
    timeout_seconds: Annotated[StrictInt, Field(ge=30, le=300)]
    reasoning_effort: Literal["low", "medium", "high"]
    max_output_repairs: Annotated[StrictInt, Field(ge=0, le=1)] = 0


def runtime_files():
    return {p.name: read_regular(p) for p in sorted(RUNTIME.iterdir()) if p.is_file()}


def admit_claude(role):
    subprocess.run(["docker", "image", "inspect", role.image], capture_output=True, check=True)
    return runtime_files()


def credentials(raw):
    data = parse_json(raw)
    auth = data.get("claudeAiOauth", {})
    if not auth.get("accessToken") or "user:inference" not in auth.get("scopes", []):
        raise ValueError("Claude Code grading requires saved claude.ai OAuth credentials")
    return tuple(auth[k].encode() for k in ("accessToken", "refreshToken") if auth.get(k))


def persist_refresh(path, original, refreshed):
    """Keep the CLI's rotated login private; never replace a concurrently changed login."""
    credentials(refreshed)
    if refreshed == original:
        return "unchanged"
    if read_regular(path) != original:
        raise ValueError("Claude login changed concurrently; refreshed login was not installed")
    descriptor, temporary = tempfile.mkstemp(prefix=".yassa-auth-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(refreshed)
        os.replace(temporary, path)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()
    return "refreshed by Claude Code"


def command(role, system, response_schema):
    return [
        "env",
        "DISABLE_AUTOUPDATER=1",
        "DISABLE_TELEMETRY=1",
        "DISABLE_ERROR_REPORTING=1",
        "CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1",
        "CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL=1",
        "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK=1",
        "CLAUDE_CODE_MAX_RETRIES=0",
        f"MAX_STRUCTURED_OUTPUT_RETRIES={2 if role.max_output_repairs else 0}",
        f"CLAUDE_CODE_MAX_OUTPUT_TOKENS={role.max_output_tokens}",
        "claude",
        "--print",
        "--safe-mode",
        "--restricted",
        "--tools",
        "",
        "--disallowedTools",
        "mcp__*",
        "--disable-slash-commands",
        "--strict-mcp-config",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--setting-sources",
        "",
        "--settings",
        '{"disableAllHooks":true}',
        "--no-session-persistence",
        "--max-turns",
        str(2 + role.max_output_repairs),
        "--model",
        role.model.split("/", 1)[1],
        "--effort",
        role.reasoning_effort,
        "--system-prompt",
        system,
        "--json-schema",
        canonical(response_schema).decode(),
        "--output-format",
        "stream-json",
        "--verbose",
    ]


def parse_capture(raw, role):
    events = [parse_json(line) for line in raw.splitlines() if line.strip()]
    initial = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    final = [e for e in events if e.get("type") == "result"]
    if len(initial) != 1 or len(final) != 1:
        raise ValueError("Claude capture requires one init and one result event")
    init, result = initial[0], final[0]
    if init.get("tools") != ["StructuredOutput"]:
        raise ValueError("Claude grading requires only the StructuredOutput response tool")
    for field in ("mcp_servers", "plugins", "skills"):
        if init.get(field) != []:
            raise ValueError(f"Claude closed grading context has missing or nonempty {field}")
    expected = role.model.split("/", 1)[1]
    if init.get("model") != expected:
        raise ValueError("Claude configured model differs from recorded init model")
    if any(e.get("subtype") == "api_retry" for e in events):
        raise ValueError("Claude made an undeclared API retry")
    submissions = []
    for event in events:
        if event.get("type") == "assistant":
            message = event.get("message", {})
            if message.get("model") != expected:
                raise ValueError("Claude response model differs from requested model")
            for content in message.get("content", []):
                if content.get("type") == "server_tool_use":
                    raise ValueError("Claude emitted a server tool call in closed grading")
                if content.get("type") == "tool_use":
                    if content.get("name") != "StructuredOutput":
                        raise ValueError(
                            "Claude emitted a non-response tool call in closed grading"
                        )
                    submissions.append((content.get("id"), content.get("input")))
    if set(result.get("modelUsage", {})) - {expected}:
        raise ValueError("Claude used an undeclared model")
    if result.get("subtype") != "success" or result.get("is_error") is not False:
        raise ValueError("Claude did not return a successful terminal result")
    submitted = result.get("structured_output")
    if (
        not isinstance(submitted, dict)
        or not 1 <= len(submissions) <= 1 + role.max_output_repairs
        or any(not isinstance(sid, str) or not sid for sid, _ in submissions)
        or submissions[-1][1] != submitted
    ):
        raise ValueError(
            "Claude structured submission does not match the terminal result or repair cap"
        )
    failed_validation = {
        content.get("tool_use_id")
        for event in events
        if event.get("type") == "user"
        for content in event.get("message", {}).get("content", [])
        if content.get("type") == "tool_result"
        and content.get("is_error") is True
        and isinstance(content.get("content"), str)
        and content["content"].startswith("Output does not match required schema:")
    }
    if len({s[0] for s in submissions}) != len(submissions) or any(
        sid not in failed_validation for sid, _ in submissions[:-1]
    ):
        raise ValueError("Claude output repair lacks a distinct failed schema-validation record")
    if submissions[-1][0] in failed_validation:
        raise ValueError("Claude terminal submission failed schema validation")
    if (
        type(result.get("num_turns")) is not int
        or not 1 <= result["num_turns"] <= 2 + role.max_output_repairs
    ):
        raise ValueError("Claude grading exceeded its declared turn cap")
    return {
        "completion": canonical(submitted).decode(),
        "completion_source": "terminal structured_output matching the final response-tool input",
        "output_repairs": len(submissions) - 1,
        "usage": result.get("usage"),
        "model_usage": result.get("modelUsage"),
        "reported_model": init["model"],
        "session_id": init.get("session_id"),
        "num_turns": result.get("num_turns"),
        "reported_cost_usd": result.get("total_cost_usd"),
        "context_check": {
            "passed": True,
            "tools": ["StructuredOutput"],
            "mcp_servers": [],
            "plugins": [],
            "skills": [],
        },
    }


def call_claude(directory, role, messages, stage, auth_path, response_schema):
    if auth_path is None:
        raise ValueError("Claude Code grading requires --auth-file")
    auth = read_regular(auth_path)
    secret_values = credentials(auth)
    if len(messages) != 2 or [m.role for m in messages] != ["system", "user"]:
        raise ValueError("Claude grading requires exactly one system and one user message")
    directory.mkdir(parents=True, exist_ok=False)
    argv = command(role, messages[0].text, response_schema)
    request = {
        "stage": stage,
        "role": role.model_dump(mode="json"),
        "identity": api_identity(role.model),
        "messages": [m.model_dump(mode="json") for m in messages],
        "command": argv,
        "response_schema": response_schema,
        "cli_version": VERSION,
        "auth": "saved Claude Code OAuth; private injection/refresh, excluded from evidence",
        "limits": {
            "automatic_retries": 0,
            "max_turns": 2 + role.max_output_repairs,
            "max_output_repairs": role.max_output_repairs,
            "hard_spend_cap": None,
            "hard_input_token_cap": None,
            "setup_export_included": False,
        },
    }
    write_new(directory / "request.json", canonical(request))
    collected = {"completion": None, "usage": None, "native_started": False}
    started = time.monotonic()

    @solver
    def claude_cli():
        async def solve(state, generate):
            sb = sandbox()
            version = await sb.exec(["claude", "--version"], timeout=30, timeout_retry=False)
            if version.stdout.strip() != VERSION + " (Claude Code)":
                raise ValueError("Claude Code version does not match the pinned adapter")
            await sb.write_file("/home/claude/.claude/.credentials.json", auth)
            await sb.exec(["chmod", "600", "/home/claude/.claude/.credentials.json"])
            await sb.write_file("/home/runtime/input.txt", messages[1].text)
            command_started = time.monotonic()
            collected["native_started"] = True
            try:
                native = await sb.exec(
                    [
                        "sh",
                        "-c",
                        shlex.join(argv)
                        + " < /home/runtime/input.txt > /home/runtime/events.jsonl"
                        + " 2> /home/runtime/stderr.txt",
                    ],
                    timeout=role.timeout_seconds,
                    timeout_retry=False,
                )
                collected["returncode"] = native.returncode
                collected["status"] = "completed" if native.success else "cli_failure"
            except TimeoutError:
                collected["status"] = "budget_exhausted"
            finally:
                collected["native_command_seconds"] = time.monotonic() - command_started
            refreshed = await sb.read_file("/home/claude/.claude/.credentials.json", text=False)
            all_secrets = secret_values + credentials(refreshed)
            captures = {}
            for name in ("events.jsonl", "stderr.txt"):
                captures[name] = await sb.read_file("/home/runtime/" + name, text=False)
            reject_secrets(captures, all_secrets)
            for name, content in captures.items():
                write_new(directory / name, content)
            collected["auth_state"] = persist_refresh(auth_path, auth, refreshed)
            terminal = [
                event
                for line in captures["events.jsonl"].splitlines()
                if line.strip() and (event := parse_json(line)).get("type") == "result"
            ]
            if len(terminal) == 1:
                # Resource evidence remains available even when context acceptance fails.
                collected.update(
                    usage=terminal[0].get("usage"),
                    model_usage=terminal[0].get("modelUsage"),
                    reported_cost_usd=terminal[0].get("total_cost_usd"),
                )
            if collected["status"] == "completed":
                collected.update(parse_capture(captures["events.jsonl"], role))
            state.output = ModelOutput.from_content(
                "native-claude-code", collected["completion"] or ""
            )
            state.completed = True
            return state

        return solve

    inert = get_model("mockllm/model", memoize=False)
    config = ComposeConfig(
        services={
            "default": ComposeService(
                image=role.image,
                init=True,
                command=["sleep", "infinity"],
                working_dir="/work",
                user="1000:1000",
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
                mem_limit="2g",
                cpus=2.0,
            )
        }
    )
    try:
        logs = eval(
            Task(
                name="claude-grade",
                dataset=[Sample(id=stage, input=messages)],
                solver=claude_cli(),
                model=inert,
                sandbox=SandboxEnvironmentSpec("docker", config),
            ),
            model=inert,
            sandbox_prebuilt=True,
            log_dir=str(directory / "inspect"),
            log_format="json",
            score=False,
            retry_on_error=0,
            max_retries=0,
            epochs=1,
            max_samples=1,
            max_tasks=1,
            time_limit=role.timeout_seconds + 120,
            cache=False,
            ctl_server=False,
            display="none",
            notification=False,
            log_shared=False,
            log_realtime=False,
        )
        if len(logs) != 1 or not logs[0].samples or len(logs[0].samples) != 1:
            raise ValueError("Claude role produced no unique Inspect sample")
        sample = logs[0].samples[0]
        if sample.error or logs[0].status != "success":
            raise ValueError(sample.error.message if sample.error else "Claude Inspect task failed")
    except Exception as error:
        collected.update(status="harness_failure", error=str(error), completion=None)
    record = {
        **collected,
        "identity": request["identity"],
        "duration_seconds": time.monotonic() - started,
        "inspect_model_calls": 0,
    }
    reject_secrets({"result": canonical(record)}, secret_values)
    write_new(directory / "result.json", canonical(record))
    return record
