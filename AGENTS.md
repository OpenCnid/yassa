# AGENTS.md — yassa

Yassa measures how agent skills affect performance on user-defined tasks, using
Inspect AI. For skill-builder comparisons, the evidence comes from fresh agents
using the generated packages on held-out work. Dovetail is the first subject;
its relative performance is an empirical question.

This file guides agents developing yassa. Evaluated agents receive only the
context declared by their study.

## Repository map and navigation

The repository implements simulated Inspect fixtures, the original bounded
native Codex comparison, and configurable native file studies. See
[README.md](README.md) for usage, [the simulated milestone](docs/milestone-1.md),
[the native fixture](docs/native-fixture.md), and
[native v2](docs/configurable-native.md) for their measured scope.

```text
yassa/
|-- AGENTS.md          Development entry point and repository index
|-- ARCHITECTURE.md    Implemented boundaries and remaining technical design
|-- README.md          Setup, run, checks, and document navigation
|-- SPEC.md            Requirements, study design, and open decisions
|-- HANDOFF.md         Current development state and next milestone
|-- pyproject.toml     Package, CLI, exact direct dependencies, and check configuration
|-- uv.lock            Complete resolved dependency pins and hashes
|-- src/yassa/         Preparation, plans, Inspect execution, evidence, scores, reports
|-- studies/           Synthetic study definitions and supplied-input fixtures
|-- runtime/codex/     Pinned container recipe, controlled config, boundary probe
|-- tests/             Contract and Inspect integration checks
`-- docs/              Milestone evidence and implementation limitations
```

Start with [README.md](README.md), then follow the relevant route:

| Work | Starting point |
| --- | --- |
| Continue development in a fresh session | [HANDOFF.md](HANDOFF.md) |
| Run or modify the implemented fixture path | [README usage](README.md#run-the-fixture) and [implemented boundaries](ARCHITECTURE.md#implemented-fixture-milestone) |
| Run or modify the native Codex comparison | [Native usage](README.md#run-the-native-codex-fixture) and [native boundaries](ARCHITECTURE.md#implemented-native-codex-fixture) |
| Configure or extend native file studies | [Native v2 guide](docs/configurable-native.md) and [implemented runner](ARCHITECTURE.md#implemented-configurable-native-runner) |
| Native catalog enforcement and failed captures | [Context control and evidence](docs/native-context.md) and [implemented boundary](ARCHITECTURE.md#implemented-native-context-control) |
| Guided preparation and answer rounds | [Preparation guide](docs/guided-preparation.md) and [implemented preparation](ARCHITECTURE.md#implemented-guided-preparation) |
| Reconciliation pilot and consumer baseline | [Pilot design and evidence](docs/reconciliation-pilot.md) and [baseline contract](docs/configurable-native.md#consumer-baseline) |
| Reconciliation work after the pilot ceiling | [Sensitivity preparation](docs/reconciliation-sensitivity.md), [event checker](src/yassa/reconciliation.py), and [constructed cases](src/yassa/reconciliation_templates.py) |
| Package reuse efficiency work | [Implemented guide](docs/package-reuse.md), [assessment and proposal](docs/package-reuse-proposal.md), and [technical boundary](ARCHITECTURE.md#package-reuse-efficiency-milestone) |
| Study preparation and user interaction | [SPEC section 3](SPEC.md#3-helping-the-user-define-a-study) |
| First Dovetail study and its two input conditions | [SPEC section 13](SPEC.md#13-first-dovetail-study-decisions-still-open) |
| Sampling, sensitivity, or scoring | [SPEC section 7](SPEC.md#7-experimental-sensitivity-and-selectable-inference-budgets) and [section 8](SPEC.md#8-scoring-recorded-work) |
| Components and interfaces | [Architecture component map](ARCHITECTURE.md#component-map-and-api-boundaries) |
| Execution, isolation, and evidence | [Run lifecycle](ARCHITECTURE.md#run-lifecycle) and [access boundaries](ARCHITECTURE.md#access-and-execution-boundaries) |

Fan out from this file as far as the work needs, and no further. Keep the map
aligned with actual files; the proposed source tree belongs in
[ARCHITECTURE.md](ARCHITECTURE.md#repository-map). Add linked guidance or a scoped
`AGENTS.md` when an implemented area needs distinct instructions. Do not create a
guide in every directory or require unrelated documents for each task.

## Establish the task and its sources

- Follow the current user request and applicable higher-priority instructions.
- Use the navigation above to read the relevant requirements and design. Read
  the study definition when working on an experiment.
- Keep accepted requirements, proposals, open decisions, and observed results
  distinguishable. Hypothetical examples do not establish defaults or findings.
- If a referenced document is absent, identify any material information gap and
  continue work supported by the current request and repository evidence.
- Maintain requirements in `SPEC.md` and technical design in `ARCHITECTURE.md`;
  link to those details from this guide rather than duplicating them.

## Work with the available harness

- Inspect the working directory, repository state, shell, permissions, and
  available tools before choosing commands or integrations. Discover capabilities
  in the current session; tool names, installed skills, and local paths from an
  earlier session do not establish availability.
- Check the installed Inspect version and relevant official documentation before
  relying on framework behavior. Reuse its supported execution primitives.
- When delegation is authorized, give each agent a bounded task, input locations,
  and acceptance criteria. Provide evidence needed to investigate; keep expected
  winners or verdicts out of the investigative context. Check shared filesystem
  access before describing a run as isolated.

## Preserve the experiment

- Resolve subject packs and dependencies from the study's pinned external
  sources. Keep Dovetail source skill text outside the yassa repository.
- Build trial contexts from explicit study inputs. Keep repository instructions,
  personal configuration, unrelated installed skills, and development notes out
  of subject contexts unless the study explicitly includes them.
- Enforce access boundaries in the harness. A fresh conversation alone does not
  protect held-out cases, scoring code, answer keys, or other arms' artifacts.
- Base final scores on recorded work. Prefer deterministic checks; final model
  grading uses a different model family from the subject. Internal evaluators in
  a skill's workflow remain part of the treatment.
- When changing a checker, verify acceptance of legitimate alternatives and
  rejection of plausible wrong outputs against the stated task requirements.
- Preserve original artifacts, logs, scorer versions, and failed attempts. Record
  corrections and retries explicitly so their effect on the result is auditable.
- Keep supplied originals, prepared derivatives, and input-preparation conditions
  traceable through the run and report, following the study's declared design.

## Verify changes

Select checks relevant to the changed behavior. Establish executable commands
from repository configuration or verified documentation before running them.

Use `uv sync --locked` for setup. Verified checks are `uv run --locked pytest -q`,
`uv run --locked ruff check src tests runtime`, and
`uv run --locked ruff format --check src tests runtime`; their configuration is in
[pyproject.toml](pyproject.toml). `git diff --check` checks patch whitespace.
The suite uses actual Inspect tasks with an explicitly simulated provider and
pure native-adapter checks. It makes no live model calls. Native behavior requires
the separately recorded Docker/Codex integration evidence.

For documentation changes, check affected local links and anchors,
current/proposed path labels, cross-document consistency, and Markdown formatting.
Preserve study fixture byte pins when changing supplied materials; a source
revision needs a deliberate new hash. Do not write run artifacts into this checkout.

Report what changed, which checks actually ran and their observed results, and
any material unresolved limitation. Distinguish planned checks from executed
checks and proposed architecture from implemented behavior.
