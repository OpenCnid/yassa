# Reconciliation sensitivity study

Prepared 2026-09-09 for **descriptive condition discovery**. The user reviewed and
approved the frozen 68-attempt allocation, and all attempts are complete. The
[authorization](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/execution-authorization.json)
and [console](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/launch-console.txt)
record this launch. All 60 consumers passed, and both offline audits passed.
New task rules and allocation are preparer-selected choices
within the authorized synthetic scope, not claims about real accounting practice.

The [first pilot](reconciliation-pilot.md#recorded-results) reached 46/46 passing
recorded consumers, including 10/10 no-package baselines. Its simple cases mostly
isolated individual summation and CSV features. Four planned uses remain missing
after an export failure, and its context audit remains **failed**. The separately
completed [native context diagnostic](native-context.md#verification-evidence)
passed. Neither completed allocation authorizes new attempts.

## Work selected and intended interpretation

The new `reconciliation-v2` checker extends the task to event histories and
per-case policy files. Earlier `reconciliation-v1` semantics, fixture pins,
results and audits remain intact. This is a new task condition; accuracy changes
relative to the pilot cannot be attributed to any one added rule, deadline or
runtime control.

| Rule | Declared behavior | Failure made observable |
| --- | --- | --- |
| Revisions | Greatest numeric revision per event ID, separately per side; equivalent repeats count once | Lexical sorting, summing history, deduplicating across sides |
| Voids and key changes | Select revision before filtering state or grouping; latest void removes the event | Resurrecting stale postings, retaining obsolete groups |
| Composite keys | Literal ID plus currency, preserving quotes, whitespace and Unicode | Normalization, splitting quoted CSV, merging currencies |
| Exact amounts | Convert signed decimals to integer minor units by the supplied scale, without rounding | Float precision loss, assuming cents for every currency |
| Presence and counts | Count retained events, keep zero sums; missing side has zero count | Counting CSV rows, dropping cancellations, treating zero as absence |
| Status | One-sided status takes precedence; otherwise absolute delta at or below tolerance matches | Ignoring one-sided zeros, strict or signed tolerance comparisons |

The complete contract is in [reconciliation.py](../src/yassa/reconciliation.py)
and the frozen review. Both builders and all consumers receive it; consumers
receive the current policy and both CSVs. Currency codes label synthetic
policies. No conversion or external currency conventions apply. Conflicting
repeated revisions and malformed inputs are preparation errors, not hidden
consumer requirements.

| Condition | Development | Held-out work |
| --- | ---: | --- |
| Supplied | 3 examples | 4 explicit cases: changed currency policies with revisions and exact amounts; void/rekey/cancellation interactions; literal CSV and large amounts; entirely voided histories |
| Prepared | 3 examples | 8 cases: revision order; void/rekey; currency precision; tolerance boundaries; presence/zero; literal CSV; combined rules; bulk interactions |

The prepared suite is `reconciliation-event-suite-v1`, seed 73029. Its bulk case
has 404 input rows across both CSVs, with unsorted histories, duplicate revisions,
voids and cancellations. The all-void supplied case is a simpler control. All
four authored cases and all eight generated scenarios are retained. No new model
outputs informed selection. The external preparation retains the authoring script.

The [supplied file](../studies/reconciliation-sensitivity-supplied.json) is
agent-authored synthetic material. “Supplied” describes its input route, not
human authorship. Conditions share rule families but have different examples
and case inputs. They are related constructed work, not independently sampled
briefs or a causal test of input preparation. More interactions and longer files
were selected to expose errors. The completed run nevertheless reached the
correctness ceiling, including every baseline. One baseline per case gives little
information about execution variance.

## Checker verification and access boundary

The generator computes candidates with streaming dictionaries and decimal-string
integer conversion. An independent oracle uses Decimal conversion, sorted
revision selection and per-key summation/filtering. Every reference must agree
before preparation or native freezing succeeds.

The checker accepts balance order, key order, whitespace and Unicode escape
alternatives. It rejects extra/duplicate fields, duplicate balance keys, missing
records, floats, numeric strings, booleans and incorrect values. The primary
score is binary complete-task correctness. Diagnostic components in `scores.json`
distinguish schema, keys, amounts, counts and statuses; they are not additional
independent outcomes or a partial-credit ranking. Malformed schemas have no
amount/count/status verdict; missing keys fail those whole-output components.

[Tests](../tests/test_reconciliation_v2.py) include hand-calculated references,
positive/negative tolerance boundaries, policy changes, void-only inputs,
conflicts, exact integer precision and semantic splits. Preparation records exact
work and verdicts for eleven deliberately faulty candidate solvers. Each fault
is detected by at least one prepared held-out case. Equivalent outputs on other
cases are recorded as passes, not falsely counted as detected faults. This checks
coverage of specified mistakes, not expected model error rates.

Development and evaluation have disjoint IDs/groups and unique semantic inputs.
Reordering and equivalent repeated-row spellings cannot bypass that check.
The controller retains held-out answers, generators, checkers and reviews.
Builders receive only the contract, development examples and declared builder
inputs. Consumers receive only current case files and their assigned package,
when applicable. Tests inspect these assembled inputs, baseline lineage and
relocated rescoring. Preparation authors can see all constructed cases; authoring
is not blinded. The native sandbox enforces the subject filesystem boundary.

The [catalog gate](native-context.md#enforced-boundary) and independent failure
captures are unchanged: root preflight precedes inference, and all recorded root
and child catalogs are checked at postflight before accepting outputs. **Child
checks occur after execution**, not before every model request. Per-request
interception is not a prerequisite for this milestone and is not claimed.

## Controls and concrete launch budget

Each condition has two `common-request` builds and two `dovetail` builds. The
latter uses the exact previously audited external runtime snapshot with explicit
creator invocation. The common request includes pinned built-ins and is not an
explicitly invoked official-creator arm. Every package gets one fresh use per
case. `no-package` gets one fresh execution per case with identical complete
facts, files, model and consumer deadline.

| Reservation | Attempts | Deadline each | Native command seconds |
| --- | ---: | ---: | ---: |
| Independent builds | 8 | 600 seconds | 4,800 |
| Package consumers | 48 | 90 seconds | 4,320 |
| No-package consumers | 12 | 90 seconds | 1,080 |
| Total | 68 | | 10,200 |

The 170-minute sum reserves native deadlines; setup/export is additional. It is
not an elapsed-time prediction. Builds retain the pilot's 600-second allowance.
Consumers get 90 seconds for added file-processing steps, common to assisted and
baseline uses. Hard token/spend ceilings and dollar estimates are unavailable.
Native children share their root's deadline and contribute to its recorded usage.

The selected runtime is Codex 0.153.4, GPT-6 Astra with `xhigh` reasoning, ordering
seed 260909 and immutable image
`sha256:e473d44f582bd20f07755a37c08907ba6b3250cc58068ca04d713ab7c9d36fe6`.
The model remains an alias. Dovetail's unchanged snapshot has 83 files and
1,576,341 bytes, artifact
`980068581a48610f08bf1a50c4be88cf0a37a02e7b7fc027397b31398f2a51eb`;
upstream commit unknown. It is resolved from sealed prior evidence, not the
current personal installation. No subject skill source enters this repository.

Whole-plan caps are exactly 68 attempts and 10,200 native seconds. No retries,
replacement builds, best-package selection, accuracy-based optional stopping or
post-outcome case additions are allocated. Operational failure can leave a run
incomplete; preserve it and separately review any later work. Failed builds give
planned uses zero; infrastructure failures and rejected context leave them
missing. Usable deadline outputs retain the timeout separately. Baselines still
run independently of builder success.

Report conditions separately, then independent-build counts and per-case package
uses, and baseline counts with null build/parent lineage. The 48 package uses do
not become 48 independent builder observations; 12 baselines are not builds.
Inspect paired cases, diagnostic components, missingness, saturation and resource
use. No significance test, population effect, equivalence conclusion or general
builder ranking is planned. A further ceiling or floor is a result to report,
not permission to extend this allocation.

## Frozen preparation and authorized launch

The portable [request](../studies/reconciliation-sensitivity-request.json)
remains pending until the external source is pinned. Local preparation at
`C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1` resolves that
binding and retains source answers, authorship, originals, checker probes and
implementation snapshots outside the checkout:

- [Ready review](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/round-1/review.md)
  and [verification](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/round-1/validation.json).
- [Frozen plan](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/run/plan.json)
  and [launch review](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/launch-review.md).
- [Offline compatibility](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/compatibility.json)
  and [verification report](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/verification.md).

The preparation artifacts remain the historical prelaunch record. The subsequent
authorization applied to this exact completed allocation. `native-execute` checks
frozen implementation, dependencies and runtime files; changes require a new
freeze, never editing this one. Do not restart this run or relaunch the completed
pilot or diagnostic.

## Recorded results

The approved command exited successfully on 2026-09-09, after 134.54 minutes of
elapsed time including setup, export, sealing and original reporting. All 68
attempts launched once: eight accepted packages, 48 package uses and 12 baselines.
Native commands used 6,198.559 seconds (103.31 minutes) of the 10,200-second
reservation. No retries, replacements or added cases ran.

The [original report](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/run/interpretations/original/report.md)
records the following complete-task scores:

| Condition | Common-request package uses | Dovetail package uses | No-package baselines | Missing |
| --- | ---: | ---: | ---: | ---: |
| Supplied | 8/8 | 8/8 | 4/4 | 0 |
| Prepared | 16/16 | 16/16 | 8/8 | 0 |

Each independent build's package passed every assigned case: 4/4 per supplied
build and 8/8 per prepared build. All diagnostic score components passed. The
prepared Dovetail build `build-430fb1d7f0ab1b262031` reached its 600-second deadline
but produced an accepted package. The prepared bulk baseline
`consume-99e9a550c477f51249ff` reached its 90-second deadline with a correct captured
output. Their native timeout statuses remain separate from correctness.

The runner's catalog checks passed for all 68 attempts and 75 recorded sessions:
68 roots and seven children, all GPT-6 Astra with `xhigh` reasoning. Offline seal
verification and the separate general and capture audits passed with no violations
or evidence gaps. Repeat scoring reproduced the original score bytes exactly.
The audit replays expected catalogs from pinned inputs and verifies raw captures,
normalized artifacts, common inputs, package lineage, modes, settings and recorded
skill reads. Child catalog checks still occur after execution, not per request.

Mean native command time per consumer was 36.97 seconds for common-request
packages, 28.78 for Dovetail packages and 61.66 for no-package baselines across
these fixed cases. Build native time totaled 26.66 and 38.02 minutes, respectively;
it is separate from consumer means. These descriptive resource observations do
not estimate future latency or billing cost. Recorded usage spans 354 response
records: 6,005,304 input tokens (5,011,584 cached) and 188,920 output tokens,
including native child work. Aborted or unreported usage can remain unavailable.

The [result assessment](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/results.md)
links exact per-case, per-build, deadline, resource and audit records. The run seal
is `a1f83c9ac4e5e3c2abc73680f22f3ac696ff87b9c54e2c7e3f0a791b29a02282`.
[Historical verification](C:/Users/Darian/yassa-runs/reconciliation-sensitivity-20260909-v1/history-after-launch.json)
confirmed unchanged prior run seals, original scores, pilot failed audits and
the diagnostic check. No historical result was replaced.

The new interactions did not produce correctness failures at the selected model
and deadlines. This is another observed score ceiling, including unassisted
consumers. It does not establish builder equivalence, package benefit, a general
ranking or a causal preparation-route effect. The resource record and deadline
outcomes remain useful descriptive evidence. Further study design needs a new
review; this completed allocation is not authorization to add harder cases.
