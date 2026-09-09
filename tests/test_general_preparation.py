"""Product acceptance with simulated Inspect responses; no live model evidence.

Only task descriptions, source inputs and provider responses live in this driver.
Preparation, validation, study compilation, freeze, scoring and reporting are product code.
"""

import copy
import json
import shutil
import sys

import pytest
from inspect_ai.model import GenerateConfig, ModelAPI, ModelOutput, modelapi

from yassa.app import main
from yassa.evidence import EvidenceStore, verify_run, write_new
from yassa.general_contracts import GeneralRequest, StudyProposal
from yassa.general_preparation import verify_proposal
from yassa.guided_preparation import prepare_draft
from yassa.json_rubric import JsonRubric, check_rubric, evaluate
from yassa.native_contracts import NativeStudyV2, builder_files, check_task, prepare_files
from yassa.preparation_evidence import load_preparation
from yassa.records import canonical, digest, parse_json

IMAGE = "sha256:" + "a" * 64


def lit(value):
    return {"literal": value}


def var(name):
    return {"var": name}


def op(name, *args, **extra):
    return {"op": name, "args": list(args), **extra}


def get(value, key):
    return op("get", value, lit(key))


def istype(value, name):
    return op("eq", op("type", value), lit(name))


def criterion(name, expression):
    return {"id": name, "description": name.replace("-", " "), "expression": expression}


def task_proposal(kind="selection"):
    data, output = get(var("input"), "input/data.json"), var("output")
    item = var("item")
    if kind == "selection":
        items = get(data, "items")
        ids = op("map", items, get(item, "id"), **{"as": "item"})
        selected = op(
            "map",
            op(
                "filter",
                items,
                op("ge", get(item, "score"), get(data, "minimum")),
                **{"as": "item"},
            ),
            get(var("row"), "id"),
            **{"as": "row"},
        )
        domain = op(
            "and",
            istype(items, "array"),
            istype(get(data, "minimum"), "integer"),
            op("unique", ids),
            op(
                "all",
                items,
                op("and", istype(get(item, "id"), "string"), istype(get(item, "score"), "integer")),
                **{"as": "item"},
            ),
        )
        assertions = [
            criterion(
                "schema",
                op(
                    "and",
                    istype(output, "array"),
                    op("all", output, istype(item, "string"), **{"as": "item"}),
                ),
            ),
            criterion("unique", op("unique", output)),
            criterion("selection", op("set-eq", output, selected)),
        ]
        requirements = (
            "Read input/data.json. Return a JSON array containing exactly once each item id "
            "whose integer score is at least minimum. IDs are unique strings; "
            "order is irrelevant. No prose."
        )
    else:
        jobs, slots = get(data, "jobs"), get(data, "slots")
        domain = op(
            "and",
            istype(jobs, "array"),
            istype(slots, "array"),
            op("unique", jobs),
            op("unique", slots),
            op("ge", op("len", slots), op("len", jobs)),
            op("ge", op("len", jobs), lit(1)),
            op("all", jobs, istype(item, "string"), **{"as": "item"}),
            op("all", slots, istype(var("slot"), "string"), **{"as": "slot"}),
        )
        outjobs = op("map", output, get(item, "job"), **{"as": "item"})
        outslots = op("map", output, get(item, "slot"), **{"as": "item"})
        assertions = [
            criterion(
                "schema",
                op(
                    "and",
                    istype(output, "array"),
                    op(
                        "all",
                        output,
                        op(
                            "and",
                            istype(item, "object"),
                            op("set-eq", op("keys", item), lit(["job", "slot"])),
                            istype(get(item, "job"), "string"),
                            istype(get(item, "slot"), "string"),
                        ),
                        **{"as": "item"},
                    ),
                ),
            ),
            criterion("coverage", op("and", op("set-eq", outjobs, jobs), op("unique", outjobs))),
            criterion(
                "allowed", op("all", outslots, op("contains", slots, var("slot")), **{"as": "slot"})
            ),
            criterion("exclusive", op("unique", outslots)),
        ]
        requirements = (
            "Read input/data.json. Assign every job exactly once to any listed slot, "
            "using each slot at most once. Return a JSON array of objects with exactly "
            "the string keys job and slot. Any feasible assignment and array order is valid."
        )
    return {
        "questions": [],
        "intended_use": "Describe package-assisted performance on constructed work.",
        "facts": [requirements],
        "inferences": [],
        "assumptions": ["Invented inputs; no real-work coverage claim."],
        "requirements": requirements,
        "input_paths": ["input/data.json"],
        "case_plan": "Exercise several independently labeled cases in disjoint development "
        "and evaluation groups.",
        "rubric": {
            "version": "json-predicates-v1",
            "input_assertions": [criterion("domain", domain)],
            "assertions": assertions,
            "limitations": "Only the declared JSON constraints; no real-world "
            "representativeness or optimality claim.",
        },
    }


def case_batch(payload):
    kind = "selection" if "minimum" in payload["task"]["requirements"] else "assignment"
    route, split = payload["route"], payload["split"]
    prefix = route + "-" + split
    cases, probes, origins = [], [], {}
    source_ids = [s["id"] for s in payload["sources"] if s["split"] == split]
    for i in range(payload["count"]):
        name = prefix + "-" + str(i)
        if route == "user-supplied":
            data = json.loads(
                next(s["content"] for s in payload["sources"] if s["split"] == split)
            )[i]
        elif kind == "selection":
            data = {
                "items": [
                    {"id": name + "-a", "score": 2},
                    {"id": name + "-b", "score": 8},
                    {"id": name + "-c", "score": 7},
                ],
                "minimum": 7,
            }
        else:
            data = {"jobs": [name + "-a", name + "-b"], "slots": ["morning", "afternoon"]}
        if kind == "selection":
            answer = [x["id"] for x in data["items"] if x["score"] >= data["minimum"]]
            alternatives = [
                (list(reversed(answer)), True, []),
                (answer + answer[:1], False, ["unique"]),
                (answer[1:], False, ["selection"]),
                ([True, True], False, ["schema", "unique", "selection"]),
            ]
        else:
            answer = [
                {"job": job, "slot": slot}
                for job, slot in zip(data["jobs"], data["slots"], strict=True)
            ]
            swapped = [
                {"job": job, "slot": slot}
                for job, slot in zip(data["jobs"], reversed(data["slots"]), strict=True)
            ]
            alternatives = [
                (swapped, True, []),
                (answer[:1], False, ["coverage"]),
                ([{**answer[0], "extra": 1}, answer[1]], False, ["schema"]),
                ([{**answer[0], "slot": "unlisted"}, answer[1]], False, ["allowed"]),
                ([answer[0], {**answer[1], "slot": answer[0]["slot"]}], False, ["exclusive"]),
            ]
        cases.append(
            {
                "id": name,
                "group": prefix,
                "files": {"input/data.json": canonical(data).decode()},
                "expected": answer,
            }
        )
        origins[name] = source_ids
        probes += [
            {
                "case_id": name,
                "output": result,
                "accept": accept,
                "fails": fails,
                "rationale": "Valid alternative" if accept else "Violates " + ", ".join(fails),
            }
            for result, accept, fails in alternatives
        ]
    return {
        "cases": cases,
        "origins": origins,
        "probes": probes,
        "selection": "All requested source cases or generated scenarios retained.",
    }


class PreparationFixtureAPI(ModelAPI):
    calls = []
    issue = False
    malformed = False

    def __init__(self, model_name, base_url=None, api_key=None, config=None):
        super().__init__(model_name, config=config or GenerateConfig())

    async def generate(self, input, tools, tool_choice, config):
        assert len(input) == 2 and not tools and config.max_retries == 0
        payload = parse_json(input[1].text)
        self.calls.append(payload)
        if "specification_sources" in payload:
            if "unclear" in payload["request"] and not payload["answers"]:
                result = {
                    "questions": [
                        {
                            "field": "success",
                            "prompt": "Which assignment constraints define success?",
                        }
                    ]
                }
            else:
                result = task_proposal(
                    "assignment" if "assign" in payload["request"] else "selection"
                )
        elif "split" in payload:
            result = case_batch(payload)
        else:
            result = {
                "issues": ["Resolve the ambiguous capacity rule."] if self.issue else [],
                "assessment": "Simulated review response for wiring tests; not semantic "
                "model validation.",
            }
        return ModelOutput.from_content(
            self.model_name, "{" if self.malformed else canonical(result).decode()
        )


@modelapi(name="yassa_preparation_test")
def fixture_api():
    return PreparationFixtureAPI


@pytest.fixture(autouse=True)
def clear_provider():
    PreparationFixtureAPI.calls = []
    PreparationFixtureAPI.issue = False
    PreparationFixtureAPI.malformed = False


def request(kind="selection"):
    return {
        "schema_version": 2,
        "id": "general-example",
        "request": task_proposal(kind)["requirements"],
        "development_cases": 1,
        "evaluation_cases": 2,
        "preparation": {
            "model": "yassa_preparation_test/prepare",
            "reviewer_model": "yassa_preparation_test/review",
            "max_calls": 6,
            "max_output_tokens": 12000,
            "timeout_seconds": 30,
        },
        "execution": {
            "model": "test-model",
            "reasoning_effort": "low",
            "arms": [{"id": "common", "builds": 1}],
            "control_rationale": {"common": "Describe a single builder; no ranking."},
            "consumer_repeats": 1,
            "schedule_seed": 1,
            "admission": {
                "max_attempts": 10,
                "max_scheduled_seconds": 600,
                "build_timeout_seconds": 60,
                "consumer_timeout_seconds": 30,
            },
        },
    }


def draft(tmp_path, value, name="round-0", previous=None):
    path = tmp_path / (name + ".json")
    path.write_bytes(canonical(value))
    root = prepare_draft(path, tmp_path / name, previous).parent
    return root, parse_json((root / "draft.json").read_bytes())


def supplied(tmp_path, value):
    value["routes"] = ["user-supplied", "yassa-prepared"]
    value["documents"] = []
    originals = {}
    for split, count in [("development", 1), ("evaluation", 2)]:
        rows = [
            {"jobs": [f"source-{split}-{i}-a", f"source-{split}-{i}-b"], "slots": ["one", "two"]}
            for i in range(count)
        ]
        body = json.dumps(rows, indent=3).replace("\n", "\r\n").encode()
        path = tmp_path / (split + ".json")
        path.write_bytes(body)
        originals[split] = body
        value["documents"].append(
            {
                "id": split,
                "file": {"path": str(path), "sha256": digest(body)},
                "split": split,
                "description": "Supplied job requests",
                "origin": "local invented source",
                "version": "1",
                "access": "user supplied",
                "license": "test data",
                "authorship": "test driver",
                "synthetic": True,
            }
        )
    return originals


@pytest.mark.parametrize("kind", ["selection", "assignment"])
def test_guided_general_complete_request_compiles_and_expert_matches(tmp_path, kind):
    value = request(kind)
    root, state = draft(tmp_path, value)
    assert state["status"] == "ready_for_freeze", (root / "validation.json").read_text()
    assert len(PreparationFixtureAPI.calls) == 4
    study = NativeStudyV2.model_validate(parse_json((root / "study.json").read_bytes()))
    material = prepare_files(study.task, study.conditions[0], root)[0]
    assert study.task.checker == "json-predicates-v1"
    assert "independently" not in (root / "validation.json").read_text()  # No oracle claim.
    witness = material.evaluation[0]
    alternative = next(
        p["output"]
        for p in parse_json((root / "proposal.json").read_bytes())["conditions"][0]["evaluation"][
            "probes"
        ]
        if p["accept"]
    )
    assert alternative != witness.expected
    assert check_task(study.task, canonical(alternative), witness)["value"] == 1
    assert load_preparation(study, root)
    expert = copy.deepcopy(value)
    proposal_bytes = (root / "proposal.json").read_bytes()
    expert["expert_proposal"] = {
        "path": str(root / "proposal.json"),
        "sha256": digest(proposal_bytes),
    }
    ready, state = draft(tmp_path, expert, "expert")
    assert state["status"] == "ready_for_freeze"
    other = NativeStudyV2.model_validate(parse_json((ready / "study.json").read_bytes()))
    assert other.task == study.task
    assert other.arms == study.arms
    assert other.model_dump(exclude={"preparation"}) == study.model_dump(exclude={"preparation"})
    assert len(PreparationFixtureAPI.calls) == 5  # Expert imports reuse the review operation.


def test_questions_revisions_source_preservation_and_split_contexts(tmp_path):
    value = request("assignment")
    originals = supplied(tmp_path, value)
    value["request"] = "unclear assignment requirements"
    root, state = draft(tmp_path, value)
    assert state["status"] == "needs_input" and len(state["questions"]) == 1
    assert len(PreparationFixtureAPI.calls) == 1
    seal = (root / "draft-seal.json").read_bytes()
    relocated = tmp_path / "relocated"
    shutil.copytree(root, relocated)
    for split in originals:
        (tmp_path / (split + ".json")).unlink()
    ready, state = draft(
        tmp_path, {"answers": [task_proposal("assignment")["requirements"]]}, "round-1", relocated
    )
    assert state["status"] == "ready_for_freeze", (ready / "validation.json").read_text()
    assert (root / "draft-seal.json").read_bytes() == seal
    for split, raw in originals.items():
        assert (ready / f"history/000-source-{split}.txt").read_bytes() == raw
    assert all(
        not p["specification_sources"]
        for p in PreparationFixtureAPI.calls
        if "specification_sources" in p
    )
    for p in PreparationFixtureAPI.calls:
        if "split" in p:
            assert all(s["split"] == p["split"] for s in p["sources"])
    study = NativeStudyV2.model_validate(parse_json((ready / "study.json").read_bytes()))
    for condition in study.conditions:
        material = prepare_files(study.task, condition, ready)[0]
        rendered = canonical(
            {k: v.decode() for k, v in builder_files(study.task, material).items()}
        )
        assert all(case.id.encode() not in rendered for case in material.evaluation)


@pytest.mark.parametrize(
    "field,value",
    [
        ("evidence", "broader-comparison"),
        ("activation", "automatic"),
        ("comparison", "direct"),
        ("clarification", "measured"),
        ("execution", None),
    ],
)
def test_unsupported_or_missing_settings_do_not_make_calls(tmp_path, field, value):
    data = request()
    data[field] = value
    root, state = draft(tmp_path, data)
    assert state["status"] == "needs_input" and 1 <= len(state["questions"]) <= 2
    assert not (root / "study.json").exists() and not PreparationFixtureAPI.calls


@pytest.mark.parametrize("failure", ["review", "malformed", "budget"])
def test_failures_are_preserved_without_runnable_export(tmp_path, failure):
    value = request()
    PreparationFixtureAPI.issue = failure == "review"
    PreparationFixtureAPI.malformed = failure == "malformed"
    if failure == "budget":
        value["preparation"]["max_calls"] = 1
    root, state = draft(tmp_path, value)
    assert state["status"] == "needs_input" and not (root / "study.json").exists()
    assert (root / "draft-seal.json").exists()
    if failure != "budget":
        assert list(root.rglob("response.json"))
    if failure == "malformed":
        assert list(root.rglob("failure.json"))


def test_general_cli_preparation_to_report_both_routes(tmp_path, monkeypatch, capsys):
    value = request("assignment")
    originals = supplied(tmp_path, value)
    source = tmp_path / "request.json"
    source.write_bytes(canonical(value))

    def cli(*args):
        monkeypatch.setattr(sys, "argv", ["yassa", *map(str, args)])
        assert main() == 0, capsys.readouterr().err

    root = tmp_path / "reviewed"
    cli("study-draft", source, "--draft-dir", root)
    assert (root / "study.json").is_file(), (root / "validation.json").read_text()
    monkeypatch.setattr("yassa.native_runner.subprocess.run", lambda *a, **k: None)
    run = tmp_path / "run"
    cli("native-prepare", root / "study.json", "--run-dir", run, "--image", IMAGE)
    study = NativeStudyV2.model_validate(parse_json((root / "study.json").read_bytes()))
    plan = parse_json((run / "plan.json").read_bytes())
    trials = {t["id"]: t for t in plan["trials"]}
    seen = []

    def adapter(root, attempt_id, prompt, files, **kwargs):
        seen.append(attempt_id)
        trial = trials[attempt_id]
        assert not any("rubric" in name or "history" in name for name in files)
        if trial["role"] == "build":
            package = (
                "---\nname: general-example\ndescription: Assign jobs.\n---\n"
                "Use the task constraints."
            )
            output = {study.task.package_path + "/SKILL.md": package.encode()}
        else:
            data = parse_json(files["input/data.json"])
            # Driver solves from subject-visible inputs, not held-out reference answers.
            answer = [
                {"job": job, "slot": slot}
                for job, slot in zip(data["jobs"], reversed(data["slots"]), strict=True)
            ]
            output = {study.task.result_path: canonical(answer)}
        result = {
            "status": "completed",
            "output_id": EvidenceStore(root).put(output),
            "rejected_paths": [],
            "duration_seconds": 1,
        }
        write_new(root / "attempts" / attempt_id / "result.json", canonical(result))
        return result

    monkeypatch.setattr("yassa.native_runner.execute_native", adapter)
    cli("native-execute", run, "--auth-file", tmp_path / "unused")
    cli("verify", run)
    cli("native-rescore", run, "--label", "repeat")
    original = (run / "interpretations/original/scores.json").read_bytes()
    assert original == (run / "interpretations/repeat/scores.json").read_bytes()
    scores = parse_json(original)["scores"]
    assert len(scores) == 4 and all(s["value"] == 1 for s in scores)
    assert len(seen) == 6
    report = (run / "interpretations/original/report.md").read_text()
    assert "preparation" in report.lower() and "modeled constraints" in report
    moved = tmp_path / "portable-run"
    shutil.copytree(run, moved)
    assert verify_run(moved) == verify_run(run)
    cli("native-rescore", moved, "--label", "relocated")
    assert original == (moved / "interpretations/relocated/scores.json").read_bytes()
    frozen = parse_json((run / "study.json").read_bytes())
    evidence = EvidenceStore(run).get(frozen["preparation_id"])
    assert all(raw in evidence.values() for raw in originals.values())


def test_rubric_wrong_outputs_and_language_boundaries():
    rubric = JsonRubric.model_validate(task_proposal()["rubric"])
    inputs = {
        "input/data.json": {
            "items": [{"id": "a", "score": 7}, {"id": "b", "score": 8}],
            "minimum": 7,
        }
    }
    assert check_rubric(rubric, b' [ "b", "a" ] ', inputs)["value"] == 1
    for output in [
        b"[]",
        b'["a","a","b"]',
        b'[true,"b"]',
        b'{"a":1,"a":2}',
        b"NaN",
        b"1e999",
        b"```[]```",
    ]:
        assert check_rubric(rubric, output, inputs)["value"] == 0
    invalid = copy.deepcopy(inputs)
    invalid["input/data.json"]["items"][0]["score"] = True
    with pytest.raises(ValueError, match="invalid case input"):
        check_rubric(rubric, b"[]", invalid)
    for expr in [
        {"op": "exec", "args": [lit("anything")]},
        var("unknown"),
        {"op": "eq", "args": [lit(True)]},
        op("all", lit([]), var("input"), **{"as": "input"}),
    ]:
        data = task_proposal()["rubric"]
        data["assertions"][0]["expression"] = expr
        with pytest.raises(ValueError):
            JsonRubric.model_validate(data)
    with pytest.raises(ValueError, match="operation budget"):
        evaluate(op("sum", lit([1, 2])), {}, [0])


def test_numeric_text_and_conditional_contracts():
    assert evaluate(op("add", lit(7), op("mul", lit(2), lit(-3))), {}) == 1
    assert evaluate(op("sum", lit([2, -5, 8])), {}) == 5
    assert evaluate(op("sub", lit(5), lit(8)), {}) == -3
    assert evaluate(op("lower", op("strip", lit("  AbC  "))), {}) == "abc"
    assert evaluate(op("contains", lit([1]), lit(True)), {}) is False
    assert evaluate(op("contains", lit("abc"), lit("b")), {}) is True
    assert evaluate(op("if", lit(False), get(lit({}), "absent"), lit(4)), {}) == 4
    for expr in [
        op("add", lit(True), lit(1)),
        op("sum", lit([False])),
        op("mul", lit(2**255), lit(2)),
        op("get", lit([1]), lit(-1)),
        op("and", lit(1)),
        op("contains", lit(3), lit(3)),
    ]:
        with pytest.raises(ValueError):
            evaluate(expr, {})
    with pytest.raises(ValueError, match="byte budget"):
        evaluate(op("eq", lit("abc"), lit("abc")), {}, [100, 1])


def test_expert_attestation_no_calls_and_preflight_admission(tmp_path, monkeypatch, capsys):
    value = request("assignment")
    task = task_proposal("assignment")
    proposal = {
        "task": task,
        "conditions": [
            {
                "route": "yassa-prepared",
                "authorship": "test expert",
                **{
                    split: case_batch(
                        {
                            "task": task,
                            "route": "yassa-prepared",
                            "split": split,
                            "sources": [],
                            "count": value[split + "_cases"],
                        }
                    )
                    for split in ("development", "evaluation")
                },
            }
        ],
    }
    body = canonical(proposal)
    path = tmp_path / "expert-proposal.json"
    path.write_bytes(body)
    review = tmp_path / "expert-review.json"
    review.write_bytes(
        canonical(
            {
                "proposal_sha256": digest(body),
                "reviewer": "test expert",
                "method": "explicit supplied verification fixture",
                "assessment": "Tests record the attestation, not a model claim.",
                "issues": [],
            }
        )
    )
    value.update(
        preparation=None,
        expert_proposal={"path": str(path), "sha256": digest(body)},
        expert_review={"path": str(review), "sha256": digest(review.read_bytes())},
    )
    root, state = draft(tmp_path, value)
    assert state["status"] == "ready_for_freeze" and not PreparationFixtureAPI.calls
    bad = copy.deepcopy(value)
    bad["execution"]["admission"]["max_attempts"] = 1
    _, state = draft(tmp_path, bad, "over-budget")
    assert state["questions"][0]["field"] == "execution.admission"
    with pytest.raises(ValueError, match="source hash|evidence changed"):
        (root / "history/000-expert_review.json").write_bytes(b"changed")
        study = NativeStudyV2.model_validate(parse_json((root / "study.json").read_bytes()))
        load_preparation(study, root)
    monkeypatch.setattr(sys, "argv", ["yassa", "study-schema", "request"])
    assert main() == 0
    assert "documents" in parse_json(capsys.readouterr().out)["properties"]


def test_invalid_general_source_shapes_are_cli_errors(tmp_path, monkeypatch, capsys):
    path = tmp_path / "bad.json"
    path.write_bytes(canonical({"schema_version": 2, "request": "work", "documents": [{}]}))
    monkeypatch.setattr(
        sys, "argv", ["yassa", "study-draft", str(path), "--draft-dir", str(tmp_path / "out")]
    )
    assert main() == 2
    assert "yassa:" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_expert_tampered_calibration_reference_and_lineage_rejected(tmp_path):
    value = request("assignment")
    supplied(tmp_path, value)
    root, _ = draft(tmp_path, value)
    proposal = parse_json((root / "proposal.json").read_bytes())
    for mutation in ["reference", "probe", "lineage", "split", "count"]:
        changed = copy.deepcopy(proposal)
        batch = changed["conditions"][0]["development"]
        if mutation == "reference":
            batch["cases"][0]["expected"] = []
        elif mutation == "probe":
            batch["probes"][0]["accept"] = False
        elif mutation == "lineage":
            batch["origins"][batch["cases"][0]["id"]] = ["evaluation"]
        elif mutation == "split":
            changed["conditions"][0]["evaluation"]["cases"][0]["group"] = batch["cases"][0]["group"]
        else:
            batch["cases"] *= 2
        with pytest.raises(ValueError):
            verify_proposal(
                GeneralRequest.model_validate(value), StudyProposal.model_validate(changed)
            )
