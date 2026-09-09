"""Codex CLI in an Inspect Docker sandbox, using an explicit file allowlist."""

import io
import json
import tarfile
import time
from pathlib import Path

from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.solver import solver
from inspect_ai.util import ComposeConfig, ComposeService, SandboxEnvironmentSpec, sandbox

from .evidence import EvidenceStore, read_regular, safe_name, write_new
from .native_capture import archive_files, preserve_export, reject_secrets
from .native_context import (
    check_prompt,
    check_sessions,
    expected_catalog,
    validate_features,
    verify_builtins,
)
from .records import canonical, digest, parse_json

RUNTIME = Path(__file__).parent / "_native_runtime"
if not RUNTIME.is_dir():
    RUNTIME = Path(__file__).resolve().parents[2] / "runtime" / "codex"

# Only bounded, regular files are exported. No CODEX_HOME credential/config dump.
COLLECT = r"""
import base64, json, os, stat
from pathlib import Path
result = {"files": {}, "executable": [], "rejected": []}
INCLUDE_OUTPUT = True
total = 0
for prefix, base in [("output", "/work/output"),
                     ("sessions", "/home/runtime/codex/sessions"),
                     ("builtin-skills", "/home/runtime/codex/skills/.system")]:
    if prefix == "output" and not INCLUDE_OUTPUT:
        continue
    if Path(base).is_symlink():
        result["rejected"].append(base)
        continue
    for root, dirs, files in os.walk(base, followlinks=False):
        for name in list(dirs):
            if Path(root, name).is_symlink():
                result["rejected"].append(str(Path(root, name)))
                dirs.remove(name)
        for name in sorted(files):
            path = Path(root, name)
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > 10_000_000:
                result["rejected"].append(str(path))
                continue
            if total + info.st_size > 40_000_000:
                result["rejected"].append(str(path))
                continue
            total += info.st_size
            key = prefix + "/" + path.relative_to(base).as_posix()
            result["files"][key] = base64.b64encode(path.read_bytes()).decode()
            if info.st_mode & 0o111:
                result["executable"].append(key)
Path("/home/runtime/export.json").write_text(json.dumps(result), encoding="utf-8")
"""


def compose(image: str) -> ComposeConfig:
    return ComposeConfig(
        services={
            "default": ComposeService(
                image=image,
                init=True,
                command=["sleep", "infinity"],
                working_dir="/work",
                user="1000:1000",
                cap_drop=["ALL"],
                security_opt=[
                    "no-new-privileges:true",
                    "seccomp:unconfined",
                    "apparmor:unconfined",
                ],
                mem_limit="4g",
                cpus=2.0,
            )
        }
    )


def execute_native(
    root: Path,
    attempt_id: str,
    prompt: str,
    files: dict[str, bytes],
    *,
    image: str,
    auth_path: Path,
    config: bytes,
    timeout: int,
    executable: tuple[str, ...] = (),
) -> dict:
    """One fresh sample/container; no automatic inference retries or resumed sessions."""
    for name in files:
        safe_name(name)
        if not (name.startswith("input/") or name.startswith(".agents/skills/")):
            raise ValueError("subject files must be declared inputs or native skills")
    auth = read_regular(auth_path)
    auth_info = json.loads(auth)
    if auth_info.get("auth_mode") != "chatgpt" or not auth_info.get("tokens"):
        raise ValueError("native fixture requires saved ChatGPT CLI authentication")
    del auth_info
    secrets = tuple(
        value.encode()
        for value in json.loads(auth)["tokens"].values()
        if isinstance(value, str) and len(value) > 40
    )
    destination = root / "attempts" / attempt_id
    destination.mkdir(parents=True, exist_ok=False)
    store = EvidenceStore(root)
    input_id = store.put({"prompt.txt": prompt.encode(), **files})
    launch = {
        "id": attempt_id,
        "route": "native-codex-cli",
        "input_id": input_id,
        "config_sha256": digest(config),
        "image": image,
        "timeout_seconds": timeout,
        "auth": "saved ChatGPT login; injected privately, excluded from evidence",
        "retry_of": None,
    }
    write_new(destination / "launch.json", canonical(launch))
    collected = {"native_started": False, "captures": {}}

    @solver
    def native_cli():
        async def solve(state, generate):
            sb = sandbox()

            async def capture(label, *, output):
                script = (
                    COLLECT
                    if output
                    else COLLECT.replace("INCLUDE_OUTPUT = True", "INCLUDE_OUTPUT = False")
                )
                result = await sb.exec(["python3", "-c", script], timeout=30, timeout_retry=False)
                if not result.success:
                    raise RuntimeError("native evidence collection failed: " + result.stderr)
                raw = await sb.read_file("/home/runtime/export.json", text=False)
                artifact, exported, data = preserve_export(store, raw, secrets)
                collected["captures"][label] = {
                    "archive_id": artifact,
                    "rejected_paths": data["rejected"],
                }
                return exported, data

            version = await sb.exec(["codex", "--version"])
            collected["codex_version"] = version.stdout.strip()
            if version.stdout.strip() != "codex-cli 0.153.4":
                raise RuntimeError("native fixture requires verified Codex 0.153.4")
            await sb.write_file("/home/runtime/codex/config.toml", config)
            await sb.write_file("/home/runtime/codex/auth.json", auth)
            await sb.exec(["chmod", "600", "/home/runtime/codex/auth.json"])
            await sb.exec(["mkdir", "-p", "/work/output"])
            payload = io.BytesIO()
            with tarfile.open(fileobj=payload, mode="w") as archive:
                for name, data in sorted(files.items()):
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    info.mode = 0o755 if name in executable else 0o644
                    archive.addfile(info, io.BytesIO(data))
            await sb.write_file("/home/runtime/inputs.tar", payload.getvalue())
            installed = await sb.exec(["tar", "-xf", "/home/runtime/inputs.tar", "-C", "/work"])
            if not installed.success:
                raise RuntimeError("native input installation failed")
            await sb.exec(["rm", "/home/runtime/inputs.tar"])
            # All attempts independently verify the real command permissions.
            await sb.write_file("/work/input/boundary.txt", b"boundary sentinel\n")
            await sb.write_file("/work/.agents/skills/boundary/SKILL.md", b"boundary sentinel\n")
            await sb.write_file(
                "/home/runtime/boundary_probe.py", read_regular(RUNTIME / "boundary_probe.py")
            )
            probe = await sb.exec(
                [
                    "codex",
                    "sandbox",
                    "-P",
                    "trial",
                    "-C",
                    "/work",
                    "--",
                    "python3",
                    "/home/runtime/boundary_probe.py",
                ],
                timeout=30,
                timeout_retry=False,
            )
            collected["boundary"] = {
                "returncode": probe.returncode,
                "stdout": probe.stdout,
                "stderr": probe.stderr,
            }
            write_new(destination / "boundary.json", canonical(collected["boundary"]))
            if not probe.success or not all(json.loads(probe.stdout).values()):
                raise RuntimeError("Codex command boundary probe failed; no inference released")
            await sb.exec(["rm", "-rf", "/work/.agents/skills/boundary"])
            await sb.exec(["rm", "/work/input/boundary.txt", "/work/output/probe.txt"])
            # Render context without inference. Expected entries come from byte-pinned
            # built-ins and explicit inputs, never from the catalog being checked.
            collected["failure_stage"] = "catalog_preflight"
            features = await sb.exec(["codex", "features", "list"], timeout=30, timeout_retry=False)
            rendered = await sb.exec(
                ["sh", "-c", "codex debug prompt-input > /home/runtime/prompt-input.json"],
                timeout=30,
                timeout_retry=False,
            )
            prompt_input = await sb.read_file("/home/runtime/prompt-input.json", text=False)
            preflight_files = {
                "features.txt": features.stdout.encode(),
                "features-stderr.txt": features.stderr.encode(),
                "prompt-input.json": prompt_input,
                "prompt-stderr.txt": rendered.stderr.encode(),
            }
            reject_secrets(preflight_files, secrets)
            collected["preflight_id"] = archive_files(store, preflight_files)
            builtins, preflight_data = await capture("preflight", output=False)
            preflight = {"passed": False}
            try:
                if not features.success or not rendered.success or preflight_data["rejected"]:
                    raise ValueError("native context preflight command or collection failed")
                validate_features(config, features.stdout)
                pins = parse_json(read_regular(RUNTIME / "builtin-skills.json"))
                verify_builtins(builtins, pins)
                expected = expected_catalog(builtins, files)
                collected["expected_catalog_id"] = store.put_json(
                    {
                        "schema_version": 1,
                        "entries": expected,
                        "builtin_profile_sha256": digest(
                            read_regular(RUNTIME / "builtin-skills.json")
                        ),
                    },
                    "catalog.json",
                )
                preflight = check_prompt(prompt_input, expected)
            except (ValueError, KeyError, TypeError, UnicodeError) as error:
                preflight["error"] = str(error)
            collected["preflight_check_id"] = store.put_json(preflight, "check.json")
            if not preflight["passed"]:
                raise RuntimeError("native catalog preflight failed; no inference released")
            collected.pop("failure_stage")
            command = [
                "codex",
                "exec",
                "--strict-config",
                "--ignore-rules",
                "--skip-git-repo-check",
                "-C",
                "/work",
                "--json",
                "-o",
                "/home/runtime/final.txt",
                "-",
            ]
            collected["command"] = command
            collected["native_started"] = True
            started = time.monotonic()
            try:
                result = await sb.exec(
                    [
                        "sh",
                        "-c",
                        '"$@" > /home/runtime/events.jsonl 2> /home/runtime/stderr.txt',
                        "native",
                        *command,
                    ],
                    input=prompt,
                    timeout=timeout,
                    timeout_retry=False,
                )
                collected["exit_code"] = result.returncode
                collected["status"] = "completed" if result.success else "cli_failure"
            except TimeoutError:
                collected["exit_code"] = None
                collected["status"] = "budget_exhausted"
            collected["duration_seconds"] = time.monotonic() - started
            collected["native_status"] = collected["status"]
            # Independent captures survive output-path rejection and collector failure.
            errors, logs = [], {}
            for name in ("events.jsonl", "stderr.txt", "final.txt"):
                try:
                    logs[name] = await sb.read_file("/home/runtime/" + name, text=False)
                except FileNotFoundError:
                    logs[name] = b""
                except Exception as error:
                    errors.append(
                        {"stage": "native_logs_capture", "file": name, "error": str(error)}
                    )
            try:
                reject_secrets(logs, secrets)
                collected["native_logs_id"] = archive_files(store, logs)
            except ValueError as error:
                errors.append({"stage": "native_logs_capture", "error": str(error)})
                logs = {}
            control = {}
            try:
                control, data = await capture("transcripts", output=False)
                if data["rejected"]:
                    raise ValueError("native transcript collection rejected paths")
                collected["transcript_id"] = store.put(control)
            except Exception as error:
                errors.append({"stage": "transcript_capture", "error": str(error)})
            try:
                exported, data = await capture("output", output=True)
                exported.update(logs)
                collected["output_id"] = store.put(exported, executable=data["executable"])
                collected["rejected_paths"] = data["rejected"]
            except Exception as error:
                errors.append({"stage": "output_capture", "error": str(error)})
            postflight = {"passed": False}
            try:
                verify_builtins(control, pins)
                postflight = check_sessions(control, expected)
            except (ValueError, KeyError, TypeError, UnicodeError) as error:
                postflight["error"] = str(error)
            collected["catalog_check_id"] = store.put_json(postflight, "check.json")
            if not postflight["passed"]:
                errors.append(
                    {"stage": "catalog_postflight", "error": "native session catalog mismatch"}
                )
            if errors:
                collected["failures"] = errors
                collected["failure_stage"] = errors[0]["stage"]
                raise RuntimeError(
                    "native acceptance failed; preserved captures and checks describe failures"
                )
            state.output = ModelOutput.from_content(
                "native-codex-cli", logs["final.txt"].decode("utf-8", errors="replace")
            )
            state.metadata["native_attempt"] = collected.copy()
            state.completed = True
            return state

        return solve

    # Inspect owns lifecycle, isolation and logs; native Codex owns model calls.
    # The inert model satisfies Inspect's Task model field and is never generated.
    inert = get_model("mockllm/model", memoize=False)
    task = Task(
        name=attempt_id,
        dataset=[Sample(id=attempt_id, input=prompt, metadata={"native_launch": launch})],
        solver=native_cli(),
        scorer=None,
        model=inert,
        sandbox=SandboxEnvironmentSpec("docker", compose(image)),
    )
    logs = eval(
        task,
        model=inert,
        log_dir=str(destination / "inspect"),
        sandbox_prebuilt=True,
        log_format="eval",
        display="none",
        notification=False,
        ctl_server=False,
        log_shared=False,
        log_realtime=False,
        score=False,
        epochs=1,
        retry_on_error=0,
        fail_on_error=False,
        max_samples=1,
        max_tasks=1,
        time_limit=timeout + 180,
    )
    log = logs[0]
    sample = log.samples[0] if log.samples else None
    error = sample.error if sample and sample.error else log.error
    record = {
        **launch,
        **collected,
        "status": "harness_failure" if error else collected.get("status", "harness_failure"),
        "error": error.message if error else None,
        "inspect_log": Path(log.location).relative_to(root).as_posix(),
        "inspect_status": log.status,
        "inspect_model_calls": 0,
    }
    write_new(destination / "result.json", canonical(record))
    return record
