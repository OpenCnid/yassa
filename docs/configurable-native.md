# Configurable native studies

The native v2 path accepts task prompts, materials, output locations, checker
selection, builder arms, pinned source files, independent build counts, and
consumer repeats from a versioned study. It uses the existing Inspect Docker and
Codex adapter. Native v1 and simulated v1 readers remain available.
An optional consumer baseline adds fresh task executions without a generated
package; see [the reconciliation pilot](reconciliation-pilot.md).

This is a bounded file-processing milestone. A subsequent
[guided preparation workflow](guided-preparation.md) produces these same contracts
for account totals and simple/event reconciliation. General task synthesis,
inferential analysis, arbitrary
checker execution, additional vendor runtimes, recovery, and token/spend limits
remain outside the implemented scope.

## Run a definition

The [account-totals example](../studies/native-totals-v2.json) and
[reconciliation example](../studies/native-reconciliation-v2.json) use the same
runner. Each declares two preparation conditions, two control builds and one
instruction-treatment build per condition, two cases, and two consumer repeats.
Each reserves 6 builds plus 24 consumers: 30 attempts and 2,520 native command
seconds. These are implementation fixtures, not recommended pilot allocations.

```powershell
$nativeImage = docker image inspect yassa-codex:0.153.4 --format '{{.Id}}'
$runDirectory = Join-Path $env:USERPROFILE 'yassa-runs/reconciliation-example'
$codexAuth = Join-Path $env:USERPROFILE '.codex/auth.json'
uv run --locked yassa native-prepare studies/native-reconciliation-v2.json --run-dir $runDirectory --image $nativeImage
uv run --locked yassa native-execute $runDirectory --auth-file $codexAuth
uv run --locked yassa verify $runDirectory
uv run --locked yassa native-rescore $runDirectory --label repeat-score
```

`native-run` combines preparation and execution, taking `--auth-file` in addition
to the preparation arguments. Native v2 uses its study's `sources` field;
`--dovetail-dir` belongs to the legacy v1 fixture only. Preparation validates
references, source pins, paths, and full-plan admission before creating a run.
The frozen plan is available for inspection before any subject call.

## Task and materials contracts

[native_contracts.py](../src/yassa/native_contracts.py) owns the schemas and
preparation. [native_runner.py](../src/yassa/native_runner.py) owns the native v2
composition. They deliberately separate task semantics from sandbox execution.

| Contract | Version | Contents |
| --- | --- | --- |
| Native study | 2 | Question, scope, model, task, conditions, arms, sources, repeats, ordering seed, admission |
| Task | 1 | Requirements, common build/consumer prompts, package name and location, brief/result locations, checker and its input paths |
| File materials | 2 | Brief, provenance, optional builder files, development/evaluation cases with IDs, groups, input files and protected expected JSON |
| Frozen study, plan, bindings, results, scores | 2 | Immutable identities and explicit build, case, group, repeat and parent lineage |
| Artifact manifests and run seals | 1 | Existing byte identities, executable flags and append-only interpretations |

Paths use relative POSIX spelling. Subject data must be under `input/`; generated
packages and result JSON must be under `output/`. Source skills are installed
under `.agents/skills/`. Names must pass the portable artifact path rules.
Traversal, file/directory collisions, case collisions, and reserved probe paths
are rejected. Input bundles contain up to 100 UTF-8 text files and 5 MB; the
rendered builder input also has a 5 MB limit. Binary input attachments are not
part of this material contract.

The builder receives its common prompt, a rendered brief containing the task
requirements and development examples, and declared `builder_files`. Evaluation
cases and their expected outputs stay in controller evidence. Each consumer
receives only its current case's `files` and the frozen parent package. Expected
evaluation JSON, other cases, source builder packs, and other builds are never
added to that context. Authors remain responsible for keeping protected content
out of explicitly supplied public prompts and files.

Supplied materials use an explicit source path and SHA-256 of original bytes.
Prepared conditions choose a versioned generator, request, seed, and case count.
Both routes yield `FileMaterials` and undergo the same split and reference checks.
Original bytes, derivatives, assumptions, authorship, and preparation route are
retained separately. Development and evaluation groups must be disjoint, IDs
unique, and inputs distinct; specialized checkers also catch row-order relabeling.
The deterministic generators implement invented rules; the recorded request does
not cause natural-language task synthesis. Guided preparation emits this same
definition with explicit decisions and richer constructed feature cases. Its
`reviewed-files-v1` conditions bind exact material files and a portable preparation
record; the existing generators and their byte-pinned examples remain unchanged.

## Checker selection

[native_checkers.py](../src/yassa/native_checkers.py) reads recorded JSON as data.
It never imports or executes submitted packages on the controller.

| Checker | Inputs | Output equivalence and reference verification |
| --- | --- | --- |
| `account-totals-v1` | One declared JSON file with `rows` | Existing normalized totals semantics; unordered totals; independent oracle validates every candidate |
| `reconciliation-v1` | Two declared CSV files, in left/right order | Aggregate duplicate IDs separately, retain the union including zero balances, report left/right and left-minus-right; unordered balances; independent oracle validates every candidate |
| `reconciliation-v2` | Left CSV, right CSV, then JSON policy | Latest event revisions, voids, literal ID/currency keys, exact decimals, event counts and inclusive tolerance statuses; independent oracle; unordered balances |
| `json-exact-v1` | Arbitrary declared case files; `checker_inputs` is empty | Supplied expected JSON; object key order and whitespace ignored; array order and JSON numeric representation preserved; booleans differ from integers |

Reconciliation v1 CSV requires exactly `id,cents` columns. IDs are nonempty and
case-sensitive without trimming; CSV quoting is supported. Cents are signed
integers. Extra fields, duplicate output IDs, missing zero entries, wrong-side
amounts, and boolean amounts fail. Header-only inputs are valid.

Event reconciliation v2 is implemented in
[reconciliation.py](../src/yassa/reconciliation.py). It requires exactly
`event_id,revision,id,currency,amount,state` columns and a per-case currency
policy. Its [preparation design](reconciliation-sensitivity.md) defines coverage,
diagnostic components, checker alternatives and interpretation limits. Use the
guided `reviewed-files-v1` path or pinned supplied materials; there is no new
legacy `NativeCondition.generator` mode.

The exact JSON matcher supports new file tasks with author-verified expected
answers without runner changes. It validates JSON representation, not the truth
of supplied answers; reports disclose that distinction. A new semantic matcher
requires a versioned checker implementation, contract selection, and acceptance
and rejection fixtures. That work stays outside Python orchestration. There is
no arbitrary external-code checker loader in this milestone.

## Arms, sources, and allocation

Each arm declares its independent `builds`, optional source IDs, and an explicit
`invocation` prefix. The common task prompt and common input bytes stay identical
across arms within a condition/stage/case. The invocation and installed files are
declared treatment differences. Controls may have neither, or may use an
instruction treatment without a source pack.

A source binding has this shape (replace the descriptive placeholder values):

```json
{
  "id": "builder-pack",
  "path": "C:/external/runtime-skills",
  "files": {
    "builder/SKILL.md": "<64 lowercase hexadecimal SHA-256 characters>",
    "builder/scripts/check.py": "<64 lowercase hexadecimal SHA-256 characters>"
  },
  "executable": ["builder/scripts/check.py"]
}
```

Only named files enter the trial. Every skill directory needs a pinned `SKILL.md`.
Dependencies must be listed explicitly, including their bytes and executable
modes; missing or changed files fail preparation. Relative source roots resolve
from the study file. Subject source packs stay outside the Yassa source tree.
There is no automatic scan of personal skills or configuration. Dovetail can be
bound through this mechanism without special arm identities or source text in
the repository.

All builds run first, followed by consumers, with seeded hash ordering in each
phase. Each package gets `consumer_repeats` fresh attempts per case. Admission
reserves every planned build/use and its native command deadline. A plan exceeding
`max_attempts` or `max_scheduled_seconds` fails in full; no arm is silently dropped.
The time reservation excludes sandbox setup/export and is not a total elapsed-time
or spend cap. There are no harness retries or selection of the best build.

### Consumer baseline

Add `"consumer_baseline": {"id": "no-package", "repeats": 1}` to a native v2
definition to measure execution without a generated package. The ID must differ
from builder arm IDs. Repeats are explicit integers from 1 through 20; sources,
invocations and build counts are forbidden on this control. Guided drafts accept
the same field and require its ID in `control_rationale`.

The planner adds one execution per condition/case/baseline repeat, independently
of package builds and `consumer_repeats`. Baseline trials have role `consume`,
with `parent` and `build` set to null; there is no placeholder build or package.
They share the seeded consumer phase and consumer deadline, including admission.
They launch even if builders fail. Their own task failures score zero and
infrastructure failures remain missing.

In studies with a baseline, all consumers receive the complete `task.requirements`
and current case files in their common context. Authors must put every task fact
needed for correctness in that contract or the shared consumer prompt/files.
Assisted consumers additionally receive and explicitly invoke their exact parent
package. Bindings retain a common input identity across assisted and baseline
consumers for the same case. The baseline installs no external/generated skills;
native built-in skills remain present in every session.

Reports and `analysis.json` retain baseline counts separately from `by_build` in
`by_baseline`. `by_case` shows coverage and possible score saturation, with raw
passed/scored/planned/missing counts. Pooling uses within a case does not create
more independent builds. Old definitions without the baseline retain their
original prompt, plan, score and preparation-identity semantics.

Failed builds contribute zero to every planned downstream use. CLI/harness
failures leave downstream scores missing. A usable package produced before a
builder deadline can proceed, with `budget_exhausted` retained in the native
attempt record. Collector-rejected export paths fail package acceptance or consumer
scoring. A host artifact-path rejection becomes a harness failure. The
[pilot incident](reconciliation-pilot.md#recorded-results) lost its entire bundle;
the current adapter supports interior spaces and independently preserves raw
exports, transcripts and logs before normalized output acceptance. It also
rejects unexpected root/child catalogs. See [context control and capture limits](native-context.md)
for the exact gate and unavailable-evidence cases.
Reports show passed, scored, planned and missing counts separately for each
condition, arm and independent build. Repeats never become independent builds.

## Evidence and compatibility

Bindings freeze common input identity, treatment artifact IDs, full input file
hashes and executable flags, prompt hash, and trial/plan/study lineage. The
adapter also records actual launch inputs and retains Inspect logs, native
sessions, output bytes, boundary probes, and usage. Identical packages can share
one content identity while retaining distinct independent build IDs.

Execution rejects changed frozen inputs, code, runtime files, or installed
dependencies. A started or incomplete run cannot be resumed. Rescoring validates
the original seal and full planned result coverage, reads preserved output files,
and creates a new interpretation. Changed checker source requires `--reason`.
Legacy study/evidence version 1 dispatches to its existing readers and checker;
old frozen procedures and originals are not rewritten.

## Verification evidence

Automated coverage is in [test_native_v2.py](../tests/test_native_v2.py), alongside
the existing simulated Inspect and legacy native checks. The native v2 controller
tests substitute an explicit adapter fixture; they do not make live model calls
or establish actual sandbox isolation. They cover both preparation routes and
tasks, multi-build lineage, unequal arm allocations, byte-identical common
inputs, executable transfer, source pins, path boundaries, admission, failure
denominators, relocation, and deterministic rescoring.

Executed application checks: 102 passed, 1 skipped; Ruff lint/format and
`git diff --check` passed. The skip is Windows symlink creation, unavailable on
this host. The collector's symlink-root rejection was separately executed in the
pinned Linux image and passed with no files exported. Wheel and source
distribution builds passed; wheel native modules and runtime resource bytes
matched their source files. Local documentation links/anchors were checked.
Inspect 0.3.263 was confirmed locally and its supported execution primitives
checked against the [official sandboxing documentation](https://inspect.aisi.org.uk/sandboxing.html).

Compatibility checks on both preserved v1 runs passed: the native run's 12 score
rows and simulated run's 36 score rows were unchanged in new
`native-v2-compatibility` interpretations. Neither original seal, frozen procedure,
nor original interpretation was modified. The previous native fixture's
substantive scope and results remain in [native-fixture.md](native-fixture.md).

The live v2 integration directory is
`C:/Users/Darian/yassa-runs/native-v2-smoke-20260908T200834Z`. Its requests narrow
the example allocations to two independent builds and two fresh consumer repeats
on one case per task. Totals uses supplied materials; reconciliation uses the
prepared route and a pinned, Yassa-owned external `smoke-checks` fixture skill.
This is an adapter check, not another Dovetail comparison. Each task reserves
6 attempts and 600 native seconds (180 per build, 60 per consumer).

The [v2 auditor](../tests/audit_native_v2_run.py) checks actual launch inputs,
bindings, source/generated package bytes and modes, Inspect samples, native
catalogs and skill reads, distinct root sessions, common input equality, and
boundary probes. Its source and result are preserved beside each original report.
Final controller-only checks for early admission and file/source bounds were
tested after the live requests were frozen. Their preserved procedure snapshots
remain intact; the adapter, checker, valid input bytes, and admitted plan
identities are unchanged. The external `smoke-design.json` records preparation
from the example fixtures and this verification boundary.

| Task / route | Usable builds | Consumer passes | Audited fresh root sessions | Evidence |
| --- | ---: | ---: | ---: | --- |
| Totals / supplied | 2 | 4/4 | 6 | [Report](C:/Users/Darian/yassa-runs/native-v2-smoke-20260908T200834Z/totals/interpretations/original/report.md), [audit](C:/Users/Darian/yassa-runs/native-v2-smoke-20260908T200834Z/totals/interpretations/original/evidence-audit.json) |
| Reconciliation / prepared | 2 | 4/4 | 6 | [Report](C:/Users/Darian/yassa-runs/native-v2-smoke-20260908T200834Z/reconciliation/interpretations/original/report.md), [audit](C:/Users/Darian/yassa-runs/native-v2-smoke-20260908T200834Z/reconciliation/interpretations/original/evidence-audit.json) |

Both audits passed, including external skill loading in reconciliation and exact
generated-package transfer. All attempts captured the same unchanged built-in
skill snapshot. Each task's `repeat-score` interpretation reproduced its original
score bytes. Both totals builds reached their 180-second deadline after producing
usable packages; reconciliation builds completed in 160.1 and 179.7 seconds.
The reports preserve these native statuses separately from package readiness.
No attempt was retried, and all smoke-test containers were removed by normal
Inspect cleanup. These small synthetic outcomes establish integration under the
recorded conditions, not a builder ranking or representative task performance.
