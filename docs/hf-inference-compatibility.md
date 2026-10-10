# HF-INFERENCE-PROVIDERS-COMPATIBILITY-1

## Current status: discovery v2 locally qualified; SYNTHETIC LIVE-PROBE READY

[PROVIDER-MODEL-DISCOVERY-2](provider-model-discovery-2.md) is **LOCALLY QUALIFIED**
on 2026-10-10 at commit `c7353ccf180a54effbf2e80a048e8ae4b8197dc8`, branch
`br-LegoAIPyLLMComfyCR-ForgeAI-KISSKIColabKagHF`; the pre-edit working tree was clean.
The maintainer's complete validator passed 723 discovery/security tests, 364
architecture/package tests and 69 ForgeAI tests (1,156 total; 2 deselected),
mypy on 16 files, Ruff lint/format and whitespace checks. Exact evidence and limits
are recorded in the linked qualification record. The earlier 1,044-test record
below remains historical. No provider API call has occurred.

The closeout sets **LIVE_READY = True** after reviewing ADR-024 and the tested
orchestration. This means **SYNTHETIC LIVE-PROBE READY**, not provider compatibility
or authorization to run. Focused post-edit checks below remain pending operator
execution; no new test results are claimed by the agent.

The current script supports the future sequence through the existing owners:
hidden S1 discovery provisioning; one governed GET; up to three observed
model/backend pairs; numbered operator selection; separate SYNTHETIC approval;
hidden S1 chat provisioning under a different purpose; one governed REMOTE chat.
Selection freezes the exact `model:provider` identity in a new chat configuration.
There is no retry, fallback, arbitrary model/method argument or repository input.
Default invocation refuses before credentials, and `--plan` performs no I/O.
`--live` requires readiness and an interactive terminal. Disabled-gate tests set
the gate false explicitly; ready-path CLI tests replace orchestration with a mock.
All real test transport remains explicit localhost synthetic TLS.

The visible shortlist policy is deliberately closed:

- Coding models: Qwen2.5-Coder-32B-Instruct, then Qwen3-Coder-480B-A35B-Instruct,
  from the official [chat recommendations](https://huggingface.co/docs/inference-providers/tasks/chat-completion).
- Backend identities: [Fireworks AI](https://huggingface.co/docs/inference-providers/providers/fireworks-ai),
  [Novita](https://huggingface.co/docs/inference-providers/providers/novita),
  [Together AI](https://huggingface.co/docs/inference-providers/providers/together).
  These dated provider-declared identities do not establish live availability.
- Each pair must actually appear in this governed discovery response, with
  status `live`, exactly text input/output and both prices present and at most
  USD 5 per million tokens each. This is price screening, not a billing guarantee.
  Missing facts exclude a candidate. No inference from model size or names.
- Order follows the displayed allowlist and backend ID, not a quality, speed or
  price ranking. Keep at most three. Only a displayed number can select a pair;
  no eligible candidate means no chat or second Secret prompt.

The declaration names both HF's router and the selected inference service using
official identity sources retrieved 2026-10-10. Other processor facts remain
UNKNOWN for this SYNTHETIC scope. Discovery grants no disclosure authority.
ADR-024 §5.2 permits the legal **or service** name: the exact observed backend ID
must match the closed Fireworks AI/Novita/Together AI mapping above. Its dated
official source and the HF router source populate a PROVIDER_DECLARED identity,
not an operator-attested policy fact. An unknown backend cannot be shortlisted.
The operator selects one numbered observed pair; that immutable candidate supplies
both the processor declaration and the exact model:provider chat admission.
Actual live availability is not established until discovery succeeds; an empty
eligible shortlist stops before chat provisioning. Location, retention, training,
human access and subprocessors remain explicitly UNKNOWN as permitted only for
this SYNTHETIC scope. Router privacy statements are not backend policy evidence.
The only message is `Return exactly the word READY.` with 16 maximum output
tokens, a 60-second timeout and unchanged exact-model/stop/framing requirements.

Diagnostic restraint is now an accepted constraint, **not a blocker requiring
new Model errors**. Typed discovery statuses can distinguish 401/403 and 5xx.
429 remains inconclusive about quota. A complete rejected chat contract stays
CHAT_CONTRACT_INCOMPATIBLE; model mismatch and non-stop reasons are not split.
Unknown framing/transport outcomes stay RESULT_INCONCLUSIVE. A valid response
must equal READY for a pass. No provider response text is printed except that
fixed successful word, so an echoed token or arbitrary reply cannot enter output.

Run locally from the root:

```powershell
uv run --locked --offline --no-sync python .\scripts\hf_inference_compatibility_probe.py --plan
uv run --locked --offline --no-sync python .\validate_provider_model_discovery_2.py
```

After focused post-edit validation and separate operator authorization, the future
interactive command is
`uv run --locked --offline --no-sync python .\scripts\hf_inference_compatibility_probe.py --live`.
Do not execute it now. Separate future authorization remains
`AUTHORIZE HF-INFERENCE-PROVIDERS-COMPATIBILITY-1 LIVE PROBE`.
Unknown mandatory processor facts can still block any later repository pilot;
synthetic success never authorizes repository disclosure. Kaggle remains a
separate deployment experiment, not a Core adapter.

### Focused closeout validation (operator-run, offline only)

Run these commands from the repository root and stop on any failure. They cover
plan/default zero-I/O behavior, disabled and ready live gates, fixed CLI arguments,
synthetic orchestration, discovery v2, architecture, typing, lint and formatting.
No credential entry or provider endpoint is used. Per the standing operator testing
workflow, the agent has not executed these checks.

```powershell
uv run --locked --offline --no-sync python -m pytest -q -p no:cacheprovider scripts/tests/test_hf_inference_compatibility_probe.py tests/integration/composition/test_provider_discovery_v2.py tests/architecture
if ($LASTEXITCODE -ne 0) { throw 'Closeout tests failed' }
uv run --locked --offline --no-sync python -m mypy scripts/hf_inference_compatibility_probe.py scripts/tests/test_hf_inference_compatibility_probe.py validate_provider_model_discovery_2.py
if ($LASTEXITCODE -ne 0) { throw 'Closeout typing failed' }
uv run --locked --offline --no-sync python -m ruff check scripts/hf_inference_compatibility_probe.py scripts/tests/test_hf_inference_compatibility_probe.py validate_provider_model_discovery_2.py
if ($LASTEXITCODE -ne 0) { throw 'Closeout lint failed' }
uv run --locked --offline --no-sync python -m ruff format --check scripts/hf_inference_compatibility_probe.py scripts/tests/test_hf_inference_compatibility_probe.py validate_provider_model_discovery_2.py
if ($LASTEXITCODE -ne 0) { throw 'Closeout formatting failed' }
git diff --check
if ($LASTEXITCODE -ne 0) { throw 'Closeout whitespace failed' }
```

No HF/KISSKI compatibility, model quality, production inference, free-GPU runtime,
or HF repository-disclosure safety is qualified. A future SYNTHETIC pass requires
a separate assessment of mandatory non-SYNTHETIC facts for FORGEAI-HF-LIVE-PILOT-1.
If those facts are insufficient, preserve disclosure policy and consider the
separately authorized FREE-GPU-MODEL-RUNTIME-KAGGLE-1 experiment instead. Neither
future slice is implemented here.

## Historical record: original blocked preflight

Everything below records the pre-v2 investigation and its qualification scope;
its implementation-gap and command descriptions are superseded by the section above.

Status, 2026-10-10: **PREFLIGHT BLOCKED — LIVE PROBE NOT READY**.
Research and a fail-closed operator preflight are prepared. No tests, static
checks, provider discovery or inference requests were executed by the agent.
Operator offline validation passed on 2026-10-10. No credential was read by
the preflight. Live provider compatibility remains unqualified.

The first supplied operator run passed all 611 preflight/discovery/REMOTE/security
tests. Architecture then reported 362 passed and two failures: its consumer
allowlist omitted the existing ForgeAI synthetic S1 fixture, and its explicit
package inventories predated the qualified REMOTE/security modules and tests.
Those inventories have been updated without relaxing exact package equality or
allowing production consumers to import internals. The source-distribution list
also now includes the existing TLS test certificates. Later validator phases did
not run in that first attempt. The agent has not run checks.

The complete subsequent operator rerun passed: 611 preflight/discovery/REMOTE/
security tests, 364 architecture tests and 69 ForgeAI tests (1,044 total; two
Docker cases deselected), mypy on five files, Ruff lint and format, and
`git diff --check`. It ended with `HF PREFLIGHT OFFLINE CHECKS PASSED; LIVE
PREFLIGHT STILL BLOCKED; no HF API calls, no named-provider qualification`.
This closes the offline validation gate for the blocked preflight only. The
GET transport, backend selection evidence and typed-observation gaps remain.

This is a named-provider compatibility investigation, not a GPU deployment or
ForgeAI repository pilot. The requested ready banner and live authorization
request are deferred because the existing contracts cannot satisfy the proposed
probe. Authorization alone would not resolve these technical blockers.

## Official evidence

Only official HF documentation was used for provider facts, retrieved 2026-10-10:

- [Inference Providers overview and authentication](https://huggingface.co/docs/inference-providers/index?python-clients=requests)
- [Hub API: OpenAI-compatible models](https://huggingface.co/docs/inference-providers/hub-api#list-openai-compatible-models)
- [Chat Completion](https://huggingface.co/docs/inference-providers/tasks/chat-completion)
- [Pricing and Billing](https://huggingface.co/docs/inference-providers/pricing)
- [Security and Compliance](https://huggingface.co/docs/inference-providers/security)
- [First API call](https://huggingface.co/docs/inference-providers/guides/first-api-call)

Under [ADR-024](../adrs/ADR-024.md), reading documentation is not mechanical
verification of a provider assertion. These facts are **PROVIDER_DECLARED**.
**VERIFIED** is reserved for properties checked by LegoAI at invocation time;
there has been no such HF invocation. Unknowns stay **UNKNOWN**.

| Fact | Evidence basis and finding |
| --- | --- |
| Service and API root | PROVIDER_DECLARED: HF Inference Providers router, `https://router.huggingface.co/v1` (overview). |
| Authentication | PROVIDER_DECLARED: HTTP `Authorization: Bearer` with an HF user token (overview HTTP example). |
| Least privilege | PROVIDER_DECLARED: fine-grained token with `Make calls to Inference Providers`. No repository-write/admin permissions required by this documented flow (overview authentication). Do not create a token for this blocked preflight. |
| Discovery | PROVIDER_DECLARED: **GET** `/v1/models`, chat models plus optional provider status, prices and modality metadata (Hub API). POST support is UNKNOWN. |
| Chat | PROVIDER_DECLARED: POST `/v1/chat/completions`, model and message list; use non-streaming plain text only (overview/chat docs). |
| Routing | PROVIDER_DECLARED: explicit `model:provider` selects that provider; unsuffixed models use automatic routing. Policy suffixes and automatic routing are prohibited here (overview). This is a provider claim, not independent execution attestation. |
| Model identity | UNKNOWN: chat schema includes a string `model`, but inspected docs do not guarantee exact preservation of submitted `model:provider`. |
| Response framing | UNKNOWN: inspected docs do not promise bounded Content-Length framing. |
| Finish reason | UNKNOWN for a future call: the schema exposes the field; a particular model need not finish with `stop`. |
| Free credit | PROVIDER_DECLARED: free accounts get $0.10 monthly, subject to change; further use needs purchased credits. This is an experimental allowance, not sustained free coding compute (pricing). |
| Router data handling | PROVIDER_DECLARED: HF says routed bodies/responses are not stored, data is not stored for training, and debugging logs without user data/tokens last up to 30 days (security). This is not a declaration about a backend. |
| Router location, human access, complete subprocessor list | UNKNOWN from inspected evidence. |
| Backend retention, training, location, human access, subprocessors | UNKNOWN: no backend has been selected; HF directs users to each provider's policy (security). |

Do not substitute HF's router policy for an inference backend's policy. A future
ProcessorDeclaration identity must name **both the HF router operator and the
selected backend service**, with dated authoritative identity sources. It must
not simply label the processor Hugging Face when another service runs inference.
For SYNTHETIC only, ADR-024 permits the other policy facts to remain UNKNOWN;
identity is still mandatory. No declaration or disclosure admission is granted
by this document.

## Blocking repository contracts

1. **Discovery method mismatch.**
   `runtime/_composition/provider_discovery.py` uses the existing T2 exchange;
   `reference/_credential_https.py` constructs a fixed POST request. There is no
   method setting. ADR-024 section 22 requires the provider's documented method.
   HF documents GET. Do not spend the discovery call testing an undocumented
   POST, monkeypatch the request, substitute an SDK, or silently change T2.
2. **Discovery loses selection evidence.**
   `parse_model_list` accepts `data[].id`, ignores additional fields and returns
   only unique ModelId values (maximum 1,024, IDs maximum 256 characters; T2 body
   bound 4 MiB). HF's documented shape is structurally compatible within those
   bounds. Its provider statuses, modality and price fields are discarded.
   Consequently the result cannot supply the requested live backend/budget
   shortlist. An ID is not proof a particular backend serves it. The parser is
   unchanged. A separately reviewed bounded metadata path or independently
   sourced operator selection evidence is needed before chat can be enabled.
3. **Typed diagnostics are too coarse for some requested classifications.**
   The adapter maps both model mismatch and non-stop/invalid replies to
   ModelResponseRejectedError. The governed host does not expose chat HTTP status.
   T2/attempt outcomes collapse unsupported framing and several incomplete
   responses to UNKNOWN. No exception-string matching or raw response logging
   can fill these gaps safely.

These are findings about this integration, not evidence that HF itself is
incompatible. Core, ForgeAI, transport, parser and historical validators remain
unchanged. No new dependency or architectural decision is introduced. A future
provider-neutral extension needs explicit scope, contract review and qualification.
No HF-specific ModelPort, Agent, runtime or compute abstraction is proposed.

## Prepared plan and authority

The [preflight script](../scripts/hf_inference_compatibility_probe.py) has a static
`--plan` mode. It performs zero credential reads, DNS or network activity.
Default execution and `--live` print the blockers and return exit code 2, before
any credential prompt or transport. `--plan` returns 0 only for displaying the
plan, **not** for provider readiness. Unknown arguments are rejected without
echoing values. There is no endpoint override, model, prompt, repository or
credential input option.

The pure `discovery_admission` factory prepares an existing
ProviderDiscoveryAdmission from an exact future S1 SecretRef:

| Field | Exact planned value |
| --- | --- |
| Admission / revision | `hf-inference-discovery-1` / `d1` |
| Provider | `huggingface-inference-router` |
| Origin / root | `https://router.huggingface.co` / `/v1` |
| Operation | MODEL_DISCOVERY |
| Operator consumer | `hf-inference-compatibility-probe` |
| Credential | Exact provisioned revision; no wildcard or current alias |
| Window | Admission time through 15 minutes later |

The factory reads no credential and performs no discovery. Future provisioning
must use S1 hidden interactive input under purpose `provider-model-discovery`
and protected consumer `legoai.provider.model-discovery`. Chat must prompt again,
using purpose `remote-model-bearer` and the existing REMOTE credential consumer.
No internal copying of Secret material, environment token, CLI token, .env,
configuration token, pipe or chat token is permitted.

After blockers are resolved, the future interactive sequence is:

1. Confirm one governed **GET** discovery; S1 prompt; one durable attempt and
   purpose-bound Secret use through T2. No retry, fallback or redirect.
2. Show at most three coding candidates with evidenced live backend,
   text/chat support and affordable price. Operator selects one exact
   `model:backend`; refuse `auto`, `fastest`, `cheapest`, `preferred`, unsuffixed,
   malformed or unsupported selections. A different model/backend requires a
   new authorization, not a retry.
3. Freeze one binding, model, backend identity, processor declaration revision
   and SYNTHETIC-only CHAT admission for this consumer (short validity, no
   repository identities). Confirm that admission, prompt through S1 again,
   then make at most one governed chat with exactly
   `Return exactly the word READY.` No platform prompt, task, diagnostics or
   repository text is included. Preserve exact response model checking and
   `finish_reason == "stop"`; use bounded output tokens and a timeout.

The chat docs recommend Qwen2.5-Coder-32B-Instruct and
Qwen3-Coder-480B-A35B-Instruct as coding models. They are **research candidates**,
not a live shortlist: neither availability, backend nor cost was observed.
Do not automatically pick the larger model. Current budget and exact pairing
must be established later. There are **zero executable calls** in this version;
the future intended ceiling is one discovery plus one chat.

## Closed outcomes and observation limits

The script declares the requested vocabulary. Only the local preflight
PROVIDER_IDENTITY_INDETERMINATE finding is emitted now, explicitly without a
provider observation. The following is the future mapping contract, not a claim
that this version implements live classification:

| Outcome | Required typed evidence / current limitation |
| --- | --- |
| HF_COMPATIBILITY_PASS | Successful governed discovery, adequately pinned processor, successful exact-model chat and exact READY reply. Not observed. |
| AUTHENTICATION_FAILURE | Complete HTTP 401; status available in ModelDiscovery, not current chat result. |
| AUTHORIZATION_FAILURE | Complete HTTP 403; same limitation. No speculation about the reason. |
| MODEL_DISCOVERY_INCOMPATIBLE | Typed MALFORMED discovery or observed method/endpoint rejection. A local method mismatch is a blocker, not an observed HTTP failure. |
| PROVIDER_IDENTITY_INDETERMINATE | Insufficient evidence for one exact backend; stop before chat. Current local finding. |
| RESPONSE_FRAMING_INCOMPATIBLE | A distinct typed framing rejection would be needed. Current UNKNOWN alone is insufficient. |
| MODEL_IDENTITY_INCOMPATIBLE | A distinct typed identity rejection would be needed. Current generic rejection is insufficient. |
| CHAT_CONTRACT_INCOMPATIBLE | Complete successful transport followed by typed adapter contract rejection; mismatch and non-stop are not distinguished. |
| PROVIDER_AVAILABILITY_FAILURE | Complete 5xx status where exposed; no retry. |
| CREDIT_OR_QUOTA_EXHAUSTED | Explicit typed quota evidence needed. 429 alone cannot distinguish exhausted credits from rate limiting; keep it inconclusive. |
| RESULT_INCONCLUSIVE | Missing evidence, NOT_SENT/UNKNOWN without a narrower typed cause, ambiguous 429, or a valid chat reply other than READY. |

No raw response or exception text is used to manufacture a finer diagnosis.
Future safe output may contain admitted identities, attempt/admission references,
typed status/state/effect and at most the fixed successful reply READY. It must
exclude token material, headers, Secret internals, raw bodies and unrestricted
metadata. Current output is static: no provider-controlled strings or reply are
printed, and no evidence store is created.

## Operator validation

Run from the repository root with the existing locked development environments:

```powershell
uv run --locked --offline --no-sync python .\scripts\hf_inference_compatibility_probe.py --plan
uv run --locked --offline --no-sync python .\validate_hf_inference_compatibility_preflight.py
```

If an environment is missing, prepare it from the local cache only:

```powershell
uv sync --locked --offline
uv sync --project .\examples\forgeai --locked --offline
```

Missing cached dependencies should be reported, not silently downloaded.
Return the validator's output and exit code. No token is needed. The validator
runs preflight/admission/parser tests, discovery regressions, REMOTE, disclosure,
Secret/S1, custody and T2 regressions, Core architecture, ForgeAI remote-profile
regressions, mypy, Ruff lint/format and `git diff --check`. Synthetic loopback TLS
is allowed. It excludes the real Docker PROJECT acquisition cases and does not
invoke the historical validator that acquires dependencies from PyPI.

Coverage boundaries against the requested 25 cases:

- Exact root, separate admission purpose, zero credentials/environment use,
  zero network in plan/default/live modes, redacted rejected arguments,
  parser shape/uniqueness and no HF identifiers in Core: new offline tests.
- Existing hidden S1, Secret purpose/currentness, disclosure, exact model,
  finish reason, framing, HTTP status, custody and no-retry contracts: existing
  regression suites included. These are provider-neutral proofs only.
- HF selection/refusal, real two-stage provisioning, at-most-one calls through
  the future harness, safe live evidence and fine-grained classifications:
  **not implemented or tested**, because live orchestration is blocked. Zero
  calls in this harness is not advertised as two-call qualification.

No validation was executed by the agent, per operator instruction. The supplied
successful operator run validates the blocked preflight only, not HF compatibility.

## Live authorization and follow-on work

There is no runnable two-call live command yet. Do not run `--live` expecting
token prompts; it deliberately refuses. Resolve the method, selection evidence
and typed-observation requirements and obtain local validation before requesting:

`AUTHORIZE HF-INFERENCE-PROVIDERS-COMPATIBILITY-1 LIVE PROBE`

This phrase is recorded for the future gate; live authorization is **not being
requested now**. No provider API calls have occurred; official documentation
reads did occur. No KISSKI, Kaggle, Colab, Space, ZeroGPU, vLLM, tunnel or ComfyUI
work is included.

After actual compatibility passes, FORGEAI-HF-LIVE-PILOT-1 remains a separately
authorized bounded repository disclosure and Coding/Reviewer quality experiment.
It additionally needs known mandatory non-SYNTHETIC processor policy facts;
synthetic success alone does not make it ready. FREE-GPU-MODEL-RUNTIME-KAGGLE-1
remains the operator's proposed first raw free-GPU experiment, separately scoped;
current Kaggle availability and suitability were not researched here.
