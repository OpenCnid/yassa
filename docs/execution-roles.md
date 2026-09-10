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

The subsequent [resource and recovery milestone](resource-controls.md) adds
`--resources`, cancellation, `--resume` and explicitly allowed infrastructure
retries to direct and grading execution. Default runs still make no automatic
retries. Controller summaries retain every physical attempt; grading's logical
call count and calibration gate remain separate from retry expenditure.

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
Direct prompts explicitly resolve the case-execution role when a source task
definition contains skill-building language. The source's complete public rules
remain quoted, and every arm receives the same case-result delivery instruction.

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

Declare an API or native Claude Code `role`, `scope`, `criteria` (IDs and descriptions), `calibration`,
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

### Saved Claude Code login

The `native-claude-code` grading role runs Claude Code 2.1.267 in a fresh Inspect
Docker sandbox per call. It uses the CLI's saved claude.ai OAuth login, including
normal refresh. No separate Anthropic API key is required. This is a grading host;
Claude direct subjects and builders are not implemented by this adapter.

```powershell
docker build --tag yassa-claude:2.1.267 --file runtime/claude/Dockerfile runtime/claude
docker image inspect yassa-claude:2.1.267 --format '{{.Id}}'
```

Use that immutable image ID in the request's role, with
`adapter: "native-claude-code"`, `model: "anthropic/claude-..."`,
`reasoning_effort` (`low`, `medium` or `high`), `timeout_seconds` (30–300) and
`max_output_tokens` (100–32000). Select an available model explicitly; aliases do
not pin immutable weights. Prepare the grading run using the same command above,
then provide the saved credential path only at execution:

```powershell
uv run --locked yassa grade-execute C:/path/outside-checkout/grades --auth-file C:/Users/NAME/.claude/.credentials.json
```

The declared system/user messages and criterion-derived response schema enter
the fresh grading context. The CLI runs in safe/restricted mode, with filesystem,
shell, network, agent and MCP tools, skills, customizations, hooks and session
persistence disabled. Its sole tool is `StructuredOutput`, the CLI's response
submission interface. The authoritative judgment is the terminal
`structured_output`, which must match the final response-tool input exactly.
Prose is retained but never extracted into a grade. Background title generation
and nonessential traffic are disabled. The native stream must record the sole
response tool, empty MCP/plugin/skill catalogs, the declared turn cap, the exact
selected response model and no extra model usage or API retry.
Capture failures retain raw evidence and yield
missing grades; calibration failure withholds all subject work. This checks the
CLI's recorded boundary, not an upstream attestation of every provider request.
Container network remains available to the CLI for authentication and inference;
the model has no network or filesystem tools.

`max_calls` counts native grading attempts for this host. `max_output_repairs`
defaults to zero and may explicitly allow one schema-format repair. A repaired
attempt must record the rejected tool input, its native schema-validation error,
and the final submission. The validator receives no calibration labels and
cannot request a semantic regrade. There are at most two turns with no repair
allowance, or three with one repair, within the same native deadline. API and
harness attempt retries remain disabled. Usage records retain all reported model
work and the number of output repairs. The response protocol follows the official
[structured-output interface](https://code.claude.com/docs/en/headless#get-structured-output).

The credential is injected privately, screened out of exported captures and
excluded from the frozen run. A CLI-refreshed login is written back to its private
credential file; a detected concurrent credential change blocks that write.
The runtime recipe, CLI version, image identity, command, native stream, Inspect
log, available model usage and elapsed command time are retained. Native output
tokens are a requested CLI setting, not a harness hard-token meter. Reported CLI
costs are provider list estimates, not verified subscription charges.

The adapter follows the official [CLI reference](https://code.claude.com/docs/en/cli-reference),
[authentication guide](https://code.claude.com/docs/en/authentication) and
[environment variable reference](https://code.claude.com/docs/en/env-vars).

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
fields explicit and distinguish calibration from external grading calls. The
[shared controller](resource-controls.md) now coordinates launch budgets,
cooperative cancellation and local resume, including explicit linked retries.
Preparation resume and authenticated native restart validation remain open.

The adapter uses installed Inspect 0.3.263's supported
[model providers](https://inspect.aisi.org.uk/providers.html),
[tasks](https://inspect.aisi.org.uk/tasks.html) and
[generation configuration](https://inspect.aisi.org.uk/models.html).
First-party SDKs are direct exact pins in [pyproject.toml](../pyproject.toml) and
their transitive resolutions are in [uv.lock](../uv.lock). Import/construction
checks of all three real Inspect provider classes make no inference requests.

[Execution-role acceptance tests](../tests/test_execution_roles.py) and
[Claude grading checks](../tests/test_claude_grading.py) exercise
the public CLI from direct preparation through execution, deterministic replay,
external calibration/grading and offline grade reporting. They use actual
Inspect model tasks with simulated provider responses, and a native adapter test
double. They test source pins, held-out context, prompt equality, legitimate work,
wrong work, infrastructure missingness, resource admission, family rejection,
calibration blocking, malformed grades and relocation. These tests establish
software behavior, not live cross-vendor or model-grading quality. The separate
live acceptance below adds evidence beyond
[the general preparation live acceptance](general-preparation.md#live-native-preparation).

## Live native direct and Claude grading

The user's continuation authorized native-direct validation and use of saved
Claude Code authentication. The external evidence is under
`C:/Users/Darian/yassa-runs/direct-live-20260909`; its
[acceptance ledger](C:/Users/Darian/yassa-runs/direct-live-20260909/acceptance.json)
preserves allocations, seals, raw captures, corrections and resource totals.

The direct comparison reused the prepared room-booking task: two material
conditions, two evaluation cases each, unassisted/existing-skill arms and one
repeat, with no builds. The previously accepted package was selected by lexical
build ID, independently of outcomes; its file bytes and executable declarations
were retained. Eight fresh GPT-6 Astra subjects used medium effort and 60-second
native deadlines, reserving 480 command seconds per separately frozen run.

The first run passed 5/8. Three unassisted agents followed source study wording
about building a skill and timed out without output. The direct prompt now
explicitly requests the case result while retaining all source requirements.
The corrected run passed **8/8, with no timeouts or missing scores**, using 132.780
native command seconds. The initial run's three failures and 313.172 seconds stay
recorded; they are not a skill-effect finding. Both context/output audits passed,
and both sets of scores replay byte-identically.

Claude Opus 5, through pinned Claude Code 2.1.267 and saved OAuth, then passed
**6/6 calibration cases and 8/8 recorded grades**, with no missing grades. The
frozen allocation reserved 14 attempts at 90 seconds each, high effort and a
requested 8,000 output tokens per response. One schema-only format repair was
allowed per attempt; **zero repairs were used**. Native commands used 110.283
seconds. All 14 native sessions recorded only the requested model and the
StructuredOutput response tool. An external audit independently checked every
calibration label and judgment against interval intersections, verified exact
call payloads and Inspect captures, and passed. Offline grading replay is
byte-identical and the original deterministic scores are unchanged.

The final passing run followed these preserved failures; no failed calibration
released subject work:

| Frozen run | Observed outcome |
| --- | --- |
| `grades` | Six calibration calls; five rejected undeclared Haiku background title usage. |
| `corrected-grades` | Six calls with title generation disabled; five responses violated the raw JSON contract. |
| `final-grades` | Six calls; stronger raw JSON instructions still failed calibration. |
| `structured-grades` | Four of six calibrations passed; one incorrect component judgment and one schema wrapper error. |
| `opus-grades` | Five of six passed; one schema wrapper error with no repair allowance. |
| `accepted-grades` | Six calibrations and eight source grades passed. |

Three separately recorded one-call diagnostics tested structured delivery and
native instructions. Two passed; one failed to use the response tool. The native
protocol now disables background title generation, validates terminal structured
delivery and enforces the explicit schema-repair allowance. Calibration examples,
labels and rubric remained unchanged throughout. The superseded
`bounded-repair-grades` freeze launched zero calls.

Across both direct runs, all grader runs and diagnostics, **63 native attempts
used 769.144 command seconds**. This excludes setup/export and the prior preparation
acceptance; native hard token/spend caps remain absent. Raw usage retains the
initial background model work. Reported list costs do not establish subscription
charges. The original prepared study seal and package bytes remain unchanged.

Study execution, grading and replay used supported product commands. Package
selection/copy, calibration authorship, raw-context and independent score audits,
and acceptance consolidation were external development operations. Reused
acceptance cases with fresh subjects validate integration, not new-task
generalization, skill superiority or broad grader reliability. API inference,
Claude subject/builder roles and broader evidence still need separate validation.

The final software suite passed 270 tests with one existing Windows symlink skip.
Ruff, formatting, patch whitespace, local documentation links and distribution
checks passed; all 43 packaged source/runtime files matched. These software checks
make no live inference calls and are separate from the acceptance outcomes above.

The [full capability map](../SPEC.md#151-capability-coverage) remains the delivery
target. Broader semantic preparation, additional native hosts and builder roles,
broader grading calibration, activation, clarification measurement,
inference, hard budget/recovery operations and the substantive Dovetail study
remain open.
