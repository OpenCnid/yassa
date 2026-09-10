# yassa

Yassa measures how prompts and agent skills affect performance on user-defined
tasks, using Inspect AI. For skill-builder comparisons, fresh agents use the
generated packages on held-out work; recorded outcomes provide the evidence.
Dovetail is the first subject.

**The core testing workflow works today and has completed live studies.** Users
can bring study materials or start with a rough request, prepare and review a task,
build or supply skills, test them with fresh agents on held-out cases, and inspect
scored results and resource reports. The current interface is a CLI.

## What works today

- **Prepare a study:** turn an ordinary description of JSON-based work into a
  reviewed task, rubric, examples and held-out cases, or supply existing materials.
  See [general preparation](docs/general-preparation.md).
- **Compare skills:** evaluate generated packages with fresh native Codex agents,
  include a no-package baseline, or compare existing skills through direct
  native/API studies. See [native studies](docs/configurable-native.md) and
  [direct execution](docs/execution-roles.md#direct-study-commands).
- **Reconstruct code artifacts:** give fresh agents specification files and test
  their saved Python projects against a separately held-out pytest suite. See
  [artifact studies](docs/artifact-studies.md).
- **Score recorded work:** use deterministic checkers or a calibrated model from
  a different family, preserve original outputs and logs, and reproduce reports
  without more model calls. See [external grading](docs/execution-roles.md#external-final-grading).
- **Control execution:** share attempt and deadline budgets across preparation,
  execution and grading; cancel and resume managed execution while retaining
  completed work and explicit failure records. See
  [resource controls and recovery](docs/resource-controls.md).

To try your own task, start with [Configure a small trial](#configure-a-small-trial).
To check the installation without live model calls, [run the simulated fixture](#run-the-fixture).

## Live evidence

These results come from recorded live runs, in addition to the software test suite.

| Workflow | Observed result |
| --- | --- |
| [Task preparation through skill use](docs/general-preparation.md#live-native-preparation) | A synthetic room-booking task reached two accepted packages and 4/4 passing held-out uses, after an explicit preparation review correction. |
| [Builder and baseline comparison](docs/package-reuse.md#recorded-results) | A 90-attempt study compared Dovetail, a common-request builder and a no-package baseline. All six packages were accepted; 84/84 consumers passed, including 12 baselines. |
| [Direct execution and independent grading](docs/execution-roles.md#live-native-direct-and-claude-grading) | The corrected native-direct run passed 8/8 cases; Claude passed 6/6 calibration cases and completed eight passing source grades. |
| [U-Neuron reconstruction from specifications](docs/u-neuron-reconstruction.md) | Dovetail passed 66/87 shipped tests versus 64/87 without it; the original passed 85/87. The two-test difference was error-message wording. Dovetail finished about 39% faster with 2.48× the reported tokens, mostly cached input; a mathematical correctness advantage was not established. |

The linked evidence retains earlier failures and corrections. Preparation,
execution, grading and offline replay used supported Yassa commands. Historical
acceptance work also used development scripts for tasks such as package selection,
calibration authorship and independent audits; those manual steps are identified
in the evidence.

These runs demonstrate that the framework operates. They do not establish a
general skill ranking. The synthetic comparisons repeatedly reached a correctness
ceiling, including the no-package baselines, which limited what they could tell us
about differences in skill quality.

## Next priority

**Resolve the correctness oracle exposed by the completed U-Neuron comparison.**
The [study record](docs/u-neuron-reconstruction.md) preserves the allocation,
results, resource tradeoff and packaging correction. The shipped tests assume
private implementation details and error-message wording absent from the two
specification sheets, limiting what the raw scores say about correctness.

The [next study work](docs/u-neuron-reconstruction.md#next-study-work) is to freeze
the required public API and test observable spec behavior, then validate the
oracle against legitimate alternatives and plausible mathematical errors.
Preserve the original artifacts and scores. A revised study needs its own frozen
definition and allocation; no additional model calls are implied. Further
engineering should address a concrete blocker in this work. Preparation recovery
is not a prerequisite for using the framework.

The full specification remains the delivery target and is incomplete. Current
task routes cover structured files/JSON and supplied Python/pytest artifacts;
broader task semantics, additional execution roles and inferential analysis remain
open. API execution is
implemented but lacks live inference acceptance. Native hard token/spend caps and
preparation resume are also absent. See the
[capability coverage map](SPEC.md#151-capability-coverage),
[development sequence](SPEC.md#152-development-sequence), and
[current priority and handoff](HANDOFF.md#current-development-priority) for the
implemented scope and remaining work.

## Implemented foundation and study history

The first implementation runs **synthetic fixtures with a simulated provider**
through Inspect AI. It supports direct tasks and a complete builder-to-consumer
path for both supplied and Yassa-prepared inputs. It preserves frozen plans,
exact packages, responses, original Inspect logs, and deterministic scores.
A second, bounded route runs real Codex CLI builders with and without a pinned
external Dovetail runtime pack, then fresh native consumers on held-out fixtures.
See [the native fixture](docs/native-fixture.md) for its design and measured scope.
The configurable native v2 route also supports declared file tasks, checker
selection, pinned source bindings, multiple builds, and consumer repeats; see
[configurable native studies](docs/configurable-native.md).
The optional consumer baseline receives complete task facts without a generated
package. The [synthetic reconciliation pilot](docs/reconciliation-pilot.md)
completed with 46/46 recorded consumers passing, including all 10 baselines;
one build-export failure left four planned uses missing.
Its context audit failed after detecting extra runtime plugin skill entries.
The subsequent [native context milestone](docs/native-context.md) adds exact
catalog checks and independent failure evidence. Authenticated root and child
validation passed; the original pilot's failed audit remains unchanged.
The subsequent [reconciliation study](docs/reconciliation-sensitivity.md) adds
event revisions, voids, exact decimals, per-case policies and interacting cases.
Its approved 68-attempt run completed with 60/60 consumers passing, including all
12 baselines: another correctness ceiling. Both offline evidence audits passed,
and repeat scoring was byte-identical.
The [package reuse milestone](docs/package-reuse.md) adds versioned resource
reports, opt-in case/repeat blocks, lifecycle diagnostics and a new synthetic
recipe. Its separately authorized 90-attempt allocation completed with all six
packages accepted and 84/84 consumers passing, including 12 baselines. Repeat
scoring and all three evidence/timing audits passed. The guide records per-build
resource curves and their narrow synthetic scope. This allocation is consumed.

## Run the fixture

Use Python 3.11.16 and [uv](https://docs.astral.sh/uv/). From this checkout:

```powershell
uv sync --locked
$runDirectory = Join-Path $env:USERPROFILE 'yassa-runs/fixture-example'
uv run --locked yassa run studies/fixture-study.json --run-dir $runDirectory
uv run --locked yassa verify $runDirectory
uv run --locked yassa rescore $runDirectory --label repeat-score
```

Choose a new run directory for each run. Evidence must live outside a Git/source
repository. `run` prints the report path, under
`RUN_DIRECTORY/interpretations/original/report.md`. The report links to original
inputs, packages, per-attempt bindings, Inspect logs, and scored work. Rescoring
makes no model calls and creates another interpretation without overwriting the
original. Changed scorer code requires `--reason "description of correction"`.

To inspect the frozen conditions before execution, use this two-step path instead:

```powershell
uv run --locked yassa prepare studies/fixture-study.json --run-dir $runDirectory
uv run --locked yassa execute $runDirectory
```

`prepare` prints the plan path. `execute` rejects changed inputs, code or
dependencies. A started managed run requires `execute RUN_DIRECTORY --resume`;
uncertain launches require an explicit disposition. Incomplete runs retain all
evidence and cannot be scored as complete. See
[cancellation and recovery commands](docs/resource-controls.md#resume-retry-and-uncertain-work).

## Run the native Codex fixture

Docker and a saved Codex ChatGPT login are required. The selected model, both
input conditions, ordering seed, and time limits are in
[native-codex-fixture.json](studies/native-codex-fixture.json). The external pack
is supplied explicitly and frozen by file hashes; it is never added to this repository.

```powershell
docker build --tag yassa-codex:0.153.4 --file runtime/codex/Dockerfile runtime/codex
$nativeImage = docker image inspect yassa-codex:0.153.4 --format '{{.Id}}'
$nativeRun = Join-Path $env:USERPROFILE 'yassa-runs/native-example'
$dovetailSource = Join-Path $env:USERPROFILE '.codex/skills'
$codexAuth = Join-Path $env:USERPROFILE '.codex/auth.json'
uv run --locked yassa native-run studies/native-codex-fixture.json --run-dir $nativeRun --dovetail-dir $dovetailSource --image $nativeImage --auth-file $codexAuth
uv run --locked yassa verify $nativeRun
uv run --locked yassa native-rescore $nativeRun --label repeat-score
```

`native-prepare` accepts the same preparation arguments without `--auth-file`;
`native-execute RUN_DIRECTORY --auth-file AUTH_FILE` starts the frozen plan.
Each attempt gets a new Inspect Docker sandbox and native Codex process.
Only its inputs and assigned skills enter `/work`. The credential file is
injected separately, denied to subject commands, and excluded from evidence.
The command boundary is probed before every attempt. Native transcripts and
Inspect logs preserve actual skill loading, tool work, usage, and output bytes.
The current profile disables plugins, remote plugins, and apps; it checks the
rendered root catalog before inference and all recorded root/child catalogs
before accepting outputs. See [the enforced scope](docs/native-context.md#enforced-boundary)
for the built-in pins and the limits of this acceptance gate.

The example plans four builds and twelve consumer runs. Deadlines are 300 seconds
per build and 120 seconds per consumer, excluding sandbox setup and export.
There are no harness attempt retries. This small synthetic comparison does not establish
a general builder ranking. [Native fixture details](docs/native-fixture.md) include
the exact source profile, runtime boundaries, and interpretation limits.

## Configure a small trial

Version 2 preparation requests use ordinary task descriptions with explicit model
and resource settings. `study-schema request` prints their schema. Yassa prepares
and reviews declarative JSON rubrics, examples and held-out cases; supplied and
constructed materials use the same native definition. See
[general preparation](docs/general-preparation.md) for model configuration,
expert imports, provenance and the complete preparation-to-report commands.

For a rough request, `study-draft REQUEST.json --draft-dir DIRECTORY` creates a
preparation review. `study-revise PREVIOUS_DIRECTORY ANSWERS.json --draft-dir
NEW_DIRECTORY` records focused answers in a new round. Complete inputs produce
the same native v2 definition used below. The bounded guided route supports
account totals and reconciliation, explicit rule choices, constructed feature
cases, original-byte provenance, checker verification, and budget review. See
[guided preparation](docs/guided-preparation.md) for the runnable example and limits.

For native v2, start from [account totals](studies/native-totals-v2.json) or
[reconciliation](studies/native-reconciliation-v2.json). Both examples use the
same native runner and include supplied/prepared materials. Run them with the
native commands above, omitting `--dovetail-dir`; source bindings belong in the
study definition. [The v2 guide](docs/configurable-native.md#run-a-definition)
describes task files, checkers, source pins, allocation, and admission limits.

[fixture-study.json](studies/fixture-study.json) is an editable example, not a
default for the Dovetail study. It declares three simulated treatments, both
preparation conditions, three evaluation cases per condition, one build per arm,
one execution repeat, and explicit limits. The supplied file is also synthetic;
the route describes how it enters the harness, separately from its authorship.

- Supplied inputs need an explicit path and SHA-256 of the original file bytes.
  Relative source paths resolve from the study file's directory. Update the pin
  deliberately when revising the source. Git preserves LF for fixture JSON.
- Prepared inputs need a request, seed, and case count. The fixed
  `account-totals-v1` template creates synthetic signed-amount cases and development
  examples. It records invented rules and validates every answer candidate with
  an independent deterministic oracle.
- Both routes pass the same schema, split, reference, and resource checks.
  Unsupported runtimes, task contracts, scoring methods, and analysis methods
  fail before any execution. JSON schemas are defined in
  [study.py](src/yassa/study.py).

`uv run --locked yassa intake REQUEST.json` provides up to two focused readiness
questions. This legacy helper is separate from the native guided workflow.
The legacy helper and version 1 recipe path do not interpret arbitrary task
descriptions. Version 2 preparation supports the declarative JSON scope above;
dataset research remains unimplemented.

## Verify changes

```powershell
uv run --locked pytest -q
uv run --locked ruff check src tests runtime
uv run --locked ruff format --check src tests runtime
git diff --check
```

These commands exercise preparation, plan arithmetic, actual Inspect requests,
package identity, checker alternatives, failure denominators, retries, limits,
evidence integrity, relocation, and rescoring. See
[the milestone evidence](docs/milestone-1.md) for observed checks and the example
run. Exact dependencies are in [pyproject.toml](pyproject.toml) and [uv.lock](uv.lock).

## Implemented boundary

The `simulated-api` route uses a trusted deterministic Inspect provider that
receives only two explicitly assembled messages, with no subject tools,
filesystem, network, or code execution. Each attempt uses a fresh model instance
and sample. Generated text packages are embedded explicitly in consumer requests;
this does **not** exercise native skill discovery, scripts, or activation.

The fixture output cap uses UTF-8 byte units, and Inspect applies per-sample time
limits. Token prices and real model token usage are unavailable. Counts stay
separate by preparation condition and execution stage; repeated uses of one
package do not become independent builder measurements. This fixture provides
no inferential analysis or cross-vendor evidence.

The `native-codex-cli` route exercises native skill loading and executable
packages in fresh Docker sandboxes. Native v2 supports UTF-8 file tasks with
account-totals, reconciliation, exact-JSON or declarative JSON checkers, configurable arms, and
independent builds/repeats. Guided preparation now produces that same definition
for account totals, simple reconciliation and event reconciliation. Legacy runs
remain verifiable and rescorable.
The [artifact route](docs/artifact-studies.md) freezes supplied specifications,
reference source and pytest suites separately, then builds and scores saved
Python projects. It has live U-Neuron evidence and requires preinstalled
dependencies; broader build systems and automatic artifact-task preparation
remain unsupported.
The general preparer adds model-assisted tasks within a bounded JSON predicate
contract. [Direct execution and external grading](docs/execution-roles.md) add
separately frozen native/API role studies and live-validated Claude Code grading
through saved OAuth. Broader semantic checkers, native subject/builder hosts,
API live inference, broader grading validation and inferential comparisons remain
future work.

## Design navigation

- [SPEC.md](SPEC.md): product requirements, measurement design, and open study choices.
- [ARCHITECTURE.md](ARCHITECTURE.md): implemented boundaries, invariants, and proposed extensions.
- [AGENTS.md](AGENTS.md): repository map and guidance for development agents.
- [HANDOFF.md](HANDOFF.md): current checkout state, evidence, and development priority.
