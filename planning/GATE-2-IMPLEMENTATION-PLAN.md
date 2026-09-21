\
# Gate-2 Implementation Plan

**Status:** PROPOSED — GATE 2 IMPLEMENTATION PLAN
**Authority:** intent.md → SPEC.md → architecture/ARCHITECTURE.md → contracts/CONTRACTS.md → plugin-spec/PLUGIN-SPEC.md → security/SECURITY.md → evaluation/EVALUATION.md → conformance/CONFORMANCE.md → adrs/ADR-INDEX.md → ADR-001 through ADR-011, ADR-015 (Accepted) → this plan.
**Scope:** Gate-2 planning only. No production code, no Gate-2 source files, no ADR changes. This document is a plan, not an authorization to implement beyond the selected first batch, which itself still requires separate implementation instruction.

---

## 1. Gate-1 handoff

Gate 1 exited READY on 2026-09-21 (`planning/NEXT-CORE-IMPLEMENTATION-BATCH.md` §26), all 17 §18.1 criteria PASS. Gate 2 may safely depend on:

- **Kernel foundations** (`legoai.kernel`): opaque identities (`TenantId`, `PrincipalId`, `ApplicationId`, `OperationId`, `RequestId`, `CorrelationId`, `TraceId`), `TenantContext`, `EffectExtent` (CTR-009, including `UNKNOWN`), `ErrorCategory`/`Recoverability`/`ErrorCause`/`ErrorDetail`, references (`PrincipalRef`, `ApplicationRef`, `ApplicationRevisionRef`, `ConfigurationRef`, `ConfigurationRevisionRef`, `OwnerRevision`, `OperationRef`, `ReferenceScope`), `Version`, `DutyId`/`DutyKind`.
- **Application configuration semantics** (`legoai.application`, `legoai.reference.application`): immutable `ComposedConfiguration`/`EffectiveConfiguration`, `ConfigurationStorePort`, `SQLiteConfigurationStore`.
- **Owner-local operation/result/duty semantics**: expected-revision conditional commit, `ConfigurationPublicationOperation`/`ConfigurationPublicationResult`/`ConfigurationSourceSubmissionDuty`, proven revision/conflict/duplicate/lost-ack/process-restart/**migration-interruption** evidence.
- **Versioned persistence representation** (`legoai.reference.application.codec`): `RecordSchemaVersion` distinct from `Version`/`OwnerRevision`/`ConfigurationRevisionRef`, fail-closed on unsupported version, no pickle/marshal.
- **SQLite persistence + restart/integrity qualification** (`legoai.reference.application.sqlite_store`, `.recovery`): `qualify_store`/`RecoveryStatus.{QUALIFIED,BLOCKED}`, `UnsupportedPhysicalSchemaVersionError`, real-subprocess-proven crash/interruption safety.
- **Inert Plugin declarations** (`legoai.plugins.values.PluginDeclaration`/`PluginId`) and **inert Capability requirements/offers** (`legoai.capabilities.values.CapabilityId`/`CapabilityOffer`/`CapabilityRequirement`/`CapabilityVersionRange`) — closed dataclasses, no callable/executable field, proven by canary tests.
- **Pure compatibility analysis** (`legoai.reference.resolution`): F7 static `NO_MATCH`/`UNIQUE_MATCH`/`AMBIGUOUS` — no runtime resolver, no winner selection, no execution.
- **Safe local observation** (`legoai.observability`): closed `Observation` value, bounded text, failure-containment proven.
- **Private deterministic composition** (`legoai.runtime._composition.direct`): substitutable pure `normalize_text`, no executable binding from inert declarations, AST-scanned for Gate-2 symbol absence.
- **Governance F1 foundation** (`legoai.governance.values`): `Principal` (identity-owner designation, no authentication/tenant/grant status) and `OperationContext` — explicitly documented in its own docstring as **"not ExecutionContext"** and satisfying only a narrow synthetic administrative anchor, not the full CTR-005 envelope.

No Gate-1 architecture is reopened; no contradiction was found during F9/re-review.

---

## 2. Authoritative Gate-2 definition

No document numbers a "Gate 2" as a named milestone with its own entry/exit checklist the way `GATE-1-FOUNDATION-IMPLEMENTATION.md` §18.1 does for Gate 1. The authoritative continuation is the **accepted ADR sequence and its stated implementation ordering**:

- `adrs/ADR-INDEX.md` §7: "Recommended order is configuration and owner-local state; then authority/tenant integration; then mandatory evidence; then bootstrap and dispatch coordination; then retry/reconciliation; then execution supervision **before the governed executable slice**."
- `adrs/ADR-INDEX.md` §9 topological order: `001 → 002 → 003 → 004 → 005 → 009 → 006 → 007 → 008 → 015 → 011`, with 010 before Secret use and 012/013 at their triggers.
- `adrs/ADR-015.md` names its own target explicitly: **"supervised live work and the governed executable slice."**

Gate 1 = ADR-001 through ADR-004 realized (Kernel, packages, configuration, owner-local state). **Gate 2 = ADR-005 through ADR-009 and ADR-015 realized, converging on one governed deterministic executable invocation** — the "governed executable slice" ADR-015 names. There is no separate Gate-2 planning document to defer to; `GATE-1-FOUNDATION-IMPLEMENTATION.md` itself only defines Gate-1 exit and lists "Remaining Gate-2 blockers" (§18.2) as an ADR-owned backlog, not a second checklist.

- **Purpose:** prove that a request can be governed end-to-end — authenticated, tenant-bound, authorized, resourced, dispatched under joint-valid ordering, executed deterministically, and evidenced — without any AI/probabilistic actor in the loop.
- **Entry criteria:** Gate-1 READY (satisfied), ADR-005 through ADR-009 and ADR-015 Accepted (satisfied — all Accepted per ADR-INDEX §3/§5.1), no unresolved Proposed ADR on the critical path of the selected slice (must be checked per batch — see §12).
- **Exit criteria (inferred, not separately numbered in any document):** one deterministic Capability invocation governed by real Principal/Tenant authorization (ADR-005), admitted through real bootstrap/admission (ADR-006), dispatched under the joint-validity arbiter with real resource claims (ADR-007), carrying real operation identity/deduplication (ADR-008), evidenced under real custody (ADR-009), and supervised by the accepted execution model (ADR-015) — all with negative/race/failure evidence matching each ADR's own acceptance-review table, and zero Model/Agent/Workflow/Embedding dependency.
- **Mandatory milestones/batches:** not pre-numbered by any accepted document; §19 below decomposes them from the ADR dependency graph.
- **Forbidden premature work:** ModelPort, Embedding, Agent runtime, Workflow runtime, Team, Goal/Outcome, RAG, Memory, MCP/A2A, any ADR-012 (isolation) or ADR-013 (production observation) dependency, any external network/broker/managed service.

---

## 3–4. Entry/exit criteria

Restated compactly from §2: **entry** = Gate-1 READY + relevant ADRs Accepted; **exit** = one governed deterministic invocation proven end-to-end with race/failure evidence under ADR-005/006/007/008/009/015, zero AI dependency. Individual batches inside Gate 2 have their own narrower entry/exit gates, defined per batch as they are planned (this task defines only the first, §20).

---

## 5. Canonical runtime ordering

Derived from ADR-INDEX §10 dependency graph plus ADR-005 §17.1, ADR-006 §6, ADR-007 §6, ADR-008 §5/7, ADR-015 §2 (not the task prompt's conceptual sketch, which is illustrative only and is superseded by this):

```text
Protected ingress (claims: identity, tenant, requested action)
  → Identity verification / Principal binding                [ADR-005 §6]
  → TenantContext binding + scope validation                  [ADR-005 §7]
  → Authorization (Grant) + Policy evaluation                  [ADR-005 §9]
  → Immutable operation security context issued                [ADR-005 §10]
  → Plugin bootstrap/admission (independent of this request,   [ADR-006 §§4-8]
     already-established finite root duties + admitted candidates)
  → Execution admission (ExecutionContext bound, attempt        [ADR-015 §2; ADR-008 §4.1]
     identity minted; distinct from operation/request identity)
  → Operation identity / equivalence check (dedup before        [ADR-008 §5]
     any new mutation attempt)
  → Preparation outside the dispatch gate: resource feasibility, [ADR-007 §6.1]
     pre-effect evidence custody                                 [ADR-009]
  → Final ordered dispatch gate: joint validity of authority,    [ADR-007 §6.2]
     Approval, resource, deadline, evidence — single arbiter
  → Governed deterministic Capability invocation (the effect)    [ADR-007 §6.2 step 7]
  → Result / effect status (none/partial/completed/UNKNOWN)      [ADR-008 §6; kernel EffectExtent]
  → Evidence commit (post-effect, repair without replay)         [ADR-009]
  → Observation (diagnostic only, non-authoritative)              [F8a/F8b, unchanged]
```

Catalog/Resolver placement: **Resolution happens before admission**, never after — a compatibility candidate is not itself authorized or dispatched (see §15). Async supervision (ADR-015) wraps the whole live-work lifetime (admission through result), not just the dispatch gate.

---

## 6. Dependency graph (implementation, not decision)

```text
Kernel (done)
  └─> legoai.execution (values: ExecutionState, ExecutionId/AttemptId, ExecutionContext, ExecutionResult)
        └─> legoai.reference.execution (Coordinator realization)  [needs governance + resources + ADR-007/008 gate]
  └─> legoai.governance expansion (Grant, Policy, Approval values/Ports; Tenant binding; Boundary Enforcement)
        └─> legoai.reference.identity / .tenant / .authorization / .policy / .approval / .enforcement
  └─> legoai.resources (new package: Budget/Quota/Limit/ResourceClaim values/Ports)
        └─> legoai.reference.resources
  └─> legoai.plugins expansion (admission/lifecycle values: PluginAdmission-related states, unchanged canonical
       Plugin lifecycle table from ADR-006 §8)
        └─> legoai.reference.plugins (Lifecycle/admission realization)
  └─> legoai.capabilities expansion (CapabilityResolutionPort, admitted-candidate result type distinct from F7's
       static compatibility candidate)
        └─> legoai.reference.catalog (new: Catalog registration/offer projections)
        └─> legoai.reference.resolution expansion (runtime CapabilityResolver, distinct module/behavior from F7)
  └─> legoai.evidence expansion (custody commit/repair Port)
        └─> legoai.reference.evidence (custody realization)
  └─> dispatch arbiter (private technical component, likely under legoai.runtime._composition, per ADR-007 §14
       "small internal coordination primitive... exact package choices deferred")
        requires: governance (authorization), resources (claims), evidence (pre-effect custody), plugins
        (admitted candidate), execution (attempt/context) — ALL of the above
  └─> legoai.reference.execution Coordinator + ADR-015 asyncio supervision
        requires: dispatch arbiter + execution values
  └─> first governed deterministic invocation (uses F8b's normalize_text as the Capability body)
```

**Exact prerequisites for governed dispatch (the critical path):** `legoai.execution` values → governance Grant/Policy/Approval values → resources ResourceClaim values → evidence custody Port → plugins admission values → capabilities runtime resolution type → dispatch arbiter → Coordinator/supervision → invocation. Nothing downstream of "governed dispatch" (ModelPort, Agent, Workflow) is on this path.

---

## 7. Special ADR treatments

### 7.1 ADR-005 (Authorization)

Before any governed dispatch: **verified identity → Principal binding → TenantContext → Grant/Policy decision → immutable operation security context** (§6, §10). Distinctions preserved, never collapsed:

| Concept | Must remain separate because |
|---|---|
| Claimed identity/evidence | Untrusted input (§4) |
| Verified Identity / Authentication | Establishes present-context acting capability only (§3, §6.1) |
| Principal | Canonical subject bound via governed mapping (§6.2) — Gate-1's `governance.values.Principal` already models the reference, not the mapping/authority |
| Current authorization | Demonstrable at the relevant boundary now (§12.1) — never a cached/historical allow |
| Historical authorization evidence | Retained fact for interpretation, never live authority (§15, Timeline 7) |

**Model/Agent output must never become authorization authority** — ADR-005 §4 and Timeline 9 (Agent context forgery) state this explicitly: forged `principal=admin` fields from model/Agent output are untrusted content, rejected by owner provenance checks before protected work. Gate-2 architecture must make this structurally impossible (no field on any Execution/Capability value ever accepts a bare string/dict as "authorization").

### 7.2 ADR-006 (Bootstrap/admission)

Five distinct stages, never collapsed (§8 table):

```text
discover_plugin → inspect_plugin → validate_plugin → admit_plugin → configure_plugin
  → initialize_plugin → activate_plugin → Catalog publication
```

Gate 1's F7 (`legoai.reference.resolution`) implemented **only static compatibility analysis** (`NO_MATCH`/`UNIQUE_MATCH`/`AMBIGUOUS`) — this is explicitly **not** admission (ADR-006 §8: "A validated contribution is still not an ordinary Provider"). **Admission is introduced by a new Gate-2 milestone realizing `legoai.reference.plugins`** (Lifecycle/admission), owned separately from Catalog (§9: "Lifecycle owns activation... Catalog owns registration, visibility"). F7 compatibility must not be treated as admission — no Gate-1 code currently claims this, and no Gate-2 code may either.

### 7.3 ADR-007 (Dispatch ordering)

Required ordering (§6):

- **Before dispatch (outside the gate):** bind exact action/target/tenant/context; resolve decisions/Approval/evidence references; persist invoking-plane intent under ADR-004; obtain owner reservations; obtain pre-effect evidence custody (§6.1).
- **At dispatch (inside the exclusive gate, §6.2):** re-validate the exact frozen action/context against **current** owner facts (not the ones read during preparation); verify every resource/Approval/evidence/deadline/isolation predicate as a complete set; commit owner-local consumption in deterministic order; re-check the final set after those mutations; commit the durable handoff-attempt obligation; commit the actual protected handoff while still holding the gate.
- **After dispatch:** release the gate without waiting for external effect completion; record effect observation separately; reconcile unknown/partial effects under ADR-008.

**State that must be revalidated immediately before effectful work:** action/target/tenant/acting-chain (frozen at prep, re-read at gate entry), Grant/Policy currentness, Approval unconsumed status, every mandatory resource dimension, deadline margin against actual acceptance timing, Plugin/Provider suitability and health. A sequential "checked five minutes ago" is explicitly insufficient (§5, §7).

### 7.4 ADR-008 (Operation identity / effect reconciliation)

Gate-2 Execution must use, not redefine, F6a/F6b's owner-local operation ledger pattern (§3: "Select A... every supported mutable owner retains a scoped operation ledger within its ADR-004 atomic commit boundary" — this is exactly F6a's existing mechanism). Preserved distinctions (§4.1):

```text
Operation identity   — one logical owner operation, stable across equivalent retransmission
Request identity     — one submission
Execution identity   — one execution ATTEMPT; a genuine retry creates a linked NEW Execution
Effect identity       — one intended protected effect, preserved across compatible attempts
```

**No global exactly-once semantics** — ADR-008's own header states acceptance "does not... establish exactly-once delivery or effects." Gate-2 `ExecutionId`/attempt identity is therefore a **new type distinct from** F4/F6a's existing `OperationRef`/`OwnerRevision` — Execution attempts are downstream consumers of operation identity, never a replacement for it.

### 7.5 ADR-009 (Evidence)

Evidence obligations become part of governed execution **before** dispatch for any mandatory-evidence path (ADR-007 §6.1 step 5: "Obtain required pre-effect custody under ADR-009" — this is a precondition of entering the final gate, not a post-hoc log). Preserved: **Evidence ≠ Observation** — `legoai.observability`'s F8a/F8b `Observation` remains explicitly diagnostic-only and non-authoritative (per Gate-1 G1-EXIT-11/12); it can never satisfy a mandatory ADR-009 custody obligation, and diagnostic logs never become authoritative regardless of volume or apparent completeness.

### 7.6 ADR-015 (Execution supervision)

Asyncio supervision is required **before** any dispatch that can be cancelled, awaited on, or run concurrently with other admitted work — it owns "Execution context, admission, attempts, scheduling intent, cancellation and reconciliation coordination" (§2). However, ADR-015 §3 Alternative B explicitly notes: "A fully serial configuration is useful for **initial deterministic baseline tests**." Given the first Gate-2 batch is values-only (§20) with **no live task, no admission queue, no cancellation surface**, **the first batch can and must remain synchronous** — there is nothing yet to supervise. Supervision becomes mandatory at the batch that introduces an actual Coordinator/dispatch loop (a later batch, §19), not at the values-definition batch.

---

## 8. Plugin isolation boundary (ADR-012, Proposed)

ADR-012 governs isolation for **hostile or insufficiently trusted** Plugin support (Class C / P3). Gate-1's admitted scope is already "sufficiently trusted shared-process" (ADR-005 §4, ADR-006 §2/§4). Gate 2's first executable slice uses **only the existing F8b deterministic reference Capability**, which is a first-party built-in under the same trusted-host assumption already accepted for Gate 1 — it introduces no new trust boundary and does **not** require a binding ADR-012 decision. **No blocker**, provided Gate 2 does not admit any third-party/untrusted Plugin. If a later Gate-2 batch needs to admit an untrusted contribution, that batch must stop and report ADR-012 as a blocker rather than deciding isolation implicitly (ADR-INDEX §5.1 row ADR-012: "Blocks implementation? Hostile/insufficiently trusted Plugin support" only).

## 9. Production observability boundary (ADR-013, Proposed)

ADR-013 governs **production** operational integration (exporters, distributed tracing, metrics backends, retention/sampling) — Class D / P3. Gate-1's F8a/F8b `Observation`/sink already satisfies the accepted **bounded local diagnostic** scope without ADR-013. Gate 2 must continue using only that bounded scope; **no OpenTelemetry, exporter, or production retention/sampling mechanism is a Gate-2 prerequisite.** No blocker.

---

## 10. Catalog vs Resolver

`ADR-002.md` line 176 names `legoai.reference.catalog` ("Catalog records and scoped offer/eligibility projections") as **distinct from** `legoai.reference.resolution` ("Resolution snapshots/closure/results"), and ADR-006 §9 states "Lifecycle owns activation... **Catalog owns registration, visibility and Provider offer state**." Neither exists yet in `src/legoai/reference/` (only the F7 static-compatibility `resolution.py` exists, and it does not publish/register anything). **Catalog is canonical and required before runtime resolution can mean anything** — a Resolver cannot return "eligible" candidates without a Catalog that recorded eligibility in the first place. Owner: Plugin/Catalog realization, milestone: after Plugin admission/lifecycle exists (§6 dependency graph). No generic registry may be built by convenience in its place — ADR-002 names it explicitly, so an ad hoc dict-based "registry" would violate canonical ownership.

---

## 11. CapabilityResolver semantics

The future runtime Resolver's return value chain, preserving strict distinctness (ADR-006 §8, ADR-007 §4):

```text
compatibility candidate (F7 static NO_MATCH/UNIQUE_MATCH/AMBIGUOUS — pure, no state)
  ≠ admitted candidate (validated + admit_plugin committed — ADR-006 §8)
  ≠ published/eligible candidate (active/degraded activation + Catalog publication — ADR-006 §9)
  ≠ authorized candidate (ADR-005 Grant/Policy allow for THIS action/tenant/Principal)
  ≠ resourced candidate (ADR-007 resource claim reserved)
  ≠ executable invocation (ADR-007 §6.2 step 7 — inside the dispatch gate, after all of the above)
```

**F7's `UNIQUE_MATCH` may never be reused as runtime authorization** — it proves only that exactly one declared offer's static contract shape matches a requirement; it says nothing about admission, activation, current eligibility, or authority. Any Gate-2 Resolver must consume `UNIQUE_MATCH` only as one necessary-but-not-sufficient input into the full chain above, never as a standalone "go" signal.

---

## 12. Plugin runtime representation

No object currently represents an admitted/activated Plugin at runtime — Gate-1's `PluginDeclaration` is a closed inert dataclass with no callable/executable field (proven by canary tests). It must **not** be mutated to add one. A later batch introducing admission must define a **separate runtime type** (e.g., an `ActivePluginHandle`-shaped value owned by `legoai.reference.plugins`, distinct from the public `legoai.plugins.values.PluginDeclaration`) that references the declaration by identity rather than subclassing or extending it. `PluginDeclaration ≠ Plugin runtime handle` is preserved by construction: the two live in different packages (`legoai.plugins` public contract vs. `legoai.reference.plugins` realization), matching ADR-002's existing implementation-free/realization split.

---

## 13. Execution semantic ownership

Canonical owner per ADR-002 line 157/178 and ADR-015 §2: **`legoai.execution`** (public values/Ports — Kernel-adjacent contract package) realized by **`legoai.reference.execution`** (Coordinator/driver/checkpoint realization). `Execution`, `ExecutionContext`, `ExecutionResult`, `ExecutionState`, attempt identity all belong here — **not** under `legoai.application` merely because Application Composition initiates work (ADR-002 explicitly separates "Application Composition values/Ports" from "Execution Coordination... values/Ports" as different table rows with different allowed dependency sets).

---

## 14. ExecutionContext — minimum contents

Canonically justified fields only, derived from ADR-015 §2 ("Execution context, admission, attempts, scheduling intent, cancellation") and ADR-005 §10 (operation security context) and ADR-007 (resource/deadline binding) and ADR-008 §4.1 (identity domains):

| Field | Justification | Type (existing Kernel/Governance type reused where possible) |
|---|---|---|
| `execution_id` | ADR-008 §4.1 distinct Execution-attempt identity | new `ExecutionId` (Kernel-style opaque identity) |
| `operation` | Links to the owning logical operation (ADR-008 §4.1) | existing `OperationRef` |
| `tenant_context` | Exactly one pinned TenantContext per Execution (ADR-005 §7) | existing `TenantContext` |
| `acting_principal` / `originating_requester` | Current authority binding, deputy distinction (ADR-005 §8) | existing `Principal` |
| `security_context_ref` | Reference to the immutable operation security context issued by ADR-005 §10 (not a copy — a reference, per §10.1's explicit rejection of "possession of a copy" as proof) | new reference type, Kernel-style |
| `correlation_id` / `trace_id` | Already-accepted Kernel correlation vocabulary | existing `CorrelationId`/`TraceId` |
| `deadline` | ADR-007 §8 — required for joint-validity timing; no execution may claim unbounded time | new bounded value (explicit duration/deadline reference, not a raw `datetime`) |
| `causation` | Parent/child lineage for nested/retried work (ADR-005 §8.3, ADR-008 §4.2) | existing `OperationRef | None` pattern from `governance.values.OperationContext` |

**Explicitly excluded from the first batch** (not yet canonically realized, so cannot be typed correctly): resource/budget context (needs `legoai.resources`, not built), admitted-candidate reference (needs Catalog, not built), Approval reference (needs Governance Approval expansion, not built). Adding placeholder fields for these now would be exactly the "convenience context bag" the task prohibits. **No `dict[str, Any]` anywhere** — every field is a named, typed value.

---

## 15. Authority external to probabilistic actors

Structural invariant for all Gate-2 design: no `Execution`/`ExecutionContext`/`Capability*` value type may accept authorization as a bare string, boolean, or unconstrained mapping. Authorization must always be represented as a reference to an owner-issued decision record (mirroring ADR-005 §10.1's rejection of "a consumer-supplied copy... `allowed=true`... possession of someone else's context reference"). Since Model/Agent/Workflow do not exist yet, this is enforced now by simply **never introducing a permissive field shape** — the same discipline Gate-1 already applied to `PluginDeclaration`/`CapabilityOffer` (closed dataclasses, `TypeError` on unsupported fields, canary tests). Any future batch introducing Agent must be reviewed against this invariant before acceptance, not after.

---

## 16. Approval semantics (deferred, not needed by Batch 1)

If a later Gate-2 batch requires Approval: what is approved = exact action/target/material revisions (ADR-007 §10); bound to = exact effect scope, not reusable; use count = single consumption, "consumed does not become reserved again" (ADR-007 §4 CTR-018 states); expiry = owner-governed validity window, not wall-clock-only; replay protection = consumed Approval cannot be retargeted or automatically refunded (ADR-007 §10); revocation = Approval cannot resurrect revoked Permission (ADR-005 §12.2). **No generic `approved=True` field is permitted anywhere.** Not required for Batch 1 (§20 has no Approval-bearing action).

## 17. Resource semantics (deferred, not needed by Batch 1)

Minimum future slice: `declared requirement` (what a Capability/action states it needs) ≠ `granted resource` (owner-issued reservation, ADR-007 §9 `reserve_resource`) ≠ `consumed resource` (ADR-007 §9 `consume_resource`, distinct from actual metered usage). No billing/quota infrastructure needed for the deterministic first slice (F8b's `normalize_text` has no external resource cost) — **defer `legoai.resources` entirely past Batch 1**; only required once a batch introduces a resource-bearing action.

## 18. Execution failure semantics

Canonical categories already exist in `legoai.kernel.errors` (`ErrorCategory`, `Recoverability`, `ErrorCause`, `ErrorDetail`) and are reused, not replaced, by every ADR (ADR-005 §16, ADR-006 §12, ADR-007 §11, ADR-008 uses `Conflict`/`VersionMismatch`/etc.). Mapping:

| Distinction | Canonical category (existing) |
|---|---|
| validation failure | `ValidationError` |
| admission failure | `PluginFailure` (ADR-006 §12: "used when no more specific category explains the Plugin failure") |
| authorization failure | `AuthorizationDenied` / `TenantViolation` |
| resource failure | `BudgetExceeded` |
| dispatch failure | `Conflict` (stale revision) / `DependencyFailure` (owner unavailable) |
| provider failure | `DependencyFailure` / `CapabilityResolutionError` |
| deadline exceeded | `DeadlineExceeded` |
| cancelled | not an error category — a canonical Execution *state* (ADR-015 §2: `cancelling`/`cancelled`) |
| partial / unknown effect | `EffectExtent.PARTIAL` / `EffectExtent.UNKNOWN` (Kernel, already exists — **not** an error category) |

**No giant new exception hierarchy is needed.** The only genuinely new category identified across all ADRs is `CapabilityResolutionError` (named explicitly in ADR-006 §12), which does not yet exist in `legoai.kernel.errors` and would need to be added when the Resolver is actually built (not Batch 1).

## 19. Retry / recovery / compensation

Kept distinct per ADR-008 §3/§7 and ADR-007 §11: **retry** = a new linked Execution attempt reusing the same operation/effect identity (ADR-008 §4.1); **recovery** = restart-time reconciliation of unresolved handoff-attempt records (ADR-007 §6.3, §13); **compensation** = "separately authorized work" (ADR-007 §11, ADR-008 §4.2) — explicitly never bundled with retry/recovery. None of the three belongs in the first Gate-2 batch (§20) since it has no dispatch, no effect, and nothing to retry/recover/compensate yet. **Unknown external effects are never auto-retried** (ADR-007 Timeline 11, ADR-008 §7).

---

## 20. Milestone decomposition and selected first batch

Decomposing §6's dependency graph into implementation-order milestones:

```text
M1  legoai.execution values (ExecutionState enum, ExecutionId, ExecutionContext, ExecutionResult)  <- SELECTED BATCH
M2  legoai.governance expansion (Grant, Policy, Approval values + Ports)                            [ADR-005]
M3  legoai.resources (new package: values + Ports)                                                  [ADR-007]
M4  legoai.reference.identity / .tenant / .authorization / .policy / .enforcement (realizations)     [ADR-005]
M5  legoai.reference.plugins (Lifecycle/admission realization)                                      [ADR-006]
M6  legoai.reference.catalog (new: registration/offer projections)                                  [ADR-006 §9]
M7  legoai.capabilities expansion + legoai.reference.resolution runtime Resolver                     [ADR-006 §8]
M8  legoai.reference.evidence (custody commit/repair realization)                                   [ADR-009]
M9  dispatch arbiter (private technical primitive)                                                   [ADR-007]
M10 legoai.reference.execution Coordinator + ADR-015 asyncio supervision                             [ADR-015]
M11 first governed deterministic invocation (uses F8b normalize_text as the Capability body)          [governed slice]
```

**Selected first Gate-2 implementation batch: M1 — `legoai.execution` values only.**

Why: on the critical path (every later milestone references `ExecutionContext`/`ExecutionId`); fully determined by ADR-015 §2's canonical state list and ADR-008 §4.1's identity domains (no invention needed); depends on no unresolved Proposed ADR (ADR-012/013 irrelevant to pure values); needs no external infrastructure (pure dataclasses/enum, stdlib only); deterministic (no I/O); independently testable (unit + negative tests, same pattern as Gate-1's Kernel/Governance values); unblocks M2 onward (nothing downstream can be typed correctly without this); feasible for a solo maintainer in one bounded batch. It is **not** Model/Embedding (§24/§27 excluded), and it follows §32's preference for values/contracts before runtime orchestration.

---

## 21. Exact scope — Batch 1 (`legoai.execution` values)

**WILL IMPLEMENT:**
- `legoai/execution/__init__.py` (inert, docstring only, per ADR-002 initializer pattern).
- `legoai/execution/values.py`:
  - `ExecutionState` enum: exactly the ten canonical states from ADR-015 §2 (`created, admitted, running, waiting, suspended, cancelling, succeeded, failed, cancelled, rejected`) — no additional states.
  - `ExecutionId` — new opaque Kernel-style identity (following `legoai.kernel.identity`'s existing pattern: frozen dataclass wrapping an opaque string/UUID-shaped value, `__post_init__` type/shape guards, no semantic meaning beyond identity).
  - `ExecutionContext` — frozen dataclass with exactly the fields justified in §14 above (`execution_id`, `operation`, `tenant_context`, `acting_principal`, `originating_requester`, `security_context_ref`, `correlation_id`, `trace_id`, `deadline`, `causation`), with `__post_init__` type guards mirroring `governance.values.OperationContext`'s existing style (tenant-consistency checks, no self-causation, explicit `Principal` type checks).
  - `ExecutionResult` — frozen dataclass carrying `execution_id`, final `ExecutionState` (restricted to the four terminal states: `succeeded`/`failed`/`cancelled`/`rejected`), `EffectExtent` (reusing the existing Kernel enum, preserving `UNKNOWN` distinctness), and an `ErrorDetail | None`.
  - A minimal opaque **security-context reference type** (e.g. `SecurityContextRef`) satisfying §14/§15's "reference, not a copy" requirement — this is new because ADR-005's actual issued security-context mechanism does not exist yet; the reference type only needs to exist as an opaque, typed placeholder Kernel-style value so `ExecutionContext` can be fully typed without inventing Governance's future decision mechanism.
- Negative/canary tests proving: no `dict[str, Any]` field is accepted anywhere; state transitions are not encoded as free-form strings; `ExecutionResult` rejects a non-terminal `ExecutionState`; tenant-consistency guard (mirroring `OperationContext`'s existing tenant-mismatch check) rejects cross-tenant `operation`/`causation`.
- Architecture-boundary test entries confirming `legoai.execution` imports only Kernel + its own values (no import of `governance`, `capabilities`, `plugins`, `resources`, `reference`, or `runtime`), matching ADR-002's DAG requirement.

**WILL NOT IMPLEMENT:**
- Any Port (`ExecutionCoordinatorPort` or similar) — deferred until M9/M10 define what admission/dispatch actually need from it.
- Any realization (`legoai.reference.execution`), Coordinator, admission logic, cancellation logic, or asyncio supervision.
- Any change to `legoai.governance`, `legoai.capabilities`, `legoai.plugins`, `legoai.evidence`, `legoai.observability`, `legoai.runtime`, or any `legoai.reference.*` module.
- Any new package (`legoai.resources` does not exist yet and is not created here).
- Any Ports, admission, dispatch, resource claim, authorization enforcement, or invocation logic of any kind.
- Any Model/Embedding/Agent/Workflow symbol, import, or reference.

---

## 22. Proposed files (for the eventual implementation task — not created in this planning task)

```text
Create:
  src/legoai/execution/__init__.py
  src/legoai/execution/values.py

Modify:
  tests/architecture/test_import_boundaries.py   (add legoai.execution to the scanned owner set)
  tests/architecture/test_package_install.py     (add new files to sdist expected-file-list assertion)

Create (tests):
  tests/unit/execution/__init__.py
  tests/unit/execution/test_values.py

Planning (this task's own output, already created/updated):
  planning/GATE-2-IMPLEMENTATION-PLAN.md          (this file)
  planning/NEXT-CORE-IMPLEMENTATION-BATCH.md       (pointer only, §27)
```

No production code, no source files beyond this list are proposed. None of the "Create" files above were written in this planning task.

---

## 23. Test strategy — Batch 1

- **Unit tests:** construction success for each value type with valid Kernel-typed inputs; enum membership completeness (exactly ten `ExecutionState` members, no more/fewer).
- **Invariant tests:** `ExecutionContext` tenant-consistency (operation/causation scope must match `tenant_context.tenant_id`, mirroring `OperationContext`'s existing check); `ExecutionResult` terminal-state-only guard.
- **Negative tests:** wrong type for every field (`TypeError`); non-terminal state passed to `ExecutionResult` (`ValueError`); attempted `dict`/`Any`-typed field addition caught by canary-style construction tests (mirroring Gate-1's `test_cannot_pass_callable_as_unsupported_field` pattern).
- **Contract tests:** none needed yet — no Port exists in this batch.
- **Architecture tests:** import-boundary DAG check (Kernel-only dependency); no-ambient-module-state check (reuse existing scanner, extend its file list).
- **Security tests:** confirm no field of any Batch-1 value type can carry a bare boolean/string "authorized" signal (static inspection test, mirroring §15's invariant).
- **Concurrency tests:** not applicable — pure immutable values, no shared state, no I/O.
- No external network/provider is used or required anywhere in this batch.

---

## 24. Risks

- **Risk: inventing `SecurityContextRef` prematurely constrains ADR-005's future actual issuance mechanism.** Mitigation: keep it maximally opaque (an identity wrapper only, no fields beyond an opaque reference value), exactly as `PrincipalRef`/`OperationRef` are already opaque in Kernel — this is the same pattern already accepted for Gate-1's forward references.
- **Risk: `ExecutionContext` field set is later found incomplete once Resources/Approval exist.** Mitigation: `ExecutionContext` is a frozen dataclass, not a public wire schema — extending it in a later, explicitly reviewed batch is expected and consistent with ADR-002's phased package table (`legoai.execution` is listed "Initial, phase 1" for values only).
- **Risk: scope creep toward building a Port "since it's easy."** Mitigation: this plan explicitly excludes it (§21); the reviewing task after Batch 1 must reject any Port addition that slipped in.

---

## 25. Path from selected batch to governed slice

```text
M1 legoai.execution values (this batch)
  → M2 legoai.governance expansion (Grant/Policy/Approval values+Ports)          [ADR-005]
  → M3 legoai.resources (new package)                                            [ADR-007]
  → M4 legoai.reference.identity/.tenant/.authorization/.policy/.enforcement      [ADR-005 realization]
  → M5 legoai.reference.plugins (admission/lifecycle)                            [ADR-006]
  → M6 legoai.reference.catalog                                                  [ADR-006 §9]
  → M7 capabilities runtime Resolver                                             [ADR-006 §8]
  → M8 legoai.reference.evidence (custody)                                       [ADR-009]
  → M9 dispatch arbiter                                                          [ADR-007]
  → M10 legoai.reference.execution Coordinator + ADR-015 asyncio supervision      [ADR-015]
  → M11 first governed deterministic invocation (F8b normalize_text as body)      [governed executable slice]
```

No security/governance step is skipped; M9 (dispatch) strictly follows M2–M8 (every predicate it must check jointly).

## 26. Future path to Model/Embedding (informational only)

```text
M11 governed deterministic execution (Gate-2 exit)
  → ModelPort semantics (legoai.intelligence.model — ADR-INDEX §9 deferred watchlist item)
  → model provider boundary / adapter contract
  → Ollama Adapter (or equivalent qualified local provider)
  → model.embedding capability, governed identically to M11's deterministic capability
  → resume DocuMind extraction (currently paused)
```

This path is not optimized for in Gate-2 design; it is shown only to confirm Gate-2's governed-execution substrate is the correct prerequisite, per ADR-INDEX's own deferred-decision register (§9: "Specific Model provider/first Model Adapter... No Model needed for deterministic slice").

---

## 27. Implementation readiness gate

```text
READY_TO_IMPLEMENT_GATE2_BATCH_1 = YES
```

Gate-1 qualified; Batch 1 (`legoai.execution` values) is canonically authorized (ADR-002 line 157, ADR-015 §2, ADR-008 §4.1); package placement resolved (`legoai.execution`, Kernel-only dependency); prerequisites exist (Kernel complete); no Proposed ADR (012/013) blocks pure values; no external infrastructure needed; tests fully defined in §23.

---

**DocuMind status:** `DOCUMIND_EXTRACTION = PAUSED` until the generic Model/Embedding substrate exists (§26). Not inspected further in this task except as the eventual consumer-validation reference named above.

---

## 28. M1 implementation status

```text
GATE2_M1_COMPLETE = YES
```

Implemented exactly the planned semantic value layer, no more: `src/legoai/execution/__init__.py` (docstring-only, matching every other owner's initializer convention) and `src/legoai/execution/values.py` defining `ExecutionState` (exact ten canonical states, ADR-015 §2), `ExecutionId`, `SecurityContextRef`, `ExecutionContext`, `ExecutionResult`. No Port, no realization, no Coordinator, no asyncio, no persistence, no Governance/Resources/Plugins/Evidence expansion, zero new runtime dependencies.

**One deviation from the plan's §14/§21 field sketch, discovered during implementation:** `ExecutionContext` does **not** carry `acting_principal`/`originating_requester` (`governance.values.Principal`) fields as originally sketched. ADR-002 §9's `values.py` rule states a values module "does not import another owner's values" — this is stricter than the foreign-*contract*-target table in §9.2 (which applies to `ports.py`, not `values.py`). Embedding `governance.values.Principal` directly in `execution/values.py` would violate that rule. `SecurityContextRef` (already planned) fully absorbs the identity/authority reference role instead, consistent with ADR-005 §10.1's own preference for an owner-issued reference over a raw Principal copy. `tenant_context: TenantContext` (Kernel-owned, not Governance-owned) was kept, satisfying ADR-005 §7 ("Each Execution pins exactly one effective TenantContext") without any cross-owner values import. This is a scope-preserving correction, not scope creep — it removes a field, adds none, and a later Port-layer batch is where Execution and Governance are actually composed together.

Architecture boundary rules were extended (`tests/architecture/test_import_boundaries.py`) to give `legoai.execution.values` the same Kernel-only import ceiling already used for `capabilities`/`plugins`/`observability` (narrower than ADR-002 §9.2's E-row maximum, since no M1 field needs any wider peer); a dedicated test proves `legoai.execution.values` cannot import `legoai.governance.values`. Wheel/sdist file lists and the F8b import-inertness script (`tests/integration/composition/test_import_inertness.py`) were extended to cover the two new production files.

Full verification: Core `pytest` 708 passed (was 634 before this batch: +56 unit tests on `legoai.execution.values`, +12 architecture boundary tests, +6 deadline-type coverage tests added during this batch's own coverage pass); `mypy src tests` — no issues in 67 source files; `ruff check`/`ruff format --check` — clean; `legoai.execution.values` itself at 100% branch coverage, overall unchanged at 94%; architecture tests 153 passed (was 141); package-install tests 5 passed including a fresh wheel build/install with `legoai/execution/__init__.py` and `legoai/execution/values.py` present and importable; Document Pack unchanged at 268 passed/64 skipped; zero new runtime dependencies (`git diff --stat HEAD -- pyproject.toml uv.lock` empty); no canonical document or Accepted ADR touched; DocuMind untouched.

**No Ports, Coordinator, Resolver, Governance expansion, Resources package, Plugin admission, Evidence custody, asyncio, or AI/Model code were introduced.** Gate-2 Batch 2 (governance expansion, per §20's M2) was not started.

---

## 29. M2 implementation status

```text
GATE2_M2_COMPLETE = YES
```

Extended the existing `legoai.governance.values` module only (no new package, no new module file) with the bounded-authority vocabulary required for the governed executable slice: `GrantId`, `ApprovalId`, `PolicyRef`, `Grant`, `Approval`. Gate-1's `Principal` and `OperationContext` are unchanged. No `AuthorizationPort`, policy engine, decision evaluator, Grant lookup, Approval consumption, or any current-validity check was implemented — every new value is a structural record of what was granted/requested, never proof it remains valid now.

**Narrowing of the plan's own §6 one-line sketch, not a contradiction:** §6's dependency graph listed M2 as "Grant, Policy, Approval values **+ Ports**." This task's explicit instruction (its own §4/§33/§61) required values-only, no Ports, in M2. This is a legitimate refinement of a rough one-line dependency-graph sketch by a more detailed batch-scoping instruction, consistent with the "values/contracts before Ports" preference already applied to M1 — not a reversal of accepted authority. `AuthorizationPort` remains for a later batch.

**Exact fields implemented, with citations:**
- `PolicyRef(issuer, policy_id, version)` — an opaque reference only (SECURITY SEC-022: "identify the accountable owner... jurisdiction... validity... revision"), reusing Kernel's generic `Version` (already reused generically for `contract_version`/`interpretation_version` in Gate-1's `ConfigurationRevisionRef`/`ApplicationRevisionRef`, so no redundant `PolicyVersion` type was introduced). No rule content, no evaluator.
- `Grant(grant_id, issuer, grantee, tenant_context, action, resource_scope, delegable, valid_from, expires_at)` — CTR: "Permission issued by an entitled authority, bounded by subject, action, resources, validity, and delegation conditions"; ADR-005 §9.1. `action`/`resource_scope` are opaque validated text, not a `resource:verb` syntax, per ADR-005 §9.1's explicit refusal to select a universal ACL schema. `expires_at` is optional (`None` = no stated time bound; still subject to a later live revocation check, never itself a wildcard/eternal-authority claim).
- `Approval(approval_id, operation, tenant_context, requester, approver, max_uses, valid_from, expires_at)` — SECURITY SEC-031's binding list, restricted to the subset with an already-canonical typed representation: exact operation/action+target via the existing `OperationRef`, tenant, requester/approver `Principal`, an explicit positive `max_uses` ceiling, and a **mandatory** (not optional) `expires_at`, since SEC-031 states "no implicit unlimited default." **Consciously not modeled** (no existing canonical typed representation exists for these, and inventing one would be scope creep beyond a values-only batch): "material input/configuration/content revisions," "risk context," "presented evidence," "decision rule," "conditions" — SEC-031 names these in prose but no accepted document defines their concrete value shape yet.

**Critical invariant preserved structurally, not just documented:** `identity ≠ authentication ≠ acting authority ≠ current authorization ≠ historical authorization evidence`. `Principal` (identity) has no authority field; `Grant`/`Approval` (bounded authority as issued) have no `revoked`/`currently_valid`/`consumed`/`remaining_uses` field — those are later live owner-state checks (ADR-005 §12, ADR-007 §6.2), proven absent by dedicated tests rather than asserted only in prose.

**Execution boundary unchanged:** `git diff --stat HEAD -- src/legoai/execution` is empty. `legoai.execution.values` still does not import `legoai.governance.values` (already enforced by M1's own architecture rule); no contradiction was found requiring that boundary to change.

Full verification: Core `pytest` 772 passed (was 708 before this batch: +49 initial unit tests on the new Governance values, +9 additional coverage-closing tests for wrong-type temporal fields, +6 sdist/wheel smoke additions counted in the architecture suite); `mypy src tests` — no issues in 68 source files; `ruff check`/`ruff format --check` — clean; `legoai.governance.values` at 100% branch coverage, overall coverage **95%** (up from 94%, since the new module is fully covered); architecture tests 153 passed (unchanged — no new boundary rule was needed, since Governance's existing Kernel-only-plus-own-values rule already covers the new classes); package-install tests 5 passed including a fresh wheel build/install with `Grant`/`Approval`/`PolicyRef` constructed and asserted in the smoke script; Document Pack unchanged at 268 passed/64 skipped; zero new runtime dependencies (`git diff --stat HEAD -- pyproject.toml uv.lock` empty); no canonical document or Accepted ADR touched; DocuMind untouched.

**No AuthorizationPort, policy engine, Grant lookup, Approval consumption/replay-store, Resources package, Plugin admission, Catalog, CapabilityResolver, Coordinator, async supervision, or AI/Model code were introduced.** Gate-2 Batch 3 (Resources, per §20's M3) was not started.

---

## 30. M3 implementation status

```text
GATE2_M3_COMPLETE = YES
```

Created the ADR-002-authorized `legoai.resources` package (`__init__.py` + `values.py`) with the minimum declarative vocabulary needed to describe a resource requirement or accounting fact: `ResourceDimension`, `ResourceAmountKind`, `ResourceQuantity`, `ResourceClaimId`, `ResourceClaim`. No `ResourcePort`, allocation/reservation engine, quota/budget service, or capacity discovery was implemented.

**Deliberately not modeled, with reasons:**
- **Budget/Quota/Limit** (ADR-007 §9.1's three distinct constraint concepts) — these are allocation/policy constraint types whose meaning depends on window/reset/occupancy semantics that are runtime accounting concerns owned later by Resource Admission and Accounting, not needed merely to describe a declared claim.
- **Precision/rounding/uncertainty** (ADR-007 §9's remaining quantity axis) — no accepted document defines a concrete typed shape for this yet; inventing one risks exactly the guessed-taxonomy problem `ResourceDimension` deliberately avoids.
- **`ResourceReservation`/`ResourceConsumption` as separate types** — a single `ResourceClaim` + `ResourceQuantity.amount_kind` (estimate/bound/reservation/actual/correction, taken verbatim from ADR-007 §9) already expresses the full declared-vs-accounting-fact distinction without inventing near-duplicate wrapper types "for symmetry" (task's own §7 warning).

**Design decisions with citations:**
- `ResourceDimension` is an opaque validated-text identifier, not a closed enum of compute/memory/network/tokens/...: ADR-007 §3/§14 explicitly states no resource quantum is selected and that dimension parameters come from "their accountable authority." An enum would have silently invented that authority's answer.
- `ResourceQuantity.magnitude` uses `Decimal` (nonnegative, finite — NaN/Infinity/bool-as-int all rejected), avoiding float ambiguity; `unit`/`unit_version` follow the same opaque-text-plus-reused-`Version` pattern already established for M2's `PolicyRef`.
- `ResourceClaim` binds to exactly **one** resource dimension (one `ResourceQuantity`), not a bundle: ADR-007 §9.1's "multi-dimension bound" requirement means dispatch later assembles a *collection* of per-dimension claims, not that one claim record should merge dimensions.
- `ResourceClaim` binds to the logical operation via Kernel's `OperationRef` only (never `ExecutionId`): ADR-002's R-row foreign-contract-target table lists K/G/O, not E, and even G/O are only a `ports.py` maximum — `values.py` stays Kernel-only per ADR-002 §9's "does not import another owner's values" rule, exactly as already established for `execution.values` (M1) and `governance.values` (M2). This preserves `operation identity ≠ execution identity` structurally, not just by convention.

**Critical invariant preserved structurally:** no field named `available`, `capacity_available`, `reserved`, `is_reserved`, `unlimited`, `authorized`, `approved`, `grant`, `approval` or `policy` exists on any M3 value — proven absent by dedicated tests, not merely asserted in prose. Constructing a `ResourceClaim` with `amount_kind=RESERVATION` or `ACTUAL` still does not mean a reservation succeeded or consumption was authoritatively recorded; that remains a later owner-committed fact under a `ResourcePort` this batch does not define.

Full verification: Core `pytest` 838 passed (was 772 before this batch: +51 unit tests on the new Resource values, +15 architecture boundary tests, +2 sdist/wheel smoke-script additions); `mypy src tests` — no issues in 71 source files; `ruff check`/`ruff format --check` — clean; `legoai.resources.values` at 100% branch coverage, overall coverage unchanged at 95%; architecture tests 168 passed (was 153); package-install tests 5 passed including a fresh wheel build/install with `ResourceQuantity`/`ResourceClaim` constructed and asserted in the smoke script; Document Pack unchanged at 268 passed/64 skipped; zero new runtime dependencies (`Decimal` is stdlib; `git diff --stat HEAD -- pyproject.toml uv.lock` empty); no canonical document or Accepted ADR touched; DocuMind untouched. `src/legoai/execution` and `src/legoai/governance` are unchanged (`git diff --stat` empty for both).

**No ResourcePort, allocation/reservation engine, quota/budget service, capacity discovery, authorization runtime, Plugin admission, Catalog, CapabilityResolver, Coordinator, async supervision, or AI/Model code were introduced.** Gate-2 Batch 4 (M4: identity/tenant/policy runtime realization) was not started.

---

## 31. M4 implementation status

```text
GATE2_M4_COMPLETE = YES
```

Implemented the minimum current-authority evaluation seam: `src/legoai/governance/ports.py` (new — `RevocationStatus`, `PolicyCurrencyStatus`, `AuthorizationOutcome`, `ApprovalUseState`, `SecurityContext`, `AuthorizationDecision`, and the `GrantStatePort`/`ApprovalUsePort`/`PolicyCurrencyPort`/`AuthorizationPort` Protocols) and `src/legoai/reference/governance.py` (new — `DeterministicAuthorizationEvaluator`, the sole reference realization of `AuthorizationPort`). No Plugin admission, Catalog, Resolver, dispatch, Coordinator, async supervision, or Resource allocation/enforcement was implemented.

**One necessary, minimal Kernel extension:** `legoai.kernel.errors.ErrorCategory` gained two members, `AUTHORIZATION_DENIED` and `POLICY_VIOLATION` — both already named as distinct canonical categories in CONTRACTS' Base error table, with M4 as their first real consumer (mirroring how F4/F5 grew this same enum incrementally for their own first real consumers). The five existing members are unchanged; the one Gate-1 exhaustiveness test (`tests/unit/kernel/test_foundation.py`) and the package-install smoke count were updated to match.

**Architectural clarification discovered during implementation, not a contradiction:** `governance/ports.py` does **not** import `legoai.execution.values.SecurityContextRef`. ADR-002's G-row allowed foreign targets (K, R, O) do not include E, and `execution.values` does not import Governance either (M1's own rule). Mapping an Execution-held `SecurityContextRef` to the `SecurityContext` this batch defines is therefore explicitly deferred to a later composition-layer batch (only the "Application"/public-runtime-consumer plane, ADR-002 §9.2, is permitted to import both) — `execution.values` is confirmed unchanged (`git diff --stat HEAD -- src/legoai/execution` empty).

**Design decisions with citations:**
- `SecurityContext` bundles already-established facts (principal, tenant, operation, action/resource-scope text mirroring `Grant`'s own shape, a candidate `Grant`/`Approval`, a `PolicyRef`, and a caller-supplied tz-aware `established_at`) — never a decision, never proof of current validity.
- `AuthorizationDecision.outcome` is a three-member enum (`ALLOWED`/`DENIED`/`UNAVAILABLE`), never a bare bool, keeping "denied" structurally distinct from "infrastructure/dependency failure" (task §12/§37); `category` is `None` iff `ALLOWED`, enforced structurally.
- Three supporting Ports (`GrantStatePort`, `ApprovalUsePort`, `PolicyCurrencyPort`) model exactly the three current-state facts `Grant`/`Approval`/`PolicyRef` deliberately omitted in M2 (revocation, use-count, currency) — no Grant/Approval/Policy *lookup* capability is added; the caller supplies the exact candidate values already found elsewhere.
- `DeterministicAuthorizationEvaluator` performs exact-match checks only (grantee/tenant/action/resource-scope/time-interval for Grant; operation/requester/time-interval for Approval — the Approval-side tenant check was found to be structurally redundant given both `Approval` and `SecurityContext` already enforce `operation.scope.tenant_id == tenant_context.tenant_id`, and was removed with that reasoning documented in the source) — no wildcard/substring matching, no RBAC inheritance.
- Time-interval semantics (not specified by any canonical document) are chosen as `[valid_from, expires_at)` — inclusive lower bound, exclusive upper bound — documented explicitly in the source and exercised at all five boundary instants (before/at valid_from, just-before/at/after expires_at) for both `Grant` and `Approval`.
- Fail-closed discipline: unknown revocation, unknown approval-use state, and unknown policy currency each produce `UNAVAILABLE`/`DEPENDENCY_FAILURE`, never `ALLOWED`; a missing candidate `Grant` produces `DENIED`/`AUTHORIZATION_DENIED` (a definite fact, not an unknown one).
- `Grant.max_uses`/`Approval` are never mutated; `ApprovalUseState` is a separate read-only current fact, and the contract suite includes an explicit test proving evaluation never changes `Approval.max_uses`.
- Test-only Port fakes (`InMemoryGrantStateFake`, `InMemoryApprovalUseFake`, `InMemoryPolicyCurrencyFake`) live under `tests/support/governance.py`, not as a production fallback; a dedicated architecture test proves `legoai.reference.governance` cannot import them.
- No identity-verification/authentication Port was built: M4 consumes already-verified `Principal` facts (per Gate-1), per the task's own permissive framing: "If M4 consumes already-verified identity facts, make that boundary explicit." No JWT/OIDC/credential handling of any kind exists.

Full verification: Core `pytest` 926 passed (was 838 before this batch: +31 contract tests, +2 architecture-test additions to existing kernel exhaustiveness/composition-root-independence lists, +~40 new unit tests on `governance.ports`/`reference.governance`, +6 new dedicated architecture-boundary tests); `mypy src tests` — no issues in 76 source files; `ruff check`/`ruff format --check` — clean; `legoai.governance.ports` and `legoai.reference.governance` both at 100% branch coverage, overall coverage unchanged at 95%; architecture tests 174 passed (was 168); package-install tests 5 passed including a fresh wheel build/install that constructs and evaluates a `SecurityContext` end-to-end to `ALLOWED`; Document Pack unchanged at 268 passed/64 skipped; zero new runtime dependencies; no canonical document or Accepted ADR touched; DocuMind untouched. `src/legoai/execution/values.py`, `src/legoai/resources/values.py`, and `src/legoai/governance/values.py` are all confirmed byte-for-byte unchanged.

**No Plugin admission, Catalog, CapabilityResolver, dispatch, Coordinator, async supervision, Resource allocation/enforcement, or AI/Model code were introduced. M4 establishes "authorized at evaluation time" only — it does not and cannot establish "authorized for dispatch forever"; ADR-007's exclusive dispatch gate still owns final revalidation.** Gate-2 Batch 5 (Plugin admission/lifecycle, per §20's M5) was not started.
