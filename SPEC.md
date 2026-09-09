# yassa specification

Status: working draft for discussion, 2026-09-08.

This document records the accepted product direction and proposes requirements
that make it implementable. Sections marked **Accepted direction** reflect the
conversation. Sections marked **Proposal** remain reviewable design choices.
The examples are explanatory, not configured defaults, benchmark results, or
evidence that a capability has been implemented.

Repository state: simulated fixtures, the original bounded native Codex fixture,
and configurable native file studies are implemented.
[README.md](README.md) provides usage and [AGENTS.md](AGENTS.md) the development
index. Python 3.11.16 and Inspect 0.3.263 are selected for this milestone;
[ARCHITECTURE.md](ARCHITECTURE.md#implemented-fixture-milestone) identifies the
implemented boundaries. [Milestone evidence](docs/milestone-1.md) distinguishes
executed fixture checks from unverified real-study capabilities. The
[native fixture](docs/native-fixture.md) records the subsequent Codex comparison. The product
requirements and open Dovetail study choices below remain broader than this path.
The [configurable native milestone](docs/configurable-native.md) supports versioned
task/file contracts, declared checker selection, pinned source bindings, multiple
builds and repeats, and full-plan attempt/deadline admission.
[Guided preparation](docs/guided-preparation.md) now develops rough requests through
explicit JSON decisions into that definition for totals and reconciliation.
General task synthesis and broader task/checker semantics remain outstanding.

## 1. Purpose

**Accepted direction.** Yassa produces recorded evidence that lets people
discriminate between prompt and agent-skill variants under explicit test
conditions. It helps users choose conditions that make a comparison informative.

The organizing question is what the measurements establish about the work under
those conditions. Useful outcomes include observed differences, comparable
performance within a meaningful tolerance, specific failure patterns, and
measurements that do not yet distinguish the variants.

Yassa supports user-defined tasks. It carries experimental-design expertise for
users who lack it, while allowing proficient users to control the study.
Dovetail is the first subject; its performance is an empirical question.

## 2. Scope and commitments

**Accepted direction.**

- Use Inspect AI as the evaluation framework.
- Compare recorded task performance, not the persuasiveness of a skill's claims.
- For builder comparisons, evaluate fresh agents using generated packages on
  held-out work. Structural package checks are useful but insufficient evidence
  of builder quality.
- Resolve Dovetail packs at runtime from pinned external sources. Keep their
  source skill text outside the yassa repository.
- Prefer deterministic final scoring. Model grading is allowed when its model
  family differs from the subject being graded. Internal evaluators used by the
  subject's own workflow remain part of the treatment.
- Keep common prompts byte-identical across comparison arms apart from the
  declared treatment pack. Record the other conditions needed to interpret this
  equality, including host behavior and resources.
- Preserve work as files and retain the evidence behind published measurements.
- Include model families from different vendors in the study program. Identify
  which stages and comparisons each family participates in.
- Help users choose informative test circumstances without requiring a winner.

**Proposal.** Support two related study forms:

1. Direct comparison: task inputs plus a prompt/skill variant produce work to
   score. This includes review, repair, planning, and self-verification tasks.
2. Builder comparison: a build brief plus a builder variant produces a package;
   fresh agents then use the frozen package on downstream tasks.

A study specifies whether it measures explicit skill use, automatic activation,
clarification, execution quality, transfer between environments, or a combination
with separately identifiable results. Success in one does not establish the
others. A native-host comparison and a comparison in a common workbench are
different studies when host behavior changes.

## 3. Helping the user define a study

**Accepted direction, clarified 2026-09-08.** Users may start with a rough request,
underspecified success criteria, and no tasks or examples. Yassa carries the work
of developing that input into a runnable study. Sufficient input proceeds without
an obligatory interview; missing information prompts focused follow-up questions,
normally one and never more than two at a time. Neither path requires the user to
know statistical terminology or prepare benchmark materials.

**Proposal.** Guided and expert paths produce the same inspectable study
definition. Preparation establishes the following from supplied information,
follow-up answers, or explicit proposed assumptions; these are not five mandatory
questions for every user:

1. The decision the comparison should inform and the work that matters.
2. The variants, intended users, tools, and execution conditions.
3. Observable success, relevant failures, and legitimate alternative outputs.
4. The circumstances to investigate and the scope of the intended claim.
5. A compute budget or desired measurement resolution.

Yassa infers details supported by supplied evidence, offers explicit defaults for
routine choices, and asks about decisions it cannot resolve from that evidence.
It distinguishes supplied requirements, inferred facts, suggested choices, and
unanswered questions. Ask when an answer would materially change the task,
success criteria, intended use of the result, or resources. Stop questioning once
there is enough information for the intended trial. Choosing a template never
silently supplies business rules.

**Accepted direction.** Assume a simple study unless the request or follow-up
answers establish a need for greater complexity or stronger evidence. Infer that
need from how the result will be used, supplied constraints, and user preferences;
ask a short follow-up if the distinction matters and remains unclear. User
proficiency, task complexity, and required evidence remain separate considerations.

**Proposal.** A small descriptive trial is a valid completed outcome: show the
observed score, its numerator and denominator, the tested conditions, and resource
use, with a brief explanation of what the number describes. A separate pilot,
power target, or inferential analysis is not required merely to report that trial.
For decisions needing broader or more precise evidence, develop the relevant
task coverage, independent sampling, checker validation, and analysis using
section 7. Study complexity and evidence requirements remain separate choices;
more complicated tasks or larger samples do not automatically justify stronger
claims. The user can inspect and change the proposed scope and depth.

The proposed **Rubric Builder** converts the intended outcome into a task and
evidence contract. The proposed **Dataset Finder** finds or helps construct cases
that exercise that contract. These are responsibilities, not yet decisions about
separate services, agents, plugins, or directories.

Dataset recommendations identify source, version, license/access conditions,
task coverage, available checkers, known limitations, and grouping needed for
sampling or held-out splits. A dataset's popularity or existing score does not
establish its suitability for the user's question.

**Accepted direction.** Support user-supplied and Yassa-prepared study materials.
When suitable tasks or examples are missing, Yassa constructs synthetic tasks and
development examples as needed. Users need not author several worked briefs
before comparing builders. A study may also combine supplied and prepared
materials, retaining the contribution of each source.

**Proposal.** Preserve supplied originals and link any completed, generated, or
adapted material to its sources. The preparation route identifies how material
entered the study; authorship and synthetic/source provenance are separate facts.
User-supplied material may itself be AI-authored, and Yassa may prepare material
from an existing dataset. Apply the same task-contract and checker verification
requirements to both routes.

**Proposal.** Construct only the material needed for the selected scope. Use
stated user facts where available and identify invented scenario rules as
assumptions, not facts about the user's actual work. An unresolved real-world
requirement that changes correctness needs clarification or an explicitly
synthetic scope. Record generator/model identities, prompts, parameters and seeds
where available, generated files, grouping, and selection history. Synthetic
cases describe performance on the constructed conditions; representation of real
work requires additional justification.

Development examples and protected evaluation cases have distinct roles. Apply
the declared split and verify expected outputs/checkers before the fixed
comparison. AI-generated reference answers do not establish correctness merely
by existing; use the verification requirements in section 8. Freeze prepared
materials and use them consistently across arms. A later change follows the
study's revision policy.

Yassa's clarification of the study request is preparation, outside the measured
builder treatment. Measuring a builder's own handling of underspecified requests
requires a declared clarification condition with common underlying user facts
and interaction rules. Preparation must preserve the intended ambiguity in that
condition rather than supplying every answer to the builder.

Before running, the user can inspect the resulting conditions, expected work,
measurement procedure, sampling plan, and estimated resource use. The system
uses the authorization supplied by the user for execution and publication.

**Implemented bounded preparation, 2026-09-08.** `study-draft` and `study-revise`
preserve original requests, answer rounds, supplied bytes, separately recorded
facts/inferences/assumptions/proposals, and unresolved choices. Complete requests
proceed directly; incomplete ones expose at most two questions per round. Explicit
contract acceptance is required for the two supported semantic families. Free-text
facts are recorded, not automatically interpreted or checked for contradiction.
Descriptive scope, prepared inputs, and all template features are identified
routine choices; models, builds, repeats and deadlines are explicit settings.
Broader evidence requests remain unresolved instead of being silently downgraded.
The generated feature suites, independent reference verification, checker probes,
source pins and admitted allocation produce the same native v2 contracts used by
expert definitions. Both routes remain identifiable; `first_dovetail_study`
requires both. This does not yet implement conversational model preparation,
dataset research, arbitrary business-rule synthesis, or a broader pilot.

## 4. Study definition

**Proposal.** Every runnable study has a versioned definition containing the
following information. The serialization and storage layout belong in
`ARCHITECTURE.md`.

| Area | Required information |
| --- | --- |
| Question | Intended use of the result, task scope, intended users, comparison, claim target, and rationale for the selected evidence requirements |
| Treatment | Pack source, immutable revision, dependencies, adaptation, loading method, and control variants |
| Models and hosts | Provider, model identity, available snapshot/version information, host version, configuration, and role in each stage |
| Input preparation | User-supplied, Yassa-prepared, or mixed materials; initial request, clarification record, preparation settings, original/derived artifacts, and authorship/source provenance where known |
| Task contract | Inputs, discoverable requirements, outputs, acceptable alternatives, tools, and constraints |
| Dataset | Provenance, task IDs, groups, eligibility, splits, generation rules, and selection history |
| Sampling | Distinct briefs/tasks, independent builds, execution repeats, allocation, pairing, and scheduling policy |
| Scoring | Scorer identity/version, evidence inputs, score meaning, aggregation, tolerances, and grading method |
| Analysis | Primary comparison, target quantity, weighting, uncertainty method, practical threshold if supplied, and handling of multiple claims |
| Resources | Per-attempt and total budgets, internal-agent accounting, pricing assumptions, and stopping rules |
| Execution boundaries | Allowed contexts, files, services, network access, and protected evaluation material |
| Failures | Model failures, infrastructure failures, invalid cases, missing scores, retry rules, and denominators |
| Publication | Artifacts, logs, report contents, access/redaction rules, and limitations on reproduction |

Definitions distinguish planning estimates from selected settings and actual
usage. Provider aliases are not described as immutable snapshots. Changes to
conditions or scoring create a new identifiable revision.

## 5. Comparisons and experimental conditions

**Proposal.**

- Within a controlled comparison, hold common task files, prompts, tools, host
  configuration, and resource opportunities constant. Record the rendered
  model-facing inputs and any host-generated differences.
- When testing both preparation routes, preserve them as identifiable input
  conditions. Freeze and share prepared inputs across builder arms within each
  matched condition. Input differences between conditions are declared variables,
  not exceptions silently introduced into an otherwise identical comparison.
- Treat complete packages and their declared workflow dependencies as the
  treatment. Record supported adaptations rather than silently rewriting packs.
- Match comparisons on task or brief where appropriate. Interleave or randomize
  scheduling under a recorded policy to reduce time-dependent differences.
- Adaptive conversations may diverge after an identical starting point. Keep
  underlying client facts and response rules common; do not force identical
  transcripts when clarification is being measured.
- Freeze each submitted builder artifact before downstream evaluation. Retain
  every planned build, including unsuccessful ones. Selecting the best of several
  builds is a separate, explicitly budgeted selection policy.
- Declare what business facts consumers receive independently of the generated
  skill. A control denied necessary task facts would measure an information
  difference as well as a skill difference.

Controls are selected to answer the study's question:

| Control | Interpretation |
| --- | --- |
| Another builder or skill | Comparison between active methods |
| Common request without a builder pack | Contribution of a builder pack to skill creation |
| Downstream execution without a generated skill | Contribution of skill assistance during task execution |
| Matched neutral instruction pack | Contribution beyond the specified additional-text control |
| Component ablation | Effect of removing the named component under the remaining workflow |

**Implemented bounded control, 2026-09-08.** Native v2 and guided preparation
accept an optional consumer baseline without a generated package. All consumers
in that study receive the same complete task facts and current input files;
assisted consumers additionally receive and invoke the assigned frozen package.
Baseline executions have their own repeat count, no build parent, and separate
reported denominators. Existing definitions retain their original contexts.
This measures package assistance under the declared native built-ins, not a
skill-free runtime. See [baseline semantics](docs/configurable-native.md#consumer-baseline).

Neutral controls record length, tokenizer, register, loading position, and
construction rules. Their text must not introduce the method under investigation.
Multiple neutral variants can test sensitivity to a particular wording choice.
Matching cannot prove that text has zero behavioral effect; the conclusion names
the actual control. Supporting background includes the context-length limitation
identified in [SkillsBench](https://arxiv.org/html/2602.12670v3).

## 6. Benchmark templates and task selection

**Proposal.** Templates contain open variables, development examples, held-out
construction/sampling guidance, output contracts, checker requirements, and
limitations. They support preparation from rough requests; their contents are
not materials the user must supply. The initial candidate families are:

| Template | Main observation | Important task-specific choice |
| --- | --- | --- |
| Data transformation and analysis | Values, records, types, totals, and relevant invariants | Semantics, units, nulls, duplicates, tolerances, and whether order matters |
| Software repair or review | Behavior under tests, regressions, or executable defect evidence | Separate discovering an unknown defect, reproducing a disclosed issue, and repairing it |
| Policy-governed workflows | Final service state and required/permitted action history | Authorization, intermediate actions, exceptions, and escalation |
| Constraint planning and review | Feasibility under a validator; objective value separately | Formal constraints, acceptable plans, and the limits of the modeled environment |
| Grounded writing and synthesis | Mechanical evidence checks plus declared semantic assessment | Source support, coverage, usefulness, and which dimensions require judgment |

These are proposed adaptations, not validated yassa benchmarks. Research
precedents include [DS-1000](https://arxiv.org/abs/2211.11501),
[SWE-bench](https://www.swebench.com/SWE-bench/guides/evaluation/),
[tau-bench](https://arxiv.org/abs/2406.12045),
[PlanBench](https://arxiv.org/abs/2206.10498), and
[ALCE](https://aclanthology.org/2023.emnlp-main.398/).

Separate two legitimate selection purposes:

- **Condition discovery:** explore task features and difficulty to find where
  variants behave differently. Record adaptive selection and report conclusions
  about those investigated conditions.
- **Population estimation:** sample from a defined workload or task source, with
  explicit eligibility and weighting, to estimate performance for that scope.

Discovery can inform a later frozen evaluation. Cases selected after observing a
variant's advantage do not become an unbiased workload sample. Held-out groups
follow the intended generalization: new input rows, new problems, new repositories,
or new domains are different claims. Renaming or paraphrasing a case does not
necessarily create a new independent group.

For clarification studies, templates distinguish complete briefs, omitted but
discoverable facts, and decisions explicitly delegated to the builder. Delegated
choices are checked against acceptable outcomes, not a hidden arbitrary
preference. Report downstream quality and interaction burden separately. A fixed
answer bank measures a narrower interaction than a natural-language client;
simulated clients do not establish performance with real inexperienced users.

## 7. Experimental sensitivity and selectable inference budgets

**Discussion status, 2026-09-08:** the user endorsed the proposed sensitivity
controls in principle. Scope, resolution, and resource allocation remain the
organizing choices, with budget-first, resolution-first, and expert routes.
Numerical defaults, supported statistical procedures, and the first study's
allocation remain open; the detailed requirements below are still proposals.

A sampling plan exposes three separate choices:

1. **Scope:** what conditions, tasks, builds, users, or environments the result is
   intended to describe.
2. **Resolution:** a meaningful score difference, desired interval width, or an
   explicitly exploratory objective.
3. **Resources:** compute/time available and how it is allocated.

Sample count changes precision under the analysis assumptions. It does not, by
itself, expand the scope represented by the selected cases. A difference worth
acting on is supplied or justified for the user's task, not derived from whatever
sample count happens to be affordable. This follows the distinction between
resource, precision, and power justifications in
[Lakens, Sample Size Justification](https://lakens.github.io/statistical_inferences/08-samplesizejustification.html).

### 7.1 User controls

Offer the following routes without hardcoded claims such as "publication grade":

| Route | User supplies | Yassa returns |
| --- | --- | --- |
| Budget first | Maximum spend/time and comparison scope | Feasible allocations and estimated sensitivity under stated assumptions |
| Resolution first | Meaningful difference or target interval width | Estimated observations and cost for the selected statistical objective |
| Expert | Briefs, builds, tasks, repeats, strata, and analysis | Explicit plan, resource estimate, and supported interpretation |

These are available controls, not an obligatory setup questionnaire. Following
section 3, Yassa can propose a small descriptive allocation within the user's
resource constraints when no precision target is needed. Record that choice and
report observed results without requiring the user to invent a statistical goal.

Power, confidence/coverage level, and practical importance are separate concepts.
Power describes the chance that the planned procedure detects an assumed real
effect. An interval's coverage concerns the procedure across repeated studies.
Neither is the probability that a named builder is best. Numerical defaults for
these settings remain open.

### 7.2 What additional runs buy

| Allocation | What it investigates |
| --- | --- |
| Repeated execution of a frozen skill on the same task | Response variability under fixed conditions |
| More independently generated skills for one brief | Builder variability for that brief |
| More distinct held-out tasks | Task coverage within the declared source or conditions |
| More independently selected build briefs | Variation across requests to the builder |
| Additional named models, hosts, or domains | Performance in those additional environments |

Record separate identifiers for input-preparation condition, domain,
source/problem group, brief, build, downstream task, and execution repeat.
Related supplied and prepared versions retain their shared problem-group identity;
a change of preparation route does not create an independent problem. Repeated
use of one skill is not repeated sampling of builder outputs. Tasks shared across
multiple generated packages can
create crossed dependencies, so the structure need not be purely nested.

Use paired differences where appropriate, and account for the independent groups
and sources of variation represented by the design. Repeated responses reduce
execution noise but cannot eliminate task-selection uncertainty.
[Miller, Adding Error Bars to Evals](https://arxiv.org/html/2411.00640v1)
provides the LLM-evaluation foundation for this distinction. The broader concern
about sampling multiple sources of experimental variation also appears in
[Bouthillier et al., Accounting for Variance in Machine Learning Benchmarks](https://proceedings.mlsys.org/paper_files/paper/2021/hash/0184b0cd3cfb185989f858a1d9f5c1eb-Abstract.html).

### 7.3 Planning and pilot information

Planning estimates use prior compatible evidence or pilot observations about
cost, disagreement, execution variability, and variation between tasks/builds.
With little evidence, present a range of scenarios rather than one precise run
count. Zero observed pilot disagreements do not establish zero population
variance. Pilots also check whether tasks exercise the capability and whether
scores are saturated near universal success or failure.

The study records the pilot's role and separates adapted/exploratory results from
a subsequent fixed comparison. More trials can improve precision without fixing
an irrelevant task or insensitive score. Simulation-based planning is appropriate
for supported designs where a simple formula does not capture the metric and
sampling process; see [Card et al., With Little Power Comes Great Responsibility](https://aclanthology.org/2020.emnlp-main.745/).

**Illustration only.** For independent binary pairs, let `D = score_A - score_B`,
`delta = E[D]`, and `q = P(score_A != score_B)`. Then
`Var(D) = q - delta^2`. A large-sample planning approximation near the null is
`n ~= (z_(1-alpha/2) + z_(power))^2 * q / delta^2`.

For one fixed two-sided comparison, `alpha = 0.05`, power `0.80`, and hypothetical
discordance `q = 0.20`, that approximation gives:

| Difference targeted against zero | Independent paired units, rounded up | Executions with one attempt per arm per pair |
| --- | ---: | ---: |
| 10 percentage points | 157 | 314 |
| 5 percentage points | 628 | 1,256 |
| 2 percentage points | 3,925 | 7,850 |

These calculated examples omit clustering, repeated builds, multiple comparisons,
and adaptive stopping. They are not defaults or a sizing formula for arbitrary
builder studies. Exact/discrete or fuller variance calculations can differ.
Detecting a true five-point effect against zero is also different from proving
that an effect exceeds five points. Paired binary planning is described in
[Stata's paired-proportions methods](https://www.stata.com/manuals/pss-2powerpairedproportions.pdf).

### 7.4 Analysis and stopping

- Declare the quantity being estimated, its units, task/domain weights, primary
  contrast, and scope before the fixed comparison.
- Retain arm-level results and paired differences. Estimate uncertainty for the
  difference directly rather than using overlap of separate arm intervals.
- Distinguish population uncertainty from execution/build variability conditional
  on a fixed set. Results for a complete finite suite can be reported directly;
  broader claims still need a sampling or modeling justification.
- Do not treat a generic bootstrap or a large deployment count as a solution to
  having very few independent briefs. Supported methods must state assumptions
  and be checked on simulations reflecting the intended dependency structure.
  Few-cluster and multiway issues are documented by
  [Cameron and Miller, A Practitioner's Guide to Cluster-Robust Inference](https://faculty.econ.ucdavis.edu/faculty/cameron/research/Cameron_Miller_JHR_2015_February.pdf).
- Report descriptive results even when a calibrated inferential analysis is not
  supported. Do not manufacture a confidence interval or an automatic ranking.
- Declare treatment of multiple primary contrasts and simultaneous domain claims.
  Exploratory comparisons remain identifiable.
- Support fixed sampling plans first. Adding an outcome-dependent sequential
  option requires a method valid for its sampling unit and stopping rule.
  Operational cancellation or budget exhaustion is recorded; it is not evidence
  that a statistical stopping criterion was met.

Ordinary fixed-sample intervals cannot be repeatedly inspected until a preferred
result appears while retaining their nominal coverage. Confidence sequences are
one possible foundation for a later sequential mode, subject to their assumptions:
[Howard et al., Time-uniform confidence sequences](https://arxiv.org/abs/1810.08240).

### 7.5 Claim language

Reports distinguish observed score differences, statistical evidence of a
difference, practical importance, and practical equivalence. These are not
necessarily mutually exclusive: a small detectable difference may be within a
predeclared acceptable tolerance.

An inconclusive result is not equivalence. Equivalence requires justified bounds
and an appropriate procedure. For example, standard two-one-sided tests at 5%
use an appropriate 90% interval within the equivalence bounds; this is distinct
from a 95% interval for a conventional two-sided difference test.
[Lakens, Equivalence Tests](https://pure.tue.nl/ws/portalfiles/portal/80918653/lakeequi2017.pdf)
describes this distinction. The estimator must still match yassa's study design.

Every claim identifies the measured conditions, sampling scope, scoring method,
effect/uncertainty where supported, and remaining unresolved differences. Sample
size alone never licenses a claim about untested domains or future model versions.

## 8. Scoring recorded work

**Proposal implementing the accepted scoring preference.**

- Score frozen output files, patches, service state, and recorded actions as
  required by the task. Self-reported success is not execution evidence.
- A deterministic score has a deterministic path from recorded evidence to value.
  LLM extraction, semantic matching, or entailment inside that path makes the
  score model-assisted, even if the final comparison is a Boolean operation.
- Define schemas, units, tolerances, required/optional fields, acceptable
  alternatives, and partial credit from the task contract. Ignore irrelevant
  formatting or ordering unless the task requires it.
- Validate checkers with successful alternatives and plausible wrong outputs.
  Include both missed failures and mistaken rejection of valid work in checker
  evaluation. AI-authored checkers and answer keys need the same verification.
- Keep final checker code and protected answers outside the subject's accessible
  environment. Score the submitted artifact, not a checker result the subject
  could modify.
- Preserve component scores and the reason for each failure. Declare any overall
  success rule and weights; adding many easy subchecks must not silently change
  the meaning of the aggregate.
- Distinguish narrow evidence from broader conclusions: reproducing one defect
  does not certify a whole repair; existing citations do not establish support;
  valid plans satisfy the modeled constraints, whose coverage must be stated.

Model-graded dimensions identify the grader family, model/version, prompt,
rubric, input evidence, and raw judgments. Compare arms using a common grader
within each subject-family comparison, obscure treatment labels where possible,
and retain calibration evidence. Rotating graders across subject families does
not automatically make their raw scores comparable. How to choose a final grader
for work jointly produced by several model families remains an explicit decision.

Mechanical and model-graded dimensions remain identifiable even if a declared
composite is reported. Model grading follows the accepted different-family rule;
internal checking performed by the evaluated skill is recorded as treatment work.

## 9. Execution, resource accounting, and failure handling

**Proposal.** Distinguish total research expenditure from the budget given to
each evaluated attempt. More attempts change sampling; more reasoning or tools
per attempt change the execution conditions being measured.

Record model calls, input/output and available reasoning usage, cache behavior,
tool use, duration, internal-agent work, and configured limits. Report actual
usage alongside estimates and mark unavailable fields rather than assuming zero.
Separate build, deployment, benchmark preparation, and external grading costs.
Cost comparisons name pricing assumptions and the number of downstream uses over
which build cost is amortized. Equal resource ceilings do not imply equal usage.

Each attempt has a stable identity, parent build/task association where relevant,
completion status, artifacts, and failure reason. Interrupted or retried attempts
remain distinguishable from independent experimental repeats.

| Event | Proposed primary handling |
| --- | --- |
| Incorrect work, refusal, or budget exhausted without required output | Task failure, with the evidence retained |
| Builder does not submit a usable package | Count in the end-to-end builder outcome; do not discard that build |
| Provider/service or harness failure | Apply the declared infrastructure policy; retain original and retry records |
| Invalid benchmark case or faulty checker | Record a correction, apply it consistently across affected arms, and version the revised analysis |
| Missing external grade | Report missingness and its denominator effect; do not quietly report only successful grading calls |

For a proposed all-required-work success metric, failed builds contribute failures
to their planned downstream uses. Other metrics must specify how such builds
enter their denominator. A conditional score among valid builds may accompany
the end-to-end result, with its different population stated.

Fresh conversations are required where independence of context is intended, but
are not sufficient isolation. Enforce the declared filesystem, configuration,
service, network, and state boundaries. Include no repository instructions,
personal skills, development notes, held-out answers, or other arms' artifacts
unless the study explicitly names them as inputs.

## 10. Evidence and reporting

**Proposal.** A run's evidence connects the study revision to source revisions,
rendered inputs, generated packages, individual attempts, submitted work, scores,
and analysis. All stages use stable identifiers and content hashes where useful.

Source packs and any artifacts reproducing their source text remain outside the
yassa source repository. Run storage preserves original files and logs; a report
does not replace them. Access and redistribution constraints are recorded.
Redacted/public derivatives identify what was omitted while preserving the
original under the applicable access policy.

Reports contain:

1. The question, tested conditions, and measured scope.
2. Planned and completed counts by brief, build, task, repeat, model, and arm.
3. Score definitions, grading provenance, denominators, and corrections.
4. Observed differences, supported uncertainty, and practical thresholds.
5. Domain and input-preparation condition breakdowns, and cost/quality results.
6. Failure examples with evidence, plus missing or unsupported measurements.
7. Artifact/log references and instructions for supported replay or rescoring.

Match presentation depth to the user's purpose. A quick trial can lead with the
observed number, counts, synthetic/source scope, and cost, with detailed evidence
available through links. A more demanding study exposes its design and analysis
in greater detail. Both retain original evidence and identify scoring provenance;
a concise report does not imply stronger evidence than was collected.

Recomputing a deterministic score from preserved evidence is different from
rerunning a stochastic agent. Provider changes or unavailable external resources
can limit reruns even when local sources and configuration are pinned.
Publishing a run does not change its inferential scope.

## 11. Inspect integration requirements

**Proposal.** Reuse Inspect's supported tasks, datasets, agents/solvers, scorers,
sandboxes, limits, and evaluation logs. Yassa adds study guidance, treatment and
artifact provenance, sampling/analysis policy, and the connection between builder
outputs and downstream trials. The implementation boundary belongs in
`ARCHITECTURE.md`.

The implementation must select and record an Inspect version, verify the APIs
actually used, and test that configuration preserves yassa's declared semantics.
Current official documentation establishes the following available mechanisms,
not a verified local installation:

- [Tasks](https://inspect.aisi.org.uk/tasks.html) and
  [datasets](https://inspect.aisi.org.uk/datasets.html) provide evaluation recipes,
  sample metadata, and file inputs.
- [Agent Bridge](https://inspect.aisi.org.uk/agent-bridge.html) supports external
  agents; bridged execution still needs context, tool, and usage verification.
- [Custom scorers](https://inspect.aisi.org.uk/custom-scorers.html) retain scores
  and evidence metadata. Unscored samples are excluded from aggregates, requiring
  explicit handling of missing results.
- [Metrics](https://inspect.aisi.org.uk/metrics.html) include grouping, clustering,
  and epoch reducers. Preserve raw results and verify that reduction matches the
  intended unit of analysis; a default reducer is not a study design.
- [Limits](https://inspect.aisi.org.uk/setting-limits.html) and
  [eval sets](https://inspect.aisi.org.uk/eval-sets.html) support execution budgets,
  resumption, and retries. Configure retention of failed attempts explicitly.
- [Early stopping](https://inspect.aisi.org.uk/early-stopping.html) provides
  scheduling hooks; statistical validity depends on the implemented method.
- [Sandboxing](https://inspect.aisi.org.uk/sandboxing.html) supports execution
  boundaries. Verify provider-side and host-side tools as well as container
  access; a container's network policy does not cover every tool.

### 11.1 Execution routes

**Clarified design intent; a bounded native Codex fixture is implemented.** Select the
execution route per stage according to the behavior being measured:

| Route | Use | What executes |
| --- | --- | --- |
| Model API | Prompt/response comparisons that do not require an agent runtime | Model requests through Inspect's provider interface, with responses preserved as artifacts |
| Inspect-native agent | Tool-using tasks in a common declared workbench | An Inspect agent loop with the selected tools and context |
| Native agent CLI | Skill behavior in a specified product runtime | A pinned CLI inside the benchmark sandbox, with declared configuration, skills, tools, and output collection |

Codex CLI and Claude Code are intended native-runtime targets. They are provisioned
as the selected trial's agent runtime, not automatically exposed as a collection
of tools that every subject can choose among. Additional runtime adapters require
their own capability and isolation verification. Build and consumer stages can
select different routes, but their identities and the resulting claim are explicit.

Native CLI execution still makes model API calls. Inspect's
[sandbox Agent Bridge](https://inspect.aisi.org.uk/agent-bridge.html) supports
routing those calls through its model provider and documents Codex CLI and Claude
Code examples. Official runtime documentation provides non-interactive entry
points: [Codex execution](https://learn.chatgpt.com/docs/non-interactive-mode) and
[Claude Code programmatic execution](https://code.claude.com/docs/en/headless).

Provision the selected runtime version and required dependencies in the declared
sandbox environment. Supply controlled configuration and only the study's input
materials; preserve the intended skill-loading behavior. A mode that disables
skill discovery is unsuitable for a study claiming to test native discovery.
Capture actual host-added context, tool activity, internal calls, and final files
to the extent required by the adapter's supported measurement contract.

Reading skill text into a model prompt can test that instruction treatment. A
claim about native package loading, scripts, resources, or activation requires
the corresponding runtime behavior to be exercised. Missing runtime capabilities
are identified before the substantive comparison rather than silently replacing
the skill's workflow. The execution boundary is described in
[ARCHITECTURE.md](ARCHITECTURE.md#execution-use-inspect-to-perform-attempts).

## 12. Acceptance evidence for an implementation

**Proposal.** The first working implementation must demonstrate the applicable
behaviors below with small fixtures before running a substantive comparison.
The applicable fixture checks are implemented under [tests](tests); see
[milestone evidence](docs/milestone-1.md) and [native evidence](docs/native-fixture.md)
for observed coverage. Additional providers/runtimes, model grading, and
inferential capabilities remain future acceptance work.

- Complete study requests proceed without redundant intake; underspecified ones
  receive at most two follow-up questions at a time and can use generated tasks
  and examples. Preparation preserves assumptions, provenance, and held-out
  boundaries in both small descriptive trials and more demanding studies.
- User-supplied and Yassa-prepared inputs each complete the build-to-score path.
  Supplied originals and derived materials remain traceable; results retain
  preparation conditions and common-input equality within matched comparisons.
- A direct comparison preserves common inputs and changes only the declared
  treatment; any host-generated differences are recorded.
- A builder trial's frozen package is the package consumed downstream, and
  each score can be traced back through the correct build and study revision.
- The subject cannot read hidden evaluation material, other arms' work, or
  undeclared development/personal configuration through available interfaces.
- Checker fixtures accept legitimate alternatives and reject relevant wrong
  outputs, including failures that preserve superficial formatting or totals.
- Deterministic rescoring of preserved artifacts gives the same scores under
  the same checker version; changed scoring preserves the original result.
- Failed builds, task failures, infrastructure retries, and missing grades retain
  the correct distinct status and declared denominator behavior.
- Different-family final grading is enforced where model grading is selected,
  and mechanical and model-assisted scores retain their provenance.
- Planning arithmetic agrees with known analytical cases. Supported inferential
  methods are evaluated on simulated null/effect cases and the dependency
  structures they claim to handle, including limited independent groups.
- Resource caps and internal-call accounting behave as declared, with unavailable
  usage reported explicitly.
- Reports preserve raw counts, grouping, uncertainty assumptions, selection
  history, and scope; they do not convert inconclusive findings into equivalence.

Verified fixture check commands are maintained in
[README.md](README.md#verify-changes) and [AGENTS.md](AGENTS.md#verify-changes).
The milestone uses the declared all-required-work rule with one binary score per
planned use. Failed builds contribute zero to their planned downstream uses;
infrastructure failures remain missing. Reports show confirmed successes,
planned denominators, and missing counts separately, without imputing missing
work or pooling preparation conditions. It makes no inferential claim.

## 13. First Dovetail study: decisions still open

**Accepted direction:** compare skill builders across multiple domains, with
Dovetail and verified first-party builders as candidates. The first Dovetail
study will test both user-supplied briefs/examples and Yassa-prepared
briefs/examples. The synthetic native fixture exercises both routes; the broader
multi-domain study remains planned.

**Open:** exact builder revisions and dependency boundaries; creator/consumer
model matrix; native hosts versus a shared workbench; domains and source datasets;
automatic activation versus explicit loading; clarification variants; primary
outcome and practical threshold; control construction; budget allocation; and the
initial supported statistical procedure.

The prior worked comparison, its sample counts, and its invented result table
establish none of these settings. A purported official comparator, including any
DeepSeek builder, must have its first-party provenance verified before being
identified as official in a study.

### 13.1 First supported study candidate

**Proposal for the broader study, 2026-09-08.** The
[native fixture](docs/native-fixture.md) implements a bounded subset. Begin with
one native-runtime builder comparison covering both accepted input-preparation
conditions, then expand the supported study program to additional domains and
vendor families. The runtime, task family, and other settings below remain
proposals.

The proposed question is: under fixed build and use conditions, does Dovetail's
builder produce packages that enable more successful held-out data-processing
work than the official Codex builder?

| Design element | Proposed starting point |
| --- | --- |
| Creation runtime | Pinned Codex CLI with one fixed supported OpenAI model/configuration across creation arms |
| Candidate creation arms | Dovetail builder and declared dependencies; official creator; a declared Dovetail-matched neutral control; common creation request without a builder pack |
| User input | A comparison request and available context; worked tasks and examples are optional |
| Prepared build inputs | Both user-supplied briefs/examples and Yassa-prepared briefs/examples as identifiable conditions, with original/derived provenance and explicit assumptions |
| Work | Tasks such as normalization, reconciliation, joins, and grouped summaries, with explicit semantics and file outputs |
| Generated artifact | Complete skill package, including scripts/resources where produced; every independent build retained |
| Consumer runtime | Fresh Codex CLI sessions under common conditions, explicitly invoking the assigned frozen package |
| Held-out trials | The same eligible unseen cases across arms, grouped by brief and underlying problem family |
| Primary measurement | Successful task completion under deterministic checks, including the declared treatment of failed builds |
| Additional observations | Results by preparation condition, component failures, independent-build variation, repeated-execution variation, and preparation/build/use costs |
| Downstream baseline | The same consumer and complete task facts without a generated skill |

Exercise both input conditions in the first study:

- **User-supplied:** use supplied briefs and examples, preserving originals and
  resolving material gaps when necessary. Sufficient material proceeds directly.
- **Yassa-prepared:** start from a comparison request and available context, ask
  one or two follow-up questions at a time as needed, and prepare the briefs and
  examples, including synthetic material where appropriate.

Compare the selected builders within each condition using the same frozen input
material. Report those contrasts separately; any combined result declares its
weighting. A raw difference between conditions can also reflect their different
tasks or information. Measuring preparation's own effect would need a comparison
designed for that question. Mixed inputs retain artifact-level provenance instead
of being relabeled as wholly supplied or wholly generated.

This first-study commitment to test both routes does not require every future
user trial to include both. Users do not have to supply examples or request several
independent briefs. Select arms and allocation for the intended question: one
brief and a small held-out set can produce a descriptive result for that scenario;
broader builder claims require the corresponding sampling and analysis. The active
builder comparison and the comparison against extra neutral text answer different
questions, so report only the contrasts actually run.

Builder clarification and automatic activation remain experimental conditions
to add explicitly. Helping a novice prepare this study does not itself measure
the competing builders' assistance for novices or native discovery quality.

Before measuring builder differences, verify that each declared workflow can
actually execute in the selected CLI, including referenced skills, validators,
scripts, and any internal evaluator tools. A Codex-oriented pack may reference
capabilities specific to another Codex surface; package naming alone is not
compatibility evidence. Required adaptations receive their own identity.

A small descriptive trial can complete the user's request. Where a more precise
or broader comparison is intended, use separately identified pilot evidence as
needed to estimate costs and variation across briefs, builds, and task executions.
Select the allocation using section 7; no universal sample count is assigned here.
A smoke run establishes integration behavior. A scored trial additionally reports
observed performance on its cases, with broader claims requiring support.

This initial native Codex comparison supports claims about those build/use
conditions and sampled data-processing requests. It does not satisfy the full
two-vendor, multi-domain program by itself. Add Claude Code as a separately
verified runtime and design comparisons within that runtime before attributing
cross-runtime differences to a builder. Cross-family consumption of generated
packages is a further transfer question when that is the intended comparison.

## 14. Documentation responsibilities

**Accepted direction from the documentation discussion.**

- `SPEC.md` owns product requirements, measurement semantics, acceptance
  criteria, and explicitly open product decisions.
- [ARCHITECTURE.md](ARCHITECTURE.md) explains the proposed high-level system,
  component/code map, interfaces, dependency boundaries, invariants, and
  cross-cutting execution concerns. Distinguish proposed design from implemented
  structure and link to real code as it appears. The structural reference is the user's pinned
  [rust-analyzer architecture document](https://github.com/rust-lang/rust-analyzer/blob/d7c99931d05e3723d878bea5dc26766791fa4e69/docs/dev/architecture.md).
- [AGENTS.md](AGENTS.md) is the development entry point and repository index.
  Include a concise tree of actual relevant files/directories, their purposes,
  and routes to task-specific guidance. Fan out through linked documents and
  scoped guides as far as the work needs, and no further. Keep planned structure
  separate from the current tree; exclude generated/cache detail that adds no
  navigation value. Add local guides when a subtree needs distinct instructions.
- [README.md](README.md) provides project orientation and verified usage as
  those become available.

Requirements and architectural explanations are linked from the agent guide,
not copied into every local guide. Update affected map entries when paths or
responsibilities change. Development guidance remains outside evaluated agents'
contexts unless the study explicitly includes it.

## 15. Next work

- [x] Research experimental sensitivity, sampling units, and supported claim types.
- [x] Produce this reviewable specification draft with research links and open choices.
- [x] Record the sensitivity-control discussion and the user's endorsement in principle.
- [x] Record adaptive study preparation, synthetic examples, and support for simple descriptive trials as well as more demanding studies.
- [x] Include both user-supplied and Yassa-prepared inputs in the first Dovetail study design.
- [x] Select and record the bounded native fixture's sources, model, input conditions, allocation, and deadlines; see [native evidence](docs/native-fixture.md).
- [ ] Resolve the broader first-study choices in section 13.1, including representative work, controls, independent builds, and the intended claim.
- [x] Draft `ARCHITECTURE.md` using the agreed map, boundaries, and invariants style.
- [x] Refine `AGENTS.md` into the repository index and bounded navigation guide.
- [x] Pin Inspect 0.3.263 and implement complete simulated and native Codex fixture paths with preserved evidence and rescoring.
- [x] Validate the account-totals checker and descriptive reporting; execute and audit the separately identified native fixture comparison.
- [x] Generalize the native study definition beyond the fixed account-totals contract, two builder arms, and one build per arm/condition; see [the bounded v2 contracts](docs/configurable-native.md).
- [x] Implement bounded preparation from a rough request into a validated, reviewable native study, with explicit decisions and extended deterministic feature suites; see [guided preparation](docs/guided-preparation.md).
- [ ] Extend preparation beyond the two fixed semantic families, including general task synthesis or research where required by the selected study.
- [x] Implement the no-package consumer control and prepare a synthetic reconciliation pilot with both input routes, distinct feature coverage, two builds per arm/condition and a concrete budget; see [pilot design](docs/reconciliation-pilot.md).
- [x] Execute the selected synthetic reconciliation pilot with two builds per arm/condition and a no-package baseline: 46/46 recorded consumers passed; one harness export failure left four uses missing. The context audit failed on extra runtime plugin skill entries, and the cases reached the score ceiling; see [measured scope](docs/reconciliation-pilot.md#recorded-results).
- [x] Enforce the declared native skill catalog through root preflight and acceptance checks on every recorded root/subagent catalog, with runtime plugins disabled; authenticated validation passed. This does not intercept every model request or attest all upstream context; see [implemented scope](docs/native-context.md#enforced-boundary).
- [x] Preserve bounded raw native exports before path validation and collect independent transcripts/logs, retaining failure attribution and immutable evidence; malformed, credential-containing and uncollected content remain explicitly unavailable. See [capture limits](docs/native-context.md#evidence-when-capture-or-acceptance-fails).
- [ ] Select more informative work after the pilot's score ceiling, with controls and budgets tied to the intended claim.
- [ ] Implement the remaining resource controls, recovery, additional vendor/runtime support, and selected analysis or model-grading methods as their study scope requires.

Research for this draft used primary statistical publications, framework
documentation, benchmark papers, repository evidence, and the exact architecture
reference supplied by the user. Sources were accessed 2026-09-08. The cited
methods inform the proposals; they do not validate an unimplemented yassa design.
