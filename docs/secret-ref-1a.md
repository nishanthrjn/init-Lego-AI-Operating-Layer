# SECRET-REF-1A: synthetic exact-use implementation



Status: **LOCALLY QUALIFIED** (2026-10-07).

Explicit maintainer resumption follows the qualified 72-phase

[durable prerequisite](../planning/LEGOAI-SECRET-USE-DURABLE-CUSTODY-DECISION.md).

The accepted [Secret scope](../planning/LEGOAI-SECRET-REF-1-DECISION.md) and

[shared arbitration scope](../planning/LEGOAI-SECRET-REF-1A-ARBITRATION-DECISION.md)

remain the authority. No ADR is allocated or amended. G03 remains open.



## Public contracts and admission



Governance defines `SecretRef` around the existing exact `SecretRevisionRef`,

adding declared class/use requirements without duplicating durable identity.

Owner/tenant, opaque identity, exact material revision and admitted mapping revision

remain explicit. This profile supports only the synthetic class; class semantics

are fixed by the qualified implementation, not an arbitrary Secret taxonomy.

There is no alias/current selector or interpretation of an environment name.

The existing immutable `SecretUsePlan` binds purpose, requester/actor, consumer

capability/version, target/account mapping, configuration revision, operation,

Grant, Policy, optional Approval, use/duty/submission identities and time bounds.



`SecretAccessPort` offers `resolve_secret_reference`, `authorize_secret_use`,

`validate_secret_revision` and `record_secret_use`. None returns material.

Authorization returns a point-in-time `AuthorizationDecision`, not a live handle

or permission to call an arbitrary consumer. A denied request raises a uniform

`PermissionError`; storage uncertainty remains an inspectable error, not success.

`record_secret_use` reads the retained source fact rather than accepting a caller's

assertion that use happened. The reference realization is private and is not

wired into `LocalRuntimeHost`, a Model adapter, an Agent or any application.



The private composition accepts only the qualified concrete participants and one

exact, externally established admission. Constructing a Grant or context does not

authenticate it. Trusted composition establishes requester and custody access,

then binds the exact context/reference/use/Catalog entry. Final currentness uses

the existing Grant/Policy/Approval owners; no independent authority universe is

created. Delegation and stronger authority profiles remain unsupported.



## Lock order and acceptance



The domain owns synchronization only. Grant `revoke`, Policy `supersede`, Approval

`consume`, Catalog `publish`/`withdraw`, Secret mapping/revision invalidation and

cancellation acquire the same injected domain by construction. Credential-free

no-argument registry/catalog construction retains its prior behavior. Bound

Approval consumption also refuses an exhausted count; the already-held private

consumption method requires the domain. Missing/mismatched domain identity or

unqualified participant types refuse composition.



The concrete order, derived before implementation, is:



1. On the SQLite owner thread, authorize the exact candidate, prepare source duty,

   and commit pre-use Evidence. Obtain its witness by durable owner lookup.

2. Acquire ephemeral synthetic material outside the domain. Publishing it into

   private owner state participates in the domain, so cancellation cannot leave

   a later usable handle.

3. Enter the shared domain once; recheck current authority, Policy, Catalog,

   exact request/mapping/revision, cancellation and sampled clock. Validate the

   exact pre-use witness and live source slot before Approval consumption.

4. Remove the private single-use material slot, consume applicable Approval once,

   then commit source accepted fact, uniqueness and outstanding attribution duty

   in the existing single local SQLite transaction. This commit is the entire

   synthetic effect. There is no independently effectful consumer callback.

5. Release the domain, discard material and invalidate the live source slot even

   on failure. Submit accepted-use Evidence separately; close duty only against

   its exact durable receipt. Submission failure leaves accepted/outstanding truth.



There is no Coordinator lock or existing dispatch-arbiter lock in this path.

The legacy arbiter can call a bound registry mutation, giving the one-way order

legacy arbiter -> domain; nothing holding the domain calls that arbiter or the

Coordinator. Evidence I/O and preparation never hold the domain. The only disk

transaction within the domain is the expressly accepted bounded source commit.

There is no queue, worker, future, network wait, arbitrary callback or `to_thread`.



SQLite retains its qualified owner-thread restriction. Acceptance, inspection and

repair refuse foreign-thread calls before touching stores. Invalidating owners may

commit from other threads. One exact use is admitted per source-ledger incarnation; its single Stage-A
binding cannot be recreated to reset cancellation or mapping/revision invalidation.

competing/repeated acceptance cannot consume it twice. There is no claim of an

arbitrary-thread SQLite service or automatic task scheduling.



## Cancellation, expiry and recovery



Cancellation becomes effective at its domain mutation. Before acceptance it denies

use without consuming Approval; after acceptance it cannot erase the fact, refund

Approval or allow reuse. Async task cancellation is not this synchronous mutation;

no remote HTTP or mid-call asyncio cancellation guarantee is asserted.



A concrete injected clock supplies local UTC or explicit deterministic test time.

The final gate samples time again, including Grant/Approval and Secret-use expiry.

At the expiry boundary acceptance refuses; expiry after acceptance preserves the

fact. This is logical sampled-time ordering for the accepted synchronous profile,

not a hard realtime CPython/storage deadline. No setting admits a stronger profile.



A lost acknowledgment is resolved using retained exact status, never by invoking

acceptance again. An uncertain/failed commit does not refund a consumed Approval.

Restart restores safe facts/duties only. It cannot restore authority, counts,

material, a handle or execution. The store's existing incarnation guard refuses

new work even if a fresh composition supplies candidate authority. A new trusted

inspection/repair admission may acknowledge the retained Evidence and close its

duty. Historical attribution access is separate from authority to use material;

revocation of use does not prevent already-entitled custody reconciliation.



Repair never calls protected acceptance or consumes Approval. Store identity,

receipt linkage, retention, corruption handling, crash/recovery and bounded

capacity retain the qualified durable prerequisite's limits. No global transaction,

shared owner store or SQLiteConfigurationStore reuse is introduced.



## Verification and limitations



Run from repository root:



```powershell

uv run python .\validate_secret_ref_1.py

```



The validator has 62 named phases. It runs the complete focused Stage-A suite once

and references that same successful invocation for requirement phases 5–49; it

does not reuse prior-run evidence. Other phases cover accepted prerequisites,

scope, architecture, participating owners, credential-free runtime, Model, Agent,

OpenAI-compatible, ForgeAI, DocuMind, durable custody/crash regressions, mypy,

Ruff lint/format and diff integrity. It uses existing environments, performs no

installation, and permits only unchanged fake loopback provider tests.



Deterministic event tests cover invalidation before acceptance and mutations

waiting at the actual source commit. Canary checks cover repr, serialized public

values, attribution reports, configuration fingerprints, errors/causal chains,

captured output/logs, SQL trace, live DB files and rollback journals during commit.

Material is not persisted, hashed into metadata or returned. Python does not

promise physical zeroization or protection against a malicious trusted host,

debugger, memory dump or privileged disk tampering.



Scope checking uses qualified baseline `aab6583`; historical validator scope guards

are not rewritten. Temporary test state is confined to ignored

`.custody-validation-secret-ref-*` directories. On hosts that deny cleanup, these

are disposable test artifacts, not qualification records.



Stage-A operator qualification is recorded below. Stage B remains gated pending

review of its ordering evidence and the separately authorized consumer boundary.

No environment source, credential header, credentialed provider, remote deployment,

remote disclosure or KISSKI work is implemented or qualified. Independent HTTP or

other consumer effects require their separately authorized architecture boundary.


## Implementation verification record — 2026-10-07

An agent-run execution of all 62 validator phases passed using the repository's
existing Python environment. Operator qualification remains pending. Subsequent
adversarial review closed facade reconstruction resetting in-memory invalidation
and tightened material disposal on Approval errors. After those changes:

- the expanded Stage-A suite passed (68 cases), followed by three passing targeted
  cases including the newly added disposal case: 69 distinct Stage-A cases covered;
- 289 durable-custody and architecture cases passed again, including crash recovery;
- mypy passed over 80 source files; Ruff lint and format passed over 13 changed
  Python files; scope and `git diff --check` passed.

The earlier full validator also passed 303 participating-owner/runtime cases,
48 Model cases, 53 Agent cases, 157 credential-free OpenAI-compatible cases,
89 ForgeAI cases and 16 DocuMind cases. The final changes did not alter those
runtime/provider paths. No external provider, credentials or Docker were used.
These implementation checks do not change the pending operator status or open
Stage B. The operator command above executes the complete final 69-case focused
suite and all 62 phases against the submitted tree.

## Change manifest

- Governance contracts: `src/legoai/governance/secret.py`,
  `src/legoai/governance/ports.py`.
- Reference owners and ordering: `src/legoai/reference/secret.py`,
  `src/legoai/reference/_secret_domain.py`, `src/legoai/reference/_secret_ledger.py`,
  `src/legoai/reference/governance.py`, `src/legoai/reference/catalog.py`.
- Private composition: `src/legoai/runtime/_composition/secret.py`.
- Verification: `tests/unit/reference/test_secret_ref.py`,
  `tests/support/secret_ref_scenario.py`, `tests/architecture/test_secret_ref.py`,
  `tests/architecture/test_import_boundaries.py`, `validate_secret_ref_1.py`.
- Documentation: this guide, `planning/LEGOAI-SECRET-REF-1-DECISION.md`,
  `planning/LEGOAI-SECRET-REF-1A-ARBITRATION-DECISION.md`,
  `planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md`.

## Operator local qualification recorded — 2026-10-07

**SECRET-REF-1A LOCALLY QUALIFIED.** The operator supplied a completed run of
`uv run python .\validate_secret_ref_1.py`: all 62 phases passed, including
69 focused Stage-A tests, 240 owner/import checks, 303 participating-owner/runtime
regressions, 48 Model, 53 Agent, 157 credential-free OpenAI-compatible, 89 ForgeAI,
16 DocuMind and 54 durable-custody tests. The additional 13-case crash/recovery
subset passed; it overlaps the durable suite and is not additional unique coverage.
Mypy passed over 80 source files; Ruff lint, format (13 files) and diff checks passed.
The attachment also contains the prior successful 72-phase durable prerequisite.

This qualifies only synthetic owner-thread acceptance, one exact use per source
incarnation, shared local invalidator ordering, sampled-clock expiry/cancellation,
and intact local-storage custody/recovery. No broader Coordinator redesign was
required for this profile. No environment source, real credential, external
provider, Docker, remote transport or live model-quality claim is established.

The Stage-A qualification prerequisite is satisfied. Stage B remains gated:
synthetic source acceptance does not establish independent consumer or HTTP
handoff atomicity. Those boundaries require their separately authorized decision
under the accepted durable-custody scope. G03 remains open; remote disclosure and
KISSKI are not authorized. No Stage-B implementation begins with this record.
The earlier implementation-time pending/stopped assessments are historical.

Repository implementation at reconciliation: `1105a02`. The supplied transcript
does not embed a commit identity; this record does not assert an independently
verified run-to-commit binding.

## SECRET-SOURCE-S1: operator-provisioned process-local material (ADR-023 §8)

S1 is the first real material source, for ADR-023's single-operator SRCP-1
profile. It is a private reference realization behind Secret Access
(`legoai.reference.secret._ProvisionedSecretSource`). There is no second
Secret subsystem: the Stage-A exact-use composition is reused unchanged,
except that the material it realizes is the operator's provisioned revision
instead of fresh synthetic bytes.

**Provisioning.**
- An explicit operator act: `provision(identity, purpose, consumer, material)`.
- It returns only a `SecretRef` of class `operator-provisioned`.
- The revision and mapping revision are owner-issued random identities, never
  digests of the material.
- Material must be visible ASCII, 1-4096 bytes (the existing material bound).
  Empty, whitespace, control and non-ASCII input is rejected without echo.
- The bootstrap helper `_provision_interactively` (private composition) reads
  hidden input via `getpass`. It refuses without an interactive terminal, and
  passes the material straight into the source.
- There is no environment, `.env`, configuration-file, command-line, keyring
  or SDK source, and no fallback.

**Immutability and lifetime.**
- A revision's bytes never change. Provisioning the same identity again issues
  a new revision and retires the previous one (no overlap).
- `retire` and `close` participate in the shared ordering domain. A retired,
  closed or replaced revision never yields material to a later use; one that
  was already accepted stays accepted.
- Material lives only in the source's private buffer for this process. Retire
  and close overwrite that buffer as best-effort hygiene only; no memory
  erasure is claimed. After a restart the operator provisions again, under a
  new revision. Close keeps safe revision metadata, and historical attribution
  is untouched.

**Use.**
- Provisioning authorizes nothing. Material is realized only inside the
  existing exact-use path: current Grant, Policy, Catalog and Approval checks,
  revision and mapping validity, expiry and cancellation, all under the shared
  domain.
- The use must also match the provisioned revision, the `SecretRef` (class and
  purpose) and the consumer.
- The only consumer is still the Stage-A source acceptance. There is no
  public plaintext API (`reveal`, `value`, `token` or `get_secret`), no
  Authorization header and no transport.
- Synthetic canaries are absent from references, statuses, facts, errors and
  their causal chains, logs, and the source and Evidence databases. Plaintext
  is never persisted.

S1 adds no credentialed transport, no REMOTE enablement, no KISSKI support and
no provider call. Environment-variable credentials remain unsupported.

```powershell
uv run python .\validate_secret_source_s1.py
```

**SECRET-SOURCE-S1 LOCALLY QUALIFIED** (2026-10-09). The operator's run of that
command passed **20/20 phases** offline on commit `f6537aa`. That includes 40
focused S1 tests with canary leak scans and 6 boundary tests; SECRET-REF-1A (75)
and durable-custody (59) regressions; governance and import boundaries (464); and
Core (1841), DocuMind (16) and ForgeAI (89) regressions. Qualification covers the
operator-provisioned, immutable, process-local material source behind the
existing exact-use mechanism only. There is no credential transport, no
Authorization header, no REMOTE enablement, no KISSKI support, no provider call
and no environment source, and no memory-erasure claim is made.

**CREDENTIAL-HTTPS-T2 (credential-bearing use).** The same exact-use
composition gains a second protected consumer, `_handoff`. Its first
occupancy performs the final checks, the durable Secret-use acceptance and
one nonblocking credential-bearing send. Each continuation write rechecks
current Grant, Policy, Catalog, revision, mapping, cancellation, expiry and
S1 eligibility before one more send. The Approval consumed at the handoff is
not required again for continuation writes of the same use. See
`docs/model-composition.md` for the transport and its validator.

**OPENAI-COMPATIBLE-REMOTE-1 (per-invocation uses).** A REMOTE Model binding
serves many invocations with one S1 revision. `_SecretUses` takes the source
ledger incarnation's single Stage-A binding once, so it can never be rebuilt
to reset it. Each `admit` composes a new exact use with its own plan, use id
(the remote attempt id), state, currentness checks, Approval consumption if
any, durable attribution and at most one handoff, and a use id is admitted
only once. S1 only: retirement and source close are owned by the shared
source under the ordering domain. `_SecretClock(domain, host=clock)` samples
the governed host's own trusted clock, so Grant, admission and Secret validity
use one time source. The one-use-per-incarnation facade
(`_SyntheticSecretAccess` without a factory) is unchanged.
