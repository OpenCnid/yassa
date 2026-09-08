# First implementation milestone

The kickoff delivered a working **simulated API fixture** path using Inspect AI
0.3.263 and Python 3.11.16 on Windows. The deterministic actors are test doubles;
their outcomes are not measurements of Dovetail, a real model, or native skill
loading. The CLI, dependency pins, and tests are implemented; the wider product
design remains in [SPEC](../SPEC.md) and [ARCHITECTURE](../ARCHITECTURE.md).

## Reproduce

The commands below were exercised from this checkout. Use a new external run
directory and a new label for each additional scoring interpretation:

```powershell
uv sync --locked
uv run --locked yassa run studies/fixture-study.json --run-dir C:/Users/Darian/yassa-runs/kickoff-fixture-v1
uv run --locked yassa verify C:/Users/Darian/yassa-runs/kickoff-fixture-v1
uv run --locked yassa rescore C:/Users/Darian/yassa-runs/kickoff-fixture-v1 --label repeat-score
uv run --locked pytest -q
uv run --locked ruff check src tests
uv run --locked ruff format --check src tests
uv build
git diff --check
```

The absolute output location is this kickoff's local evidence locator; it is not
a product default. The [README](../README.md#run-the-fixture) gives a portable
PowerShell example using the user's home directory. A source distribution and
wheel build successfully from the pinned project configuration.

## Observed fixture result

The example plans 42 logical trials: 18 direct tasks, six builds, and 18 downstream
uses. Its maximum reservation is 84 attempts, including every allowed retry.
Observed execution uses 36 Inspect attempts: 18 direct tasks, six builds, and
12 consumers. Four packages are usable. Two builders intentionally fail to submit
a usable package, leaving six explicit failed downstream dependencies without
fabricated consumer attempts. The normal example has no infrastructure retries;
separate integration tests inject and exhaust them.

| Preparation route | Stage | Complete fixture | Lossy fixture | Invalid fixture |
| --- | --- | --- | --- | --- |
| Supplied | Direct | 3 / 3 | 1 / 3 | 0 / 3 |
| Supplied | Consumer | 3 / 3 | 1 / 3 | 0 / 3 |
| Yassa-prepared | Direct | 3 / 3 | 0 / 3 | 0 / 3 |
| Yassa-prepared | Consumer | 3 / 3 | 0 / 3 | 0 / 3 |

Each value is confirmed successful work / planned uses. The lossy actor deliberately
omits negative amounts; the supplied empty-input case still passes. This table
checks denominator and lineage behavior, not comparative builder quality.
Preparation conditions are not pooled, and their different case sets do not
estimate an effect of preparation. Model token counts and prices are null;
recorded calls and attempt durations appear in the full report.

The local [example report](C:/Users/Darian/yassa-runs/kickoff-fixture-v1/interpretations/original/report.md)
links to original inputs, frozen study/plan, per-attempt input bindings, exact
packages and responses, and native Inspect `.eval` logs. Original evidence stays
outside the repository. The additional
[rescored report](C:/Users/Darian/yassa-runs/kickoff-fixture-v1/interpretations/repeat-score/report.md)
is derived from that evidence without model calls. The two `scores.json` files
are byte-identical under the same checker version.

Recorded run seal:
`a24f0b8502178ef10a36538d5664a34974aba75b25fcaab19c7e32b8b880d7ba`.
The original and repeated score files both have SHA-256
`b467a60492b3d43282d86c474b7e4231694c736366cb89ae80a09a1e4ffc84fa`.

## Acceptance coverage

| Boundary | Executed evidence |
| --- | --- |
| Intake and preparation | Complete requests receive no redundant questions; incomplete intake returns at most two; supplied byte pins and prepared seed/provenance are retained |
| Freeze and planning | Unsupported conditions, incorrect references, overlapping IDs/groups/equivalent inputs, and insufficient attempt budgets fail before launch; enumeration agrees with the fixture's analytical counts |
| Model access | Actual Inspect sample messages, model events, and raw provider requests match the intended binding; no tool access or hidden targets are exposed; each sample/model is fresh |
| Builder to consumer | Consumer binding references the exact complete package manifest and producing build attempt; failed builders retain planned downstream failures |
| Artifact ingestion | Path traversal, absolute paths, Windows streams/reserved names, case collisions, executable files, and NTFS junction sources are rejected |
| Checker | Valid reordered/formatted work passes; missing/duplicated accounts, wrong counts, floats/booleans, non-finite numbers, duplicated JSON keys, and incorrect per-account values fail, including errors preserving the grand total |
| Failures and resources | First infrastructure failures and linked retries survive; exhausted infrastructure stays missing; truncated outputs fail without task retries; Inspect time limits are observed |
| Evidence and rescoring | Sealed-file tampering is detected, artifacts retain identity when relocated, incomplete runs are rejected, repeated scoring matches byte for byte, and changed scoring retains originals with a correction reason |
| Reporting | Route/stage/arm counts agree with selected records; generated evidence links resolve; unavailable costs remain null; no unsupported inferential claims |

All 65 tests pass with no skips. Ruff checks and formatting checks pass.
The documentation/report check resolved 431 local links and anchors across eight
files, and `git diff --check` reported no whitespace errors.
The initial development run exposed a missing Inspect provider registration,
which was corrected before the first complete path. An early test run then had
60 passes, one false-positive string assertion, and one OS symlink-privilege skip.
The assertion now checks structured case identities, and Windows link coverage
uses an actual NTFS junction. A subsequent strengthening of the raw request check
exposed Inspect's attachment indirection in stored events; the reader now uses
its supported attachment-resolution option before comparing request bytes.
Study attempts remain in their original evidence throughout these harness checks.

## Limits and next step

This section records the simulated milestone's scope at completion. The subsequent
[native fixture milestone](native-fixture.md) exercises real Codex and Dovetail;
it does not change these original simulated results.

- No OpenAI, Anthropic, or Google API keys were present in the checked environment;
  no paid model calls were made. Docker was reachable, but no native agent or
  sandboxed skill-loading workflow was exercised.
- The provider and controller are trusted local code. Their model interface has
  no filesystem, network, or tools. This does not establish OS isolation for
  untrusted native programs or arbitrary provider plugins.
- Preparation is a fixed synthetic task template with focused readiness feedback.
  General natural-language study synthesis, research, dataset discovery, and
  arbitrary user-domain contracts are not implemented.
- External builder sources, scripts, automatic activation, native hosts, model
  grading, inferential statistics, and automatic crash recovery remain unsupported.
  Model-grading configurations are rejected before execution, so different-family
  grading is not yet an exercised capability.

The next bounded milestone is one pinned native CLI in an Inspect sandbox using
a Yassa-owned fixture package. Verify actual package loading, clean configuration,
held-out/tool boundaries, artifact capture, and real usage before admitting
Dovetail or another substantive builder source. Models, domains, external packs,
and sample allocation for that real study remain explicit open choices.
