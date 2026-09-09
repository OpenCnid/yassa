# yassa

Yassa measures how prompts and agent skills affect performance on user-defined
tasks, using Inspect AI. For skill-builder comparisons, fresh agents use the
generated packages on held-out work; recorded outcomes provide the evidence.
Dovetail is the first subject.

Users can bring study materials or start with a rough request. Yassa is intended
to help clarify the work and prepare missing tasks and examples, supporting both
small descriptive trials and studies requiring stronger evidence.

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

`prepare` prints the plan path. `execute` rejects changed inputs, code, or
dependencies and an already-started run. Automatic crash recovery is not yet
supported; an incomplete run is retained and cannot be scored as complete.

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
Neither path interprets arbitrary natural language into task semantics,
researches datasets, or generates model-based rubrics.

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
package do not become independent builder measurements. No inferential analysis
or cross-vendor claim is supported yet.

The `native-codex-cli` route exercises native skill loading and executable
packages in fresh Docker sandboxes. Native v2 supports UTF-8 file tasks with
account-totals, reconciliation, or exact-JSON checkers, configurable arms, and
independent builds/repeats. Guided preparation now produces that same definition
for account totals, simple reconciliation and event reconciliation. Legacy runs
remain verifiable and rescorable.
General task synthesis, broader semantic checkers, additional native CLIs, model
grading, and inferential comparisons remain future work.

## Design navigation

- [SPEC.md](SPEC.md): product requirements, measurement design, and open study choices.
- [ARCHITECTURE.md](ARCHITECTURE.md): proposed components, boundaries, and invariants.
- [AGENTS.md](AGENTS.md): repository map and guidance for development agents.
- [HANDOFF.md](HANDOFF.md): current checkout state, evidence, and the next implementation milestone.
