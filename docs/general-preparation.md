# General preparation through a runnable study

`study-draft` accepts a version 2 preparation request describing work in ordinary
language. It uses explicitly configured Inspect models to prepare a task, rubric,
development examples and held-out cases, then independently review the proposal.
Version 1 requests retain the existing deterministic recipe behavior described
in [guided preparation](guided-preparation.md).

This milestone advances Y01, Y02, Y03 and Y10. The supported wider contract is
JSON input files and a JSON output judged by declarative predicates. It supports
rule-based selection/transformation and modeled constraint satisfaction without
adding a Python checker or material recipe for each task. It does not implement
all task semantics or complete the specification. Native execution remains the
existing builder-to-consumer route with optional no-package baselines.

## Prepare, inspect and execute

Use the [locked environment](../README.md#run-the-fixture). The
[example request](../studies/general-preparation-request.json) contains only a
work description and configuration, with explicit placeholder model names.
Choose available Inspect preparation/review models and a supported native subject
model before using it. Inspect provider credentials are configured through the
provider's normal environment. Alternatively use the native preparation role
[described below](#live-native-preparation) with a saved Codex login. Credentials
are passed separately from the frozen request and never included in its history.

```powershell
$draftRoot = Join-Path $env:USERPROFILE 'yassa-runs/general-preparation-example'
# REQUEST.json is your edited copy of the example request, outside the checkout.
uv run --locked yassa study-draft REQUEST.json --draft-dir "$draftRoot/round-0"
# If the review has material questions, provide answers in a new immutable round:
uv run --locked yassa study-revise "$draftRoot/round-0" ANSWERS.json --draft-dir "$draftRoot/round-1"
```

`ANSWERS.json` can contain `{"answers":["the clarification in ordinary language"]}`
along with changed configuration fields. Top-level fields replace prior values;
include prior answers when retaining them in the current answers list. Exact
original requests and all answer rounds remain in history regardless of replacement.
A sufficient task request uses no obligatory question round. Model errors,
unsupported semantics and material review findings withhold `study.json` and are
shown in the review. A failed response is preserved; a new `study-revise` call is
an explicit new allocation, with no silent retry or replacement of the old round.

Inspect `review.md`, `proposal.json` and `validation.json`. `draft.json` has a
machine-readable status and at most two next questions. The proposed assumptions,
all review issues, source/access records, selection, calibration output bytes,
component verdicts, model settings and native reservation remain inspectable.
Ready drafts connect directly to the current runner:

```powershell
$nativeImage = docker image inspect yassa-codex:0.153.4 --format '{{.Id}}'
$nativeRun = Join-Path $env:USERPROFILE 'yassa-runs/general-study-example'
uv run --locked yassa native-prepare "$draftRoot/round-1/study.json" --run-dir $nativeRun --image $nativeImage
$codexAuth = Join-Path $env:USERPROFILE '.codex/auth.json'
uv run --locked yassa native-execute $nativeRun --auth-file $codexAuth
uv run --locked yassa verify $nativeRun
uv run --locked yassa native-rescore $nativeRun --label repeat
```

Use `round-0` when it was already ready. `native-run` combines freeze and execute
when execution is authorized. These operations need no developer-authored
orchestration between the draft and the final native report. Preparation itself
does not launch subjects. Execution or publication authorization is separate
from a proposal's readiness.

## Requests, sources and expert imports

`yassa study-schema request` prints the current request schema. The command also
accepts `task`, `cases`, `proposal`, `review` and `native`. Their owning contracts
are [general_contracts.py](../src/yassa/general_contracts.py) and
[native_contracts.py](../src/yassa/native_contracts.py).

The request distinguishes the original work, intended use, answers, scope,
evidence requirement, material routes, preparation settings and execution settings.
Routine proposed settings are a descriptive trial, synthetic scope, explicit
skill use, seed 0, two development cases and three evaluation cases per route.
They are displayed in the review and can be revised. Subject models, treatment
arms, control rationales, repeats and resource caps have no inferred allocation.
Requests selecting native direct comparison, automatic activation, measured
clarification or broader inference remain unresolved. An optional consumer
baseline is the [existing control](configurable-native.md#consumer-baseline).

For supplied materials, each `documents` entry binds a local UTF-8 file by path
and SHA-256, plus an ID, description, origin, version, access, license, authorship,
synthetic flag and `split`: `specification`, `development` or `evaluation`.
Metadata can explicitly say unknown; this is recorded uncertainty, not verified
license or representativeness. Documents may be unstructured text or JSON;
preparation adapts them into JSON task inputs. Remote source discovery, downloads
and license research are not implemented. Do not use a specification document
to smuggle held-out answers into the public task contract.

Choose `routes: ["user-supplied", "yassa-prepared"]` to exercise both conditions.
The supplied route requires development and evaluation sources. Every adapted
case names its sources; the prepared route constructs new cases and may use
only specification sources. Supplied originals remain byte-identical in history,
while adapted materials retain the supplied route and link to that history.
Authorship, route and synthetic provenance are distinct records. Relative paths
resolve from each answer file; inherited sources use the prior draft's preserved
copies after relocation or deletion of the original input file.

Experts can provide `expert_proposal: {"path": "...", "sha256": "..."}` using
the same `StudyProposal` emitted by guided synthesis. Both routes run
`verify_proposal`, then the independent review and identical native compilation.
An expert can instead supply a pinned `expert_review` with `proposal_sha256`,
`reviewer`, `method`, `assessment` and `issues`. The proposal hash must match;
material issues block export. This records the supplied reviewer attestation,
not authenticated identity or proof of semantic correctness. With both expert
records, no preparation model configuration or calls are required. Ordinary
native v2 definitions using the new rubric must carry a pinned preparation review.

## Product operations and boundaries

[general_preparation.py](../src/yassa/general_preparation.py) implements reusable
task synthesis, case preparation, reference/calibration validation, independent
review, compilation and immutable round storage. These operations contain no
selection-task or assignment-task recipe. The acceptance test's task inputs,
simulated provider responses and native output driver are test data and adapters.
They do not implement any missing preparation or report step.

The task model receives only the request, answers and specification documents.
Separate fresh case calls receive the resolved task and sources for one route and
one split. Development construction never receives supplied evaluation sources.
The review call receives all preparation evidence in a fresh context, without
subject outcomes or treatment labels. It checks rule coverage, witness validity,
plausible failures, alternative outputs, provenance and source adaptation. It is
preparation assistance; final scoring makes no model calls. A model review can
still miss a semantic error, so its findings and limitations remain evidence.

Each guided round reserves one task call, two case calls per selected route and
one review call: four calls for one route or six for both. Explicit caps bound
calls, output tokens per call and request/sample time. Provider and Inspect
retries are disabled. Inspect logs preserve identities, inputs, responses, usage
when reported, and failures. Input tokens, dollar spend and setup overhead are
not hard capped; model aliases and seeds do not guarantee repeat generation.
Source pins and planned native attempts/deadlines are checked before model calls.
The exact generated outputs, rather than regeneration, are the replay basis.

Documents are limited to 20 files of 1 MB each; total input/history evidence is
limited to 10 MB before calls. Final preparation evidence is bounded to 500 files
and 20 MB. Each revision keeps prior source snapshots, model responses, decisions,
reviews, verification and exact preparer code in history. Original Inspect log
filenames remain in the draft; compact aliases with byte hashes are frozen for
Windows path portability. Incomplete/unsealed drafts remain inspectable but
cannot be revised as completed evidence.

Subjects receive public requirements, their assigned inputs and the declared
treatment package. Builders receive development examples only. Held-out files,
rubrics, reference witnesses, calibration outputs and preparation histories stay
in controller evidence. Group IDs must be disjoint across development/evaluation;
duplicate inputs are rejected after JSON normalization. Domain-specific semantic
equivalence beyond that normalization depends on reviewed grouping and selection;
the product does not claim to detect all disguised duplicates or semantic leaks.

## Declarative rubric and scoring

[json_rubric.py](../src/yassa/json_rubric.py) defines `json-predicates-v1`. JSON
trees can read declared parsed input files and the recorded JSON output, inspect
types/keys/length, compare values, perform bounded arithmetic, normalize strings,
map/filter/quantify arrays and compare unordered sets. It has no file, network,
Python evaluation or submitted-code execution capability. The model prompt and
public schema describe the exact operator vocabulary; unsupported operations
fail validation. Final checkers are protected controller code.

Input predicates must validate the case domain. Every scoring criterion must
inspect output, and the rubric must relate output to input. All output criteria
must pass; the recorded score retains each component and any evaluation errors.
Equality is type strict, so booleans are not numbers. JSON key order and whitespace
are irrelevant. Array order and permitted alternatives depend on the declared
predicates. Numeric operations exclude booleans and non-finite values; integers
are bounded to 256 bits. Trees, collections, operation counts and comparison
traversals are bounded; exceeding a checker bound rejects a candidate or output.

Every reference is a feasibility witness checked against predicates, not an exact
answer key. A different feasible assignment can pass. Every case also needs a
passing calibration probe, and plausible negative probes must exercise all score
criteria per condition, with declared failed criteria matching observed failures.
The separate preparation review assesses whether these checks and candidates
actually express the requested task. This is narrower than an independent
semantic oracle, and the report says so. Subject-output parsing failures become
zero scores; invalid protected case inputs prevent scoring as valid evidence.

Existing v1/v2 checker source files and their identities are unchanged. The new
rubric identity binds its declarative rules and interpreter source. Corrections
use new preparation rounds or the existing explicitly reasoned rescore policy;
original scores and failed evidence are preserved.

## Acceptance evidence and remaining work

Recorded checks: **234 tests passed, 1 skipped**; the **17 general preparation
tests** passed again after the final checker-identity change. Ruff, formatting,
patch whitespace and distribution builds passed; 36 packaged source/runtime files
matched their source bytes. The initial documentation check resolved 663 links
without failures. The [local acceptance record](C:/Users/Darian/yassa-runs/general-preparation-20260909-v1/acceptance-final.json)
links the preserved product review/report, score identity and exact software scope.
The final [historical compatibility check](C:/Users/Darian/yassa-runs/general-preparation-20260909-v1/historical-compatibility-summary.json)
retains all 250 score rows across seven studies and the context diagnostic seal;
original interpretations, including failed audits, remain unchanged.

Integration uses installed Inspect **0.3.263**, checked against its local
`Task`, `eval`, `GenerateConfig` and model output interfaces and the official
[task documentation](https://inspect.aisi.org.uk/tasks.html) and
[model configuration documentation](https://inspect.aisi.org.uk/models.html).
The preparer uses ordinary generation with explicit JSON schema instructions,
followed by strict local parsing/validation. It does not assume every provider
supports enforced structured decoding; invalid or truncated responses remain
failed preparation evidence.

The tracked [acceptance tests](../tests/test_general_preparation.py) exercise
rule-based record selection and feasible job assignment. They use actual Inspect
tasks with a simulated preparation provider and a controlled native adapter.
The CLI case prepares both supplied and constructed assignment conditions, freezes
them, records two builds and four consumer outputs, verifies the seal, rescores
and relocates the run. Consumers solve only their visible inputs and deliberately
submit valid assignments different from the stored witnesses. Other checks cover
questions, revisions, originals, source splits, unsupported conditions, admission,
model errors, independent review findings, invalid witnesses, checker failures and
expert import equivalence.

These initial results are software acceptance, not experimental findings. Initial
implementation made no live preparation API calls or native subject trials.
The subsequent separately authorized [live acceptance](#live-native-preparation)
adds evidence for one task; it does not establish general synthesis reliability.
The prior native adapter evidence remains in the
[v2 guide](configurable-native.md#verification-evidence). The prior 90-attempt
allocation remains consumed.

Y01/Y02 remain partial for general semantic tasks, source research and verified
real-world coverage. The subsequent [execution roles](execution-roles.md) add
direct native/API studies and external grading; additional native vendor/builder
roles, activation and measured clarification remain incomplete. Y10 remains partial
for full role coverage and public/redacted derivatives. The later
[resource/recovery controller](resource-controls.md) adds shared preparation and
execution accounting plus managed execution resume. Preparation resume, broader
model-grading evidence, inference/planning, native hard token/spend controls and
the substantive first Dovetail study remain on the
[full-spec roadmap](../SPEC.md#151-capability-coverage). Follow the
[current priority](../HANDOFF.md#current-development-priority); live validation is
scoped separately to a named capability and concrete resources.

## Live native preparation

The user separately authorized a small live acceptance on 2026-09-09, followed by
execution/grading implementation. It uses a synthetic room-booking conflict task
that has no task-specific generator or checker in product code. The development
agent supplied only ordinary requirements and raw development/evaluation inputs;
live models produced the task, JSON predicates, witnesses, cases and calibration.
Yassa commands perform the preparation, review, freeze, execution and reporting.

Native preparation settings use `runtime: "native-codex-cli"`, a pinned Docker
`image`, explicit `model`, `reviewer_model`, `reasoning_effort`, `max_calls`,
`max_output_bytes` and `timeout_seconds`. Append `--auth-file AUTH.json` to
`study-draft` or `study-revise`. Each call is a fresh Inspect Docker/Codex attempt
using the same permission and catalog acceptance boundary as subjects. Preparation
can use local tools to check its JSON. Its byte cap applies to accepted response
files; it is not a hard generation-token cap. Deadlines cover the native command,
excluding setup/export; input tokens and spend remain uncapped. Native internal
model requests and tool work are retained and can exceed one per preparation call.

The [allocation](C:/Users/Darian/yassa-runs/gp-live-20260909/allocation.json) reserves
at most two rounds of six preparation attempts at 180 seconds each, two builds at
120 seconds and four uses at 60 seconds: 2,640 maximum native command seconds.
No old benchmark allocation is reused and no automatic retry is permitted.
The initial round made six calls. The live reviewer found a source-narrative
ambiguity: task/case models referred to their own restricted source views while
the reviewer was given the global inventory without those views. It found no
booking-rule, source-adaptation, witness or calibration error, but the material
issue correctly withheld study export. That failed review remains unchanged.

The correction makes source visibility explicit. `study-revise` imported the
exact same model-produced proposal by hash and made one new review call, retaining
the original request, raw source bytes, generated cases and prior review. The new
review accepted the six witnesses and 100 probes, and the runnable study was
frozen. No hand-written rubric, substituted answers or regenerated cases were
used to obtain acceptance. The [ready review](C:/Users/Darian/yassa-runs/gp-live-20260909/r1/review.md)
and [frozen native plan](C:/Users/Darian/yassa-runs/gp-live-20260909/run/plan.json)
link the exact evidence.

Both packages were accepted and **4/4 fresh held-out consumers passed**, with no
missing scores or deadline failures. The [native report](C:/Users/Darian/yassa-runs/gp-live-20260909/run/interpretations/original/report.md)
records the two material conditions separately. The [acceptance audit](C:/Users/Darian/yassa-runs/gp-live-20260909/acceptance.json)
verifies the unchanged proposal and supplied originals, independently checks all
six references and four consumer decisions, and records a passing native-context
audit and byte-identical rescoring. All 13 root attempts used 1,262.516 native
command seconds (21.04 minutes), with 69 recorded internal model responses.
There were no automatic retries. Five reserved preparation attempts were unused;
they are not standing authorization for another study.

The final software check passed **248 tests, with one existing skip**. Ruff,
formatting and patch whitespace passed, and the built wheel matched all 41
source/runtime files. The SDK construction checks made no API inference calls.
This live acceptance establishes the connected workflow on one specified
synthetic task; broader preparation reliability, real booking reliability and
skill rankings remain unmeasured. New direct/API and external grading roles have
separate [software acceptance and limits](execution-roles.md).
