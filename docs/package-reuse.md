# Offline package reuse milestone

Implemented 2026-09-09 from the [proposal](package-reuse-proposal.md). This adds
offline preparation, ordering, resource interpretation and timing evidence to
the existing native v2 runner. **No new experimental attempts are authorized or
executed.** The proposed one-brief study and its allocation still need a separate
concrete launch review. No completed run or consumed approval is reused.

## Resource interpretation

`native-resources` reads a sealed native v2 run and an existing score
interpretation, and creates a new external directory. For example:

```powershell
uv run --locked yassa native-resources C:/path/to/completed-run --scores audited --output-dir C:/path/to/new-resource-review
```

The command makes no model calls, does not rescore work, and does not modify the
source run or its interpretations. It rejects an existing output directory and
an output directory inside the preserved run. [The interpreter](../src/yassa/native_resources.py)
records its version, source hashes, run seal, plan identity and score-file hash.
`resources.json` is the complete machine-readable interpretation; `report.md`
provides a short linked view.

| Record | Meaning |
| --- | --- |
| `attempts` | Every planned root, lineage, correctness, result/native status, raw duration, reconciliation issues, usage/session records and lifecycle availability |
| `research` | Every build and consumer arm's observed expenditure, status counts, launched/planned counts, timeouts and unavailable durations/usage |
| `builds` | Each independent build, equal-case mean use time, case comparisons, baseline differences and deployment curves |
| `baselines` | Complete case/repeat denominator, zero build cost, null build/parent lineage and baseline curves |
| `arms` | Equally weighted build curves and ranges, baseline contrasts, build timeout counts and consumer coverage |

Repeat durations are averaged within each case, then cases are weighted equally.
For build `b`, the hypothetical deployment curve is `B_b + H*T_b`. Arm curves
average those build curves equally. Research expenditure sums actual attempt
durations separately; it is never charged to a single hypothetical package.
Baseline case means are shared comparison evidence, not replicated independent
measurements. The frozen optional `resource_scenarios` field declares `horizons`
and `primary`. For historical studies without that field, the interpreter labels
1, 5, 20 and 50 uses (primary 20) as **post hoc default scenarios**.

Missing durations suppress complete means and curves instead of selecting
successful attempts. Observed sums remain visible and may be partial. Failed
builds retain all planned consumer zeros; infrastructure/context failures retain
missing scores. Incorrect or missing package/baseline work, failed packages,
unreconciled durations, mismatched coverage or unavailable/failed recorded catalog
acceptance suppress a qualified crossover. A correctly captured timeout can
qualify while retaining its native timeout status and observed overshoot. With
zero or negative per-use savings there is no finite positive crossover. Any
crossover is arithmetic extrapolation under the stated case mixture and
stationary time assumption, not an observed deployment or reliability claim.

Usage is recomputed from raw session captures and checked against the legacy
response-ID accounting. A response shared across recorded root/child files is
counted once; conflicting duplicates and cross-root response reuse are rejected.
Session parent IDs and response IDs remain inspectable. Root-inclusive totals
are not added to child/session totals. Cached input and reasoning output are
subsets, not extra token categories. Missing or malformed captures are explicitly
unavailable; unreported or aborted provider work can still be absent. Dollar cost
is unavailable. This interpreter checks recorded acceptance verdicts; it does
not replace the independent context and capture audits.

## Frozen scheduling

Native v2 and guided requests accept optional
`"scheduling": "case-repeat-blocks-v1"`. It requires a consumer baseline with
the same repeat count as package consumers. The existing algebra admits the
entire allocation before ordering. An absent or null option is omitted from
serialization and preserves legacy study/preparation identity inputs and plan
bytes. Trial identities and parent meanings do not depend on ordering.

[The scheduler](../src/yassa/native_scheduling.py) interleaves seeded build queues
by arm, then orders case/repeat blocks with a seeded hash. Each block includes
one use of every planned package and one shared baseline. It chooses seeded ring
rotations to reduce accumulated squared arm-position counts, and freezes actual
orders and balance counts. This is a deterministic balancing heuristic, not a
promise of globally optimal balance for every possible allocation. The proposed
six-build/twelve-block fixture has at most two counts of positional spread per
arm. Execution stays serial. Failed dependencies leave their planned slots
unlaunched, while baselines execute independently; the schedule is not rewritten.

## Timing boundaries

[Lifecycle records](../src/yassa/native_timing.py) use a controller monotonic clock
at public Inspect 0.3.263 boundaries. The actual installation and
[sandbox API](https://inspect.aisi.org.uk/sandboxing.html#exec) were verified
before implementation; `SandboxEnvironment.exec(timeout=..., timeout_retry=False)`
remains the native deadline boundary. [Inspect limits](https://inspect.aisi.org.uk/setting-limits.html)
do not establish hard token or spend enforcement for native CLI calls.

| Phase | Observed boundary |
| --- | --- |
| `evaluation` | Immediately around `inspect_ai.eval`; includes Inspect setup, teardown and logging |
| `adapter_setup` | Solver entry through input installation, permission probe and root catalog preflight |
| `native_command` | Existing `sandbox.exec` call start through return/cancellation |
| `capture_acceptance` | After native return through independent logs/output captures and root/child catalog acceptance |
| `sandbox_provisioning`, `sandbox_cleanup` | Explicitly unavailable: no separate adapter hook observes these framework-owned phases |

The evaluation duration encloses adapter phases; do not add them together.
Offsets, durations and completion/failure status are recorded in each attempt's
`lifecycle.json` and result. Unreached phases are unavailable. Setup, capture and
evaluation exceptions retain timing evidence; native duration and acceptance
semantics are unchanged. Controlled-clock tests cover success, deadline overshoot
and setup/capture/evaluation failures. These additions have **no new live
validation**. They do not measure first-correct-output time, full user latency,
or an enforced whole-session elapsed cap.

## Synthetic material recipe

Guided preparation accepts `material_recipe: "reconciliation-reuse-suite-v1"`
with `family: "reconciliation-v2"`, only the prepared route, and pinned
`historical_materials` file bindings. The new recipe retains the existing complete
contract and checker. It constructs three development examples and six held-out
inputs, two each for compact, interaction and bulk profiles, with equal case
weights. The bulk histories remain within the earlier roughly 400-row scale.
Only the complete contract and development examples enter builder contexts.

The [recipe](../src/yassa/reuse_materials.py) records deterministic per-case seeds,
authorship, shared ancestry, profile weights, lineage, exact file hashes and an
all-candidate selection ledger. Event histories and values are newly constructed;
changing seeds does not create independent briefs. All nine candidates are
retained before subject outcomes. Preparation authors see the validation cases.

Each candidate agrees with the independent Decimal/sort oracle before preparation
succeeds. Exact semantic identities ignore row ordering and equivalent repeats.
An additional conservative history fingerprint ignores event/account names to
reject renamed/reordered historical histories. It is a construction screen, not
a complete equivalence algorithm. Historical bundles under other contracts are
identified as different-contract comparisons; a comparable reconciliation-v2
bundle is required. Original historical bytes are pinned and copied into the
external preparation history. New bundles, probes and selection records also
remain outside the repository.

The existing hand-calculated tests and legitimate output alternatives remain.
Each preparation records the eleven faulty-solvers' exact outputs and verdicts;
observationally equivalent faults pass the relevant cases. Existing recipes,
supplied fixture bytes and checker identity remain unchanged.

## Separate launch review

The external review is under
`C:/Users/Darian/yassa-runs/package-reuse-efficiency-20260909-v1`.
It freezes the candidate material/source/runtime identities and records offline
validation. The proposed allocation is six builds, 72 package consumers and
12 baselines: **90 root attempts**, **11,160 native seconds**, with 600/90-second
deadlines and a primary hypothetical reuse scenario of 20. Horizons 1, 5 and 50
are additional scenarios. The 60-minute operational allowance is planning
headroom, not a cap. Model alias availability has not been tested with a new
authenticated request. No launch authorization record is created.

The previously audited 83-file Dovetail snapshot remains external and byte-pinned;
fresh verification precedes freezing. Its upstream commit remains unknown.
Common-request is not an explicitly invoked official-creator arm. No best-of
selection, replacement builds, retries, outcome-driven extension, general builder
ranking or equivalence claim is included. Exact root preflight, recorded
root/child postflight and independent captures remain acceptance gates; child
checks remain after execution. Original pilot failures, audits, scores and seals
remain historical facts.
