# Development handoff

Updated 2026-09-08 after the simulated and native Codex fixture milestones.
The full spec is not implemented. The next recommended milestone is a configurable
native study runner, followed by broader study preparation and a more informative
pilot. Follow the current user's request if it changes that direction.

## Begin here

Read [AGENTS.md](AGENTS.md) and [README.md](README.md), then:

- [SPEC next work](SPEC.md#15-next-work) for completed and outstanding scope.
- [Architecture: implemented native fixture](ARCHITECTURE.md#implemented-native-codex-fixture)
  and [remaining decisions](ARCHITECTURE.md#open-implementation-decisions).
- [Native milestone evidence](docs/native-fixture.md) for the actual experiment,
  source selection, limitations, and recorded corrections.

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

Native support is deliberately narrow: one account-totals contract, two fixed
builder arms, one build per arm/condition, and one consumer per case. The
Yassa-prepared route is a seeded deterministic fixture generator. The intake
helper does not yet synthesize general studies from natural language.

## Next recommended implementation milestone

**Completion target:** a new task brief, materials, checker, comparison groups,
and build allocation can run through the native path without editing its Python
orchestration for that particular study.

Develop a short concrete implementation plan, then carry it through code and
verification. A bounded sequence is:

1. Define versioned task/evidence contracts and native study configuration. Move
   task-specific prompts, input/output locations, package naming, and checker
   selection out of the fixed native orchestration. Keep protected scoring data
   separate from subject-visible inputs.
2. Make builder arms, source bindings, independent build counts, consumer repeats,
   and attempt admission configurable. Reuse the existing planning and evidence
   responsibilities where appropriate; keep Inspect responsible for execution.
3. Exercise the common path with account totals and a second deterministic
   file-processing task, such as reconciliation or joins. The second task is a
   proposed implementation check, not a selected substantive benchmark.
4. Keep supplied and prepared materials traceable through the same definition.
   Preserve both routes in the first Dovetail study; future user studies need not
   always include both. General preparation from a rough request should feed
   this shared definition rather than a separate execution pipeline.
5. Verify isolation, byte-identical common inputs, lineage across multiple builds,
   file/package boundaries, failure accounting, and deterministic rescoring.
   Existing recorded runs must remain verifiable and rescorable; introduce format
   changes explicitly and preserve the legacy readers needed for old evidence.

After this milestone, choose a pilot's work, controls, independent builds, and
budget for its actual question. The previous small comparison is complete; its
case count and deadlines are not defaults for that pilot. Broader preparation,
resource controls, recovery, additional vendor runtimes, inferential analysis,
and different-family model grading remain outstanding spec work. Some details
are still proposals, not settled product requirements.

## Code entry points

| Area | Start here |
| --- | --- |
| CLI and simulated composition | [app.py](src/yassa/app.py) |
| Schemas, preparation, planning | [study.py](src/yassa/study.py), [prepare.py](src/yassa/prepare.py), [planning.py](src/yassa/planning.py) |
| Fixed native study and reporting | [native.py](src/yassa/native.py) |
| Native Inspect execution boundary | [native_execution.py](src/yassa/native_execution.py) |
| Evidence and deterministic checking | [evidence.py](src/yassa/evidence.py), [scoring.py](src/yassa/scoring.py) |
| Container and access profile | [Dockerfile](runtime/codex/Dockerfile), [config.toml](runtime/codex/config.toml), [boundary probe](runtime/codex/boundary_probe.py) |
| Regression evidence | [tests](tests), [native evidence auditor](tests/audit_native_run.py) |

Start generalization by inspecting `NativeStudy`, `BUILD_PROMPT`,
`CONSUMER_PROMPT`, `native_package`, and `execute_native_study` in `native.py`.
They currently fix the task name, builder identities, paths, and allocation.
The simulated and native paths have separate study schemas and orchestration;
choose shared responsibilities deliberately while preserving their different
execution capabilities.

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

Last application verification: **75 tests passed**, Ruff checks and formatting
passed, wheel and source distribution built, and native runtime resources in
the wheel matched their source bytes. The full native evidence audit and
deterministic repeat scoring passed. Later handoff edits are documentation-only.

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
