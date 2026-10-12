# GENERATIVE-MEDIA-MPBP1-REMAINING-BLOCKERS-1

Status: Proposed — NOT ACCEPTED.
Baseline: `cb0f4fb02c9140c2e2ab1f1a12d30405725c0676`.
ADR-027: Proposed. Readiness: Blocked. H-01: OPEN.
B-01: RESOLUTION_DRAFT_READY.
B-02: STILL_BLOCKED.
B-03: RESOLUTION_DRAFT_READY.
B-04: RESOLUTION_DRAFT_READY.
B-05: RESOLUTION_DRAFT_READY.
No blocker is CLOSED. Architecture approval is pending.
Verification: NOT RUN — Awaiting user execution.
No implementation or live execution authorized.
Credentialed media NOT QUALIFIED; remote VTO UNSUPPORTED.
SRCP-1 remains Model-only. No generic credential service approved.

This proposes architecture, not acceptance or qualification. The maintainer supplied
successful document validation of the preceding
[blocker package](GENERATIVE-MEDIA-ADR-027-BLOCKER-RESOLUTION-1.md). Its historical
reasoning and B-01/B-04 drafts remain unchanged; only current-status metadata is
added. The assistant inspected source and first-party documentary websites, but
ran no tests, validators, provider APIs, credentials or application workloads.

## 1. B-02 authoritative evidence register

Research accessed 2026-10-12. Links are documentary resources, not provider-call
instructions. Branch URLs are mutable snapshots, not release pins; recheck before
later acceptance. No login, credential submission or provider API call occurred.
No unofficial search result was used as normative evidence.

| ID | Source title, publisher and reference | Version/date | Proposition and evidence class | Authority and limitations |
| --- | --- | --- | --- | --- |
| E1 | [v1 Cloud API Overview](https://docs.comfy.org/development/cloud/overview), Comfy | Undated; accessed above | DOCUMENTED FACT: Cloud base is cloud.comfy.org; v1 specifies X-API-Key and is deprecated | First-party protocol documentation; does not establish bearer acceptance |
| E2 | [Comfy Cloud OpenAPI](https://raw.githubusercontent.com/Comfy-Org/docs/main/openapi-cloud.yaml), Comfy-Org/docs | info.version 1.0.0; main snapshot | DOCUMENTED FACT: GET `/api/system_stats` explicitly has empty security; `/api/user` returns account information | Normative schema description, not deployment proof; public-route exception differs from E1's broad authentication wording |
| E3 | [ComfyUI server.py](https://raw.githubusercontent.com/Comfy-Org/ComfyUI/master/server.py), Comfy-Org/ComfyUI | master snapshot; no release pinned | SOURCE-CODE FACT: `/system_stats` gathers device/system/version data, including argv; handler does not enqueue a job | Descriptive implementation; not a remote authentication, logging or privacy contract |
| E4 | [Comfy API v2 OpenAPI](https://raw.githubusercontent.com/Comfy-Org/docs/main/openapi-v2.yaml), Comfy-Org/docs | info.version 2.0.0; main snapshot | DOCUMENTED FACT: bearer scheme covers account-scoped keys on Cloud/serverless; examined operations concern assets/jobs, including workflow/log retrieval | Normative published schema; v2 bearer support does not transfer to v1 status routes |
| E5 | [Getting an API Key](https://docs.comfy.org/development/api-development/getting-an-api-key), Comfy | Undated; accessed above | DOCUMENTED FACT: operators create/manage/delete account keys through the platform | First-party operational documentation; not designation of an MPBP-1 route or authority to provision credentials |
| E6 | [Trust Center controls](https://trust.comfy.org/controls), Comfy | Undated indexed extract; opened page exposed no substantive text | DOCUMENTED FACT limited to indexed description that retention/disposal procedures exist | Descriptive general assurance, not route-specific log fields, duration or billing terms |
| E7 | [Privacy policy](https://www.comfy.org/privacy), Comfy; linked from official docs | Fetch failed; bare-domain retry also failed | UNKNOWN: operative policy text was not retrieved | No privacy guarantee inferred; no forum policy or enterprise agreement substituted |

DOCUMENTED FACT describes documentation; SOURCE-CODE FACT describes implementation;
INFERENCE is our bounded conclusion; UNKNOWN is not permission. Schema availability
does not establish live conformance or LegoAI admission. No credentials are included.

## 2. B-02 decision test and alternatives

| Test | Evidence assessment | Disposition |
| --- | --- | --- |
| A service identity | E1/E4 identify Comfy Cloud; no deployment admitted for MPBP-1 | Known service, missing exact admitted binding |
| B bearer for selected route | UNKNOWN for legacy `/system_stats`; E1 specifies another header; E2 status is public | Required evidence absent |
| C HTTPS route | E2 documents `/api/system_stats`, not equivalence with legacy `/system_stats` | Do not silently change route or transfer auth semantics |
| D empty body | E2 GET has no request body; E3 handler reads no application body | Supports empty client request only |
| E no generation creation | E3 handler gathers status | INFERENCE: observational intent, not all middleware effects |
| F status rather than job content | E2/E3 report system metadata; E3 includes argv | No job result; raw operational metadata may be sensitive |
| G bounded one exchange | Client can impose one request and byte caps | No provider latency/size guarantee inferred |
| H redirects/fallback | Examined definitions do not require them | Refuse locally; not proof that deployment never redirects |
| I account/recipient | E4 account-key semantics apply to v2 | No cross-version recipient authorization by analogy |
| J logging/billing/retention | UNKNOWN at route level; E6 is general, E7 unavailable | No zero-logging, free-call or deletion claim |

B-02 remains STILL_BLOCKED. No remote provider/family is selected for activation.
Legacy GET `/system_stats` remains a local client candidate only. Observational
intent is supported, authenticated remote semantics are not. Sending a bearer to
a documented public Cloud status route is not justified just to test acceptance.

Alternatives examined: Cloud `/api/user` uses v1 authentication and exposes account
data; it is not an established bearer status replacement. Queue/job routes expose
customer work. The published v2 asset/job/workflow/log operations violate the
no-customer-content/no-polling/no-result profile. A fabricated job ID changes none
of those semantics. OSS `/features` is source-level observation, not a designated
remote bearer service. No suitable alternative was established in the examined
first-party sources; this is not a claim about every possible provider.

Exact exit: obtain first-party or independently admitted deployment evidence for
one issuer/designated service, account and bearer-authenticated empty-body
observational endpoint, response and metadata-handling terms; resolve A–J without
promoting UNKNOWN. Then review the fixed client bounds. Until then remote
credentialed media stays unsupported. No live call substitutes for authority.

## 3. B-03 source and composition decision

Select alternative A: a narrow public Runtime composition entry for one admitted
protected probe operation, backed by private owners. Candidate architectural name:
`open_bound_probe_session`. No function, type or implementation is added here.

| Alternative | Assessment |
| --- | --- |
| A narrow Runtime entry | Selected proposal: integrates exact-use owners without exposing private state |
| B private Runtime through existing public facade | Existing claim/close supplies no source or protected-send control; claiming otherwise leaves H-01 open |
| C media public composition alone | May wrap the eventual safe Runtime entry; cannot itself reach private owners without duplication or forbidden imports |
| D generic credential service | Rejected: no interchangeable multi-consumer semantics justify it |
| E remain undecided | Activation remains blocked, but the architectural seam can be proposed now |

Runtime owns assembly; Secret Access owns material/revision/use and lifecycle;
media owns probe meaning; its admitted driver owns wire shape/parsing; Evidence
owns custody. Current consumer is the explicit media probe, not generation/VTO.
One reference realization initially reuses S1, ordering and protected transport
mechanics inside their owners. No media imports of `_source`, `_domain` or private
Core classes. No Model purpose, ModelId or Model public CredentialSource reuse.

Safe inputs: independently established Principal/TenantContext, exact configuration,
contribution/operation/execution references, closed profile version, provider/account/
recipient mapping, root/source admission, independent disclosure admission, bounds
and margin-qualification reference. Values declare scope; they do not grant it.
Safe outputs: owner-issued SecretRef/SecretRevisionRef, canonical execution/use/
effect evidence references and closed outcome categories. No header, raw body,
authenticated client, socket or material handle leaves the session. Media's
normalized observation stays in its versioned evidence schema for entitled readers;
Core gains no media result union or domain schema.

Lifecycle: inert open validates admitted composition; explicit provisioning reads
hidden input inside the source; execute-once has no caller URL/body/header/callback
and runs the frozen operation through G/H; inspect returns safe status; close
commits a shared-domain stop before returning, retaining unresolved obligations.
There is no dynamic profile registration, arbitrary loader, resumption or reusable
authorization interval. Driver contribution is selected by trusted admission, not
a caller factory. It supplies pinned nonsecret request shape and parses bounded
responses privately; the private transport injects material only under exact gates.
Runtime wires this one operation, not arbitrary protected HTTP operations.

New API necessity: the existing public Model source fixes Model purpose/consumer,
and GovernedExecution expressly grants no later-send authority. Existing canonical
values cannot assemble hidden owners by themselves. Propose an additive, concrete
session/admission contract in runtime.api and factory in runtime.local, requiring
explicit approval as a bounded extension of ADR-026. It is not already authorized
by ADR-026's implemented facade. No new generic Protocol/Port or registry is needed.
Substitution: replace private source/transport/custody without changing safe calls
or media imports. Version the closed contract/profile at v1; unknown operations or
versions refuse. The security cost is a new trusted composition surface, requiring
forgery, foreign-context, private-boundary and one-use tests before enablement.

S1 contract: one attended hidden provision, incarnation/revision/use; purpose
`media-provider-probe/1`, consumer `legoai-generative-media/provider-probe@1`.
Reuse owner-private semantics in [reference/secret.py](../src/legoai/reference/secret.py),
not the Model wrapper: 4096 visible-ASCII byte ceiling, owner-issued exact revision,
no environment/file/CLI/pipe source, raw return API, persistence, adapter cache or
authenticated pool. Canonical SecretRef.exact supplies revision identity.
Previously proposed source/use lifetime caps remain subject to approval. Close,
retirement and expiry join the shared domain; rotation ends this attempt, never
refreshes it. Best-effort disposal is not physical zeroization or hostile-host isolation.

## 4. B-03 validity-margin criterion

No magic duration is selected. Admission references a named host/runtime profile:
OS/Python build, clocks/resolution, TLS/socket realization, gate/owner/storage
revisions, admitted load, power/scheduling assumptions and validity window.
Qualification evidence records procedure, coverage, observed delays, limitations,
explicit safety reserve and accountable owner approval.

Configured margin M >= U + C + R. U is the qualified observed maximum local
final-check-to-OS-acceptance uncertainty in that admitted envelope; C covers clock
resolution/conversion/uncertainty; R is an approved positive reserve with rationale.
Measure owner rechecks, remaining local commits, serialization and nonblocking
acceptance, including fresh/partial writes, contention and admitted failure loads.
Remote response latency is not this uncertainty. An empirical maximum is not a
hard bound on scheduler suspension and MUST NOT be described as one.

At each G require remaining validity strictly greater than M for every interval;
re-sample after consumption/custody work and retain original deadlines. Observe H
time; late/unobservable H produces violation/unknown evidence. Suspend/resume,
clock discontinuity, runtime/transport/store changes, expired evidence or delays
outside the admitted envelope invalidate qualification and block future H until
requalified. A suspension after the final check can still yield late H: detect,
record and stop later sends, never claim prevention or rollback.

No qualified margin -> protected send refused.
No measurements were made here. Future maintainer-run synthetic qualification
supplies deployment evidence; architectural readiness requires this criterion,
not fabricated measurements. Strict real-time and remote issuer currentness remain
unsupported. B-03 is RESOLUTION_DRAFT_READY, not accepted or implemented.

## 5. B-05 custody selection and source evidence

Select A, existing owner-local durable evidence mechanics with a media-specific
schema, concretized by B, a narrow SQLite realization within existing owners.
This adds no generic service and reuses no Model attempt identity/schema.

[ADR-004](../adrs/ADR-004.md) sections 3–4 require conditional owner-local durable
state/history/results/obligations. [ADR-009](../adrs/ADR-009.md) sections 3–5 require
durable source obligations plus separately authoritative Evidence acknowledgment;
source persistence alone is not independent custody. Media owns intent/meaning,
Secret Access owns use facts, Evidence owns custody/access/disposition.

Inspected [_custody_sqlite.py](../src/legoai/reference/_custody_sqlite.py): explicit
provisioning, separate owner files/schemas, exclusive writer admission, integrity
checks, rollback journal, synchronous EXTRA and no busy retry.
[_durable_evidence.py](../src/legoai/reference/_durable_evidence.py) binds access and
acknowledges Secret-use evidence; [_secret_ledger.py](../src/legoai/reference/_secret_ledger.py)
retains source obligations/interventions. [_remote_attempts.py](../src/legoai/reference/_remote_attempts.py)
offers bounded intent/outcome mechanics but contains Model/provider-discovery
semantics. [custody.py](../src/legoai/evidence/custody.py) explicitly limits the
intact-local profile: no inherited power-loss or hostile-storage guarantee.
Media's in-memory unresolved handle does not supply durable custody.

| Alternative | Durability/commit/crash | Recovery/capacity/burden/replacement | Decision |
| --- | --- | --- | --- |
| A existing owner-local mechanism, media schema | Atomic source and separate custody commits; no global transaction | Existing scope/integrity/writer mechanics; bounded new schema; safe migration required | Selected architecture |
| B narrow SQLite repository | Concrete implementation of A, with immutable observations and expected revision | Stdlib mechanism, existing operational pattern; new schema and storage qualification required | Selected realization proposal |
| C append-only files | Requires framing, flush, torn-tail repair and conditional outcomes | Bespoke indexes/access/disposition logic; append alone insufficient | Reject |
| D Model attempt schema | Domain identity does not match media | Dummy ModelId or repurposed discovery authority forbidden; private mechanics may be reused | Reject schema reuse |
| E generic Evidence service | Additional API/network/storage contract | No required new generic owner/service; greater operator burden | Reject |
| F remain undecided | Safe unsupported scope | Existing accepted ownership supports a concrete proposal; activation still blocked | Not selected |

## 6. B-05 transactions, root and recovery

Proposed media-probe-attempt/1 records immutable intent and appended safe
observations, owner revision, result and obligations. Unique attempt/use/execution
binding prevents duplicate initiation. Commit INTENDED with submission responsibility
atomically in the source owner, obtain a distinct Evidence-owner receipt, persist
its linkage, then permit H only after exact receipt/currentness checks. Storage
preparation/waits remain outside G. Any bounded owner-local final commit inside G
requires a new time check before H; no asynchronous disk wait/callback enters G.

Use existing SecretUseFact/SourceEvidence/receipt meanings for Secret-use facts.
Media intent/effects require a distinct media schema and versioned Evidence
admission; do not cast them to SecretUseFact or Model attempts. Separate owner
transactions/adapters retain authority even on shared storage. Media cannot issue
its own Evidence receipts. No public SQL, universal repository or transaction API.

Recovery treats INTENDED lacking durable terminal facts as unresolved/UNKNOWN,
never replay permission. Inspect exact revisions and original submission status
after lost custody acknowledgment. Post-H failure retains effects and repair
obligations; repeat equivalent evidence work only. Corruption, missing/incompatible
stores, lost writer ownership, rollback or unknown commit status fail closed.
Never initialize empty replacement state on reopen. Migration must preserve exact
identities, interpretation, histories and duties; replacing SQLite needs separately
governed migration and qualification, not a silent backend switch.

Target the applicable ADR-004 durable-write failure scope. Current INTACT_LOCAL_V1
excludes power loss and cannot silently satisfy a stronger duty. Before enabling,
qualify SQLite/filesystem/flush/storage against the required receipt guarantees,
including machine interruption where required, or refuse the scope. This is a
mandatory implementation gate, not proof supplied here. No hostile-admin, rollback
immunity or lost-device survival promise is made.

Root authority: independently admitted operator under bounded Evidence/Secret
administration explicitly provisions or opens stores. Admission binds Principal,
tenant, configuration, root/custodian identity/profile, schema version, canonical
path, permissions, allowed lifetime and policy. CustodyAccess declares scope, not
authentication. Trusted composition alone selects storage; media requests,
provider responses, Secret values and model outputs never select it. Require
private file/directory ACLs, verified ownership, no symlink/reparse substitution,
one writer and no cross-tenant store reuse. Root access terminates at local
operator/OS authority, not an unavailable credentialed service. Missing authority,
unknown ACLs, unavailable root/custody or capacity exhaustion prevents H. Reopening
does not restore grants, source material or old execution authority.

## 7. B-05 capacity, retention and disposition

No universal retention duration. Evidence Governance approves a finite versioned
policy per tenant/configuration/profile; the operator selects values within its
approved bounds. Required fields: maximum attempts/records, observations per
attempt, logical bytes, physical store/journal envelope, resolved retention interval
and permitted minimum/maximum, disposition authority, tombstone lifetime and
repair reserve. Missing/conflicting policy refuses admission, not an implicit default.

The previous proposed 65536-byte record ceiling is a media proposal, not proof
that current 32768-character serialization accepts it. Qualify the schema and
UTF-8 byte counting. Aggregate ceilings are finite Evidence/Resource owner profile
decisions, not caller knobs; existing 4096-record limits are prior art, not a
capacity guarantee. Reserve terminal/repair/disposition space before admitting
INTENDED. Physical SQLite/journal overhead requires a qualified disk envelope;
row-byte limits alone do not bound physical storage. Full capacity refuses new H.

Unresolved records cannot be evicted. At resolved retention expiry, an entitled
disposition operation checks holds/duties, commits required disposition evidence,
then purges eligible payloads. No automatic deletion of unresolved liability.
Conflicts or unavailable evidence capacity stop disposition/new admission and go
to the retention authority; do not invent indefinite-retention permission or erase
duties. Tombstones have finite governed retention, and later reference gaps stay
visible. No background janitor or generic retention framework is introduced.

Status/retrieval/repair require current tenant-aware access without existence leaks.
Evidence repair retains original submission identity and equivalence. Root admission,
numeric deployment profile and actual durability/disposition proof remain enablement
conditions. B-05 is RESOLUTION_DRAFT_READY: mechanism, ownership and policy contract
are proposed, not already provisioned, implemented or qualified.

## 8. Independent disclosure and six effect facts

Proposed media-provider-control/1 independently binds principal/tenant, execution/
operation/attempt, contribution/configuration, provider/account/recipient, route/
profile revision, permitted fields, bounds and validity. B-02 is blocked, so this
is an abstract fixed-profile contract, not a named-provider grant. Permit only
necessary fixed HTTP routing/protocol metadata and separately authorized bearer
to its issuer/designated service. Prohibit image, prompt, workflow, repository
content, job result, application metadata and arbitrary caller headers/body.
Credential authority is not disclosure authority; neither gate grants the other.
No Model vocabulary is borrowed; ADR-020 remote-VTO prohibition is preserved.

Keep six facts: acquisition; OS credential send; remote credential receipt/use;
provider-control response; job effect; custody effect. Job effect is NONE because
MPBP-1 submits no jobs, not because logging/billing is absent. Pre-H refusal means
send NONE while earlier acquisition/cost facts remain. Proven accepted prefix is
PARTIAL; proven full OS send is COMPLETED locally but no response leaves remote
outcome UNKNOWN. Complete 401/403 cannot erase credential use. Malformed response
preserves prior send and no raw body enters evidence. Post-H custody failure creates
a repair duty, never a provider retry. Crash cannot replay. Continue only the same
unsent suffix on the same connection after each G. No fallback/reconnect/auto discovery.

## 9. B-01 and B-04 cross-check

| Constraint | Compatibility |
| --- | --- |
| Recipient | None admitted while B-02 blocked; later session freezes exact approved mapping |
| Source lifecycle | One S1 revision; retirement/teardown/expiry share G/H ordering |
| Margin | Operational criterion, not hard real-time bound; original late-H residual retained |
| Custody before H | Source INTENDED plus independent applicable receipt; unavailable custody refuses |
| Close/teardown | New session integrates owners; old facade close alone does not stop owner transport |
| Partial writes | Same request/connection, complete recheck, no reusable permit |
| Evidence availability | Reserved repair space; unknown receipt blocks future H without erasing effects |

No contradiction requires rewriting B-01/B-04 drafts. The new seam needs explicit
architecture approval; it is not assumed covered by existing facade acceptance.
SRP/SoC preserve owners; DRY reuses private mechanics, not Model types; DIP/LoD
prohibit private traversal; ISP/KISS bound one operation; OCP/LSP require equivalent
safe semantics under replacement; YAGNI rejects services, material callbacks and
global registries. No accepted ADR body or production source changes.

## 10. Current exits and maintainer handoff

| Blocker | State | Owner | Documentary evidence and exact exit |
| --- | --- | --- | --- |
| B-01 | RESOLUTION_DRAFT_READY | Architecture/Runtime and Security | Existing scoped proposals; explicit upstream acceptance pending |
| B-02 | STILL_BLOCKED | Media provider-contract owner and Security | Sections 1–2; obtain missing bearer/recipient/metadata contract satisfying A–J |
| B-03 | RESOLUTION_DRAFT_READY | Runtime composition and Secret Access with media | Sections 3–4; approve bounded new seam/source and margin criterion; later implementation qualification |
| B-04 | RESOLUTION_DRAFT_READY | Runtime and participating authority owners | Existing event-order matrix plus section 9; approve participants and later race/no-bypass proof |
| B-05 | RESOLUTION_DRAFT_READY | Evidence/Secret Access with media source owner | Sections 5–8; approve SQLite owner realization/root/finite policy; later durability/capacity/disposition proof |

Prerequisites: repository root, Git and existing locked uv/Python environment.
No credential environment variables needed. The validator checks local documents
and Git only, never fetches citations or imports production. Positive/negative
fixtures cover documentary boundaries; accepted ADRs/dependencies/production and
historical package prose are pinned unchanged. No internal execution occurred.

```powershell
uv run --locked --offline --no-sync python .\validate_generativemedia_mpbp1_remaining_blockers_1.py
if ($LASTEXITCODE -ne 0) { throw 'MPBP-1 remaining blocker validation failed' }
```

Expected: LOCAL DOCUMENT CHECKS PASSED; PACKAGE INCOMPLETE; B-02 STILL BLOCKED;
ADR-027 PROPOSED; H-01 OPEN; NO IMPLEMENTATION OR LIVE EXECUTION AUTHORIZED.
Paste output before further changes. Document success proves no security,
credential, provider, margin or storage guarantees. If B-02 later has sufficient
evidence, conduct explicit upstream/addendum architecture acceptance review and
then fresh ADR-027 readiness after required decisions are accepted. While incomplete,
keep remote credentialed media unsupported and obtain the missing authoritative
contract; do not test credentials against public routes or widen scope for success.

Proposed commit: `docs(security): resolve MPBP-1 source and custody drafts`

## 11. Final package decision

REMAINING_BLOCKER_RESOLUTION_INCOMPLETE
