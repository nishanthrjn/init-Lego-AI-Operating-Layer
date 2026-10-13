# FORGEAI-KISSKI-SAIA-CHAT-INTEROP-DIAGNOSTIC-1

Date: 2026-10-13. Source baseline: `ad9d67ec11a00192aacf8874163c7d0d71153da7`.
Status: diagnostic report and offline characterization prepared.
Verification: **NOT RUN — Awaiting user execution**.
Final implementation conclusion: **EVIDENCE_INSUFFICIENT**.
**NO LIVE EXECUTION AUTHORIZED** by this report or its validator.

Scope: this report, one synthetic test module and one maintainer validator.
No production, qualification runner, ForgeAI worker, dependency, public API,
accepted ADR, credential, disclosure or attempt schema changes. No new Port.
Read-only custody inspection and public first-party documentation research were
performed; tests, validators, builds and provider requests were not executed.

## 1. Observed live evidence

Sources are the maintainer's two transcripts and the two existing local
`remote-attempts.db` records. Inspection opened SQLite with `mode=ro` and
`PRAGMA query_only=ON`, selecting only state, observation labels, creation and
settlement timestamps for the exact execution IDs. No raw record, SecretRef,
credential, response body or header was exported. Durations below are wall-clock
custody intervals, not instrumented network-stage durations.

| Fact | Qwen attempt | GLM attempt |
| --- | --- | --- |
| Local custody directory basename | `kisski-saia-qualification-0tx1kf01` | `kisski-saia-qualification-x6eophoj` |
| Discovery attempt | `attempt-cc55ff333dbb180eceb5c67c5dfb4a59` | `attempt-a2d47b14310d74be3d4a9e3a26b7fb55` |
| Discovery | POST /v1/models; listed; completed; HTTP 200 | POST /v1/models; listed; completed; HTTP 200 |
| Selected exact model | `qwen3-coder-next` | `glm-5.3-flash` |
| Chat execution | `exec-cab1444ed4644f26aed1ee3156366ccb` | `exec-6722aab4c83a48ab956c233c20a88823` |
| Durable chat state | unknown | unknown |
| Durable observations | sent_all, response_incomplete | sent_all, response_incomplete |
| Custody interval, seconds | 0.182773 | 60.026151 |
| Public ModelFailure in transcript | Not recorded by that runner version | timeout |
| Reported Model effect | unknown | unknown |
| Final classification | RESULT_INCONCLUSIVE; no replay | RESULT_INCONCLUSIVE; no replay |
| Stage 3 | Not run | Not run |

`sent_all` means OS acceptance of the complete credential-bearing ciphertext
flight, not evidence that the provider completed computation or billing.
Successful discovery establishes only that invocation's listing contract.

## 2. Attempt separation and recoverability

Qwen's short recorded interval is inconsistent with an ordinary exhaustion of
the configured 60-second budget, assuming stable local clocks. It does not
identify framing, EOF, TLS, status or provider behavior. A clock discontinuity
cannot be ruled out by these wall-clock timestamps. Do not label Qwen a timeout.

GLM has explicit timeout evidence and a matching approximate duration. This
does not establish whether it waited for the first byte, partial headers or
body completion. Do not label GLM chunked or a model-identity mismatch.

Historical Qwen cause: **NOT RECOVERABLE FROM EXISTING EVIDENCE**.
Historical GLM timeout stage: **NOT RECOVERABLE FROM EXISTING EVIDENCE**.
The persisted attempt schema has no transport failure, framing, response byte
count or stage timing fields. The public ModelFailure is ephemeral. Inspection
of more raw custody cannot recreate facts that were never recorded.

Listing position six referred to different models in the two runs. Listing
order is not stable. Both advertised Qwen; neither qualifies coding quality.

## 3. Discovery versus chat call graphs

Source references (function names are navigation anchors):

- [SAIA runner](../scripts/kisski_saia_qualification.py): `run`, `host_config`,
  `chat_stages`, `chat_once`.
- [Legacy probe composition](../scripts/kisski_compatibility_probe.py):
  `_discover`, `discovery_admission`, `chat_admission`, `ProbeConfig.live`.
- [Discovery plane](../src/legoai/runtime/_composition/provider_discovery.py):
  `discover_remote_models`.
- [Model plane](../src/legoai/runtime/_composition/remote_model.py):
  `RemoteModelPlane.chat`, `_Invocation.exchange`, `record_fault`.
- [Protected exchange](../src/legoai/runtime/_composition/credential_https.py):
  `exchange`, `settlement`.
- [T2](../src/legoai/reference/_credential_https.py): `tls_context`,
  `_CredentialFlight.open`, `_begin`, `_send_once`, `receive`, `_parse`.
- [OpenAI adapter](../src/legoai/reference/model_openai_compatible.py):
  `chat`, `_request`, `_payload`, `_json_body`, `parse_model_list`.

Discovery graph:

```text
runner.run -> open_credential_source -> hidden discovery S1 provisioning
 -> legacy._discover (catalog/grants, ledger/evidence/attempt custody)
 -> discover_remote_models -> evaluate_discovery -> exact /models target
 -> ProviderControlAttempt INTENDED -> exact_use_request -> uses.admit
 -> authorize_secret_use -> protected exchange
 -> T2 open DNS/TCP/verified TLS -> durable claim_for_handoff
 -> Secret _handoff / gated _begin + _send_once continuations
 -> receive -> _parse -> settlement -> durable status / Secret use attribution
 -> parse_model_list -> LISTED IDs (not configuration or disclosure authority)
 -> close discovery custody handles
```

Chat graph:

```text
runner.run -> exact listed model selection + operator tiny-chat approval
 -> separate hidden remote-model-bearer S1 provision -> host_config
 -> open_local_host (public governed host) with RemoteModelRuntime
 -> chat_stages -> chat_once -> host.governed_chat (SYNTHETIC ChatRequest)
 -> governed invocation/catalog/grants/disclosure check
 -> RemoteModelPlane.chat -> OpenAICompatibleModelAdapter.chat
 -> _request JSON serializer -> per-invocation _Invocation.exchange
 -> credential association + exact recipient -> prepare_attempt -> INTENDED
 -> exact_use_request -> uses.admit -> authorize_secret_use
 -> protected exchange -> same T2 open/claim/handoff/receive/_parse/settlement
 -> Model failure mapping OR complete HTTP response -> _payload / chat parser
 -> governed result + runner exact KISSKI_OK content check
 -> Stage 3 only after success and separate approval
```

| Dimension | Discovery | Chat |
| --- | --- | --- |
| Bootstrap | Trusted script constructs provider-control participants | Public Model host constructs governed invocation plane |
| Secret purpose | provider-model-discovery | remote-model-bearer; separate provision and use |
| Authorization/disclosure | Exact provider-control admission; no model-visible content | Catalog/grant invocation plus exact SYNTHETIC disclosure admission |
| Custody | ProviderControlAttempt; admission/recipient/method | RemoteAttempt; execution, binding, exact model, declaration/admission |
| HTTP path/body | POST /v1/models, empty bytes | POST /v1/chat/completions, JSON encoded with json.dumps |
| Headers | Host, Content-Type application/json, Accept application/json, protected Bearer, Content-Length 0, Connection close | Same six header names; body length differs |
| Connection/TLS | New T2 connection, system CA, hostname verification before handoff | Same implementation; separate connection and handoff |
| Timeout | Configured 60-second T2 budget per discovery | Configured 60-second T2 budget per chat |
| Response mechanics | T2 _parse, Content-Length required, TE refused, no EOF delimiter | Same parser and bounds; not the adapter's LOCAL urllib path |
| Bounds | Request 1,048,576; response body 4,194,304 bytes; header caveat in section 4 | Same T2 constants, not LOCAL urllib's 1 MiB response limit |
| JSON | Strict shared JSON decoding; data/IDs, maximum 1,024 models, IDs <=256 characters; duplicates refused | Strict shared JSON decoding; exact model, one assistant text choice, stop, no tools/functions |
| Settlement | HTTP completion first, then listing shape; malformed list can have completed custody | HTTP completion first, then Model parsing; rejected content can have completed custody |
| Diagnostics | Listed outcome/state/attempt/HTTP status | Execution/state/effect, complete HTTP status, safe ModelFailure |

Neither successful discovery nor the shared parser implies identical server
responses: endpoint-specific response framing, scheduling and inference costs
can differ. That is a possibility, not an observed SAIA implementation fact.

## 4. T2 framing support matrix

This matrix classifies the current client implementation, not observed SAIA
responses. Runtime characterization remains pending maintainer execution.

| Response behavior | Classification | Exact boundary |
| --- | --- | --- |
| One valid Content-Length, complete bounded body | SUPPORTED | HTTP/1.0 or HTTP/1.1, status 200..599, exactly declared bytes |
| Transfer-Encoding: chunked | REFUSED | Any Transfer-Encoding field raises PROTOCOL; no chunk decoder |
| HTTP/1.1 connection-close-delimited body | REFUSED | Missing Content-Length raises PROTOCOL; EOF is not a delimiter |
| HTTP/2 frames or HTTP/2 status text | REFUSED | No HTTP/2 implementation; textual version outside 1.0/1.1 rejected |
| SAIA negotiated HTTP version in these attempts | UNKNOWN | Not recorded; no ALPN advertised by current client |
| Missing Content-Length, even empty body | REFUSED | No special 204/304/EOF exemption |
| Content-Length together with Transfer-Encoding | REFUSED | TE rejects independently of length and ordering |
| Duplicate Content-Length | REFUSED | Even equal duplicate values refused |
| Compressed JSON with valid Content-Length | REFUSED end-to-end | T2 accepts framed bytes and ignores Content-Encoding; adapter cannot decode actual gzip JSON; no decompressor |
| Interim 1xx then final response | REFUSED | First status outside 200..599; no interim-response loop |
| Keep-alive response with complete Content-Length | SUPPORTED | Returns on exact body completion; closes its socket; never reuses connection |
| Server closes after full Content-Length body | SUPPORTED | Completion does not require waiting for EOF |
| Server closes before declared length | REFUSED | Incomplete response, sent_all => UNKNOWN |
| Extra bytes already buffered beyond declared length | REFUSED | Parser rejects len(body) > length; later unread bytes are not inspected |

Bounds nuance: `_parse` enforces 64 header lines and a 32,768-byte limit when
the header terminator is still absent. It does not separately compare the
completed header offset to that byte limit. `receive` additionally caps total
plaintext at 32,768 + 4,194,304 bytes. Thus the nominal header-byte limit is not
uniformly enforced for a completed header arriving in one read. This is a
separate source-review hardening finding, not proof of either live failure;
no production correction or qualification is claimed here. Malformed numeric
lengths can also escape the ordinary PROTOCOL projection through conversion
exceptions; `record_fault` then preserves uncertainty.

## 5. What response_incomplete can mean

The sole normal producer is `credential_https.settlement`: progress ALL and
response None => UNKNOWN with sent_all + response_incomplete. It is not a
diagnosis and does not imply that zero response bytes arrived.

| Cause / path | Current result | Historical assessment |
| --- | --- | --- |
| EOF before any/full header or declared body; SSLZeroReturn/SSLEOF | receive returns None; usually no transport failure enum | POSSIBLE Qwen; GLM primary observed failure is timeout |
| TE, missing/duplicate CL, invalid status/header, excessive CL, extra body | TransportError(PROTOCOL) caught in receive => None | POSSIBLE Qwen; EXCLUDED as GLM's recorded primary category, not as eventual unseen response behavior |
| Deadline during response selector wait | TIMEOUT, None | GLM CONFIRMED category; Qwen NOT RECOVERABLE FROM EXISTING EVIDENCE, ordinary 60-second exhaustion unsupported by short interval |
| TLS read error or socket OSError after send | None without finer failure category | POSSIBLE Qwen; no recorded evidence of this for GLM |
| Unterminated header over byte cap; header count or aggregate/body cap | PROTOCOL, None | POSSIBLE Qwen; actual bytes/counts not recorded |
| Fragmented, incomplete parser input | _parse returns None; continue reading until completion/EOF/failure | POSSIBLE in both; parser state/fragment boundaries not recorded |
| Header/body stall | Wait until remaining budget expires | POSSIBLE location of GLM timeout; first-byte vs body not recoverable |
| Gate cancellation/invalidation during writes | NONE -> NOT_SENT or PARTIAL -> UNKNOWN sent_partial | EXCLUDED for these sent_all records as explanation of partial send |
| Async cancellation during synchronous exchange | Deferred until exchange returns; does not interrupt TLS read on this thread | Not evidence of a read cancellation; existing cancellation regressions retained |
| Crash, exceptional parse/conversion/custody failure after claim | record_fault may settle UNKNOWN with empty observations, or leave INTENDED if custody fails | Separate UNKNOWN route, not the normal response_incomplete producer; recorded label pair does not identify this route |
| Complete HTTP response but JSON/model/finish failure | Custody already completed; adapter rejects contract | EXCLUDED as explanation of these response_incomplete records |
| Connection/certificate failure before handoff | NOT_SENT, sent_none | EXCLUDED for both sent_all records |

The final EOF `_parse` call lies outside `receive`'s TransportError handler.
An exception there propagates to the plane's fault handler instead of becoming
a normal response_incomplete observation. These distinctions matter for future
diagnostics. No synthetic reproduction can identify an unrecorded historical
server behavior merely because it yields the same coarse result.

## 6. Timeout analysis

`ProbeConfig.live` chooses 60 seconds; the SAIA runner preserves it.
`_CredentialFlight.__init__` creates one monotonic deadline. `_remaining` and
selector waits use the remaining shared budget, not a fresh timeout per stage.

| Stage | Implementation |
| --- | --- |
| DNS/TCP | socket.create_connection receives remaining timeout; synchronous DNS and multiple address attempts are not a proven hard aggregate deadline |
| TLS handshake | Nonblocking BIO/socket readiness waits use remaining budget |
| Credential writes | Gated nonblocking sends; would-block waits use same budget |
| First response byte | Same read readiness wait, no separately configured timeout |
| Response headers/body | Same deadline; no idle-time reset and no separate body budget |
| Complete governed invocation | Setup/custody/serialization and scheduling lie outside T2 construction-to-read budget |

The implementation does not check the deadline on every immediately available
TLS read/write. This is a finite configured I/O-wait budget, not a hard real-time
proof covering DNS, scheduling and all computation. The custody interval starts
before transport setup; GLM's 60.026151 seconds is consistent with that design.

Sixty seconds is a qualification-runner policy choice; it is not an ADR-mandated
number or a provider promise. T2 permits a positive timeout up to 3,600 seconds.
The Secret margin and admission validity are separate security constraints;
raising a timeout must not bypass them or imply hard validity at OS acceptance.

GWDG documents completion latency and a streaming alternative, without a
60-second guarantee. Therefore a tiny prompt alone does not justify assuming
60 seconds suffices on shared infrastructure. Conversely, one GLM timeout
cannot justify a particular longer value for Qwen. Keep 60 unchanged in this
slice; obtain stage observations first. Any later profile change needs an
explicit finite total budget, output bound, validity-window assessment and
operator wait budget. No invented SLA, capacity, queue-delay or cold-start claim.

## 7. Request compatibility and verified public sources

First-party pages inspected on 2026-10-13:

- [GWDG SAIA API documentation](https://docs.hpc.gwdg.de/services/ai-services/saia/index.html):
  OpenAI-compatible API, Bearer authentication, the configured API root, POST
  chat and POST model listing. Examples use model/messages/max_tokens and
  optional sampling fields. Its non-streaming discussion explains waiting for
  full generation and demonstrates stream=True as an alternative. No response
  framing or completion-time guarantee is established by those examples.
- [GWDG JupyterHPC model selection](https://docs.hpc.gwdg.de/services/ai-services/jupyter-ai/index.html#model-selection):
  recommends Qwen3 Coder Next for agentic coding and describes it as specialized
  for coding. This is provider documentation, not LegoAI evaluation evidence.
- [GWDG agentic coding](https://docs.hpc.gwdg.de/services/ai-services/coco-ai/agentic_coding/index.html):
  also documents an Anthropic-compatible messages path and Qwen configuration.
  Its model-selection examples differ from the Jupyter page; documentation and
  historical account listings must not be treated as permanent availability.

Exact tiny-chat JSON semantics (whitespace from json.dumps is immaterial):

```json
{
  "model": "<the operator-selected exact listed ID>",
  "messages": [{"role": "user", "content": "Return the exact token KISSKI_OK."}],
  "stream": false,
  "max_tokens": 512
}
```

The model was qwen3-coder-next in the first run and glm-5.3-flash in the second.
There is no temperature (deterministic setting is false), top_p,
response_format, tools, functions, reasoning parameter, system message or
provider-specific extension. Stage 3 also uses text JSON instructions, not an
unimplemented response_format contract. The payload is consistent with the
documented field family; this is not proof of acceptance by every backend.
Keep the minimal payload. The 512-token cap bounds requested output; it does
not promise that queueing, internal reasoning or inference finishes quickly.

## 8. Response-contract strictness

| Requirement | Classification and decision |
| --- | --- |
| One assistant text choice | LegoAI's supported ModelPort contract; normal for a default single completion, not a universal requirement on all OpenAI-compatible APIs |
| finish_reason == stop | Supported complete-output contract and qualification constraint; other protocol-valid reasons such as length are deliberately refused |
| Exact response model equality | LegoAI identity/admission consistency requirement; an alias is not automatically evidence of a different provider, but accepting it silently would weaken the current binding |
| No tool_calls/function_call | Supported text-only contract and deterministic authority boundary; tool output cannot authorize execution; even present-but-null fields currently refuse |
| Content exactly KISSKI_OK | Runner qualification convenience, separate from HTTP/Model protocol |

No item is established as unnecessary strictness by these attempts: neither
reached a complete transport response. Model echo is not cryptographic proof
of backend execution. Supporting aliases would require an explicit,
source-backed requested-to-resolved identity mapping bound to configuration,
disclosure and attempt attribution, with negative tests for arbitrary changes.
An untrusted reply cannot authorize its own alias. Do not relax equality here.

## 9. Streaming and alternative options

HTTP chunked transfer framing and application SSE streaming are distinct.
A stream=false JSON reply could use chunked HTTP without being SSE; neither
is established for SAIA's two historical chat replies.

| Option | Security/effects and custody | Parsing, cancellation and reuse | Decision |
| --- | --- | --- | --- |
| A: bounded non-streaming, evidence-backed framing/timeout correction | Retain exact S1 handoff, admission, one attempt, UNKNOWN on incomplete response | Lowest burden; generic reuse; finite decoded/body/header bounds; cancellation remains current synchronous behavior unless separately reviewed | Preferred direction if an actual gap is evidenced; no correction selected now |
| B: bounded SSE/chunked T2 | Same handoff possible, but partial text must not count as completion or authority; custody needs terminal semantics | Chunk sizes/extensions/trailers, cumulative bytes/events, UTF-8 fragments, SSE terminal/error events, cancellation and identity/usage aggregation; highest burden, generic potential | ADR-023 revisit trigger; blocked pending separate decision |
| C: KiSSKI-only qualification transport | Risks bypassing S1 ordering, disclosure or custody if built around an SDK; identical enforcement would duplicate T2 | Low provider neutrality; second parser/security surface; timeout and cancellation still necessary | Not justified |
| D: other official SAIA path | GWDG documents /v1/messages; current target allowlist/Model adapter do not support it | Different schema and parser; finite bounds, custody and cancellation need qualification; no evidence it fixes underlying HTTP framing | Not an escape hatch or authorized fallback |
| E: keep chat unqualified | Preserves fail-closed behavior and unknown historical effects | No new parsing burden; does not assert provider-wide incompatibility | Current operational disposition until evidence supports A or an approved alternative |

No HTTP/2, chunk decoder, SSE consumer, alternate endpoint, model fallback,
provider-specific transport or third-party SDK is added.

## 10. HTTP version and ALPN

`tls_context` constructs a verified TLS client (minimum TLS 1.2) and never
calls set_alpn_protocols. It neither advertises h2 nor explicitly advertises
http/1.1. `_begin` unconditionally writes HTTP/1.1. `_parse` recognizes 1.0 and
1.1 only. No negotiated ALPN value is collected by production code.

The new synthetic fixture advertises h2 and http/1.1 on the server and asserts
that this client negotiates neither. An ordinary ALPN negotiation cannot
select h2 without a client offer. A server closing a non-ALPN connection is
still possible, not observed. Binary HTTP/2 data would fail HTTP/1 parsing or
remain incomplete until EOF/deadline; an HTTP/2 textual status is refused.
The official SAIA page contains an HTTP/2 example from a different client;
that is not evidence this client negotiated HTTP/2. No HTTP/2 implementation
is justified.

## 11. Safe diagnostics: existing and proposed

Already available: exact execution ID, attempt state, effect, closed
ModelFailure enum and HTTP status only after complete bounded framing. The
new tests verify that peer header canaries stay out of output, logs and custody.
No new production diagnostic was added: a script alone cannot recover facts
discarded in protected T2 without adding an owner-controlled observation seam.

Proposed next bounded diagnostic design (not implemented or authorized here):

| Observation | Value/bound and purpose |
| --- | --- |
| Receive stage | Closed enum: awaiting-header, header-partial, body-partial, complete; distinguish first-byte and body timeout |
| Header framing class | Closed enum: length, transfer-encoding-refused, length-missing, invalid; classify before discarding response |
| First plaintext byte observed | Boolean; not proof of a valid HTTP response |
| Length/count evidence | Content-Length present boolean; validated in-range length or over-cap enum; bounded observed body count plus overflow flag |
| HTTP metadata | Validated version enum and integer status marked HEADER-ONLY unless full response completes; never reuse as complete-status authority |
| Duration | Optional bounded monotonic aggregate; stage enum has higher initial value than a full timing taxonomy |

Own extraction in protected transport; carry only immutable bounded facts to
trusted composition; expose through an owner-controlled diagnostic accessor.
Do not monkeypatch receive in the live runner, add raw callbacks, perform a
second request, retain a response buffer, or use diagnostics in settlement.
No raw headers, body, Authorization, SecretRef, key, unrestricted error text,
model-generated content or prompt content beyond the fixed synthetic identifier.
Prefer ephemeral per-execution facts like the existing HTTP-status projection;
persisting a new diagnostic would require an explicit custody/schema decision.
This design needs its own implementation and safety validation before a new
live diagnostic run can distinguish the remaining hypotheses.

## 12. Synthetic reproduction matrix

New executable module:
[test_kisski_saia_chat_interop.py](../scripts/tests/test_kisski_saia_chat_interop.py).
It reuses the established Runner's synthetic purpose-separated S1 provision
and TLS test CA. Its independent wire fixture always completes discovery, then
changes only the chat response. No production parser is used to build replies.

| Case | Prepared expected result |
| --- | --- |
| A: complete Content-Length, immediate server close | Connectivity-only after explicit Stage 3 decline; completed custody |
| B: 0.05-second delayed Content-Length under existing fixture's 1-second budget | Same success |
| C: no response until beyond budget | timeout; UNKNOWN; exactly one chat |
| D: valid chunked JSON | protocol_incompatible; UNKNOWN; no replay |
| E: close-delimited JSON | protocol_incompatible; UNKNOWN |
| F: Content-Length greater than transmitted bytes | provider_execution_failure; UNKNOWN |
| G: complete headers followed by body stall | timeout; UNKNOWN; no complete-status diagnostic |
| H: malformed chunk size | TE refused before chunk decoding; protocol_incompatible; UNKNOWN |
| I: complete response with model alias | Completed HTTP custody; Model contract rejected; no Stage 3 |
| J: complete response with finish_reason length | Same contract refusal |
| Additional: compressed JSON | Framing complete; adapter rejects; no decompression |
| Additional: CL plus TE / interim 1xx / HTTP/2 textual status | protocol_incompatible; UNKNOWN |
| Additional: keep-alive / HTTP/1.0 with CL | Complete without waiting for peer EOF; no connection reuse |
| Cross-cutting | Current payload, separate connections, no ALPN selection, canary containment, exact sent_all/response observations |

There are 16 new parameterized cases. Cases D/E/F reproduce the *shape* of
Qwen's coarse observations, not its historical cause. C/G reproduce GLM's
timeout category without claiming which stage stalled live. H characterizes
refusal, not a new streaming implementation. Existing T2/SRCP-1 tests cover
TLS trust, caps, protected writes, revocation, time validity, cancellation,
fault settlement and canary containment. This is characterization of current
behavior before any correction, not tests altered to make a provider pass.

## 13. Effect semantics

No attempt is replayed. Complete request plus incomplete response remains
UNKNOWN; timeout or framing failure after send is not no-effect evidence.
Model selection changes would create new effectful attempts, not recover old
ones. Provider computation, credential use and billing cannot be inferred
absent because the caller lacks a result.

Complete HTTP response settles transport custody before adapter validation.
A rejected model alias, finish reason or JSON body therefore remains completed
transport custody even if the Model operation reports a rejected/NONE result.
That does not assert that the provider saw nothing or incurred no cost.
Cancellation does not rewrite already recorded transport observations. None
of the tests or proposed diagnostics changes these rules.

## 14. Architecture and ADR impact

[ADR-023](../adrs/ADR-023.md) sections 7.1/7.3 preserve exact recipient,
purpose-bound protected handoff, one HTTP/1.1 connection per attempt, no retry
and explicit uncertainty. Section 18 explicitly identifies streaming as a
separate decision trigger. [ADR-024](../adrs/ADR-024.md) retains independent
provider-control and model-visible disclosure authority. Adapter contract
ownership remains [ADR-014](../adrs/ADR-014.md); script convenience cannot relax it.

No accepted ADR is edited and no new transport guarantee is implemented.
Materially broadening T2 to chunked/SSE/HTTP2 requires a reviewed decision
covering qualified framing, completion, cancellation, bounds and failure
semantics before production work. Plain chunked non-streaming HTTP should be
assessed separately from SSE; broadening the tested security mechanism is not
automatically authorized by the label OpenAI-compatible. Documentation and
characterization alone do not require accepting a new architecture.

The header-byte enforcement caveat and cooperative deadline limitations are
separate review findings. They do not identify a SAIA incompatibility, authorize
scope expansion or constitute global transport/security qualification.

## 15. Final implementation conclusion and validation

The single conclusion recorded at the top is evidence insufficiency. The
earliest prerequisite is trustworthy receive-stage/framing evidence, not a
chosen new timeout, a parser relaxation or a provider incompatibility verdict.

Secondary findings: current T2 cannot accept chunked/close-delimited replies;
GLM exceeded the current budget; exact identity parsing is deliberately strict;
streaming needs a separate architecture decision. None identifies Qwen's cause.

Maintainer prerequisites: repository root, existing locked Python 3.14 uv
environment with pytest/mypy/Ruff already installed; test TLS certificates in
`tests/support/tls`; permission to bind loopback sockets. No environment
variables, account, API key, package acquisition, Docker or GPU are required.
The validator does not open historical custody or fetch documentation.
It imports only regression-path constants from the earlier validator, never
calls that validator's main function, and never invokes a live runner.
ForgeAI application files are unchanged, so no additional ForgeAI project
suite is selected. Existing runner, adapter, SRCP-1, T2 and architecture tests
remain included.

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_kisski_saia_chat_interop_diagnostic_1.py
if ($LASTEXITCODE -ne 0) { throw 'KiSSKI SAIA chat interop diagnostic validation failed' }
```

Expected evidence: all 16 new characterization cases plus selected existing
regressions pass; typing, lint, format and working/staged whitespace pass; final
output states LOCAL CHECKS PASSED, EVIDENCE_INSUFFICIENT and no live execution
authorization. This would qualify the local characterization only. Paste the
complete result before further implementation. Current verification remains
pending; previous provider-profile validator success does not validate these
new files.

## 16. Next live qualification design

No live command is issued by this slice. Local characterization passing alone
does not establish a correction/profile change or authorize another call.
First implement and locally qualify the bounded diagnostic proposal in section
11 (or obtain equivalent trustworthy provider evidence), then reassess the
smallest generic correction and any ADR gate. Do not silently rerun either
historical attempt to obtain the missing evidence.

If a correction/profile change is established and its local validation passes,
prepare exactly ONE separately authorized synthetic requalification:

1. New exact authorization scoped to that diagnostic/correction version;
   new custody, at most one discovery and one tiny chat, no retries or fallback.
2. Discover once, choose by the displayed exact ID qwen3-coder-next, not its
   previous numeric position. If absent, stop; do not choose a substitute.
3. Qwen is the original candidate, was advertised to this account and is
   documented for coding. This is candidacy, not selection as a preferred
   coding model or proof of quality/continued account entitlement.
4. Separate hidden S1 provisions; same SYNTHETIC-only message and exact
   recipient/model admission. No repository input, file mutation, tool use or
   generated-code execution. Explicit approval immediately before chat.
5. Keep current output/timeout limits unless a specifically reviewed profile
   change supplies different finite limits. Capture only approved safe facts
   and keep header-only status distinct from complete response status.
6. Stop after Stage 2, including on success; decline Stage 3. Unknown remains
   unknown and requires inspection, never replay. Coding evaluation is separate.

This is a conditional design, not an executable bypass of the existing gates
or authorization for a new provider effect.

Suggested commit: `test(runtime): characterize SAIA chat framing and timeout evidence`.
