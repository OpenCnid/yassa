# Development handoff

Updated 2026-09-08 after the configurable native v2 implementation.
The full spec is not implemented. The next recommended milestone is broader
study preparation into the shared native definition, followed by a pilot whose
work, controls, and budget are chosen for its question. Follow the current user's
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

Inspect the current checkout and tools before choosing commands. This is a dated
handoff, not evidence that a path, installed tool, or account connection is still
available in a later environment. Requirements stay in SPEC and technical design
in ARCHITECTURE; update those documents as implementation advances.

## Checkout and evidence

The implementation and this handoff are delivered together in the fixture
milestone. Begin from the commit containing this file or a later revision of the
default branch. Inspect `git status --short` and preserve any additional local
changes before beginning new work.

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
Yassa-prepared materials still use seeded deterministic fixture generators; the
intake helper does not synthesize general studies from natural language.

## Next recommended implementation milestone

**Completion target:** a rough user request can be developed into a validated,
reviewable native v2 study, with task facts, invented assumptions, development
examples, held-out materials, checker verification, controls, and budget made
explicit. The expert file-definition path and guided preparation should converge
on the existing contracts and runner.

Develop a short concrete implementation plan, then carry it through code and
verification. A bounded sequence is:

1. Define a bounded preparation interaction using SPEC section 3. Distinguish
   supplied facts, proposals, invented rules, and unresolved correctness choices.
2. Produce the existing `NativeStudyV2` and `FileMaterials` contracts. Extend their
   limits deliberately when required; avoid a separate execution pipeline.
3. Verify prepared references and splits with versioned checkers. The generic
   exact-JSON checker does not independently establish semantic correctness.
4. Preserve source originals, preparation records, assumptions, and both routes
   in the first Dovetail study. Future user studies may select one route.
5. Validate the preparation experience before choosing representative pilot work,
   controls, independent builds, and resources. Preserve old evidence/readers.

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
| Native version dispatch and legacy fixture | [native.py](src/yassa/native.py) |
| Native v2 schemas, preparation, allocation | [native_contracts.py](src/yassa/native_contracts.py) |
| Native v2 freezing, execution, reporting | [native_runner.py](src/yassa/native_runner.py) |
| Versioned file-task checkers | [native_checkers.py](src/yassa/native_checkers.py) |
| Native Inspect execution boundary | [native_execution.py](src/yassa/native_execution.py) |
| Evidence and deterministic checking | [evidence.py](src/yassa/evidence.py), [scoring.py](src/yassa/scoring.py) |
| Container and access profile | [Dockerfile](runtime/codex/Dockerfile), [config.toml](runtime/codex/config.toml), [boundary probe](runtime/codex/boundary_probe.py) |
| Regression evidence | [tests](tests), [legacy auditor](tests/audit_native_run.py), [v2 auditor](tests/audit_native_v2_run.py) |

Start preparation work from `NativeStudyV2`, `TaskContract`, `FileMaterials`,
`prepare_files`, and `validate_materials`. The simulated schema and legacy native
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

Current application verification: **102 tests passed, 1 skipped**, Ruff checks
and formatting passed, wheel and source distribution built, and native modules
and runtime resources in the wheel matched their source bytes. Windows cannot
create the symlink used by the skipped collector test; the same rejection check
passed in the pinned Linux container. A local documentation check resolved
affected links/anchors. Both original v1 runs still verify; their
`native-v2-compatibility` interpretations preserve all original score rows.

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
