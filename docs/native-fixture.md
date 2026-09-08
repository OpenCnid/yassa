# Native Codex fixture

This milestone adds real Codex CLI execution to the simulated fixture harness.
The comparison asks whether fresh consumers complete synthetic account-total work
using skills built with or without the Codex-oriented Dovetail runtime pack.
It is a small descriptive test of this installed revision and configuration.

## Frozen design

[native-codex-fixture.json](../studies/native-codex-fixture.json) selects Codex
0.153.4 with GPT-6 Astra and `xhigh` reasoning in both primary builder and consumer
runs. One build per arm is planned for each preparation condition. Each package
is then installed into three fresh consumer containers: four builds and twelve
consumer attempts, with no harness attempt retries. Build and consumer deadlines are
300 and 120 seconds respectively, excluding sandbox setup and export.

Both arms receive identical build-brief bytes within each condition. The added
Dovetail skill catalog and explicit `$better-skill-creator` invocation define the
treatment. The baseline retains Codex's version-pinned built-in skills, including
its skill creator. Consumers receive only the frozen generated package and current
rows, explicitly invoking `$account-totals`. Protected expected results and other
cases stay outside all subject containers.

The supplied condition preserves the repository's synthetic supplied fixture
bytes. The prepared condition uses the deterministic generator with seed 73019.
These labels describe input provenance; they do not compare real user work with
model-generated work. Results stay separate by condition. This design does not
include a no-package consumer baseline, neutral-text control, or repeated builds.

## Source and runtime

The selected external source is the Codex-oriented installed pack under
`C:/Users/Darian/.codex/skills`, containing eight explicitly named Dovetail skills.
Its 83 runtime files total 1,576,341 bytes and have bundle identity
`980068581a48610f08bf1a50c4be88cf0a37a02e7b7fc027397b31398f2a51eb`.
Six Dovetail skills enter the automatic catalog; `spark-steering` and `upsum`
retain their explicit-only invocation policy and are present on disk.
The source snapshot includes `SKILL.md`, runtime references, scripts, assets,
agents, viewer, license/notice, README, and requirements where present. Development
tests/fixtures, dotfiles, and caches are excluded and the inclusion profile is
recorded in `study.json`. Included bytes are unchanged. Source scripts are
installed without executable bits and can be run through their interpreters.

This is a file-hashed installed revision with unknown upstream commit, not a
claim to benchmark upstream `OpenCnid/dovetail` at its current commit. The public
upstream checkout examined during preparation retained Claude-specific workflow
text. No Dovetail source text is stored in this repository. External evidence
preserves the exact runtime snapshot and its manifest.

The [Dockerfile](../runtime/codex/Dockerfile) pins Node's base image digest and
Codex's npm version. The actual tested local image is
`sha256:e473d44f582bd20f07755a37c08907ba6b3250cc58068ca04d713ab7c9d36fe6`.
Python 3.11, PyYAML, Node, Git, ripgrep, curl, and Bubblewrap are available in
the image. Debian package installation is captured by the resulting image identity;
rebuilding later may yield a different image and must use a new identity.

Inspect 0.3.263 provisions and cleans up a fresh Docker sandbox per attempt. The
native CLI uses a privately injected saved ChatGPT login. Its named command
permissions deny reads of that credential and writes to inputs, skill sources,
and runtime configuration. Shell network is disabled; Codex retains provider
connectivity. No host repository/home mounts, Docker socket, scorer, answer keys,
personal configuration, MCP connections, or other arms' files enter the container.
The native built-in skills are retained and captured in both arms.

Containers are unprivileged UID 1000 with capabilities dropped. Docker seccomp
and AppArmor restrictions are relaxed so Codex can create its own Bubblewrap
namespace. The boundary does not claim resistance to kernel/container exploits.
See [architecture](../ARCHITECTURE.md#implemented-native-codex-fixture) for the
implemented access and evidence rules.

## Verification and evidence

An initial unauthenticated command probe tested credentials with a harmless
sentinel. The authenticated `native-probe-01` then passed every command boundary
check, loaded a Yassa-owned skill through native discovery, and wrote the required
JSON. Its native transcript records the skill in the catalog, the actual read of
`SKILL.md`, the named permission profile, GPT-6 Astra, and `xhigh` reasoning.
It made three recorded model calls in 23.7 seconds, using 39,623 input tokens
(12,928 cached) and 140 output tokens. This probe is separate from comparison data.

Every comparison attempt repeats the boundary probe before inference. Full
native session transcripts, event JSONL, output files, built-in skill bytes,
file modes, timing, usage, and Inspect logs are collected before teardown.
Export excludes credentials. The controller scores only recorded result JSON;
it never imports or executes submitted code.

The completed run is preserved at
`C:/Users/Darian/yassa-runs/codex-dovetail-native-v1`. Its
[audited report](C:/Users/Darian/yassa-runs/codex-dovetail-native-v1/interpretations/audited/report.md)
shows package decisions and underlying native attempt status separately.
The [original report](C:/Users/Darian/yassa-runs/codex-dovetail-native-v1/interpretations/original/report.md)
remains unchanged. Reproduction commands are in
[README](../README.md#run-the-native-codex-fixture).

| Input condition | Without Dovetail | With Dovetail |
| --- | ---: | ---: |
| Supplied synthetic inputs | 3/3 | 3/3 |
| Yassa-prepared synthetic inputs | 3/3 | 3/3 |

All four packages were usable and all twelve consumer attempts completed, with
no missing outcomes. Both control builds completed in about 195 seconds. Both
Dovetail builds reached their 300-second deadline after producing packages;
the declared rule retained those packages for downstream use. Neither timed-out
build is represented as a completed native attempt in the audited report.

The runtime recorded 20 native sessions and 90 model response usage records.
Each Dovetail build used two native subagents. Control builds recorded 277,965
input tokens and 11,176 output tokens in total; Dovetail builds recorded 690,966
input tokens and 18,275 output tokens. Input totals include cached tokens, and
interrupted requests can leave unreported usage. These results show equal success
on this fixture with different observed build resource use; they establish no
general ranking.

Original run seal:
`254ba558ea80e124074049bc9fc39816dea686b9ed00a92cf3aed393063b5f98`.
The audited and repeat-score interpretations have identical score bytes, SHA-256
`da4a0e24fbf27ef59dd665a5056ed4986f90e1c7e6e35a7bc1a473881ccb005f`.
Their twelve score rows match the original interpretation; only the recorded
reporting-correction reason differs from the original score record.

Verification executed after implementation: 75 tests passed, Ruff checks and
format verification passed, wheel and source distribution built, and
`git diff --check` passed. The wheel includes the Docker recipe, configuration,
and boundary probe. Tests also verify package-mode preservation, source exclusions,
held-out projection, failure denominators, and deterministic native rescoring.
The [evidence auditor](../tests/audit_native_run.py) checks actual recorded Inspect
inputs, native catalogs and reads, configuration, distinct root sessions, common
input equality, and exact consumer package bytes.
The completed audit passed all 16 attempts, verified 16 distinct root sessions,
and found one unchanged built-in skill snapshot across the run. Its
[result and source identity](C:/Users/Darian/yassa-runs/codex-dovetail-native-v1/interpretations/audited/evidence-audit.json)
are preserved beside the report.

The first audit incorrectly expected an explicit-only built-in skill in the
automatic catalog. Its metadata handling was corrected; the initial auditor and
correction note are preserved under the audited interpretation. A Windows package
sync was deferred while the live CLI executable was locked; it succeeded after
the run exited. Neither correction changed subject work or scores.

## Interpretation limits

- This is one synthetic contract, one build per arm/condition, and one consumer
  per case. Reusing a package on several cases does not add independent builds.
- Native loading is explicitly invoked. This does not estimate automatic routing,
  clarification quality, novice support, or performance on other domains.
- Internal native subagents are permitted within the same sandbox and deadline;
  they remain part of the treatment. External nested model CLIs and downloads
  cannot cross the command credential/network restrictions. Not every shipped
  optional workflow has been exercised.
- Usage is summed from native response records, deduplicated by response ID.
  Cached tokens are included in input totals. Dollar costs are unavailable;
  hard token/spend limits are not implemented. Interrupted provider requests may
  consume usage absent from the returned records, so these are recorded token
  counts rather than an independently reconciled billing total.
- The harness never reruns a failed attempt. Any native provider transport retries
  remain CLI behavior; the adapter does not expose every failed provider request.
- Model aliases and account-side inference behavior are recorded as observed;
  they are not immutable model-weight pins.
- Equal pass counts on small fixtures would not establish equal package quality
  or an absence of Dovetail benefit. Broader claims require more varied tasks
  and independent builds under a declared sampling design.

## Documentation checked

- [Inspect sandboxing](https://inspect.aisi.org.uk/sandboxing.html): Task/Sample
  Docker lifecycle, `ComposeConfig`, `sandbox().exec`, file access, timeout and
  output limits. Installed source was also checked for process-tree timeout behavior.
- [Inspect Agent Bridge](https://inspect.aisi.org.uk/agent-bridge.html): an available
  alternative for provider routing; this saved-auth fixture does not use it.
- [Codex non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode),
  [native skills](https://learn.chatgpt.com/docs/build-skills),
  [permissions](https://learn.chatgpt.com/docs/permissions), and
  [authentication](https://learn.chatgpt.com/docs/auth), checked against the
  installed CLI help and actual session records.
