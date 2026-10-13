# FORGEAI-KISSKI-SAIA-BOUNDED-RECEIVE-DIAGNOSTICS-1

Date: 2026-10-13. Baseline: `9e0abf40fe2a862f5982fd25a0059d9fae72a9c9`.
Status: IMPLEMENTED — MAINTAINER VALIDATION REQUIRED.
Verification: **NOT RUN — Awaiting user execution**.
No provider request, credential access, network probe, test or validator was
performed by the implementation agent. No live execution is authorized here.

## Ownership and change boundary

The existing private T2 module owns `ReceiveDiagnostics`, attached optionally
to the existing `HandoffObservation`. It introduces no public Port, Model API,
provider-specific transport or second evidence store. The existing remote Model
plane projects diagnostics into its ephemeral, per-execution storage, bounded
by existing attempt capacity. The private runtime inspection function checks
host type, thread confinement and execution ownership before returning facts.
The SAIA operator script prints the projection only when Model failure exists.

Files changed:

- `src/legoai/reference/_credential_https.py`: safe stage observations.
- `src/legoai/runtime/_composition/remote_model.py`: optional safe projection.
- `src/legoai/runtime/local.py`: private host-owned diagnostic inspection.
- `scripts/kisski_saia_qualification.py`: failure output and explicitly opted-in
  one-chat diagnostic mode.
- `scripts/tests/test_kisski_saia_receive_diagnostics.py`: synthetic tests.
- `validate_forgeai_kisski_saia_bounded_receive_diagnostics_1.py`: offline checks.
- This document.

No ForgeAI worker, CodingAgent, quality harness, dependency, accepted ADR,
custody schema, parser, TLS configuration, recipient allowance, retry policy,
Secret handoff authority or disclosure policy changes.

## Diagnostic fields and safety

| Fields | Representation / interpretation |
| --- | --- |
| receive_stage | CONNECT, TLS, SEND, WAIT_FIRST_BYTE, READ_HEADERS, READ_BODY, COMPLETE; emitted lowercase |
| connected, tls_completed, request_fully_sent | Observed booleans, not remote computation evidence |
| first_byte_seen | First decrypted HTTP plaintext observed; not first TLS record |
| headers_complete | CRLFCRLF observed; does not imply headers are valid |
| protocol_version | http_1_0, http_1_1, other, unknown; never raw peer text |
| header_status_code | Optional integer 100..599 from complete headers; HEADER-ONLY evidence |
| content_length_present, transfer_encoding_present | Optional booleans; unknown before metadata inspection or when diagnostic header bound prevents it |
| framing | content_length, chunked, close_delimited, cl_and_te, unknown |
| content_length_declared | Optional valid unique nonnegative length <=4,194,304; over-cap or malformed value is absent |
| body_bytes_observed | Bytes after header delimiter, saturated at 4,194,304; not decoded chunk/SSE content |
| body_complete | Set only after the existing parser returns a complete response |
| eof_seen | Observed TLS EOF/close during receive; does not claim the peer stayed open if false |
| parser_rejected | Existing TransportFailure.PROTOCOL caught in receive; use framing fields to distinguish advertised unsupported framing from other rejection |
| cap_reached | Observed declared/body/unterminated-header/aggregate overflow; does not alter any cap or repair historical header-limit gaps |
| read_error | TLS/socket read failure; no exception message |
| deadline_stage | Optional observed stage at the existing timeout; absent means unknown, not inferred |
| failure_category | Existing closed TransportFailure category or unknown |
| Four duration fields | Optional nonnegative integer milliseconds, saturated at 3,600,000 |

`ReceiveDiagnostics` is immutable, has no content-bearing fields and suppresses
its generated repr. Its output projection accepts only the closed enum types,
booleans, None and bounded integers. Arbitrary strings/objects are refused.
Field names come from the fixed dataclass, never from the peer. No raw header,
body, Authorization, Cookie, Set-Cookie, SecretRef, key, provider request ID,
certificate text, traceback or prompt is retained in diagnostics. Header
metadata scanning is bounded to 32,768 bytes and happens in an exception guard;
raw bytes remain local to the existing receive buffer, not diagnostic storage.
The parser remains the only authority for acceptance.

`header_status_code` is deliberately distinct from the existing `chat HTTP
status`, which remains available only after full bounded response completion.
A header-only 200 with an incomplete body must not be called successful chat.

## Stage order and timing

```text
CONNECT -> TCP observed -> TLS -> verified handshake observed -> SEND
 -> full credential flight accepted by OS -> WAIT_FIRST_BYTE
 -> first plaintext -> READ_HEADERS -> delimiter observed -> READ_BODY
 -> original parser accepts exact body -> COMPLETE
```

Refusal, EOF, read error or deadline can leave the last stage incomplete.
Observations add no waits or network operations. Private monotonic samples for
send, first plaintext and headers are converted to:

- `send_to_first_byte_ms`
- `first_byte_to_headers_ms`
- `headers_to_body_complete_ms`
- `total_receive_ms` (send-to-final-observation interval)

Unknown stages have absent durations. Samples include interpreter/scheduling
overhead and do not establish hard real-time accuracy. Connection/TLS time is
not included in receive duration. The existing single monotonic deadline,
including its synchronous DNS and cooperative-check limitations, is unchanged.
The production profile remains **60 seconds and 512 output tokens**.

Timeout interpretation is explicit: `failure_category=timeout` together with
deadline_stage wait_first_byte, read_headers or read_body corresponds to
TIMEOUT_BEFORE_FIRST_BYTE, TIMEOUT_DURING_HEADERS or TIMEOUT_DURING_BODY.
CONNECT/TLS/SEND stages may also be observed; do not map them to response waits.
No stage is reconstructed from elapsed time alone.

## Framing and failure isolation

All Transfer-Encoding responses, absent Content-Length, CL+TE, malformed
framing and unsupported HTTP versions retain their original refusal behavior.
The diagnostic class `close_delimited` means a syntactically scanned header
has neither CL nor TE: it identifies unsupported candidate framing, not proof
that the provider intended a valid close-delimited message. Malformed headers
use unknown framing. No chunk decoder, decompressor, SSE or HTTP/2 is added.
Bodies above the bound and truncated responses retain their existing outcomes.

Diagnostics are never read by `_parse`, `settlement`, disclosure, Secret
authorization, retry decisions or model selection. Collection exceptions drop
diagnostics; projection exceptions omit the projection; accessor exceptions
produce the fixed unavailable line. Exceptions are not logged or stringified.
This intentional best-effort observation boundary does not suppress transport
failures. Fault injection covers both successful and failed transport outcomes.

If an exceptional path escapes the existing exchange without a returned
HandoffObservation, the existing fault/custody handling remains authoritative
and diagnostics may be unavailable. This slice does not alter that handling
to force a diagnostic record. The final EOF parser path and historical
completed-header cap caveat are unchanged. No durable diagnostic schema is added.

## Runner-safe output

Failure output uses a fixed prefix, fixed field names and the closed safe
projection. For example, a partial-body deadline may report:

```text
chat model failure: timeout
chat receive receive_stage: read_body
chat receive header_status_code: 200
chat receive framing: content_length
chat receive body_complete: false
chat receive deadline_stage: read_body
```

Other fields use the same `chat receive <field>: <safe value>` format. Absent
values print `unknown`. Missing diagnostics prints only
`chat receive diagnostics: unavailable`. The existing attempt/effect and Model
failure output stays authoritative; diagnostic failure does not retry a call.

## Historical evidence and effect truth

Qwen's historical 0.182773-second attempt remains sent_all/response_incomplete,
UNKNOWN, with exact cause not recoverable. GLM's historical 60.026151-second
attempt remains timeout/UNKNOWN, with exact timeout stage not recoverable.
These new fields apply only to future attempts. Neither record is rewritten.

Complete send plus no complete response is never changed to no effect.
Framing refusal and timeout after send remain UNKNOWN. Full HTTP completion
followed by adapter rejection keeps completed transport custody. Provider
computation, credential use, billing and Model acceptance remain distinct.
There is no replay, automatic retry, fallback or model reselection.

## Synthetic tests and maintainer verification

Prepared tests cover delayed first byte, all three receive timeout stages,
complete Content-Length, truncated EOF, chunked refusal, missing CL, CL+TE,
malformed framing, declared body cap overflow, header-only status, bounded
timings/counts, exact formatting, repr/output/log/custody canaries, injected
collection/projection/accessor faults, and unchanged success/UNKNOWN outcomes.
Canary body text in the partial-body case makes raw response output a test
failure. The earlier 16 framing cases remain selected. Diagnostic mode tests
cover exact ID selection, rejection of numeric selections, disabled JSON stage,
inert default plan and refusal of the old authorization string.

The validator checks seven-file scope and AST preservation of `_parse`, TLS
configuration and all existing transport cap functions. It selects diagnostics,
T2, SRCP-1, custody/effects, adapter, KiSSKI runner, discovery and architecture
regressions, then typing, lint, format and working/staged whitespace.

Prerequisites: repository root, existing locked Python 3.14 uv environment with
pytest/mypy/Ruff installed, repository test TLS certificates, loopback socket
permission. No new environment variables, API credentials, provider access or
dependency acquisition required. The validator never invokes the live runner.

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_kisski_saia_bounded_receive_diagnostics_1.py
if ($LASTEXITCODE -ne 0) { throw 'KiSSKI SAIA bounded receive diagnostics validation failed' }
```

Only after maintainer success:
`FORGEAI-KISSKI-SAIA-BOUNDED-RECEIVE-DIAGNOSTICS-1 LOCALLY QUALIFIED`.
That qualifies local safe diagnostics only, not SAIA connectivity, coding
quality, streaming, chunked support or global security. Paste results before
any further implementation or live qualification. Nothing has been run here.

## Exact conditional live follow-up design

NOT AUTHORIZED NOW. After maintainer local pass and separate explicit live
authorization, the prepared mode is:

```powershell
uv run --locked --offline --no-sync python -m scripts.kisski_saia_qualification --live --receive-diagnostic
```

It requires this new exact interactive authorization, not the historical one:

```text
AUTHORIZE FORGEAI-KISSKI-SAIA-BOUNDED-RECEIVE-DIAGNOSTICS-1 LIVE SYNTHETIC
```

Use new custody and two separate hidden purpose-bound S1 provisions. One
discovery, then select the displayed exact ID `qwen3-coder-next` (not a number).
If absent, decline and stop without choosing an alternative. Explicitly approve
one fixed `Return the exact token KISSKI_OK.` SYNTHETIC chat. JSON Stage 3 is
disabled by this mode even after success. No repository input or mutation.
The existing ordinary qualification mode is unchanged. The prepared diagnostic
mode has no new authority beyond its separately required interactive approval.

Qwen is the original account-listed coding candidate; its prior documentation
review is preserved without new network research or quality claims in this
slice. A future listing is needed to observe continued availability. This
design neither replays nor resolves either historical attempt.

## Interpretation after that future attempt

| Observed future evidence | Decision to investigate, not a preselected outcome |
| --- | --- |
| Sent fully; timeout; no first plaintext byte | Timeout-profile/provider-latency decision; no proof whether queue, backend or delivery caused delay |
| First byte; chunked metadata; parser refusal | Generic transport capability decision; ADR review before broadening |
| Headers without CL/TE; refusal | Close-delimited capability decision; do not relax parser automatically |
| CL headers and partial body; timeout | Body delivery/response latency investigation |
| Complete bounded HTTP response; adapter rejection | OpenAI-compatible response-contract review; identity checks remain enforced |
| Successful complete tiny token reply | Live connectivity may qualify for that exact attempt/profile; no coding-quality conclusion |
| Missing/failed diagnostics or ambiguous facts | Inconclusive; keep UNKNOWN where applicable; inspect custody, do not replay |

## Architecture and non-goals

This is an implementation-level observation extension under existing private
T2/composition ownership. ADR-023/024 authority, disclosure and effects remain
unchanged. There is no new public contract or security mechanism. Streaming or
framing expansion would require a separate reviewed decision; it is not part
of this slice. No timeout increase, live call, provider-specific production
adapter, credential inspection, model-quality evaluation or commit is performed.

Suggested commit: `feat(runtime): add bounded safe receive diagnostics to T2`.
