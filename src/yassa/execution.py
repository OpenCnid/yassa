"""The only Inspect-specific execution boundary; one fresh sample per attempt."""

from pathlib import Path

from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.model import ChatMessageSystem, ChatMessageUser, GenerateConfig, get_model
from inspect_ai.solver import generate

from .evidence import EvidenceStore, write_new
from .records import canonical
from .simulation import MODEL_NAME, fixture_api  # noqa: F401 -- registers the provider
from .study import Limits


def execute_attempt(
    root: Path,
    trial: dict,
    context: dict,
    limits: Limits,
    attempt_number: int,
    injected_failures: int,
) -> dict:
    attempt_id = f"{trial['id']}-a{attempt_number}"
    attempt_directory = root / "attempts" / attempt_id
    store = EvidenceStore(root)
    context_id = store.put_json(context, "binding.json")
    launch = {
        "schema_version": 1,
        "id": attempt_id,
        "trial_id": trial["id"],
        "number": attempt_number,
        "binding_id": context_id,
        "retry_of": f"{trial['id']}-a{attempt_number - 1}" if attempt_number > 1 else None,
        "status": "launched",
        "injected_infrastructure_failure": attempt_number <= injected_failures,
    }
    write_new(attempt_directory / "launch.json", canonical(launch))
    config = GenerateConfig(
        max_tokens=limits.max_output_tokens,
        max_retries=0,
        timeout=limits.time_limit_seconds,
        max_connections=1,
        cache=False,
        temperature=0,
    )
    model = get_model(
        f"yassa_fixture/{MODEL_NAME}",
        config=config,
        memoize=False,
        fail=attempt_number <= injected_failures,
    )
    api = model.api
    messages = [
        ChatMessageSystem(content=context["messages"][0]["content"]),
        ChatMessageUser(content=context["messages"][1]["content"]),
    ]
    task = Task(
        name=attempt_id,
        version="1",
        dataset=[Sample(id=trial["id"], input=messages)],
        solver=generate(tool_calls="none"),
        scorer=None,
        model=model,
        config=config,
    )
    logs = eval(
        task,
        model=model,
        log_dir=str(attempt_directory / "inspect"),
        log_format="eval",
        log_model_api=True,
        log_samples=True,
        log_buffer=1,
        log_shared=False,
        log_realtime=False,
        display="none",
        notification=False,
        ctl_server=False,
        score=False,
        epochs=1,
        retry_on_error=0,
        fail_on_error=False,
        time_limit=limits.time_limit_seconds,
        max_samples=1,
        max_tasks=1,
        message_limit=3,
        **config.model_dump(exclude_none=True),
    )
    if len(logs) != 1:
        raise RuntimeError("Inspect did not return exactly one attempt log; run remains unsealed")
    log = logs[0]
    sample = log.samples[0] if log.samples else None
    error = sample.error if sample and sample.error else log.error
    output = sample.output.completion.encode("utf-8") if sample else b""
    evidence_id = store.put({"response.txt": output})
    error_text = error.message if error else None
    if error:
        status = (
            "infrastructure_failure"
            if "explicit simulated infrastructure failure" in error_text
            else "harness_failure"
        )
    elif log.status != "success" or sample is None:
        status = "harness_failure"
        error_text = f"Inspect status {log.status}; sample present: {sample is not None}"
    elif sample.limit or any(
        choice.stop_reason == "max_tokens" for choice in sample.output.choices
    ):
        status = "budget_exhausted"
    else:
        status = "completed"
    record = {
        **launch,
        "status": status,
        "error": error_text,
        "output_id": evidence_id,
        "inspect": {
            "task_id": log.eval.task_id,
            "sample_id": sample.id if sample else None,
            "sample_uuid": sample.uuid if sample else None,
            "epoch": sample.epoch if sample else None,
            "log": Path(log.location).relative_to(root).as_posix(),
            "status": log.status,
        },
        "usage": {
            "provider_calls": api.calls,
            "internal_calls": 0,
            "tool_calls": 0,
            "model_tokens": None,
            "cost_usd": None,
            "simulated_output_units": len(output),
            "duration_seconds": sample.total_time if sample else None,
            "accounting": "simulated output byte units; no model tokens or price",
        },
        "limits": limits.model_dump(),
        "limit": sample.limit.model_dump(mode="json") if sample and sample.limit else None,
    }
    write_new(attempt_directory / "result.json", canonical(record))
    return record
