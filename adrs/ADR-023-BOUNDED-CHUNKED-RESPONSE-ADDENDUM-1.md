# ADR-023 proposed addendum: bounded chunked response framing

Status: Proposed — NOT ACCEPTED.

Owner: T2 protected HTTPS transport. Parent: [ADR-023](ADR-023.md),
especially §7.3; application result semantics remain [ADR-014](ADR-014.md)
§14.8 and §14.12. Review: [decision and evidence](../planning/T2-BOUNDED-CHUNKED-RESPONSE-ADR-1.md).

## Authority and classification

This standalone bounded addendum proposes an implementation-compatible response
framing extension inside the existing HTTP/1.1 owner. ADR-023 does not establish
Content-Length-only framing as an architectural guarantee or reject chunked
framing explicitly. Its streaming revisit trigger concerns streaming semantics;
this proposal still delivers one complete ordinary response. ADR-014's minimal
application subset, identity checks and errors remain unchanged.

Under ADR-INDEX §14, accepted decision bodies remain immutable. This document
neither edits nor supersedes them, allocates no new ADR number, and grants no
implementation authority. The maintainer must explicitly accept the addendum
before a separately scoped implementation. Any broader architectural change
requires the new-ID/supersession process. Registration/acceptance metadata is
deferred to that decision; the review links this proposal for discovery.

## Proposed contract

The following table is the single authority for this proposed profile. Existing
Content-Length behavior remains subject to its existing contract and regression
qualification; the new branch accepts HTTP/1.1 only.

| Property | Proposed value |
|---|---|
| Protocol | HTTP/1.1 response chunking only |
| CL plus TE | Hard refusal, including duplicate/conflicting field forms; never prefer either |
| Transfer coding | One field, one token chunked, ASCII case-insensitive, surrounding SP/HTAB only |
| Coding chains | Refuse duplicate TE fields, comma lists, parameters, compression and unknown codings |
| Chunk size | 1–6 ASCII hexadecimal digits, upper/lowercase; leading zeros within that limit |
| Extensions | Refuse every chunk extension; maximum accepted extension bytes/count: 0/0 |
| Trailers | Refuse every nonempty trailer section; maximum accepted trailer bytes/fields: 0/0 |
| Line ending | Exact CRLF; no bare LF, whitespace around size, signs or 0x prefix |
| Terminal | Zero size followed by CRLF and empty trailer-section CRLF required |
| Decoded body cap | 4194304 bytes, existing T2 response-body cap |
| Header cap | 32768 bytes including terminator, at most 64 fields, every completion path |
| Size-line cap | 8 bytes including CRLF |
| Framing cap | 32768 encoded framing bytes, excluding headers and decoded data |
| Chunk-count cap | 6552 nonterminal chunks; terminal zero is separate and ends parsing |
| Encoded body cap | 4227072 bytes, decoded body plus framing caps |
| Deadline | Existing absolute monotonic attempt deadline; never reset per chunk/read |
| Delivery | One fully decoded bounded body only after terminal and empty trailers complete |
| Failure after send | UNKNOWN where remote work may have occurred; no partial-body delivery |
| Retry | None; no replay, resume, fallback or automatic model reselection |
| Provider branch | None; generic private T2 framing, never a KiSSKI-specific transport |
| Streaming | stream=false; SSE and model-token streaming unsupported |
| HTTP/2 | Excluded |

## Grammar and deliberately restricted interoperability

Accept a sequence of positive-size chunks, each with exactly the declared data
octets and trailing CRLF, followed by a zero-size last chunk and the empty
trailer section. Data is opaque: embedded CRLF or hexadecimal text in data is
not framing. Zero-size bodies are framing-valid; the application can still
reject an empty JSON response. Reject bytes already buffered beyond the terminal
boundary; close the single-use connection without waiting for EOF or accepting
another response. Completion is a framing boundary, not a promise about future
bytes a peer might send after close.

[RFC 9112 §7.1–7.1.3](https://www.rfc-editor.org/rfc/rfc9112.html#section-7.1)
defines chunked framing and its terminal/trailer structure. Section 7.1.1
requires general recipients to ignore unrecognized extensions. This proposal
deliberately refuses extensions and nonempty trailers: it is a restricted
interoperability profile, **not a fully conforming general RFC 9112 recipient**.
Accepted messages use RFC chunk framing; unsupported valid messages fail closed.
No live evidence establishes whether SAIA uses extensions or trailers. Supporting
them later requires a reviewed, bounded grammar extension, not a silent fallback.

The six-digit bound is sufficient to represent the existing 4 MiB cap (400000
hexadecimal). Longer numerals, including excessive leading zeros, are outside
this subset. Compare size against remaining decoded capacity before reading or
allocating its data. The framing budget reuses the header metadata budget as a
separate finite allowance, not a provider capacity claim. A positive chunk costs
at least five framing bytes; the final terminator costs at least five. Thus
floor((32768 - 5) / 5) = 6552 bounds nonterminal chunks independently of payload
size. The byte budget also covers larger size numerals and the terminal line.
Required final empty-section CRLF is framing, not accepted trailer content.
These caps intentionally reject excessively fragmented otherwise-valid messages.

## Parser, deadline and security

Reuse header parsing and dispatch exactly once to fixed-length or chunked
framing. Validate CL+TE before either path. Do not accept close-delimited bodies
as a fallback. The current parser's completed-header path needs an explicit
32768-byte check as well as its incomplete-header check in the later slice;
this closes a gap rather than treating the old implementation as proof.

Use private incremental states: SIZE_LINE, DATA, DATA_CRLF, TERMINAL_CRLF,
COMPLETE or FAILED. Read one bounded line, validate its size and both budgets,
consume exactly that chunk, require CRLF, repeat. Zero enters TERMINAL_CRLF;
the next bytes must be CRLF, otherwise refuse trailers. Never accumulate the
entire encoded response and decode afterward. A bounded decoded buffer, an
8-byte line buffer, counters and a bounded input buffer suffice. Reuse the
existing at-most-65536-byte receive unit, processing/discarding framing as it
arrives. Check limits before retention; copying at delivery may use a bounded
constant multiple of the body cap, never an unbounded raw accumulator.

Every read and parser continuation checks the same monotonic deadline;
available buffered data does not bypass it. No per-chunk timeout renewal or
slow-drip extension. Timeout stage remains an observation, not an authorization.
TLS verification, exact recipient binding, protected credential handoff and send
ordering remain unchanged. Response reads stay outside Secret ordering. Keep
one connection per attempt, no proxy, redirect, pooling, retry or fallback.
No credential, payload, framing text or trailer enters custody or diagnostics.

## Effect and result truth

Malformed size, missing CRLF, premature EOF, close before terminal zero,
mid-chunk timeout, timeout before zero, cap overflow and parser failure after
any decoded bytes all retain UNKNOWN after a sent request where remote work
may have occurred. Never translate protocol failure to effect NONE. Do not
deliver partial decoded bytes. Existing pre-send failure semantics are unchanged.

Terminal zero alone is insufficient: terminal framing and the empty trailer
section must complete within every bound. Only then may the existing complete
HTTP status mapping and adapter JSON/model/finish validation run. HTTP 200 or
successful framing alone is not application success or provider qualification.
Custody settlement and cancellation/reconciliation retain their existing owner.

## Application separation and safe diagnostics

Chunked framing is distinct from SSE. Keep Model stream=false and complete
JSON parsing. SSE indicated by text/event-stream or application semantics must
be refused, even if the transfer framing completes. Later implementation must
verify the existing adapter refusal and preserve that boundary; if content-type
evidence is not available there, use a private bounded transport header check
without adding a public Model API. No transparent decompression or arbitrary
content/transfer-coding support is introduced. HTTP/2, request-body chunking,
infinite bodies, pooling and token delivery are excluded.

Preserve existing closed receive diagnostics and their failure isolation.
Possible additions are bounded chunks_observed (0–6552), decoded_body_bytes
(0–4194304), terminal_chunk_seen and trailer_present flags. Existing
body_bytes_observed remains an encoded-wire observation, never relabeled decoded.
Counters saturate safely if reporting a rejected over-limit event; cap_reached
records refusal. No payload, extension, trailer content, Authorization, raw header
or response-body output. Diagnostics remain optional evidence, never control input,
and their collection failure cannot alter settlement or release partial data.

## Consequences and acceptance

This adds parser complexity and an explicit restricted-profile interoperability
limit in exchange for ordinary bounded JSON interoperability. It is provider
neutral and reversible by refusing the new framing branch; existing successful
Content-Length contracts must remain unchanged. No new Port, Model API, worker,
provider abstraction or dependency is warranted.

Acceptance requires maintainer architecture review of these caps and restricted
RFC scope. Implementation qualification and any new live authorization remain
separate. Required observable cases and the staged live plan are in the linked
review. No implementation, credentials, provider call or acceptance occurs here.

Final decision: T2_BOUNDED_CHUNKED_SUPPORT_RECOMMENDED
