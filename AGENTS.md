# Engineering Principles

This repository is developed from requirements, specifications, contracts,
and first-principles engineering reasoning.

## Core rules

- Correctness, clarity, maintainability, security, and operability take
  precedence over implementation speed.
- Prefer the simplest design that satisfies known requirements.
- Do not introduce speculative abstractions or extension points.
- Preserve architectural boundaries and dependency direction.
- Domain logic must remain independent of infrastructure concerns.
- Public boundaries require explicit contracts and validation.
- External I/O must define timeout, failure, retry, and cancellation behavior
  where applicable.
- Errors must preserve useful causal information.
- Security and authorization decisions must be explicit and externally
  enforceable.
- Do not use global mutable state unless explicitly justified.
- Do not silently swallow failures.
- New dependencies require technical justification.
- Tests must derive from requirements, invariants, contracts, boundaries,
  and failure modes rather than implementation details.
- Significant architecture decisions require an ADR.
- Implementation is incomplete until applicable verification succeeds.

## External code policy

External repositories are prior art, not implementation authority.

They MAY be inspected to understand:

- protocols and standards,
- interoperability requirements,
- ecosystem conventions,
- known failure modes,
- algorithms or published approaches.

They MUST NOT be used as the default source of architecture or implementation.

Before adopting an external pattern, independently determine whether it is
appropriate for this repository's requirements, constraints, security model,
failure model, and architecture.

Prefer authoritative specifications, standards, RFCs, primary documentation,
and first-principles reasoning over copying repository implementations.

## Repository knowledge

Before making a substantial change, inspect the applicable:

- specifications,
- ADRs,
- module documentation,
- security requirements,
- conformance requirements,
- existing public contracts,
- relevant tests.

More specific AGENTS.md files may define module-local constraints.

## Architecture and ownership review

This file is the shared engineering policy for repository coding agents.
Tool-specific entry points reference it; they must not fork this policy.
Canonical specifications and accepted ADRs govern architectural semantics;
skills describe the implementation workflow, not alternative authority.

- REUSE > EXTEND > CREATE. Apply KISS and YAGNI before adding abstraction.
  Prefer deterministic logic, then one model invocation, then workflows,
  then autonomous or multi-agent behavior, only as requirements justify.
- Keep application intent, domain values, orchestration and acceptance criteria
  in the application. Generalization requires independent consumers with the
  same semantics, ownership, authority/effects and failure behavior.
- Consumers use documented public Ports/APIs, not `legoai.reference.*`,
  `legoai.runtime._composition.*` or another owner's private names.
  Owner-internal implementation and focused contract tests are different scopes.
- Concrete adapters, provider SDKs and deployment choices belong in composition
  or adapter code, not domain code. Configuration selects supported variation;
  configuration != authorization, plugin admission or permission to execute code.
- Model/Agent output is data, never authority. Deterministic boundaries enforce
  authorization, disclosure and effects. Preserve explicit unknown/partial
  effects, retry bounds, cancellation and reconciliation; never weaken security
  or effect truth to make a test pass.
- Review SOLID, DRY (one authority for knowledge), KISS, YAGNI, separation of
  concerns and Law of Demeter. Immutable value traversal is not automatically
  a violation. Preserve deliberately independent evaluation fixtures.
- For every new Port/interface, record the semantic owner, independent consumers,
  expected implementations and concrete substitution requirement. Without
  concrete answers, do not introduce it. Read accepted architecture/ADRs before
  changing a boundary; record unresolved decisions instead of inventing semantics.
- Place fixes with their semantic owner: application logic, reusable capability,
  adapter/provider, composition, configuration, governance or deployment.
- Tests must prove observable behavior and failure boundaries. Architecture
  fitness checks need known-bad and allowed controls where practical.

Use the shared implementation workflow in
`.agents/skills/engineering-implementation/SKILL.md` for substantial changes.
Respect the task's validation authority: when the maintainer will run checks,
provide exact commands and keep validation pending until results are supplied.


## Documentation rules
- Do not create new .md files unless asked. Update existing ones instead.
- Plans for a feature go in docs/specs/<yyyy-mm-slug>/ only.
- When a feature is merged: set the spec's status to done and move it to docs/archive/.
- Any significant architectural choice gets a new ADR; never edit an accepted ADR — supersede it.
- After changing behavior, update ARCHITECTURE.md if it is now wrong.