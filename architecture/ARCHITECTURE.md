# Lego AI Operating Layer — Logical Architecture

**Architecture version:** 0.1.0  
**Status:** Proposed architecture; review pending  
**Governing sources:** [intent.md](../intent.md), version 1.0, ACCEPTED — FOUNDATIONAL; [SPEC.md](../SPEC.md), version 0.1.0, ACCEPTED — CANONICAL SEMANTIC SPECIFICATION  
**Scope:** Technology-neutral decomposition, responsibility allocation, interactions, and conformance boundaries

## 1. Authority and architectural decisions

Authority flows from `intent.md` to `SPEC.md` to this document. The normative vocabulary and canonical semantics of SPEC §1 apply. Architecture MUST NOT redefine canonical entities, ownership, cardinalities, state transitions, errors, or compatibility. References such as S-10 or E-06 refer to requirement identifiers in SPEC; identifiers prefixed AR belong to this architecture.

This architecture allocates the responsibilities necessary to realize those semantics. It defines logical modules and their contracts, not programming interfaces, concrete schemas, transports, products, deployment units, or implementation algorithms. A **plane** groups related responsibilities; a **module** owns a bounded responsibility and authoritative state; a **runtime** is a composition performing governed execution. None of these terms requires a separate process or service.

### 1.1 Decisions established here

| ID | Decision | Governing rationale |
|---|---|---|
| AR-01 | Use a small stable Kernel of shared semantics and abstract contracts, surrounded by independently composable modules. | Intent §§5–6, 11, 42; SPEC §§1.2, 4.12. |
| AR-02 | Separate logical control responsibilities from execution responsibilities, without separate deployment requirements. | Definitions, bindings, state, and effects have different authorities and lifetimes. |
| AR-03 | Separate discovery, resolution, authorization, and invocation. | Selection is neither trust admission nor an authority grant (C-01–C-06, S-09). |
| AR-04 | Assign each authoritative state item to one module; other modules interact through contracts and revisioned references. | S-06 and L-01 prohibit silent state conflicts. |
| AR-05 | Enforce policy and resource obligations at protected action/data boundaries outside probabilistic Actors. | Intent §§19–20, 35; E-03, E-06. |
| AR-06 | Support direct capabilities, Workflows, Models, Agents, Teams, Humans, and Services as optional compositions. | I-02–I-03, I-13–I-15. |
| AR-07 | Distinguish operational results from deliberately represented accountable Outcomes. | SPEC §12.2 DEC-01 and the accepted direction for Q-01. |
| AR-08 | Preserve the ability to start as a modular monolith and later distribute modules behind unchanged semantic boundaries. | Intent §§24–25, 38–40. Distribution must preserve guarantees, not merely message shapes. |

### 1.2 Source issues and compatibility boundaries

The supplied SPEC has an unclosed text fence following DEC-01 and §13 still says acceptance remains a governance decision despite the accepted header. These are recorded source defects, not authority for changing semantics. This architecture reads DEC-01 and the subsequent Q-02–Q-08 text as the intended sections and uses the explicit accepted status; it does not edit the source. A specification maintenance change should repair the fence and reconcile the stale status wording.

The requested plugin activity sequence includes inspect, admit, configure, suspend, and upgrade. SPEC §5.12 does not define these as Plugin states. Section 11 maps them to activities and permitted transitions; it MUST NOT introduce an incompatible lifecycle.

Intent §42 shows registry, resolver, events, and configuration within the Kernel. Here their stable meanings and contract anchors remain part of that Kernel boundary; their operating implementations and mutable state belong to surrounding modules. This is a decomposition of the illustrated responsibility, not removal of it or a dependency from Kernel to concrete providers.

One additional lifecycle ambiguity affects recovery: SPEC §5.8 permits `suspended → admitted` and `admitted → rejected`, but defines rejected as work that did not begin. A resumed attempt may already have effects. Section 8.3 preserves failure/uncertainty and does not use rejected to erase prior work; the exact admissible transition guards require clarification in SPEC before recovery contracts are finalized (R-03).

## 2. Overall logical architecture

```text
APPLICATION / INTENT
  declarations • configuration • blueprints • goals • organizations / teams
                              |
                    CANONICAL PUBLIC CONTRACTS
                              |
  +---------------- SMALL STABLE KERNEL ----------------+
  | identity/reference semantics • context invariants   |
  | lifecycle/version/error primitives • port contracts |
  | capability/event/provenance/configuration meanings  |
  +----------------------------------------------------+
                              |
              COMPOSABLE LOGICAL RESPONSIBILITIES
  +------------------------+---------------------------+
  | Capability Plane       | Execution Plane           |
  | Coordination Plane     | Tool / Action Plane       |
  | Intelligence Plane     | Context / Memory /        |
  | Artifact Plane         | Knowledge Plane           |
  | Governance Plane       | Resource Governance Plane |
  | Evaluation Plane       | Observability / Provenance|
  | Extension Plane        | Event coordination module |
  +------------------------+---------------------------+
                              |
                     PORT IMPLEMENTATIONS
                              |
              ADAPTERS / PLUGIN CONTRIBUTIONS
                              |
                   REPLACEABLE REALIZATIONS
```

This diagram groups responsibility; it is not a mandatory invocation chain. A minimal composition MAY contain only a direct capability and the context, enforcement, accounting, and trace responsibilities applicable to that use. It MUST NOT load Team, Agent, Model, or Workflow functionality merely to satisfy a diagram. Governance and observation responsibilities may be small local modules; they need not be network services.

Public contracts are owned by the module responsible for their meaning, conform to the Kernel's shared rules, and have no dependency on that module's implementation. A Port describes an interaction boundary. An Adapter realizes that boundary. A Plugin packages admitted contributions; it is not a privileged alternate path.

## 3. Control Plane and Execution Plane

```text
LOGICAL CONTROL RESPONSIBILITIES
 register definitions / offers / plugins
 validate and version configuration
 define policy, resource rules, evaluation criteria
 discover → resolve → record bindings
 admit / activate / deprecate / retire contributions
                       |
       immutable revisions + scoped binding references
                       v
LOGICAL EXECUTION RESPONSIBILITIES
 authenticate / bind context / admit work
 perform work → govern each effect → preserve products
 transition state / wait / checkpoint / recover / cancel
 account resources / assess results / record evidence
                       |
       observations + explicit change requests / events
                       v
 CONTROL RESPONSIBILITIES validate any resulting changes

Live authorization, policy, approval, resource, and tenant checks
apply at execution boundaries; historical control decisions are
evidence, never perpetual permission.
```

The Control Plane owns definition and eligibility changes; the Execution Plane performs admitted work and reports actual effects. Several modules participate in both: Governance defines rules and supplies live decisions; Resource Governance defines allowances and arbitrates consumption; Extension manages lifecycle and reports operational health; Evaluation defines criteria and performs assessment.

**AR-09.** A control update MUST create attributable revisions and explicitly state its applicability to existing work. Restrictive changes and revocations MUST affect subsequent governed actions as required by E-03. New grants MUST NOT silently expand an admitted attempt. Configuration and definition updates MUST NOT rewrite pinned history.

**AR-10.** An execution observation MAY motivate control changes, but MUST NOT directly mutate policy, offers, grants, or configuration. The responsible owner validates and authorizes each change. Evaluation recommendations are inputs to release/admission decisions, not those decisions themselves.

**AR-11.** Failure or unavailability of a control function MUST NOT cause stale bindings or missing mandatory policy checks to be treated as valid. Existing work may continue only while its applicable current validity, authority, and resource conditions can be established. No globally available controller is assumed.

## 4. Layer and bounded-module responsibilities

Each subsection identifies responsibility, owned state, and public interactions. Ownership here means authority to change a record, not physical storage custody or business ownership. Shared rule S-02 still governs accountable domain owners.

### 4.1 Application / Intent Layer

The **Application Composition module** manages Application declarations, domain configuration, blueprint expansion, referenced Organizations/Teams, capability requirements, goals, and acceptance criteria. Blueprint expansion produces ordinary canonical compositions; it MUST NOT hide executable privileged behavior. Domain logic defines desired work and evaluates domain expectations through declared contracts.

- **Owns:** Application definition/configuration revisions, activation records, composition validation, blueprint expansion lineage, selected requirement sets.
- **Uses:** Definition-validation, discovery/resolution, lifecycle, and execution-entry contracts; Coordination contracts when organizational work is represented.
- **Exports:** Validated declarations and activation requests, not provider-specific executable structures.
- **Boundary:** MUST NOT depend directly on concrete Adapters. Intentional extensions remain explicit requirements with documented portability consequences. Activation validates mandatory dependencies and governance; activation is not blanket invocation permission.

### 4.2 Lego AI Kernel

The Kernel is the smallest common semantic foundation, not a central scheduler or universal mutable object repository.

| Candidate responsibility | In the stable Kernel | Outside the Kernel |
|---|---|---|
| Canonical identity | Identity, scope, reference, revision, and attribution rules | Identity verification, identity issuance policy, credential handling |
| Execution context | Envelope meaning, immutable fields, propagation invariants | Context admission/assembly and mutable attempt state |
| Capability semantics | Capability identity, requirement/offer/binding meaning | Catalog state, discovery, matching, ranking, dependency search |
| Lifecycle primitives | Transition evidence, expected revision, terminal-state rules | Per-concept state machines operated by their owning modules |
| Registry abstractions | Registration/discovery contract meaning | Registration stores, access filtering, health projections |
| Dependency rules | Direction, compatibility, explicit dependency declarations | Dependency-closure calculation and composition planning |
| Configuration interpretation | Revision, validation, unknown-field/extension and reference rules | Domain configuration, plugin-specific validation, effective configuration assembly |
| Provenance primitives | Attribution, source/version/causal-reference meaning | Lineage capture, evidence retention, audit review |
| Event semantics | Fact identity, type/version, causation and scope | Routing, delivery attempts, consumer disposition |

- **Owns:** Published shared contract versions and invariant definitions; no tenant execution balances, plugin instance state, or business work state.
- **Exports:** Stable abstractions against which all modules and Adapters conform.
- **Boundary:** MUST NOT require an Agent, Model, Workflow, catalog implementation, policy engine, or telemetry implementation to define its contracts. Common semantics do not require one physical package or one global identity allocator.

### 4.3 Capability Plane

The **Capability Catalog module** owns registrations and offer revisions, capability namespaces as declared by their authorities, discoverable metadata, and published eligibility/health evidence references. It distinguishes a registered offer from an active eligible offer. Discovery returns scoped candidates and evidence, not guarantees of selection or permission.

The **Capability Resolution module** owns resolution request records, input snapshots, constraint evaluations, dependency closures, ranking/ambiguity evidence, and immutable CapabilityResolutions. Compatibility includes capability/Port/specification versions, explicit extension semantics, consumer constraints, and provider suitability.

- **Uses:** Catalog queries, Governance constraints/trust evidence, Extension eligibility, resource feasibility evidence, and canonical version rules.
- **Exports:** Explainable selected bindings or unsatisfied/conflict/ambiguous/invalid results.
- **Boundary:** The resolver MUST NOT issue grants, consume approvals, reserve spend simply by selecting a provider, or invoke the selected capability. Admission and invocation revalidate live restrictions. Composite guarantees include dependency failure and degradation semantics.

### 4.4 Execution Plane

The **Execution Coordination module** owns Execution admission, immutable ExecutionContext envelopes, attempt state revisions, scheduling intent, waits, parent/child attempt links, cancellation coordination, deadlines, and result reconciliation. It exposes a common governed entry contract without requiring a central executable runtime.

Optional execution drivers are separate:

- **Direct capability driver:** Routes an admitted invocation to its bound Port without a Task, Workflow, Goal, or Agent requirement.
- **Workflow driver:** Owns Workflow definitions, WorkflowState revisions, branching/join/iteration interpretation, and workflow-specific state compatibility.
- **Agent driver:** Owns Agent behavior definitions, instance state, bounded decision iterations, and action proposals. Models and Skills are optional dependencies, not universal prerequisites.
- **Human/Service participation drivers:** Track work delivery, acceptance, waits, and attributed results under the same execution governance; participation is not an error condition.
- **Recovery responsibility:** Execution Coordination owns Checkpoint records referencing driver-owned state and authoritative effect/accounting evidence. Drivers own the meaning and compatibility of their captured state.

Drivers report progress through contracts; they MUST NOT directly change Task acceptance, approval status, or resource balances. One implementation MAY combine these modules physically while preserving ownership and replaceability.

### 4.5 Coordination Plane

The **Organizational Composition module** owns operational Organization/Team compositions, Role definitions and RoleAssignments, Actor participation associations, and staffing/eligibility records. Identity and grants remain Governance responsibilities. Team composition is acyclic and does not union members' permissions.

The **Work Coordination module** owns Goals, Plans, Tasks, Delegation records, assignment decisions, completion acceptance, and canonical Outcome assessment records. Business ownership remains Organization → Goal and Team → Outcome; module stewardship does not replace it.

- **Uses:** Capability requirements/resolution, current Governance decisions, Resource Governance allocations, Execution requests/results, Artifact references, and Evaluation results.
- **Exports:** Accepted work obligations, bounded delegations, progress, and evidence-backed acceptance decisions.
- **Boundary:** A Team recipient identifies its authorized acceptance Principal and subsequently accountable Actors. Coordination MUST NOT pretend a Team itself is an Actor subtype or give organizational hierarchy runtime privilege. Human-only and service-heavy Teams are valid.
- **Q-01 decision:** Direct invocations return operational results without creating canonical Goal/Outcome or organizational composition. Promotion to an Outcome is an intentional, authorized assessment with an accountable Team and evidence. No fabricated organizational entities are needed for standalone capabilities.

### 4.6 Tool / Action Plane

The **Action Mediation module** owns Tool contract registrations, action validation, effect classifications, invocation records, effect identities, deduplication/equivalence checks, dispatch decisions, effect observations, and reconciliation/compensation requests. Tool discovery uses the Capability Catalog; separate private tool listings MUST NOT bypass its scope rules.

- **Uses:** Governance decisions, approvals and Secrets contracts; Resource Governance admission; selected Tool Port bindings; sandbox/isolation contracts when required; observation contracts.
- **Exports:** Action results with canonical errors and known/unknown effects, never an unconditional claim that timeout means failure without effects.
- **Boundary:** Agents MUST route governed actions through this plane. Tools called by Workflows, Humans, Services, Skills, or direct Applications receive equivalent enforcement. A sandbox bounds admitted activity; it does not replace authorization, tenant isolation, or effect accounting.

Effect classification includes read/disclosure, mutation, external communication, irreversible action, and unknown/mixed effects as contract-defined categories. Classification determines required controls; a read may still disclose sensitive data or incur cost. Compensation, where available, is a new separately governed action. Tool mediation does not own authorization policy or issue Permissions.

Other planes retain domain-specific Ports for Models, retrieval, artifacts, and evaluation. Their protected uses MUST enforce the same E-06 action obligations. They need not relabel every operation as a Tool. They MUST NOT use domain-specific Ports to provide an Agent an unmediated path to governed Tool effects.

### 4.7 Intelligence Plane

The **Model Interaction module** owns model descriptors, ModelCapability declarations, input/output contract validation, invocation evidence, model revision attribution, and relevant usage observations. Provider offers remain registered through the Capability Plane. Structured-output requirements describe shape/meaning guarantees without selecting serialization. Multimodal requirements specify admissible input/output modalities and limits without a mandatory model family.

The **Skill Asset module** owns versioned expertise definitions, instructions/resources, Skill dependencies, composition validation, and evaluation references. Executable Skill resources require the same governed action routes as other work.

- **Uses:** Model/Skill Ports, governed invocation facilities, authorized Context, optional Artifact references, and Evaluation contracts.
- **Exports:** Validated model results, explicit output-contract failures, and reusable Skill assets.
- **Boundary:** Models MUST remain independently consumable and MUST NOT imply Agents or Workflows. Generated plans/actions are proposals. Structured output is not proof of truth, safety, authorization, or domain correctness. Skill instructions cannot self-authorize dependency installation or control changes.

### 4.8 Context / Memory / Knowledge Plane

| Module / semantic scope | Owned state and responsibility | Boundary |
|---|---|---|
| Context Assembly | Scoped input/reference sets, origin/trust classification, summary lineage, freshness | Supplies information, not grants; separate from immutable ExecutionContext |
| Working state | Driver-owned current computation/progress and variables | Authoritative execution progress stays with its driver; working Memory may reference it but cannot overwrite it |
| Session Memory | Session-scoped retained information and expiry rules | Session identity is not tenant identity or authorization |
| Semantic Memory | Meaning-oriented retained facts/associations with source/confidence | No indexing/storage technique defines its semantics |
| Episodic Memory | Attributed experiences and prior activity records | Recalled experience does not become current state or current permission |
| Procedural Memory | Retained learned procedures and usage conditions | Promotion to published Skill or Policy needs separate validation and authority |
| Knowledge Curation | Governed sources, assertions, revisions, applicability, organizational knowledge | Organizational ownership does not grant universal organizational access |
| Retrieval | Query semantics, admissible source bindings, ranking evidence, result references | Filters access before disclosure; returns source lineage, not automatic truth |

Memory submodules MAY share one implementation if their contracts and ownership are distinguishable. Retrieval may consume Memory, Knowledge, or other governed source Ports. Their interfaces MUST remain independently usable without Agent, generation, or conversation dependencies.

**Memory ≠ vector database. Knowledge ≠ retrieval-augmented generation (RAG). RAG ≠ Agent.** Retrieval-augmented generation is a composition of retrieval and generation; the architecture gives it no privileged or mandatory orchestration path.

### 4.9 Artifact Plane

The **Artifact Management module** owns Artifact identities, ArtifactVersions, metadata, version aliases, ArtifactRelationships, publication/withdrawal records, visibility decisions as applied under policy, and disposition progress. It validates exact-version relationships and preserves producer attribution.

- **Uses:** Content-access/preservation abstraction, Governance policy/access/retention decisions, provenance evidence, Evaluation results, and approval gates.
- **Exports:** Stable identities and pinned versions with accessible content references or explicit unavailability.
- **Boundary:** Content location MUST remain independent of Artifact identity. Storage custody does not own canonical identity. Moving content behind the abstraction MUST preserve meaning, version, integrity guarantees, and scope. Artifact relationship metadata is itself access-controlled.

Artifact Management owns work-product lineage edges; Provenance owns general production evidence. The modules exchange references and validate consistency, rather than each maintaining a competing authoritative artifact ancestry graph. Publication and acceptance are distinct: publishing an Artifact does not mark a Task successful or a Goal achieved.

### 4.10 Governance Plane

Bounded responsibilities are:

| Module | Owned state / decision responsibility |
|---|---|
| Identity and Principal | Verified Identity associations, Principal status, acting-on-behalf-of evidence |
| Tenant Governance | Tenant status, isolation rules, verified TenantContext admission, cross-scope grant evidence |
| Authorization | Permission grant/deny records, issuer authority, delegation eligibility, current action authorization |
| Policy Decision | Policy versions, combination rules, applicability, decisions and obligations |
| Guardrail Coordination | Control definitions, placement, evaluations, verdicts and enforcement obligations |
| Approval Management | Approval/HumanApproval requests, presented action revisions, eligible approvers, decisions, consumption/revocation |
| Secret Access | Secret references, validity, rotation and authorized-use evidence; protected material through its Port |
| Boundary Enforcement | Protected-operation checks and decision evidence at each consuming boundary |

Boundary Enforcement is a responsibility installed at each relevant module boundary; it is not necessarily a central gateway. The protected action owner MUST enforce its returned obligations before the action. No Agent, provider advertisement, or generated text may assert that enforcement has already succeeded without verifiable evidence.

Policy defines when a Guardrail, HumanApproval, sandbox, resource check, or audit record is necessary. A model-assisted Guardrail can supply evidence; deterministic authorization and mandatory policy obligations MUST remain enforceable outside it. Unknown mandatory policy decisions fail closed. Approval fulfillment does not replace Principal authorization or grant increased authority.

### 4.11 Resource Governance Plane

The **Resource Admission and Accounting module** owns Budget allocations, reservation and consumption records, Quota window usage, Limit measurements, reconciliation status, resource admission decisions, and parent/child allocation links. It applies ResourcePolicy versions governed by the Policy lifecycle; it does not create unrelated authorization grants.

- **Uses:** Governed ResourcePolicy and scope inputs, attributable effect/usage observations, authorized allocation changes, and deadline semantics.
- **Exports:** Scoped admission/reservation decisions, remaining availability, exhaustion signals, and reconciled usage.
- **Boundary:** Resource observations from execution are claims to reconcile, not direct writes to balances. One logical authority MUST arbitrate each allocation's spendable amount. Concurrent children MUST NOT spend copied snapshots of parent balances.

Execution Coordination owns deadline propagation and stopping/waiting behavior; Resource Governance owns time-as-resource accounting and checks the effective bound during admission. Neither can extend a parent deadline without the applicable authorized change. Section 9 defines concurrent and uncertain accounting.

### 4.12 Evaluation Plane

The **Evaluation Management module** owns Evaluator definitions, method/criteria versions, Evaluation attempt records, EvaluationResults, baseline comparisons, uncertainty, and assessment limitations.

- **Uses:** Evaluation Port realizations, authorized subject/input references, governed execution and resource facilities, Artifacts, and provenance.
- **Exports:** Evidence and judgments, including inconclusive judgments and assessment failures.
- **Boundary:** Runtime and offline evaluation differ in trigger and input environment, not tenant, authorization, attribution, or version obligations. Evaluation MUST work without Agents. EvaluationResult pass/fail is distinct from Execution success/failure.

Release gates are Governance decisions using Evaluation evidence. Conformance evaluation applies contract criteria; the scope and authority of certification are defined by later CONFORMANCE/GOVERNANCE documents. Evaluators MAY be deterministic, Human, probabilistic, or composed. Criteria/method changes and provider substitutions remain independently evaluable.

### 4.13 Observability / Provenance Plane

| Responsibility | Meaning | Owned evidence |
|---|---|---|
| Trace | Operational activity and causal relationships | Activity observations, timing/status, attempt correlations, collection completeness |
| Telemetry | Measurements and diagnostic observations | Governed metrics and safe diagnostic records, including usage observations |
| Audit | Attributable evidence of material actions and decisions | Retained decision/action attestations and evidence of their recording; source modules still own decisions |
| Provenance | What produced a subject and under what conditions | Source/version/transformation evidence and references to Artifacts, resolutions, decisions, and Trace |
| Evaluation | Assessment against criteria | Owned by Evaluation, linked here as evidence rather than reinterpreted as telemetry |

The **Observation Collection module** owns trace/telemetry collection. The **Evidence and Provenance module** owns audit retention and general production-lineage records. Source modules MUST create the underlying attributable decision/effect records; collection MUST NOT invent or overwrite their facts. Artifact lineage remains owned by Artifact Management.

Observability MUST NOT become domain business logic or an alternate authorization service. Policy MAY explicitly require audit recording as a precondition for an action. Optional diagnostic collection failure need not stop work, but MUST NOT hide missing mandatory evidence. Retention/classification apply independently to each evidence type. Cost telemetry is derived from or reconciled with authoritative accounting, never a second source of spendable balance. Private model reasoning MUST NOT be required.

### 4.14 Extension Plane

The **Plugin Admission and Lifecycle module** owns plugin descriptions, contribution inventory, version compatibility assessments, validation/admission evidence, configuration bindings, activation records, health evidence, and retirement coordination. Providers and Adapters have explicit owning Plugin versions, including built-in contributions.

- **Uses:** Canonical Port contracts, capability dependency assessment, Governance trust/permissions/tenant decisions, resource admission, conformance evidence, and lifecycle-control contracts.
- **Exports:** Admitted contribution availability and health evidence to the Catalog; exact activation/version references to invokers.
- **Boundary:** Discovery or installation is not trust. A Plugin MUST NOT install its own authority or bypass governance through activation callbacks. Replaceable implementations remain outside stable contract dependencies. Section 11 defines admission, bootstrap, and upgrade boundaries.

### 4.15 Event coordination module

An **Event Coordination module**, usable across planes, owns authorized publication/routing definitions, event delivery attempts, retry/dead-letter or equivalent unresolved-delivery records, and acknowledgment evidence. The module owning the underlying fact owns its truth; consumers own their handling decisions.

It uses Event Ports and MUST preserve source/type/version, tenant, correlation, and causation. Publication does not imply delivery; delivery does not imply acceptance or effects. Event Coordination MUST NOT authorize triggered work, order unrelated domains globally, or infer exactly-once effects from event identity. It supports event-native Applications without requiring conversational interfaces.

## 5. Dependency direction and matrix

### 5.1 Contract dependency direction

```text
Application domain logic ---> Canonical public contracts
                                      |
                                      v
                         Kernel semantics / Port contracts
                                      ^
                                      |
                            Modules and Adapters

For each replaceable realization:
       Core / consuming module ---> Port <--- Adapter

Forbidden dependency:
       Core / domain meaning ------> Concrete Adapter semantics
```

Dependencies in this section mean reliance on another module's **published contract**, never its internal implementation or writable records. Runtime calls can flow both ways through independent contracts without introducing implementation imports in both directions. Every contract package or equivalent representation MUST be separable from its provider.

### 5.2 Architectural dependency matrix

Abbreviations: **K** Kernel, **C** Capability, **E** Execution, **W** Work/organizational Coordination, **T** Tool/Action, **I** Intelligence, **M** Context/Memory/Knowledge, **A** Artifact, **G** Governance, **R** Resource, **Q** Evaluation, **O** Observability/Provenance, **X** Extension, **V** Event. Application is the external composition consumer.

This is a sparse dependency matrix: the middle column names all permitted module-contract targets; omitted targets are prohibited until an explicit architecture revision supplies a rationale. A permitted dependency is not mandatory. Intra-plane submodules use their own published boundaries. All interactions inherit K's rules even where K is not repeated.

| Consumer | Allowed contract targets | Responsibility restriction |
|---|---|---|
| Application | K, C, E, W, T, I, M, A, G, R, Q, O, X, V | Uses supported public capabilities; administration targets require explicit administrative authorization |
| K | None of the operating modules | Defines shared semantics; no operational implementation dependency |
| C | K, G, R, O, X | Discovery uses Catalog internals; resolution consumes eligibility/constraints and feasibility, never invocation or grants |
| E | K, C, T, I, M, A, G, R, O, X, V | Invokes drivers/ports and records attempts; no direct mutation of W's Task/Outcome state |
| W | K, C, E, A, G, R, Q, O, V | Assigns/accepts work, not effect execution or permission issuance |
| T | K, C, G, R, O, X, V | Executes bounded actions; external implementation behind Tool Port |
| I | K, C, M, A, G, R, O, X | Model/Skill realization independent of Workflow/Agent; Skill actions route via E/T from the consumer |
| M | K, C, A, G, R, O, X | Governed information/queries; MUST NOT require Agent or Model |
| A | K, G, R, Q, O | Artifact state/content and release evidence; no storage-specific semantics |
| G | K, R, O | Accesses Resource decisions as obligations, not accounting internals; guardrail/approval providers implement G's Ports |
| R | K, G, O | Applies versioned policies and verifies claims; MUST NOT recursively request a decision on the same unresolved operation |
| Q | K, C, A, G, R, O, X | Governs its assessment execution through shared admission contracts owned by G/R; evaluator driver is behind Q's Port |
| O | K, G | Evidence access/retention and attribution; no scheduling, ranking, or business decision dependency |
| X | K, C, G, R, Q, O, V | Assesses/adopts contributions; cannot make an inactive provider eligible by calling resolution |
| V | K, G, R, O | Delivers facts to declared consumer ingress; cannot directly mutate consumer work state |
| Adapter | K and implemented Port contracts | Uses replaceable implementation facilities internally; other canonical capabilities only through declared, governed dependencies |

A standalone consumer of T/I/M/A/Q receives governed execution admission through E's public entry or an equivalent local composition of the same E contract responsibilities. The capability implementation itself need not depend on E or know whether its caller is an Agent or Workflow. Thus Model implementations do not depend on Workflow; Evaluation remains standalone while its work still has Execution attribution.

**AR-12.** Contract-level cycles such as G ↔ R, A ↔ Q, or C ↔ X MUST NOT imply recursive admission or shared state. Split read-only evidence queries from commands: a decision may consume already identified policy/evidence revisions, while an explicit orchestration request advances the next step. A release evaluation reads a pinned ArtifactVersion; it does not request publication recursively. Plugin dependency inspection uses declared offers; activation publishes eligibility later. Section 11.3 governs bootstrap dependencies.

**AR-13.** Prohibited dependencies include Kernel → Adapter implementation, Agent → authorization ownership, Retrieval → Agent, Model → Workflow, Policy enforcement → model compliance, Artifact identity → storage location, Resolution → permission issuance, and Observability → application business decisions. A module MUST NOT read or mutate another module's private state to bypass its Port.

## 6. State ownership and consistency boundaries

### 6.1 Authoritative state map

| State | Authoritative module | Other modules receive |
|---|---|---|
| Application declarations / effective configuration | Application Composition | Pinned validated revisions |
| Shared concept/version/transition meanings | Kernel contract governance | Immutable published contracts |
| Capability registrations / offers | Capability Catalog | Scoped snapshots plus eligibility evidence |
| Resolution decisions / dependency closure | Capability Resolution | Immutable result and binding references |
| Plugin instances / activation / health evidence | Plugin Lifecycle | Eligibility observations, exact activation references |
| Organization / Team / Role / Actor participation | Organizational Composition | Validated compositions and RoleAssignments |
| Goal / Plan / Task / Delegation / Outcome | Work Coordination | Work obligations, grants by reference, acceptance records |
| Execution envelope / attempt status / cancellation | Execution Coordination | Revisioned status and causal result references |
| WorkflowState / Agent instance state | Respective driver | Compatible snapshots or state references |
| Checkpoint identity / captured revision set | Execution Coordination | Immutable checkpoint references; drivers retain state meaning |
| Protected invocation / effects / reconciliation evidence | Invoking plane; Action Mediation for Tools | Attributable effect records, not inferred success |
| Context / Memory / Knowledge / retrieval evidence | Respective information module | Scoped values/references and lineage |
| Artifact identity / version / relationships / publication | Artifact Management | Exact versions and governed content access |
| Policy / grants / approvals / Secret validity / tenant admission | Respective Governance module | Verifiable current decisions and safe references |
| Budgets / reservations / quota usage / reconciliation | Resource Admission and Accounting | Allocation and usage decisions; projections are non-authoritative |
| Evaluator definitions / assessment results | Evaluation Management | Versioned evidence, not release authority |
| Trace observations / audit retention / general provenance | Respective observation/evidence module | Policy-filtered evidence and completeness status |
| Event delivery attempts | Event Coordination | Delivery acknowledgment; source/consumer own fact/handling |

### 6.2 Cross-module changes

**AR-14.** Each owner MUST validate scope, expected prior revision, authorized command, and valid transition before acknowledging authoritative state change. Read projections MAY exist, but MUST identify revision/freshness and MUST NOT independently authorize changes to their source. No global shared mutable execution context is permitted.

**AR-15.** Cross-module work MUST identify its operation, causal context, intended sub-operations, each owner's acknowledgments, and incomplete obligations. Atomicity across all modules is not assumed. If publication, accounting, event delivery, or acknowledgment fails after an external effect, record partial completion and reconcile it; do not retry the original effect merely to reconstruct local records.

**AR-16.** A module publishing a material state-change Event MUST distinguish a proposed change from a committed fact. The relationship between state acknowledgment and event publication MUST have declared failure/recovery semantics. The producer retains an attributable publication obligation until its declared delivery guarantee is met or failure is explicitly recorded. This does not mandate a particular storage or messaging pattern.

**AR-17.** Concurrent action admission MUST coordinate approval-use bounds, resource reservations, revocation checks, and effect identity without assuming that sequential checks alone eliminate races. Each owning module arbitrates its own consumable claims. The effect dispatcher MUST verify that the specific action is still covered at the dispatch boundary. Unknown or expired claims prevent dispatch. The exact commit/freshness semantics belong in CONTRACTS and SECURITY; no distributed atomicity product is selected.

## 7. Capability discovery, resolution, and binding

```text
CapabilityRequirement revisions
             |
             v
Scoped Discovery ---> Candidate Provider offers + evidence snapshot
             |
      Compatibility / versions / explicit extensions
             |
      Hard constraints / known evidence
             |
      Policy and trust suitability constraints
             |
      Recursive dependency closure + composition conflicts
             |
      Preference ranking + authorized ambiguity handling
             |
      Immutable CapabilityResolution + provenance
             |
      Exact binding reference for admitted use
             |
      SEPARATE: live authorization / admission / invocation
```

### 7.1 Separation of responsibilities

| Operation | Answers | Does not establish |
|---|---|---|
| Discovery | Which visible offers exist and what do they claim? | Compatibility, current invocation authority, or trust solely from registration |
| Resolution | Which eligible complete binding satisfies the requirement set? | A grant, consumed approval, actual reserved budget, or effect |
| Authorization/admission | May this Principal perform this action now under these constraints? | Provider quality beyond evaluated evidence, or proof that an effect occurred |
| Invocation | Perform the admitted operation and report observed effects/result. | Task acceptance, Goal achievement, or permission for another action |

Governance supplies applicable policy/trust constraints to matching, but invocation authorization remains a separate decision for a specific action and Principal. Resource feasibility during resolution is an estimate or query; actual spend arbitration occurs at admission. Provider health evidence has freshness and cannot replace checks at use.

### 7.2 Binding rules

The Catalog MUST distinguish visible registration, provisional contribution inspection, active eligibility, and withdrawal. Only eligible offers can become executable resolution bindings. Resolution MUST preserve all C-01–C-06 semantics: namespaces, exact offered versions, requirement ranges, hard constraints, optional omission, preferences, complete recursive dependency closure, conflict diagnosis, and explicit extension behavior.

Mandatory dependency cycles without a valid complete closure MUST fail; recursive search MUST NOT silently drop edges. Shared dependency bindings require compatible versions, tenancy, state-isolation, and multiplicity. Optional omission is recorded and cannot weaken a mandatory composite guarantee. Deterministic selection uses the complete recorded input snapshot and stable tie rules when required. Ambiguity without an authorized tie rule remains unresolved.

Binding provenance identifies requirement/configuration revisions, offer/Plugin activation versions, policy/evidence references, resolver rules, dependency closure, alternatives/omissions, and validity limitations. A binding reference is not a credential. Invokers revalidate current eligibility, tenant suitability, policy, authority, and resources. Re-resolution creates new evidence; replacing an in-flight provider also requires declared state/effect compatibility and any required migration.

## 8. Governed execution and representative flows

### 8.1 Common governed execution flow

```text
Application / authorized trigger
            |
 Verify Principal + TenantContext + input/work revision
            |
 Resolve or revalidate declared binding where needed
            |
 Bind immutable ExecutionContext; validate admission
            |
 Select optional driver: Direct / Workflow / Agent / Human / Service
            |
 Proposed protected operation
            |
 Current authorization + policy + validation + required guardrails
            |
 Required Approval? ---- yes ---> wait for attributed decision
            |                          |
            +<------ revalidate -------+
            |
 Resource admission + current deadline + approval-use arbitration
            |
 Record effect intent / dispatch through governed Port
            |
 Observe result: none / partial / completed / unknown effects
            |
 Reconcile resources + state + Artifact / provenance evidence
            |
 Operational result; optional separate work acceptance / Outcome
```

Authorization is evaluated at entry and again for each protected operation, not only once per attempt. Admission may permit waiting for approval, but the guarded effect cannot occur before approval; execution transitions remain those of SPEC §5.8. Decisions are action-specific and cannot be copied to unrelated operations.

ExecutionContext binds execution/tenant/Application identity, acting and originating Principal attribution, configuration/work revisions, Trace, policy/authorization references, resources, deadline, and provenance. Optional Team/Role/Goal/Task/Plan references are bound only when relevant. Mutable progress, balances, approvals, and health stay in owner-managed state. Child work gets its own identity and preserves inherited constraints. Current restrictions always apply; no checkpoint or historical decision is a perpetual grant.

### 8.2 Representative compositions

#### Direct capability execution

Application declares or references a capability requirement → scoped discovery/resolution → governed entry validates context and admission → direct driver invokes the selected capability Port → invoking plane records result/effects and resource use → Application receives operational result and optional ArtifactVersions.

This path has no mandatory Task, Goal, Organization, Team, Workflow, Agent, or Model. Evaluation, retrieval, Memory, Policy, and Model capabilities can each use it independently. Applicable governance and trace responsibilities remain present even for a small local composition.

#### Deterministic workflow

Application references a Workflow revision → Workflow driver creates governed Execution and WorkflowState → eligible Tasks, when represented, are assigned through Coordination → Tools, Services, or Humans perform steps under governed Ports → driver records joins, waits, and transitions → Artifacts and operational result are preserved → Work Coordination assesses a canonical Outcome only if accountable achievement was intentionally represented.

Workflow completion is separate from Task acceptance and Goal achievement. Branch errors and unfinished work follow declared join/cancellation semantics. An all-deterministic workflow requires no Agent or Model; a human step can be an ordinary planned step.

#### Single-agent execution

Application selects an Agent behavior revision → Agent driver binds a governed attempt and explicit state → approved Context/Skills and optional Model calls inform decisions → Agent proposes actions → Action Mediation authorizes, validates, and performs Tool effects → results and ArtifactVersions return through governed references → Agent reports completion evidence.

The Agent controls proposals within its autonomy bound, not policy enforcement, approval consumption, or resource accounting. Model-generated instructions and retrieved text remain untrusted. An Agent behavior need not use a language model.

#### Team / delegation execution

```text
Application intent → Organization-owned Goal
                           |
                 Plan / Team composition revision
                           |
            Roles → scoped Actor assignments
                           |
      Authorized delegator Actor / acting Principal
                           |
      Delegation: work + authority ceiling + policies
                  budget allocation + deadline + expectations
                           |
              Recipient Actor or Team acceptance
                           |
              Human / Service / Agent Executions
                           |
            Governed actions → versioned Artifacts
                           |
                  Evaluation / acceptance evidence
                           |
              Team-owned canonical Outcome assessment
                           |
             Separate Organization Goal assessment
```

Work Coordination validates Role eligibility and staffing independently from authorization. A Team delegate accepts through a stated authority and identifies Actors for actual work. The delegator MUST be an attributable Actor, even when acting for a Team. Further delegation preserves the chain, inherited policies, resource reservations, and deadline. An independent supplementary grant cannot be inferred from membership or delegation.

#### Human approval

Proposed effect → Policy declares Approval requirement → Approval Management pins action, target, revisions, evidence, approver eligibility, use bounds, and expiry → authenticated Human receives authorized decision context → explicit decision is recorded → invoker revalidates current authority, policy, action identity, scope, resources, and deadline → Approval Management arbitrates permitted use → effect dispatch proceeds if all obligations still hold.

Silence, timeout, generated text, and delivery acknowledgment are never human consent. Changed action content requires a new request. Rejected/expired requests cannot be reopened; new proposals create new records. Used approvals cannot be replayed beyond their scope/count.

### 8.3 Retry, checkpoint, cancellation, and effect uncertainty

Execution Coordination owns retry eligibility and new attempt identities; invoking planes own facts about effects. Retries share inherited deadlines and applicable cumulative accounting. A failed Task is not reopened by retrying an Execution; Coordination applies SPEC §5.7 replacement semantics.

For checkpointed capabilities, a checkpoint pins compatible state, definitions, bindings, and effect references. Before resuming, the owner verifies integrity/availability, state compatibility, live grants and revocations, approval applicability, Secret validity, remaining resources, and deadlines. It MUST NOT restore copied balances or replay completed non-idempotent effects. An attempt with prior effects MUST retain them and MUST NOT be labeled as never-started rejection. The ambiguity in SPEC §5.8 is carried as R-03; resume revalidation failure can use the permitted suspended → failed transition while preserving prior-effect evidence.

Cancellation coordinates drivers and invokers, prevents new work under cancelled/revoked scope, and tracks in-flight effects. A late success cannot erase a cancellation decision; nor can cancellation erase a completed effect. The owning module resolves state races using expected revisions and records late/uncertain effects separately.

Unknown effects require reconciliation, safe deduplication with a declared equivalence contract, or an authorized intervention decision before potentially duplicating harmful actions. Compensation is a new action with its own resources, authority, effect identity, and failure conditions. No universal rollback or exact replay guarantee is implied.

## 9. Resource and deadline coordination

**AR-18.** Resource Admission and Accounting MUST establish one authoritative claim against each applicable allocation/window/limit before admitting consumption. All concurrent allocations and consumption MUST preserve B-01–B-04. This is a consistency requirement, not a choice of lock, transaction mechanism, or shared database.

A reservation identifies scope, resource dimension/unit, amount or permitted uncertainty bound, parent allocation, work/effect identity, validity, and reconciliation status. Admission checks all applicable tenant, Application, delegation, shared-provider, and per-action restrictions. Partial admission across multiple resource dimensions MUST not dispatch the action until the whole required set is covered; unused claims are released through their owners.

For delegated allocation, the implementation MUST declare one of the SPEC-permitted modes: exclusive reservation, coordinated shared accounting, or authorized transfer. Allocating child capacity makes that capacity unavailable for incompatible parent/sibling claims. Parent aggregation MUST count the same capacity once: child spending consumes its reserved/transferred envelope; it is not added again as an independent charge on top of the full unreduced reservation. Releasing unused capacity reconciles the parent only after outstanding obligations are known.

For example, with a parent allowance of 100 units, two children requesting 70 each cannot both receive independent 70-unit authority. One may be admitted and the other refused/waited, or an authorized rule may allocate different amounts. A child finishing 40 units of an exclusive 70-unit allocation releases at most the remaining 30 after unresolved charges are settled. It cannot refund the incurred 40 by retrying, cancelling, or changing Actor.

Usage observations include actual/estimated/unknown status, units, source, and correlation to the reservation/effect. Duplicate reports MUST NOT double-charge; missing reports MUST NOT automatically refund unknown consumption. Reservation expiry MUST NOT free capacity that may already have incurred unreported effects without reconciliation or an explicitly authorized accounting decision. Uncertain external charges require an approved uncertainty/overrun policy; otherwise the operation cannot claim a guaranteed hard bound.

Deadline propagation takes the effective parent/child restrictions and records any authorized change. Waiting, delegation, retries, and provider replacement do not reset time or quota windows. Execution Coordination performs controlled waiting/stopping; invokers check deadlines before effects; accounting records time consumption where applicable. Clock precision, measurement windows, and reconciliation tolerances remain Q-06/Q-07 contract questions.

## 10. Trust, tenant, artifact, and event boundaries

### 10.1 Trust boundary map

```text
User / external event / Human decision
                  |
       [identity, input, tenant admission boundary]
                  v
              Application
                  |
       [runtime admission / authority boundary]
                  v
         Governed runtime composition
          /               |                \
 [model boundary]  [plugin boundary]   [action boundary]
        |                 |                  |
   Model Port       admitted provider     Tool Port
        |                 |                  |
        +---- [tenant-to-shared-use] ---+ [external-system boundary]
                                      |          |
                               shared realization / external system

Human → [approval identity + action scope + eligibility] → Approval
Every data/effect crossing retains tenant scope and causal evidence.
```

| Crossing | Enforcement owner and required controls |
|---|---|
| User → Application | Application ingress with Governance verifies identity/Principal, scope, input validity, disclosure permissions, and attribution; user text is not governing configuration |
| Application → Runtime | Execution entry verifies current authority, TenantContext, pinned work/configuration, binding eligibility, policy/resource feasibility, and trace context |
| Runtime → Model | Model Interaction verifies data disclosure/use conditions, capability/input limits, current authority/resources, required output validation, and version/usage evidence |
| Runtime → Tool | Action Mediation enforces current authorization, policy, approval, input validation, resource/deadline claims, effect classification, and sandbox requirements |
| Runtime → Plugin | Extension admission plus invoking Port boundary verifies exact admitted contribution, health/suitability, trust/isolation obligations, and restricted authority; admission alone does not authorize calls |
| Tool → External System | Tool realization and Action Mediation enforce target scope, Secret use, permitted effects, request equivalence, result validation, and uncertain-effect reporting |
| Tenant → Shared Provider | Tenant Governance and invoking plane verify scoped use, no state/credential leakage, source/destination transfer permissions, and separate accounting/data contexts |
| Human → Approval | Approval Management verifies Human identity, eligibility, presented action revision, explicit decision, expiry, and permitted consumption |
| External Event → Application | Event ingress authenticates source where required, validates version/scope/content and duplicate handling; Application separately authorizes triggered execution |

The same boundary requirements apply whether calls are local or remote. **AR-19.** An admitted Plugin with direct access to host state can invalidate logical enforcement if it is not sufficiently trusted or isolated. Trust admission MUST establish that the selected realization can enforce its declared boundaries; otherwise activation/use MUST fail. No isolation technology is chosen here, and logical modularity alone is not a security proof.

### 10.2 TenantContext propagation

| Path | Required preservation and validation |
|---|---|
| Application execution | Bind exactly one verified tenant; single-tenant use still has explicit context |
| Workflow branches / resumed execution | Preserve parent scope and references; never recover another tenant's checkpoint |
| Agent state / model input | Preserve data classification and scope through observations, prompts, and outputs; no implicit cross-tenant learning/retention grant |
| Team / Delegation / Actor assignment | Keep membership scope separate from grants; child work inherits bounds; external participation uses explicit authorized Principals |
| Memory / Context | Scope storage, summarization, recall, and source metadata; summaries do not remove restrictions |
| Retrieval / Knowledge | Filter content and existence metadata before disclosure; source/recipient rules both apply |
| Artifact | Preserve owner/tenant/version and content visibility; import/export retains original provenance and separately governed destination use |
| Event / Message | Scope routing, payload references, deduplication keys, and delivery metadata; receiving tenant text is not trusted context |
| Trace / Audit / Provenance | Scope observation access and correlation traversal; shared collector implementation does not grant shared visibility |
| Evaluation | Scope cases, subjects, outputs, evaluator use, and release evidence; offline execution is not exempt |
| Plugin / Provider | Separate published definitions from operational configuration, memory, credentials, state, and budgets for each use |

**AR-20.** Cross-tenant operations require the explicit grants and both-source-and-destination policy approval of S-11. Ordinary child work preserves its tenant. If an authorized crossing starts destination-tenant execution, it MUST be a distinct admitted execution with explicit crossing evidence and causal linkage, not replacement of the parent's TenantContext. Co-owned cross-tenant operational entities remain unsupported under Q-02.

Shared implementation MAY reuse public definitions and non-private resources under policy, but MUST NOT equate shared code, batching, caches, or physical custody with shared tenant state. Any retained/intermediate data, deduplication key, configuration, health diagnostic, or result projection MUST preserve the isolation and disclosure guarantees of its contract. Data access restrictions also apply to metadata and error details.

### 10.3 Artifact flow

Producer invocation → attributed content/result → Artifact Management validates owner, tenant, type, stable content reference, version, policy, retention, visibility, and provenance → version record is preserved → Evaluation and Approval evidence are collected when required → authorized publication decision → consumers receive pinned versions → derived products add validated lineage references.

A content write alone is not publication. A failed metadata/publication step after content production records an incomplete obligation and reconciles it without repeating the producing external effect. Availability claims MUST be truthful. Aliases may change only through authorized revisioned decisions; approvals, evaluations, and derivations retain pinned versions.

Retention/disposition is Artifact Management's coordinated operation using current Governance decisions and content-preservation obligations. Holds, references, data deletion obligations, and audit retention may conflict; A-03 requires escalation without treating blocked deletion as permission for indefinite retention. Content unavailability is explicit; permitted tombstones preserve identity without forbidden data.

### 10.4 Event flow

Source owner commits an attributable fact → Event Coordination accepts an authorized versioned Event → scoped delivery attempts → consumer validates source/version/tenant and records handling identity → consumer requests governed work if needed → normal execution/effect admission → handling/result evidence links to original causation.

The source owns fact identity; Event Coordination owns delivery attempts; the consumer owns deduplication and handling semantics; an invoker owns effect equivalence. Deduplicating receipt does not prove effect deduplication. Delayed, duplicated, out-of-order, and missing events follow declared capability/profile guarantees. Retried delivery retains fact identity and separately identifies delivery attempts. Poisoned/invalid input is retained only as permitted diagnostic evidence and cannot repeatedly bypass admission.

No mandatory broker, total-order mechanism, or delivery topology is implied. Event-native and synchronous compositions share the same governing contracts.

## 11. Plugin lifecycle, activation, and replacement

### 11.1 Activity diagram and canonical state mapping

```text
Discover → Inspect → Validate / Admit → Configure / Initialize
                                              |
                                           Activate
                                              |
                                       Observe health
                                              |
                        +---------------------+------------------+
                        |                     |                  |
                  Continue use        Suspend use / stop     Upgrade request
                                              |                  |
                                       Revalidate/reactivate   New version:
                                              |              full admission
                                              +--------+---------+
                                                       |
                                             Drain / stop / retire
```

These are management activities, not newly defined Plugin states:

| Activity | SPEC §5.12 mapping and owner obligations |
|---|---|
| Discover / Inspect | `discovered`; inspect declared identity, versions, contributions, configuration, dependencies, and trust evidence without granting execution authority |
| Validate / Admit | `discovered → validated` only when compatibility, dependencies, configuration prerequisites, policy, tenant suitability, permissions, and required conformance evidence pass |
| Configure / Initialize | Bind validated configuration; `validated → initialized`; initialization side effects remain admitted and governed, failure becomes failed |
| Activate | `initialized → active`; publish eligible offers with exact activation references |
| Health | Observe freshness; `active ↔ degraded` only as defined; a degraded contribution is eligible only while it satisfies requirements |
| Suspend use | Revoke/withdraw eligibility for new use and coordinate `active/degraded → stopping → stopped`; dependent executions may independently enter their permitted suspended states. There is no new Plugin `suspended` state |
| Reactivate | `stopped → initialized` through a new validated activation record, then active; historical bindings are not silently refreshed |
| Upgrade | Admit and activate a new Plugin version, explicitly rebind new work, and migrate or drain old work under declared compatibility; upgrade is not an in-place state rewrite |
| Retire | `stopped → retired` or other unused-version retirement paths explicitly allowed by SPEC; preserve historical interpretation and outstanding obligations |

### 11.2 Admission and active use

Plugin admission MUST validate offered/required Capability and Port compatibility, specification ranges, required permissions, trust evidence, configuration, tenant/data suitability, dependency closure, and conformance evidence when policy requires it. Provider claims alone do not establish these facts. Unknown mandatory requirements prevent admission. Built-in contributions have the same descriptive and governance obligations as extensions.

Activation is bound to a configuration and scope; shared definitions do not make tenant-specific activation data public. A Plugin cannot publish itself as eligible outside Lifecycle's admitted record. Catalog visibility and executable eligibility are different. Invokers verify exact active contribution versions and current suitability rather than trusting a stale registry projection.

### 11.3 Bootstrap and dependency activation

**AR-21.** Dependency **assessment** for admission MAY inspect inactive declared contributions, but MUST NOT produce an executable CapabilityResolution binding to them. Dependencies needed to initialize a contribution must already be admitted and usable before dependent initialization. Lifecycle orders activation over a validated dependency graph; ordinary selection observes active eligible contributions only. Unsupported activation cycles fail explicitly.

The smallest host composition needs established identity/scope, policy enforcement, lifecycle control, and evidence/accounting responsibilities appropriate to admitting extensions. These bootstrap realizations are explicitly declared and admitted under accountable administrative authority; they are not self-trusted plugins. They implement the same applicable contracts and built-in contribution obligations. Administrative authority and initial trust establishment belong to SECURITY/GOVERNANCE; their physical packaging is an ADR concern.

Control-plane operations themselves are attributable governed operations with scoped Principals, context, policies, and applicable resource/evidence requirements. This MUST NOT trigger infinite resolution to start the resolver, or recursive authorization to authorize the same unresolved decision. Bootstrap uses explicitly established contract realizations and records the boundary of that trust. Additional capabilities use ordinary resolution and admission.

### 11.4 Replacement and isolation

Replacement MUST preserve the consumer's contracted guarantees, current policy, tenant separation, resource obligations, and provenance. A new provider version does not imply state compatibility. Migrations follow SPEC V-08 and require explicit source/target mapping, validation, loss/reversibility declaration, and affected-work treatment. Outstanding effects/charges remain attributed to the original version.

Stopping prevents new work while existing work is drained, cancelled, or explicitly migrated. Health loss cannot silently route work to a weaker, more privileged, or less isolated provider. A shared provider failure can affect multiple tenant uses, but notifications and diagnostics MUST disclose only authorized scope. Logical module separation does not guarantee failure or memory isolation; admission must match the actual isolation guarantees available.

## 12. Failure architecture

Canonical failures originate at the boundary that can explain their meaning. Adapters translate implementation failures before exposing canonical results. They MUST preserve category, affected action/subject, attribution/correlation, safe cause references, effect status, and recoverability under SPEC §10.

| Origin | Principal canonical categories | Propagation responsibility |
|---|---|---|
| Definition/context/transition validation | ValidationError, Conflict, VersionMismatch | Owner rejects invalid change without corrupting prior state |
| Catalog/resolution | CapabilityUnavailable, CapabilityResolutionError, VersionMismatch, Conflict | Preserve unsatisfied/conflict/ambiguity/invalid details; no executable complete binding on non-success |
| Tenant/identity/authorization boundaries | TenantViolation, AuthorizationDenied | Stop protected disclosure/effect; do not leak inaccessible resource details |
| Policy/guardrail/approval checks | PolicyViolation, HumanRejected | Explicit human rejection remains distinct from timeout/expiry or unavailable decisions |
| Resource/deadline checks | BudgetExceeded, DeadlineExceeded | Report dimension/scope and known usage/effect uncertainty; no retry reset |
| Tool dispatch / external realization | ToolFailure | Preserve none/partial/completed/unknown effects; coordinate reconciliation before unsafe retry |
| Model invocation / output contract | ModelFailure | Distinguish invocation-contract failure from completed low-quality output assessed by Evaluation |
| Plugin initialization/health/lifecycle | PluginFailure | Withdraw unsuitable eligibility, coordinate affected work, preserve safe cause/version evidence |
| Driver / dependent work | ExecutionFailure, DependencyFailure | Parent records child cause without hiding more specific policy/tenant/resource failures |

Artifacts, Memory, retrieval, event delivery, and evaluation failures use the most specific applicable canonical category; this architecture does not invent new exception types. Evaluation execution failure differs from a failing or inconclusive EvaluationResult. Cancellation is a lifecycle decision, not a synonym for every failure.

**AR-22.** Boundary translation MUST NOT turn timeout into proof of no effect, collapse security denial into a retryable generic error, or leak raw implementation diagnostics. Diagnostic detail may be retained under restricted policy. Parent aggregation keeps safe causal references and specific important categories. Recoverability depends on effect safety, current authority, resources, deadlines, and declared retry contracts, not on category alone.

Failures during observation/publication/accounting after effects create reconciliation obligations. A retry that only repairs missing evidence MUST be distinguishable from retrying the original action. No universal transaction or exactly-once execution guarantee is asserted.

## 13. Independently testable conformance boundaries

Every supported Port has a contract owner, semantic version, required behavior, optional features, lifecycle/error semantics, and governance/evidence obligations. A runtime MUST NOT be required to implement every Port. Small implementations conform to their declared supported scope and all applicable cross-cutting requirements.

| Surface | Independent evidence required for its supported scope |
|---|---|
| Model Port | Input/output behavior, advertised modalities/constraints, version attribution, usage, errors, disclosure/tenant controls; no Agent/Workflow prerequisite |
| Memory Port | Memory-kind behavior, update/recall/forgetting, revision/retention, access/isolation, declared consistency |
| Retrieval Port (RetrieverPort) | Source-scoped queries, pre-disclosure filtering, result lineage, ranking meaning, freshness/error behavior; no Agent/generation dependency |
| Tool Port | Input/effect contract, external enforcement, approval use, idempotency/unknown effects, compensation limits, accounting |
| Workflow Port | Valid transitions, waits/human steps, branch joins, failure/cancellation, and checkpoint guarantees when offered |
| Agent Runtime Port | Explicit bounded state, action proposals through governance, pause/recovery where offered, no authority from generated content |
| Artifact Port | Stable identity, immutable content versions, content-location independence, lineage, publication/access/retention/disposition |
| Event Port | Scope, immutable fact identity, version/cause preservation, duplicate/order/delivery guarantees as declared |
| Evaluation Port | Pinned subjects/criteria/methods, pass/fail/inconclusive interpretation, attempt failure distinction, standalone consumption |
| Policy Port | Applicability/combination, current decisions, obligations, fail-closed mandatory checks, exception/revocation evidence |
| Identity / Tenant / Secret / Approval Ports | Verified scope, current grants/validity, no Secret leakage, explicit human decisions, bounded replay-resistant approval use |
| Resource admission/accounting boundary | Concurrent parent/child allocations, quota windows, duplicate/unknown charges, reserve/use/release consistency and deadline behavior |
| Capability Catalog / Resolution boundary | Scoped discovery, eligible snapshots, full closure, hard constraints, ambiguity, deterministic selection when required, no permission issuance |
| Plugin lifecycle boundary | Admission versus discovery, compatibility/configuration, active eligibility, governed initialization, withdrawal and migration |
| Observability / Provenance boundary | Attribution, evidence completeness, lineage integrity, sensitive-data minimization, independent retention, no private reasoning dependency |

**AR-23.** A conformance claim MUST identify implementation/release, SPEC and architecture versions, supported concepts and Port/Capability versions, optional features, extensions, declared profile versions, and evidence/limitations. Until named profiles are approved, implementations MUST state an explicit supported contract set rather than inventing an official certification. Profile design MUST not waive universally applicable tenant, authority, effect, or resource obligations.

Tests SHOULD include both independent Port behavior and composition failures: revocation between selection and effect, concurrent approval/budget claims, stale eligibility, missing audit obligations, duplicate events, unknown external effects, cross-tenant reference attempts, and migration with outstanding consumption. Replacement is demonstrated with different realizations of the same supported contract and preserved consumer semantics. Such evidence is future work; this document makes no implementation conformance claim.

## 14. SPEC Q-01 through Q-08 disposition

| Question | Disposition | Architectural decision / explicit owner and exit criterion |
|---|---|---|
| Q-01 — Operational result versus canonical Outcome | **Resolved by accepted direction** | AR-07 and §4.5 apply SPEC DEC-01: direct work needs no canonical Goal/Outcome or organizational composition. Representing accountable achievement intentionally adds the required Team/Organization ownership. No source amendment is made here. |
| Q-02 — Cross-tenant organizational co-ownership | **Carried to GOVERNANCE and SECURITY; semantic extension requires SPEC** | §§4.5, 10.2 preserve one tenant per operational entity and explicit grants for collaboration. Exit: approved accountability/transfer model and, if joint ownership is desired, an explicit higher-level semantic amendment. Architecture cannot weaken S-02/S-10. |
| Q-03 — Namespace and certification authority | **Carried to GOVERNANCE, then CONTRACTS / CONFORMANCE** | Catalog and Plugin admission validate declared authority, not a chosen registry operator. Exit: named authority/delegation/registration rules, extension vocabulary ownership, and certification authority; contracts then define interoperable references. |
| Q-04 — Named conformance profiles | **Carried to CONFORMANCE** | §13 establishes surfaces and claim content, not universal feature bundles. Exit: versioned minimum supported sets, evidence requirements, optional features, and limitations for each approved profile. |
| Q-05 — Policy and retention conflict authority | **Carried to SECURITY and GOVERNANCE** | Governance owns decisions; protected actions fail closed on unresolved mandatory conflicts; Artifact disposition follows A-03. Exit: precedence, exception authority, emergency controls, and timely retention-conflict resolution rules. |
| Q-06 — Metering precision and uncertainty | **Architectural ownership resolved; parameters carried to CONTRACTS and GOVERNANCE** | Resource Accounting is authoritative; §9 prevents aggregate double-spend and unsafe refunds. Exit: units, time/measurement precision, reservation validity, reconciliation bounds, and authorized uncertainty/overrun rules. |
| Q-07 — Durability/order/recovery/retention levels | **Architectural boundaries resolved; profiles carried to CONTRACTS, CONFORMANCE, and SECURITY** | State/effect/event/evidence owners expose explicit guarantees; no universal ordering/replay promise. Exit: testable capability-specific recovery/delivery/retention guarantees and required profile combinations. |
| Q-08 — Cardinality defaults and vocabularies | **Carried to CONTRACTS and GOVERNANCE** | Existing SPEC cardinalities remain binding; blueprint expansion creates ordinary compositions. Exit: versioned Artifact type/relation vocabularies, blueprint/configuration meanings, and explicit defaults that do not contradict SPEC. |

No open question is resolved by selecting an implementation technology. The owners above identify responsibility, not authorization to create those documents during this task.

## 15. Risks, unresolved ambiguities, and decision boundaries

### 15.1 Newly exposed risks and follow-up

| ID | Risk / ambiguity | Architectural containment and follow-up |
|---|---|---|
| R-01 | Small Kernel decomposition could be read as removing responsibilities shown inside Kernel in intent §42. | §1.2 and §4.2 retain their semantic/contract anchors and delegate only implementations/state. Review this allocation explicitly; do not silently move domain meaning into plugins. |
| R-02 | Admission/resolution bootstrap can become cyclic, or inactive offers can accidentally become executable. | §11.3 separates inspection from binding, requires admitted bootstrap responsibility, and rejects unsupported cycles. SECURITY must specify initial trust establishment; CONTRACTS must define eligibility freshness. |
| R-03 | SPEC §5.8 allows re-admission after suspension but calls rejected work never-started. | §8.3 preserves prior effects and uses suspended → failed on resume validation failure. SPEC maintenance must clarify rejection guards for previously started attempts before recovery contracts are finalized. |
| R-04 | Separate authorization, approval, and resource checks can race or become stale before dispatch. | AR-17 requires owner-arbitrated claims and dispatch-time validation. CONTRACTS/SECURITY must specify freshness, consumption, and in-flight revocation semantics; a series of checks alone is insufficient proof. |
| R-05 | Plugin suspension/upgrade activities could silently add states absent from SPEC. | §11.1 maps activities to canonical states; no new suspended/upgrading Plugin state. Any broader lifecycle needs a SPEC change. |
| R-06 | A shared host may let an insufficiently trusted Plugin bypass logical boundaries. | AR-19 makes adequate trust/isolation an admission prerequisite; implementation ADRs must demonstrate enforcement and failure containment. |
| R-07 | Cross-module partial completion can lose artifact publication, accounting, or audit evidence after a real effect. | §§6, 8–10 retain operation/effect identity and reconciliation obligations; contracts must define recoverability/acknowledgment guarantees without assuming global atomicity. |
| R-08 | Mandatory evidence collection can recursively invoke its own governance or become a hidden availability dependency. | §§5, 11.3 separate established decision responsibilities from new work and distinguish required evidence from optional telemetry. SECURITY/CONFORMANCE must define minimum evidence and failure behavior. |
| R-09 | Accepted SPEC formatting/status defects obscure the open-question register in rendered form. | §1.2 records the unclosed fence and stale acceptance wording. A separate source-maintenance change should fix presentation/status without altering accepted semantics. |

These findings do not justify implementation work or a lower-level reinterpretation of SPEC. Higher-level semantic corrections must follow the project authority hierarchy.

### 15.2 Decisions deferred to ADRs

Reference-implementation ADRs MUST address, without changing the contracts established above:

- Reference implementation language and SDK languages.
- Web/API framework and external interaction representation.
- Agent runtime and workflow engine.
- Model providers and model realization choices.
- Database, cache, and content storage implementation.
- Event broker and delivery implementation.
- Vector/search infrastructure and retrieval realization.
- Protocol adapters and serialization technology.
- Observability implementation, audit retention mechanisms, and provenance realization.
- Policy engine and identity/security integration.
- Secrets implementation and isolation mechanisms.
- Container/deployment technology, physical distribution, and cloud platform.

No option is selected here. ADRs must state supported contract guarantees, conformance evidence, replacement/migration effects, and intentional extension use. Starting with a modular monolith preserves logical contracts; later distribution must revisit latency, failures, trust, consistency, and recovery without changing canonical meaning.

## 16. Traceability, self-review, and next document

### 16.1 Governing requirement coverage

| Source requirements | Architecture coverage |
|---|---|
| Intent §§3–11, 21–25, 38–42 | §§1–5, 7, 11: small stable contracts, Ports/Adapters, composition and replaceability |
| SPEC S-01–S-08, L-01–L-04 | §§4–6, 8, 11: identities, ownership, revisions, state/lifecycle operation |
| SPEC S-09–S-12, E-01–E-11 | §§3, 6, 8–10: enforcement, context, effects, recovery, scope, evidence |
| SPEC C-01–C-06 | §§4.3, 7, 11.3: discovery, matching, closure, constraints and extension boundaries |
| SPEC D-01–D-05, B-01–B-04 | §§4.5, 4.11, 8–9: bounded work delegation and aggregate accounting |
| SPEC A-01–A-05 | §§4.8–4.10, 10.3: content/identity, lineage, retention, policy and data integrity |
| SPEC ERR-01–ERR-02, V-01–V-09 | §§11–13, 15: error translation, replacement, migration and evidence |
| SPEC I-01–I-20, DEC-01 | §§4, 8, 13–14: independent modes, governance, accountability and conformance |

### 16.2 Final architectural self-review

| Question | Assessment |
|---|---|
| Can a non-Agent application use Lego AI? | Yes — direct capability entry (§8.2). |
| Can a non-language-model application use it? | Yes — deterministic and human/service paths (§§4.4, 8.2). |
| Can a human-only or service-heavy Team exist? | Yes — Role/Actor composition is independent of Agent (§4.5). |
| Can providers be swapped without domain changes? | Yes within compatible declared guarantees; extensions/migrations remain explicit (§§7, 11.4). |
| Can each major capability be tested independently? | Yes — module contracts and conformance surfaces (§13). |
| Is authorization separate from resolution? | Yes — four separate responsibilities (§7.1). |
| Is Tool execution externally governable? | Yes — Action Mediation and current boundary checks (§§4.6, 10.1). |
| Can tenants safely share provider implementations? | Yes where admitted isolation guarantees are demonstrated; state and scope remain separate (§10.2). |
| Are budgets safe under concurrent delegation? | Required — owner-arbitrated allocations, claims, and reconciliation (§9); implementation proof remains necessary. |
| Are Artifacts storage-neutral? | Yes — identity/version separated from content location (§4.9). |
| Are Trace, Provenance, Audit, and Evaluation distinct? | Yes — distinct responsibilities and owners (§4.13). |
| Can the architecture begin as a modular monolith? | Yes — no plane/module requires independent deployment (AR-08). |
| Can modules become services without changing semantics? | Yes if implementations preserve boundary guarantees; distribution adds explicit failure/trust obligations (§15.2). |
| Are implementation technologies deferred? | Yes — no products, protocols, representations, or runtime technologies are selected (§15.2). |
| Are Q-01–Q-08 all resolved or tracked? | Yes — individual disposition, owner, and exit criteria (§14). |

This review establishes architecture coverage, not verified runtime security, performance, or conformance. The source ambiguities in §15.1 remain explicitly tracked.

**Recommended next document:** `contracts/CONTRACTS.md`. It should inventory canonical Port interactions and operation semantics, bind inputs/results/errors to exact SPEC concepts, specify revision and acknowledgment rules, separate admission from effects, define concurrency and claim-consumption guarantees, and map each surface to future conformance cases. It should carry the SECURITY, GOVERNANCE, and CONFORMANCE questions forward by identifier and resolve the SPEC lifecycle clarification before finalizing recovery contracts. Representation choices and implementation technologies remain separate decisions.

The architecture phase ends with this document. No runtime, SDK, schema, Adapter, dependency, or deployment infrastructure is created by this deliverable.
