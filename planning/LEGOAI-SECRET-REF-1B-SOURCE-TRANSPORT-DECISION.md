# SECRET-REF-1B SOURCE + TRANSPORT BOUNDARY DECISION

Date: 2026-10-07. Status: **DEFERRED/BLOCKED by explicit maintainer disposition**.

- Source: **PROVISIONED IMMUTABLE LOCAL SOURCE RECOMMENDED** (S1).
- Transport: **NO TRANSPORT PROFILE YET SATISFIES ADR-010** (T4 for current support; T2 is the smallest candidate for further proof).
- Overall: **SECRET-REF-1B STILL BLOCKED**.

S1 can establish exact local source identity/currentness under the bounded
ownership model below. The inspected transport does not establish bounded
actual-use validity. This decision narrows both questions but does not pretend
to have resolved the transport blocker. It authorizes no source, transport,
settings or runtime implementation. No accepted ADR is amended or reinterpreted.

## Maintainer disposition — 2026-10-07

**SECRET-REF-1B DEFERRED — BLOCKED ON QUALIFIED CREDENTIAL TRANSPORT**.
The completed assessment's outcome remains **SECRET-REF-1B STILL BLOCKED**.
No further Secret/transport architecture or implementation work should begin
without a concrete credentialed consumer/provider requirement whose product
value justifies transport qualification, and explicit maintainer authorization.
The conditional future work below is deferred, not an instruction to proceed.

S1 is the preferred future source profile but remains unimplemented because
no qualified credential-bearing consumer exists. Blocking `urllib`/`to_thread`
has no qualified ADR-010 credential-use boundary; T2 remains only a candidate.
Check-to-handoff validity and bounded occupancy remain unproven. Durable
Execution-owned external-attempt integration needs additional implementation
authority. No `api_key` field is authorized.

SECRET-REF-1A and SECRET-USE-DURABLE-CUSTODY-1 remain **LOCALLY QUALIFIED**
within their recorded scopes. Credential-free OpenAI-compatible
`ModelDeployment.LOCAL` support remains **LOCALLY QUALIFIED**. No credentialed
model provider is currently supported. G03 remains open; REMOTE providers and
KISSKI remain unsupported and gated. This disposition changes no architecture,
runtime behavior or qualification claim.

## 1. Authority and current evidence

Inspected repository HEAD: `e3c6623` (`docs(secret): assess SECRET-REF-1B consumer boundary`).
Tracked working tree was clean before this documentation change.

Authorities inspected: [ADR-010](../adrs/ADR-010.md) §§3–11,
[ADR-007](../adrs/ADR-007.md) §§4–8,
[ADR-008](../adrs/ADR-008.md) §§7–11,
[ADR-009](../adrs/ADR-009.md) §§8–9,
[ADR-014 §14](../adrs/ADR-014.md),
[CONTRACTS](../contracts/CONTRACTS.md) §15.5 and CTR-056–061, and
[SECURITY](../security/SECURITY.md) SEC-020, SEC-039, SEC-057–060, SEC-075/077/085.
The [accepted staged scope](LEGOAI-SECRET-REF-1-DECISION.md),
[accepted arbitration scope](LEGOAI-SECRET-REF-1A-ARBITRATION-DECISION.md),
[durable custody decision](LEGOAI-SECRET-USE-DURABLE-CUSTODY-DECISION.md) and
[consumer-boundary assessment](LEGOAI-SECRET-REF-1B-CONSUMER-BOUNDARY-DECISION.md)
remain governing records. Ordinary mutable environment sourcing remains rejected.

Accept [Stage-A qualification](../docs/secret-ref-1a.md): operator command
`uv run python .\validate_secret_ref_1.py`, all 62 phases, including 69 focused
tests. Its synthetic owner-thread acceptance and intact local-storage scope is
unchanged. It qualifies neither real material nor HTTP.

| Source inspected | Finding relevant to this decision |
| --- | --- |
| [Secret contracts](../src/legoai/governance/secret.py), [synthetic source](../src/legoai/reference/secret.py), [composition](../src/legoai/runtime/_composition/secret.py) | Reference-only public access; one synthetic exact use; current checks and participating invalidation under the injected domain. |
| [Ordering domain](../src/legoai/reference/_secret_domain.py), [Secret ledger](../src/legoai/reference/_secret_ledger.py), [Evidence adapter](../src/legoai/reference/_durable_evidence.py) | The source SQLite transaction is the complete synthetic effect. Owner-thread restrictions and separate custody remain; no external HTTP attempt ledger is supplied. |
| [OpenAI adapter](../src/legoai/reference/model_openai_compatible.py) | `_post` uses blocking `urllib`, through `asyncio.to_thread`; no credential-aware write boundary. |
| [Settings](../src/legoai/runtime/api.py), [local composition](../src/legoai/runtime/local.py), [governed Model calls](../src/legoai/runtime/_composition/model_governed.py), [Execution Coordinator](../src/legoai/reference/execution.py) | Credential-free settings; REMOTE refusal; invocation claim and Model settlement. Coordinator `_states`/`_claimed` are in-memory, not durable external-attempt records. |

The installed interpreter inspected using `inspect.getsource` was CPython
**3.14.5, Windows x86-64**, with **OpenSSL 3.5.6**. Reads covered
`urllib.request.AbstractHTTPHandler.do_open`, `http.client.HTTPConnection.send`
and `_send_output`, `HTTPSConnection.connect`, `ssl.SSLSocket.send/sendall`,
`SSLObject.write`, `SSLContext.wrap_bio`, `create_default_context`, and
`asyncio.to_thread`. This is source inspection, not a transport qualification run.

## 2. Source options

| Option | Revision, mutation and rotation | Lifecycle, storage and deletion | Risk, testing, size and portability | Disposition |
| --- | --- | --- | --- | --- |
| S1: provisioned immutable local source | One admitted exact revision bound once to private immutable bytes; all eligibility/mapping changes use the domain; rotation provisions a new revision, never replaces old bytes. | Finite source incarnation; volatile protected backing material only; explicit teardown/revocation; restart requires new provisioning and new revision identity. | Smallest implementation; deterministic mutation/race tests; trusted-process memory exposure; no OS-specific material-store integration. | Recommend under §3; not yet implemented or qualified. |
| S2: owned local versioned file store | Potentially viable only with immutable records, exclusive authorized writers, ordered metadata changes, stale-revision refusal and rollback/identity protection. Files alone do not enforce these properties. | Persistent confidential material requires a separately protected provider store, permissions, backup/deletion and crash semantics. Restart must not restore use authority. | More storage/security work than the first consumer needs; testable locally; filesystem/OS guarantees need their own profile. | Defer; no reuse of ordinary Configuration or Evidence storage for material. |
| S3: OS credential store/keyring | No named backend has supplied an exact-version and mutation-participation contract. External administrative mutation cannot simply be treated as ordered. | OS-managed persistence/deletion; retrieval and restart validity depend on the selected store and scope. | Adds platform binding, access-control and external-mutation tests. A keyring API name supplies no currentness proof. | Not required for this first profile; defer pending a concrete backend contract. |
| S4: external vault/cloud store | Version IDs may help identity, but fetch success alone cannot order remote rotation/revocation with local use. Needs a qualified equivalent protocol. | External persistence, network acquisition, bootstrap credentials and remote failure/recovery duties. | Largest dependency/trust surface here; fake tests cannot establish real vault ordering. Portability depends on vendor semantics. | Not justified by the first LOCAL consumer. |
| S5: defer material sources | Preserves the present reference-only scope; no real revision/use claim. | No new material lifetime or persistence. | Smallest immediate change but cannot authenticate the endpoint. | Current operational state until both source and transport are authorized and qualified. |

## 3. Recommended S1 contract

### Ownership and exactness

Trusted composition explicitly provisions a protected Secret-owner realization
with one exact `SecretRevisionRef` and material. This is a confidential provider
provisioning boundary, not a raw-value field on `LocalHostConfig`, a public
Secret Access result, or an Agent/application input. No environment, `.env`,
arbitrary loader callback or ambient credential discovery is involved. The
composition root is within the declared trusted-host boundary; this does not
protect against a malicious host administrator or in-process memory reader.

Copy mutable provisioning input into owner-controlled immutable storage before
admission, retain no caller-owned mutable buffer, and reject a second binding
of the same revision. The admitted mapping binds owner/tenant, Secret identity,
mapping revision, exact material revision, permitted purpose, consumer/version
and provider/account target. SecretRef remains the sole source selector.
Revision identity is owner-issued metadata, never a digest of credential bytes.

There is no in-place replacement API, alias/latest fallback or read/export API.
Rotation creates a distinct revision and retires the old one under the domain;
the first profile has no overlap. Wrong, missing, retired or stale references
deny rather than upgrade. Cancellation, mapping invalidation, revision
revocation and source closing share the same participating domain as use.
Publication of a prepared immutable revision and retirement are bounded local
state transitions; preparation and disposal work stay outside the final gate.

Exactness follows from exclusive owner control of an immutable binding, not
from periodically checking mutable external storage. This is a defensible local
source contract under ADR-010 §§3 and 11, not yet implementation evidence.
It does not establish that a separately administered issuer still accepts the
token. Any issuer validity/revocation fact required by the admitted use must
participate in this order or supply a qualified equivalent guarantee; otherwise
that endpoint/profile remains unsupported. LOCAL classification alone supplies
neither issuer participation nor recipient identity proof.

### Source lifetime versus acquired material

The **protected material provider** may retain its authoritative backing bytes
for its explicitly admitted finite source incarnation. The host holds an opaque
association with that provider, not a normal configuration value containing
material. This differs from resolving a Secret at host open and caching its raw
value in the runtime/Model client: that ADR-010 §4B pattern remains rejected.
The exception is not a reusable consumer credential cache or an authenticated
connection pool.

Only after current preliminary authorization may the protected source create
an operation-bound private handle/material view. Do this just in time after
non-secret preparation, outside any slow final-gate work. Final use still
rechecks current source and governing owner facts. Every use has finite
acquisition/holding/call bounds; a fresh copy alone is not authorization or
freshness. Do not require physical copying as a security guarantee: controlled
references to immutable bytes can share physical storage. No acquired handle
survives its operation, cancellation or invalidation.

Teardown first marks the source closed under the domain, preventing new
acquisitions and writes through outstanding handles. Then release controlled
backing and operation references and close unsent transport buffers. Already
handed-off data remains in-flight truth. No memory zeroization, swap/core-dump
erasure or retraction from provider memory is claimed.

Restart restores only safe attribution/repair records. It must not reconstruct
material or handles from the ledger. Explicit reprovisioning uses a **new
material revision and mapping/incarnation association**, even if an operator
supplies the same bytes. Old references cannot bind to the new source. Safe
identity allocation/history must prevent retired identity reuse; missing or
uncertain history refuses admission. No persisted material hash is used to
claim byte identity across restarts. Actual token replacement at the issuer
is separate from issuing a new local provisioning identity.

## 4. Transport alternatives and source findings

`urllib.do_open` calls `HTTPConnection.request`, then waits in `getresponse`.
`_send_output` joins headers and calls `send`, then sends body chunks.
`HTTPConnection.send` can auto-connect, invokes `sys.audit('http.client.send',
..., data)`, and calls `sock.sendall`; debug mode can print data. HTTPS connects
then wraps the socket; `SSLSocket.sendall` loops over SSL writes. These paths
provide neither a per-credential currentness gate nor safe partial-send counts
on every failure. Do not instrument them by sending secrets through audit/debug
surfaces and assuming observers never retain the payload.

| Option | What it supplies | Decision |
| --- | --- | --- |
| T1: retain urllib with lower-level interception | A custom connection could intercept `send`, but still must replace implicit connection, `sendall`, TLS, audit/debug disclosure and delayed write behavior. Intercepting request construction is too early. | Reject as the minimal qualified bridge; the substantive work becomes T2 anyway. |
| T2: private socket/ssl/http.client transport | Explicit nonblocking socket sends can expose progress; `SSLObject`/MemoryBIO can isolate TLS processing from socket I/O; response parsing can remain separate. | Closest candidate, but the actual-use timing/occupancy and safe invoking-owner integration proof below is missing. Do not label it feasible under the complete ADR contract yet. |
| T3: new HTTP dependency | Convenience, async support or cancellation APIs alone do not prove ordered irreversible writes, bounded acceptance or durable attempt ownership. | No dependency justified. No particular third-party client has been qualified or claimed incapable. |
| T4: unsupported pending a qualified boundary | Preserves credential-free transport and refuses credentialed use. | Select for current support. This is not a claim that all future stdlib designs are impossible. |

## 5. Candidate handoff, and why it is not yet sufficient

The narrow T2 candidate is one exact private transport instance per attempt,
with no pool, redirect, proxy inheritance, ambient auth or background writer.
It prepares DNS, TCP connection, recipient verification and TLS negotiation
without credential bytes outside the domain. Serialize the non-secret request
parts separately; no credential-bearing request bytes are sent during this
preparation. LOCAL HTTP without TLS additionally needs an admitted protected
local channel; LOCAL is not a confidentiality guarantee for arbitrary networks.

After JIT acquisition, a private admitted bridge would perform final exact
authority, mapping/revision, cancellation, expiry, Approval, attempt uniqueness,
pre-use custody and transport-ownership checks under the domain. All bytes for
this operation remain privately bound to that checked connection/target.

The proposed external handoff H is **positive acceptance of credential-bearing
wire bytes by the local transport's nonblocking socket send**, ordered inside
the domain. It is not `Request` creation, header construction, connection,
`to_thread`, readiness notification, or TLS encryption into a memory buffer.
For TLS, conservatively treat the outbound application-data ciphertext flight
associated with the credential as credential-bearing; do not claim a ciphertext
offset is an exact plaintext disclosure count.

Each later write of that flight needs another current gate. A would-block
result causes gate release and readiness waiting outside it, followed by fresh
checks; it does not grant future authority. This is continuation of one attempt,
not a retry/resend of the HTTP operation. Body transmission remains the same
governed external action and must not bypass cancellation or current controls
merely because the Authorization field was already sent. No network response
wait, readiness wait, task submission or arbitrary callback belongs in the gate.

**Unresolved proof:** nonblocking is not a demonstrated maximum duration from
the last validity check to H. The inspected CPython C wrapper releases the GIL
around the OS call and can handle interrupted calls; it supplies no joint
LegoAI authority/expiry-and-send primitive. See
[CPython 3.14.5 socket implementation](https://raw.githubusercontent.com/python/cpython/v3.14.5/Modules/socketmodule.c),
`sock_call_ex`, `sock_send` and `sock_send_impl`. Its nonblocking path avoids
waiting for writable capacity, but that does not prove a scheduling bound.

Concrete counterexample: authority expires at E; final checks run before E;
the thread is suspended before the syscall; it resumes after E and the socket
accepts bytes. No competing domain mutation is needed. A post-send clock check
can report the violation but cannot prevent disclosure. Readiness polling,
tiny buffers, the GIL and a configured timeout do not repair this counterexample.
ADR-007 §8 and ADR-010 §8.3 explicitly require a qualified check-to-acceptance
bound or equivalent atomic validity guard. No such bound/guard is supplied by
the current Windows/CPython profile. Stage A's sampled-time synthetic
qualification cannot be extended to HTTP by analogy.

The accepted Stage-A domain profile also expressly excludes network I/O and
permits only its named bounded source commit. A future approved transport
profile must explicitly qualify any nonwaiting socket operation under that
domain; it cannot silently reuse the Stage-A exception. This is an additional
scope obligation, not proof that a nonblocking send necessarily waits on network
readiness. No redesign or weakening of Stage A is requested here.

Before T2 can be authorized, provide a concrete platform/profile proof of actual
validity and bounded occupancy, including supported interruption/callback
behavior, or a separately approved equivalent transport enforcement mechanism.
Finite deadlines cannot simply be deleted or redefined as background invalidation.
This is the exact remaining transport blocker, not merely the absence of tests
for an otherwise approved implementation.

## 6. Partial writes and TLS facts

Keep these observations separate; they are private safe facts, not new canonical
Execution states or additional Model effect enum values.

| Observation | Meaning |
| --- | --- |
| Proven zero credential-bearing bytes handed off | No credential transmission for this attempt; preparation/acquisition and earlier claim consumption can still be real. A prefix-only cleartext write does not count as credential bytes. |
| Some credential-bearing bytes handed off | Local use accepted at least in part; possible disclosure; no assertion that a usable token or full request reached the provider. |
| All credential-bearing bytes handed off locally | Local acceptance complete for that flight; kernel buffering is not provider receipt. Body or response may still be incomplete. |
| Send outcome unavailable | Preserve UNKNOWN, even if the last durable observation showed zero or a smaller partial send. |
| Provider response observed | Record its actual complete/incomplete status separately; no inference of full successful Model execution from authentication alone. |

Use a minimal safe observation category such as zero/partial/all/unknown plus
observation sequence, attempt identity and phase; persist no header, token,
plaintext length, ciphertext or material-derived fingerprint. Exact offsets
needed for live continuation remain private and die with the attempt. A failed
`sendall` cannot establish exact prior progress; the
[Python socket contract](https://docs.python.org/3.14/library/socket.html#socket.socket.sendall)
is why the proposed bridge must not use it as its observation primitive.

`SSLSocket` can combine cryptographic buffering with transport activity.
`SSLWantReadError`/`SSLWantWriteError` is not proof that no earlier output was
generated or transmitted. For the T2 candidate, `SSLObject` with MemoryBIO
separates TLS from network I/O, as documented in
[Python's Memory BIO contract](https://docs.python.org/3.14/library/ssl.html#memory-bio-support).
Encryption into a BIO remains private preparation, not H. Every subsequent
network flush of credential-associated ciphertext is gated. Invalidation drops
unsent ciphertext and the connection; a TLS control step cannot secretly flush
credential application data after cancellation. Partial TLS-record transmission
is conservatively possible disclosure, not confirmed plaintext receipt.

A complete authenticated HTTP response is evidence about the peer response,
not proof of a usable Model result or backend completion. Confirmed receipt of
the complete expected Authorization header can be asserted in fake-server tests
using a private boolean observation, not inferred from local SSL writes.
An arbitrary 401 alone does not prove the server parsed every credential byte.

TLS qualification would require certificate/hostname verification, HTTP/1.1-only
operation, no client-certificate credential path, no resumption/pool authority
or early-data shortcut. Installed `ssl.create_default_context` honors
`SSLKEYLOGFILE`; the protected profile must disable ambient TLS key logging by
construction without weakening peer verification. No TLS secrets or buffers
enter logs, crash-recovery data or Evidence. These requirements do not resolve
the check-to-H bound.

## 7. Invalidation and cancellation

If Grant/Policy/Catalog, mapping/revision, source teardown or ordered
cancellation becomes effective before H, H must be refused. If H wins the
domain order, retain that accepted partial/full fact; later invalidation stops
future writes but cannot recall kernel-owned data. A pending cancellation
request is distinct from its authoritative domain transition. No alternative
writer may bypass that transition.

| Cancellation point | Required behavior of any future qualified bridge |
| --- | --- |
| Before acquisition | Deny acquisition; no material handle. |
| During acquisition | Reject/dispose late material; no downstream handoff. |
| After acquisition or connection preparation | Disable the operation; discard handle/buffers and close preparation outside the gate. |
| Immediately before H | Compete in the same domain; cancellation winning means no H. |
| During partial handoff | Preserve known partial/unknown observations; deny remaining writes once cancellation is effective. |
| After local handoff or during response wait | Stop only controllable later actions, retain observation responsibility and uncertain provider effect; no remote-cessation claim. |
| Awaiter cancelled while worker continues | The invoking owner retains supervision and attribution responsibility. Any surviving writer must still check the ordered cancellation/currentness at every write; otherwise the profile is rejected. |

The smallest candidate would keep acquisition and protected sends on the
invoking owner thread, using readiness suspension outside the gate. Workers
used for non-secret preparation receive no credential or capability to write
it. Async cancellation must commit the synchronous cancellation transition
before abandoning the attempt; cleanup/outcome custody must remain owned if
the caller departs. Closing a descriptor from an unrelated thread is not a
proof of stopped transmission. Current `_post`/`to_thread` does not satisfy
this lifecycle, and no force-thread-kill or new worker framework is proposed.

## 8. Durable external-attempt ownership

Select **the existing Model invoking plane, under Execution Coordination**, as
owner of a narrow credentialed-HTTP attempt record. Extend that owner's
realization rather than appoint Secret Access, Evidence, or the HTTP adapter as
a second dispatcher. The transport produces observations; Secret Access owns
revision/use authorization and safe Secret-use attribution; Evidence separately
owns custody. Runtime composition binds these responsibilities without merging
their stores or importing peer owner implementations.

Before possible H, the invoking owner must durably retain exact operation,
effect/attempt, requester/tenant, reference/revision, target/configuration,
decision/claim associations and reconciliation/submission duty. Preparation and
pre-use custody occur outside the gate. ADR-007 §6.2 additionally requires the
exact final handoff-attempt obligation to commit before H, after final claims;
storage delay requires revalidation. A future profile must explicitly authorize
and bound that owner-local commit. The Stage-A SQLite exception does not
authorize an extra Execution-store transaction.

Append observations for accepted local handoff, partial/unknown send, complete
provider response and outstanding duties with expected-revision/uniqueness
guards. Record only safe categories and references, never request content,
Authorization, handles, callbacks, TLS state or material-derived fingerprints.
One unresolved/completed attempt blocks a second independent dispatch. No
global event journal, distributed transaction or cross-owner rollback is needed.

The pre-handoff durable record means **handoff may follow**, not accepted Secret
use. A crash between send and recording its observation leaves UNKNOWN; SQLite
cannot atomically include a socket write. Even a retained partial observation
does not exclude further unrecorded progress. Missing post-send acknowledgment
does not establish zero. Recovery inspects/repairs safe records and Evidence
receipts; it never reconnects/resends, reacquires material or restores counts,
handles or authority. Post-effect custody failure leaves an outstanding duty.

The current Coordinator has no such durable store, and Stage-A Evidence codecs
are typed for synthetic facts. Reuse qualified storage/custody principles and
receipt semantics, not a synthetic `accepted` row to represent HTTP. A narrow
Execution-owned store and typed custody records would require explicit bounded
implementation scope and qualification. This is a named minimum extension for
review, not authorization for a general Coordinator persistence redesign.

## 9. Model effects, settings and endpoint boundary

| Event | Secret/transport truth | Existing Model meaning |
| --- | --- | --- |
| Connection refused before credential handoff | Not accepted; no credential send. | Preflight, NONE, potentially retryable. |
| H accepted, then reset/timeout or lost acknowledgment | Accepted if known; partial/all/unknown transmission and uncertain completion retained. | Uncertain, UNKNOWN, intervention. |
| Complete 401/403 after admitted credential handoff | Accepted local use; disclosure knowledge remains independent of peer parsing. Not a Secret-resolution failure. | Terminal rejected, NONE (no usable Model result). |
| Complete 429/503 | Preserve Secret use; no rollback. | Retryable rejected, NONE, potentially retryable. |
| Complete but invalid Model response | Preserve credential-use facts. | Rejected, NONE, terminal. |
| Cancelled caller with possible send | No inferred cessation or unused Secret. | Preserve UNKNOWN pending attributable outcome; do not invent existing cancellation settlement behavior. |

No automatic retry, resend, Approval refund or Secret "unuse". Model NONE never
means no credential disclosure or no provider-side work. Authoritative pre-use
denial remains denial; it is not laundered into a provider-response failure.

Only after both source and transport receive authorization may a future change
add `api_key: SecretRef | None = None` to `OpenAICompatibleSettings`. No field is
authorized now. It would store no material or environment locator and introduce
no second source selector. Its safe reference identity participates in
configuration revisions/equality/fingerprints without credential hashing.
Credential-free behavior and ModelPort remain unchanged.

The only future header is `Authorization: Bearer <material>`, for both chat and
embeddings under the same admitted binding with purpose checks per invocation.
No custom-header framework, redirects, proxy credentials or ambient auth.
Retain the versioned API-root paths and nonstreaming chat wire contract.

`ModelDeployment.LOCAL` remains mandatory. No REMOTE enablement or SEC-039
disclosure admission is implemented. Local addressing or a loopback tunnel to
KISSKI does not make remote processing LOCAL. KISSKI remains blocked.

## 10. Conditional offline qualification and next gate

No tests or provider calls were run for this documentation assessment. If a
concrete transport validity proof and the narrow invoking-owner scope are
accepted, the future implementation must supply a Python validator with a
repository-root operator command, using only fake local HTTP/TLS and synthetic
credential canaries. No real credential or external provider is permitted.

| Qualification area | Required evidence |
| --- | --- |
| S1 | Duplicate revision refusal; immutable copy/admission; source mutation bypass refusal; rotation/revocation/teardown; stale reference; wrong tenant/purpose/consumer/account/config; explicit fresh reprovisioning and no restart authority restoration. |
| Exact H | Deterministic barriers before acquisition, after acquisition/connect/TLS preparation, before H, between partial writes and during response wait. Test both orderings against Grant, Policy, Catalog, source and cancellation changes. |
| Timing/occupancy | Establish the admitted platform bound or equivalent atomic guard; inject expiry between check and H. Benchmarks, no-await code and passing race tests alone cannot establish that bound. Fail unsupported profiles closed. |
| Transport | Zero/partial/all/would-block/unknown progress; TLS WANT_READ/WANT_WRITE and buffered-flight cases; no unauthorized flush; reset, timeout, refused connection, complete 401/403/429/503 and truncated/lost replies. |
| Cancellation | Every §7 point, repeated caller cancellation, preparation worker finishing late, retained outcome ownership; no abandoned worker credential transmission. |
| Durability | Crash before final attempt commit, after commit/before H, after partial/full H before observation, after observation before Evidence receipt. Inspection/repair never resends; uncertainty and consumed claims survive. |
| Containment | Canary absent from public values, errors/causes, logs, reports, databases/journals and configuration fingerprints. Exercise echoed error/response content, audit/debug paths and ambient TLS key logging. Test failure output must not print headers. |
| Compatibility | No header without a reference, exact header with it, chat/embedding wire and error contracts, no redirects/proxies/fallback, no credentialed REMOTE construction. |

Future numeric acquisition/holding/network bounds, size limits and retention
coverage must be explicit and qualified before enablement; this assessment
invents no measured values. Strict currentness remains the acceptance criterion.

| REUSE / EXTEND / CREATE | Scope |
| --- | --- |
| REUSE | SecretRef and public Secret operations; participating owners/domain; Stage-A ledger semantics; separate Evidence receipts/repair; ModelPort, wire parsing and Model effect vocabulary. |
| EXTEND, conditional | Private source admission, local composition, optional reference setting and exact Model invoking-plane attempt/cancellation ownership; safe typed Evidence submissions. |
| CREATE, conditional | One private immutable provisioned source; only a proven private transport bridge and an Execution-owned attempt-store adapter if authorized. No generic credential/network framework or shared Configuration store. |

The next decision must resolve **actual check-to-handoff validity and bounded
occupancy for a concrete transport profile**, and approve its narrow durable
invoking-owner integration. If it needs wider governance, owner, Coordinator
or arbitration semantics, obtain separate maintainer authority before code.
Changing to a cloud store or HTTP library does not remove these obligations.

Only this document and one roadmap status/link line change. Stage A stays
locally qualified; the prior environment rejection stays in force. No code,
test, validator, ADR, credential, remote mode or commit is created here.

**SECRET-REF-1B STILL BLOCKED**
