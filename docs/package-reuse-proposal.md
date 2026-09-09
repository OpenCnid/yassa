# After the reconciliation ceiling: assessment and next proposal

Implementation update: the requested offline harness work is now implemented;
see [the implemented guide](package-reuse.md). The assessment below remains the
proposal as reviewed; future study choices and launch authorization stay separate.

2026-09-09. **Evidence review complete; next design proposed, not accepted or
launch-ready.** This work makes no experimental model calls. The checkout began
clean at merged PR #6, `7c362caa3a24c1dbe10c1f8b2a5e459e4b6a793c`.

Recommend one offline implementation milestone: prepare a prospective,
correctness-qualified **package reuse efficiency** comparison on the existing
event-reconciliation contract. Keep new correctness workloads as alternatives.
The reason is an observed resource tradeoff worth testing, not an expectation
that more complicated inputs will distinguish builders.

## What the completed evidence establishes

The [completed assessment](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/results.md),
[frozen plan](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/run/plan.json),
[authorization](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/execution-authorization.json)
and [launch result](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/launch-result.json)
establish a completed allocation, not a pending launch. The request fixture and
launch review retain their historical preparation meaning.

| Evidence | Observed result | Supported interpretation |
| --- | --- | --- |
| Correctness | 8 accepted builds; 48/48 package uses and 12/12 baselines passed; no missing scores | Successful recorded work on these 12 constructed cases; no observed correctness gain from assistance |
| Build replication | Two builds per arm per condition; each passed its assigned four or eight cases | Limited within-brief build replication; 48 uses are not 48 independent builds |
| Deadlines | One Dovetail build at 600.234 seconds; one bulk baseline at 90.265 seconds; both had usable captured outputs | Timeout and output correctness are different outcomes; this does not establish time to first correct output or performance at shorter deadlines |
| Resources | 6,198.559 native seconds, 103.31 minutes, against 170 reserved; 134.54 minutes launch elapsed | Native command time excludes setup/export/reporting and is not end-to-end latency or billing cost |
| Reproducibility | Original and audited repeat-score bytes agree | Deterministic replay of recorded outputs, not an independent agent replication |
| Audits | General and capture audits pass; 68 roots, 7 children, no recorded violations or gaps | Evidence supports the declared catalog/capture boundary in this run |

The [general audit](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/run/interpretations/audited/general-auditor.json)
checks inputs, lineage and recorded work. The
[capture audit](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/run/interpretations/audited/capture-auditor.json)
checks raw/independent captures and exact recorded root/child catalogs. Root
preflight precedes inference; child checks occur after execution. Neither audit
attests all upstream context or intercepts every child request. An audit pass
also does not validate workload representativeness or statistical power.

The separate [offline review calculations](C:/Users/Darian/yassa-runs/reconciliation-next-design-20260909-v1/evidence-review.json)
reconcile native durations from individual attempt records and usage aggregates,
check auditor-source hashes and score bytes, and reverify run seals. They review
the recorded audits; they do not claim to have rerun both audit procedures.

Preserve the earlier evidence sets separately:

- [Reconciliation pilot](reconciliation-pilot.md#recorded-results): 46/46 recorded
  consumers passed, including 10 baselines; four planned uses remain missing and
  the catalog audit remains failed. It cannot supply a clean treatment contrast.
- [Native context diagnostic](native-context.md#verification-evidence): the
  separately authorized boundary validation passed. It does not repair the
  pilot's missing outputs or replace its failed audit.
- [Sensitivity study](reconciliation-sensitivity.md#recorded-results): the new
  68-attempt allocation is complete and audited. Changed rules, deadlines and
  runtime controls prevent attributing cross-run differences to one cause.

The [historical preservation record](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/history-after-launch.json)
is intact. This review also checked the pilot's two failed-audit artifacts and
the diagnostic check against their previously recorded hashes.

## Resource findings and unresolved questions

Use condition-specific means; supplied and prepared cases differ. The following
seconds are calculated from the recorded attempts, including deadline attempts:

| Condition | Consumer treatment | Mean build | Mean consumer | Uses per build in this run | Build plus those uses | Same-count baseline scenario |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Supplied | Common-request package | 404.60 | 38.74 | 4 | 559.55 | 242.91 |
| Supplied | Dovetail package | 570.78 | 28.91 | 4 | 686.41 | 242.91 |
| Prepared | Common-request package | 395.28 | 36.09 | 8 | 683.99 | 496.97 |
| Prepared | Dovetail package | 569.73 | 28.71 | 8 | 799.40 | 496.97 |

Baseline consumer means are 60.73 seconds supplied and 62.12 prepared, with no
build cost or build lineage. The final column multiplies those observed means;
it is a matched-use arithmetic scenario, not additional baseline executions.
Assisted consumers were faster descriptively, but neither arm repaid its build
time at the reuse counts actually assigned. Dovetail's lower consumer time came
with higher build time. There is no overall resource winner independent of reuse.

For illustration, `B + H*T` versus `H*T0` crosses at `H = B/(T0-T)` if `T0 > T`.
Using condition means yields approximately **15-19 uses** across the four rows
(the first strictly faster integer counts are 19, 18, 16 and 18). These are
post hoc extrapolations assuming the same case mixture, stationary use time,
successful builds and correct outputs. No package was actually tested for that
many uses. A negative/zero saving has no positive crossover; do not force one.

[Recorded usage](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/run/interpretations/audited/usage.json)
contains 354 response records: 6,005,304 input tokens, including 5,011,584 cached,
and 188,920 output tokens, including 28,417 reasoning tokens. Children are counted
within their roots. Recorded usage exists for every root, but unreported or
aborted requests can still be absent. Cache/reasoning subsets must not be added
again. Lower consumer duration does not imply lower total token use or price.

Unresolved: correctness benefit away from this ceiling; reliability across fresh
builds and repeated executions; whether time differences persist prospectively;
quality and resource behavior on other briefs, domains, models or real work;
and the useful reuse horizon. The cases are related synthetic constructions,
with one baseline execution per case. Supplied material is agent-authored, not
evidence of human authorship. Conditions do not isolate preparation effects.
The runtime model is an alias, and the Dovetail snapshot's upstream commit is
unknown. No equivalence, population effect or general builder ranking follows.
Common-request was not an explicitly invoked official-creator arm.

## Designs considered

| Candidate | Decision it could inform | Why it could be informative | Main cost or limitation | Recommendation |
| --- | --- | --- | --- | --- |
| Existing event contract, prospective reuse efficiency | Whether package generation saves native time over repeated fresh-session work, while preserving observed correctness | Directly tests the recorded build/use tradeoff; retains an independently checked task | Narrow to this contract and case mixture; timing noise and amortization assumptions | Select for the next bounded milestone |
| Pinned small repository repairs, split by defect/root cause | Whether generated workflow assistance improves functional repairs and avoids regressions | Multiple permissible patches and hidden behavioral tests can reveal procedural transfer | Need repository/license selection, defect provenance, patch execution isolation and validated tests; difficulty does not guarantee disagreement | Retain if correctness transfer becomes the primary decision |
| Synthetic policy-constrained allocation/planning | Whether assistance improves feasibility and objective quality | Many legitimate outputs; feasibility and objective can be checked independently | New semantics, independent optimum/reference method and validator calibration; no present evidence of model sensitivity | Retain as a later new-domain candidate |

Simply lengthening ledgers or reducing consumer deadlines is not a separate
justified correctness benchmark. A deadline sweep would study performance under
resource pressure and needs its own allocation; final artifacts cannot be
rescored as if they had been captured at an earlier time.

## Proposed study and claim

**Decision:** whether to invest in a broader package-efficiency comparison after
a prospective replication of this tradeoff. This is a small descriptive study,
not a deployment recommendation or an equivalence/non-inferiority test.

Primary contrasts: each generated-package arm versus no package, reporting
complete-task correctness together with build-inclusive native command time at
**20 downstream uses per build**. Twenty is a proposed scenario near the observed
crossover, not a user-provided business requirement or a measured reuse count.
Also report horizons 1, 5 and 50 and per-build crossover values. The Dovetail versus
common-request contrast is secondary. These are descriptive comparisons without
significance tests, confidence intervals or a winner-selection procedure.

Supported claim form: on the six frozen cases and selected runtime/deadlines,
these independent builds produced these correctness results and native-time
curves under a stated reuse assumption. A time advantage with correctness losses
or missing evidence does not support a claim of correctness-preserving efficiency.
Even universal observed success does not establish equal underlying reliability.
If the tradeoff fails to recur or remains inconsistent across builds, report that
and finish; do not add attempts to find a preferred result.

## Workload provenance and separation

Use one complete event-reconciliation brief, **Yassa-prepared synthetic inputs
only**, retaining the `reconciliation-v2` semantics. This is a focused follow-up;
the broader accepted multi-domain/two-route study remains open. No preparation-
route contrast is intended here.

Construct three development examples and six new evaluation inputs: two compact
cases, two cases combining revisions/voids/policy changes, and two bulk histories
within the prior roughly 400-row scale. Give the three profiles equal weight
(two cases each). This weight is a declared constructed workload, not estimated
production frequency. Avoid increasing size merely to induce errors.

Before any model attempts, record a new recipe/version, seeds, authored rules,
profile/lineage IDs, exact bytes and hashes, and a selection ledger retaining all
eligible constructed cases. Use independent event histories and values rather
than renamed or reordered copies. Validate that development/evaluation inputs are
semantically disjoint and that new evaluation inputs do not duplicate historical
cases. Keep shared template ancestry explicit: fresh data and seeds do not create
independent briefs or a representative workload. Prior results informed this
design and therefore belong to discovery evidence, not its prospective results.

Builders see only the common contract and development examples. All consumers
receive the complete contract, current policy and CSVs, and identical tool access;
assisted consumers additionally receive their frozen parent package. Keep held-out
inputs/answers, checkers, generator, reviews and other arms' artifacts outside
builder contexts. Only the current held-out input enters each consumer sandbox.
Authors can inspect validation cases; preparation is not blinded. Final material
bundles and the external source pack stay outside the repository.

## Arms, controls and sampling units

- **Common-request:** three independently generated packages, common creation
  request and pinned native built-ins. No added builder pack or explicit official
  creator invocation. Record any actual built-in use.
- **Dovetail:** three independent builds using the same previously audited
  external 83-file snapshot and explicit creator invocation, subject to fresh
  byte-pin verification. Preserve its unknown upstream-commit status. This tests
  that pack-plus-invocation treatment, not all Dovetail versions.
- **No-package consumer:** two fresh executions per case, no build/parent lineage,
  complete task facts and the same pinned built-ins. It may write scripts during
  its attempt. No files or conversation state persist between consumers.

Each package gets two fresh consumers on each of six cases: **6 builds, 72 package
uses, 12 baselines**. Cases are crossed with builds; repeats are nested within
package/case. The independent builder unit is a build conditional on this one
brief, not a use, script, child session or case. Two repeats expose execution
variation; three builds per arm provide only a small descriptive view of builder
variation. Neither removes uncertainty about workload selection.

Freeze every package; no best-of selection, repair or replacement. Retain the
same pinned image/CLI, model alias, reasoning setting, tools and deadlines across
arms and stages as the completed sensitivity study. Confirm availability before
freezing; a changed runtime becomes a separately reviewed condition.

After a seeded interleaved build phase, schedule 12 case/repeat blocks. Each block
contains all six package consumers and one baseline in a recorded seeded order;
balance arm positions as closely as possible without outcome-dependent changes.
Execute serially to limit host contention. The common baseline in a block is
shared comparison evidence, not copied into six independent observations.

This control measures persistent package assistance versus fresh sessions with
no retained artifact. It does not compare packages against a reusable ordinary
script, isolate instructions from code, or test automatic discovery. Adding a
direct-script, neutral-text or official-creator arm would change the question and
allocation; none is silently implied by these labels.

## Scoring, analysis and validation

Retain binary complete-task correctness from captured output bytes and the
existing independently validated `reconciliation-v2` checker. Keep schema, keys,
amounts, counts and statuses diagnostic. Accept balance/key reordering, whitespace
and Unicode-escape alternatives; accept any implementation producing valid work.
Reject duplicate/missing keys, extra fields, wrong numeric types, stale revisions,
wrong counts, float precision loss and incorrect tolerance/status precedence.

Validate all new references through the independent Decimal/sort oracle and the
separate candidate implementation. Retain hand-calculated cases, metamorphic
input/output alternatives and the eleven faulty-solver probes. Record exact
verdicts; a faulty solver that is equivalent on one case must pass that case.
These checks establish specified checker behavior, not expected model failures.

For build `b`, average both repeats within each case, then equally weight the six
cases to obtain `T_b`. Report `C_b(H) = B_b + H*T_b`; baseline is `C_0(H) = H*T_0`
with zero build cost, not a fictitious build. Average per-build curves equally
within each arm and show every build's curve/range and paired case differences.
Do not amortize the cost of all research builds onto a single deployed package.
Report total research expenditure separately. Keep usage categories and build/
consumer totals alongside native time; there is no dollar-cost metric.

The native-time endpoint is command start to return/cancellation, including the
observed small timeout overshoot. It is not first-correct-output latency. Record
normal completion, deadline termination and captured correctness separately;
show timeout counts beside every time summary. Add controller lifecycle timing
as a separate diagnostic for setup, execution, capture and cleanup, without
relabeling native time as end-to-end user latency.

All planned correctness outcomes stay in the denominator. Failed builds produce
zero for their planned uses; failed consumers retain zero and consumed resources.
Infrastructure/context failures remain missing. Usable deadline artifacts can
score correctly while retaining timeout status. Resource tables include every
launched attempt, not only successes. A build with incorrect/missing uses has no
qualified crossover or deployable efficiency claim; still show its observed
resources and failure coverage. Never make an early wrong answer look efficient
by reporting a success-only latency mean. No retries or automatic extensions.

## Required harness work and acceptance

The [technical design](../ARCHITECTURE.md#proposed-package-reuse-efficiency-milestone)
identifies changes against the existing runner. The bounded work is:

| Change | Acceptance evidence before a launch review |
| --- | --- |
| New prepared material recipe and provenance | Exactly 3 development/6 held-out cases; independent reference agreement; semantic split checks, lineage and recorded alternatives/fault probes; old fixtures/pins unchanged |
| Opt-in case/repeat block schedule | Deterministic for a frozen seed; exact 90-attempt/11,160-second admission; complete 12 blocks, valid parents, baseline independence, recorded ordering; old plan bytes unchanged when absent |
| Versioned descriptive resource report | Reconcile raw durations and root/child usage; explicit missing data; correct equal case/build weights, finite/no crossover and failure handling; distinguish research cost from per-build reuse |
| Lifecycle timing evidence | Monotonic durations with documented boundaries on success, timeout and capture/setup failures; native duration semantics unchanged; unavailable fields explicit; zero-call adapter tests |
| Compatibility and access | Context assembly excludes protected material; exact catalog/failure-capture regressions; baseline null lineage; relocated offline scoring; prior originals, scores, audits and seals unchanged |

Use existing Inspect tasks and Docker sandbox primitives. The locked installation
is Inspect **0.3.263**; its
[sandbox documentation](https://inspect.aisi.org.uk/sandboxing.html) and
[limits documentation](https://inspect.aisi.org.uk/setting-limits.html) were checked
during this review. Native calls here run through the CLI; Inspect's documented
model-generation token/cost limits do not by themselves establish a hard cap on
those calls. Verify behavior in the actual adapter rather than assuming coverage.

Acceptance for the offline PR: relevant focused tests, the full no-live-call
pytest suite, Ruff lint/format, documentation links/anchors and `git diff --check`.
Use recorded/fake adapter output and controlled clocks for scheduling/timing
tests. No authenticated smoke calls are included in this milestone. Newly added
timing fields remain unvalidated live until a separately authorized execution;
the existing runtime audit still gates acceptance of that future run.

## Proposed allocation and resource budget

| Allocation | Attempts | Native deadline | Reserved seconds |
| --- | ---: | ---: | ---: |
| Independent builds: 2 arms x 3 | 6 | 600 s | 3,600 |
| Package consumers: 6 builds x 6 cases x 2 repeats | 72 | 90 s | 6,480 |
| No-package consumers: 6 cases x 2 repeats | 12 | 90 s | 1,080 |
| Total | **90** | | **11,160 (186 minutes)** |

This redirects effort from two preparation conditions to execution repeats on
one brief; it is a resource-bounded descriptive allocation, not power-based
sizing. Build deadlines already approached saturation for Dovetail, so retain
600 seconds and report deadline failures instead of assuming every build works.
Keep 90-second consumers; no new deadline pressure or model change is proposed.

Applying the previous prepared-condition rates to these counts gives a planning
scenario of about **100 native minutes**, **6.44 million input** and **172,000
output tokens**. The new case mixture may differ. Mechanical half/double-usage
scenarios are roughly 3.2-12.9 million input and 86,000-344,000 output tokens;
these are sensitivity illustrations, not bounds, intervals or spend estimates.
Cache and child behavior can change; do not count their subset tokens twice.

The prior launch's non-native elapsed overhead was about 31 minutes for 68 roots.
Allow **60 additional minutes** for setup/export/reporting here: approximately
**4 hours 6 minutes** against the full native reservation, with offline preparation
and audits additional. This is planning headroom, not an enforced wall-clock cap.
Native deadline termination can also overshoot slightly. Hard token, dollar and
whole-session elapsed ceilings are unavailable in the current adapter. If one
is required, implement and verify it before launch; do not promise this allowance
as a spend or completion guarantee.

**Current authorized allocation: zero experimental attempts.** All numbers above
are proposals. No previous approval applies, and no executable launch command or
authorization record is created by this document.

## Review decisions and exact next work

Material decisions for the next review are whether reuse efficiency is the
intended next question, whether the one-brief synthetic scope and 20-use primary
scenario are useful, and whether the 90-attempt reservation with unavailable hard
spend/elapsed caps is acceptable. If correctness transfer or an explicit official
builder comparison is the priority, select a different design before building
its launch allocation. These are open choices, not missing facts needed to finish
this proposal.

Recommended next work is one **offline implementation PR** containing the recipe,
block scheduling, resource interpretation and timing evidence above. Start with
resource-report fixtures derived from the recorded evidence, then add scheduling/
timing tests and new materials. Finish by freezing the resulting material/source/
runtime identities and exact allocation in a new external review directory.
Deliver the admission arithmetic, validation results, capability limitations and
concrete launch review for separate authorization. Do not launch as part of that
PR, reopen completed runs, or select cases after observing new model outcomes.
