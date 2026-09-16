# Lego AI Operating Layer — Plugin Specification

**Plugin specification version:** 0.1.0  
**Status:** ACCEPTED — CANONICAL PLUGIN SPECIFICATION
**Authority:** [intent.md](../intent.md) 1.0 → [SPEC.md](../SPEC.md) 0.1.0 → [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) 0.1.0 → [CONTRACTS.md](../contracts/CONTRACTS.md) 0.1.0 → this document.  
**Scope:** Technology-neutral Plugin declarations, contributions, dependencies, compatibility, configuration, lifecycle operations, bootstrap, and evidence.

## 1. Authority and scope

**PLG-001.** This document MUST preserve the governing documents' definitions, cardinalities, state transitions, ownership, dependency directions, and observable contracts. SPEC §1 supplies normative language. Each operation and declaration below inherits the applicable shared rules in SPEC and Contracts. A lower-layer declaration cannot waive them. Any discovered contradiction MUST identify exact upstream sections and their owner, and only the affected behavior MUST remain unfinalized pending an upstream correction.

The accepted correction recorded as Contracts §1.1 HLC-01 is preserved: Intelligence does not directly invoke Evaluation. An authorized consumer allowed to depend on both orchestrates Model/Skill evaluations; Intelligence may reference existing authorized evidence. No new higher-level contradiction was identified in this review.

**PLG-002.** A conforming Plugin MAY be implemented or referenced using any realization that satisfies its declared contracts. No language, package manager, loader, linking mechanism, process arrangement, transport, discovery mechanism, registry product, marketplace, cloud, container, framework, SDK, or cryptographic technology is required here. Distribution, installation, physical packaging, and deployment are implementation concerns; none establishes activation, trust, or authority.

This document defines semantic properties and relationships, not canonical serialized fields, schemas, callable signatures, or storage records. Tables are normative semantic inventories. Conceptual examples carry the label **illustrative semantic structure — not canonical serialization**. Diagrams show responsibility and ordering constraints, not required protocols.

**PLG-003.** Requirement identifiers in this document use `PLG-###`. Tables inherit the enclosing requirements and cited Contracts families. A supported subset MUST identify its exact contract scope and meet all applicable cross-cutting obligations; it MUST NOT imply support for unrelated capabilities. Unknown required semantics MUST fail explicitly. An empty collection means no declared members only where zero members is permitted, never unrestricted permission or an undisclosed dependency.

## 2. Constitutional principles and canonical definition

Applications own Intent. Organizations own Goals. Teams own Outcomes. Roles define Responsibilities. Agents, Humans, and Services perform Roles. Skills provide Expertise. Tools provide Actions. Artifacts preserve Work. Policies bound Autonomy. Lego AI owns Contracts. Plugins provide Capabilities. Technology remains Replaceable.

**PLG-004.** A **Plugin** is a governed, versioned extension unit declaring contributions, requirements, compatibility, configuration, lifecycle behavior, trust and permission requirements, operational characteristics, and evidence. It MAY package or reference concrete realizations. It MUST NOT redefine canonical domain meaning, acquire governance authority through its declaration, or move implementation-specific assumptions into the Kernel.

Plugin is not an Actor, Service, Agent, Adapter, Provider, or deployment instance. A Service may expose a realization; an Agent runtime may be contributed; neither makes the Plugin itself a participating Actor. A Port is the stable interaction contract, an Adapter maps that contract to realization behavior, a Capability names ability, and a CapabilityProvider supplies versioned offers. These relationships do not collapse identities or owners.

**PLG-005.** Independent consumption MUST remain possible. A Model contribution does not require Agent support; Retrieval does not require generation; Tool use does not require a Team; Memory does not require vector storage; Workflow does not require an Agent; Evaluation does not require a Model; deterministic behavior does not require AI. A Plugin contributing one capability is valid. Applicable execution, governance, resource, and evidence responsibilities remain required without inventing Goal, Organization, Team, Workflow, or Outcome entities. SPEC DEC-01 governs operational results.

## 3. Identity, release versions, and accountability

### 3.1 Identity dimensions

**PLG-006.** Stable Plugin identity MUST comprise or unambiguously reference a namespace and local identity, with namespace authority and accountable publisher/source references. Each release binds an exact Plugin version. The accountable owner, publisher, source, and admission authority MUST be distinguishable; they may coincide only with independently valid authority evidence. Identity MUST NOT derive solely from a display name, package name, repository, executable path, artifact location, endpoint, or deployment address. Namespace changes and owner transfers require authorized mappings and preserved provenance, not silent identity reuse.

| Dimension | Meaning and independent identity |
|---|---|
| Plugin identity | Stable extension identity across releases; namespace plus local identity |
| Plugin release version | Immutable contribution definition and declarations for one release |
| Contribution identity/version | Release-owned descriptor of a supplied item; version pins its declared meaning |
| Capability identity/version | Independently governed ability and exact semantic guarantees |
| Provider identity/version | Realization offering one or more exact CapabilityVersions; owning Plugin release explicit |
| Adapter identity/version | Mapping realization; implemented Port versions are separate |
| Port identity/version | Stable behavioral boundary, including errors, lifecycle and governance |
| Configuration contract/version | Meaning and validation rules for configuration |
| Configuration instance/revision | Scoped bound settings used by a particular activation |
| Deployment instance | Optional realization placement/instance attribution; never canonical Plugin identity |
| Activation identity | Exact admitted use of a release, scope, configuration, dependency evidence, and lifecycle history |
| State revision | Owner-issued revision of mutable operational state, not a semantic release |

**PLG-007.** References MUST identify kind, identity, scope, and exact revision/version wherever execution or historical interpretation depends on them. A release can have multiple separately scoped activation records. Deployment relocation MUST NOT silently replace a bound activation or reinterpret historical references. Missing historical content is explicit unavailability, not permission to resolve an old reference to a new release.

```text
Diagram 1 — Identity and contribution relationships
namespace authority --> Plugin identity --> immutable release version
                                              |
                           owns 0..* contribution descriptors
                             /                |               \
                       Provider A         Adapter B        other realization
                       | 1..* offers      | implements          |
                       v                  v                     v
                 CapabilityVersion     Port version <---- declared boundary
                      (contract authorities own canonical semantics)
release --> activation A [tenant/config/dependencies/revision]
        --> activation B [tenant/config/dependencies/revision]
placement references remain independent of every identity above
```

### 3.2 Release evolution

**PLG-008.** Plugin versions MUST follow semantic major/minor/patch meaning and Contracts CTR-064: nonnegative numeric components, explicit prerelease qualifier where present, ranges with inclusive/exclusive bounds and prerelease handling. An unspecified prerelease rule excludes prereleases; incompatible prerelease ordering schemes require an explicitly shared interpretation. Initial 0.x releases are not implicitly compatible. No textual encoding is mandated.

**PLG-009.** Published release content MUST be immutable. Incompatible observable change requires a major semantic change; compatible additions may be minor; corrections preserving valid obligations may be patch changes. Removing a contribution or operation, narrowing accepted inputs, weakening errors, health, isolation, resource, effect, or recovery guarantees, or adding required permissions/dependencies without compatible behavior MUST be assessed as potentially breaking. A label such as correction cannot conceal a semantic break. Changes to deployment details that leave declared semantics unchanged still require attributable realization/configuration revisions when relevant to admission evidence.

**PLG-010.** Plugin version MUST NOT imply a matching Capability, Port, Adapter, Model, Tool, Skill, Workflow, schema, content-artifact, or deployment version. Compatibility is explicit per dimension. Deprecation MUST identify affected release/contributions, replacement or its absence, support expectations, migration guidance, and consequences for new and existing uses. Deprecation is release guidance, not an extra Plugin lifecycle state. Withdrawal of an offer and retirement of a Plugin are separate governed decisions; urgent withdrawal retains reasons and affected-work obligations.

## 4. Contributions, Providers, Adapters, and Ports

**PLG-011.** A Plugin release MAY own zero or more contribution descriptors. Each descriptor MUST identify exactly one owning Plugin release. Every Provider and Adapter contribution, including built-in realizations, MUST satisfy SPEC §3 ownership. Referencing an external dependency does not make it an owned contribution. A new release can contribute a new version of a logically related item without changing the old descriptor's owner or historical meaning.

Contribution ownership here is accountability for the release's declaration and realization. Canonical Capability and Port meanings remain with their contract authorities. Module-owned operational facts remain with Architecture §6.1 owners: a Plugin offering Artifact storage does not own Artifact identities; a Policy evaluator does not own its admission policy; an accounting realization does not let arbitrary Plugin code edit budgets.

**PLG-012.** Each contribution MUST declare the following semantics directly or by exact governed reference. Required collections may be empty only with the indicated applicability meaning.

| Declaration | Required meaning |
|---|---|
| Identity, kind, version, owning release | Stable scoped descriptor; kind describes the contributed role, not a new lifecycle |
| Implemented Ports and operations | Exact supported boundary versions, mandatory/optional features and unsupported operations; non-executable assets identify their asset interaction contract; no fictitious execution Port |
| Provided CapabilityVersions and offers | Exact identities/versions and Provider relationship; empty if not advertised as a capability; each Provider still has 1..* offers |
| Configuration | Contract and defaults/constraints or explicit no-settings contract; activation settings remain separately scoped |
| Dependencies | Complete stage-specific requirements, optional omission and selected closure; empty only when none beyond inherited host obligations |
| Tenant constraints | Permitted use scope, data-transfer and shared-state assumptions, isolation requirements |
| Resources | Startup/use/migration/stop needs, units, uncertainty, limits and accounting responsibilities, or explicit no additional resource requirements |
| Trust and permissions | Required evidence/control properties and requested actions/resources/purposes; requirements are not decisions or grants |
| Health | Observable scope, freshness, failure effects and mapping to contribution suitability |
| Limitations | Known unsupported guarantees, failure domains and reproducibility/recovery bounds; explicit none-known is an assertion, not proof |
| Extensions | Explicit required/optional namespaced semantics or empty set |
| Conformance evidence | Attributed claim/evidence references, applicable versions and limitations; empty/unverified when no evidence exists, never implicit certification |

The inventory can describe CapabilityProviders, Adapters, Tools, Models, Skills, Workflow and Agent Runtime realizations, Memory, Knowledge, Retrievers, Evaluators, Event, Artifact, Policy, Guardrail, Secret, Human Approval, Sandbox/isolation, and other declared contract realizations. These are contribution roles; this specification does not create a parallel Plugin subtype hierarchy. SPEC's required Plugin `type` remains descriptive, versioned and extensible, and MUST NOT switch off lifecycle or governance rules.

**PLG-013.** An Adapter MUST preserve its Port's inputs/results, canonical error categories, acknowledgment meaning, effect uncertainty, current authority checks, tenant attribution, resource conservation, lifecycle obligations, and trace/provenance references. Mapping limitations MUST be declared before admission and matching. Matching shape or successfully loading a realization is insufficient conformance evidence. Consumers depend on the Port; implementation facilities stay behind it. Other canonical capabilities are consumed only through declared governed dependencies permitted by Architecture §5.2.

**PLG-014.** Provider identity MUST remain distinct from Plugin identity. A release may own multiple Providers and Adapters with different offers, configurations and eligibility. Multiple offers do not automatically imply shared state, permissions, aggregate guarantees, or multi-provider selection. SPEC §3's one selected Provider per atomic requirement applies unless the requirement explicitly declares a set and its aggregation semantics.

A composite Plugin MAY span multiple capability families and Ports. It MUST retain independent contribution identities and compatibility declarations, explicitly describe dependencies between contributions in the same release, and disclose failure propagation through shared realization state or resources. An Adapter MAY expose multiple compatible capabilities where declared. Co-packaging cannot hide a dependency or exempt an internal call from its governing boundary.

## 5. Requirements and dependency model

**PLG-015.** Requirements SHOULD target Capability, Port, and contract semantics rather than named implementation products. A hard dependency on a particular Plugin/contribution MUST explicitly identify the coupling, exact compatible versions, rationale, affected behavior, and portability impact; provider-specific meaning MUST use a namespaced extension. Merely listing a preferred Provider cannot turn a preference into a hidden hard requirement.

**PLG-016.** Each dependency MUST identify its owning declaration, target kind/identity and acceptable versions, required stage(s), mandatory/optional designation, hard constraints, multiplicity, configuration/context needs, applicable tenant/trust/permission/resource/isolation constraints, evidence freshness, and the consequences of absence or failure. Preferences, alternative acceptable behaviors, selected binding, and omission evidence MUST be distinguishable. Installation instructions cannot substitute for dependency semantics or authorize dependency execution.

| Category | Assessment and use stage | Mandatory meaning | Activation, health, and eligibility effect |
|---|---|---|---|
| Semantic | Inspection/validation: SPEC and behavioral Contracts | Required interpretation must be supported | Incompatible or unknown required meaning blocks admission/activation |
| Capability | Closure assessment; live selection at declared use stages | All hard guarantees for selected requirement must hold | Missing required closure blocks activation or affected use according to declared stage; no weakened fallback |
| Port | Validation of supported operation/boundary versions | Required behavior must be realizable | Unsupported required boundary blocks corresponding contribution and activation when required by release |
| Initialization | Before initialization dispatch | Already admitted and usable for its exact duty | Missing dependency prevents initialization; failure/effects retained |
| Runtime | Activation readiness and each affected invocation | Required conditions for declared operational guarantees | Loss prevents affected new use; existing work follows explicit continuation policy |
| Optional | At relevant assessment/use stage | Omission is expressly allowed with documented result | Omission recorded; selected optional dependencies must meet every hard constraint |
| Bootstrap | Host establishment, before dependent initialization | Explicitly admitted bounded duty, not ordinary inactive selection | Unestablished root or unresolved cycle blocks dependent work |
| Migration | Before a specific migration | Required only when undertaking that migration | Absence prevents migration; cannot use target with incompatible state; unrelated compatible fresh use may remain possible |
| Observability/evidence | Before/after actions according to governing policy | Required evidence cannot be recast as optional diagnostics | Missing mandatory pre-evidence prevents dispatch; post-effect failure creates obligation |

Configuration, Secret references, permission/trust requirements, resource guarantees, tenant characteristics and runtime characteristics are typed constraints in this model. Runtime characteristics describe required behavior or isolation/failure bounds, not a mandatory platform for all Plugins. Categories may overlap; stage obligations are cumulative.

**PLG-017.** Dependency assessment MUST expand a complete compatible closure, retain versioned edges and binding context, detect unresolved cycles, and expose conflicts. Silent truncation or dropping a mandatory edge is forbidden. A mandatory condition required for activation cannot be deferred by calling it a runtime dependency. Future action-specific inputs may be checked at invocation where the admitted contract expressly allows them; they do not establish current invocation authority at activation. A release MUST declare whether a failed contribution is essential to activation or an optional omitted contribution. Omission cannot weaken the remaining advertised guarantees.

An unresolved mandatory dependency in the admitted operational contribution set MUST prevent operational activation, including mandatory runtime capability dependencies. A conditionally needed migration dependency for an operation not being undertaken is not an omitted mandatory operational dependency. New action-specific authority and resource claims are checked at use even when the required capability closure is already resolved.

**PLG-018.** Reuse of a dependency across contributions or releases requires compatible versions, tenant/state isolation, multiplicity and resource accounting. Shared references do not copy grants or spendable balances. Different versions can coexist only under explicitly compatible isolation and state rules. An unresolved mandatory cycle yields CapabilityResolutionError with safe cycle evidence; subordinate execution failure retains DependencyFailure and specific causes. No inactive offer becomes executable through graph inspection.

## 6. Compatibility matrix

**PLG-019.** Admission MUST evaluate all applicable compatibility dimensions together, using exact candidates and evidence revisions. Numeric version overlap is necessary where declared but does not prove behavior, trust, isolation or recovery suitability. Unknown required compatibility blocks the affected admission/activation/use. Optional unsupported features may be omitted only with explicit safe omission semantics.

| Relationship | What is declared | Validator / authoritative decision | Failure meaning | Activation blocked? |
|---|---|---|---|---|
| Plugin ↔ SPEC | Supported semantic version ranges and concept scope | Lifecycle validation against accepted SPEC | VersionMismatch or unsupported required semantics | Yes for required semantics |
| Plugin ↔ Contracts | Supported document/family versions, operations and guarantees | Lifecycle with contract evidence | Incompatible requests/results/acknowledgments | Yes for required families |
| Plugin ↔ Port | Implemented exact versions and optional features | Lifecycle; Port conformance evidence from authorized assessment | Cannot preserve boundary obligations | Yes for required contributed behavior |
| Plugin ↔ Capability | Exact offers; required version ranges and constraints | Catalog validates declarations; Resolution matches; Lifecycle admits | Offer mismatch, missing ability, unsatisfied closure | Yes when necessary to activation; affected invocation otherwise |
| Plugin ↔ Adapter | Exact Adapter release, owner and Port mappings | Lifecycle with attributable evidence | Mapping incompatible or ownership invalid | Yes for affected required realization |
| Plugin ↔ Dependency | Stage, versions, complete closure, coexistence/failure rules | Lifecycle assessment; Resolution owns executable bindings | Unsatisfied/conflicting/cyclic dependency | Yes for required activation closure; later stage blocks that operation |
| Plugin ↔ Configuration | Contract version, constraints, bound instance revision | Lifecycle with scoped configuration authority | Invalid settings or incompatible interpretation | Yes until required configuration is valid |
| Plugin ↔ State Migration | Source/target state contracts, transformations, validation, reversibility | Each state owner; Lifecycle coordinates affected activation | State unsafe/incompatible; VersionMismatch | Yes for use of affected state; independent fresh activation only if expressly supported |
| Plugin ↔ Extension | Namespace/owner/version, requiredness, compatibility and portability | Lifecycle and consuming contract owner | Required meaning unsupported or overriding canonical behavior | Yes when required; explicit optional omission otherwise |

**PLG-020.** Compatibility evidence MUST state tested/assessed versions, configuration and environment assumptions, date/freshness and limitations. A changed realization, configuration, dependency closure, policy requirement, or isolation assumption MUST trigger assessment of evidence applicability. No release may inherit verification merely through a matching name or publisher.

## 7. Discovery, inspection, validation, and admission

**PLG-021.** Discovery MUST return scoped identity/version/source metadata and attributable provenance, including whether origin/integrity claims are asserted or verified. A new discovered record follows Contracts §26. Discovery does not imply installation, compatibility, trust, available code, activation or invocation permission. Metadata visibility is policy-controlled, including existence, dependency names, and diagnostics.

**PLG-022.** Inspection MUST expose authorized contribution, requirement, configuration, compatibility, lifecycle, health, limitation, extension and evidence semantics without executing activation callbacks or initialization effects. Query disclosure, metering and audit are governed under Contracts Q semantics. Inspection of unavailable realization metadata is valid when its provenance/availability limitations are explicit; a Plugin need not be active to be inspected.

**PLG-023.** Validation MUST assess identity/namespace authority, owning release, version interpretation, SPEC/Contract/Port/Capability compatibility, contribution consistency, stage-specific closure and cycles, configuration, Secret-reference requirements, permissions, trust, tenancy, resources, isolation, extensions, and policy-required conformance evidence. Findings identify exact subject/revisions, checks, assertions versus verified evidence, unmet conditions, safe causes and applicability. `validate_plugin` returns a report; it does not commit canonical `validated`, initialize, activate, grant authority or reserve invocation resources.

**PLG-024.** `admit_plugin` MUST be an accountable governed decision by Plugin Admission and Lifecycle using valid authority from Governance. For a discovered candidate it commits `validated` only after required checks pass, under expected revision. The admission record MUST bind Plugin identity/release, decision identity/revision, deciding Principal/authority, effective tenant or governed host scope, configuration contract and validated candidate revision, admitted contributions and Capability/Port scope, dependency assessment, trust/permission/isolation/resource constraints, evidence revisions, validity/reassessment conditions, exclusions, and provenance. Operational use has exactly one verified TenantContext; shared publication scope is not an operational wildcard.

Admission is neither unrestricted invocation authority nor a perpetual decision. Validated candidate configuration can be supplied by reference before formal configuration binding; the bound instance MUST match that validation or be reassessed. A Plugin-supplied validator may contribute evidence only through an already admitted governed realization; it cannot execute unadmitted code or decide its own trust. An implementation of Policy evaluation does not automatically control the authority governing its own admission.

```text
Diagram 2 — Discovery through activation
visible source --> discover --> discovered record --> inspect
                                                       |
                                   validate report + closure assessment
                                                       |
                    accountable admit decision --> validated
                                                       |
                         bind validated config --> initialize
                                                       |
                                                  initialized
                                                       |
                         recheck current conditions --> active
                                                       |
                                  separate Catalog publication obligation
No report, package installation, or admission alone performs activation.
```

## 8. Configuration and Secrets

**PLG-025.** A configuration contract MUST define semantic settings, requiredness, types/units, constraints, explicit defaults, supported extensions, allowed references, compatibility and change/migration effects. Provider-specific settings belong in that Plugin's configuration or explicit extensions, not new mandatory Kernel fields. Unknown required fields/semantics fail; unknown optional metadata may be retained only without behavioral meaning. Contradictory values or undefined defaults MUST NOT silently widen authority, disclosure or resources.

**PLG-026.** Configuration contract, scoped configuration instance, bound revision, environment assumptions and realization settings MUST remain distinct. Effective non-secret values MUST be pinned and attributable, including the origin and precedence of each applicable setting. Unresolved conflicts prevent binding. Configure is an operation, not a Plugin state. Active changes require a new admitted activation/version treatment under Contracts §26: stop/revalidate/reactivate the same compatible release or separately admit a new activation/release as appropriate. In-place mutation of pinned settings is forbidden. A release change is required when published semantic declarations change; a new configuration revision alone does not rename an unchanged release.

**PLG-027.** Secret requirements MUST identify reference kind, purpose, required/optional designation, allowed consumer, use/action scope, rotation expectations, validity/revision requirements and behavior on unavailable/revoked material. Public declarations, results, manifests and telemetry MUST NOT contain or require raw Secret material. Binding a reference is not authorizing its use. Current validity and purpose authorization apply at each protected use; a checkpoint, rollback or old configuration cannot restore revoked material. Rotation attribution records safe revision identifiers, not old values. Optional Secret absence must disable or omit the explicitly dependent behavior rather than fall back to broader credentials.

## 9. Permission, trust, and isolation declarations

**PLG-028.** Requested permissions MUST describe actions, resource/target scope, purpose, consumers, lifecycle stage, conditions, delegation needs if any, and necessity or optional feature dependence. A declaration is a reviewable requirement, not a Permission grant. Current authorization, inherited ceilings, applicable policy, approvals, tenant rules and resource bounds MUST still hold at dispatch. A publisher, owner, healthy status, selection, or active lifecycle cannot confer authority.

**PLG-029.** Trust inputs MUST describe source/publisher provenance, executable or dynamic-code behavior, sensitive-data handling, external communication/state mutation, network/filesystem access, privileged host functions, Secret access, tenant crossings, required isolation, shared-state assumptions, dependency trust and evidence limitations. Required versus optional access and affected operations MUST be explicit. These are declarations and evidence inputs, not final risk classes, accepted privileges, verified trust, or authentication decisions.

**PLG-030.** Isolation declarations MUST state required containment properties, threat/control scope, failure domain, concurrency/shared-state assumptions, privileged operations, external-access bounds, persistence/residual effects, and verified versus claimed guarantees. If an admitted realization cannot demonstrate required boundaries, activation or affected dispatch MUST fail. Logical modularity or sharing a host is not proof of safe isolation. No sandbox, credential, network enforcement, or security-root technology is selected. A confinement realization remains governed and cannot promise reversal of effects already released outside its boundary.

## 10. Canonical Plugin lifecycle and operation mapping

**PLG-031.** Plugin lifecycle MUST be exactly SPEC §5.12. Its states are `discovered`, `validated`, `initialized`, `active`, `degraded`, `stopping`, `stopped`, `retired`, and `failed`. The following is the complete permitted transition interpretation; no table below adds an edge.

| Source | Permitted target | Guard / meaning |
|---|---|---|
| discovered | validated | Authorized admission after complete required validation |
| validated | initialized | Governed initialization with bound configuration and already usable initialization dependencies |
| initialized | active | Activation checks complete |
| active | degraded | Authorized lifecycle decision based on declared conditions |
| degraded | active | Validated restoration; no automatic resurrection of prior failed work |
| active or degraded | stopping | Block new work and coordinate existing-work disposition |
| stopping | stopped | Declared stop postconditions satisfied with residual obligations explicit |
| stopped | retired | Governed retirement preserving historical interpretation |
| validated or initialized | stopped | Explicit cancellation on SPEC's allowed path |
| discovered or validated | retired | Unused-version retirement only |
| initialization attempt from validated | failed | Initialization failure; `initializing` is not a Plugin state |
| initialized, active, degraded, or stopping | failed | Attributable failure under declared contract |
| failed | stopping | Governed cleanup; not direct restart |
| stopped | initialized | Only through a new validated activation record and governed reinitialization |

**PLG-032.** Inspect, admit, configure, health observation, offer publication, suspend use, upgrade, migration and rollback are operations/records/orchestrations, not additional lifecycle states. No `installed`, `configured`, `admitted`, `upgrading`, `suspended`, `paused`, or `quarantined` Plugin state is introduced. Installation metadata may be recorded outside this lifecycle. Suspend use changes eligibility and follows stop/reactivation semantics; dependent Executions independently use their permitted SPEC states.

Owner-local transitions MUST identify expected prior revision, authority/cause, guard evidence and produced revision. A failed command does not automatically put its subject into failed. Concurrent stop, degradation, retirement and activation requests cannot overwrite each other through last-arriving updates. Stopped reactivation preserves the old activation history and records the newly validated activation; retired records are never reopened.

## 11. Initialization and activation

**PLG-033.** Initialization MUST use exact validated admission and configuration references, already admitted usable dependencies, and current permission/trust/tenant/isolation/resource/evidence/deadline conditions. Initialization effects, including allocating resources, opening external state or disclosing data, require ordinary governed dispatch under Contracts §6. Required initialization effect/equivalence identities, cancellation boundaries, cleanup, recoverability and uncertainty MUST be declared. Initialization is not a trusted callback exempt from enforcement.

If initialization times out after possible effects, record unknown for uncertain components and keep outstanding charges/cleanup obligations. Failure may commit `failed`; it does not prove no effect. An initialization operation may remain pending while its outcome is investigated without creating an `initializing` lifecycle state. A second attempt cannot proceed merely because the first acknowledgment is absent.

**PLG-034.** Activation MUST verify the initialized revision, current admission/configuration applicability, full required activation closure, contribution health/suitability, trust/isolation, permissions, tenant/resource conditions, mandatory evidence, and required conformance evidence. The Lifecycle owner commits active and exact activation references. Catalog offer publication is a separate owner-local operation and acknowledgment. Active may therefore coexist with an incomplete publication obligation; it MUST NOT be reported as all contributions visible or eligible.

No contribution is ordinarily eligible before activation. A release with omitted optional contributions MUST expose the admitted subset and omission reasons. An active contribution cannot exceed the admitted subset merely because its code supports additional functions. Every invocation still validates its exact current binding, action and governing claims.

## 12. Health, eligibility, bindings, and offer publication

### 12.1 Health and degraded use

**PLG-035.** Health observations MUST identify Plugin/activation and affected contributions, observer/source, observation and recording times, state `healthy`, `degraded`, `unhealthy`, or `unknown`, freshness/time uncertainty, observed conditions, scope, evidence, limitations and impact on declared guarantees. Per-Plugin aggregation MUST declare its meaning and not hide an unhealthy mandatory contribution. Stale evidence cannot establish a required current health predicate; a recent timestamp does not verify an untrusted assertion.

**PLG-036.** Observation alone MUST NOT change lifecycle, authority or offers. Lifecycle and Catalog owners perform separate revisioned decisions using health evidence. Degraded use is eligible only while all consumer hard requirements and current governance hold. A weaker alternative requires an explicitly acceptable requirement/fallback and new resolution where needed; no silent weakening of output, durability, isolation, permission or cost limits. Restoration to active requires valid evidence and revalidation, not merely removal of an alarm.

### 12.2 Contribution condition matrix

**PLG-037.** The following are observable conditions, not a new linear contribution lifecycle. A contribution can satisfy several simultaneously, with differing scope/time. Only existing Provider lifecycle states retain their SPEC meaning.

| Condition | Meaning | Authoritative source |
|---|---|---|
| declared | Exact release asserts a contribution and its requirements | Release descriptor under Lifecycle stewardship |
| inspected | An authorized query examined declared metadata | Inspection result; no activation mutation |
| validated | Identified checks/admission cover contribution/configuration/scope | Lifecycle validation/admission evidence; report alone distinguished |
| published | A specified description or offer revision has publication acknowledgment | Description owner or Catalog, explicitly named |
| visible | Requester may discover metadata at a stated observation | Catalog/access decision; not public to every tenant |
| eligible | Currently satisfies activation and matching constraints for stated use | Catalog status with authoritative Lifecycle/Governance evidence; Resolution checks consumer constraints |
| selected | Immutable Resolution chose exact offer/dependency closure | Capability Resolution |
| bound | Exact selection/configuration/activation associated with admitted work | Resolution plus consuming Execution binding owner |
| invoked | Governed invocation occurred or is in progress with effect evidence | Invoking plane; Execution owns attempt status |
| unavailable | Cannot currently meet relevant use conditions | Catalog Provider status and attributed cause; not a Plugin state |
| withdrawn | Offer/Provider removed from new selection via permitted transition | Catalog; retained history stays interpretable |

**PLG-038.** Eligibility MUST consider exact release/activation/configuration, implemented Port and Capability guarantees, complete dependencies, tenant suitability, current policy/trust/isolation, resources, health freshness, required extensions and evidence. Eligible is not selected; selected is not authorized. A historical Resolution MUST remain immutable when health, policy, configuration, trust, dependency or lifecycle changes invalidate reuse. New resolution creates a linked record and does not silently migrate running state.

**PLG-039.** Existing work referencing an unavailable contribution MUST receive the affected activation/offer/binding identities, reason/effective time, evidence freshness, impacted guarantees, new-work prohibition, in-flight effect status, continuation/drain/cancel options, state compatibility, resource liabilities and reconciliation route. The execution owner chooses permitted continue, wait, fail, re-resolve, drain or cancel behavior under current policy and contract. Continued work needs demonstrable current conditions; no stale permission is preserved by an old binding. No new Execution state is defined here.

```text
Diagram 3 — Health and re-resolution
attributed observation --> Lifecycle assessment --> active/degraded/failure decision
          |                        |
          +--------------> contribution suitability --> Catalog status revision
                                                    |
                           old Resolution retained; reuse checked
                                                    |
                 still satisfies? --yes--> separately governed invocation
                         |
                         no --> wait/fail/cancel or new Resolution
                                state/effect compatibility checked before replacement
```

### 12.3 Capability offers

**PLG-040.** Each offer MUST bind exact Capability identity/version, Provider identity/version, owning Plugin release and contribution, implemented Port/version/features, configuration applicability, guarantees/limitations, stage-specific dependencies, health evidence/freshness, tenant/resource/trust/permission/isolation constraints, extensions, conformance evidence and activation reference when asserting eligibility. Provided capabilities in the Plugin description MUST agree with these offers. A Provider assertion of capability name alone proves neither compatibility nor conformance.

**PLG-041.** Catalog owns registration, visibility and status; Lifecycle owns activation/health records. Registration may precede activation but MUST NOT establish ordinary eligibility. Publishing eligibility requires current authoritative activation evidence and the applicable Catalog revision checks. Provider transitions remain `registered → eligible ↔ unavailable → withdrawn`, with registered → withdrawn allowed. Withdrawing an eligible Provider first makes it unavailable. Retiring a Plugin does not retire the independently governed Capability contract.

Lost publication acknowledgment MUST be reconciled by querying/retransmitting the same equivalent Catalog operation within its coverage. It MUST NOT repeat initialization or create another external realization merely to repair Catalog state. A delayed publication carrying an old activation revision MUST NOT restore eligibility after stopping/revocation; the Catalog and invoker verify applicability, not arrival order.

```text
Diagram 4 — Publication, resolution, invocation
Lifecycle active revision --> Catalog register/update offer --> visible snapshot
                                                                  |
requirements --> Resolution [hard constraints + closure] <----------+
                         |
                  exact selected binding
                         |
Execution admission --> current eligibility + authority + ordered claims/evidence
                         |
                    governed Port invocation --> result/effects/provenance
Publication and selection are never grants.
```

## 13. Bootstrap and finite dependency roots

**PLG-042.** Bootstrap assessment MUST distinguish declared, inspected, validated, bootstrap-eligible and active eligible contributions under Contracts §§27, 29. Inspection may assess inactive descriptions but MUST NOT return ordinary executable bindings to them. Bootstrap-eligible means a host authority has already established and admitted a specific realization for a bounded duty and scope; it does not make an arbitrary inactive Plugin callable. Initialization dependencies MUST already be admitted and usable before dependent initialization.

**PLG-043.** A bootstrap declaration/host admission record MUST identify accountable authority and Principal, realization/contribution/version, applicable contracts, allowed duties/actions, verified tenant context, configuration, required dependencies, trust/isolation assumptions, resource/accounting and evidence duties, exclusions from general discovery, lifecycle/termination/replacement conditions, admission evidence and its validity. Bootstrap publication does not automatically expose general-purpose offers. Ordinary eligibility requires the normal activation/publication path.

**PLG-044.** The dependency and evidence obligation graph MUST terminate in explicitly admitted accountable roots with stated guarantees, failure behavior and scope. Unsupported initialization, authorization or evidence cycles MUST fail with safe cycle evidence. A Policy or audit Plugin cannot self-admit or invent an exemption for its own admission. Root authority and evidence sufficiency remain Security/Governance decisions; this specification declares the required inputs, not whom to trust. Acknowledging the bounded evidence duty does not recursively require another identical acknowledgment under Contracts CTR-061.

```text
Diagram 5 — Bootstrap dependency handling
accountable host authority established outside Plugin self-assertion
                 |
admitted identity / enforcement / lifecycle / evidence / accounting duties
                 |
inspect declared graph --> assess closure and cycles
                 |
already usable dependencies --> governed dependent initialization
                 |
normal activation --> separate eligible-offer publication

inactive A needs inactive B needs inactive A --> explicit unresolved cycle failure
No inactive inspection result becomes an executable ordinary binding.
```

## 14. Stopping, retirement, and retained interpretation

**PLG-045.** Stop MUST prevent new ordinary work under the affected activation and specify disposition of each in-flight invocation: drain, cancel, permitted migration, or outstanding reconciliation. The effective stop decision and competing dispatches MUST be ordered under Contracts §6; a stale Catalog projection cannot bypass stop. Cleanup/status reconciliation may remain permitted only under explicit bounded authority and resource/evidence obligations. Such cleanup is not renewed ordinary eligibility.

Stopped means declared stop postconditions are met; it does not claim all external effects, liabilities or independent records have vanished. A pending stop retains its actual canonical state/revision until the owner can acknowledge the transition. A late completion is recorded against its original work, not used to revive a stopped activation. Failed cleanup uses the permitted failed/stopping paths and explicit obligations; no forced stopped acknowledgment hides uncertainty.

**PLG-046.** Retirement MUST use only SPEC's permitted paths, prohibit new use, and preserve necessary historical interpretation through exact version/configuration/binding/effect/evidence references or governed tombstones with explicit unavailability. Retention follows applicable policy, including conflict escalation; it is not an indefinite retention exemption. Any remaining evidence, accounting or externally unresolved effects MUST have accountable owners and recovery routes independent of ordinary retired contribution selection. Retirement cannot delete another module's Artifacts, Executions or accounting. Retired Plugin history cannot be reopened; a later replacement requires a distinct allowed release/activation path.

```text
Diagram 6 — Stop and retirement
active/degraded --> stop decision --> stopping --> stopped --> retired
                         |                |           |
                  deny new work      drain/cancel    retain interpretation
                                     or migrate     and owned obligations
failed ----------------------------> cleanup via stopping
validated/initialized --> stopped [explicit cancellation]
discovered/validated --> retired [unused only]
stopped --> new validated activation record --> initialized --> active
```

## 15. Upgrade, coexistence, rollback, and migration

**PLG-047.** Upgrade MUST be an explicit orchestration adopting a new immutable release: discover/inspect, validate/admit, bind configuration, initialize using admitted dependencies, activate, publish eligible offers, explicitly re-resolve/rebind permitted new work, and drain/stop/retire the old activation as appropriate. It is not an `upgrading` state or in-place rewrite. Each step retains its own operation identity, owner, revisions, acknowledgments, effects and incomplete obligations. Successful new activation does not imply successful old-version stop.

**PLG-048.** Version coexistence MUST declare permitted consumers, tenant isolation, state ownership/access, resource/concurrency sharing, dependency versions, offer selection constraints and deduplication/effect identity coverage. A default/current alias may change only through an authorized revisioned decision; pinned work does not follow it implicitly. Both versions cannot independently mutate incompatible shared state merely because they implement the same Port. If required coexistence guarantees cannot be established, use an explicitly governed drain/migration sequence before dependent target use.

**PLG-049.** Rollback means a new authorized selection or permitted reactivation of a prior compatible non-retired release with current validation/configuration/dependency/trust checks. It MUST NOT claim reversal of external effects, emitted events, published ArtifactVersions, approvals consumed, resource charges or state migrations. Prior release availability is not proof it can interpret current state. Irreversible migration or expired evidence may prevent rollback; reconciliation, compatible new migration or intervention is then explicit. Restoring a checkpoint cannot restore revoked authority or obsolete Secret validity.

**PLG-050.** Migration declarations MUST identify migration identity/version, source and target releases/configuration/state contracts, owning state modules, affected scopes and work, prerequisite dependency/authority/approval/resource/evidence conditions, transformation meaning, consistency boundary, loss and limitations, reversibility, validation/acceptance criteria, effect implications, expected revisions, deduplication/uncertainty guarantees, and recovery/partial-failure treatment. A no-migration-required claim MUST identify the compatibility evidence supporting it.

Plugin configuration is governed by Lifecycle; Provider-private state is behind its declared Port. Workflow, Agent, Memory, Artifact and other canonical state remains with its Architecture owner. Migration requests use those owners' contracts; Plugin ownership does not authorize direct state rewriting. Every migrated state binds a target revision and lineage while preserving tenant identity, old references, prior effects, outstanding charges and provenance. Target work MUST NOT consume incompatible or unvalidated migrated state. A partially migrated collection MUST identify which items are valid for which release; success cannot be inferred from a parent acknowledgment.

```text
Diagram 7 — Upgrade and coexistence
release A / activation A ---- existing pinned work ----> drain/stop A
         |                                |
         | explicit state-owner migration | original effects/accounting retained
         v                                |
release B --> validate/admit/configure/initialize/activate --> publish B
                                                          |
                          new compatible Resolution --> new work bound to B
Coexist only with explicit state/isolation/effect guarantees.
Rollback selects a compatible prior release; it does not reverse history.
```

## 16. Errors, retries, partial completion, and failures

**PLG-051.** Plugin operations MUST use exactly the canonical error categories and envelopes in SPEC §10 and Contracts §4: ValidationError, CapabilityUnavailable, CapabilityResolutionError, AuthorizationDenied, PolicyViolation, BudgetExceeded, DeadlineExceeded, DependencyFailure, ExecutionFailure, ToolFailure, ModelFailure, HumanRejected, Conflict, VersionMismatch, TenantViolation, PluginFailure. Use the most specific known category and safe cause chain; PluginFailure is not a wrapper that conceals authorization, tenant, policy or resource failure. HumanRejected requires explicit human rejection.

Every consequential result distinguishes operation disposition, Plugin lifecycle, acknowledgment stage and effect statuses `none`, `partial`, `completed`, `unknown` for identified effects. Recoverability is `terminal`, `potentially retryable`, `requires intervention`, or `unknown`; category alone does not permit retry. Timeout and missing acknowledgment never prove none.

**PLG-052.** Every mutation/effectful lifecycle, publication or migration operation MUST use Contracts §§5–6 identity/equivalence and expected-revision rules. It MUST declare deduplication scope, retention horizon, covered failure domain, status-query route, relevant effect identities, uncertainty treatment, and retry/deadline/resource bounds. Equivalent replay returns the prior authorized outcome without reapplying a committed mutation. A new execution attempt retains cumulative restrictions and the same intended effect identity when relying on deduplication. Changed configuration, input or target is not equivalent merely because the Plugin name matches.

**PLG-053.** Unknown initialization, migration, stop or external effects MUST be reconciled, safely retransmitted within demonstrated end-to-end equivalence coverage, or held for an authorized intervention before potentially duplicating harmful effects. Deduplication expiry does not make retry safe. Current access controls apply to retained results; denying their disclosure does not erase their effects. Resource liabilities remain outstanding until reconciled or explicitly settled by their owner; compensation is new governed work, never deletion of history.

**PLG-054.** Cross-owner operations MUST expose Contracts CTR-056 outstanding obligations: identity, owner, requester/Principal, tenant, parent operation/effect, required action/target revision, due/retention bound, guarantee, pending/satisfied/failed/requires-intervention condition, last evidence/error, next safe action and reconciliation authority. Owner-local commits are preserved even when the parent operation is incomplete. Global atomicity, universal exactly-once effects, total ordering and perfect durability are not implied.

| Failure scenario | Required behavior / safe recovery |
|---|---|
| Lost acknowledgment or duplicate mutation request | Query same operation identity; equivalent replay returns prior commit within coverage; no repeated initialization |
| Initialization succeeded, activation or publication failed | Retain initialized/active state as actually committed, effects and liabilities; repair only missing stage after current checks |
| Active committed, audit acknowledgment lost | Retain active fact and unknown audit custody; reconcile same evidence identity; mandatory pre-evidence must already have been established |
| Migration completed, old Plugin stop failed | Preserve migrated state and actual old activation status; enforce coexistence restrictions and track stop obligation; no automatic reverse migration |
| Provider timeout / unknown initialization effect | Preserve unknown effect and possible usage; reconcile or hold, not blind retry |
| Catalog unavailable | Publication incomplete; no assumed visible/eligible offers. Existing valid binding use requires independently verifiable current conditions; otherwise wait/refuse |
| Audit unavailable | Missing mandatory pre-evidence prevents protected dispatch. Post-effect failure creates obligation. Optional diagnostics may report a gap |
| Resource owner unavailable | No new consumption without verifiable valid claims/joint ordering; copied balances cannot admit work |
| Dependency fails | Reassess impacted contributions, stop affected new use, preserve causal error/effects; no implicit weaker dependency |
| Stale health | Required current predicate unsatisfied; obtain valid evidence, wait/refuse or explicitly re-resolve |
| Partition or disconnected stale participant | No stale authority/claim evidence used for new dispatch; preserve local facts and uncertainty for reconciliation |
| Late stop/effect completion | Expected revisions preserve authoritative lifecycle; append late effect/usage evidence, never resurrect activation |

```text
Diagram 8 — Partial activation
initialize --> initialized acknowledgment [effects recorded]
activate   --> active committed at Lifecycle owner
                   |                    |
                   v                    v
             publish offer        record audit evidence
             Catalog timeout      acknowledgment lost
                   |                    |
             publication obligation + evidence-custody obligation
                   |                    |
          query/reconcile SAME owner operations under current authority
No repeated initialization; no claim that all owners committed atomically.
```

## 17. Tenant scope, resource governance, and shared realization

**PLG-055.** Shared Plugin definitions may have explicit publication scope and custodian. Each operational activation/use MUST have one verified tenant scope, separately attributable configuration, Secret references, state, permissions, resource accounting and evidence access. Shared code, caching, batching, infrastructure or physical custody MUST NOT imply shared private state. Metadata, errors, deduplication keys, health diagnostics, evaluations and provenance traversals obey isolation too. Cross-tenant co-ownership remains unsupported under Q-02.

**PLG-056.** Cross-tenant access MUST identify source/destination, resource/action/purpose, explicit grants, both policy decisions and transfer constraints. Preserve source attribution and a distinct destination use/copy or separately admitted destination Execution when applicable; never relabel a bound TenantContext. A Plugin's advertised multi-tenant support is a claim requiring relevant evidence, not authority for transfer or unrestricted training/retention.

**PLG-057.** Resource declarations MUST cover applicable initialization, ordinary operation, migration, health checking, evidence production and stopping/cleanup costs. Identify dimensions/units, precision/uncertainty, bounds versus estimates, concurrency/occupancy, external metering, reservation/reconciliation responsibility, deadlines, applicable shared-provider and tenant constraints, and exhaustion behavior. No universal tariff, currency, tolerance or resource ceiling is selected. Explicit no-additional-needs metadata does not waive the host's applicable metering/governance obligations.

**PLG-058.** Resource Admission and Accounting remains authoritative for allocations, claims and liabilities. Capability feasibility and Plugin cost estimates are not reservations. Concurrent children/versions/tenants MUST NOT spend copied capacity; shared limits and tenant budgets both apply. Initialization failure, stopping, retirement, replacement or expiry MUST NOT refund consumed or unknown usage. Cleanup itself requires bounded authority/resources; inability to obtain them creates an explicit obligation, not an invisible emergency exemption. Joint validity at dispatch follows Contracts CTR-019–CTR-022.

```text
Diagram 9 — Shared realization, separate scoped uses
shared published Plugin release / replaceable realization
                 /                             \
    tenant A admission/activation       tenant B admission/activation
    config A + Secret refs A            config B + Secret refs B
    state A + accounting A              state B + accounting B
    evidence visibility A               evidence visibility B
                 \                             /
                  applicable shared capacity limits
Crossing A → B requires grants + both policies + distinct destination use.
Shared implementation does not merge tenant identity or private state.
```

## 18. Observation, provenance, and conformance evidence

**PLG-059.** Material discovery/validation/admission/configuration/lifecycle, health, offer, dependency selection, invocation, migration and retirement facts MUST be attributable. Preserve Plugin/release, publisher/source claims, contribution/Provider/Adapter/Port/Capability versions, activation/configuration revisions, Principal/tenant, operation/Execution/effect identities, observation/recording times, authority decisions, resource evidence, causal links, results, limitations and outstanding obligations as applicable. Private model reasoning, implementation internals and raw Secrets MUST NOT be required for conformance or indiscriminately logged.

**PLG-060.** Source owners retain authoritative decisions; Observation Collection owns trace/telemetry and Evidence and Provenance owns audit/general lineage. Artifact Management retains Artifact relationships. Required pre-evidence MUST declare class, owner, acknowledgment, persistence/recovery/retention guarantee and validity/deadline, and be established before dispatch. Required post-evidence has an obligation if recording fails. Optional telemetry cannot substitute for mandatory evidence. Historical evidence availability and governed tombstones are explicit; retaining an identifier alone is not a claim that its evidence remains accessible.

**PLG-061.** A conformance claim MUST identify claimant/assessor, exact Plugin/contribution/Adapter releases, SPEC/Architecture/Contracts/Port/Capability versions, supported operations and feature sets, applicable profile references or explicit supported set, extensions, configurations/dependency/environment assumptions, behavioral tests/evaluations, security/isolation assessment references when relevant, evidence times/freshness, limitations, failure domains and compatibility scope. Evidence applies only to its assessed subject and conditions. Unknown or stale evidence cannot satisfy a mandatory gate.

| Evidence qualification | Meaning; not interchangeable |
|---|---|
| Declared | Publisher/Provider asserts support; no independent verification implied |
| Verified | Identified assessor checked stated behavior under recorded conditions; scope and method explicit |
| Certified | A named entitled certification authority issued a scoped claim under an approved scheme; none is appointed here |
| Unknown | Adequate evidence/applicability is unavailable or not established |
| Stale | Prior evidence no longer satisfies stated freshness or changed-subject conditions |

**PLG-062.** Policy determines required evidence for admission/use; evaluations do not grant release or invocation authority. Claims MUST NOT invent official profile names, certification authorities or universal security assurance. Future Conformance dimensions include basic contribution, stateful, effectful, isolated, multi-tenant, bootstrap and durable behavior; these are independently applicable dimensions, not product tiers or mandatory bundles. Replaceability requires boundary behavior evidence, including failures, not just compatible declaration shapes.

## 19. Semantic manifest model

**PLG-063.** A Plugin declaration MUST provide the following semantic inventory, directly or by governed reference. This is not a prescribed file, schema or physical nesting structure. `R` means required, `C` conditional, `O` optional, `P` prohibited. Per-contribution requirements in §4 are cumulative. Presence does not imply verification or admission.

| Semantic property | Presence | Meaning and validation |
|---|---|---|
| Plugin namespace/local identity/version/type | R | §3 stable identity, exact release, descriptive type |
| Accountable owner, publisher/source, namespace authority | R | Distinct attributable references; authenticity status explicit |
| Metadata | R | Description and declaration provenance; safe metadata may be minimal |
| Provided and required capabilities | R | Explicit sets, possibly empty; offers/dependencies are consistent |
| Contributions | R | Explicit 0..* release-owned descriptors with §4 semantics |
| Configuration contract | R | Version, required/default/optional meanings; explicit no-settings contract valid |
| Compatibility | R | Required SPEC/Contracts/Port/Capability/Adapter/dependency dimensions and ranges |
| Lifecycle contract | R | Applicable canonical operations, effects, stop/recovery/retry guarantees and limitations |
| Health semantics | R | Observation scopes, freshness, impact, aggregation and unknown handling |
| Permissions and trust requirements | R | Explicit requested scope/evidence; empty requirements do not assert trust |
| Dependencies | R | Complete declarations with stages, constraints and optional omission |
| Tenant use and isolation characteristics | R | Scope/sharing and required guarantees; no wildcard operational tenant |
| Extensions | R | Explicit list, possibly empty; requiredness and portability per item |
| Resource requirements | C/O | Required when resources/guarantees affect admitted behavior; optional additional estimates; per-contribution applicability explicit |
| Secret requirements | C | Required when protected material is used; references/purpose only |
| Realization references | C | Required to identify the realization when participating; no mandated address/package syntax; an inspection-only candidate may declare unavailability |
| Migration/deprecation/replacement declarations | C | Required when advertised, needed for compatibility or withdrawing supported use |
| State/recovery/retention guarantees | C | Required for stateful/durable behavior and retained evidence claims |
| Bootstrap duty declaration | C | Required for proposed bootstrap participation; §13, not self-issued status |
| Conformance/integrity/publisher evidence | O/C | May be absent as explicitly unverified; required when an admission/consumer policy demands it; contribution evidence status always explicit |
| Labels, display names, documentation links | O | Advisory; cannot override canonical identities or rules |
| Raw Secrets, private reasoning, self-issued grants/trust | P | Forbidden public material or authority claims; no activation by declaration |
| Canonical override or hidden executable metadata | P | Unknown optional metadata cannot carry required effects or change higher-level meaning |

### 19.1 Minimal single-capability example

**illustrative semantic structure — not canonical serialization**

```text
Plugin identity: illustrative publisher namespace + text-normalizer
Release: major 1, minor 0, patch 0; type: deterministic contribution
Owner / publisher / namespace authority: explicit accountable references
Metadata: bounded deterministic text normalization; source provenance asserted
Compatibility: explicit supported SPEC and Contracts 0.1.0 semantic sets
Configuration contract: revisioned no-settings contract
Lifecycle: canonical Plugin lifecycle; initialization has no external mutation
Health: attributed availability observation with a consumer-checkable freshness bound
Trust / permission needs: host-reviewed bounded computation and result disclosure
Tenant/isolation: each use binds one tenant; no retained cross-request private state
Resources: bounded input size/work units; host resource policy supplies admitted limit
Required capability dependencies: empty; applicable governed host duties retained
Extensions: empty
Contributions:
  Provider P at its own version, owning release above
    one offer: illustrative normalization Capability at exact version 1.0.0
    Adapter A at its own version implements that capability's declared Port
    supported operation: normalize; bounded input and exact output/error meaning
    contribution configuration/dependencies/constraints reference declarations above
    evidence: declared, not verified; no official certification claimed
Activation/configuration-instance/Execution: absent from shared release description
```

The illustrative Capability/Port names and versions are explanatory placeholders, not new canonical contracts. Actual admission requires published valid referenced contracts and every policy-required check/evidence. This is one capability with its minimal Provider/Adapter realization; it adds no Model, Agent, Workflow, Team, Goal or Outcome. Its normalizer behavior would be defined by its own governed capability authority, not by this example. Zero-contribution descriptions are valid inspectable units but provide no selectable ability.

### 19.2 Explicit extensions

**PLG-064.** Each extension MUST declare namespace, owner, version, semantic purpose, applicability, compatibility, required/optional designation, omission behavior, and portability impact. Required unsupported semantics fail. Unknown optional extensions may be ignored only when explicit omission preserves all required behavior. Extensions MUST NOT override canonical fields, grant permissions, weaken tenant/resource/error/evidence obligations, silently change lifecycle, or make a provider-specific mechanism a de facto core requirement. Promotion to shared canonical meaning requires the normal upstream governance process.

## 20. Plugin operation matrix

**PLG-065.** Every row below inherits Contracts §§2–6, 26–29. **L** = Plugin Admission and Lifecycle; **C** = Catalog; **S** = respective state owner. Governance is **G**: current authenticated Principal, verified tenant, authorization/policy/trust/isolation checks applicable to the exact operation. It applies to every row, including access-controlled queries. **B** errors are all applicable canonical validation, version, revision Conflict, tenant, authorization, policy, budget and deadline errors; extra categories are listed without suppressing B.

Resource column **A** means evaluate applicable resource requirements and acquire owner-issued claims when required before consumption, or use explicit policy-permitted empty applicability. **D** means required dispatch claims and joint validity under Contracts §6 for the declared work, not merely feasibility. Every query may incur disclosure, usage and evidence effects even when it does not mutate its target. **ER** means expected revision per changed owner, expected absence for creation, and immutable original preconditions on duplicate replay. “Partial” refers to compound postconditions, not permission to claim an invalid state transition. Q/M/X/F retry classes have Contracts §5 meaning.

| Operation | Canonical state preconditions | Owner | Mutation? | Effectful? | Expected revision? | Dependencies required? | Governance? | Resource claims | Possible partial completion? | Canonical errors | Evidence produced |
|---|---|---|---|---|---|---|---|---|---|---|---|
| discover | No record for create; accessible record for query | L | Discovered record M; query Q | Record/disclosure | Absence on create | Metadata source, no executable candidate | G | A | Source/record acknowledgment uncertainty | B, PluginFailure | Source/release/visibility, discovered revision |
| inspect | Any accessible retained state/version | L | No target mutation Q | Disclosure/usage only | Pinned query revision | Metadata/evidence access | G | A | Incomplete evidence explicitly reported | B, PluginFailure | Exact description, assertions/limitations |
| validate | Exact candidate; no state transition | L | Report only Q | Assessment/disclosure | Candidate revisions pinned | Full stage-specific graph assessment | G | A | Incomplete checks are not pass | B, CapabilityResolutionError, PluginFailure | Checks, closure, unmet conditions |
| admit | discovered; stopped reactivation uses new validated activation record | L | validated admission M, or new reactivation admission record | Local decision | ER | Required admission closure/evidence | G | A | Decision commit and evidence custody distinct | B, PluginFailure, DependencyFailure | Authority, scope, config/graph/evidence revisions |
| configure | Candidate/admitted record; active change through new admitted activation treatment | L | Bound configuration M | Local binding | ER configuration and applicability | Config contract, required refs; Secret access separately authorized | G | A | Binding/evidence acknowledgments distinct | B, VersionMismatch | Effective revision, validation, origin |
| initialize | validated, or stopped through new validated activation | L; invokers own sub-effects | initialized or failed X | Declared init effects | ER activation and sub-effects | Already admitted usable initialization dependencies | G | D | Unknown/partial init and usage | B, PluginFailure, DependencyFailure | Init stages, effects, claims, cleanup obligations |
| activate | initialized | L | active M/X for declared effects | State; any extra effect governed | ER | Required activation closure/current suitability | G | A/D | Catalog/audit publication may remain incomplete | B, PluginFailure, DependencyFailure | Active revision, current checks, publication obligation |
| observe health | Identified activation/version; retained historical observation allowed | L | Evidence F, no implicit lifecycle | Observation/evidence; probes separately governed | ER for updated projection; new evidence identity | Declared observer/probe dependencies | G | A/D for probe | Missing/stale/unknown observations | B, DependencyFailure | Source/time/scope/freshness/limits |
| degrade | active | L | degraded M | State change | ER | Applicable health/impact evidence | G | A | Catalog invalidation obligation | B, PluginFailure | Affected guarantees and retained eligible subset |
| restore | degraded | L | active M | State change | ER | Renewed required closure/suitability | G | A | Offer/evidence repair separately tracked | B, PluginFailure, DependencyFailure | Revalidation and new state revision |
| stop | active/degraded/failed → stopping; stopping completion; validated/initialized cancellation → stopped | L plus effect owners | stopping/stopped or permitted failed M/X | Drain/cancel/cleanup effects | ER each owner | Existing-work/cleanup requirements | G | D where cleanup consumes | In-flight effects, usage, late completion | B, PluginFailure, DependencyFailure | Stop scope/order, work disposition, residual obligations |
| retire | stopped; discovered/validated if unused | L; C owns offers | retired M | State/disposition actions | ER | Historical-interpretation and obligation custody | G | A/D for disposition | Catalog/evidence/disposition obligations | B, PluginFailure, DependencyFailure | Retirement, retained references, exclusions |
| upgrade orchestration | Each release follows its own allowed path | L coordinator; other owners retain state | Multiple M/X/F operations, no upgrade state | Per sub-operation | ER per owner | Both closures, coexistence/migration requirements | G | D per effect | New active while old stop/publication fails | B plus sub-operation categories | New/old versions, bindings, per-step obligations |
| assess migration | Exact source/target and owned state revisions | S with L coordination | Assessment Q/M if recorded | No transformation yet | Pinned source/target; ER recorded assessment | Migration contract/dependencies | G | A | Missing evidence yields incomplete assessment | B, DependencyFailure | Compatibility/loss/reversibility/criteria |
| perform/validate migration | Permitted states of affected owners; Plugin lifecycle unchanged except explicit separate operations | S | State transformation X; validation Q/X as declared | State/external effects | ER each changed state | Already usable migration dependencies | G | D | Per-item progress, unknown effects | B, DependencyFailure, ExecutionFailure; specific causes preserved | Source/target lineage, validation, liability |
| offer publication/status | Registration before activation allowed; eligibility needs active or suitable degraded activation | C | Offer/status M | Local publication | ER offer + current activation evidence | Exact contracts, scope and freshness | G | A | Lost acknowledgment/stale publication rejected | B, PluginFailure, CapabilityUnavailable | Offer revision, eligibility evidence, custody |

Failure recording, cancellation, reactivation, withdrawal and retirement MUST remain within §10 and Contracts' Provider lifecycle. No generic row is authority to invent additional transitions. Migration and upgrade are compositions of existing owner contracts, not new universal runtime APIs.

## 21. Security concerns intentionally deferred to SECURITY.md

**PLG-066.** This document supplies reviewable declarations and required external decision boundaries. It MUST NOT establish trust roots, accept a Plugin as trusted, grant permissions, choose authentication/credential storage, decide acceptable privilege or appoint exception authorities. A declaration of an implementation's security requirement is an input to those decisions, not their outcome.

| Input provided to Security | Decision/evidence question for the next phase |
|---|---|
| Publisher/source and namespace authority references | How are identity, ownership, provenance and impersonation resistance established? |
| Trust requirements, integrity and evidence status | Which authority may admit this realization, under what validity/revocation conditions? |
| Requested permissions and stage-specific actions | Which privileges/purposes/targets are allowed, and who can approve exceptions? |
| Secret requirements | Who may authorize use, rotation and revocation without public material leakage? |
| Isolation/failure/shared-state requirements | What threat assumptions and demonstrable containment are required? |
| Resource requirements and uncertainty | What bounded use, enforcement, settlement and cleanup obligations are acceptable? |
| External access and code execution/dynamic loading | What boundary controls, disclosure restrictions and residual effects must be assessed? |
| Tenant characteristics and crossing declarations | What verified scope, separation and transfer evidence must be enforced? |
| Admission and conformance evidence | What assessor authority, freshness, coverage and failure handling satisfy gates? |
| Bootstrap responsibilities/exclusions and finite evidence graph | Who establishes initial duties/roots and their trust, and how is recursion prevented? |
| Dispatch ordering, health validity and outstanding obligations | What failure/revocation assumptions and evidence make current decisions defensible? |

Security/Governance, followed by appropriate ADRs, must decide trust roots, signature mechanisms, certificate formats, publisher reputation policy, allowed privileges, sandbox technology, credential technology, network policy technology, security classification levels and security exception authority. None is selected here. This separation does not postpone existing fail-closed authorization, tenant, effect, resource or evidence obligations.

```text
Diagram 10 — Inputs to Security
Plugin declaration + contribution requirements + attributed evidence
   | publisher/source | permissions | Secrets | isolation | resources
   | code/external access | tenancy | admission/conformance | bootstrap
   v
SECURITY / GOVERNANCE: threat model, authorities, trust and control requirements
   |
   v
attributable scoped decisions --> Lifecycle admission and protected-use boundaries
Plugin may supply evidence; it cannot appoint itself the deciding authority.
Mechanisms remain later choices with conformance obligations.
```

## 22. Open questions and inherited risks

### 22.1 SPEC questions

**PLG-067.** The dispositions below MUST remain traceable in later Security, Governance, Conformance, profiles and ADR work. “Resolved” concerns the stated semantic boundary only, not implementation proof. Open questions do not authorize weaker behavior.

| ID | Disposition in this layer | Next owner | Exit criterion |
|---|---|---|---|
| Q-02 | Unaffected; carried forward. Shared release and scoped uses do not add cross-tenant co-ownership (§17) | GOVERNANCE / SECURITY; SPEC for semantic expansion | Approved accountability/crossing model; explicit SPEC amendment before any true co-ownership |
| Q-03 | Partially resolved: Plugin namespace/publisher/owner and evidence references explicit (§§3, 18); authority not appointed | GOVERNANCE / SECURITY / CONFORMANCE | Approved namespace registration/delegation and certification-authority rules |
| Q-04 | Partially resolved: supported-set and evidence declarations plus independent dimensions (§18) | CONFORMANCE / GOVERNANCE | Accepted named versioned profiles and evidence requirements; no invented certification |
| Q-05 | Unaffected authority question; carried forward with scoped admission/retention obligations (§§7, 14, 21) | SECURITY / GOVERNANCE | Approved precedence, exception/emergency authority and timely retention-conflict resolution |
| Q-06 | Partially resolved: lifecycle-stage resource/uncertainty declarations (§17); parameters deferred | Resource CONTRACT profiles / GOVERNANCE | Approved domain units, precision, uncertainty/overrun, time and settlement parameters |
| Q-07 | Partially resolved: dependency/effect/recovery/evidence guarantees scoped (§§5, 16, 18) | CONFORMANCE / SECURITY / capability CONTRACT profiles | Testable required failure, ordering, durability, retention and retry-horizon guarantees |
| Q-08 | Partially resolved only for semantic Plugin inventory (§19); existing cardinalities preserved | CONTRACT vocabulary governance / GOVERNANCE | Approved needed vocabularies/representations without redefining core; unrelated blueprint/business types remain deferred |

### 22.2 Architecture risks

| ID | Disposition in this layer | Next owner | Exit criterion |
|---|---|---|---|
| R-01 | Unaffected/preserved: Kernel meanings remain upstream; contributions own implementations (§§2, 4) | ARCHITECTURE / GOVERNANCE / CONFORMANCE | Confirm allocation and demonstrate no core-to-concrete-Adapter dependency |
| R-02 | Partially resolved: stage graph, inactive inspection, admitted bootstrap duties and cycle failures (§§5, 13) | SECURITY / GOVERNANCE / CONFORMANCE | Approved initial trust admission and demonstrated finite bootstrap with current eligibility |
| R-04 | Contract solution preserved; Plugin operations inherit joint dispatch validity (§§11, 16, 17, 20) | SECURITY / CONFORMANCE / implementation ADRs | Concrete mechanism proves concurrency/revocation behavior for stated failure assumptions |
| R-05 | Resolved here for Plugin semantics: all activities mapped to SPEC states (§10) | SPEC if future expansion desired; CONFORMANCE for proof | No unlisted transition/state; explicit upstream amendment for any expansion |
| R-06 | Carried forward: explicit isolation and shared-host assumptions, no safety claim (§9) | SECURITY / implementation ADRs / CONFORMANCE | Required trust/containment established and tested against admitted threats |
| R-07 | Contract solution specialized: partial activation, migration, publication and stop obligations (§16) | CONFORMANCE / implementation ADRs | Failure evidence preserves facts and repairs records without duplicate original effects |
| R-08 | Partially resolved: finite evidence duties/dependency roots and pre/post-evidence (§§13, 18) | SECURITY / GOVERNANCE / CONFORMANCE | Approved roots, minimum guarantees, failure/privacy/retention behavior and termination proof |

### 22.3 Contract risks

| ID | Disposition in this layer | Next owner | Exit criterion |
|---|---|---|---|
| CR-01 | Carried forward: claim-owner unavailability blocks unprovable new dispatch (§16) | SECURITY / CONFORMANCE / ADRs | Demonstrated joint validity and explicit availability limits under partition/failure |
| CR-02 | Partially resolved: lifecycle/publication/migration replay scope and horizon required (§16) | CONTRACT profiles / CONFORMANCE / GOVERNANCE | Retention and maximum retry windows aligned; safe outside-horizon intervention demonstrated |
| CR-03 | Unaffected; consumed approval does not auto-refund after Plugin operation failure (§§16–17) | GOVERNANCE / SECURITY | Approved attributable new-entitlement process that prevents replay |
| CR-04 | Carried forward: safe metadata/error redaction with scoped evidence references (§§7, 16, 18) | SECURITY / GOVERNANCE | Approved diagnostic/reviewer access preserving tenant confidentiality |
| CR-05 | Partially resolved: exact release/configuration/evidence refs plus availability/retirement duties (§§3, 14, 18) | Evidence/Artifact CONTRACT profiles / SECURITY / CONFORMANCE | Demonstrated preservation bounds and truthful unavailable/tombstone behavior |
| CR-06 | Resolved at declaration boundary: publication/report/admission cannot imply activation (§§7, 10–12) | CONFORMANCE | Negative cases prove inactive registered offers never become ordinary eligible through generic publication |
| CR-07 | Partially resolved: explicit bootstrap/enforcement/evidence duties and cycle rejection (§13) | SECURITY / GOVERNANCE / CONFORMANCE | Approved bounded initial authority and demonstrated nonrecursive enforcement/evidence roots |

HLC-01 remains resolved upstream (Architecture §§4.7, 5.2; Contracts §1.1). No affected Plugin behavior is marked unfinalized by a new contradiction. Security-owned policy and mechanism questions remain deliberately open; they do not prevent defining the declaration and behavioral obligations here.

## 23. Plugin-specific risks

These risk labels are local review labels, not additional normative requirement namespaces.

| Risk | Containment here | Next owner | Exit criterion |
|---|---|---|---|
| Dependency explosion | Full closure and explicit stage/optional constraints; bounded resource/deadline behavior (§5) | Resolution CONTRACT profiles / CONFORMANCE / ADRs | Large/adversarial graphs terminate with truthful results within declared bounds; no silent truncation |
| Provider shadowing | Identity/version/owner evidence and explicit selection rules (§§3, 12) | GOVERNANCE / SECURITY / CONFORMANCE | Collision/alias/priority rules cannot silently replace pinned or preferred-by-policy Providers |
| Namespace impersonation | Authority references and asserted/verified distinction (§3) | SECURITY / GOVERNANCE | Namespace/publisher verification and transfer rules resist impersonation |
| Capability spoofing | Exact contracts, required evidence and independent matching (§§4, 6, 18) | CONFORMANCE / SECURITY | False offer claims rejected before protected use; evidence scope verifiable |
| Stale health evidence | Scoped timed observations and current reuse checks (§12) | CONTRACT profiles / SECURITY / CONFORMANCE | Freshness rules and partition cases prevent stale evidence satisfying hard predicates |
| Hidden implementation coupling | Contract-first dependencies and explicit extensions (§§4–5, 19) | ARCHITECTURE / CONFORMANCE | Substitute different realizations without changed domain behavior or expose explicit incompatibility |
| State migration incompatibility | State-owner validation, exact versions/loss and per-item progress (§15) | State-owning CONTRACT profiles / CONFORMANCE | Failure and irreversible migration cases cannot admit incompatible target state |
| Configuration drift | Pinned effective revision and new admitted activation treatment (§8) | Lifecycle CONTRACT profiles / CONFORMANCE | Changed runtime settings detected and reassessed; history unchanged |
| Partial activation | Separate authoritative state and obligations (§§11, 16) | CONFORMANCE / ADRs | Lost/failed steps do not create duplicate initialization or false completion |
| Contribution publication races | Expected revisions plus current activation applicability (§12) | Catalog CONTRACT profiles / CONFORMANCE | Late active publication cannot override later stop/revocation |
| Shared-host escape | Declared access/threat assumptions; no modularity-as-security proof (§9) | SECURITY / ADRs / CONFORMANCE | Admitted privilege/containment survives relevant adversarial tests |
| Trust bootstrap circularity | Explicit finite admitted duties, no self-admission (§13) | SECURITY / GOVERNANCE | Established authority/evidence roots and tested cycle refusal |
| Extensions becoming de facto core | Explicit optionality/portability and upstream governance (§19) | GOVERNANCE / ARCHITECTURE / CONFORMANCE | Baseline Port behavior remains independently usable without provider-specific extensions |
| Version coexistence conflicts | State/effect/resource separation and explicit migration (§15) | State-owning CONTRACT profiles / CONFORMANCE | Concurrent versions preserve state compatibility, deduplication and accounting |
| Silent guarantee weakening | Multi-dimensional compatibility and failure-aware replacement evidence (§§6, 15, 18) | CONFORMANCE / SECURITY / contract authorities | Replacement preserves promised errors, effects, isolation, resources and recovery, or is rejected |

## 24. Traceability

**PLG-068.** Future representations, release gates, conformance cases and ADRs MUST reference the applicable PLG requirements and their governing obligations. They MUST NOT claim a Plugin-wide waiver from a narrow optional feature. The matrix covers every PLG requirement; source references identify authority, not copied implementation design.

| Plugin requirements / concern | intent.md | SPEC.md | ARCHITECTURE.md | CONTRACTS.md |
|---|---|---|---|---|
| PLG-001–005: authority, neutrality, definition, modularity | §§3–11, 38–43, 47, 54–55 | §§1–3, 4.12, DEC-01, I-01/I-13 | AR-01–08; §§2, 5 | CTR-001–003, 028, 062 |
| PLG-006–010: identities, ownership, releases | §§21–22, 24, 40 | S-01–08, §3, V-01–09 | §§4.14, 6.1, 11 | CTR-004, 013–016, 063–065 |
| PLG-011–014: contributions/Adapters/Providers | §§5–10, 21–24, 54 | §§3, 4.4, 4.12, I-12 | §§4.2–3, 4.14, 5.2 | §§8, 26, 30; CTR-052 |
| PLG-015–018: requirements/closure | §§7–11, 22, 41 | C-01–06; §4.4 | AR-12/21; §§7, 11.3 | CTR-026, 054–055 |
| PLG-019–020: compatibility | §§24, 34, 40 | §11, S-05 | §§7, 11.4, 13 | CTR-052, 063–069 |
| PLG-021–024: discovery/admission | §§19–22, 35 | S-09–12, §4.12, §5.12 | §§4.14, 7.1, 11.2 | §§8, 26–27; CTR-051 |
| PLG-025–027: configuration/Secrets | §§8, 20, 35, 41 | S-05–08, E-02–03, Secret §4.9 | §§4.10, 11.2 | §§15.5, 26; CTR-040 |
| PLG-028–030: permission/trust/isolation | §§19–20, 29, 35 | S-09–11, E-03/06, A-05 | AR-19; §§10–11 | §§6, 15, 26.2; CTR-053 |
| PLG-031–034: lifecycle/init/activation | §§22, 24, 26 | L-01–04, §5.12, E-06–11 | §11 | CTR-051, 054–055 |
| PLG-035–041: health/eligibility/offers | §§7, 10, 22, 32 | §4.4, L-04, §5.12, C-03–05 | §§4.3, 7, 11 | CTR-025–026, §§26–27 |
| PLG-042–044: bootstrap/recursion | §§19–22, 35, 42 | S-09, E-06, C-03 | AR-12/21; §11.3 | CTR-054–055, 059–061 |
| PLG-045–050: stop/retire/upgrade/migrate | §§24, 26, 31, 40 | §5.12, L-02, E-09–11, V-07–08 | §§8.3, 11.4 | CTR-051, 056–058, 065 |
| PLG-051–054: errors/retry/partial failure | §§19–20, 26, 30–32 | E-06–11, §10, B-03 | AR-15–17/22; §12 | CTR-007–022, 056–058 |
| PLG-055–058: tenant/resources | §§29–30, 35 | S-10–11, B-01–04 | AR-18/20; §§9–10 | CTR-037–040; §§6, 15 |
| PLG-059–062: evidence/conformance | §§31–35, 46, 51 | S-12, §4.11, V-09, I-19/20 | §§4.12–13, 13 | CTR-049–050, 059–062, 066/068/069 |
| PLG-063–064: semantic manifest/extensions | §§8, 22–24, 39, 41 | §4.12, S-05, C-06, V-04 | §§4.14, 11 | CTR-005, 051, 063–067 |
| PLG-065–066: operation matrix/security handoff | §§19–22, 35, 47 | §§5.12, 6, 10 | §§6, 10–12 | §§2–6, 26–29 |
| PLG-067–070: dispositions/traceability/review/proof | §§34, 46–51, 55 | §§12–13 | §§13–16 | §§34–36 |

## 25. Conformance hooks

**PLG-069.** Each supported contribution MUST be independently assessable against its advertised boundary and applicable governance, without requiring unrelated subsystems. These are future proof obligations, not a test suite or evidence that any implementation already conforms.

| Dimension / case | Observable required result |
|---|---|
| Basic identity and ownership | Same release cannot change meaning; another namespace/publisher cannot silently shadow it; Provider/Adapter owns one release reference |
| Minimal and modular | Direct single-capability use works without Agent/Team/Goal; Model, Retrieval, Memory, deterministic Workflow and Evaluation can each omit unrelated dependencies |
| Admission authority | Plugin self-trust/permission/admission assertions never satisfy external decisions; Policy Plugin has no special exception |
| Discovery/publication | Inspection does not initialize; validate report does not activate; inactive published offer cannot become ordinary eligible |
| Dependency and bootstrap | Unknown required dependency or unresolved cycle blocks affected activation; optional omission recorded; admitted bootstrap duty cannot expand into general selection |
| Lifecycle | Every §10 transition guard holds; no installed/configured/upgrading/suspended state; stopped reactivation creates new validated activation evidence |
| Health and selection | Stale hard health predicate fails; degradation removes eligibility only for contributions/use constraints no longer satisfied; other use still requires all checks; old Resolution immutable |
| Stateful/migration | Target rejects incompatible state; explicit migration preserves tenant/lineage/prior effects; partial migration exposes actual per-item progress |
| Effectful/retry | Lost initialization/publication acknowledgment never blindly repeats original effects; outside deduplication horizon uncertainty remains; same operation cannot change input meaning |
| Claims/concurrency | Approval/resource/revocation race prevents dispatch without joint validity; consumed approvals not refunded by failure; duplicate reports not double-charged |
| Upgrade/coexistence | New release cannot rewrite old bindings; incompatible concurrent state users refused; rollback cannot claim reversed events/effects/costs |
| Stop/retire/durable | Stop forbids new work despite stale offer; late completions retained; history available within declared guarantees or explicitly unavailable; no retired reopening |
| Multi-tenant | Shared realization cannot mix config/Secrets/state/accounting/results or expose private metadata; transfer requires explicit grants and both policies |
| Isolated | Unsupported required containment blocks use; shared-host realization cannot claim safety solely from module boundaries |
| Replacement | Different Adapter preserves canonical errors, authority, effect uncertainty, usage and scope; weaker mapping fails compatibility |
| Extension | Unsupported required extension fails; optional omission cannot weaken hard guarantees or carry hidden authority |
| Evidence/durable | Mandatory pre-evidence unavailable prevents dispatch; post-effect evidence failure yields obligations; finite roots terminate; no private reasoning required |
| Security/evidence attribution | Declared differs from verified/certified; changed subject or stale evidence fails required gates; no invented certification authority |

## 26. Final self-review

**PLG-070.** This review establishes document coverage only. Implementation conformance and security assurance require the later evidence and decisions identified above. Future changes MUST repeat the applicable review and update affected traceability/dispositions.

### 26.1 Thirty-six required checks

| # | Check | Result / anchor |
|---|---|---|
| 1 | No technology-specific Plugin mechanism required | Pass — §§1–2 |
| 2 | No serialization format canonical | Pass — §§1, 19 |
| 3 | Plugin identity independent of package/deployment | Pass — §3.1 |
| 4 | Plugin version distinct from Capability/Port/Adapter | Pass — §3 |
| 5 | Plugin does not own canonical Capability semantics | Pass — §4 |
| 6 | Multiple capabilities allowed | Pass — §§4, 12.3 |
| 7 | Minimal single-capability valid | Pass — §§2, 19.1 |
| 8 | Discovery does not establish trust | Pass — §7 |
| 9 | Inspection has no activation effects | Pass — §7 |
| 10 | Validation does not activate | Pass — §§7, 10 |
| 11 | Admission not unrestricted invocation authority | Pass — §7 |
| 12 | Configuration changes revisioned | Pass — §8 |
| 13 | Raw Secrets never required in manifests | Pass — §§8, 19 |
| 14 | Permission requirements not grants | Pass — §9 |
| 15 | Trust requirements not trust decisions | Pass — §§9, 21 |
| 16 | Canonical SPEC Plugin lifecycle preserved exactly | Pass — §10 table |
| 17 | No invented installed/configured/upgrading/suspended states | Pass — §10 |
| 18 | Initialization effects governed | Pass — §11 |
| 19 | Activation differs from offer publication | Pass — §§11–12, 16 |
| 20 | Active differs from eligible | Pass — §12.2 |
| 21 | Eligible differs from selected | Pass — §12.2 |
| 22 | Selected differs from authorized | Pass — §12.2 |
| 23 | Health freshness-bounded | Pass — §12.1 |
| 24 | Degradation cannot silently weaken guarantees | Pass — §12.1 |
| 25 | Bootstrap cannot self-authorize | Pass — §13 |
| 26 | Unresolved dependency cycles fail explicitly | Pass — §§5, 13 |
| 27 | Upgrade adopts new release without rewritten history | Pass — §15 |
| 28 | Rollback not external-effect reversal | Pass — §15 |
| 29 | Migration explicit and versioned | Pass — §15 |
| 30 | Partial completion representable | Pass — §16 |
| 31 | Shared realization preserves tenant scope | Pass — §17 |
| 32 | Isolation declarable, mechanisms unspecified | Pass — §§9, 21 |
| 33 | Conformance evidence attributable/freshness-aware | Pass — §18 |
| 34 | Plugin cannot become own security authority | Pass — §§7, 9, 13, 21 |
| 35 | Existing Q/R/CR identifiers individually tracked | Pass — §22 |
| 36 | Clear Security input boundary | Pass — §21 |

### 26.2 Focused boundary reviews

| Review | Result and limits |
|---|---|
| Anti-coupling | No package manager, runtime loader, dynamic linking, containers, Kubernetes, Python entrypoints, Java ServiceLoader, npm, OCI images, REST, gRPC, MCP, A2A, registry server, marketplace, or cryptographic technology required. Any may later be a realization choice under unchanged semantics (§1). |
| Modularity | Model without Agent; Retrieval without generation; Tool without Team; Memory without vector storage; Workflow without Agent; Evaluation without Model; deterministic contribution without AI; one-capability release valid (§§2, 19). |
| Authority | Declaration ≠ trust; discovery ≠ trust; validation ≠ authorization; admission ≠ universal permission; activation ≠ invocation authority; active ≠ all eligible; selection ≠ permission; health ≠ authority; publisher ≠ security authority (§§7, 9, 12, 21). |
| Lifecycle | Inspect/admit/configure/upgrade/suspend use/migrate/publish/observe remain operations; canonical transitions explicitly enumerated (§10). |
| Distributed failures | Lost acknowledgments, duplicates, partial activation, timeouts, Catalog/audit/resource unavailability, dependency failure, stale health, partitions, late stop completion, unknown initialization covered with owner-local facts and reconciliation (§16). |
| Security boundary | No Plugin declared trusted, roots established, permissions granted, authentication chosen, sandbox selected, privilege accepted, or credential storage defined; decisions remain external (§21). |
| Replacement | Stateful and stateless replacements preserve current authority, tenant scope, effects, canonical errors, accounting and evidence; explicit migration where needed (§§4, 6, 15, 18). |

## 27. Next document and phase boundary

**Recommended next document:** `security/SECURITY.md`.

It should consume §21's declarations to define the threat model, accountable trust/admission authorities, namespace/publisher verification, identity and tenant enforcement, permission/Secret handling, isolation and failure assumptions, revocation/dispatch guarantees, finite bootstrap/evidence roots, confidentiality/retention, and security exception rules. It must carry §22's unresolved identifiers and §23's risks to their named owners without redefining accepted semantics.

This phase ends with this Plugin specification. No security policy, schema, package format, loader, registry, marketplace, SDK, Adapter, runtime, deployment, conformance suite, or ADR is created or selected by it.
