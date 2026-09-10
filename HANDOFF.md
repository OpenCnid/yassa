# Development handoff

Updated 2026-09-09: **the delivery target is the full specification, and the
product is incomplete.** The user clarified that their build approvals were for
that target. The completed fixture milestones and study runs remain useful
evidence, but do not substitute for the missing product capabilities.

## Current development priority

The [execution roles implementation](docs/execution-roles.md) advances
[SPEC step 2](SPEC.md#152-development-sequence), Y03, Y04, Y05 and Y07: direct
native/API comparisons reuse a pinned task and both material routes, and external
grading enforces a different vendor/family with calibration, blinded call inputs,
missingness and replayable judgments. Native v1/v2 builder/consumer routes remain.
The user authorized one bounded live general-preparation acceptance and continued
execution/grading development. The room-booking task uses live native preparation,
one preserved failed review, one explicit correction review and the same generated
proposal. Evidence is under `C:/Users/Darian/yassa-runs/gp-live-20260909`.

This is bounded implementation coverage, not full-product completion. New direct
native/API roles and external grading have software acceptance, not live
cross-vendor quality evidence. Additional native hosts and API builders, measured
activation and clarification, semantic tasks outside JSON predicates, source
research, inferential planning and the substantive first study remain open.
Continue necessary integrated resource and durable cancellation/recovery work
(Y08/Y09/Y10, SPEC step 3) alongside the remaining role support. Live validation
must serve a named capability; do not default to another benchmark. See the updated
[capability map](SPEC.md#151-capability-coverage) and
[implemented boundary](ARCHITECTURE.md#implemented-general-preparation).

The new work began from PR #7's merge `8a7158259e6cc31240d7fda301946391cbd21131`
in `C:/Users/Darian/.codex/worktrees/cdb4/yassa`, on branch
`codex/general-preparation`. No prior benchmark allocation was reused. The
90-attempt reuse study remains consumed; new live validation needs a named
capability claim, concrete resource allocation and applicable authorization.
Do not merge the new milestone PR without authorization.

## Latest live product acceptance

The room-booking acceptance completed under its separate user authorization.
Seven preparation attempts (six initial calls and one explicit review correction),
two builders and four fresh consumers used 1,262.516 native command seconds of
the 2,640-second reservation. Both packages were accepted; 4/4 held-out outputs
passed, with no missing scores or deadline failures. The raw source originals
and model-generated proposal are unchanged across the correction. The initial
failed review remains preserved. The native context audit passed and repeat
scoring is byte-identical. [Acceptance evidence](C:/Users/Darian/yassa-runs/gp-live-20260909/acceptance.json).

The final software suite passed 248 tests with one existing Windows symlink skip.
Ruff, formatting, whitespace and distribution checks passed; the wheel matched 41
source/runtime files. New direct/API and grading tests use simulated providers and
a native test adapter. SDK construction checks exercise the real Inspect provider
classes, with zero API inference. Native direct execution and live cross-vendor
grading quality still require their own bounded verification. Core legacy native
runner/checker files and study fixtures are byte-unchanged from PR #8's prior head;
the previous 250-row historical replay remains earlier evidence, not a new replay.

The unused preparation reservation does not authorize another study. Continue
product implementation using the current priority above. Keep PR #8 unmerged
unless the user explicitly authorizes merging.

## Latest completed experiment

The separately authorized [package reuse allocation](docs/package-reuse.md#recorded-results)
completed all 90 attempts: six accepted packages, 72 package consumers and 12
no-package baselines. All 84 consumers passed; no scores are missing. Native
command time was 7,545.795 seconds (125.76 minutes); elapsed launch time
through original reporting was 165.16 minutes. Five baselines reached their
90-second deadlines with usable correct outputs. No builds or package consumers
timed out. No retries, replacement builds or added attempts ran.

Repeat scoring is byte-identical. General evidence, raw-capture/context and live
schedule/lifecycle audits passed, as did independent resource arithmetic checks.
The original frozen review, six historical seals and read-only proposal files
remain unchanged. The [result assessment](C:/Users/Darian/yassa-runs/package-reuse-execution-20260909-v1/results.md) links the complete
external evidence under `C:/Users/Darian/yassa-runs/package-reuse-execution-20260909-v1`.
The copied execution preserves the [original review](C:/Users/Darian/yassa-runs/package-reuse-efficiency-20260909-v1/launch-review.md) and its
unexecuted candidate. Do not relaunch this allocation or merge as a consequence
of this handoff. Further studies need their own concrete scope and authorization.

The preceding offline implementation began from PR #6 at `7c362caa`, integrated
the seven proposal documents from the read-only `5040` worktree and made no
experimental calls. The user then separately authorized this exact frozen run.

Earlier execution status: the user-approved reconciliation sensitivity allocation
completed all 68 attempts under
`C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1`. All eight
packages were accepted and all 60 consumers passed, including all 12 no-package
baselines. There are no missing scores. Native command time was 6,198.559 seconds
(103.31 minutes); elapsed launch time including setup, export, sealing and original
reporting was 134.54 minutes. One build and the bulk baseline reached their
deadlines with usable outputs. No retries, replacement builds or added cases ran.

Repeat scoring is byte-identical, and both general and raw-capture audits passed
with no violations or evidence gaps across 75 recorded root/child sessions.
Historical seals, original scores, the pilot's failed audits and the context
diagnostic were reverified unchanged. The external
[result assessment](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/results.md)
links the complete evidence.
Do not relaunch any completed allocation or request its already-granted approval.

Preparation state before the approved launch:
The [new preparation](docs/reconciliation-sensitivity.md) adds a separate event
contract, interacting cases and checker diagnostics. Its frozen plan reserves
68 attempts and 10,200 native command seconds: 8 builds, 48 package consumers and
12 baselines. [Reviewed launch plan](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/launch-review.md).

The previously implemented native catalog controls and independent captures
remain unchanged. The user-approved authenticated diagnostic passed:
two fresh roots and one child had exactly the expected catalogs, with no extra
plugins, and produced correct outputs. Native commands used 66.938 seconds of a
separately frozen 240-second reservation. No attempt was retried. See the
[context milestone](docs/native-context.md) and
[verified diagnostic report](C:/Users/Darian/yassa-runs/native-context-20260909-v1/interpretations/verified/report.md).

The earlier user-approved synthetic reconciliation pilot remains unchanged.
All 46 recorded consumers passed,
including all 10 no-package baselines. One build-export failure left four planned
uses missing. Native commands used 4,256.216 seconds (70.94 minutes) of the approved
7,800-second reservation. The run is sealed; no attempts were retried.

The declared-context audit failed: two unpinned plugin skill entries appeared in
five Dovetail builder subagent catalogs and one Dovetail consumer catalog. Preserve
the failed audit and the fuller follow-up findings. These observations prevent a
clean controlled comparison. The score ceiling still describes the recorded
outputs, without establishing equivalence or a builder ranking.
The [pilot assessment](C:/Users/Darian/yassa-runs/reconciliation-pilot-20260908-v1/pilot-analysis.md)
links to the original evidence, failed audit and correction checks.

After execution, host storage was corrected to accept interior-space filenames
such as `left ledger.csv`. Original output/transcript loss and the four missing
uses remain unchanged. The current adapter now archives raw exports before path
materialization, captures transcripts independently, and rejects unexpected
catalogs. Its root preflight precedes inference; the child gate checks recorded
context after execution and does not intercept each model request. The full spec
is not implemented.

## Begin here

Read [AGENTS.md](AGENTS.md) and [README.md](README.md), then:

- [SPEC capability coverage](SPEC.md#151-capability-coverage) and
  [development sequence](SPEC.md#152-development-sequence) for remaining product
  work; completed milestones are recorded separately in section 15.3.
- [Architecture: implemented native fixture](ARCHITECTURE.md#implemented-native-codex-fixture)
  and [remaining decisions](ARCHITECTURE.md#open-implementation-decisions).
- [Native milestone evidence](docs/native-fixture.md) for the actual experiment,
  source selection, limitations, and recorded corrections.
- [Configurable native studies](docs/configurable-native.md) for v2 contracts,
  examples, admission, compatibility, and integration evidence.
- [Guided preparation](docs/guided-preparation.md) for draft/revision commands,
  explicit correctness choices, constructed feature suites and preparation evidence.
- [Reconciliation pilot](docs/reconciliation-pilot.md) for the selected work,
  controls, source profile, exact allocation, observed scores and audit failures.
- [Native context control](docs/native-context.md) for catalog enforcement,
  independent raw capture, authenticated checks and remaining limits.
- [Reconciliation sensitivity study](docs/reconciliation-sensitivity.md)
  for the frozen materials, checker contract, completed allocation and new ceiling.
- [Assessment and next proposal](docs/package-reuse-proposal.md) for the reviewed
  correctness/resource/audit evidence, alternative designs and proposed allocation.

Inspect the current checkout and tools before choosing commands. This is a dated
handoff, not evidence that a path, installed tool, or account connection is still
available in a later environment. Requirements stay in SPEC and technical design
in ARCHITECTURE; update those documents as implementation advances.

## Checkout and evidence

The implementation and this handoff advance together. Begin from the revision
containing this milestone or a later default-branch revision. Inspect
`git status --short` and preserve additional local changes before beginning work.
This preparation began from merged PR #5, `0919307`, in
`C:/Users/Darian/.codex/worktrees/e3cc/yassa`. New run/preparation outputs are at
`C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1`.

The subsequent proposal review began from a clean detached checkout at merged
PR #6, `7c362caa3a24c1dbe10c1f8b2a5e459e4b6a793c`, in
`C:/Users/Darian/.codex/worktrees/5040/yassa`. Its separate offline calculations
are under `C:/Users/Darian/yassa-runs/reconciliation-next-design-20260909-v1`.
No completed run or interpretation was rewritten.

The original development workspace was
`C:/Users/Darian/.codex/worktrees/68a6/yassa`, based on `95666e2`
(`Merge pull request #1 from OpenCnid/codex/yassa-design-docs`). That base commit
predates the implementation. The source checkout is portable; the external
evidence and installed source pack described below are local to this machine.

The original kickoff document has been retired in favor of this handoff.
The consumer-baseline implementation made no live subject calls. The user then
approved launch of the frozen pilot; that run completed outside the repository.
Do not launch it a second time. Authorization and console output are recorded
beside the run in `execution-authorization.json` and `launch-console.txt`.
The separately authorized native context diagnostic is also complete. Its plan,
results, seal, and checks are under
`C:/Users/Darian/yassa-runs/native-context-20260909-v1`. Do not relaunch either
completed run or treat its allocation as standing authorization for new calls.

## What works

The implemented path is:

```text
study inputs -> frozen plan -> builder -> frozen package -> fresh consumer
             -> recorded work -> deterministic score -> report
```

- Simulated Inspect fixtures support direct and builder comparisons, both input
  preparation routes, configured repetitions, and explicit failure injection.
- Native Codex runs use one fresh Inspect Docker sandbox per attempt, actual
  skill discovery and explicit invocation, executable package transfer, native
  transcripts, token usage, and retained Inspect logs.
- Evidence has exact byte identities and seals. Rescoring creates a new
  interpretation without model calls or overwriting original evidence.
- Failed packages contribute zero to downstream uses; infrastructure failures
  remain missing. A usable package can proceed after its builder's deadline,
  with the underlying timeout retained separately from package readiness.

Native v2 accepts task prompts, UTF-8 input files, package/result locations,
account-totals/reconciliation/exact-JSON checkers, explicit pinned source bindings,
configurable arms and independent builds, and consumer repeats. Whole-plan
attempt/deadline admission occurs before launch. Both preparation routes produce
the same file-material contract. Native v1 remains readable and rescorable.
`study-draft` and `study-revise` now develop rough requests through explicit JSON
decisions into those same contracts for account totals and reconciliation.
Complete inputs proceed without an extra interview. Pending drafts expose at
most two questions, retain open correctness choices and cannot export a runnable
study. Preparation retains source originals, answer history, facts, assumptions,
controls and budget review, plus checker/preparer source identities. The new
seeded suites exercise six distinct features per family; callers may select a
subset. Both routes use independent reference and split validation, with checker
acceptance/rejection probes. Native freezing pins the review and materials, and
native reports link to preparation evidence kept outside subject contexts.
General natural-language synthesis and dataset research remain unimplemented.

Native v2 and guided drafts now accept an optional no-package consumer baseline
with a separate repeat count and null build/parent lineage. All consumers in
that study share complete task requirements and current case files; package
consumers additionally receive and invoke their parent package. Baseline calls
are fully admitted, interleaved with consumers, and launched even when builders
fail. Reports retain separate baseline and independent-build denominators and
add per-case counts for coverage/saturation review. Old definitions keep their
original prompts, plan, score and preparation-identity semantics. That baseline
milestone did not change the adapter, access profile or deterministic checker.
The subsequent context milestone adds the gate and independent evidence capture
described above; the command permission profile and task checker remain unchanged.

The new `reconciliation-v2` contract adds event revision/void processing, exact
decimals, policy-driven currency precision/tolerances, composite keys, counts and
statuses. Its separate recipe constructs three development examples and eight
held-out scenarios; the new supplied fixture has three examples and four cases.
Every reference passes an independent oracle, and 476 recorded checker probes
cover legitimate alternatives, structural errors and eleven faulty solvers.
Diagnostic components stay in score records; the primary outcome remains binary.

## Interpretation of completed studies

These results are historical context for development. The
[current implementation priority](#current-development-priority) owns the next
product work.

**The earlier sensitivity allocation and its assessment are complete.** Its
60/60 correctness ceiling gives no builder separation or equivalence result.
Assisted consumers used less native command time, but build costs were not
recovered at the four/eight uses actually assigned per package. The post hoc
15-19-use crossover calculation is an extrapolation, not a measured result.

1. [The completed package reuse results](docs/package-reuse.md#recorded-results)
   and their external evidence record primary H=20 arithmetic contrasts that are
   conditional on one synthetic brief and case mixture. Package uses are nested
   in builds; the shared baseline is not independent evidence for each contrast.
2. The broader multi-domain/official-builder program remains unimplemented.
   Retained ordinary scripts and instruction-versus-code ablations were outside
   this study. Further experimental work needs a concrete purpose and allocation;
   it must not displace unfinished product work by default. This completed run
   does not authorize outcome-driven extensions.
3. Lifecycle timing now has live evidence for evaluation, adapter setup, native
   command and capture/acceptance. Separate provisioning/cleanup and
   first-correct-output time remain unavailable. See
   [the technical boundary](ARCHITECTURE.md#package-reuse-efficiency-milestone).
4. Retain exact root preflight, recorded root/child postflight, raw captures,
   unsuccessful denominators and immutable history. Child checks remain after
   execution. Preserve the pilot's failed audits and four missing uses.

The previous small comparison is complete; its case counts and deadlines, and
the v2 example allocations, are not pilot defaults. Binary inputs, broader
checker semantics, hard token/spend controls, recovery, additional native vendor
runtimes and inferential analysis remain outstanding. The subsequent external
grading implementation has software acceptance, with live quality still unverified.
Some details are proposals, not settled product requirements.

## Code entry points

| Area | Start here |
| --- | --- |
| CLI and simulated composition | [app.py](src/yassa/app.py) |
| Schemas, preparation, planning | [study.py](src/yassa/study.py), [prepare.py](src/yassa/prepare.py), [planning.py](src/yassa/planning.py) |
| General model preparation and expert review | [general_preparation.py](src/yassa/general_preparation.py), [general_contracts.py](src/yassa/general_contracts.py), [preparation_model.py](src/yassa/preparation_model.py), [json_rubric.py](src/yassa/json_rubric.py) |
| Guided draft schema, readiness and revision | [guided_preparation.py](src/yassa/guided_preparation.py) |
| Constructed feature cases and checker probes | [preparation_templates.py](src/yassa/preparation_templates.py) |
| Event reconciliation semantics and faulty-solver probes | [reconciliation.py](src/yassa/reconciliation.py), [reconciliation_templates.py](src/yassa/reconciliation_templates.py) |
| Review/material byte pins and portable provenance | [preparation_evidence.py](src/yassa/preparation_evidence.py) |
| Native version dispatch and legacy fixture | [native.py](src/yassa/native.py) |
| Native v2 schemas, preparation, allocation | [native_contracts.py](src/yassa/native_contracts.py) |
| Package reuse resources, scheduling, timing and materials | [native_resources.py](src/yassa/native_resources.py), [native_scheduling.py](src/yassa/native_scheduling.py), [native_timing.py](src/yassa/native_timing.py), [reuse_materials.py](src/yassa/reuse_materials.py) |
| Native v2 freezing, execution, reporting | [native_runner.py](src/yassa/native_runner.py) |
| Versioned file-task checkers | [native_checkers.py](src/yassa/native_checkers.py) |
| Native Inspect execution boundary | [native_execution.py](src/yassa/native_execution.py) |
| Exact native catalogs and raw failure captures | [native_context.py](src/yassa/native_context.py), [native_capture.py](src/yassa/native_capture.py), [built-in pins](runtime/codex/builtin-skills.json) |
| Evidence and deterministic checking | [evidence.py](src/yassa/evidence.py), [scoring.py](src/yassa/scoring.py) |
| Container and access profile | [Dockerfile](runtime/codex/Dockerfile), [config.toml](runtime/codex/config.toml), [boundary probe](runtime/codex/boundary_probe.py) |
| Regression evidence | [tests](tests), [legacy auditor](tests/audit_native_run.py), [v2 auditor](tests/audit_native_v2_run.py) |

Start preparation work from `StudyDraft`, `prepare_draft`, `NativeStudyV2`,
`TaskContract`, `FileMaterials`, `prepare_files`, and `validate_materials`.
The simulated schema and legacy native
schema remain separate compatibility paths. Both reuse original account-totals
checking; v2 also adapts its generator. Preserve their recorded scope and readers.

## Completed native comparison

The run used Codex 0.153.4, GPT-6 Astra with `xhigh` reasoning, four builds and
twelve held-out consumer runs. Both arms scored 3/3 under supplied inputs and
3/3 under prepared inputs. Both control builds finished in about 195 seconds;
both Dovetail builds reached the 300-second deadline after writing usable packages.
Each Dovetail build used two native subagents, included in recorded usage.

This establishes success on the tested fixture and verifies the integration.
It does not establish equal skill quality or a general Dovetail ranking.

Evidence is at `C:/Users/Darian/yassa-runs/codex-dovetail-native-v1`:

- [Audited report](C:/Users/Darian/yassa-runs/codex-dovetail-native-v1/interpretations/audited/report.md).
- [Passing audit](C:/Users/Darian/yassa-runs/codex-dovetail-native-v1/interpretations/audited/evidence-audit.json): 16 attempts, 16 distinct root sessions, unchanged built-in skill bytes, actual skill reads, and exact input/package checks.
- Original, audited, and repeat-score interpretations remain preserved. The
  audited report makes build timeouts explicit; score rows match the original
  and repeat-score bytes match the audited scores.

The original frozen procedure predates the reporting-only timeout disclosure
correction. Do not rewrite frozen source or results to match newer checkout code.
The audit also corrected its expectation for explicit-only built-in skills;
the earlier auditor and correction note are retained with the audited report.

The simulated run is separately preserved at
`C:/Users/Darian/yassa-runs/kickoff-fixture-v1`; see
[its milestone document](docs/milestone-1.md). The authenticated loading probe
is at `C:/Users/Darian/yassa-runs/native-probe-01`. These are distinct runs.

## Source and runtime cautions grounded in this run

- Dovetail was the **installed Codex-oriented runtime pack**, snapshotted from
  `C:/Users/Darian/.codex/skills`, with 83 included runtime files pinned by hashes.
  Its upstream commit is unknown. It is not the public upstream revision examined
  during preparation, whose workflow text differed. Full pins and inclusion rules
  are in the native milestone document and frozen study.
- Keep subject skill text outside this repository. Do not apply evaluated skill
  instructions as development instructions. Native invocation policies matter:
  explicit-only skills can be on disk without appearing in the automatic catalog.
- The sandbox has no host workspace/home mounts or protected evaluation data.
  Saved ChatGPT authentication is injected privately and denied to subject commands.
  Shell network is disabled while Codex retains provider connectivity. No personal
  config or rules are included in launch inputs. The pilot nevertheless exposed
  runtime plugin catalog entries beyond the frozen sources; fixed-image and
  boundary-probe checks alone do not establish a closed subject context. The
  current explicit feature controls and exact catalog checks passed authenticated
  validation, within the limits recorded in the context milestone.
- Native calls use the CLI's saved-auth route, not Inspect Agent Bridge. Reported
  usage counts native response records, including subagents; aborted requests may
  leave unreported usage. Dollar cost and hard token/spend limits are unavailable.
- A rebuilt Docker image can differ because Debian packages are resolved at build
  time. Record and use its actual immutable image identity. Do not replace the
  tested image's identity with a mutable tag in a frozen run.
- On Windows, package sync can fail while `yassa.exe` is running. Finish the run
  before reinstalling the package; use the existing Python interpreter for
  concurrent read-only diagnostics. No broader run should start merely to refresh
  already verified evidence.

## Verification and delivery

General preparation verification: **234 passed, 1 skipped** in the full suite;
the **17 new tests** passed again after the final checker-identity binding change.
Ruff checks, formatting and patch whitespace passed. Wheel/source distributions
built outside the checkout; 36 packaged source/runtime files matched source bytes.
The documentation check resolved 663 links across owning documents and generated
reviews at that check. The existing Windows symlink-permission skip remains.

The [acceptance record](C:/Users/Darian/yassa-runs/general-preparation-20260909-v1/acceptance-final.json)
links the product-generated review and report under
`C:/Users/Darian/yassa-runs/general-preparation-20260909-v1`. The tracked CLI test
made six simulated preparation calls, then recorded two native-adapter builds
and four passing consumers across supplied/prepared assignment work. Consumers
used valid alternative assignments. Repeat and relocated scores were identical.
Separate tests cover selection, revisions, failures, source boundaries and
byte-identical guided/expert executable definitions. No live calls were made.

Historical v1 and v2 compatibility replays preserve original score rows and
all prior interpretations, including failed audits. Older v2 frozen checkers
already differed from the pre-milestone source; their replays record an explicit
reason. The [follow-up verification](C:/Users/Darian/yassa-runs/general-preparation-20260909-v1/historical-compatibility-followup.json)
records those checks and the context diagnostic's unchanged seal. No original
run, score, failed capture or benchmark allocation was replaced.
The completed [compatibility summary](C:/Users/Darian/yassa-runs/general-preparation-20260909-v1/historical-compatibility-summary.json)
confirms 250 unchanged score rows across seven historical studies, plus the
context diagnostic seal. Initial path/interpretation diagnostics and their
explicit follow-up corrections are retained. PR [#8](https://github.com/OpenCnid/yassa/pull/8)
is open and unmerged.

Offline reuse implementation: **217 tests passed, 1 skipped** in 353.69 seconds.
The existing Windows symlink skip remains. The focused reuse/resource/timing
checks passed 21 tests, including failed-build baseline independence and byte-
identical relocated scores/resource interpretations. `uv sync --locked`, Ruff
lint/format and whitespace checks passed. No authenticated smoke or model calls
ran during that implementation stage. The later separately authorized run adds
the live evidence linked at the top of this handoff.

The separate historical resource replay reconciled 68 roots, 354 native response
records and 6,198.559 native seconds. The external candidate preparation freezes
90 roots and 11,160 native seconds with the same checker/runtime and verified
83-file external pack as sensitivity. See the
[launch review](C:/Users/Darian/yassa-runs/package-reuse-efficiency-20260909-v1/launch-review.md)
for exact identities, validation and history preservation at freeze time.
Separate user authorization subsequently launched its exact copied candidate;
the completed allocation and new audits are linked at the top of this handoff.

Offline proposal review: resource arithmetic and original/audited score bytes
agree; six run seals were reverified, and the pilot's failed audits and diagnostic
check match their historical hashes. All 220 checked local documentation links/
anchors and `git diff --check` passed. `uv sync --locked` confirmed Inspect
0.3.263. Repository changes are documentation only; the full pytest/Ruff checks
were not rerun for this proposal. Review scripts and results are in the separate
`reconciliation-next-design-20260909-v1` external directory. No experimental
model calls were made. The results below remain the previous milestone's checks.

Prelaunch preparation verification: **196 tests passed, 1 skipped** in 239.73
seconds. The existing Windows symlink skip remains. Focused preparation/event
checks passed 60 tests before the full suite. Ruff lint/format, wheel/source
builds and whitespace checks passed; final distribution and documentation details
are in the external [verification report](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/verification.md).

The subsequent approved native launch completed 68/68 attempts, with 60/60
passing consumer scores, no missing uses, 75 recorded sessions and two usable
deadline outputs. Both general and capture audits passed, and offline rescoring
reproduced original score bytes. The
[postlaunch history check](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/history-after-launch.json)
reverified the prior seals, original scores and failed audit artifacts unchanged.
These authenticated results are separate from the prelaunch offline test suite.
The offline tests, compatibility rescores and postprocessing checks made no
experimental model calls. The unchanged native execution adapter and
catalog/capture implementation were exercised by the approved 68-attempt study
in addition to the separately completed diagnostic.

The ready review records 179 supplied and 297 prepared checker probes. All eleven
faulty solvers are detected by at least one prepared evaluation case. The freeze
pins exact materials, sources, checker/preparer bytes, dependencies and runtime
files. Freeze ID is
`821a2153d927614ffa363433d84c228e71c85bb7792717adf5b49fef4cf03b28`.
The completed attempts and results are sealed under that frozen allocation. If
implementation/dependencies change, create a separately identified new freeze;
never edit this one.

Offline `sensitivity-preparation-compatibility` interpretations preserved all
50 pilot, 12 native v1, 4 native v2 reconciliation and 4 native v2 totals score
rows. The original score files and seals are unchanged. New interpretation
metadata records the changed checker dispatcher and explicit reason, so whole
rescore files are not byte-identical. The pilot's initial/follow-up failed audits
and four missing rows remain intact. The diagnostic's seal still verifies.

Previous context implementation verification: **163 tests passed, 1 skipped** in the full
suite, including 11 context/capture tests and six Inspect adapter outcomes using
a simulated sandbox. These checks make no model calls. Authenticated validation
separately passed for two roots and one child. All 26 packaged source/runtime
files matched checkout bytes; wheel and source builds passed. See the
[diagnostic report](C:/Users/Darian/yassa-runs/native-context-20260909-v1/interpretations/verified/report.md)
for final lint, documentation, distribution and compatibility checks.

Offline replay of 53 preserved pilot exports detected all six unexpected
catalogs across four attempts under the new gate. Pilot and native v1 offline
rescores preserve their 50 and 12 score rows, original bytes and original seals.
The diagnostic's original seal remains unchanged. A postprocessing helper was
briefly written at its sealed root, then moved into `interpretations/verified`;
no original evidence changed. The correction and successful seal recheck are
recorded beside the diagnostic report.

Previous consumer-baseline verification: **151 tests passed, 1 skipped** in the
full suite after the exporter fix. The final catalog-audit refinement then passed
all **3 focused audit tests**; Ruff lint/format and `git diff --check` passed.
Wheel and source builds passed.
The 14 new cases exercise baseline admission/context/failure/reporting behavior,
review compatibility and pilot preparation. The earlier test run had two failures
in a test that replaced hashing during material validation; the test was corrected
to observe Docker admission directly, then the focused and full checks passed.
No production checker correction was needed. The Windows symlink skip remains.
All 23 packaged source/runtime files matched the corrected checkout bytes.
The final documentation check resolved **594 local links/anchors** across 16
files, including preparation reviews, all three reports and the pilot assessment.
No pilot container remains running.
Offline `consumer-baseline-compatibility` interpretations preserved the original
36 simulated, 12 native v1, 4 native v2 totals and 4 native v2 reconciliation
score rows. Their original bytes and seals remain unchanged. The previous guided
preparation manifest also still validates. The external `compatibility.json`
records those checks and the historical unstarted freeze identity.

The local [ready pilot review](C:/Users/Darian/yassa-runs/reconciliation-pilot-20260908-v1/round-1/review.md)
and [frozen plan](C:/Users/Darian/yassa-runs/reconciliation-pilot-20260908-v1/run/plan.json)
preserve both input routes, independent reference/checker probes and the complete
58-attempt allocation. The preparation script, source answers and source
provenance are preserved beside the review. The completed run has 54 launched
attempts (8 builds and 46 consumers) and four unlaunched dependencies. Seven
packages were accepted. There were no native timeouts; the export failure remains
a harness failure after a native exit code of 0. Original and offline repeat
scores are byte-identical, including all four missing rows, and the original
run seal remains unchanged.

The audit first stopped at an unexpected consumer catalog; its source and
traceback remain under `interpretations/audited`. The follow-up auditor checks
all recorded root/subagent catalogs and reports violations with a **failed**
verdict, separate from missing evidence. It never turns a catalog mismatch into
a passing audit. The builder export gap remains unavailable, with no invented
package, session identity or usage. See [pilot evidence](docs/reconciliation-pilot.md#recorded-results).

The new space-path regression reproduced the native export rejection before the
fix and passed afterward. A no-network, no-auth, no-model run of the pinned Linux
collector preserved the same kind of filenames and an executable script. Its
recorded export round-tripped through corrected Windows storage and relocation.
`export-fix-verification.json` preserves byte/mode and distribution checks;
`path-fix-compatibility.json` records the unchanged pilot seal and 50 score rows.

Previous guided-preparation application verification: **130 tests passed, 1 skipped** in the full
suite; the **28 preparation tests** passed again after final provenance and
review-format refinements. Ruff checks and formatting passed, wheel and source
distribution built, and 23 packaged source modules/runtime files matched their
source bytes. Windows cannot create the symlink used by the skipped collector
test; the same rejection check passed in the prior milestone's pinned Linux
container. A local documentation check resolved 160 links/anchors, including the
generated preparation reviews.

Both original v1 runs and both native v2 smoke runs still verify. New
`guided-preparation-compatibility` interpretations preserve all original native
score rows: 12 in the v1 comparison, 4 in v2 totals, and 4 in v2 reconciliation.
Those are offline rescores of preserved work, with no new subject calls.

The documented draft/revision commands completed under
`C:/Users/Darian/yassa-runs/guided-preparation-milestone-v2`. The
[ready review](C:/Users/Darian/yassa-runs/guided-preparation-milestone-v2/round-1/review.md)
records both preparation routes, source originals, checker/preparer source bytes,
and a plan reserving 54 attempts and 1,800 native command seconds. These are
reviewed example settings; no subjects were launched. The earlier
`guided-preparation-milestone-v1` draft example is preserved and predates final
selection-provenance and review-format refinements. The native test adapter
separately exercised freezing, 48 recorded consumer outcomes, preparation-context
exclusion, report linkage and byte-identical relocated rescoring.

The v2 live smoke evidence and audit are recorded in
[configurable native studies](docs/configurable-native.md#verification-evidence).
Both task runs completed: 4 usable builds and 8/8 successful consumers across
12 native attempts. Each task's six-session audit and byte-identical repeat
scoring passed. Both totals builders reached their deadline with usable packages;
the reconciliation builds completed within it. The runs used supplied totals and
prepared reconciliation inputs; this was not a new Dovetail comparison. No smoke
container remains running. Final preflight-only bounds have separate passing
tests; the live runs retain their exact earlier procedure snapshots.
The previous native milestone's 75-test result and original comparison remain
historical evidence in its own document.

The pinned environment is Python 3.11.16, Inspect AI 0.3.263, Pydantic 2.13.5,
and PyYAML 6.0.3, with the complete dependency graph in `uv.lock`.

```powershell
uv sync --locked
uv run --locked pytest -q
uv run --locked ruff check src tests runtime
uv run --locked ruff format --check src tests runtime
uv build --no-sources
git diff --check
```

Select checks appropriate to new changes. Unit/integration tests make no live
model calls. Native runtime changes need separately recorded native evidence
under the current user's authorized scope and resources. Use new external run
directories; preserve originals and record corrections explicitly. Before closing
the next milestone, update the owning spec/design sections, verified commands,
evidence documentation, and this handoff's remaining work.
