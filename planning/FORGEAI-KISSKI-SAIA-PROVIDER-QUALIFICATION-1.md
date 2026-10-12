# FORGEAI-KISSKI-SAIA-PROVIDER-QUALIFICATION-1

Status: IMPLEMENTED — MAINTAINER VALIDATION REQUIRED.
Verification: NOT RUN — Awaiting user execution.
Baseline: `c01df354d1987a498dd8af27286ce6c00c04d106`.
Integration classification: CONFIG_ONLY. No production source, dependency,
public export, accepted ADR or API-key storage change. No API call was made.

## 1. Decision and implementation plan

Reuse the existing REMOTE OpenAI-compatible binding for the `kisski-saia`
deployment identity. The endpoint protocol does not justify a new adapter, Port,
Model request type, SDK or provider branch in ForgeAI. Provider identity is
configuration, not permission, disclosure admission or model availability.

The implementation adds a trusted operator qualification runner, synthetic
runner tests, ForgeAI configuration/parser regression tests, this record and a
maintainer-only local validator. It preserves all existing source mechanisms.
The old `scripts/kisski_compatibility_probe.py` remains historical tooling;
use the new default-inert runner for this slice.

## 2. First-party evidence and its limits

Public documentation only was read on 2026-10-13 after explicit maintainer
permission. No API endpoint, credential, account or model was accessed.

- [GWDG SAIA API documentation](https://docs.hpc.gwdg.de/services/ai-services/saia/index.html)
  documents the versioned root `https://chat-ai.academiccloud.de/v1`, Bearer
  authentication, POST chat completions and **POST models listing**. Its examples
  use messages/model/max_tokens/temperature/top_p. It advertises streaming and
  several other endpoints; this slice uses only non-streaming chat and listing.
  It describes quota headers; illustrated numbers are not account entitlements.
- [KiSSKI service description](https://kisski.gwdg.de/en/leistungen/2-02-llm-service/)
  states basic free-service limits of 10/minute, 200/hour, 400/day and 3000/month.
  Account-specific applicability remains UNKNOWN. Its chat-history and training
  claims do not establish complete API request logging, access or subprocessors.

Actual account model access, quota, context/output ceilings, concurrency and
timeout SLA remain UNKNOWN. The runner does not expose response headers as an
unreviewed diagnostics surface. No numeric quota is configured from examples.
Documentation model names are not evidence of this account's availability.

The explicit documented POST listing is the “equivalent supported models
listing” requested for stage 1. There is no GET-first attempt, alternate-method
retry or endpoint substitution. The initial candidate names from the request
(`qwen3-coder-30b-a3b-instruct`, `qwen2.5-coder-32b-instruct`, `codestral-22b`,
`openai-gpt-oss-120b`) are unverified candidates only, never defaults/allowlists.

## 3. Governing contracts and actual reuse path

Accepted [ADR-010](../adrs/ADR-010.md), [ADR-023](../adrs/ADR-023.md) and
[ADR-024](../adrs/ADR-024.md) govern Secret use, SRCP-1 and disclosure.
Their acceptance does not qualify this named provider. Source inspected:

| Concern | Existing implementation and boundary |
| --- | --- |
| Model contract | `src/legoai/intelligence/model/ports.py`: ModelPort; provider-neutral request/result and typed failures |
| Wire contract | `src/legoai/reference/model_openai_compatible.py`: OpenAICompatibleModelAdapter.chat, _payload; same serializer/parser for LOCAL and REMOTE |
| Public composition | `src/legoai/runtime/api.py`: OpenAICompatibleSettings, LocalHostConfig, RemoteModelRuntime, CredentialSource, ExecutionDisclosure; `runtime/local.py`: open_local_host/open_credential_source |
| Protected remote invocation | `runtime/_composition/remote_model.py`: RemoteModelPlane; disclosure admission precedes association, durable INTENDED, exact Secret use and T2 |
| Protected transport | `reference/_credential_https.py` and `runtime/_composition/credential_https.py`; TLS, scoped handoff, bounded framing and attempt settlement |
| Discovery | `runtime/_composition/provider_discovery.py`: discover_remote_models; separate ProviderDiscoveryAdmission, purpose and custody; not ModelPort |
| ForgeAI | `examples/forgeai/src/forgeai/remote.py`: RemoteProfile/load_profile; `composition.py`: bind_remote/prepare_run; worker/domain unchanged |
| Proposal semantics | `packages/legoai-engineering/src/legoai_engineering/coding/api.py`: CodingAgent.propose; strict provider-neutral proposal validation |

The new script reuses the existing trusted KiSSKI probe's discovery bootstrap,
scope, admissions and provider declaration. These private operator seams remain
in scripts, not in ForgeAI or a new public API. Safe HTTP-status inspection uses
the existing trusted `_remote_chat_http_status` seam. It does not add body/header
access. The historical declaration's evidence date remains 2026-10-09; its cited
public pages were rechecked for this record without upgrading unknown facts.

## 4. Exact non-secret configuration

Provider kind: `OpenAICompatibleSettings` (openai-compatible).
Profile/provider ID: `kisski-saia`. Deployment: `ModelDeployment.REMOTE`.
Base URL: `https://chat-ai.academiccloud.de/v1`.
Model: exact operator-selected ID observed in this run's account listing.
No preferred model, embedding model or provider-native response format is set.

The qualification binding reuses `kisski-probe` and `legoai-compat-probe`, scoped
to SYNTHETIC only. ForgeAI uses its existing `openai-compatible-remote` binding
and `forgeai` consumer; the probe admission does not cover that application.
The runner pins the real endpoint; tests substitute loopback TLS. Production
ForgeAI continues to take base URL/model/provider from operator configuration.

Existing ForgeAI TOML requires exactly: provider, base_url, model, repository,
revision, processor, locations, retention_days, training, human_access,
subprocessors, not_before, not_after and basis=`operator_attested`.
These are policy facts that an operator must actually establish; this review
does not supply fabricated retention/location/access attestations or a runnable
repository-disclosure policy. Its profile window is at most one hour.

The typed binding adds the source-issued SecretRef at runtime; no raw key is a
configuration field. RemoteProfile's typed timeout defaults to 120 seconds
(1..300 supported); the current TOML format does not accept a timeout field.
The synthetic runner uses 60 seconds per request, at most 512 output tokens
per chat, a five-minute SRCP-1 margin and a 30-minute admission window.
These are client bounds, not provider capacities or end-to-end real-time guarantees.

## 5. Secret use and residual limits

S1 hidden interactive provisioning occurs before governed use. It issues an
immutable, process-local revision; no key file, environment fallback, argument,
pipe, SDK credential discovery, cache or persistence is added. Discovery and
chat have separate purposes (`provider-model-discovery`, `remote-model-bearer`)
and separate hidden provisions; chat provisioning occurs only after successful
discovery, model selection and chat consent. The two chats reuse one eligible
chat revision but each creates a fresh exact use and durable attempt.

The credential's recipient must be its issuer/designated service. The documented
SAIA Bearer endpoint fits that shape; possession of a key does not prove its
eligibility, live acceptance or current provider-side state. Current local
invalidators remain ordered at protected sends. No proxy, redirect, pooling,
alternate recipient, credential rotation retry or TLS verification exception.

SRCP-1 does not guarantee remote revocation ordering, recall of already sent
bytes, memory zeroization or protection against hostile in-process code. Its
wall-clock handoff expiry is detected rather than strictly prevented. Closing
S1 on all exit paths prevents further local realization. The existing Model
host has no public close API; custody handles follow host/process lifetime.

Provider content/errors are not printed by the new runner. Only categories,
status, attempt/execution IDs, effect state and escaped listed model IDs are
reported. Raw content is neither logged nor written as qualification evidence.
The CLI suppresses invalid argument values and raw failure tracebacks.

## 6. Disclosure and ForgeAI boundary

Configuration != authorization. Secret reference != authority. Provider
selection != disclosure permission. Model output != authority. Documentation
!= account availability. Connectivity success != full provider/security/quality
qualification.

Initial requests carry only fixed operator-authored SYNTHETIC strings. The JSON
fixture contains an invented path/content, not repository text; it is never
applied or executed. There is no repository/prompt/config input option.

Actual ForgeAI tasks still require its separate exact task/path disclosure
confirmation and current admission for PLATFORM_INSTRUCTION, TASK_TEXT,
REPOSITORY_CONTENT and, during rework/review, DERIVED_DIAGNOSTIC. Repository
identity, target/context paths and task digest bind that run. Core rechecks
per invocation. Disclosure evidence records safe classifications/identities,
not file contents. Patch approval remains separate and exact.

Unknown API processor facts block private repository admission; academic status
and successful synthetic calls cannot remove that gate. This slice authorizes
no private repository run and no new processor attestations.

## 7. Endpoint and structured-output compatibility

The existing adapter sends `model`, role/content `messages`, `stream=false`,
optional `max_tokens`, and `temperature=0` only if deterministic mode is set.
This runner leaves deterministic mode off and sends no top_p, native schema,
max_completion_tokens, tools, reasoning controls or other optional extensions.

It requires one assistant text choice, finish_reason=`stop`, exact response
model equality and no tool/function calls. Usage is optional and validated
through existing token fields. Alias model echoes, length/tool finish reasons,
malformed JSON or incompatible shape fail closed. Those live behaviors remain
unverified until the exact selected model completes the probe.

T2 still requires bounded Content-Length framing (response cap 1 MiB), without
chunked-transfer support. HTTP/1.1/framing compatibility is a live prerequisite,
not established by the phrase OpenAI-compatible. No transport relaxation.

Provider-native response_format support is UNKNOWN and unclaimed. This adapter
currently refuses a non-None ChatRequest.response_format before transport.
ForgeAI's portable mechanism instead prompts for JSON and validates the result
with CodingAgent and Reviewer contracts. Stage 3 checks equality to a fixed
ForgeAI-like JSON fixture; it is deliberately not a replacement proposal parser
or a proof of coding ability. Actual parser behavior is exercised by the new
ForgeAI synthetic TLS tests plus existing Engineering tests.

## 8. Failure and effect semantics

| Observation | Existing semantics / runner behavior |
| --- | --- |
| Complete 400/401/403/404/408 or other non-2xx | Safe DependencyFailure, ordinarily terminal; exact safe status retained; stop |
| 404 plus bounded known model-not-found code | Existing ModelFailure.MODEL_UNAVAILABLE; status alone is insufficient |
| 429 or 503 | Existing potentially-retryable rejection category; this runner still never retries |
| Other 5xx | Existing terminal rejection; no provider-specific remapping |
| Complete malformed/model-mismatched chat | Contract failure, not a successful result; transport completion remains recorded |
| Refusal before send | No chat transport; preserve existing gate diagnostic |
| Lost response, partial handoff, timeout after send, unsupported framing | UNKNOWN attempt/effect as applicable; no replay, fallback or false no-effect claim |
| Unexpected exception/interruption | Safe RESULT_INCONCLUSIVE; retain custody; later stages stop |
| Correct protocol, wrong synthetic token/JSON | Content/structured smoke failure; preserve transport evidence; no quality claim |

Model effect NONE does not mean the credential was unused, disclosure did not
occur, or the provider did no computation/billing. Local cancellation cannot
recall a request; the existing synchronous protected exchange observes cancellation
before entry or after settlement, not as remote inference cancellation.

## 9. Deterministic qualification coverage

`scripts/tests/test_kisski_saia_qualification.py` uses only the existing test CA,
loopback TLS server and synthetic S1 canary. It covers inert entry, explicit
opt-in, two purpose-specific provisions, exact selection, bounded POST listing,
three-stage ordering, refusal/declines, protected Bearer headers, disclosure
before chat, no response-text leakage, no retry/fallback, safe status mapping,
malformed/model/finish rejection, lost-response truth and fixed JSON controls.

`examples/forgeai/tests/test_kisski_saia_profile.py` supplies synthetic processor
facts and varied configured model IDs through RemoteProfile and bind_remote.
It proves actual CodingAgent proposal acceptance/refusal and reviewer routing
through the unchanged remote path, exact approvals and non-secret TOML parsing.
These fixtures make no real GWDG privacy or model-availability assertions.

The validator also selects existing OpenAI-compatible, S1/Secret, disclosure,
attempt custody, T2, LOCAL/Ollama, ForgeAI and architecture regressions. No
Docker workload, package acquisition, export change or wheel build is needed.
Tests have been written but not executed. There is no pass claim yet.

## 10. Maintainer local execution

Prerequisites: Git, uv, Python 3.14 and the already installed locked development
environments at repository root, `examples/forgeai` and
`packages/legoai-engineering` (Engineering analyst extra). The validator uses
`--locked --offline --no-sync`; it does not install missing dependencies. No
credentials, environment variables or live service are needed. Local TLS sockets
are test fixtures, not external network calls. Run from the repository root:

```powershell
uv run --locked --offline --no-sync python .\validate_forgeai_kisski_saia_provider_qualification_1.py
if ($LASTEXITCODE -ne 0) { throw 'KiSSKI SAIA provider qualification validation failed' }
```

Expected: all phases pass, exit zero and KISSKI-SAIA PROVIDER PROFILE LOCALLY
QUALIFIED. This means deterministic configuration/protocol/security wiring only.
Paste the complete output. No tests, validators, mypy, Ruff or builds were run
internally. Maintainer validation remains pending.

## 11. Separate live qualification procedure — prepared, not authorized

Runner: `scripts/kisski_saia_qualification.py`, module entry from repository root.
Default and `--plan` print only an inert plan. After local validation and a
separate explicit maintainer live authorization, the attended command is:

```powershell
uv run --locked --offline --no-sync python -m scripts.kisski_saia_qualification --live
if ($LASTEXITCODE -ne 0) { throw 'SAIA synthetic qualification stopped; inspect safe output' }
```

`uv --offline` constrains dependency access; it does NOT disable the explicitly
requested live API calls. No execution of this command is requested now.

1. Type `AUTHORIZE FORGEAI-KISSKI-SAIA-PROVIDER-QUALIFICATION-1 LIVE SYNTHETIC`
   at the visible authorization prompt. The script refuses pipes/noninteractive
   terminals, creates a separate temporary custody directory and reports its path.
2. At the hidden Credential prompt only, provision the SAIA key into the existing
   S1 mechanism for discovery. One POST /models occurs. Failure stops immediately.
3. Select one numbered model returned by that account. No automatic choice.
   Approve one tiny synthetic chat; then provision separately at the second
   hidden prompt for the remote-model-bearer purpose. Never paste a key into
   chat, arguments, source, a configuration file or logs.
4. One `Return the exact token KISSKI_OK.` chat occurs. Protocol/token failure
   stops. A successful token establishes only scoped live connectivity.
5. Optionally approve the fixed synthetic proposal JSON chat. One additional
   request, same model/provider and independent exact Secret use; no mutation.
   Declining records connectivity-only. Failure is not a full pass.
6. Preserve safe output and the custody directory. Do not automatically rerun on
   any error/UNKNOWN; a fresh run requires a new operator decision. Do not share
   raw credentials/provider bodies or upload the custody database by default.

Maximum is three provider operations, sequentially, with no fallback/reselection.
No optional coding-quality execution is bundled into this runner.

## 12. Claims and follow-up

| Evidence | Permitted claim | Still excluded |
| --- | --- | --- |
| Written code only (current) | IMPLEMENTED — MAINTAINER VALIDATION REQUIRED | Local pass, live connectivity, private source disclosure, coding quality |
| Maintainer local validator passes | KISSKI-SAIA PROVIDER PROFILE LOCALLY QUALIFIED | Actual account/model interoperability or private data permission |
| Maintainer live stage 2 passes | KISSKI-SAIA LIVE CONNECTIVITY QUALIFIED for the observed exact endpoint/model/run | Structured proposal success, coding quality, availability guarantee |
| Stage 3 also passes | Fixed synthetic JSON smoke passed for that same selection | General structured-generation reliability, native schema support, ForgeAI quality |
| Later fixed-harness coding evaluation | Only the measured model/task/rubric scope | Global security/correctness or broader disclosure authority |

Next after a local pass: separately authorize the synthetic live procedure.
Then `FORGEAI-KISSKI-CODING-MODEL-EVALUATION-1` should compare only account-listed
candidates with identical frozen tasks/rubric/bounds using the existing ForgeAI
quality harness. Model size/name is not a quality result. No such evaluation
or repository execution is authorized or implemented by this slice.

## 13. REUSE / EXTEND / CREATE and review

REUSE: adapter, ModelPort, public composition, S1, SRCP-1/T2, disclosure,
attempt custody, governed POST discovery, exact model configuration, ForgeAI
proposal/review parser, synthetic TLS fixtures and regression suites.
EXTEND: operator qualification coverage with staged explicit approvals and safe
typed diagnostics; no runtime/profile schema extension.
CREATE: this record, one attended script, two focused test files and validator.

SRP/SoC: operator tooling owns qualification; Core owns protection/protocol;
ForgeAI owns coding workflow. DIP/LoD: application imports remain public;
trusted internal diagnostics stay in scripts. DRY: reuse discovery/bootstrap
rather than copy transport/security. KISS/YAGNI: no new SDK, Port, agent,
provider branch or generalized orchestration. Existing consumers/implementations
remain substitutable; no new interface requires an owner/substitution decision.

Adversarial review covers credential-bearing argument errors, reflected response
content, permission confused with configuration, discovery failure before chat
provisioning, model substitution, stale admissions, indefinite retry and false
success after structured failure. Synthetic controls are prepared; verification
is NOT RUN — Awaiting user execution. No commit was made.
