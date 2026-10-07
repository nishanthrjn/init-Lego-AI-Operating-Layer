# SECRET-REF-1A — accepted bounded shared local arbitration scope

**Status: ACCEPTED — 2026-10-07 by explicit maintainer decision.**
**Date:** 2026-10-07.
**Outcome:** Bounded shared local ordering scope authorized as a prerequisite
for SECRET-REF-1A; no implementation or qualification established.

This is the separate maintainer decision required by
[the accepted staged scope, §8](LEGOAI-SECRET-REF-1-DECISION.md#8-accepted-implementation-order--2026-10-07).
Stage A remains unimplemented and unqualified. Stage B remains gated. G03 remains
open. No ADR is allocated or amended by this document.

## 1. Exact unmet guarantee

ADR-010 §8.2 requires current authority, Secret eligibility and all participating
invalidators to share an effective order with the actual protected use. Section
8.3 requires a revocation that becomes effective before use acceptance to prevent
that use. ADR-007 §§4–6 requires participation at the authoritative mutation
commit, not merely a caller convention. A permit, queued task or earlier
authorization decision is not protected acceptance.

Current source has neither a shared mutation/acceptance participation seam nor
an actual-consumer-acceptance operation within the dispatch arbiter. Satisfying
these requirements with existing authority owners would change their mutation
and arbitration contracts beyond the authorized additive Secret Access scope.
The blocker applies to a synchronous synthetic consumer too; HTTP is not its cause.

## 2. Concrete source inventory

| Existing fact/path | Source seam | Ordering currently established |
| --- | --- | --- |
| Grant revocation | `src/legoai/reference/governance.py`: `InMemoryGrantRegistry.revoke`, `current_revocation_status` | Direct set mutation/read; no participation in dispatch's lock |
| Policy supersession | Same file: `InMemoryPolicyRegistry.supersede`, `current_status` | Direct set mutation/read; no participation in dispatch's lock |
| Approval use exhaustion, when applicable | Same file: `InMemoryApprovalRegistry.consume`, `current_use_state` | Direct count mutation; arbiter calls consume under its own lock, but the owner does not enforce that lock on other callers |
| Consumer capability eligibility | `src/legoai/reference/catalog.py`: `publish`, `withdraw`, `snapshot` | Local catalog revision/list; no shared arbitration participation; withdrawal is an existing eligibility invalidator, not a Secret-specific consumer-revocation service |
| Final dispatch check | `src/legoai/reference/execution.py`: `DeterministicDispatchArbiter.__init__`, `arbitrate` | Private `threading.Lock`; checks authority/catalog/evidence, consumes applicable approval, returns an inert `DispatchPermit` and releases the lock |
| Invocation uniqueness | Same file: `ExecutionCoordinator.claim_invocation` | Separate `asyncio.Lock` guards RUNNING/claimed state; does not jointly revalidate Grant/Policy/Catalog or accept protected material |
| Authority expiry | `reference/governance.py`: `_grant_covers`, `_approval_covers`; `governance/ports.py`: `SecurityContext.established_at` | Evaluation uses supplied context time; not an atomic expiry guard at a later Secret-use acceptance point |
| Required evidence availability | `src/legoai/reference/evidence.py`: `InMemoryEvidenceCustody.record`, `read` | Append-only process-local custody; no delete/revoke API and no concurrency or durability claim. Do not invent an evidence-removal invalidator |
| Secret mapping/revision/eligibility invalidation | No Secret Access realization in current `src/legoai/governance` or `reference/secret` | Not implemented; not counted as existing participants |
| Dedicated Secret consumer invalidation | Not implemented | Catalog withdrawal is relevant existing eligibility behavior, but does not supply this missing Secret contract |
| Tenant/owner/configuration identity | Existing immutable nominal values and captured configuration | Scope constraints, not a discovered live Secret mutation API; mismatch must be rejected by any future implementation |

The observation sink projects safe observation fields; it is not mandatory
evidence custody or a repair ledger. Configuration capture/composition retains
revision identity; it does not establish Secret currentness. The Model adapter's
`to_thread` invocation does not provide the missing gate. None of these modules
was changed or used to acquire material.

## 3. Counterexample derived from source

This is a source-derived interleaving, **not an executed race-test result**:

1. The authorization evaluator reads ACTIVE from the Grant registry.
2. `revoke(grant_id)` changes that registry and returns; it need not acquire
   the arbiter's private lock.
3. Authorization continues with policy/approval checks and can return ALLOWED
   without rereading grant status.
4. The arbiter can issue its inert permit. The separate invocation claim does
   not check grant status; a hypothetical consumer then accepts use.

A still simpler gap exists between permit issuance and any later acceptance:
revocation can finish entirely in that interval. Moving a final recheck into a
new Secret-only lock leaves a check-to-use interval that current mutation APIs
do not honor. Adding repeated reads does not establish an atomic ordering proof.
The same structural issue exists for policy supersession and applicable catalog
withdrawal. This is a missing guarantee for the new Secret-bearing scope, not a
retraction of credential-free provider qualification.

## 4. Smallest candidate change for maintainer review

Authorize a narrowly scoped **shared local arbitration participation design**,
before resuming SECRET-REF-1A implementation:

1. Specify one explicit, process-local ordering domain, injected through trusted
   composition. It owns ordering only; Governance, Catalog, Evidence and Execution
   retain their decisions and state. No global singleton or distributed protocol.
2. Make every supported invalidating owner commit participate by construction,
   beginning with grant revocation, policy supersession and applicable approval/
   catalog mutations. Direct owner APIs must not bypass it. Determine compatible
   legacy construction and reject mismatched participant domains for protected use.
3. Specify a bounded, non-reentrant private exact-acceptance operation combining
   final revalidation, applicable consumption and a synchronous synthetic consumer's
   acceptance. Do not expose the arbiter's lock as a public convenience API or hold
   it during network waits. Review lock order against the Coordinator's claim and
   cancellation paths before choosing concrete signatures.
4. Define acceptance-time clock assumptions and unsupported expiry guarantees.
   A deterministic clock test does not establish a hard real-time CPython bound.
5. Define safe accepted-use attribution and post-use evidence repair ownership.
   Existing in-memory custody cannot justify a durable repair claim; any required
   durable extension needs explicit scope approval rather than an in-memory substitute.

This accepted bounded design is not a completed proof or an instruction to implement
a general Coordinator rewrite. The first known required changes cross Governance
mutation and dispatch arbitration seams. Whether the Coordinator itself needs
changes must be resolved in that design; no necessity for a complete rewrite is
asserted. An independent synthetic authority universe would not prove participation
of today's supported owners and is not a substitute.

## 5. Affected authority and verification requirements

- ADR-010 §§7–11, 14, 21: exact purpose/use, currentness, lifetime, safe evidence.
- ADR-007 §§4–8: all mutation paths, actual acceptance, partial consumption, time.
- ADR-005: current authority and requester/deputy/tenant scope.
- ADR-009: pre-use custody and truthful post-effect repair obligations.
- CONTRACTS §15.5 and existing authorization/dispatch/claim contracts: reference-only
  public operations; any new participation surface must preserve owner direction.
- SECURITY SEC-020, SEC-057–060 and §20: current applicability and restricted disclosure.
- ADR-014: composition may wire admitted implementations but does not authorize a
  new credential-bearing path by itself. ModelPort and model settings stay unchanged.

Before implementation, specify deterministic event/barrier tests
for revoke/policy/catalog changes before and after acceptance, all supported owner
mutation entry points, competing uses, cancellation and expiry. Test pre-evidence
failure and post-acceptance recording failure without retrying use. Then resume
the complete Stage A contract, canary, single-use, restart and regression matrix.

No tests or `validate_secret_ref_1.py` were created: the explicit stop condition
was reached before implementation. No successful race proof or Stage A validation
is claimed. This documentation change is checked with `git diff --check`.

## 6. Accepted decision and unchanged gates

The maintainer explicitly accepts only the bounded shared-domain design in §4,
subject to the implementation constraints in §7 below. Do not mark Stage A
qualified until its executable proof passes. Changes beyond this bounded
authority require a separate maintainer decision.

Stage B, environment sources, model credential fields/headers, authenticated
providers, remote disclosure and KISSKI remain disabled. No credentials,
environment variables, network endpoints or Docker were accessed by this work.

## 7. Accepted implementation constraints — 2026-10-07

Exactly one shared process-local ordering domain is authorized, injected through
trusted composition. It owns ordering participation only. Governance retains
grant/policy/approval state, Catalog contribution eligibility, Evidence custody,
Execution dispatch/invocation semantics, and Secret Access reference/use semantics.
No owner state is moved into a combined owner.

All supported mutation paths relevant to protected use must participate by
construction in that same domain: grant revocation, policy supersession,
applicable approval mutation/consumption, Catalog withdrawal/eligibility changes,
future Stage-A Secret mapping/revision invalidation, and protected acceptance.
Caller convention or alternate bypassing mutation APIs are insufficient.
Preserve credential-free construction and behavior; protected use must fail
closed on missing or mismatched domains, never silently create independent
domains that appear compatible. Unrelated consumers acquire no Secret semantics.

Authorize one bounded, non-reentrant, private synchronous exact-acceptance
operation for final current-authority, policy/eligibility and Secret revision/use
validation, applicable approval consumption, and consumer acceptance of one exact
use. Do not expose a raw lock, generic transaction facility or application-facing
ordering convenience. Applications, Agents, ModelPort and provider adapters must
not manipulate the ordering primitive. Any genuinely necessary public type/Port
requires explicit justification.

Before concrete locking is implemented, produce a lock-order analysis covering
the shared domain, DeterministicDispatchArbiter, ExecutionCoordinator claim lock,
Governance registries, Catalog and Evidence interactions. Avoid inversion and
reentrant deadlock; unsafe ordering requires a stop, not a timeout workaround.
Do not hold the gate during network I/O or call enqueue, task/worker/future
creation or `asyncio.to_thread` submission actual acceptance.

Invalidation or expiry effective before acceptance must prevent acceptance;
later invalidation cannot erase accepted use. Support deterministic acceptance-
time tests without claiming hard-real-time expiry. Required pre-use custody must
complete before acceptance. Post-acceptance evidence failure preserves truthful
use/effect knowledge and repair/reconciliation duties without automatic repeat.
If normative compliance requires durable custody beyond existing support, stop
and request separate scope; no durable evidence subsystem is authorized here.

Stop and report if participation needs a broader semantic redesign, safe ordering
cannot be established in this scope, or an ADR contradiction is found. This is
an implementation profile under ADR-005/007/009/010 and existing dispatch
contracts; no ADR semantics are changed and no new ADR is allocated.

Explicit non-goals: general Coordinator rewrite, distributed arbitration, global
singleton lock, remote execution, credential support, environment-backed Secrets,
OpenAI credential headers, KISSKI, retry/fallback changes, and generalized
workflow/runtime redesign.

SECRET-REF-1A remains unimplemented and unqualified; Stage B remains gated and
G03 remains open. This acceptance task changes documentation only. Arbitration
implementation does not begin in this task.

## 8. Implementation assessment — 2026-10-07

**SECRET-REF-1A STOPPED — DURABLE CUSTODY SCOPE REQUIRED.**

The subsequent implementation request authorizes Stage A and the shared local
domain above. That authorization is not the blocker. Its explicit durability
stop condition applies before implementation; Stage A remains unimplemented and
unqualified. The following is source analysis, not an executed ordering proof.

### Lock inventory and candidate partial order

`reference/execution.py` has two independent synchronization primitives:
`DeterministicDispatchArbiter._lock` is a synchronous `threading.Lock`, held
across authorization evaluation, Catalog snapshot, Evidence reads and applicable
Approval consumption. It returns an inert permit, not consumer acceptance.
`ExecutionCoordinator._lock` is an `asyncio.Lock` guarding state and invocation
claims. Claim releases it before invoking a consumer; settlement acquires it
separately. No existing nested acquisition establishes Secret-use ordering.

Governance registries, Catalog and in-memory Evidence have no owner-local locks.
The supported mutation entry points are Grant `revoke`, Policy `supersede`,
Approval `consume`, and Catalog `publish`/`withdraw`. Future Secret mapping and
revision invalidation must join the same domain. Evidence is append-only and
has no removal API to treat as an invalidator. `runtime/local.py` currently
constructs independent reference owners and in-memory Evidence custody; it does
not wire a shared domain. Governed Model composition claims invocation before
calling the provider and settles afterward; that path must remain unchanged.

A candidate Stage-A order, derived from these existing separable scopes, is:

1. Complete required pre-use custody and safe source-obligation preparation.
2. Where Coordinator invocation is used, acquire/release its claim lock before
   entering the protected boundary. A claim does not authorize Secret use.
3. Acquire the single shared synchronous domain; perform final current authority,
   policy, Catalog, Secret revision/use, expiry and cancellation checks; consume
   applicable Approval and accept the exact synthetic use within that boundary.
4. Release the domain before any await, settlement or post-use custody operation.

The protected arbiter path must use the domain instead of nesting its old lock
with the domain. Participating public mutations acquire that domain once;
already-held internal operations must not reenter guarded public methods.
Owners retain their state and decisions; the domain owns ordering only. No
Coordinator lock may be held while waiting for the domain, and no code inside
the domain may acquire the Coordinator lock. Missing/mismatched domain identity
must refuse protected use. Arbitrary injected Port callbacks cannot be assumed
bounded or non-reentrant: only qualified synchronous participants and the private
synthetic consumer could run there, without I/O, task submission or callbacks
into guarded entry points.

Cancellation while waiting needs an ordered pre-acceptance check; synchronous
lock waiting alone does not deliver asyncio cancellation. Cancellation after
acceptance cannot erase use. A concrete cancellation participation mechanism
and deterministic event/barrier tests remain unimplemented. The same is true of
injected-clock expiry tests; this analysis establishes no hard-real-time bound.
The candidate avoids nested lock inversion by construction, but is not a claim
that the complete acceptance/cancellation protocol has been implemented or proved.

### Independent evidence blocker

[ADR-010 §14](../adrs/ADR-010.md) requires a **durable repair/intervention
obligation** after post-effect evidence failure. [ADR-009 §§8.2–9](../adrs/ADR-009.md)
requires crash-discoverable source identity and submission responsibility before
effectful handoff; for a purely local source mutation, the fact and obligation
commit atomically. A volatile accepted-use flag and repair list cannot satisfy
this requirement even for a synthetic consumer. Failing closed after restart
prevents further use but does not recover a lost accepted-use obligation.

`reference/evidence.py:InMemoryEvidenceCustody` explicitly has no persistence or
concurrency guarantee. `evidence/ports.py:EvidenceRecord` supports configuration
revision and authorization-decision subjects, with no Secret-use custody or
durable repair contract. Coordinator claims/state are also process-local.
`reference/application/sqlite_store.py:SQLiteConfigurationStore` is an
Application Configuration store, not an Evidence custodian or Secret-use ledger;
repurposing it would require new owner contracts and qualification. Observation
and logs cannot supply the missing custody guarantee.

The smallest additional maintainer decision needed is a bounded local durable
safe-use attribution/repair scope under ADR-004/009/010: identify the source owner,
define safe intent/fact/obligation commits and discoverable repair, define the
required Evidence custody acknowledgment, and qualify crash/failure behavior.
It must resolve atomic local acceptance attribution without holding this gate
across disallowed work or assuming an in-memory substitute is durable. Material
and live handles must never be persisted. This is a scope request, not approval
to implement a database, generic transaction API or broader Coordinator redesign.

No source, contracts, tests, validator or ADRs were changed. No executable race,
restart or qualification result is claimed. Documentation verification is
`git diff --check`. Stage B, environment sources, provider credentials, remote
use and KISSKI remain gated; G03 remains open.

Durability follow-up (2026-10-07): [bounded source-use and custody decision](LEGOAI-SECRET-USE-DURABLE-CUSTODY-DECISION.md)
is **ACCEPTED** by explicit maintainer decision. Its [durable prerequisite is
LOCALLY QUALIFIED](LEGOAI-SECRET-USE-DURABLE-CUSTODY-DECISION.md#11-secret-use-durable-custody-1-implementation--2026-10-07)
from the operator's 72-phase result. Shared arbitration acceptance remains valid;
the prerequisite gate is satisfied, but Stage A remains unresumed/unqualified
pending explicit resumption. Stage B and KISSKI remain gated.

## 9. Resumed Stage-A implementation — 2026-10-07

**SECRET-REF-1A LOCALLY QUALIFIED.** The maintainer explicitly
resumed the accepted Stage-A scope after the 72-phase durable prerequisite was
locally qualified. The earlier stopped/unresumed assessments above are historical.
The implementation reuses that ledger/custody profile and adds reference-only
Secret Access, shared owner mutation participation and exact synthetic acceptance.
See the [implementation and lock-order analysis](../docs/secret-ref-1a.md).

Operator command: `uv run python .\validate_secret_ref_1.py` (62 phases).
No broader Coordinator/runtime redesign, ADR amendment, environment source,
credential or provider integration is included. G03 remains open. Stage B remains
gated on its separately authorized consumer boundary; neither
stage authorizes remote use or KISSKI. The operator qualification below
supersedes the implementation-time pending status.

## Operator local qualification recorded — 2026-10-07

**SECRET-REF-1A LOCALLY QUALIFIED.** Operator command:
`uv run python .\validate_secret_ref_1.py`. All 62 phases passed, including
69 focused tests, owner/runtime/consumer regressions, durable crash/recovery,
mypy, Ruff lint/format and diff checks. See the
[qualification evidence and limits](../docs/secret-ref-1a.md#operator-local-qualification-recorded--2026-10-07).

The Stage-A qualification prerequisite is satisfied for synthetic owner-thread
acceptance and intact local storage, without a broader Coordinator redesign.
Stage B remains gated on its separately authorized consumer/HTTP boundary;
no credentials, external provider, remote use or KISSKI qualification is established.
G03 remains open. Earlier pending/stopped assessments are historical.
