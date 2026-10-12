# GENERATIVE-MEDIA-ADR-027-BLOCKER-RESOLUTION-1

Status: Proposed — NOT ACCEPTED.
<!-- GENERATIVE-MEDIA-MPBP1-REMAINING-BLOCKERS-1 CURRENT BEGIN -->
Current resolution record: [GENERATIVE-MEDIA-MPBP1-REMAINING-BLOCKERS-1](GENERATIVE-MEDIA-MPBP1-REMAINING-BLOCKERS-1.md).
Current states: B-01 RESOLUTION_DRAFT_READY; B-02 STILL_BLOCKED; B-03 RESOLUTION_DRAFT_READY; B-04 RESOLUTION_DRAFT_READY; B-05 RESOLUTION_DRAFT_READY. No blocker is CLOSED; all approvals remain pending.
Prior blocker-package document validation: maintainer-run LOCAL DOCUMENT CHECKS PASSED. This new remaining-blockers slice awaits maintainer validation.
Historical baseline, states, reasoning and handoff below describe the preceding slice and are preserved unchanged.
<!-- GENERATIVE-MEDIA-MPBP1-REMAINING-BLOCKERS-1 CURRENT END -->
Baseline: `e1376135509185b9b4f91f4b23d14fc9e501a1d6`.
ADR-027: Proposed. Readiness: Blocked. H-01: OPEN.
M-01: CLOSED. M-04: CLOSED. ADR-026: Accepted.
No blocker is CLOSED. Architecture approval is pending.
Verification: NOT RUN — Awaiting user execution.
No implementation or live execution authorized.
Credentialed media NOT QUALIFIED; remote VTO UNSUPPORTED.
SRCP-1 remains Model-only. No generic credential framework approved.

This package supplies exact candidate addenda and bounded contract proposals.
It does not accept architecture, change production, qualify credentials/providers
or replace the successful maintainer-run document evidence in the
[readiness review](GENERATIVE-MEDIA-ADR-027-READINESS-REVIEW-1.md).
No tests, validators, network, providers or Secret operations ran here.
The five original blockers remain the entire blocker set. Missing decisions below
are assigned to those blockers, not promoted into new blockers.

## 1. Governing evidence and scope

[ADR-027](../adrs/ADR-027.md) proposes one bounded probe, not credentialed media
generally. [ADR-INDEX](../adrs/ADR-INDEX.md) sections 1/14 distinguish proposed,
blocked, ready and accepted; draft language cannot approve its own upstream change.
Accepted ADR bodies and their statuses remain unchanged. Separate proposal files
avoid implying that text appended to an accepted ADR is already normative.

Exact governing clauses: ADR-007 sections 5–8/18; ADR-010 sections 6–15/23;
ADR-023 sections 7–8/11–12; ADR-014 section 15; ADR-026's claim/close contracts;
ADR-009 pre-effect custody and repair duties; ADR-020 decision 8; ADR-024 sections
14/22; SECURITY SEC-020/037/057–060/066–067/075/077/081; CONTRACTS 15.5/CTR-040.
The current public facade's claim is explicitly not permission for a later send.
Its close reports unresolved owner work, rather than stopping an owner's transport.

Read-only implementation evidence:

| Source | Observation and limitation |
| --- | --- |
| [service.py](../packages/legoai-generative-media/src/legoai_generative_media/service.py), `probe_provider` | Current explicit probe resolves raw env credentials, constructs transport and confirms a family; not MPBP-1 authority |
| [discovery.py](../packages/legoai-generative-media/src/legoai_generative_media/discovery.py), `confirm`/`discover` | Explicit confirm is one selected exchange; auto may probe both families and is excluded |
| [legacy.py](../packages/legoai-generative-media/src/legoai_generative_media/drivers/legacy.py), `probe`/`object_response` | GET `/system_stats`, empty body, 1 MiB limit, JSON object with string version; no submit/retrieve call in this path |
| [v2.py](../packages/legoai-generative-media/src/legoai_generative_media/drivers/v2.py), `probe` | Fixed job-ID lookup, not a pure server-status route; reject for the first profile |
| [http.py](../packages/legoai-generative-media/src/legoai_generative_media/http.py) | Existing credential cap 4096 characters, 64 KiB response headers, default request timeout 10 seconds; retains raw Authorization and uses writer.write/drain, so it is not the proposed protected realization |
| [drivers/base.py](../packages/legoai-generative-media/src/legoai_generative_media/drivers/base.py) | Read-only wrapper prohibits body/POST; response observations still require explicit safe classification |
| [runtime/local.py](../src/legoai/runtime/local.py) | Model source provisions its fixed Model purpose/consumer; facade control owners are not automatically joined to the source ordering domain |
| [remote_attempt.py](../src/legoai/runtime/_composition/remote_attempt.py) | Existing attempt construction requires Model disclosure and ModelId; not a media custody schema |

## 2. B-01 proposed upstream language

B-01 state: RESOLUTION_DRAFT_READY.
This describes draft completeness, not amendment approval or blocker closure.

| Proposal | Exact affected clauses | Owner | Risk and residual | Acceptance condition |
| --- | --- | --- | --- | --- |
| [ADR-007 MPBP-1 addendum](ADR-007-MPBP-1-PROPOSED-ADDENDUM.md) | 6.2 item 7, 6.3, 8, 18 | Architecture/Runtime with Security | Nonblocking H inside G; scheduling pause can outlive validity; no strict real-time bound | Explicitly approve the MPBP-1-only exception, paired ADR-010 text and participation contract |
| [ADR-010 MPBP-1 addendum](ADR-010-MPBP-1-PROPOSED-ADDENDUM.md) | 8.2 step 5, 8.3, 23 scope | Secret Access/Security with Runtime | Narrow timing residual and no remote issuer currentness; exact revision and recipient remain mandatory | Approve residual and margin qualification rule; settle source and custody decisions before enabling |
| [ADR-023 reciprocal reference](ADR-023-MPBP-1-PROPOSED-CROSS-REFERENCE.md) | 7–8, 11–12 relationship metadata | Model Runtime/Security with Secret Access/media | Accidental inheritance of Model authority/qualification | Approve reciprocal scope metadata with exact accepted decision references later |

All three files contain exact candidate text, are Proposed — NOT ACCEPTED, and
change no existing accepted ADR. ADR-007's current SRCP-1-only exception and
ADR-010 section 23 cannot already authorize the candidate media behavior.

## 3. B-02 one client route and remaining provider evidence

B-02 state: STILL_BLOCKED.
Sole local client candidate: legacy GET /system_stats.
No supported remote provider route is selected or qualified.

Freeze the proposed local protocol contract to legacy `GET /system_stats` at one
admitted canonical HTTPS origin, with API root `/`, empty body and one bearer
Authorization header. The path is a literal, with no query, fragment, redirect,
caller headers, job identifiers or endpoint-derived substitution. Exactly one
request/connection, no proxy, retry, fallback, refresh or auto-family discovery.
No image, prompt, workflow, repository content or result retrieval. The raw media
transport is not reused as the protected credential boundary.

`GET /system_stats` is sufficiently observational **on the client side**: the
source requests status and extracts a version, without calling submission or
retrieval methods. It cannot prove server-side no-job-creation, authentication
requirements, account recipient identity, billing or logging/retention. The v2
candidate accesses a job namespace; a fixed ID does not prove nonexistence or
exclude a job/result response. No other explicit route is registered in discovery.

Proposed response contract: exactly HTTP 200 and JSON media type; one UTF-8 JSON
object with a `system` object and `comfyui_version` string of 1–64 printable ASCII
characters. Reject duplicate keys, non-finite constants, malformed encoding,
trailing content and nesting above 16 levels. Unknown fields are bounded input,
never authority and never retained or returned. Return only a safe compatible/
incompatible observation and the validated version where disclosure permits.
The existing source does not establish all these stricter parser properties;
they are proposed implementation requirements, not claims of current conformance.

Use HTTP/1.1 with one valid bounded Content-Length response, no transfer encoding,
compression or ambiguous/duplicate framing; no EOF-delimited success. Reject all
3xx without following. Parse 401/403 as rejection without retaining body text.
Other non-200 statuses yield a closed non-success classification, not an inferred
remote effect. A valid version never proves authenticated identity: a public
endpoint may answer 200 despite ignoring a bearer header.

Remaining evidence B-02-PROVIDER: an authoritative provider contract or independently
admitted deployment contract identifying the issuer/designated HTTPS service,
account, bearer acceptance, observational `/system_stats` semantics and permitted
metadata handling. None is established by the inspected client code. No external
lookup is permitted in this slice, and no external facts are asserted. Local
client design can be reviewed now; named-provider activation stays unsupported.
The existing readiness exit also requires that recipient/provider basis, so B-02
is not declared draft-complete merely by choosing a familiar route.

## 4. B-03 source, lifetime and composition

B-03 state: STILL_BLOCKED.
Proposed purpose: media-provider-probe/1.
Proposed consumer: legoai-generative-media/provider-probe@1.
These are closed profile identifiers to be owned by Secret Access/media, not
unrestricted strings accepted from requests and not new canonical Kernel types.

Secret Access owns the protected source, material revision and exact-use decisions.
Runtime owns assembly of authoritative controls; media owns the probe meaning;
driver owns wire serialization. Bootstrap must record the independently admitted
operator Principal, verified tenant, configuration, grant/policy basis, exact
consumer/provider/account mapping and independent local evidence root. Neither
environment possession nor configuration creates that authority.

Candidate S1-shaped source reads one hidden interactive value itself, validates
the credential shape, issues canonical SecretRef/SecretRevisionRef and returns only
the exact reference. One source, one revision, one attempt. No environment, file,
pipe, argument, SDK default, persistence, consumer cache, raw return API, public
bearer handle or material callback. The Model CredentialSource remains unchanged.

After successful provision the source has a proposed 300-second maximum lifetime.
The one-use realization holds material at most the original 10-second probe budget,
and only inside the protected owner. It cannot become adapter configuration.
Completion/denial/cancel/abandonment closes the source and drops use buffers;
teardown is ordered with H. Rotation retires the frozen revision and ends this
attempt; a new revision requires separately admitted intent, never refresh.
Expiry under scheduling suspension has the explicit timing residual, not a physical
zeroization promise. No guaranteed erasure of Python copies, crash dumps or hostile
same-process memory is claimed. No authenticated pool or post-response reuse.

Proposed safe composition inputs are canonical scope/identity/configuration,
exact credential reference, provider binding and typed probe admission; outputs
are safe status/evidence references only. Prefer owner-private reuse behind an
approved composition entry; media cannot import `_source`, `_domain`, private
Secret Access realization or Model attempt builders. Existing generation/VTO offers
cannot stand in for a probe, and ModelId cannot be fabricated for custody.

Remaining decision B-03-SEAM: the existing public source is Model-only and the
execution facade has no protected probe/source integration seam. A concrete
owner-approved placement and exact safe factory contract are still required.
Neither copying enforcement into media nor a generic callback-based broker resolves
that gap. No new public API is proposed as approved here. If a narrow public entry
is chosen, the review must state owner, actual media probe consumer, implementation,
substitution requirement (replace protected realization without exposing material),
why current canonical inputs alone cannot compose it, versioning and security
impact. This unresolved decision is B-03, not a sixth blocker.

Remaining decision B-03-MARGIN: select a configured validity margin and documented
clock-uncertainty/admission basis for the intended host; no measured evidence in
this slice responsibly establishes one. Missing margin must refuse H. Lifetime
ceilings below are policy caps, not evidence for the margin or hard real-time bounds.

## 5. B-04 ordered participation contract

B-04 state: RESOLUTION_DRAFT_READY.
G = final ordered currentness gate in one exclusive live local domain.
H = protected OS credential-bearing send acceptance in that domain.
H is not resolution, TLS preparation, facade claim, queue insertion or provider
response. Every continuation has its own G/H pair for the same attempt.

All rows below must participate before each H. A required participant being absent,
unavailable or independently mutable makes the proposed composition unsupported.
Safe evidence means references/revisions/order observations, never material.

| Invalidator | Owner | Authoritative state | Point observed | Before H? | Continuation behavior | Post-send behavior | Evidence produced |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Principal/tenant eligibility | Identity/Tenant Governance | Verified principal/tenant eligibility revisions | Preliminary checks and each G | Yes | Refuse on changed/ineligible scope | No recall; stop new bytes | Eligibility decision/revision |
| Grant | Governance | Exact current grant/revocation | Each G | Yes | Deny revoked scope | Preserve prior use | Grant/refusal reference |
| Policy | Governance | Effective policy revision/constraints | Each G | Yes | Re-evaluate frozen action; no widening | Preserve prior use | Policy decision/revision |
| Approval | Approval Governance | Bound consumption/expiry ledger | Before consumption, after consumption and each G | Yes | Only same consumed attempt may continue | No automatic refund | Approval use/remaining facts |
| Provider binding publication/currentness | Lifecycle/Catalog | Exact admitted published binding and eligibility | Each G, prepared peer match | Yes | Refuse retired/replaced binding | No alternate provider | Binding revision/retirement |
| Configuration revision | Configuration/Lifecycle | Exact active immutable configuration | Each G | Yes | Refuse stale binding; no substitution | Preserve historical config | Configuration revision |
| Secret mapping | Secret Access | Tenant/purpose/consumer/recipient mapping | Resolution and each G | Yes | Refuse changed target/purpose | No alternate recipient | Mapping/decision reference |
| Secret revision | Secret Access | Exact current revision validity | Acquisition and each G | Yes | Never upgrade frozen revision | Preserve old attribution | Exact revision/use reference |
| Secret retirement | Secret Access | Retirement event | Each G | Yes | No further send | No recall | Retirement order |
| Source teardown | Secret Access | Closed incarnation flag and use handles | Each G | Yes | Disable buffers/continuation | Dispose; retain safe obligations | Close/incarnation reference |
| Cancellation | Runtime/media owner | Attempt cancellation flag | Each G | Yes | Stop future writes; wait outside gate only | Preserve partial/unknown | Cancellation order/extent |
| Execution close | Runtime with Secret Access/media composition | Closed facade/attempt/source admission | Each G | Yes | Close commits in shared domain before return; no later send | Report unresolved owner effects; late settlement allowed | Close order/obligations |
| Deadline/expiry | Each validity owner, coordinated by Runtime | Original deadline, interval, configured margin, expiry event | Each G and after H | Yes, event order only | No deadline reset; refuse exhausted margin | Record late/unknown observation | G/H times, margin basis, violation |
| Required custody availability | Evidence owner | Durable receipt, capacity and custody applicability | Before G and validated at G | Yes | Missing required receipt refuses more bytes | Preserve effect and repair obligation | Receipt/repair identity |
| Frozen wire/recipient binding | Media composition and transport owner | Prepared peer, exact request digest of nonsecret shape and method/path | Each G | Yes | Only unsent suffix on same connection | No reconnect/resend | Safe shape/recipient binding |

Event-order argument: let M be a locally effective invalidator. M and H require
exclusive entry into the same live domain, so M-before-H means G observes M or
fails closed; H cannot proceed on the prior positive state. H-before-M means
accepted bytes are history; M prevents later H events. A pending requested M is
not an effective M until its authoritative owner commits it. A close request
does not claim preemption: once close commits, future H is refused. Existing
facade close alone does not implement this integration.

The private prepared request cannot release material to a generic client or
detached worker. TLS handshake/DNS/connect/operator waits happen outside G.
The credential-free connection is pinned before G; bounded owner operations,
post-consumption checks and durable pre-H intent do not grant reusable authority.
Actual send is one nonblocking step under G, with no arbitrary callbacks. A stalled
holder cannot be bypassed: stop admission, preserve obligations and require confirmed
termination/fencing before replacement. No distributed/global atomicity is claimed.

Clock expiry is the deliberate exception to the M-before-H proof: a wall-clock
instant is not a committed local mutation. Margin plus ordered expiry and post-H
detection cannot prevent all late sends under suspension. No claim is made about
independently effective remote revocation. Approval/resource consumption can remain
after a later participant refuses; independent commits are not a transaction.

Future proof obligations: each row's mutation enters the same domain, no bypass or
reentrancy, material does not escape, close/partial-write races preserve order,
and accepted bytes survive in effects. These require later authorized synthetic
tests, not live proof or implementation during architecture drafting.

## 6. B-05 custody, disclosure and effects

B-05 state: STILL_BLOCKED.
Proposed safe record schema: media-probe-attempt/1.
INTENDED must have durable custody before H.

One attempt/use ID is bound to profile/schema version, verified tenant/principal
references, ExecutionId, OperationRef, contribution/consumer, configuration,
provider/account mapping reference, permitted recipient reference, exact SecretRef
and SecretRevisionRef, closed purpose, GET and `/system_stats`, decision references
(including independent disclosure), validity intervals, margin basis and intent.
Append G/H order/time observations, send extent, response classification, canonical
failure, late-handoff flag (true/false/unknown), resource facts, receipt and unresolved
obligations. Keep prior records immutable; corrections link to the same attempt.

Never record Secret material, fingerprints, Authorization header, raw response body,
unsafe stack trace, image, prompt, workflow, repository content or arbitrary caller
metadata. Reference metadata is tenant-sensitive; public diagnostics expose only
an authorized safe correlation, closed category and effect truth. No raw provider
error code/version is persisted beyond the explicitly validated output contract.

Proposed independent admission: media-provider-control/1, bound to the operator,
tenant, execution/attempt, contribution/configuration, provider/account/recipient,
fixed method/path, expiry, bounds and exact metadata fields. It permits only the
necessary HTTP routing/protocol fields and the separately authorized bearer header
to that recipient. It admits no request body or application/customer data.
The credential gate and disclosure gate are independently necessary; neither can
mint the other. No Model SYNTHETIC class or model-catalog exception is borrowed.
Unknown recipient/metadata conditions refuse before H. ADR-020 decision 8 and
remote personal-image VTO prohibition remain unchanged.

Local append-only durable attempt custody is the smallest candidate; no new remote
backend is selected. Reserve capacity, establish independently authorized root
custody and persist INTENDED before allowing H. A filesystem write without its
qualified durable receipt is insufficient. Keep enough pre-H custody to expose
an unresolved attempt after crash. Post-H write failure cannot become a clean
success or erase effects; reconcile/retransmit the same evidence operation only.
Provider retry, resend, reconnect-and-repeat and query-to-test-credentials are forbidden.

Remaining decision B-05-CUSTODY: name the permitted media custody realization and
independent root authority, required durability/failure model, and bounded
retention/disposition basis. Existing Model attempts require Model identities;
they cannot be reused by inventing a ModelId. No universal retention duration can
be inferred from source. Require operator-authorized retention limits and safe
export/repair ownership; full/unavailable custody refuses new attempts, never evicts
unresolved evidence. This is unresolved under the original B-05 exit.

## 7. Closed failure and effect mapping

Named facts stay separate: acquisition; credential-bearing OS send; remote
credential receipt/use (often unknown); provider response; job submission (not
authorized or performed by this client); custody completion. OS acceptance proves
local handoff, not provider receipt. A complete response does not prove a provider's
absence of logging/billing or authenticate an endpoint that ignores credentials.

| Failure case | Closed result/category | Send extent and retained facts | Permitted next action |
| --- | --- | --- | --- |
| Denied before acquisition | AuthorizationDenied / established TenantViolation or PolicyViolation | NONE; no material acquisition | Safe refusal only |
| Denied after resolution before H | AuthorizationDenied, Conflict or DeadlineExceeded according to established cause | NONE for send; retain prior acquisition/consumption facts | Dispose private use, safe evidence |
| Connect/TLS fails before credential send | DependencyFailure | NONE when pre-send failure is established | No second connection/attempt |
| Zero-byte nonblocking result | Internal pending continuation, not success | NONE only if no bytes ever accepted; otherwise prior extent retained | Bounded readiness wait outside G, same-attempt recheck |
| Partial send | Pending continuation, or ExecutionFailure/DeadlineExceeded on terminal stop | PARTIAL only for proven OS accepted prefix; remote processing UNKNOWN | Continue unsent suffix only under G; otherwise stop |
| Full send, no response | DependencyFailure or DeadlineExceeded | OS send COMPLETED when proven; remote outcome UNKNOWN | Record uncertainty, no replay |
| Complete 401/403 | AuthorizationDenied with authentication/authorization rejection detail | Prior send remains; rejection does not erase Secret use | Safe status only, no refresh/fallback |
| Timeout after possible send | DeadlineExceeded | UNKNOWN unless stronger prefix/full-send facts exist | Stop future writes, retain obligations |
| Malformed response | VersionMismatch / closed protocol-invalid detail | Prior send retained; no validated compatibility | No body retention or second probe |
| Other non-200, including redirect | DependencyFailure / closed status-rejected detail | Prior send retained; no inference of no remote effects | Never follow Location or retry |
| Evidence write failure before H | PolicyViolation if mandatory custody absent; DependencyFailure for unavailable owner | NONE for new send; earlier local costs remain | No H; preserve owner-local failure |
| Evidence write failure after H | ExecutionFailure with custody-incomplete detail | Actual/UNKNOWN extents preserved | Repair evidence only under current authority |
| Process crash after H | Recovered unresolved attempt; no invented successful terminal state | UNKNOWN unless durable stronger send/response facts exist | Fence old incarnation; evidence recovery/intervention, no replay |

Unknown acquisition, late-handoff time or receipt stays unknown. Categories above
map to existing canonical errors; internal detail labels are closed proposed media
vocabulary, not new Kernel states. Partial approval consumption is not refunded
automatically. Only full bounded structured 200 yields client compatibility, not
credential, security, generation or live qualification.

## 8. Proposed numeric ceilings and unresolved parameters

Numbers below are proposed limits, not measured security guarantees. Counts/byte
caps are enforceable contract bounds; deadlines are fail-closed policy limits with
the explicit scheduler residual. None establishes a qualified G-to-H margin.

| Quantity | Proposed maximum | Basis and disposition |
| --- | --- | --- |
| Attempts, exchanges, recipients, revisions | 1 each | Exact MPBP-1 scope; no retry/reconnect/replay |
| Credential | 4096 printable ASCII bytes | Existing media `_authorization` cap; no CR/LF/space; candidate limit, not remote acceptance evidence |
| Serialized exact reference | 2048 UTF-8 bytes per reference | Conservative profile ceiling to bound safe records; reject oversize canonical serialization, never truncate/change identity |
| Request body | 0 bytes | Selected GET contract |
| Request headers including request line | 8192 bytes total | Conservative ceiling: 4096-byte bearer plus bounded host/fixed fields; reject overflow rather than expand |
| Response headers | 65536 bytes total | Existing media header ceiling, now paired with strict framing |
| Response body | 1048576 bytes | Existing legacy probe ceiling; not a permission to retain metadata |
| JSON nesting and returned version | 16 levels; 64 printable ASCII characters | Conservative parser-depth ceiling; existing profile version cap respectively |
| DNS/connect/TLS combined | 5 seconds, within remaining total | Existing remote connect cap min(5, timeout/2) at default 10 seconds; no wait inside G |
| Request/send/read interval | 10 seconds maximum, never beyond original overall deadline | Existing transport default chosen as a tighter profile ceiling than supported 60 seconds |
| Overall probe after operator admission | 10 seconds including preparation/custody/connect/send/read | Conservative one-request ceiling; no summed per-stage extensions |
| Per-use material hold | Remaining overall budget, at most 10 seconds | Match one exchange; destroy realization on termination; no waiting for operator input with a live use |
| Source lifetime after successful provision | 300 seconds or attempt termination, whichever first | Conservative five-minute attended setup policy; not borrowed Model authority; expiry/close must prevent future use |
| Evidence record | 65536 serialized UTF-8 bytes | Conservative safe-reference schema ceiling; reject oversize before H; never truncate mandatory facts |
| Active attempts per source | 1 | Avoid concurrent material reuse; no pool/cache |
| Validity margin / clock uncertainty | UNRESOLVED: B-03-MARGIN | Requires host-specific reviewed qualification basis; missing value refuses use |
| Durable record retention/capacity policy | UNRESOLVED: B-05-CUSTODY | Evidence owner must set finite aggregate capacity and governed retention/disposition; full store refuses, unresolved records never silently evicted |

Hidden input happens before the timed probe and outside G. The source lifetime
starts only on successful provision, not an unbounded reusable provisioning session.
One bounded synchronous hidden read can still block awaiting the human; no material
exists in the source until it succeeds. If the host requires cancellable timed
input, that mechanism requires separate qualification rather than a detached reader.
All finite ceilings require owner approval and future synthetic enforcement tests.

## 9. Public API and design-principle review

No public API added or approved. Existing canonical safe values are retained.
No Model concepts move into media; no media protocol concepts move into Core.
The unresolved B-03 composition seam must not expose source/domain internals.

| Principle | Proposed disposition |
| --- | --- |
| SRP / SoC | Source/use authority, media meaning, wire transport, governance, lifecycle and evidence keep separate owners |
| OCP | A driver can change only behind the closed profile and its newly reviewed binding; configuration cannot add routes |
| LSP | Model and media are not substitutable; any eventual provider realization must preserve probe/error/effect contract |
| ISP | One probe does not require upload, refresh, enumeration or material-export methods |
| DIP / Law of Demeter | Public safe contracts and owner composition only; no traversal of private source or ordering state |
| DRY | Reuse exact owner semantics without cloning enforcement or using dummy Model IDs; seam remains explicitly unresolved |
| KISS | One source/revision/provider/family/recipient/exchange/attempt |
| YAGNI | Reject generic credential framework, universal protected HTTP, broker/service, material callback, workflow engine, global registry and broad provider abstraction |

## 10. Blocker exit matrix

RESOLUTION_DRAFT_READY means candidate text is reviewable, not approved or closed.
STILL_BLOCKED means a mandatory architectural choice/evidence remains missing in
addition to approval. Later implementation proof is listed separately; no live test
is demanded as a prerequisite to drafting architecture.

| ID | State | Owner | Proposed resolution / documentary evidence | Remaining approval | Remaining implementation proof | Exact exit condition |
| --- | --- | --- | --- | --- | --- | --- |
| B-01 | RESOLUTION_DRAFT_READY | Architecture/Runtime and Secret Access/Security, with Model owner | Section 2 and three separate exact proposed addenda | Explicit upstream addenda/residual/cross-reference decisions | Gate/transport/time qualification after implementation authorization | Owners accept scoped addenda with recorded references; no implicit SRCP-1 inheritance |
| B-02 | STILL_BLOCKED | Media provider-contract maintainer and Security | Section 3 freezes sole local client candidate and excludes v2; section 8 bounds | Provider/issuer/recipient and observational contract basis not supplied | Parser/framing/bounds and later named-provider qualification | Supply B-02-PROVIDER authoritative evidence and approve fixed single-exchange contract without widening to jobs/results |
| B-03 | STILL_BLOCKED | Secret Access source owner and Runtime composition maintainer with media | Section 4 source/purpose/lifetime proposal; section 8 caps | Exact B-03-SEAM and B-03-MARGIN decision/basis missing | No-leak, revision/teardown, wrong-purpose/recipient and timing fixtures | Approve concrete safe owner composition placement and source admission with qualified margin criterion; retain no material API |
| B-04 | RESOLUTION_DRAFT_READY | Runtime with Governance, Lifecycle, Secret Access and Evidence | Section 5 complete owner/invalidator matrix and conditional order argument | Review shared-domain participation contract | All invalidator races, close, partial writes, fencing/no-bypass | Owners accept every participant and handoff contract; implementation proof remains a later enablement gate |
| B-05 | STILL_BLOCKED | Evidence Custody and Secret Access with media disclosure/effect owner | Sections 6–8 schema, admission and failure mapping | B-05-CUSTODY root/durability/capacity/retention decision missing | Pre/post-H failure, crash recovery, safe evidence and evidence-only repair | Approve bounded media custody realization/root/disposition and independent disclosure admission without Model identity substitution |

## 11. Maintainer validation and next action

Prerequisites: repository root, Git and existing locked uv/Python environment.
No credential environment variables or dependency acquisition required. The new
validator checks only local document/repository invariants and synthetic document
fixtures, not production behavior. Scope is these five new files; ADR-027/index,
prior evidence, accepted ADRs, production and dependencies remain unchanged.
Working and staged snapshots are checked independently; an incomplete staged
package is refused. No internal execution has been performed.

```powershell
uv run --locked --offline --no-sync python .\validate_generativemedia_adr_027_blocker_resolution_1.py
if ($LASTEXITCODE -ne 0) { throw 'ADR-027 blocker-resolution validation failed' }
```

Expected evidence: LOCAL DOCUMENT CHECKS PASSED; PACKAGE INCOMPLETE; ADR-027
PROPOSED; READINESS BLOCKED; H-01 OPEN; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED.
Passing checks establish document invariants only, not security/credential/provider
qualification. Paste the full log before further changes.

After a pass, the next action is a separately authorized document-only resolution
of B-02-PROVIDER, B-03-SEAM/MARGIN and B-05-CUSTODY with their owners. Source-only
evidence cannot manufacture the absent remote contract or custody authority.
B-01/B-04 drafts can be reviewed in parallel conceptually, but no approval is
recorded here. Once the package is complete, conduct an explicit upstream/addendum
architecture acceptance review, then a fresh ADR-027 readiness review after required
upstream decisions are accepted. Neither step is ADR-027 implementation.

Proposed commit: `docs(security): draft ADR-027 blocker resolutions and upstream addenda`

## 12. Final package decision

Unresolved: B-02 lacks a provider/recipient contract; B-03 lacks a concrete safe
composition seam and margin basis; B-05 lacks approved custody/root/retention basis.
B-01 and B-04 have reviewable drafts but remain unapproved. All five original
blockers remain unresolved; ADR-027 is not Ready for Decision.

BLOCKER_RESOLUTION_INCOMPLETE
