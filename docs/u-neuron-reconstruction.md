# U-Neuron reconstruction: Dovetail versus baseline

Completed 2026-09-10. Yassa ran one fresh reconstruction per arm from the two
U-Neuron specification sheets, then tested the saved projects against the
unchanged upstream suite. **Dovetail finished faster, but this pair did not
establish a mathematical correctness advantage.** The two-test score difference
came entirely from error-message wording.

This document preserves the study design, findings and evidence locations in the
repository. The [artifact guide](artifact-studies.md) describes the reusable
product workflow. Original inputs, source packs, implementations and run logs
remain outside the checkout.

## Design and allocation

The user selected an existing scientific software artifact whose correctness
could be judged against its implementation and tests. The question was whether
explicitly using Dovetail improved reconstruction from specifications alone.
This was a direct artifact-building comparison, not a skill-builder/consumer
study or a test of automatic skill activation.

| Condition | Frozen choice |
| --- | --- |
| U-Neuron source | [Lexideck-Technologies/U-Neuron](https://github.com/Lexideck-Technologies/U-Neuron/tree/6778cefdceef55997a06734727ac5b0e799ee6dd), commit `6778cefdceef55997a06734727ac5b0e799ee6dd` |
| Task-specific inputs | Only `U-NEURON_Foundational_Specification.md` and `u-neuron-pytorch.md`, preserved verbatim |
| Protected evaluator inputs | Original `src/`, all original `tests/` files and `pyproject.toml` at that commit |
| Dovetail source | [OpenCnid/dovetail](https://github.com/OpenCnid/dovetail/tree/356c096a21f1eed35659fea577c10f51d2970c13), commit `356c096a21f1eed35659fea577c10f51d2970c13` |
| Treatment | Explicit Dovetail invocation, beginning with subagent composition and applicable companion skills; corrected extraction of all eight skills and runtime resources |
| Baseline | Same common task prompt and native tools, with no Dovetail files or invocation |
| Root model | GPT-6 Astra, xhigh reasoning |
| Runtime | Codex CLI 0.153.4; Python 3.11; PyTorch 2.14.0+cpu; pytest 9.1.1; NumPy 2.4.3; Inspect 0.3.263 |
| Per-root limits | 1800 seconds, two CPUs and 4 GB memory; no hard token or spend cap |
| Initial allocation | One attempt per arm, 3600 reserved seconds, schedule seed 20260910 |
| Feedback and repair | No held-out test feedback, implementation repair or additional model attempt after submission |

The immutable image ID was
`sha256:32dcd44374a54d27e054e49b5a318fcfa2cefc2f43f57c4d6b38ab56cb99dac1`.
The frozen Yassa procedure artifact ID was
`8fb64957a434c412418a10ddac8a3ef0016cb243e538cb3a365bed75ace093ba`.
The recorded image and procedure define the run; a future rebuild or the current
checkout need not be byte-identical to them.

Both arms retained the native runtime's same pinned built-in skills. The actual
builds overlapped in separate containers after the packaging correction below.
Neither builder could access the original source, shipped tests, the other
artifact or development notes. The earlier manual U-Neuron regularizer change
was excluded from the reference. Each agent could write and run its own tests;
those results did not enter the primary score.

## Recorded results

| Artifact | Shipped tests passed | Native execution time | Accepted sessions |
| --- | ---: | ---: | ---: |
| Original reference | 85/87 | Not a reconstruction attempt | — |
| Without Dovetail | 64/87 | 1167.125 s (19m 27s) | 1 |
| With Dovetail | 66/87 | 716.047 s (11m 56s) | 4: root and three children |

Both actual reconstruction attempts completed and passed the native permission
and catalog checks. Their saved artifacts were scored in fresh offline Inspect
Docker sandboxes, using read-only source/tests and no credentials, host mounts
or candidate installation hooks. Every test collected on the reference remained
in the denominator. The initial Dovetail preflight failure remains a separate
missing outcome in the original run; it was not counted as a failed artifact.

The original reference failed `test_reg_identical_states_returns_zero` because
of a nonzero smoothing offset and `test_gradient_flow_unitary` because of the
test's parameter-name/gradient assumption. Both reconstructions passed the
unchanged identical-state regularizer test. No original test was altered or
removed, and neither submitted project was repaired after scoring.

## Failure analysis and interpretation

Dovetail passed exactly two tests that the baseline did not:
`test_doubly_stochastic_requires_square` and `test_unitary_requires_square`.
Both implementations raised the expected `ValueError` for rectangular
constrained weights. The baseline message said `in_channels == out_channels`;
the test regex required `square`. The specs do not prescribe that wording.

The 21 shared failures have these immediate causes:

| Cause | Tests per arm | What the failure establishes |
| --- | ---: | --- |
| Missing `UTensor.EPS_FLOOR` class attribute | 15 | Both provide the specified module constant and floor behavior, but not the class alias assumed by the tests. Several tests stop in setup before exercising the named behavior. |
| Missing private `_DEPTH_COUNTER` dictionary | 2 | The tests manipulate the original implementation's private emission guard. Both reconstructions use a different guard. |
| Missing parameter named `theta` | 1 | The test assumes a particular unitary parametrization. Both reconstructions use differentiable matrix-exponential constructions with other parameter names. |
| Exact exception-message regex | 3 | Both raise the expected exception type, with strings differing from the original implementation. |

The baseline has two additional wording failures, described above. This is
**post hoc failure analysis, not rescoring**. Scores remain 64/87 and 66/87.
Blocked assertions leave behavior unassessed; they must not be relabeled as
passes. The shipped tests measure compatibility with the original implementation
as well as observable behavior specified in the documents.

This pair therefore does not demonstrate a mathematical correctness advantage,
prove either reconstruction fully correct, or establish a general skill ranking.
The 87 tests are correlated checks on one artifact, not 87 independent tasks.
Because the source is public, model training exposure cannot be excluded.

## Resource tradeoff

Dovetail's native execution was about 39% shorter in this pair. Three internal
agents handled tensor utilities, linear/emission work and test development while
the root integrated the model and regularizer. The baseline used one session.
This is an observed difference, not a causal estimate from one pair. Native time
excludes container setup, export and later testing.

| Reported usage, including child work | Without Dovetail | With Dovetail |
| --- | ---: | ---: |
| Input tokens, including cached input | 1,284,230 | 3,215,678 |
| Cached input tokens | 1,214,720 | 2,974,848 |
| Uncached input tokens | 69,510 | 240,830 |
| Output tokens | 34,847 | 52,191 |
| Total reported tokens | 1,319,077 | 3,267,869 |
| Tool calls | 26 | 62 |

Response IDs are deduplicated across root and child transcripts; session totals
are not added again. Dovetail used about 2.48 times the reported tokens and 3.46
times the uncached input. Most input was cached, so these ratios are not spending
ratios. No measured dollar cost or hard spending limit is claimed.

## Preserved corrections

The initial full Dovetail tree contained 418 files. It exposed five nested
development fixture skills and changed a skill name through nested Claude plugin
metadata. Yassa rejected that catalog **before inference**. The corrected runtime
extraction excluded `tests/` and `.claude-plugin/` directories, retaining 85
original files and all eight skill instructions. No retained skill text changed.
This extraction differs from the upstream unfiltered copy installer.

The correction was declared before either artifact was scored. The baseline was
retained regardless of outcome, without a rerun. A separate Dovetail-only run
received one 1800-second reservation. The original failed reservation was not
refunded: the two ledgers record three reservations and 5400 scheduled seconds,
including one preflight that never reached inference. Exactly two roots performed
reconstruction. Earlier evaluator permission and Windows path-length preparation
failures were also preserved; none supplied feedback to a subject.

## Evidence and verification

These are local evidence locations, not files bundled with the repository:

| Location | Contents |
| --- | --- |
| `C:/yr/u1` | Sealed original run: missing Dovetail preflight and completed baseline; primary scores under `interpretations/original/` |
| `C:/yr/u2` | Sealed corrected Dovetail run and its primary scores under `interpretations/original/` |
| `C:/yr/ubudget`, `C:/yr/ubudget2` | Original and corrective reservation/usage ledgers |
| `C:/Users/Darian/yassa-runs/u-neuron-reconstruction-20260910` | Source selection, requests, setup evidence, correction, audits, synthesis and implementation copies |

In the last directory, `REPORT.md` links the evidence. `request.json` and
`request-corrected.json` preserve the definitions; `CORRECTION.md` and
`pack-exclusions.json` preserve the packaging decision and every excluded hash.
`comparison-audit.json` verifies identical public files, protected bundles,
common prompt, model settings, image, runtime and procedure across the retained
attempts, plus all five accepted session catalogs. `failure-analysis.json`
records exact messages and the two differing tests. `dependency-freeze.txt`
records installed packages. `implementations/with-dovetail/` and
`implementations/without-dovetail/` contain copies of the untouched submissions.

Read existing `interpretations/original/report.md` and `scores.json` to inspect
the outcomes without execution. The supported verification commands are:

```powershell
uv run --locked yassa verify C:/yr/u1
uv run --locked yassa verify C:/yr/u2
```

Both commands passed. The [artifact guide](artifact-studies.md#product-workflow)
describes preparation, execution and scoring commands. Scoring under a new label
reruns tests without model calls and requires the frozen procedure/dependencies.
It creates a new interpretation and does not overwrite the original.

Software verification at completion was **299 passed, one skipped**, with Ruff
lint/format and patch whitespace checks passing. A separate real Inspect/Docker
acceptance accepted correct addition, rejected subtraction, and verified an
unprivileged evaluator, read-only tests, absent credentials and denied network
access. These software checks are not additional experimental samples.

Source selection, the packaging correction, independent auditing and synthesis
were performed manually by the development agent. Freezing, model execution,
primary scoring, resource accounting and verification used Yassa commands. The
artifact route advances partial Y03/Y04/Y07/Y10 coverage; this one-artifact,
one-vendor study does not complete the full product or broader Y12 program.

## Next study work

The concrete blocker is the correctness oracle. Before another comparison:

1. Freeze the required public API and distinguish required behavior from
   implementation choices the specs leave open.
2. Test observable behavior without private-state manipulation or incidental
   message wording; demonstrate acceptance of legitimate alternatives and
   rejection of plausible mathematical errors.
3. Freeze the revised oracle and any new allocation before launching new subjects.
   Preserve this pair and its original scores as a separate study version.

This is a proposed follow-up, not completed oracle work or authorization for more
model calls. General hardening and preparation recovery are not prerequisites.
