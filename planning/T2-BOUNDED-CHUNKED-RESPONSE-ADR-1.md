# T2-BOUNDED-CHUNKED-RESPONSE-ADR-1

Status: Proposed architecture recommendation; NOT ACCEPTED.
Verification: NOT RUN — Awaiting user execution.

## Question and authority

Should protected T2 decode bounded HTTP/1.1 chunked ordinary response bodies?
Recommend the restricted generic response profile in the separate
[Proposed ADR-023 addendum](../adrs/ADR-023-BOUNDED-CHUNKED-RESPONSE-ADDENDUM-1.md).
That table owns the proposed limits; this review owns evidence, alternatives
and qualification requirements. Recommendation is not implementation authority.
Accepted ADR-023 §7.3 owns HTTP/1.1 T2; ADR-014 §14.8/§14.12 owns application
outcomes. Neither explicitly makes Content-Length-only framing an immutable
architectural guarantee. A bounded addendum is appropriate; accepted ADR bodies
and ADR index are unchanged. No new numbered ADR or supersession is proposed.

## Live evidence, supplied by maintainer

| Observation | Value |
|---|---|
| Model | qwen3-coder-next |
| Request mode | stream=false |
| Execution | exec-6b1bfe333b9e4809aeba4d060ce26e9e |
| Connected | true |
| TLS completed | true |
| Request fully sent | true |
| First byte seen | true |
| Headers complete | true |
| Protocol | HTTP/1.1 |
| Header status | 200 |
| Content-Length | absent |
| Transfer-Encoding | present |
| Framing | chunked |
| Body bytes observed | 638 encoded bytes; not decoded entity bytes |
| Body complete | false |
| EOF seen | false |
| Parser rejected | true |
| Cap reached | false |
| Read error | false |
| Receive stage | read_body |
| Deadline stage | unknown |
| Failure category | protocol |
| Send to first byte | 135 ms |
| First byte to headers | 0 ms |
| Headers to body complete | unknown |
| Total receive | 135 ms |
| Effect | UNKNOWN |
| Attempt state | UNKNOWN |
| Final classification | RESULT_INCONCLUSIVE |

The observed non-streaming response used chunked framing rejected by current
T2. Response-body correctness is unknown. SAIA live connectivity is NOT qualified;
coding quality is NOT qualified. No response was decoded to completion. This
does not retrospectively diagnose earlier timeout/inconclusive attempts. Keep
attempt custody and DO NOT REPLAY this execution. The logged status is a header
observation, not a complete-response acceptance.

## Current implementation and sources

Inspected `src/legoai/reference/_credential_https.py` (`_parse` and receive loop),
`src/legoai/runtime/_composition/remote_model.py`, `src/legoai/runtime/local.py`,
`scripts/kisski_saia_qualification.py`, their bounded receive diagnostics tests,
ADR-023 §7.3/§18, ADR-014 §14.8/§14.12 and ADR-INDEX §14.
Current T2 refuses Transfer-Encoding, requires a bounded Content-Length and
returns only a complete body; it does not decode chunked responses. Existing
limits are 4194304 body bytes, 32768 header bytes and 64 fields, with a completed
header-path enforcement gap identified in the addendum. No production file is
changed by this review. Prior maintainer validation qualified safe diagnostics,
not this proposed decoder.

Protocol authority: [RFC 9112 §6.3](https://www.rfc-editor.org/rfc/rfc9112.html#section-6.3)
and [§7.1](https://www.rfc-editor.org/rfc/rfc9112.html#section-7.1).
The proposed accepted grammar uses chunk framing but intentionally excludes
extensions and trailers; its general-recipient conformance limitation is explicit
in the addendum. The live observation does not prove this subset sufficient for
a future SAIA response. No external repository is implementation authority.

## Security and proposed design

Keep CL+TE hard-refused; accept only one chunked token without coding chains.
Refuse extensions and nonempty trailers, without exposing their content. Apply
the existing body cap to decoded bytes and separate finite framing/line/count
bounds. Use incremental parsing under the existing absolute monotonic deadline.
Preserve protected handoff, recipient/TLS binding, custody and UNKNOWN effects
on malformed, incomplete or over-limit responses after send. No retry or fallback.
Return only a complete ordinary body to unchanged status/application validation.
Safe diagnostics are evidence only. Chunked != SSE; stream=false remains required.
HTTP/2 is excluded. No provider-specific transport or new public interface.

## Alternatives

| Option | Security and semantic fidelity | Complexity, maintenance and testing | Interoperability and portability | Operations, migration and reversibility |
|---|---|---|---|---|
| A: bounded generic T2 decoder | Preserves custody/order; explicit finite framing and UNKNOWN; parser is new attack surface | Small private state machine but substantial malformed-input, timing and cap tests; one owner | Standard response framing across admitted providers; restricted extensions/trailers may still fail | Same operator flow; qualify before enablement; reversible to refusal without API migration |
| B: KiSSKI-specific transport | Duplicates protected boundary and risks divergent security/effect semantics | Highest duplicated maintenance and regression burden | Solves one provider only; HTTP framing has no provider-specific semantics | Separate deployment/debug path; harder removal and migration |
| C: provider streaming/SSE | Changes application lifecycle, cancellation and partial-output semantics beyond evidence | New streaming API/state and tests; much larger scope | Does not remove HTTP framing needs; not ordinary complete JSON | New consumer handling and reconciliation; costly migration; reject for this slice |
| D: switch provider/model | Does not establish framing compatibility or solve T2's generic limitation | No decoder code, but each provider/model needs qualification | Unknown framing elsewhere; reduces portability through selection workaround | New authorization/configuration and operational dependency; selection alone is no evidence |
| E: keep unsupported | Smallest current attack surface, preserves fail-closed behavior | No parser cost; maintain refusal tests | Fails observed legitimate ordinary-response framing | Safe present default until acceptance/qualification; reversible later, blocks this interoperability |

A is recommended because the real consumer exposes a framing limitation in
the existing owner. E remains actual behavior until separate acceptance and
implementation qualification. B/C/D are not evidence-based substitutes.

## REUSE / EXTEND / CREATE and ownership

REUSE: TLS, protected credential handoff, header parser, absolute deadline,
response-body cap, custody, effect semantics and safe diagnostics.
EXTEND: generic private T2 response-framing dispatch and bounded parsing only.
CREATE: only private bounded parser state/helpers and observable contract tests
needed to prove the profile. No new Port, provider abstraction, Model API, worker
behavior or dependencies. The only current creations are these two documents
and a documentary validator. No production implementation is authorized.

## Later implementation acceptance matrix

| Area | Required observable evidence |
|---|---|
| Valid grammar | One complete JSON, multiple chunks, upper/lowercase hex, boundary splits at every framing byte, payload CRLF, valid empty framing followed by application refusal |
| Size | Malformed hex/sign/prefix/whitespace; size-line cap and excessive leading zeros; oversized chunk refused before allocation; decoded aggregate overflow |
| Completeness | Exact data lengths and CRLF; missing CRLF; premature EOF in every state; close before zero; terminal zero alone insufficient; empty trailer CRLF; buffered surplus refusal |
| Coding ambiguity | CL+TE, duplicate TE, coding parameters/chains, gzip and unknown codings refused; case/OWS accepted only as specified |
| Restricted subset | Every extension refused, every nonempty trailer refused, valid unsupported messages fail closed; no trailer/extension exposure |
| Resources | Framing budget, 6552 chunk-count boundary and over-limit, header cap on completed/incomplete paths, 64-field cap, bounded buffers; no raw body accumulation |
| Time | Timeout mid-chunk and before zero; slow drip and buffered parser continuations share deadline; no timeout resets |
| Effects | Failures after send remain UNKNOWN, no partial delivery, custody/cancellation preserved; only completed framing enters existing complete HTTP status mapping |
| Containment | Canary payload/header/extension/trailer/credential absent from repr, errors, logs, diagnostics and custody; collector failure cannot alter outcomes |
| Diagnostics | Encoded/decoded counts distinct; bounded chunk counter, terminal/trailer flags, parser/deadline observations correct; diagnostics not authority |
| Compatibility | Existing Content-Length, T2/SRCP-1, disclosure, Secret, LOCAL/Ollama and adapter model/finish regressions preserved |
| Application | stream=false; SSE media type and SSE semantics refused; no HTTP/2 or token delivery |
| Consumer | Synthetic KiSSKI fixture with HTTP/1.1 200, no CL, chunked complete JSON; no captured provider payload needed |

These are future executable implementation tests, not claims established by
documentary fixtures. Cap boundary tests must demonstrate allowed and refused
cases without weakening tests to match implementation.

## Live requalification after acceptance and implementation

Only after explicit architecture acceptance and separately successful offline
implementation qualification, request separate live authorization for ONE new
discovery plus ONE tiny synthetic chat. Select exact qwen3-coder-next ID, keep
stream=false, request KISSKI_OK, no retries/reselection/fallback and no JSON
Stage 3. Do not replay the unknown attempt. Full bounded decode plus valid adapter
result and exact token could establish connectivity only for that exact
model/endpoint/run. Coding quality remains separate. No live execution is
authorized by this proposal or its validator.

## Documentary validation handoff

From the repository root, with the existing locked uv environment and Git:

```powershell
uv run --locked --offline --no-sync python .\validate_t2_bounded_chunked_response_adr_1.py
if ($LASTEXITCODE -ne 0) { throw 'T2 bounded chunked response ADR validation failed' }
```

No environment variables, credentials or network are required. The validator
checks scope, proposal/evidence invariants, positive/negative document fixtures,
staged consistency and whitespace. Expected: LOCAL DOCUMENT CHECKS PASSED;
PROPOSED ONLY; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED. Maintainer must
paste results before implementation proceeds. It does not test HTTP parsing.

Final decision: T2_BOUNDED_CHUNKED_SUPPORT_RECOMMENDED
