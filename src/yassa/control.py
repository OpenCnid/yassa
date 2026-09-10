"""Durable local orchestration and shared, conservative launch admission.

Provider execution is not exactly once. A launch without a committed return is
uncertain, even if Inspect retained a partial log. Locks cover local controllers;
the shared ledger reserves the full declared deadline before effectful work.
"""

import math
import os
import time
import uuid
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from typing import Annotated

from pydantic import Field, StrictInt

from .evidence import EvidenceStore, inventory, read_regular, reject_links, write_new
from .records import canonical, digest, identity, parse_json
from .study import Record

CURRENT = ContextVar("yassa_controller", default=None)
RETRYABLE = {"harness_failure", "provider_failure", "cli_failure", "infrastructure_failure"}


class ResourceLimits(Record):
    max_attempts: Annotated[StrictInt, Field(ge=1)]
    max_scheduled_seconds: Annotated[StrictInt, Field(ge=1)]


class ControlStopped(ValueError):
    """A durable pause; no additional subject work is scheduled."""


@contextmanager
def locked(path):
    """Nonblocking OS lock, automatically released on process death, including Windows."""
    reject_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError("another controller owns this run/resource ledger") from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def read_json(path):
    return parse_json(read_regular(path))


def put_json(path, value):
    write_new(path, canonical(value))


def same_or_new(path, data):
    """Reconstruct an identical binding/result after interruption, never replace it."""
    if path.exists():
        if read_regular(path) != data:
            raise ValueError(f"recovery evidence differs: {path}")
    else:
        write_new(path, data)


def check_freeze(root):
    freeze = read_json(root / "freeze-seal.json")
    body = {k: v for k, v in freeze.items() if k != "id"}
    if "id" in freeze and identity(body) != freeze["id"]:
        raise ValueError("invalid freeze identity")
    for entry in freeze["files"]:
        content = read_regular(root / entry["path"])
        if len(content) != entry["size"] or digest(content) != entry["sha256"]:
            raise ValueError("prepared evidence changed after freeze")
    return freeze


def verify_execution_freeze(root):
    """Inside a managed run execution files are additional to the unchanged freeze."""
    freeze = check_freeze(root)
    if CURRENT.get() is None:
        if [x for x in inventory(root) if x["path"] != "freeze-seal.json"] != freeze["files"]:
            raise ValueError("execution already started; use explicit resume")


def resource_init(root, limits):
    from .app import external_root

    limits = ResourceLimits.model_validate(limits)
    root = external_root(root)
    root.mkdir(parents=True, exist_ok=False)
    body = {"schema_version": 1, "nonce": uuid.uuid4().hex, "limits": limits.model_dump()}
    put_json(root / "resources.json", {"id": identity(body), **body})
    return root / "resources.json"


def resource_config(root):
    config = read_json(root / "resources.json")
    if config.get("schema_version") != 1 or identity(
        {k: v for k, v in config.items() if k != "id"}
    ) != config.get("id"):
        raise ValueError("invalid resource ledger identity")
    ResourceLimits.model_validate(config["limits"])
    return config


def reserve(root, key, request):
    with locked(root / "resource.lock"):
        config = resource_config(root)
        path = root / "reservations" / (key + ".json")
        if path.exists():
            if read_json(path) != request:
                raise ValueError("resource reservation binding mismatch")
            return False
        rows = [read_json(p) for p in sorted((root / "reservations").glob("*.json"))]
        if len(rows) + 1 > config["limits"]["max_attempts"] or (
            sum(r["seconds"] for r in rows) + request["seconds"]
            > config["limits"]["max_scheduled_seconds"]
        ):
            raise ControlStopped("shared resource budget exhausted before launch")
        put_json(path, request)
        return True


def usage_record(root, result, route):
    usage = result.get("usage")
    if route == "native-codex-cli":
        from .native_capture import recorded_native_files
        from .native_resources import usage_evidence

        try:
            usage = usage_evidence(recorded_native_files(EvidenceStore(root), result))
        except (ValueError, KeyError, TypeError, UnicodeError) as error:
            usage = {"unavailable": str(error)}
    return {
        "status": result["status"],
        "duration_seconds": result.get("duration_seconds", (usage or {}).get("duration_seconds")),
        "native_command_seconds": result.get("native_command_seconds"),
        "duration_scope": "native command; excludes setup/export"
        if route in {"native-codex-cli", "preparation-native"}
        else "adapter elapsed; native_command_seconds is separate where available",
        "usage": usage,
        "reported_cost_usd": result.get("reported_cost_usd"),
        "model_usage": result.get("model_usage"),
        "output_repairs": result.get("output_repairs"),
        "hard_spend_cap": None,
        "usage_scope": "recorded usage only; unavailable or interrupted usage is not zero",
    }


def _attempts(root):
    return [read_json(p) for p in sorted((root / "control" / "attempts").glob("*/launch.json"))]


def control_config(root):
    config = read_json(root / "control/run.json")
    if config.get("schema_version") != 1 or config.get("policy_id") != identity(
        {k: v for k, v in config.items() if k != "policy_id"}
    ):
        raise ValueError("execution policy identity changed")
    return config


def _completion(root, launch):
    path = root / "control" / "attempts" / launch["attempt"] / "completion.json"
    return read_json(path) if path.exists() else None


def selected_result(root, logical, fallback):
    """Resolve an explicitly selected retry for offline grading replay."""
    attempts = [a for a in _attempts(root) if a["logical"] == logical]
    if attempts:
        selected = max(attempts, key=lambda a: a["number"])
        completion = _completion(root, selected)
        if completion is not None:
            return completion["result"]
    return read_json(fallback)


def result_path(root, logical, fallback):
    attempts = [a for a in _attempts(root) if a["logical"] == logical]
    if not attempts:
        return fallback
    selected = max(attempts, key=lambda a: a["number"])
    path = root / selected["directory"] / "result.json"
    return (
        path
        if path.exists()
        else root / "control/attempts" / selected["attempt"] / "completion.json"
    )


def control_link(root):
    return (
        "\n- [Launch budget, all attempts, retries and recovery](../../control/summary.json)\n"
        if (root / "control/summary.json").exists()
        else ""
    )


class Controller:
    def __init__(
        self,
        root,
        kind,
        resources,
        resume,
        retry,
        abandon,
        reason,
        retry_limit,
        cancellation_baseline=(),
    ):
        self.root, self.kind = root, kind
        self.resources = Path(resources).resolve() if resources else None
        self.retry, self.abandon = set(retry), set(abandon)
        self.reason, self.resume = reason, resume
        if (self.retry or self.abandon) and (not resume or not reason or not reason.strip()):
            raise ValueError("retry/missing decisions require --resume and a nonempty --reason")
        if self.retry & self.abandon:
            raise ValueError("an attempt cannot be both retried and marked missing")
        if type(retry_limit) is not int or retry_limit < 0:
            raise ValueError("infrastructure retries must be a nonnegative integer")
        config_path = root / "control" / "run.json"
        if config_path.exists():
            if not resume:
                raise ValueError("execution already started; use --resume")
            self.config = control_config(root)
            if self.config["kind"] != kind:
                raise ValueError("recovery route mismatch")
            configured = self.config["resources"]
            if bool(configured) != bool(self.resources) or (
                configured and resource_config(self.resources) != configured
            ):
                raise ValueError("resume requires the same shared resource ledger")
            if retry_limit and retry_limit != self.config["retry_limit"]:
                raise ValueError("retry policy changed since first execution")
        else:
            if resume:
                raise ValueError(
                    "no durable controller to resume; preserve legacy interrupted work"
                )
            if retry_limit and not self.resources:
                raise ValueError("retry allowance requires an explicit shared resource budget")
            self.config = {
                "schema_version": 1,
                "id": uuid.uuid4().hex,
                "kind": kind,
                "freeze_sha256": digest(read_regular(root / "freeze-seal.json")),
                "resources": resource_config(self.resources) if self.resources else None,
                "retry_limit": retry_limit,
            }
            self.config["policy_id"] = identity(self.config)
        if digest(read_regular(root / "freeze-seal.json")) != self.config["freeze_sha256"]:
            raise ValueError("run freeze identity changed")
        launches = _attempts(root)
        latest = {}
        for launch in launches:
            if (
                launch["logical"] not in latest
                or launch["number"] > latest[launch["logical"]]["number"]
            ):
                latest[launch["logical"]] = launch
        for name in self.retry | self.abandon:
            if name not in latest:
                raise ValueError("recovery decision names an unknown logical attempt: " + name)
            previous = _completion(root, latest[name])
            if previous and (name in self.abandon or previous["result"]["status"] not in RETRYABLE):
                raise ValueError(
                    "only infrastructure failures or uncertain launches can be retried"
                )
            if name in self.retry and latest[name]["number"] > self.config["retry_limit"]:
                raise ValueError("frozen infrastructure retry allowance exhausted")
        sessions = root / "control" / "sessions"
        ignored = set()
        for path in sessions.glob("*.json"):
            ignored.update(read_json(path)["cancel_requests"])
        self.cancel_ignored = ignored
        if resume:
            # Resume acknowledges only requests that preceded this invocation.
            self.cancel_ignored.update(cancellation_baseline)
        self.cancellation_baseline = cancellation_baseline if resume else ()
        self.session = {
            "resume": resume,
            "retry": sorted(self.retry),
            "missing": sorted(self.abandon),
            "reason": reason,
            "cancel_requests": sorted(self.cancel_ignored),
            "time": time.time(),
        }
        self.started = False

    def begin(self):
        if self.started:
            return
        same_or_new(self.root / "control/run.json", canonical(self.config))
        for name in self.cancellation_baseline:
            same_or_new(
                self.root / "control/cancellations" / name,
                read_regular(self.root / "control/requests" / name),
            )
        put_json(self.root / "control/sessions" / (uuid.uuid4().hex + ".json"), self.session)
        self.started = True

    def cancel_requests(self):
        return {p.name for p in (self.root / "control" / "requests").glob("*.json")}

    def check_cancel(self):
        pending = self.cancel_requests() - self.cancel_ignored
        if pending:
            for name in sorted(pending):
                request = read_json(self.root / "control" / "requests" / name)
                same_or_new(self.root / "control" / "cancellations" / name, canonical(request))
            raise ControlStopped("cancelled: the active bounded call settled; new launches stopped")

    def _verify_completion(self, completion):
        for entry in completion["evidence"]:
            data = read_regular(self.root / entry["path"])
            if len(data) != entry["size"] or digest(data) != entry["sha256"]:
                raise ValueError("committed attempt evidence changed")
        for artifact in completion["artifacts"]:
            EvidenceStore(self.root).get(artifact)

    def _commit(self, launch, result, directory, *, recovered=False, missing=False):
        if not isinstance(result, dict) or result.get("status") not in (
            RETRYABLE | {"completed", "budget_exhausted"}
        ):
            raise ValueError("adapter return has no supported execution status")
        if result.get("id", launch["attempt"]) != launch["attempt"]:
            raise ValueError("adapter return belongs to a different attempt")
        log_name = result.get("inspect_log") or result.get("inspect", {}).get("log")
        log_paths = (
            [self.root / log_name] if log_name else sorted((directory / "inspect").glob("*.json"))
        )
        if log_paths:
            from inspect_ai.log import read_eval_log

            for log_path in log_paths:
                read_regular(log_path)
                log = read_eval_log(str(log_path))
                if result["status"] == "completed" and (
                    log.status != "success" or not log.samples or any(s.error for s in log.samples)
                ):
                    raise ValueError(
                        "completed adapter return disagrees with retained Inspect evidence"
                    )
        evidence = (
            [
                {**e, "path": (directory.relative_to(self.root) / e["path"]).as_posix()}
                for e in inventory(directory)
            ]
            if directory.exists()
            else []
        )
        artifacts = sorted(
            {
                v
                for k, v in result.items()
                if k
                in {
                    "output_id",
                    "input_id",
                    "transcript_id",
                    "native_logs_id",
                    "catalog_check_id",
                    "binding_id",
                }
                and v is not None
            }
        )
        for artifact in artifacts:
            EvidenceStore(self.root).get(artifact)
        completion = {
            "result": result,
            "evidence": evidence,
            "artifacts": artifacts,
            "recovered_return": recovered,
            "uncertain_marked_missing": missing,
            "resources": usage_record(self.root, result, launch["route"]),
        }
        put_json(
            self.root / "control" / "attempts" / launch["attempt"] / "completion.json", completion
        )
        self._settle(launch, completion)
        return dict(result)

    def _settle(self, launch, completion):
        if self.resources:
            with locked(self.resources / "resource.lock"):
                same_or_new(
                    self.resources / "outcomes" / (launch["reservation"] + ".json"),
                    canonical(
                        {
                            "run": self.config["id"],
                            "attempt": launch["attempt"],
                            **completion["resources"],
                        }
                    ),
                )

    def call(self, logical, role, route, seconds, binding, directory, invoke):
        self.begin()
        self.check_cancel()
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("attempt requires a positive bounded deadline")
        prior = sorted(
            (a for a in _attempts(self.root) if a["logical"] == logical), key=lambda a: a["number"]
        )
        signature = identity({"binding": binding, "role": role, "route": route, "seconds": seconds})
        if prior:
            launch = prior[-1]
            if signature != launch["binding"]:
                raise ValueError("attempt binding changed on recovery")
            completion = _completion(self.root, launch)
            previous_dir = self.root / launch["directory"]
            if completion:
                self._verify_completion(completion)
                self._settle(launch, completion)
            elif (previous_dir / "result.json").exists():
                # The adapter committed a return before the controller died. Logs remain
                # attached to the return; incomplete Inspect logs alone are not a return.
                result = read_json(previous_dir / "result.json")
                self._commit(launch, result, previous_dir, recovered=True)
                completion = _completion(self.root, launch)
            if (
                completion is None
                and self.resources
                and (self.resources / "outcomes" / (launch["reservation"] + ".json")).exists()
            ):
                raise ControlStopped(
                    "attempt settled in the shared ledger; restore its original local evidence: "
                    + logical
                )
            if logical in self.retry:
                if completion and completion["result"]["status"] not in RETRYABLE:
                    raise ValueError("recovered completed work cannot receive an extra chance")
                self.retry.remove(logical)
            elif completion:
                if logical in self.abandon:
                    raise ValueError(
                        "adapter return recovered; it cannot be marked uncertain/missing"
                    )
                return dict(completion["result"])
            elif logical in self.abandon:
                self.abandon.remove(logical)
                return self._commit(
                    launch,
                    {
                        "status": "harness_failure",
                        "completion": None,
                        "output_id": None,
                        "error": "uncertain launch explicitly retained as missing: " + self.reason,
                        "uncertain": True,
                        "id": launch["attempt"],
                        "usage": {
                            "provider_calls": None,
                            "internal_calls": None,
                            "tool_calls": None,
                            "duration_seconds": None,
                        },
                    },
                    previous_dir,
                    missing=True,
                )
            else:
                raise ControlStopped(
                    "uncertain launch "
                    + logical
                    + "; choose --retry or --mark-missing with --reason"
                )
        number = len(prior) + 1
        attempt = logical if number == 1 else f"{logical}-retry-{number - 1}"
        directory = (
            directory
            if number == 1
            else directory.with_name(directory.name + f"-retry-{number - 1}")
        )
        reservation = identity({"run": self.config["id"], "attempt": attempt})
        launch = {
            "logical": logical,
            "attempt": attempt,
            "number": number,
            "role": role,
            "route": route,
            "seconds": seconds,
            "binding": signature,
            "directory": directory.relative_to(self.root).as_posix(),
            "retry_of": prior[-1]["attempt"] if prior else None,
            "reason": self.reason if prior else None,
            "reservation": reservation,
        }
        if self.resources:
            fresh = reserve(self.resources, reservation, {"run": self.config["id"], **launch})
            if not fresh:
                put_json(self.root / "control" / "attempts" / attempt / "launch.json", launch)
                raise ControlStopped(
                    "reserved launch has no local return; restore original evidence or resolve "
                    + logical
                )
        # No provider call precedes this durable intent. A crash here remains uncertain.
        put_json(self.root / "control" / "attempts" / attempt / "launch.json", launch)
        result = invoke(directory, attempt)
        result = self._commit(launch, result, directory)
        if result["status"] in RETRYABLE and self.config["retry_limit"] >= number:
            raise ControlStopped(
                "infrastructure failure retained; resume or explicitly --retry " + logical
            )
        return result


def fixture_call(adapter, root, trial, context, limits, number, failures):
    controller = CURRENT.get()
    if controller is None:
        return adapter(root, trial, context, limits, number, failures)
    logical = f"{trial['id']}-a{number}"
    # Simulated fixture retries already have frozen per-trial identities/policy.
    return controller.call(
        logical,
        trial["role"],
        "simulated-api",
        limits.time_limit_seconds,
        {"context": context, "limits": limits.model_dump(), "failures": failures},
        root / "attempts" / logical,
        lambda directory, aid: adapter(root, trial, context, limits, number, failures),
    )


def managed(kind):
    def decorate(function):
        @wraps(function)
        def run(
            root,
            *args,
            resources=None,
            resume=False,
            retry=(),
            mark_missing=(),
            reason=None,
            infrastructure_retries=0,
            **kwargs,
        ):
            root = Path(root).resolve()
            cancellation_baseline = {p.name for p in (root / "control/requests").glob("*.json")}
            if kind == "fixture" and (retry or infrastructure_retries):
                raise ValueError("fixture retries use only the policy frozen in the study")
            if CURRENT.get() is not None:
                if CURRENT.get().root != root or CURRENT.get().kind != kind:
                    raise ValueError("nested execution requires the same managed run")
                return function(root, *args, **kwargs)
            if (root / "run-seal.json").exists():
                raise ValueError("execution already started and sealed; use offline reporting")
            if (root / "results.json").exists() and (retry or mark_missing):
                raise ValueError("result selection already committed; resume sealing or reporting")
            # Validate before introducing operational files. Legacy started runs need an
            # explicit migration; accepting arbitrary additions would hide changed inputs.
            freeze = check_freeze(root)
            if not (root / "control" / "run.json").exists():
                current = [
                    e
                    for e in inventory(root)
                    if e["path"] not in {"freeze-seal.json", "control.lock"}
                ]
                if current != freeze["files"]:
                    raise ValueError("prepared evidence changed or execution already started")
            with locked(root / "control.lock"):
                if (root / "run-seal.json").exists():
                    raise ValueError("execution already started and sealed; use offline reporting")
                controller = Controller(
                    root,
                    kind,
                    resources,
                    resume,
                    retry,
                    mark_missing,
                    reason,
                    infrastructure_retries,
                    cancellation_baseline,
                )
                token = CURRENT.set(controller)
                try:
                    shared_lock = (
                        locked(controller.resources / "runs" / (controller.config["id"] + ".lock"))
                        if controller.resources
                        else nullcontext()
                    )
                    with shared_lock:
                        return function(root, *args, **kwargs)
                except (ControlStopped, KeyboardInterrupt) as error:
                    controller.begin()
                    return control_report(
                        root, str(error) or "interrupted; active launch may be uncertain"
                    )
                finally:
                    CURRENT.reset(token)

        return run

    return decorate


def start_control():
    """Commit execution state after preflight and before materializing trial inputs."""
    if CURRENT.get() is not None:
        CURRENT.get().begin()


def native_call(adapter, root, attempt_id, prompt, files, *, role, **kwargs):
    controller = CURRENT.get()
    if controller is None:
        return adapter(root, attempt_id, prompt, files, **kwargs)
    binding = {
        "prompt": digest(prompt.encode()),
        "files": {n: digest(b) for n, b in files.items()},
        "config": digest(kwargs["config"]),
        "image": kwargs["image"],
        "executable": sorted(kwargs.get("executable", ())),
    }
    return controller.call(
        attempt_id,
        role,
        "native-codex-cli",
        kwargs["timeout"],
        binding,
        root / "attempts" / attempt_id,
        lambda directory, aid: adapter(root, aid, prompt, files, **kwargs),
    )


def role_call(adapter, directory, settings, messages, stage, *args, role, **kwargs):
    controller = CURRENT.get()
    if controller is None:
        return adapter(directory, settings, messages, stage, *args, **kwargs)
    return controller.call(
        stage,
        role,
        settings.adapter,
        settings.timeout_seconds,
        {
            "settings": settings.model_dump(mode="json"),
            # Inspect assigns fresh local message IDs when reconstructing inputs.
            # They do not change model-visible content or execution conditions.
            "messages": [m.model_dump(mode="json", exclude={"id"}) for m in messages],
            "schema": args[-1] if args and isinstance(args[-1], dict) else None,
        },
        directory,
        lambda target, aid: adapter(target, settings, messages, stage, *args, **kwargs),
    )


def cancel(root, reason):
    root = Path(root).resolve()
    if not (root / "control" / "run.json").exists() or (root / "run-seal.json").exists():
        raise ValueError("cancellation requires an unsealed managed run")
    path = root / "control" / "requests" / (uuid.uuid4().hex + ".json")
    put_json(path, {"reason": reason, "time": time.time(), "mode": "settle_active"})
    return path


def control_status(root):
    if (root / "run-seal.json").exists():
        from .evidence import verify_run

        verify_run(root)
    check_freeze(root)
    config = control_config(root)
    attempts = []
    for launch in _attempts(root):
        completion = _completion(root, launch)
        attempts.append(
            {
                **launch,
                "status": completion["result"]["status"] if completion else "uncertain",
                "resources": completion["resources"] if completion else None,
                "uncertain_execution": bool(completion and completion["result"].get("uncertain"))
                or completion is None,
            }
        )
    plan = read_json(root / "plan.json") if (root / "plan.json").exists() else None
    latest = {}
    for attempt in sorted(attempts, key=lambda a: a["number"]):
        latest[attempt["logical"]] = attempt
    for attempt in attempts:
        attempt["selected"] = latest[attempt["logical"]]["attempt"] == attempt["attempt"]
    trials = []
    for trial in (plan or {}).get("trials", []):
        attempt = latest.get(trial["id"])
        if config["kind"] == "fixture":
            candidates = [a for key, a in latest.items() if key.startswith(trial["id"] + "-a")]
            attempt = (
                max(candidates, key=lambda a: int(a["logical"].rsplit("-a", 1)[1]))
                if candidates
                else None
            )
        trials.append(
            {**trial, "execution_status": attempt["status"] if attempt else "not_launched"}
        )
    if (root / "results.json").exists():
        final = read_json(root / "results.json")
        for trial in trials:
            if trial["id"] in final.get("trials", {}):
                trial["execution_status"] = final["trials"][trial["id"]]["status"]
    if config["kind"] == "grading":
        grading = read_json(root / "grading.json")
        final_grades = (
            {r["trial"]["id"]: r for r in final.get("grades", [])}
            if (root / "results.json").exists()
            else {}
        )
        count = len(grading["request"]["calibration"])
        trials = []
        for work in grading["evidence"]["work"]:
            eligible = work["submitted_output"] is not None and work["status"] not in RETRYABLE | {
                "dependency_missing"
            }
            if eligible:
                count += 1
            attempt = latest.get(f"work-{count:04}") if eligible else None
            trials.append(
                {
                    "id": work["trial"]["id"],
                    "role": "grading",
                    "execution_status": final_grades.get(work["trial"]["id"], {}).get(
                        "status", attempt["status"] if attempt else "not_graded"
                    ),
                }
            )
    return {
        "schema_version": 1,
        "run": config,
        "sealed": (root / "run-seal.json").exists(),
        "trials": trials,
        "attempts": attempts,
        "planned": len(trials) if plan or config["kind"] == "grading" else None,
        "attempts_reserved": len(attempts),
        "scheduled_seconds": sum(a["seconds"] for a in attempts),
        "scope": "Operational evidence; execution completion is not task correctness. "
        "Unlaunched and uncertain work remains in the planned denominator.",
    }


def control_report(root, reason="operational snapshot"):
    report = root / "interpretations" / ("control-" + uuid.uuid4().hex)
    report.mkdir(parents=True, exist_ok=False)
    status = control_status(root)
    put_json(report / "status.json", {"reason": reason, **status})
    write_new(
        report / "report.md",
        (
            "# Execution control report\n\n"
            + reason
            + ".\n\n"
            + f"Planned trials: {status['planned']}. Reserved attempts (including retries): "
            + f"{status['attempts_reserved']}; "
            + f"scheduled seconds: {status['scheduled_seconds']}.\n\n"
            + status["scope"]
            + "\n\n"
            + "Cancellation settles the active bounded call and stops further launches. "
            + "Reservations include in-flight/uncertain work and are never refunded. "
            + "Native deadlines exclude setup/export; "
            + "hard token and spend caps are unavailable.\n\n"
            + "[All planned trials, attempt lineage and recorded usage](status.json)\n"
        ).encode(),
    )
    return report / "report.md"


def resource_status(root):
    with locked(root / "resource.lock"):
        config = resource_config(root)
        rows = []
        for path in sorted((root / "reservations").glob("*.json")):
            outcome = root / "outcomes" / path.name
            rows.append(
                {**read_json(path), "outcome": read_json(outcome) if outcome.exists() else None}
            )
        stages = {}
        for role in sorted({r["role"] for r in rows}):
            selected = [r for r in rows if r["role"] == role]
            durations = [(r["outcome"] or {}).get("duration_seconds") for r in selected]
            stages[role] = {
                "attempts": len(selected),
                "scheduled_seconds": sum(r["seconds"] for r in selected),
                "reported_seconds": sum(d for d in durations if d is not None),
                "duration_unavailable": sum(d is None for d in durations),
                "duration_scopes": sorted(
                    {(r["outcome"] or {}).get("duration_scope", "unavailable") for r in selected}
                ),
            }
        return {
            "schema_version": 1,
            "config": config,
            "by_role": stages,
            "attempts": rows,
            "remaining_attempts": config["limits"]["max_attempts"] - len(rows),
            "remaining_scheduled_seconds": config["limits"]["max_scheduled_seconds"]
            - sum(r["seconds"] for r in rows),
            "accounting": "Unique root reservations across roles/runs; native child usage is "
            "root-inclusive, never added again. Unknown usage and spend are not zero.",
        }
