# Development handoff

Updated 2026-09-08 after the bounded guided preparation implementation.
The full spec is not implemented. The next recommended milestone is to develop
an informative pilot's work, controls and budget for its question, extending
preparation/checker semantics where that work needs it. Follow the current user's
request if it changes that direction.

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

Inspect the current checkout and tools before choosing commands. This is a dated
handoff, not evidence that a path, installed tool, or account connection is still
available in a later environment. Requirements stay in SPEC and technical design
in ARCHITECTURE; update those documents as implementation advances.

## Checkout and evidence

The implementation and this handoff advance together. Begin from the revision
containing this milestone or a later default-branch revision. Inspect
`git status --short` and preserve additional local changes before beginning work.

The original development workspace was
`C:/Users/Darian/.codex/worktrees/68a6/yassa`, based on `95666e2`
(`Merge pull request #1 from OpenCnid/codex/yassa-design-docs`). That base commit
predates the implementation. The source checkout is portable; the external
evidence and installed source pack described below are local to this machine.

The original kickoff document has been retired in favor of this handoff.
No experiment or helper container from this work remains running. Completed
evidence is outside the repository. There is no unfinished live run to resume.

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

## Next recommended implementation milestone

**Completion target:** choose an informative pilot for the intended comparison,
with explicit work coverage, controls, independent builds, resources and limits
on interpretation, then run and audit it under the user's chosen scope.

1. Use SPEC sections 3, 7 and 13 to establish what the result should inform. A
   descriptive trial can be complete; broader claims need an appropriate design.
2. Assess whether the two supported task families fit. Extend semantic contracts
   and preparation deliberately when they do not; do not recast a user's work as
   the nearest fixture. Arbitrary natural-language task synthesis remains open.
3. Choose and pin external builder sources and any adaptations. Verify their
   native capabilities before using a study to compare their outcomes.
4. Preserve both preparation routes for the first Dovetail study. The draft's
   `first_dovetail_study` flag enforces this commitment; future trials may select
   one route. Source authorship and preparation route remain separate facts.
5. Select controls and resources for the question. The native runner currently
   measures builder treatments with package consumers; a consumer control without
   a package requires an explicit runner extension. Execute only once the study
   and its resources are concrete and authorized, then preserve and audit evidence.

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
| Review/material byte pins and portable provenance | [preparation_evidence.py](src/yassa/preparation_evidence.py) |
| Native version dispatch and legacy fixture | [native.py](src/yassa/native.py) |
| Native v2 schemas, preparation, allocation | [native_contracts.py](src/yassa/native_contracts.py) |
| Native v2 freezing, execution, reporting | [native_runner.py](src/yassa/native_runner.py) |
| Versioned file-task checkers | [native_checkers.py](src/yassa/native_checkers.py) |
| Native Inspect execution boundary | [native_execution.py](src/yassa/native_execution.py) |
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
  config, rules, apps, or MCP connections are imported. Preserve this boundary.
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

Current application verification: **130 tests passed, 1 skipped** in the full
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
