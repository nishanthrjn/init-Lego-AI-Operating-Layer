# Reference Local Persistence Realization and Qualification

**Status:** ACCEPTED — IMPLEMENTATION DECISION

**Date:** 2026-09-20

**Decision owner:** Reference-runtime maintainer acting as persistence realization owner

**Review responsibilities:** Security, recovery and release reviewers retain their accepted responsibilities.

**Classification:** Lower-level implementation decision beneath ADR-004. No numbered ADR, canonical amendment or ADR-index allocation.

**Decision versus proof:** This record selects a mechanism and specifies its qualification. No persistence source, executable schema, migration, database or test is implemented by this task. Decision acceptance is not implementation qualification, Gate-2 readiness, Conformance or production approval.

**Acceptance:** Accepted after implementation-architecture review on 2026-09-20. Acceptance selects the reference local persistence mechanism and qualification obligations. It does not qualify the implementation, establish machine-durability guarantees, authorize operational protected use, or constitute Conformance, release, security, or production-readiness evidence.

## 1. Authority and decision question

Authority runs from accepted canonical documents through accepted ADRs, implementation-readiness, the Gate-1 plan and this record. Implementation details below cannot weaken a higher-level requirement.

| Governing source | Constraint carried into this decision |
| --- | --- |
| [intent](../../intent.md), [SPEC](../../SPEC.md) | Small local reference realization; explicit identity, tenancy, state and effects; optional AI remains optional. |
| [Architecture](../../architecture/ARCHITECTURE.md), especially AR-14–18 | Each owner controls its state; infrastructure does not merge owners or imply global atomicity. |
| [Contracts](../../contracts/CONTRACTS.md), CTR-013–016, CTR-056–058 | Conditional mutation, original-operation equivalence, retained status/coverage and explicit duties. |
| [Security](../../security/SECURITY.md) | Current authority at protected boundaries; scoped disclosure, safe recovery and no raw Secret retention. |
| [Conformance](../../conformance/CONFORMANCE.md), CONF-032–045, 067–068, 074 | Actual negative/concurrency/failure proof and exact applicability; no claim from architecture alone. |
| [ADR-001](../../adrs/ADR-001.md), [ADR-002](../../adrs/ADR-002.md) | Conventional CPython 3.14, owner-specific implementation behind inward contracts; Kernel has no store. |
| [ADR-003](../../adrs/ADR-003.md) | Immutable owner-issued configuration revisions, exact source interpretation and separate mutable selection head. |
| [ADR-004](../../adrs/ADR-004.md) | Qualified durable owner-local state/history/result/obligation commits, guarded revisions, restart and restore limits. |
| [ADR-005](../../adrs/ADR-005.md) | Explicit verified context and current access/mutation enforcement; possession of an ID is not authority. |
| [ADR-008](../../adrs/ADR-008.md) | Look up equivalent original outcome before evaluating the old head precondition as new work. |
| [ADR-009](../../adrs/ADR-009.md) | Source fact plus source duty is not Evidence custody; repair never repeats the producing mutation. |
| [ADR-011](../../adrs/ADR-011.md) | Exact environment/build/compatibility evidence; historical interpretation and truthful migration limits. |
| [ADR-015](../../adrs/ADR-015.md) | Owned bounded blocking workers; cancelling an awaiter does not stop SQL or release worker ownership. |
| [Readiness](../IMPLEMENTATION-READINESS.md), [Gate-1 plan](../GATE-1-FOUNDATION-IMPLEMENTATION.md) | Configuration owner first; SQLite leading candidate; isolated qualification before any operating protected service. |

**Question:** How will the first local CPython reference runtime realize owner-local durable state, history, results and obligations with conditional mutation, exact historical interpretation, lost-ack recovery and manageable local operation?

**Answer:** Select standard-library `sqlite3`, one local SQLite database, owner-specific relational tables and explicit owner-local transactions. Use DELETE rollback journaling, EXTRA synchronization, scoped relational constraints and versioned JSON records. Start with one synchronous connection per operation and fail-fast contention. Qualify the actual implementation and storage stack before admitting its durability guarantees.

The Gate-1 plan's recommendation survives comparison. No blocking upstream contradiction has been identified. Historical prospective instructions inside accepted ADRs do not reopen their current decisions. ADR-015 is Accepted and governs later integration.

## 2. Scope and non-goals

This decision fixes the first engine/settings, connection and transaction discipline, configuration-owner schema, revision/equivalence rules, retained results, obligations, codecs, migrations, startup/recovery and proof requirements.

The first supported implementation target is one trusted local process with one explicit operational tenant, on one specifically qualified local environment. Adversarial synthetic two-tenant tests remain mandatory. Physical database access assumes trusted host code and protected files; schema names do not isolate malicious in-process code.

Excluded: distributed persistence, external database deployment, cloud/multi-region replication, event sourcing, global transaction management, generic repositories, ORM, Workflow engine, HA, backup service, automatic pruning, online migration and multi-process runtime takeover. No Agent, Tool, Team, Workflow, Memory, Events, Resources or Approval tables are pre-created.

Gate-1 storage experiments use synthetic data in test-only stores. They prove storage mechanics, not a publicly accessible or fully governed configuration service. Current authorization, finite roots, resources and mandatory pre-effect custody must be implemented before operational use. There is no `skip_authorization` flag or test identity promoted to production trust.

## 3. Alternatives and selection

The comparisons are requirement-based judgments, not measured performance scores.

| Criterion | A — stdlib SQLite | B — SQLite async facade | C — embedded transactional KV | D — JSON/files | E — external relational DB |
| --- | --- | --- | --- | --- | --- |
| Atomic owner set and guards | Explicit SQL transaction, guarded head, constraints | Same engine guarantees; wrapper does not improve them | Viable if one engine transaction covers complete invariant | Requires custom multi-file journal/locking or replacement of a whole aggregate | Viable server transaction, still needs owner semantics |
| History/result/obligation lookup | Scoped keys and bounded indexed reads | Same schema/query work | Extra key/index organization and consistency work | Custom indexing and recovery | Mature query support, unused scale initially |
| Durability qualification | Local SQLite/VFS/filesystem/drive | Same stack plus worker/queue behavior | Engine/native binding and host stack | Must build and qualify commit protocol | Server, client/network and server storage |
| Migration/corruption | Explicit transactional migration and integrity checks | Same, plus cancellation ownership | Engine-specific migration/readers | Format and journal repair authored locally | More operating procedures and upgrades |
| Concurrency | Single writer; short reads/writes; fail-fast contention | Async syntax does not remove writer serialization | Depends on engine; no measured advantage yet | Must invent robust exclusion | More concurrency, no demonstrated need |
| Setup/dependencies | No server or extra Python runtime package | Added dependency and hidden execution behavior to inspect | Typically native dependency/packaging | Few initial dependencies, substantial correctness code | Service, credentials, provisioning and monitoring |
| Crash testing | Real file and subprocess barriers | Same plus cancelled-await tests | Engine-specific fault boundaries | Custom journal fault matrix | Server/client interruption matrix |
| Solo cost / replacement | Moderate storage discipline; data migration still substantial | More moving parts without current benefit | More unfamiliar maintenance for no current benefit | Apparent simplicity transfers cost into bespoke reliability | Highest initial operating burden |

**Select A.** B is not selected merely because the runtime later uses asyncio; integrate A using ADR-015's bounded bridge. C has no concrete first-owner advantage. D is rejected as authoritative state, but JSON remains a payload format. E is premature for the local scope. Reconsider only when measured contention, a required deployment/failure scope or an actual data access need defeats the selected mechanism.

No ORM: the first owner needs a small reviewed set of guarded multi-row commands, not object tracking or a generic query surface. No generic `Repository[T]`, `save(entity)` or `find_by_id()` API: the boundary must expose scoped publication, exact reads, operation status and duty inspection. Immutable history is not event sourcing; current state is stored directly.

## 4. SQLite settings and platform envelope

### 4.1 Selected settings

| Setting | Decision | Verification / meaning |
| --- | --- | --- |
| Engine | CPython 3.14 standard-library `sqlite3` linked to a qualified SQLite build | Record actual interpreter/distributor/build and SQLite version; no server. |
| Python transaction control | Explicit `autocommit=True` | Use SQL transaction statements; no legacy implicit transaction policy. |
| Journal | `PRAGMA journal_mode=DELETE` | Set during explicit initialization; inspect and require DELETE on ordinary opens. Never silently convert a foreign WAL store on recovery. |
| Synchronization | `PRAGMA synchronous=EXTRA` | Set and verify numeric value 3 on every connection before transaction use. |
| Foreign keys | `PRAGMA foreign_keys=ON` | Set outside transactions and verify 1 on every connection. |
| Busy handling | `timeout=0.0`; verify `PRAGMA busy_timeout=0` | No hidden waiting or internal busy retry. Contention returns a classified bounded failure; this does not bound OS I/O latency. |
| Connection sharing | `check_same_thread=True`, private cache | Connection stays on its creating thread; no shared-cache mode or global pool. |
| Extensions | Never enable/load extensions | Explicitly disable when supported; if extension APIs are absent, preserve that restricted build. |
| SQL surface | Fixed SQL/identifiers, parameterized values; no `ATTACH` | No user-defined functions/collations or candidate callbacks. |
| Schema types | STRICT tables, explicit NOT NULL/CHECK/UNIQUE/FK rules | Require a build supporting the selected features; capability check and actual constraints tested. |
| Application codecs | `detect_types=0`, explicit decoding | No registered object converters, executable deserialization or process-global adapters. |

CPython's `autocommit=True` selects SQLite autocommit mode; `Connection.commit()` and `rollback()` do not supply the desired explicit transaction behavior in that mode. The adapter therefore uses SQL `BEGIN IMMEDIATE`, `COMMIT` and `ROLLBACK`, and checks transaction state on failures. Connections are explicitly closed. [CPython transaction control](https://docs.python.org/3.14/library/sqlite3.html#transaction-control).

STRICT tables provide a useful SQL type constraint but may still perform lossless coercions. The application must validate exact Python/JSON types first, especially bool versus int; SQL is a second invariant boundary. [SQLite STRICT tables](https://sqlite.org/stricttables.html).

### 4.2 DELETE versus WAL

DELETE uses the database and its transient rollback journal. WAL supports overlapping readers/writer but adds persistent WAL/shared-memory state, checkpoint behavior and backup/copy considerations. Long readers can obstruct checkpoint progress; choosing WAL would not eliminate single-writer serialization. The first small synchronous owner does not need those extra operating concerns. [SQLite WAL behavior](https://sqlite.org/wal.html).

Select DELETE initially. Keep read snapshots short: a reader can delay a rollback-journal writer's commit. Never delete a journal as cleanup; it may be needed for recovery. Shutdown closes owned transactions/connections after work settles. Reconsider WAL through an implementation decision update only after measured contention justifies it, with requalification of crash, checkpoint, backup and shutdown behavior.

### 4.3 EXTRA and its limits

EXTRA adds synchronization of the directory after rollback-journal deletion compared with FULL in DELETE mode. Select it to address commit-adjacent power loss conservatively. It is not encryption, replication, an independent freshness witness or proof that this host honors flush requests. [SQLite synchronous settings](https://sqlite.org/pragma.html#pragma_synchronous).

SQLite's atomic commit relies on filesystem, locking and storage assumptions. Qualification must establish the chosen OS/VFS/filesystem/device behavior; process termination cannot stand in for loss of volatile OS/device caches. Network shares, cloud-synchronized folders, removable media and alternate VFS implementations are unsupported unless separately qualified. [SQLite atomic commit](https://sqlite.org/atomiccommit.html).

No production throughput, latency or database-size target is invented. Initial fixtures use at most 64 KiB UTF-8 per JSON record, depth 16, 128 rows per obligation page and a 64 MiB test-volume budget. These are test limits, not universal contract limits or runtime resource grants. Larger workload requirements require explicit revised bounds and proof before admission.

## 5. Connection ownership and transaction discipline

**Select one fresh synchronous connection per owner operation**, including a read/status page. Open, verify identity/settings, begin the needed transaction, perform bounded work, materialize the bounded response, close cursors, end the transaction and explicitly close the connection on the same thread. No lazy cursor escapes the operation. One runtime may have overlapping operations later, but outstanding connections are bounded by admitted operation/worker capacity, not an unbounded pool.

Mutation uses `BEGIN IMMEDIATE`: acquire the writer position before reading the head and deciding a mutation. This avoids starting a read transaction and then discovering an upgrade race. SQLite still provides the actual database guard; no Python check-then-write or GIL assumption replaces it. An already retained result may first be read through a coherent status query; if not found, the write transaction repeats the operation lookup before any new mutation.

SQLite permits only one concurrent writer. `BEGIN IMMEDIATE` can return BUSY; a rollback-journal COMMIT can also return BUSY while leaving the transaction active. [SQLite transaction behavior](https://sqlite.org/lang_transaction.html).

The selected adapter does **not** retry COMMIT internally. On a positively identified BUSY with the transaction still active, explicitly roll back and close. If rollback is confirmed, report this attempt did not commit. If completion/rollback cannot be established, preserve unknown and reconcile. A later retry is a new bounded submission of the **same operation meaning**, under current controls, not a hidden loop.

| Cause | Response |
| --- | --- |
| Scoped head differs from original expected head; conflicting operation reuse | `Conflict`; safe authorized details only. |
| BUSY/LOCKED without established semantic conflict | `DependencyFailure` with safe contention category. Never call it stale-write Conflict merely because a lock was unavailable. |
| Malformed input | `ValidationError` before mutation. |
| Unsupported record/contract reader | `VersionMismatch`, no reinterpretation. |
| Missing/corrupt/unusable store or storage I/O error | `DependencyFailure`, with commit knowledge separately reported. |
| Established wrong tenant / denied access | `TenantViolation` / `AuthorizationDenied` according to the owning boundary; no foreign existence details. |
| Actual inherited deadline exhausted | `DeadlineExceeded` when established; does not prove worker/commit stopped. |

The error category, recoverability, acknowledgment stage and local effect extent remain separate. A database exception does not prove rollback. `partial` is not a valid torn single-transaction outcome; a valid atomic set is old or new. Unknown describes unavailable knowledge, not a third permissible half-commit.

Reads spanning head/revision/result use an explicit short read transaction for one coherent snapshot. A fresh current-read operation started after a completed commit must observe that commit or later, or return unavailable. A previously open snapshot is historical and must not be labeled current for a new request. End each page/read before returning.

Do not use `executescript`, `INSERT OR REPLACE`, `INSERT OR IGNORE`, implicit connection-context commits, nested transaction frameworks or arbitrary callbacks in owner commands. Replacements can hide identity conflicts or delete rows. Validation/encoding happens before taking the write lock where possible; guards and semantic-equivalence comparison are repeated under the transaction. No network, Plugin, authorization callback or diagnostic sink invocation runs while holding it.

## 6. Storage identity, creation and ordinary open

Store identity is an opaque randomly issued UUID4 text value created by the trusted bootstrap procedure; it is not a path, rowid, owner revision, tenant or security token. The database stores it; an independently supplied expected-store designation binds that ID to the allowed local path and runtime context. Two checks agreeing do not prove freshness if both can be rolled back.

The initial protected parent directory is explicitly provisioned. Resolve the intended absolute path, reject unapproved path redirection/reparse/symlink locations and ensure the file and journal cannot be replaced by untrusted users under the admitted host assumptions. Path validation alone is not race-proof against a malicious administrator; that threat is outside this realization.

| Open intent | Behavior |
| --- | --- |
| Explicit create-new | Require separately authorized bootstrap/test setup, absent destination and a new store identity. Exclusively reserve the file in the protected directory, initialize schema/metadata transactionally, then verify it before publishing the designation as ready. Never overwrite or “repair” an existing file. |
| Interrupted create | A reserved empty/partial artifact is not a ready owner. A repeated create reports existing/unready state; entitled setup recovery inspects or abandons that unused identity explicitly. Never reuse an old operational identity. |
| Open-existing | Use safely constructed SQLite URI `mode=rw` to prevent create-if-missing; compare expected ID, purpose, format/readers and allowed path. Do not accept a caller-supplied arbitrary SQLite URI or `immutable=1`. |
| Migration required | Ordinary mutation blocked; explicit supported maintenance procedure only. |
| Unsupported version | Unavailable/VersionMismatch; preserve original bytes. |
| Missing expected store | DependencyFailure/unavailable; no empty replacement. |
| Corrupt or mismatched identity | Unavailable, no deletion/recreation; safe diagnosis under current access. |
| Known copy/restore | Controlled recovery, not normal live open; see §13. |

Test stores carry `purpose=qualification` metadata; later operational bootstrap requires `purpose=operational` and its real gates. Neither the file nor a modified metadata flag is an authorization token. An operational root refuses qualification stores, and test setup refuses paths outside its dedicated temporary root. No operational bootstrap implementation is authorized here.

## 7. First owner and concrete schema contract

### 7.1 Scope and identities

First owner: **Application Composition configuration-revision owner**. The subject is `(tenant, application, configuration instance)`.

For table notation, **S** expands to four explicit TEXT columns: `tenant_id`, `owner_id`, `application_id`, `configuration_instance_id`. `owner_id` is the expected configuration-owner identity, not a caller-selected table selector. All are NOT NULL, validated opaque IDs with binary comparison. Every owner query supplies S, or supplies exact tenant/owner plus an authorized bounded subject enumeration. No default tenant and no opaque-ID-only lookup.

**H** is a positive signed-64-bit integer head successor scoped to S. First publication creates H=1; updates produce H+1. Check overflow before mutation and fail explicitly; do not wrap or reuse a revision. H is not a wall clock/global sequence. The first format supports no deletion/recreation of S; later recreation requires a new configuration-instance identity.

**R** is an owner-issued opaque UUID4 revision identity, scoped by S. Allocate it for a new publication and guard collisions in the database. A collision fails Conflict rather than overwriting. Distinct publications with identical values can have distinct R because provenance/intent differs. No content hash identity or cross-tenant deduplication.

**O** is the caller's declared operation identity within owner/contract/subject scope. It is independent of rowid, H, R and SQLite transaction identity. Its versioned descriptor retains original requester, exact typed input/provenance and governing revisions, contract/operation name, equivalence rule and original expected H/absence. Fresh current disclosure/authorization evidence does not rewrite original intent.

### 7.2 Tables

This is a design specification, not executable DDL. All owner tables are named `application_config_*`; metadata is a physical-store responsibility, not a generic domain schema. All durable tables are STRICT with explicit NOT NULL keys. Foreign keys use full composite scope, `NO ACTION`, no cascading deletes, and deferred checking only for the intra-transaction cycles below. Foreign-key enforcement must be enabled per connection. [SQLite foreign-key enforcement](https://sqlite.org/foreignkeys.html).

| Table | Purpose / columns | Keys, relationships and indexes | Mutability / retention |
| --- | --- | --- | --- |
| `store_metadata` | Singleton: `singleton=1`, `store_id`, `store_format_version=1`, `creation_interpretation_version`, `purpose` | PK singleton with CHECK=1; unique store_id; constrained purpose | Identity/creation meaning immutable; format only via reviewed maintenance. No deployment inventory copied here. |
| `application_config_schema` | Owner realization identity, `schema_version=1`, `reader_contract_version=1`, `created_by_realization_version` | PK owner_id; scoped schema identity is checked by every adapter open | Versions change only with owner migration; creation version remains historical. |
| `application_config_head` | S, `head_revision`, `configuration_revision_id` | PK S; composite FK `(S,H,R)` to revision's unique `(S,published_head_revision,R)` | Conditional head update only. No automatic deletion. |
| `application_config_revision` | S, R, `published_head_revision`, `previous_revision_id` nullable for first; `publication_operation_id`; `required_obligation_id` nullable; `record_json` | PK `(S,R)`; unique `(S,published_head_revision)`, `(S,O)`, `(S,H,R)`; deferred FK previous `(S,R)`, publication `(S,O)` to result, required `(S,obligation_id)` to obligation | Immutable history/payload and provenance. No runtime UPDATE/DELETE. Exact retained reader required. |
| `application_config_result` | S, O; `expected_kind` (absence/revision), nullable `expected_head_revision`; resulting H/R; `descriptor_json`; `result_json` | PK `(S,O)`; unique `(S,R)` for the single-publication operation; deferred FK `(S,H,R)` to revision. CHECK expected kind/null consistency and positive revisions | Immutable successful owner-commit result. No result row claiming merely queued work. Retain through coverage and dependent duties. |
| `application_config_obligation` | S, `obligation_id`, source R/O, `obligation_revision=1`, `status`, `created_head_revision`, `duty_json` | PK `(S,obligation_id)`; unique `(S,source R)` for this first profile's zero-or-one bounded source custody duty; FKs to scoped R/O; status discovery index below | Initial implementation inserts pending duty and reads it. No fake closure. Future disposition is a separately guarded operation with retained history/results. |
| `application_config_migration` | owner_id, `migration_id`, source/target schema and reader versions, migration fingerprint, `result_stage=committed`, safe resulting metadata | PK `(owner_id,migration_id)`; unique `(owner_id,target_schema_version)` for initial linear path | Append committed markers; no durable “success” written before migration commit. |

No separate full history table is needed: `application_config_revision` is immutable history. No generic event stream is needed. Extra indexes exist only for specified access paths; the first store does not pre-create other owners' records.

Every JSON envelope repeats its kind/version and relevant S/O/R/H so decoders can reject SQL-column/payload substitution. Relational columns are authoritative query/constraint keys; inconsistency with payload is corruption, not a choice of which copy to trust.

### 7.3 Invariant enforcement

SQL enforces explicit scope uniqueness, positive integer bounds, expected-kind consistency, allowed status vocabulary, referential completeness and head-to-exact-revision association. Deferred revision↔result and revision↔required-obligation references permit inserting the compound set in one transaction while rejecting dangling mandatory members at COMMIT. Inserts include a final bounded owner consistency check before COMMIT: one result matching the revision/operation, correct predecessor/head transition and exact required duty/reference set. Test all deferred constraints at actual COMMIT, not only at INSERT.

The owner derives required custody applicability from the explicit operation requirement; it cannot set `required_obligation_id=NULL` to ignore a mandatory duty. The first supported qualification profile permits zero or one source-submission duty containing a bounded requirement set for the exact source fact. An operation needing a different duty structure is unsupported until the schema/contract is extended and tested; it is never silently collapsed or omitted.

Use small immutability triggers on revision/result rows to reject ordinary UPDATE/DELETE. They enforce physical history preservation only, not authorization, policy, lifecycle or the entire canonical semantics. Schema migrations may change representation only through the reviewed process, reinstating and checking protections. A host with arbitrary schema-write privileges can bypass triggers; no malicious-host protection is claimed.

## 8. Mutation, duplicates and compound commit

The storage Port is owner-specific and internal. The operating Application owner must enforce current ADR-005 disclosure before result lookup and current mutation controls for new intent. Old permission or caller-created context cannot authorize a command. Gate-1 direct adapter tests supply synthetic data, not an operating trust bypass.

### 8.1 Ordered algorithm

1. Validate bounded descriptor, supported interpretation, explicit S/O and original requester/inputs/preconditions. Capture immutable candidate values before opening a write transaction.
2. Establish current permitted access without leaking another tenant's existence. Optionally answer a retained result in a short coherent read transaction; missing result is not enough to declare a new operation.
3. For the mutation path, open a verified connection and issue `BEGIN IMMEDIATE`. Repeat lookup of O under exact S.
4. If O exists, decode/compare semantic descriptors under the recorded equivalence rule. Equivalent returns the original retained owner outcome under current disclosure. Different meaning returns Conflict. Unsupported interpretation returns VersionMismatch. End the transaction with no mutation. Do this **before** evaluating original expected H against today's head.
5. If O is absent, establish admissible freshness/complete retained coverage for the test scope, current new-mutation authority and original expected H/absence. Missing evidence outside coverage is not permission to repeat.
6. For creation, require S absent and use plain guarded insertion. For update, require the exact head and issue conditional UPDATE with S and original H, requiring one affected row. No load-latest-and-retry.
7. Allocate new R and required duty identity; validate all owner invariants. Insert immutable revision/provenance, insert/update head, insert retained result and applicable obligation. These steps are one transaction with deferred intra-owner references.
8. Check the complete owner set and close statement cursors. Execute SQL COMMIT. Return the exact owner-commit acknowledgment only after successful completion under the qualified settings.
9. On failure, classify actual knowledge, roll back if the transaction remains active and rollback is possible, close, then reconcile O if commit may have occurred. Never return a successful durable acknowledgment before COMMIT or infer “none” merely from an exception.

After restart the new head, history, result and required duty are all visible or none of that mutation is visible. A successfully committed owner set may still have an unsatisfied Evidence duty; that is not a torn transaction or successful custody.

### 8.2 Operation/result meaning

Retain a small result envelope: schema/reader version, S/O and original semantic descriptor reference, acknowledgment stage `owner_commit`, resulting H/R, local configuration-mutation extent `completed`, safe error/cause if applicable to a recorded stage, duty references and declared coverage. `owner_commit` is acknowledgment meaning, not a new canonical lifecycle state. No external Effect is invented for the configuration test.

The successful stored publication outcome has no fabricated business error. Pre-commit rejection/failure responses do not gain a committed result row by logging them. Failure to report a committed outcome cannot overwrite it with failure. Later obligation observations/status are separately returned by status inspection; they do not rewrite the original publication result.

The semantic descriptor includes original expected absence or H, exact typed effective input and source interpretation, subject/requester and governing versions. Object key order may be irrelevant where declared; omitted/null/empty, numeric conversions, collection order and defaults are not guessed equivalent. Compare decoded validated values; no digest-only equality or model judgment.

Mandatory lost-ack case: **O expects H1 → commit H2/R2 → response lost → another operation commits H3/R3 → equivalent O with original H1 returns H2/R2**. It neither creates R4 nor returns Conflict solely because H3 is current. A different descriptor under O conflicts. A genuinely new O2 expecting H1 conflicts.

## 9. Historical lookup, retention and obligations

Exact `(S,R)` lookup returns the retained immutable interpretation, or explicit unavailable/VersionMismatch. No rebuild from current defaults, source files or environment; no redirect to latest. Current head reads are a different operation.

Initial qualification retains every synthetic head/history/result/duty until the explicitly disposable test store is torn down. Coverage identifies that fixture/store identity, all submitted operations in the test interval, supported failures and the intact/non-restored assumption. No TTL, production support interval or eternal retention promise is implied. Teardown ends test coverage and cannot be an operational cleanup path.

Before operating retry support, the accountable owners must approve actual coverage/retention intervals under ADR-008/009/011 and capacity bounds. Outstanding duties may require longer retention. This format provides explicit coverage fields; it does not fabricate policy precedence. Automatic pruning is not selected. If a real policy forbids retaining required records, block the affected guarantee and route governed disposition rather than silently keeping forever or deleting recovery proof.

### 9.1 Source duty

`duty_json` retains exact obligation identity/revision, S, source R and source O, responsible requester/Principal/duty, required action and target, requirement/guarantee refs, due and retention bounds/time basis, status, next safe action and reconciliation authority. It records safe source fact/provenance, last evidence/error where present and actual observation times with stated uncertainty. `created_head_revision` orders creation only within S; wall time is diagnostic, not revision authority.

Initial status is **pending**. Canonical obligation vocabulary remains pending, satisfied, failed, requires intervention; the first implementation provides no mutating repair endpoint. It does not manufacture custody, an Evidence ID or a receipt. Absence of pre-effect custody cannot be excused by this post-effect duty. Later repair requires its own operation ID, expected obligation revision, current authority, evidence and history under CTR-057; add its exact schema evolution before implementing those writes.

### 9.2 Bounded discovery

Create index `(tenant_id, owner_id, status, application_id, configuration_instance_id, created_head_revision, obligation_id)`. Issue one query per explicit status within the authorized tenant/owner. Order lexicographically by `(application_id, configuration_instance_id, created_head_revision, obligation_id)` using fixed binary comparison, with a keyset cursor and `LIMIT`, never increasing OFFSET or loading all history.

Cursor binds store ID, tenant, owner, status, query/reader version and last key; validate it as untrusted input and recheck authority on each request. Use at most 128 rows per fixture page and the payload limits. Per-subject discovery adds exact application/instance predicates. Index plans and actual behavior are tested.

Pages are current observations, not a global snapshot. New rows whose key sorts behind an in-progress cursor appear in the next scan from the beginning; status changes may similarly move duties between scans. Restart starts a fresh pass. Returned duty identity/revision supports idempotent later claiming. There is no claim of one-pass completeness under concurrent mutation or exactly-once scheduling. A finite pass over quiescent test state must enumerate every outstanding duty exactly once; repeating a live pass is bounded work, not an infinite retry service selected here.

## 10. JSON records and strict decoding

Select stdlib JSON encoded as UTF-8 TEXT record envelopes plus explicit relational keys. Each record declares `record_kind`, `record_schema_version`, `reader_contract_version`, exact scope/identities/revisions and its specific fields. Configuration contract/composition versions remain distinct from record and SQL schema versions. Old supported readers remain available for exact history.

| Input condition | Required behavior |
| --- | --- |
| Duplicate object key | Reject using a decoder hook that detects duplicates at every object level; no last-key-wins. |
| NaN/Infinity or overflowing float interpretation | Reject non-finite numbers. Initial records use bounded integers/text for exact numeric meaning; unsupported fractional fields fail rather than coerce. |
| Bool supplied for integer | Reject by exact type, not `isinstance(value, int)` alone. |
| Missing/wrong field/type | Fail validation; never apply today's defaults to historical records. |
| Unknown mandatory field/kind/version | Fail closed. First schema has a closed field set; no catch-all executable extension bag. |
| Oversize/deep input | Check UTF-8 byte length before parse; enforce depth/token/collection bounds with a string/escape-aware preflight and post-parse validation. A post-parse depth check alone is insufficient protection. |
| SQL key versus JSON envelope mismatch | Treat as corrupt/substituted record; do not choose whichever copy is convenient. |
| Invalid UTF-8/surrogate or malformed JSON | Reject; no replacement decoding or best-effort salvage into authority. |

Rendering uses sorted object keys, explicit separators and `allow_nan=False` for reproducible fixtures. Stable bytes are not semantic identity or authority. Keep semantic equivalence explicit; do not persist dataclass repr, SDK objects, Python exception objects, pickle, eval, import paths to classes or arbitrary object hooks.

No additional payload digest is selected initially: it would not authenticate a maliciously rewritten record and does not replace schema/decoder/integrity checks. The integrity claim is bounded structural consistency and trusted writes, not detection of every valid-looking byte alteration. A requirement for stronger content authenticity needs independently qualified integrity evidence before support.

## 11. Migrations

Select a short owner-local registry of reviewed numbered migrations, not Alembic or a universal migration framework. Store format, owner schema, record schema, reader contract and canonical contract versions are distinct. Initial SQL/record/reader versions are 1; future transitions name exact supported source and target.

Each migration specifies immutable ID, SHA-256 fingerprint of the reviewed migration artifact, owner, source/target versions, reader range, preconditions, data transformation, historical-meaning argument, failure behavior and postchecks. The fingerprint binds reviewed bytes; it is not a signature, authority or data identity.

Procedure:

1. Explicit maintenance authorization, known expected store identity and source schema, compatible readers, adequate bounded working space and reviewed recovery/backup plan.
2. Stop admissions and confirm all owner work/connections quiescent. For this shared first database, maintenance quiesces the whole runtime. This technical exclusion does not merge owner semantics.
3. Open one verified maintenance connection. Check source integrity/foreign keys and metadata. Reject unsupported starting versions or a previously used migration ID with different fingerprint.
4. Use one explicit transaction for the first bounded owner migration. Apply transactional DDL/data changes, validate the complete target and preserved historical meaning, insert the committed migration marker and update schema metadata in that same transaction.
5. COMMIT; close and reopen; verify target schema/readers, integrity and exact old results/revisions/duties before returning the owner to service.

No migration on import or ordinary open; no VACUUM, journal-mode switch, external I/O or other nontransactional maintenance inside the migration unit. No nested `executescript` assumptions. Unknown commit uses the migration ID and metadata for inspection; do not blindly rerun. If source state is intact and the transition never committed, explicit authorized retry may proceed. If the target marker/state is complete, validate it instead of applying again. Mixed/inconsistent/unreadable state remains unavailable/requires intervention.

A supported migration must preserve old revision identity and exact interpreted meaning. Representation changes require explicit equivalence and retained reader evidence; a semantic change publishes new meaning/revisions instead of rewriting old history. Immutability protections removed during a reviewed representation migration are restored in the same transaction and checked after reopen.

No actual predecessor release exists yet. Test initial schema and unsupported versions immediately; use labeled synthetic migration fixtures for interruption machinery. Those fixtures do not establish a real release upgrade claim. Real format changes require real old-format fixtures and ADR-011 compatibility assessment. Downgrade is unsupported until separately demonstrated.

## 12. Restart, integrity and corruption

Normal restart presumes the expected persistence domain is intact, has not been restored/replaced and no predecessor can still act. Establish the independent expected identity/context first; open-existing; let SQLite recover its journal through supported mechanisms; verify metadata/schema/readers/settings; validate head/revision/result/duty relationships and exact records needed for use; enumerate retained operations/duties before dependent admission.

Never delete a “stale” journal manually. Recovery itself may need writes/locks; a permission or lock failure means unavailable, not permission to bypass recovery with immutable/read-only assumptions. A diagnostic copy may be inspected separately without claiming operational readiness.

| Check | When | Failure treatment |
| --- | --- | --- |
| Store identity, purpose, schema/reader and settings | Every connection before owner work | Mismatch/unsupported mode unavailable; no automatic conversion. |
| Expected table/index/constraint/trigger definitions | Startup and migration reopen against versioned schema definition | Unexpected objects/definitions invalidate the supported schema. No substring-only acceptance. |
| `PRAGMA integrity_check` | Initial startup/recovery qualification, suspected damage and post-migration; before opening supported work for the bounded first store | Non-ok or incomplete/cancelled check blocks readiness. This may scan the bounded database; not run on every command. |
| `PRAGMA foreign_key_check` | Same controlled startup/recovery/migration checks | Any returned violation blocks affected use; integrity_check alone is insufficient. |
| Strict record decoding and cross-field checks | Every returned/used record; bounded startup traversal of retained required records | Malformed or uninterpretable row unavailable; never returned as valid empty data. |
| Owner compound-set consistency | Commit and restart tests; startup verification in bounded pages | Dangling/mismatched head/result/duty is corruption or implementation defect. |

These are design requirements for this small bounded store. An interrupted/over-budget full check leaves startup unavailable; increasing supported size requires a qualified verification strategy, not silently skipping integrity. Diagnostic reports contain safe categories and references only. Preserve original files for entitled investigation where feasible; do not overwrite, delete or recreate them. Physical corruption may affect every owner in a shared DB, so do not claim unaffected scopes without evidence.

SQLite explicitly separates foreign-key checking from `integrity_check`; both are required for the stated structural checks. Neither attests semantic truth or freshness. [SQLite integrity checks](https://sqlite.org/pragma.html#pragma_integrity_check).

## 13. Restore, backup and exclusivity

**Restore is not restart.** An old internally consistent image may omit head advancements, original outcomes, source duties and, once other owners exist, revocations or consumed claims. Store ID equality and integrity_check cannot establish that no newer history existed.

Known restored/copied stores enter controlled recovery with live mutation and automatic replay disabled. The entitled maintainer must establish lineage, lost interval, current controls and outstanding effects/duties from adequate independent evidence. Reconcile under the accepted owners; if freshness/completeness cannot be established, dependent live use remains unavailable. A new identity can host a separate new deployment but cannot claim continuation of lost old history. No claim to detect arbitrary coordinated rollback from the database's own metadata.

No automated backup service is selected. A later backup procedure must use qualified SQLite online backup or a verified quiescent closed-store copy; never copy only a live database file and assume journal state irrelevant. Preserve exact source identity/schema and backup observation scope. Every restored backup still faces the restore gate.

One admitted runtime process owns this physical persistence domain initially. Database writer locks protect transactions, not runtime authority or external handoff. A local epoch, PID file or SQLite lock cannot prove an old supervisor no longer acts. Operational startup must establish exclusive predecessor termination/fencing under ADR-015 before replacement. If that is unknown, no replacement mutation/dispatch. Subprocesses in contention tests exercise engine guarantees only; they do not advertise multi-process runtime support.

## 14. Disk full, I/O errors and unknown commit

Errors can occur during staging, journal creation, flush, commit or rollback. Preserve the actual SQLite error code/name and transaction stage in restricted diagnostics, not raw parameters/messages. Do not assume every OperationalError means the same outcome.

| Observed boundary | Safe conclusion |
| --- | --- |
| Before transaction or write, proven no earlier equivalent operation | This attempted mutation did not commit; prior operation history still checked. |
| Failure before COMMIT, active transaction and successful explicit rollback | This attempt's staged changes are absent. Verify through the tested boundary; do not erase older commits. |
| COMMIT returns success | New owner set is committed under the configured stack; acknowledge only the qualified failure guarantee. |
| COMMIT succeeds but response disappears | Caller knowledge unknown; owner status returns original committed result. |
| Storage error during COMMIT / process lost at boundary | No assumption of rollback or success; close/quarantine connection as safe, reopen verified store and inspect same O. |
| Rollback/close/reopen cannot establish outcome | Preserve unknown and require intervention/status recovery; no new operation ID or blind mutation replay. |

`SQLITE_FULL` qualification includes a constrained page-count fixture that provokes the actual engine code and an actual limited-volume case for journal/commit-space behavior where the host test environment supports it. Injected exceptions test application control flow only. Test write/flush failures and failure during rollback separately; a full condition while staging does not prove commit-time I/O behavior.

If a coherent intact store with complete scoped coverage proves O absent after the failed transaction, a later currently authorized equivalent submission may safely attempt the original guard. A missing row in a corrupt, restored, expired or incompletely verified store does not prove absence. A diagnostic log is never the recovery authority.

## 15. Concurrency and ADR-015 integration

Two genuinely new writers expecting H cannot both advance the same subject. Use actual overlapping connections/processes and barriers. One may acquire the writer lock while another receives fail-fast contention; after the winner finishes, a bounded explicit resubmission of the loser must observe Conflict. Also exercise overlap in validation with database-ordered entry to prove the guard, not just a busy error. No test-wide mutex may serialize away the contention being tested.

Concurrent equivalent O must yield one committed R; the second contender eventually obtains the retained result through a permitted bounded status/equivalent submission. Different meaning under O conflicts. Uniqueness and guarded transactions enforce this after any preliminary read race. Same opaque IDs in different authorized synthetic scopes remain distinct.

For later asyncio use, route synchronous SQL operations through ADR-015's explicit bounded worker bridge when necessary. Create/use/close each connection in its owning worker. Carry immutable context, S/O, deadline and admission scope explicitly; no ambient thread tenant. Register the assignment before it can run, bound pending and active work, and retain it until actual completion.

Cancelling or timing out the awaiting coroutine does not stop SQLite, roll back a transaction, free its worker slot or establish effect none. Retain ownership and reconcile the same O after completion/restart. A cancellation signal may prevent new work where ordered before it begins; do not claim a generic thread interrupt makes all I/O safely stoppable. No default executor, async DB facade or unbounded database pool is selected.

Follow ADR-015 lock order: release supervisor registry locks before owner/storage work; participating protected mutations acquire ADR-007 arbitration before owner transactions; no reverse wait or arbitrary callback. Fail-fast BUSY limits deliberate lock waiting but cannot prove a hard storage/OS execution bound. Any protected final-handoff path requiring an unproven bound remains unsupported.

## 16. Multiple owners and security

Later owners receive their own tables, schema/reader versions, transaction entrypoints and scoped contract vectors. Reuse connection mechanics only when real duplication justifies a small technical helper that respects ADR-002. No peer reference implementation imports or foreign-table updates through an owner's adapter. Root composition supplies the backing location; it does not become the state owner.

A single SQLite writer transaction can technically access all tables; the first realization prohibits cross-owner compound mutations. Enforce fixed statement inventories, owner-prefixed schema objects, tests that unrelated owner sentinels are unchanged and review of every transaction/migration. Consider a fixed SQLite authorizer as an additional future guard only if implementation evidence justifies it; no arbitrary callback framework is introduced here. Physical co-location remains a common failure/privilege domain, not a sandbox or global rollback guarantee.

| Threat | Control / residual limit |
| --- | --- |
| SQL injection | Parameterized values, fixed identifiers and no dynamic query builder/ATTACH. Exercise malicious input strings without leaking them. |
| Path substitution / store replacement | Protected parent directory, approved resolved path, expected external designation and store ID comparison; hostile admin replacement is outside proof. |
| Cross-tenant status/history leakage | Exact S predicates, composite foreign keys, explicit authorized enumeration; test same IDs in different tenants and non-disclosing errors. |
| Unsafe JSON | Bounded preflight, strict decoder, exact versions/types and no executable loaders. |
| Raw Secret retention | Closed configuration schema; safe SecretRef metadata only under ADR-010; no credentials in results, dumps or exceptions. |
| Rollback/stale copy | Known-restore recovery gate; no database-local anti-rollback claim. |
| Extension loading | Never enable/load arbitrary extensions; no SQL callbacks executing Plugin code. |
| Dependency/toolchain compromise | Record CPython/SQLite origin/build, reviewed lock/build inventory and known security findings under ADR-011. |
| Logs / debug leakage | Allowlisted owner/stage/error category and permitted O/H/R refs; never SQL parameters, raw payloads or unrestricted traceback messages. |
| Qualification DB used operationally | Purpose designation, separate temporary root, operational startup rejects fixture stores; no promotion by renaming a file. |
| Hostile in-process Plugin | Not supported; file/table boundaries do not establish ADR-012 isolation. |
| Weak file protection | Deployment owner must protect DB, journal, directories, diagnostic copies and backups with appropriate OS permissions/ACLs. No SQLite encryption or at-rest secrecy claim. |

Observation is not state, Evidence or provenance. A diagnostic sink failure cannot change a committed result or satisfy a custody duty. If the storage itself is lost, do not promise to persist the fact of that loss back into the same failed store.

## 17. Qualification layers and environment record

No layer below has been executed by this documentation task.

| Layer | Evidence required | What it does not establish |
| --- | --- | --- |
| Semantic contract | Owner Port vectors, original guard/equivalence, exact history, required duties, scoped access inputs | SQLite or durability behavior. |
| SQLite integration | Real disk file, actual constraints/triggers/index plans, explicit transaction behavior, settings on every connection, bounded contention and coherent reads | Abrupt machine failure. |
| Process crash | Separate OS child processes, real termination at named barriers, fresh-process reopen, all-or-none owner set | OS/device cache loss or power-loss flush behavior. |
| Migration | Source/target reader fixtures, atomic marker, interruption and unchanged old meaning | Unimplemented release upgrade paths. |
| Corruption/fault | Damaged DB/JSON, FK inconsistency, unsupported schema, FULL/I/O/rollback errors and safe unavailability | Detection of all malicious valid-looking changes. |
| Host/filesystem | Actual OS/VFS/filesystem/device flush/locking behavior and abrupt-machine termination/restart with intact media | Device loss, arbitrary rollback, all platforms or HA. |

The in-memory test fake implements the same owner-specific Port and semantic vectors. It is test-only and cannot be a runtime fallback. **Fake pass ≠ SQLite pass ≠ durability proof.** SQL-specific tests must deliberately bypass the Python validator to confirm durable constraints reject invalid rows/links; normal tests still exercise public owner behavior. Faults after each staged component must test COMMIT/reopen, including deferred FK failures.

Qualification report fields: exact source revision; test/oracle versions; interpreter full version/build/distributor and GIL mode; standard-library sqlite3 provenance tied to that CPython build; SQLite runtime version/source ID and compile options; supported APIs/STRICT/FK availability; OS build/architecture; filesystem/mount/location; selected VFS and evidence for that identification; device/controller/cache/flush assumptions; connection settings; fixture bounds; executed cases/results/counterevidence; limitations and reviewer.

Do not require the removed `sqlite3.version` attribute as a module-version source on Python 3.14. Record sqlite3 as the standard-library module shipped with the exact interpreter, and record `sqlite3.sqlite_version`/SQLite build metadata separately. Do not assume CPython 3.14 distributions link identical engines. If stdlib cannot expose an environmental detail directly, use distributor/OS qualification evidence and label uncertainty; do not fabricate a VFS name. [CPython sqlite3 constants](https://docs.python.org/3.14/library/sqlite3.html#module-constants).

Start with the maintainer's explicitly identified local Windows environment only after its details are recorded. The current workspace path is not enough to infer its filesystem or device guarantees. Other OS/build combinations require separate evidence under ADR-011. Measure commit/reopen latency and test volume after implementation; no production threshold or optimization ADR is selected.

**Machine-durable guarantee remains unqualified until actual host/storage evidence exists.** Review flush/locking guarantees and perform controlled abrupt-machine interruption experiments at relevant boundaries, with suitable external observation of acknowledgments and intact media. VM guest termination alone may leave host caches alive and is not automatically a power-cut test. Document precisely which failure was exercised. No successful PRAGMA query or subprocess kill discharges this obligation.

## 18. Failure timelines

These are expected outcomes and mandatory future tests, not observed results. Barriers use explicit parent/child signals; sleeps alone do not select the crash point. Parent watchdogs bound each test and verify child death before replacement. Fresh processes use no shared Python state.

| # | Timeline | Required outcome / proof |
| --- | --- | --- |
| 1 | Validate descriptor → prior O lookup → original H guard → insert revision → update head → result → required duty → COMMIT → ack | Exactly one complete new owner set; no ack before commit. |
| 2 | O1 expects H1 → another valid O2 commits H2 → O1 enters guarded mutation | Conflict; H2/history/result untouched; no automatic latest substitution. |
| 3 | O commits H2/R2 → same O and descriptor retransmitted | Retained H2/R2, no second revision/duty. |
| 4 | O exists → same O with changed input/requester/original guard | Conflict/identity misuse, no mutation; protected details withheld. |
| 5 | Two processes validate distinct O1/O2 expecting H → overlap BEGIN/write requests | One commit; contender may get BUSY then on bounded resubmission Conflict. Actual contention and the final revision guard both demonstrated. |
| 6 | Begin → stage some/all rows → injected failure or child killed before COMMIT | Fresh process sees old complete state; no orphan head/result/history/duty. |
| 7 | COMMIT succeeds → child signals post-commit barrier → response suppressed/child killed | Fresh process recovers new complete set and original outcome. |
| 8 | Staging or COMMIT hits FULL/write/flush error → rollback/reopen attempted | No false ack; inspect O. Proven absent allows only original guarded work; unresolved state remains unknown/intervention. |
| 9 | Retained JSON malformed or DB pages damaged → reopen/read | Affected scope unavailable; no default/empty result or automatic recreation; safe diagnostics only. |
| 10 | Store/schema/record reader version unsupported | Fail before mutation; no current-default interpretation. |
| 11 | Migration stages DDL/data/marker → kill before commit, then separately after commit | Old complete source or new complete target; inspect metadata before any retry; inconsistency blocks service. |
| 12 | Expected established store file absent | Open-existing fails; no auto-created file/owner. |
| 13 | Restore an older valid copy with same store ID | Known restore enters recovery-only scope; newer missing facts are not assumed absent. |
| 14 | Commit pending source duty → terminate → fresh process enumerates bounded indexed pages | Every quiescent outstanding duty found; no volatile queue dependency or fake custody. |
| 15 | O expects H1 → commits H2/R2 → ack lost → unrelated O2 commits H3/R3 → retry O | Original H2/R2 returned before checking current H3; H3 remains selected. |
| 16 | Two overlapping equivalent O submissions both initially see absent result | Exactly one committed publication; other returns retained result or truthful temporary unavailability. |
| 17 | Reader holds rollback-journal snapshot → writer COMMIT is BUSY | Explicit rollback/close; no internal infinite commit retry; original state unless a prior commit is independently established. |
| 18 | Child killed before BEGIN, during reopen/status or after read before reply | No new mutation from read; next fresh inspection repeats safely; no write replay. |
| 19 | Async caller cancelled while worker may be committing | Worker remains owned; slot not recycled prematurely; same O reconciled on actual completion. Later ADR-015 integration test. |
| 20 | Same opaque O/R in another synthetic tenant; wrong-scope query | No cross-scope result, mutation or existence disclosure. |
| 21 | Required duty omitted or result mismatches revision → COMMIT | Deferred constraint/owner consistency check refuses complete transaction; reopen preserves old set. |
| 22 | Create-new interrupted before metadata ready → ordinary open-existing attempted | Unready/malformed store unavailable; no inferred first-run authorization. |

## 19. ADR-004 behavior mapping

| Required behavior | Concrete realization / proof reference |
| --- | --- |
| Owner-local transaction | Fixed configuration transaction module; no foreign tables; §§5, 16. |
| Expected revision | S/H conditional UPDATE, positive monotonic successor; §§7–8, timeline 2/5. |
| Expected absence | Plain scoped insertion and uniqueness; no REPLACE; §8. |
| Compound commit | Deferred referential complete head/revision/result/duty set and final owner check; §§7–8, timeline 21. |
| State | Mutable configuration head only; §7. |
| History | Immutable exact revision/provenance, original reader; §§7, 9. |
| Result | Immutable original descriptor/outcome and coverage; §8.2. |
| Obligation | Applicable pending source duty in same transaction; §9.1. |
| Durable acknowledgment | SQL COMMIT followed by acknowledgment, qualified stack; §§4, 8, 17. |
| Exact historical read | S/R with recorded interpretation or unavailable; §9. |
| Lost acknowledgment | Same O recovers original H/R after advancement; timeline 15. |
| Equivalent retry | Original outcome before stale-guard test; §8. |
| Conflicting reuse | Exact semantic descriptor comparison and scoped uniqueness; timeline 4. |
| Restart | Expected identity, physical recovery and complete owner verification; §12. |
| Duty discovery | Scoped status index and bounded keyset pages; §9.2. |
| Tenant scoping | Explicit S on every operation and full scoped FK; §§7, 16. |
| Owner scoping | Owner-specific schema, statement inventory and no peer writes; §16. |
| Integrity validation | Schema/FK/structural checks and strict record decoding; §12. |
| Corruption handling | Unavailable, preserve safe diagnosis, no reset; §§12, 14. |
| Migration | Owner-local transactional transition and marker with reopen proof; §11. |
| Retention | Fixture coverage now; governed operating intervals before promises; §9. |
| Recovery | Discover truth/duties, current controls before work, no blind replay; §§12–15. |

## 20. Solo-developer burden and reversibility

| Burden | Selected SQLite approach | More complex external DB alternative |
| --- | --- | --- |
| Implementation | Small fixed SQL/codec/owner boundary; exact failure semantics still substantial | Same owner semantics plus network/client/server failure modes. |
| Operations | One protected file set, bounded startup and manual recovery | Provisioned service, credentials, connectivity, server upgrades and monitoring. |
| Maintenance | Interpreter/SQLite qualification, schema/readers and lock/settings review | Client/server versions, service configuration and compatibility matrix. |
| Testing | Actual constraints, subprocess crashes, migration/corruption and host qualification | Adds network partitions, server termination, connection pools and server storage. |
| Local development | Isolated temporary files and directly inspectable records | Service/container lifecycle and credential setup. |
| Deployment | Qualified local disk/ACLs and exclusive runtime | Separate deployment, service authority and operational ownership. |
| Learning | SQL transactions, journals, scoped invariants and honest unknown outcomes | All owner concerns plus server administration and distributed failure knowledge. |

The first approach has meaningful cost; correctness testing is not optional simplicity. External services and frameworks are rejected because they add cost without removing the accepted obligations.

Replacing SQLite is possible through the owner-specific Port but not trivial. Quiesce/fence writers; bind exact source/target identity and supported readers; transfer all current heads, immutable R/provenance, scoped H/O meanings, exact original descriptors/results, coverage and every duty; verify counts/relationships **and semantic content**, not counts alone; retain source read access as policy permits; atomically establish the controlled routing/cutover decision without pretending both stores share a global transaction. Only one realization may own new mutations. Unknown transfer/cutover keeps dependent work unavailable until inspected.

Preserve owner identity and canonical revision/reference meaning; physical store identity may change through an explicitly recorded transfer, never by silently changing the expected path. Target qualification repeats conditional/duplicate/crash/read/retention tests. Once the target commits new work, returning to an old source image is a new reconciled transfer, not rollback. Evidence/source custody and external effects remain separately owned. Stronger concurrency, topology or threat requirements can require an ADR change only if they change accepted semantics; an engine replacement alone does not.

## 21. Decision acceptance and implementation qualification

This document can be accepted before code exists because it selects a concrete mechanism, schema/transaction discipline, test obligations and limitations. **Accepted decision ≠ qualified implementation.** The following checklist assesses document coverage only. “Specified” does not mean tested.

| # | Acceptance criterion | Disposition / section |
| --- | --- | --- |
| 1 | ADR-004 preserved | Specified, §§1, 19 |
| 2 | ADR-008 duplicate ordering | Specified, §8 |
| 3 | ADR-009 duty/custody separation | Specified, §9 |
| 4 | ADR-015 cancellation/worker ownership | Specified, §15 |
| 5 | Concrete engine | SQLite, §§3–4 |
| 6 | Journal mode | DELETE, §4 |
| 7 | Synchronous setting | EXTRA, §4 |
| 8 | Transaction mode | Explicit SQL, §5 |
| 9 | Connection ownership | Per-operation/thread-affine, §5 |
| 10 | First owner | Configuration, §7 |
| 11 | Head versus configuration revision | H versus R, §7 |
| 12 | Operation identity separate | O, §§7–8 |
| 13 | Compound commit | Specified, §8 |
| 14 | Duplicate handling | Specified, §8 |
| 15 | Expected revision | Specified, §§7–8 |
| 16 | Lost ack | Specified, timeline 15 |
| 17 | Historical lookup | Specified, §9 |
| 18 | Bounded duty discovery | Specified, §9.2 |
| 19 | Tenant/owner scope | Specified, §7 |
| 20 | No default tenant | Required, §§2, 7 |
| 21 | Schema strategy | Specified, §7.2 |
| 22 | Immutable history | Specified, §§7, 9 |
| 23 | Strict serialization | Specified, §10 |
| 24 | Unsafe deserialization rejected | Required, §10 |
| 25 | Migration discipline | Specified, §11 |
| 26 | Migration interruption | Specified, §11/timeline 11 |
| 27 | Restore versus restart | Specified, §13 |
| 28 | Stale restore blocks blind mutation | Required, §13 |
| 29 | Missing store fails closed | Required, §6 |
| 30 | Corruption fails closed | Required, §12 |
| 31 | Disk full | Specified, §14 |
| 32 | Commit uncertainty | Specified, §14 |
| 33 | Concurrent writers | Specified, §15 |
| 34 | Bounded contention | Fail-fast, §5 |
| 35 | No infinite busy retry | Required, §5 |
| 36 | Parameterized SQL | Required, §§4, 16 |
| 37 | Extension loading prohibited | Required, §4 |
| 38 | No arbitrary callbacks under transaction | Required, §5 |
| 39 | Machine/process distinction | Explicit, §17 |
| 40 | Filesystem/VFS inputs | Specified, §17 |
| 41 | No encryption claim | Explicit, §16 |
| 42 | No raw Secret storage | Required, §16 |
| 43 | Safe observation | Specified, §16 |
| 44 | Scoped integrity checks | Specified, §12 |
| 45 | No ORM | Selected, §3 |
| 46 | No generic repository | Selected, §3 |
| 47 | No event sourcing | Selected, §3 |
| 48 | No global transaction | Required, §16 |
| 49 | Co-location does not merge owners | Explicit, §16 |
| 50 | Fake not durability proof | Explicit, §17 |
| 51 | Real SQLite tests | Required, §17 |
| 52 | Subprocess crash tests | Required, §§17–18 |
| 53 | Migration tests | Required, §§11, 17 |
| 54 | Corruption tests | Required, §§12, 17 |
| 55 | At least 14 failure timelines | 22 specified, §18 |
| 56 | Security analysis | Specified, §16 |
| 57 | Seven burdens | Compared, §20 |
| 58 | Replacement/migration | Specified, §20 |
| 59 | No source implemented | Documentation-only deliverable |
| 60 | No canonical ADR/index change | This lower-level record only |
| 61 | Acceptance is not qualification | Explicit, §§1, 17, 21 |

**Unsatisfied document-design criteria:** none identified after review. All executable proof remains outstanding: semantic vectors, actual DDL/constraints, process-crash recovery, migration/corruption/disk errors, the real platform/VFS/flush guarantee and later supervised cancellation/security integration. No unavailable proof is treated as passed.

**Ready for implementation review:** yes, as a Proposed decision. The maintainer can accept/reject this exact choice without approving an unbuilt durability claim. No canonical amendment or numbered ADR is needed for the selected scope.

**Recommended next action:** review and accept this lower-level record, then follow the Gate-1 dependency order. Start F0 if foundations are not implemented; proceed through values/configuration, owner contract and codecs before F6 durable code. Implement the selected store only through a separately authorized bounded task, then qualify each layer before its corresponding runtime guarantee. Do not create further ADRs or implement source as part of this deliverable.
