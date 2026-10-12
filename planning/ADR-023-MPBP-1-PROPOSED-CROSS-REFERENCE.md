# ADR-023 MPBP-1 proposed reciprocal cross-reference

Status: Proposed — NOT ACCEPTED.
Package: [GENERATIVE-MEDIA-ADR-027-BLOCKER-RESOLUTION-1](GENERATIVE-MEDIA-ADR-027-BLOCKER-RESOLUTION-1.md).
Semantic owner: Model Runtime/Security maintainer, with Secret Access and media review.
Affected clauses: ADR-023 sections 7–8 and 11–12, relationship metadata only.
Accepted ADR-023 is unchanged. This proposal has no present normative effect.

## Exact candidate text

SRCP-1 remains Model-only. ADR-027 proposes the separate MPBP-1 media
provider-control profile, with its own purpose, source mapping, recipient,
disclosure, attempt/effect contract and qualification. Media receives no authority
by analogy with SRCP-1, no Model consumer identity and no use of the Model
CredentialSource API under a disguised purpose.

Any MPBP-1 admission requires explicit acceptance of ADR-027 and its own bounded
ADR-007 and ADR-010 addenda. Sections 7–8 and 11–12 retain their existing scope.
Private implementation primitives may be reused only through their semantic
owner's approved composition boundary and with independent media qualification.
This cross-reference exposes no private classes, material handle or universal
protected HTTP interface. No upload, job submission, polling, result retrieval
or personal-image disclosure is added to SRCP-1 or MPBP-1.

The reciprocal ADR-027 relationship shall identify those upstream decisions and
their exact acceptance records only when accepted. Until then it shall say that
the amendments and architecture approval are pending. Existing Model source,
disclosure, transport and qualification decisions remain unchanged.

## Risk, residual and acceptance condition

Risk introduced: readers could confuse similarity of mechanisms with shared
authority or qualification; explicit separate names and scope prevent that claim.
Residual limitation: reuse is not evidence that media satisfies the Model profile,
or that a Model-qualified primitive is qualified for the media composition.

Acceptance condition: Model Runtime/Security and Secret Access approve reciprocal
metadata with the paired addenda and ADR-027 acceptance record in a later review.
No accepted-looking text is appended to an accepted ADR in this slice. Approval
is pending; no implementation or live execution is authorized.
