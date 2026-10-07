# SECRET-REF-1 — implementation-scope decision

**Status: ACCEPTED — 2026-10-07 by explicit maintainer decision, subject to the staged implementation gate in §8.**
**Prepared:** 2026-10-07 against `5f4a6ec69656f5ff42619a7e11a0fad1560cff9d`.
**Authority:** accepted ADR-010, ADR-005/007/009, ADR-014 §14.7,
CONTRACTS §15.5 and SECURITY §§17, 20. This record proposes implementation
scope; it neither amends an ADR nor declares a Secret provider qualified.

## 1. Completed prerequisite and requested sequence

OPENAI-COMPATIBLE-MODEL-1 is implemented in `c948adc` and its operator
qualification is recorded in `5f4a6ec`. All 52 validator phases passed;
qualification is offline/process-local, credential-free and LOCAL only.
Both commits already exist; no duplicate or empty commit is needed.

Requested order:

1. Preserve the completed provider commits.
2. Decide SECRET-REF-1 scope here.
3. Implement SECRET-REF-1 if authorized, then qualify its actual supported scope.
4. Decide and implement REMOTE-MODEL-DISCLOSURE-1 under its required authority.
5. Perform KISSKI-HOSTED-QUAL-1 only after Secret and disclosure prerequisites
   and endpoint-specific operator admission are satisfied.

No credential, environment material, remote endpoint or real provider was used
to prepare this decision. No production code is changed by this record.

## 2. Source findings that govern scope

| Evidence | Consequence |
| --- | --- |
| ADR-010 acceptance statement explicitly does not itself authorize implementation or Secret use | Acceptance of the architecture is not approval of an arbitrary material resolver |
| ADR-010 §3 and CONTRACTS §15.5 define four Secret Access operations | Public resolution returns protected references/status, never a token string |
| ADR-010 §§6–7 bind identity, tenant, selector, purpose, consumer and provider/account target | An environment variable name or a broad invocation grant cannot authorize Secret use |
| ADR-010 §§8.2–8.3 require invalidator participation and actual-use ordering | Lookup followed by a later transport call is insufficient, even with a recent authorization check |
| ADR-010 §15 makes environment variables a possible qualified source, not a selected canonical source | The portability plan §12 is an implementation recommendation subject to these stronger constraints |
| `reference/execution.py` documents gate release after issuance of an inert permit | The existing dispatch lock is not an established credential-use acceptance gate |
| `reference/governance.py` implements revocation/policy mutations independently of that gate | Adding a separate Secret lock alone cannot prove participation of every applicable invalidator |
| `reference/model_openai_compatible.py` performs HTTP through `asyncio.to_thread` | A pre-worker check or queue acceptance cannot be called actual credential-use acceptance |
| ADR-010 §§9, 11, 14, 21 require bounded holding, safe evidence, cancellation and qualification | Header injection plus redacted repr is not enough to close the Secret gate |

These findings do not reclassify the qualified credential-free provider as
defective. They identify obligations for the new Secret-bearing path.

## 3. Decision question and recommendation

**Recommend a bounded, offline-first SECRET-REF-1 implementation, with an
explicit actual-use qualification gate before credentialed provider enablement.**

Authorize implementation work in the order below, not a claim that every stage
is already feasible or qualified. If the protected transport boundary cannot
satisfy ADR-010, stop that stage and report the specific unmet guarantee; do not
weaken the ADR, label a queue as protected acceptance, or silently broaden Core.

| Alternative | Disposition |
| --- | --- |
| Adapter calls `getenv` and sets Authorization | Reject: ambient acquisition, no qualified current-use/invalidator ordering |
| Public resolver returns bytes/string to application code | Reject: violates CONTRACTS §15.5 and ADR-010 §3 |
| Resolve at host open and retain credentials | Reject: no per-use currentness; expands lifetime and does not prove rotation/revocation |
| Local Secret Access with reference-only public contracts and protected single-use realization | Recommend, conditional on the proof gates below |
| Add a vault, generic provider registry or distributed lease mechanism now | Defer: no selected provider contract or demonstrated need; outside this slice |

## 4. Proposed implementation scope

### 4.1 Public contracts and ownership

REUSE Governance authority/context, Kernel identity/references/error vocabulary,
Execution/effect identity, existing evidence custody, ModelPort and host binding
selection. Preserve owner dependency direction; Governance must not import the
Execution or runtime realization to obtain a context.

EXTEND the named Secret Access sections of `legoai.governance.values` and
`legoai.governance.ports`. Define immutable, validated reference/status/use
contracts for the existing operations:

- `resolve_secret_reference`: authorized safe reference/revision/status only;
- `authorize_secret_use`: bounded exact-use decision, not general export;
- `validate_secret_revision`: current authorized validity/eligibility;
- `record_secret_use`: safe immutable attribution, separate from model success.

The proposed initial selector is an explicit **exact material revision**.
Current/alias selection is not silently implemented as exact selection; it remains
unsupported until its own currentness and rotation cases are qualified.

`SecretRef` must bind an opaque identity, authoritative owner and tenant scope,
Secret class/use requirements, admitted resolver mapping and exact revision.
A separate use request binds requester/acting context, operation/attempt,
purpose, admitted consumer/version, target/account, configuration and lifetime.
Neither value contains material or grants authority. Concrete Python signatures
must be checked against existing nominal types before editing; no loose options
dictionary or public `get_secret` convenience API is proposed.

### 4.2 Protected realization and proof before enablement

CREATE a private `legoai.reference.secret` realization. Start with synthetic
material and a deterministic test-only consumer. No public callback may export
raw material; no general-purpose material getter, enumeration or cached bearer
object is exposed to applications, Agents, Plugins or model output.

Before enabling even local authenticated HTTP, demonstrate all of these:

1. One exact use cannot obtain a second independent slot; the owning operation
   and Secret-use observation are linked without inventing a new effect model.
2. Every supported local authority, policy, mapping, eligibility, rotation,
   revocation and consumer invalidator participates in the same effective order.
   A second independent lock is insufficient. Identify necessary owner changes
   explicitly and retain credential-free behavior.
3. The private consumer accepts responsibility for the exact use at a bounded,
   non-reentrant boundary. Arbitrary later worker execution is not that boundary.
   No network wait occurs while holding the final gate. Any later protected
   sub-action must have the current checks required by ADR-010 §8.3.
4. Time/expiry and check-to-acceptance assumptions are stated and demonstrated;
   CPython scheduling, a TTL or a timestamp is not a hard real-time guarantee.
   Unsupported strict guarantees fail closed.
5. Required pre-use evidence is admitted before handoff. Post-use evidence failure
   preserves actual/unknown effects and repair obligations, without retrying the
   model request. If required durability is unavailable, that path is unsupported.
6. Restart, cancellation, expiry and abandonment cannot restore a handle or permit
   another use; disposal claims cover controlled references, not physical erasure.

This proof may expose a need to extend the existing arbitration/owner seams.
Approval of this proposal permits the bounded investigation and qualification
work, not an unreviewed general Coordinator redesign. Record any required wider
change for maintainer decision before implementing it.

### 4.3 Material source and Model integration

Only after the proof succeeds, assess one explicit operator-configured local
source. The environment-backed source recommended by the portability plan is a
candidate, not an automatic default. Its revision mapping, mutation controls,
process inheritance, diagnostic exposure and currentness must be qualified;
uncontrolled environment mutation must not be presented as ordered rotation.
No ambient fallback, `.env` scanner, production credential fixture or secret hash
in ordinary configuration/evidence is permitted.

Then propose the narrow host configuration addition `api_key: SecretRef | None`
to OpenAI-compatible settings with a source-compatible default of None, and
private protected-call integration. No raw key field or environment name enters
Model requests. ADR-014 §14.7 provides the reference-only constraint; exact host
wiring and ownership must be reviewed against the use-boundary proof before
credential support is enabled.

LOCAL remains the only supported deployment. Credential-free hosts must neither
start a Secret provider nor resolve material. No ModelPort, Agent, Ollama protocol,
Reviewer, Analyst, routing, retry or fallback behavior change is proposed.
Media migration is the later MEDIA-SECRET-1 slice, not part of this work.

## 5. Qualification plan for an authorized implementation

Create `validate_secret_ref_1.py` with an operator command from repository root:

```powershell
uv run python .\validate_secret_ref_1.py
```

**Planned only: this script does not exist yet.** The present decision is
documentation and is checked by diff review, not by claiming implementation tests.

Required implementation evidence:

- reference-only APIs, owner boundaries, exact selectors and invalid configurations;
- wrong tenant, requester/deputy scope, purpose, consumer, target/account, revision
  and missing authority, with no material/existence leak and no provider send;
- deterministic races before acquisition, between acquisition and use, at actual
  acceptance and after acceptance; all relevant invalidators and expiry included;
- source unavailable, invalid source identity, rotation, revocation, no stale or
  ambient fallback, and no initialization-time material acquisition;
- one admitted use, cancellation and restart handling, no reusable raw cache;
- synthetic material absent from repr, exceptions including causal chains,
  prompts, public results, evidence, reports, logs and configuration fingerprints;
- required pre-evidence failure and post-use evidence failure with honest effect
  and repair behavior; no second model call to repair evidence;
- fake local authenticated HTTP only if its protected boundary is qualified;
- credential-free provider conformance/regressions, runtime/Agent/consumer
  regressions, mypy, Ruff and diff checks.

Passing synthetic tests establishes only their declared local scope. It does not
qualify real credential providers, remote revocation, remote storage, memory
zeroization, output quality or KISSKI.

## 6. Subsequent gates, preserved in requested order

**REMOTE-MODEL-DISCLOSURE-1:** prepare the required ADR/addendum decision and
implement only after its approval. Apply a provider-neutral admission boundary
to both Ollama and OpenAI-compatible remote processing, including loopback
tunnels. Bind declared data-use, retention, training-use, residency and external
transfer conditions to the pinned endpoint/provider/configuration; unknown
mandatory guarantees refuse before disclosure. Secret permission does not grant
remote-data disclosure permission.

**KISSKI-HOSTED-QUAL-1:** after those prerequisites qualify, obtain the exact
operator endpoint/model, credential reference (never a key in chat), provider
terms and explicit admission, synthetic workload, request/token limits and
cost constraints. Verify current official endpoint/terms information at that
stage. Freeze a qualification plan before sending requests. Record protocol,
identity, effects, credential safety and disclosure evidence separately from
model quality. No KISSKI-specific adapter, VTO, personal images, Slurm or live
Analyst rerun is authorized by this planning record.

## 7. Requested maintainer decision

Accept or revise the bounded SECRET-REF-1 scope in §4, beginning with reference-only
contracts and actual-use/invalidator qualification using synthetic material.
Keep credential enablement conditional on its proof; keep remote and KISSKI
work behind §6. Acceptance must be recorded explicitly before treating this
proposed scope as an implementation decision. Do not mark ADR-010, G03 or any
provider fully qualified merely because this planning decision is accepted.

## 8. Accepted implementation order — 2026-10-07

The maintainer accepts this bounded implementation scope in two gated stages.
The technical proposal above is preserved; this note records acceptance of §7
and governs implementation order. Acceptance does not qualify Secrets or close G03.

**Stage A — SECRET-REF-1A:**

- Public reference/status/use contracts and Secret Access Port operations.
- Private synthetic Secret realization and deterministic exact-use/invalidation tests.
- No environment source, model credential header or credentialed provider enablement.

**Stage B — SECRET-REF-1B:**

- One explicitly configured environment-backed source.
- OpenAICompatibleSettings reference field and private protected credential handoff.
- Fake local authenticated HTTP qualification; still LOCAL deployment only.

Stage B is not authorized merely by acceptance of this scope. It may proceed
only after Stage A is locally qualified and its report demonstrates ADR-010
actual-use/current-invalidator ordering without an unapproved broader runtime
redesign. If Stage A requires a broader owner, Coordinator, governance, execution
or arbitration redesign, **STOP** and prepare a separate maintainer decision
before implementing that wider change.

Neither stage authorizes a remote provider. Remote disclosure and KISSKI remain
behind the separate decisions, admission and qualification prerequisites in §6.
This acceptance record makes SECRET-REF-1A the next implementation slice; no
implementation begins in this documentation-only change.

## 9. Stage A implementation assessment — 2026-10-07

**SECRET-REF-1A STOPPED — DURABLE CUSTODY SCOPE REQUIRED.** The accepted shared
local arbitration prerequisite is authorized, but the subsequent implementation
assessment reached the explicit durable-custody stop condition. ADR-010 §14 and
ADR-009 §§8.2–9 require durable safe-use attribution/repair obligations that
current in-memory Evidence support cannot provide. See the
[lock-order analysis and smallest additional scope decision](LEGOAI-SECRET-REF-1A-ARBITRATION-DECISION.md#8-implementation-assessment--2026-10-07).
No code or validator was implemented; Stage A is unqualified. Stage B, credentials,
remote use and KISSKI remain gated. G03 remains open. Accepted architecture and
the two-stage scope above are unchanged.

Durability follow-up (2026-10-07): [SECRET-USE-DURABLE-CUSTODY decision](LEGOAI-SECRET-USE-DURABLE-CUSTODY-DECISION.md)
is **ACCEPTED** by explicit maintainer decision. The [durable prerequisite is
LOCALLY QUALIFIED](LEGOAI-SECRET-USE-DURABLE-CUSTODY-DECISION.md#11-secret-use-durable-custody-1-implementation--2026-10-07)
from the operator's 72-phase result. Its prerequisite gate is satisfied; Stage A
remains unresumed/unqualified pending explicit resumption. Stage B remains gated.
