# GENERATIVE-MEDIA-PUBLIC-EXECUTION-MIGRATION-1

Status: implemented; pending maintainer validation. M-01 remains OPEN until the
maintainer supplies passing evidence. Baseline:
`9dae5680f8f86e92c5056534a2e2cee0416b8cd3`.

Authority: the maintainer's bounded migration request, accepted ADR-026 and the
locally qualified public execution facade. ADR-020 image/disclosure semantics
remain unchanged. H-01 remains OPEN; ADR-027 remains Proposed; MPBP-1 is not
implemented. No live execution or credentialed media is qualified. Remote VTO
remains unsupported. Core implementation, providers, dependency files and ADRs
are unchanged.

## Inspected responsibilities and migration

Before migration `local_host.py` imported `legoai.reference.catalog`, `.evidence`,
`.execution`, `.governance`, and `.plugins`; `composition.py` imported
`.execution` and `.resolution`. It reconstructed lifecycle activation, a Catalog,
contribution resolution, security-context and authority registries, evaluator,
arbiter and coordinator for every invocation. Services called that coordinator
through the media composition helpers.

| Responsibility | Decision | Resulting owner/location |
| --- | --- | --- |
| Catalog, lifecycle admission and contribution currentness | MIGRATE TO PUBLIC FACADE | Existing `GovernedExecution` realization |
| Context registry, authorization, dispatch and coordinator | MIGRATE TO PUBLIC FACADE | Existing public `runtime.local` entry point |
| One-shot claim and canonical settlement | MIGRATE TO PUBLIC FACADE | Public `claim` / `settle`, with trusted owner facts |
| Private registry construction and `select` lifecycle/resolution glue | REMOVE AS DUPLICATED CONTROL | Deleted from media |
| Requests, results, images, disclosure, preflight, job effects and retention | KEEP MEDIA-OWNED | Existing media contracts and engines |
| Job polling, retrieval and read-only reconciliation | KEEP MEDIA-OWNED | Existing adapters, no Core callbacks |
| Discovery, family selection, transport and serialization | KEEP PROVIDER-OWNED | Existing discovery/drivers, unchanged |
| Adapter/workflow binding and returned-result attribution | KEEP PRIVATE TO MEDIA | Simplified `Contribution` and composition checks |

No new Port, registry, host framework or service manager. The internal
`LocalSession.coordinator`, catalog/requirement fields, activation mirror and
`select` helper are removed. They were private composition wiring, not documented
application Ports. The services' public signatures and all request/result fields
remain unchanged. Only two closed media failure reasons are added:
`media_execution_refused` and `media_execution_unsettled`.

## Trusted binding and flow

The operator composition still selects `PluginId("legoai", "local-comfyui")`
release 1.0.0 and exactly `legoai.text-to-image` or `legoai.virtual-try-on` v1.
The local-operator tenant, local-host operator principal and operator-generation
policy remain explicit. The configuration revision remains pinned to the service
digest. An `OperatorGrant` scopes only `invoke-capability` to the selected offer;
the public facade integrates the actual Grant, lifecycle and registries. No task,
prompt, image or provider response can specify these authority values.

Service invocation -> `prepare_local` -> `open_governed_execution` -> `establish`
-> `coordinate` -> public `claim` -> media adapter -> media validation/mapping
-> canonical `ExecutionResult` -> public `settle` -> close.

The facade's canonical operation action is `invoke-capability`; the selected
offer and pinned configuration distinguish the two media operations. The old
private operation labels `generate-image` / `try-on` are not public media API.
Original minted context/READY objects are retained; reconstructed contexts are
rejected rather than treated as authority. No adapter callback or media result
object is passed into Core. Claim is one local attempt, not perpetual permission
for a later protected send or exactly-once external effects.

## Effects, diagnostics and lifecycle

Existing owner results preserve NONE versus UNKNOWN, completed generation after
failed retrieval, independent input disclosure, known job IDs and cancellation
receipts. One submission remains one submission. No retry, fallback, resubmission,
remote interruption or deletion is added. Output attribution checks remain local
to media. If settlement fails, owner-private exception custody retains both the
canonical facts and original `GenerationResult`, plus the causal failure.

`probe_provider` and read-only reconciliation remain independent operations.
Service construction does not open the facade. M-04 refusal stays before driver,
credential, discovery, workflow or image handling; a new negative spy also forbids
facade opening on remote VTO construction.

The service has no lifetime/shutdown API. The smallest owner-correct lifetime is
one async context-managed `LocalSession` per invocation: capacity 1, execution
deadline bounded by the existing media completion policy (maximum 1800 seconds),
5-second preparation and shutdown bounds, finite grant expiry. Success, returned
failure and ordinary cancellation settle before close. Normal cancellation still
raises `GenerationCancelled` with the owner receipt.

Close must report no unresolved IDs before the service returns normally. Otherwise
it raises a sanitized `ProviderError` subclass with reason
`media_execution_unsettled`; the handle, IDs and original failure stay in private
exception custody. Interrupted close also reports failure. No raw host error text,
registry details, prompts or image bytes appear in exception messages. A claim
refusal can leave READY control work unresolved even though no provider operation
began: this is explicitly reported, not erased by a fabricated settlement.

Limitation: custody is in memory and only retained while the caller retains the
exception. It is not a durable journal or public repair API. A claimed operation
with retained facts can be investigated by the trusted owner; unclaimed READY
work has no fabricated settlement path. No clean-shutdown, external cessation or
crash-recovery guarantee is inferred. Process loss remains unresolved.

Credential resolution in legacy construction/diagnostics is untouched and remains
unqualified under H-01. A successful public execution claim does not qualify those
paths or implement ADR-027. Remote VTO is still refused.

## Design review and evidence

SRP/SoC: Core owns shared controls, media owns semantics, drivers own protocols.
DIP/ISP: consumer imports only the existing public concrete facade and canonical
values; no speculative interface. DRY removes repeated control integration and
activation mirrors. KISS/YAGNI retain one invocation-scoped handle, with no global
state or manager. LSP preserves provider result/effect contracts. Law of Demeter:
no registry traversal; canonical immutable value inspection remains appropriate.

Prepared evidence includes real facade spies (old private wiring would bypass
them), exact single claim/settlement, duplicate/stale/revoked/retired/foreign
controls, public signature snapshots, NONE/UNKNOWN and completed-retrieval failure,
cancellation, failed-settlement custody, diagnostic/reconciliation separation and
M-04 early refusal. Architecture ratchets remove both media exceptions and include
known-bad private imports plus allowed public/owner-internal controls.

The validator pins changed scope and unchanged service behavior outside invocation,
unchanged request/result ASTs apart from the two reason additions, Core facade
regressions, deterministic media suites and actual offline Core/media wheel builds
and isolated installed-wheel invocation with a synthetic owner. Socket transport
tests are excluded. Typing, lint, format and working/staged whitespace follow.

No tests, validators, typing, lint, formatting, builds, installs or provider/network
operations were executed by the implementation agent. All verification is pending.

```powershell
uv run --locked --offline --no-sync python .\validate_generativemedia_public_execution_migration_1.py
if ($LASTEXITCODE -ne 0) { throw 'Generative Media public execution migration validation failed' }
```

Return the full phase log, including any traceback/failure and final exit status.
Only a complete pass permits `GENERATIVE-MEDIA-PUBLIC-EXECUTION-MIGRATION-1 LOCALLY
QUALIFIED; M-01 CLOSED`. H-01 stays OPEN and ADR-027 stays Proposed. No automatic
credential work follows; the next step is the evidence/debt closeout, then a
separately authorized architecture decision if credential work is requested.
