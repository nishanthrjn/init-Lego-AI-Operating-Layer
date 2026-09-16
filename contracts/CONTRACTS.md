# Lego AI Operating Layer — Canonical Behavioral Contracts

**Contract document version:** 0.1.0  
**Status:** ACCEPTED — CANONICAL BEHAVIORAL CONTRACTS
**Authority:** [intent.md](../intent.md) 1.0 → [SPEC.md](../SPEC.md) 0.1.0 → [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) 0.1.0 → this document.  
**Scope:** Observable semantic interactions, independent of language, representation, transport, and deployment.

## 1. Authority, scope, and reading rules

**CTR-001.** These contracts MUST preserve governing definitions, ownership, cardinalities, lifecycle states, authority, tenancy, and dependency direction. SPEC's normative vocabulary applies. A conflicting interaction MUST remain unfinalized until its higher-level owner resolves the conflict; the rest of the contract set MAY proceed independently. This document does not create runtime code, SDKs, schemas, wire messages, protocols, or a technology stack.

**CTR-002.** Each family is independently supported and versioned. Supporting one family MUST NOT require unrelated families. A direct Model or Retrieval consumer needs applicable execution context, governance, resource, and evidence behavior, not Team, Goal, Agent, Memory, or Workflow functionality. In-process, embedded, cross-process, remote, and distributed realizations MUST preserve the same observable semantics. Contract names and property labels below are semantic identifiers, not prescribed function signatures or serialized field names.

**CTR-003.** Normative requirements use unique `CTR-###` identifiers. Each operation row inherits the shared envelopes, ownership, errors, revision, retry, evidence, and dispatch rules unless an explicit specialization narrows them. An operation's complete contract is its row plus its family rules, shared rules, and relevant Port obligations. Aliases separated by a slash name related semantic operations, not a required combined endpoint. Unspecified operations are unsupported, not implicit permission to mutate state.

### 1.1 Higher-level observations and unfinalized interaction

### 1.1 Higher-level observations and resolved architectural issue

**HLC-01 — RESOLVED.** The previously detected conflict between Architecture §4.7 and the exhaustive dependency matrix in §5.2 has been resolved at the architectural layer.

Intelligence does not directly invoke Evaluation. Model and Skill behavior MAY be evaluated by an authorized consumer that is permitted to depend on both Intelligence and Evaluation. Intelligence MAY retain or reference existing authorized Evaluation evidence without introducing an Intelligence → Evaluation module dependency.

The corrected SPEC §5.8 and Architecture §8.3 forbid rejection of previously begun work. Recovery contracts use only canonical Execution states; intervention is represented as an obligation, recovery condition, or required external decision rather than as an additional Execution lifecycle state.

## 2. Shared identity, reference, and request semantics

### 2.1 Distinct semantic objects

| Term | Exact contract meaning |
|---|---|
| Identity | Stable designation of one entity or logical operation in a declared scope; never merely a display name |
| Reference | Typed, scoped locator by canonical identity, with revision when interpretation depends on it; not proof of access |
| Revision | Owner-issued identity of an authoritative state/definition observation; equality and ancestry only as declared, not assumed numeric ordering |
| Snapshot | Attributed collection of values/references observed at identified revisions/times with stated consistency; not current authority by itself |
| Claim | Owner-arbitrated, action-bound right to consume capacity/use or occupy an effect slot under §6; distinct from a caller's unverified assertion |
| Decision | Attributable conclusion about a stated question, inputs, scope, obligations, and validity; may deny or require conditions |
| Grant | Permission issued by an entitled authority, bounded by subject, action, resources, validity, and delegation conditions |
| Binding | Selected compatible provider/dependency association recorded by resolution; grants no invocation authority |
| Evidence | Attributed observation or reference supporting a claim/decision/result, with source, revision, trust and completeness; assertions are labeled as assertions |

**CTR-004.** Recipients MUST distinguish those objects. Supplying identifiers, snapshots, Role membership, provider selection, or asserted evidence MUST NOT impersonate a Principal, establish a TenantContext, issue a grant, or prove an effect. Reference resolution MUST preserve kind/scope/revision and access policy. No reference may silently resolve to another tenant or a different historical version.

### 2.2 Common request envelope

`U` = universally required for every operational request, either explicit or through a validated immutable envelope reference. `C` = required exactly when the condition holds. `O` = optional. `P` = prohibited as specified. Empty sets and explicit unbounded values have only the meanings assigned below; omission never means unrestricted access or spending.

| Semantic field | Presence | Meaning / validation |
|---|---|---|
| contract_identity, contract_version, operation_name | U | Identify supported semantic surface and exact operation/version; unknown mandatory semantics fail before effects |
| operation_identity | U | Identifies one logical requested operation; stable across retransmission, distinct from entity identity and execution retry identity |
| request_identity | U | Identifies one submission of that operation; retransmission of the same submission retains it; a new submission has its own identity and same operation identity only if semantically equivalent |
| correlation_identity | U | Links the interaction group; not authority or deduplication by itself |
| causation_reference | C | Required for triggered, subordinate, retry, correction, or reconciliation requests; explicit root designation for a root operation |
| tenant_context | U | Verified TenantContext or authoritative reference; ingress may submit a candidate scope only to its verifying boundary; operational use requires verified scope |
| acting_principal | U | Authenticated request initiator or established host/ingress Principal; MUST be validated, not selected by untrusted text |
| application_revision | C | Required for Application-originated work and every ExecutionContext; other administrative requests identify their governed owner context; no invented Application is required for mere inspection |
| execution_identity / ExecutionContext reference | C | Required for work invocation, effect dispatch, resource use, and execution evidence. Creation may supply a proposed identity subject to owner validation; admission/result binds the authoritative identity |
| parent_execution | C | Required for child attempts; origin and child identity are distinct |
| actor, role_assignment | C/O | Required when performing or claiming an assigned Role/Actor attribution; otherwise optional. Role version, scope, interval and Principal association must match |
| organization, team, goal, plan, task, delegation | C/O | Required if the operation or governing work uses them; otherwise optional and scope-checked. Plan/Task/work revisions are pinned. A Team is not an acting Actor |
| trace_identity | U | Existing trace/correlation reference or a request for receiving boundary to establish and return one; required evidence must be available before dispatch |
| subject_references / payload | C | Operation-specific subjects and semantically typed input; exact revisions where required by the row |
| expected_revision | C | Required for each existing authoritative mutable subject changed; owner-verified “absent” condition for creation. A map is used when several owner-local subjects participate |
| deadline | U | Explicit effective bound with time basis/uncertainty, or policy-permitted unbounded designation; descendants cannot silently extend it |
| budget / resource references | U | Applicable allocations, Quota windows, Limits, ResourcePolicy references, or explicit policy-permitted empty applicability set; balances are not trusted caller authority |
| policy_context | U | Applicable policy/authorization context reference and admitted ceiling where present; live authority rechecked. A caller cannot select only favorable policies |
| configuration_revision | C | Required when configurable behavior influences the operation; must pin governing non-secret configuration |
| extension_requirements | U | Explicit list, possibly empty, of namespace/version/required-or-optional semantics; unsupported required extensions fail |
| equivalence / effect references | C | Required for consequential operation deduplication, dispatch, retry, claims and reconciliation under §§5–6 |
| selection / guarantee requirements | C | Required when choosing provider multiplicity, consistency, recovery, delivery, or effect-equivalence guarantees beyond the base contract |
| advisory metadata | O | Safe labels/descriptions; MUST NOT affect authority or override canonical fields |
| raw Secret material / private reasoning | P | MUST NOT be required or included in public requests, artifacts of this envelope, or telemetry; protected identity-verification evidence uses a separately controlled reference |
| unrelated identity assertions / authority expansions | P | MUST NOT be used to fabricate Goal/Team participation, override scope, or enlarge admitted authority |

**CTR-005.** An owner MUST validate every applicable field before its protected operation. Fields may be inherited by reference only when immutable identity/meaning and current validity can be verified. A status query about an Execution names it as the subject; it MUST NOT pretend to act as that Execution. Unauthenticated external input is handled by an established ingress Principal which verifies the candidate subject; the candidate cannot self-establish authenticated status. Bootstrap follows §27, not an implicit wildcard context.

**CTR-006.** Errors on unverifiable input MUST carry safe receiver-assigned correlation/trace and untrusted-request correlation where safe; they MUST NOT copy forged tenant or Principal values as verified attribution. Failure to establish identity/scope prohibits operational mutation/disclosure except narrowly governed rejection/audit handling by the receiving boundary.

## 3. Result and acknowledgment semantics

### 3.1 Common result envelope

| Semantic field | Required meaning |
|---|---|
| result_identity / revision, responding owner | Required; identify this immutable observation and its authoritative source |
| request_identity, operation_identity, contract/version | Required; echo validated request association without implying authority from an unverified request |
| processing disposition | Required: pending, completed, failed, or refused at the **operation** level; these are result descriptors, not new domain lifecycle states |
| acknowledgment evidence | Required for each claimed stage; scoped as in §3.2; stages may be returned together |
| result payload / typed reference | Required on completed operation, including an explicit empty result where valid; may contain a negative domain judgment or unresolved resolution |
| authoritative subject state/revision | Required on mutation or state query; identify produced revisions and prior revision links, or explicit no-change result |
| effect observations | Required for consequential operations; identify each effect, observation time/source and SPEC effect status; explicit none of the intended effects when proven |
| ArtifactVersion references | Required for produced/preserved work products where applicable; empty when none produced, never a fabricated Artifact |
| resource observations / claims | Required when resources were reserved/used/possibly used; distinguish actual, estimated, outstanding/unknown and released amounts |
| policy / authorization / approval evidence | Required for material decisions and effects, under access policy; may be safe references instead of content |
| errors / warnings | Canonical errors required for failure/refusal; warnings optional and MUST NOT downgrade mandatory violations |
| provenance / audit references | Required for material decisions, mutations, and production; query provenance identifies source revision/freshness and safe access evidence |
| trace / correlation / causation | Required with validated tenant/owner attribution |
| observation time / completion time | Observation time required; completion time only for completed/failed/refused operation disposition, not an estimate of eventual business completion |
| outstanding obligations | Required when any postcondition/evidence/accounting/cleanup is incomplete; §28 defines content and responsible owner |

**CTR-007.** `completed` means the named operation's declared postconditions are met. A completed `request_execution` may only have created an Execution; a completed `resolve_requirements` may yield `unsatisfied`; a completed Evaluation may judge the subject failed. Execution status, acceptance judgment, effect status, and operation disposition MUST be separate. Results are observations; late evidence creates a new result linked to the prior observation rather than rewriting it.

### 3.2 Acknowledgment classes

Acknowledgments are evidence statements, not a universal linear protocol or entity lifecycle. Their scope MUST name the operation, subject, and owner. “Terminal” below means terminal for the **declared obligation**, not all surrounding work.

| Acknowledgment | Proves / does not prove | Terminal? | Can effects already exist? | Retry implication and required evidence |
|---|---|---|---|---|
| received | Boundary obtained the request / no validity, durable custody, authorization, or completion promised | No | Possibly, including earlier submission | Receipt identity/time; consult operation status, never infer safe retry |
| validated | Specified inputs/revisions passed identified checks / not current invocation authority or a reserved resource | Only for validate operation | Intended execution effects not caused by validation; earlier effects may exist | Validation scope/revisions/rules/time; repeated validation is permitted but may differ with current facts |
| accepted_for_processing | Owner accepted a handling obligation under stated custody/recovery guarantees / not admitted, started, or effectful work | Only for enqueue/request operation whose sole postcondition is custody | Possibly | Custody owner, operation reference, status-query route, guarantee; retransmit only under §5 |
| admitted | Execution or named action is eligible under identified checks/ceiling / not all future effect checks or approval fulfilled | Only for admission operation | Earlier effects may exist on re-admission | Admission decision, versions, bounds and state revision; does not authorize new independent retry |
| started | Named governed work began / not completion or particular external effect | No for executing work | Yes | Execution/state transition evidence; new Execution identity is a retry, not a retransmission |
| committed | Named owner accepted an authoritative state change at produced revision with declared persistence guarantees / not other owners' commits or external effect | Yes for that state mutation if its other postconditions are met | Possibly; committing a record is itself a local effect | Owner, prior/new revision, operation identity, content/equivalence evidence; same operation returns same commit without reapplying |
| effect_confirmed | Evidence establishes the named intended effect occurred to its stated extent / not all effects, local recording obligations, or business acceptance | Only for confirming that effect observation | Yes, by definition | Effect identity, target, action equivalence, observation/source, extent; never repeat merely for lost result |
| completed | Named operation's postconditions reached and result recorded under declared guarantee / not necessarily successful Evaluation judgment, Task acceptance, Goal achievement or whole parent completion | Yes for this operation | Any status consistent with its postconditions, including unknown for a status/reconciliation query | Final result, revisions, errors/negative judgment where applicable, effects and outstanding parent obligations |

**CTR-008.** Delivery, receipt, acceptance, admission, start, commit, effect confirmation, and completion MUST NOT be substituted for one another. A stage may be acknowledged only when its required evidence exists. A caller receiving no acknowledgment knows neither that the operation was not received nor that no effect occurred. `get_operation_status` (§5) or equivalent owner query is the recovery route.

**CTR-009.** Task-result acceptance belongs to Work Coordination and evaluates pinned completion criteria. Goal achievement is an authorized assessment against Goal criteria. Outcome assessment creates evidence-backed Team-accountable meaning. None is implied by an Execution succeeding, Artifact publication, approval, or any generic acknowledgment.

### 3.3 Effect vocabulary

Use SPEC §10 values **none, partial, completed, unknown**. `effect_confirmed` is an acknowledgment about a named effect; it does not replace these values. `none` requires evidence that the named intended effect did not occur, not simply lack of a success response. `completed` means the named intended effect was confirmed to its declared extent. `partial` requires known incomplete extent; if any additional extent is unknown, record unknown for that component. `unknown` records uncertainty, not absence.

**CTR-010.** Effects MUST have explicit scope. Intended external work, local state commits, data disclosures, resource charges, and evidence recording MAY have separate effect identities. A refused Tool action can have none of its intended external effect while still producing a rejection audit record. Parent aggregation MUST NOT hide an unknown component: report unknown overall when completion cannot be established, alongside known per-effect facts. Successfully recording an error does not make the failed business effect completed.

## 4. Canonical error contract

**CTR-011.** Every error MUST contain error identity (or stable enclosing-record key), category, operation/contract, affected subject where safely identifiable, safe message, source owner, tenant-safe correlation, effect status/references, observation time, recoverability, and cause attribution. Retry conditions are required whenever recovery is potentially retryable. Violated constraints, causal errors, remediation references and warnings are conditional on availability/disclosure policy. No raw implementation error is sufficient by itself.

| Category | Contract boundary meaning |
|---|---|
| ValidationError | Invalid input, unsupported mandatory field/operation semantics, invalid transition; no silent coercion |
| CapabilityUnavailable | Required ability has no usable current realization |
| CapabilityResolutionError | Cannot create complete binding; carries unsatisfied/conflict/ambiguous/invalid diagnosis |
| AuthorizationDenied | Effective Principal authority absent/invalid; retry cannot bypass denial |
| PolicyViolation | Mandatory rule/obligation is violated, unresolved, or cannot be established |
| BudgetExceeded | Effective Budget, Quota, or Limit bound exceeded; dimension/unit/scope identified |
| DeadlineExceeded | Bound elapsed or cannot safely be met under its uncertainty rule; effect status independent |
| DependencyFailure | Required subordinate obligation failed; safe cause chain preserved |
| ExecutionFailure | Attempt or internal operation failed without a more specific category, or as an attributed aggregate |
| ToolFailure | Tool invocation/effect confirmation failed |
| ModelFailure | Model invocation/output contract failed; subject quality may instead be an Evaluation judgment |
| HumanRejected | Required Human explicitly rejected; silence and expiry never map to this category |
| Conflict | Expected revision, claim allocation, equivalence identity, or mutually incompatible commitments conflict |
| VersionMismatch | Contract/definition/state/binding versions cannot be interpreted compatibly |
| TenantViolation | Scope invalid or crossing rules violated; no protected disclosure/effect |
| PluginFailure | Plugin admission realization, initialization, lifecycle or health behavior failed its contract |

**CTR-012.** Recoverability uses exactly SPEC's meanings: terminal, potentially retryable, requires intervention, unknown. Category alone MUST NOT authorize retries. Translate implementation failures at the Adapter boundary; retain safe cause evidence and known/unknown effects. Aggregation MUST NOT hide authorization, tenant, policy or resource violations. An unknown failure source uses ExecutionFailure with limitations, not a fabricated specific cause. Unsupported optional operations return explicit unsupported detail under ValidationError or CapabilityUnavailable when a required capability is absent; unsupported versions use VersionMismatch.

## 5. Revision, repeat, and retry contracts

**CTR-013.** Mutable owner-local operations MUST compare expected revisions at the authoritative change boundary. Stale expectations produce Conflict and no requested mutation; current revisions are disclosed only if authorized. Creation uses an expected-absence condition on scoped identity; conflicting creation cannot overwrite. Published semantic versions and historical facts are immutable. Correction creates a linked new record/version; changing operational status creates a new state revision without editing published content.

**CTR-014.** Operation equivalence comprises contract/version, operation name, verified tenant and subject scope, originating authorized requester, pinned input/action meaning, governing immutable revisions, and effect identity where relevant. A repeated operation identity with different meaning MUST fail Conflict. Changes to authorization evidence during a safe retransmission may refresh eligibility but MUST NOT widen action meaning. Representation differences alone do not change semantic equivalence; equivalence rules MUST be declared, not guessed from text similarity.

Expected-revision/absence preconditions are part of that original operation meaning and MUST NOT be silently changed on retransmission. An owner encountering an equivalent operation that it already committed MUST return the authorized prior outcome rather than reapply it or treat its own resulting revision as a fresh stale-write failure. Current access MUST be checked before returning retained results; deduplication MUST NOT redisclose data after access revocation. Refusal to disclose an old result does not erase the old effect or make a new attempt safe.

**CTR-015.** Every supported owner MUST expose `get_operation_status` or an explicitly equivalent family query: input operation identity and current authorized requester; output recorded stages/results, owner revision/freshness, effects, outstanding obligations and declared record-retention coverage. No mutation except governed access evidence. “No retained record” does NOT prove no effect; indicate whether authoritative absence is established for the relevant interval. Queries MUST NOT leak another tenant's existence metadata.

Operation-table retry codes have the following complete shared meaning:

| Code | Semantics inherited by every marked operation |
|---|---|
| Q | Read/inspect/validate: repeat under current access, deadline and resource rules; may observe newer state. Pinned historical reads must preserve version. No intended target mutation, but disclosure/usage/evidence may occur and are recorded |
| M | Owner-local mutation: same equivalent operation identity returns previous commit/result without applying again within declared deduplication coverage; otherwise reconcile status before resubmission. New intent needs new identity and expected revision |
| X | Work/effect attempt: retransmission is deduplicated only under the declared effect/equivalence guarantee; a genuine execution retry creates a new Execution linked to prior work, preserving cumulative restrictions and checking prior effects |
| F | Reconciliation/correction: repeat the same evidence/correction identity without applying twice; new evidence creates a linked observation and expected-revision update; MUST NOT redispatch the original effect |

**CTR-016.** Every operation offering retry/deduplication MUST declare identity scope, equivalence rule, retention/validity interval, failure domain covered, and status-query behavior. Outside retained coverage, or with unknown prior effects, MUST reconcile or require intervention; MUST NOT treat expiration as permission to repeat. Retries use current grants, policy, approvals, deadlines and budgets. Control queries themselves can consume resources; retry codes are not a claim of zero cost. A failed precondition does not erase earlier effects of the same logical work.

## 6. Claims, concurrency, and the dispatch boundary

### 6.1 Contract-state claims

**CTR-017.** Claims are contract records under existing owners, not new domain entities that grant general authority. Each claim MUST identify claim identity, kind, authoritative owner, expected/current owner revision, tenant/subject, operation and effect/action equivalence, amount or bounded scope, validity interval/time basis, governing decisions/policies, state, liability/accounting status, and provenance. A claimant cannot self-issue or edit an owner's claim.

| Claim kind | Owner | Covered obligation |
|---|---|---|
| Approval use | Approval Management | One or more permitted uses of the exact approved action scope; use count cannot be copied |
| Budget reservation / Quota consumption | Resource Admission and Accounting | Specified units/dimension/window and inherited allocation, with remaining liability |
| Limit check / occupancy | Resource Admission and Accounting | Current measurement predicate; concurrent occupancy reserves capacity, static payload check produces a bound decision rather than a consumable balance |
| Delegation capacity | Work Coordination for assignment scope/count; Resource Accounting for allocated resource capacity | Explicit further-delegation or staffing bounds where declared; no invented universal delegation count |
| Effect identity | Invoking plane, Action Mediation for Tools | One authorized dispatch obligation for one intended effect, including provider-side equivalence scope |

**CTR-018.** Claim states describe consumption records only: **reserved** (capacity/use exclusively earmarked or coordinated under explicit sharing), **consumed** (use committed to the exact dispatch/operation), **released** (unused entitlement returned after non-use established), **expired** (no new use valid), **invalid** (revoked/incompatible). Available capacity is an owner query result, not a grant-bearing claim. Creation yields reserved; reserved may become consumed/released/expired/invalid. Consumed is not made reserved again. Corrections and settlements are linked records. Expired/invalid status revokes future use but does not erase liability or already consumed use. Partial consumption splits identified disjoint units with conserved totals.

### 6.2 Ordering requirements, without a global transaction

**CTR-019.** A protected effect MUST NOT dispatch until every mandatory decision, approval-use claim, resource claim, delegation restriction, deadline, boundary/evidence obligation and effect-identity claim covers the exact action **at the dispatch boundary**. Sequential stale “yes” responses are insufficient. The dispatcher MUST establish a valid joint decision interval or equivalent authoritative ordering proof for the full set; if it cannot, it MUST refuse/hold dispatch and report the unsatisfied obligation. This is a required observable guarantee, not a chosen coordination mechanism.

**CTR-020.** The invoking plane owns a single dispatch decision for each effect identity. Claim owners arbitrate incompatible allocations/uses before acknowledgment. For each authority/claim affected by a revocation, expiry, or conflicting update, the effective order relative to dispatch MUST be established. A revocation effective before dispatch prevents it. A concurrent revocation that wins ordering prevents dispatch; if dispatch wins, the effect is in flight and revocation cannot claim to undo it. Final revocation acknowledgment MUST identify affected future/in-flight scope and MUST NOT promise stopped in-flight effects. A disconnected/stale participant cannot authorize new dispatch by merely retaining old decisions. No authority is frozen indefinitely by preparation.

**CTR-021.** Preparation/consumption across owners MAY partially complete. Resource or approval consumption alone MUST NOT imply dispatch occurred. The dispatcher proceeds only after the joint validity in CTR-019 is established, records the exact claim set and action, and prevents a second independent dispatch of that effect identity. If any precondition fails, remaining claims are released only under their owner's non-use rules; already consumed approvals are not automatically refunded. Uncertain dispatch preserves claims' liabilities until reconciliation. This does not assume atomic commits across all owner records or external systems.

Claim consumption for dispatch records a use committed to that operation; it does not assert actual measured resource consumption or successful external effect. Resource Accounting retains the reservation/liability and reconciles actual amounts separately. The same approval-use or effect claim cannot be retargeted to another action after consumption. Repeated consume requests return their prior owner-local outcome rather than consuming again.

**CTR-022.** Dispatch means the governed boundary commits handoff of one protected operation to its realization. It is distinct from the later external effect and from request queuing. A delayed request not yet committed at that boundary MUST still be checked. Where the realization delays a further protected sub-action, that sub-action requires current checks at its own boundary. An interface unable to guarantee stop of already handed-off work MUST disclose that limitation; it cannot claim revocation rollback. Deadline/evidence validity MUST cover the actual handoff; inability to establish safe timing prevents dispatch.

```text
Budget reservation and dispatch
consumer --request--> Resource owner --validate/authorize--> reserve amount
consumer <--committed claim: reserved---------------------- owner
dispatcher --exact action--> Approval / Resource / Governance owners
           <--ordered current validation + bounded claim evidence--
dispatcher --joint validity established--> commit dispatch obligation
           --one handoff/effect identity--> realization
           <--effect observation / unknown-- realization
owners     <--consume/reconcile exact usage and outstanding liability
Any failed/unknown prerequisite => no new dispatch; reconcile held claims.
```

### 6.3 Operation-row conventions

From §7 onward each table specifies **operation, required additions/preconditions, result and owner-local change, retry, special errors**. “Base” errors means every applicable category in §4 for envelope validation, scope, authorization, policy, version, deadline, resource or expected-revision failure. Rows add operation-specific categories; they do not suppress Base. All mutations use M unless a row says X/F. Q never grants future effect authority. The owning module is given at the start of each family and cannot be overridden by a caller.

## 7. Definition and lifecycle contracts

**CTR-023.** Owner is the module allocated that definition by Architecture §§4, 6.1: Application Composition for Applications, Organizational Composition for Roles, Skill Asset for Skills, Workflow driver for Workflows, Policy Decision for Policies, Capability Catalog for Capabilities, and the responsible contract authority for Ports. Plugin lifecycle is specialized by §26. Publication does not bypass a concept's explicit lifecycle or activate a Plugin merely by publishing its description.

| Operation | Required additions / preconditions | Result, acknowledgment and authoritative change | Retry / errors |
|---|---|---|---|
| validate_definition | Candidate kind/identity/version/content, source revision, references, compatibility/extension requirements | Validation evidence and violations; no publication; validated acknowledgment. Owner may record validated status only if requested and permitted, then requires expected revision | Q for assessment; M for requested transition; Base |
| publish_definition | Validated content, immutable version, publication/access scope, compatibility evidence, expected revision/absence | Owner records publication and applicable permitted definition transition; committed version/reference. Runtime activation requires its separate contract | M; Base, DependencyFailure |
| deprecate_definition | Exact published version, allowed active state, replacement/support guidance | New lifecycle revision deprecated; historical content/bindings unchanged | M; Base |
| retire_definition | Version, retirement authority, disposition of active uses/recovery obligations | New retired revision on a permitted path; new use prohibited; outstanding obligations reported, not implicitly deleted | M; Base, DependencyFailure |
| get_definition | Typed scoped identity and exact version or explicit current-selection request | Authorized definition, status, version and observation freshness; selected current version returned explicitly | Q; Base |
| resolve_reference | Typed scoped reference, required revision and access purpose | Exact target/reference status and access-filtered evidence; never silently substitutes newer content | Q; Base, CapabilityUnavailable |

**CTR-024.** Unknown references have explicit unresolved/unavailable status; protected existence may be withheld. “Published” is a recorded fact about availability of a version, not a new universal canonical state. Deprecation/retirement use SPEC D or a concept's specialized states. Published versions cannot be replaced by new content at the same identity/version. Activation/configuration changes affecting behavior need new revisions and current governance.

## 8. Capability Catalog contracts

Owner: **Capability Catalog**; Plugin Lifecycle supplies authoritative activation/health evidence rather than allowing providers to self-assert eligibility.

| Operation | Required additions / preconditions | Result and owner change | Retry / errors |
|---|---|---|---|
| register_offer | Namespace authority, provider/Plugin version, exact CapabilityVersion, dependencies, limits, trust/configuration/compatibility evidence; expected absence | Registered offer revision and visibility policy; no authorization or automatic eligibility | M; Base, PluginFailure |
| update_offer_status | Offer revision, source status evidence and freshness, permitted provider transition | Committed status revision; eligible only with verified active suitable contribution; changed semantic offer requires new version | M; Base, PluginFailure |
| withdraw_offer | Offer identity/revision, withdrawal authority, affected-binding disposition | Withdrawal on permitted path; when currently eligible, first make unavailable then withdraw with recorded revisions. No silent invalidation of history | M; Base |
| discover_capabilities | Scoped identity/version/feature query, limits, consistency/freshness requirements | Authorized candidates, snapshot/continuation identity, omission/truncation information; no whole-catalog completeness claim unless supported | Q; Base |
| inspect_provider | Provider/version and permitted metadata scope | Offers, limitations, owning Plugin, activation references, declared/verified evidence distinction | Q; Base, CapabilityUnavailable |
| query_health_evidence | Provider/activation identity, freshness bound | Attributed observations with observation/recording times, healthy/degraded/unhealthy/unknown and limitations; not new activation | Q; Base, CapabilityUnavailable |

**CTR-025.** Registered means cataloged; visible means discoverable to this requester; eligible means usable for matching under current constraints; healthy is an observation; selected means chosen by a Resolution; authorized means a live action-specific decision; active is a Plugin/definition lifecycle condition. None implies all the others. Pagination/continuations MUST bind tenant, query meaning and snapshot semantics and cannot be reused to bypass access changes.

## 9. Capability Resolution contracts

Owner: **Capability Resolution**. Matching consumes Catalog snapshots and current constraint evidence, never invocation permissions.

| Operation | Required additions / preconditions | Result and owner change | Retry / errors |
|---|---|---|---|
| resolve_requirements | Requirement revisions; version ranges; mandatory/optional designation; hard constraints; preferences; multiplicity/aggregation; extension requirements; tenant/policy/trust/resource feasibility; candidate snapshot or scoped discovery rule | Immutable CapabilityResolution: resolved, unsatisfied, conflict, ambiguous, invalid; full selected closure and provenance. Negative resolution may complete this operation but cannot be used as an executable binding | M for recorded decision; Base, CapabilityResolutionError, CapabilityUnavailable |
| explain_resolution | Exact Resolution reference and allowed explanation scope | Original rules/snapshot, selected/rejected candidates, omissions, dependency edges, predicates, tie evidence; redactions explicit without leaking inaccessible offers | Q; Base |
| validate_resolution | Resolution plus intended consuming context/action requirements and current validity conditions | Current eligibility assessment, stale/invalid reasons and changed inputs; no modification of original decision and no authorization grant | Q; Base, CapabilityUnavailable, VersionMismatch |
| refresh_resolution | Prior Resolution, current requirement/policy/offer inputs, explicit allowed changes | New Resolution linked to prior, differences and compatibility; never silently rebinds running work | M; Base, CapabilityResolutionError |

**CTR-026.** Resolved requires every mandatory and every selected optional dependency to satisfy its hard constraints. Unknown hard evidence fails matching. Composite closure, cycle detection, version coexistence and aggregation follow SPEC §7. Candidate rejection reasons are retained subject to disclosure policy. Deterministic mode MUST produce the same binding for the same complete inputs/rules; a changed snapshot is a changed input. Ambiguity requires an authorized selection rule or remains ambiguous. Optional omission cannot authorize weaker mandatory behavior. No resolution operation reserves actual spend, consumes Approval, dispatches effects, or grants authority.

```text
Capability resolution
consumer --request requirements--> resolver --validate--> scoped Catalog query
resolver <--candidate snapshot / eligibility evidence--- Catalog
resolver --compatibility + hard constraints + trust + closure--> eligible solutions
resolver --preferences / declared tie rule--> immutable Resolution
consumer <--completed + resolution provenance------------ resolver
Separate later boundary: authorization → reservation/admission → invocation/effect.
```

## 10. Execution admission and direct invocation

Owner: **Execution Coordination** for envelopes, admission, state and attempts. Invoking planes retain effect ownership. ExecutionContext includes all SPEC-required properties; no new mandatory Goal/Team is introduced.

| Operation | Required additions / preconditions | Result and state effect | Retry / errors |
|---|---|---|---|
| request_execution | Work/capability contract revision, intended performer, governing context, optional Task/Delegation, expected new Execution identity | Created Execution and bound context/reference; committed creation or accepted-for-processing with status route; not admission | M; Base |
| validate_execution | Created/suspended subject revision, inputs, binding where applicable, admission scope | Check results and evidence; no work start, no added authority | Q; Base, CapabilityUnavailable |
| admit_execution | Created subject (or re-admission under resume), expected revision, validated live conditions/ceiling, resource/deadline feasibility | admitted state/revision and admission decision; approval may still block protected effects | M; Base, CapabilityUnavailable |
| reject_execution | Created or never-started admitted subject, expected revision, cause, evidence no protected execution effect was admitted | rejected terminal state, no started-work effect; prior control/audit records retained | M; Base; Conflict if begun/effect admitted |
| cancel_execution | Target revision, reason and authority | created or never-started admitted may cancel; running/waiting/suspended enter cancelling then cancelled when declared stop obligations settle, or permitted failed state with uncertainty | M for request; X for governed stop effects; Base, ExecutionFailure |
| suspend_execution | running/waiting subject, driver suspension boundary and reason | suspended when boundary reached; until then pending request/current state remains explicit; never claims rollback | M/X; Base, ExecutionFailure |
| resume_execution | suspended subject revision, compatible checkpoint/state, renewed live validity evidence | admitted only after successful revalidation; begun work never rejected. On failure remain safely suspended with explicit unmet conditions or take permitted failure/cancellation path; preserve prior artifacts/effects/accounting/evidence | M/X; Base, VersionMismatch, DependencyFailure |
| get_execution_status | Execution reference, freshness requirement | Authoritative state/revision, begun-work evidence, transitions, effects, artifacts, resource/approval/obligation references; query does not resume work | Q; Base |
| begin_execution | admitted revision, live start preconditions, performer and input bindings | running plus started evidence; refusal of this command is not rejection of an already-begun attempt | M; Base |
| wait_execution | running revision, wait reason/condition/deadline | waiting; later valid signal may allow running, no reset of limits | M; Base |
| complete_execution | running revision, driver result/effect evidence, postconditions/accounting status | succeeded or failed per contract; known/unknown effects retained. Other failure paths use SPEC §5.8. Owner rejects unsupported terminal transition | M/F; Base, ExecutionFailure, DependencyFailure |

**CTR-027.** Public states are exactly created, admitted, running, waiting, suspended, cancelling, succeeded, failed, cancelled, rejected. No new `intervention` state is introduced. A failure response to a command is distinct from a change to the subject's lifecycle. A temporary failed resume check can leave suspended with an intervention obligation; unrecoverable/deadline failure can use suspended → failed. A previously running attempt re-admitted for resume MUST NOT use admitted → rejected or erase begun-work evidence. Drivers preserve the valid transition chain; expected revisions arbitrate races.

**CTR-028.** `invoke_capability` requires an admitted ExecutionContext, exact valid requirement/binding or established admitted realization, input contract, current governance, effect/resource/evidence requirements, and explicit requested guarantees. The Direct driver routes to the bound Port and returns operation result/effects/ArtifactVersions; invoking plane owns the effect. Retry is X, errors Base plus the invoked family's categories. If admission is provided as part of a convenience operation, its created/admitted/started/effect stages MUST remain separately observable. No Agent, Goal, Team, Workflow, conversation, or canonical Outcome is required unless the requested capability explicitly requires it.

```text
Direct invocation
consumer --request--> requirement/binding validation
         --request_execution--> created acknowledgment
         --admit_execution--> admission decision / revision
         --invoke_capability--> authorization + resource/evidence checks
invoker  --dispatch--> provider --effect / result--> invoker
consumer <--operational result + effect/accounting/provenance---- invoker
No automatic Goal / Team / Outcome creation.
```

## 11. Workflow contracts

Owner: **Workflow driver** for definition/WorkflowState; **Execution Coordination** for Execution/Checkpoint records. Workflow operations return separate revisions for each owner, never an unsupported claim of cross-owner atomicity.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| start_workflow | Workflow version, admitted Execution, input references, new WorkflowState identity | Valid initial positions/variables, created then advancing state and Execution running through its owner; effects only through their own contracts | M/X; Base, DependencyFailure |
| advance_workflow | Expected WorkflowState revision, transition cause, required branch/input evidence | Validated next positions/revision, explicit child work/effect requests, join disposition; no arbitrary caller-set state | M/X; Base, Conflict, DependencyFailure |
| signal_workflow | Exact instance/wait/branch identity, typed signal/version, signal identity, source authority | Signal receipt/handling evidence and transition only if wait rule matches; duplicate signal cannot satisfy a join twice | M; Base |
| wait_workflow | Expected advancing revision, declared wait predicate and continuing deadline | waiting WorkflowState and corresponding Execution wait; waiting never becomes approval | M; Base |
| pause_workflow | Execution/WorkflowState revisions and suspension boundary | Requests suspension via Execution owner; WorkflowState retains last progress, no invented paused WorkflowState value | M/X; Base |
| resume_workflow | Suspended/waiting cause, state and definition versions, validated resume evidence or satisfied wait | Uses Execution resume or waiting → running as applicable; WorkflowState returns to advancing through valid rules | M/X; Base, VersionMismatch |
| cancel_workflow | Expected revisions, branch disposition and authority | Coordinates Execution cancellation; records completed/in-flight/unknown branch effects and terminal workflow positions when valid | M/X; Base, ExecutionFailure |
| inspect_workflow_state | Exact state/instance and freshness | Positions, branch identities, waits, committed-effect references, compatibility and revisions | Q; Base |
| checkpoint_workflow | Expected coherent state revision, definition/binding versions, effect/resource references, recovery guarantees | Driver supplies captured state; Execution owner commits immutable Checkpoint; response distinguishes captured state from durable checkpoint acknowledgment | M; Base, VersionMismatch, DependencyFailure |

**CTR-029.** Branch identities MUST distinguish iterations and attempts. Joins declare required branches, duplicate rules, success/failure predicate and unfinished-branch treatment. Signals cannot invent transitions. Checkpoints identify a consistent recovery cut: state plus completed/pending/unknown effects and compatible versions; if a coherent cut cannot be established, checkpoint fails. Durability is only as declared, not implied by the word checkpoint. Resume cannot restore revoked authority, expired approval, obsolete Secret validity, copied balances, or elapsed deadlines.

```text
Workflow checkpoint / resume
driver --request at expected revision--> capture state + effect references
Execution owner --validate compatibility/coverage--> commit Checkpoint
caller <--checkpoint acknowledgment + declared guarantee-- owner
caller --resume request--> current authority / claims / deadline revalidation
owner --valid--> admitted → running; driver advances compatible state
      --invalid--> retained suspension or permitted failure/cancellation
Reconciliation preserves earlier effects; no restoration of spent capacity.
```

## 12. Agent Runtime contracts

Owner: **Agent driver**. Activation/instance state is distinct from each governed Execution.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| activate_agent | Behavior/version, instance identity, autonomy bounds, required dependencies, state compatibility, governance | created → initializing → ready where valid; failures recorded; no blanket action grant | M/X; Base, DependencyFailure |
| invoke_agent | Ready/eligible instance, admitted Execution, scoped Context/Skills, work constraints, concurrency limit | Instance activity and Execution progress, public proposals/results, artifact/action references and errors | X; Base, ExecutionFailure, ModelFailure where applicable |
| suspend_agent | Expected instance revision, reason/boundary, active work references | Active/waiting → suspended when acknowledged; separate attempt states/unknown effects preserved | M/X; Base |
| stop_agent | Expected revision, permitted state, work disposition | stopping → stopped after obligations or failed on permitted unrecoverable condition; no erased work | M/X; Base, ExecutionFailure |
| inspect_agent | Instance/definition revision and disclosure scope | Behavior, public state, work references, bounds and status; private reasoning neither required nor returned by this contract | Q; Base |

**CTR-030.** Agent outputs MAY include proposed/selected action, requested calls, public rationale, artifacts and state observations. Proposals MUST go through the relevant mediated effect boundary; reasoning cannot grant authority. Restarting a failed/stopped Agent creates a linked new instance. Model/Skill use follows their independently governed contracts, not an internal bypass.

## 13. Team, Goal, Plan, Task, and Delegation contracts

Owners: **Organizational Composition** (OC) for Teams/Roles/assignments; **Work Coordination** (WC) for Goals/Plans/Tasks/Delegations/Outcomes. Governance owns grants; Resource Accounting owns resource allocations, even when referenced by WC records.

| Operation / owner | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| create_team_composition / OC | Owning Organization, members/child Teams, Roles, coordination/acceptance rules; new identity | Draft definition and forming composition revision; no automatic staffing grants | M; Base |
| validate_team_composition / OC | Exact composition, role eligibility/cardinality and acyclicity evidence | Validation report; ready transition only if explicitly requested and valid with expected revision | Q/M; Base, CapabilityResolutionError |
| assign_role / OC | Role version, Actor, scope/interval, assigning authority, expected staffing revision | Explicit RoleAssignment, eligibility and active status where permitted; no Permission issued | M; Base, Conflict |
| revoke_role_assignment / OC | Active assignment revision, cause/authority | Revoked assignment plus affected-work obligation; future action eligibility changes, prior effects retained | M; Base |
| create_goal / WC | Owning Organization, Application intent reference, criteria, assessor authority, bounds | Proposed Goal revision | M; Base |
| accept_goal / WC | Proposed revision, authorized acceptance evidence | accepted; activation is a distinct permitted transition | M; Base |
| create_plan / WC | Target Goal revisions, Tasks/dependencies, assumptions/author | Draft Plan revision; no execution or criterion changes | M; Base |
| select_plan / WC | Validated/approved Plan as appropriate, governing Goal/work scope, selection authority and prior selection revision | Selection record with exact Plan version; approval/activation only through permitted transitions; disposition of superseded work explicit | M; Base, Conflict |
| create_task / WC | Work/input/result contracts, owner, requirements/bounds, criteria; optional Goal/Plan | proposed Task revision | M; Base |
| assign_task / WC | ready Task, eligible Actor/RoleAssignment or accepted recipient routing, expected revision | assigned Task and responsibility record; no implicit Execution start or grant | M; Base |
| accept_task_result / WC | running/blocked Task revision, exact Execution/Artifact/evaluation evidence, criteria and acceptance authority | succeeded only if criteria met; otherwise assessment with permitted failed/continuing state; terminal Task is not reopened | M/F; Base, DependencyFailure |
| delegate_work / WC | Full §13.1 declaration and authority/capacity evidence | offered Delegation with immutable proposed scope; no recipient consent inferred | M; Base, AuthorizationDenied |
| accept_delegation / WC | Offered revision, authenticated recipient/Team acceptance Principal, capacity/eligibility | accepted record, bound scope and acknowledgment; activation/work starts separately | M; Base, Conflict |
| reject_delegation / WC | Offered revision, recipient decision and safe reason | rejected; decision attribution, no HumanRejected unless this is a required Human decision | M; Base |
| revoke_delegation / WC | accepted/active revision, revocation authority, affected children | revoked with future-action restriction and in-flight reconciliation obligations; no deletion of history | M; Base |
| assess_outcome / WC | Owning Team, target criteria/work revision, evidence, assessor/acceptance authority | Immutable Outcome assessment, judgment and evidence; not automatic Goal achievement | M/F; Base |
| transition_coordinated_work / OC or WC | Exact subject kind, expected revision, desired listed transition, cause/evidence/authority | One permitted transition such as Goal activation/achievement, Plan approval/activation/supersession, Task readiness or Delegation activation/completion; owner validates all concept-specific guards | M; Base, DependencyFailure |

**CTR-031.** The generic transition operation cannot bypass specialized acceptance/grant/claim rules. Team/Role/Actor, Goal/Task, Execution/Task, operational result/Outcome remain distinct. Humans and Services fulfill Roles without Agents. A Team is never supplied as an acting Actor; its responsible Principal and actual performers are identified. Goal achievement requires its own authorized criteria assessment even after Task success.

### 13.1 Delegation declaration and attenuation

**CTR-032.** A Delegation request MUST bind delegator Actor/Principal, delegate Actor or Team, recipient Principal/acceptance rule, exactly one Task or Goal target with revision, allowed actions/resources, required and allowed Capabilities, Context reference and permitted disclosure, inherited Policy references, ResourcePolicy/Budget/Quota/Limit references and allocation mode, effective deadline, expected Artifact/result/Outcome contract, approval requirements, parent Delegation/chain or explicit root. An expected canonical Outcome requires accountable Team semantics; ordinary result expectations do not.

Acceptance returns exact accepted scope/revision, authority-chain validation evidence, recipient attribution, resource/capacity claims where applicable, status and completion/reporting obligations. Effective authority is bounded by the intersection required by SPEC D-02; further delegation must be explicitly permitted and cannot widen scope or deadline. Supplemental authority requires separate valid grants and cannot enlarge an existing accepted Delegation silently. Capacity checks are owner-arbitrated, not copied snapshots. Completion preserves artifact versions, incurred/unknown resource use, effect uncertainty and evidence before authorized acceptance.

```text
Delegation
delegator --request bounded work--> WC --validate Role/authority chain--> Governance
WC --reserve child capacity through owner--> Resource Accounting
recipient <--offered scope/revisions/expectations-- WC
recipient --explicit acceptance--> WC --commit accepted delegation--> acknowledgment
actor --admitted Execution--> governed dispatch/effects → Artifacts/results
WC <--completion evidence-- actor; WC --separate acceptance--> accountable result
```

## 14. Tool / Action contracts

Owner: **Action Mediation**. An `action specification` means pinned Tool contract/version, operation/input meaning, target resources/revisions, expected effects, tenant/Principal scope, allowed data disclosure, constraints and equivalence rule. A preparation reference is not permission by itself.

| Operation | Required additions / preconditions | Result and owner change | Retry / errors |
|---|---|---|---|
| inspect_tool | Tool/version, authorized scope | Input/output/effect classifications, required authority, retry/idempotency/compensation/usage guarantees and limitations | Q; Base, CapabilityUnavailable |
| validate_action | Exact action specification, contextual constraints | Attributable validation findings; no reservation, approval consumption, dispatch or authority grant | Q; Base |
| prepare_action | Action/effect identity, admitted Execution, validation evidence, current authorization/policy inputs and required claim/evidence set | Owner records immutable preparation/action equivalence and unmet obligations; references owner-issued reservations/approval readiness when acquired; committed preparation ≠ dispatched | M; Base, ToolFailure |
| dispatch_action | Exact prepared action/effect identity, expected preparation revision, all current §6 conditions, active eligible realization | One handoff obligation and dispatch acknowledgment/effect observation. Returns pending/unknown if confirmation absent; no second independent dispatch from duplicate submissions | X; Base, ToolFailure |
| get_effect_status | Effect identity, observation freshness/evidence scope | none/partial/completed/unknown, source/time/extent, dispatch/claim/result links and unresolved obligations | Q; Base, ToolFailure |
| reconcile_effect | Effect identity, expected observation revision, new independently attributable evidence/equivalence, authority | New linked effect observation and obligation decisions; does not automatically repeat action or refund claims | F; Base, ToolFailure, Conflict |
| request_compensation | Original effect/version, supported compensation contract, intended compensating effect/new identity, live authority/approval/resources | New governed work/preparation reference or refusal; separate effect/result, no promise to erase original | M/X; Base, CapabilityUnavailable, ToolFailure |

**CTR-033.** `effect_identity` identifies one intended protected effect in tenant/subject scope across retransmissions and compatible recovery. It is distinct from an Execution attempt, dispatch transport attempt, Tool name, request identity and business Task. The invoking plane arbitrates its dispatch slot and verifies action equivalence. A retry using a new Execution MUST retain the same effect identity for the same intended effect when relying on deduplication; a truly new intended effect needs a new identity and independent authority. Provider change MUST preserve the deduplication guarantee or trigger reconciliation; it cannot silently reset effect history.

**CTR-034.** Action preparation separates validation, authorization decision, resource reservation, approval-use allocation, required evidence and dispatch. These operations may be composed but each acknowledgment/claim must remain observable. A Tool timeout after possible handoff yields unknown unless stronger evidence exists. Unknown outcomes MUST be reconciled, safely retransmitted under a declared end-to-end equivalence guarantee, or held for an authorized intervention before potential duplicate harmful effects. An effect-identity record in the caller alone cannot prove external deduplication.

```text
Protected Tool/action invocation
caller --proposal/validate_action--> Action Mediation <--validation evidence
Action --authorize_action--> Governance <--decision/obligations
Action --claims--> Resource / Approval owners <--reserved/consumed evidence
Action --mandatory pre-evidence--> Evidence owner <--required acknowledgment
Action --dispatch_action exact identity--> joint-valid dispatch boundary
       --handoff--> realization --effect--> target
caller <--result/effect observations-- Action <--reconciliation evidence-- owners
```

## 15. Governance, approvals, resources, tenant and Secret contracts

### 15.1 Identity, authorization and policy

Owners are **Identity and Principal**, **Authorization**, **Policy Decision**, and **Boundary Enforcement**, as indicated. Identity verification is not an authentication protocol.

| Operation / owner | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| verify_identity / Identity | Candidate Identity/issuer and protected proof references; trusted ingress initiator | Verified/failed evidence and validity/claims; no grant or arbitrary Principal selection | Q/F evidence; Base, AuthorizationDenied |
| establish_principal / Identity | Verified Identity, tenant scope, permitted kind, establishment authority, expected absence/revision | Attributable Principal association/status record; no implicit action Permission | M; Base |
| validate_acting_on_behalf_of / Authorization | Acting/originating Principals, delegation/grant chain, exact scope/action | Validity decision with chain/bounds and current restrictions; cannot substitute credentials | Q; Base |
| evaluate_permission / Authorization | Principal, action/target/revisions, eligible grants/denials and caller context | Decision on eligible authority at observed revisions/time; no general grant created | Q/F evidence; Base |
| evaluate_policy / Policy Decision | Action/subject, all applicable policy authority/revision inputs, classified Context, decision purpose | Decision allow/deny/conditions-unmet, obligations/conflicts and evidence; cannot select only favorable rules | Q/F evidence; Base, PolicyViolation |
| authorize_action / Boundary Enforcement with Authorization/Policy | Exact action and admitted ceiling, current grants/chain/tenant, applicable policies and required controls | Attributable action-specific decision, scope, conditions/obligations, validity/time basis, policy/grant revisions, evidence; dispatch still requires §6 claims | Q/F evidence; Base |
| evaluate_guardrail / Guardrail Coordination | Control/version, boundary/action, authorized input references, threshold/failure rule | Attributed verdict/transformation reference and uncertainty; resulting obligations imposed by Policy, not model confidence alone | X; Base, DependencyFailure |

**CTR-035.** Identity identifies a subject; Principal is the verified security subject; Actor performs work; Role defines responsibility; RoleAssignment binds an Actor; Permission bounds eligible actions; Policy governs conditions. Authorization outputs are expiring/revocable decisions, never eternal Permissions. Current restrictive policy and admitted authority ceiling apply at dispatch and resume. Unknown mandatory policy decision or conflict prevents action. Authority precedence/exception issuers are inputs from governing authority, not invented by these contracts.

### 15.2 Approval and HumanApproval

Owner: **Approval Management**. Every request binds exact action/target/relevant revisions, requester, scope, Policy, eligible approvers, decision/quorum rule, expiry/time basis, explicit allowed-use bound, evidence presented and required separation of duties. Unbounded use requires explicit Policy permission; no implicit unlimited default.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| request_approval | Full scoped proposal above, new request identity | requested/pending Approval, presented-evidence revision, recipient obligations; no consent inferred | M; Base |
| submit_approval_decision | Pending revision, authenticated eligible decision-maker, exact presented scope, explicit approve/reject and time | Immutable decision evidence; quorum updates remain pending or reach approved/rejected per rule; no Machine decision masquerades as HumanApproval | M; Base, HumanRejected when required human rejection prevents work |
| validate_approval | Exact action/Approval and current authority/revisions/expiry/use bounds | Applicability verdict and evidence, remaining-use observation; no reserved use | Q; Base, PolicyViolation |
| reserve_approval_use | Approved revision, exact effect/action, use amount and validity | Owner-arbitrated reserved use claim under §6, not an additional canonical Approval state | M; Base, Conflict |
| consume_approval | Exact reserved use claim, expected claim/Approval revision and §6 dispatch binding | Consumed use record; Approval becomes consumed only when all allowed uses exhausted, otherwise remains approved; not effect confirmation | M; Base, Conflict |
| revoke_approval | Approved revision, revocation authority/cause | revoked under §6 ordering; prior decisions/uses and in-flight obligations retained | M; Base |
| expire_approval | Requested/pending/approved revision, authoritative time/expiry evidence | expired on permitted path; outstanding effects/claims retained, not a rejection decision | M; Base |

**CTR-036.** Decision/request/claim revisions are checked by their owner; concurrent uses cannot exceed the approved bound. Changed action semantics require new approval where relevant. A consumed use is not auto-refunded on downstream failure; a new request or explicitly governed new entitlement is needed. Silence never approves or rejects. HumanApproval requires attributable authenticated Human participation, adequate disclosed decision context and the same bounded-use contract. Approval ≠ authorization ≠ effect ≠ Task success.

```text
Human approval
proposed effect --policy evaluation--> Approval required
requester --request_approval exact revision--> pending acknowledgment
Human <--authorized decision context-- Approval owner
Human --explicit decision--> owner --commit approved/rejected--> acknowledgment
invoker --validate + reserve/consume use--> owner
invoker --revalidate all claims/authority--> dispatch boundary → effect/result
No response/expired scope => no approval; changed proposal => new request.
```

### 15.3 Resource operations

Owner: **Resource Admission and Accounting** for every authoritative allocation/window/claim/usage revision; **Execution Coordination** propagates deadlines. Quantity requires resource-dimension identity, unit identity/definition revision, nonnegative magnitude, measurement scope/window, amount kind (estimate, bound, reservation, actual, correction), precision/rounding rule, and uncertainty bounds or explicit unknown. Units must be semantically compatible; a correction's signed delta is separately identified and authorized, not negative consumption hidden as a new charge.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| check_resource_feasibility | Resource quantities/estimates, applicable Budget/Quota/Limit/Policy references, deadline | Feasible/infeasible/unknown assessment at revisions/time; no reservation or spend grant | Q; Base, BudgetExceeded |
| reserve_resource | Exact operation/effect, units/upper bound or approved uncertainty policy, parent allocation mode, expected authority revision | Committed bounded reserved claim or refusal; all required scopes considered, no double-allocation from copied balance | M; Base, Conflict, BudgetExceeded |
| consume_resource | Claim, unique usage-report identity, measured/estimated quantity with scope/time and effect evidence, expected revision | Consumption/committed liability entry and remaining reserved balance; duplicates return prior accounting effect | M/F; Base, Conflict, BudgetExceeded |
| release_resource | Claim, quantity, expected revision, proof of non-use/cancelled handoff or authorized settlement | Release only unused/unencumbered capacity; consumed/unknown liability stays outstanding | M/F; Base, Conflict |
| reconcile_resource | Claim/report identities, actual measurements or explicitly authorized settlement, conversion/rate evidence if any | Linked correction/settlement, authoritative revised balances, remaining unknown liability; history preserved | F; Base, Conflict |
| query_resource_state | Scope/claim/allocation identity, window and freshness | Allocated, reserved, consumed, remaining, outstanding/unknown and explicit overdraft status in stated units; a snapshot is not spend authority | Q; Base |

**CTR-037.** For each dimension/allocation/window, committed consumption plus outstanding reserved liability MUST stay within the effective allocation and explicitly approved overdraft bound. Child allocation counts once against its parent; child spend consumes its envelope rather than adding consumption on top of an unchanged full reservation. Distinct concurrent children cannot reserve the same units. Occupancy Limits reserve concurrent capacity until release; immutable payload Limits bind validation to exact input. Quota reset rules are explicit and retry does not create a new window. No billing currency, tariff, universal precision or time source is chosen.

**CTR-038.** Unknown external charges remain outstanding until reconciled or explicitly settled by an entitled accounting authority. Expiry, cancellation, provider replacement or missing acknowledgments never auto-refund possible consumption. Estimates need bounds/uncertainty rules; hard-limit admission MUST fail if the necessary bound cannot be established. Partial multi-dimension reservations cannot dispatch work until all mandatory dimensions are covered. Child deadlines are no later than parents unless a valid parent change explicitly extends the constraint.

### 15.4 Tenant boundaries

Owner: **Tenant Governance** for scope and crossing decisions; transferred data remains owned by its domain module, and **Evidence and Provenance** records general transfer evidence. Separate owners acknowledge their own changes.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| bind_tenant_context | Candidate Tenant and verification/source evidence, current Principal scope, trusted ingress attribution | Bound verified TenantContext reference or denial; no caller override/wildcard | M/F; Base, TenantViolation |
| validate_tenant_scope | Verified context, subject/resource scopes, intended action | Current consistency decision; no transfer grant inferred from common owner/person | Q; Base, TenantViolation |
| authorize_cross_tenant_access | Source/destination Tenant, exact resource/action scope, purpose where required, valid grant, both policy contexts | Scoped crossing decision/evidence and conditions; neither data relabeling nor co-ownership | Q/F; Base, TenantViolation, AuthorizationDenied |
| record_cross_tenant_transfer | Exact crossing decision, original source/version, destination use/copy reference, transfer effect and source/recipient evidence | Linked immutable transfer record; target module separately commits its scoped copy/use; original scope/lineage retained | F; Base, TenantViolation, Conflict |

**CTR-039.** Each operational entity has one tenant. Destination execution is a distinct admitted Execution causally linked to the authorized crossing, never a modified parent TenantContext. Transfer recording cannot retroactively authorize an unapproved disclosure. Shared provider implementations keep tenant-specific state/configuration/Secret/usage/evidence isolated. Cross-tenant co-ownership remains outside these contracts.

### 15.5 Secret access

Owner: **Secret Access**. Public results are protected references and use evidence, not material. Actual confidential material use remains inside an authorized protected realization; the contract does not prescribe how it is conveyed there.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| resolve_secret_reference | Scoped Secret reference, intended purpose/consumer, relevant revision requirement | Validated protected reference and material revision identity/status; never raw Secret value | Q; Base |
| authorize_secret_use | Exact action/consumer, Secret reference and current authority/purpose/validity | Bounded use decision, not general read/export permission | Q/F; Base, AuthorizationDenied |
| record_secret_use | Use identity, authorized action/Secret revision, actual/unknown use evidence | Immutable use attribution without material | F; Base |
| validate_secret_revision | Secret/material revision reference and current usage conditions | Current validity/rotation/revocation result; old checkpoint references do not restore expired material | Q; Base, VersionMismatch |

**CTR-040.** Raw Secret material MUST NOT appear in public results, manifests, provenance or telemetry. Secret reference possession is not permission. Rotation and revocation must affect subsequent uses; forensic attribution retains identifiers, not obsolete values.

## 16. Model contracts

Owner: **Model Interaction**. Model invocation is independently usable and carries admitted Execution identity without depending on an Agent or Workflow implementation.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| describe_model | Model/provider/Capability version references | Input/output/modalities, supported ModelCapabilities, limitations, reproducibility and usage guarantees | Q; Base, CapabilityUnavailable |
| validate_model_request | Input contract/references, requested ModelCapabilities/versions, structured-output meaning if required, input/output limits, tenant/data-use constraints | Validation findings, requested behavior compatibility; no inference performed or authority granted | Q; Base, VersionMismatch |
| invoke_model | Validated request, exact model/binding revision or disclosed opaque-version limitation, admitted Execution, live disclosure/authority/resource/deadline checks | Invocation evidence, untrusted output/reference, actual version evidence, usage and none/partial/completed/unknown effects. A completed inference may produce invalid output and a ModelFailure | X; Base, ModelFailure |
| cancel_model_request | Invocation identity/revision, advertised cancellation support, authority | Stop request/result with known/unknown in-flight work and charges; unsupported cancellation explicit, no false rollback claim | M/X; Base, CapabilityUnavailable, ModelFailure |
| report_usage | Invocation/effect identity, unique report/source, quantity kind/units/measurement and uncertainty | Model-owned usage observation; Resource Accounting separately reconciles it through an allowed contract | F; Base, Conflict |

**CTR-041.** Structured output is not proof of truth, safe instructions, authorization, or subject quality. Outputs retain trust and source attribution. Models may be multimodal or non-language models. Repeat invocation may differ even on the same input; deterministic inference or exact replay is not implied. A lost invocation result requires effect-safe retry and usage reconciliation. Evaluation of Model results is orchestrated by an authorized consumer permitted to depend on both Intelligence and Evaluation; Model Interaction does not directly invoke Evaluation.

## 17. Skill contracts

Owner: **Skill Asset**. Skills describe expertise and dependencies; consumers orchestrate admitted actions through E/T as required by Architecture §5.2.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| inspect_skill | Skill/version and visibility scope | Instructions/resource references, usage contract, dependencies and evaluation evidence references where authorized | Q; Base |
| validate_skill | Exact Skill content/version, references, compatibility and composition constraints | Validation report including cycles/unavailable resources; no publication/installation | Q; Base, DependencyFailure |
| resolve_skill_dependencies | Versioned dependency requirements, consumer context, mandatory/optional constraints | CapabilityResolution or explicit non-success, pinned dependencies/provenance; no automatic dependency installation | M; Base, CapabilityResolutionError |
| use_skill | Exact Skill version, authorized Context/resources, admitted work and bound dependencies | Attributable expertise use/result reference or action proposals for the consumer to mediate; usage evidence, not authority or control configuration mutation | X; Base, DependencyFailure |

**CTR-042.** Skill use MUST NOT install arbitrary dependencies, grant Permissions, bypass Tool mediation, override Policy, or mutate control-plane configuration. Governing-definition publication requires its own authorized contract and cannot be implicit in instructions. Every contributing Skill version is attributable. Evaluation of Skill behavior is orchestrated by an authorized consumer permitted to depend on both Intelligence and Evaluation. Skill Asset MAY reference existing authorized Evaluation evidence but does not directly invoke Evaluation.

## 18. Context contracts

Owner: **Context Assembly**. Context is information; ExecutionContext is bound governing execution identity and references owned by Execution Coordination.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| assemble_context | Authorized source references/revisions, purpose, tenant scope, trust/classification, required freshness and input contract | New scoped Context value/record with explicit inclusion/omission and source lineage | M/X if material work; Base, DependencyFailure |
| validate_context | Exact Context revision, required content/visibility/freshness constraints | Validity report; no authority gained from text | Q; Base |
| derive_context | Source Context revisions, transformation meaning/version, source access and target restrictions | New derived Context and provenance, inherited restrictions; lossy summaries identify limitations | M/X; Base, DependencyFailure |
| redact_context | Source revision, authorized redaction rule/purpose, target visibility | New Context with redaction/lineage evidence safe for recipient; does not edit source history or imply declassification | M/X; Base, PolicyViolation |

**CTR-043.** Origin, source revisions, trust classification, tenant scope, freshness and lineage MUST survive transformation. Redaction must not leak hidden information through metadata or source existence. Promoting Context to Policy/configuration is an explicit separately authorized publication; interpreting instruction-like text cannot bypass that boundary.

## 19. Memory contracts

Owner: **the respective Memory module**. Supported operation/kind combinations MUST be advertised; no generic interface forces every kind to support query, arbitrary mutation or durable recall.

| Kind | Required specialization |
|---|---|
| Working/session | Working Memory is distinct from driver-authoritative Workflow/Agent state; session binding/expiry/visibility and volatility declared |
| Semantic | Meaning-oriented entries/associations retain attribution, update interpretation and confidence where applicable |
| Episodic | Episode identity/time, source events and correction lineage explicit; recall does not become current execution state |
| Procedural | Retained procedure/version and permitted uses explicit; publication as Skill or Policy is separate governed work |

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| read_memory | Kind/store scope, entry/session and revision/current-read semantics, freshness/access | Entry/reference, version/source/trust and availability; no recall authority | Q; Base, CapabilityUnavailable |
| write_memory | Supported kind, content/source/trust/retention, expected entry/collection revision or absence, declared append/correction/update mode | Owner-committed entry/revision; immutable records corrected by linked additions, not overwritten | M; Base, Conflict |
| query_memory | Supported query meaning, scopes, bounds/freshness, result limits | Access-filtered attributed results and query coverage/truncation evidence; no implementation-specific index required | Q/X if declared metered work; Base, CapabilityUnavailable |
| forget_memory | Scope/entries/revisions, authorized retention/disposition decision, expected revision, requested extent | Disposition result including remaining holds/copies/references/unknown obligations; no unsupported guarantee all derived knowledge is erased | M/F; Base, PolicyViolation, Conflict |

**CTR-044.** Memory does not require embeddings, vector storage, any database, or Agents. Read/query disclosures and writes are governed effects. Forgetting an entry cannot silently delete another module's Artifacts, facts, or required audit records. Unknown mandatory retention conflicts fail closed for destructive action and identify resolution obligations under SPEC A-03.

## 20. Knowledge contracts

Owner: **Knowledge Curation**.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| publish_knowledge | Content/reference, source/version, provenance, scope/access, validity/freshness, confidence if claimed; expected absence/collection revision | Recorded knowledge identity/revision and curation/publication evidence; assertion remains labeled unless verified | M; Base |
| query_knowledge | Scoped query/coverage, source/validity constraints, result limits | Governed matching records, versions, freshness/confidence meanings and query completeness limitations | Q; Base |
| get_knowledge | Exact identity/version or explicit current selection | Source-attributed record and access-filtered lineage; selected revision disclosed | Q; Base |
| supersede_knowledge | Original revision, new record/source, supersession rationale, expected collection revision | New record and linked supersession; old claims remain historical and are not silently rewritten | M/F; Base, Conflict |

**CTR-045.** Knowledge content MUST NOT become Policy, authority, or verified truth automatically. Retrieval-augmented generation is a composition, not the Knowledge contract. Subject access and existence metadata are both governed.

## 21. Retrieval contracts

Owner: **Retrieval**. This Port has no mandatory Agent, Model, generation or conversation dependency.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| query_retrieval | Query meaning/version, source scopes, hard constraints, ranking requirements, freshness, result limits, intended disclosure scope | Results with source references/versions, provenance, access-filtering evidence and bounded completeness. Scores only with defined scale/meaning. No privileged post-filter leak allowed | Q/X for declared execution; Base, CapabilityUnavailable, DependencyFailure |
| explain_retrieval | Exact query/result record, authorized explanation scope | Source/selection/ranking/freshness evidence from that query, safe omissions and limitations; no new query passed off as old reasoning | Q; Base |

**CTR-046.** Limits bound both exposed results and declared work/resource behavior. Freshness and ranking requirements are predicates, not promises of perfect relevance. Continuations bind query/snapshot and tenant and revalidate disclosure; a hidden source cannot be revealed through rank, count, score or explanation contrary to policy. A result reference does not grant subsequent content access.

## 22. Artifact contracts

Owner: **Artifact Management**. A content reference identifies stable content meaning/version, interpretation/type, governed access and preservation/availability guarantees; it is not canonical storage location or a bearer access grant.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| create_artifact | New identity, type, owner, tenant, metadata, policy/retention/visibility, provenance; expected absence | Draft Artifact identity/revision; no available-content claim without a valid version | M; Base |
| create_artifact_version | Artifact expected revision, stable new version identity, content reference/type, producer/time, metadata/policies/provenance, predecessor references | Immutable version record and Artifact revision; unavailable content is explicit; no overwrite of prior version | M; Base, Conflict, DependencyFailure |
| get_artifact | Identity and metadata/access scope, requested revision | Authorized metadata, lifecycle, versions/aliases and observation revision; does not imply content access | Q; Base |
| get_artifact_version | Exact ArtifactVersion, required content guarantee and disclosure purpose | Pinned content/reference, provenance and accessible/unavailable/tombstone status; no newer substitution | Q; Base, CapabilityUnavailable |
| relate_artifacts | Typed relation/version, exact endpoints/revisions, creator/evidence, expected graph/subject revision | Immutable edge/record; validates direction/cardinality/cycles and metadata visibility | M; Base, Conflict |
| publish_artifact_version | Exact version, required evaluation/Approval evidence, current release policy/access, expected publication revision | Version-specific release record and visibility; owner makes Artifact available only on a permitted path with valid version | M; Base, PolicyViolation, DependencyFailure |
| withdraw_artifact_version | Exact published version/release revision, authority/reason | Withdrawal/visibility decision, no content-history mutation or automatic Task reversal | M; Base |
| supersede_artifact_version | Old/new exact versions and authorized supersession evidence, expected relationship/alias revision | Linked supersession record and explicitly requested alias/Artifact transition where valid; no new ArtifactVersion lifecycle state | M; Base, Conflict |
| dispose_artifact | Artifact/version scope, expected revision, current holds/retention/disposition evidence | Disposition outcome, content unavailability and permitted tombstone or outstanding obligations; no unsupported deletion guarantee | M/F; Base, PolicyViolation, DependencyFailure |

**CTR-047.** Execution inputs, evaluations, approvals, provenance and derivations MUST pin exact versions when meaning depends on content. Mutable current aliases are not approval targets. Derivation/supersession are acyclic; citation may cycle. Publication, disposition and relationship access are governed effects. A failed publication after production is reconciled against the same version, not by repeating the producing Tool/Model effect.

## 23. Event contracts

Owner: **Event Coordination** for publication/delivery records; source module owns fact and consumer owns handling/consumer effects.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| publish_event | Fact identity/type/version, source attribution, occurrence/recording times, subject/payload references, tenant/causation, declared publication guarantee | Publication custody/commit acknowledgment with guarantee and delivery obligations; does not prove consumer receipt or effect | M; Base, DependencyFailure |
| deliver_event | Event identity, distinct delivery-attempt identity, recipient scope, source/version validity, ordering/equivalence declaration | Receipt/acceptance evidence or failed/unknown delivery; event fact unchanged | X; Base, DependencyFailure |
| acknowledge_event | Delivery identity, authenticated consumer, exact stage (receipt/handling acceptance/handling completion), associated evidence | Immutable acknowledgment record scoped to that stage; business effects only via separate effect references | M/F; Base, Conflict |
| reject_delivery / record_failed_delivery | Delivery identity, safe reason/evidence, retry eligibility and uncertainty | Recorded rejection/failure/unknown status, retained unresolved delivery obligation under policy; not a change to original fact | F; Base, DependencyFailure |

**CTR-048.** Fact occurrence ≠ recording ≠ publication ≠ delivery ≠ receipt ≠ consumer acceptance ≠ consumer effect. Duplicate handling keys bind tenant, consumer, event identity and declared handler semantics; a new delivery attempt is not a new fact. Out-of-order behavior declares the ordering domain and policy: wait, reject, or process with evidence, never infer universal order. Unknown receipt is not failed effect. End-to-end consumer effects need their own effect identities and §6 governance; event identity alone provides no exactly-once business guarantee.

## 24. Evaluation contracts

Owner: **Evaluation Management**. Any supported Evaluator realization sits behind its Port; callers MUST follow Architecture's permitted dependency matrix. Intelligence does not directly invoke Evaluation; authorized consumers MAY orchestrate evaluation of Model or Skill behavior.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| describe_evaluator | Evaluator/version | Criteria, method/input/result scale, uncertainty/failure meaning, applicability and independence requirements | Q; Base |
| request_evaluation | Subject/input/case revisions, Evaluator/method/criteria versions, required conditions/baseline, scope/resources | requested Evaluation with governance/Execution attribution; custody acknowledgment is not assessment result | M; Base |
| execute_evaluation | Requested revision, admitted execution, valid subject access, applicable method/independence conditions | running then completed/failed/cancelled as permitted; evidence and result references; real work subject to claims and uncertainty | X; Base, ExecutionFailure, DependencyFailure |
| record_evaluation_result | Evaluation, exact subject/criteria versions, judgment/measurements and units/scales, assessor/time/evidence/limitations | Immutable EvaluationResult; correction links new result; no automatic release/Task success | M/F; Base, Conflict |
| compare_evaluations | Exact results/conditions, declared comparison method and compatibility criteria | Attributed comparison with incompatible/inconclusive detail if methods/conditions differ; original judgments unchanged | Q/X when assessment work; Base, VersionMismatch |

**CTR-049.** Evaluation execution succeeded does not mean the subject passed; assessment failed does not mean the subject failed. Inconclusive is explicit. Offline and runtime evaluation have identical scope/evidence obligations and no Agent requirement. Policy decides whether evidence satisfies a release gate. Evaluation itself cannot appoint certification authority or waive isolation.

## 25. Observation, audit and provenance contracts

Owners: **Observation Collection** (trace/telemetry); **Evidence and Provenance** (audit/general lineage). Original decisions/effects remain authoritative at their source owners; artifact relationship edges remain Artifact Management's state.

| Operation / owner | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| record_trace_activity / Observation | Activity identity, Trace/Execution, source/time/status, causation, classification and completeness | Appended attributable activity; committed acknowledgment states persistence/collection coverage, not work success | M/F; Base |
| record_audit_evidence / Evidence | Evidence identity, material decision/action references, issuer/source, revisions/times, mandatory guarantee/retention/access policy | Evidence custody/commit acknowledgment with exact guarantee and source linkage; no creation of the source decision itself | M/F; Base, PolicyViolation |
| record_provenance / Evidence | Subject/source/transform versions, producer/Execution, input references, decisions, declared unknown/asserted origins | Immutable general lineage record with safe references; no competing artifact relationship mutation | M/F; Base, Conflict |
| record_telemetry / Observation | Measurement identity, resource/unit or diagnostic meaning, time/source/scope, sensitivity, collection rule | Measurement accepted/recorded/dropped-with-reason under declared policy; never authoritative resource balance | M/F; Base |

**CTR-050.** These operations MUST preserve distinct Trace, Audit, Provenance and Evaluation meanings. No generic logging operation substitutes for required evidence. Public reasoning may be recorded only when allowed; private chain-of-thought is never required. Duplicate evidence identity with different content fails Conflict; a correction appends lineage. Private data and Secrets are not indiscriminately logged. Required audit/provenance guarantee handling and recursion termination are specified in §29.

## 26. Plugin, Adapter, and isolated-execution operations

Owner: **Plugin Admission and Lifecycle**; Catalog owns offers. “Inspect”, “admit”, “configure”, “upgrade” and “suspend use” are activities, not new Plugin states.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| discover_plugin | Visible description identity/version/source and scope | discovered description/reference; no trust or activation | M for new record / Q for query; Base |
| inspect_plugin | Exact Plugin/Port/Capability contribution revisions, allowed metadata | Declared contributions, configuration/compatibility, requirements, integrity/trust/conformance evidence and limitations | Q; Base, PluginFailure |
| validate_plugin | Exact candidate/version/configuration, graph assessment, permissions/trust/tenant suitability and required evidence | Validation report only; validated state is committed by admit_plugin after all checks pass | Q; Base, PluginFailure, CapabilityResolutionError |
| admit_plugin | Expected discovered revision, verified validation/trust evidence and accountable admission authority | validated state/admission record; no activation; plugin cannot sign its own admission as authority | M; Base, PluginFailure |
| configure_plugin | Candidate/activation reference, non-secret configuration revision, Secret references, expected configuration revision | Bound validated configuration; changing active configuration requires a new admitted activation/version treatment, no silent content rewrite | M; Base, VersionMismatch |
| initialize_plugin | validated record, bound configuration and already admitted usable initialization dependencies, live authority/resources | initialized or failed; initialization effects separately governed and retained | X; Base, PluginFailure, DependencyFailure |
| activate_plugin | initialized revision, current admission/configuration/health/suitability and dependency evidence | active activation record; Catalog receives eligibility contribution via its contract; partial catalog publication is explicit | M/X; Base, PluginFailure |
| observe_plugin_health | Exact activation, attributed health/time/freshness evidence | Health record; no implicit lifecycle transition, grant or indefinite eligibility | F; Base |
| degrade_plugin | Active revision, health evidence and authority | degraded; only still-satisfying contributions remain eligible | M; Base, PluginFailure |
| restore_plugin_health | degraded revision, validated recovery evidence | active if requirements hold; historical failed work unchanged | M; Base, PluginFailure |
| stop_plugin | Permitted active/degraded/failed state and work-disposition authority, expected revision | stopping then stopped; new work blocked, ongoing effects/charges reconciled; appropriate initialization cancellation uses SPEC's permitted stopped path | M/X; Base, PluginFailure |
| retire_plugin | stopped or explicitly permitted unused state, evidence of required disposition/historical interpretation | retired; new use prohibited, retained versions remain interpretable as required | M; Base, PluginFailure |

**CTR-051.** Suspension of use withdraws/makes unavailable offers and follows stop/reactivation semantics; it does not add a Plugin suspended state. Upgrade means new version admission, explicit bindings/migration and old-version drain/retire; no in-place semantic overwrite. Reinitialization of stopped requires a new validated activation record. Compatibility, required capabilities, trust/permissions, configuration, tenant suitability and required conformance evidence MUST all be established. Admission failure cannot be hidden by invoking plugin code to approve itself.

### 26.1 Adapter conformance and binding

**CTR-052.** `describe_port` returns published purpose/version/operations/guarantees through definition inspection; `inspect_adapter` is Plugin inspection restricted to its owning Plugin, implemented Port versions, offers, limitations and conformance evidence. `validate_adapter_conformance` is an Evaluation requested by an allowed consumer and yields evidence, not a grant. Binding replacement requires a new compatible Resolution/activation and explicit migration for incompatible retained state. No operation permits a consumer to import Adapter-specific authority, errors or state semantics as canonical behavior.

### 26.2 Sandbox / isolated-execution Port

Architecture §4.6 retains sandbox responsibilities. The admitted realization implements this Port; **Action Mediation** owns the invoking isolation requirement/session record, and Plugin admission owns the realization's trust evidence. No new deployment unit or domain lifecycle is required.

| Operation | Required additions / preconditions | Result and change | Retry / errors |
|---|---|---|---|
| describe_isolation | Realization/version and required threat/control scope | Claimed and verified isolation capabilities, resource/data/effect constraints and limitations | Q; Base |
| validate_isolation_request | Exact intended action, required boundary/Policy controls, available conformance evidence | Suitability verdict; no authority created or containment assumed from module boundaries | Q; Base, CapabilityUnavailable |
| begin_isolated_execution | Admitted effect/Execution, current authority and claims, pinned confinement constraints | Isolation-use record and governed work handoff with explicit guarantees/effects; no unrestricted credential/resource access | X; Base, ToolFailure, PolicyViolation |
| stop_isolated_execution / inspect_isolation | Exact use reference; stop authority/revision for mutation | Stop acknowledgment with known/unknown effects, or current observed constraint/activity status | M/X for stop, Q for inspect; Base, ToolFailure |

**CTR-053.** Isolation guarantees MUST be demonstrable for the admitted threat scope; unsupported mandatory confinement prevents dispatch. Sandbox presence is not permission, tenant isolation proof or rollback guarantee. Adapter replacement MUST preserve isolation obligations and evidence or require new admission; silent weakening is prohibited.

## 27. Bootstrap and lifecycle dependency contracts

**CTR-054.** Bootstrap uses existing Plugin/Catalog inspection and admission operations plus a **bootstrap assessment** owned by Plugin Lifecycle. `assess_bootstrap_dependencies` takes exact declared contributions, dependency stages, existing admitted host references, trust/tenant constraints and expected graph revision. It returns an inspection/initialization order assessment with unresolved/cycle evidence (Q/M for recorded assessment; Base, CapabilityResolutionError, DependencyFailure). It MUST NOT return an executable CapabilityResolution binding to inactive offers.

| Term | Observable meaning |
|---|---|
| Declared contribution | Published claim of ability in a Plugin description, not necessarily validated |
| Inspected contribution | Description examined with provenance, no activation authority |
| Validated contribution | Required compatibility/configuration/trust assessments completed under Plugin admission; still not ordinary eligible provider |
| Bootstrap-eligible dependency | Accountable host has explicitly established and admitted a realization for the specified bootstrap duty and scope, already usable for that duty; not a bypass that makes an arbitrary inactive plugin usable |
| Active eligible provider | Plugin active (or permitted suitable degraded use), contribution currently eligible and suitable for ordinary resolution; invocation still governed |

**CTR-055.** Before invoking a dependency for initialization, its required scope MUST already be admitted and usable. A host bootstrap record identifies authority, realization/version, allowed duties/actions, tenant context, policy/evidence/accounting obligations, and exclusions from general discovery. Ordinary plugin implementations MUST NOT self-assign this status. Cycles lacking established dependencies fail explicitly. After normal activation, eligible offer publication has a separate acknowledgment. Lost publication acknowledgment yields an outstanding obligation, not repeat initialization effects.

```text
Plugin admission / activation
operator --discover/inspect request--> Lifecycle <--description evidence
Lifecycle --assess dependency declarations--> graph (NOT executable binding)
Lifecycle --validate trust/configuration/compatibility--> admission authority
operator <--validated admission acknowledgment----------- Lifecycle
Lifecycle --initialize using already admitted duties--> initialized / failure
Lifecycle --activate--> active revision --register/update eligible offer--> Catalog
operator <--activation + catalog obligation/result------- Lifecycle
Cycles / self-admission / missing trust => explicit failure, no hidden bootstrap.
```

## 28. Partial completion, effect uncertainty and reconciliation

**CTR-056.** Each cross-module operation MUST expose its sub-operation identities, owner-local acknowledgment/result revisions, known effects, incomplete postconditions and **outstanding obligations**. An obligation is a contract record: identity, owner, responsible requester/Principal, tenant, parent operation/effect, required action/target revision, due/retention bound, guarantee required, state (pending, satisfied, failed, requires intervention), last evidence/error, next safe action and reconciliation authority. These are obligation descriptors, not new canonical Execution states.

**CTR-057.** `inspect_obligations` returns authorized current obligations and evidence (Q). `reconcile_obligation` requires expected revision, exact outstanding identity, authorized evidence/remediation and its own operation identity (F). It records completion/failure/remaining uncertainty and separately links any newly required work. A repair to Artifact publication, audit custody or accounting MUST NOT repeat the already performed producing effect. Each owner commits only its own state. Parent completion requires the parent's declared postconditions, not merely every received acknowledgment.

| Situation | Required result and safe next operation |
|---|---|
| External effect confirmed; Artifact publication failed | Preserve completed external effect, exact ArtifactVersion/content evidence and failed publication obligation; retry/reconcile publication only under current policy |
| Effect confirmed; audit acknowledgment lost | Preserve effect evidence and audit custody unknown; query record by same evidence identity before resubmitting equivalent evidence; no repeat effect |
| Provider may have executed; caller lost response | Report unknown effect and outstanding usage; query authoritative effect identity/equivalence scope or require intervention; never assume none from timeout |
| Some claims consumed; final dispatch validation failed | Record no dispatch if proven, consumed approval/resource liability and releasable unused claims separately; no automatic approval refund or silent capacity reset |
| Owner committed; result acknowledgment lost | Equivalent repeated operation returns commit evidence within retained coverage; expected revision mismatch on a duplicate does not reapply the mutation |

**CTR-058.** Reconciliation adds observations; an unknown effect may later be established as none/partial/completed using attributable evidence. A previous false assertion is corrected by linked evidence, not overwritten. Contradictory observations remain visible under disclosure policy until an authorized resolution is recorded. A reconciliation operation can complete its investigation with effect still unknown; that does not satisfy an obligation requiring confirmation. Compensation creates new work and never rewrites the original effect status.

```text
Unknown-effect reconciliation
caller --dispatch request--> provider --possible effect--> target
caller <--lost/timeout acknowledgment--------------------- provider
caller --get_effect_status same identity--> invoker/provider evidence
       <--unknown + usage liability + obligations--------- owner
reconciler --new attributable evidence--> reconcile_effect
           <--new observation: none / partial / completed / still unknown
Only declared equivalent safe retry or separately authorized intervention follows.
```

```text
Cross-module partial completion
Action owner --governed handoff--> target --effect confirmed--> Action owner
Action owner --result reference--> consumer/composition owner
consumer --publish same ArtifactVersion--> Artifact owner --failure--> obligation
consumer --record audit evidence--> Evidence owner --unknown acknowledgment
consumer <--partial parent result: confirmed effect + two obligations
reconciler --query/repair publication and evidence only--> respective owners
consumer <--owner-local commit evidence / remaining obligations
No global atomic commit and no repeat of the original external effect.
```

## 29. Mandatory evidence and finite governance

**CTR-059.** Policy-required pre-dispatch evidence MUST name subject, evidence class, owner, required acknowledgment class, persistence/recovery/retention guarantee, allowed latency/deadline and validity. Dispatch proceeds only when that actual guarantee is established. Merely received or accepted-for-processing evidence is insufficient if the policy requires committed recoverable evidence. The contract does not promise perfect durability; a provider unable to meet the declared guarantee fails the protected operation before its effect.

**CTR-060.** Required post-effect evidence has a separately tracked obligation. If recording fails after the effect, report partial completion and reconcile; do not claim the effect never happened. Optional telemetry failure may produce a warning/collection-gap record and allow work to continue only when it was not a mandatory precondition. An optional logging configuration cannot disable required source attribution or audit.

**CTR-061.** Evidence recording uses an already established, bounded owner/Principal/policy scope for that recording duty. Its acknowledgment attests the record itself and need not recursively request a new identical audit approval. A configured evidence-obligation graph MUST terminate in an admitted accountable evidence root with explicit guarantees, scope and failure behavior. If the configured policy instead requires an unresolved cycle, return PolicyViolation/DependencyFailure and do not bypass it. No caller may self-declare an audit exemption. Root trust/admission authority remains SECURITY/GOVERNANCE; implementation realization remains replaceable.

## 30. Port template and instantiations

**CTR-062.** Every supported Port MUST publish the following twelve dimensions. The shared obligations below are part of **each** Port contract, not optional guidelines. The family referenced by a Port supplies its specific operation rows, owning module, inputs/results and conformance evidence. A Port describes supported operations/features explicitly; unsupported families need not be installed or implemented.

| Dimension | Mandatory contract content |
|---|---|
| 1. Purpose | Canonical ability and boundary; consumer does not depend on realization |
| 2. Supported operations | Versioned semantic names, required/optional operation set and unsupported features |
| 3. Request semantics | §2 envelope plus family predicates; pinned identities/revisions, exact owner and allowed dependency direction |
| 4. Result semantics | §3 envelope, postconditions, owner-local acknowledgment/effect scope and outstanding obligations |
| 5. Error semantics | §4 canonical categories and family specializations, safe causes and effect-aware recoverability |
| 6. Lifecycle obligations | SPEC's relevant state transitions, expected revision, definition/instance separation, stop/retire/recovery bounds |
| 7. Tenant obligations | Verified scope, authorized crossings, metadata isolation, preserved round-trip attribution |
| 8. Security obligations | External enforcement, current authority/Policy/Approval and trust/Secret restrictions; no actor self-authorization |
| 9. Resource obligations | Applicable §6/§15.3 units/claims/deadlines/uncertainty; explicit policy-permitted empty applicability if none |
| 10. Observability obligations | Source decisions/effects, Trace, audit/provenance and privacy; mandatory evidence guarantees, no private reasoning |
| 11. Versioning rules | §§31–32 and SPEC §11; independent Port/Capability/Adapter versions, behavior compatibility and migration |
| 12. Conformance expectations | §34 surface obligations and advertised guarantees with evidence/failure cases; no structural-only claim |

| Port surface | Purpose and supported family | Specific lifecycle / behavioral emphasis beyond template |
|---|---|---|
| Model Port | Inference and ModelCapabilities, §16 | Model definition versus invocation; cancellation only if supported; no Agent prerequisite |
| Agent Runtime Port | Bounded Agent participation, §12 | Instance lifecycle distinct from attempts; mediated proposals, public behavior only |
| Workflow Port | Explicit control/data flow, §11 | WorkflowState/Execution split, joins/waits and advertised checkpoint/resume |
| Tool Port | Bounded action, §14 | Proposal/preparation/dispatch/effect/reconciliation, exact effect identity |
| Memory Port | Kind-specific recall/retention, §19 | Advertised operation/kind support and forgetting limits |
| Knowledge Port | Source-attributed content/claims, §20 | Curation/publication/correction, no automatic authority |
| Retrieval Port | Scoped information selection, §21 | Filtering before disclosure, source/ranking meaning; standalone use |
| Artifact Port | Versioned work-product preservation, §22 | Identity/location separation, publication versus content and retention |
| Event Port | Governed fact delivery, §23 | Immutable fact and separate delivery/handling effects |
| Policy/Governance Port | Current decisions and obligations, §15.1 | Decision is not grant; fail closed on mandatory uncertainty/conflict |
| Evaluation Port | Criteria-based assessment, §24 | Execution status distinct from judgment; no Agent requirement |
| Observability Port | Trace, audit, provenance and telemetry, §§25, 29 | Separate operations/guarantees; finite evidence roots |
| Human Approval Port | Explicit Human decisions, §15.2 | Approved action scope, authenticated Humans, bounded non-replayable uses |
| Secret Port | Protected reference/use governance, §15.5 | Current material revision validity, no public material result |
| Sandbox/isolated-execution Port | Admitted confinement, §26.2 | Required threat/control scope and verifiable limits, not permission or rollback |
| Skill Port | Expertise assets, §17 | Version attribution; executable dependencies through consumers' mediated work |
| Identity / Tenant Ports | Verified subject and scope, §§15.1, 15.4 | Establishment differs from a caller assertion; scope never wildcard |
| Resource contract surface | Allowance/claim/usage arbitration, §§6, 15.3 | Concurrent conservation, unknown liability and clock/measurement meaning |

The extra surfaces are logical contracts under existing Architecture owners, not new mandatory modules. Provider dependency and consumer invocation MUST follow Architecture §5.2. Resolved HLC-01 introduces no direct Intelligence → Evaluation dependency.

## 31. Contract versioning and evolution

**CTR-063.** SPEC version governs domain meaning; Contract version governs operation/envelope behavior; Port version governs its supported boundary; Capability version governs offered guarantees; Plugin version identifies a contribution release; Adapter version identifies a realization; Artifact version identifies immutable content; state revision identifies an owner-local state observation. These dimensions MUST NOT be collapsed. Requests select exact interpretable contract versions; compatibility claims name supported ranges and behavior evidence.

**CTR-064.** Semantic contract versions comprise major, minor, patch and optional explicitly identified prerelease qualifier. Numeric components are nonnegative integers ordered lexicographically; ranges declare inclusive/exclusive bounds and whether prerelease versions are admitted. An unspecified prerelease rule excludes prereleases. Different prerelease schemes require an explicitly shared ordering definition; they cannot be guessed. No concrete textual/wire encoding is mandated. Initial 0.x compatibility MUST be explicitly declared as SPEC requires.

| Change | Compatibility obligation |
|---|---|
| New optional metadata ignored without behavioral effect | May be compatible if existing valid consumers/guarantees remain unchanged |
| New optional operation | May be compatible; support discovery explicit; existing consumers need not use it |
| New mandatory input/obligation without equivalent existing semantics | Breaking |
| Removing operation / accepted input / supported behavior | Breaking, with deprecation/replacement and affected-use treatment |
| Changed error category, retry eligibility, acknowledgment meaning or effect guarantees | Behaviorally assessed; breaking if existing valid interpretation is no longer safe |
| Changed security, tenant, claim, resource or retention guarantees | Compatibility-relevant; weakening cannot be hidden as a patch or optional extension |
| Changed state interpretation / lifecycle transition | Requires higher-level compatibility alignment and explicit migration where applicable |
| Description correction with unchanged obligations | Patch; wording alone cannot reclassify a semantic break |

**CTR-065.** Deprecation MUST identify versions/operations, replacement or absence, support/withdrawal conditions, migration evidence and ongoing/recovery obligations. Retired operations cannot silently reinterpret requests as a replacement. Migrations pin source/target, authorized transformation, loss and reversibility, scope, and preserved effects/accounting/provenance. An Adapter substitution cannot widen output meaning, weaken errors/isolation or silently accept provider extensions. Unknown mandatory extension semantics fail; optional extension omission must be explicitly allowed.

## 32. Guarantee profiles and vocabulary boundaries

**CTR-066.** A future profile is a versioned declared bundle of supported operations and guarantees, not a product tier or deployment topology. A declaration MUST identify its authority/owner, applicable SPEC/Contract/Port versions, required and optional operations, consistency/acknowledgment/deduplication coverage, recovery/failure domains, resource/evidence/tenant obligations, limitations, and conformance evidence references. Names and certification authorities remain Q-03/Q-04 governance decisions; this document finalizes no profile names.

Guarantees MUST identify subject and scope: which owner state survives which interruption, what acknowledged custody means, ordering domain, delivery/recovery bounds, retention/deduplication interval, clock/measurement uncertainty, and what happens outside those bounds. Missing stronger guarantees are not inferred. No profile automatically promises universal exactly-once effects, global order, exact replay or perfect durability. Supported-set declarations are valid before named profile governance exists, without claiming official certification.

### 32.1 Minimal interoperable vocabularies

**CTR-067.** Standardize only the following contract meanings and preserve SPEC's existing values. Each extension vocabulary MUST have explicit namespace/owner/version, applicability and compatibility, without appointing a universal global authority.

| Vocabulary | Required semantic boundary |
|---|---|
| Effect status | none, partial, completed, unknown as SPEC §10 and §3.3; no competing top-level taxonomy |
| Effect classification | read/disclosure, mutation, external communication, irreversible, unknown/mixed are descriptive declared control classifications; multiple may apply; classifications do not replace effect status |
| Acknowledgment stages | Exact §3.2 statements with subject/owner/guarantee; not a total-order universal protocol |
| Error recoverability | terminal, potentially retryable, requires intervention, unknown; category alone never permits retry |
| Capability multiplicity | Exactly one selected provider per atomic requirement by default under SPEC §3; explicit set must define cardinality, membership/aggregation/failure semantics |
| Content/reference status | Resolvable/access permitted, unavailable, unresolved, or governed tombstone; withheld existence must not imply absence. Content address/location is not identity |
| Event delivery status | pending, delivered, failed, unknown for delivery attempts; consumer acceptance/completion separately evidenced |
| Artifact relation types | derived-from (source product → input/source), depends-on (source → prerequisite), supersedes (new → old), cites (source → cited target), contains (container → member), evaluates (evaluation artifact → subject). Exact versions when meaning requires; SPEC acyclicity/cardinality rules preserved |
| Resource quantity | Dimension, unit, amount kind, precision, uncertainty, accounting window and conversion evidence; no fixed currency/tariff |

Artifact business types, domain Roles, subject taxonomies, business outcome labels and blueprint domain contents remain extensions. Blueprints must expand to valid existing compositions with pinned revisions and provenance; no separate privileged runtime or oversized business ontology is established. Standard defaults cannot contradict SPEC cardinalities.

## 33. Contract inventory matrix

All rows require **T** = verified TenantContext/current authorized initiator and **E** = Trace plus applicable provenance/audit under §§2–3, 25, 29. Query evidence identifies source/freshness and protected disclosures. “Effectful” distinguishes target mutation/work from disclosure, metering and evidence that can accompany reads. Errors include Base (§6.3); listed extras are family-specific. Future profile entries name **guarantee dimensions to be assigned**, not approved profile names. Retry codes are fully defined in §5. The operation tables provide the exact per-operation mutation owner and effects.

| Surface | Owning module | Primary consumer | Primary operations / section | Authoritative state changed? | Effectful? | Retry conditions | Canonical errors beyond Base | Tenant context? | Trace/provenance? | Future profile dimensions |
|---|---|---|---|---|---|---|---|---|---|---|
| Definitions | Respective definition owner | Applications/admin/composers | validate/publish/deprecate/retire/get/resolve, §7 | Yes for publication/lifecycle | Local changes/disclosure | Q/M | DependencyFailure | T | E | Publication, version compatibility |
| Catalog | Capability Catalog | Resolver/composers | register/status/withdraw/discover/inspect/health, §8 | Offers/status | Local changes/disclosure | Q/M | PluginFailure, CapabilityUnavailable | T | E | Scoped discovery/freshness |
| Resolution | Capability Resolution | Applications/Execution/Coordination/Extension | resolve/explain/validate/refresh, §9 | Immutable decisions | Decision record; no invocation | Q/M | CapabilityResolutionError, CapabilityUnavailable | T | E | Closure, deterministic selection |
| Execution | Execution Coordination | Applications/Coordination | request/admit/reject/cancel/suspend/resume/status, §10 | Attempt/context/checkpoints | Local state; work through invokers | Q/M/X/F | ExecutionFailure, DependencyFailure, CapabilityUnavailable | T | E | Admission/recovery/cancellation |
| Direct capability | Direct driver plus invoking plane | Applications | invoke_capability, §10 | Attempt and invoked state | Per requested capability | X | Invoked-family errors | T | E | Independent invocation/effects |
| Workflow | Workflow driver; Execution for attempts/checkpoints | Applications/Execution | start/advance/signal/wait/resume/cancel/checkpoint, §11 | WorkflowState and owner-specific records | Step-dependent | Q/M/X | DependencyFailure, ExecutionFailure | T | E | Branching/wait/durability |
| Agent Runtime | Agent driver | Applications/Execution | activate/invoke/suspend/stop/inspect, §12 | Agent instance state | Governed proposals/work | Q/M/X | ExecutionFailure, ModelFailure | T | E | Bounded public behavior |
| Team/Role | Organizational Composition | Applications/Work Coordination | create/validate composition, assign/revoke role, §13 | Composition/assignments | Local responsibility changes | Q/M | CapabilityResolutionError | T | E | Staffing/composition/isolation |
| Goal/Plan/Task/Outcome | Work Coordination | Applications/Teams | create/select/assign/accept/assess/transition, §13 | Work/acceptance records | Local accountability changes | M/F | DependencyFailure | T | E | Versioned criteria/acceptance |
| Delegation | Work Coordination; Resource owner for allocations | Authorized Actors/Teams through Actors | delegate/accept/reject/revoke, §13.1 | Delegation and separate claims | Responsibility/capacity changes | M/F | DependencyFailure | T | E | Attenuation/chain/revocation |
| Tool/Action | Action Mediation | Direct/Workflow/Agent/Service/Human callers | inspect/validate/prepare/dispatch/status/reconcile/compensate, §14 | Preparations/effect records | External/local declared effects | Q/M/X/F | ToolFailure, CapabilityUnavailable | T | E | Equivalence/unknown effects |
| Identity/Authorization/Policy | Respective Governance owners | Protected boundary owners | verify/establish/evaluate/authorize, §15.1 | Identity and decision records | Decision/verification effects | Q/M/F | DependencyFailure | T | E | Current authority/revocation |
| Approval/HumanApproval | Approval Management | Governance-driven protected invokers/Humans | request/decide/validate/reserve/consume/revoke/expire, §15.2 | Approval/use records | Bounded use consumption | Q/M/F | HumanRejected | T | E | Human attribution/replay bounds |
| Resource | Resource Admission and Accounting | Boundary owners/Coordination | check/reserve/consume/release/reconcile/query, §15.3 | Allocation/claim/usage | Capacity and consumption | Q/M/F | None beyond Base | T | E | Concurrent conservation/metering |
| Tenant boundary | Tenant Governance; evidence/data owners for transfer | Ingress/invokers | bind/validate/authorize crossing/record transfer, §15.4 | Scope and crossing evidence | Decisions; transfer separately governed | Q/M/F | None beyond Base | T | E | Scope propagation/crossing |
| Secret | Secret Access | Authorized protected realizations | resolve/authorize/record/validate revision, §15.5 | Use evidence/status observations | Protected use/disclosure boundary | Q/F | None beyond Base | T | E without material | Rotation/revocation/least disclosure |
| Model | Model Interaction | Applications/Execution | describe/validate/invoke/cancel/report usage, §16 | Invocation/use evidence | Inference, disclosure, charges | Q/M/X/F | ModelFailure, CapabilityUnavailable | T | E | Modalities/output/usage |
| Skill | Skill Asset | Applications/Actors via Execution | inspect/validate/resolve/use, §17 | Expertise use/dependency evidence | Consumption; actions via consumer | Q/M/X | DependencyFailure, CapabilityResolutionError | T | E | Versioned expertise/dependencies |
| Context | Context Assembly | Applications/Execution/Intelligence | assemble/validate/derive/redact, §18 | Derived values/lineage | Information transform/disclosure | Q/M/X | DependencyFailure | T | E | Trust/freshness/lineage |
| Memory | Respective Memory module | Applications/Execution/Intelligence/Retrieval | read/write/query/forget, §19 | Entries/corrections/disposition | Read/write/disclosure | Q/M/X/F | CapabilityUnavailable | T | E | Kind-specific consistency/retention |
| Knowledge | Knowledge Curation | Applications/Retrieval/Context | publish/query/get/supersede, §20 | Knowledge records/collection | Content/disclosure | Q/M/F | None beyond Base | T | E | Source/validity/curation |
| Retrieval | Retrieval | Applications/Execution/Intelligence | query/explain, §21 | Query evidence, not source content | Disclosure and declared usage | Q/X | DependencyFailure, CapabilityUnavailable | T | E | Filtering/ranking/source versions |
| Artifact | Artifact Management | Applications/producers through allowed consumers | create/version/get/relate/publish/withdraw/supersede/dispose, §22 | Products/versions/relations | Content/publication/disposition | Q/M/F | DependencyFailure, CapabilityUnavailable | T | E | Preservation/access/retention |
| Event | Event Coordination; source/consumer own facts/handling | Authorized source/consumer modules | publish/deliver/acknowledge/fail, §23 | Delivery records | Delivery; consumer effects separate | M/X/F | DependencyFailure | T | E | Custody/order/duplicate handling |
| Evaluation | Evaluation Management | Applications/Coordination/Artifact/Extension | describe/request/execute/record/compare, §24 | Evaluation and results | Assessment/usage | Q/M/X/F | ExecutionFailure, DependencyFailure | T | E | Criteria/judgment/independence |
| Observability | Observation Collection / Evidence and Provenance | All permitted emitters | trace/audit/provenance/telemetry, §25 | Evidence records | Recording/disclosure | M/F | None beyond Base | T | E; finite roots | Mandatory evidence/collection gaps |
| Plugin/Adapter | Plugin Admission and Lifecycle; Catalog for offers | Authorized administration | inspect/validate/admit/configure/initialize/activate/health/stop/retire, §26 | Lifecycle/configuration/evidence | Initialization/activation may affect resources | Q/M/X/F | PluginFailure, DependencyFailure, CapabilityResolutionError | T | E | Admission/isolation/replacement |
| Sandbox | Action Mediation and admitted isolation realization | Action Mediation | describe/validate/begin/stop/inspect, §26.2 | Isolation-use records | Confined work, not blanket authority | Q/M/X | ToolFailure, CapabilityUnavailable | T | E | Threat-scope confinement |
| Bootstrap | Plugin Lifecycle / established host authorities | Authorized lifecycle administration | assess_bootstrap_dependencies, §27 | Assessment/admission records | No unadmitted execution | Q/M | CapabilityResolutionError, DependencyFailure | T | E | Finite trust/dependency roots |
| Partial completion | Each original obligation owner | Parent composition/reconciler | inspect/reconcile_obligation, §28 | Owner-local repair records | Repair only; new effects explicit | Q/F | Original family causes | T | E | Partial progress/reconciliation |

## 34. Observable conformance obligations

**CTR-068.** Each supported surface MUST be independently testable against its observable postconditions, failures, ownership, and guarantees. Tests need not share a representation or deployment. The following obligations identify future cases; this phase creates no test suite or certification.

| Surface | Observable proof obligation |
|---|---|
| Shared envelope/result | Invalid tenant or Principal assertion is denied; preserved identity/revision round trip; accepted-for-processing does not report effect completion |
| Definition/lifecycle | Same published version cannot change content; stale expected revision fails; retirement does not mutate old records |
| Catalog | Visible-but-inactive offer is inspectable only as allowed and never eligible for executable selection; status needs authoritative activation evidence |
| Resolution | Hard-constraint violation excludes preferred provider; optional omission and closure are visible; ambiguous choice stays unresolved; result grants no invocation authority |
| Execution/direct | Direct retrieval/model/tool works without Agent/Team/Goal; previously begun execution cannot become rejected; repeated creation does not duplicate attempt |
| Workflow | Duplicate signals cannot satisfy joins twice; invalid transitions fail; checkpoint/resume preserves current restrictions, earlier effects and consumption |
| Agent Runtime | A proposed ungranted action is blocked outside Agent; private reasoning absent still conforms; instance status does not overwrite attempt history |
| Team/Role | Human and Service assignments work without Agents; Role change does not fabricate permissions; Team is not an acting Actor |
| Goal/Plan/Task/Outcome | Execution success alone cannot mark Task success or Goal achievement; selected revisions and acceptance evidence are preserved |
| Delegation | Child authority/capacity cannot exceed valid grant/allocation; chain and current revocation are checked; supplementary grant is separate |
| Tool/Action | Validation/preparation causes no target effect; unknown dispatch result stays unknown; duplicate equivalent effect request cannot independently dispatch twice under advertised guarantee |
| Identity/Authorization/Policy | Supplied Principal name alone cannot impersonate; stale decision cannot dispatch after effective revocation; mandatory policy conflict prevents action |
| Approval | Two concurrent users cannot exceed one permitted use; modified action rejected; no silence-as-consent; consumption does not report effect success |
| Resource | Concurrent sibling reservations conserve parent budget; duplicate usage is not double-charged; unknown charges survive expiry/cancel; mismatched units fail |
| Tenant | Cross-scope references require grants from relevant authorities and both policies; destination use preserves source lineage; no relabeling |
| Secret | Public response contains reference/validity only; revocation affects next use; no Secret in telemetry/evidence |
| Model | Different realization preserves declared output/error/usage/privacy meaning; invalid structured output is not treated as truth; no Agent required |
| Skill | Use attributes exact version and cannot auto-install, grant authority or change configuration; caller mediates executable actions |
| Context | Derived/redacted data retains source/trust restrictions; instruction-like content cannot become Policy |
| Memory | Supported kind semantics and forgetting limits hold without Agent/vector implementation; working Memory cannot rewrite driver state |
| Knowledge | Unverified assertion remains labeled; supersession preserves prior claim and source |
| Retrieval | Unauthorized source content/existence is filtered before disclosure; source revisions and score meaning retained; standalone operation succeeds |
| Artifact | Moving content location preserves Artifact identity/version; exact approved version does not become another version; partial publication failure is repairable without reproducing source effect |
| Event | Delivery duplicate preserves fact identity; receipt does not imply handling/effect; out-of-order policy is visible |
| Evaluation | Failed subject and failed assessor produce different results; result can be inconclusive; incompatible comparisons are not silently scored |
| Observability/evidence | Optional telemetry gap differs from failed mandatory pre-evidence; trace/audit/provenance stay distinct; no private reasoning required |
| Plugin/Adapter | Plugin cannot self-admit; inactive dependency cannot become ordinary executable binding; equivalent replacement preserves canonical errors/governance |
| Sandbox | Unsupported required isolation prevents dispatch; stopping reports residual/unknown effects rather than claiming rollback |
| Bootstrap | Unsupported dependency/evidence cycle fails; only explicitly admitted roots perform bootstrap duties |
| Claims/partial completion | Losing one prerequisite before dispatch prevents handoff; late revocation reports in-flight scope; confirmed effect plus failed audit/publication retains separate repair obligations |

**CTR-069.** A conformance declaration MUST identify implementation/release, all applicable SPEC/Architecture/Contract/Port/Capability versions, supported operations, extensions, profiles or explicit supported sets, claimed guarantees/failure domains, evidence and limitations. A claim cannot silently include unsupported optional surfaces. Structural compatibility alone is insufficient. Replacement tests must preserve errors, context, authority, effects and resource semantics, not just output shape.

## 35. Open questions, risks, and higher-level dispositions

### 35.1 SPEC questions

| ID | Disposition here | Next decision owner | Exit criteria |
|---|---|---|---|
| Q-02 | Carried forward; single-tenant ownership and explicit crossing enforced (§15.4) | GOVERNANCE / SPEC / SECURITY | Deliberately accepted semantic amendment if true co-ownership is required; no amendment inferred here |
| Q-03 | Partially resolved: namespace owner/version/reference and evidence required (§§8, 32); no global authority appointed | GOVERNANCE, then CONFORMANCE | Authority/delegation/registration/certification rules approved and referenced by profiles |
| Q-04 | Partially resolved: modular supported-set and profile declaration mechanism (§§30, 32–34) | CONFORMANCE / GOVERNANCE | Named, versioned guarantee bundles and certification evidence rules accepted |
| Q-05 | Partially resolved: authority/decision/obligation/conflict representations, fail-closed mandatory rules (§15.1) | SECURITY / GOVERNANCE | Applicable organizational/retention/exception precedence explicitly approved; no legal authority invented by contracts |
| Q-06 | Partially resolved: amount/unit/precision/uncertainty/reservation/reconciliation semantics (§15.3) | Resource CONTRACT profiles / GOVERNANCE | Chosen domain units, precision/time policies and permitted uncertainty/overrun parameters have accountable approval |
| Q-07 | Partially resolved: acknowledgment/custody/recovery/order/retention guarantees declared (§§3, 11, 23, 29, 32) | CONFORMANCE / SECURITY / capability CONTRACT profiles | Required guarantees for each approved profile and failure domain are testable; no universal exactness claim |
| Q-08 | Partially resolved: narrow shared vocabulary and existing multiplicities preserved (§32.1) | CONTRACT vocabulary governance / GOVERNANCE | Additional relation/business type/blueprint vocabularies approved only as needed with versions; no universal business ontology |

DEC-01 remains accepted: direct operational results do not automatically become canonical Outcomes. It needs no new question or amendment in this layer.

### 35.2 Architecture risks

| ID | Disposition here | Next decision owner | Exit criteria |
|---|---|---|---|
| R-01 | Preserved; contracts attach shared meanings to Kernel and mutations to existing modules | ARCHITECTURE / GOVERNANCE | Confirm accepted Kernel allocation; implementations demonstrate no hidden core-to-adapter coupling |
| R-02 | Partially resolved: inspection/assessment versus usable bootstrap/active eligibility and cycle failure (§27) | SECURITY / GOVERNANCE / CONFORMANCE | Initial trust-root admission procedure approved; bootstrap/eligibility guarantees proven |
| R-04 | Behavioral contract resolved: per-effect dispatch ordering, bounded claims, revocation and no stale-check authorization (§6) | SECURITY / CONFORMANCE / implementation ADRs | Threat/failure assumptions and concrete mechanism demonstrate joint validity and concurrency guarantees; deployments unable to do so must fail closed |
| R-05 | Resolved for contracts: activities mapped to existing Plugin states (§26) | SPEC if future lifecycle expansion is desired | No new canonical state without explicit higher-level amendment |
| R-06 | Carried forward with enforceable admission/isolation preconditions (§26.2) | SECURITY / implementation ADRs / CONFORMANCE | Evidence demonstrates actual containment/trust requirements of shared realization; logical boundaries alone insufficient |
| R-07 | Behavioral contract resolved: owner-local acknowledgment, effect uncertainty and obligation reconciliation (§28) | CONFORMANCE / implementation ADRs | Failure-injection evidence demonstrates retained partial progress and no duplicate source effects |
| R-08 | Partially resolved: mandatory evidence guarantees and finite admitted roots (§29) | SECURITY / GOVERNANCE / CONFORMANCE | Minimum evidence, root trust, persistence/failure guarantees and privacy/retention policy approved and proven |

The earlier resume-rejection issue is corrected in SPEC §5.8 and Architecture §8.3. No old R-03 workaround or invented Execution state is introduced. Intervention remains an obligation or recovery condition rather than an Execution lifecycle state.

### 35.3 New contract risks and contradiction

| ID | Finding | Boundary / correction owner |
|---|---|---|
| HLC-01 | RESOLVED upstream: direct Intelligence → Evaluation invocation was removed from Architecture §4.7, preserving the exhaustive §5.2 dependency matrix. Evaluation is orchestrated by an allowed consumer; Intelligence may only reference existing authorized Evaluation evidence without a direct module dependency. | No further contract-layer action required unless Architecture changes again. |
| CR-01 | Claim ordering across independent owners can be unavailable during failures | §6 requires fail-closed dispatch unless joint validity is demonstrable. SECURITY/CONFORMANCE must test failure domains; there is no availability promise during uncertainty |
| CR-02 | Deduplication evidence may expire before a delayed retry | §§5, 28 require status coverage and intervention outside it; profile retention and maximum retry horizon must align |
| CR-03 | Approval may be consumed although later dispatch fails | §6 preserves consumed use separately from actual effect; no automatic replay/refund. GOVERNANCE must define new-entitlement approval practice |
| CR-04 | Confidentiality restrictions may hide details needed by a consumer to diagnose a failure | Results retain safe categories/correlation and authorized evidence references; SECURITY defines redaction and review access, not cross-tenant data leakage |
| CR-05 | Reference/record loss can undermine a historical guarantee without changing immutable identifiers | Profiles declare preservation/failure bounds; unavailability is explicit. Artifact/evidence owners must not return fabricated historical content |
| CR-06 | Generic lifecycle publication could accidentally activate a specialized concept | §7 defers to specialized lifecycles; Plugin validation/publication is distinct from activation. CONFORMANCE must test this boundary |
| CR-07 | Core enforcement/evidence operations could recursively require themselves | §§27, 29 require explicit bounded admitted roots and cycle failure; root authority is a SECURITY/GOVERNANCE decision, not a caller exception |

HLC-01 has been resolved at the architectural layer and no longer blocks contract finalization. The remaining contract risks are intentionally carried to Security, Governance, Conformance, profiles, or implementation ADRs according to their assigned owners.

## 36. Traceability and final self-review

### 36.1 Requirement anchors

| Governing requirements | Contract anchors |
|---|---|
| Intent §§3–12, 21–25, 38–42; Architecture AR-01–AR-08, AR-13 | CTR-001–CTR-004, CTR-028, CTR-041–CTR-046, CTR-052, CTR-062–CTR-069 |
| SPEC S-01–S-08; Architecture AR-04, AR-09, AR-14 | CTR-004–CTR-016, CTR-023–CTR-027 |
| SPEC S-09–S-12, E-01–E-11; Architecture AR-05, AR-11, AR-17 | CTR-005–CTR-022, CTR-027–CTR-030, CTR-033–CTR-040 |
| SPEC C-01–C-06; Architecture §§4.3, 7, AR-21 | CTR-025–CTR-026, CTR-054–CTR-055 |
| SPEC D-01–D-05, B-01–B-04; Architecture AR-18, §9 | CTR-017–CTR-022, CTR-032, CTR-036–CTR-038 |
| SPEC A-01–A-05; Architecture §§4.8–4.10, 10.3 | CTR-043–CTR-047, CTR-056–CTR-058 |
| SPEC ERR-01–ERR-02, V-01–V-09; Architecture AR-22–AR-23 | CTR-011–CTR-016, CTR-052, CTR-063–CTR-069 |
| SPEC DEC-01, I-01–I-20; Architecture AR-07, §13 | CTR-028–CTR-032, CTR-041–CTR-050, CTR-068–CTR-069 |
| Architecture AR-12, AR-15–AR-16, R-02, R-04–R-08 | CTR-019–CTR-022, CTR-048, CTR-053–CTR-061 |

All operation rows are normative through CTR-003 and their family requirements. Inventory §33 and proof obligations §34 are the map for later representation contracts and conformance cases. HLC-01 is resolved by the accepted Architecture correction and introduces no direct Intelligence → Evaluation contract.

### 36.2 Thirty completion checks

| # | Check | Review result / anchor |
|---|---|---|
| 1 | No implementation technology selected | Pass — §1, §30 |
| 2 | No canonical wire format | Pass — semantic fields/references only, §2 |
| 3 | No programming-language interface | Pass — operation semantics, not signatures |
| 4 | Every authoritative mutation identifies owner | Pass — family owners, per-row changes, §33 |
| 5 | Explicit revisions | Pass — CTR-013 and every mutation row |
| 6 | Explicit tenant scope | Pass — CTR-005–CTR-006, CTR-039 |
| 7 | Explicit Principal identity | Pass — §2, CTR-035 |
| 8 | Availability distinct from authorization | Pass — CTR-025–CTR-026 |
| 9 | Resolution distinct from invocation | Pass — §§9–10 |
| 10 | Admission distinct from effect | Pass — §3.2, §10 |
| 11 | Acknowledgment distinct from effect | Pass — CTR-008–CTR-010 |
| 12 | Timeout not proof of no effect | Pass — CTR-034, §28 |
| 13 | Retry accounts for uncertainty | Pass — CTR-014–CTR-016, CTR-058 |
| 14 | Bounded non-replayable Approval use | Pass — CTR-017–CTR-022, CTR-036 |
| 15 | Concurrent Budget conservation | Pass — CTR-037–CTR-038 |
| 16 | Delegation attenuates authority | Pass — CTR-032 |
| 17 | Direct invocation needs no Agent | Pass — CTR-028 |
| 18 | Retrieval needs no Agent | Pass — §21 |
| 19 | Model needs no Agent | Pass — §16 |
| 20 | Team may contain Humans/Services | Pass — CTR-031 |
| 21 | Operational result distinct from Outcome | Pass — CTR-009, CTR-028, CTR-031 |
| 22 | Artifact identity storage-independent | Pass — §22 |
| 23 | Event delivery distinct from consumer effect | Pass — CTR-048 |
| 24 | Evaluation execution distinct from judgment | Pass — CTR-049 |
| 25 | No private reasoning requirement | Pass — CTR-030, CTR-050 |
| 26 | Plugins cannot self-authorize | Pass — CTR-051, CTR-055 |
| 27 | Adapter replacement preserves errors/governance | Pass — CTR-052, CTR-065, CTR-069 |
| 28 | Cross-module partial completion representable | Pass — CTR-056–CTR-058 |
| 29 | Independent observable testing | Pass — §§30, 33–34; resolved HLC-01 preserves the declared dependency boundaries |
| 30 | Required Q/R identifiers tracked | Pass — §35 lists every required identifier, owner and exit criterion |

### 36.3 Security and replacement review

| Security question | Required observable answer |
|---|---|
| Can a caller forge TenantContext or select arbitrary Principal? | No accepted operational use — verified binding/current authority required (§§2, 15) |
| Can a resolved provider bypass authorization or a Plugin self-admit? | No — selection/admission/dispatch separated (§§9, 26–27) |
| Can an Agent directly invoke a protected Tool outside mediation? | No conforming path — external enforcement at Tool boundary (§§12, 14) |
| Can Approval replay or concurrent siblings overspend? | No — owner-arbitrated claims and dispatch ordering (§6, §15) |
| Can stale grants survive resume or unknown effects be blindly retried? | No — current checks and effect reconciliation (§§10–11, 28) |
| Can telemetry expose Secrets or Context become Policy? | No — protected material excluded; explicit governed publication required (§§15.5, 18, 25) |
| Can Skill instructions mutate governing configuration? | No — consumer-mediated actions and separate publication (§17) |
| Can an Adapter silently weaken tenant isolation? | No conforming substitution — compatibility/admission evidence required (§§26, 31, 34) |

Model, Agent Runtime, Workflow, Memory, Retrieval, Tool, Event, Artifact storage and Policy realizations are replaceable at their declared Ports. Stateful replacement may require explicit migration and re-admission; it cannot redefine canonical meaning. Deployment topology may change while preserving the same failure, claim, identity, scope and evidence guarantees. These are contract obligations requiring future proof, not claims about an implemented system.

**Recommended next document:** `security/SECURITY.md`, defining the threat model, trusted admission/evidence roots, revocation and dispatch trust assumptions, tenant enforcement, and policy/exception authorities required by the now-explicit contracts. `conformance/CONFORMANCE.md` should subsequently turn §34 into versioned proof obligations and approved profiles. None of these follow-up documents, schemas, or implementations is created in this phase.
