# Guided native study preparation

This page describes version 1 preparation requests and the original recipe path.
Version 2 requests add [general model-assisted preparation](general-preparation.md)
for user-described JSON work, with the same native study/export commands.

`study-draft` and `study-revise` develop a rough request into a reviewable native
v2 study without subject or preparation model calls. This bounded implementation
supports account totals, simple reconciliation and event reconciliation with a
per-case policy file. It retains free-text facts
and decisions, asks at most two readiness questions per round, constructs missing
synthetic examples and cases, and verifies references, checkers, splits, sources,
and allocation. A complete request produces a study immediately.

This is a deterministic preparation interaction with JSON answers. It does not
interpret arbitrary natural language into business rules, research datasets, or
invent new semantic checkers. An assistant or expert caller can translate the
user's answers into its explicit fields. The expert native file-definition path
remains available for other tasks, including author-verified exact JSON.

## Prepare and revise

From the checkout, with the [locked environment](../README.md#run-the-fixture):

```powershell
$draftRoot = Join-Path $env:USERPROFILE 'yassa-runs/preparation-example'
uv run --locked yassa study-draft studies/preparation-request.json --draft-dir "$draftRoot/round-0"
uv run --locked yassa study-revise "$draftRoot/round-0" studies/preparation-answers.json --draft-dir "$draftRoot/round-1"
```

The first command returns `review.md`, showing two questions and available task
contracts. The second uses [example answers](../studies/preparation-answers.json)
to exercise both preparation routes. These answers reserve 6 builds and 48 uses:
54 attempts and 1,800 native command seconds. Their model, deadlines and allocation
are implementation examples, not pilot recommendations. They compare a common
request with an instruction treatment; they are not a Dovetail comparison.

Each destination must be new and outside any Git/source repository. Answers
replace top-level fields; an `arms`, `sources`, `admission`, or `supplied` answer
replaces that entire value. Omitted fields retain the previous choice. Use `null`
to clear optional scalar choices and `[]` to resolve recorded open lists.
Paths in newly supplied answers resolve from that answer file's directory.
Inherited supplied materials use preserved copies from the previous draft, so
removing the original source or relocating a draft does not lose those bytes.
External subject packs remain external and must still match their declared pins.

Read `review.md` in each round. `draft.json` exposes `status`, up to two
`questions`, and all `remaining_fields` for an integrating client. A pending draft
has no `study.json`. A ready draft includes the native definition, review,
materials, verification, exact originals and answers, normalized round states,
preparer/checker source snapshots, and a pinned preparation manifest. Invalid
references, source hashes or over-budget allocations fail before creating a new
draft; prior rounds remain intact. An interrupted unsealed write is incomplete.

## Decisions and correctness

The minimum initial input is `{"request": "the work and comparison you want"}`.
The [StudyDraft schema](../src/yassa/guided_preparation.py) defines the fields:

| Fields | Meaning |
| --- | --- |
| `request`, `intended_use` | Original comparison and the decision/work it should inform |
| `family`, `scope` | Supported semantic contract; invented scenarios or user-defined work |
| `accepted_contract_sha256` | Explicit correctness choice tied to the complete displayed rules |
| `facts`, `inferences`, `assumptions` | Separately recorded statements; free text does not alter checker semantics |
| `proposals`, `unresolved` | Open choices that prevent a runnable export until resolved |
| `evidence` | Descriptive by default; a broader comparison is left unresolved rather than silently downgraded |
| `routes`, `supplied`, `first_dovetail_study` | Selected preparation conditions, original file pins, and the first-study requirement for both routes |
| `features`, `seed` | Synthetic scenario selection and reproducible generation |
| `sources`, `arms`, `control_rationale` | Existing pinned source/arm contracts plus the interpretation of each arm |
| `consumer_baseline` | Optional distinct control ID and fresh repeats per case without a generated package; its rationale is required |
| `model`, `reasoning_effort` | Explicit subject configuration; no model is silently selected |
| `consumer_repeats`, `schedule_seed`, `admission` | Explicit execution allocation, ordering and limits |

The full contract and its hash appear in the review. Selecting a family alone
does not accept its rules. Record the hash only once the contract resolves the
task's correctness choices; changing families invalidates an earlier acceptance.
Free-text facts that contradict the contract need resolution by the caller.
Yassa does not claim to detect semantic contradictions in those statements.
Choosing synthetic scope also does not silently clear open questions.

Routine initial choices are a descriptive trial, prepared inputs, and all declared
features of the selected template. The review identifies them; callers can
override them. Build counts, deadlines, model and seeds are explicit choices.
Supplied-only studies need no generation seed. Every arm needs a rationale;
one arm can describe its own outcome without establishing a comparative effect.
The runner measures builder treatments and generated-package use, with an
optional [consumer baseline](configurable-native.md#consumer-baseline) given the
complete task facts. Automatic activation remains unimplemented.
The [reconciliation pilot](reconciliation-pilot.md) exercises this preparation
path with both routes and explicitly selected controls and resources.

## Case construction and checking

The versioned `guided-file-suite-v1` recipe constructs two development examples
and one held-out case for each selected feature:

| Family | Features |
| --- | --- |
| `account-totals-v1` | `normalization`, `signed-amounts`, `cancellation`, `duplicates`, `empty`, `integer-bounds` |
| `reconciliation-v1` | `duplicates`, `identifiers`, `one-sided`, `cancellation`, `empty`, `csv-quoting` |

These are constructed scenarios, not independently sampled briefs, domains, or
a representative workload. The seed controls generated amounts; feature choices
control behaviors. All selected cases are retained, with no outcome-based
selection. The original v1 generators and existing v2 examples are unchanged.

The separate `reconciliation-event-suite-v1` recipe for `reconciliation-v2`
constructs three development examples and eight selectable scenarios: revision
order, void/rekey, currency precision, tolerance boundaries, presence/zero, literal
CSV, combined rules and bulk interactions. See the
[post-ceiling preparation](reconciliation-sensitivity.md) for its task choices,
eleven faulty-solver probes and frozen allocation. Verification for this recipe
also preserves each probe's exact output text and per-case fault detection.

Both routes produce `FileMaterials`. Validation recomputes every reference using
the independent versioned oracle, checks disjoint IDs/groups and unique semantic
inputs, and probes checker acceptance of order/whitespace alternatives and
rejection of wrong values, booleans, missing/duplicate records and extra fields.
Empty references have an invented-record rejection probe. The verification record
stores each probe's output hash and expected/observed verdict, checker identity,
preparer source hashes, seed, selection, and the exact plan arithmetic.

The guided route excludes `json-exact-v1`: accepting a supplied answer's JSON
representation cannot independently establish semantic correctness. The existing
expert route retains that narrower, disclosed capability.

## Freeze and execute with the existing runner

After inspecting a ready review, use the existing native commands:

```powershell
$nativeImage = docker image inspect yassa-codex:0.153.4 --format '{{.Id}}'
$runDirectory = Join-Path $env:USERPROFILE 'yassa-runs/reviewed-native-example'
uv run --locked yassa native-prepare "$draftRoot/round-1/study.json" --run-dir $runDirectory --image $nativeImage
$codexAuth = Join-Path $env:USERPROFILE '.codex/auth.json'
uv run --locked yassa native-execute $runDirectory --auth-file $codexAuth
```

The exported native v2 definition adds an optional `preparation` file/hash binding.
Generated conditions use `reviewed-files-v1` with a pinned `materials` file/hash,
request, seed and case count. Their route remains `yassa-prepared`; supplied
originals retain `user-supplied`. No second execution pipeline is involved.

Native freezing verifies the preparation manifest against the effective study,
all evidence hashes and current checker identity before inspecting Docker. It
also revalidates materials and admission. Changes to a reviewed study require a
new draft revision; editing its exported JSON leaves the old review inapplicable.
The manifest and all declared preparation records enter the sealed run as an
artifact. Native reports link to the review and originals. Preparation histories,
protected cases and verification evidence do not enter subject contexts.

Old definitions need no preparation binding. Old sealed evidence remains readable
and rescorable, with unchanged checker source identities. A future change to
checker semantics must use the existing correction/rescoring policy.

## Verification evidence

The preparation tests exercise rough and complete requests, explicit rule choices,
both routes and supplied-only work, exact original bytes, revision and relocation,
checker calibration, case coverage, admission, evidence tampering and native
adapter composition. The adapter integration supplies deterministic recorded
outputs without model calls; it checks contexts, 48 consumer score rows, both
conditions, the report link and byte-identical relocated rescoring.

The final milestone check results and remaining work are recorded in
[HANDOFF.md](../HANDOFF.md#verification-and-delivery). No new live native trial
or Dovetail ranking is claimed by these tests. The Inspect sandbox/CLI adapter
is unchanged; its previous live evidence remains in the
[v2 guide](configurable-native.md#verification-evidence).
