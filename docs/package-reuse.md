# Package reuse milestone

Implemented offline on 2026-09-09 from the [proposal](package-reuse-proposal.md),
then separately authorized and executed against the exact frozen launch review.
All 90 attempts completed; all six packages were accepted and all 84 consumers
passed, including 12 baselines. Repeat scoring and all three evidence/timing
audits passed. [Recorded results](#recorded-results) describe this narrow synthetic
comparison. The completed allocation is consumed; no further attempts or merge
are authorized by this document.

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
promise of globally optimal balance for every possible allocation. The executed
six-build/twelve-block fixture achieved at most one count of positional spread
per arm. Execution stays serial. Failed dependencies leave their planned slots
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
and setup/capture/evaluation failures. The separately authorized run validated
the recorded live phase contract across 90 roots, including five native
deadlines. It does not measure first-correct-output time, full user latency,
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

## Frozen launch review

The [original review](C:/Users/Darian/yassa-runs/package-reuse-efficiency-20260909-v1/launch-review.md) freezes six builds, 72 package consumers and
12 baselines: 90 root attempts and 11,160 reserved native seconds, with 600/90-second
deadlines. H=20 is primary; 1, 5 and 50 are additional arithmetic scenarios.
The 60-minute operational allowance is planning headroom, not a hard cap.
The user subsequently authorized one execution of this exact freeze. A
byte-identical copy ran in a new external directory, preserving the original
review seal and unexecuted candidate. No retries, replacements or extensions ran.

The verified external 83-file Dovetail snapshot remains byte-pinned; its upstream
commit is unknown. Model alias `gpt-6-astra` with xhigh is not an immutable weight
pin. Codex 0.153.4, Inspect 0.3.263 and the reviewed immutable Docker image were
retained. Common-request is not an explicitly invoked official-creator arm.
Exact root preflight, recorded root/child postflight and independent captures
remain acceptance gates. Child checks occur after execution.

## Recorded results

The [complete external assessment](C:/Users/Darian/yassa-runs/package-reuse-execution-20260909-v1/results.md) links authorization, exact
identities, original/audited scores, every attempt, audit sources and machine-
readable resource curves. Run seal: `964e058c04594cebb56249b22aec4558d4c1074b6f9698d0e8d5cca4db525769`.

| Arm | Passed consumers | Missing | Accepted builds | Native consumer timeouts |
| --- | ---: | ---: | ---: | ---: |
| common-request | 36/36 | 0 | 3/3 | 0 |
| dovetail | 36/36 | 0 | 3/3 | 0 |
| no-package | 12/12 | 0 | null | 5 |

Native command time was **7,545.795 seconds (125.76 minutes)**. Launch
elapsed through original reporting was **165.16 minutes**. All six builds
finished within their deadlines. Five baselines reached 90 seconds with usable
correct outputs; their observed overshoot and timeout status remain recorded.

The primary comparison charges one build plus 20 times that build's equal-case
mean use time. It averages repeats within case, six cases equally within build,
then the three builds equally within arm. The 12 baseline executions are shared
comparison evidence; they have zero build cost and null build/parent lineage.

| Package arm | H=20 mean native seconds | Range across three builds | Shared baseline H=20 seconds | Difference from baseline |
| --- | ---: | --- | ---: | ---: |
| common-request | 1,449.25 | 1,408.03–1,477.15 | 1,652.99 | -203.74 |
| dovetail | 1,515.03 | 1,484.72–1,540.17 | 1,652.99 | -137.97 |

All six build curves meet the recorded correctness, coverage and audit gates.
Additional H=1/5/50 scenarios and each build's crossover are in the assessment.
These are descriptive extrapolations of the configured budgeted protocol, not
observed deployments at every horizon or uncapped session completion times.
Research expenditure includes all actual builds and uses separately. Recorded
token totals may omit aborted/unreported work; no dollar-cost metric is inferred.

General evidence, raw-capture/catalog and live schedule/lifecycle audits passed
without violations or evidence gaps. Repeat score bytes are identical; an
independent arithmetic check verifies case/build weights and every curve.
The original review's 289 files, six historical run seals, original scores,
failed pilot audits and read-only proposal files reverified unchanged.

This is another observed correctness ceiling on one synthetic brief and six
related cases. It does not establish equivalent reliability or a general builder
ranking. Retained ordinary scripts and instruction/code ablations were outside
the comparison, so these results do not isolate skill packaging. The broader
multi-domain and explicitly invoked official-builder study remains unimplemented.
