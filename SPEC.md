# Lego AI Operating Layer — Canonical Specification

**Specification version:** 0.1.0  
**Status:** ACCEPTED — CANONICAL SEMANTIC SPECIFICATION  
**Authority:** [intent.md](intent.md), version 1.0, ACCEPTED — FOUNDATIONAL  
**Scope:** Technology-neutral domain semantics and behavioral contracts

## 1. Authority, scope, and normative language

This document defines WHAT Lego AI means. It refines, and MUST NOT override, `intent.md`. A conflict MUST be reported and resolved through the intent change process before the conflicting behavior is treated as conformant. No implementation convenience constitutes an amendment.

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in this document are to be interpreted as described in BCP 14 (RFC 2119 and RFC 8174) when, and only when, they appear in all capitals.

MUST and MUST NOT represent mandatory requirements. SHOULD and SHOULD NOT permit a documented exception only when the full implications are understood and the rationale, impact, and compensating measures are recorded. MAY denotes permission, not a requirement.

Lowercase descriptive language explains concepts and does not waive normative requirements. Required properties MUST have meaningful values; an empty collection is valid only where zero members is permitted. Optional properties MAY be absent; absence MUST NOT imply authority, consent, unlimited resources, successful execution, or any other implicit default not explicitly defined by this specification.

This specification defines semantic properties, not programming interfaces, physical records, wire formats, or storage layouts. A property may be represented directly or through an unambiguous, authorized reference. Multiple independent implementations can conform without sharing representation or deployment topology.

### 1.1 What this document does not own

This document does not select an implementation language, model vendor, agent framework, workflow engine, storage system, event broker, protocol adapter, cloud, or deployment architecture. It does not define runtime code, provider adapters, infrastructure, concrete schemas, or language interfaces. Those decisions belong to lower-level architecture, contracts, and architecture decision records (ADRs).

The initial reference-runtime guidance in intent §25 remains applicable to that reference runtime; it is not a requirement that every conforming implementation share its topology. No particular transport or persistence technique is mandatory.

`SPEC.md` is the root canonical specification requested for this phase. It occupies the specification layer shown as `spec/` in intent §47; that directory is not a competing authority. Future specifications MUST cite this document and MUST NOT silently redefine it.

### 1.2 Conformance scope

An implementation MUST declare its supported specification version, concepts, capability versions, ports, extensions, and unsupported optional features. It MUST satisfy all cross-cutting requirements applicable to its supported behavior. Supporting a subset MUST NOT be presented as implementing every capability. Unsupported mandatory requirements MUST fail explicitly.

Agents, Models, Teams, Workflows, Memory, and retrieval MUST be independently consumable where their declared dependencies permit. An Application MUST be able to operate without an Agent or a language model. A direct capability invocation remains governed and traceable, but does not require inventing a Goal, Plan, Team, or conversation.

## 2. Shared semantic rules

The following rules apply to **every concept in §4**, including embedded values and supporting concepts. Concept entries add requirements to these rules. Their properties are cumulative; subtype entries inherit their parent requirements. These rules avoid repeating identical security and tenancy obligations in every entry.

### 2.1 Identity, ownership, and references

**S-01.** Every independently referenced entity MUST have a stable identity, concept kind, owner, scope, lifecycle status, and applicable definition/schema revision. A value embedded in another entity MAY use its owner's identity plus an unambiguous local key. Identity MUST NOT be derived solely from mutable display names or implementation addresses. Distinct owners or tenants MUST NOT accidentally resolve to the same entity.

**S-02.** Ownership means accountability for the entity's governance and lifecycle. It does not automatically grant permission, prove authorship, or imply physical containment. Each entity MUST have exactly one accountable owner at a time; contributors and custodians MAY be many. Owner transfers MUST be authorized, recorded, and MUST preserve provenance and applicable retention obligations.

**S-03.** References MUST identify their target kind, identity, and scope, and MUST pin a revision when historical interpretation or execution depends on it. Reference validation MUST check existence or explicitly declared unresolved status, compatibility, access, and tenant scope. An unresolved reference MUST NOT be used for execution. Historical references MAY terminate at a governed tombstone after deletion; they MUST NOT silently identify a different object.

**S-04.** Relationships do not transfer ownership or authorization by implication. Reusable definitions MAY be shared through explicit publication and access policy. Tenant-scoped uses of shared definitions MUST retain distinct execution state, authority, resources, and private data.

### 2.2 Common properties and validation

All entries inherit the required properties in S-01 and references in S-03. Optional common properties are display name, description, labels, annotations, external correlation references, and explicitly namespaced extensions. Governed records MUST additionally identify their applicable access, retention, and audit policies, directly or through versioned policy references. Instances MUST distinguish definition version from mutable state revision.

**S-05.** Validation MUST check required properties, allowed cardinalities, valid state transitions, revision compatibility, reference integrity, and all applicable constraints before admitting a definition or authorizing its use. Invalid or unknown mandatory semantics MUST be rejected. Unknown optional metadata MAY be retained without execution meaning. Extension data MUST NOT override canonical fields or requirements.

**S-06.** Changes MUST carry the expected prior state revision or equivalent conflict-detection semantics. Conflicting updates MUST be rejected or reconciled under an explicit rule with provenance. A last-arriving update MUST NOT silently erase authority changes, consumed resources, approval decisions, or committed work.

### 2.3 Lifecycle and versioning defaults

**D — Definition lifecycle:** draft → validated → active → deprecated → retired. Validated MAY return to draft before activation; validated MAY go directly to retired; active MAY go directly to retired for safety reasons. Published semantic content is immutable: amendments create a new version. Deprecation discourages new use without rewriting existing bindings. Retirement prohibits new use; existing use follows explicit drain, migration, or termination policy.

**R — Record lifecycle:** created → validated → recorded → retained → disposed. Invalid candidates are rejected before recording. Recorded facts are immutable; corrections are new records referring to the corrected record. Disposition MUST follow policy and preserve permitted minimal tombstones. Retention MAY begin immediately at recording. A record of an event does not imply that event succeeded.

**V — Embedded value lifecycle:** proposed → validated → bound → superseded. Bound content is immutable in its enclosing revision. A replacement requires a new enclosing revision. Values cannot outlive their owner's retention policy without an independently governed copy.

**S-07.** Where §5 provides an explicit lifecycle, it replaces these default states. All transition requirements in §5.1 still apply. Deletion is governed disposition, not an alternate path around lifecycle obligations.

**S-08.** Definition changes MUST follow §11 compatibility rules. Execution and historical records MUST retain the versions that governed them. A state revision is not a new semantic definition version. No identifier may be reused to disguise a breaking change.

### 2.4 Universal security, tenancy, and observability

**S-09.** Every use MUST be evaluated against the acting Principal's current authorization and applicable Policy at the relevant TrustBoundary. Capability availability, Role membership, ownership, or possession of a reference alone MUST NOT authorize an action. Untrusted content MUST be treated as data and MUST NOT alter control-plane authority.

**S-10.** Every operational entity MUST have exactly one tenant scope. Deliberately shared definitions MAY instead have an explicit publication scope and custodian. Every Execution MUST bind exactly one effective TenantContext, including in a single-tenant environment. There is no implicit wildcard tenant. Scope MUST propagate to delegated work, artifacts, retrieval, messages, events, checkpoints, evaluations, telemetry, and resource accounting.

**S-11.** Cross-tenant access MUST require an explicit grant covering the resource, action, purpose where required, recipient, and applicable transfer constraints. Both source and destination policies MUST permit the operation. A crossing MUST retain the originating scope and create a distinct destination use or copy where needed; relabeling data's tenant is forbidden. Missing or contradictory scope MUST stop the operation before disclosure or effect. Shared definitions MUST NOT embed private tenant state or Secrets.

**S-12.** Material lifecycle changes, authority decisions, boundary crossings, resolutions, execution attempts, resource consumption, and work-product production MUST be traceable through attributable records. Records MUST carry event time, recording time where different, relevant identities and revisions, result, and correlation/causation links where applicable. Telemetry MUST obey access and retention policies. Secrets, sensitive payloads, and private model reasoning MUST NOT be indiscriminately logged. Private chain-of-thought MUST NOT be required for provenance or conformance.

## 3. Canonical relationships and ownership

The arrows below describe associations, not mandatory execution pipelines. `0..*` means zero or more; `1..*` means one or more. Each direction's cardinality is stated explicitly.

| Association | Allowed cardinality and meaning |
|---|---|
| Tenant → operational entity | A Tenant scopes 0..* entities; each operational entity has exactly 1 tenant scope. Shared definitions follow S-10. |
| Application → Organization | An Application associates 0..* Organizations; an Organization MAY serve 0..* Applications in its tenant. Association does not transfer ownership. |
| Organization → Team | An Organization owns 0..* Teams; each operational Team has exactly 1 accountable Organization. Other Organizations MAY collaborate through authorized associations. |
| Team → Team | A Team composes 0..* child Teams; a child MAY participate in 0..* compositions. Composition MUST be acyclic and does not change its accountable Organization. |
| Organization/Team → Role | An Organization or Team owns 0..* Role definitions; each Role has exactly 1 owner. Definitions MAY be reused by authorized reference. |
| Role ↔ Actor | Each Role has 0..* assignments; each Actor has 0..* assignments. Each assignment binds exactly 1 Role and 1 Actor in a stated scope and interval. Required staffing cardinality is a Role property, not a universal one-Actor rule. |
| Organization → Goal | An Organization owns 0..* Goals; every Goal has exactly 1 accountable Organization, as required by intent §54. Applications declare the intent that motivates Goals. |
| Goal → Plan | A Goal has 0..* Plan versions/alternatives. Each Plan targets 1..* Goals with compatible ownership/authority. A selection record determines which revisions apply to which work. |
| Plan → Task | A Plan references 0..* Tasks in draft and 1..* when active. A Task MAY occur in 0..* Plans, but each Execution binds at most 1 governing Plan revision. |
| Task → Delegation | A Task has 0..* Delegations. Each Delegation targets exactly 1 Task or exactly 1 Goal; the associated Goal MAY additionally be recorded for a Task delegation. |
| Delegation → delegate | Each Delegation has exactly 1 delegator Actor and 1 delegate Actor or Team. A Team delegate MUST identify the accountable recipient Principal and its authorized acceptance process. |
| Task/Delegation → Execution | A Task has 0..* attempts. An Execution references 0..1 Task and 0..1 governing Delegation; direct capability use need have neither. A Delegation MAY produce 0..* attempts and subordinate Delegations. |
| Execution → ArtifactVersion | An Execution produces 0..* ArtifactVersions; each version has exactly 1 producer attribution. External production MUST be explicitly identified instead of inventing a local Execution. |
| Execution → Outcome | An Execution contributes to 0..* Outcomes; each Outcome identifies 1..* supporting evidence references. An Outcome has exactly 1 accountable Team under intent §54. |
| Application → CapabilityRequirement | An Application declares 0..* requirements; each requirement has exactly 1 owning declaration, which MAY instead be a Task, Role, Plugin, or composite dependency. |
| Requirement → Resolver → Resolution → Provider | A resolution request includes 1..* requirements and exactly 1 resolver identity/version. Each satisfied atomic requirement has exactly 1 selected provider binding unless the requirement explicitly specifies a provider set and its aggregation semantics. |
| Provider → CapabilityVersion | A Provider advertises 1..* offers; an offer identifies exactly 1 CapabilityVersion. A version MAY have 0..* providers. |
| Plugin → Provider/Adapter | A Plugin contributes 0..* providers and adapters; each contribution has exactly 1 owning Plugin version. Built-in contributions follow the same descriptive and governance obligations. |
| Actor → Principal | An Actor has 1..* valid Principal associations during active participation. Every action selects exactly 1 acting Principal. The association is not a grant. |
| Role assignment → Permission → capability use | Assignments MAY establish eligibility for grants. Effective Permission is determined by authorization and policy. Required/available Capabilities describe ability; Permission describes whether that ability may be exercised. |
| Artifact → ArtifactVersion/Relationship | An Artifact has 0..* versions in draft and 1..* when available. Each version belongs to exactly 1 Artifact. Each relationship has exactly 1 source and 1 target, with endpoint revisions where semantically needed. |

An Agent is an individual software Actor with bounded decision autonomy. A Team is a composition coordinating Actors and child Teams, never an Actor subtype by implication. An Organization is a governance and goal-accountability composition, not a privileged runtime. A Role describes responsibility; an Actor performs it. Team participation, Role assignment, delegated authority, and resource allocation MUST be independently inspectable.

Direct capability use MAY produce Artifacts and operational results without canonical Goal or Outcome entities. If a result is promoted to an Outcome, an accountable Team MUST be identified. Minimal Organizations and Teams MAY consist of existing human/service compositions; they MUST NOT require agent orchestration or new privilege. This reconciles intent §§11–12 and §54 without forcing organizational bookkeeping onto every invocation.

## 4. Canonical concept catalog

Each entry uses the same thirteen dimensions, grouped for readability: **Purpose; Definition; Responsibilities; Required properties; Optional properties; Relationships; Lifecycle; Invariants; Validation; Versioning; Security; Tenancy; Observability.** Shared rules in §2 apply in addition to the named specializations. A lifecycle marker D, R, or V has the exact meaning in §2.3.

### 4.1 Application and ownership

#### Application

- **Purpose:** Preserve domain intent across technology changes. **Definition:** A governed composition declaring desired behavior and capability needs. **Responsibilities:** Own intent, configuration, composition, and acceptance criteria.
- **Required properties:** Intent, accountable owner, capability requirements (possibly empty), composition references, configuration revision, governance references. **Optional properties:** Organizations, Goals, Workflows, blueprints, activation triggers, evaluation profile.
- **Relationships:** §3; Application scopes its executions without owning every reused definition. **Lifecycle:** §5.2.
- **Invariants:** MUST express requirements independently of provider implementations; explicit extensions follow §7. **Validation:** Activation MUST validate composition, configuration, policies, and mandatory resolution.
- **Versioning:** Intent/configuration revisions used for execution MUST be pinned. **Security:** Activation is not blanket execution authorization. **Tenancy:** A reusable definition MAY be shared; each operational use binds one tenant. **Observability:** Record activation, revisions, resolutions, and execution correlations.

#### Tenant

- **Purpose:** Establish an isolation and governance scope. **Definition:** A boundary for accountable resources, data, and operations. **Responsibilities:** Scope ownership, policy, access, and resource accounting.
- **Required properties:** Tenant identity, accountable administrative owner, isolation policy, lifecycle status. **Optional properties:** External identity mapping, residency constraints, commercial metadata.
- **Relationships:** Scopes Applications, Organizations, Principals, and other operational entities. **Lifecycle:** provisioned → active ↔ suspended → closing → closed; active MAY enter closing directly.
- **Invariants:** Tenant identity MUST NOT be silently reassigned. **Validation:** Closing MUST settle or explicitly preserve live work, retention, and resource obligations.
- **Versioning:** Governance changes are revisioned, identity remains stable. **Security:** Tenant administration requires explicit grants. **Tenancy:** Parent/child business relationships MUST NOT imply shared access. **Observability:** Audit tenant transitions and cross-scope grants.

#### Organization

- **Purpose:** Coordinate goal accountability. **Definition:** A composition of people, services, agents, Teams, Roles, and policies under governance. **Responsibilities:** Own Goals and Team accountability.
- **Required properties:** Accountable owner, governance references, Team and Role references (possibly empty). **Optional properties:** Application associations, organizational relationships, shared knowledge references.
- **Relationships:** Owns Goals and operational Teams; may serve multiple Applications. **Lifecycle:** D; retirement MUST settle Goal and Team accountability.
- **Invariants:** MUST NOT acquire privileged runtime authority by being an Organization. **Validation:** Goal owners and Team ownership MUST resolve within permitted scope.
- **Versioning:** Composition and governance revisions MUST remain attributable. **Security:** Organizational hierarchy is not implicit authorization. **Tenancy:** Operational Organization belongs to one Tenant. **Observability:** Record goal ownership and governance changes.

### 4.2 Intelligent organization and Actors

#### Team

- **Purpose:** Coordinate work and own Outcomes. **Definition:** A reusable composition of Actors and optionally child Teams. **Responsibilities:** Coordinate Roles, work allocation, and outcome accountability.
- **Required properties:** Owning Organization, composition, coordination rules, Role requirements, accountability/acceptance rules. **Optional properties:** Shared Context, Skills, goals served, interaction preferences.
- **Relationships:** Actors MAY participate through multiple scoped assignments; Teams MAY contain humans, services, agents, and Teams. **Lifecycle:** §5.3.
- **Invariants:** MUST NOT be equated with an agent runtime; composition MUST be acyclic. **Validation:** Active work MUST have eligible assignees for required Roles and unambiguous responsibility.
- **Versioning:** Work binds a composition revision; changing membership does not rewrite history. **Security:** Team membership grants no automatic union of members' permissions. **Tenancy:** Membership crossings follow S-11. **Observability:** Record assignments, coordination decisions, and Outcome acceptance.

#### Role

- **Purpose:** Separate responsibility from performer. **Definition:** A named responsibility contract with qualification and work expectations. **Responsibilities:** Describe obligations, required Capabilities, and assignment constraints.
- **Required properties:** Responsibility description, owner, capability requirements, assignment scope/cardinality rules. **Optional properties:** Eligibility criteria, separation-of-duty constraints, Permission eligibility references.
- **Relationships:** Many-to-many with Actors through RoleAssignment. **Lifecycle:** D; assignments have independent validity.
- **Invariants:** A Role MUST exist independently of any Actor. **Validation:** Assignments MUST meet eligibility, interval, and staffing rules before work begins.
- **Versioning:** Responsibility changes create a new Role version. **Security:** A Role describes eligible authority, never self-issued grants. **Tenancy:** Reuse MUST preserve assignment scope. **Observability:** Record assignment and responsibility revisions.

#### Actor

- **Purpose:** Attribute participation and actions. **Definition:** A Human, Service, or Agent able to perform Roles. **Responsibilities:** Act within accepted work, authority, and constraints.
- **Required properties:** Actor kind, Principal associations, participation status. **Optional properties:** Role assignments, available Capability references, availability preferences.
- **Relationships:** Performs Roles, accepts Delegations, participates in Teams and Executions. **Lifecycle:** registered → available ↔ unavailable → retired; available MAY retire directly after obligations settle. Agent specializes this lifecycle.
- **Invariants:** Actor identity MUST NOT be confused with its Role or authorization Principal. **Validation:** Every action MUST bind a valid acting Principal and permitted scope.
- **Versioning:** Behavioral definition changes are versioned independently of identity. **Security:** Ability to perform an action does not confer Permission. **Tenancy:** External Actors use explicitly authorized tenant-scoped participation. **Observability:** Attribute actions without exposing unnecessary personal information.

#### RoleAssignment

- **Purpose:** Make responsibility fulfillment explicit. **Definition:** A scoped binding of one Actor to one Role. **Responsibilities:** Establish accountable participation and its validity.
- **Required properties:** Actor, Role version, assigning Principal, scope, validity interval, assignment status. **Optional properties:** Team, qualification evidence, Permission-grant references.
- **Relationships:** Bridges Actor and Role; MAY apply within a Team or Organization. **Lifecycle:** proposed → active → ended or revoked; proposed MAY be rejected.
- **Invariants:** MUST NOT exceed the assigner's assignment authority or grant action authority by itself. **Validation:** Eligibility, separation of duties, and required staffing counts MUST be checked.
- **Versioning:** Reassignment creates a new binding or explicitly superseding revision. **Security:** Revocation MUST affect subsequent action authorization. **Tenancy:** Actor and Role scope must be compatible. **Observability:** Record assignment, acceptance where required, and revocation.

#### Agent

- **Purpose:** Provide bounded autonomous decision-making. **Definition:** A software Actor that selects or proposes actions toward objectives using explicit state and decision behavior. **Responsibilities:** Respect goals, report results, and request governed actions.
- **Required properties:** Actor properties, behavior version, autonomy bounds, state description, capability requirements. **Optional properties:** Models, Skills, Memory, planning/delegation capabilities.
- **Relationships:** MAY use Models; MAY perform Roles; is not a Team or retrieval pipeline. **Lifecycle:** §5.4.
- **Invariants:** Reasoning MUST NOT create authority; an Agent MUST NOT enforce its own trustworthiness solely through instructions. **Validation:** Activation MUST validate dependencies, bounds, and external enforcement.
- **Versioning:** Behavior and state compatibility MUST be recorded. **Security:** Treat decisions as untrusted requests at action boundaries. **Tenancy:** Memory and context MUST retain tenant scope. **Observability:** Record actions, decisions' public rationale where available, versions, and errors; private reasoning is unnecessary.

#### Human

- **Purpose:** Enable native human participation. **Definition:** An Actor representing a person acting through authenticated identity. **Responsibilities:** Perform assigned work and attributable decisions.
- **Required properties:** Actor properties, human identity association. **Optional properties:** Availability, notification preferences, qualifications.
- **Relationships:** MAY perform Roles, create Artifacts, evaluate work, or issue HumanApproval decisions. **Lifecycle:** Actor lifecycle; inactivity MUST NOT imply consent.
- **Invariants:** Humans MUST be supported as ordinary participants, not only failure recovery. **Validation:** Sensitive decisions MUST authenticate the correct authorized person.
- **Versioning:** Qualification/assignment revisions remain distinct from person identity. **Security:** Human status does not bypass policy. **Tenancy:** One person MAY participate through different tenant-scoped Principals. **Observability:** Minimize personal data while retaining decision attribution.

#### Service

- **Purpose:** Enable callable software participation. **Definition:** A software Actor providing declared behavior without requiring autonomous planning. **Responsibilities:** Fulfill assigned contracts and report effects/results.
- **Required properties:** Actor properties, behavior contract version, capability requirements/offers. **Optional properties:** Availability conditions, interaction constraints.
- **Relationships:** MAY perform Roles, accept Tasks, or expose Tools/Providers. **Lifecycle:** Actor lifecycle.
- **Invariants:** A Service need not be remote or separately deployed. **Validation:** Contract compatibility and action authorization MUST be checked.
- **Versioning:** Behavior versions MUST accompany attributable work. **Security:** Service credentials MUST be scoped; automation does not confer trust. **Tenancy:** Shared Service implementations MUST isolate operational uses. **Observability:** Record invocations, effects, and failures.

### 4.3 Intent and work

#### Goal

- **Purpose:** Express a desired end condition. **Definition:** An accountable objective defined by success criteria rather than an execution sequence. **Responsibilities:** State desired change, constraints, and acceptance evidence.
- **Required properties:** Owning Organization, intent/Application reference, objective, success criteria, evaluation/acceptance authority, constraints. **Optional properties:** Parent Goal, Plans, priority, deadline, Budgets.
- **Relationships:** MAY have child Goals and multiple Plans; parent Goal links MUST be acyclic. **Lifecycle:** §5.5.
- **Invariants:** Completion MUST be assessed against criteria, not inferred from Task termination. **Validation:** Criteria and acceptance authority MUST be meaningful and resolvable.
- **Versioning:** Criteria changes create a new revision and explicit impact on running work. **Security:** Replanning MUST NOT expand authority. **Tenancy:** Goal ownership remains in one tenant. **Observability:** Record progress evidence and terminal assessment.

#### Plan

- **Purpose:** Describe an intended approach to Goals. **Definition:** A versioned arrangement of Tasks, dependencies, and assumptions. **Responsibilities:** Explain sequencing, constraints, and success contribution.
- **Required properties:** Target Goals, Task references, dependency semantics, assumptions, author attribution. **Optional properties:** Alternatives, estimates, branching/replanning conditions.
- **Relationships:** Organizes Tasks; MAY be represented by an ArtifactVersion without becoming identical to its presentation. **Lifecycle:** §5.6.
- **Invariants:** Plans MAY be static, generated, adaptive, human-authored, Agent-authored, or hybrid. **Validation:** Dependencies MUST be resolvable; cycles need explicitly bounded iteration semantics, otherwise MUST be rejected.
- **Versioning:** Active content is immutable; replanning supersedes a revision. **Security:** Plan authorship is not execution authority. **Tenancy:** All referenced work must pass scope checks. **Observability:** Record selected alternatives and reasons/evidence for replanning.

#### Task

- **Purpose:** Define an assignable unit of work. **Definition:** A bounded work obligation with inputs and completion criteria. **Responsibilities:** Specify expected behavior/products and track accepted completion.
- **Required properties:** Work description, accountable owner, input contract, completion criteria, requirements, constraints, expected result contract. **Optional properties:** Goal, Plans, Role, dependencies, deadline, Budgets.
- **Relationships:** MAY execute directly or through Delegation; may have multiple attempts. **Lifecycle:** §5.7.
- **Invariants:** Task identity MUST remain distinct from an Execution attempt. **Validation:** Inputs/dependencies MUST satisfy declared readiness rules.
- **Versioning:** Changed work semantics require a new revision; attempts pin it. **Security:** Assignment does not confer unrestricted tool access. **Tenancy:** Inputs/results remain scoped. **Observability:** Record readiness, attempts, acceptance, and unresolved effects.

#### Delegation

- **Purpose:** Transfer bounded responsibility for work. **Definition:** An explicit offer and acceptance of work under attenuated authority. **Responsibilities:** Preserve parent constraints, accountability, and completion reporting.
- **Required properties:** Delegator, delegate, target Task or Goal, allowed authority, requirements, Context reference, constraints, inherited policy/Budget references, expected Artifact/Outcome contract, deadline bound, approval requirements, status. Explicitly unbounded deadline is permitted only if parent and policy allow it.
- **Optional properties:** Parent Delegation, progress expectations, revocation conditions, approved supplemental grants.
- **Relationships:** Links work to Actor/Team recipient and child Executions. **Lifecycle:** offered → accepted → active → completed, failed, revoked, expired, or cancelled; offered MAY be rejected, cancelled, or expired; accepted MAY be revoked, cancelled, or expired.
- **Invariants:** MUST satisfy §8 attenuation and resource propagation. **Validation:** Acceptance and each consequential action MUST validate the current grant chain.
- **Versioning:** Accepted scope is immutable; amendments require explicit replacement/acceptance. **Security:** Supplementary authority requires a separate authorized grant. **Tenancy:** Delegation cannot launder scope. **Observability:** Record offer, acceptance, chain, effects, and completion evidence.

#### Execution

- **Purpose:** Represent one actual attempt. **Definition:** An attributable performance of work or a direct capability invocation under bound context. **Responsibilities:** Govern effects, maintain state, and report results.
- **Required properties:** ExecutionContext, work/capability contract revision, performer attribution, resolution binding where used, attempt status, state revision. **Optional properties:** Task, Delegation, WorkflowState, parent attempt, checkpoints, Artifacts, errors.
- **Relationships:** Each retry is a new Execution; child Executions retain causal links. **Lifecycle:** §5.8.
- **Invariants:** MUST distinguish successful performance from accepted Task/Goal success. **Validation:** Admission and every governed effect MUST satisfy §6 and §9.
- **Versioning:** Execution identity and bound revisions never change; state advances explicitly. **Security:** Recheck live restrictions on resume. **Tenancy:** Exactly one TenantContext. **Observability:** Every attempt MUST have a Trace and effect/result attribution.

#### Outcome

- **Purpose:** Record accountable achievement or non-achievement. **Definition:** An evidence-backed assessment of work against declared expectations. **Responsibilities:** Preserve assessed result and acceptance status.
- **Required properties:** Owning Team, target Goal/Task/expectation reference, assessment, evidence, assessor, assessment time. **Optional properties:** ArtifactVersions, EvaluationResults, residual issues, acceptance decision.
- **Relationships:** May combine evidence from multiple Executions and Artifacts. **Lifecycle:** R; disputed or corrected assessments create linked records.
- **Invariants:** A claim without evidence MUST NOT be treated as verified success. **Validation:** Assessment MUST use the applicable criteria revision and authorized acceptance process.
- **Versioning:** Corrections MUST preserve prior assessments. **Security:** Self-reported outcomes require the declared verification policy. **Tenancy:** Evidence visibility MUST not exceed access grants. **Observability:** Record assessment provenance and acceptance separately.

### 4.4 Capability system

#### Capability

- **Purpose:** Name reusable ability independently of implementation. **Definition:** An identified semantic contract describing behavior and guarantees. **Responsibilities:** Define what consumers may require and providers must supply.
- **Required properties:** Namespace, local identity, semantic purpose, contract owner, version references. **Optional properties:** Classification, related Capabilities, discovery metadata.
- **Relationships:** Has CapabilityVersions; required by compositions and supplied through offers. **Lifecycle:** D.
- **Invariants:** Identity MUST NOT be a disguised mandatory technology choice. **Validation:** Namespace ownership and uniqueness MUST be verified.
- **Versioning:** Semantic guarantees belong to immutable CapabilityVersions. **Security:** Describes ability, not permission. **Tenancy:** Published contracts MAY be shared. **Observability:** Identity/version MUST appear in resolution and invocation records.

#### CapabilityRequirement

- **Purpose:** Declare needed ability. **Definition:** A consumer's request for a Capability under admissibility and selection conditions. **Responsibilities:** Separate mandatory needs, optional needs, hard constraints, and preferences.
- **Required properties:** Owning declaration, Capability identity, acceptable version range, mandatory/optional designation, hard constraints, provider multiplicity rule. **Optional properties:** Ranked preferences, fallback/degradation contract, namespaced extension requirements.
- **Relationships:** Belongs to Application, Role, Task, Plugin, or composite dependency. **Lifecycle:** V.
- **Invariants:** Optional means omission is permitted, not that hard constraints can be ignored. **Validation:** Contradictory ranges/constraints MUST fail before selection.
- **Versioning:** Changes create a new owning declaration revision. **Security:** Requirements MUST include applicable trust restrictions. **Tenancy:** Resolution uses consuming tenant's effective policies. **Observability:** Retain selected, omitted, and rejected requirement explanations.

#### CapabilityProvider

- **Purpose:** Supply a declared Capability. **Definition:** A substitutable realization advertising versioned offers and operational conditions. **Responsibilities:** Meet advertised contracts and expose dependencies, limitations, and health.
- **Required properties:** Provider identity/version, owning Plugin version, offers, dependency requirements, compatibility, trust/Permission needs, health status. **Optional properties:** Cost estimates, performance claims, extension offers.
- **Relationships:** One provider can offer multiple versions/capabilities through Adapters/Ports. **Lifecycle:** registered → eligible ↔ unavailable → withdrawn; registered MAY be withdrawn.
- **Invariants:** Claims MUST NOT be mistaken for verified guarantees. **Validation:** Compatibility and conformance evidence MUST satisfy consumer policy.
- **Versioning:** Offer changes affecting guarantees require new versions. **Security:** Selection grants no permissions. **Tenancy:** Eligibility MUST include scope, data-transfer, and isolation requirements. **Observability:** Record offer revisions, health changes, invocation outcomes.

#### CompositeCapability

- **Purpose:** Reuse compositions as abilities. **Definition:** A Capability whose guarantees depend on an explicit composition of requirements. **Responsibilities:** Define dependency, aggregation, and failure semantics.
- **Required properties:** Capability properties, component requirements, composition rules, output guarantees, failure/degradation behavior. **Optional properties:** Alternatives, optional components.
- **Relationships:** Recursively depends on atomic or composite Capabilities. **Lifecycle:** D.
- **Invariants:** MUST NOT hide provider coupling or cycles without resolvable semantics; §7 prohibits unresolved recursive cycles. **Validation:** Full dependency closure MUST satisfy the advertised aggregate contract.
- **Versioning:** Dependency changes MUST be assessed for external compatibility. **Security:** Composed authority is bounded, never the automatic union of providers' authority. **Tenancy:** Each dependency crossing is checked. **Observability:** Preserve component bindings and propagated failures.

#### CapabilityVersion

- **Purpose:** Pin a precise ability contract. **Definition:** An immutable version of a Capability's semantics. **Responsibilities:** State guarantees and compatibility boundaries.
- **Required properties:** Capability identity, semantic version, input/output meaning, behavior, errors, constraints, compatibility declarations. **Optional properties:** Deprecation guidance, migration references.
- **Relationships:** Referenced by requirements, offers, and resolutions. **Lifecycle:** D; published content remains immutable.
- **Invariants:** An existing version MUST NOT change meaning. **Validation:** Version ordering and compatibility MUST follow §11.
- **Versioning:** Breaking guarantees require a new major version. **Security:** Security semantics are part of compatibility. **Tenancy:** Shared contract does not share tenant data. **Observability:** Exact version MUST be available in historical binding records.

#### CapabilityConstraint

- **Purpose:** Express admissibility or preference precisely. **Definition:** A typed predicate over capability/provider/composition facts. **Responsibilities:** State what must hold or how eligible choices are ranked.
- **Required properties:** Subject/property, operator semantics, expected value with units where relevant, hard/preference designation, origin. **Optional properties:** Preference priority, evidence freshness, explanation.
- **Relationships:** Used by requirements, policies, and resolver input. **Lifecycle:** V.
- **Invariants:** Unknown truth MUST NOT satisfy a hard constraint. **Validation:** Operators, types, units, and scope MUST be interpretable; unsupported hard predicates fail.
- **Versioning:** Changed predicate meaning changes its containing revision. **Security:** Provider assertions need evidence according to policy. **Tenancy:** Tenant policy constraints cannot be weakened by preferences. **Observability:** Record predicate outcomes without leaking prohibited facts.

#### CapabilityResolver

- **Purpose:** Determine admissible bindings. **Definition:** The logical responsibility that evaluates requirements against available offers and constraints. **Responsibilities:** Resolve dependencies, conflicts, ambiguity, and selection evidence.
- **Required properties:** Identity/version, supported semantics, selection policy, determinism declaration. **Optional properties:** Ranking strategy descriptions, diagnostic detail policy.
- **Relationships:** Consumes requirements and offer snapshots; produces CapabilityResolution. **Lifecycle:** D for definition; each resolution activity has its own governed Execution/record.
- **Invariants:** MUST follow §7 and MUST NOT silently relax requirements. **Validation:** Unsupported semantics MUST yield a resolution error.
- **Versioning:** Selection-rule revisions MUST be recorded. **Security:** Cannot confer invocation authority. **Tenancy:** Candidate discovery and diagnostics MUST be scope-filtered. **Observability:** Record input snapshot, rules, and decisions.

#### CapabilityResolution

- **Purpose:** Preserve an explainable binding decision. **Definition:** An immutable result of resolving a requirement set. **Responsibilities:** Identify selected dependency closure or explicit non-success.
- **Required properties:** Requirements/revisions, resolver/version, candidate snapshot reference, effective constraints/policies, selected bindings, omitted requirements, status, reasons, provenance. **Optional properties:** Alternatives, validity interval, selection tie-break evidence.
- **Relationships:** Used by Executions; includes all selected dependency bindings. **Lifecycle:** R; operational validity MAY expire or be revoked without changing the recorded decision.
- **Invariants:** Success requires every mandatory requirement and selected optional requirement to be fully satisfied. **Validation:** Reuse MUST recheck current eligibility and authorization.
- **Versioning:** Re-resolution creates a new result. **Security:** Resolution is not an access token. **Tenancy:** Result is scoped to its consumer. **Observability:** Must explain selection and non-selection to authorized observers.

### 4.5 Intelligence, reusable expertise, and action

#### Model

- **Purpose:** Supply inference or transformation ability. **Definition:** A versioned computational model with declared input/output behavior and ModelCapabilities. **Responsibilities:** Report outputs, limits, and relevant usage under its contract.
- **Required properties:** Model identity/version, input/output contract, declared capabilities, known limits. **Optional properties:** Modality, quality evidence, reproducibility conditions.
- **Relationships:** Supplied by Providers; usable directly, by Workflows, Services, or Agents. **Lifecycle:** D; operational availability is separate from definition status.
- **Invariants:** Model MUST NOT be synonymous with Agent or a language-only model. **Validation:** Inputs and requested features MUST satisfy its contract.
- **Versioning:** Historical executions pin the best available immutable model revision; opaque provider changes MUST be disclosed as a reproducibility limitation. **Security:** Model outputs are untrusted data. **Tenancy:** Invocation and data-use constraints MUST be enforced. **Observability:** Record model/version, usage, and permitted input/output references.

#### ModelCapability

- **Purpose:** Describe an inference-specific ability. **Definition:** A Capability specialization for model behavior, such as interpreting a modality or producing constrained output. **Responsibilities:** State supported behavior and measurable conditions.
- **Required properties:** Capability properties, behavioral conditions and evidence requirements. **Optional properties:** Quality thresholds, supported modalities, known failure modes.
- **Relationships:** Advertised for Model versions through Provider offers. **Lifecycle:** D.
- **Invariants:** A capability name MUST NOT imply perfect correctness. **Validation:** Claimed quality and structural guarantees MUST be distinguished.
- **Versioning:** Changed guarantees follow CapabilityVersion rules. **Security:** Output constraints do not make content trusted. **Tenancy:** Shared ability definitions do not authorize data transfer. **Observability:** Evaluations SHOULD reference the exact model capability/version tested.

#### Skill

- **Purpose:** Package reusable expertise. **Definition:** A versioned asset of instructions, examples, resources, and optional executable/action dependencies. **Responsibilities:** Declare expertise, usage conditions, dependencies, and evaluation expectations.
- **Required properties:** Skill identity/version, expertise description, content references, capability/Tool requirements, usage contract. **Optional properties:** Examples, prompts, schemas, scripts, policies, evaluation cases, constituent Skills.
- **Relationships:** Used by Actors or Workflows; MAY be preserved as Artifacts. **Lifecycle:** D.
- **Invariants:** Skill content MUST NOT grant authority or silently install dependencies. **Validation:** Resources, requirements, composition cycles, and compatibility MUST be checked.
- **Versioning:** Independently releasable; content changes create a new version. **Security:** Executable content and instructions remain subject to policy and boundary checks. **Tenancy:** Shared expertise MUST exclude private operational state. **Observability:** Record Skill versions contributing to work.

#### Tool

- **Purpose:** Provide a bounded action. **Definition:** A declared operation with inputs, outputs, effects, and failure semantics. **Responsibilities:** Expose action constraints and report actual or uncertain effects.
- **Required properties:** Action contract/version, input/output meaning, effect classification, Permission needs, errors, retry/idempotency semantics. **Optional properties:** Compensation contract, approval requirements, cost estimates.
- **Relationships:** Invoked by authorized Actors or direct Application execution through a Port/Provider. **Lifecycle:** D.
- **Invariants:** A request MUST pass enforcement before effects occur. **Validation:** Inputs, authority, policy, approval, resources, and deadline MUST be checked.
- **Versioning:** Changed effects or safety guarantees are compatibility-relevant. **Security:** Secrets MUST be resolved through authorized access, not exposed by default. **Tenancy:** Action targets and returned data retain scope. **Observability:** Record action/effect identity, result, and uncertainty.

### 4.6 Workflow and execution state

#### Workflow

- **Purpose:** Describe coordinated behavior. **Definition:** A versioned control-and-data-flow contract with explicit transitions and completion conditions. **Responsibilities:** Define sequencing, branching, concurrency, waiting, and error handling.
- **Required properties:** Behavior definition/version, input/output contracts, transition rules, start/terminal conditions, dependency and failure semantics. **Optional properties:** Roles, human steps, iteration bounds, checkpoint/durability requirements.
- **Relationships:** Instantiated through Execution and WorkflowState; MAY implement a Plan but is not a Goal. **Lifecycle:** §5.9.
- **Invariants:** MUST NOT require an Agent or Model; human participation is normal behavior. **Validation:** Reachability, joins, loops, and error paths MUST have explicit semantics.
- **Versioning:** Each run pins a definition; migration is explicit. **Security:** Transitions cannot bypass action authorization. **Tenancy:** Branches inherit scope. **Observability:** Record transitions, waits, joins, and effects.

#### WorkflowState

- **Purpose:** Make progress explicit. **Definition:** The revisioned state of one Workflow instance within an Execution. **Responsibilities:** Track active positions, bound variables, waits, branch outcomes, and completed effects.
- **Required properties:** Workflow version, Execution, revision, active/terminal positions, variables/references, wait conditions, effect references. **Optional properties:** Pending approvals, branch correlations, recovery metadata.
- **Relationships:** Checkpoints capture it; transitions occur under Workflow rules. **Lifecycle:** created → advancing ↔ waiting → terminal; advancing MAY terminate directly.
- **Invariants:** State MUST NOT depend exclusively on conversation history. **Validation:** A transition MUST originate from the expected prior revision and a valid condition.
- **Versioning:** Each committed change creates a new state revision. **Security:** State input is not authorization. **Tenancy:** Scope cannot change on transition. **Observability:** Record transition causation and state revisions, with sensitive values referenced/redacted.

#### Checkpoint

- **Purpose:** Support inspection and permitted recovery. **Definition:** An immutable snapshot/reference set sufficient to resume a declared execution boundary. **Responsibilities:** Preserve resumable state and relevant committed-effect knowledge.
- **Required properties:** Execution, state revision, definition/binding versions, state references, completed/pending effect references, creation time, compatibility conditions. **Optional properties:** Integrity evidence, retention override subject to policy.
- **Relationships:** Captures WorkflowState or other explicit execution state. **Lifecycle:** R; usable checkpoints MAY become invalid for resumption without losing historical status.
- **Invariants:** A checkpoint MUST NOT assert rollback of external effects. **Validation:** Resume MUST validate integrity, compatibility, live authority, approval validity, deadline, and remaining resources.
- **Versioning:** Migration creates a new checkpoint with provenance. **Security:** MUST NOT restore revoked authority or obsolete Secret values. **Tenancy:** Resume retains originating scope. **Observability:** Record creation, selected recovery point, and recovery limitations.

#### ExecutionContext

- **Purpose:** Carry attributable governing context. **Definition:** The bound identity envelope and versioned references governing one attempt. **Responsibilities:** Propagate scope, authority constraints, causal links, and effective configuration.
- **Required properties:** Execution identity, TenantContext, Application revision, acting Principal/performer attribution, Trace, authorization and policy references, Budget/resource-policy references, deadline bound, configuration revision, provenance root, correlation identity. Empty budget sets or an unbounded deadline MUST be explicit and policy-permitted.
- **Optional properties:** Organization, Team, RoleAssignment, Actor, Goal, Plan, Task, Workflow, Delegation, parent Execution, input Context, additional correlation identifiers.
- **Relationships:** Exactly one bound context per Execution; §6 defines propagation. **Lifecycle:** V; consequential changes require a linked new attempt or an explicit context amendment record as limited by §6.
- **Invariants:** Immutable identities MUST be separate from mutable progress and resource balances. **Validation:** References MUST be scope-consistent and applicable to the admitted action.
- **Versioning:** Original governing revisions remain recorded alongside live restriction decisions. **Security:** Context is evidence to validate, not self-authenticating authority. **Tenancy:** TenantContext cannot be replaced mid-attempt. **Observability:** Correlates work without requiring sensitive payload logging.

### 4.7 Information, Memory, and Knowledge

#### Context

- **Purpose:** Supply relevant information for work. **Definition:** A scoped collection of inputs and references with origin and trust classification. **Responsibilities:** Preserve meaning, source, freshness, and visibility.
- **Required properties:** Content/references, origin, trust/data classification, applicable scope, content revision. **Optional properties:** Relevance annotations, validity interval, summarization lineage.
- **Relationships:** Consumed by Actors, Tools, Models, Tasks, and Delegations; distinct from ExecutionContext. **Lifecycle:** V or R when independently recorded; the representation MUST declare which.
- **Invariants:** Informational content MUST NOT override authority or policies. **Validation:** Reference access, freshness constraints, and input contracts MUST be checked.
- **Versioning:** Summaries/transforms MUST retain source lineage and create new revisions. **Security:** Treat imported instructions as untrusted data unless explicitly admitted as governed definitions. **Tenancy:** Scope-filter before disclosure. **Observability:** Record permitted source references, not indiscriminate content.

#### Message

- **Purpose:** Convey participant communication. **Definition:** An attributable communication with declared communicative intent and recipients. **Responsibilities:** Preserve sender, content, and conversation/causal context.
- **Required properties:** Sender attribution, recipient scope, content/reference, communicative type, creation time, correlation. **Optional properties:** Reply reference, Artifact references, delivery/acknowledgment records.
- **Relationships:** Actors and Applications exchange Messages; Messages MAY cause Events or work. **Lifecycle:** R for content; delivery status is separate and MAY be pending, delivered, failed, or unknown.
- **Invariants:** Delivery MUST NOT imply acceptance, authorization, or execution. **Validation:** Recipients and content disclosure MUST be authorized.
- **Versioning:** Corrections are new linked Messages. **Security:** A message asking for an action is not an approved action. **Tenancy:** Routing MUST preserve tenant boundaries. **Observability:** Track causation/delivery without requiring a chat interface.

#### Memory

- **Purpose:** Retain information from activity for later use. **Definition:** Governed state or records with working, session, semantic, episodic, or procedural meaning. **Responsibilities:** Define recall scope, update, forgetting, and retention behavior.
- **Required properties:** Memory kind, owner/scope, content contract, update/recall semantics, retention/access policies. **Optional properties:** Confidence, temporal relevance, source/episode links.
- **Relationships:** Used independently or by Actors/Workflows; MAY reference Knowledge and Artifacts. **Lifecycle:** D for the memory contract; entries use R with linked corrections or explicit revisioned state semantics.
- **Invariants:** Memory is not a vector database; storage does not define meaning. **Validation:** Updates and recall MUST honor scope, classification, and declared consistency.
- **Versioning:** Contract and entries have independent revisions. **Security:** Retrieved memory remains source-classified, not automatically trusted. **Tenancy:** Recall MUST filter before disclosure; shared memory requires explicit grants. **Observability:** Attribute updates, recalls, forgetting, and sources subject to policy.

#### Knowledge

- **Purpose:** Represent governed reusable information and claims. **Definition:** A body of content, facts, assertions, or relationships with source and applicability metadata. **Responsibilities:** Preserve provenance, validity, and access semantics.
- **Required properties:** Content/reference, source, scope, validity/freshness description, governance policy. **Optional properties:** Confidence, citations, topic relationships, curation status.
- **Relationships:** MAY be retrieved, curated from Memory, or preserved as Artifacts. **Lifecycle:** R for knowledge records; changing collections are revisioned definitions/state with explicit entry membership.
- **Invariants:** Knowledge is not retrieval-augmented generation; that is a composition using retrieval and generation. Such a composition is not inherently an Agent. **Validation:** Claims MUST retain attribution; unknown truth MUST NOT be promoted to verified fact.
- **Versioning:** Changes retain source/version history. **Security:** Knowledge content is not executable policy. **Tenancy:** Visibility applies to content and existence metadata. **Observability:** Record curation and source lineage where used.

#### Retriever

- **Purpose:** Select relevant accessible information. **Definition:** A capability realization for querying sources and returning attributed results. **Responsibilities:** Apply query semantics, access filtering, and result provenance.
- **Required properties:** Retrieval contract/version, source scopes, query/result contracts, filtering and ranking semantics. **Optional properties:** Confidence/scores with defined meaning, freshness constraints, multiple retrieval strategies.
- **Relationships:** Reads Knowledge, Memory, or other governed sources; independently usable. **Lifecycle:** D.
- **Invariants:** Retrieval MUST NOT require an Agent, generation, or a particular index. **Validation:** Query and every returned reference MUST satisfy access and source constraints.
- **Versioning:** Ranking/contract changes MUST be independently evaluable. **Security:** Result text MUST NOT change caller authority. **Tenancy:** Cross-scope results need explicit grants. **Observability:** Record query attribution, source revisions, and permitted selection evidence.

### 4.8 Work products and coordination

#### Artifact

- **Purpose:** Preserve first-class work products. **Definition:** A governed identity grouping versions of a meaningful product. **Responsibilities:** Maintain ownership, discoverability, lifecycle, visibility, and relationships.
- **Required properties:** Identity, type, owner, tenant, version references, metadata, provenance reference, policy, retention, visibility. **Optional properties:** Title, classification refinements, tags, current-version designation, relationships.
- **Relationships:** Has ArtifactVersions and typed ArtifactRelationships; documents, code, reports, images, videos, datasets, plans, and results are valid types. **Lifecycle:** §5.10.
- **Invariants:** MUST be independent of any file/object storage technology. **Validation:** Available Artifacts MUST have at least one valid version; aliases MUST resolve unambiguously.
- **Versioning:** Artifact identity persists across immutable content versions. **Security:** Access to metadata and content MUST both be governed. **Tenancy:** Ownership and tenant MUST be explicit. **Observability:** Record production, access where required, revisions, release, and disposition.

#### ArtifactVersion

- **Purpose:** Identify exact produced content. **Definition:** An immutable content and provenance revision of one Artifact. **Responsibilities:** Preserve what was produced, by whom, and under what conditions.
- **Required properties:** Artifact identity, unique version identity, content reference, content type/interpretation, producer, creation time, metadata snapshot, provenance, applicable policy/retention/visibility. **Optional properties:** Integrity evidence, predecessor versions, EvaluationResults, release labels.
- **Relationships:** Producer is an Actor with Execution attribution when locally executed, or an explicitly external source. **Lifecycle:** R, with release/withdrawal recorded separately.
- **Invariants:** Content references MUST identify stable content or explicitly declare inability to preserve it; unavailable content MUST NOT be represented as retrievable. **Validation:** Release MUST check content accessibility/integrity guarantees and required evaluations/approvals.
- **Versioning:** Changed content creates a new version; branch/merge ancestry MAY be many-to-many without renumbering history. **Security:** Revoking visibility does not mutate content history. **Tenancy:** Imported versions retain source scope/provenance. **Observability:** Exact versions MUST be referenced by downstream work.

#### ArtifactRelationship

- **Purpose:** Explain work-product connections. **Definition:** A typed directed relation between Artifacts or pinned versions. **Responsibilities:** State derivation, dependency, supersession, citation, containment, or evaluation links.
- **Required properties:** Source, target, relation type/version, creator attribution, creation time. **Optional properties:** Rationale, qualifiers, evidence.
- **Relationships:** Each edge has two governed endpoints. **Lifecycle:** R; removal/correction is a new record.
- **Invariants:** Derivation and supersession MUST be acyclic; citation MAY be cyclic. **Validation:** Endpoint kinds, direction, revisions, and type-specific cardinalities MUST be checked.
- **Versioning:** Relationship vocabulary has independent compatibility rules. **Security:** A relationship MUST NOT disclose a protected target to unauthorized readers. **Tenancy:** Cross-tenant edges require permitted metadata disclosure. **Observability:** Preserve relationship creation and lineage traversal provenance.

#### Event

- **Purpose:** Report a fact relevant to coordination. **Definition:** An immutable attributable statement that something occurred. **Responsibilities:** Preserve event meaning, source, time, and causation.
- **Required properties:** Event identity, type/version, source attribution, occurrence time, tenant scope, payload/reference, correlation/causation where applicable. **Optional properties:** Recording time, ordering domain/sequence, subject references.
- **Relationships:** MAY trigger Applications, Workflows, or evaluation; MUST remain distinct from an imperative command or Message. **Lifecycle:** R; delivery has independent attempt records.
- **Invariants:** Duplicate delivery MUST NOT be mistaken for a new fact; no global ordering or exactly-once effect guarantee is implied. **Validation:** Consumers MUST validate source, version, scope, and applicable deduplication semantics.
- **Versioning:** Event meaning is versioned; recorded events are immutable. **Security:** Receiving an Event does not authorize effects. **Tenancy:** Publication and subscription/disclosure are governed. **Observability:** Preserve causal links and duplicate/out-of-order handling decisions.

### 4.9 Governance and security

#### Policy

- **Purpose:** Bound permitted behavior. **Definition:** An authoritative versioned rule set evaluated over actions, resources, and context. **Responsibilities:** Produce enforceable decisions and obligations.
- **Required properties:** Authority/owner, applicability, rule semantics, decision outcomes, combination/precedence rules, version. **Optional properties:** Explanation templates, exception process, validity interval.
- **Relationships:** Governs every relevant concept; MAY require Guardrails, Approvals, or ResourcePolicy. **Lifecycle:** D; emergency revocation is an explicit governed change.
- **Invariants:** Enforcement MUST be possible outside probabilistic Actors. **Validation:** Unknown/failed mandatory policy evaluation MUST prevent the protected action; unresolved policy conflict MUST deny it.
- **Versioning:** Decisions pin evaluated versions and current revocation checks. **Security:** Subjects MUST NOT self-modify their governing Policy without authority. **Tenancy:** Applicable tenant and source/destination constraints combine. **Observability:** Record inputs by safe reference, decision, reasons, and obligations.

#### Guardrail

- **Purpose:** Check or constrain behavior at defined boundaries. **Definition:** A preventive, detective, or corrective control with declared coverage and failure behavior. **Responsibilities:** Assess input/output/action and produce a control result.
- **Required properties:** Version, control objective, placement, input/result contract, enforcement/failure behavior. **Optional properties:** Evaluator, thresholds, transformation/redaction behavior.
- **Relationships:** Policy determines required control and response to its result. **Lifecycle:** D.
- **Invariants:** Probabilistic detection MUST NOT replace authoritative permission enforcement. **Validation:** Mandatory guardrail failure/uncertainty MUST follow explicit fail-closed or approved bounded fallback policy.
- **Versioning:** Threshold/control changes require revision and evaluation. **Security:** Bypass MUST require explicit authority and be recorded. **Tenancy:** Control inputs/results remain scoped. **Observability:** Record control/version, verdict, and applied response.

#### Approval

- **Purpose:** Represent a required authorization decision gate. **Definition:** A governed request and attributable decision for a precisely scoped proposed action. **Responsibilities:** Bind approver eligibility, evidence, validity, and permitted use.
- **Required properties:** Requester, action/target/revision scope, governing policy, eligible approvers, decision rule, requested time, expiry rule, status. **Optional properties:** Risk assessment, evidence, usage count bound, separation of duties.
- **Relationships:** Required by policy before guarded work; HumanApproval specializes it. **Lifecycle:** §5.11.
- **Invariants:** Approval MUST NOT substitute for all other required authorization. **Validation:** Action identity, revisions, conditions, approver authority, and expiry MUST match at use.
- **Versioning:** A material action change requires new approval; decisions cannot be overwritten. **Security:** Forged, stale, replayed, or out-of-scope approvals MUST fail. **Tenancy:** Approver access and request disclosure require scope grants. **Observability:** Record decision and every authorized consumption.

#### HumanApproval

- **Purpose:** Support accountable human consent. **Definition:** An Approval whose required decision-makers are Humans. **Responsibilities:** Present adequate decision context and capture explicit human decisions.
- **Required properties:** Approval properties, human approver identities, decision attribution, presented scope/evidence revision. **Optional properties:** Human rationale, multi-person decision rule.
- **Relationships:** Humans approve or reject; Agent-generated recommendations MAY be evidence. **Lifecycle:** Approval lifecycle.
- **Invariants:** Silence, availability, generated text, or timeout MUST NOT count as human approval. **Validation:** Required human identities and decision rule MUST be verified.
- **Versioning:** Changed presented scope invalidates prior applicability. **Security:** Delegated machine approval MUST NOT masquerade as HumanApproval. **Tenancy:** Human participation uses authorized tenant Principals. **Observability:** Preserve decision evidence with personal-data minimization.

#### Identity

- **Purpose:** Identify a subject distinctly. **Definition:** An identifier and governed claims about a subject, with issuer/source attribution. **Responsibilities:** Support identity verification without implying permissions.
- **Required properties:** Subject identifier, issuer/authority, subject kind, claim validity/status. **Optional properties:** Verified claims, external mappings.
- **Relationships:** Principals reference verified Identities; Actors MAY have multiple identities. **Lifecycle:** established → valid → expired or revoked; refreshed claims create a new revision.
- **Invariants:** Identity and credentials MUST be distinguishable. **Validation:** Issuer, validity, and proof requirements MUST be checked at authentication boundaries.
- **Versioning:** Claim changes are revisioned. **Security:** Unverified claims MUST NOT establish authority. **Tenancy:** Global person identity does not imply global tenant access. **Observability:** Record verification outcomes without recording credentials.

#### Principal

- **Purpose:** Identify the subject of authorization. **Definition:** A verified acting security subject in a stated scope. **Responsibilities:** Anchor grants, accountability, and delegation chains.
- **Required properties:** Identity reference, principal kind, scope, authorization status. **Optional properties:** Actor association, group/Role eligibility, originating Principal for acting-on-behalf-of.
- **Relationships:** Holds eligible Permission grants and acts for Actors/Applications. **Lifecycle:** established → active ↔ suspended → revoked; active MAY revoke directly.
- **Invariants:** A caller MUST NOT select an arbitrary Principal merely by supplying its identifier. **Validation:** Authentication and acting-on-behalf-of chain MUST be valid.
- **Versioning:** Grants/status are revisioned independently of stable identity. **Security:** Revocation applies to subsequent governed actions. **Tenancy:** Scope limits every action. **Observability:** Record acting and originating Principals where applicable.

#### Permission

- **Purpose:** Define authorized action scope. **Definition:** A grant or denial concerning a Principal's action on resources under conditions. **Responsibilities:** Bound eligible authority and its validity.
- **Required properties:** Issuing authority, subject/eligibility rule, actions, resource scope, effect (grant/deny), conditions, validity, delegation allowance. **Optional properties:** Purpose restrictions, use bounds, parent grant.
- **Relationships:** Evaluated with Policy and RoleAssignment eligibility. **Lifecycle:** issued → active → expired or revoked; issued MAY be withdrawn before activation.
- **Invariants:** Grants MUST derive from authorized issuers; unresolved applicable denial MUST prevent action. **Validation:** Scope, conditions, issuer authority, and delegation attenuation MUST hold.
- **Versioning:** Scope amendments issue a new grant/revision with explicit invalidation semantics. **Security:** No default grant on missing information. **Tenancy:** Grants MUST identify allowed tenant/resource scope. **Observability:** Record issuance, evaluation, use where required, and revocation.

#### TrustBoundary

- **Purpose:** Make changes in trust and authority explicit. **Definition:** A governed crossing between domains with different trust assumptions or control obligations. **Responsibilities:** Specify admission, disclosure, and action controls.
- **Required properties:** Source/destination trust domains, crossing types, required controls, failure behavior. **Optional properties:** Risk classification, transformation rules, isolation requirements.
- **Relationships:** Crossed by actions, Messages, Events, data, and Plugin interactions. **Lifecycle:** D.
- **Invariants:** Shared process/location MUST NOT imply equal trust. **Validation:** Required identity, authorization, policy, validation, resource, and approval controls MUST complete before protected effects.
- **Versioning:** Boundary-rule changes are governance changes. **Security:** Enforcement cannot rely solely on untrusted Actors. **Tenancy:** Tenant crossing is always a governed trust concern. **Observability:** Record admissions/denials and safe causal evidence.

#### Secret

- **Purpose:** Govern sensitive authentication or confidential material. **Definition:** Protected material accessed through a controlled reference and usage policy. **Responsibilities:** Support authorized use, rotation, and revocation without unnecessary disclosure.
- **Required properties:** Secret reference, owner/tenant, purpose, access policy, validity/status, material revision identifier. **Optional properties:** Rotation policy, expiry, consumer restrictions.
- **Relationships:** Used by authorized Providers/Tools/Principals; Context carries references where possible. **Lifecycle:** provisioned → active → rotated, expired, or revoked; rotation activates a new material revision.
- **Invariants:** Raw values MUST NOT be required in manifests, provenance, or telemetry. **Validation:** Use MUST check current validity and authorized purpose.
- **Versioning:** Rotation MUST preserve attribution without retaining exposed obsolete values. **Security:** Least disclosure and revocation MUST be enforceable. **Tenancy:** Cross-tenant sharing MUST be explicitly permitted. **Observability:** Audit access/rotation using references only.

#### TenantContext

- **Purpose:** Propagate verified isolation scope. **Definition:** A bound declaration of the effective Tenant and applicable scope evidence. **Responsibilities:** Preserve tenant identity and crossing constraints.
- **Required properties:** Tenant identity, verified source/binding evidence, applicable isolation/policy references. **Optional properties:** Authorized cross-scope grant references, originating tenant for imported data.
- **Relationships:** Required by ExecutionContext and propagated to child work. **Lifecycle:** V.
- **Invariants:** Caller-supplied tenant text MUST NOT override verified context. **Validation:** Tenant status, Principal scope, and resource scope MUST agree.
- **Versioning:** Bound tenant identity is immutable; live policy restrictions remain enforceable. **Security:** Missing or ambiguous scope fails closed. **Tenancy:** Explicit single-tenant context is valid. **Observability:** Tenant attribution MUST be retained without cross-tenant leakage.

### 4.10 Resource governance

#### Budget

- **Purpose:** Bound cumulative resource consumption. **Definition:** An allocation of finite resource quantities to accountable work or scope. **Responsibilities:** Track reservations, consumption, releases, and remaining allocation.
- **Required properties:** Owner/scope, resource dimensions and units, allocation, accounting interval/lifetime, consumed/reserved amounts, exhaustion behavior. **Optional properties:** Parent Budget, alerts, approved overdraft policy, estimates.
- **Relationships:** Propagates through Delegations and Executions. **Lifecycle:** allocated → active → exhausted or closed; exhausted MAY return to active only by authorized replenishment; active MAY close directly.
- **Invariants:** Child allocations/reservations MUST NOT permit aggregate spending beyond effective parent bounds. **Validation:** §8.2 accounting rules MUST hold across concurrent work.
- **Versioning:** Allocation amendments are revisioned; consumption history is not reset by retry. **Security:** Only authorized authorities may replenish. **Tenancy:** Usage belongs to the effective tenant and payer scope. **Observability:** Record units, estimates, reservations, actuals, and uncertainty.

#### Quota

- **Purpose:** Bound usage over a recurring or shared allowance scope. **Definition:** A resource allowance with an explicit measurement window or replenishment rule. **Responsibilities:** Track admissible consumption and resets.
- **Required properties:** Subject/scope, resource/unit, allowance, window/replenishment semantics, enforcement behavior. **Optional properties:** Burst allowance, allocation subscopes.
- **Relationships:** ResourcePolicy applies it with Budgets and Limits. **Lifecycle:** D for rule; each measurement window has explicit opening, consumption, and closing records.
- **Invariants:** Reset boundaries MUST be defined; retries MUST NOT reset a quota window. **Validation:** Admission MUST account for concurrent usage.
- **Versioning:** Rule revisions cannot erase consumed usage. **Security:** Subject changes MUST NOT evade quotas. **Tenancy:** Tenant and shared-provider quotas MAY both apply. **Observability:** Record window, usage, refusals, and replenishment.

#### Limit

- **Purpose:** Enforce a boundary on an operation or state. **Definition:** A maximum/minimum predicate such as concurrency, payload size, duration, or per-action consumption. **Responsibilities:** Define measurable admissibility.
- **Required properties:** Subject, metric/unit, boundary, measurement semantics, enforcement response. **Optional properties:** Warning threshold, validity interval.
- **Relationships:** Used by ResourcePolicy and CapabilityConstraints. **Lifecycle:** V within its governing versioned policy.
- **Invariants:** A Limit is not a consumable Budget or replenishing Quota. **Validation:** Unknown measurements MUST follow declared conservative admission behavior.
- **Versioning:** Changed thresholds create policy revisions. **Security:** A consumer cannot self-relax a Limit. **Tenancy:** All applicable scoped limits compose. **Observability:** Record breaches and enforcement responses.

#### ResourcePolicy

- **Purpose:** Define controlled resource behavior. **Definition:** Policy specializing admission, accounting, and exhaustion for resource use. **Responsibilities:** Combine Budgets, Quotas, Limits, priorities, and uncertainty rules.
- **Required properties:** Policy properties, resources/units, accounting and composition rules, admission/exhaustion behavior. **Optional properties:** Reservation strategy semantics, estimation tolerance, authorized fallback.
- **Relationships:** Governs all consuming Executions and Delegations. **Lifecycle:** D.
- **Invariants:** Exhaustion MUST cause controlled refusal, waiting, stopping, or authorized degradation; not silent overrun. **Validation:** Dimensional units and compatible accounting scopes MUST be checked.
- **Versioning:** Changes preserve already committed accounting obligations. **Security:** Probabilistic estimates cannot self-authorize excess. **Tenancy:** Attribution cannot move to another tenant to evade restrictions. **Observability:** Record decisions and cost/usage reconciliation.

### 4.11 Quality and operations

#### Evaluator

- **Purpose:** Assess behavior or work against criteria. **Definition:** A versioned assessment contract and realization, deterministic, human, probabilistic, or composed. **Responsibilities:** Define methodology, inputs, result meaning, and limitations.
- **Required properties:** Criteria/version, input contract, method/version, result scale and interpretation, uncertainty/failure semantics. **Optional properties:** Calibration evidence, independence requirements, resource needs.
- **Relationships:** Performs Evaluations of Models, Skills, Tools, Agents, Teams, Workflows, Adapters, or products. **Lifecycle:** D.
- **Invariants:** Evaluation MUST be independently consumable. **Validation:** Method applicability and required evaluator independence MUST be checked.
- **Versioning:** Criteria/method changes require new revisions. **Security:** Evaluators do not automatically authorize release. **Tenancy:** Evaluation input/output disclosure is governed. **Observability:** Record evaluator version and assessment conditions.

#### Evaluation

- **Purpose:** Represent an assessment attempt. **Definition:** A governed application of an Evaluator to pinned subjects and criteria. **Responsibilities:** Preserve test conditions, inputs, and result attribution.
- **Required properties:** Evaluator version, subject revisions, criteria, input/case references, execution attribution, status. **Optional properties:** Baseline, sampling conditions, environment characteristics relevant to validity.
- **Relationships:** Produces EvaluationResults; runs as governed work. **Lifecycle:** requested → running → completed, failed, or cancelled; requested MAY be cancelled.
- **Invariants:** Assessment execution failure MUST NOT be recorded as a passing subject result. **Validation:** Subject, criteria, method, and evidence MUST be compatible.
- **Versioning:** Re-evaluation creates a new attempt. **Security:** Adversarial inputs remain governed data. **Tenancy:** Test data and results retain scope. **Observability:** Record execution failure separately from subject quality.

#### EvaluationResult

- **Purpose:** Preserve interpretable assessment evidence. **Definition:** An immutable result from an Evaluation. **Responsibilities:** State measured judgment, uncertainty, and limitations.
- **Required properties:** Evaluation, subject/criteria revisions, judgment or measurements with scale/units, evidence, assessor attribution, time. **Optional properties:** Confidence, limitations, explanatory findings, ArtifactVersion reference.
- **Relationships:** Supports Outcome acceptance, release policy, or regression comparison. **Lifecycle:** R.
- **Invariants:** Inconclusive MUST remain distinct from pass/fail. **Validation:** Metrics MUST have defined meaning; comparisons MUST account for changed methods/conditions.
- **Versioning:** Corrections create linked results. **Security:** Result validity and release authority are separate. **Tenancy:** Reports MUST not disclose protected subjects. **Observability:** Preserve method and evidence provenance.

#### Trace

- **Purpose:** Explain operational causality. **Definition:** A correlated set of execution activities and observations. **Responsibilities:** Link attempts, transitions, decisions, resource usage, and failures.
- **Required properties:** Trace identity, tenant scope, root attribution, activity identities, causal relationships, timing/status semantics. **Optional properties:** Metrics, remote correlation links, safe diagnostic details.
- **Relationships:** ExecutionContext references it; Provenance MAY link to its activities. **Lifecycle:** opened → collecting → closed → retained → disposed; late observations are appended with explicit recording times.
- **Invariants:** Trace coverage MUST NOT depend on Agents being present. **Validation:** Causal references and time uncertainty MUST not imply unsupported total order.
- **Versioning:** Observations are immutable; format revisions preserve meaning. **Security:** Sensitive content MUST be minimized and access-controlled. **Tenancy:** Cross-tenant correlation MUST not expose protected activity. **Observability:** Missing/dropped observations MUST be disclosed where they affect audit completeness.

#### Provenance

- **Purpose:** Explain what produced a result and under what conditions. **Definition:** An attributable lineage record linking subjects, inputs, transformations, versions, and governance decisions. **Responsibilities:** Preserve origin and known reproducibility limits.
- **Required properties:** Subject, producer/source, input references, transformation/execution attribution, relevant versions, governance decision references, time. Explicit unknown/external origin MUST be distinguished from verified origin.
- **Optional properties:** Model, prompt, Skill, Tool, retrieved sources, evaluations, Trace, integrity evidence, reproduction conditions.
- **Relationships:** Applies to Artifacts, Outcomes, resolutions, and other derived records. **Lifecycle:** R.
- **Invariants:** MUST NOT require private model reasoning or promise exact replay of probabilistic/external behavior. **Validation:** Lineage claims MUST distinguish observed, asserted, and unavailable evidence.
- **Versioning:** Corrections retain original claims. **Security:** Provenance authenticity and evidence access MUST be governed. **Tenancy:** Source scope remains visible to authorized lineage consumers. **Observability:** Links production evidence beyond transient runtime telemetry.

### 4.12 Extensibility

#### Port

- **Purpose:** Preserve a replaceable contract boundary. **Definition:** A technology-neutral interaction contract for a capability family or infrastructure dependency. **Responsibilities:** Define behavior, lifecycle, errors, security, state, and observability obligations.
- **Required properties:** Identity/version, semantic input/output contracts, behavioral obligations, error/lifecycle semantics, governance hooks. **Optional properties:** Optional features, conformance profile references.
- **Relationships:** Adapters implement Ports; domain logic depends on them. **Lifecycle:** D.
- **Invariants:** Stable abstractions MUST NOT depend on concrete Adapters. **Validation:** Conformance MUST assess behavior, not merely structural compatibility.
- **Versioning:** Breaking behavior changes require a new compatible boundary/version. **Security:** Enforcement obligations MUST survive adapter replacement. **Tenancy:** Isolation semantics are part of the contract. **Observability:** Consistent attribution MUST cross the boundary.

#### Adapter

- **Purpose:** Connect a realization to a Port. **Definition:** A replaceable mapping between canonical semantics and implementation behavior. **Responsibilities:** Preserve meaning, translate errors, disclose limitations/extensions.
- **Required properties:** Identity/version, owning Plugin, implemented Port versions, capability offers, configuration contract, known limitations. **Optional properties:** Conformance evidence, migration support.
- **Relationships:** Bridges Provider realizations to Ports. **Lifecycle:** D for definition; operational activation follows owning Plugin lifecycle.
- **Invariants:** MUST NOT silently weaken guarantees or redefine domain concepts. **Validation:** Required port behavior and policy hooks MUST be demonstrated.
- **Versioning:** Port compatibility and adapter release versions are separate. **Security:** Boundary enforcement MUST not be bypassed by mapping. **Tenancy:** Translation MUST preserve scope and data restrictions. **Observability:** Preserve canonical error/trace/provenance links.

#### Plugin

- **Purpose:** Package discoverable extension contributions. **Definition:** A governed, versioned unit declaring provided and required capabilities and lifecycle behavior. **Responsibilities:** Describe contributions, compatibility, configuration, health, permissions, and trust needs.
- **Required properties:** Identity/version/type, provided and required Capabilities, configuration contract, compatibility ranges, lifecycle contract, health semantics, permissions/trust requirements, dependencies, metadata. Collections MAY be empty when appropriate.
- **Optional properties:** Adapters, resource needs, migration/deprecation guidance, conformance evidence, integrity/publisher evidence.
- **Relationships:** Owns provider/adapter contributions; discoverable without modifying core where supported. **Lifecycle:** §5.12.
- **Invariants:** Discovery/install MUST NOT imply trust or activation. **Validation:** Dependency closure, compatibility, configuration, trust, and required permissions MUST be checked before activation.
- **Versioning:** Plugin release is distinct from provided Capability versions and specification compatibility. **Security:** Contributions MUST stay within admitted authority; no self-granting. **Tenancy:** Shared code MUST have separately scoped uses. **Observability:** Record discovery, validation, activation, health, failure, and retirement.

## 5. Explicit lifecycle semantics

### 5.1 Rules for every transition

**L-01.** A transition MUST name its subject, expected prior revision/state, initiating Principal or attributable system cause, preconditions, and resulting state. It MUST be authorized and recorded. Unlisted transitions MUST be rejected; terminal work MUST NOT be silently reopened. Corrections, retries, replacement versions, and migrations are explicit linked operations.

**L-02.** Cancellation/revocation expresses intent to stop; it does not prove external effects stopped. Completion and cancellation races MUST have one authoritative local state decision and a record of any late or uncertain effects. A terminal failure/cancellation MUST NOT erase usable Artifacts, consumption, or audit history.

**L-03.** Waiting, pausing, and suspension MUST identify reason and resumption conditions. Deadlines and budget windows continue unless the governing contract explicitly defines otherwise. Resume MUST revalidate current authority, policies, dependencies, approvals, and remaining resources.

**L-04.** Definition lifecycle and operational state MUST be separate. An active definition can have many concurrent operational instances in different states. Health (healthy, degraded, unhealthy, or unknown) is an observation with freshness, not successful lifecycle completion.

### 5.2 Application

Definition: draft → validated → active → deprecated → retired, with D's additional transitions. Operational use: inactive → activating → running ↔ suspended → stopping → stopped. Running MAY enter stopping directly. Activating MAY fail or be cancelled into stopped with a reason. Stopped MAY reactivate as a new activation record after validation. Activation MUST resolve mandatory capabilities and validate governance before work admission. Stopping MUST define drain/cancel treatment for existing work; stopped means no admitted work remains active under that activation.

### 5.3 Team

Definition uses D. Operational composition: forming → ready → active ↔ suspended → disbanding → disbanded. Ready MAY enter disbanding; active MAY enter disbanding directly. Ready requires composition and staffing validation. Disbanding MUST settle, transfer, or explicitly preserve responsibility for outstanding Tasks and Outcomes before disbanded. Resuming after membership change MUST validate the new composition revision.

### 5.4 Agent

Definition uses D. Operational instance: created → initializing → ready → active ↔ waiting; active or waiting MAY return to ready once all current work is settled. Active or waiting MAY enter suspended; suspended → ready after revalidation. Ready, active, waiting, or suspended MAY enter stopping → stopped. Initializing MAY enter failed; ready, active, waiting, suspended, or stopping MAY enter failed on unrecoverable failure. Failed/stopped instances are terminal; restarting creates a linked new instance and MUST NOT restore revoked grants. Multiple governed Executions MAY be served only if declared concurrency limits allow it; active/waiting status MUST describe aggregate instance activity without replacing per-Execution state.

### 5.5 Goal

proposed → accepted → active ↔ paused → achieved, failed, or abandoned. Active MAY enter a terminal state directly. Proposed MAY be rejected or abandoned; accepted MAY be abandoned. Achievement requires evidence against the applicable success criteria and authorized assessment. A changed objective requires a new revision and explicit disposition of existing Plans/Tasks. Completed Tasks alone do not prove achievement.

### 5.6 Plan

draft → validated → approved → active → completed, superseded, or abandoned. Validated MAY return to draft; draft/validated/approved MAY be abandoned; approved MAY be superseded. Approval means admitted by the applicable decision rule, which need not require human approval. Active content MUST NOT be edited in place. Supersession MUST specify continuing, cancelled, and replaced Tasks and handle already committed effects. Completed means plan obligations are assessed as complete; Goal achievement is separate.

### 5.7 Task

proposed → ready → assigned → running ↔ blocked → succeeded or failed. Running MAY succeed/fail directly. Ready MAY enter running for authorized direct assignment. Proposed, ready, assigned, running, or blocked MAY enter cancelling → cancelled. Assigned MAY return to ready after explicit release if no attempt is active. A failed attempt MAY lead the still-running Task to a new attempt under its retry policy; once the Task itself is failed, subsequent work requires a linked replacement Task. Success requires the Task's result/acceptance criteria, not simply an Execution exit status.

### 5.8 Execution

created → admitted → running ↔ waiting. Running or waiting MAY enter suspended; suspended → admitted after revalidation. Created MAY be rejected or cancelled; admitted MAY be cancelled or fail admission revalidation into rejected. Running MAY succeed or fail. Running, waiting, or suspended MAY enter cancelling → cancelled. Waiting/suspended MAY fail on deadline or unrecoverable conditions; cancelling MAY fail if cancellation cannot be completed, with effect uncertainty recorded. Terminal states are succeeded, failed, cancelled, rejected. Rejected means work did not begin; failed/cancelled MAY have effects. Every retry is a new linked attempt with independent status and shared applicable accounting.

### 5.9 Workflow

Definition uses D. Operational progress is represented by WorkflowState inside Execution: advancing and waiting map to running/waiting; suspension belongs to Execution. Terminal workflow positions MUST map to a declared success, failure, or cancellation result. Parallel branches MUST define join success/failure conditions and disposition of unfinished branches. Loops MUST have termination or bounded-governance conditions; a loop cannot bypass deadlines or budgets. Checkpoint/durable resumption is required only when that capability is declared, and then MUST satisfy §6.3.

### 5.10 Artifact

draft → available → superseded or archived → disposed. Available MAY go directly to archived or disposed under policy; superseded MAY enter archived/disposed. Draft MAY be disposed. Archived MAY return to available only if content remains accessible and policy permits. Superseded does not invalidate references to earlier versions. Release, approval, and withdrawal are version-specific records distinct from content identity. Disposition MUST obey retention, holds, and reference policy; retained tombstones MUST describe content unavailability without retaining prohibited data.

### 5.11 Approval

requested → pending → approved, rejected, expired, or cancelled. Requested MAY be cancelled or expired. Approved MAY become expired, revoked, or consumed. Consumption means all permitted uses are exhausted; use records MUST prevent replay beyond the declared scope/count. Approved actions MUST satisfy current policy at use time. A changed proposal requires a new request; rejected/expired/cancelled/revoked/consumed decisions are terminal. Multi-approver rules MUST specify quorum, rejection precedence, eligibility, and expiry without inferring consent from absent responses.

### 5.12 Plugin

discovered → validated → initialized → active ↔ degraded → stopping → stopped → retired. Active MAY enter stopping directly. Validated/initialized MAY enter stopped by explicit cancellation; discovered/validated MAY retire if unused. Initialization failure enters failed; initialized/active/degraded/stopping MAY enter failed. Failed MAY enter stopping for cleanup; stopped MAY enter initialized only through a new validated activation record. Validation includes dependency closure, configuration, compatibility, permissions, and trust admission. No contributions are eligible for new selection before activation. Degraded contributions are eligible only when they still meet requirements. Stopping MUST prevent new work and define existing-work disposition. Retirement MUST not destroy needed historical interpretation.

## 6. Execution context and behavioral requirements

### 6.1 Immutable envelope and mutable state

**E-01.** Execution identity, tenant, Application revision, originating Principal, causal parent, and initially bound work/definition revisions MUST remain immutable during an attempt. Optional Organization/Team/Role/Goal/Task references MUST be consistent when present; absence MUST NOT be replaced with fabricated organizational identities.

**E-02.** State positions, progress, resource balances, dependency health, pending approvals, and observed results are mutable execution state with explicit revisions. They MUST NOT be hidden in conversational history or encoded by changing immutable identity fields. Non-secret configuration is a pinned revision; Secret references are resolved against current authorization and validity.

**E-03.** Historical authorization/policy references describe admission conditions, not perpetual grants. Before every protected effect, effective authority MUST intersect the admitted authority ceiling with current grants, current restrictive policies, delegation scope, approval validity, and resource/deadline constraints. Later grants MUST NOT silently expand an admitted attempt. An expansion requires an explicit authorized amendment recording affected actions and renewed approvals, or a new attempt. Immutable identity/tenant/work bindings cannot be amended in place.

**E-04.** Child contexts MUST preserve tenant, originating causation, and inherited restrictions, and identify their own Execution and acting Principal. Context minimization SHOULD provide only information needed for delegated work. Correlation identifiers link observations; they MUST NOT be used as credentials.

### 6.2 Admission, effects, and completion

**E-05.** Before admission, the implementation MUST validate work/input contracts, bound versions, effective scope, capability resolution if needed, governance, and resource/deadline feasibility. A required approval MAY place admitted work in waiting, but the guarded effect MUST NOT occur before valid approval.

**E-06.** Each consequential effect MUST have attributable intent, current authorization, applicable validation/guardrail decisions, resource admission, and a result identifying whether the effect occurred, did not occur, or is unknown. A timeout or lost acknowledgment MUST NOT be interpreted as proof of no effect.

**E-07.** Completion MUST preserve operational result, produced ArtifactVersion references, errors, resource accounting, and unresolved effect status. Important produced work SHOULD be Artifacts, including relevant test and evaluation results. Omitting an important Artifact SHOULD have a recorded reason. Operational output MAY remain transient when policy and work expectations permit.

**E-08.** Synchronous and asynchronous work have the same authority and result semantics. Event receipt, command acceptance, execution completion, Task acceptance, and Goal achievement MUST remain distinct. No global ordering, universal delivery guarantee, or exact replay guarantee is implied by canonical entities.

### 6.3 Durability, retry, and recovery

**E-09.** A declared durable/checkpoint capability MUST preserve enough explicit state and effect history to resume at its documented boundary after interruption. It MUST state recoverability guarantees and limitations. Recovery MUST NOT double-count, reset, or lose committed resource consumption.

**E-10.** Retry policy MUST define eligible error categories, attempt/deadline/resource bounds, and treatment of possible prior effects. Safe deduplication requires a stable effect identity scoped to work and tenant, with a declared validity interval and equivalence rule. This specification requires the semantics, not a particular coordination mechanism.

**E-11.** Unknown-effect operations MUST be reconciled, safely deduplicated under a declared contract, or held for an authorized decision before potentially duplicating harmful effects. Compensation is a new authorized action with its own costs and failure modes; it MUST NOT be described as erasing history or guaranteed rollback.

## 7. Capability resolution semantics

### 7.1 Identity and versions

**C-01.** Capability identity is a namespace plus a local name. Namespace ownership MUST be explicit, stable, and protected against collisions or impersonation. Exact textual encoding and registry representation belong to later contracts. Renaming MUST use an explicit alias/migration declaration and MUST NOT silently merge different capabilities.

**C-02.** A requirement MUST identify an acceptable CapabilityVersion range. Unbounded ranges MUST be deliberate and MUST NOT imply compatibility across breaking major versions. Providers advertise exact offered versions and qualifications. Provider release versions and Capability versions MUST remain separate.

### 7.2 Resolution procedure and outcomes

A resolver MUST perform these semantic steps; their physical execution order MAY vary if externally observable correctness is preserved:

1. **Validate inputs:** Check requirement identity, ranges, multiplicity, constraints, extension semantics, and applicable tenant/security/resource policies. Contradictory mandatory requirements yield conflict diagnostics.
2. **Establish an input snapshot:** Identify the requirement revisions, available candidate offers, evidence freshness, configuration, current policy inputs, resolver version, and selection rules. Discovery MUST not leak inaccessible providers or tenants.
3. **Match candidates:** Match exact semantic identity/compatible version, then apply every hard constraint, trust requirement, data restriction, health condition, and dependency requirement. Missing or unknown evidence for a hard constraint is not satisfaction.
4. **Resolve dependencies recursively:** Expand provider and composite requirements to a complete compatible closure. Track dependency identity and binding context. Repeated requirements MAY share a provider only when version, state isolation, multiplicity, and resource semantics permit. Unresolved recursive dependency cycles MUST fail with cycle evidence; silently truncating expansion is forbidden.
5. **Check composition conflicts:** Reject incompatible version obligations, mutually exclusive providers, unsatisfied aggregate guarantees, scope violations, or resource constraints. Different versions MAY coexist only if their contracts and consumer isolation rules allow it.
6. **Rank eligible solutions:** Apply declared preferences only after hard constraints. Deterministic selection, when required by consumer or policy, MUST use stable ordering/tie-break semantics over the recorded input snapshot. It MUST produce the same binding decision for the same complete inputs; it does not promise deterministic execution output.
7. **Handle ambiguity:** If multiple eligible solutions remain and no authorized selection rule chooses one, return unresolved ambiguity. Interactive selection MAY be requested by the surrounding workflow; arbitrary hidden choice is forbidden. A declared non-deterministic selection mode MAY be used only when permitted and MUST record the realized choice and relevant selection evidence.
8. **Record the result:** Return resolved, unsatisfied, conflict, ambiguous, or invalid status with reasons, chosen offers/versions, dependency closure, omissions, rule versions, and provenance. Non-success MUST NOT be represented as an executable complete binding.

**C-03.** Optional requirements MAY be omitted with explicit reasons and resulting degradation. Once selected, an optional requirement and its dependencies MUST meet their hard constraints. If a mandatory composite depends on a component to uphold its guarantee, that dependency cannot be made optional merely to make resolution succeed.

**C-04.** Resolution MUST NOT silently fall back to a weaker capability, broader data disclosure, higher budget, incompatible version, or more privileged provider. A fallback MUST have declared acceptable behavior and remain within all effective constraints.

**C-05.** Binding reuse MUST consider expiry, health changes, policy changes, revocations, and evidence freshness. Invalid bindings MUST trigger controlled failure, waiting, or explicit re-resolution. An existing historical resolution record MUST remain unchanged. Replacement MUST record changed provenance and compatibility; in-flight state migration cannot be assumed.

### 7.3 Provider extensions

**C-06.** Extensions MUST have an explicit namespace, owner, version, documented semantics, compatibility requirements, and portability impact. Applications MUST explicitly opt into required extension behavior. Unsupported required extensions MUST fail. Optional unknown extensions MAY be ignored only when the declaration explicitly permits omission without weakening the required contract. Extensions MUST NOT bypass canonical security, tenancy, resource, error, or provenance obligations.

## 8. Delegation and resource propagation

### 8.1 Bounded authority

**D-01.** A Delegation MUST identify the delegator's acting Principal, delegate and recipient Principal/acceptance authority, work revision, relevant Context, required/allowed Capabilities, allowed actions/resources, constraints, inherited policies, resource bounds, deadline, expected products/results, approval gates, and completion reporting. A Team recipient MUST route responsibility through explicit RoleAssignments and attributable Actors.

**D-02.** Effective delegated authority MUST be no greater than the intersection of the delegator's delegable authority, the delegation grant, the delegate's eligible authority, and all applicable policies. Delegation does not transfer the delegator's credentials. Further delegation MUST be explicitly permitted and MUST retain the chain and all non-waivable restrictions.

**D-03.** A delegate MAY receive additional authority only through a separate explicit grant from an authority entitled to issue it. That grant MUST identify scope, justification, validity, and approval evidence. The existence of a delegation MUST NOT manufacture or imply such a grant.

**D-04.** Revocation/cancellation MUST prevent new protected actions under the revoked delegation. In-flight effects MUST be reported and reconciled under the declared cancellation contract. Revocation does not delete already produced artifacts or retroactively remove accounting.

**D-05.** Delegate completion MUST report evidence against the expected result contract, produced ArtifactVersions, resource use, failures, and residual effects. The delegator's or other designated acceptance authority's acceptance is a separate decision; a delegate cannot assert global Goal achievement merely by reporting completion.

### 8.2 Resource accounting

**B-01.** Resource dimensions MUST carry explicit units and accounting scope. Quantities in different dimensions or currencies MUST NOT be combined without an explicit conversion rule, rate/version, and uncertainty policy. Budgets, Quotas, and Limits MAY apply simultaneously; the most restrictive applicable admissibility conditions MUST all be met.

**B-02.** Delegated budgets MUST identify their parent allocations and whether funds are reserved exclusively, shared with coordinated accounting, or transferred under an authorized rule. Concurrent children MUST NOT each treat the same remaining allocation as independently spendable. Committed consumption plus outstanding enforceable reservations MUST stay within the effective allocation unless an explicit authorized overdraft policy defines the permitted bound.

**B-03.** Admission MUST use known upper bounds or an explicitly permitted uncertainty/overrun policy for costs not known in advance. If a hard bound cannot be assured, the operation MUST not be represented as guaranteed to fit it. Reconciliation MUST record actual usage and release unused reservations without erasing incurred cost. Unknown charges MUST remain outstanding until reconciled or explicitly settled by an authorized accounting decision.

**B-04.** Child deadlines MUST be no later than applicable parent deadlines unless an authorized governing change explicitly extends the parent constraint. Waiting/retrying/redelegating MUST NOT reset consumed budget, quota usage, or elapsed deadlines. Exhaustion MUST yield controlled refusal, waiting for authorized replenishment, stopping, or pre-authorized degradation.

## 9. Artifact, policy, and information integrity

**A-01.** Every ArtifactVersion MUST identify stable content meaning and its producer, owner, tenant, policy, visibility, retention, and provenance. Content may be a document, dataset, media asset, structured result, or any other work product; it need not be a file. Representation-specific locations MUST be replaceable without changing artifact identity or content meaning.

**A-02.** Mutable aliases such as a current-version designation MAY exist, but executions, evaluations, approvals, and derivation records MUST pin exact versions where results depend on content. An approved version MUST NOT silently become approval of a later version.

**A-03.** Visibility changes, corrections, supersession, publication, and disposition MUST be authorized, revisioned decisions. Retention and deletion obligations MUST be evaluated together. An unresolved conflict MUST block destructive disposition and be escalated to the accountable policy authority; this rule MUST NOT be treated as permission for indefinite retention contrary to governing obligations.

**A-04.** Untrusted Messages, retrieved Knowledge, Memory, Artifact content, Model outputs, or Skill instructions MUST NOT become Policy, Permission, or configuration merely because an Actor reads them. Promotion into a governing definition requires explicit validation and authorized publication with provenance.

**A-05.** Policy combination MUST be explicit. A lower-scope rule cannot weaken an inherited non-waivable restriction. A policy exception MUST identify its granting authority, scope, validity, and constraints. An unresolved conflict, unavailable mandatory policy decision, or missing required approval MUST prevent the protected action.

## 10. Canonical error model

An error is a semantic failure report, not a programming-language exception. Each error MUST identify category, affected operation/subject, execution/correlation where applicable, safe explanation, source attribution, effect status (none, partial, completed, unknown), and recoverability assessment (terminal, potentially retryable, requires intervention, or unknown). Optional properties are safe cause references, violated constraints, retry conditions, and remediation guidance. S-01 through S-12 and R apply to independently recorded errors; embedded errors inherit their owning record. Corrections MUST preserve the original report.

| Category | Meaning and required handling distinction |
|---|---|
| ValidationError | Malformed or semantically invalid declaration/input/state transition; repair before retry. |
| CapabilityUnavailable | A required ability has no currently usable realization, including a formerly valid provider becoming unavailable. |
| CapabilityResolutionError | Resolution cannot produce an admissible complete binding; MUST carry unsatisfied/conflict/ambiguity/invalid detail. |
| AuthorizationDenied | Principal lacks effective authority; retry MUST NOT bypass the denied scope. |
| PolicyViolation | An applicable governing rule prohibits the proposed/observed behavior or a mandatory policy obligation cannot be met. |
| BudgetExceeded | Admission or observed consumption exceeds an effective resource bound; MUST identify whether Budget, Quota, or Limit, its unit/scope, and known overrun. |
| DeadlineExceeded | An applicable deadline elapsed; effect completion may still be unknown and MUST be reported separately. |
| DependencyFailure | Required subordinate work or provider failed; preserve safe causal references. |
| ExecutionFailure | Work attempt failed for a reason not more precisely categorized, or as an aggregate with explicit causes. |
| ToolFailure | A Tool invocation failed or its effect could not be confirmed; effect status is mandatory. |
| ModelFailure | Model invocation/output failed its declared contract; low task quality MAY instead be an EvaluationResult if the invocation contract succeeded. |
| HumanRejected | A required human decision explicitly rejected the request; silence/timeout is not rejection and MUST be represented by expiry/wait/deadline semantics. |
| Conflict | Incompatible concurrent revisions, claims, constraints, or commitments prevent a valid decision. |
| VersionMismatch | Required versions, state, or contract interpretations are incompatible. |
| TenantViolation | Scope is missing, contradictory, or an isolation/cross-tenant rule is violated; disclosure/effects MUST stop. |
| PluginFailure | Plugin initialization, lifecycle, contribution, or health behavior cannot meet its declared contract. |

**ERR-01.** Adapters MUST preserve the most specific known semantic category and safe causal chain. Multiple causes MAY be retained; a primary category MUST NOT conceal tenant, authorization, policy, or resource violations. Diagnostic detail MUST not reveal inaccessible resources or Secrets.

**ERR-02.** Category alone MUST NOT imply safe retry. Retry requires current authority, resource/deadline availability, and effect-safe semantics (§6.3). Cancellation, rejection, timeout, policy denial, and a completed but low-quality result MUST remain distinguishable.

## 11. Versioning and compatibility

**V-01.** Specification, schema, capability, plugin, adapter, behavioral definition, and artifact versions are distinct dimensions. A release identifier in one dimension MUST NOT imply compatibility in another. Each operational use MUST state the versions necessary to interpret its behavior and retained data.

**V-02.** Specification and published contract versions use semantic major/minor/patch meaning: major for incompatible semantic change; minor for compatible additions; patch for corrections that do not alter valid observable obligations. Numeric version syntax and canonical serialization are deferred to contracts. Initial 0.x revisions MUST NOT be presumed mutually compatible; compatibility MUST be declared explicitly.

**V-03.** A breaking change includes removing/renaming required concepts or properties without compatible mapping, adding mandatory inputs without an equivalent default, narrowing valid inputs, broadening outputs beyond the existing consumer contract, weakening guarantees, changing lifecycle/error meanings, or altering security/tenant/resource semantics incompatibly. Labeling a change a correction does not make it non-breaking.

**V-04.** Schema versions govern representation and validation, not a competing domain model. A schema MUST identify the specification/contract semantics it represents. Backward compatibility means previously valid consumer interactions remain valid with their promised behavior and safety guarantees. Unknown required fields/semantics cannot be ignored merely to claim compatibility.

**V-05.** Capability versions govern offered behavior. Plugin versions govern the contributed package; Plugins SHOULD declare compatible specification, Port, and Capability ranges and MUST declare enough compatibility information to validate activation. Ranges MUST define inclusive/exclusive bounds and prerelease handling where applicable. Matching version numbers alone MUST NOT override unsatisfied behavioral constraints or missing conformance evidence.

**V-06.** Artifact versions identify immutable content, not semantic compatibility releases. A content version MAY use an opaque identifier. Ordering, ancestry, and release status MUST be explicit; clients MUST NOT infer compatibility from artifact numbering.

**V-07.** Deprecation MUST identify affected versions, replacement or absence of replacement, support expectations, and migration guidance. Retirement MUST define effects on new bindings, ongoing executions, recovery, and retained records. Urgent security withdrawal MAY preempt normal deprecation, with attributable justification and controlled failure behavior.

**V-08.** Migrations MUST declare source/target versions, preconditions, semantic transformations, loss/limitations, authorization, and validation criteria. They MUST preserve identity links, tenant scope, provenance, and already committed effects/accounting. Reversibility MUST be stated, never assumed. Running state MUST NOT migrate silently; recovery on incompatible state MUST fail with VersionMismatch unless an explicit validated migration exists.

**V-09.** Conformance claims MUST include the applicable semantic version and supported profile. Replaceability MUST be demonstrated through behavioral tests at canonical boundaries; compatibility is not established solely by loading a plugin or accepting the same shape of data.

## 12. Core invariants and future conformance evidence

The identifiers below are stable anchors for future conformance tests. A conforming implementation MUST meet each applicable invariant; tests listed are acceptance scenarios, not implementation prescriptions.

| ID | Normative invariant | Observable conformance scenario |
|---|---|---|
| I-01 | Applications MUST express intent/capability needs independently of provider implementation; extensions MUST be explicit. | Replace a provider satisfying the same contract; intent/domain behavior remains valid, or explicit extension incompatibility is reported. |
| I-02 | Roles MUST be independent of Actors. | Assign the same Role to an eligible Human, Service, or Agent without redefining its responsibility. |
| I-03 | Teams MUST be compositions and MUST NOT require a specific orchestration framework. | Coordinate a Team of Humans and Services, including a child Team. |
| I-04 | Agents MUST NOT gain authority merely through reasoning or generated instructions. | Agent requests an ungranted action; enforcement denies it before effect. |
| I-05 | Capability resolution MUST satisfy every hard constraint and mandatory dependency. | Prefer a cheaper candidate that violates isolation; resolver excludes it despite its ranking. |
| I-06 | Tenant boundaries MUST persist through every operational association. | Forged context, delegated work, retrieval, or telemetry access cannot disclose another tenant's data without a valid grant. |
| I-07 | Execution MUST remain traceable. | Direct deterministic Tool use yields attributable context, decisions, effects, result, and resource records without an Agent. |
| I-08 | Important produced work SHOULD be represented as Artifacts. | A report/result has versioned producer, content, ownership, policy, and provenance; exceptions are justified. |
| I-09 | Delegation MUST preserve authority and inherited constraints. | A child request beyond parent delegable scope fails; a separate authorized grant is independently visible. |
| I-10 | Budgets MUST propagate and constrain aggregate delegated work. | Concurrent children cannot each spend the same remaining parent allocation. |
| I-11 | Policy enforcement MUST be possible outside probabilistic Actors. | Malicious instructions cannot suppress a mandatory policy/approval gate. |
| I-12 | Implementations MUST remain replaceable at canonical contract boundaries. | Two different adapters demonstrate equivalent lifecycle, error, tenant, governance, and observability behavior for their shared supported contract. |
| I-13 | Agent and language-model use MUST be optional. | A deterministic Workflow or direct retrieval path runs with neither Agent nor Model configured. |
| I-14 | Memory, Knowledge, retrieval, and Agents MUST retain distinct semantics. | Independent memory/retrieval usage does not construct an Agent or require generation. |
| I-15 | Human participation MUST be native and explicit. | A Workflow waits for HumanApproval; timeout never becomes consent. |
| I-16 | Historical versions and provenance MUST NOT be silently rewritten. | A new Skill, Plan, or Artifact version leaves an old Execution's bindings interpretable. |
| I-17 | Recovery MUST preserve effects, authority restrictions, and consumption. | Resuming a checkpoint does not replay a non-idempotent effect or restore revoked authority. |
| I-18 | Organizations MUST own canonical Goals and Teams MUST own canonical Outcomes without runtime privilege. | Goal/Outcome accountability is explicit; a direct invocation still runs without creating either. |
| I-19 | Private model reasoning MUST NOT be required for provenance or observability. | A Model exposing only outputs, usage, and version metadata can participate with sufficient public attribution. |
| I-20 | Evaluation MUST remain a first-class independent capability. | Assessment failure, inconclusive judgment, and failed subject quality produce distinguishable results. |

### 12.1 Intent traceability

| Intent sections | Specification coverage |
|---|---|
| 1–4, 38–41, 43–45, 52–54 | §§1–3, 7.3, 12: neutrality, intent, replaceability, escape hatches, accountability |
| 5–10, 21–24, 39, 42 | §§4.4, 4.12, 7, 11: contracts, composition, ports, plugins, versioning, independent representation |
| 11–17, 36–37 | §§3–6, 8: optional AI, Roles, Teams, Goals, delegation, humans, event-native work |
| 18, 26–28, 31–32 | §§4.5–4.8, 4.11, 5–6, 9: Skills, explicit state, Artifacts, information, provenance, tracing |
| 19–20, 29–30, 35 | §§2, 4.9–4.10, 6, 8–10: security, trust, tenants, resources, governance |
| 25, 46–51, 55–56 | §§1, 11–13: reference architecture remains lower-level; evaluation, conformance, governance, next artifacts |
| 33–34 | §§4.11, 11–12: independently evaluable changes and behavioral conformance |

Blueprints in intent §23 are reusable compositions of the definitions above and MUST obey the same validation/governance rules. No separate privileged Blueprint execution semantics are introduced here. Registry and configuration in intent §42 are logical discovery and declaration responsibilities; they do not prescribe centralized services or persistence. Their representation contracts remain future work.

## 12.2 Accepted semantic decisions

### DEC-01 — Operational Result vs Canonical Outcome

Direct primitive or capability execution MAY produce an operational result without creating a canonical Goal, Team, Organization, or Outcome.

A result becomes a canonical **Outcome** only when the application intentionally represents an accountable organizational or business achievement requiring the semantics defined for Outcome.

Therefore:

```text
Operational Result ≠ Canonical Outcome

## 13. Open questions, risks, and next document

These are explicit unresolved governance/contract questions, not permission to bypass the safe rules above. The specification introduces semantic refinements where intent is silent; acceptance of this revision remains a project governance decision.

| ID | Question / ambiguity | Current boundary and required follow-up |
|---|---|---|
| Q-02 | Can Organizations be co-owned across tenants, or is collaboration through scoped associations sufficient? | This revision uses one tenant per operational entity and explicit cross-scope grants. Joint cross-tenant ownership is unsupported until a deliberate semantic extension is accepted. |
| Q-03 | Who governs canonical namespaces, approved extension vocabularies, and compatibility certification? | Namespace authority MUST be explicit; no global registry operator or distribution design is selected. Define governance before public contract publication. |
| Q-04 | Which minimum feature sets deserve named conformance profiles? | §1.2 requires explicit supported scope; §12 supplies applicable invariants. Define profiles and evidence requirements before making implementation-wide conformance claims. |
| Q-05 | What policy authority resolves organizational, tenant, retention, residency, and emergency-control conflicts? | No silent weakening is permitted. Protected actions fail on unresolved conflicts; disposition follows A-03. Define authority/exception profiles without selecting a policy technology. |
| Q-06 | What precision, reservation tolerance, and overrun policy apply to uncertain externally metered resources? | §8 requires explicit units and bounded admission/uncertainty rules. No universal currency, tariff, clock precision, or billing model is assumed. |
| Q-07 | What durability, ordering, recovery, and retention levels are mandatory for each capability/profile? | Capabilities MUST declare guarantees and limitations; universal exact replay/ordering is not promised. Specify independently testable profiles at the contract layer. |
| Q-08 | Which cardinality defaults, standard Artifact types/relations, and blueprint manifest vocabulary should be standardized? | §3 provides base cardinalities; extensions require declared semantics. Domain vocabularies and serialization remain later contracts and MUST not redefine core concepts. |

### 13.1 Architectural risks

- **Abstraction breadth:** A single mandatory runtime containing all concepts would undermine independent reuse. Conformance scopes and capability dependency closure MUST preserve modular consumption.
- **Authority confusion:** Conflating Role, Actor, Principal, Provider, or Team membership risks privilege escalation. Their independent bindings and checks are normative.
- **Recovery and accounting races:** Retrying uncertain effects or double-allocating parent resources can violate correctness even when individual calls appear valid. Effect attribution and aggregate resource governance require behavioral proof.
- **False portability:** Declared compatibility without matching guarantees, or hidden extension dependencies, can make providers nominally interchangeable while changing safety or results. Conformance evidence and explicit extension impact are necessary.
- **Audit versus confidentiality:** Excessive logging or indefinite retention can violate tenant/privacy obligations; insufficient evidence undermines accountability. Policy must govern both content and audit references, with explicit handling of conflicts and missing evidence.

### 13.2 Final specification self-review

| Check | Result and evidence |
|---|---|
| No technology-specific assumptions in the canonical model | Pass: no vendor, runtime, transport, storage, language, or cloud is required (§1). |
| Independent language implementations can conform | Pass: semantic properties and behaviors, no language interfaces (§§1–2). |
| Different agent runtimes can conform | Pass: Agent behavior and Ports are independent (§§4.2, 4.12). |
| Operation without Agents | Pass: independent capability consumption (§1.2, I-13). |
| Operation without a language model | Pass: deterministic/direct work is valid (§1.2, §4.6). |
| Teams contain Humans and Services as well as Agents | Pass: §3 and Team definition. |
| Roles separated from Actors | Pass: RoleAssignment and I-02. |
| Requirements separated from Providers | Pass: §4.4 and §7. |
| Tenant boundaries represented | Pass: S-10–S-11, TenantContext, I-06. |
| Trust boundaries represented | Pass: TrustBoundary, S-09, E-06. |
| Resource budgets represented | Pass: §4.10 and §8.2. |
| Artifacts first-class | Pass: §4.8, §5.10, §9. |
| Provenance represented | Pass: §4.11, S-12, E-07. |
| Delegation authority bounded | Pass: D-01–D-05. |
| Future technologies can implement existing contracts | Pass: Ports/Adapters/Plugins and explicit extension rules (§§4.12, 7.3, 11). |

This is a semantic review, not evidence that any runtime or adapter already conforms.

**Next document:** `architecture/ARCHITECTURE.md`, a technology-neutral logical architecture derived from this specification. It should define module responsibilities, dependency direction, enforcement boundaries, configuration/discovery/resolution responsibilities, and independent conformance scopes; it should address Q-01 through Q-08 or carry them forward explicitly. Concrete contracts and conformance cases follow that architecture. No implementation is authorized by this specification task.
