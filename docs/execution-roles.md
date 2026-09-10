# Direct execution and external grading

This milestone advances Y03, Y04, Y05 and Y07. Direct studies run existing prompt
or skill variants on held-out work without building a package first. They reuse a
pinned native v2 task definition, its supplied/prepared conditions and any bound
general preparation review. The source definition's builder allocation and
treatments are not executed. Original source bytes, prepared cases, protected
rubrics and source provenance are retained in the new freeze.

This is bounded product coverage. The common API route supports text tasks and
text skill resources without tools. It does not provide another vendor's native
agent host, executable API packages, automatic activation, measured clarification,
or multi-vendor builders. Those differences remain explicit requirements rather
than assumed properties of an API model.

## Direct study commands

Use the [locked environment](../README.md#run-the-fixture). Print the request
schema with `yassa role-schema direct`. A request has:

- `schema_version: 1`, an `id` and the study `question`.
- `task_source: {path, sha256}` pointing to a native v2 definition, including a
  `study.json` produced by [general preparation](general-preparation.md).
- An explicit `role`, selecting one host/model for every arm in this study.
- Pinned external `sources`, using the existing source-file contract, and `arms`
  containing `id`, source IDs, an optional invocation and a required rationale.
  Arms with sources require an explicit invocation.
- `repeats`, `schedule_seed`, `max_attempts` and `max_scheduled_seconds`.

Native roles declare `adapter: "native-codex-cli"`, a `gpt-` model name, immutable
Docker `image` identity, `reasoning_effort` and `timeout_seconds`. API roles declare
`adapter: "inspect-api"`, a first-party `openai/gpt-`, `anthropic/claude-` or
`google/gemini-` model, `max_output_tokens` and `timeout_seconds`. Model versions
are study decisions; aliases do not pin immutable weights. API roles explicitly
use the provider's first-party endpoint; proxy/Vertex roles are not implemented.

```powershell
uv run --locked yassa direct-prepare REQUEST.json --run-dir C:/path/outside-checkout/direct-run
# Native role only: append --auth-file C:/path/to/codex/auth.json
uv run --locked yassa direct-execute C:/path/outside-checkout/direct-run
uv run --locked yassa verify C:/path/outside-checkout/direct-run
uv run --locked yassa direct-rescore C:/path/outside-checkout/direct-run --label repeat
```

Inspect `review.md` and `plan.json` before execution. The plan admits all
conditions × cases × arms × repeats before calls, orders common case/repeat blocks
by a seeded hash, and records zero build parents. Every arm receives the same
public task requirements and current case; only its declared invocation/resources
differ. Development data, references, rubric and preparation histories stay in
controller evidence. Prompt/file hashes and treatment IDs are bound per attempt.

The native route calls the existing Inspect Docker adapter, including command
permission probes, pinned built-ins, root catalog preflight and recorded root/child
catalog acceptance. The API route uses fresh Inspect samples with only two explicit
messages, no tools, no model cache and no harness/provider retry allocation. It
embeds the declared UTF-8 `.md`, `.txt` and `.json` resources; executable resources
are rejected before calls. Native skill discovery is not reproduced by text
embedding. API input/treatment bundles are bounded to 5 MB as an admission check,
not an input-token or spend ceiling.

Reports retain all planned attempts, component verdicts, supplied/prepared
conditions, per-arm counts, available usage and missing infrastructure results.
Incorrect or absent work is zero; infrastructure failures are missing. Recorded
usable deadline output can still be checked. Repeat scoring makes no model calls;
changed checker identity requires an explicit correction reason. Relocation does
not require the original sources or credentials. Host differences remain part of
the measured conditions, and repeated executions do not become new sampled tasks.

## External final grading

`yassa role-schema grading` prints the grading request schema. External grading
reads sealed native v2 or direct-study work. It creates a separate frozen grade
run and leaves original deterministic interpretations unchanged. Each requested
dimension is binary, with overall success requiring every dimension; there is
no undeclared weighting or automatic deterministic/model composite.

Declare an API `role`, `scope`, `criteria` (IDs and descriptions), `calibration`,
`max_calls` and `max_scheduled_seconds`. Each calibration item has an ID, input
files, submitted output, expected Boolean components and a rationale. Every
criterion requires both successful and failing calibration examples. The
calibration labels are supplied judgments; their correctness is not authenticated
by the product. Include legitimate alternatives and plausible wrong work when
authoring them. Grading currently evaluates submitted UTF-8 output and input files,
not arbitrary services, images, tool trajectories or hidden filesystem state.

```powershell
uv run --locked yassa grade-prepare C:/path/to/sealed-run GRADE_REQUEST.json --grade-dir C:/path/outside-checkout/grades
uv run --locked yassa grade-execute C:/path/outside-checkout/grades
uv run --locked yassa verify C:/path/outside-checkout/grades
uv run --locked yassa grade-report C:/path/outside-checkout/grades --label repeat
```

The initial family gate is deliberately strict: the grader must have a different
vendor and model family from the subject. Another GPT version cannot grade native
GPT work through this route. First-party model prefixes establish the configured
identity; reported model identifiers and API responses remain inspectable. Unknown
proxy identities and jointly produced mixed-family work require a future explicit
policy. One grader configuration is common to every arm in a grade run.

The frozen review reserves every calibration call plus every planned source work
item. All calibration judgments must exactly match their labels before any source
work is released to the grader. A failed calibration retains its responses and
leaves all source grades missing. Missing submitted work is an explicitly recorded
task failure; source infrastructure failures and unavailable external grades remain
missing. There are no automatic replacement grades or retries. A new rubric,
calibration or model requires a new, separately recorded grading run and allocation.

Calls receive only common task requirements, the rubric, input files and submitted
output. They do not receive treatment labels, subject identities, source trial IDs,
expected verdicts or calibration labels. Content can reveal its author, so this is
label withholding, not guaranteed anonymization. Raw requests/responses, component
semantics, calibration verdicts, missingness, original source seal, model settings,
code snapshots and available usage are retained. Offline reporting re-parses the
recorded judgments and validates the calibration gate. Different grader scales are
not automatically comparable across subject families.

## Resource and verification boundaries

Direct and grading operations enforce whole-plan attempt admission and per-call
deadlines. API roles request an output-token cap; native roles retain native
command deadlines without a hard token cap. Input tokens, spend and setup/export
overhead are not hard capped. Native subagent work belongs to its root attempt.
Provider-returned usage can omit interrupted calls. Reports keep unavailable
fields explicit and distinguish calibration from external grading calls. Full
cross-role budget coordination, cancellation and crash recovery remain unfinished.

The adapter uses installed Inspect 0.3.263's supported
[model providers](https://inspect.aisi.org.uk/providers.html),
[tasks](https://inspect.aisi.org.uk/tasks.html) and
[generation configuration](https://inspect.aisi.org.uk/models.html).
First-party SDKs are direct exact pins in [pyproject.toml](../pyproject.toml) and
their transitive resolutions are in [uv.lock](../uv.lock). Import/construction
checks of all three real Inspect provider classes make no inference requests.

[Execution-role acceptance tests](../tests/test_execution_roles.py) exercise
the public CLI from direct preparation through execution, deterministic replay,
external calibration/grading and offline grade reporting. They use actual
Inspect model tasks with simulated provider responses, and a native adapter test
double. They test source pins, held-out context, prompt equality, legitimate work,
wrong work, infrastructure missingness, resource admission, family rejection,
calibration blocking, malformed grades and relocation. These tests establish
software behavior, not live cross-vendor or model-grading quality. Live verification
of each new native/API role remains separate from
[the general preparation live acceptance](general-preparation.md#live-native-preparation).

The [full capability map](../SPEC.md#151-capability-coverage) remains the delivery
target. Broader semantic preparation, additional native hosts and builder roles,
live cross-vendor grading calibration, activation, clarification measurement,
inference, hard budget/recovery operations and the substantive Dovetail study
remain open.
