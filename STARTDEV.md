# Start development

Begin implementing yassa. Inspect the repository, explain the first implementation
plan, then carry that milestone through working code and verification.

This is the build kickoff. [AGENTS.md](AGENTS.md) provides standing development
guidance; [SPEC.md](SPEC.md) owns requirements; [ARCHITECTURE.md](ARCHITECTURE.md)
owns the technical design.

## Establish the starting point

- Read AGENTS.md and [README.md](README.md), then the relevant specification and
  architecture sections. Focus on study preparation, execution routes, acceptance
  evidence, the first Dovetail study, component boundaries, and the run lifecycle.
- Inspect the actual checkout, existing changes, dependencies, and available
  runtimes. At this handoff the repository contains design documents; verify its
  current state before choosing work or commands.
- Separate accepted requirements from proposals and unresolved choices. In
  particular, testing both user-supplied and yassa-prepared inputs is accepted;
  specific models, datasets, sample counts, and the initial runtime remain open.

## Explain the plan before editing

Give a short account of:

1. The observed starting point and the first milestone's concrete outcome.
2. The components and data flow needed to deliver it.
3. Decisions needed now, their rationale, and choices that can remain deferred.
4. The checks that will establish completion, including relevant failure cases.

Then proceed. Resolve routine, reversible engineering choices from repository
evidence and official documentation, recording material decisions in the owning
document. Ask only when missing information materially affects the work; keep
questions to one or two at a time and continue independent work while waiting.

## Build the first complete path

Use the architecture's proposed starting sequence: establish Inspect task
plumbing with small direct-task fixtures, then connect the builder path:

```text
study inputs -> frozen plan -> builder -> frozen package -> fresh consumer
             -> preserved work -> deterministic score -> descriptive report
```

Select and pin the dependencies actually used. Verify the selected Inspect
primitives and runtime capabilities against current official documentation.
Implement only the components needed for this path; keep remaining study choices
configurable rather than turning the worked example into product defaults.

Exercise both input-preparation routes, retaining their provenance and separate
results. Use SPEC's acceptance evidence to select meaningful checks for common
inputs, held-out access, package identity, failed builds, and deterministic
rescoring. A small descriptive result is sufficient for this implementation
milestone; broader statistical claims belong to a suitably designed study.

Use fixtures and simulated providers to develop and verify local behavior.
Identify simulation explicitly. Native CLI support requires exercising the actual
runtime and its skill-loading behavior; an API-only run establishes its own
execution route. Use live calls within the session's authorized resources and
report any capability that remains unverified.

## Close the milestone

Deliver the working path, reproducible setup/run/check commands, and an example
report linked to its evidence. Update the affected repository map and document
implemented boundaries accurately. Report what ran, what passed or failed, any
remaining limitation, and the next bounded implementation step. Keep fixture
results distinguishable from measurements of Dovetail or another real builder.
