# Lego AI Operating Layer — Security Specification

**Security specification version:** 0.1.0  
**Status:** PROPOSED — FOR CANONICAL REVIEW  
**Authority:** [intent.md](../intent.md) 1.0 → [SPEC.md](../SPEC.md) 0.1.0 → [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) 0.1.0 → [CONTRACTS.md](../contracts/CONTRACTS.md) 0.1.0 → [PLUGIN-SPEC.md](../plugin-spec/PLUGIN-SPEC.md) 0.1.0 → this document.  
**Scope:** Technology-neutral trust, security decisions, enforcement obligations, threat assumptions, evidence, and safe failure.

## 1. Authority, interpretation, and phase boundary

**SEC-001.** This specification MUST preserve upstream concepts, ownership, cardinalities, lifecycle states, capability and Port meaning, Plugin semantics, dependency direction, tenant scope, effects, resource accounting, and behavioral contracts. SPEC §1 supplies normative language. Every requirement below is cumulative with its governing contracts. A contradiction MUST identify exact upstream sections and their responsible owner; only the affected security rule remains unfinalized pending upstream correction. No security convenience authorizes a silent amendment.

No new higher-level contradiction was identified. Contracts §1.1 HLC-01 remains resolved by Architecture §§4.7 and 5.2: Intelligence may reference authorized Evaluation evidence but does not directly invoke Evaluation. Security evaluation is orchestrated by a consumer permitted to use the relevant contracts. Previously begun Execution work cannot later become rejected; intervention remains an obligation or recovery condition under SPEC §5.8, not a new state.

**SEC-002.** This document defines security semantics, not mechanisms or deployed policy. It selects no identity provider, authentication protocol, authorization engine, policy language, cryptography, certificate/signature format, Secret store, sandbox, container, VM, network/firewall technology, cloud, Kubernetes, SIEM, SOC tooling, scanner, SBOM format, or package-signing system. No IAM syntax, security schema, middleware, deployment configuration, test suite, or implementation is created. Local and distributed realizations MUST provide the same declared observable guarantees, with explicit failure assumptions.

**SEC-003.** Security terms MUST retain existing meanings: Identity, Principal, TenantContext, Permission, Policy, Approval, Secret, Claim, ExecutionContext, TrustBoundary, Evidence, Audit and Provenance. A **Grant** is the granting form of Permission; it is not a new authority-bearing entity class. Terms such as policy authority, exception, risk classification, trust assessment and root designation describe governed records or responsibilities under existing owners. They do not create new domain lifecycle states, universal administrators or security planes outside Architecture.

## 2. Principles, objectives, and invariants

**SEC-004.** No implicit trust or action authority MUST arise from location, network origin, process sharing, Plugin packaging, Team membership, Role, Actor identity, ownership, prior success, reference possession, Capability availability, resolution, or generated content. Every protected use MUST establish its current applicable authority. Protected use includes sensitive read/disclosure, state mutation, resource consumption and control administration, not just externally visible writes.

**SEC-005.** Trust MUST be a scoped assessment binding subject/version, action/duty, resource, tenant, purpose, time/validity, environment assumptions, evidence, assessor authority and limitations. Publisher identity verification does not verify Plugin behavior; integrity of a release does not establish safe behavior; behavioral conformance does not issue permissions. “Trusted” without scope MUST NOT satisfy a mandatory decision predicate. Default unassessed content and realizations supply claims, not authority.

**SEC-006.** Security objectives are authentication and authorization integrity, least privilege, tenant isolation, confidentiality, information and supply-chain integrity, effect safety, resource conservation, Secret protection, accountable decisions, evidence integrity, safe failure, and availability within declared guarantees. Any non-repudiation claim MUST identify the disputed action/subject, evidence custody, verifier, threat assumptions and limitations; attribution alone MUST NOT be represented as such a guarantee. Perfect confidentiality, availability, containment or replayability is not asserted.

The following invariants summarize mandatory rules specified in later sections:

| Invariant | Requirement anchors |
|---|---|
| No authority from untrusted content; no Agent self-authorization | SEC-038–042, SEC-066–069 |
| No protected effect without current authorization and valid obligations | SEC-016–021, SEC-027–030 |
| No implicit wildcard tenant or unapproved cross-tenant disclosure | SEC-060–062 |
| No Plugin self-admission or self-grant | SEC-046–050 |
| No Secret material on public contract surfaces | SEC-057–059 |
| No stale Approval replay or copied-budget double-spend | SEC-031–034, SEC-063–065 |
| No security weakening through Adapter replacement | SEC-050, SEC-087 |
| No historical effect erasure or repeated effect to repair evidence | SEC-029–030, SEC-075–077 |
| No probabilistic model as sole security authority | SEC-026, SEC-038–042 |
| No security exception without an explicit governed record | SEC-078–080 |

## 3. Assets, trust domains, and ownership

**SEC-007.** Security decisions MUST identify the asset and authoritative owner; enforcement cannot silently take ownership of business or operational state. Asset inventories MUST include private content and existence/relationship metadata, configuration and recovery copies, and authority/evidence needed to interpret them.

| Asset | Authoritative responsibility / security concern |
|---|---|
| Tenant data, Context, Memory, Knowledge and retrieval results | Respective information modules; confidentiality, integrity, scope, retention and provenance |
| Artifacts, versions, relationships and content references | Artifact Management; exact content meaning, publication and access independent of location |
| Identity evidence, Principals, Permissions and grants | Identity/Principal and Authorization; authenticity, issuer entitlement, validity and revocation |
| Policy and security configuration | Policy Decision and respective configuration owners; applicability, authority, revisions and non-waivable restrictions |
| Approval decisions/use claims | Approval Management; exact proposal, approver authenticity, permitted-use conservation |
| Budgets, Quotas, Limits, reservations and liabilities | Resource Admission and Accounting; no double-spend, forged usage or unsafe refund |
| Plugin/Adapter realizations, releases and dependencies | Plugin Lifecycle and accountable release owners; admission, integrity, isolation and replacement |
| Capability offers, aliases, bindings and health | Catalog, Resolution and source evidence owners; no spoofing, stale eligibility or silent substitution |
| Models, prompts, Skills, Tools and credentials | Respective definition/invoking owners; untrusted behavior, data-use constraints, governed effects; credentials stay under Secret Access |
| ExecutionContext, checkpoints, Workflow/Agent state | Execution Coordination and respective drivers; immutable scope/ceiling and safe recovery |
| Events and delivery/handling records | Source, Event Coordination and consumer owners; fact identity distinct from effect authority |
| Audit, Trace, Provenance and evaluation evidence | Respective evidence/observation/evaluation owners; custody, confidentiality, completeness and validity |
| Bootstrap designations and namespace authority | Accountable administrative/contract authorities through existing Governance/Lifecycle records; bounded root duties, transfer and revocation |

**SEC-008.** User/external caller, Application, runtime, Governance, Plugin, Adapter, Model Provider, Tool Provider, external system, Human operator, evidence system, Secret system and resource accounting are logical trust domains. A process may contain several domains; a domain may span several deployments. Crossing obligations follow authority, data and effect boundaries, never merely network hops. Publicly shared definitions do not carry an implicit shared operational Principal or TenantContext.

**SEC-009.** Each admitted composition MUST declare its relevant attacker capabilities and trusted enforcement assumptions, including compromise of callers, dependencies, privileged code, shared-host components, time/freshness sources, state owners and evidence custody. If an attacker can alter an enforcement owner or read its protected memory under the admitted threat model, claims depending on that owner's integrity/confidentiality require independent effective protection or MUST NOT be made. Risks excluded from a profile MUST be explicit; exclusions cannot waive an applicable canonical requirement.

## 4. Structured threat model

**SEC-010.** The following threats MUST be assessed when their surfaces are supported. “Required control semantics” refers to observable obligations, not products. Residual risks remain within declared assumptions and require the named proof owner; this table is not a claim of tested security.

| Threat | Asset | Attacker capability | Boundary | Security objective | Required control semantics | Residual risk / next proof owner |
|---|---|---|---|---|---|---|
| Malicious external caller | Data, action authority | Forges request fields/references | External ingress | Authenticated scope and safe input | Verify identity/tenant, validate payload and bound resources before disclosure | Ingress exhaustion; CONFORMANCE / ingress ADR |
| Compromised Principal | Grants and data | Uses valid but stolen authority | Authorization/use | Limit scope and duration | Current restrictions, purpose, revocation, approval and resource gates | Abuse within still-valid scope; GOVERNANCE / security evaluation |
| Overprivileged Service | Protected target/credentials | Applies own maximum privilege to requests | Deputy dispatch | Attenuated authority | Intersect requester, delegated scope, service ceiling and policy | Malicious entitled operator; CONFORMANCE / GOVERNANCE |
| Malicious/compromised Plugin | Host/tenant/Secrets | Executes hostile admitted code | Plugin-to-host/data | Containment and least privilege | Threat-scoped isolation, mediated effects, no self-admission | Enforcement-base compromise; isolation ADR / red team |
| Malicious dependency | Plugin behavior/evidence | Replaces or corrupts transitive component | Dependency admission | Preserve admissible closure | Exact provenance/version/evidence and trust reassessment | Undiscovered defects; supply-chain evaluation |
| Prompt-injected Agent/Model | Policy and effect authority | Generates plausible malicious instructions | Content-to-action | No content authority | Validate proposals, external enforcement, data-flow controls | Bad authorized output quality; EVALUATION / CONFORMANCE |
| Malicious Tool response | Context and subsequent actions | Returns spoofed success/instructions | Tool result ingress | Result integrity and scope | Validate result/effect evidence, classify content, no control promotion | Dishonest remote observation; Tool profile / EVALUATION |
| Poisoned Retrieval/Knowledge | Context and decisions | Inserts false or instruction-like content | Information assembly | Source attribution and safe consumption | Pre-disclosure filtering, provenance, classification, explicit promotion | Incorrect eligible information; EVALUATION |
| Cross-tenant attacker | Content and metadata | Guesses references/caches/continuations | Tenant boundary | Isolation | Verified tenant, per-access filtering, explicit crossing, scoped keys | Timing/shared-resource channels; isolation profile / red team |
| Insider misuse | Administration and audit | Abuses legitimate privileged access | Governance/admin | Accountability and bounded privilege | Explicit authority, separation of duties where required, attributable changes | Colluding authorized authorities; GOVERNANCE / EVALUATION |
| Approval replay | Approved actions | Repeats/concurrently consumes decision | Approval-to-dispatch | Bounded exact use | Owner-arbitrated claims, scope/revision binding, current revocation | In-flight authorized effect; CONFORMANCE |
| Secret theft | Protected material | Reads outputs/logs/host state | Secret-use boundary | Least exposure | Purpose/consumer-bound use, no public material, isolation | Authorized consumer compromise; Secret ADR / red team |
| Resource exhaustion | Capacity and allowances | Loops/floods/amplifies work | Admission/accounting | Bounded consumption | Claims, quotas/limits, inherited deadlines, bounded validation | Service denial within limits; Resource profile / EVALUATION |
| Provider spoofing | Bindings and data | Impersonates identity or guarantees | Catalog/resolution | Authentic matching | Namespace/release authority, exact offers, independent evidence | Entitled publisher compromise; GOVERNANCE / red team |
| Catalog poisoning | Offers/aliases/health | Writes misleading registrations/projections | Catalog mutation | Selection integrity | Authorized revisioned updates and fresh source applicability | Catalog authority compromise; Catalog ADR / CONFORMANCE |
| Stale authorization | Targets and grants | Reuses old allow decision | Dispatch | Current authority | Joint validity and effective revocation ordering | Availability loss; dispatch ADR / CONFORMANCE |
| Partition-induced stale state | Claims/health/policy | Separates consumers from current owners | Distributed boundary | Safe failure | No dispatch when current joint validity cannot be established | Work unavailable; profile / failure testing |
| Audit tampering | Evidence/history | Alters/deletes material records | Evidence custody | Detect alteration and retain meaning | Attributable integrity/custody guarantees, linked corrections | Compromised evidence root; evidence ADR / red team |
| Evidence suppression | Audit completeness | Drops or delays pre/post evidence | Dispatch/evidence | No false completion | Required pre-ack gate, post-effect obligation and gap reporting | Denial of service; evidence profile / CONFORMANCE |
| Supply-chain compromise | Realization/release | Alters source/build/dependency | Release admission | Assessed provenance/integrity | Policy-required release/build/dependency evidence with current validity | Authentic but malicious build; EVALUATION / supply-chain ADR |
| Migration abuse | State/config/history | Rewrites identity/scope/effects during move | State-owner migration | Preserve constraints and lineage | Exact authorized transformations, expected revisions, validation, no restored grants | Transformation defects; state profile / CONFORMANCE |
| Bootstrap compromise | Initial authorities | Substitutes root or broadens duty | Initial establishment | Finite bounded trust | Independent accountable designation, exact duty/evidence, recovery limits | Compromised ultimate authority; GOVERNANCE / bootstrap ADR |

## 5. Trust boundary matrix

**SEC-011.** Every supported crossing MUST enforce the applicable obligations in this matrix and the decision matrix (§27). **Common validation** means verified initiating Principal/acting chain and TenantContext, exact action/target/version, current authorization/policy, input/classification checks, Secret restrictions, resource/deadline limits, required effect identity/claims/evidence, and revocation awareness. Source assertions alone do not satisfy validation. Audit records material decisions and effects with safe correlation; all disclosure remains access-controlled.

| Source | Destination | Threats | Required validation | Allowed data | Authority propagation | Tenant rules | Audit requirements | Failure mode |
|---|---|---|---|---|---|---|---|---|
| External caller | Application ingress | Forged identity, malicious input | Common; candidate identity/scope verified by established ingress | Minimum validated input; rejected fields not trusted attribution | No authority from caller text | Bind verified scope before operational use | Ingress acceptance/denial, safe receiver correlation | Reject/hold protected operation; bounded rejection handling |
| Application | Governed runtime | Forged context, excess scope | Common; pinned work/configuration and admission ceiling | Validated references and required input | Explicit Principal chain, no Application-name grant | One bound tenant | Admission and chosen revisions | Refuse admission or permitted wait |
| Runtime | Plugin/Adapter | Malicious realization, drift | Common; exact admitted release/config/dependencies and isolation | Admitted minimum configuration/input | Admission ceiling plus current call authority | Separately scoped activation/use | Admission, use, health and effects | Block unsuitable use; stop through canonical paths |
| Runtime | Model Provider | Disclosure, retention/training misuse | Common; data-use/residency/retention suitability | Only policy-permitted minimized input | No authority delegated by prompt | Scope and provider crossing constraints | Exact model/use/usage and disclosure evidence | Refuse incompatible disclosure; retain uncertainty |
| Runtime/Agent | Tool mediation | Untrusted proposal, bypass | Common; exact Tool action/equivalence | Validated arguments/references | Proposal never carries a grant | Caller/deputy scope intersection | Preparation, ordered claims and dispatch | No handoff if conditions unmet |
| Tool/runtime | External system | Target spoofing, unknown effects | Common; target, credential purpose, transfer conditions | Authorized action and minimum payload | Bounded action-specific use | Preserve origin and allowed recipient | Handoff and observed/unknown effects | Reconcile timeout; no blind replay |
| Plugin | Host resources | Escape, privilege escalation | Common; admitted privileged duties and isolation | Only necessary declared host access | No host-wide privilege inheritance | Scope each use and shared limits | Privileged use, denial and containment evidence | Refuse access/admission if containment unproved |
| Plugin | Tenant data | Theft and shared-state leakage | Common; per-resource access and data flow | Authorized scoped subset | No access from code co-location | Separate content, metadata, state and caches | Data access/crossing as required | No unauthorized disclosure |
| Tenant A | Tenant B | Relabeling and transfer abuse | Common; explicit grant and both policies | Exact permitted copy/use and metadata | Crossing grant not transferable wildcard | Original scope retained; distinct destination use | Grant/decision, source/target lineage and effects | Fail closed on missing/conflicting scope |
| Human | Approval Management | UI deception, impersonation/replay | Common; Human authenticity, eligibility, presented action revision | Adequate authorized decision context | Explicit decision only, no silence | Approver/request scope checked | Presentation, decision and use evidence | No approved use until valid explicit decision |
| Runtime | Secret Access/material use | Secret deputy theft | Common; exact Secret purpose/consumer/current revision | Public reference and use evidence; material only in protected realization | Use permission not general export permission | Owner and consumer scope match crossing rules | Safe revision/use/rotation attribution | Deny unavailable/revoked/out-of-purpose use |
| Runtime | Evidence custody | Forgery, suppression/leakage | Common; source authority, evidence class/integrity/ack guarantee | Minimized classified records/references | Record custody grants no source decision authority | Filter evidence and graph traversal | Custody/completeness and linked correction | Missing required pre-evidence blocks; post-failure obligation |
| Bootstrap designation | Ordinary dependencies | Self-trust and cycles | Common under already established bounded root duty | Exact duty/config/evidence references | No expansion into general eligibility | Explicit operational tenant, no wildcard | Root designation/admission/replacement evidence | Unsupported cycles or missing root fail |

```text
Diagram 1 — External request to protected effect
external request --> established ingress verifies Identity + TenantContext
    --> Principal / acting chain --> exact work and input validation
    --> current authorization + applicable Policy + required controls
    --> Approval use + resource/deadline/effect claims + mandatory evidence
    --> joint-valid dispatch boundary --> realization --> effect observation
    --> result / Artifacts / accounting / audit / provenance / reconciliation
Every later protected sub-action passes its own current boundary.
```

## 6. Identity and Principal establishment

**SEC-012.** A claimed identity is unverified input. A verified Identity binds issuer/authority, subject, kind/scope, verification evidence, validity, revocation semantics and assurance/context. Authentication establishes that this requester may act as the claimed subject for the present context under a declared verification method and threat assumptions. Neither verification nor authentication alone grants action permission. Caller-supplied text, address, display name, Plugin metadata or model output MUST NOT establish either.

**SEC-013.** Only a Principal with explicitly established identity-establishment authority for the relevant issuer/subject/scope may issue or accept identity associations through Identity and Principal contracts. That authority MUST trace to an accountable configured authority or admitted bounded root (§16), not to the new subject's self-assertion. Authority records MUST specify accepted evidence, assurance/freshness, revocation and protected verification handling. The platform does not appoint one universal issuer or require an authentication protocol.

**SEC-014.** Establishing an acting Principal MUST bind verified Identity, tenant scope, permitted principal kind, authority/restrictions, validity/status, authentication/evidence context, and acting-on-behalf-of chain where applicable. Establishment and action authorization are separate. Actor, Identity and Principal remain distinct: one Human/Service/Agent may have multiple scoped Principals; each action selects exactly one valid acting Principal with origin attribution. Plugin identity, publisher identity and deployment identity MUST NOT substitute for the acting Principal without explicit establishment and binding.

**SEC-015.** Reverification MUST occur when validity, assurance, actor/Principal association, issuer trust, tenant status, purpose or environment no longer meets the applicable requirement. Authentication evidence and credential material MUST be minimized and protected; public requests/results use safe references. Invalid input receives receiver-attributed rejection evidence under Contracts CTR-006, not forged tenant/Principal attribution copied from the request. Unauthenticated public ingress still acts through an established bounded ingress responsibility; it creates no wildcard authority for external callers.

## 7. Authorization, Grants, freshness, and dispatch

**SEC-016.** Authorization MUST evaluate the exact Principal/acting chain, verified TenantContext, action, resource and relevant revisions, purpose, environment, current grants/denials, admitted ceiling, delegated scope, Role eligibility where used, applicable policies, risk/control obligations, approvals, resource/deadline conditions and trust requirements. RoleAssignment, ownership, Capability, Plugin activation, selection and reference possession MUST NOT independently authorize protected effects.

**SEC-017.** Permission issuance MUST require an entitled issuing Principal whose current authority explicitly covers issuing that action/resource/tenant scope and permitted delegation. A Grant MUST identify issuer, subject Principal or canonical eligibility rule, actions, resources, tenant, purpose where required, constraints, delegability, validity, revocation conditions, applicable policies and provenance. Grants/denials retain SPEC's lifecycle and expected revisions. An issuer cannot create authority beyond its granted issuing scope. A historical grant or admission record is evidence, not perpetual authority.

**SEC-018.** An authorization decision MUST expose deciding authority, exact scope and inputs/revisions, allow/deny or conditions-unmet result, validity and timing assumptions, obligations, safe reasons, evidence and unresolved facts. A security assessment may describe a conditional or indeterminate finding: conditional means obligations remain unmet; indeterminate means a required predicate could not be established. These are explanatory findings mapped to existing Contracts decision/error semantics, not new canonical wire values or an alternate lifecycle. Neither finding permits the protected effect.

**SEC-019.** Effective authority MUST intersect the admitted ceiling with current grants, current restrictive policy, delegation, tenant, approval, resource, deadline and realization constraints. New grants MUST NOT silently expand an admitted attempt; expansion requires the explicit authorized amendment or new attempt permitted by SPEC E-03. Only separately established entitled authorities may amend grants/policy; the subject's request or reasoning is insufficient. Consumer-selected policy subsets are forbidden.

**SEC-020.** Current applicability MUST be established at protected dispatch, Secret use, tenant crossing, Approval consumption, resource reservation/consumption, Plugin initialization effects and activation, migration, external communication, destructive effects and resumed Execution. “Current” means demonstrably valid for the action under the declared effective-order and freshness guarantees, not necessarily a separate network query. A timestamp or cached allow alone is insufficient. Cache/reuse claims MUST identify revisions, validity, revocation sensitivity, time uncertainty and failure bounds; inability to prove applicability blocks use.

**SEC-021.** The dispatcher MUST establish Contracts CTR-019's jointly valid full set of authority decisions, consumable claims, deadline, isolation/boundary and evidence obligations for the exact action at handoff. Claim owners arbitrate their own state; the invoking plane owns one dispatch obligation/effect identity. Sequential stale positive responses do not prove joint validity. The declared security guarantee MUST cover expiry, concurrent changes, clock uncertainty, disconnection and replay. If that guarantee cannot be met, refuse or hold before handoff; do not assume global atomicity or freeze authority indefinitely.

## 8. Policy authority, combination, conflict, and Guardrails

**SEC-022.** A policy-authority reference MUST identify the accountable owner and issuing/administrative Principals, jurisdiction of actions/resources/tenants, allowed rule-management and exception scope, validity, delegation, revision and evidence. This is authority metadata for existing Policy and Permission records, not a new privileged Actor type. Owning a Policy is accountability; publishing, changing, evaluating or granting exceptions requires separate current authority.

**SEC-023.** Applicable policy MUST be derived from all relevant security baseline, tenant, Application, Organization, data, resource, Plugin, retention, residency, external obligation and emergency authorities. The selection/combination decision MUST record applicability, exact policy versions, non-waivable restrictions, required obligations, authorized precedence/exception rules and conflicts. A caller or Plugin MUST NOT omit inconvenient rules or replace an unknown rule with allow. Organizational hierarchy alone supplies no legal or technical precedence.

**SEC-024.** A mandatory unresolved conflict or unknown applicability MUST block the affected protected action and create an attributable resolution obligation for the relevant policy authority. Governance must identify who may resolve each conflict and under what basis; this specification does not invent organizational/legal precedence. Security default-denial cannot itself authorize indefinite retention contrary to governing duties. Destructive disposition conflicts follow SPEC A-03: preserve permitted state pending accountable, timely resolution, record due/review obligations, and do not silently choose deletion or permanent retention.

**SEC-025.** Policy decisions and changes MUST be revisioned, attributable, scoped and reviewable. Changes affecting grants, data classification, retention, eligibility or security configuration require current administrative authority, applicable approval/separation-of-duties and resource/evidence controls. Existing work receives current restrictions without rewriting pinned historical meaning. A security configuration flag MUST NOT function as an unrecorded exception or disable a mandatory control.

**SEC-026.** Guardrails MAY be deterministic, model-assisted, Human-assisted, external or composed. Their declarations MUST identify objective, placement, inputs, coverage, uncertainty, failure behavior and the Policy determining the response. A verdict is evidence, not general authorization. If a control realizes an authorized policy rule, it must satisfy that rule's decision contract; a probabilistic judgment MUST NOT become the sole authority for identity, grant validity, tenant scope or mandatory claim enforcement. Required uncertain/failed controls fail closed unless a governing rule expressly authorizes a bounded alternative that still satisfies all non-waivable obligations.

## 9. Revocation and races

**SEC-027.** Revocation MUST distinguish request, authoritative effectiveness, consumer observation, enforcement at a boundary, already committed dispatch and completed effect. The owner-issued revocation record MUST identify subject/scope, authority, expected/produced revision, cause, effective ordering/time basis, affected future uses, known in-flight uses, evidence and outstanding propagation/reconciliation obligations. A final acknowledgment MUST NOT claim universal enforcement or stopped in-flight work beyond its proven scope.

| Subject revoked/restricted | Authoritative owner and consequence |
|---|---|
| Principal or identity/issuer acceptance | Identity/Principal; invalidates affected current subject bindings and future uses |
| Grant/Permission | Authorization; removes covered authority from future action intersection |
| RoleAssignment | Organizational Composition; removes eligibility where required, without rewriting separately issued grants unless their conditions depend on assignment |
| Approval | Approval Management; no further covered use; consumed decisions/effects retained |
| Plugin admission/publisher trust | Admission/trust decision owners; reassess impacted releases/dependencies, prevent unsuitable new use through Lifecycle/Catalog |
| Secret/material revision | Secret Access; stop new covered use; residual external credential effects disclosed |
| Capability eligibility | Catalog with Lifecycle/source evidence; old Resolution remains historical, not current authority |
| Tenant access/crossing grant | Tenant Governance/Authorization; block affected future disclosure and effects |
| Delegation | Work Coordination plus grant owners; prevent new scope-dependent actions, preserve child/in-flight evidence |
| Resource entitlement | Resource Accounting and grant/policy owners; no new unauthorized spend, incurred/unknown liability retained |

These are restrictions/decisions under existing lifecycles. Revoking Plugin admission does not create a Plugin `revoked` or `quarantined` lifecycle state.

**SEC-028.** Every affected future dispatch MUST be ordered against effective revocation/expiry. If revocation wins, the effect cannot be handed off under the revoked authority; if dispatch wins, it is in flight and MUST be reported as such. Consumers MUST NOT use delayed observation as an exemption from an already effective restriction. A realization must demonstrate a mechanism satisfying this ordering for its claimed failure model or refuse dispatch when it cannot establish it. No profile may define away current restrictive updates merely to permit stale disconnected use.

| Race point | Required handling |
|---|---|
| Before authorization | Revoked scope cannot yield valid authority |
| After authorization | Old allow is insufficient; validate joint applicability at dispatch |
| After Approval reservation | Unconsumed reserved use cannot authorize revoked action; owner releases/invalidates according to its contract |
| After resource claim | No dispatch without remaining conditions; non-use release only through owner, liabilities preserved |
| Immediately before handoff | Establish one authoritative order; revocation winning prevents handoff |
| During provider execution | Identify already handed-off scope; prevent later protected sub-actions and request permitted stop; do not assert external rollback |
| After external effect | Preserve completed/partial/unknown effect and accounting; govern compensation/reconciliation separately |

**SEC-029.** Long-running/resumed work MUST revalidate at each later protected boundary, preserving immutable tenant/origin/work identities and prior effects. A restrictive update can require waiting, permitted suspension, cancellation, failure or re-resolution; it cannot relabel begun work as rejected. Stop/revocation limits and residual effects MUST be disclosed to the caller. Revocation cannot erase Artifacts, emitted Events, consumed resources, audit facts or completed disclosures.

**SEC-030.** Retries, replay and recovery MUST retain Contracts operation/effect equivalence, expected revisions and declared deduplication coverage. No response does not prove no effect; expired deduplication records do not permit unsafe repetition. Reconcile uncertain effects, use demonstrated equivalent retry, or hold for an authorized decision. Compensation and exceptional reissue are new governed work with their own authority/costs; no old approval, credential or balance is restored by recovery.

```text
Diagram 7 — Revocation at dispatch
authorization / Approval / resource / evidence owners --> bounded claims
revocation owner --> effective restriction ----+
                                               v
dispatcher establishes order + joint validity for exact effect
    revocation wins --> no handoff; reconcile claims
    dispatch wins   --> in-flight effect; stop later sub-actions when required
                      --> observe/reconcile, retain prior facts
Unprovable order or validity --> no new dispatch.
```

## 10. Approval, Human decisions, and replay

**SEC-031.** Approval MUST bind exact action semantics, target/resources, tenant, acting/requesting Principal and performer where relevant, material input/configuration/content revisions, effect scope, risk context, presented evidence, eligible approver authority, decision rule, validity, conditions and allowed-use count. Material change requires renewed approval when applicability changes. An Approval cannot substitute for other authorization, policy, isolation or resource obligations.

**SEC-032.** HumanApproval MUST authenticate the eligible Human's scoped Principal and preserve decision-channel authenticity and presented-context integrity. The Human MUST receive authorized information sufficient to understand the material action, including target, extent, recipients, irreversibility and uncertainty where relevant; a misleading summary cannot stand in for exactness required by policy. If necessary context cannot lawfully be disclosed, the gate remains unmet or routes to an eligible authorized reviewer. Silence, timeout, model text and delivery acknowledgment never constitute consent or explicit Human rejection.

**SEC-033.** Approval Management MUST arbitrate bounded use claims against exact action/effect scope under Contracts §6. Concurrent use, duplicate submissions and lost acknowledgment cannot consume beyond the allowed count or retarget a consumed claim. Expired/revoked approvals cannot dispatch. If consumption occurred but downstream dispatch failed, retain consumed use and known/unknown effect facts; do not automatically refund or reopen the terminal decision.

**SEC-034.** A new-entitlement process MAY issue a separate Approval only through an entitled decision authority after inspecting prior consumption, dispatch/effect uncertainty, current action applicability, duplicate-risk treatment and separation-of-duties rules. It MUST link the old decision, record justification and new bounded scope, and preserve old history. Unknown prior effects cannot be reclassified as none merely to obtain new consent. Human status confers no bypass of tenant, resource, retention, audit or eligibility controls.

```text
Diagram 6 — Human approval
exact proposed action + risk/evidence --> Approval Management
    --> authenticated eligible Human sees material scoped action
    --> explicit decision bound to presented revisions and permitted use
    --> owner-arbitrated use claim --> current all-condition dispatch check
    --> handoff/effect observation
Lost consumption acknowledgment --> same-identity status/reconciliation, not replay.
```

## 11. Delegation, acting-on-behalf-of, and confused deputies

**SEC-035.** Each acting-on-behalf-of chain MUST identify originating Principal, actual acting Principal/Actor association, issuer/delegator authority, recipient, exact work and scope, validity, attenuation, causation and evidence. Humans and Services may act directly; Agents may act through scoped runtime/Service Principals; Plugin work uses an established realization/host Principal; automation and administrators use explicit Application/tenant authority. None implies hidden impersonation, transfer of credentials or authority from a display name.

**SEC-036.** Effective delegated work MUST remain within delegator delegable authority, accepted delegation scope, recipient eligibility/current authority, inherited policy, tenant restrictions, resource allocation and deadline. Further delegation must be expressly permitted and traceable. A separately authorized supplemental grant remains independently inspectable and cannot silently enlarge already admitted work. A Team accepts through its responsible Principal/Actors; it is not an Actor subtype. Agent-to-Agent messages are data; delegated requests still pin sender, recipient, Task/Goal revision, expectations, resources, deadline and tenant.

**SEC-037.** A deputy MUST NOT use its maximum privilege merely because a less privileged requester supplied a valid request. Effective request-driven authority MUST intersect the requester's applicable authority, explicit delegated scope, deputy/service/Plugin ceiling and current policies/constraints. The deputy MUST bind target, purpose, input and Secret use to that intersection and attribute both principals. Independently authorized service work requires its own explicit authority/causal record; it cannot be silently substituted to bypass a requester's denial.

```text
Diagram 12 — Confused-deputy prevention
requester identity + action/target/purpose --> verified requester scope
delegation chain --------------------------> permitted delegated scope
Service/Plugin Principal ------------------> admitted deputy ceiling
current policies/tenant/resources ---------> restrictive conditions
                         |
                 intersection for exact action
                         |
                 dispatch only within resulting scope
Deputy's larger credential access cannot widen the request.
```

## 12. Agent, Model, Context, and Skill security

**SEC-038.** Agents are untrusted decision-makers within externally enforced bounds. They MAY plan, recommend, request and select permitted alternatives. Their reasoning MUST NOT grant Permissions, change governing Policy/TenantContext, mint Secrets, consume claims outside their owners, bypass approvals/Tool mediation, certify trust or assert enforcement success without evidence. If an Agent proposes an administrative change, an independently authorized boundary must validate it; generated content never supplies its own authority.

**SEC-039.** Model outputs, including structured output and tool-call proposals, MUST be treated as untrusted content. They do not prove truth, safety, identity, approval, policy or verified evidence. Model invocation must enforce declared provider data-use, retention, training-use, residency, external transfer and confidentiality constraints before disclosure. Unknown mandatory provider guarantees block the call. Output contract validity and subject quality remain separate; Model security does not require an Agent, Workflow or particular vendor.

**SEC-040.** Context MUST preserve source, revision, origin, trust/classification, tenant, freshness and derivation. A source authenticated for attribution may still provide false or hostile content. Sanitized means an identified transformation was applied with declared limits; it does not mean declassified, truthful or authorized. Summarization, aggregation and redaction MUST NOT discard inherited restrictions or promote instructions into Policy/configuration.

**SEC-041.** Skills remain versioned expertise assets. Their instructions/resources MUST NOT self-install dependencies, issue grants, change policy/tenant scope, access Secrets or invoke protected actions outside ordinary governed routes. Executable dependencies require admitted realizations and current action enforcement. Procedural Memory promotion to a Skill or governing definition requires explicit validation and authorized publication; reading text is not publication.

**SEC-042.** Prompt injection is untrusted content attempting to change control or authority behavior. Direct and indirect sources—including retrieved documents, web pages, emails, Messages, Plugin metadata, Tool outputs, Artifacts, Memory and Knowledge—MUST remain in classified content channels until an authorized promotion operation admits a governing definition. Implementations MUST preserve origin and enforce action/data-flow boundaries independently of model compliance. Detection/redaction may add evidence but MUST NOT be the sole protection against granting authority, Secret disclosure or tenant crossing. Authorized malicious persuasion may still degrade output quality; Evaluation must assess that residual risk without claiming perfect detection.

```text
Diagram 2 — Agent to Tool mediation
Agent state + untrusted Model/Context --> proposed action
    --> Action Mediation validates exact Tool/target/input/effect
    --> current Principal + policy + Approval + resource/evidence claims
    --> joint-valid handoff --> Tool realization --> observed/unknown effect
Agent receives scoped result; it cannot write grants or owner claims.
```

```text
Diagram 9 — Prompt-injection containment
retrieved document / Tool output / Artifact / Plugin metadata
    --> origin + tenant + classification --> information Context --> Model/Agent
                                                                    |
                                                            action proposal
                                                                    v
                                           external governed action boundary
malicious instruction cannot --> Policy / Permission / TenantContext / Secret grant
Explicit authorized publication is the only promotion route for governing content.
```

## 13. Tool, external effect, and risk security

**SEC-043.** Tool use MUST preserve separate proposal, validation, authorization, applicable Approval, resource/effect claims, evidence, dispatch, effect observation and reconciliation under Contracts §14. Every caller—including direct Applications, Humans, Services, Workflows and Agents—uses the applicable boundary; no LLM-to-production-Tool bypass is conformant. Other domain Ports enforce equivalent protected-effect obligations without being redefined as Tools.

**SEC-044.** Effect risk classification MUST be governed, versioned, scoped and attributable to an entitled policy/classification authority. Useful characteristics include read, sensitive disclosure, local/external mutation, external communication, financial/resource commitment, privileged administration, irreversible/destructive and unknown/mixed effects. They refine Contracts CTR-067 classifications, not a new effect-status taxonomy. Multiple characteristics may apply; unknown does not mean low risk. A Plugin/caller supplies evidence, not its own final risk acceptance. No universal ordered risk labels are imposed.

Policy MAY require stronger assurance, HumanApproval, independent review, tighter resource/action bounds, isolation or pre-evidence for deployment, credential changes, financial transactions, external publication, cross-tenant disclosure, irreversible actions and security administration. The rule must identify triggering characteristics and exact additional obligations; domains choose thresholds through accountable governance.

**SEC-045.** External systems MUST be treated as separate trust domains. Bind target identity, permitted operation/input, credential consumer/purpose, transfer restrictions, effect identity/equivalence and expected result contract. Provider success is attributed evidence whose reliability/extent must meet the declared contract, not an unconditional fact about every external effect. Timeout may leave effects unknown. A provider-side retry after credential/configuration change must preserve intended action equivalence and current authority; changed targets or meanings require new work. Independent external restrictions are not overridden by local authorization.

## 14. Plugin trust, admission, and supply chain

**SEC-046.** Plugin trust assessment MUST consume PLUGIN-SPEC declarations: exact release/contributions/namespace/publisher/source, integrity and dependency provenance, build provenance where required, conformance/security evidence, requested permissions, Secret needs, external/network/filesystem/code-loading behavior, tenant/resource characteristics, isolation, configuration, limitations/vulnerabilities where policy requires, and bootstrap duties. Sufficient evidence means every applicable mandatory predicate has attributable, authorized, relevant, current, integrity-protected support at the required assurance; self-assertion cannot replace required independent verification. Evidence absence or a clean assessment alone does not prove safety.

**SEC-047.** Only a currently entitled Plugin-admission Principal may decide admission for its specified tenant, release, capability scope and risk class. Identity authenticity, namespace/publisher authority, release integrity, dependency trust, least privilege, Secret purpose, isolation, tenant/external-access constraints, resource bounds and required evidence MUST pass before committing admission. The decision MUST bind exact subject/config/dependency/environment evidence, ceiling, validity, restrictions and revocation/reassessment conditions. Lifecycle owns the admission/transition; Governance owns authority. A publisher/evaluator/Plugin cannot appoint itself admission authority through its declaration. Separation of duties applies when required by policy even if one person otherwise has both roles.

**SEC-048.** Trust evidence MUST bind subject/revision, scope, assessor and its authority, issue/observation time, validity/freshness, integrity/custody, limitations and revocation status. Changed release, configuration, dependency, isolation environment, vulnerability knowledge or trust authority MUST trigger applicability reassessment. Relevant dependency trust is transitive: a compromised required dependency cannot be hidden behind an otherwise admitted parent. Unknown required trust or stale health evidence prevents affected new use; prior admission is not perpetual trust.

**SEC-049.** Namespace/release authority MUST be verified against an accountable accepted authority record with scoped delegation, collision/alias rules, validity and authorized transfer evidence. Display names, priority registration or matching package names are insufficient. Owner transfers preserve predecessor lineage and MUST NOT silently transfer existing grants/trust. Catalog changes require authorized expected-revision decisions; aliases cannot rewrite pinned identities. Provider shadowing through a higher priority, spoofed namespace, stale projection or alias manipulation MUST NOT silently replace a bound realization. Capability assertions require the policy-demanded conformance/evaluation evidence before sensitive use; self-description is not verification.

**SEC-050.** Plugin permission scope MUST be explicit, minimal for declared purposes, tenant/action-bound, reviewable, revocable and time-bounded where applicable. Optional broader features SHOULD be independently disabled where contracts permit; missing optional privilege cannot trigger use of a broader fallback credential. Adapter/provider replacement, upgrade, migration or rollback MUST preserve security/error/effect/resource obligations and exact historical attribution. No extension, older profile or restored configuration may downgrade mandatory enforcement. Migration remains under state owners and current authority; it cannot copy revoked permissions, relabel tenants or erase effects.

```text
Diagram 3 — Plugin admission security
release/configuration/dependency declarations + attributed evidence
    --> namespace/source/integrity verification
    --> trust, permission, Secret, tenant, resource and isolation assessment
    --> entitled admission Principal + applicable Policy/required review
    --> Lifecycle admission record [scope/ceiling/validity/evidence]
    --> governed initialization --> current activation checks
    --> separate Catalog eligibility --> separately authorized invocation
Publisher or Plugin assertions cannot replace the admission decision.
```

## 15. Isolation and shared-host security

**SEC-051.** Required isolation MUST derive from declared threat assumptions and protected assets. Applicable properties include memory/state separation, filesystem/data-access bounds, network/external-access restrictions, credential separation, tenant separation, resource confinement, effect mediation, code-loading restrictions and failure containment. Claims MUST state what a malicious contribution can execute/read/change, privileges shared with other components, control ownership, measurement/evidence and residual channels. No process, host or sandbox technique is mandated.

**SEC-052.** Shared-host admission MUST assess whether one contribution can read/alter another's private state, credentials, context, claims, enforcement or evidence; whether privileges are shared; how failure and resource starvation propagate; and whether required guarantees survive that access. If required separation cannot be demonstrated, admission/use MUST fail or adopt another realization that can meet it. Labeling modules separately is not protection. An explicitly accepted trust assumption must identify the accountable authority and scope and cannot waive a canonical non-waivable isolation obligation.

**SEC-053.** Isolation validity MUST be reassessed when privilege, code, dependency, configuration, shared-state layout, containment environment or threat assumptions change. Compromised/unknown isolation prevents affected new dispatch; stop/drain/cleanup use only bounded authorized paths, retain residual effects and preserve evidence. Side-channel and collusion exclusions must be explicit and compatible with claimed tenant/confidentiality guarantees; there is no implicit promise to eliminate every possible channel.

## 16. Bootstrap roots and finite trust

**SEC-054.** Initial trust cannot be proved by the unadmitted Plugin asking to be trusted. The environment's accountable governing authority MUST explicitly designate initial bounded identity establishment, authorization/enforcement, lifecycle, evidence, Secret and resource duties as needed, using an independently established administrative basis. The basis and responsible decision-makers MUST be recorded as initial assumptions with verification/review requirements; this document appoints no actual operator, issuer or universal root. Without a valid designation, dependent protected work cannot begin.

**SEC-055.** Each root designation MUST identify accountable authority and performing Principal/realization/version, allowed duties/actions/resources, explicit tenant context, configuration, authority ceiling, validity/revocation, evidence/custody guarantee, dependencies, exclusions, threat assumptions, failure behavior and replacement/recovery process. Roots receive no unrestricted authority. A single-tenant host still binds a tenant; a multi-tenant administrator performs separately scoped decisions. Bootstrap eligibility is usable only for admitted duties, not ordinary discovery/invocation of an inactive contribution. Canonical Plugin state transitions remain unchanged.

**SEC-056.** Trust, initialization and evidence dependencies MUST terminate at independently established accountable roots. An unresolved cycle fails explicitly; no caller can exempt its own audit/authorization to break a cycle. Bounded root evidence records attest their own custody under Contracts CTR-061 without recursively demanding identical approvals. Replacement MUST be authorized by an established entitled authority independent of the untrusted replacement, preserve lineage/obligations, revoke superseded scope and reassess descendants. Suspected root compromise requires bounded recovery authority/evidence from outside the compromised basis; if unavailable, affected work remains blocked. No automatic promotion of a dependent Plugin into root authority is allowed.

```text
Diagram 8 — Bootstrap trust root
accountable environment authority + explicit independent establishment basis
    --> scoped root designation [Principal, tenant, duties, validity, evidence]
    --> admitted bounded identity / policy / lifecycle / evidence / resource duties
    --> assess dependency graph --> initialize ordinary admitted dependencies
    --> normal activation and eligible publication
cycle with no established independent root --> fail, no self-trust exception
root replacement --> independent entitled decision + preserved lineage
```

## 17. Secret security

**SEC-057.** Public Secret contracts MUST expose only governed references, safe material revision/status and authorized-use evidence. Bind Secret identity, purpose, owner/tenant, consumer, action/target scope, validity, access policy, rotation/revocation and evidence. Possession of a reference grants no read/use/export authority. Material MUST NOT appear in public manifests/results, Context, Artifacts, diagnostic output or telemetry; a sensitive application datum is not automatically a Secret, but actual Secret material remains protected regardless of label.

**SEC-058.** Secret Access MUST authorize minimum necessary use by the exact admitted consumer for the exact purpose under requester/deputy scope and current policy. The protected realization receives only the access needed for that use, not default distribution of the raw value to all callers/Plugins. Any material handling stays inside an expressly authorized protected boundary with disclosure and retention constraints. Credential access to one target cannot be reused for arbitrary outbound targets suggested by content. No storage, credential-exchange or signing technique is prescribed.

**SEC-059.** New uses MUST validate current material revision/validity. Rotation preserves old attribution by identifiers while applying the declared overlap/revocation conditions to new use; it cannot implicitly reactivate a revoked revision. Long-running work rechecks later uses; already handed-off external operations retain their effects and disclosed stop limits. Retry after rotation requires current authorized use and unchanged action/effect equivalence, not automatic redispatch. Checkpoint/configuration restore cannot restore obsolete credentials. Historical evidence MUST NOT retain prohibited old material merely for replay.

```text
Diagram 4 — Secret access
requester + exact action + Secret reference + consumer/target/purpose
    --> verified tenant/Principal and deputy-scope intersection
    --> Secret Access checks current policy + material validity + use conditions
    --> protected realization performs minimum authorized use
    --> safe revision/use/effect evidence to caller
No public raw-material result; rotation/revocation applies to subsequent uses.
```

## 18. Tenant isolation and cross-tenant operations

**SEC-060.** Every operational decision/use MUST bind exactly one verified TenantContext consistent with Principal, resource, configuration and work scope. Caller-provided tenant text cannot override it. Isolation MUST cover data, existence metadata, errors, logs/traces, caches, Memory/Knowledge, Artifacts/relationships, Events, Evaluations, Plugin state/configuration, Secrets, resource reports, deduplication keys, health diagnostics and provenance traversal. Shared definitions have explicit publication scope/custodian and no private operational state.

**SEC-061.** Cross-tenant access MUST bind source/destination tenants, exact resource/revision, action, purpose where required, recipient, grant/issuer validity, both policies, transfer constraints, lineage and current evidence. Recheck before disclosure and subsequent protected use. A crossing creates a distinct authorized destination use/copy or destination Execution, retaining origin and causal links. It MUST NOT relabel existing data or replace a parent Execution's tenant. One-tenant ownership remains canonical; Q-02 co-ownership is not introduced.

**SEC-062.** Shared realizations MUST retain separate tenant admissions, configurations, Secrets, private state, authority decisions, accounting and evidence visibility. Shared compute/code/batching does not union permissions. Caches, continuations, state aliases and replay identities MUST bind the appropriate tenant/query/consumer semantics and recheck current disclosure access. Failure diagnostics and global health summaries MUST NOT reveal another tenant's activity or identity contrary to policy. If shared capacity or side channels cannot meet the admitted guarantees, use a conforming isolation arrangement or refuse use.

```text
Diagram 5 — Cross-tenant transfer
source A: exact resource/revision + authorized sender
    --> explicit crossing grant + source Policy + destination Policy
    --> recipient/purpose/constraints/current claims and evidence
    --> protected disclosure --> distinct destination B use/copy/Execution
    --> original A lineage + B admission/accounting/evidence
No relabeling and no implicit cross-tenant ownership.
```

```text
Diagram 10 — Shared Plugin across tenants
shared immutable release + admitted realization assumptions
          /                                      \
 tenant A activation                         tenant B activation
 Principal/config/Secret refs A              Principal/config/Secret refs B
 state/accounting/evidence A                 state/accounting/evidence B
          \                                      /
         enforced shared capacity + declared isolation/failure limits
No shared private data, authority or visibility merely from shared code.
```

## 19. Resource abuse, claims, and deadlines

**SEC-063.** Supported operations MUST have policy-governed resource/admission bounds appropriate to abuse: model/token exhaustion, Agent loops, Tool floods, recursive delegation, dependency explosion, retrieval amplification, event storms, storage exhaustion and expensive provider selection. Bounds may cover counts, payloads, depth, concurrency, work/compute, time, storage, network or money in explicitly defined units. Expensive validation, rejection and audit handling also need bounded established duties; the pre-authentication path cannot become an unlimited resource bypass. No universal thresholds are selected.

**SEC-064.** Only Resource Admission and Accounting may issue/arbitrate authoritative allocation, reservation, consumption, release and settlement records. Callers cannot forge claims or spend copied balance snapshots. Expected revisions, unique usage/effect identities, scope and conservation MUST protect concurrent children and duplicate reports. Estimates/feasibility are not spend authority. Unknown incurred usage remains outstanding across expiry, cancellation, Plugin replacement and failures; settlement requires entitled authority and attributable evidence. Security uses these decisions without becoming a competing balance owner.

**SEC-065.** Effective child deadlines and resource bounds MUST not exceed inherited limits absent an authorized parent change. Retry, resume, re-resolution, delegation or identity rotation cannot reset consumed quotas/budgets or elapsed deadlines. Time basis and uncertainty must support actual handoff validity. Resource-owner outage cannot justify new spend from stale snapshots; existing bounded claims may support work only when full current joint validity is established. Resource exhaustion causes controlled refusal/wait/stop or already authorized degradation, not silent overrun.

## 20. Classification and information flow

**SEC-066.** Data classification MUST use a small extensible, versioned policy vocabulary with owner/assigning authority, scope, handling characteristics, applicable subjects and transformation rules. Characteristics may describe public, internal/restricted, confidential, Secret or regulated/domain-specific handling without imposing those exact labels or one universal total ordering. Public visibility does not imply truth or executable authority. Unknown required classification prevents disclosure until resolved; multiple applicable restrictions combine without silent weakening.

**SEC-067.** Information flow MUST be authorized for source and destination, purpose, recipient, classification and tenant, including source → Context, Context → Model, Model → Tool, Tool → Artifact, Artifact → external recipient, tenant crossing and Plugin → host access. Disclose only needed inputs, prompts, arguments, configuration, logs, review context and evaluation data. Derived summaries/embeddings/redactions retain restrictions and lineage unless an explicitly entitled classification authority approves a permitted change with evidence. Sanitization alone is not declassification.

**SEC-068.** Memory and Knowledge MUST retain source/version, scope, classification, freshness, access and retention/forgetting rules. Recalled records do not restore grants, current state or Secret validity. Episodic Memory is historical evidence; procedural Memory does not become Skill/Policy without authorized publication. Unverified Knowledge claims remain labeled; poisoned content cannot become verified truth or authority by repeated retrieval. Forgetting/disposition cannot silently erase another owner's required facts.

**SEC-069.** Retrieval MUST enforce source access before unauthorized content or existence metadata crosses into the consumer/Agent context. Authorized retrieval infrastructure may process protected data only within its admitted boundary and purpose; downstream filtering by an Agent is not the access control. Results, scores, counts, rankings, explanations and continuations MUST preserve source/tenant/version/classification/provenance/freshness and disclosure restrictions. A returned reference does not grant subsequent content access.

## 21. Artifact, Event, and Message security

**SEC-070.** Artifact identity, content access, immutable versions, visibility, publication, relationships and lineage MUST be independently governed. Approvals/evaluations bind exact relevant versions, not mutable aliases. Publishing content does not establish truth, safety, Task acceptance or permission to execute it. Malicious documents, code or media remain classified data until separately admitted for an authorized use. Relationships and source references cannot leak protected existence. Content location changes preserve identity, access and integrity meaning.

**SEC-071.** Event publication MUST validate attributable source and source authenticity to the required assurance, publisher authorization, type/version, tenant, classified payload and subscriber access. Source owns the fact; Event Coordination owns delivery; consumer owns handling/effects. Delivery/receipt is not a trusted command or authorization. Duplicate/replay handling binds tenant, event, consumer and declared handler semantics; transport deduplication does not prevent business-effect replay. Out-of-order and unknown delivery follow declared contracts, never an assumed global order.

**SEC-072.** Messages, including Agent-to-Agent and Human requests, MUST preserve sender attribution, recipient scope, content classification and causation. A request is not a grant; another Actor's assertion is not verified evidence. Any resulting delegated work or action separately validates its canonical contract and authority. Correction, deletion and retention across information/Artifact/Event records use owner contracts and preserve permitted minimal tombstones and honest effect history without retaining prohibited material indefinitely.

## 22. Evidence, audit, provenance, disclosure, and retention

**SEC-073.** Security evidence MUST identify evidence/source/issuer, exact subject/revisions and scope, tenant, event/recording times and uncertainty, integrity status, custody, access classification, retention, completeness, freshness, limitations and causal links. Required integrity and tamper-evidence guarantees MUST name covered changes, adversary/failure assumptions and verifier behavior; mechanisms remain open. Unverified, unavailable, stale and contradictory evidence cannot silently satisfy a verified mandatory predicate. Corrections append linked records; no overwriting inconvenient findings.

**SEC-074.** Mandatory pre-dispatch evidence MUST specify class, authoritative owner, required acknowledgment, persistence/recovery/retention guarantee, deadline and validity. Examples include current authority, approved-use consumption, resource reservation, Plugin admission, isolation suitability and crossing grants. The actual required guarantee MUST be established before handoff; mere receipt/queued custody cannot satisfy a committed-recoverable requirement. Unavailable/unverifiable required evidence blocks the protected effect. Finite evidence roots under §16 provide accountability without infinite recursion.

**SEC-075.** After an effect, failed or unknown audit custody MUST preserve the real effect and an outstanding obligation under Contracts CTR-056. Query/reconcile/retransmit the same equivalent evidence operation, not the original external action. Separate owner-local commits and incomplete postconditions remain visible; a successful error log does not mean the parent work succeeded. Effect uncertainty stays `none`, `partial`, `completed` or `unknown` per named effect; absence of evidence is not evidence of none.

**SEC-076.** Audit MUST capture who acted, what exact action/target/revisions, tenant, time, authority/policy/Approval/claim evidence, public rationale when appropriate, effect/result, usage and correlation. It records source-owner facts without becoming the business decision owner. Provenance links production inputs, Models, Plugins, Tools, Artifacts and governance evidence under authorized graph traversal; lineage may itself be sensitive. Trace, telemetry, audit, provenance and evaluation retain distinct meanings. No private chain-of-thought is required.

**SEC-077.** Disclosure MUST distinguish safe caller errors, restricted diagnostics, tenant-private evidence and explicitly authorized security-review views, with Secret-redacted content throughout. Public results retain useful canonical category, safe correlation, effect uncertainty and next authorized recovery route even when causes are withheld. Logs/audit MUST minimize sensitive payloads, credentials/tokens, prompts, private reasoning and cross-tenant identifiers. Retention/deletion must reconcile data minimization, tenant deletion, Artifact/evidence obligations, applicable legal/domain rules and Secret rotation through governing authority; unresolved conflicts use §8 without inventing precedence or indefinite retention. Evidence identifiers cannot falsely imply available historical content after permitted deletion or loss.

```text
Diagram 11 — Evidence precondition and post-effect repair
exact action --> mandatory evidence requirement [owner + acknowledgment + guarantee]
    --> establish required custody/validity --> joint-valid dispatch --> effect
            |                                     |
      missing/unverifiable                        v
            |                              post-effect audit/provenance
        no dispatch                               |
                                      failure --> outstanding obligation
                                      repair same evidence; never repeat effect
```

## 23. Separation of duties, exceptions, and emergency access

**SEC-078.** Policy MAY require separation between creator/reviewer, developer/deployer, requester/approver, publisher/admission authority or evaluator/subject. The constraint MUST identify subject identities, affected actions, independence criteria, validity and evidence, and be enforced using verified associations rather than display names or multiple accounts alone. No universal pairwise separation rule is imposed. Absence of an eligible independent reviewer leaves the requirement unmet.

**SEC-079.** An exception MUST be an explicit governed decision identifying identity/revision, requester, entitled approver/issuing authority, affected rule and permitted exception basis, exact action/resource/tenant scope, justification, start/end validity, compensating controls, review obligation, revocation and audit. The issuer must be entitled to override that rule; unresolved authority conflicts and inherited non-waivable constraints cannot be bypassed. Exception requests/approvals use existing Policy/Approval/Permission behavior and do not add a generic exempt lifecycle or hidden configuration switch.

**SEC-080.** Emergency or break-glass access MUST use a pre-established entitled authority or separately valid exceptional authority, explicit reason, minimal scope, bounded duration, required strong attributable evidence, current mandatory controls, audit and post-event review with accountable owner/due condition. It MUST NOT bypass non-overridable tenant/legal constraints, fabricate Approval or silently waive evidence. If required authority/evidence is unavailable, emergency urgency alone does not authorize the effect. Every subsequent action remains within the exception and independently current; expiration/revocation closes future use without erasing past effects.

## 24. Fail-closed behavior, availability, and replay

**SEC-081.** Mandatory identity, tenant, authorization, Secret-use, crossing, Approval, isolation and pre-evidence requirements MUST fail closed on unknown/indeterminate/invalid conditions. Mandatory resource/deadline/effect-safety conditions likewise remain enforced. Fail closed means no protected disclosure/handoff; an explicit denied/pending operation, safe wait or permitted lifecycle response may result. It does not invent a new subject state or falsely claim earlier work had no effects.

**SEC-082.** Optional diagnostics, non-security telemetry or non-sensitive cosmetic metadata MAY fail without blocking work only where an explicit governing rule allows omission, limits impact and records relevant completeness gaps. This is optional failure tolerance, not authority to ignore a mandatory control. A profile calling a required control optional cannot waive upstream obligations. An allowed bounded fallback must still meet the full applicable contract, not silently weaken it.

**SEC-083.** During partition or control-owner outage, stale grants, balances, health or Policy MUST NOT authorize new effects when current validity cannot be established. Declared guarantees may permit use of verifiable still-valid bounded evidence, but not disregard effective restrictive changes or joint ordering. Security may reduce availability; an inability to prove a claim means refuse/wait. Replay protection for requests, approvals, resources, activation, crossing, events, dispatch and migration MUST follow semantic operation/effect identities, equivalence, expected revisions and retention coverage. Transport-level replay controls alone do not establish these guarantees.

## 25. Canonical security errors and safe disclosure

**SEC-084.** Security MUST use existing SPEC §10 / Contracts §4 categories and recoverability, preserving the most specific known cause and scoped effect status. No new security exception hierarchy is defined.

| Condition | Canonical reporting and handling |
|---|---|
| Principal/grant/issuer authority absent or invalid | AuthorizationDenied; no protected action |
| Mandatory policy/control/evidence unmet or conflict unresolved | PolicyViolation with safe obligation/cause references |
| Invalid/missing/contradictory tenant or crossing | TenantViolation; no protected disclosure |
| Invalid action, forged/uninterpretable declaration or unsupported mandatory input | ValidationError where most precise; preserve AuthorizationDenied/TenantViolation when applicable |
| Incompatible contract/state/profile interpretation | VersionMismatch; no silent downgrade |
| Required provider unusable or binding cannot resolve | CapabilityUnavailable or CapabilityResolutionError with safe resolution detail |
| Plugin lifecycle/contribution cannot meet admitted contract | PluginFailure only when no more specific category explains it |
| Subordinate security/evidence dependency fails | DependencyFailure with specific safe underlying category; not assumed permission |
| Resource bound or deadline exceeded | BudgetExceeded or DeadlineExceeded; prior/unknown effects remain separate |
| Required Human explicitly rejects | HumanRejected; silence/expiry do not map to rejection |
| Concurrent revision/use/equivalence conflict | Conflict; no duplicate mutation or claim use |
| Tool/Model/other work fails after valid security gate | ToolFailure, ModelFailure or ExecutionFailure as appropriate; retain effect and security causes |

**SEC-085.** Error detail MUST NOT disclose protected tenant existence, Secret material, hidden policies/resource names, identities, Plugin/dependency topology or vulnerability details to an unauthorized recipient. Safe receiver-assigned correlation and authorized evidence references allow investigation without laundering forged attribution. Withheld detail MUST be identified as such where safe and MUST NOT be replaced with a false absence/success claim. Access to retained results is rechecked after revocation; non-disclosure never implies safe retry of prior effects.

## 26. Security profiles and assurance claims

**SEC-086.** A future security profile MUST identify accountable authority/version, applicable SPEC/Architecture/Contracts/Plugin-spec versions, supported operations and environments, threats/assets, explicit assumptions, controls/mandatory evidence, identity/assurance requirements, revocation/dispatch/freshness guarantees, isolation/data/resource obligations, retention/recovery/failure domains, exception rules, exclusions and observable proof criteria. Single-tenant, multi-tenant, isolated Plugin, privileged Tool, external processing, high-assurance audit, restricted data and production-effect behavior are potential dimensions, not finalized product tiers or official profile names.

**SEC-087.** Evaluation, red-team, supply-chain and conformance results supply evidence; they do not grant admission or release authority. Claims MUST bind exact subjects/configurations/dependencies and assessment methods, assessor authority/independence, dates/freshness, limitations and reproducibility conditions. Security evidence can be declared, verified, certified under an entitled scheme, unknown or stale; no certifier is appointed here. Replacement/profile updates MUST preserve mandatory guarantees or require explicit compatible re-admission. Test success under one threat environment cannot certify another by name similarity.

## 27. Security decision and identity/authority matrices

### 27.1 Protected-operation decision matrix

**SEC-088.** These matrices specialize existing owner contracts and grant no authority. **Y** is required; **P** means required when governing policy/contract declares it, otherwise explicit evaluated non-applicability; **R** means Resource Governance assesses applicable claims, with explicit policy-permitted empty applicability where appropriate; **S** means Secret use only when the action requires it, through §17. **E** means source attribution/decision evidence always and required pre-dispatch custody according to §22. **F** means fail closed before protected handoff, preserve prior/uncertain effects and owner-local obligations. Policy-selected controls are not caller-optional. All audit entries obey confidentiality/retention.

| Protected operation | Identity | Tenant verification | Authorization | Policy | Approval | Resource claim | Isolation | Mandatory evidence | Secret access | Revalidation point | Failure behavior | Audit required |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Direct capability invocation | Y | Y | Y | Y | P | R | P | E | S | Invocation handoff and subsequent effects | F | Y |
| Model call | Y | Y | Y | Y | P | R | P | E | S | Before input disclosure/inference and later protected use | F; usage uncertainty retained | Y |
| Retrieval | Y | Y | Y | Y | P | R | P | E | S | Query/source access and each result/continuation disclosure | F; no metadata leak | Y |
| Tool action | Y | Y | Y | Y | P | R | P | E | S | Joint-valid exact action dispatch | F; reconcile unknown effect | Y |
| Plugin initialization | Y | Y | Y | Y | P | R | P | E | S | Every setup effect using admitted dependencies | F; no self-admission | Y |
| Plugin activation | Y | Y | Y | Y | P | R | P | E | S | Active commit/current trust; publication separate | F; partial owner commits explicit | Y |
| Plugin/state migration | Y | Y | Y | Y | P | R | P | E | S | Each owner transformation/dispatch and target-use validation | F; preserve partial migration | Y |
| Cross-tenant transfer | Y | Y, both sides | Y, crossing scope | Y, both sides | P | R | P | E | S | Immediately before disclosure/destination admission | F; never relabel scope | Y |
| Secret use | Y | Y | Y | Y | P | R | P | E | Y | Exact consumer/purpose/material use | F; no public material | Y |
| Artifact publication | Y | Y | Y | Y | P | R | P | E | S | Exact version/visibility change | F; source production not repeated | Y |
| Event publication | Y | Y | Y | Y | P | R | P | E | S | Source/payload publication and subscriber disclosure | F; delivery/effects separate | Y |
| Approval consumption | Y | Y | Y | Y | Y, valid decision | R | P | E | S | Owner use commit and dispatch joint validity | F; no automatic refund | Y |
| Delegated work | Y | Y | Y, chain | Y | P | R | P | E | S | Acceptance, further delegation and protected effects | F; parent bounds retained | Y |
| Production-effect action | Y | Y | Y | Y | P, stronger gates as specified | R | P | E | S | Exact target/effect handoff and later sub-actions | F; no universal risk threshold invented | Y |

### 27.2 Identity and authority matrix

Entries describe canonical distinctions, not default privileges. **Via P** means only through a separately established acting Principal with the specific current grant; it is never intrinsic to the row. **Accountable** means possible declared Policy accountability under SPEC S-02 and Policy's owner rules, with governance actions through entitled Principals; accountability grants no action rights. No new restriction on eligible Policy owner kinds is imposed here. Only Organization owns canonical Goal and only Team owns canonical Outcome. “Provides” distinguishes supplying a realization from the Provider/Plugin declarations required to advertise a Capability.

| Subject | Actor? | Principal? | Hold Permission? | Issue Permission? | Approve? | Own Policy? | Own Goal? | Own Outcome? | Provide Capability? |
|---|---|---|---|---|---|---|---|---|---|
| Human | Yes | Distinct associated P | Via P | Via P with issuing authority | Via P; HumanApproval eligibility checked | Accountable if designated | No | No | May perform capability-backed work; no implicit Provider registration |
| Service | Yes | Distinct associated P | Via P | Via P if explicitly entitled | Via P for permitted non-Human decision | Accountable if designated | No | No | May realize Provider/Tool under declared Plugin ownership |
| Agent | Yes | Distinct associated P | Via P | No authority from reasoning; only independently entitled governed issuing action via P | Proposal is not approval; permitted machine decision via P, never HumanApproval | Accountable designation does not allow self-changing governing policy | No | No | May realize declared Agent capability; no self-grant |
| Plugin | No | Identity is not P; performing realization uses established P | Realization via P, not manifest | No self-grant; separate entitled Governance action | No declaration-based consent | Accountable designation cannot create self-admission authority | No | No | Owns declared Providers/Adapters, not canonical semantics |
| Model | No | Model identity is not P | Invoking/realization P only | No output authority | Output is evidence, not decision/consent | Accountability by declared owner, no authority from output | No | No | Supplied through a Provider |
| Tool | No | Tool identity is not P | Invoking/realization P only | No inherent issue right; explicitly authorized governance operation may be mediated | Tool execution is not Human consent | Declared owner accountability only | No | No | Supplies declared bounded action via Provider |
| Application | No | Application identity distinct from its acting P | Via established acting P | Via P if explicitly entitled | Via P if eligible; not HumanApproval by name | Accountable if designated | No; declares intent | No | May compose/expose declared realization; not automatic Provider |
| Tenant administrator | Human/Service/Agent acting in administrative capacity, not new Actor kind | Scoped established P | Only granted administrative scope | Only expressly granted issuing scope | Only eligible decisions; Human requirement preserved | Accountable if designated | No in administrator capacity | No | No inherent capability from title |
| Organization | No | Responsible acting P is distinct | No membership-based pooled grant | Entitled P only | Entitled performers only | Accountable if designated | Yes | No | Composition may expose Provider realization without privileged status |
| Team | No | Acceptance/performing P is distinct | No union of members' grants | Entitled P only | Eligible identified performers, no Team-as-Human | Accountable if designated | No | Yes | Composition may realize capability; declarations still required |
| Role | No | No; assigned Actor uses P | Eligibility may condition grants; Role is not a grant | No | Responsibility/eligibility only | Owner/authority references confer no execution right | No | No | Declares requirements, not implementation by itself |

Permission's canonical eligibility rules may refer to Roles or groups; the evaluated action still selects a verified acting Principal. The table does not deny such canonical rules or collapse issuer, owner, performer and security subject.

## 28. Observable conformance and red-team hooks

**SEC-089.** Every supported security surface MUST expose evidence sufficient to assess its observable requirements within declared threats and failure domains. The following are future case definitions, not executable tests or claims of passed assessment. Evaluation may assess detection/quality; Conformance verifies required boundary behavior. Mechanism-specific proof belongs to ADRs and implementation validation.

| Requirements | Future adversarial/observable proof |
|---|---|
| SEC-001–009 | Replace technology/topology without changed semantics; scoped trust claims and explicit exclusions visible; no hidden universal administrator |
| SEC-010–011 | Each supported threat/boundary maps to controls, failure result, retained evidence and residual assumptions |
| SEC-012–015 | Forged Identity/TenantContext/Principal text rejected; invalid issuer/revocation/assurance cannot establish current subject; ingress rejection uses safe receiver attribution |
| SEC-016–021 | Role/owner/selection alone cannot authorize; stale sequential allows cannot dispatch; changed action or widened scope fails exact grant/claim checks |
| SEC-022–026 | Omitted conflicting policy detected; unknown mandatory decision blocks; model-assisted guardrail cannot waive identity/tenant/approval; authority conflict has responsible resolver |
| SEC-027–030 | Revoke before/after every preparation stage; revocation winning order prevents handoff; dispatch winning retains in-flight effects; partitions deny unprovable dispatch; begun work never rejected |
| SEC-031–034 | Concurrent Approval replay cannot exceed uses; changed target/content fails; deceptive review cannot substitute exact required context; lost ack/failed dispatch never refunds consumed use |
| SEC-035–037 | Delegated chain preserves ceilings/tenant/deadline; privileged deputy denies requester-forbidden target and Secret use; Agent peer assertion creates no grant |
| SEC-038–042 | Inject commands through prompt, Tool response, document, Artifact, metadata and retrieved content; no permission/policy/tenant/Secret change or Tool bypass occurs |
| SEC-043–045 | Direct Tool bypass rejected for all caller kinds; unknown external effect cannot be blindly replayed; output spoofing cannot establish required verified effect |
| SEC-046–050 | Plugin self-admission and capability/namespace spoofing rejected; dependency compromise and changed config invalidate relevant evidence; shadowing/aliases cannot replace pinned provider |
| SEC-051–053 | Malicious Plugin attempts host/peer/credential escape and tenant leakage under claimed threat model; insufficient isolation blocks admission; residual channels explicit |
| SEC-054–056 | Bootstrap self-trust/cycles refused; bounded root cannot perform unrelated duty; compromise/replacement cannot promote an unadmitted dependent |
| SEC-057–059 | Secret exfiltration through arguments/logs/errors denied; wrong-purpose deputy use fails; rotated/revoked material cannot be restored by checkpoint/retry |
| SEC-060–062 | Shared realization and guessed metadata/cache/continuation keys cannot leak tenant data; crossing requires both policies and distinct destination use |
| SEC-063–065 | Parallel requests/delegations cannot double-spend; duplicate reports not double-charge; unknown charges survive expiry; floods/loops/graphs are bounded under declared limits |
| SEC-066–069 | Poisoned Knowledge/Memory remains classified; unauthorized retrieval content/existence never reaches consumer; summary/redaction cannot remove restrictions |
| SEC-070–072 | Malicious Artifact or Event does not authorize execution; exact approved version remains exact; replayed delivery cannot independently authorize duplicate effect |
| SEC-073–077 | Evidence forgery/tampering/gaps detected within guarantee; failed pre-audit prevents effect; post-effect loss repairs evidence only; confidential causes stay restricted |
| SEC-078–080 | Required independent reviewer cannot be impersonated with alternate label; exception needs entitled issuer, bounds and review; break-glass cannot waive non-waivable restrictions |
| SEC-081–085 | Unavailable mandatory controls fail closed; optional telemetry gap cannot hide mandatory evidence loss; safe errors disclose no protected existence or Secret |
| SEC-086–088 | Expired/inapplicable profile evidence rejected; all supported operation rows meet applicable gates; identity/Actor/owner distinctions survive implementation |
| SEC-089–093 | Claim documentation maps requirements, assumptions, proof and unresolved risks; updates preserve all inherited identifiers and repeat the review |

## 29. Inherited questions and risks

**SEC-090.** Each inherited item below MUST remain traceable to its next owner and exit criterion. A security semantic resolution is not implementation proof. No item is closed by selecting a technology, asserting trust or renaming a state.

### 29.1 SPEC questions

| ID | Disposition here | Next owner | Exit criterion |
|---|---|---|---|
| Q-02 | Unchanged/carried: one operational tenant, explicit crossing (§18) | GOVERNANCE / SPEC | Accepted amendment before any cross-tenant co-ownership; no inferred exception |
| Q-03 | Partially resolved: namespace/issuer entitlement, transfer, scoped certification evidence (§§6, 14, 26) | GOVERNANCE / CONFORMANCE | Actual authority/delegation/collision/certification rules appointed and versioned |
| Q-04 | Partially resolved: security-profile declaration and testability dimensions (§26) | CONFORMANCE / GOVERNANCE | Approved named supported sets/evidence thresholds; no product tiers implied |
| Q-05 | Materially advanced: authority/applicability/combination/conflict/exception records, fail-closed and timed retention escalation (§§8, 23) | GOVERNANCE / domain authorities | Approved organizational/legal precedence and entitled exception/conflict resolvers; non-waivable constraints identified |
| Q-06 | Partially resolved: security claim integrity, abuse bounds and no unsafe refunds (§19) | Resource CONTRACT profiles / GOVERNANCE | Domain units, precision/time uncertainty, overrun and settlement authority parameters approved |
| Q-07 | Partially resolved: required evidence/dispatch/partition/retention failure guarantees (§§9, 22, 24, 26) | CONFORMANCE / capability profiles / ADRs | Testable per-profile durability, ordering, recovery and retention bounds demonstrated |
| Q-08 | Unchanged except minimal versioned classification/risk metadata (§§13, 20) | CONTRACT vocabulary governance / GOVERNANCE | Approved needed vocabularies/representations without incompatible cardinality/business meanings |

### 29.2 Architecture risks

| ID | Disposition here | Next owner | Exit criterion |
|---|---|---|---|
| R-01 | Unchanged/preserved: security responsibilities use existing owners; Kernel semantics stable | ARCHITECTURE / CONFORMANCE | Demonstrated no core-to-concrete-realization dependency |
| R-02 | Materially advanced: independent designation, bounded root duties/replacement and finite graph (§16) | GOVERNANCE / bootstrap ADR / CONFORMANCE | Actual accountable root basis approved and adversarial cycle/replacement behavior proven |
| R-04 | Security semantics resolved: exact effective ordering, joint validity, partition refusal (§§7, 9) | Dispatch/claim ADRs / CONFORMANCE | Mechanism proves race behavior under stated time/failure assumptions |
| R-05 | Preserved upstream resolution: security restriction is not new Plugin/Execution state (§§1, 9) | CONFORMANCE; SPEC if expansion proposed | Lifecycle checks show only upstream permitted states/transitions |
| R-06 | Materially advanced: threat-based shared-host admission/privilege/containment conditions (§15) | Isolation ADRs / EVALUATION / CONFORMANCE | Actual realization demonstrates required boundaries, including admitted adversary capabilities |
| R-07 | Preserved and specialized: security partial commits/effect/evidence repair (§§9, 22) | CONFORMANCE / ADRs | Lost acknowledgments and partial evidence never repeat original effect or erase facts |
| R-08 | Materially advanced: bounded evidence roots and exact pre/post guarantees (§§16, 22) | GOVERNANCE / evidence ADRs / CONFORMANCE | Approved custody/failure/privacy rules and finite evidence recording demonstrated |

### 29.3 Contract risks

| ID | Disposition here | Next owner | Exit criterion |
|---|---|---|---|
| CR-01 | Security choice resolved: availability yields to unprovable joint validity; profile bounds explicit (§24) | ADRs / CONFORMANCE | Failure-domain tests prove no stale dispatch; honest availability envelope published |
| CR-02 | Partially resolved: security replay preserves identities and horizon limitations (§§9, 24) | CONTRACT profiles / CONFORMANCE | Retention/retry horizon aligned; outside-coverage intervention behavior demonstrated |
| CR-03 | Semantic process resolved: no refund; separately authorized linked new entitlement (§10) | GOVERNANCE / CONFORMANCE | Actual approver rules and duplicate-risk review implemented without reopening consumed Approval |
| CR-04 | Semantic access model resolved: safe caller report, restricted diagnostic/review evidence (§§22, 25) | GOVERNANCE / evidence ADRs / CONFORMANCE | Authorized access/redaction rules tested against metadata leakage and usable remediation |
| CR-05 | Partially resolved: integrity/custody/availability and honest tombstones (§22) | Evidence/Artifact profiles / CONFORMANCE | Preservation and loss behavior demonstrated within retention/failure guarantees |
| CR-06 | Unchanged/preserved: publication/validation never implicitly activates (§14) | CONFORMANCE | Negative cases reject inactive eligible offers and stale re-publication |
| CR-07 | Materially advanced: independently accountable root basis and finite enforcement/evidence graph (§16) | GOVERNANCE / bootstrap ADRs / CONFORMANCE | Root establishment/replacement and cycle rejection proven; no self-exemption |

### 29.4 All Plugin-specific risks (PLUGIN-SPEC §23)

| Risk | Disposition here | Next owner | Exit criterion |
|---|---|---|---|
| Dependency explosion | Partially resolved: bounded assessment resource/depth/work under policy (§19) | Resolution profiles / CONFORMANCE | Adversarial closure ends within bounds without silently omitting mandatory edges |
| Provider shadowing | Security semantics resolved: exact authority/pins/aliases/revisions (§14) | GOVERNANCE / Catalog ADR / CONFORMANCE | Collision/priority/stale projection attacks cannot silently substitute provider |
| Namespace impersonation | Partially resolved: accountable namespace delegation/transfer verification (§14) | GOVERNANCE / identity ADR / CONFORMANCE | Chosen authority establishment resists spoofed ownership and transfer |
| Capability spoofing | Security semantics resolved: claims not proof; required scoped evidence (§14) | EVALUATION / CONFORMANCE | Sensitive use refuses unsupported/unverified mandatory guarantees |
| Stale health evidence | Security semantics resolved: freshness/applicability/current-use predicate (§§9, 14, 24) | Health profiles / CONFORMANCE | Stale or forged observation cannot authorize matching/use under partition |
| Hidden implementation coupling | Unchanged/preserved: security replacement preserves Port behavior (§26) | ARCHITECTURE / CONFORMANCE | Independent realization passes equivalent security/error/effect contracts |
| State migration incompatibility | Partially resolved: exact owner/current authority/lineage, no copied grants (§14) | State profiles / CONFORMANCE | Malicious/incompatible/partial migration cannot admit unsafe target state |
| Configuration drift | Partially resolved: trust reassessment and pinned environment/config (§14) | Lifecycle profiles / CONFORMANCE | Drift invalidates applicable admission evidence before unsafe use |
| Partial activation | Unchanged behavioral solution; security evidence/current-check specialization (§§14, 22) | CONFORMANCE / ADRs | Incomplete activation/publication never yields false authority or duplicate initialization |
| Contribution publication races | Security semantics resolved: current source applicability and revisions (§§9, 14) | Catalog profiles / CONFORMANCE | Late publication cannot override effective stop/revocation |
| Shared-host escape | Materially advanced: explicit attacker access, shared privileges and containment evidence (§15) | Isolation ADRs / red team / CONFORMANCE | Claimed containment withstands admitted threats or admission refuses |
| Trust bootstrap circularity | Semantic model resolved; actual establishment remains open (§16) | GOVERNANCE / bootstrap ADR / CONFORMANCE | Independent accountable roots and finite dependency proof exist |
| Extensions becoming de facto core | Unchanged/preserved: no extension/profile security downgrade (§§14, 26) | GOVERNANCE / ARCHITECTURE / CONFORMANCE | Base contracts work without undeclared provider security assumptions |
| Version coexistence conflicts | Partially resolved: scoped claims/state/current trust across versions (§§14–15, 19) | State profiles / CONFORMANCE | Concurrent versions conserve authority/resources and preserve effect identity |
| Silent guarantee weakening | Security semantics resolved: evidence applicability, no downgraded replacement (§26) | Contract authorities / EVALUATION / CONFORMANCE | Replacement weakens no mandatory isolation/revocation/effect/resource guarantees |

HLC-01 remains resolved upstream. No new upstream amendment is requested. Outstanding authority selections, assurance thresholds and mechanisms are intentionally governed follow-up work, not permission to bypass the semantic requirements above.

## 30. Security-specific risks and follow-up

**SEC-091.** The following local risk labels describe additional security concerns. They are not new canonical entities or error categories. Each accepted deployment/profile MUST address relevant residual risk and identify the accountable authority for its assumptions.

| Risk | Containment in this specification | Next owner | Exit criterion |
|---|---|---|---|
| Identity-provider compromise | Scoped issuer acceptance, validity and revocation; explicit root recovery (§§6, 16) | GOVERNANCE / identity ADR / EVALUATION | Compromised issuer cannot retain unbounded acceptance; independently authorized recovery demonstrated |
| Overbroad delegation | Requester/delegate intersection and separate supplemental grants (§11) | GOVERNANCE / CONFORMANCE | Multi-hop delegation cannot amplify authority or hide source |
| Policy conflict ambiguity | Complete applicability and explicit unresolved conflict obligation (§8) | GOVERNANCE / domain authorities | Named resolvers and approved precedence/exception bounds exist |
| Break-glass abuse | Bounded scope/time/evidence and required post-review (§23) | GOVERNANCE / EVALUATION | Emergency use cannot self-approve, outlive bounds or bypass non-waivable restrictions |
| Trust-root compromise | Independent initial basis and recovery authority, affected work blocked (§16) | GOVERNANCE / bootstrap ADR | Recovery no longer depends solely on compromised authority/evidence |
| Approval UI deception | Exact material action/presented revision and authenticated decision (§10) | Approval-channel ADR / EVALUATION | Adversarial summaries/target changes cannot produce misbound approval |
| Secret confused-deputy attack | Consumer/target/purpose and requester intersection (§§11, 17) | Secret/Tool ADRs / red team | Privileged credential use cannot serve unauthorized requester target |
| Cross-tenant metadata leakage | Existence/diagnostic/lineage/cache access checks (§§18, 20, 22) | Isolation/evidence profiles / red team | Guessed references, error differences and graph traversal do not violate admitted confidentiality |
| Side-channel leakage | Explicit shared-resource/threat assumptions and refusal of unproved guarantees (§15) | Isolation ADR / EVALUATION | Relevant channel analysis and mitigation/accepted residual bounds support actual claim |
| Privileged Plugin collusion | Shared privilege/control ownership assessment; no implicit trust union (§15) | GOVERNANCE / isolation ADR / red team | Colluding contributions cannot exceed admitted isolation/authority assumptions |
| Audit denial-of-service | Bounded evidence duty, precondition safety and explicit availability limits (§§19, 22, 24) | Evidence/resource profiles / EVALUATION | Exhaustion preserves safe failure and honest gaps without recursive overload |
| Evidence forgery | Issuer entitlement, exact subject, custody/integrity and scope (§22) | Evidence ADR / CONFORMANCE | Forged/altered/stale evidence rejected within declared adversary bounds |
| Security-control downgrade | No hidden extension/fallback/rollback waiver (§§14, 24, 26) | GOVERNANCE / CONFORMANCE | Older profiles/configurations cannot silently weaken current mandatory controls |
| Stale security profile | Exact subject/environment applicability and freshness (§26) | Profile governance / CONFORMANCE | Changed threat/environment or expired assessment triggers reassessment |
| Revocation propagation failure | Effective-order proof and fail-closed uncertainty (§9) | Dispatch/identity ADRs / CONFORMANCE | Delayed/lost updates cannot permit later revoked dispatch within claimed guarantee |

## 31. Traceability to governing documents

**SEC-092.** Later Evaluation, Conformance, representations, ADRs and release gates MUST reference applicable SEC requirements and preserve their upstream anchors. All major security requirements map below; the tables and diagrams inherit their enclosing requirements. Document completion does not establish actual deployed assurance.

| SEC requirements | intent.md | SPEC.md | ARCHITECTURE.md | CONTRACTS.md | PLUGIN-SPEC.md |
|---|---|---|---|---|---|
| 001–006: authority/baseline/objectives | §§19–20, 35, 38–41, 47, 54–55 | §§1–2, S-09–12, I-04/11 | AR-01–08/13 | CTR-001–006 | PLG-001–005, 066 |
| 007–011: assets/threats/boundaries | §§19–20, 29–35 | §§4.8–4.12, E-06 | §§4–6, 10 | §§2, 6, 15, 26.2 | PLG-028–030, 055–060 |
| 012–015: identity/Principal | §§19–20, 35 | Identity/Principal/TenantContext §4.9; S-09–11 | §4.10, §10.1 | CTR-004–006, 035, 039 | PLG-024, 028, 043 |
| 016–021: grants/authorization/dispatch | §§19–20, 30, 35 | E-03/06, Permission/Policy, B-01–04 | AR-17/18; §§8–9 | CTR-017–022, 035–038 | PLG-028, 033–034, 058 |
| 022–026: policy/guardrails | §§19–20, 35–36 | A-03/05; Policy/Guardrail §4.9 | §4.10, AR-12 | CTR-035–036, 059–061 | PLG-029, 044, 066; Q-05 |
| 027–030: revocation/retry | §§19–20, 26, 30–32 | L-01–04, E-03/09–11, ERR-02 | AR-17/22; §8.3 | CTR-013–022, 027, 033–034, 056–058 | PLG-039, 045, 051–054 |
| 031–034: approvals | §§19, 35–36 | §5.11, Approval/HumanApproval | §§4.10, 8.2 | CTR-017–022, 036; CR-03 | PLG-028, 052–054 |
| 035–037: delegation/deputies | §§12–17, 19–20 | §3, D-01–05, E-03–04 | §§4.5, 8.2 | CTR-031–032, 035 | PLG-028, 055–058 |
| 038–042: Agent/Model/Skill/injection | §§11, 18–20, 27–28, 35 | §§4.2, 4.5, A-04, I-04/11/19 | §§4.4, 4.6–8, AR-10/13 | CTR-030, 041–043 | PLG-004–005, 028–029 |
| 043–045: Tool/risk/external effects | §§19–20, 30, 35 | Tool §4.5, E-06–11, §10 | §4.6, AR-22 | CTR-033–034, 053, 067 | PLG-013, 029–030, 051–053 |
| 046–050: Plugin/supply-chain | §§21–22, 24, 34–35, 40 | §§4.12, 5.12, 7, 11 | §§7, 11 | CTR-025–026, 051–055, 063–069 | PLG-006–024, 028–041, 047–050, 061–064 |
| 051–056: isolation/bootstrap | §§19–22, 35, 42 | TrustBoundary, S-09–11, E-06 | AR-12/19/21; §11.3 | CTR-053–055, 061 | PLG-030, 042–044, 066 |
| 057–062: Secrets/tenants | §§20, 29, 35 | Secret/TenantContext §4.9, S-10–11 | §§4.10, 10 | CTR-039–040 | PLG-027, 055–056 |
| 063–065: abuse/resources | §§19, 30, 35 | B-01–04, §4.10 | AR-18; §9 | CTR-017–022, 037–038 | PLG-057–058 |
| 066–072: information/Artifacts/Events | §§26–29, 31, 35, 37 | §§4.7–8, A-01–05 | §§4.8–9, 4.15, 10 | CTR-043–048 | PLG-050, 055–060 |
| 073–077: evidence/confidentiality/retention | §§31–32, 35 | S-12, A-03, §4.11, I-19 | §§4.13, 10.3; R-07/08 | CTR-050, 056–061; CR-04/05 | PLG-046, 054, 059–062 |
| 078–085: exceptions/failure/errors | §§19–20, 30, 35, 48 | S-09, A-05, §10, Q-05 | AR-11/17/22; §12 | CTR-011–022, 035–038 | PLG-051–054, 066 |
| 086–089: profiles/matrices/proof | §§33–34, 46–51 | V-09, §12, Q-03/04/07 | AR-23; §13 | CTR-062–069 | PLG-061–062, 065, 068–070 |
| 090–093: dispositions/risks/review | §§46–48, 51, 55 | §13 | §§14–16 | §§35–36 | §§22–27 |

## 32. Final self-review

**SEC-093.** The following review verifies specification coverage, not implementation proof. Future changes MUST repeat affected checks, preserve requirement identifiers and revise traceability and residual-risk dispositions. No technology choice or security test execution is implied.

| # | Required check | Result / evidence |
|---|---|---|
| 1 | No security technology selected | Pass — §1 |
| 2 | No concrete IAM syntax created | Pass — semantic requirements only, §1 |
| 3 | Claimed identity differs from verified identity | Pass — §6 |
| 4 | Identity differs from Principal | Pass — §§6, 27.2 |
| 5 | Actor differs from Principal | Pass — §§6, 27.2 |
| 6 | Role differs from Permission | Pass — §§7, 27.2 |
| 7 | Capability differs from Permission | Pass — §§2, 7 |
| 8 | Plugin activation differs from Permission | Pass — §§7, 14 |
| 9 | Resolution differs from authorization | Pass — §§7, 14 |
| 10 | Admission decisions not perpetual grants | Pass — §§7, 14 |
| 11 | Current authorization before protected effects | Pass — §7 |
| 12 | Revocation cannot erase completed effects | Pass — §9 |
| 13 | Revocation prevents future effects under guarantees | Pass — §§9, 24 |
| 14 | Approval scoped and non-replayable | Pass — §10 |
| 15 | Human status cannot bypass Policy | Pass — §10 |
| 16 | Agent reasoning never grants authority | Pass — §12 |
| 17 | Model output untrusted | Pass — §12 |
| 18 | Context cannot become control authority | Pass — §§12, 20 |
| 19 | Skill content cannot bypass enforcement | Pass — §12 |
| 20 | Tool dispatch mediated | Pass — §13 |
| 21 | No Secret material in public contracts | Pass — §17 |
| 22 | Old checkpoints cannot restore revoked Secrets | Pass — §17 |
| 23 | Every operational use binds one tenant | Pass — §18 |
| 24 | Crossing requires grants and both policies | Pass — §18 |
| 25 | Shared realization preserves tenant isolation | Pass — §§15, 18 |
| 26 | Shared host not assumed safe | Pass — §15 |
| 27 | Plugin cannot self-admit | Pass — §14 |
| 28 | Bootstrap graph terminates in accountable roots | Pass — §16 |
| 29 | Failed mandatory pre-evidence blocks effect | Pass — §22 |
| 30 | Post-effect audit failure does not repeat effect | Pass — §22 |
| 31 | Prompt injection cannot alter authority | Required invariant — §12; implementation proof deferred |
| 32 | Deputy intersects requester/deputy authority | Pass — §11 |
| 33 | Delegation attenuates authority | Pass — §11 |
| 34 | Break-glass explicit, bounded and audited | Pass — §23 |
| 35 | Security exceptions governed records | Pass — §23 |
| 36 | Mandatory controls fail closed on uncertainty | Pass — §24 |
| 37 | Resource abuse bounded | Required declared bounds — §19; operational proof deferred |
| 38 | Errors do not leak sensitive metadata | Required boundary — §25; adversarial proof deferred |
| 39 | Supply-chain trust evidence-based | Pass — §14 |
| 40 | All inherited Q/R/CR/Plugin risks tracked | Pass — §29; each has disposition, next owner and exit criterion |

Additional review: existing Goal/Outcome ownership and Actor/Principal separation are preserved; no new Plugin or Execution state is introduced; direct capabilities remain usable without Agents/Models/Teams; control obligations retain existing owners; matrices and twelve diagrams are semantic; no perfect availability, universal exactly-once effects or unqualified shared-host safety is claimed.

## 33. Next document

**Recommended next document:** `evaluation/EVALUATION.md`.

It should define technology-neutral evaluation methodology, criteria/result meaning, datasets/case governance, evaluator independence and uncertainty, regression and adversarial assessment, risk/coverage reporting, exact subject/version attribution, and how evidence informs governed decisions without granting authority. It should consume §28's security/red-team hooks and carry relevant unresolved §29–30 items forward. Named conformance suites/profiles, concrete security mechanisms, schemas, ADRs and implementation remain separately authorized future work.

The Security specification phase ends with this document.
