# T2-BOUNDED-CHUNKED-RESPONSE-ACCEPTANCE-REVIEW-1

Status: Architecture accepted by maintainer-delegated review; document validation pending.
Date: 2026-10-13.
Verification: NOT RUN — Awaiting user execution.

## Decision and placement

Decision: ACCEPT_BOUNDED_CHUNKED_ADDENDUM

Classification A: compatible bounded extension of ADR-023/T2.
The explicit maintainer task delegates this acceptance review; no independent
review or implementation conformance is claimed. Accept the unchanged contract
in [the addendum](../adrs/ADR-023-BOUNDED-CHUNKED-RESPONSE-ADDENDUM-1.md).
Its new current-status block overrides proposal-time authority statements while
preserving the complete original reasoning. [Index metadata](../adrs/ADR-INDEX.md)
provides reciprocal registration. No new ADR ID or supersession is required.

ADR-023 §7.3 explicitly owns private HTTP/1.1, one connection per attempt,
protected nonblocking credential send, and response wait outside Secret ordering.
It delegates result mapping to ADR-014 §14.8. It does not require Content-Length
as the sole architectural framing mechanism. Section 18's streaming revisit
trigger is not entered: consumers still receive one complete bounded response.
ADR-014 §14.12's minimal non-streaming Model subset remains binding. This is
framing expansion within those owners, not permission to weaken their security
guarantees. Accepted ADR-023 and ADR-014 bodies remain unchanged under index §14.

## Prior validation and preserved evidence

Maintainer execution of `validate_t2_bounded_chunked_response_adr_1.py` PASSED,
including scope, profile/evidence, positive/negative fixtures, staged consistency
and working/staged whitespace. Recorded final result:

```text
T2-BOUNDED-CHUNKED-RESPONSE-ADR-1 LOCAL DOCUMENT CHECKS PASSED; PROPOSED ONLY; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED
```

The [original planning record](T2-BOUNDED-CHUNKED-RESPONSE-ADR-1.md) remains
unchanged historical proposal evidence, including its then-pending validation
wording. The completed proposal validation is recorded here; validation of this
new acceptance record is NOT RUN. Documentary checks are not parser tests.

Live evidence remains the exact original table: qwen3-coder-next, stream=false,
HTTP/1.1, header status 200, Content-Length absent, Transfer-Encoding present,
chunked framing, 638 encoded bytes observed and first byte at 135 ms. Execution
exec-6b1bfe333b9e4809aeba4d060ce26e9e was not decoded to completion;
attempt state UNKNOWN, effect UNKNOWN, final RESULT_INCONCLUSIVE. This proves
the observed framing mismatch only. No response-body correctness, successful
model execution, live connectivity or coding quality is established. Earlier
timeouts are not retrospectively diagnosed. DO NOT REPLAY the unknown attempt.

## Accepted subset and exclusions

Accept only HTTP/1.1 response framing with one Transfer-Encoding field containing
one case-insensitive chunked token after surrounding SP/HTAB normalization.
Incremental bounded decoding requires terminal zero and empty-trailer closure
before exposing one complete decoded body to existing status/adapter validation.
No provider-name test is allowed: generic T2 owns framing, not KiSSKI, ForgeAI
or the Model domain. The real consumer motivates the need, not special authority.

Exclude SSE, stream=true, text/event-stream, token-by-token Model API, partial
ModelResult publication, streaming tool calls, HTTP/2, request-body chunking,
decompression, pooling, retry, replay, resume, fallback and arbitrary transfer
codings. HTTP chunked transfer framing != OpenAI streaming. These application
streaming semantics would need a separate design. Preserve stream=false and
refuse SSE media type/application semantics even when framing completes.

## Closed policy review

| Policy | Verdict and rationale |
|---|---|
| CL+TE | ACCEPT hard refusal; do not select precedence or normalize ambiguous lengths |
| Coding chains | ACCEPT refusal of gzip/compress chains, duplicate TE, repeated chunked, parameters and unknown codings; one token only |
| Extensions | ACCEPT refusal of every extension; removes grammar/metadata surface; no observed evidence requires extensions |
| Trailers | ACCEPT refusal of all nonempty trailers; accept only required empty CRLF closure; no new metadata authority or disclosure |

Extensions/trailers may exist in the undecoded live response; their absence is
not established. The restricted profile knowingly trades interoperability for
a smaller parser. It is not a fully conforming general RFC 9112 recipient.
Acceptance does not promise SAIA success. If valid excluded framing is later
observed, stop and review that evidence separately instead of relaxing policy.

## Numeric and timing bound review

| Bound | Decision | Basis |
|---|---|---|
| Decoded body: 4194304 bytes | ACCEPT | Reuses existing T2 body cap; applies to decoded bytes before accumulation |
| Framing overhead: 32768 bytes | ACCEPT | Separate header-sized metadata budget bounds all size lines and CRLF; consciously restrictive resource policy, not provider-capacity evidence |
| Size line: 8 bytes including CRLF | ACCEPT | Six hex digits represent 400000 hex (4 MiB); extra leading zeros/whitespace/extensions refused |
| Nonterminal chunks: 6552 | ACCEPT | floor((32768 - 5) / 5); minimum five framing bytes per positive chunk plus minimum five for terminal closure |
| Encoded body: 4227072 bytes | ACCEPT | Sum of decoded cap and separate framing cap; both component limits still independently enforced |
| Headers: 32768 bytes and 64 fields | ACCEPT | Existing intended bounds, enforced on incomplete and complete-header paths; completion-path gap must be closed in implementation |
| Deadline: existing absolute monotonic attempt deadline | ACCEPT | No reset per chunk/read; buffered continuations also check time; prevents slow-drip extension |

No bound requires modification. The metadata budget is a deliberate bounded
resource policy, not a mathematically unique optimum. Its fragmentation limit
is an acknowledged portability cost. The chunk-count ceiling is conservative
and partially redundant with overhead checks; tests must prove refusal without
requiring a particular counter to fire first. Terminal zero is not an unlimited
zero-chunk loop. Trailer/extension accepted content bytes and fields/count stay
zero. Header hardening preserves intended limits; no previously out-of-contract
oversized-header behavior is promised as compatibility.

## Memory, deadline and parser authorization

One bounded size line, size validated before allocation/read, aggregate capacity
checked before accumulation, exact chunk-data consumption, mandatory CRLF,
terminal zero and trailer policy provide sufficient requirements for a separate
implementation. Never retain the entire encoded wire body to decode afterward.
Use bounded input (existing receive unit at most 65536 bytes), bounded line and
decoded buffers, finite counters; delivery copies may have bounded constant
overhead. Reject buffered surplus after terminal framing and close the single-use
connection without waiting for EOF. No header or raw framing is upper-layer input.

Every read and parser continuation uses the existing absolute monotonic deadline.
No timeout reset, slow-drip extension or automatic continuation outside the budget.
These are requirements to prove, not claims about code not yet implemented.

## Effects, custody and diagnostics

Malformed framing, cap rejection, premature EOF, framing rejection, timeout
mid-chunk or before terminal closure after send preserve UNKNOWN where processing
may have occurred. No chunk-parser outcome can rewrite a possible remote effect
to NONE. No partial decoded bytes may escape. Only full bounded framing success
permits the existing complete HTTP-status mapping and Model validation; framing
success does not itself imply a successful model result.

No custody schema change is required. Keep SRCP-1 Secret-use evidence, durable
INTENDED/outcome facts, exact execution/attempt identity and reconciliation
semantics unchanged. Diagnostics remain optional ephemeral safe observations,
not authority or durable payload. Closed flags/counters may describe framing,
chunk count, decoded bytes, terminal seen, trailer presence and parser rejection.
No payload, raw extension/trailer, Authorization or credential material. Preserve
encoded/decoded distinction and collector-failure isolation. No new diagnostic
fact authorizes retries or changes settled effects.

## Design principles

| Principle | Review |
|---|---|
| SRP | T2 owns HTTP response framing; adapter owns JSON/application validation |
| OCP | One bounded framing extension; no provider branches |
| LSP | Existing qualified Content-Length behavior unchanged; same complete-body contract |
| ISP | No new public interface, Port or Model API |
| DIP | Model and ForgeAI remain independent of transport parser mechanics |
| DRY | One T2 framing owner; no provider-specific copies |
| KISS | One narrow coding, no extension/trailer grammar |
| YAGNI | No SSE, HTTP/2, decompression or pooling |
| SoC | Transport completion distinct from Model result acceptance |
| Law of Demeter | Upper layers receive decoded bounded bytes, never parser internals |

## Frozen implementation acceptance criteria

These A–Z obligations supplement the unchanged addendum and original acceptance
matrix. Positive/negative documentary fixtures below cannot establish them.

| ID | Required observable evidence |
|---|---|
| A | Valid single chunk yields one complete bounded body |
| B | Valid multiple chunks, including input fragmentation at framing boundaries |
| C | Upper/lowercase hexadecimal accepted within the six-digit bound |
| D | Malformed size line refused |
| E | Overlong size line refused before unbounded buffering |
| F | Decoded aggregate body overflow refused before accumulation |
| G | Framing-overhead overflow refused |
| H | Chunk-count overflow refused; test exact allowed boundary too |
| I | Premature EOF in every parser state refused |
| J | Missing chunk CRLF refused |
| K | Terminal zero and empty trailer closure required; zero alone insufficient |
| L | Every chunk extension refused |
| M | Every nonempty trailer refused without exposure |
| N | CL+TE refused without precedence selection |
| O | Coding chains, duplicate fields/tokens and unsupported codings refused |
| P | Timeout before terminal chunk preserves incomplete outcome |
| Q | Timeout mid-chunk preserves incomplete outcome |
| R | No deadline reset; slow drip and buffered continuation stay bounded |
| S | Qualified Content-Length regressions unchanged; intended header caps enforced |
| T | Safe diagnostics correct, bounded and unable to alter settlement |
| U | No response-body or credential/canary leakage in logs/errors/custody |
| V | UNKNOWN effect truth preserved on failures after send |
| W | No retry, replay, resume or provider/model fallback |
| X | SRCP-1, disclosure, Secret ordering and custody regressions preserved |
| Y | KiSSKI-like synthetic complete chunked JSON fixture, no real payload needed |
| Z | Existing LOCAL/Ollama/remote Model regressions preserved |

Additional existing obligations remain: SSE refusal even with complete framing,
buffered surplus refusal, body/header/count boundary controls, cancellation and
reconciliation, and no new dependencies/public interfaces.

## Implementation and future live gates

Next slice: T2-BOUNDED-CHUNKED-RESPONSE-1

Acceptance authorizes a separate implementation slice after this documentary
validation; no production implementation occurs here. Implementation qualification
is pending and requires maintainer-run offline evidence against A–Z.
No live execution is authorized.

Only after accepted architecture AND successful implementation local qualification
may separate authorization permit one new discovery and one qwen3-coder-next
synthetic KISSKI_OK chat: exact model-ID selection, stream=false, no JSON Stage 3,
no replay, retry or fallback. The response must be completely decoded, valid
OpenAI-compatible JSON, exact selected model accepted, assistant content ==
KISSKI_OK and valid finish_reason (stop under the existing runner contract).
Only that exact endpoint/model/run could support live connectivity qualification;
coding quality remains separate. No current result is reclassified.

## Maintainer handoff

From the repository root with the existing locked uv environment and Git, no
credentials or environment variables required:

```powershell
uv run --locked --offline --no-sync python .\validate_t2_bounded_chunked_response_acceptance_review_1.py
if ($LASTEXITCODE -ne 0) { throw 'T2 bounded chunked acceptance review validation failed' }
```

Expected successful final output:

```text
T2-BOUNDED-CHUNKED-RESPONSE-ACCEPTANCE-REVIEW-1 LOCAL DOCUMENT CHECKS PASSED; BOUNDED CHUNKED RESPONSE ARCHITECTURE ACCEPTED; IMPLEMENTATION AUTHORIZED SEPARATELY; NO LIVE EXECUTION AUTHORIZED
```

Paste results before further implementation. Do not rerun the historical proposal
validator against the now-Accepted metadata; this validator checks its preserved
proposal body and evidence at the pinned baseline instead.
