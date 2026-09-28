---
name: engineering-implementation
description: >
  Use for substantial feature implementation, architectural changes,
  refactoring, new modules, infrastructure changes, security-sensitive
  changes, or other non-trivial production code. Guides work from
  requirements through design, implementation, verification, adversarial
  review, and simplification.
---

# Engineering Implementation

Approach the task as the responsible senior/principal engineer for this
codebase.

Do not treat the requested implementation as merely a code-generation task.

## Understand first

Before changing production code:

1. Inspect the governing specifications, ADRs, module documentation,
   existing contracts, relevant implementation, and tests.
2. Determine current behavior.
3. Identify the requirements governing the requested change.
4. Resolve important contradictions from repository evidence where possible.
5. State assumptions only when necessary.

Do not ask the user questions when the repository provides enough evidence
to make a reasonable engineering decision.

## Derive the design

Derive the solution from requirements and first principles.

For a substantial change, reason about whichever of these are relevant:

- domain invariants,
- architecture boundaries,
- ownership,
- public contracts,
- state transitions,
- trust boundaries,
- authorization,
- validation,
- persistence,
- consistency,
- concurrency,
- idempotency,
- retries,
- timeouts,
- partial failure,
- resource limits,
- observability,
- compatibility,
- migrations,
- security,
- operability.

Do not mechanically introduce every item above. Apply engineering judgment.

Prefer the smallest design that fully satisfies current requirements.

Avoid:

- speculative abstractions,
- unnecessary interfaces,
- unnecessary factories,
- premature generalization,
- architectural layering without a real boundary,
- duplication of existing concepts,
- framework mechanisms where ordinary language constructs suffice.

## External implementations

External repositories are research material only.

Do not begin implementation by searching for code to copy.

Use external implementations only when they materially help understand:

- a standard,
- protocol,
- compatibility requirement,
- ecosystem convention,
- documented algorithm,
- known failure mode.

Independently justify any borrowed design pattern.

Do not copy implementation simply because a popular project uses it.

## Plan

For non-trivial work, create a concise implementation plan before editing.

The plan should identify, where applicable:

- governing requirements,
- architectural boundary,
- affected modules/files,
- contracts being added or changed,
- important invariants,
- failure behavior,
- required tests,
- validation commands,
- migration/compatibility considerations,
- explicit non-goals.

Keep the plan proportional to the task.

## Implement

Implement incrementally.

Maintain existing architectural boundaries unless changing them is part of
the approved task.

Favor:

- explicit contracts,
- cohesive modules,
- strong typing where supported,
- deterministic domain logic,
- dependency inversion at meaningful boundaries,
- validated external inputs,
- bounded resource behavior,
- clear error propagation,
- observable external operations.

Do not preserve bad existing patterns merely for consistency when doing so
would propagate a defect. If changing them is outside task scope, isolate the
new code and document the limitation.

## Tests

Derive tests from observable requirements and invariants.

Use applicable forms of testing, not every form mechanically:

- unit,
- contract,
- integration,
- architecture,
- property-based,
- concurrency,
- resilience/failure-path,
- security,
- migration,
- end-to-end.

Test meaningful failure paths, not only successful execution.

Avoid tests that merely duplicate implementation details.

## Verify

Run all applicable repository verification available for the affected area,
such as:

- formatter,
- lint,
- static analysis,
- type checks,
- unit tests,
- contract tests,
- integration tests,
- architecture tests,
- security checks,
- conformance checks,
- build/package checks.

Never state that a check passed unless it was executed successfully.

If a verification step cannot be run, say exactly why.

## Adversarial review

Before considering the task complete, review the implementation assuming
it contains defects.

Look for relevant issues such as:

- requirement violations,
- invalid assumptions,
- architectural leakage,
- hidden coupling,
- race conditions,
- non-idempotent retries,
- unbounded work,
- resource leaks,
- timeout omissions,
- inconsistent state after partial failure,
- authorization confusion,
- insecure defaults,
- weak validation,
- backwards-compatibility regressions,
- schema drift,
- observability blind spots,
- fragile tests.

Fix substantive problems found and rerun affected verification.

## Simplify

After correctness is established, inspect the solution for accidental
complexity.

Remove unnecessary:

- abstraction,
- indirection,
- interfaces,
- wrappers,
- factories,
- configuration,
- duplication,
- extension mechanisms.

Do not sacrifice a real architectural boundary or known requirement merely
to reduce line count.

## Complete

Before finishing:

- update relevant documentation,
- create/update ADRs for significant architectural decisions,
- preserve requirement traceability where the repository requires it.

Report concisely:

- what was implemented,
- important design decisions,
- verification actually executed,
- unresolved risks or limitations,
- intentionally deferred work.

A feature is complete only when there is engineering evidence that its
requirements are satisfied.
