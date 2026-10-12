# ADR-007 MPBP-1 proposed addendum

Status: Proposed — NOT ACCEPTED.
Package: [GENERATIVE-MEDIA-ADR-027-BLOCKER-RESOLUTION-1](GENERATIVE-MEDIA-ADR-027-BLOCKER-RESOLUTION-1.md).
Semantic owner: Architecture/Runtime maintainer, with Security approval.
Affected clauses: ADR-007 sections 6.2 item 7, 6.3, 8 and 18.
Accepted ADR-007 is unchanged. This proposal has no present normative effect.

## Exact candidate text

For MPBP-1 only, after separate acceptance of ADR-027 and the corresponding
ADR-010 timing addendum, one nonblocking OS socket acceptance of credential-bearing
bytes is an admitted protected handoff H inside the final ordered currentness
gate G of section 6.2 item 7. The admitted scope is one exact provider-control
attempt, provider binding, recipient, method/path and Secret revision. This does
not admit generation, image upload, VTO, polling or result retrieval.

G holds the same exclusive live domain as every effective local invalidator.
Immediately before each H, the complete exact authority, revision, recipient,
configuration, lifecycle, resource, approval, disclosure, custody and validity
predicates MUST be current. Claiming an invocation or resolving a Secret is not H.
There is no reusable authorization interval. Private material realization and
wire serialization MUST remain inside the protected owner boundary; a generic
queued client MUST NOT receive a material handle or permission to send later.

DNS, connection, TLS negotiation, readiness waiting, response reads, operator
input and all arbitrary callbacks MUST remain outside G. Only the admitted
nonblocking send step is permitted network I/O inside G. On would-block or partial
write, release G before waiting. Every continuation MUST re-enter G and recheck
the complete current set before sending only the unsent suffix on the same
connection. It MUST NOT retransmit accepted bytes or create a second request.
No reconnect-and-repeat, retry, alternate recipient/provider/family or Secret
fallback is permitted. Zero-progress waiting remains within the original deadline.

Section 8's demonstrated check-to-handoff wall-clock bound is narrowed only for
MPBP-1 according to its separately accepted ADR-010 addendum: configured qualified
margin at G, domain-ordered expiry, and late-handoff detection/evidence after H.
Strict real-time validity at H is unsupported. Wall-clock expiry during suspension
may precede H without being prevented; a late observation cannot undo accepted
bytes. An unavailable observation leaves an unresolved obligation, not a false
claim that H was timely. Section 18's SRCP-1 exception remains unchanged.

If a participating invalidator commits before H, H is refused. If H happens
first, later invalidation stops future sends/continuations but cannot recall bytes.
Unresolved attempts survive as safe custody obligations and MUST NOT be replayed
after crash or restart. No distributed/global atomicity or remote issuer ordering
is asserted. All clauses outside this exact exception remain applicable.

## Risk, residual and acceptance condition

Risk introduced: permitting a credential-bearing send within the gate and
explicitly tolerating the check-time versus handoff-time gap. Nonblocking is not
a real-time scheduling guarantee. Gate occupancy and evidence writes can delay
expiry events; the implementation cannot pretend that a lock stops wall-clock time.

Residual limitation: late use can occur; only local effective events are ordered.
Remote revocation, provider logging and already-disclosed bytes cannot be undone.
Fail-stop fencing is required before replacing a stalled domain incarnation.

Acceptance condition: Architecture/Runtime and Security explicitly approve this
scope and residual together with the ADR-010 proposal, review all participation
rows in the package and settle its remaining mandatory decisions. Record the
qualified margin criterion before enabling any implementation. Approval is pending;
this text does not accept ADR-027 or authorize implementation or live execution.
