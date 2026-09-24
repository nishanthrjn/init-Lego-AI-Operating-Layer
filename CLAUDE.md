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
