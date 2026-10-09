# Configuration-selected Model composition proof

This is the first narrow reference implementation of configuration-driven
composition, not a complete application manifest/runtime product. See
[ADR-019](../adrs/ADR-019.md).

## Development direction

Build minimum stable primitives, prove an end-to-end runtime slice through a real
consumer, then generalize from repeated evidence. Accepted canonical documents
and ADRs remain authoritative. The assessment app exposed a platform gap; its
dotenv convenience and dependency-free export are not proof of governed platform
composition. This increment adds the private reusable mechanism and an executable
offline consumer proof; migrating the assessment HTTP composition is separate.

Next use Career Inbox Assistant to drive actual Email/Gmail and Notification/
Telegram needs; Job Discovery and then ForgeAI provide broader consumers.
Do not prebuild those adapters now. Apply the Rule of Two except where accepted
foundational invariants already justify a mechanism. Prefer deterministic logic,
then one model invocation, before workflows or autonomous Agents. Additional
Agents require distinct responsibility, context, authority, lifecycle and evaluation.

## Input and ownership

A host captures input, for example:

    {"revision": "composition-1", "binding": "offline"}

Changing binding to ollama selects the other known compatible contribution in
the offline proof. These labels are local operator bindings, not global provider
names. The host supplies the expected owner-issued ConfigurationRevisionRef;
input cannot publish a revision or select another tenant by changing a string.

Inside Core composition, use capture_model_selection, then compose_model in the private
legoai.runtime._composition.model_selection module. Pass an explicit
CapabilityRequirement, trusted contribution tuple, Catalog and evaluation time.
The resulting route and configured association feed existing invoke_routed_chat
after the normal authorization and coordinator path. Construction grants no
permission to invoke.

Each contribution pins the full CatalogEntry, ModelBinding, configuration
revision and Plugin lifecycle record. The Catalog remains the admitted published
candidate source. Explicit selection can choose among compatible candidates but
does not erase ambiguity from the retained resolver result. Failed selection
does not call a constructor or another provider.

Environment/.env are optional host input mechanisms only. They must be captured
and validated into explicit values; semantic modules do not read them implicitly.
No database/service or generic precedence/merge language is added. Configuration
cannot import a Python class, install a Plugin, provide admission, or issue
authority. Known host constructors are executable code supplied by the operator,
not data. Raw Secret values are not supported in this input.

## Verification

Run from the repository root:

    uv run --locked --no-sync python -m pytest -q tests/integration/composition/test_model_selection.py tests/integration/composition/test_model_governed.py tests/unit/reference/test_model.py tests/unit/reference/test_model_foundation.py tests/architecture/test_import_boundaries.py
    uv run --locked --no-sync python -m mypy src tests examples/model_routing.py

| Requirement | Evidence / limit |
|---|---|
| Same consumer, changed binding | FixedModel and actual Ollama adapter with mocked transport; exact provider identity and classification JSON asserted |
| Unknown binding | Explicit unknown-binding failure before construction |
| Unavailable/unpublished contribution | Exact entry absent from Catalog fails before construction |
| Incompatible provider | Capability version mismatch rejected, regardless of ModelPort shape |
| Invalid data / executable configuration | Closed fields, types, bounds and duplicates rejected; import/class/tenant/admission/Secret fields rejected |
| Unadmitted Plugin | Validation alone and non-active admission cannot publish Catalog contributions |
| Cancellation | Cancellation propagates, claims are not replayed; provider cessation is not claimed |
| Disabled Plugin | Non-active lifecycle rejected even if a stale Catalog entry remains |
| Missing dependency | Constructor ImportError becomes explicit missing-dependency failure; no fallback |
| Initialization failure | Explicit failure, safe category and preserved restricted cause |
| Invocation failure | Actual mocked transport refusal/timeout retain existing NONE/UNKNOWN mapping and single invocation |
| Stale configuration | Full expected revision association checked; mismatches fail without latest substitution |
| Restart pin | Two fresh processes reconstruct the same exact selection; different expected revision rejected |
| Secret reference missing | Not applicable to the two credential-free fixtures; authenticated providers unsupported, not silently satisfied |
| Error/timeout/resource/evidence contract | Existing Model/governed tests retained; no new budget, transport or evidence guarantees |
| Behavioral evaluation | Deterministic classification/schema regression only; live quality, tool behavior, latency and cost qualification still required |

Ollama response buffering and worker cancellation limitations remain as documented
in [ports and adapters](ports-and-adapters.md). Cancellation does not prove that
the provider stopped. No retries, fallback, generation limits, generalized tool
support or live-reload mechanism is introduced.

Only trusted in-process wiring is covered. Lifecycle values and Catalog facts
are not cryptographic attestations against hostile Python code. The host must
manage current records/withdrawal. Restart proof is configuration reconstruction,
not durable in-flight recovery or revival of an old authorization.

## Follow-up acceptance gates

Before claiming production substitution, use executable real-consumer evaluations
for quality, hallucination, structured outputs, requested tool behavior, latency,
usage/cost and regressions, alongside adapter contracts and security negatives.
Reject unsupported required capabilities explicitly. Retain provider-specific
extensions behind declared contracts instead of weakening the common interface.
Implement Secret-reference access only with explicit purpose/consumer/tenant and
current authorization. Configuration grants none of these.

No new foundational abstraction or configuration storage service follows from
this proof. Expand only when the next real consumer supplies concrete evidence.

Local validation: the focused composition/Model/architecture suite passed 333 tests.
This is scoped offline evidence, not full-platform or live-provider qualification.

## OPENAI-COMPATIBLE-MODEL-1 (ADR-014 §14)

Implemented; **LOCALLY QUALIFIED** by operator validation. Applications use only
`legoai.runtime.api` and, at their composition root, `open_local_host` from
`legoai.runtime.local`. Domain code receives `GovernedHost` and owner contracts.
The closed provider union is `OllamaSettings | OpenAICompatibleSettings |
TrustedModelContribution`. Trusted contributions remain supported; no import
strings, registry, fallback, automatic retry or per-call routing is introduced.

`OpenAICompatibleSettings` is frozen/slotted and requires these explicit fields:
`base_url`, `chat_model`, `embedding_model`, `timeout_seconds`,
`max_output_tokens`, `provider_id`, and `deployment`. Optional values are expressed
as `None`. `ModelDeployment` has LOCAL and REMOTE; REMOTE fails at open with
`HostFailure.UNSUPPORTED_COMPOSITION` before admission or adapter construction.
*(Amended by OPENAI-COMPATIBLE-REMOTE-1, below: the optional
`bearer_credential` field and the one credentialed REMOTE profile; every other
REMOTE configuration is still refused this way.)*
LOCAL is an operator attestation about processing location, never inferred from
the URL. A loopback tunnel to a remote service is REMOTE and unsupported.

The API root includes its version prefix: `http://127.0.0.1:8000/v1` becomes
`http://127.0.0.1:8000/v1/chat/completions`, never `/v1/v1/chat/completions`.
Chat sends only `model`, plain-text `messages`, `stream: false`, and `max_tokens`
when configured. `max_output_tokens` accepts an exact integer in 1..2**31-1,
or None (omitted); the representation bound is not provider capacity or a cost
budget. Models use the existing 1..256-character identity bound, with blank,
control-character and non-UTF-8 names rejected. Timeouts must be positive and
finite. Full semantic settings validation happens at host open; Python type
errors are rejected at value construction, consistent with Ollama settings.

Chat requires exactly one choice, an assistant message with string content,
the exact configured response model, and `finish_reason == "stop"`. `length`,
missing/other finish reasons, tools, malformed success and streaming are rejected.
Usage counts are optional nonnegative integers; missing/invalid counts remain
unknown, never fabricated zeros. No alias resolution is performed.

Embeddings are available only when `embedding_model` is configured. The request
is `POST {base_url}/embeddings` with `model` and `input`. Response model must match
exactly; count and ordered indexes must match inputs; vectors must have consistent
positive dimensions and finite numeric components. Empty input/result has the
existing dimension 0 contract. With no embedding model, the host publishes only
CHAT and refuses EMBEDDING with PURPOSE_UNAVAILABLE before dispatch.

| Observation | Governed effect / recoverability |
| --- | --- |
| Connection refused or DNS failure before send | NONE / POTENTIALLY_RETRYABLE |
| Timeout, reset, incomplete body (including an error body) | UNKNOWN / REQUIRES_INTERVENTION |
| Complete 429 or 503 | NONE / POTENTIALLY_RETRYABLE |
| Other non-2xx, malformed success, wrong identity, invalid vectors or finish reason | NONE / TERMINAL |

`ModelResponseRetryableRejectedError` subclasses `ModelResponseRejectedError`;
composition classifies it before its terminal base class, for both chat and
embedding. No status causes retry or fallback. Redirects are rejected and ambient
proxies are disabled. No Authorization header, credential fields, environment
secret lookup, new dependency or provider SDK is used. Constructor/host open
perform no HTTP; only chat/embed perform I/O.

Offline conformance rows A-C use the same governed application with a FixedModel
contribution, Ollama over mocked HTTP, and OpenAI-compatible over a process-local
stdlib server. They test contracts and effects, not output-quality equivalence.
The Ollama protocol and configured-identity behavior remain unchanged; capability
IDs/version are shared neutral helpers, with separate provider plugin identities.

Locally qualified scope: credential-free LOCAL OpenAI-compatible endpoints. Remote,
credentials, KISSKI hosted, authenticated vLLM, cloud APIs, automatic routing,
retries and VTO remain unsupported. The existing blocking-to-thread cancellation
and complete-response buffering limitations remain; cancellation does not prove
provider cessation. No live endpoint is qualified by these tests. The next
separately authorized slice is SECRET-REF-1;
REMOTE-MODEL-DISCLOSURE-1 is also required before remote use.

Run from the repository root using installed project environments:

```powershell
uv run python .\validate_openai_compatible_model_1.py
```

The validator has 52 phases: scope and accepted ADR; public settings and closed
union; deployment/credential controls; neutral offers; private adapter and stdlib
boundaries; inert construction; chat wire, identity, usage and truncation;
HTTP/effect matrix; embeddings and purposes; no retry/fallback; conformance A-C;
runtime/Model/Agent/DocuMind/ForgeAI regressions; mypy, Ruff and diff checks.
It makes no provider connection beyond the process-local scripted server.

Implementation verification (2026-10-07): the offline 52-phase validator run
passed, including 88 runtime, 100 Model, 53 Agent, 16 DocuMind and 89 ForgeAI
regressions. Final focused verification passed all 161 new tests after tightening
malformed-JSON diagnostic isolation and identity/construction tests. Operator
qualification is now **LOCALLY QUALIFIED**: running
`uv run python .\validate_openai_compatible_model_1.py` from the repository root
passed **52/52 validator phases**, including conformance rows A–C. The 161 focused
tests had already passed during implementation verification. Qualification is
offline/process-local contract and conformance evidence only. No external or live
provider was contacted, no Docker was invoked, and no remote endpoint or
credentialed provider was used. No live model quality was measured or live
output-quality equivalence established; remote/credential support remains absent.

## Remote disclosure configuration (ADR-024; governance only)

REMOTE-DISCLOSURE-GOVERNANCE-1 adds the values that ADR-024 decided, in
`legoai.governance.disclosure`:
- the closed provenance vocabulary `model-disclosure/1` (`SYNTHETIC`,
  `PLATFORM_INSTRUCTION`, `TASK_TEXT`, `REPOSITORY_CONTENT`,
  `DERIVED_DIAGNOSTIC`; an empty declaration is UNCLASSIFIED);
- a fact basis (`VERIFIED` is reserved for LegoAI's own mechanical checks and
  is never declarable; `PROVIDER_DECLARED` needs a source reference);
- versioned processor declarations, operator disclosure admissions and an
  opaque operator-declared `RepositoryIdentity`;
- one pure evaluator, `evaluate_disclosure`, with a closed refusal taxonomy.

`LocalHostConfig` gains an optional `disclosure: RemoteDisclosureConfig | None`
(default `None`, so existing configurations are unchanged). At host open the
configuration is checked for consistency only. Each admission must pin an
existing exact declaration revision, and name only existing REMOTE-declared
OpenAI-compatible bindings whose provider, https endpoint, API root and served
models match. Inconsistency fails with `INVALID_CONFIGURATION`; duplicates fail
with `CONTRIBUTION_CONFLICT`.

**This enables nothing.** REMOTE bindings are still refused at open with
`UNSUPPORTED_COMPOSITION`, however complete the disclosure configuration. No
invocation-time gate, declaration carrier or disclosure evidence existed in
that slice; REMOTE-DISCLOSURE-GATE-1 adds them (below). No provider is contacted.
ModelPort, `ChatRequest`, `EmbeddingRequest` and `AgentRequest` are unchanged.
Remote providers, credentials and KISSKI remain unsupported.

```powershell
uv run python .\validate_remote_disclosure_governance_1.py
```

Operator qualification (2026-10-09): **LOCALLY QUALIFIED**. That command passed
**20/20 phases** offline on commit `19d0e39`. That includes 95 focused
governance tests, 24 host-open tests, the REMOTE-still-refused regression, and
Core (1760), DocuMind (16) and ForgeAI (89) regressions. Qualification covers
the governance values, the pure evaluator and host-open validation only. No
provider, network or credential was used. REMOTE remains refused, and no
invocation-time gate exists.

## Invocation-time disclosure gate (REMOTE-DISCLOSURE-GATE-1)

**Carrier.** A composition declares what one model execution will disclose
when it mints it:

```python
host.model_execution(
    ModelPurpose.CHAT,
    disclosure=ExecutionDisclosure(
        "forgeai", DisclosureDeclaration(classes, repository)
    ),
)
```

The host stores the declaration privately against that exact `ExecutionId`. It
is immutable; different classes need a different execution. It never enters
`ChatRequest`, `EmbeddingRequest`, `AgentRequest`, ModelPort or the provider
wire. Model output, content and responses cannot assign or widen it.

**Gate.** For a REMOTE binding only, the governed Model path (chat, embedding
and the Agent runtime alike) evaluates `evaluate_disclosure` after claiming
the invocation and **before** the adapter. It uses the host's configured
admissions and declarations and the current time. A missing declaration is
UNCLASSIFIED.
- **Refusal:** no provider work. The execution settles FAILED, effect `NONE`,
  `PolicyViolation`/`TERMINAL`. Its single `ErrorCause` names the disclosure
  Evidence record, never the reason text, the prompt or the provider terms.
- **Admission:** the call proceeds unchanged. The exact request object is
  sent, with no redaction or rewrite.

**Evidence.** Each gated invocation records a typed `DisclosureObservation`
through the existing `EvidenceCustodyPort` (ADR-009), under id
`disclosure-<execution id>`. It holds only identities, classes, the repository
identity when one applies, the disposition and the disclosure effect: `NONE`
for refusals and preflight failures; `COMPLETED` for complete replies,
including rejections; `UNKNOWN` for uncertain outcomes and cancellation. It
never holds prompts, repository text, responses, credentials or headers. The
gate records Evidence but never reads it back: Evidence is not admission. A
custody failure propagates after the execution has settled truthfully.

**LOCAL is unchanged and REMOTE is still refused.** The public host installs no
gate, because REMOTE bindings are refused at open with `UNSUPPORTED_COMPOSITION`.
*(Since OPENAI-COMPATIBLE-REMOTE-1 the host installs this gate for an admitted
credentialed REMOTE binding only; see the last section.)*
LOCAL calls never consult disclosure policy, and declarations are ignored for
them. The gate is exercised through a bounded internal test seam, never a real
remote provider. No credential, KISSKI or external provider is involved.
ForgeAI is not remote-enabled.

```powershell
uv run python .\validate_remote_disclosure_gate_1.py
```

Operator qualification (2026-10-09): **LOCALLY QUALIFIED**. That command passed
**20/20 phases** offline on commit `8e607f2`. That includes 39 gate tests (the
refusal matrix with zero-transport proof, no-widening checks, Evidence,
cancellation, and LOCAL/REMOTE checks), and Core (1801), DocuMind (16) and ForgeAI
(89) regressions. Qualification covers the carrier, the invocation-time gate
and the disclosure Evidence through an internal test seam only. REMOTE is still
refused at open; no credential, provider, network or KISSKI was involved; and
ForgeAI is not remote-enabled.

## Remote attempt custody (REMOTE-ATTEMPT-CUSTODY-1)

The Model invocation plane owns a narrow durable record of responsibility for
each exact prospective remote Model invocation (ADR-007 §6.2, ADR-023 §9). The
private store is `legoai.reference._remote_attempts`, reached only through
`runtime/_composition/remote_attempt.py`.

**When an attempt exists.** `prepare_attempt` builds a `RemoteAttempt` only
from an **admitted** disclosure decision of the gate bound to that execution.
The attempt binds:
- the execution and operation, and the configuration revision;
- the admission id and revision, and the declaration id and revision;
- the binding, provider, endpoint origin and API root, model and capability;
- the credential's `SecretRevisionRef`, or `None` for a future credential-free
  provider;
- the creation time.

It never holds a prompt, repository content, a response, credential material
or a header. Preparing an attempt never realizes the Secret.

**INTENDED before any handoff.** `intend` durably commits `INTENDED` and
returns an `IntendedReceipt`. A future transport must call
`claim_for_handoff(receipt)`, which works once, only for that incarnation's
durable, still-INTENDED attempt. A failed or uncertain commit yields no
receipt, so no send is possible. Duplicate attempt or execution identities
are refused, never overwritten.

**Outcomes.** Exactly one terminal category: `NOT_SENT`, `PROVIDER_REJECTED`,
`COMPLETED` or `UNKNOWN`. Each must be justified by ADR-023 §9 observations:
- `NOT_SENT` needs positive proof. Before handoff that is refusal,
  cancellation or a zero-byte send; after handoff, only the transport's own
  zero-byte proof.
- A provider outcome needs a complete response.
- Absence of evidence never becomes success or no-effect. `UNKNOWN` is always
  truthful.

No transition leaves a terminal state.

**Recovery never resends.** Read-only inspection lists attempts still
`INTENDED`, reported effectively as `UNKNOWN`. A later writer incarnation may
only reconcile them to `UNKNOWN`. It cannot claim them or settle them any
other way. Nothing calls a provider, a transport or Secret realization.
Corrupt or inconsistent rows fail closed. Capacity is bounded (4096 attempts)
and refuses new work rather than deleting anything.

**Separate owners.** Disclosure Evidence (`DisclosureObservation`) records the
information flow. The attempt store records external-effect responsibility.
Neither authorizes the other, and neither authorizes Secret use. The store
reuses the qualified intact-local-storage SQLite custody mechanics; no
further durability is claimed.

LOCAL invocations create no attempt rows. REMOTE is still refused at open, and
there is no transport, Authorization header, KISSKI support or provider call.

```powershell
uv run python .\validate_remote_attempt_custody_1.py
```

**REMOTE-ATTEMPT-CUSTODY-1 LOCALLY QUALIFIED** (2026-10-09). The operator's run of
that command passed **20/20 phases** offline on commit `c0cb4e3`. That includes 41
attempt-custody tests (with real process-death windows A-D), 7 invocation-plane
tests, ownership and import boundaries (254), disclosure, S1 and Secret (281) and
durable-custody (59) regressions, and Core (1889), DocuMind (16) and ForgeAI (89)
regressions. Qualification covers durable, content-minimized INTENDED custody for
one exact intended remote attempt before any future credential-bearing handoff,
with no resend on recovery and UNKNOWN for unresolved attempts. There is no
transport, no REMOTE support, no Bearer authentication, no KISSKI support and no
live remote-effect qualification.

## Credential-bearing HTTPS transport (CREDENTIAL-HTTPS-T2)

A private SRCP-1 transport (`legoai.reference._credential_https`), driven only
by the invocation plane's `runtime/_composition/credential_https.exchange`. It
is not a ModelPort, a public HTTP client or a provider client.

**Order.**
1. Recipient binding: the target's https origin and API root must equal the
   attempt's. The Secret revision and use id must equal the attempt's.
2. DNS and TCP connect, then a TLS handshake with certificate and hostname
   verification, over `ssl.SSLObject` and `MemoryBIO`. No credential exists
   yet.
3. `claim_for_handoff` on the durable INTENDED receipt, once.
4. The Secret owner's `_handoff`. In one ordering-domain occupancy: final
   currentness (with the SRCP-1 validity margin), durable Secret-use
   acceptance, encryption of the single request into the outgoing BIO, and
   **one nonblocking `send`**.
5. Each continuation waits for writability **outside** the domain, re-enters,
   rechecks currentness and makes one more nonblocking send. If an
   invalidation wins, nothing further is sent.
6. A bounded response read, outside the domain.
7. The plane maps the observation to custody:
   - zero credential bytes → `NOT_SENT`;
   - partial or uncertain → `UNKNOWN`;
   - all bytes without a complete response → `UNKNOWN`;
   - complete 2xx → `COMPLETED`;
   - any other complete status → `PROVIDER_REJECTED`.

   The Secret use is then attributed (same id as the attempt).

**Request.** `POST` to the exact API-root path, with only `Host`,
`Content-Type`, `Accept`, `Authorization: Bearer <material>`, `Content-Length`
and `Connection: close`. One connection per attempt. There are no redirects,
proxies, cookies, compression, chunking, pooling or retries. The response must
use `Content-Length` framing, with bounded headers (64) and body (4 MiB);
malformed, chunked, oversized or truncated responses are incomplete. A single
monotonic deadline bounds connect, TLS, send readiness and the response.
Cancellation never retracts accepted bytes.

**Guarantee scope.** Local event currentness is strictly ordered before every
credential-bearing write. Wall-clock expiry is enforced by the margin at each
gate, and a handoff observed after expiry is recorded
(`TIME_VALIDITY_VIOLATION`) but **not prevented**. Provider-side revocation
is not ordered. Material lives only in the protected scope: the plaintext
request buffer is overwritten after encryption (best effort, no zeroization
claim).

The TLS context is built explicitly: system trust store, or an explicit test
anchor; verification mandatory; TLS ≥ 1.2; key logging disabled. No proxy,
CA-bundle, key-log or API-key environment variable is read. Qualification
uses only a process-local synthetic TLS server with test-only certificates.

REMOTE is still refused at open, and nothing here is wired into
`OpenAICompatibleSettings` or the public host. There is no KISSKI support and
no external provider call.

```powershell
uv run python .\validate_credential_https_t2.py
```

**CREDENTIAL-HTTPS-T2 LOCALLY QUALIFIED** (2026-10-09). The operator's run of
that command passed **20/20 phases** offline on commit `862767b`. That includes 59
T2 tests (transport, end-to-end exchange, adversarial and architecture),
ownership and import boundaries (270), attempt custody, S1, disclosure and
Secret (317), durable custody, OpenAI-compatible LOCAL and Ollama (227), and Core
(1944), DocuMind (16) and ForgeAI (89) regressions. Qualification covers the
SRCP-1 private credential-bearing HTTPS transport: TLS is established before
Secret realization, each credential-bearing nonblocking handoff is
currentness-gated under the shared ordering domain, durable INTENDED custody
precedes handoff, and bounded observations preserve NONE/UNKNOWN/completed
effect truth without retry or fallback. Synthetic local TLS only. There is no
REMOTE provider support, no OpenAI-compatible REMOTE, no KISSKI or ForgeAI
remote support, no production credential management, no strict wall-clock
atomic expiry and no provider-side revocation ordering.

## Credentialed REMOTE OpenAI-compatible binding (OPENAI-COMPATIBLE-REMOTE-1)

**Status: LOCALLY QUALIFIED (2026-10-09; commit `f411fc4`), within the scope
recorded at the end of this section.** This joins the qualified disclosure, Secret, attempt-custody
and T2 mechanisms behind the existing provider-neutral OpenAI-compatible
binding. There is no new ModelPort, adapter, Secret system, disclosure system
or attempt store, and no provider-specific code.

**Supported profile (the only one).** A single operator on a trusted local
host, an OpenAI-compatible endpoint over verified HTTPS, a Bearer credential
from S1 under SRCP-1, an explicit disclosure admission, one request per
invocation, no retry or fallback, attended use. Hosted, multi-tenant,
unattended and production-SaaS use are not supported.

**Configuration.** `OpenAICompatibleSettings.bearer_credential: SecretRef |
None = None` (ADR-014 §14.18) holds a reference only; there is no `api_key`,
token or header field and no environment or CLI source. The operator obtains
the `SecretRef` from `open_credential_source(scope).provision(identity)`, which
reads the credential through hidden interactive input inside the source. The
trusted runtime participants are passed separately from configuration data:
`open_local_host(config, selection, clock=..., remote=RemoteModelRuntime(
credentials, custody, validity_margin, trust_anchor=None))`. `custody` is a
local directory for the attempt store and the Secret-use ledger.
`validity_margin` is the SRCP-1 margin, between 0 and 1 hour. An explicit
`trust_anchor` replaces the system trust store; it never disables
verification. A Grant with action `secret-use` on the credential identity must
be configured.

**Host open.** The selected REMOTE binding opens only when it is an
OpenAI-compatible binding admitted by the disclosure configuration, with an
https endpoint matching the admission and declaration, a `bearer_credential`
of the S1 class with the REMOTE Model purpose issued by this host's credential
source and still current, the `secret-use` Grant, and `RemoteModelRuntime`.
Failures:

- a missing admission, credential or participants, or an unsupported
  credential class or source: `UNSUPPORTED_COMPOSITION`;
- a provider, endpoint, http or model mismatch, a wrong purpose, a missing
  Grant or a missing custody directory or anchor: `INVALID_CONFIGURATION`;
- a retired or unknown revision: `STALE_CONFIGURATION`.

Credentialed LOCAL is `UNSUPPORTED_COMPOSITION`. Opening reads the trust store
and opens SQLite custody; it performs no DNS, connection, TLS, Secret
realization or request. Admission authorizes no request.

**Per invocation**, after the governed path claims the invocation, each step
is a separate check:

1. The disclosure gate must ADMIT, with the execution's trusted
   `ExecutionDisclosure` mandatory for REMOTE. A refusal reaches no attempt,
   Secret use or network.
2. The credential association (binding, provider, https origin, API root,
   revision) must equal the admitted processor, the attempt and the TLS target.
3. One exact `RemoteAttempt` (model of this purpose, capability, revisions,
   credential revision) is committed INTENDED. If the commit fails, nothing
   else happens.
4. A new exact Secret use is composed for this invocation: its own plan,
   `use_id` = the attempt id, Grant, expiry (Grant expiry and deadline, at
   most one day) and attribution. Current Secret authority is checked before
   any connection.
5. T2 runs: verified TLS, a single-use claim, the final check with the margin
   inside the ordering domain, gated writes, and a bounded response.
6. The attempt is settled from the observation, and Secret-use attribution
   is recorded only if the credential was actually handed off.
7. The adapter's own status mapping and parser classify the complete response.

The per-invocation Secret-use factory (`_SecretUses`) takes the ledger
incarnation's single Stage-A binding once and admits each use id once. The
credential revision is reused; a protected use never is.

| Observation | Attempt | Governed effect / recoverability |
| --- | --- | --- |
| Refused before the handoff claim (association, custody, Secret, TLS, connect, timeout before send) | none or NOT_SENT | NONE / POTENTIALLY_RETRYABLE |
| Partial send, or full send without a complete response | UNKNOWN | UNKNOWN / REQUIRES_INTERVENTION |
| Complete 429 or 503 | PROVIDER_REJECTED | NONE / POTENTIALLY_RETRYABLE |
| Complete 401, 403, 404, other non-2xx or 3xx | PROVIDER_REJECTED | NONE / TERMINAL |
| Complete 2xx rejected by the parser (malformed, wrong model, finish reason, shape) | COMPLETED | NONE / TERMINAL |
| Complete valid 2xx | COMPLETED | COMPLETED |

A REMOTE timeout before any byte is sent is NONE, which is more precise than
LOCAL, because T2 proves that zero bytes were sent. Protocol rejection never
rewrites the attempt's transport truth. Nothing is retried, resent or routed
elsewhere, and error bodies are never decoded or retained. Disclosure
Evidence records the observed effect.

**Limits.** The exchange runs on the host's confined thread, because the
owner-local SQLite custody and the Secret owner are thread-confined. It
blocks that event loop for at most `timeout_seconds`. asyncio cancellation is
observed before the exchange or after it settles, never mid-write, and never
rewrites recorded truth. Mid-write stopping is driven by in-domain
invalidators: retirement, source close, Grant, Policy and Catalog. Each host
open provisions a fresh Secret-use ledger in `custody`, because a reopened
ledger allows repair only; the attempt store persists across hosts with a
single writer. The reference host has no close operation, so its custody
handles live as long as the host object.

**Not claimed.** KISSKI, any named cloud provider, hosted or multi-tenant
use, remote model quality, ForgeAI remote support, ComfyUI remote support,
production credential management, strict wall-clock atomic expiry and
provider-side revocation ordering. Qualification uses process-local synthetic
TLS servers emulating the OpenAI-compatible contract, with synthetic S1
material.

```powershell
uv run python .\validate_openai_compatible_remote_1.py
```

**OPENAI-COMPATIBLE-REMOTE-1 LOCALLY QUALIFIED** (2026-10-09). The operator's run
of that command passed **21/21 phases** offline on commit `f411fc4`. That includes
83 REMOTE-1 tests (public-host chat, embedding and Agent end to end;
per-invocation Secret uses; scenarios A-D; host-open admission; the failure
matrix; cancellation; canaries; ambient inputs), ownership and import boundaries
(357, with the pre-existing stale wheel-manifest test deselected), T2, attempt
custody, S1, disclosure and Secret (426), OpenAI-compatible LOCAL, Ollama, Model
and Agent (274), and Core (2027), DocuMind (16) and ForgeAI (89) regressions.
Qualified claim: LegoAI locally qualifies one single-operator credentialed
REMOTE OpenAI-compatible Model profile over verified HTTPS. Each invocation
independently passes remote-disclosure admission, durable attempt custody,
purpose-bound current Secret use and the SRCP-1 credential handoff before one
request; no retry or fallback occurs. Synthetic local TLS and S1 material only.
Not qualified: KISSKI, cloud providers generally, hosted or multi-tenant
support, remote model quality, ForgeAI remote support and ComfyUI remote
support.

## Governed model discovery (PROVIDER-MODEL-DISCOVERY-1)

**Status: LOCALLY QUALIFIED (2026-10-09; commit `198956a`), within the scope
recorded at the end of this section.** This adds one credentialed
provider-control operation: it
retrieves a remote OpenAI-compatible provider's advertised model ids. It is an
operator/provider-setup step, not a Model invocation, and lives outside
ModelPort, every request type, the public host and ForgeAI. It discloses no
model-visible content.

**Authority (ADR-024 §22).** `legoai.governance.provider_control` holds
`ProviderDiscoveryAdmission`. It binds the admission id and revision, the
provider, the normalized https origin and API root, `ProviderOperation.MODEL_DISCOVERY`,
the operator-control consumer, the credential `SecretRevisionRef`, and a
validity window, with no wildcards. `evaluate_discovery` is a pure function
with a closed refusal set. This admission and `DisclosureAdmission` are
unrelated types: neither is accepted in place of the other, and
`model-disclosure/1` gains no class.

**Sequence** (`runtime/_composition/provider_discovery.discover_remote_models`):

1. The admission is evaluated now, and the credential must carry the
   `provider-model-discovery` Secret purpose.
2. The fixed `/models` target is built.
3. A durable INTENDED `ProviderControlAttempt` is committed.
4. A new exact Secret use is composed (use id = attempt id, consumer
   `legoai.provider.model-discovery`) and its current authority is checked.
5. T2 runs: verified TLS, one claim, the final check with the margin, and
   `POST {api_root}/models` with an empty body.
6. The attempt is settled.
7. The bounded parser reads the response.

A refusal before custody records nothing and sends nothing. A Secret refusal
settles NOT_SENT. One call makes one request, with no retry or fallback.

**Custody.** The existing attempt store gains a separately tagged record kind
(`"kind": "provider-control"`): operation, admission id and revision,
provider, origin, API root, credential revision and time. It carries no
disclosure, declaration, binding or model identity. `RemoteAttempt` and the
Model path are unchanged, and older records still decode. No
`DisclosureObservation` and no other Evidence record is written, because
nothing model-visible is disclosed. The attempt and the Secret-use
attribution are the durable record.

**Secret purpose.** S1 binds each revision to exactly one purpose and
consumer. A discovery credential is therefore its own revision, provisioned
for `provider-model-discovery`; a revision provisioned for REMOTE Model use
is refused for discovery, and the reverse also holds.

**Outcomes** (`ModelDiscovery`):

| Outcome | Meaning |
| --- | --- |
| REFUSED | Refused before custody, with a `DiscoveryRefusal`. |
| NOT_SENT | No credential-bearing byte was sent. |
| UNKNOWN | Partial or full send without a complete response (chunked framing included). |
| PROVIDER_REJECTED | Complete non-2xx; the status is reported. |
| MALFORMED | Complete 2xx outside the model-list contract; the attempt stays COMPLETED. |
| LISTED | The advertised ids. |

The parser (`parse_model_list`) accepts only `{"data": [{"id": ...}]}`, with
at most 1,024 ids. Ids must be valid and unique, other fields are ignored, and
anything malformed fails closed. Raw responses are never retained or logged.
Returned ids are an observation at that moment, never configuration,
admission, Catalog entries or routing. They change no binding.

**Not claimed:** KISSKI compatibility, dynamic model routing, provider
discovery in general, model availability beyond the observed call, ForgeAI
remote support or production provider management. Qualification uses
process-local synthetic TLS servers only.

```powershell
uv run python .\validate_provider_model_discovery_1.py
```

**PROVIDER-MODEL-DISCOVERY-1 LOCALLY QUALIFIED** (2026-10-09). The operator's
run of that command passed **19/19 phases** offline on commit `198956a`. That
includes 90 discovery tests (admission values and evaluator, bounded parser and
the fixed `/models` target, the governed flow, authority separation, Secret
purpose and currentness, canaries), ownership and import boundaries (363, with
the pre-existing stale wheel-manifest test deselected), REMOTE chat and
embedding (83), T2, attempt custody, S1, disclosure and Secret (426),
OpenAI-compatible LOCAL, Ollama, Model and Agent (274), and Core (2111),
DocuMind (16) and ForgeAI (89) regressions. Qualified claim: LegoAI locally
qualifies one explicitly operator-authorized, provider-neutral credentialed
model-discovery operation over the existing SRCP-1 HTTPS path. It can retrieve
a bounded set of advertised model ids without disclosing application or model
content, changing application bindings, retrying or falling back. Synthetic
local TLS and S1 material only. Not qualified: KISSKI compatibility, dynamic
model routing, provider discovery in general, model availability beyond the
observed call, ForgeAI remote support and production provider management.

## KISSKI compatibility harness (KISSKI-COMPATIBILITY-1; not yet run live)

**Status: HARNESS LOCALLY READY (offline validation). KISSKI is not claimed
compatible.** One operator-run live probe has taken place (2026-10-09; see
the end of this section). The harness
is `scripts/kisski_compatibility_probe.py`, an operator-run script outside
Core. It composes the qualified paths unchanged. GWDG facts appear only in
this script.

- **Plan:** `uv run python .\scripts\kisski_compatibility_probe.py --plan` prints the plan. It makes no network call, no
  prompt and no credential read.
- **Live run** (only after explicit maintainer authorization): `uv run python .\scripts\kisski_compatibility_probe.py`
  needs an interactive terminal. It asks for the same API key twice through
  S1 hidden input, because each revision carries exactly one purpose:
  `provider-model-discovery`, then `remote-model-bearer`. There is no
  argument, environment, file or pipe input.
- **Calls:** one governed `POST /v1/models`, which must list models. Then the
  operator selects one listed id by number, and one governed SYNTHETIC
  `POST /v1/chat/completions` follows through the public host. The message is
  `Return exactly the word READY.`. There is no retry, fallback or automatic
  model choice.
- **Processor declaration:** provider identity and training NO are
  provider-declared. Retention is UNKNOWN: the no-storage statements concern
  Chat AI conversations, not SAIA API logging. Location, human access and
  subprocessors are UNKNOWN.
- **Classification:** limited to what typed results prove. They do not
  distinguish:
  - a TLS failure from a connection failure;
  - chunked framing from truncation or timeout;
  - a model-identity mismatch from another chat-contract rejection.

  Those cases report as RESULT INCONCLUSIVE or CHAT-CONTRACT INCOMPATIBLE,
  with the observed attempt state and effect.
- **Diagnostics (KISSKI-PROBE-DIAGNOSTICS-1):** the harness preserves the exact
  HTTP status of a complete provider-control (`/models`) response, taken from
  the typed discovery result. It is diagnostic metadata only: the attempt
  stays PROVIDER_REJECTED and nothing is retried. It maps:
  - 401 to AUTHENTICATION FAILURE;
  - 403 to AUTHORIZATION FAILURE;
  - 404 and 405 to MODEL-DISCOVERY CONTRACT INCOMPATIBLE;
  - 429 and 5xx to PROVIDER AVAILABILITY FAILURE.

  A status proves the provider's answer, not its cause. `--plan` prints PLAN
  (no prompt, DNS or network). A live run prints LIVE RUN and its at most two
  governed calls before any credential prompt. Exact chat statuses are not in
  the Model path's typed result and are not shown.

**Operator live probe 1 (2026-10-09).** This was a single governed
`POST /v1/models` call. TLS was verified through the system trust store, and
KISSKI returned a complete 4xx response (401 or 403; the harness showed only
the status class then). The attempt settled PROVIDER_REJECTED and the Secret
use was attributed. There was no retry and no chat call; no SYNTHETIC or other
model-visible content was sent. Classified as AUTHENTICATION FAILURE under the
earlier 401/403 mapping. Compatibility is not established.

**KISSKI-PROBE-DIAGNOSTICS-1 LOCALLY VALIDATED** (2026-10-09). The operator's
offline run of `uv run python .\validate_kisski_compatibility_preflight.py` passed **14/14 phases** on commit `064d388` (harness 36, discovery
and REMOTE 168, T2, custody, S1 and disclosure 348, architecture 363). The
harness now reports the exact `/models` status and labels PLAN and LIVE runs.

```powershell
uv run python .\validate_kisski_compatibility_preflight.py
```
