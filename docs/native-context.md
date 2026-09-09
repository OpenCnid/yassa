# Native skill catalog control and failure evidence

The native adapter now checks the declared skill catalog before inference and
checks every recorded root and subagent catalog before accepting an attempt.
Authenticated validation passed with two distinct roots and one child, using
66.938 native command seconds. This implements the follow-up to the
[reconciliation pilot's context and export failures](reconciliation-pilot.md#recorded-results).
The original pilot remains sealed with its failed audit and four missing uses.

## Enforced boundary

The subsequent [reconciliation study](reconciliation-sensitivity.md)
retains this gate and independent capture path unchanged. Its separately approved
68-attempt run completed with passing catalog checks across 75 recorded sessions;
both offline audits passed without violations or evidence gaps. It does not
require per-request context interception.

[config.toml](../runtime/codex/config.toml) explicitly disables `plugins`,
`remote_plugin`, and `apps`. Before each native attempt, the adapter verifies both
the configured values and the effective `codex features list` values, captures
`codex debug prompt-input`, and checks its rendered skill catalog. The inference
command continues to use `codex exec --strict-config` and the existing trial
permission profile. Local declared skills remain available with these features
disabled.

[builtin-skills.json](../runtime/codex/builtin-skills.json) pins 60 built-in file
paths and hashes from the recorded Codex 0.153.4 image. The profile has six skill
roots, with the explicit-only review skill excluded from the automatic catalog.
Generated Python caches are excluded from the byte comparison. The pins are
runtime assets frozen into each new plan; they are not inferred from a session's
observed catalog. A runtime update needs a deliberate profile review and new
validation rather than automatically accepting changed built-ins.

[native_context.py](../src/yassa/native_context.py) derives expected entries from
those verified bytes and the trial's declared `.agents/skills/<name>/SKILL.md`
inputs. It respects `allow_implicit_invocation: false`. Each entry must match its
name, whitespace-normalized description, and resolved absolute path. Extra,
missing, duplicate, malformed, or changed entries fail. The postflight check
also verifies built-in bytes and requires a valid transcript and catalog for
each recorded session, exactly one root, and recorded child parent identities.
It checks every catalog occurrence, not just the first catalog in each file.

A failed preflight records a harness failure without releasing inference.
A failed postflight records a harness failure even if Codex exited successfully
and wrote correct outputs. Its native exit status, duration, mismatched catalogs,
and surviving artifacts remain recorded. Such attempts and dependent uses remain
missing, rather than being accepted or assigned a task-correctness score of zero.
No automatic retry or broadening of the expected catalog occurs.

This is a preflight and postflight **acceptance gate**, not interception of every
model request. A changed child catalog may already have reached that child when
the postflight check rejects its attempt. The gate covers the pinned native skill
catalog format and declared top-level skill locations. It does not attest every
upstream system instruction or tool definition, or provide general prevention of
runtime context changes during inference.

## Evidence when capture or acceptance fails

[native_execution.py](../src/yassa/native_execution.py) records native event,
stderr, and final-response files independently, then collects control evidence
(sessions and built-ins) separately from trial outputs. For each successful
collection, [native_capture.py](../src/yassa/native_capture.py) screens decoded
contents for the injected credentials and stores the original export JSON before
portable-path materialization. Original paths are archive metadata; byte chunks
use short indexed storage names. Unsupported Windows names can therefore remain
in raw evidence without becoming extraction paths. Hashes, sizes, and executable
metadata survive archive reads and relocation.

An output-path rejection cannot erase an already captured transcript or raw
export. An output collector failure retains independently captured native logs
and control evidence. Results link to the capture archives and exact preflight
and postflight checks; reports expose those links. Usage extraction can use the
separate transcript and event captures when normalized output is unavailable.
Native completion and harness acceptance remain separate statuses.

Collection remains bounded: regular files up to 10 MB each and 40 MB total;
rejected paths and size limits are reported. Raw exports are chunked in 8 MB
pieces for storage. Malformed or undecodable export JSON and captures containing
the injected credentials are withheld; arbitrary crash recovery, disk failure,
and lossless recovery of all collector-rejected content are not implemented.

## Verification evidence

The user-approved diagnostic used the existing immutable image
`sha256:e473d44f582bd20f07755a37c08907ba6b3250cc58068ca04d713ab7c9d36fe6`
and saved authentication. Its allocation was frozen before launch: two attempts,
180 seconds for a root with exactly one child and 60 seconds for a root without
declared skills. Child work shared its root's deadline. Setup and export were
additional; neither attempt timed out or retried.

| Attempt | Authenticated sessions | Expected automatic catalog | Native seconds | Result |
| --- | --- | --- | --- | --- |
| Root with child | 1 root, 1 child | 5 built-ins plus declared `catalog-probe` | 49.532 | Passed |
| Root only | 1 fresh root | 5 built-ins | 17.406 | Passed |

All three sessions used GPT-6 Astra with `xhigh` reasoning, the trial permission
profile, and disabled shell networking. Both root and child read the declared
skill. They produced the correct integer sum and count; the root-only output
was also correct. All catalogs matched exactly, with no unexpected plugin
entries. Built-in byte checks, boundary probes, Inspect logs, and raw capture
checks passed. This validates this runtime integration; it does not measure
Dovetail performance or prove broader context isolation.

Evidence lives outside the checkout at
`C:/Users/Darian/yassa-runs/native-context-20260909-v1`:

- [Frozen allocation](C:/Users/Darian/yassa-runs/native-context-20260909-v1/plan.json)
  and [verified report](C:/Users/Darian/yassa-runs/native-context-20260909-v1/interpretations/verified/report.md).
- [Diagnostic check](C:/Users/Darian/yassa-runs/native-context-20260909-v1/interpretations/verified/check.json),
  including native usage and exact check identities.
- [Pilot transcript replay](C:/Users/Darian/yassa-runs/native-context-20260909-v1/interpretations/verified/pilot-context-replay.json):
  the new gate rejects all six previously observed bad catalogs across four of
  53 preserved attempts. No inference or original reclassification was performed.
- [Offline compatibility](C:/Users/Darian/yassa-runs/native-context-20260909-v1/interpretations/verified/compatibility.json):
  original pilot and native v1 scores and seals remain unchanged.

Plan identity: `aa9eb5b41847c12af28e0ab0856b75c853c5a10686dd79fae381f1f70a597cdc`.
Run seal: `d443278bba62b17d4bbde9c555d3991079d565fc06cb2622845a31bbb310616a`.
The [opt-in driver](../tests/run_native_context_probe.py) and its exact executed
source are retained. Running it again requires a new external run directory and
authorization for another model allocation; the completed diagnostic is not a
standing instruction to spend more.

Application verification: **163 passed, 1 skipped** in the full suite. The skip
is the existing Windows symlink test. The 11
[context/capture tests](../tests/test_native_context.py) include actual Inspect
tasks with a simulated sandbox for preflight rejection, child drift,
nonportable paths, collector failure, and credential withholding, plus archive
relocation and catalog parser checks. They make no model calls. Wheel and source
builds passed, and all 26 packaged source/runtime files matched the checkout.
