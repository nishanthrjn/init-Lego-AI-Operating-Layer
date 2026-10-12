# ADR-010 MPBP-1 proposed addendum

Status: Proposed — NOT ACCEPTED.
Package: [GENERATIVE-MEDIA-ADR-027-BLOCKER-RESOLUTION-1](GENERATIVE-MEDIA-ADR-027-BLOCKER-RESOLUTION-1.md).
Semantic owner: Secret Access/Security maintainer, with Runtime review.
Affected clauses: ADR-010 section 8.2 step 5, section 8.3 and section 23 scope.
Accepted ADR-010 is unchanged. This proposal has no present normative effect.

## Exact candidate text

MPBP-1 is a separate single-operator, attended, trusted-process media
provider-control profile. It admits at most one empty-body HTTPS bearer probe
exchange under an exact typed purpose, consumer, execution/operation, provider
mapping, recipient, configuration, SecretRef and SecretRevisionRef. It does not
inherit Model SRCP-1 authority. No image, prompt, workflow, repository data,
submission, polling or result retrieval is admitted.

Section 8.2 steps 1–4 and 6 remain unchanged. Every locally effective invalidator,
including mapping/revision retirement, grant/policy/approval change, Principal and
tenant eligibility, binding/configuration retirement, cancellation, close and
source teardown, MUST participate in the same exclusive ordering domain as each
credential-bearing OS acceptance H. Exact-purpose authorization MUST be current
at each H; earlier resolution/acquisition/approval does not establish later use.
One exact revision remains frozen; rotation MUST NOT silently substitute a new one.

Within MPBP-1 only, step 5 is satisfied by a qualified configured remaining-validity
margin at final gate G, a domain-ordered expiry event and a recorded late-handoff
observation after H. The margin MUST cover admitted uncertainty according to its
reviewed basis; absence of a qualified margin refuses use. This is not a proven
upper bound on G-to-H delay. A suspension can make H later than wall-clock expiry;
late use is detected, not necessarily prevented. Strict real-time scopes remain
unsupported. Every partial-write continuation repeats the complete gate and time
checks without resetting the original attempt or deadline.

No equivalent order with independently changing remote provider state is claimed.
The credential recipient MUST be its issuer or an explicitly designated service
bound in its admitted account/provider mapping and exact verified HTTPS origin.
No redirect, proxy, alternate endpoint or credential refresh/fallback is permitted.
An issuer's remote rejection does not establish that no credential use occurred.

All remaining Secret obligations are unchanged: protected reference/material
separation; minimum exact consumer/purpose use; current revision and rotation/
revocation; no raw material in public results, settings, logs, evidence or exception
chains; no material fingerprint; no consumer cache, persistence or replay; durable
pre-use custody; safe effect and repair evidence; independently admitted bootstrap
roots. Source-held material and one-use realization have distinct finite lifetimes
and ordered teardown. No environment, file or generic material-returning source
is authorized. No generic credential broker/framework is created.

MPBP-1 may be enabled only after its source, transport, custody and owner-ordering
implementation is separately authorized and qualified. Section 23 remains SRCP-1
only; unmodified section 8 requirements govern every other Secret-use path.

## Risk, residual and acceptance condition

Risk introduced: a separately named wall-clock timing exception. Its bounds cannot
be inferred from successful network requests or borrowed Model configuration.
Residual limitation: neither remote credential currentness nor physical memory
zeroization, hostile-process isolation or recall of transmitted bytes is promised.

Acceptance condition: Secret Access/Security and Runtime approve the precise
exception, recipient basis, margin qualification rule and paired ADR-007 text;
source, composition and evidence contracts must have no unresolved mandatory
decisions. Approval is pending. No general Secret rule, accepted ADR, implementation
or live authorization changes through this proposal.
