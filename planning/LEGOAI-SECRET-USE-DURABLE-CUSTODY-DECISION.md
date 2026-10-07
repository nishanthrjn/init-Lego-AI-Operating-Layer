# Secret use durable custody — bounded scope decision

**Status: ACCEPTED — 2026-10-07 by explicit maintainer decision.**
**Date:** 2026-10-07.
**Source baseline:** `6018515938ac2d322ce2727e2de56cd9811e5b32`.
**Decision:** SECRET-SPECIFIC DURABLE USE LEDGER JUSTIFIED.

Select option C with separately owned Evidence custody, not an Evidence-owned
acceptance journal. This is an accepted bounded implementation profile of
ADR-004/008/009/010. No ADR status or semantics are changed. The next implementation
slice is SECRET-USE-DURABLE-CUSTODY-1; this acceptance record implements nothing.
SECRET-REF-1A remains stopped until that prerequisite is implemented and locally
qualified.

## 1. Requirement and inspected evidence

[ADR-010 §§11, 14](../adrs/ADR-010.md) requires safe exact-use attribution and a
durable repair/intervention obligation after post-effect evidence failure.
[ADR-009 §§8.2–9](../adrs/ADR-009.md) assigns pre-handoff submission responsibility
and outstanding submission duties to the source owner, separately from Evidence
custody. For a purely local source mutation, source fact and obligation commit
atomically. [ADR-004 §§5.1, 9–13](../adrs/ADR-004.md) requires owner-local atomic
state/result/obligation records, lost-acknowledgment status and crash discovery.
[ADR-008 §§3, 5, 9, 11](../adrs/ADR-008.md) retains owner-local operation meaning
and partial completion without a global journal or automatic repeat.

[CONTRACTS §§15.5, 25, 28–29](../contracts/CONTRACTS.md) separates
`record_secret_use` from `record_audit_evidence`, source effects from custody,
and mandatory evidence from telemetry. SEC-057–060, 073–077 and 081–085 in
[SECURITY](../security/SECURITY.md) require current exact use, safe attribution,
tenant isolation, actual custody guarantees and truthful effect uncertainty.

| Inspected source | Actual capability and limit |
| --- | --- |
| `src/legoai/evidence/ports.py` | `EvidenceRecord.subject` is only configuration revision or authorization decision; `record` returns a record, `read` looks up exact identity. No explicit durable receipt, source-use transaction or discoverable repair lifecycle. |
| `src/legoai/evidence/values.py` | `EvidenceRequirement` names a configuration revision and description; it is not custody or a receipt. |
| `src/legoai/reference/evidence.py` | Dictionary custody; explicitly no persistence or concurrency guarantee. |
| `src/legoai/application/ports.py` | Configuration-only publish/result/outstanding-duty operations. A useful owner-boundary precedent, not a Secret/Evidence API. |
| `src/legoai/reference/application/sqlite_store.py` | SQLite configuration schema and owner-local durability settings; not a general ledger or Evidence custodian. |
| `src/legoai/reference/application/recovery.py` | Read-only configuration inspection, integrity/representation checks and outstanding duties; no execution or replay. Its qualification does not transfer to a new store. |
| `src/legoai/reference/execution.py` | Private dispatch lock returns a permit; separate Coordinator asyncio lock guards volatile state/claims. Neither commits actual Secret acceptance. |
| `src/legoai/reference/governance.py` | Grant revoke, Policy supersede and Approval consume are process-local mutations. Approval consumption can precede later failure; it is not automatically refunded. |
| `src/legoai/reference/catalog.py` | Publish/withdraw and revisions are process-local; no durable Secret-use state. |
| `src/legoai/observability/{ports,values}.py` | Diagnostics only; emission is not custody or source authority. |
| `src/legoai/runtime/local.py` | Independent reference registries, in-memory Evidence, arbiter and Coordinator; no shared durable Secret boundary. |

Also inspected the accepted [Secret scope](LEGOAI-SECRET-REF-1-DECISION.md),
[arbitration scope and lock assessment](LEGOAI-SECRET-REF-1A-ARBITRATION-DECISION.md),
and roadmap G02/G03/G06. Accepted shared arbitration remains valid; its cancellation
mechanism and executable proof remain outstanding. No existing contract is inferred
from a prior conversation or from the mere availability of SQLite.

## 2. Options

| Option | Correctness, ownership and atomicity | Discovery, scope, reuse and coupling | Stage-A disposition |
| --- | --- | --- | --- |
| A. Persistent Evidence adapter, unchanged contracts | Can retain existing evidence, but cannot create the source acceptance fact or express its duty/receipt. Dual write remains. | Small implementation, useful storage reuse, insufficient semantic coverage. | Reject as sufficient. |
| B. Evidence extension for attribution/repair plus adapter | Correct for Evidence-owned custody and its repair; incorrect if Evidence starts owning consumer acceptance or Secret use state. | Reusable custody receipts/subjects; source lifecycle still needs another owner. Moderate complexity. | Necessary supporting capability, insufficient alone. |
| C. Secret-owned durable use ledger, separate Evidence | Source owner atomically commits its own synthetic acceptance, fact and duty. Evidence separately acknowledges custody. | Narrow domain storage, two explicit owner boundaries, no universal journal; moderate implementation/qualification cost. | Recommend only for the precisely bounded consumer in §3. |
| D. General execution/event transaction journal | Recording more events does not atomically change an independent consumer. Risks moving owner state or cross-owner transactions. | Broad coupling, high complexity; general recovery reuse is not a present requirement. | Reject for this local profile; stop if independent consumer atomicity is required. |
| E. Volatile evidence, defer durability | Loses mandatory duty on crash; violates ADR-009/010 for this scope. | Small code, no qualifying recovery. | Reject. |

## 3. Selected owner and exact atomicity boundary

Secret Access, under Governance, owns the source-use ledger. The private Stage-A
synthetic consumer is part of that protected realization and has exactly one
observable domain effect: accepting one exact synthetic use. Its authoritative
acceptance state is the owner-local durable transition itself. It has no separate
callback, mutable consumer counter, network effect, queued work or independent
owner state that must also commit. This consumer definition needs explicit
maintainer acceptance as part of this profile, now recorded in §10; it is not a
completed proof.

The private realization validates the supplied in-memory synthetic value, exact
revision, purpose and current controls within the shared domain. Validation is
not acceptance: it cannot publish results or mutate consumer acceptance state.
The one conditional source transaction then commits together:

- synthetic consumer acceptance state for the exact use;
- immutable safe accepted-use fact, retained outcome and uniqueness guard;
- the outstanding post-use attribution/submission obligation.

**That commit is actual synthetic acceptance.** There is no subsequent consumer
call which could fail independently after a row falsely says accepted. Material
is never bound into SQL, a serializer, a storage exception or a durable record.
The persisted result is structural acceptance status, never a material-derived
fingerprint. A duplicate exact identity returns retained status under current
disclosure authority; it cannot revalidate material as a second use. Conflicting
meaning under an existing identity refuses without altering history.

Evidence owns the separately committed audit representation, receipt and any
Evidence-internal custody faults. It never decides source acceptance. Execution
retains invocation/effect state; Governance retains Grant/Policy/Approval state;
Catalog retains eligibility; Configuration retains revisions. No consumer state
from an arbitrary Adapter is moved into Secret Access or Evidence.

### Dual-write analysis

Writing “accepted” before an independent consumer accepts can record a false
fact. Writing afterward permits an unrecorded accepted use on crash. A mutex,
durable intent, `try/finally`, or two writes in one function does not solve that
problem. Intent alone preserves investigation, not proof that acceptance occurred.

The selected profile removes the second authoritative state mutation only because
the synthetic consumer's effect is this very owner-local transaction. It does
not assert atomicity between SQLite and Python memory or between two owners.
If the implementation needs any independently effectful consumer callback, or
must call delivery of bytes to that callback “acceptance,” this solution does
not apply: STOP for a broader execution/consumer decision, not a write-before or
write-after workaround. No generic transaction participant protocol or 2PC.

## 4. Minimum safe durable records

These are semantic fields, not an approved SQL schema. Reuse existing nominal
identities where they express the meaning. References must resolve within declared
retention coverage; an unresolved mandatory reference blocks the claim. Do not
invent a second identifier for an existing decision that has no nominal ID.

| Record/field group | Minimum meaning and normative reason |
| --- | --- |
| Prepared identity | Exact use identity, operation/effect/attempt linkage where applicable, owner scope and expected revision; ADR-008 equivalence and ADR-010 exact use. A use identity is never a credential. |
| Protected subject | Exact Secret reference/revision, resolver mapping revision, declared purpose, admitted consumer identity/version and target mapping; ADR-010 §§7–8, 11, 14 binds historical meaning without retaining material. |
| Attribution scope | Requester and acting Principal references, verified tenant, configuration/activation references where applicable; SEC-060/076 and ADR-010 §14. No free-text metadata bag. |
| Authority basis | Exact historical authorization/Policy/Grant references or safe bounded decision evidence; applicable Approval identity/consumption observation; currentness basis and applicability. SEC-076; never authority for a future use. |
| Interpretation and timing | Record/profile version, source revision, preparation/acceptance/recording times and declared clock uncertainty/order; ADR-004 recovery interpretation and SEC-073. No realtime guarantee inferred from timestamps. |
| Prepared source duty | Duty/submission identity, responsible owner/Principal, exact target evidence/subject, required guarantee/class, due and retention bounds, repair authority and next safe action; ADR-009 §§8–9, CONTRACTS §28. |
| Accepted transaction | Synthetic acceptance state, immutable accepted-use fact, retained structural result, exact-use uniqueness and outstanding duty in one commit; ADR-004 §10 and ADR-009 §8.2. No separate mutable “accepted” cache is authoritative. |
| Duty progress | Pending/satisfied/requires-intervention or entitled disposition, expected duty revision, last safe error/evidence reference, linked completion evidence; ADR-009 §9. Keep history, do not overwrite acceptance. |
| Evidence-owned record/receipt | Exact source subject/revision, issuer, tenant, submission identity, evidence class and interpretation, committed durability/retention/access/integrity/coverage guarantee and limitations, custody identity/time; ADR-009 §7 and SEC-073/074. |

Store each fact once with references where sufficient. Purpose and subject belong
to the prepared immutable meaning; acceptance pins that meaning. An acceptance
timestamp cannot substitute for the final authority/currentness basis. Policy
non-applicability is explicit; unrelated resource fields or provider responses
are not added. If resource/claim observations are actually required, retain their
safe owner-issued references and partial status, not invented default success.

Never persist Secret bytes/string, bearer token, auth header, environment value,
live handle, resolver callback, authenticated client/session, raw material hash,
or credential-bearing provider response. Safe metadata is still restricted:
current authorized scope checks apply to reads, enumeration and repair. No
credentials, environment source or provider response exists in this profile.

## 5. Pre-use, acceptance and post-use sequence

1. Durably prepare exact source intent and submission responsibility. This says
   “intended,” not “accepted.” Refuse if storage/identity/interpretation is unknown.
2. Complete any mandatory pre-use Evidence custody outside the shared domain.
   Require an exact committed-recoverable receipt matching subject, submission,
   tenant, class, retention/integrity/coverage, validity and deadline. Queued or
   in-memory acknowledgment is insufficient. Lost receipt requires status
   inspection; it does not permit acceptance. Establish bounded root authority
   per ADR-010 §13/CTR-061 without recursive logging-as-custody.
3. Complete/release Coordinator claim where applicable. It does not accept use.
4. Enter the single shared domain, revalidate current authority, policy, Catalog,
   Secret mapping/revision/use, pre-use receipt applicability, cancellation and
   expiry; validate synthetic material without external effects.
5. Consume applicable Approval through its participating owner, preserving partial
   consumption semantics. Commit the §3 source atomic set as actual acceptance.
   A failed/uncertain commit never triggers another use attempt.
6. Release the domain. Submit the accepted source fact to Evidence, obtain its
   durable receipt, then conditionally mark the source duty satisfied. These two
   owners commit separately; source duty survives either write failing.

The accepted scope **permits one bounded synchronous local source-store commit
inside the shared domain**, narrowing the previous assessment's “without I/O”
candidate. No network, subprocess, task/worker submission or arbitrary callback
is permitted there. Acquire domain before the private source transaction; never
hold a source transaction while acquiring the domain. Pre-use preparation and
post-use repair release their store transaction before any domain entry.
Coordinator claim/settlement locks never nest with either. Evidence transactions
occur outside the domain and never call back into protected acceptance.

Local storage can stall; fixed work and a no-busy-retry policy are not a hard
wall-clock bound. The implementation must qualify this lock/commit/expiry profile
and refuse deadlines requiring an unsupported guarantee. Moving the commit after
unlocking or pretending disk latency is zero is not acceptable. If the approved
meaning of bounded synchronous acceptance excludes this local commit, stop for
maintainer review rather than silently widening it.

### Approval partial completion

Approval is not folded into the Secret or Evidence transaction. ADR-010 §11 and
CONTRACTS §28 explicitly preserve consumed claims if later use fails. The prepared
duty exists before consumption. If a crash separates consumption from a retained
receipt, recovery reports possible consumption/intervention, not a refund or
“unused.” The successful source commit retains the actual consumption observation.
No second consume occurs on attribution repair.

This profile does not restore the in-memory Approval registry after restart or
enable fresh protected uses with its reset counts. Recovery is inspection/repair
only; missing current Grant/Policy/Approval/Catalog/Secret state blocks use. A
requirement to resume the same bounded approval across restart needs its owner's
durable consumption profile, separately approved. Within the live qualified
domain, competing final-use contenders must still yield at most one acceptance.

## 6. Evidence Port consequence

A. Existing `EvidenceCustodyPort` can own audit custody, but cannot own the entire
intent/acceptance/repair lifecycle without becoming a source transaction service.

B. Additive typed source-subject/event representation is needed: exact safe
prepared-use and accepted-use revision references with attributable source facts.
Do not encode a use as a fake `ConfigurationRevisionRef`, stuff it into
`content_reference`, or use an unvalidated `Any` payload. Keep Secret semantics
in Governance and dependency direction consistent with existing Evidence imports.

C. Returning `EvidenceRecord` alone does not express the required durable
guarantee, retained submission outcome and receipt coverage. A deployment promise
must not silently upgrade existing in-memory acknowledgments.

D. A persistent adapter alone is insufficient: it supplies neither source atomicity
nor the new subject and acknowledgment contract.

E. Propose a narrow additive acknowledged custody operation and exact submission
status query, with immutable receipt values. Each custody commit atomically stores
record, custody metadata and retained submission outcome; exact equivalent
submissions recover the same result and conflicts refuse. Preserve existing
`record`/`read` behavior for current callers. Final Python names are implementation
details; no transaction object or SQL connection becomes public.

F. Durable receipts and source-revision references are reusable Evidence semantics
under CONTRACTS §25/ADR-009. Secret acceptance state and source duty transitions
are not. Evidence owns only its own storage/intervention duties. Secret Access
retains submission responsibility until matching custody or entitled disposition.

## 7. Storage, recovery and repair

After semantics, permit local SQLite as the smallest existing technical
choice: separate private Secret source adapter/schema and separate Evidence
custody adapter/schema, separately authoritative commits. Do not reuse or extend
`SQLiteConfigurationStore` tables, its owner or its recovery authority. Reuse
understood durability/inspection techniques only after qualifying them anew.
No PostgreSQL, Redis, broker, distributed log or generic persistence framework.

Use one admitted writer incarnation; exclusive recovery admission prevents stale
writers. The supported storage profile, atomic uniqueness/conditional revision,
bounded record/query sizes, explicit schema interpretation, integrity checks,
retention/access controls and no silent memory fallback require qualification.
ADR-004 intact-storage crash/restart scope applies; process kill tests alone do
not establish power-loss durability, disk-loss survival or rollback resistance.
Unknown/corrupt/incompatible storage blocks dependent use and exposes a safe gap.

Trusted recovery performs authorized read-only inspection of both owners and
enumerates unresolved duties. It never resolves material or opens a use handle.
It distinguishes:

- Prepared only: no acceptance in the recovered complete source transaction
  history; possible prior Approval consumption remains independently reportable.
- Accepted with outstanding attribution: source acceptance and duty exist,
  Evidence absent/unknown or receipt not yet linked; repair required.
- Accepted and attributed: matching custody receipt retained and source duty
  satisfied. Lost source completion acknowledgment is resolved by exact lookup.
- Reconciled/intervention: linked disposition or repair result remains visible.
  Closing an investigation does not manufacture missing required custody.

These are inspection categories, not new canonical Execution states. Missing or
unavailable history is UNKNOWN, not prepared-only or proof of no use. All categories
prohibit replay of the original use. New work requires separate current admission;
this recovery utility does not implement it. No authority, Approval count, material
or handle is restored from historical success.

Repair means authorized submission/status reconciliation of the same evidence
meaning and identity, then a conditional source-duty update referencing the exact
receipt. It never repeats protected use, consumes another Approval, compensates,
or retries a provider. No automatic repair scheduler/retry is selected. An operator
may request an explicitly governed evidence repair; current read/write authority,
tenant scope and deadlines apply. Permanent gaps stay visible with intervention.

## 8. Deterministic future qualification matrix

Notation: P = prepared source duty plus required pre-use receipt where completed;
A = atomic acceptance/fact/outstanding duty; E = matching durable Evidence receipt;
S = source duty satisfied. No row permits repeating this use, including P-only
after restart. “None” below requires intact recovered source history. Unavailable
history always yields UNKNOWN and admission blocked. Approval liability is a
separate observation, not inferred from the use column.

| Explicit failpoint/process termination | Recovered records | Use occurred? | Repair and recovery report |
| --- | --- | --- | --- |
| 1. Before pre-use custody | None or prepared source responsibility; no required receipt | No | Unfinished preparation; obtain custody/disposition only, no use. |
| 2. After pre-use custody, before domain entry | P | No | Prepared, never accepted; retain/dispose duty under authority. |
| 3. During final validation | P | No | Validation incomplete/denied; no accepted fact, inspect any prior claims. |
| 4. After Approval consumption, before acceptance commit | P; consumption receipt may be absent | No | Possible/known consumed Approval, intervention; no refund or reconsume. |
| 5. Immediately before/during/after source commit | P or A, never a partial A set | No for P; yes for A | Lost acknowledgment resolved from source; A requires attribution. Unreadable store => UNKNOWN. |
| 6. Around synthetic acceptance | Same failpoints as row 5 | Exactly the commit outcome | There is no separate consumer callback gap. A separate acceptance point fails qualification. |
| 7. After acceptance, before post-use Evidence | A | Yes | Outstanding attribution survives, repair evidence only. |
| 8. Evidence write fails or receipt is lost | A; E may exist | Yes | Query exact submission; recover E or explicitly repair; never repeat use. |
| 9. After attribution obligation creation | A, because obligation and acceptance are atomic | Yes | Obligation cannot be absent for accepted use; enumerate it after restart. |
| 10. During repair completion | A+E, with or without S | Yes | Conditional closure/query only; duplicate repair must not duplicate evidence or use. |
| 11. Restart with outstanding obligation | A, E optional, no S | Yes | Read-only discovery, current authorized attribution repair/intervention. |
| 12. Restart after completed attribution | A+E+S | Yes | Historical attributed use, no pending duty, no replay. |

Also test duplicate/conflicting identities, wrong tenant/disclosure, missing or
incompatible receipts, source/Evidence corruption and unsupported schema, rollback
coverage gaps, exhausted Approval contenders, all invalidator ordering, canary
absence in DB files/journals/backups/output/exceptions, and legacy credential-free
regressions. Use explicit failpoints and child-process handshakes/termination,
not sleep races. Do not dump material when a canary assertion fails.

Future implementation must supply a Python validator with the documented root
command `uv run python .\validate_secret_use_durable_custody_1.py`; it does not
exist in this documentation-only slice. Qualification must report exercised crash
boundaries and storage failure assumptions, separately from later Stage-A ordering
proof. No tests, runtime qualification or generic exactly-once claim is made here.

## 9. Accepted implementation scope and gates

Next implementation slice under the explicit acceptance recorded in §10:
`SECRET-USE-DURABLE-CUSTODY-1` — source-owned synthetic acceptance and separate
durable Evidence custody profile.

- Ownership/packages: reusable safe Secret contracts in `legoai.governance`;
  custody subjects/receipts in `legoai.evidence`; private source/custody storage
  and trusted inspection in reference realizations. No dependency on SQL in domain
  contracts and no expansion of Application Configuration ownership.
- Public surface: additive validated safe attribution/reference and custody receipt
  values, acknowledged custody/status operations justified in §6. Secret Access's
  accepted four operations retain their meaning. Source store, exact acceptance,
  SQL and ordering-domain machinery remain private. Inspection exposes safe typed
  results through trusted composition, not public raw transaction APIs.
- Private source operations: prepare responsibility, conditionally commit the §3
  atomic acceptance set, inspect exact status/outstanding duties, and conditionally
  link a matching custody receipt or entitled disposition. No arbitrary callback
  inside commit and no generic workflow queue.
- Approval and restart: preserve partial claims under §5; inspection/repair only
  after restart. Do not enable durable resume or reset-count admission. If wider
  Governance persistence is necessary to meet this profile, stop for a separate
  scope decision rather than storing Governance state in the Secret ledger.
- Failure: unacknowledged pre-use custody prevents acceptance; uncertain source
  commit requires inspection; accepted use never rolls back due to failed audit;
  missing/corrupt recovery coverage blocks claims and subsequent use.
- Qualification: §8 plus receipt integrity, source uniqueness, private consumer
  ownership, storage/lock ordering and safe recovery. No application-facing
  framework, DB migration of unrelated owners or live provider testing.

**ADR consequences:** ADR-004 already selects owner-local durable commits and
permits owner-specific private adapters; it does not authorize new implementation
scope by itself. No addendum/new ADR is needed for the selected single-owner
synthetic mutation. ADR-009 supplies source duty plus separate custody, including
acknowledgment and repair rules not yet represented in current Python contracts.
ADR-010 supplies safe exact-use attribution and prohibits material persistence.
No semantics/status changes to these ADRs. Independent consumer transactions or
broader Execution ownership would invalidate this profile and require a separate
maintainer architecture decision before work continues.

**Roadmap:** split G02/G03 responsibility (classification C): G02 gains reusable
durable custody receipts/adapter; G03 gains Secret-owned source-use semantics and
ledger. G06 contributes inspection/no-repeat rules, not an execution-resume engine.
None of these gates closes from this scope acceptance.

**Cancellation:** waiting-domain cancellation remains a separate Stage-A item.
Durability adds an uncertain-commit case: cancellation cannot assert no use after
commit starts; inspect source outcome. Post-commit cancellation preserves A and
its duty. No generic cancellation mechanism is selected here.

**Stage A:** remains stopped; accepting this scope does not itself qualify or
resume it. Qualify the durable prerequisite first, then explicitly resume the
accepted Stage-A scope with the local-commit allowance and remaining ordering,
expiry and cancellation proofs. The strongest potential claim is at-most-one
accepted synthetic use per exact identity within this qualified local protocol
and retained coverage; not exactly-once execution generally.

Stage B remains gated. No environment source, credential header, remote provider,
remote disclosure, KISSKI, or VTO remote image flow is authorized. Independent HTTP
handoff cannot reuse the synthetic atomicity claim and needs its own proof.

## 10. Maintainer acceptance and verification — 2026-10-07

The maintainer explicitly accepts the bounded scope in this document:

- Secret Access owns the source-side durable exact-use ledger; Evidence remains
  a separate custody owner with separate commits and durable receipts.
- Stage-A synthetic acceptance is the owner-local durable source transition
  itself, with no independently effectful consumer callback. The atomic source
  transaction commits accepted-use fact, uniqueness and outstanding attribution
  duty together.
- Post-use Evidence failure leaves that source duty outstanding and recoverable;
  repair never repeats protected use.
- Secret material, credentials, live handles, callbacks and material-derived
  fingerprints must never be persisted.
- Local SQLite is permitted only through separate owner-specific Secret and
  Evidence adapters; SQLiteConfigurationStore is not reused.
- One bounded synchronous local source-store commit is permitted inside the
  shared ordering domain for this qualified Stage-A profile only. No network,
  subprocess, worker/task submission, arbitrary callback or remote I/O is
  permitted while the domain is held.
- Restart is inspection/repair only. It restores neither authority, Approval
  counts, Secret handles nor execution resume.
- Independent consumer effects, HTTP handoff or broader execution atomicity
  require a separate architecture decision.
- Stage A remains stopped until SECRET-USE-DURABLE-CUSTODY-1 is implemented and
  locally qualified. Stage B, credentials, remote providers and KISSKI remain gated.

No ADR status or semantics are changed by this acceptance. The technical scope
and qualification requirements above remain binding; acceptance is not evidence
of implementation or local qualification.

This task creates/links planning documents only. No database, source, tests,
validator or ADR change. Documentation verification: `git diff --check` and local
Markdown-link checks. No runtime or crash qualification is claimed.

## 11. SECRET-USE-DURABLE-CUSTODY-1 implementation — 2026-10-07

**IMPLEMENTED — LOCAL VALIDATION PENDING.** This status concerns the durable
prerequisite only. It does not resume or qualify SECRET-REF-1A. The acceptance
record above and all Stage-B/remote/KISSKI gates remain unchanged.

### Implemented boundary

- `legoai.governance.secret`: immutable safe exact-use plan, exact Secret revision,
  prepared/accepted fact, duty state, Approval observation and recovery projection.
  Existing nominal Principal, scope, configuration, operation, submission, Grant,
  Approval, Policy and version types are reused. No material field or metadata bag.
- `legoai.evidence.custody`: additive source evidence, declared
  `INTACT_LOCAL_V1` profile, durable receipt and acknowledged-custody/status Port.
  Existing EvidenceRecord and EvidenceCustodyPort.record/read are unchanged;
  in-memory custody acquires no durability promise.
- Private `reference/_secret_ledger.py`: source-owned preparation, exact-use
  uniqueness, retained synthetic acceptance, submission duty/history, conditional
  receipt linkage and intervention. The acceptance transaction commits the fact,
  pre-use custody reference and outstanding duty transition together. There is
  no independent consumer callback. The retained structural fact stays visible
  even when the duty requires intervention.
- Private `reference/_durable_evidence.py`: separately committed source evidence
  and immutable custody receipt; exact equivalent submission returns its retained
  outcome, conflicting identity refuses. The private witness is obtained by an
  Evidence-owner lookup before domain entry, not by trusting a caller-created
  receipt value. No Evidence transaction runs inside the acceptance domain.
- Private `reference/_secret_domain.py`: injected, instance-local, non-reentrant
  synchronous ordering identity. This slice tests the storage ordering boundary;
  it does not wire or qualify Grant/Policy/Catalog invalidator participation.
  No public ordering or transaction API was added.

The adapters are private trusted-composition facilities, not application Secret
services. `CustodyAccess` is an explicit scope/requester input, not authentication
or a grant. The trusted caller must establish current admission and entitled
repair authority; stored authority references never do that. Scope mismatches
refuse without exposing another subject. The synthetic storage harness supplies
the in-memory validation inputs; no production runtime host is wired to it.
Stage A must still implement current-authority/current-invalidator checks and
cancellation before this private acceptance boundary can serve protected use.

### Persistence and recovery profile

The source and Evidence files have separate owner schemas and version-1 metadata.
Shared private code is limited to closed safe-value serialization and SQLite
mechanics; it does not define a generic repository, journal or transaction Port.
SQLiteConfigurationStore, Governance registries, Execution, Catalog, runtime/local
composition, providers and ADRs were not changed.

Both files use rollback journal `DELETE`, `synchronous=EXTRA`, foreign keys,
zero busy timeout and no retry. Each owner uses a separate SQLite admission
sidecar whose held EXCLUSIVE transaction admits one writer incarnation. Process
termination releases that lock. Each physical store durably pins its admitted
owner/tenant/requester scope and refuses rebinding on writable or read-only reopen;
this scope binding is not authentication. Explicit provisioning requires new paths;
reopening uses `mode=rw`, inspection `mode=ro`. Missing/incompatible/corrupt stores
never silently initialize or fall back to memory. Integrity and typed-history
checks reject incomplete atomic sets, including a missing accepted fact. Public
record encodings are bounded to 32 KiB and each store to 4,096 source/submission
records in this profile. A capacity failure never authorizes use.

Source preparation and required pre-use Evidence custody complete before entry;
the source commit runs inside the domain. Source transactions are released before
domain exit. Post-use Evidence and conditional duty closure run afterward.
Coordinator locks and provider calls are absent. This ordering permits local disk
latency, not a hard realtime bound or proof of acceptance-time expiry; Stage-A
time qualification remains outstanding. Acceptance timestamps are the supplied
observation-clock basis, not measured storage completion timestamps.

A persisted first-incarnation marker disables new preparation/acceptance on
reopen, including fresh identities: this profile reopens for inspection and repair
only. Equivalent preparation/status can recover retained meaning but cannot admit
a prepared-only use for acceptance. No authority, Approval count or Secret handle
is restored. Read-only inspection uses a coherent SQLite read transaction and
reports prepared-only, accepted/outstanding, accepted/attributed, intervention,
or UNKNOWN/GAP. Missing history is never reported as unused. A hot journal that
cannot be recovered read-only yields a gap until the trusted owner can recover
storage; inspection does not secretly perform recovery writes.

Approval remains a separate owner. The crash driver exercises its real in-memory
consume operation before source acceptance; the source retains only applicability
and known/possible consumption observations. It neither restores nor refunds a
count. Post-use custody failure leaves accepted truth and a pending duty. Explicit
repair submits/looks up that same Evidence meaning and conditionally links its
receipt; no acceptance, second consume, automatic retry or execution resume.

### Verification and operator command

Focused tests cover 13 explicit child-process termination points, source/Evidence/
duty lost acknowledgments, duplicate/conflicting identities, pre-use refusal,
matching receipt/revision checks, writer admission, scope non-disclosure, recovery
gaps and corruption. Child failpoints are test-only injections around actual SQL
commits, not production callback hooks or sleep races. Canary checks inspect SQL
traces, source/Evidence files, active rollback journals, stdout/stderr, logs and
safe serialized results without displaying material. WAL is rejected by the
selected profile and is not claimed to be qualified.

Implementation verification passed: focused custody tests and architecture guards,
748 existing Core regression tests, 89 ForgeAI regression tests and 16 lightweight
DocuMind regression tests. Canary checks passed. Full-source mypy and focused Ruff
checks passed. These are implementation checks, not an operator qualification
result for all validator phases. Existing provider regressions use mocks/local fake
HTTP only; no live or remote provider, credential, environment Secret source or
Docker was used by this slice.

Prepared `validate_secret_use_durable_custody_1.py` with 72 numbered phases covering
the accepted matrix, safe contracts/owner separation, crash/storage/disclosure
proofs, existing regressions, mypy, Ruff and diff checks. Identical selectors are
reused only after they pass earlier in that same run; each phase reports that reuse.
The validator requires existing repository/example environments and downloads
nothing. Run from repository root:

```powershell
uv run python .\validate_secret_use_durable_custody_1.py
```

No operator qualification is recorded yet. The storage evidence is limited to
intact local-storage process crash/restart; no power-loss, disk-loss, hostile-admin,
coordinated rollback, distributed durability, remote handoff or general exactly-
once guarantee is established. Ordinary Python process privacy is not hostile-code
isolation. Full Stage-A ordering, expiry and cancellation qualification remains
separate; Stage B, credentials, remote providers and KISSKI stay gated.

Implementation workspace limitation: Windows ACLs prevented removal of the exact
task-generated `.custody-...-temp` test directories, including attempts with
elevated tool permissions. They are enumerated in the validator's
`IMPLEMENTATION_TEST_DIRECTORIES`, excluded from source scope, and never reused
as qualification evidence or implementation input. Do not commit these temporary
test artifacts. The operator validator creates a fresh temporary directory.
