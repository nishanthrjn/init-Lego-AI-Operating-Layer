# Lego AI Operating Layer — Implementation Readiness, Gap Closure and Risk Mitigation

**Status:** ACCEPTED — IMPLEMENTATION READINESS PLAN

**Date:** 2026-09-20

**Artifact type:** Planning / decision-routing artifact only

**Accountable reviewer:** Project maintainer; reference-runtime, security and release responsibilities remain with their accepted owners.

**Scope:** Source start, governed deterministic runtime, first ForgeAI consumption, later Model/Agent/Multi-Agent integration, and bounded release/production claims.

**Decision boundary:** This plan proposes sequencing and gates. It does not authorize source implementation, change canonical semantics, accept a new ADR, select a datastore or developer API, or establish implementation/security/Conformance proof. ADR-INDEX is unchanged.

**Acceptance:** Accepted after architectural review on 2026-09-20. Acceptance authorizes the planning sequence and architecture freeze described here; it does not itself authorize implementation, establish executable-runtime readiness, approve ForgeAI consumption, or constitute release, Conformance, security, or production-readiness evidence.

## 1. Verdict and evidence basis

**READY WITH CONDITIONS for bounded foundational source work; not ready for protected runtime execution, ForgeAI runtime consumption or supported/production release.** The architecture is sufficiently defined to implement foundations. More canonical abstraction is not the critical path. Execution supervision, a supported application-facing composition boundary, concrete realizations and executable failure proof are.

The repository inspected for this review contains canonical Markdown documents, ADR-001 through ADR-011, the ADR index, the readiness prompt and `.gitignore`. It contains no reference-runtime source, package configuration, implemented tests or executable release evidence. All eleven ADR files, including ADR-010 and ADR-011, now state **Accepted**, and the index records that disposition. ADR-012/013 remain proposed candidates in the index without individual decision files. Acceptance is decision evidence, not working software.

### 1.1 Reviewed authority

The review used the actual current documents in authority order, rather than relying on conversation summaries:

1. [intent.md](../intent.md)
2. [SPEC.md](../SPEC.md)
3. [ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
4. [CONTRACTS.md](../contracts/CONTRACTS.md)
5. [PLUGIN-SPEC.md](../plugin-spec/PLUGIN-SPEC.md)
6. [SECURITY.md](../security/SECURITY.md)
7. [EVALUATION.md](../evaluation/EVALUATION.md)
8. [CONFORMANCE.md](../conformance/CONFORMANCE.md)
9. [ADR-INDEX.md](../adrs/ADR-INDEX.md)
10. [ADR-001](../adrs/ADR-001.md), [ADR-002](../adrs/ADR-002.md), [ADR-003](../adrs/ADR-003.md), [ADR-004](../adrs/ADR-004.md), [ADR-005](../adrs/ADR-005.md), [ADR-006](../adrs/ADR-006.md), [ADR-007](../adrs/ADR-007.md), [ADR-008](../adrs/ADR-008.md), [ADR-009](../adrs/ADR-009.md), [ADR-010](../adrs/ADR-010.md), [ADR-011](../adrs/ADR-011.md).

Repository inventory, current acceptance headers, the index blocker matrix, actual owner/Port definitions and ADR qualification requirements support the findings below. No runtime was executed or assessed because none exists. The current user modification to the readiness prompt is preserved. All existing files remain unchanged by this task.

### 1.2 Strongest conclusions

- Control-plane ownership and behavior are substantially closed; their concrete enforcement is unimplemented.
- Execution Coordination already owns supervision semantics. The missing decision is how the reference runtime implements them, not a new canonical scheduler owner.
- Application Composition and public contract packages exist architecturally, but ADR-002 explicitly leaves a supported external composition API open. A consumer must not import the private technical wiring root by accident.
- ADR-004 explicitly leaves storage product/representation selection below its semantic boundary. Continuing to avoid that decision would be technology avoidance.
- ADR-013 explicitly permits mandatory local observation before production integration. Logging need not wait, and cannot replace Evidence.
- ADR-010 acceptance does not enable real credential use. The implemented and qualified Secret path is a hard conditional gate.
- ADR-011 supplies release workflow, not permission to postpone development testing until release.
- No blocking contradiction requiring immediate amendment to accepted canonical documents was identified. Several wording/feasibility tensions need precise implementation treatment, documented below.

## 2. Balanced readiness assessment

### 2.1 Control / Governance plane

| Surface | Existing decision / owner | What is closed | What is still needed |
|---|---|---|---|
| Configuration | Application Composition; ADR-003 | Immutable effective meaning, reference binding, no ambient overlays | Concrete validation/representation, source capture, revision tests and restart readers |
| Identity / authorization | Respective Governance owners; ADR-005 | Explicit Principal/Tenant, current authority, deputy limits | Qualified local trust basis, actual policy inputs and negative enforcement tests |
| Tenancy | Tenant Governance; SPEC S-10/11, SEC-060 | Explicit scope and governed crossing | One-tenant realization plus adversarial wrong/missing-tenant cases; no multi-tenant SaaS claim |
| Owner state | Each state owner; ADR-004 | Guarded atomic state/result/history/obligation sets | Storage realization, serialization/migration rules, crash and corruption handling |
| Plugins | Lifecycle/Catalog; ADR-006 | Finite roots, staged admission, offer eligibility | Bounded built-in inventory, actual lifecycle/recovery implementation |
| Resources / Approval | Resource and Approval owners; ADR-007 | Authoritative claims, conserved liability, no auto-refund | Scope-specific units/limits/retention, concurrent owner enforcement and settlement proof |
| Effects / retries | Invoking planes, Execution Coordination; ADR-007/008 | Single effect responsibility, uncertainty and equivalence | Exact local acceptance/currentness boundary, effect fixture, retained outcomes and reconciliation |
| Evidence / provenance | Source owners and Evidence; ADR-009 | Source facts distinct from qualified custody, finite roots | Working custody, availability/privacy/repair proof and bounded storage |
| Secrets | Secret Access; ADR-010 | Purpose-bound guarded use, no raw cache/state, finite roots | Implement/qualify only when a real Secret path is selected |
| Evaluation | Evaluation Management; EVAL-006–009/077–084 | Exact subjects, methods, results and uncertainty | Minimal deterministic assessment tooling; no Model judge required |
| Conformance / release | Assessors and Governance; ADR-011 | Scope closure, impact reuse, separate approval/publication | Clause ledger, actual evidence, exact build/compatibility artifacts and release decision |

### 2.2 Developer / Execution plane

| Surface | Existing basis | Remaining implementation-readiness gap |
|---|---|---|
| Application authoring | intent §§22, 45; Application Composition | No selected supported authoring experience, validation feedback or consumer lifecycle |
| Composition / developer API | ADR-002 public packages/thin facade/private root | Need explicit boundary for application code, technical wiring, startup/shutdown and test substitutes |
| Runtime execution | Architecture §4.4; Contracts §10 | Need concrete supervision and driver ownership model |
| Concurrency / cancellation | Execution owner, canonical states, ADR-007 | Gate serializes handoff, not all work; cancellation, queue bounds and cleanup mechanism open |
| Local development | CPython 3.14, one distribution, ADR-002 | Environment/package/test commands and a repeatable local example absent |
| Testing | Conformance obligations and ADR proof lists | No executable tests; day-one test harness and fault seams needed |
| Debugging / logs | Observation owner; Contracts §25 | Safe correlated local diagnostics and retained failures needed before first action |
| Packaging | ADR-002 `src/`, `legoai`, one `legoai-reference` distribution | Build backend, metadata, dependency lock/update workflow and install checks are concrete choices |
| Deployment | Local modular monolith scope | Single-process operating recipe, shutdown, storage ownership and restore procedures absent |
| Application integration | Ports/public values and Application owner | First ForgeAI consumer contract and compatibility boundary not yet demonstrated |
| Model integration | Model Interaction / ModelPort | Optional driver, adapter qualification, usage/uncertainty and real-credential gate |
| Agent integration | Agent driver / Work Coordination / Action Mediation | Stable supervised Model/Tool paths, bounded autonomy, state and evaluation first |
| Multi-Agent | Team/Role/Delegation semantics | Real coordination need plus proven child ownership, authority and shared-artifact behavior first |

The developer/execution gaps are equal-priority engineering work. Implementing every policy descriptor while leaving no understandable way to run/cancel/debug one action would fail this review.

## 3. Contradictions, duplication and complexity findings

| Finding | Source / evidence | Disposition |
|---|---|---|
| “One Port / Plugin / Provider” is easily overstated | ADR-INDEX §16 recommends one business Capability/Adapter; ADR-006 requires admitted finite root duties and owning Plugin associations | Count one application business Port/provider path. Mandatory Governance, Resources, Evidence, Execution and lifecycle contracts remain. Do not merge owners to achieve a cosmetic total of one. |
| Async primitives are discussed, not a complete supervision decision | ADR-001 discusses cooperative tasks/cancellation; Architecture allocates Execution ownership; ADR-007 covers only final arbitration | A bounded reference supervision ADR is justified. A language decision or lock is not that mechanism. |
| Public entry exists conceptually but supported authoring is unfinished | ADR-002 §12 distinguishes private technical root from later supported builder/external composition API | A bounded authoring/composition ADR is justified before supported consumer coupling, not before all foundation code. |
| Strict timing/currentness is a conditional feasibility obligation | ADR-007 §8; ADR-010 §8 reject unbounded check-to-use gaps and stale remote revocation | Early feasibility experiment must prove the intended local boundary or reject that path. Never quietly downgrade mandatory semantics to best effort. A real incompatibility routes back to the relevant accepted ADR for explicit review. |
| “Profile v0.1” could invent a platform profile | CONF-011/082; ADR-011 uses supported sets | This plan defines a bounded reference implementation scope, not an official profile, certification tier or version-numbering policy. |
| Accepted ADRs contain historical “next document” instructions | Individual ADR closing recommendations versus current accepted headers/index | Treat those as historical authorship context, not commands to repeat completed work. Current acceptance/index governs sequence; no content change needed now. |
| Requirements repeat across Security, Contracts, Conformance and ADRs | Same authority/effect/tenant/evidence invariants in several layers | Use linked requirement/proof IDs and one coverage ledger. Do not create a fifth semantic copy or merge accepted authorities during implementation. |
| Evidence, logs and state can be physically co-located but not interchangeable | ADR-004 §15, ADR-009, Architecture §4.13 | Preserve separate ownership, acknowledgment and failure behavior even with one local backing realization. |
| Material parameter values remain unchosen | ADR-007 Q-06 and ADR-008 Q-07 gates | Name units, bounds, expiry/retention and failure coverage for the selected scope before its protected use. No need to settle every possible profile. |
| “Production-grade .gitignore” is not supply-chain or Secret enforcement | Existing `.gitignore` excludes local credentials/state/generated evidence and includes template exceptions | Treat ignores as hygiene only. Future fixtures must be synthetic and promoted evidence explicitly reviewed; ignore rules do not establish custody or safe credential handling. |
| ForgeAI is named but its actual requirements/code are absent here | Repository inventory contains no ForgeAI implementation/brief | Define an integration discovery deliverable. Do not invent its domain architecture or claim validated reuse. |

No new canonical owner is missing for these concerns. Missing concrete policy configuration, tool choices, tasks and proof are not evidence that another platform entity is needed. If implementation exposes a genuine contradiction, record exact clauses and the affected conclusion; block only that scope and request an explicit upstream correction through normal governance.

## 4. GAP-A — Application authoring and composition

The desired application journey is not yet executable or sufficiently specified as a supported developer experience. Existing contracts describe meaning and ownership, not how a user discovers the right operations, supplies domain logic, receives validation errors and owns runtime lifetime.

| Journey stage | Existing owner/boundary | Remaining practical decision |
|---|---|---|
| Idea → Application | Application Composition | Small authoring surface and example, not an application framework |
| Choose Capabilities → reconcile Plugins | Capability Catalog/Resolution, Plugin Lifecycle | Explicit declaration/binding feedback and safe unsatisfied/ambiguous diagnostics |
| Configure → domain logic | Application/configuration, public Ports | Revision capture and domain callbacks without private implementation imports |
| Tools → Skills → policies | Action Mediation, optional Skill, Governance | Supported registration/use paths; Skills remain optional, policy never inferred from text |
| Compose → validate | Public facade versus private wiring | Ownership of lifetime, injected substitutions and validation-only mode |
| Execute → test → debug locally | Execution, Observation, test harness | Clear result/status/cancel interfaces, isolated state and trace correlation |
| Package → deploy | Distribution/release and operational integration | Build/install recipe, explicit config/roots/state paths and supported operating scope |

Compare four candidates in the future decision:

| Approach | Benefit | Cost / risk | Evidence needed |
|---|---|---|---|
| Direct Python API | Idiomatic domain logic, editor/type feedback | Boilerplate, arbitrary callbacks, accidental wiring exposure | Small direct Capability and real ForgeAI consumer examples |
| Builder API | Guided composition and validation | Another abstraction layer, fluent API complexity | Demonstrably simpler authoring without hidden authority/defaults |
| Declarative manifest | Inspectable intent and reproducible capture | New loader/representation/expression surface; domain logic still needed | Clear non-executable declaration semantics and useful diagnostics |
| Hybrid declaration + Python extension | Separate intent from specialized logic | Two paths can diverge or let escape hatches bypass gates | Both lower to the same governed owners and preserve security/context |

No mechanism is selected here. ADR-003's snapshot mechanism is not an application manifest language. ADR-002 permits a thin facade but does not authorize a public alias for private wiring.

**Route:** justify a bounded future **ADR-014 — Reference Application Authoring and Composition Experience**, with numbering provisional until index approval. Decide before Gate 3 or any supported third-party authoring API. Foundation code and a private deterministic test harness may begin earlier. Use the first internal skeleton's call sequence and an explicit ForgeAI integration brief as evidence; do not wait for a mature platform to discover that consumers cannot use it.

## 5. GAP-B — Execution supervision and concurrency

Execution Coordination already owns admission, context, attempts, scheduling intent, waits, parent/child links, cancellation/deadlines and reconciliation. Drivers own their state and invokers their effects. A concrete supervision contract must connect those facts to live tasks, worker lifetime and shutdown. ADR-007's bounded gate does not own arbitrary background work or external completion.

The new decision must resolve these observable responsibilities before the first governed asynchronous/effectful runner:

| Concern | Required decision / proof |
|---|---|
| Task ownership | Every task/worker belongs to an admitted Execution or explicitly bounded root/repair duty; no detached fire-and-forget work |
| Bounded concurrency | Queue/admission and active-work bounds tied to authoritative resources; capacity counters are not copied balances |
| Backpressure | Defined reject/wait behavior, deadline/cancellation while queued, finite memory growth |
| Context propagation | Explicit immutable governing context at entry/child boundary; ambient convenience cannot become authority |
| Cancellation | Distinguish request, preventing new work, driver acknowledgment and settled obligations; preserve in-flight effects |
| Timeouts | Timeout does not prove none or kill a blocking SDK; actual acceptance/expiry qualifications remain ADR-007 |
| Driver cleanup | Bounded joins, cleanup outcome and visible incomplete obligations; no fabricated terminal success |
| Blocking work | Explicit containment/offload policy and non-cooperative worker disposition; no unbounded thread pool by default |
| Shutdown | Stop admissions, fence new dispatch, drain/cancel within declared bounds, preserve unresolved work and close custody/storage safely |
| Background duties | Named purpose, owner, authority, resource ceiling and restart behavior for reconciliation/evidence repair |
| Orphans | Detect owner/task mismatch, retain durable attempt knowledge, reconcile rather than assuming no effect |
| Restart | No resurrection of tasks/authority from memory snapshots; ADR-004/007/008 exclusive recovery and effect knowledge govern next work |

Compare a single local structured asynchronous supervisor, a synchronous runner with explicitly owned bounded workers, and a minimal hybrid where required by qualified Adapters. A distributed workflow engine, general job platform and multi-service scheduler are not justified. No particular library/executor is selected in this plan.

**Route:** justify future **ADR-015 — Reference Execution Supervision and Concurrency Model**, before implementing supervised live execution for Gate 2. Foundation values, configuration and storage qualification can proceed first. This is a reference-runtime decision beneath existing canonical semantics, not a new execution model or new canonical states.

## 6. GAP-C — Persistence realization and technology choices

**Placement: lower-level implementation ADR beneath ADR-004.** The durable on-disk commitment and recovery evidence justify an attributable implementation decision, but not a new canonical datastore abstraction or top-level product-choice ADR. Its exact local location/number can be chosen when authorized; none is created now. Driver syntax, query layout and minor library settings normally remain ordinary implementation decisions.

Choose before implementing the first durable owner commit. Do not choose a database in this review. Compare candidate realizations using ADR-004 §15's capabilities: atomic expected-revision/absence guards; compound owner state/history/result/obligation commits; invariant/uniqueness protection; coherent authoritative reads; durable acknowledgment and qualified crash recovery; exact historical references; scoped equivalence; outstanding-duty discovery; integrity/corruption handling; versioned readers/migrations; retention/coverage semantics.

Also assess solo operational burden: local setup, dependency support for accepted CPython, transaction boundaries, bounded blocking behavior compatible with supervision, concurrent access, exclusive process admission, deterministic fault injection, inspectability, backup/restore limits, migration interruption, disk exhaustion and preservation of evidence/result history. “ACID” or a successful insert is not qualification. Shared physical storage cannot create cross-owner rollback or substitute for Evidence custody.

A realization that cannot prove accepted behavior is rejected for that scope. Only a discovered unavoidable semantic conflict justifies an explicit ADR-004/upstream review; convenience does not weaken the contract.

### 6.1 Technology neutrality is not technology avoidance

Canonical architecture remains technology-neutral. The reference implementation must be deliberately opinionated within those boundaries.

| Choice | Placement | Latest safe decision point |
|---|---|---|
| Validation library or standard-library validation | Implementation-local | Before first external/configuration boundary implementation; preserve canonical meanings/errors |
| Datastore/durability mechanism | Lower-level implementation ADR under ADR-004 | Before durable owner operations, not before all stateless source |
| State serialization and migration tooling | Implementation-local, recorded with persistence decision | Before writing durable formats; exact interpretation and version lineage required |
| Test runner, static checker, package architecture checks | Implementation-local | First foundation change; ADR-001 already requires strict typing as development control |
| Build backend, packaging and dependency workflow | Implementation-local under ADR-002 | First installable source increment; no registry publication required |
| Local logging implementation | Implementation-local under Observation contracts | Before first executable slice |
| Supervision behavior and concurrency lifetime | Proposed ADR-015; primitive/library selection within its scope | Before live runner/task ownership is implemented |
| Public authoring/composition lifecycle | Proposed ADR-014 | Before supported consumer/ForgeAI dependency |
| CLI and local developer commands | Mostly implementation-local after authoring boundary | First documented developer loop; do not invent a generic CLI framework |
| Deployment packaging/topology expansion | Local operating recipe first; new decisions only if semantics change | Before claiming support for that deployment/failure scope |

Concrete dependencies need provenance, review and tests, not a separate foundational ADR for every library. No technology products are selected here.

## 7. GAP-D — Finite reference runtime v0.1 supported scope

“v0.1” here is a planning label for the first implementation increment, **not an official profile, certification, maturity level or newly selected release-number scheme**. Scope is one trusted local process/domain, one explicit operational tenant, one narrowly scoped administrative maintainer Principal, one application, one deterministic business Capability through a Tool Port and one admitted business Provider/Adapter with a declared owning built-in Plugin. Tests introduce denied/revoked/mismatched identities without claiming multi-tenant deployment support.

One business path is not one total Port or root. Identity/Policy, Resources, Evidence, Execution and Plugin lifecycle remain distinct owners/contract surfaces. Built-in implementations all need declared owning Plugin associations; bootstrap duties remain finite independently designated duties, not ordinary inactive Plugin offers. A single physical distribution/process can contain those logical boundaries.

Proposed demonstration: a deterministic local Tool creates an attributable receipt in an isolated test target for an exact intended effect. The target's receipt/status behavior is independently observable from invoking owner state so a lost acknowledgment can be tested. This is a test realization, not a new canonical receipt entity or production storage product. The implementation task must approve its exact target/identity/failure contract before use. A truly new effect gets new intent; repeated equivalent work must not create another receipt within qualified coverage.

### 7.1 Included capabilities

| Included capability | Why required | Owning module | Prerequisite decision | Minimum test/proof |
|---|---|---|---|---|
| Reference package/typed anchors | Runnable source with enforceable boundaries | Existing owner contracts / technical root | ADR-001/002 | Install/import/type checks; no optional AI/SDK imports from contracts |
| One Application declaration | Useful end-to-end consumer | Application Composition | ADR-002/003; ADR-014 for supported facade | Domain callback uses public contracts, validation fails safely |
| Immutable effective configuration | Repeatable interpretation/recovery | Application Composition | ADR-003 | Same revision retains meaning; changed inputs create explicit new revision |
| Explicit Tenant/Principal/current policy | No temporary security bypass | Identity, Tenant, Authorization/Policy | ADR-005/006 | Allowed action plus deny/revoke/wrong-tenant/deputy cases |
| Finite root duties | Start controls without circular self-admission | Governance, Lifecycle, Evidence, Resources | ADR-005/006/009 | Missing/cyclic root evidence blocks start; exact duty ceilings |
| Capability inventory and resolution | Prove WHAT/HOW separation | Catalog/Resolution | ADR-002/006 | Exact versions, deterministic binding, unsatisfied/ambiguous result, no grant from resolution |
| Built-in business Plugin/contribution | Prove governed replaceable realization | Plugin Lifecycle/Catalog | ADR-006 | Inspect/admit/config/init/activate/publication/stop/restart stages and adverse paths |
| One Tool Provider/Adapter | Useful protected deterministic effect | Action Mediation / admitted realization | ADR-006/007/008 | Exact target/input/effect; independently observable result; test-only alternate realization |
| Supervised Execution | Work has ownership and bounded lifetime | Execution Coordination / direct driver | Proposed ADR-015; ADR-004/005/007/008 | Queue/concurrency/cancel/shutdown/orphan cases with context preserved |
| Durable state/results/obligations | Recovery and truthful duplicates | Each owner | ADR-004; lower-level persistence decision | Atomic crash/lost-ack/expected-revision guards; unknown not treated as absent |
| Resource accounting | No overspend or erased liability | Resource Admission and Accounting | ADR-007 | Explicit authority-approved unit/bound; concurrent reservation, duplicate settlement, unknown liability |
| Approval where required | Independent action entitlement | Approval owner | ADR-005/007 | Exact-action use bound, race and consumed-before-failure behavior; Human interaction only if the policy requires it |
| Dispatch arbitration | Current complete predicates at handoff | Invoking plane + participating owners | ADR-007 | Revocation races, exclusive incarnation, actual acceptance/time feasibility |
| Retry/status/reconciliation | Safe lost response and recovery | Invoking owner / Execution | ADR-008 | Equivalent committed result, conflicting reuse, horizon gaps, no blind replay |
| Mandatory custody/provenance | Attributable decisions/effects | Source owners / Evidence and Provenance | ADR-009 | Pre-effect failure blocks; post-effect loss repairs without repeated effect |
| Basic structured observation | Debug every first-slice failure | Observation Collection | Existing contracts; no ADR-013 production claim | Safe correlation, gaps, bounded output and no sensitive payload leakage |
| Restart/recovery | Useful durable local operation | Execution and relevant state owners | ADR-004/006/007/008/009 | Stop/crash/restart with pending and unknown work; old process fenced; no authority resurrection |
| Durable result/Artifact references where required | Preserve produced work and interpretation | Invoking owner; Artifact owner when producing an ArtifactVersion | Contracts; ADR-004/009 | Result references remain exact/authorized; no full Artifact platform required for unrelated work |
| Development evidence and scoped release assessment | Verify the increment, not merely demo it | Test/assessor roles; Governance release decision | ADR-011 for release | Requirement/proof mapping, retained failures, exact candidate and compatibility declaration |

Scope-specific parameters must be recorded before the corresponding path: units/precision and bounds, admission/concurrency/queue limits, deadlines and time assumptions, retention/deduplication intervals, evidence guarantees, rooted authority and threat/failure coverage. Their values come from accountable decisions and experiments, not this plan's invented production thresholds.

### 7.2 Excluded capabilities and triggers

| Excluded initially | Why defer | Inclusion trigger |
|---|---|---|
| Model/Agent/Team/Multi-Agent | Not needed for deterministic boundary proof | Staged prerequisites in §16 and a real application need |
| Workflow engine | Supervision is not durable domain orchestration | Repeated real workflow/state/branch requirement beyond direct execution |
| RAG / persistent Memory / vector database | Unrelated to first protected action | Measured information/retrieval need with its own contracts and data governance |
| Message broker / distributed services / HA | Extra failure domains and operating burden | Measured/reliability requirement that cannot be met by local scope |
| Hostile/semi-trusted external Plugin execution | In-process controls cannot provide claimed containment | ADR-012 accepted, implemented and proven for actual attacker scope |
| Enterprise IAM | Local explicit authority sufficient for first scope | Actual external identity/federation requirement and provider qualification |
| Public remote API | Expands authentication, protocol and deployment exposure | Real remote consumer requirement and boundary evidence |
| Real Secret/provider credentials | Avoid unnecessary bootstrap/material exposure | Any actual Secret use activates implemented ADR-010 path first |
| Production telemetry/export backend | Local diagnostics sufficient to develop/debug | Operational-assurance need activates ADR-013 |
| Arbitrary Plugin marketplace/loader | No ecosystem needed to prove built-in lifecycle | Real third-party distribution use and qualified supply-chain/isolation scope |
| Generic scheduler, DI framework, repository framework | No demonstrated need beyond existing owners | Evidence-driven abstraction rule, not expected future scale |
| Broad OS/runtime/upgrade matrix | No proof yet for such promises | Claim a specific additional environment/path and produce adequate evidence |

## 8. Required Gap-Routing Matrix

Severity describes the consequence of leaving the gap open at its trigger: Critical = unsafe execution/false authority; High = major usability/recovery/claim blocker; Medium = bounded local engineering gap. It is planning judgment, not a canonical incident taxonomy. “No” before source means safe stateless/foundation work may proceed; it does not waive the later gate. “If used/claimed” is a hard conditional requirement.

Route values are exactly: **A — Already covered; B — Resolve in an existing ADR; C — Lower-level implementation decision; D — New ADR justified; E — Wait for runtime/ForgeAI evidence; F — Reject as unnecessary/overengineering.** A means semantics/ownership covered, not implemented.

| Gap | Severity | Existing owner? | Remaining work | Route | Needed before source? | Before slice? | Before ForgeAI? | Before release? | Trigger |
|---|---|---|---|---|---|---|---|---|---|
| Developer experience | High | Application / public facade | Supported authoring/lifetime/diagnostic boundary | D — New ADR justified | No | Private harness allowed | Yes | Yes for supported API | First external consumer |
| Application composition | High | Application; private technical root | Same ADR-014 candidate, not second decision | D — New ADR justified | No | Internal explicit wiring | Yes | Yes | Stable composition promise |
| Execution supervision | Critical | Execution Coordination | Task ownership, bounds, cancellation/shutdown/restart | D — New ADR justified | No for foundations | Yes | Yes | Yes | First governed runner |
| Persistence product | Critical | State owners, ADR-004 | Choose/qualify lower-level realization | C — Lower-level implementation decision | Before durable code | Yes | Yes | Yes | First durable commit |
| Serialization/migration tooling | High | State owners | Exact versioned representation and recovery | C — Lower-level implementation decision | Before durable format | Yes for used state | Yes | Yes for claims | First persisted record/change |
| Development testing | Critical | Maintainer/test roles | Runner, strict typing, cases/fault seams from first change | C — Lower-level implementation decision | With first source | Yes | Yes | Yes | Every implementation increment |
| Basic observation | High | Observation Collection | Safe correlated bounded local sink | C — Lower-level implementation decision | No | Yes | Yes | Yes | First executable path |
| Production observability | High | ADR-013 | Resolve existing production integration candidate | B — Resolve in an existing ADR | No | No | If claimed | If claimed | Production monitoring/assurance |
| Secrets | Critical | ADR-010 / Secret Access | Implement and qualify accepted decision | B — Resolve in an existing ADR | If used | If used | If used | If used | First real credential anywhere |
| Hostile Plugin isolation | Critical | ADR-012 / Lifecycle/enforcement | Decide, implement and prove containment | B — Resolve in an existing ADR | No | Excluded | If needed | If claimed | Untrusted/semi-trusted code |
| Configuration semantics | High | ADR-003 | Implementation/proof already routed | A — Already covered | Accepted prerequisite exists | Yes | Yes | Yes | Configurable use |
| Dispatch/effect/evidence semantics | Critical | ADR-007/008/009 | Qualification incl. timing, not another semantic model | A — Already covered | Accepted prerequisites exist | Yes | Yes | Yes | Protected action |
| Finite scope parameters / authority roots | Critical | Governance/Resources/runtime | Concrete bounded values and qualified designations | C — Lower-level implementation decision | Before affected code/use | Yes | Yes | Yes | Root/claim admission |
| Supply-chain ownership | High | ADR-006/011 | Existing decisions cover admission/release duties | A — Already covered | No new owner | Yes for included dependencies | Yes | Yes | Dependency/Plugin/build change |
| Supply-chain tools/procedures | High | Dependency/release maintainer | Pinning, inventory, scanning/triage and integrity realization | C — Lower-level implementation decision | With first dependency | Yes, scoped | Yes | Yes, claimed scope | Dependency introduction |
| Performance baselines | Medium | Runtime/operations | Early measurements; later workload-derived targets | C — Lower-level implementation decision | No | Initial measurements | Relevant workload | Targets for promises | Runnable boundary |
| Speculative optimization framework | Medium | None needed | Reject without measurement | F — Reject as unnecessary/overengineering | No | No | No | No | Hypothetical scale only |
| Local deployment | High | Runtime/operations | Single-process start/stop/state/recovery recipe | C — Lower-level implementation decision | No | Yes, local | Yes | Yes | First runnable installation |
| Distributed deployment/HA | High | Existing owners affected | Wait for concrete scale/failure requirement | E — Wait for runtime/ForgeAI evidence | No | Excluded | If demonstrated | If claimed | Measured need |
| Model/AI integration | High | Model Interaction | Qualified bounded ModelPort path and usage/evaluation | C — Lower-level implementation decision | No | Excluded | Only AI features | If included | Reliable skeleton plus Model need |
| Agent integration | High | Agent driver / Work Coordination | Bounded state/planning/tool/delegation proof | E — Wait for runtime/ForgeAI evidence | No | Excluded | Only Agent features | If included | Stable Model/Tool + use case |
| Multi-Agent integration | High | Work Coordination / Agent drivers | Need evidence, child authority and shared work proof | E — Wait for runtime/ForgeAI evidence | No | Excluded | Only team features | If included | Proven single-Agent limits |
| ForgeAI integration | High | ForgeAI application owner | Integration brief, vertical slice and public-contract tests | C — Lower-level implementation decision | No | No | Yes | If used as release evidence | Gate 2 evidence + ADR-014 |
| AI-assisted SDLC | High | Human maintainer | Bounded roles, review and executable evidence | C — Lower-level implementation decision | Yes as working rule | Yes | Yes | Yes | First generated change |
| Release evidence workflow | High | ADR-011 | Implement coverage/compatibility/approval process | B — Resolve in an existing ADR | No | Test traceability begins | No release claim needed | Yes | Supported release claim |
| Universal platform framework layer | High | No justified owner | Reject speculative shared mechanisms | F — Reject as unnecessary/overengineering | No | No | No | No | One-consumer abstraction demand |

For route B, an accepted ADR such as ADR-010/011 normally needs execution of its implementation/qualification obligations, not reopening its decision. Reopen only on concrete contradictory evidence. Each gap has one routing choice; cross-cutting dependencies are recorded separately.

## 9. Proposed ADR-INDEX Amendments

**Recommendations only. ADR-INDEX is not modified and these IDs are not allocated by this plan.**

| Proposed candidate | Decision question | Class / priority / reversibility | Proposed dependencies | Trigger / timing | Why not merely a library choice |
|---|---|---|---|---|---|
| ADR-014 — Reference Application Authoring and Composition Experience | How does a supported consumer declare/configure/compose/validate/run/stop/test an application without private wiring or bypassing owner contracts? | B / P1 / Type 2, provided facade remains thin and versioned | ADR-002, ADR-003, ADR-006 and proposed ADR-015; accepted enforcement contracts also apply | Before supported consumer API/ForgeAI; after concrete internal call-flow and consumer brief exist | Exposes a maintained consumer boundary spanning composition, runtime lifetime and diagnostics; alternatives change application coupling and compatibility |
| ADR-015 — Reference Execution Supervision and Concurrency Model | How are live tasks/workers, queue bounds, cancellation, shutdown, cleanup and restart coordinated while preserving canonical states and effect knowledge? | B / P1 / Type 1 due to durable attempt ownership and external-effect consequences | ADR-001, ADR-002, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008, ADR-009 | Before live supervised/effectful runner; may precede ADR-014 | Cross-owner timing/failure and lifecycle consequences cannot be hidden in executor defaults |

The proposed ADR-014 dependency on ADR-015 makes the supported run/stop surface consume the supervision contract, with no reverse dependency. Number order is not dependency order: decide ADR-015 first while gathering ADR-014 consumer examples. Neither candidate blocks stateless foundation source under Gate 1.

Keep ADR-010 conditional P2: acceptance is complete, implementation moves earlier only when Secrets are actually used. Keep ADR-012 triggered by the trust scope and ADR-013 by operational claims; do not promote every conditional feature to a global P0 blocker. Link the four proposed gates and finite scope from the index only after review/acceptance of this plan.

Do not allocate new canonical ADRs for a database brand, validation library, generic testing framework, logging vendor, `.env` handling, SBOM format, separate release pipeline or additional supply-chain owner. Record necessary concrete choices below existing ADRs. Reject a generic workflow engine, global persistence repository abstraction, universal Plugin marketplace, model-mandatory Kernel or multi-agent scheduler absent evidence. Do not schedule ADR-016+ merely to make the roadmap appear complete.

## 10. Architecture freeze and anti-overengineering policy

### 10.1 Freeze point

Recommend a **foundational semantic freeze now**, on acceptance of this readiness plan: ADR-001 through ADR-011 are already accepted. Of the proposed milestones, **after the accepted ADR-011 and its protected-execution prerequisites** is the appropriate dependency-safe point. ADR-008 alone leaves mandatory custody/bootstrap/release-proof issues open; ADR-009 alone does not close dispatch/retry or release qualification. Waiting for optional isolation, production exporters or all future AI subsystems would perpetuate architecture work.

This freezes speculative foundational expansion, not implementation choices, testing, defect corrections or justified ADRs. ADR-014/015 are bounded reference mechanisms closing evidenced gaps in existing Application/Execution responsibilities; they do not reopen canonical ontology. They are the limited pre-consumer/pre-execution exceptions, not permission for another open-ended foundational sequence.

### 10.2 Evidence-driven abstraction rule

A new generic abstraction requires at least one strong basis: an existing canonical obligation; two independent real use cases; repeated demonstrated implementation duplication; an actual provider-replacement need; or a security/correctness/Conformance requirement. Two variants of the same ForgeAI feature are not automatically independent use cases. The proposer must still show that a smaller application-local function, Adapter or existing owner extension is insufficient.

Record the evidence, owner, consumer contract, alternatives, dependencies, local-run/debug/recovery burden, compatibility effect and proof obligation. A second use case is not mandatory for a real security invariant, but a hypothetical future app does not count. Keep an application-owned extension local until reuse evidence justifies promotion.

### 10.3 Stop rules

1. No new foundational abstraction without the evidence above and an accountable owner.
2. No framework layer solely because one application needs it; keep its domain objects/workflows in that application.
3. No support/production/isolation/compatibility claim beyond actual qualified evidence.
4. No optimization ADR without measurement; correctness fixes do not need a performance justification.
5. No Python-package-as-security-isolation claim; admit only the supported trust scope.
6. No Secret shortcut outside implemented, qualified ADR-010, including temporary `.env` or SDK defaults.
7. No generated implementation accepted without contract review and appropriate executable tests.
8. No large generated change spanning unrelated owners; split by one coherent behavior and proof boundary.
9. No canonical dependency on optional AI; deterministic use remains independently executable.
10. No technology-neutral framework when an implementation-local choice suffices.
11. No full rerun or new ADR by ritual: use ADR-011 material impact to select affected proof.
12. No background task, migration or repair without explicit owner, context, bounds and observable completion/uncertainty.
13. No new mandatory feature merely because its package or contract exists.
14. No upstream edits hidden inside implementation; contradictions require explicit scope and governance review.

Warning signs requiring rejection or application-local placement include ForgeAI-only names in Kernel, a complex generic interface to satisfy one provider quirk, optional systems becoming base imports, domain workflows becoming runtime behavior, or a Plugin extension used by one consumer being promoted without proof. A provider-specific extension can remain explicit without becoming canonical.

## 11. Four separate gates

These are proposed engineering acceptance gates, not new canonical lifecycle states. “Pass” requires reviewable evidence, not assertions or model agreement. This task performs none of the implementation actions.

### GATE 1 — SOURCE START

Foundation implementation may begin when:

1. The maintainer explicitly authorizes a bounded source task and its scope; acceptance of architecture alone is not that instruction.
2. ADR-001/002 and applicable accepted decisions are bound to the task; no unresolved contradiction blocks its behavior.
3. First scope/exclusions, package ownership, requirement IDs and tests are written into the task acceptance criteria.
4. Concrete local package/environment/test/static-check choices are recorded with the first increment; no CI vendor, registry or public API is required.
5. The first diff includes relevant invariant/import/typing tests and excludes real credentials, live external effects and unqualified Plugin execution.
6. A datastore/representation decision precedes durable implementation; ADR-015 precedes a live supervisor; ADR-014 precedes a supported consumer API. None is a blanket prerequisite for all stateless foundation code.

**Current disposition:** architectural prerequisites for bounded source foundations are satisfied. Authorization of the next implementation task and its concrete tool/test setup remain. No new canonical specification is required first.

### GATE 2 — GOVERNED EXECUTABLE SLICE

The first protected deterministic action is allowed only when:

1. The included scope in §7 has working owners and finite independent rooted duties; required scope parameters are explicit.
2. ADR-015 is accepted and the local task/admission/cancellation/shutdown model is implemented for the path.
3. The storage realization demonstrates the claimed atomicity/durability/history/absence/recovery behavior with actual fault tests.
4. Plugin validation/config/init/activation/offer eligibility and deterministic resolution work without self-admission or inactive binding.
5. Actual Principal/Tenant/current policy, resource/Approval controls, mandatory pre-effect custody and single effect obligation are enforced before handoff.
6. ADR-007 participation, exclusivity and timing/currentness are demonstrated at the real Adapter acceptance boundary; an unprovable boundary blocks the path, even if ordinary success tests pass.
7. The test target and operation/effect equivalence/status behavior are defined; retry/unknown/partial outcomes are durable and conservative.
8. Basic safe observation is usable; cancellation, timeout, lost acknowledgment, duplicate, post-effect evidence failure and restart cases pass for declared scope.
9. No real Secrets or hostile Plugins are used without their implemented/qualified conditional gates. No unresolved mandatory defect remains in the claimed slice.

**Current disposition:** not passed. Decisions alone do not meet any implementation proof item.

### GATE 3 — FORGEAI START

ForgeAI may consume Lego AI through a bounded integration when:

1. Gate 2 has passed and Phase 3 fault/recovery coverage is adequate for the chosen integration.
2. ADR-014 is accepted and its thin supported entry/lifetime/config/result/status interface is implemented with an integration example and compatibility expectations.
3. ForgeAI supplies one concrete workflow/use-case brief, data/authority/Secret needs, expected effects and acceptance criteria; no invented platform-wide domain requirement fills this gap.
4. ForgeAI depends on a pinned tested runtime revision and public contracts, with integration tests and explicit unsupported scope; it does not import private reference wiring.
5. Any real credentials, remote systems or broader trust assumptions meet their conditional gates first.
6. Domain data, tasks, UI, prompts, business criteria and workflow remain ForgeAI-owned; promotion requests follow §12.

ForgeAI domain discovery, UI/domain code and contract-level design can begin independently now without claiming runtime consumption. Early integration can use deterministic paths; Model/Agent work is not a prerequisite unless the chosen ForgeAI feature needs it. A supported public release is not required for pinned internal integration, but production promises remain blocked by Gate 4 and deployment proof.

### GATE 4 — FIRST USABLE RELEASE

A supported reference-runtime release requires:

1. Gate 2 and the supported developer experience are demonstrated; Gate 3's application feedback is used where available, but a full ForgeAI product is not a hidden release dependency.
2. ADR-011 exact candidate, scope/applicability ledger, evidence custody, Conformance findings, compatibility/migration relations, known gaps and impact/reuse decisions exist for the actual artifacts.
3. Package install/run/test/debug/shutdown/recovery instructions work in the exact qualified environment; dependency inventory/provenance and security findings have attributable disposition.
4. Supported state/config/Plugin/effect-history upgrade or initial-only limits are explicit; no automatic downgrade, universal Provider or OS compatibility claim.
5. All mandatory evidence and current release/publication authority are valid; actual publication identity, unknown/partial outcomes and repair follow ADR-008/009/011.
6. Published support excludes unimplemented AI/isolation/Secret/production surfaces; no undefined maturity badge substitutes for evidence.

**Production-capable is an additional scope of Gate 4, not a synonym for first usable.** Before claiming it, identify a concrete workload/deployment/threat model, measurable operating targets, resource/retention capacity, backup-and-restore proof with unknown effects, migration/shutdown/recovery exercises, operational diagnosis/alert response duties, dependency/vulnerability response, incident/Secret handling where applicable and an accountable operator. ADR-013 must be decided/implemented for the claimed production observation guarantees; ADR-010/012 activate where Secrets/trust require them. One successful local demonstration establishes none of these deployment assurances.

## 12. ForgeAI as the first architecture validator

Adopt **ForgeAI requirement ≠ Lego AI requirement.** The actual ForgeAI specification and code are not in this repository; first obtain a small integration brief rather than asserting a known domain architecture.

Consume initially: Application/configuration contracts, Capability resolution, supervised Execution, governed local Tools, existing Principal/Tenant/resource controls, evidence, result/Artifact references and local diagnostics. Add ModelPort only when the feature needs inference and its gates pass. Keep ForgeAI's product concepts, UI, project/workspace rules, domain object model, prompts/Skills, task acceptance criteria, domain workflows, tool business logic and domain-specific evaluation criteria outside Kernel and canonical platform behavior.

Promotion workflow:

1. Implement the need in ForgeAI through public contracts or an application-owned Plugin/Adapter.
2. Capture actual duplication, second consumer, replacement pressure or canonical safety requirement.
3. Identify the existing Lego AI owner, smallest transferable behavior, portability limits and proof obligations.
4. Compare keeping it local with a small reusable library/Adapter and only then a platform abstraction.
5. Submit a bounded proposal with consumer compatibility and migration evidence. Promote only after maintainer acceptance; preserve domain-specific policy in ForgeAI.

Use the first integration to measure how many concepts/imports/configuration fields a developer needs, whether failures can be diagnosed from one correlation, whether cancellation/shutdown are understandable, and whether a provider can be substituted without changing domain logic. These are qualitative/usability experiments until workload-derived targets exist, not a promise of a particular line count.

## 13. Day-one testing and evidence strategy

Development testing begins with the first implementation change. Formal Conformance evidence is a governed assessment of exact subjects and all applicable obligations; a passing test suite alone is not that finding. Tests can later become evidence through attributable versions, custody, scope and sufficiency review under ADR-011. A rejected/flaky run remains visible where material.

| Test family | Start / owner | Minimum meaningful case |
|---|---|---|
| Unit/invariant | Phase 1; implementing owner | Invalid transitions, immutable identity/revision rules, canonical error/effect separation |
| Package/import/type architecture | First source; maintainer | No contract→reference/SDK import, no optional AI on direct path, strict type checking |
| Port contracts | First supported operation; owner | Preconditions, exact result stages, current access, unsupported version/error behavior |
| Adapter substitution | First Tool realization; integration/test role | Test-only alternate same-contract implementation preserves success, failure, context, accounting and uncertainty; not a new production Provider claim |
| Configuration revisions | Phase 1; Application | Defaults/overrides explicit, same historical meaning, no raw values/ambient reload |
| Owner-state concurrency | First persistence increment; state owner | Competing revisions/absence guards, atomic result/obligation commit, coherent status |
| Supervision/concurrency | Runner introduction; Execution | Bounded queue/tasks, context propagation, cancellation races, hanging worker and shutdown |
| Tenant isolation/security negatives | First governance operation | Missing/wrong tenant, revoked Principal, forged deputy, unauthorized result disclosure even in single-tenant supported scope |
| Plugin lifecycle | First bootstrap integration | Cycle/missing root, data-only inspection, failed init, late publication after stop, restart |
| Lost acknowledgment | First guarded commit/handoff | Commit succeeds then reply lost; equivalent status returns prior result, no duplicate effect |
| Crash/restart | First durable path | Kill at before/after commit and acceptance boundaries; real store/target observations, not just mocked exceptions |
| Partial completion | First multi-owner sequence | Approval consumed then abort, effect done/audit failed; retain each fact and repair correct duty |
| Retry/reconciliation | First effect | Original expected revision retained, identity conflict, horizon gap, unknown not none |
| Evidence | First custody path | Required pre-effect outage blocks; post-effect custody failure and safe repair |
| Migration | Before first persistent-format change | Source/target interpretation, interrupted progress, retained identities/effects/liabilities; initial release explicitly declares unsupported upgrade paths |
| Composition | Walking skeleton onward | Shared resource/authority constraints across individually passing owners |
| Fault injection | Add at each boundary | Delayed/reordered acknowledgments, storage unavailable/full, crash, stale facts and evidence loss within declared failure model |
| Eventual Conformance suites | Coverage ledger grows from Phase 1; formal before claim | Requirement → proof obligation → evidence → finding; negative cases and transitive closure, no skipped-as-pass |

Fault hooks are controlled test mechanisms, not runtime authority bypasses. Synthetic credentials/data belong in isolated test scope; production secrets never become fixtures. A simulator's pass does not qualify a real external Provider. Broad testing occurs when changes or failures justify it; do not require expensive full reruns after unrelated documentation changes.

## 14. Observation, Secrets, isolation and supply chain

### 14.1 Minimum observation baseline

Operational logging/tracing/metrics ≠ mandatory Evidence ≠ authoritative owner state ≠ provenance. Observation Collection owns diagnostics; source owners create facts; Evidence and Provenance retains its declared custody/lineage duties. Shared identifiers do not merge these records or make trace output recovery state.

The first executable slice needs a bounded local structured observation path and a way for an authorized developer to follow one invocation and its failures. Record applicable Trace ID, correlation/causation, Execution/operation/effect identity, tenant-safe identity, exact configuration revision, Plugin/Provider/Adapter versions, state transition references, authorization decision reference, Tool/effect status, authoritative resource observation references, latency/time basis and canonical error/recoverability. Values need not all appear on every event; relevance and disclosure are explicit. Unknown observations are not filled with invented certainty.

Prohibit ordinary raw Secrets/credentials, unrestricted payloads, private chain-of-thought and inaccessible tenant/reference detail. Bound log size/rate/buffering and record gaps. Optional telemetry failure may follow its explicit tolerance rule; required audit failure still follows ADR-009. Tests must verify both paths independently. Debugging uses status/obligation queries plus safe correlation, never resurrecting state from logs.

ADR-013 can defer exporter standard/vendor, remote collection, dashboards, sampling at production volume, distributed trace transport, operational alerting integration and continuous-Conformance claims. It cannot defer useful local diagnostics, mandatory provenance or evidence. No logging vendor or OpenTelemetry choice is made here.

### 14.2 Secret trigger

**Before any real credential/Secret is stored, resolved or consumed by Lego AI, ADR-010 and its prerequisites must be accepted and implemented/qualified for that path.** Acceptance is now present; implementation is not. This includes model API keys, GitHub tokens, OAuth credentials, database/cloud credentials, external Tool access, root identity/evidence credentials and publication credentials.

A temporary `.env`, ignored file, environment variable or provider SDK auto-discovery cannot bypass the gate. A later `.env` source is permissible only inside a qualified governed material-source mechanism; it is not ordinary canonical configuration. A Secret-free local target/store/identity basis is preferred for the first skeleton only when its actual design needs no hidden credential. Strong security semantics are not supplied by merely calling the path local.

### 14.3 Plugin trust scope

Initial executable contributions are **built-in, locally trusted, explicitly admitted trusted code** under declared host/root assumptions. They are not semi-trusted, untrusted or arbitrary marketplace code. Admission remains mandatory even for built-ins. Python package isolation ≠ security isolation; neither namespace conventions nor a process-shared handle prevents hostile memory access.

ADR-012 activates before admitting code with insufficient trust for the shared-process assumptions, exposing real Secrets to a hostile/co-tenant Plugin scope, or claiming attacker containment across those boundaries. Decide, implement and demonstrate actual isolation first. Do not call a Plugin safe merely because it passed a declaration check.

### 14.4 Supply-chain ownership

| Concern | Existing owner / decision | Remaining concrete work |
|---|---|---|
| Dependency pinning/update | Reference build/dependency maintainer; ADR-002/011 | Record material versions, reviewed updates, repeatable install and drift checks |
| Package integrity/publisher identity | Plugin admission and Governance; ADR-006 | Qualified exact artifact/source/namespace binding, no identity by display name |
| Plugin provenance | Lifecycle/source owners and Evidence; ADR-006/009 | Exact contribution/build/dependency records and custody |
| Inventory / SBOM | Release evidence workflow; ADR-011 | Dependency inventory required for scope; choose an SBOM format only if an actual exchange/assurance requirement needs it |
| Dependency scanning/triage | Security assessor + release/dependency maintainer; ADR-011 | Select scoped tools/procedure, preserve findings and actionable disposition; clean scan not universal safety |
| Vulnerability management | Release claimant/Governance and security reviewer; ADR-011 | Named response duty, affected-scope reassessment/advisory and update procedure |
| Signing/attestation | Integrity/authenticity realization under ADR-006/011 | Implement when claimed/required; no new certifier or signing technology chosen |
| Release provenance | Source/build/Artifact and Evidence owners; ADR-011 | Exact assessed/published artifact set, dependency inputs and publication verification |

No genuinely unowned canonical supply-chain concern was found. Actual accountable task assignments, tooling and operational procedures are missing; those are implementation/release work, not grounds for another foundational ADR. Registry names and third-party ecosystem guarantees remain unclaimed.

## 15. NFRs, solo complexity budget and application velocity

### 15.1 Measurement before optimization

Begin measurements with runnable boundaries, before any performance optimization proposal. Preserve environment/build/configuration/dependency identity, workload, warm/cold distinction, sample/run count, distribution/variance, method and instrumentation overhead. No synthetic number in this plan is a production SLO.

| Scenario | Measure starting when | Evidence/use |
|---|---|---|
| Cold start, roots and Plugin activation | Phase 2 | Startup/activation latency and failure path cost |
| Idle configured runtime | Phase 2 | Idle memory/tasks, background work and observation volume |
| Conditional owner commit/status | First Phase 1 persistence prototype | Commit latency, contention and durability settings alongside crash correctness |
| Denied and allowed authorization | Phase 2 | Authorization cost without suppressing required checks |
| Protected Tool invocation versus direct target baseline | Phase 2 | Incremental admission/dispatch/evidence overhead; same effect/guarantee scope |
| Concurrent admissions and saturated queue | Phase 2/3 | Throughput, tail latency, bounded memory, cancellation and fairness observations |
| Crash and unresolved-work recovery | Phase 3 | Recovery time, backlog and correctness under declared failures |
| Repeated effects/evidence/retry retention | Phase 3 | State/evidence growth, cleanup/coverage behavior and storage budget |
| Diagnosis and telemetry | Phase 2/3 | Trace/log volume and overhead, lost-observation behavior |
| ForgeAI representative action | Gate 3 onward | Application workload, user latency, payload/cost and operating targets |

Set explicit engineering targets after baseline and real workload/resource constraints exist; set release/production promises before claiming them, with accountable approval and measured evidence. **No optimization ADR without measurement.** A benchmark cannot justify weakening correctness, custody or currentness. Unexpected inability to meet a mandatory safety bound is a qualification failure even if throughput looks good.

### 15.2 Solo-developer complexity budget

For each introduced mechanism, the maintainer must be able to explain its invariants/owner, run it locally, test/fault it, diagnose it, upgrade/migrate it, recover it and deploy its declared scope. If no credible bounded operating recipe exists, simplify/defer the scope instead of copying an enterprise pattern. One process and one distribution are defaults already supported by accepted ADRs; logical ownership still remains explicit.

| Pending subsystem/work | Classification | Reason / limit |
|---|---|---|
| Scope/task decomposition, package/test/static-check loop, AI review discipline | needed now | Unlock small safe source changes |
| Concrete config/state representations, local rooted authority, Plugin roots, resources/evidence, dispatch/retry | needed before executable slice | Each guards the first effect; implement incrementally, not a giant framework |
| Supervision decision/implementation and local diagnostics | needed before executable slice | No owned/cancellable/debuggable work otherwise |
| Public authoring/composition API and consumer integration brief | needed before ForgeAI | Prevent private wiring and accidental stable API |
| Build/provenance, support/compatibility ledger, migration/retention and release gate | needed before release | Actual bounded support claims |
| Secrets implementation | trigger-based later | Move earlier immediately if any real credential is required |
| Hostile Plugin containment / production exporters / enterprise IAM / remote API | trigger-based later | Broader threat/operating claims only |
| Model, Agent, Team, Workflow, Memory, retrieval, broker, HA | trigger-based later | Application evidence and staged gates |
| Universal registry/DI/persistence framework, generic certification program, speculative multi-service control plane | unjustified | No current requirement or proof benefit |

### 15.3 Realistic application throughput

Prototypes can become fast to assemble when their requirements fit already qualified authentication, Models, Tools, Artifacts, workflows, evaluation, diagnostics and deployment templates. Likely compositional categories include bounded internal automation, document processing, retrieval-backed assistance and developer-tool workflows **once** their required reusable modules actually exist. This is a conditional engineering expectation, not evidence these modules are implemented today.

Production-ready applications still require domain acceptance criteria, data/permission design, failure/recovery, quality/security evaluation, deployment operations and supported-provider proof. Regulated/high-risk applications additionally need their actual external obligations, entitled review, traceability and risk evidence; the platform cannot supply these by naming a profile. There is no defensible promise of dozens of unrelated production-grade applications in one or two weeks.

Measure real delivery cycle time, reused versus new integration work, escaped defects and operating burden after ForgeAI and another consumer. Rapid composition is credible when scope, data and policies are familiar, adapters/deployment paths are proven, and only bounded domain logic differs. New providers, trust models or high-risk effects remain engineering work.

## 16. AI-native SDLC and staged intelligence

### 16.1 Multiple coding assistants

This is a development process recommendation, not authorization for autonomous agents to merge, migrate or release. Tools/models may change; role and evidence boundaries stay explicit.

| Role | Duty | Acceptance control |
|---|---|---|
| Architect | Bind task to accepted clauses/owners, alternatives and explicit unknowns | Human accepts consequential architecture; no generated semantic amendments hidden in code |
| Implementer | One bounded behavior/diff with declared dependencies and tests | Source contracts constrain implementation; no ambient authority or speculative framework additions |
| Reviewer | Independently read actual diff and governing sources | Check owner boundaries, failure semantics, new dependencies and omissions; not merely the implementer's summary |
| Test/Adversarial Agent | Attempt violating/race/crash paths and challenge assumptions | Separate oracle/requirements derivation, actual commands/results and limitations |
| Human Maintainer | Accept/reject consequential architecture, migrations, risk and release changes | Verify evidence, scope and current authority; model consensus is not proof |

Use small work items with requirement IDs, allowed files/owners, observable success/failure criteria and a defined stop boundary. Give reviewers original sources and observed results; do not let the implementing model's rationale become the only test oracle. Different models can share the same mistake. Resolve disagreement through clauses, counterexamples and executed evidence rather than majority vote.

Record dependencies deliberately; review build/install hooks and public-interface leakage. Avoid generated migrations on valuable state until source/target, backup/restore and dry-run/fault evidence are reviewed under current authority. Keep generated commits cohesive and inspectable; split independent owners/features, preserve user edits and do not use broad rewrites to hide semantic changes. A passing happy-path or copied mock is insufficient for durability, authorization or provider behavior. Require actual test provenance and retain material failing/flaky results.

### 16.2 First Model slice

After the deterministic skeleton and relevant failure/recovery proof: Application → ModelPort → replaceable admitted Model Provider/Adapter → governed invocation → authoritative resource accounting → safe evidence/trace → Artifact/result. No Agent required.

Prerequisites: supported consumer entry, supervised cancellation/timeout, current governance, explicit model/output contracts and uncertainty, provider usage/unknown-charge treatment, deterministic fixtures plus scoped real-provider qualification, and implemented ADR-010 before any API key. A Secret-free qualified local model is possible but still introduces runtime/resource/quality assumptions. Provider replacement preserves consumer semantics/errors/disclosure/resource guarantees; content-quality comparison uses Evaluation with declared cases and uncertainty, not identical generated text. No provider vendor is selected here.

### 16.3 First Agent slice

Require stable Model and Tool paths, actual application need and a bounded Agent driver/state contract. Pin behavior/version and allowed tools, bound plan revisions/steps/resources, supervise state transitions and cancellation, and mediate every proposed Tool call through existing controls. Delegation is explicit only where used; it never transfers the Agent's maximum authority. Checkpoint support, if claimed, needs compatible driver state plus authoritative effect/accounting references and restart proof; otherwise declare it unsupported. Evaluate task quality, prompt injection, tool misuse, termination and cost. Begin with one bounded Agent, not a team framework.

### 16.4 First Multi-Agent slice

Require evidence that single-Agent/deterministic composition is insufficient, and already proven supervisor/child lifecycle, delegation/authority intersection, parent/child resource conservation, shared Artifact/version conflict handling, cancellation/retry/effect identity and complete causal traces. Then test Supervisor → Worker Agents → bounded Delegation → mediated Tool calls → shared Artifacts, with independent current authority at every protected action. A Team is not an acting Principal; each performer is attributed. Test failed/hanging worker, duplicate delegation, conflicting outputs, canceled parent, shared budgets and nested retries before support. No distributed topology follows automatically.

## 17. Walking skeleton and failure proof

The conceptual chain is Application → configuration → Principal/TenantContext → Capability requirement → Resolution → admitted Plugin contribution → Provider/Adapter → Execution → current authorization/resource/evidence admission → protected effect → owner result/history commit → custody/observation → result.

This linear view must not imply that all durable state/evidence starts after the effect. Persist exact intent/attempt and required source obligations first, obtain mandatory pre-effect custody, commit claims under ADR-007, and only then reach actual acceptance. Afterward each owner records its own observations/results and outstanding duties; no global transaction spans the target.

Bootstrap precedes executable resolution: inspect/admit/configure/initialize/activate required contributions using independent roots, publish ordinary eligibility, then resolve the application's exact requirement. Resolution identifies a provider but grants neither authority nor spend. A test-only alternate realization proves substitutability without requiring a second production provider or external protocol.

| Exercise | Required observable result |
|---|---|
| Success | One intended local receipt effect, exact retained outcome, resource reconciliation, evidence and trace references |
| Denial | No protected effect; canonical safe denial and no foreign existence leakage |
| Timeout | Deadline/timeout cause preserved independently from none/partial/completed/unknown effect; pending work bounded |
| Lost acknowledgment | Distinguish owner commit from effect acceptance; same equivalent operation retrieves permitted outcome or honest uncertainty |
| Retry | Same intended effect/deduplication scope and original preconditions, no new capacity/deadline, current authority |
| Partial completion | Consumed claim/audit failure remains real; repair appropriate obligation without repeating effect |
| Runtime restart | Exclusive incarnation, exact historical config/state, visible unresolved obligations, no replay from missing records or old grants |

Reject a “demo mode” that bypasses evidence, authorization or durability just to print success. A smaller genuinely non-effectful scope is acceptable earlier under Gate 1, but must not be labeled Gate 2.

## 18. Recommended development phases

The sequence is dependency-driven, not a waterfall where testing and evidence arrive last. Foundation work can overlap bounded decision closure. ForgeAI domain discovery starts now; its runtime consumption starts at Gate 3. Release assurance runs incrementally from Phase 1 and can finish for a deterministic scope before optional Model/Agent phases. The numeric phase labels do not make AI a release prerequisite.

| Phase | Entry criteria | Deliverables | Tests / evidence | Exit criteria | Main risks | Explicit non-goals |
|---|---|---|---|---|---|---|
| 0 — Bounded gap closure | This plan reviewed; existing decisions accepted | Authorize foundation task; propose ADR-015 before runner and ADR-014 before consumer; scope parameters/qualification work items | Source/owner trace and decision alternatives | No unresolved decision on the next affected increment; Gate 1 task ready | Architecture paralysis | No new canonical ontology, optional ADR completion marathon |
| 1 — Foundation/package | Gate 1 authorization | Incremental ADR-002 package subset, values/Ports, config, concrete storage decision/qualification, strict local test/build loop | Invariant/import/type/config/owner-state tests; early commit measurements | Tested foundations and qualified enough state for integration | Empty-framework scaffolding, weak persistence | No protected live runner before its gate, no all-domain scaffolding |
| 2 — Deterministic skeleton | Relevant foundations and ADR-015 accepted | Finite roots, one business contribution/effect, supervision, claims/evidence/status/local diagnostics | Success/deny/context/lifecycle/hand-off/concurrency and initial crash cases | Gate 2 passes exact local scope | Control-plane integration gaps, unproven timing | No Model/Agent/remote service/real Secrets |
| 3 — Failure/recovery proof | Gate 2 candidate | Complete declared crash/lost-ack/cancel/partial/repair/shutdown behavior, developer runbook | Actual store/target fault injection and migration/restore limits; growth/recovery measurements | No unresolved mandatory failure in chosen consumer scope | False happy-path confidence | No HA or universal crash guarantee |
| 4 — First Model capability, optional | Phase 3 plus Model need; Secret gate if used | Direct ModelPort realization, provider/result/usage boundaries | Stub and actual provider scope, cancellation/unknown charge, quality/uncertainty and substitution | Bounded Model support demonstrated | Hidden credential/SDK retries, quality overclaim | No Agent prerequisite or provider-vendor lock-in |
| 5 — ForgeAI integration | Gate 3; Phase 4 only for Model-dependent feature | One real ForgeAI vertical slice, public integration tests, friction/reuse findings | Contract/consumer tests and actual domain acceptance criteria | Useful integration without private imports or domain leakage | Framework creep, platform/product coupling | No complete ForgeAI product requirement for platform progress |
| 6 — First Agent capability, optional | Stable Model/Tool/supervision and explicit need | Bounded Agent state/planning/tool/delegation/cancel behavior | Safety/quality/cost, injection, step bound and checkpoint cases if claimed | One bounded Agent meets stated task and safety criteria | Autonomy inflation, state/effect confusion | No multi-agent framework or generalized cognition |
| 7 — First Multi-Agent capability, optional | Phase 6 + demonstrated coordination need | Bounded supervisor/workers, shared Artifacts and delegated authority | Parent cancellation, worker failure, concurrent updates/budgets, nested retries | Traceable and conservative composed execution | Multiplying failure/authority paths | No automatic distribution or unbounded hierarchy |
| 8 — Release assurance | Any supported scope with implemented Gates 2/API and evidence | ADR-011 candidate/manifests/findings, compatibility, exact publication and instructions | Full applicable closure, change-impact reuse, package/migration/security/publication evidence | Gate 4 usable-release criteria met | False universal/production claims | No requirement to wait for phases 4/6/7; no certification scheme |
| 9 — Triggered production scope | Concrete operator/workload/deployment need | ADR-013 integration and conditional Secret/isolation features, operational procedures/targets | Recovery/restore, diagnosis, workload/resource/retention and incident exercises | Gate 4 production claim justified for exact deployment scope | Enterprise imitation, operational overload | No universal enterprise/high-risk readiness |

## 19. Risk register

Likelihood is a qualitative current planning estimate given a document-only repository and solo-maintainer context, not measured incidence. Impact refers to the affected engineering/safety outcome. Owners are responsibilities, not newly appointed authorities.

| Risk | Likelihood | Impact | Trigger | Mitigation | Owner | Exit condition for current scope |
|---|---|---|---|---|---|---|
| Architecture paralysis | High | High | Another generic ADR before runnable proof | Freeze foundations, limit to ADR-014/015 and concrete tasks | Maintainer/architect | Foundation increment and Gate 2 plan executed without speculative expansion |
| Overengineering | High | High | Multiple services/frameworks for one action | Local one-process scope and complexity budget | Runtime maintainer | Solo run/debug/recover recipe demonstrated |
| Control-plane dominance | High | High | Many policy records, no usable invocation | Equal DX/execution work and walking skeleton | Architect/runtime | Consumer runs/cancels/diagnoses a governed action |
| Bad developer experience | Medium | High | Consumer imports private wiring or copies boilerplate | ADR-014 + ForgeAI integration experiment | Application/DX maintainer | Supported API used by real integration with actionable errors |
| Excessive generic abstraction | High | High | One-consumer domain concept enters Kernel | Evidence rule and application-local extension | Architect | Each promoted abstraction has explicit justified owner/use evidence |
| Missing supervision | High | Critical | Detached tasks, swallowed cancellation or hanging shutdown | ADR-015, bounds and fault cases | Execution maintainer | Task/worker lifecycle and unresolved-work proof passes |
| Hidden persistence weakness | Medium | Critical | Crash loses result/claim/evidence history | Lower-level ADR-004 qualification, real crash tests | State/storage maintainer | Acknowledged atomic sets survive declared failures |
| Insufficient failure testing | High | Critical | Demo success mistaken for usable runtime | Fault seams and negative cases from first boundary | Test/reliability role | Scope's loss/race/restart/partial cases evidenced |
| Logging/evidence confusion | Medium | Critical | Trace used as audit acknowledgment/recovery state | Separate stores/contracts/acks even if co-located | Observation/Evidence owners | Optional sink failure and mandatory custody failure behave distinctly |
| Temporary Secret bypass | High | Critical | API key in .env/SDK default for quick integration | Hard implemented ADR-010 gate | Security/integration maintainer | No unqualified real-secret path, material exclusion tests pass |
| False Plugin isolation claim | Medium | Critical | Built-in package checks called sandboxing | Explicit admitted trusted scope; ADR-012 trigger | Plugin/security maintainer | Claims match actual attacker assumptions/proof |
| Dependency/supply-chain compromise | Medium | Critical | Unreviewed library/update or artifact mismatch | Inventory, pinning, scoped scanning, exact provenance | Dependency/release maintainer | All included inputs attributable; findings dispositioned; artifact matches |
| AI-generated quality drift | High | High | Generated code diverges from owners/contracts | Small tasks, source-aware review and tests | Maintainer/reviewer | Diff traces to requirements and observable tests |
| Shared model hallucination | Medium | High | Several assistants repeat same unsupported assumption | Independent source review and adversarial oracle | Reviewer/test role | Conclusion supported by clauses and executed evidence, not agreement |
| Unreviewable generated diffs | High | High | Unrelated modules rewritten together | Cohesive change limits and split tasks | Implementer/maintainer | Each accepted increment has reviewable behavior/proof boundary |
| ForgeAI/Lego AI coupling | High | High | Product object/workflow becomes core default | Public contracts, separate domain ownership, promotion process | ForgeAI owner/architect | Integration works without private imports or domain concepts in Kernel |
| Premature multi-agent complexity | Medium | High | Team framework before single-Agent need | Stage gates and measured coordination problem | Agent/Work Coordination maintainer | Bounded single-Agent/child/effect behavior proven first |
| Premature distributed architecture | Medium | High | Broker/HA introduced for hypothetical scale | Measurement and failure-scope justification | Runtime/operations | Local limit documented before topology proposal |
| False production-readiness claim | High | Critical | ADR acceptance or one demo labeled production-ready | Separate Gate 4 scope/operational evidence | Release authority | Exact supported deployment/workload and procedures evidenced |
| Unprovable dispatch timing/currentness | Medium | Critical | Check-to-acceptance can pause outside qualified bounds | Early actual-boundary feasibility test; reject unsupported path | Runtime/security | Declared ordering/timing proven or scope explicitly blocked |
| Retention/storage exhaustion | Medium | High | Unresolved obligations outlive capacity assumptions | Bounded admission and measured growth; no silent deletion | Resources/Evidence/state owners | Coverage/retention promises fit admitted operational capacity |
| Unsafe restore/downgrade | Medium | Critical | Old snapshot reinstates permission or repeats effect | Exact compatibility and post-restore reconciliation/fencing | State/Execution owners | Restore exercise preserves history, liabilities and current authority |

## 20. Review completeness and immediate work recommendation

This plan covers both planes, GAP-A through GAP-D, the required routing matrix, four separate gates, scoped v0.1 inclusion/exclusion, proposed index amendments, day-one tests/observation, Secret/isolation triggers, supply-chain ownership, NFRs, AI-native review, realistic throughput, staged intelligence, phases and risks. These are proposed planning decisions, not passed runtime tests.

Recommended immediate sequence: accept/revise the finite scope and freeze; authorize one foundation/package/config/invariant-test increment under existing ADR-001/002/003; prepare the bounded ADR-015 before live supervision, qualify the local persistence realization under ADR-004, and develop the internal deterministic test harness. Prepare ADR-014 using that call-flow plus the ForgeAI brief before external API commitment. This avoids both unsafe early effects and indefinite architecture delay.

All existing accepted artifacts and ADR-INDEX remain unchanged. No additional ADR, source code, test, configuration, credentials or operational manifest is created. The only new file is this proposed planning document.

## 21. Final Verdict

Current architecture readiness:
READY WITH CONDITIONS

Critical gaps before further ADR work:
Adopt finite scope and evidence-driven freeze; restrict new candidates to the demonstrated authoring/composition and execution-supervision gaps. Distinguish missing implementation from missing architecture.

Critical gaps before source implementation:
Explicit authorization of a bounded foundation task, concrete local package/test/static-check setup and requirement-linked acceptance criteria. Existing canonical/ADR decisions suffice for stateless foundations; storage and runner decisions gate only their affected implementation.

Critical gaps before executable runtime:
ADR-015 decision/implementation, qualified persistence, finite actual roots and scope parameters, complete protected-execution/custody/retry chain, bounded diagnostics and actual failure/restart/currentness proof.

Critical gaps before ForgeAI:
Gate 2 and adequate Phase 3 evidence, accepted/implemented ADR-014 consumer boundary, one concrete ForgeAI integration brief, pinned integration tests and any triggered Secret/provider qualification.

Critical gaps before AI/Agents:
Reliable deterministic Model/Tool/supervision foundations, Model-specific usage/quality/provider evidence and implemented Secret handling when needed; bounded single-Agent proof precedes any Multi-Agent claim.

Critical gaps before release:
ADR-011 actual scope/coverage/compatibility/custody/build/publication evidence and supported developer instructions. Production additionally requires concrete deployment/workload targets, recovery/operations evidence and applicable ADR-013/010/012 mechanisms.

New ADR candidates justified:
Provisional ADR-014 — Reference Application Authoring and Composition Experience; provisional ADR-015 — Reference Execution Supervision and Concurrency Model. Neither is created or indexed here.

New ADR candidates rejected:
Canonical database/tooling/vendor decisions, duplicate supply-chain/release/Secrets owners, speculative generic workflow/DI/persistence frameworks, marketplace/distributed/Multi-Agent infrastructure without actual need.

Architecture freeze point:
Now, upon review acceptance of this plan, after the already accepted ADR-011 and protected-execution prerequisites; permit only bounded evidenced mechanisms, implementation-driven corrections and justified changes.

Source implementation start:
After explicit authorization of Gate 1's bounded foundation increment; do not wait for optional ADR-012/013 or all AI functionality. This planning task itself authorizes no source work.

ForgeAI start:
Domain discovery/development can begin independently now. Lego AI runtime consumption starts at Gate 3, with deterministic integration before AI where useful; production use requires its actual release/deployment evidence.

Recommended next action:
Review and accept or revise this readiness plan, then authorize a small tested foundation increment and the bounded supervision decision before implementing the live runner. Keep authoring/API and persistence decisions at their explicit triggers; create no further speculative architecture.
