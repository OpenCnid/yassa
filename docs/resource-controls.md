# Resource controls and recovery

This milestone advances **Y08, Y09 and Y10** through supported CLI operations.
New simulated fixtures, native v1/v2 studies, direct and artifact studies, and
external grading runs record durable controller state. Model-assisted preparation can charge the
same resource ledger. Existing study definitions, task scoring, protected context
and adapter deadlines retain their semantics.

The full product remains incomplete. This implementation provides conservative
launch admission and local recovery. It does not add native hard token/spend caps,
automatic recovery of legacy interrupted runs, or same-directory preparation
resume. Native cancellation/restart has adapter-double tests; authenticated native
process validation is still separate from these software checks.

## Shared resource budget

Create an external ledger once and supply it to every operation whose expenditure
should share that allocation. The following **illustrative** bounds are not an
experimental allocation or product defaults:

```powershell
$resources = Join-Path $env:USERPROFILE 'yassa-runs/example-resources'
uv run --locked yassa resource-init $resources --max-attempts 20 --max-scheduled-seconds 2400
uv run --locked yassa resource-status $resources

uv run --locked yassa study-draft REQUEST.json --draft-dir DRAFT_DIRECTORY --resources $resources
uv run --locked yassa native-execute RUN_DIRECTORY --auth-file AUTH_FILE --resources $resources
uv run --locked yassa grade-execute GRADE_DIRECTORY --resources $resources
```

`--resources` is also accepted by `study-revise`, `execute`, `run`, `native-run`
and `direct-execute`, as well as `artifact-execute` for
[artifact reconstruction](artifact-studies.md). Native grading and preparation retain their existing
`--auth-file` requirements. Credentials and their values are not put in the ledger.
Recipe preparation has no model calls to charge. Imported prior preparation
evidence is not charged again merely because another run references it.

The ledger enforces two limits under an OS file lock:

| Limit | Admission and enforcement |
| --- | --- |
| `max_attempts` | Reserve one root attempt before invoking an adapter, including each explicit retry. Native internal agents belong to that root; this is not a cap on native model calls. |
| `max_scheduled_seconds` | Reserve the full declared attempt deadline before launch. The sum of reservations cannot exceed the ledger limit. Existing Inspect/API/native deadline enforcement controls the attempt itself. |

Reservations are **not refunded** after early completion, a failed call, a crash
or uncertain execution. They are conservative allocation units, not measured
elapsed time. In-flight work therefore cannot disappear from admission arithmetic.
This policy may stop a study even when actual reported time is below the ceiling.
Frozen per-study admission limits still apply; the shared budget can stop work
earlier, and never silently reduces an attempt's selected deadline.

Native command deadlines exclude Docker setup, permission/catalog probes, capture
and export. API records contain elapsed call time; Claude grading also records
native command time separately. The ledger retains each duration's scope. It does
not promise a hard bound on total research wall time, provider spend, input tokens
or native output tokens. API output limits retain the adapter's configured
`max_output_tokens`. Unknown hard-cap fields are rejected by the budget schema.

`resource-status` returns the pinned configuration, remaining reservations,
per-role counts and reported durations, and every root's raw usage/outcome. Roles
include preparation, build, consume/consumer, direct, artifact-build, calibration
and grading.
Native usage deduplicates response IDs within each root and includes recorded
children; child totals are not added again. Failed attempts and schema-invalid
preparation calls retain their charges. Missing durations, usage and spend remain
explicit. Recorded partial duration sums do not establish complete expenditure.

The ledger is an explicit external input. Resuming a run requires the same ledger
identity and limits, including after relocation. A separate ledger cannot replace
an exhausted allocation on resume. Local locks cover each active run and shared
reservations; copies with stale evidence cannot silently reuse a spent reservation.
These are local filesystem controls, not a distributed execution service.

## Cancellation and partial reports

```powershell
uv run --locked yassa cancel RUN_DIRECTORY --reason "Stop this allocation"
uv run --locked yassa run-status RUN_DIRECTORY
uv run --locked yassa run-report RUN_DIRECTORY
```

Cancellation is cooperative: it stops new launches and lets an already active
bounded adapter call finish, time out and capture available evidence. It does not
immediately terminate Docker or a provider request. A request is checked before
every launch and before final sealing. If execution has already sealed, cancellation
is rejected and offline reporting remains available.

`run-status` reads a started managed run. `run-report` writes a new interpretation
with all planned trials, launched attempts, retry lineage and available resources.
Partial reports identify unlaunched and uncertain work; they do not turn an
execution completion into a correctness score. Final native/direct/grading reports
link to the sealed controller summary, which retains superseded attempts as well
as the selected returns. Existing score denominators remain unchanged.

Execute commands print the report path and return **exit code 3** when paused by
cancellation, exhaustion, a retry decision or uncertainty. Ordinary successful
execution returns 0; invalid inputs return 2. An incomplete run remains unsealed,
and `verify`/scoring cannot treat it as a complete study. `run-report` remains
available for an exhausted allocation without making additional model calls.

Ctrl+C can interrupt Inspect during capture or cleanup. Available logs remain,
but the absence of a durable return makes the launch uncertain. A killed process
may leave a native container or remote request requiring external cleanup. The
controller does not infer that a provider did no work merely because it died.

## Resume, retry and uncertain work

Use the original execute command, with the same authentication where needed:

```powershell
uv run --locked yassa native-execute RUN_DIRECTORY --auth-file AUTH_FILE --resources $resources --resume
uv run --locked yassa direct-execute DIRECT_DIRECTORY --resources $resources --resume
uv run --locked yassa grade-execute GRADE_DIRECTORY --resources $resources --resume
```

Resume verifies frozen inputs, procedure/runtime identity, reconstructed bindings,
committed output artifacts and log bytes before reusing work. Stable bindings
exclude Inspect's newly generated local message IDs while retaining actual message
content and settings. A completed builder's package is reconstructed from its
recorded output, with the same hash and downstream parent. Completed wrong answers
are reused as recorded; resume provides no extra answer attempt.

If the adapter wrote `result.json` before the controller died, recovery can commit
that return and reconcile its available Inspect logs and artifacts. Partial Inspect
logs alone do not establish a completed return. A launch without a verifiable return
pauses recovery. Choose an explicit disposition using the logical ID printed by
the report:

```powershell
# Keep uncertain execution in the missing denominator and continue other work.
uv run --locked yassa direct-execute RUN_DIRECTORY --resources $resources --resume --mark-missing LOGICAL_ID --reason "Process ended without a committed return"
```

The disposition preserves partial logs and adds a controller record; it does not
invent an adapter response. Consumers of an uncertain failed build remain missing,
with no fabricated consumer launch. Ordinary task/build failures keep the original
failure-denominator policy.

Explicit infrastructure retries require an allowance recorded **at first
execution** and an explicit shared resource ledger with room for the added work:

```powershell
uv run --locked yassa direct-execute RUN_DIRECTORY --resources $resources --infrastructure-retries 1
# After an eligible failure pauses this run:
uv run --locked yassa direct-execute RUN_DIRECTORY --resources $resources --resume --retry LOGICAL_ID --reason "Recorded provider outage"
```

An allowance is not an automatic retry. Plain `--resume` retains an already
recorded infrastructure failure and continues; `--retry` creates a new directory
and attempt ID linked by `retry_of`. Wrong answers, refusals, malformed grades and
deadline outcomes cannot be retried through this infrastructure policy. The
allowance cannot be raised on resume. Grading calibration must still pass before
source work is released. Original failed calibration calls and all retry resources
remain visible. The legacy simulated fixture keeps its own declared automatic
infrastructure policy; it does not accept an additional controller retry allowance.

Completed result selections and run seals cannot be reopened for retries. If a
crash occurs after sealing but before reporting, use the appropriate offline
rescore/report command with a new interpretation label. Changed code or dependencies
require a new execution freeze. Old sealed runs remain readable; interrupted runs
that predate controller records require separate reconciliation and cannot simply
be adopted by `--resume`.

Preparation retains its existing immutable draft/revision workflow. Shared resource
charges survive failures, but a hard-interrupted preparation directory has no
same-directory resume or `cancel` command in this milestone. Preserve it and create
a new draft from the original request, using the remaining shared allocation if
applicable. This remains a Y09 gap. Reuse-efficiency curves also lack a declared
retry/uncertainty cost allocation; `native-resources` rejects those histories and
directs users to operational resource reports.

## Evidence and verification

[control.py](../src/yassa/control.py) owns run locks, launch admission, cancellation
requests, reconciliation and operational reports. `control/run.json` binds the
initial execution policy and ledger to the preparation freeze. Each physical
attempt has a durable launch and separate completion; returns retain artifact and
file hashes. Session records retain explicit resume/retry/missing decisions.

Control-channel requests and the lock file are excluded from the run seal; handled
or acknowledged requests are copied into immutable cancellation evidence before
continuation. Final controller summaries, launches, completions and session records
are sealed. Interpretation directories keep their existing exclusion. Atomic
write publication prevents a process crash from exposing a partially written
authoritative JSON file; artifact bundles are staged before publication. Orphaned
pending bytes are retained. Hashes are integrity checks, not protection against a
privileged actor replacing all evidence. Network filesystems and machine power-loss
durability are not claimed as validated.

The implementation uses installed Inspect **0.3.263**, checked against its
[limits](https://inspect.aisi.org.uk/setting-limits.html) and
[eval-set recovery documentation](https://inspect.aisi.org.uk/eval-sets.html).
Inspect continues to own samples, deadlines, logs and sandbox lifecycle. Yassa
owns cross-role reservation and build/consumer selection; it does not call eval-set
retry machinery that could repeat completed study work without this policy.

Behavioral checks are in [test_control.py](../tests/test_control.py),
[test_control_roles.py](../tests/test_control_roles.py) and
[test_control_process.py](../tests/test_control_process.py). They cover in-flight
exhaustion, cancellation, OS lock release on process death, uncertain dispositions,
linked retries, refusal to retry completed work, binding/evidence changes, native
package reuse, direct/grade CLI composition, preparation charges, relocation and
offline scoring. The process test executes the real fixture CLI with actual Inspect
and its explicitly simulated provider, then cancels, kills and restarts the process.
It makes no live model calls. Final executed check results are recorded in
[the handoff](../HANDOFF.md#resource-and-recovery-milestone).
