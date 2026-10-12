# GENERATIVE-MEDIA-ADR-027-READINESS-REVIEW-1

Date: 2026-10-12.
Review baseline: `5dd89f66cc1207ca22c8a9704a002c4d4f9ab67c`.
Readiness decision: ADR_027_BLOCKED
ADR-027 status: Proposed; MPBP-1 readiness: Blocked.
H-01: OPEN. M-01: CLOSED. M-04: CLOSED.
Verification: NOT RUN — Awaiting user execution.
No acceptance, implementation or live execution authorized.
Credentialed media NOT QUALIFIED; remote VTO UNSUPPORTED.

This is a source-based readiness review by the implementation assistant, not an
independent security certification. The maintainer supplied successful facade
and media migration validation, including migration's 529 tests, isolated wheel
invocation, typing, lint and formatting. Those results establish their stated
local scope only. No checks, imports of project code, Secret resolution,
environment credential reads, provider calls or network access ran in this review.

Authority: [ADR-INDEX](../adrs/ADR-INDEX.md) sections 1 and 14 require an affected
option to remain blocked while an upstream amendment or mandatory evidence is
missing. Readiness and acceptance are separate. ADR-027's historical context
predates M-04 closure and ADR-026 acceptance; new header metadata records current
prerequisites without rewriting that history.

## 1. Current H-01 call chain

Inspected implementation, not just planning claims:

- [config.py](../packages/legoai-generative-media/src/legoai_generative_media/config.py):
  `ProviderConfig.secret_ref` is a string constrained to `env:NAME`;
  `resolve_secret` reads the supplied mapping and returns raw text. This is not
  canonical Secret reference resolution or exact revision/use authorization.
- [service.py](../packages/legoai-generative-media/src/legoai_generative_media/service.py):
  `_driver` and `probe_provider` resolve the string from the supplied mapping or
  `os.environ`, pass the token into a transport factory, then discover/confirm.
  Explicit family construction skips discovery but still constructs a transport
  holding the token. `probe_provider` explicitly confirms the selected family.
- [http.py](../packages/legoai-generative-media/src/legoai_generative_media/http.py):
  `LocalHTTP` and `RemoteHTTPS` retain `_authorization`; `_exchange` serializes it
  and calls `writer.write`/`drain` without an ordered exact Secret-use gate.
- [local_host.py](../packages/legoai-generative-media/src/legoai_generative_media/local_host.py)
  and [composition.py](../packages/legoai-generative-media/src/legoai_generative_media/composition.py)
  now use the public execution facade. Their generation/VTO claim and settlement
  do not authorize construction-time credentials or the separate probe path.

```text
configured env:NAME -> mapping lookup -> raw token -> retained bearer header
  -> discovery/explicit confirmation -> request write
                 missing: exact current Secret-use enforcement
```

The [public facade](../src/legoai/runtime/local.py) explicitly documents `claim`
as not permission for a later protected send. `close` stops facade admission and
reports unresolved work; it does not supervise an owner's provider operation.
M-01 closure removes private Core imports. M-04 refuses remote VTO before driver
construction. Neither fixes H-01. Existing raw-token behavior is inspected debt,
not permission to reuse it for MPBP-1.

## 2. ADR-027 proposed profile

[ADR-027](../adrs/ADR-027.md) proposes MPBP-1: one explicitly selected provider,
one family, one bounded empty-body HTTPS bearer provider-control exchange, one
exact Secret revision and one attempt. Retain this scope. Exclude image upload,
VTO submission, generation submission, polling, result retrieval, personal-image
disclosure, arbitrary URLs/headers and automatic discovery or fallback.

This is a real operator need: the existing public `probe_provider` diagnoses API
family compatibility independently of generation. It is independently testable
with a synthetic transport and structurally separable from image/workflow input.
It is useful only as bounded compatibility/authentication observation, never proof
that generation succeeds or that a remote provider is safe. The need is real;
the exact first credentialed provider contract is still missing (B-02).

## 3. Actual probe semantics

Source: [discovery.py](../packages/legoai-generative-media/src/legoai_generative_media/discovery.py),
[legacy.py](../packages/legoai-generative-media/src/legoai_generative_media/drivers/legacy.py),
[v2.py](../packages/legoai-generative-media/src/legoai_generative_media/drivers/v2.py),
[drivers/base.py](../packages/legoai-generative-media/src/legoai_generative_media/drivers/base.py).

| Property | Current source evidence | MPBP-1 disposition |
| --- | --- | --- |
| Legacy | GET `/system_stats`, empty body, at most 1 MiB response; structured `system.comfyui_version` | Possible candidate, not a selected authenticated provider contract |
| v2 | GET `/api/v2/jobs/00000000-0000-4000-8000-000000000000`, empty body, at most 64 KiB; expects structured job-not-found; 401/403 are authorization errors | Uses a fixed identifier, not customer data; still queries a job namespace. Cannot assume nonexistence, harmlessness or permission. Do not designate this as the first MPBP-1 route without resolving the job-lookup exclusion |
| Explicit family | `confirm` makes one selected probe; total budget 2 times request timeout | Select one reviewed family only |
| Auto | v2 followed by legacy; total budget 3 times request timeout | Excluded; can send credentials more than once |
| Timing | Each request bounded by remaining monotonic budget and request timeout; transport requires 0 < timeout <= 60 seconds; remote connect/TLS <= min(5 seconds, timeout/2) | Existing ceilings are observations, not adopted MPBP-1 timing/holding guarantees |
| Request bounds | Empty probe body; generic transport path <=8192 characters, bearer input <=4096 characters; broader generic body ceiling is 16 MiB + 64 KiB | Close method/path/header shape and total wire bound; do not inherit upload-sized authority |
| Response framing | Header ceiling 65536 bytes; content-length, bounded chunking or bounded EOF; no encoded response; duplicate headers refused | Choose and document MPBP-1 framing/parser contract; existing media framing is not SRCP-1 qualification |
| Redirect/retry | No transport retry or proxy; local redirects refused, remote 3xx returned without following | MPBP-1 refuses redirects, no follow-up request or alternate recipient |
| Diagnostics | `observed` selects status, normalized media type and error-code identifier, not bodies/messages; provider version can reach profile after validation | Bound and close diagnostics; untrusted identifier text is not inherently safe. No raw body, header, credential or chained unsafe exception in evidence |
| Failure | Malformed/version-incompatible evidence, authorization error, dependency failure and timeouts remain distinguishable in source | Use canonical categories with independent send/use/effect observations; absent authority is not fabricated invalid credentials |

GET and a method named probe do not prove side-effect freedom. Provider logging,
credential disclosure, quota/accounting or a job lookup can occur. Source inspection
does not establish server-side authorization requirements, retention or a provider
promise of no job creation. No named remote endpoint is qualified here. MPBP-1
needs a documented observational route with no job submission or result retrieval;
if neither existing route fits, stop rather than silently broaden the profile.

## 4. ADR-007 currentness analysis

[ADR-007](../adrs/ADR-007.md) sections 5, 6.1–6.3, 7 and 8 require more than
resolution-time checks or a timestamp before send. Preliminary resolution and
acquisition are protected for their own purposes. Immediately before the actual
credential-bearing acceptance H, a common ordered interval must cover the complete
current authority, Secret revision, recipient, configuration, lifecycle, approval,
resource, evidence and time predicates. A queue/claim is not H.

Proposed sequence: safe reference resolution -> protected material acquisition ->
credential-free DNS/connect/TLS preparation -> durable intended-attempt custody ->
final ordered gate G -> protected realization handoff -> nonblocking OS send H.
Material acquisition and TLS preparation may be reordered outside G if bounded;
neither authorizes H. Pre-use evidence must exist before H in either ordering.
Every partial-write continuation re-enters the gate; readiness/response waits occur
outside. There is no reusable authorization interval between handing material to a
generic client and that client's eventual send.

Required addendum to ADR-007 section 6.2 item 7 and section 8, alongside section 18:
admit only MPBP-1's bounded nonblocking credential-bearing socket acceptance inside
the gate; forbid waiting, callbacks, DNS/connect/TLS inside it. Adopt explicitly,
if approved, the SRCP-shaped residual: configured conservative validity margin at G,
domain-ordered expiry, late-handoff detection after H, no guaranteed wall-clock
check-to-H bound. Strict real-time scopes remain unsupported. Section 18 currently
names SRCP-1 only; a media profile cannot inherit it. Architecture/Runtime and
Security owners must approve the exact bounded addendum and residual (B-01).

## 5. ADR-010 compatibility

[ADR-010](../adrs/ADR-010.md) sections 5–15 and
[CONTRACTS](../contracts/CONTRACTS.md) section 15.5/CTR-040 keep resolution,
acquisition, exact-use authorization, protected handoff and transport send distinct.
Successful resolution grants no permission to use. Canonical safe references and
revision identities replace raw string interpretation at the admitted boundary.

Purpose/consumer, account/recipient, current grant, exact revision, bounded use,
rotation and safe evidence are compatible design requirements. The selected
timing alternative is **not fully conformant under current wording**: section 8.2
step 5 requires actual-use validity through a qualified bound or atomic mechanism.
Section 23 narrows that only for SRCP-1. Required separate MPBP-1 addendum must
describe local ordering, G margin, post-H violation evidence, unsupported strict
time scopes and the remote issuer revocation limit. It must not waive exact-use,
no-material-public-results, revocation or recipient constraints (B-01).

SEC-020/037/057–060/066–067/075/077/081 in
[SECURITY](../security/SECURITY.md) remain binding. No universal credential broker,
ambient lookup, file store or generic material-returning service follows.

## 6. ADR-023 relationship

Choose a media-specific similarly shaped profile, with reusable generic Secret
semantics and a reciprocal cross-reference: options B and C in the review request.
[ADR-023](../adrs/ADR-023.md) sections 7–8 and 11–12 supply prior accepted Model
semantics, not media authority. Keep SRCP-1, Model purposes and public Model
CredentialSource unchanged. The required cross-reference must identify MPBP-1 as
separate, its upstream addenda, accepted residual and excluded media actions.

[ADR-014](../adrs/ADR-014.md) section 14.18 remains Model-scoped; section 15 and
[ADR-026](../adrs/ADR-026.md) permit secret-free execution composition only.
[ADR-024](../adrs/ADR-024.md) section 22's model-catalog exception is not a media
admission. Reuse of private S1/transport primitives, if later approved, must remain
inside their owner; consumers must not import or traverse private Core classes.

## 7. Purpose and recipient binding

Minimum exact-use identity uses existing canonical values where available:
requester/acting Principal and verified TenantContext; ExecutionId/OperationRef;
consumer identity/version and admitted capability/contribution; operation=probe;
ConfigurationRevisionRef; SecretRef and exact SecretRevisionRef; trusted provider
binding/issuer or designated service and account mapping; canonical HTTPS origin,
API root, closed method/path; one attempt/use identity; count=one exchange and
finite validity window; current grant/policy and applicable approval references.

These dimensions prevent tenant/deputy confusion, use substitution, stale material,
endpoint substitution and replay. A free-form purpose label alone provides none of
those guarantees. Define one closed media probe purpose owned by Secret Access and
media, not `remote-model-bearer`; do not invent dummy Model identities or assume a
canonical `ProviderId` type when the admitted provider binding supplies identity.

Bind both trusted logical provider/account identity and exact HTTPS destination.
An origin string alone cannot prove the credential's issuer/designated recipient;
a provider label alone permits endpoint substitution. Freeze configuration and
check binding retirement before each H. Resolve/connect/TLS against that binding,
verify certificate and hostname, retain the prepared connection identity, forbid
redirects/proxies/alternate origins. No new certificate-pinning requirement is
inferred. DNS/TLS authenticates the admitted destination within the stated threat
scope; it does not prove remote policy/currentness or defeat a compromised issuer.

## 8. Material lifetime and source

Current env:NAME is inadequate. Smallest candidate is a separately admitted
S1-shaped hidden interactive source that reads input itself and returns only an
owner-issued exact reference. Existing `open_credential_source` is pinned to the
Model purpose/consumer; its public API does not authorize a media mapping.
No adequate supported media source is established today (B-03).

Distinguish protected source custody from a one-use material realization. The
candidate source holds immutable material only in its bounded process incarnation;
the private realization may hold it only for the bounded exchange and permitted
continuations. No consumer cache, reuse across polling, raw adapter configuration,
public handle, config serialization, log/repr/exception, fixture or evidence copy.
End the one-probe source/use lifecycle after completion or abandonment; no retained
authenticated client/session. Specify numeric hold/close bounds before implementation.
Source teardown disables future use; Python physical zeroization, crash-dump
protection and hostile same-process code resistance are not claimed. Rotation
creates a new exact revision; no silent upgrade or retry with a fresh credential.

## 9. Disclosure separation

Credential authority != disclosure authority. Empty body and closed route prevent
prompt, image, personal-image, workflow and repository-content transfer; they do
not eliminate credential disclosure and network/account metadata. Require a media
provider-control admission for that exact minimized exchange and recipient.
No Model disclosure class, including SYNTHETIC, or Model catalog admission is
automatically applicable. Any identifying application input or job-result retrieval
would require separate review and is outside MPBP-1 (B-02/B-05).

[ADR-020](../adrs/ADR-020.md) decision 8 remains unchanged: remote personal-image
VTO is unsupported. A valid probe credential or successful response changes none
of its upload, retention, deletion or disclosure gates.

## 10. Retry and effect semantics

One authorization admits one bounded attempt. No retry, fallback Secret/provider,
alternate endpoint/family, hidden refresh or uncredentialed fallback. Nonblocking
continuations complete the same request under current gates; they are not a second
HTTP exchange. Unknown completion is not resolved by replay.

Separate named facts: acquisition, protected credential use/send extent,
provider-control response, and job effect (no job submission authorized).
A local refusal before any protected bytes can establish send NONE; a send error
after possible bytes requires UNKNOWN or PARTIAL only where actually established.
A complete 401/403 can establish rejection while credential use still occurred.
A 2xx does not qualify generation, retention or broader credential compatibility.
No acknowledgement is not evidence of no effect. Preserve consumed approval,
acquisition costs and outstanding custody duties; do not invent refunds.

Map malformed input to ValidationError, absent authority to AuthorizationDenied
or the established policy/tenant category, deadline to DeadlineExceeded, stale
binding to Conflict, unavailable transport to DependencyFailure, incompatible
profile to VersionMismatch as established. Body messages cannot set authority or
error categories. Final safe mapping belongs to the reviewed media contract (B-05).

## 11. Invalidation and revocation ordering

| Point | Required behavior |
| --- | --- |
| Before resolution | Deny unavailable/currently invalid scope; no acquisition or external use |
| After resolution, before H | Final exact gate observes rotation/revision retirement, grant/policy/binding changes, cancellation/close and expiry; refuse and dispose use material |
| After private handoff, before OS acceptance | Private handoff must not escape the same protected boundary. An effective earlier invalidator prevents H; queued client work cannot retain permission |
| After send, before response | Stop future continuations/new sends when invalidated; cannot recall accepted bytes. Retain actual/unknown credential disclosure and remote effects |
| After response | Preserve safe attribution and obligations; retire source/use state. Revocation does not rewrite historical effects |

Secret Access owns mapping/revision rotation and retirement; Governance owns
grant/policy/approval; Lifecycle owns provider binding/configuration eligibility;
Runtime owns facade admission/close and cancellation integration. All locally
effective invalidators, including source teardown and expiry handling, must enter
the same ordering domain as G/H. A revision change selects no new revision for the
frozen attempt. Reopening a facade restores no old authority. Existing facade
registries/close and the Model source domain do not prove this shared participation.
An owner-by-owner integration contract and no-bypass argument are missing (B-04).
Independent remote issuer revocation is not locally serialized; only the explicit
accepted recipient/timing residual may narrow that claim, never implicit rollback.

## 12. Evidence record

Minimum restricted safe record: schema/profile version; tenant and principal safe
references; consumer/contribution/configuration; execution/operation/attempt/use
IDs; provider/account mapping reference and recipient; exact SecretRef/revision;
closed purpose/method/path; admission, grant/policy/approval decision references;
validity bounds and G/H ordering/time observations; intent/acquisition/send/response
classification; canonical failure and per-effect extent; resource observations;
late-handoff flag; custody receipt and unresolved repair/disposition obligations.

Use references to sensitive endpoint/account metadata where full text is not
authorized. Public output is a safe category/correlation and truthful effect extent;
restricted evidence needs tenant-aware access and bounded retention. Never retain
Secret bytes/fingerprints, Authorization header, raw response body, unsafe payloads
or diagnostic stack chains carrying material. Safe evidence is not public by default.

Require durable INTENDED custody before H, append observed facts afterward, and
retain crash-window UNKNOWN without replay. Failed post-use custody repairs the
same evidence operation, not the provider call. Current media in-memory unresolved
handles and facade settlement are not proof of durable Secret attempt custody.
Choose source/root custody, capacity, retention/disposition and failure/recovery
contract under ADR-009 and ADR-010 sections 13–14; no new backend is selected (B-05).

## 13. Public API impact

Acceptance itself adds no API. Prefer media-private provider semantics and existing
canonical security/reference/effect contracts. The public facade is for execution
composition, not Secret material or an arbitrary transport callback. Current media
offers are generation/VTO; a probe must not impersonate either or Model chat.

The missing source mapping and owner integration seam must be decided before
implementation (B-03/B-04). First consider a narrow owner-controlled composition
entry with media-private protocol logic and canonical safe values. Do not expose
Core source internals or clone them into media. No new generic SecretService,
CredentialPort or GenericProtectedHTTPPort is justified by this one consumer.
If a public addition is necessary, its proposal must name semantic owner, actual
consumer(s), implementation, concrete substitution requirement, versioning and why
private composition is insufficient; this review invents no interface signature.

## 14. SOLID, KISS, YAGNI and ownership review

| Principle | Assessment / constraint |
| --- | --- |
| SRP / SoC | Secret Access owns material/use; media owns probe semantics; adapter owns wire behavior; Runtime composes; disclosure remains separate |
| OCP | Driver variation is allowed only within the accepted closed probe contract, not arbitrary routes or authority |
| LSP | No claim that Model and media operations substitute; provider variants must preserve exact probe, error and effect semantics |
| ISP | Probe consumer needs one protected exchange, not generic credential export, upload or polling APIs |
| DIP / LoD | Consume public safe contracts; never traverse source/domain internals or expose private aliases |
| DRY | Reuse exact canonical semantics and qualified owner primitives; do not duplicate enforcement or independent evaluation fixtures |
| KISS / YAGNI | One source candidate, one family/recipient, one exchange; no broker, credential framework, multiple backends, agent or retry engine |

[ARCHITECTURE](../architecture/ARCHITECTURE.md) sections 4.10, 5/AR-13, 6.1 and 8
assign governance ownership and forbid resolving a binding into permission.
Upstream ADR-002/003/005/006/008/009/015 continue to govern public boundaries,
configuration, deputy authority, admission, effect equivalence, custody and bounded
lifecycle. No change to these accepted contracts is proposed.

## 15. Blocker matrix

Exactly five architecture readiness blockers. Owners below are accountable roles;
no approval by a named person is fabricated. These are missing decisions/contracts,
not a demand to implement or perform live tests before architectural acceptance.

| ID | Exact owner | Upstream clause | Missing evidence | Exit condition |
| --- | --- | --- | --- | --- |
| B-01 | Architecture/Runtime maintainer and Security/Secret Access maintainer | ADR-007 6.2 item 7, 8, 18; ADR-010 8.2 step 5, 23; ADR-023 11–12; ADR-INDEX 1, 14 | Approved MPBP-1-only nonblocking handoff/time exception and recipient residual; reciprocal profile separation | Accountable upstream owners approve bounded addenda and ADR-023 cross-reference, explicitly retain unsupported strict timing and unchanged SRCP-1; record decisions before readiness |
| B-02 | Generative Media provider-contract maintainer, reviewed by Security | ADR-010 7, 15; ADR-023 11; ADR-024 14, 22; ADR-027 Option A probe constraints | One designated provider/family/route with authenticated observational semantics, no job retrieval, bounded request/response/framing/time and safe diagnostics | Review authoritative provider contract and freeze one empty-body HTTPS exchange, accepted recipient basis, limits and failure/effect mapping; exclude auto discovery and job-result routes; no live call required |
| B-03 | Secret Access source owner and Runtime composition maintainer, with media consumer owner | ADR-010 6–9, 12–13; ADR-023 8, 11–12; ADR-014 15; ADR-026 responsibility contract | Media-specific S1 mapping, closed purpose/probe identity, bootstrap/source authority, exact revision lifetime and safe composition seam | Approve narrow media source/admission contract with owner-issued references, finite hold/close bounds, no environment source or raw material API; justify any public addition and preserve Model mapping |
| B-04 | Runtime ordering maintainer with Governance, Lifecycle and Secret Access owners | ADR-007 5–8; ADR-010 8.2–8.3, 10–11; ADR-026 claim/close contract | Joint ordering design for every invalidator, actual H placement and continuation/cancel/close participation; facade claim is insufficient | Reviewed owner participation matrix and event-order argument cover each race in section 11, no bypass or callbacks/waits inside gate, no post-close future send, no rollback claim |
| B-05 | Evidence Custody and Secret Access maintainers with media effect/disclosure owner | ADR-009 custody duties; ADR-010 11, 13–15; SEC-066/067/075/077; ADR-020 decision 8; ADR-024 14 | Bounded durable media attempt/evidence, provider-control admission, safe error/effect and crash/recovery contract with independent root basis | Approve exact empty-content admission and safe evidence schema, root/capacity/retention bounds, intent-before-H, truthful unknown and evidence-only repair; preserve remote VTO prohibition |

Later implementation gates, **not additional readiness blockers**: synthetic tests
of denied/wrong-purpose/revision/recipient use; partial sends, expiry and revocation
races; source teardown; no-leak canaries; bounds/parser/error cases; pre/post-custody
failure and restart; public/private architecture controls; Model regressions.
Separate named-provider qualification and explicit live authorization would follow
only after implementation and maintainer validation. No readiness document can
mark these passed. No implementation is authorized by this review.

## 16. Exact readiness decision

The decision at the top is the sole machine-readable readiness decision.
The proposed bounded direction is coherent; it does not require broadening media
scope. It remains blocked, rather than ready, because of B-01–B-05. This is not a
finding that ADR-027 has already authorized its own exceptions. Keep Status:
Proposed with affected-profile Readiness: Blocked, matching the index's established
scoped-blocker convention. H-01 remains open and no ADR is accepted here.

## 17. Next step and maintainer handoff

First run the document-only validator from the repository root, with Git and the
existing locked uv/Python environment available. No credential environment variables
or new dependencies are required. It uses stdlib and local Git only; no project
imports, tests, providers, network or Secret resolution. It checks working and
staged scope against the pinned baseline, preserved ADR history, decision/status,
blocker fields, document controls and whitespace. Partial staging is rejected when
it changes the four-file slice inconsistently. Its internal positive/negative
document fixtures exercise the checker, not runtime behavior.

```powershell
uv run --locked --offline --no-sync python .\validate_generativemedia_adr_027_readiness_review_1.py
if ($LASTEXITCODE -ne 0) { throw 'ADR-027 readiness review validation failed' }
```

Expected final evidence: LOCAL DOCUMENT CHECKS PASSED; ADR-027 PROPOSED;
READINESS BLOCKED; H-01 OPEN; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED.
Paste the full result before further changes. Validation is pending; the validator
does not prove security adequacy, source correctness or provider compatibility.

After successful document validation, request a separately authorized **document-only
blocker-resolution slice**: resolve B-01 with the upstream decision owners and
prepare B-02–B-05 contracts. Do not edit accepted ADRs without that authority.
Only after all exits are recorded should a new readiness review recommend an
acceptance review. If subsequently ready, the next slice is ADR-027 acceptance
review, not implementation or a live probe.

Proposed commit message: `docs(security): record blocked ADR-027 readiness review`
