"""Deterministic test double, not an LLM or a measurement of skill-builder quality.

The provider only receives Inspect messages. It does not read paths, reference
answers, study objects, or scorer code. No generated code is executed.
"""

import json

from inspect_ai.model import GenerateConfig, ModelAPI, ModelCall, ModelOutput, modelapi

MODEL_NAME = "yassa-fixture-v1"


def treatment_files(behavior: str) -> dict[str, bytes]:
    return {
        "fixture-treatment.json": (
            json.dumps({"behavior": behavior}, sort_keys=True) + "\n"
        ).encode()
    }


class FixtureAPI(ModelAPI):
    def __init__(
        self, model_name=MODEL_NAME, base_url=None, api_key=None, config=None, fail: bool = False
    ):
        if base_url or api_key or model_name != MODEL_NAME:
            raise ValueError("the fixture provider accepts no credentials or endpoint")
        super().__init__(model_name, config=config or GenerateConfig())
        self.fail = fail
        self.calls = 0

    async def generate(self, input, tools, tool_choice, config: GenerateConfig):
        self.calls += 1
        if tools or len(input) != 2 or input[0].role != "system" or input[1].role != "user":
            raise ValueError("fixture API only permits a fresh two-message request with no tools")
        if self.fail:
            raise ConnectionError("explicit simulated infrastructure failure")
        payload = json.loads(input[-1].text)
        common = json.loads(payload["common"])
        treatment = payload["treatment"]
        if common["stage"] == "build":
            behavior = json.loads(treatment["fixture-treatment.json"])["behavior"]
            if behavior == "invalid":
                result = {"files": {"notes.txt": "No submitted skill in this failure fixture."}}
            elif behavior == "refusal":
                result = {"refusal": "Explicit fixture refusal"}
            else:
                result = {
                    "files": {
                        "SKILL.md": "# Synthetic account totals\n\nFollow the task contract. "
                        "The fixture policy is in policy.json.\n",
                        "policy.json": json.dumps(
                            {"include_negative": behavior != "positive-only"}
                        ),
                    }
                }
        else:
            # Direct treatment and generated-package consumption are different inputs.
            if "fixture-treatment.json" in treatment:
                behavior = json.loads(treatment["fixture-treatment.json"])["behavior"]
                include_negative = behavior != "positive-only"
            else:
                behavior = "complete"
                include_negative = json.loads(treatment["policy.json"])["include_negative"]
            if behavior in {"invalid", "refusal"}:
                result = {"refusal": "Explicit fixture task failure"}
            else:
                totals = {}
                for row in common["rows"]:
                    if not include_negative and row["cents"] < 0:
                        continue
                    name = row["account"].strip().lower()
                    if name not in totals:
                        totals[name] = {"account": name, "net_cents": 0, "count": 0}
                    totals[name]["net_cents"] += row["cents"]
                    totals[name]["count"] += 1
                result = {"totals": list(totals.values())}
        completion = json.dumps(result, ensure_ascii=False)
        # The simulated provider defines one UTF-8 byte as one output token.
        # These are budget units, not real model token usage.
        encoded = completion.encode("utf-8")
        truncated = len(encoded) > config.max_tokens
        if truncated:
            completion = encoded[: config.max_tokens].decode("utf-8", errors="ignore")
        output = ModelOutput.from_content(
            MODEL_NAME, completion, stop_reason="max_tokens" if truncated else "stop"
        )
        return output, ModelCall.create(
            request={
                "messages": [message.model_dump(mode="json") for message in input],
                "tools": [],
                "simulation": True,
            },
            response={"completion": completion, "simulated_output_units": len(completion.encode())},
        )


@modelapi(name="yassa_fixture")
def fixture_api():
    return FixtureAPI
