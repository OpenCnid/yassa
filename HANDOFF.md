# Development handoff

Updated 2026-09-09: the [offline package reuse milestone](docs/package-reuse.md)
implements versioned resource interpretation, opt-in case/repeat scheduling,
controller lifecycle timing and a separate synthetic recipe under the unchanged
event contract. It began from PR #6 at `7c362caa` and integrated the seven
uncommitted proposal documents from the read-only `5040` worktree. No experimental
model calls were made.

The candidate review is external at
`C:/Users/Darian/yassa-runs/package-reuse-efficiency-20260909-v1`. Its one-brief
scope, 20-use primary scenario, 90-root allocation and 11,160-second reservation
remain proposals requiring separate concrete launch authorization. Do not merge
or launch as a consequence of this handoff.

Completed execution status: the user-approved reconciliation sensitivity allocation
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

- [SPEC next work](SPEC.md#15-next-work) for completed and outstanding scope.
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

## Next step: review the implementation and frozen launch proposal

**The approved allocation, audits and requested assessment are complete.** The
60/60 correctness ceiling gives no builder separation or equivalence result.
Assisted consumers used less native command time, but build costs were not
recovered at the four/eight uses actually assigned per package. The post hoc
15-19-use crossover calculation is an extrapolation, not a measured result.

1. Review [the implemented guide](docs/package-reuse.md) and
   [the proposal](docs/package-reuse-proposal.md). The latter recommends a
   prospective resource comparison over new inputs under the existing contract,
   ahead of repository-repair or constraint-planning workloads. The proposed
   decision, reuse horizon, synthetic scope and budget remain open. The broader
   multi-domain/official-builder program remains unimplemented.
2. The offline PR implements prepared material provenance, opt-in case/repeat
   blocking, versioned resource interpretation and lifecycle timing. Review
   [SPEC section 13.3](SPEC.md#133-proposed-package-reuse-efficiency-follow-up) and
   [the proposed technical boundary](ARCHITECTURE.md#proposed-package-reuse-efficiency-milestone).
   New lifecycle fields remain unvalidated live until a separately authorized run.
3. Proposed future allocation: one brief, six held-out cases, three builds per
   arm and two consumer repeats including baseline repeats; 6 builds + 72 package
   uses + 12 baselines = 90 attempts, 11,160 reserved native seconds. Budget and
   model/source assumptions require a new frozen review and separate launch
   authorization. No live smoke calls are included in the offline milestone.
4. Retain the current root preflight and recorded root/child postflight gates,
   raw captures, failed/missing denominators and immutable history. Child checks
   remain after execution. Preserve all original pilot, context and sensitivity
   evidence; do not reuse consumed approvals or restart completed runs.

The previous small comparison is complete; its case counts and deadlines, and
the v2 example allocations, are not pilot defaults. Binary inputs, broader
checker semantics, hard token/spend controls, recovery, additional vendor
runtimes, inferential analysis, and different-family grading remain outstanding.
Some details are proposals, not settled product requirements.

## Code entry points

| Area | Start here |
| --- | --- |
| CLI and simulated composition | [app.py](src/yassa/app.py) |
| Schemas, preparation, planning | [study.py](src/yassa/study.py), [prepare.py](src/yassa/prepare.py), [planning.py](src/yassa/planning.py) |
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

Offline reuse implementation: **217 tests passed, 1 skipped** in 353.69 seconds.
The existing Windows symlink skip remains. The focused reuse/resource/timing
checks passed 21 tests, including failed-build baseline independence and byte-
identical relocated scores/resource interpretations. `uv sync --locked`, Ruff
lint/format and whitespace checks passed. No authenticated smoke or model calls
ran; lifecycle timing has controlled-clock evidence only.

The separate historical resource replay reconciled 68 roots, 354 native response
records and 6,198.559 native seconds. The external candidate preparation freezes
90 roots and 11,160 native seconds with the same checker/runtime and verified
83-file external pack as sensitivity. See the
[launch review](C:/Users/Darian/yassa-runs/package-reuse-efficiency-20260909-v1/launch-review.md)
for exact identities, validation, history preservation and unresolved launch
choices. This review grants no execution authorization.

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
