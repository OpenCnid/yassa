# Synthetic reconciliation pilot

This pilot asks whether generated-package assistance changes completion of
constructed reconciliation tasks, and whether Dovetail-assisted builds differ
from the common build request under the selected conditions. The user selected
synthetic reconciliation work on 2026-09-08. Preparation and the required consumer
baseline are implemented. The approved run completed: all 46 recorded consumer
outputs passed, including all 10 no-package baselines. One build-export failure
left four planned package uses missing. No attempt was retried.
The declared-context audit failed because additional plugin skill entries
appeared in six recorded catalogs; this prevents a clean controlled comparison.

The intended use is condition discovery: inspect feature failures, saturation,
build variation and observed resource use before choosing a broader comparison.
This is one contract and related build briefs, not a representative accounting
workload or a multi-domain builder ranking. A ceiling result is useful evidence
about these cases' sensitivity, not evidence of equivalence.

## Work and comparisons

The subsequent [sensitivity study](reconciliation-sensitivity.md) uses a new
event-reconciliation contract. Its separately approved run completed with another
ceiling: 60/60 passing consumers, including all 12 baselines. Both offline audits
passed. This does not alter the original pilot or its failed audit.

The accepted reconciliation contract sums duplicate IDs separately on each side,
keeps literal case-sensitive IDs, includes the union with zero balances, and
computes left minus right using signed integers. CSV quoting, Unicode and embedded
newlines are legitimate inputs. The existing independent semantic checker covers
these rules; this milestone does not change it.

| Condition | Development | Held-out coverage |
| --- | ---: | --- |
| Supplied | 2 examples | 4 cases: duplicate-side sums with cancellation; literal IDs and quoted CSV; one-sided and zero balances; empty inputs |
| Prepared | 2 examples | 6 cases: duplicates, identifiers, one-sided records, cancellation, empty inputs, CSV quoting |

[Supplied materials](../studies/reconciliation-pilot-supplied.json) have explicit
rows and independently checked references, agent authorship, a deliberate byte
pin in the request. The route means a supplied file; it does not mean
human-authored work. Prepared materials use `guided-file-suite-v1`, seed 73027,
and retain all six selected features. No cases were chosen after observing pilot
outcomes. Both conditions share the development examples and empty evaluation
problem; their group IDs preserve that relationship. Other cases exercise related
features. Conditions are reported separately, with no causal preparation contrast.

| Arm/control | Allocation per condition | Interpretation |
| --- | --- | --- |
| `common-request` | 2 independent builds; 1 fresh use per package/case | Common build request with pinned native built-ins |
| `dovetail` | 2 independent builds; 1 fresh use per package/case | Exact external runtime pack plus explicit creator invocation |
| `no-package` | 1 fresh execution per case; no build | Task execution with the same complete facts and no generated package |

The common-request arm is not an explicitly invoked official-creator arm.
Neutral text, component ablations, automatic activation, clarification and
cross-vendor transfer are outside this pilot. Native built-ins remain present
in every session. Package uses are dependent on their independent builds; two
builds investigate variability for these briefs and cannot establish a broad
builder effect. Execution repeats are deliberately limited to prioritize feature
coverage. The [baseline contract](configurable-native.md#consumer-baseline)
describes context equality, lineage and denominators.

## Sources and resources

The prepared local pilot binds the unchanged 83-file Dovetail runtime snapshot
from the [previous audited native comparison](native-fixture.md#source-and-runtime):
artifact `980068581a48610f08bf1a50c4be88cf0a37a02e7b7fc027397b31398f2a51eb`,
1,576,341 bytes, with unchanged non-executable modes and unknown upstream commit.
It uses the same immutable image
`sha256:e473d44f582bd20f07755a37c08907ba6b3250cc58068ca04d713ab7c9d36fe6`.
The prior audit establishes native loading and builder/subagent capability for
that snapshot and image; it does not establish performance on these new cases.
No external skill text enters this repository.

The selected configuration is Codex 0.153.4, GPT-6 Astra, `xhigh` reasoning,
schedule seed 260908, and no harness retries or best-package selection.
The model is an alias, not an immutable weight snapshot.

| Reservation | Calls | Deadline each | Native command seconds |
| --- | ---: | ---: | ---: |
| Builds | 8 | 600 seconds | 4,800 |
| Package-assisted consumers | 40 | 60 seconds | 2,400 |
| Baseline consumers | 10 | 60 seconds | 600 |
| Total | 58 | | 7,800 |

The build allowance gives both treatments more time than the earlier 300-second
fixture, in which Dovetail wrote usable packages but reached its deadline. The
consumer deadline bounds small file tasks and is common to all consumers. The
130-minute sum is a reservation, not a duration prediction: sandbox setup/export
is additional. Hard token/spend controls and dollar estimates are unavailable.
Failed builds contribute zero to planned package uses; infrastructure failures
remain missing. Usable deadline outputs proceed with their native timeout retained.

## Preparation and execution

[The request](../studies/reconciliation-pilot-request.json) deliberately remains
pending until an external source is pinned. Use the existing draft/revision path:

```powershell
$pilotRoot = Join-Path $env:USERPROFILE 'yassa-runs/reconciliation-pilot-example'
uv run --locked yassa study-draft studies/reconciliation-pilot-request.json --draft-dir "$pilotRoot/round-0"
```

Supply a revision containing the exact external `sources` binding, both complete
`arms` entries with Dovetail's source ID attached, and `unresolved: []` after
resolving the source choice. Follow the [file-pin contract](configurable-native.md#arms-sources-and-allocation).
The local milestone's source-answer file and source provenance are preserved in
`C:/Users/Darian/yassa-runs/reconciliation-pilot-20260908-v1`, alongside the exact
preparation script. It reuses the archived source bytes after verifying their
original run seal; it does not scan the current installed personal skills.

The local ready review and `run/plan.json` froze the complete allocation
before launch; `compatibility.json` records the earlier unstarted-freeze check.
The user's subsequent approval is preserved in `execution-authorization.json`,
and `launch-console.txt` records execution. The original run is sealed and must
not be relaunched or rewritten. The [native commands](configurable-native.md#run-a-definition)
create separate interpretations for offline rescoring.

## Recorded results

Local evidence: [pilot assessment](C:/Users/Darian/yassa-runs/reconciliation-pilot-20260908-v1/pilot-analysis.md),
[failed follow-up audit](C:/Users/Darian/yassa-runs/reconciliation-pilot-20260908-v1/run/interpretations/path-fix-compatibility/evidence-audit.json),
and [score/resource summary](C:/Users/Darian/yassa-runs/reconciliation-pilot-20260908-v1/run/interpretations/path-fix-compatibility/pilot-summary.json).
Original and both repeat score files are byte-identical; the original seal is
`7370e91ad0b6b4d373d9bdcd09145a13776b84e4e4aa8cb817164c59a7a7c284`.

| Condition | Arm/control | Passed | Scored | Planned | Missing |
| --- | --- | ---: | ---: | ---: | ---: |
| Supplied | common-request | 8 | 8 | 8 | 0 |
| Supplied | dovetail | 4 | 4 | 8 | 4 |
| Supplied | no-package | 4 | 4 | 4 | 0 |
| Prepared | common-request | 12 | 12 | 12 | 0 |
| Prepared | dovetail | 12 | 12 | 12 | 0 |
| Prepared | no-package | 6 | 6 | 6 | 0 |

All four common-request builds and three Dovetail builds produced accepted
packages. The second supplied Dovetail build exited with code 0, but host storage
rejected `output/check-evidence/generated-24/left ledger.csv` because of its
interior space. The collector had accepted that regular file. The whole output
bundle, including native transcripts and usage, was therefore unavailable. Its
package quality cannot be inferred, and its four consumers were not launched.
The preserved [incident record](C:/Users/Darian/yassa-runs/reconciliation-pilot-20260908-v1/export-incident.json)
describes the retained launch, binding, boundary and Inspect error evidence.

The catalog audit found `deep-research-work` and `plugin-management` entries
outside the pinned skill set. They appeared in five subagent catalogs across
the three exported Dovetail builds and in one prepared Dovetail consumer catalog
(`heldout-cancellation`, build 1). The consumer's catalog maps these entries to
`/home/runtime/codex/plugins/cache/openai-curated-remote`. Their complete source
bytes were not included in the exported built-in snapshot. Fixed image identity
and denied shell networking did not ensure a fixed skill catalog. The origin of
this runtime behavior and its influence on the work were unresolved in that
audit. Subsequent investigation found the trial left Codex's plugin, remote
plugin, and app features enabled; the remote cache path is consistent with that
loading route. The exact service-side selection event was not captured.

The first audit assertion and its exact source are preserved under
`interpretations/audited`. The follow-up auditor examines every recorded catalog
and emits a **failed** verdict with explicit violations. Missing export evidence
is reported separately. The expected catalog is not broadened after observing
the unexpected entries. Deterministic output scores remain descriptive records;
the failed context audit prevents attributing differences to the planned
treatments alone.

This is a score ceiling on the fixed cases: package assistance produced no
observed accuracy gain over the baseline. It does not establish equivalence,
the quality of the missing package, or a general builder ranking. The supplied
condition has only one observed Dovetail build. The cases and development briefs
are related, and there is only one baseline execution per case. More repetitions
of these same cases would not address their limited work coverage.

The 54 native launches used **4,256.216 command seconds (70.94 minutes)**;
container setup/export is additional. No native command reached its deadline.
Recorded usage totals are 4,169,036 input tokens (including 3,348,480 cached),
96,912 output tokens, 58 native sessions and 237 response records. These totals
omit the unpreserved build's usage and may omit unreported aborted requests.
They do not establish billing cost. Build and consumer resources, conditions,
and missing counts remain separate in the machine-readable summary.

## Validation boundary

[Consumer baseline tests](../tests/test_consumer_baseline.py) cover strict control
configuration, independent allocation, preflight admission, complete common
facts, absence of treatment files, builder-independent launch, zero/missing
denominators, separate reports, preparation pins and relocated rescoring. A
source fixture validates pilot preparation without claiming to be Dovetail.
Every pilot reference passes independent verification and checker probes.

The native execution adapter, command permissions and checker are unchanged.
Inspect 0.3.263 was confirmed in the locked environment and its supported
execution boundary checked against the [official sandbox documentation](https://inspect.aisi.org.uk/sandboxing.html).
Tests substitute a recorded-output adapter. The separately preserved pilot
provides live evidence with a failed context audit and missing build output.
After execution, the artifact store was corrected to preserve interior spaces,
without changing path bytes or executable metadata. Traversal, device aliases,
leading/trailing spaces, collisions and links remain rejected. A regression
reproduced the observed rejection before the fix; the actual pinned Linux
collector's space-path fixture then round-tripped through corrected Windows
storage and relocation without model calls. This fixes the observed path case;
it does not implement lossless recovery for every unsupported export path.
Final executed checks and external review paths are recorded in
[the handoff](../HANDOFF.md#verification-and-delivery).

The subsequent [native context milestone](native-context.md) disables those
features, checks exact root and child catalogs, and preserves raw exports and
independent transcripts before output-path acceptance. Its separately authorized
authenticated diagnostic passed. An offline replay rejects all six preserved
unexpected catalogs under the new gate. These changes do not restore the lost
pilot build or convert its failed context audit into a controlled comparison.
