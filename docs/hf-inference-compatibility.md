# HF-INFERENCE-PROVIDERS-COMPATIBILITY-1

## Current status: discovery v2 locally qualified; SYNTHETIC LIVE-PROBE READY

[PROVIDER-MODEL-DISCOVERY-2](provider-model-discovery-2.md) is **LOCALLY QUALIFIED**
on 2026-10-10 at commit `c7353ccf180a54effbf2e80a048e8ae4b8197dc8`, branch
`br-LegoAIPyLLMComfyCR-ForgeAI-KISSKIColabKagHF`; the pre-edit working tree was clean.
The maintainer's complete validator passed 723 discovery/security tests, 364
architecture/package tests and 69 ForgeAI tests (1,156 total; 2 deselected),
mypy on 16 files, Ruff lint/format and whitespace checks. Exact evidence and limits
are recorded in the linked qualification record. The earlier 1,044-test record
below remains historical. The first live discovery is recorded separately below.

The closeout sets **LIVE_READY = True** after reviewing ADR-024 and the tested
orchestration. This means **SYNTHETIC LIVE-PROBE READY**, not provider compatibility
or authorization to run. The maintainer's focused closeout run passed **467 tests
in 29.54s**, mypy on **3 source files**, Ruff lint, format (**3 files already
formatted**) and `git diff --check`. This passed the prerequisite gate for the
diagnostics slice; its new edits remain **LOCAL VALIDATION PENDING**.

## LIVE PROBE 1 — DISCOVERY SUCCEEDED / CHAT NOT ATTEMPTED

Observed on **2026-10-10**, from the maintainer's supplied live transcript:
one governed **GET /v1/models** at `https://router.huggingface.co/v1`, router
`huggingface-inference-router`; HTTP **200**, ModelDiscovery **LISTED**, attempt
**COMPLETED**. Attempt metadata: `attempt-3ebe90cc6e7fbf9965ac9d56b5c9a478`.
No eligible exact pair survived the shortlist. There was no second Secret prompt,
**zero chat calls**, no repository disclosure, no retry and no fallback.
Final classification: **PROVIDER_IDENTITY_INDETERMINATE**.

This is live discovery evidence only. It does not establish HF chat or selected
backend compatibility, model quality, long-term availability or repository-disclosure
readiness. The raw catalog was deliberately not persisted; the exact failed policy
assumptions cannot be reconstructed from this transcript. The local custody database
has not been copied into the repository, and no credential is recorded here.

## LIVE PROBE 2 — DISCOVERY SUCCEEDED / NO ALLOWLIST OVERLAP

Maintainer-observed on **2026-10-10**: one governed GET `/v1/models`, HTTP **200**,
ModelDiscovery **LISTED**, attempt **COMPLETED**. Attempt metadata:
`attempt-0737882d7ad3609dcb5927d5326b5c36`.
128 models, 294 model/backend pairs, one allowlisted model observed, zero models
without backend observations, and **zero eligible pairs**.

Rejection counts (overlapping pair counts): MODEL_NOT_ALLOWED 292;
BACKEND_NOT_ALLOWED 219; BACKEND_STATUS_NOT_LIVE 0; INPUT_MODALITY_MISSING 0;
OUTPUT_MODALITY_MISSING 0; MODALITY_SHAPE_UNSUPPORTED 104; INPUT_PRICE_MISSING 104;
OUTPUT_PRICE_MISSING 104; INPUT_PRICE_ABOVE_LIMIT 0; OUTPUT_PRICE_ABOVE_LIMIT 8.

There were **two pairs for allowlisted models** (294 minus 292). Neither overlapped
the current backend allowlist: otherwise the old both-allowlisted sampling rule
would have printed a rejection sample or the pair would have been eligible.
Their exact backend IDs were not printed and are not inferred here. Zero chat
calls, no second Secret prompt, no repository disclosure, no retry/fallback.
Final classification: **PROVIDER_IDENTITY_INDETERMINATE**. This remains discovery
evidence only, not chat compatibility, processor identity or lasting availability.

## LIVE PROBE 4 — ELIGIBLE NSCALE PAIR / CHAT PROVIDER-REJECTED

Maintainer-supplied live record, 2026-10-10: discovery HTTP **200**, **LISTED /
COMPLETED**, attempt `attempt-23a88a4f04923b4b5db52d4eb8032453`.
The fresh eligible pair was `Qwen/Qwen2.5-Coder-32B-Instruct:nscale`, advertised
live, text/text, USD 0.06 input / 0.20 output per million tokens. Operator selected
pair **1**, approved SYNTHETIC disclosure and completed the second hidden S1
provisioning. Admission `hf-synthetic-chat@a1`, declaration `hf-probe-processor@r1`.

Exactly one chat attempt: execution `exec-de25271a0d8b4e659927c3421f77e760`, attempt
state **PROVIDER_REJECTED**, effect **NONE**, error **DependencyFailure / terminal**.
Final classification: **RESULT_INCONCLUSIVE**. No retry, fallback, second model or
repository disclosure. The exact chat HTTP status was not exposed or persisted;
it cannot be inferred retrospectively. This is not evidence of Nscale incompatibility
or a quota/authentication root cause, and does not qualify HF chat compatibility.

## REMOTE-CHAT-HTTP-STATUS-DIAGNOSTICS-1

Status: **IMPLEMENTED — LOCAL VALIDATION PENDING**. No provider requests during
implementation. The prerequisite Nscale maintainer run passed 336 regression and
364 architecture tests (700 total), mypy on six files, lint, formatting and whitespace.
Those results do not cover this diagnostic extension.

The private REMOTE Model invocation plane captures only an integer HTTP status,
keyed by execution identity, after T2 observes a complete bounded response and
custody terminal settlement returns. The existing parser convention is exact
Python `int`, **200–599**, excluding bool. Capture precedes adapter validation:
a complete 200 with an invalid model/finish reason therefore still has status 200.
Invalid diagnostic values are ignored, not converted into invocation failures.
No headers, reason phrase, error body, exception text, URL, prompt or credential
are added to diagnostics. No error-body parsing or exception-message matching.

Storage is per-host and ephemeral, bounded by the existing attempt-store capacity
(one entry per completed chat attempt). A private thread-confined host inspection
helper returns `int | None` for an execution minted by that host. Unsent, incomplete,
unknown, foreign, embedding and LOCAL executions have no chat status. The mapping
does not survive a fresh host or process restart. No custody schema/record changes
or historical rewrites; prior attempts remain readable and have no recoverable
exact status. This is trusted internal inspection, not a new public HTTP API.

Pipeline review: T2 constructs HttpResponse only after complete framing; exchange
settles the attempt; the REMOTE invocation captures the integer; the shared adapter
retains existing validation and exceptions; governed Model and Agent projection
retain their existing effect/error values. ForgeAI's projection is unchanged.
The HF harness reads the separate private observation by execution ID. ErrorCause
currently carries attributed category/record identity, so extending it would broaden
a public contract unnecessarily. ModelPort, ChatRequest/ChatResponse, AgentRequest,
GovernedHost and all public result contracts remain unchanged. KISSKI discovery
status handling is unchanged. No provider-specific branches were added to Core.

| Complete chat status | HF classification |
| --- | --- |
| 401 | AUTHENTICATION_FAILURE |
| 403 | AUTHORIZATION_FAILURE |
| 404, 405 and other 4xx except 429 | CHAT_CONTRACT_INCOMPATIBLE |
| 429 | RESULT_INCONCLUSIVE; no credit/quota diagnosis |
| 5xx | PROVIDER_AVAILABILITY_FAILURE |
| 2xx | Existing strict model, finish-reason and exact READY checks still required |
| Absent/incomplete | Existing coarse outcome; no invented status |

Status grants no retry, fallback, disclosure, selection or binding authority.
Complete non-2xx attempts still settle PROVIDER_REJECTED with Model effect NONE;
429/503 retain their existing potentially-retryable category without executing a
retry. Other existing recoverability and disclosure-effect semantics remain intact.
Complete invalid 2xx attempts remain transport COMPLETED but Model-rejected; they
do not become compatibility passes. Timeout, malformed/truncated/chunked framing
and connection failures retain their qualified effects and absent status.

Operator validator (locked existing environment, synthetic local TLS only):

```powershell
uv run --locked --offline --no-sync python .\validate_remote_chat_http_status_diagnostics_1.py
```

It covers complete status and incomplete-response cases, T2/attempt/REMOTE/Agent,
HF/Nscale/KISSKI discovery, disclosure, Secret/canary and architecture regressions,
mypy, Ruff lint/format and whitespace. No provider, token prompt or Docker acquisition.
The agent did not run tests or checks; formatter edits only. After maintainer
validation, stop. One separately authorized diagnostic live probe may re-observe
discovery, require selection and SYNTHETIC approval, provision the second Secret
and attempt one chat. No live root cause, provider compatibility, error-body
support, quota diagnosis or repository-disclosure readiness is claimed here.

## LIVE PROBE 3 — NSCALE OBSERVED / CHAT NOT ATTEMPTED

Maintainer-supplied bounded discovery observations, recorded 2026-10-10:
`Qwen/Qwen2.5-Coder-32B-Instruct` had these two backend observations:

| Backend | Status | Input/output | Input/output USD per million tokens | Rejections at probe time |
| --- | --- | --- | --- | --- |
| featherless-ai | live | text/text | UNKNOWN / UNKNOWN | BACKEND_NOT_ALLOWED, INPUT_PRICE_MISSING, OUTPUT_PRICE_MISSING |
| nscale | live | text/text | 0.06 / 0.20 | BACKEND_NOT_ALLOWED |

Zero chat calls, no repository disclosure, no retry/fallback; final classification
**PROVIDER_IDENTITY_INDETERMINATE**. No attempt ID was supplied for this record.
These are point-in-time observed values, not permanent availability or prices.
The VERIFIED scope is limited to mechanical observation through the governed path;
advertised status/prices do not verify actual service delivery, billing or policy.
No raw catalog, credential or custody database is added to the repository.

## HF-NSCALE-SYNTHETIC-BACKEND-POLICY-1

Status: **IMPLEMENTED — LOCAL VALIDATION PENDING** (2026-10-10).
The prerequisite overlap validator passed 184 regression tests and 364 architecture
tests (**548 total**), mypy on four files, Ruff lint/format and whitespace checks.
Those results do not cover this policy change. No provider API calls or credential
prompts occurred during the review; public documentation lookup only.

### Authoritative source review

All sources below were inspected on 2026-10-10. Documentation statements are
**PROVIDER_DECLARED**, never VERIFIED or OPERATOR_ATTESTED.

- [HF Nscale provider documentation](https://huggingface.co/docs/inference-providers/providers/nscale)
  identifies the Nscale inference service, lists Chat Completion and demonstrates
  explicit `model:nscale` routing through the HF router. No specific contracting
  Nscale legal entity is inferred for this routed request.
- [HF security/privacy](https://huggingface.co/docs/inference-providers/security)
  describes router-side handling: no request/response storage, no user-data storage
  for training, and debugging logs retained up to 30 days without user data/tokens.
  Those statements concern HF, not backend policy; HF directs readers to providers.
- [Nscale Serverless Inference announcement](https://www.nscale.com/blog/introducing-nscale-serverless-inference-scalable-ai-without-infrastructure-hassles),
  published 2025-04-02, explicitly says the Serverless service does not log or train
  on request/response content. This is a service-specific content-handling claim,
  not proof of no technical/account logs or human access.
- [Nscale Serverless documentation overview](https://docs.nscale.com/docs/getting-started/overview)
  and [Chat Completion API documentation](https://docs.nscale.com/api-reference/inference/create-chat-completion)
  establish the documented Serverless/chat service context; neither is an executed
  API request. They do not bind this HF-routed request to a processing region.
- [Nscale privacy policy](https://www.nscale.com/policies/privacy-policy), updated
  **2026-05-12**, covers usage details, technical logs/timestamps/routing metrics,
  international transfers and purpose-dependent retention without a fixed maximum.
  These broad personal-data statements are not prompt-content retention claims.
- [Nscale subprocessor policy](https://www.nscale.com/policies/sub-processors), updated
  **2026-09-15**, lists Auth0, Vercel, Neon, Upstash, Sentry, PostHog, Novu,
  Metronome and Stripe. It qualifies service/customer applicability and says
  processing locations can vary by configuration, region and subprocessors.
  This list does not establish the exact processors of an HF inference request.

### Fact disposition and decision

| Fact | Review basis and scope | Executable declaration |
| --- | --- | --- |
| Processor identity | PROVIDER_DECLARED: Hugging Face router and Nscale service, from dated HF sources | `Hugging Face router; inference processor Nscale`, PROVIDER_DECLARED |
| Training | PROVIDER_DECLARED: Serverless content is not used for training | Existing aggregate declaration remains UNKNOWN; no policy-fact specialization added |
| Request/response retention | PROVIDER_DECLARED: Serverless request/response content is not logged; not a general all-data retention guarantee | UNKNOWN retained conservatively |
| Service/account metadata retention | PROVIDER_DECLARED: metadata/usage collection and purpose-dependent retention; no precise duration established | No new Core field; kept separate in this review |
| Location | UNKNOWN for the exact routed request; no region binding established | UNKNOWN |
| Human access | UNKNOWN for inference content; no-access is not implied by non-logging, non-training or security controls | UNKNOWN |
| Subprocessors | General list is PROVIDER_DECLARED; exact request-specific applicability UNKNOWN | UNKNOWN |

ADR-024 §5.2 allows those UNKNOWN facts for **SYNTHETIC only**, while requiring a
processor service/legal identity. The service identity satisfies that requirement;
no legal-entity assumption or router-to-backend policy substitution is needed.
The review therefore permits appending `("nscale", "Nscale", "nscale")` to the
harness policy using its existing dated source and declaration mechanism. The prior
three entries retain their order. The generic evaluator and Core are unchanged.

This policy admits consideration of Nscale only for `Return exactly the word READY.`
under a SYNTHETIC admission. No TASK_TEXT, REPOSITORY_CONTENT, DERIVED_DIAGNOSTIC
or customer data is admitted. Featherless AI is not added: its observed prices
were absent, so it is not eligible under current policy. This is not an assessment
that Featherless is unsafe, incompatible or unsupported by HF.

Nscale's observed live/text/text/0.06/0.20 shape becomes eligible solely through
allowlist membership. Future discovery must re-observe the facts; no production
code hard-codes that pair, availability or prices. Missing/non-live/unsupported/
over-limit observations still fail. The operator must choose a number, approve
SYNTHETIC disclosure and provision the second S1 credential before any chat.

Operator validation from the repository root:

```powershell
uv run --locked --offline --no-sync python .\validate_hf_nscale_synthetic_backend_policy_1.py
```

The validator includes Nscale identity/policy, eligibility/overlap/HF harness,
discovery-v2, disclosure governance, Secret/canary and architecture tests, mypy,
Ruff lint/format and whitespace. Local synthetic TLS exercises the actual governed
chat path with the Nscale suffix; no provider or Docker acquisition. No tests or
checks were run internally by the agent; formatting edits only.

After successful maintainer validation, the maximum claim is approval of the
Nscale service identity for this harness's SYNTHETIC policy. This establishes no
HF/Nscale chat compatibility, ForgeAI compatibility, repository-disclosure safety,
production suitability, free-GPU qualification or persistent model availability.
Stop after validation. A separately authorized future live probe may perform one
discovery and, after fresh eligibility, selection, approval and separate S1
provisioning, at most one chat. That would be the first HF chat attempt. No such
run is authorized or executed by this change.

## HF-ALLOWLIST-OVERLAP-DIAGNOSTICS-2 (prior policy context)

Status: **IMPLEMENTED — LOCAL VALIDATION PENDING**. Harness-local changes only.
The prerequisite diagnostics-1 maintainer run passed **174** eligibility/security
tests and **364** architecture tests (**538 total**), mypy on three files, Ruff
lint/format and whitespace. Those results do not validate this new slice.

Official documentation inspected on **2026-10-10**, separately from live evidence:
HF's [Chat Completion recommendations](https://huggingface.co/docs/inference-providers/tasks/chat-completion)
still list both `Qwen/Qwen2.5-Coder-32B-Instruct` and
`Qwen/Qwen3-Coder-480B-A35B-Instruct` as coding models. The
[provider matrix](https://huggingface.co/docs/inference-providers/index#partners)
lists additional Chat Completion providers, including Cerebras, DeepInfra and Groq,
beyond the harness's Fireworks/Novita/Together policy. This does not establish that
any additional provider served either model in probe 2. Only public documentation
was read; no discovery/inference API call occurred during implementation.

The current diagnostic rule supersedes the diagnostics-1 sample rule below:
sample only **allowlisted models**, regardless of backend allowlist membership.
Do not sample arbitrary models even if their backend is allowed. At most **four
observations total**, including eligible observations, are ordered lexically by
model/backend ID. Existing aggregate counts remain unchanged; at most **20 lines**
are emitted (six summary lines, ten reason counts, four observations).

Each sample contains only the exact allowlisted model ID, observed backend ID,
status, input/output modalities, input/output prices and closed rejection reasons.
These come from parser-normalized observations, never a raw response. JSON string
escaping prevents delimiter ambiguity; this is an explicit field projection, not
a response/catalog dump. Absent values remain null or empty modality arrays.
The display guard retains printable non-whitespace ASCII, no wildcard/control
characters and 128-character backend / 32-character status/modality bounds.
It additionally omits observations containing URLs or HF-token-shaped text.
Such omissions never change aggregate counts or eligibility. No credential value
or SecretRef is passed to diagnostics, and nothing is persisted.

An observed backend ID is **not authority**: it does not establish identity or
processor policy, construct a ProcessorDeclaration, change a binding, grant
disclosure or admit chat. Unknown backends still receive BACKEND_NOT_ALLOWED.
The evaluator, both allowlists, price ceiling, status and modality requirements,
three-choice ordering, numbered selection, no-retry/no-fallback policy and Core
contracts remain unchanged.

Operator validation (existing locked environment; no Internet, Docker or provider):

```powershell
uv run --locked --offline --no-sync python .\validate_hf_allowlist_overlap_diagnostics_2.py
```

This runs overlap/eligibility/HF tests, discovery-v2, Secret/canary and architecture
regressions, mypy, Ruff lint/format and whitespace checks. The agent has not run
these checks. Stop after validation. One more **separately authorized governed
discovery** is needed to observe the exact current backend IDs; it is not authorized
or executed here. Its result would support either reviewing observed providers for
an allowlist proposal or stopping HF work if none is acceptable.

Any future backend review must cover official HF identity documentation, Chat
Completion support, explicit model:provider routing, ADR-024 processor/privacy
facts and observed status/modalities/prices. No provider is trusted simply because
HF lists its ID. No backend policy review or allowlist expansion is implemented.

## HF-DISCOVERY-ELIGIBILITY-DIAGNOSTICS-1 (historical sampling rule)

Status: **LOCALLY VALIDATED** by the maintainer (538 tests and all static checks,
as recorded above). The sample rule described in this historical section is
superseded by diagnostics-2. No provider call occurred
during this slice. Do not rerun discovery or `--live` as part of validation.

The harness now evaluates each parser-normalized model/backend pair with a pure
`evaluate_candidate` function. Its immutable result holds only the exact observed
model and provider IDs, eligibility and an ordered tuple of closed reasons:

`MODEL_NOT_ALLOWED`, `BACKEND_NOT_ALLOWED`, `BACKEND_STATUS_NOT_LIVE`,
`INPUT_MODALITY_MISSING`, `OUTPUT_MODALITY_MISSING`, `MODALITY_SHAPE_UNSUPPORTED`,
`INPUT_PRICE_MISSING`, `OUTPUT_PRICE_MISSING`, `INPUT_PRICE_ABOVE_LIMIT`,
`OUTPUT_PRICE_ABOVE_LIMIT`.

All applicable reasons are retained in that order. Missing status is not live;
empty modality observations receive missing reasons, while nonempty shapes other
than exactly text receive the unsupported-shape reason. Prices use only the finite,
nonnegative bounded numeric observations accepted by the existing parser.

Output contains model, pair and eligible-pair counts, the count of observed
allowlisted models, models without backend observations, and all ten rejection
counts. Counts overlap because a pair can fail several rules. Models with no
provider observations contribute to model counts but do not create invented pairs.
Eligible counts cover all pairs, before the existing three-choice shortlist cap.

At most **five rejected pairs** are sampled in lexical model/provider order.
Both identifiers must be allowlisted, a deliberately stricter subset of the
permitted model-OR-backend sampling boundary. This avoids echoing arbitrary IDs,
URLs or credential-like provider strings. Samples show only those fixed IDs and
closed reasons; other pairs contribute aggregate counts only. At most **21 output
lines** are emitted: six summary lines, ten reason counts and five samples.
No raw JSON, descriptions, arbitrary status text, metadata, prices or modalities
are printed by diagnostics. No catalog or diagnostic object is persisted.

The same evaluator controls the existing shortlist. Coding models, backend
identities, `live` status, exact text/text shape, both prices present and <= USD 5/M
remain unchanged. Ordering, numbered selection, exact binding, SYNTHETIC admission,
separate S1 purposes, output containment and call ceilings remain unchanged.
Diagnostics have no Secret input, I/O, authority, routing or binding mutation.
Core discovery, ModelPort, T2, provider control and Model errors are unchanged.
An empty shortlist retains **PROVIDER_IDENTITY_INDETERMINATE**.

Run from the root with the existing locked environment:

```powershell
uv run --locked --offline --no-sync python .\validate_hf_discovery_eligibility_diagnostics_1.py
```

The focused validator runs evaluator and HF harness tests, discovery-v2 and
Secret/canary regressions, architecture, mypy, Ruff lint/format and whitespace.
Tests use synthetic data and localhost TLS only; no Internet, real provider or
Docker acquisition. No tests or checks were executed internally by the agent.

After local qualification, stop. Another live probe is **not authorized** by this
slice. A separately authorized future observation could support maintainer review
of these decision categories; the first response cannot establish any of them:

- A: policy identifiers are stale; prepare a separately reviewed policy update
  using authoritative documentation and bounded observations.
- B: required models/backends are absent from the observed catalog.
- C: an observed backend fails current status, price or modality constraints.
- D: discovery metadata is insufficient.

If no suitable HF pair exists, stop adapting HF and consider separately authorized
FREE-GPU-MODEL-RUNTIME-KAGGLE-1. If an eligible pair later passes SYNTHETIC chat,
review mandatory non-SYNTHETIC facts before FORGEAI-HF-LIVE-PILOT-1. Neither next
slice is authorized or implemented here.

## Existing fixed SYNTHETIC probe contract

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
  [Together AI](https://huggingface.co/docs/inference-providers/providers/together),
  then [Nscale](https://huggingface.co/docs/inference-providers/providers/nscale)
  for SYNTHETIC only under the policy review above.
  These dated provider-declared identities do not establish live availability.
- Each pair must actually appear in this governed discovery response, with
  status `live`, exactly text input/output and both prices present and at most
  USD 5 per million tokens each. This is price screening, not a billing guarantee.
  Missing facts exclude a candidate. No inference from model size or names.
- Order follows the displayed model and backend allowlist order, not a quality, speed or
  price ranking. Keep at most three. Only a displayed number can select a pair;
  no eligible candidate means no chat or second Secret prompt.

The declaration names both HF's router and the selected inference service using
official identity sources retrieved 2026-10-10. Other processor facts remain
UNKNOWN for this SYNTHETIC scope. Discovery grants no disclosure authority.
ADR-024 §5.2 permits the legal **or service** name: the exact observed backend ID
must match the closed Fireworks AI/Novita/Together AI/Nscale mapping above. Its dated
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

Diagnostic restraint remains: the REMOTE-CHAT-HTTP-STATUS-DIAGNOSTICS-1 section
above extends exact complete-response status to chat without new Model errors.
Discovery and chat distinguish 401/403 and 5xx; 429 remains inconclusive about quota.
Model mismatch and non-stop reasons stay coarse CHAT_CONTRACT_INCOMPATIBLE.
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
