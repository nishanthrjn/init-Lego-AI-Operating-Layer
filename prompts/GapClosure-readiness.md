Act as the **Principal Software Architect, AI Platform Architect, Runtime Architect, Developer Experience Architect, Reliability Engineer, Security Architect, Test Architect, Production Readiness Architect, and Solo-Developer Technical Advisor** for the **Lego AI Operating Layer**.

We have completed a substantial canonical architecture/specification stack and multiple implementation ADRs. Before continuing architecture indefinitely, perform a **deep implementation-readiness, gap-closure, and risk-mitigation review**.

Create:

`planning/IMPLEMENTATION-READINESS.md`

Status:

`PROPOSED — FOR CANONICAL REVIEW`

This document is a **planning / decision-routing artifact only**.

Do NOT implement source code.

Do NOT modify accepted canonical specifications.

Do NOT create additional ADRs during this task.

Do NOT modify ADR-INDEX yet.

Your objective is to determine exactly what remains necessary before:

1. implementation can safely begin,
2. an executable deterministic Lego AI runtime can exist,
3. ForgeAI can begin consuming Lego AI,
4. AI/Agent/Multi-Agent functionality should be added,
5. the first production-capable Lego AI release can be claimed.

---

# 1. Read the Entire Current Project

Review all current accepted artifacts in authority order, including:

* `intent.md`
* `SPEC.md`
* `architecture/ARCHITECTURE.md`
* `contracts/CONTRACTS.md`
* `plugin-spec/PLUGIN-SPEC.md`
* `security/SECURITY.md`
* `evaluation/EVALUATION.md`
* `conformance/CONFORMANCE.md`
* `adrs/ADR-INDEX.md`
* every completed ADR through the latest accepted ADR, including ADR-009
* ADR-010 / ADR-011 drafts if they already exist

Do not trust summaries alone.

Use the actual documents.

Identify contradictions, duplication, missing ownership, undefined mechanisms, premature abstractions, and unnecessary complexity.

---

# 2. Review From Two Equal Perspectives

Do NOT evaluate Lego AI only as a governance/control plane.

Review both:

CONTROL / GOVERNANCE PLANE

* configuration
* security
* tenancy
* state
* Plugins
* resources
* evidence
* authorization
* effects
* evaluation
* conformance

AND:

DEVELOPER / EXECUTION PLANE

* application authoring
* application composition
* developer API
* runtime execution
* concurrency
* cancellation
* local development
* testing
* debugging
* logging/tracing
* packaging
* deployment
* application integration
* AI integration
* Agent integration
* Multi-Agent integration

A platform is NOT implementation-ready merely because the control plane is rigorous.

---

# 3. Evaluate the Major Gaps We Have Identified

Perform an independent review of each.

## GAP-A — Application Authoring / Developer Experience

Determine whether Lego AI sufficiently answers:

> How will a developer actually build an application with Lego AI?

Analyze the desired flow:

Idea
→ define Application
→ choose Capabilities
→ choose/reconcile Plugins
→ configure
→ add domain logic
→ connect Tools
→ define Skills
→ define policies
→ compose runtime
→ validate
→ execute locally
→ test
→ debug
→ package
→ deploy

Determine whether a future ADR such as:

`ADR-014 — Reference Application Authoring and Composition Experience`

is genuinely required.

Evaluate future approaches such as:

* Python API
* builder API
* declarative manifest
* hybrid declarative + Python escape hatch

Do NOT select the mechanism now unless current evidence is sufficient.

State exactly when this ADR should happen.

---

## GAP-B — Execution Supervision / Concurrency

Determine whether current ADRs fully define how actual admitted work executes.

Analyze:

* async task supervision
* bounded concurrency
* cancellation propagation
* timeouts
* shutdown
* backpressure
* orphan detection
* worker ownership
* context propagation
* task cleanup
* background work
* restart interaction

Determine whether a future:

`ADR-015 — Reference Execution Supervision and Concurrency Model`

is necessary.

Do not invent a distributed workflow engine.

Prefer the smallest sufficient runtime mechanism.

---

## GAP-C — Concrete Persistence Realization

ADR-004 defines the persistence semantics.

Determine where the actual datastore decision belongs.

Classify it as either:

* canonical architecture ADR,
* implementation ADR beneath ADR-004,
* ordinary implementation decision.

Strongly prefer lower-level placement unless the technology changes canonical behavior.

Do NOT select the database during this review.

Define required datastore capabilities and decision criteria.

---

## GAP-D — Reference Runtime v0.1 Scope

Define a finite first implementation profile.

This is mandatory.

Derive the smallest useful governed runtime that proves Lego AI.

Seriously evaluate this approximate scope:

* one explicit Tenant
* one administrative Principal
* one Application
* one deterministic Capability
* one Port
* one Plugin
* one Provider
* one Adapter
* one protected Tool/effect
* immutable effective configuration
* durable owner state
* authorization
* resource accounting
* evidence
* retry/reconciliation
* structured logging/tracing
* restart/recovery

Initially exclude unless required:

* Agent
* Model
* Team
* Workflow engine
* RAG
* persistent Memory
* vector database
* message broker
* distributed services
* hostile third-party Plugin execution
* enterprise IAM
* public remote API

For every included capability document:

* why required,
* owning module,
* prerequisite ADR,
* minimum test/proof.

For every excluded capability document:

* why deferred,
* trigger for inclusion.

---

# 4. Establish an Architecture Freeze

The project must stop producing foundational abstractions at some point.

Determine the correct freeze point.

Evaluate a rule similar to:

> Once the foundational protected-execution chain is resolved, no new foundational abstraction may be introduced without evidence from implementation, a failed test/conformance case, ForgeAI, another real application, or measured operational evidence.

Determine whether the freeze should occur after:

* ADR-008,
* ADR-009,
* ADR-011,
* or another dependency-safe point.

Explain why.

Define what “architecture freeze” actually means.

It must NOT prevent bug fixes or justified ADRs.

It SHOULD prevent speculative generic abstractions.

---

# 5. Make ForgeAI the First Architecture Validator

ForgeAI is intended to be the first serious production application using Lego AI.

Determine:

* earliest safe point ForgeAI development can begin,
* which Lego AI modules ForgeAI should consume first,
* which ForgeAI functionality must remain ForgeAI-specific,
* how discovered reusable infrastructure gets promoted into Lego AI,
* how to prevent ForgeAI requirements from automatically becoming generic platform requirements.

Adopt this rule unless contradicted:

`ForgeAI requirement ≠ Lego AI requirement.`

Promotion into Lego AI should require evidence of reusable infrastructure.

---

# 6. Define the Evidence-Driven Abstraction Rule

A new generic Lego AI abstraction should require at least one strong justification:

* canonical semantic requirement,
* at least two independent real use cases,
* repeated implementation duplication,
* demonstrated provider replacement need,
* security/correctness/conformance requirement.

Speculative future reuse alone is insufficient.

Create an explicit anti-overengineering policy.

---

# 7. Testing Must Start With Implementation

ADR-011 / Conformance must NOT imply testing happens late.

Define a day-one implementation test strategy covering:

* unit/invariant tests,
* package/import architecture tests,
* Port contract tests,
* Adapter substitution tests,
* configuration revision tests,
* owner-state tests,
* concurrency tests,
* tenant isolation tests,
* security negative tests,
* Plugin lifecycle tests,
* lost-acknowledgment tests,
* crash/restart tests,
* partial-completion tests,
* retry/reconciliation tests,
* evidence tests,
* migration tests,
* composition tests,
* fault injection,
* eventual conformance suites.

Explicitly separate:

`development testing`

from:

`formal conformance evidence`.

---

# 8. Logging / Observability Baseline

Preserve:

Operational logging/tracing/metrics
≠
mandatory evidence
≠
authoritative owner state
≠
provenance.

Determine the minimum observation capability that MUST exist in the first executable slice.

At minimum evaluate recording:

* Trace ID,
* correlation/causation,
* Execution ID,
* tenant-safe identity,
* configuration revision,
* Plugin/Provider/Adapter versions,
* state transitions,
* authorization decision reference,
* Tool/effect status,
* resource usage,
* latency,
* error category.

Explicitly prohibit ordinary logging of:

* raw Secrets,
* credentials,
* unrestricted sensitive payloads,
* private chain-of-thought.

Determine what ADR-013 can safely defer.

Do not select OpenTelemetry or a logging vendor unless a later implementation decision requires it.

---

# 9. Secret Handling Trigger

Review ADR-010 priority.

Do not automatically make Secrets a mandatory baseline feature.

Instead define this hard gate:

> Before any real credential/Secret is stored, resolved, or consumed by Lego AI, ADR-010 and all prerequisites MUST be resolved and implemented.

Include:

* model API keys,
* GitHub tokens,
* OAuth credentials,
* database credentials,
* cloud credentials,
* external Tool credentials.

Explicitly prevent temporary `.env` handling from bypassing the architecture.

`.env` may eventually be an input mechanism only if it participates in the governed Secret mechanism.

---

# 10. Plugin Isolation Claims

Preserve:

`Python package isolation ≠ security isolation.`

Until ADR-012 is resolved and implemented, define the allowed threat model.

State precisely whether initial Plugins are:

* built-in,
* locally trusted,
* admitted trusted code,
* semi-trusted,
* untrusted.

Do not claim arbitrary hostile Plugin safety until actual isolation exists and is proven.

Define the trigger that activates ADR-012.

---

# 11. Supply-Chain Security

Determine whether ADR-006 and ADR-011 sufficiently own:

* dependency pinning,
* package integrity,
* publisher identity,
* Plugin provenance,
* SBOM,
* dependency scanning,
* vulnerability management,
* signing/attestation,
* release provenance.

Do not create a new ADR if existing owners already cover these correctly.

Identify only genuinely unowned concerns.

---

# 12. Non-Functional Requirements

Define when performance measurements should begin.

Consider:

* startup latency,
* idle memory,
* state commit latency,
* authorization overhead,
* protected invocation overhead,
* Plugin activation latency,
* recovery time,
* concurrent executions,
* trace/log volume,
* persistence growth.

Do not fabricate production thresholds.

Instead define:

* benchmark scenarios,
* measurement phase,
* when targets are set,
* evidence required before optimizing.

Adopt:

`No optimization ADR without measurement.`

---

# 13. Technology Neutrality vs Technology Avoidance

Review whether the project is accidentally avoiding concrete implementation decisions.

Preserve:

`Canonical architecture = technology-neutral.`

But also adopt:

`Reference implementation = deliberately opinionated.`

The reference runtime will eventually need concrete choices for:

* validation library,
* datastore,
* migration tooling,
* serialization,
* testing stack,
* logging stack,
* packaging,
* concurrency implementation,
* CLI/developer tools.

These do NOT violate platform neutrality if hidden behind correct boundaries.

Determine which choices happen before implementation versus during implementation.

---

# 14. Framework-Creep Detection

Define warning signs that Lego AI is absorbing application-specific concepts.

At minimum:

* concept exists only because ForgeAI needs it,
* no second use case,
* domain-specific object appears in Kernel,
* generic interface becomes very complex for one provider,
* optional capability becomes mandatory,
* application-domain workflow becomes canonical runtime behavior,
* Plugin extension exists only for one consumer.

Define when such a proposal should be rejected or kept in the consuming application.

---

# 15. Solo-Developer Complexity Budget

For every platform mechanism ask:

Can one developer realistically:

* understand it,
* run it locally,
* test it,
* debug it,
* upgrade it,
* migrate it,
* recover it,
* deploy it?

Classify every pending subsystem as:

* needed now,
* needed before executable slice,
* needed before ForgeAI,
* needed before release,
* trigger-based later,
* unjustified.

Do not copy enterprise architecture patterns merely because they are theoretically robust.

---

# 16. Multiple AI Coding Assistants / Agentic Development

We intend to use multiple coding/reasoning systems such as ChatGPT, Astra, Claude, and future coding agents during development.

Define a safe AI-native SDLC for this project.

The assistants may perform:

* architecture analysis,
* implementation,
* code review,
* test generation,
* documentation,
* refactoring,
* threat modeling,
* fault analysis.

But no model's output should be accepted merely because another model agrees with it.

Define roles such as:

`Architect`
→ creates decision/spec

`Implementer`
→ implements a bounded task

`Reviewer`
→ independently reviews diff against contract

`Test/Adversarial Agent`
→ attempts to break assumptions

`Human Maintainer`
→ accepts/rejects consequential architecture/release changes

Define controls against:

* shared hallucination,
* specification drift,
* models reviewing their own assumptions,
* massive unreviewable generated commits,
* hidden dependency introduction,
* unsafe automated migrations,
* false test confidence.

Require small reviewable changes and executable evidence.

---

# 17. Application Throughput Expectations

Analyze realistic application-development velocity after Lego AI matures.

Distinguish:

`prototype`
from
`production-ready application`
from
`regulated/high-risk enterprise application`.

Do NOT claim that dozens of unrelated production-grade applications can automatically be created in one or two weeks.

Instead determine which categories of applications could plausibly become highly compositional once Lego AI has reusable:

* authentication,
* Models,
* Tools,
* Artifacts,
* workflows,
* evaluation,
* observability,
* deployment templates.

Define conditions under which rapid application creation is realistic.

---

# 18. Required Gap-Routing Matrix

Create a matrix:

| Gap | Severity | Existing owner? | Remaining work | Route | Needed before source? | Before slice? | Before ForgeAI? | Before release? | Trigger |
| --- | -------- | --------------- | -------------- | ----- | --------------------- | ------------- | --------------- | --------------- | ------- |

Route must be exactly one of:

A — Already covered
B — Resolve in an existing ADR
C — Lower-level implementation decision
D — New ADR justified
E — Wait for runtime/ForgeAI evidence
F — Reject as unnecessary/overengineering

Include at least:

* developer experience,
* execution supervision,
* persistence product,
* testing,
* observability,
* Secrets,
* Plugin isolation,
* supply chain,
* performance,
* deployment,
* application composition,
* AI integration,
* Agent integration,
* Multi-Agent integration,
* ForgeAI integration,
* AI-assisted SDLC.

---

# 19. Proposed ADR Changes

Do NOT modify ADR-INDEX.

Create:

`## Proposed ADR-INDEX Amendments`

Recommend only justified changes.

Assess whether future candidates are warranted, including:

* Reference Application Authoring / Composition
* Execution Supervision / Concurrency

Do not create these ADRs yet.

For each proposed candidate specify:

* decision question,
* class,
* priority,
* reversibility,
* dependency,
* trigger,
* reason it cannot be an implementation detail.

Reject unnecessary ADR candidates.

---

# 20. Define Four Gates

Produce exact criteria for:

## GATE 1 — SOURCE START

When foundational implementation may begin.

## GATE 2 — GOVERNED EXECUTABLE SLICE

When Lego AI can safely execute its first protected deterministic action.

## GATE 3 — FORGEAI START

When ForgeAI can begin consuming Lego AI without forcing unsafe premature abstractions.

## GATE 4 — FIRST USABLE RELEASE

When Lego AI can be presented as a supported reference runtime.

Do not combine these gates.

---

# 21. Define the Walking Skeleton

Specify the first end-to-end implementation:

Application
→ configuration
→ Principal/TenantContext
→ Capability requirement
→ resolution
→ Plugin
→ Provider
→ Adapter
→ Execution
→ authorization
→ resource admission
→ protected effect
→ owner-state commit
→ evidence
→ trace/log
→ result

Then exercise:

* success,
* denial,
* timeout,
* lost acknowledgment,
* retry,
* partial completion,
* runtime restart.

Avoid Agent/Model complexity initially.

---

# 22. First AI Slice

After the deterministic skeleton is reliable, define the smallest Model integration.

Prefer proving:

Application
→ ModelPort
→ replaceable Model Provider/Adapter
→ governed invocation
→ resource accounting
→ evidence
→ tracing
→ Artifact/result

without requiring an Agent.

Explain prerequisites.

---

# 23. First Agent Slice

Only after the Model/Tool/runtime paths are stable, define prerequisites for:

* Agent state,
* planning,
* Tool requests,
* delegation,
* checkpointing,
* cancellation,
* evaluation.

Do not add multi-agent complexity prematurely.

---

# 24. First Multi-Agent Slice

Define what must already be proven before:

Supervisor
→ Worker Agents
→ Delegation
→ Tool calls
→ shared Artifacts
→ independent authority checks.

Explicitly require bounded delegation and traceable execution.

---

# 25. Development Phases

Produce a recommended sequence approximately like:

Phase 0 — Critical ADR completion
Phase 1 — Foundation/package implementation
Phase 2 — Deterministic walking skeleton
Phase 3 — Failure/recovery proof
Phase 4 — Model/AI integration
Phase 5 — ForgeAI integration
Phase 6 — Agent capability
Phase 7 — Multi-Agent capability
Phase 8 — Release assurance
Phase 9 — Triggered production features

For every phase define:

* entry criteria,
* deliverables,
* tests,
* exit criteria,
* risks,
* explicit non-goals.

---

# 26. Risk Register

Include at minimum:

* architecture paralysis,
* overengineering,
* control-plane dominance,
* bad developer experience,
* excessive generic abstraction,
* missing runtime supervision,
* hidden persistence weakness,
* insufficient failure testing,
* logging/evidence confusion,
* temporary Secret bypass,
* false Plugin isolation claim,
* dependency/supply-chain compromise,
* AI-generated code quality drift,
* shared hallucination across AI assistants,
* unreviewable generated diffs,
* ForgeAI/Lego AI coupling,
* premature multi-agent complexity,
* premature distributed architecture,
* false production-readiness claims.

For each:

* likelihood,
* impact,
* trigger,
* mitigation,
* owner,
* exit condition.

---

# 27. Architecture Stop Rules

Recommend explicit engineering rules such as:

1. No new foundational abstraction without evidence.
2. No new framework layer because one application needs it.
3. No production claim without corresponding evidence.
4. No optimization without measurement.
5. No arbitrary Plugin-trust claim without isolation evidence.
6. No Secret shortcut outside ADR-010.
7. No generated code accepted without tests/review.
8. No large AI-generated commits spanning unrelated modules.
9. No canonical dependency on optional AI functionality.
10. No new technology-neutral abstraction when an implementation-local choice is sufficient.

Improve these rules where necessary.

---

# 28. Final Verdict

Conclude with exactly:

Current architecture readiness:
READY / READY WITH CONDITIONS / NOT READY

Then provide:

Critical gaps before further ADR work:
...

Critical gaps before source implementation:
...

Critical gaps before executable runtime:
...

Critical gaps before ForgeAI:
...

Critical gaps before AI/Agents:
...

Critical gaps before release:
...

New ADR candidates justified:
...

New ADR candidates rejected:
...

Architecture freeze point:
...

Source implementation start:
...

ForgeAI start:
...

Recommended next action:
...

---

# 29. Completion Requirements

At completion report only:

1. file created,
2. readiness verdict,
3. critical gaps,
4. gaps already covered,
5. gaps routed to existing ADRs,
6. lower-level implementation decisions needed,
7. justified new ADR candidates,
8. rejected ADR candidates,
9. v0.1 runtime scope,
10. architecture freeze point,
11. source-start gate,
12. executable-slice gate,
13. ForgeAI-start gate,
14. AI/Agent-start gate,
15. release gate,
16. Secrets trigger,
17. Plugin-isolation trigger,
18. testing baseline,
19. observability baseline,
20. persistence decision placement,
21. execution-supervision placement,
22. developer-experience placement,
23. AI-native SDLC recommendation,
24. NFR measurement approach,
25. top risks,
26. framework-creep controls,
27. recommended development phases,
28. proposed ADR-index changes,
29. whether accepted canonical documents require amendment.

STOP afterward.

Do NOT create another ADR.

Do NOT implement source code.
