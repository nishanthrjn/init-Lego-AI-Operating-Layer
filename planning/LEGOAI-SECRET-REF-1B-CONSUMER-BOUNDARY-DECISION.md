# SECRET-REF-1B consumer boundary decision

Date: 2026-10-07. Status: **architecture assessment ready; Stage-B implementation not authorized**.

Outcome: **ENVIRONMENT-BACKED SOURCE DOES NOT SATISFY ADR-010**.

This outcome rejects the ordinary mutable process-environment source previously
proposed for Stage B. It is not a proof that every separately constrained,
qualified environment realization is impossible. The current blocking HTTP path
also lacks a qualified credential-use boundary. Fixing the source alone would
not authorize Stage B. No ADR status or semantics change, and no new ADR is
allocated by this assessment.

## 1. Authority, inspected evidence and prerequisite

The accepted authorities are [ADR-010](../adrs/ADR-010.md) §§6–11 and 14–15,
[ADR-007](../adrs/ADR-007.md) §§5–8, [ADR-008](../adrs/ADR-008.md) §§7–11,
[ADR-009](../adrs/ADR-009.md) §§8–9, [ADR-014 §14](../adrs/ADR-014.md),
[CONTRACTS](../contracts/CONTRACTS.md) §15.5 and §§28–29, and
[SECURITY](../security/SECURITY.md), including SEC-020, SEC-039 and SEC-057–059.
This assessment applies those authorities rather than amending them.

Current records and source were inspected at repository HEAD `32d19ad`:

| Evidence | Relevant finding |
| --- | --- |
| [Accepted staged scope](LEGOAI-SECRET-REF-1-DECISION.md), [shared arbitration decision](LEGOAI-SECRET-REF-1A-ARBITRATION-DECISION.md), [Stage-A qualification](../docs/secret-ref-1a.md) | Stage A is locally qualified; Stage B requires a separately defensible consumer boundary. |
| [Durable custody decision](LEGOAI-SECRET-USE-DURABLE-CUSTODY-DECISION.md), [Secret ledger](../src/legoai/reference/_secret_ledger.py), [Evidence adapter](../src/legoai/reference/_durable_evidence.py) | The synthetic source transaction is the complete Stage-A effect. Separate Evidence receipt/repair does not repeat use. This is not an HTTP atomicity mechanism. |
| [Secret composition](../src/legoai/runtime/_composition/secret.py), [synthetic source](../src/legoai/reference/secret.py), [ordering domain](../src/legoai/reference/_secret_domain.py) | Acquisition precedes final guarded checks; synthetic acceptance and participating invalidators share the domain. The qualified ledger profile is owner-thread bound. |
| [OpenAI-compatible adapter](../src/legoai/reference/model_openai_compatible.py) | Chat/embedding call `asyncio.to_thread(self._post, ...)`. Blocking `urllib` request opening combines connection, transmission and response work; it exposes no protected credential-disclosure step. |
| [Settings](../src/legoai/runtime/api.py), [local host](../src/legoai/runtime/local.py), [Model selection](../src/legoai/runtime/_composition/model_selection.py), [governed Model calls](../src/legoai/runtime/_composition/model_governed.py), [execution](../src/legoai/reference/execution.py) | Settings are credential-free; REMOTE is refused. Invocation claim and Model error settlement do not implement a Secret-to-HTTP handoff. Awaiter cancellation is not proof that blocking transmission stopped. |

Accept the operator result for `uv run python .\validate_secret_ref_1.py`:
62/62 phases passed, including 69 focused Stage-A tests, invalidator ordering,
durable recovery, regressions, mypy, Ruff and diff integrity. Its scope remains
**synthetic owner-thread exact-use acceptance plus intact local storage**.
Environment material, headers, authenticated HTTP, remote providers and KISSKI
are not qualified. SecretRef, arbitration, the ledger, Evidence custody and
synthetic acceptance are not reopened here.

## 2. Material-source disposition

A future source mapping would belong to Secret Access: the SecretRef names the
admitted owner/tenant/source mapping and exact material revision. Only that
private mapping could contain an explicit environment-variable locator. Neither
the Model adapter nor Model settings may look up a variable, enumerate the
environment, load `.env`, or use an ambient fallback.

An ordinary environment entry supplies bytes, not an owner-issued revision or
an atomic relationship between bytes, revision, mapping and current validity.
A second variable containing a revision does not make the pair atomic. Rotation
must establish a new authoritative revision; an exact old revision must fail
unless explicitly still valid under an admitted overlap policy. It cannot
silently acquire replacement bytes under its old identity.

Python's environment mapping is cached; native environment changes need not
appear in it, and direct `putenv` does not update that mapping. Refreshing it is
not a thread-safe revision protocol. These are runtime constraints documented in
the [Python environment API](https://docs.python.org/3.14/library/os.html#os.environ).
Even repeated fresh reads cannot exclude change-and-restore mutations or a
mutation between the final read and use. A wrapper that cooperating callers
usually use does not enforce participation by every mutation path.

Consequently, ordinary process-environment mutation cannot be reliably detected
and ordered by the present Secret owner. Reject the profile at admission rather
than claiming that a missing-variable check or periodic comparison guarantees
currentness. A material hash is neither permitted persistence nor an ordering
solution. Provider rejection also does not prove that disclosure was authorized.

A replacement source proposal must establish authoritative exact revisions and
prevent bypass mutation by construction, or explicitly qualify an equivalent
ordering mechanism. A constrained immutable/provisioned process source would
need its own enforceable lifetime and rotation semantics; it is not approved by
renaming ordinary environment variables. No host-open snapshot or long-lived
material cache is authorized as a workaround. This decision does not select or
implement a replacement source.

## 3. Acquisition and private lifetime

For any subsequently qualified source, acquire just in time, after preliminary
current authorization for the exact requester, actor, tenant, purpose, attempt,
consumer/version, provider/account target and configuration revision. Acquisition
is preparation, not acceptance or permission to send.

Perform potentially waiting acquisition outside the shared ordering domain.
Bind its private result to the exact source revision and operation; then check
all current authority, source/mapping validity, time constraints and applicable
Approval/claim conditions at the protected-use boundary. Cancellation or
invalidation while acquisition is in flight makes its late result unusable.
Discard it without calling the consumer. If the source cannot substantiate
currentness at that boundary, deny use.

No material enters host-open state, public values, ModelPort, Agent/task input,
logs, Evidence, reports or persisted recovery records. Private material must
have finite operation-scoped lifetime, no reusable cache or session authority,
and logical disposal on every exit. Python string disposal is not physical
zeroization. A worker retaining material after its awaiter disappears must remain
owned and subject to invalidation; fire-and-forget retention is unacceptable.

## 4. HTTP boundary alternatives

ADR-010 §8.3 distinguishes bounded acceptance of responsibility from arbitrary
deferred use. If work waits before credential disclosure, the later protected
boundary needs current checks. Neither resolving material, constructing a header,
creating a socket nor scheduling a worker proves accepted HTTP Secret use.

| Option | Assessment |
| --- | --- |
| A — handoff to current transport | Reject as the use boundary. `_post` invocation or thread submission can precede DNS, connection and scheduling delays. Revocation can win before disclosure. An invocation claim is not a credential-use permit valid indefinitely. |
| B — first successful socket write | Not sufficient as specified. The first write can contain only an HTTP prefix; partial writes can split credentials. TLS and buffering add different local handoff boundaries. A successful local write does not prove remote receipt, authentication or a Model result. Blocking send cannot hold the ordering domain. |
| C — Secret-aware bounded synchronous acceptance primitive | A possible subject for a separate transport-boundary addendum, not an established capability. It must take responsibility for the exact operation and enforce currentness at actual credential-bearing handoff, including later protected writes. A bounded local start before a wait is insufficient by itself. |
| D — leave credentialed HTTP unsupported in the current adapter | Required present disposition. Credential-free behavior remains supported. Source currentness and a qualified transport primitive both need evidence before implementation authorization. |

The narrow candidate boundary is an admitted, bounded, nonwaiting local
credential-bearing transport handoff ordered against every relevant local
invalidator. Its contract must identify which bytes or private transport
ownership transfer constitute use. It cannot equate remote response completion
with local acceptance. No such boundary is exposed by today's `_post`.

DNS, connection preparation without credentials and response waits can conceptually
occur outside the domain. A future design still has to prove that handing off
credential-bearing bytes requires neither waiting nor arbitrary callbacks, and
that every subsequent protected subaction checks currentness. Merely setting a
socket timeout does not prove the bounded synchronous property. Python documents
that a failed `sendall` cannot report how many bytes were successfully sent;
see the [socket API](https://docs.python.org/3.14/library/socket.html#socket.socket.sendall).
Nonblocking writes also require a partial-write and backpressure proof; they are
not an approved shortcut or an implementation prescription here.

Never hold the domain across DNS/connect/send waits, thread/task submission,
subprocesses, remote I/O or arbitrary consumer callbacks. Do not move `_post`
inside the domain or move the Stage-A owner-thread ledger into its worker.
The accepted exception for one bounded local source-store commit is not a
network-I/O exception.

## 5. Revocation and cancellation ordering

Let P be preliminary authorization, A acquisition, H a future qualified local
consumer acceptance, W a credential-bearing handoff, and M an effective local
invalidation. H and W may coincide only if a qualified primitive proves that;
separate H must not confer permanent authority for W.

| Ordering | Required result |
| --- | --- |
| M before P, or before A completes | Deny; discard any late material; no credential handoff. |
| P → A → M → H/W (the requested T1–T4 race) | Final current check rejects; no Authorization transmission. |
| M races H/W | Participating transitions serialize in the shared domain; M winning denies, qualified use winning records that exact accepted fact. |
| H → M → W, with a wait after H | Preserve any truthful responsibility-acceptance fact, but reject W at its current check. H cannot bypass the intervening revocation. |
| W → M | Already handed-off bytes cannot be recalled. Retain use/effect truth; prohibit later protected writes, retries or reuse that lose current authorization. |
| Partial W → M → remaining writes | Do not transmit further protected material; preserve possible partial disclosure and uncertain provider outcome. |

Mapping/revision invalidation, expiry, Approval changes and cancellation must use
their authoritative participating owner paths. Independent issuer-side token
revocation has no proven atomic ordering with the local domain. Neither a local
lock nor a later 401 supplies that proof; unsupported source/provider currentness
claims must be refused.

Cancellation before H/W prevents use and disposes preparation. After H but
before W, cancel the still-pending protected action without erasing H or refunding
consumption; claim no transmission only with positive transport evidence.
After bytes may have been handed off, cancellation requests cessation but cannot
promise remote cessation. Preserve UNKNOWN where completion is ambiguous.

Cancelling an await of `asyncio.to_thread` is not evidence that the blocking
operation ended. The current governed Model call path has no Secret-specific
worker lifetime, cancellation gate or durable credential-handoff reconciliation.
A future bridge needs ownership of the in-flight worker, ordered cancellation
before disclosure, and outcome observation/attribution despite caller departure;
otherwise refuse that profile. Existing code is not claimed to synthesize the
required UNKNOWN settlement on every task cancellation.

## 6. Separate effect and custody truth

Keep local Secret responsibility/acceptance, credential transmission observations
and Model outcome distinct. Current Model `NONE` means no usable Model result;
it does not mean no credential disclosure or no provider-side work.

| Case | Secret/transport truth | Model disposition |
| --- | --- | --- |
| Qualified H accepted; definitely no HTTP send | Retain H if actually established; record no transmission only if proven. Stage-A synthetic acceptance alone cannot establish HTTP H. | NONE when the transport establishes no dispatch/result; classify the actual failure. |
| H accepted; request may have been sent | Retain H; transmission/completion uncertainty remains. If H itself is unobserved after failure, do not fabricate acceptance. | UNKNOWN; requires intervention. |
| Complete HTTP 401/403 | Provider rejection, not Secret-resolution failure. Credential use/disclosure is separate from lack of usable result. | `ModelResponseRejectedError`, NONE, TERMINAL. |
| Connection refused before send | Acquired material alone is not use. Preserve any separately proven H; no transmission when positively established. | `ModelPreflightError`, NONE, POTENTIALLY_RETRYABLE. |
| Timeout/reset after possible send | Preserve accepted use if known and uncertain transmission/provider completion. | `ModelResponseUncertainError`, UNKNOWN, REQUIRES_INTERVENTION. |
| Caller cancelled; worker continues | No inferred cessation, no inferred unused Secret, no authority for later unguarded disclosure. Keep the attempt attributable until observation or explicit uncertainty. | Do not claim NONE from cancellation alone; unresolved possible send remains UNKNOWN. |

Retryability labels authorize no automatic retry. Do not refund Approval, clear
uniqueness or "unuse" a Secret because the Model failed. A full provider reply
does not retroactively repair unauthorized disclosure.

The Stage-A transaction can atomically commit its own synthetic effect,
uniqueness and attribution duty. It cannot atomically commit independent HTTP
and SQLite effects. ADR-007/009 require durable invoking-plane attempt identity
and outstanding attribution duty before external handoff. Such preparation is
not a sent/accepted fact. A crash between possible HTTP handoff and observation
must remain unknown, with investigation/repair that never resends protected use.

Any future addendum must name the owner and safe durable records for this new
external attempt and its observations before authorizing implementation. Reuse
separate Evidence custody and durable receipts; never relabel the existing
synthetic ledger transition as HTTP success. No ledger redesign, global journal,
distributed transaction or persistence of material, handles, callbacks or
material-derived fingerprints is approved here. Restart remains inspection and
repair, not restored authority, Approval counts, handles or execution resume.

## 7. Future configuration and credential scope

Subject to both blockers being resolved, the narrow additive setting is
`api_key: SecretRef | None = None` on `OpenAICompatibleSettings`. It stores only
the reference; absent means the existing credential-free local path. ModelPort
and Model request types stay unchanged. No environment locator, raw token or
second resolver/provider-profile selector belongs in this field.

SecretRef remains the sole Secret source identity; its admitted mapping is
resolved behind Secret Access. The existing Model binding/configuration still
identifies the consumer and provider target; that is not another Secret source
identity. Admission must bind these identities rather than accept arbitrary
reference substitution.

The reference's safe identity, mapping and exact revision must participate in
configuration revision/equality and any canonical configuration fingerprint,
without material or its digest. The current host consumes supplied configuration
revisions; this is not a claim that it already generates a new credential-aware
fingerprint. A future extension must reject stale associations and test that
reference changes require the appropriate new configuration identity.

Only `Authorization: Bearer <material>` is proposed, privately constructed for
the admitted chat/embedding operation. No arbitrary-header framework, fallback
credential mechanism, redirect forwarding or ambient proxy credential behavior.
Acquisition and header validation must fail closed without exposing material in
exceptions; malformed header material must never reach transmission. Response
and diagnostic handling must be qualified against canary disclosure, including
provider error echoes. An assertion that settings are reference-only is not a
proof that all error and result paths are safe.

## 8. Future qualification plan, not executed

Use process-local fake HTTP and deterministic transport controls only, with
synthetic canaries and no real credential, external endpoint or Docker. A fake
server proves receipt behavior, not atomic ordering; separately instrument the
qualified transport acceptance boundary. Use barriers rather than timing sleeps.

| Area | Required evidence before Stage-B qualification |
| --- | --- |
| Header and compatibility | Exactly one expected Bearer header when configured; absent otherwise; both chat and embeddings; existing URL/version-prefix and nonstreaming behavior retained. No ambient fallback, redirects or arbitrary headers. |
| Exact authority | Wrong reference, purpose, consumer/version, tenant, provider/account target or configuration prevents handoff. Check final authority after slow preparation and any applicable consumption. |
| Races | Pause before/during acquisition, before H, between H and W, and after partial W. Invalidation/cancellation winning before W prevents it; prior irreversible handoff remains truthfully attributed. |
| Cancellation ownership | Cancel awaiter before submission, while worker waits and after possible send. Prove no abandoned worker can later bypass currentness; capture eventual outcome or durable uncertainty without claiming forced thread termination. |
| Effects and custody | Complete 401/403, refused connection, reset, timeout, truncated response, lost response/receipt and crashes around attempt/handoff/observation. Separate Secret facts from Model effects; recovery and Evidence repair never replay use. |
| Containment | Canary absent from public values, exceptions/causes, logs, reports, Evidence and source persistence. Exercise echoed error bodies and malformed responses; define safe handling of returned content rather than assuming the provider never echoes material. Test helpers must not print header values on failure. |
| Bounds | Prove the permitted synchronous primitive has no network wait, task submission or arbitrary callback under the domain. Server success or a timeout setting is not this proof. |

The ordinary environment profile is rejected, so no environment test pass is
claimed. If a new constrained source is proposed, its separate qualification
must cover explicit mapping, missing/changed values, exact revision mismatch,
rotation, mapping invalidation, direct/native mutation and change-and-restore
attempts. It must demonstrate enforced refusal of unsupported mutation, not
merely demonstrate cooperative setter behavior.

That plan must also cover process inheritance and child-process leakage
assumptions, restart without restoring authority or material handles, no ambient
fallback, no `.env`, no enumeration, no logging and no material fingerprint.
Environment inheritance is not a rotation protocol. No OS-level mutation
atomicity is established by this assessment.

## 9. REUSE / EXTEND / CREATE and authorization gate

These are conditional future directions, not approval to change code.

| Disposition | Element | Boundary |
| --- | --- | --- |
| REUSE | Qualified SecretRef/public contracts | Reference-only identity and exact-use authority unchanged. |
| REUSE | Shared ordering domain and participating invalidators | No broader lock authority or network-wait exception. |
| REUSE | Durable Secret ledger and separate Evidence custody | Preserve qualified synthetic semantics and receipt/repair mechanisms; they do not prove HTTP atomicity. |
| REUSE | OpenAI-compatible adapter and Model effect vocabulary | Preserve credential-free behavior, wire contract and established error meanings; its current dispatch is not a qualified credential bridge. |
| EXTEND | OpenAICompatibleSettings | Optional reference only, with safe configuration identity, after authorization. |
| EXTEND | Local host composition and provider call path | Admit the exact source/consumer binding and own guarded acquisition, handoff and cancellation; no new public material path. |
| CREATE | Minimum admitted material-source realization | Requires a defensible exact-revision/currentness proposal replacing the rejected ordinary environment profile. |
| CREATE | Minimum protected consumer/transport bridge | Requires proof of bounded actual-use ordering and separately owned external-attempt attribution. No generic credential framework. |

Stage-B implementation remains blocked by both source currentness and actual
HTTP-use ordering. A subsequent maintainer decision must approve a concrete
source profile and transport-boundary contract, including cancellation and
durable attempt ownership, before implementation. If that requires broader
owner, Coordinator, governance, execution or arbitration redesign, stop for its
separate authorization. Stage A remains locally qualified and unchanged.

Even a later successful Stage B is **credential-free or credentialed LOCAL
deployment only**, with operator-controlled processing as required by ADR-014.
A loopback tunnel to a remote provider is still REMOTE. A credential is not
disclosure admission. REMOTE-MODEL-DISCLOSURE-1/SEC-039 and KISSKI qualification
remain separately gated; G03 is not closed and Secrets are not broadly qualified.

No source, tests, validator, ADR or runtime behavior is changed by this record.
No provider was exercised. The only roadmap change is a link/status line.

**ENVIRONMENT-BACKED SOURCE DOES NOT SATISFY ADR-010**
