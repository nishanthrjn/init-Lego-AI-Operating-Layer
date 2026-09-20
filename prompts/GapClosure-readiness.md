Act as the **Principal Software Architect, AI Platform Architect, Runtime Architect, Developer-Experience Architect, Reliability Engineer, Security Architect, Test Architect, and Solo-Developer Technical Advisor** for the **Lego AI Operating Layer**.

Your task is to perform a **formal implementation-readiness and architecture-gap closure review** of the Lego AI Operating Layer.

Create:

```text
planning/IMPLEMENTATION-READINESS.md
```

Status:

```text
PROPOSED — FOR CANONICAL REVIEW
```

This document is a **planning and decision-routing artifact**, not a new semantic specification.

Do NOT implement code.

Do NOT modify accepted canonical documents.

Do NOT create new ADRs during this task.

Do NOT modify `ADR-INDEX.md`.

Instead, identify precisely:

1. which remaining gaps are already covered by existing ADRs,
2. which require implementation decisions beneath existing ADRs,
3. which genuinely require new ADR candidates,
4. which should be resolved only after implementation/ForgeAI provides evidence,
5. which risks must be mitigated immediately,
6. where architecture work must stop and implementation must begin.

---

# 1. Governing Documents

Read all current accepted project artifacts in authority order:

1. `intent.md`
2. `SPEC.md`
3. `architecture/ARCHITECTURE.md`
4. `contracts/CONTRACTS.md`
5. `plugin-spec/PLUGIN-SPEC.md`
6. `security/SECURITY.md`
7. `evaluation/EVALUATION.md`
8. `conformance/CONFORMANCE.md`
9. `adrs/ADR-INDEX.md`
10. `adrs/ADR-001.md`
11. `adrs/ADR-002.md`
12. `adrs/ADR-003.md`
13. `adrs/ADR-004.md`

Also inspect ADR-005's intended scope from `ADR-INDEX.md`.

If later accepted ADRs exist when this task is run, include them.

Preserve the authority hierarchy.

No lower-level planning recommendation may silently redefine accepted semantics.

---

# 2. Objective

Determine whether the current Lego AI program is sufficiently complete to move from:

```text
architecture/specification program
```

to:

```text
reference-runtime implementation
+
real application validation
```

without either:

```text
A. implementing too early with unresolved correctness/security gaps

or

B. continuing architecture indefinitely and overengineering the platform
```

The review must optimize for:

```text
semantic correctness
security
replaceability
developer usability
solo-developer feasibility
time-to-first-working-runtime
real-world validation
long-term extensibility
```

---

# 3. Fundamental Constraint

The original objective of Lego AI is not merely:

```text
build a correct runtime
```

It is:

```text
build reusable intelligent-application infrastructure once
and compose future applications from reusable capabilities.
```

Therefore evaluate the architecture from TWO equally important perspectives:

```text
CONTROL / GOVERNANCE PLANE
    security
    tenancy
    configuration
    state
    evidence
    resources
    effects
    plugins
    conformance

AND

DEVELOPER / EXECUTION PLANE
    authoring
    composition
    runtime execution
    debugging
    testing
    local development
    application integration
```

Do not declare the program implementation-ready if only the first is mature.

---

# 4. Review the Current ADR Program

Review ADR-001 through ADR-013.

For each ADR determine:

```text
What risk does it close?
What implementation blocker does it remove?
What remains deliberately deferred?
Is its current priority still correct?
Does another gap already belong inside it?
```

Pay special attention to:

```text
ADR-005 Principal / Authorization / Tenant
ADR-006 Plugin bootstrap
ADR-007 Dispatch / resources
ADR-008 Retry / reconciliation
ADR-009 Mandatory evidence
ADR-010 Secrets
ADR-011 Release evidence
ADR-012 Plugin isolation
ADR-013 Operational observation
```

Do NOT create duplicates for responsibilities already owned by these ADRs.

---

# 5. Gap 1 — Developer Experience / Application Authoring

Evaluate whether the current program sufficiently decides:

> How does an application developer actually build something using Lego AI?

Analyze the developer-facing flow:

```text
Idea
→ Application declaration
→ select Capabilities
→ select/resolve Plugins
→ configuration
→ domain logic
→ Tools/Skills
→ policies
→ composition
→ validation
→ local execution
→ inspect/debug
→ test
→ package/release
```

Determine whether a new candidate such as:

```text
ADR-014 — Reference Application Authoring and Composition Experience
```

is justified.

Possible approaches to evaluate later include:

```text
Python composition API
declarative manifest
builder DSL
hybrid declarative + Python escape hatch
```

Do NOT select one during this gap-review task.

Decide only:

```text
Is a separate ADR required?
When should it be written?
What prerequisites must exist first?
What exact question should it answer?
```

Prevent Lego AI from becoming architecturally rigorous but unpleasant to consume.

---

# 6. Gap 2 — Reference Execution Supervision / Concurrency

Determine whether existing ADRs fully answer:

```text
How does actual admitted work run?
```

Analyze missing implementation concerns such as:

```text
async task supervision
bounded concurrency
cancellation propagation
timeouts
shutdown
backpressure
orphaned tasks
background work
process termination
context propagation
worker ownership
resource cleanup
```

Do not confuse:

```text
Execution semantics
```

with:

```text
reference runtime scheduling/supervision mechanism.
```

Determine whether a future candidate such as:

```text
ADR-015 — Reference Execution Supervision and Concurrency Model
```

is needed.

Do not create it now.

If ADR-007/008 already own enough of this behavior, explicitly say so and identify only the residual mechanism decision.

---

# 7. Gap 3 — Concrete Persistence Realization

ADR-004 defines persistence behavior but intentionally does not select a datastore.

Determine when the first reference implementation must decide the actual realization supporting:

```text
conditional owner-local commit
durable mutation
exact revision lookup
history
operation results
outstanding obligations
migration
restart/recovery
```

Decide whether this should be:

```text
a new architecture ADR

OR

a lower-level implementation decision / implementation ADR
under ADR-004
```

Prefer the lower-level decision if canonical architecture does not depend on the product.

Do NOT select SQLite/PostgreSQL/etc. in this task.

Define the trigger and decision criteria.

---

# 8. Gap 4 — Reference Runtime v0.1 Scope

This is mandatory.

Define a proposed finite:

```text
Reference Runtime v0.1 Profile
```

that prevents implementation scope explosion.

It should be the smallest governed slice that proves the architecture.

Evaluate a candidate scope approximately like:

```text
one explicit Tenant
one administrative Principal
one Application
one deterministic Capability
one Plugin
one Provider
one Adapter
one Port
one protected Tool/effect
one configuration revision
durable state
authorization
resource/effect handling
evidence
retry/reconciliation
basic structured observation
```

and initially exclude unless absolutely required:

```text
Agent
Model
Team
Workflow engine
persistent Memory
RAG
vector database
event broker
multi-service deployment
hostile third-party Plugin execution
enterprise IAM
public protocol
cloud-specific infrastructure
```

Do not blindly accept this list.

Derive the actual v0.1 profile from the accepted semantics and ADR dependencies.

For every included feature state:

```text
why required
owning module
required ADR
minimum proof
```

For every excluded feature state:

```text
why excluded
trigger for inclusion
```

---

# 9. Gap 5 — Architecture Freeze / Stop Rule

Define an explicit rule preventing endless architecture expansion.

Seriously evaluate adopting:

```text
FOUNDATIONAL ARCHITECTURE FREEZE
after ADR-008
```

or the nearest dependency-safe point.

Suggested principle:

```text
After the foundational execution chain is resolved,
no new foundational abstraction is added
without evidence from:

1. reference-runtime implementation,
2. a failing conformance/test case,
3. ForgeAI consumption,
4. another real consumer,
5. measured operational evidence.
```

Determine the exact freeze point.

If ADR-009 must precede the freeze because it is required by the execution path, say so.

Do not blindly use ADR-008 if the dependency graph proves another point is safer.

---

# 10. Gap 6 — ForgeAI as Architecture Validator

Define how **ForgeAI** should become the first serious consumer of Lego AI.

The relationship should NOT be:

```text
Finish every possible Lego AI feature
→ then start ForgeAI.
```

Evaluate instead:

```text
minimum safe Lego AI runtime
→ ForgeAI consumes it
→ friction/gap discovered
→ evidence collected
→ Lego AI abstraction changed only when justified
```

Define:

```text
earliest safe ForgeAI start point
which Lego AI capabilities ForgeAI should consume first
what ForgeAI-specific logic must stay outside Lego AI
how reusable discoveries are promoted back into Lego AI
how premature generalization is prevented
```

Create a formal rule:

```text
ForgeAI requirement
≠ automatically Lego AI requirement.
```

A requirement should enter Lego AI only when it represents reusable infrastructure rather than ForgeAI domain logic.

---

# 11. Gap 7 — Testing from Day One

ADR-011 owns release/conformance evidence.

That MUST NOT mean testing waits until ADR-011.

Define an implementation testing strategy beginning with the first source commit.

Cover:

```text
unit / invariant tests
owner-state tests
Port contract tests
Adapter substitution tests
architecture/import boundary tests
configuration revision tests
security negative tests
tenant isolation tests
concurrency tests
crash/restart tests
lost-ack tests
effect uncertainty tests
failure injection
migration tests
composition tests
eventual conformance tests
```

Distinguish:

```text
development tests
≠
formal conformance evidence
```

Recommend when each layer begins.

Do not select a test framework unless unavoidable.

---

# 12. Gap 8 — Observability / Logging

Confirm and preserve:

```text
operational logging/tracing/metrics
≠
authoritative owner state
≠
mandatory evidence
≠
provenance
```

ADR-013 may own full production operational integration.

But determine the **minimum observation baseline required from the first executable slice**.

At minimum consider:

```text
structured events
Trace/correlation identity
Execution identity
tenant-safe identifiers
configuration revision
Plugin/provider version
state transition
authorization result reference
effect status
errors
resource usage
timing
```

while excluding:

```text
raw Secrets
credentials
sensitive payloads by default
private chain-of-thought
```

Decide:

```text
what must exist immediately
what may wait for ADR-013
```

Do NOT select an observability vendor/backend.

---

# 13. Gap 9 — Secret Trigger

Review ADR-010 priority.

Do NOT automatically promote it.

Instead define the hard trigger:

```text
Before the first implementation stores,
retrieves or uses a real Secret-bearing credential,
ADR-010 and its prerequisites MUST be resolved.
```

Examples include:

```text
Model API key
GitHub token
database password
OAuth client secret
cloud credential
SMTP credential
Tool credential
```

Prevent:

```text
temporary .env shortcut
```

from becoming an architectural bypass.

---

# 14. Gap 10 — Plugin Isolation / Trust Claims

Preserve the distinction:

```text
Python package boundary
≠ security isolation
```

Until ADR-012 is resolved and implemented, define exactly how Plugins may be described.

For example distinguish:

```text
admitted/trusted Plugin within declared threat model
```

from:

```text
arbitrary hostile third-party code safely sandboxed
```

Determine:

```text
initial Plugin trust assumption
what claims may be made
what claims must NOT be made
trigger for ADR-012
```

This must prevent misleading platform promises.

---

# 15. Gap 11 — Supply Chain

Determine whether ADR-006 + ADR-011 sufficiently own:

```text
dependency locking
artifact integrity
publisher identity
release provenance
vulnerability scanning
SBOM
signing/attestation
dependency response
```

Do NOT invent another ADR if those responsibilities fit existing ones.

If something remains unowned, identify it.

Do not select signing/SBOM products.

---

# 16. Gap 12 — Non-Functional Baseline

The first runtime eventually needs measurable operating expectations.

Define when and how to establish a small benchmark profile covering things such as:

```text
startup time
idle memory
protected invocation overhead
authorization overhead
state-commit latency
trace volume
concurrent executions
Plugin count
state size
recovery time
```

Do NOT invent arbitrary targets now.

Instead define:

```text
when measurement begins
what needs measurement
what evidence determines acceptable thresholds
```

Performance requirements must be evidence-driven.

---

# 17. Gap 13 — Technology Neutrality vs Technology Avoidance

Explicitly preserve this principle:

```text
Canonical contracts are technology-neutral.

Reference implementation is allowed
and expected to be opinionated.
```

The project must eventually choose concrete:

```text
validation library
persistence implementation
migration tooling
testing tools
logging implementation
packaging/build tooling
runtime concurrency mechanism
CLI/developer tooling
```

at lower layers.

Reject the idea that choosing a concrete reference implementation violates portability.

The correct model is:

```text
neutral semantics
+
opinionated reference implementation
+
replaceable Ports/Adapters
```

---

# 18. Gap 14 — Reuse Target / Framework Creep

Review the long-term reuse aspiration.

Prevent:

```text
maximize percentage of code reused
```

from becoming a design constraint.

Adopt instead:

```text
reuse recurring infrastructure
without forcing irreducible domain logic
into generic Lego AI abstractions.
```

Define indicators of framework creep:

```text
domain-specific concepts entering Kernel
one-consumer abstraction
complex generic interface with no second use
Plugin extension added only for ForgeAI
mandatory dependency introduced for optional feature
```

Define a rejection rule.

---

# 19. Gap 15 — Solo-Developer Complexity Budget

Create a complexity budget.

For every proposed new subsystem/ADR ask:

```text
Can one developer:
understand it?
run it locally?
test it deterministically?
upgrade it?
debug it?
recover it?
deploy it?
```

Classify complexity as:

```text
necessary now
necessary before release
triggered later
not justified
```

Reject enterprise-platform machinery without a current semantic requirement.

---

# 20. Required Gap Matrix

Create a table with columns:

```text
Gap
Severity
Already covered?
Current owner
Remaining decision
Needed before source start?
Needed before executable slice?
Needed before ForgeAI?
Needed before release?
Trigger
Recommended action
```

At minimum include:

```text
developer authoring
execution supervision
persistence realization
runtime v0.1 profile
architecture freeze
ForgeAI validation
testing
baseline observation
Secrets
Plugin isolation
supply chain
NFR benchmarks
technology choices
framework creep
solo-developer complexity
```

---

# 21. Decision Routing

For every gap classify it into EXACTLY one category:

```text
A — Already covered by existing accepted specification/ADR

B — Must be resolved inside an existing planned ADR

C — Needs lower-level implementation decision after an ADR

D — Justifies a new ADR candidate

E — Must wait for runtime/ForgeAI evidence

F — Not required / reject as overengineering
```

Explain each classification.

---

# 22. Proposed New ADR Candidates

Do NOT create them.

Only propose candidates that survive the routing analysis.

Likely candidates to evaluate include:

```text
ADR-014 — Reference Application Authoring and Composition Experience

ADR-015 — Reference Execution Supervision and Concurrency Model
```

But these are NOT mandatory.

A candidate is justified only if:

```text
the decision is cross-cutting
hard to reverse
not already owned
materially affects multiple modules/consumers
```

If a problem can be solved as an implementation detail, do not create an ADR.

---

# 23. ADR-INDEX Amendment Proposal

Do NOT edit `ADR-INDEX.md`.

Instead include:

```text
## Proposed ADR-INDEX Amendments
```

containing:

```text
new candidate
class
priority
reversibility
dependencies
trigger
blocks
reason
```

Also recommend whether any existing priorities/triggers should change.

For ADR-010/012/013 prefer explicit feature triggers unless strong evidence says they must become baseline blockers.

---

# 24. Implementation Start Gate

Define objective criteria for:

```text
SOURCE START
```

and separately:

```text
EXECUTABLE GOVERNED SLICE
```

and:

```text
FORGEAI INTEGRATION START
```

and:

```text
USABLE RELEASE
```

Example distinction:

```text
SOURCE START
package/contracts/state foundations may be coded

EXECUTABLE SLICE
safe protected action can actually execute

FORGEAI START
stable enough for first real consumer

RELEASE
supported scope has required proof/evidence
```

Derive actual conditions from the project.

---

# 25. Proposed Development Phases

Produce a concrete phased plan.

Use approximately:

```text
Phase 0 — Finish critical ADR chain

Phase 1 — Foundation implementation

Phase 2 — Governed deterministic walking skeleton

Phase 3 — Failure/recovery proof

Phase 4 — ForgeAI consumption

Phase 5 — First reusable AI capability

Phase 6 — Release qualification

Phase 7 — Triggered features
```

For every phase define:

```text
entry criteria
deliverables
exit criteria
tests
risks
what must NOT be built yet
```

---

# 26. Walking Skeleton

Define the smallest end-to-end reference flow that should be implemented first.

It should test the architecture from:

```text
Application
→ configuration
→ Principal/Tenant
→ Capability resolution
→ Plugin/Provider/Adapter
→ Execution
→ protected action
→ state commit
→ evidence
→ observation
→ result
```

through:

```text
failure
retry/reconciliation
restart
```

The skeleton should initially avoid unrelated AI complexity.

---

# 27. First AI Slice

Only after the deterministic walking skeleton is sound, define what the first AI integration should prove.

Potentially:

```text
ModelPort
→ one replaceable Model Adapter
→ governed invocation
→ resource accounting
→ evidence/trace
```

No Agent is required merely to prove Model integration.

Determine the correct order.

---

# 28. First Agent Slice

Define what must already be stable before adding:

```text
Agent
planning
delegation
Tool selection
multi-agent work
```

Do not let Agent complexity mask defects in the underlying runtime.

---

# 29. ForgeAI Integration Boundary

Define which capabilities ForgeAI should initially consume from Lego AI.

Examples to evaluate:

```text
configuration
Plugin system
Model capability
Tool capability
Execution
Artifacts
Policy
Evidence
Tracing
```

Then identify ForgeAI-specific concepts that must remain outside Lego AI.

---

# 30. Evidence-Driven Abstraction Rule

Adopt a strict rule:

```text
A new reusable abstraction requires at least one of:

1. two independent real use cases,
2. a canonical semantic requirement,
3. a demonstrated replaceability need,
4. repeated implementation duplication,
5. conformance/security correctness requirement.
```

One speculative future use case is insufficient.

---

# 31. Stop Conditions

Define explicit stop conditions for architecture work.

Examples:

```text
No new foundational specification
while an accepted mechanism remains unimplemented.

No new generic subsystem
without consumer evidence.

No new provider abstraction
before at least one working provider exists,
unless canonical contracts already require it.

No optimization ADR
without measurement.
```

Refine these rules.

---

# 32. Risk Register Update

Produce a gap-specific risk register.

At minimum include:

```text
architecture paralysis
framework overgeneralization
developer UX neglect
control-plane dominance
integration complexity
untested abstractions
hidden runtime concurrency failure
logging/evidence confusion
temporary Secret bypass
false Plugin isolation claims
technology-choice avoidance
ForgeAI divergence
premature distributed architecture
release-before-proof
```

For every risk provide:

```text
probability
impact
trigger
mitigation
owner
exit condition
```

Use qualitative ratings.

---

# 33. Do Not Reopen Good Decisions

Do NOT revisit without contradiction:

```text
technology-neutral canonical semantics
Ports/Adapters
minimal Kernel
owner-local state
immutable configuration revisions
explicit tenancy
Agent ≠ Principal
Evaluation ≠ Conformance
logging ≠ mandatory evidence
no global transaction
AI optionality
modular-monolith-first
```

The goal is gap closure, not architecture churn.

---

# 34. Do Not Implement

During this task DO NOT:

```text
write source code
create Python packages
choose database
choose IAM product
choose logging backend
choose Agent framework
choose Workflow engine
create ADR-014
create ADR-015
modify ADR-INDEX
modify canonical specs
start ForgeAI implementation
```

---

# 35. Required Final Recommendation

Conclude with ONE program recommendation using this structure:

```text
Current architecture readiness:
READY / READY WITH CONDITIONS / NOT READY

Critical gaps before continuing ADR work:
...

Critical gaps before implementation:
...

Critical gaps before executable slice:
...

Critical gaps before ForgeAI:
...

Critical gaps before release:
...

New ADR candidates justified:
...

New ADR candidates rejected:
...

Recommended architecture freeze point:
...

Recommended implementation start point:
...

Recommended ForgeAI start point:
...
```

Do not use vague language.

---

# 36. Completion Report

After creating:

```text
planning/IMPLEMENTATION-READINESS.md
```

STOP.

Report only:

1. file created,
2. overall readiness verdict,
3. gaps found,
4. gaps already covered,
5. gaps routed into existing ADRs,
6. implementation decisions required,
7. proposed new ADR candidates,
8. rejected ADR candidates,
9. proposed v0.1 scope,
10. proposed architecture freeze point,
11. source-start gate,
12. executable-slice gate,
13. ForgeAI-start gate,
14. release gate,
15. Secrets trigger,
16. Plugin-isolation trigger,
17. observability baseline,
18. testing baseline,
19. persistence-decision placement,
20. execution-supervision decision placement,
21. developer-experience decision placement,
22. NFR measurement strategy,
23. framework-creep controls,
24. top five risks,
25. recommended development phases,
26. proposed ADR-INDEX amendments,
27. whether accepted canonical documents require changes.

Do NOT create or modify any ADR.
