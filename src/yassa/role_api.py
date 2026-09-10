"""Explicit first-party API identities and a closed, recorded Inspect message adapter."""

import os
import re
import time
from typing import Annotated, Literal

from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.model import get_model
from inspect_ai.solver import generate
from pydantic import Field, StrictInt, model_validator

from .evidence import write_new
from .records import canonical
from .study import Record

ENDPOINTS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "google": "https://generativelanguage.googleapis.com",
}


def api_identity(model):
    """Reject proxies/unknown aliases rather than trusting a caller's family label."""
    for provider, family, prefix in (
        ("openai", "gpt", "gpt-"),
        ("anthropic", "claude", "claude-"),
        ("google", "gemini", "gemini-"),
    ):
        if model.startswith(provider + "/" + prefix) and re.fullmatch(
            r"[a-z0-9]+/[a-zA-Z0-9_.-]+", model
        ):
            return {"provider": provider, "family": family, "model": model}
    raise ValueError(
        "use an explicit first-party openai/gpt-, anthropic/claude- or google/gemini- model"
    )


class ApiRole(Record):
    adapter: Literal["inspect-api"]
    model: str
    max_output_tokens: Annotated[StrictInt, Field(ge=100, le=32000)]
    timeout_seconds: Annotated[StrictInt, Field(ge=1, le=300)]

    @model_validator(mode="after")
    def identity(self):
        api_identity(self.model)
        return self


def call_api(directory, role, messages, stage):
    """No tools, shared state, retries or model caches; preserve every response and error."""
    directory.mkdir(parents=True, exist_ok=False)
    request = {
        "stage": stage,
        "role": role.model_dump(mode="json"),
        "identity": api_identity(role.model),
        "messages": [m.model_dump(mode="json") for m in messages],
    }
    write_new(directory / "request.json", canonical(request))
    started = time.monotonic()
    try:
        provider = request["identity"]["provider"]
        if (
            provider == "google"
            and os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
        ):
            raise ValueError("this role requires the first-party Gemini API, not a Vertex override")
        args = {"responses_store": False} if provider == "openai" else {}
        logs = eval(
            Task(name="yassa-role", dataset=[Sample(id=stage, input=messages)], solver=generate()),
            model=get_model(role.model, base_url=ENDPOINTS[provider], memoize=False, **args),
            log_dir=str(directory / "inspect"),
            log_format="json",
            log_model_api=True,
            score=False,
            retry_on_error=0,
            max_retries=0,
            epochs=1,
            max_samples=1,
            max_tasks=1,
            max_connections=1,
            max_tokens=role.max_output_tokens,
            timeout=role.timeout_seconds,
            time_limit=role.timeout_seconds,
            cache=False,
            ctl_server=False,
            display="none",
            notification=False,
            log_shared=False,
            log_realtime=False,
        )
        if len(logs) != 1 or not logs[0].samples or len(logs[0].samples) != 1:
            raise ValueError("API role produced no unique Inspect sample")
        sample = logs[0].samples[0]
        write_new(directory / "response.json", canonical(sample.output.model_dump(mode="json")))
        write_new(directory / "completion.txt", sample.output.completion.encode())
        stopped = bool(sample.output.choices) and all(
            c.stop_reason == "stop" for c in sample.output.choices
        )
        status = (
            "completed"
            if logs[0].status == "success" and not sample.error and stopped
            else "budget_exhausted"
            if not sample.error and sample.output.choices
            else "provider_failure"
        )
        record = {
            "status": status,
            "identity": request["identity"],
            "reported_model": sample.output.model,
            "completion": sample.output.completion,
            "usage": sample.output.usage.model_dump(mode="json") if sample.output.usage else None,
            "error": sample.error.message if sample.error else None,
        }
    except Exception as error:
        record = {
            "status": "provider_failure",
            "identity": request["identity"],
            "completion": None,
            "usage": None,
            "error": str(error),
        }
    record["duration_seconds"] = time.monotonic() - started
    record["endpoint"] = ENDPOINTS[request["identity"]["provider"]]
    write_new(directory / "result.json", canonical(record))
    return record
