# LegoAI provider and compute portability — architecture decision

Status: **DECISION RECORD — architecture assessment only (2026-10-07).** No code,
configuration, ADR or runtime change. No model was run, no provider was contacted
and nothing was downloaded. KISSKI was not accessed; every KISSKI statement below
is labelled as verified, inferred or an unverified operational assumption.

Outcome: **PROTOCOL-ADAPTER PORTABILITY RECOMMENDED.**

Evidence base (inspected at `9422a33`):
- `src/legoai/intelligence/model/{ports,values,routing}.py`;
- `src/legoai/runtime/{api,local}.py` and `runtime/_composition/{model_selection,model_governed}.py`;
- `src/legoai/reference/model.py` (the Ollama adapter) and `kernel/errors.py`;
- ADR-010, ADR-014, ADR-017, ADR-019 and ADR-020; SECURITY SEC-039;
- ForgeAI `composition.py`/`cli.py`, the three engineering Agent definitions;
- `packages/legoai-generative-media` (`config.py`, `ports.py`, `composition.py`);
- MODULE-CATALOG, ASSEMBLING-APPLICATIONS, the consumer-readiness plan and the
  master roadmap (G01, G03, G10).

## 1. Executive decision

1. **The vision is reachable with the existing Ports.** ModelPort and its request,
   result and error contracts are already provider-neutral. Generative media
   already has its own Ports. No universal provider abstraction is needed.
2. **Integrate by protocol, not by platform.** Add a small number of protocol
   adapters behind the existing Ports. The first is a generic
   **OpenAI-compatible ModelPort adapter**. KISSKI, local vLLM, an owned GPU and
   compatible hosted endpoints are then endpoints, not adapters.
3. **Selection stays trusted configuration, pinned at host open.** ADR-014's one
   pinned binding per host and ADR-019's configuration selection are kept. There
   is no runtime routing, fallback or per-call switching.
4. **Two prerequisites are blockers for any remote or credentialed provider:**
   - a minimal ADR-010 Secret realization (no credentialed provider may be added
     without it; ADR-019 already says so);
   - enforcement of SEC-039 provider data-use constraints before content leaves
     the machine (today a remote Ollama URL is accepted with no such check).
5. **Virtual Try-On on KISSKI is blocked by ADR-020 §8,** not by compute. Remote
   personal-image transfer is refused by decision until that ADR is amended.
6. **CONTENT-DISCOVERY-1Q-R4 is already complete** (decision C, stop rule applied).
   Portability work does not depend on it and must not be used to rescue it.

## 2. Current architecture (verified)

```
Application domain (ForgeAI, DocuMind, engineering Agents)
    | imports only public values/Ports
GovernedHost (legoai.runtime.api)           <- public Protocol
    | opened by legoai.runtime.local.open_local_host(config, selection)
Private composition (_composition/*)        <- Catalog, resolution, authorization,
    |                                          dispatch, Coordinator, effect mapping
ModelPort (chat, embed)                     <- provider-neutral Port
    |
OllamaModelAdapter (reference/model.py)     <- stdlib urllib, /api/chat, /api/embed
    |
Ollama endpoint (any http/https base URL)
```

- **Model contracts.** `ChatRequest` carries messages only. `ChatResult` and
  `EmbeddingResult` carry the observed `ModelId` and `ProviderId`. Requests never
  name a model or provider. There are no provider SDK types.
- **Errors and effects.** Three adapter exceptions map, in private composition, to
  `EffectExtent` and `Recoverability`:

  | Adapter exception | Effect | Recoverability |
  | --- | --- | --- |
  | `ModelPreflightError` (nothing sent) | NONE | POTENTIALLY_RETRYABLE |
  | `ModelResponseUncertainError` (sent, no reliable response) | UNKNOWN | REQUIRES_INTERVENTION |
  | `ModelResponseRejectedError` (complete error or invalid response) | NONE | TERMINAL |

  A result whose model or provider identity differs from the pinned binding is
  rejected. There is one invocation claim, no retry and no fallback.
- **Configuration.** `LocalHostConfig.bindings` holds up to 16
  `ModelBindingConfig(binding_id, requirement, provider)`. `provider` is a closed
  union: `OllamaSettings` (built-in, credential-free) or `TrustedModelContribution`
  (operator composition-root code supplying any `ModelPort`).
- **Selection.** The selection mapping is exactly `{"revision", "binding"}`.
  Only the selected binding is admitted, published and constructed, once, at open.
  A changed selection means opening a new host.
- **Purposes.** `ModelPurpose` is closed (`CHAT`, `EMBEDDING`). A purpose the
  selected binding lacks fails with `PURPOSE_UNAVAILABLE` before dispatch.
- **Agents.** RepositoryAnalyst, CodingAgent and IndependentReviewer all declare
  `ModelRequirement("engineering-reasoning")`. The host's Agent runtime routes
  over the single pinned binding.
- **Consumers.** ForgeAI builds `ollama_binding(...)` or a replay
  `TrustedModelContribution` in its composition root. Domain code never sees a
  provider.
- **Generative media** has separate Ports (`TextToImagePort`, `VirtualTryOnPort`,
  `JobReconciliationPort`) and a strict TOML provider config with `endpoint`,
  `api_family`, `deployment = local | remote`, `binding`, `allowed_origins` and
  `auth = none | bearer` with `secret_ref = env:NAME`. Its secret resolver is
  explicitly adapter-local. It still composes Core through private internals
  (CR-1c).

## 3. Current limitations

| # | Limitation | Kind |
| --- | --- | --- |
| L1 | Ollama is the only built-in provider settings type; any other provider needs composition-root code, not configuration | Debt |
| L2 | No governed Secret realization (ADR-010 accepted, not implemented); `OllamaSettings` has no credential field and ADR-019 rejects raw-secret paths | Blocker for credentialed providers |
| L3 | SEC-039 provider data-use, retention, residency and training constraints are not enforced; `OllamaSettings` accepts any http/https host, so remote disclosure is unchecked today | Security gap |
| L4 | The provider-neutral chat/embedding offers and their release are produced by Ollama-named functions (`ollama_chat_offer`, `ollama_release`) and reused for every contribution | Naming/ownership debt; contract content is neutral |
| L5 | Every complete provider error is TERMINAL; a rate limit or temporary unavailability cannot be reported as retryable | Vocabulary gap (small) |
| L6 | Truncated generation is not detected: the Ollama adapter ignores the done reason, so a length-cut reply can be a success | Adapter gap |
| L7 | Blocking `urllib` inside `asyncio.to_thread`: cancelling the caller does not stop the HTTP request. Remote calls widen the UNKNOWN window | Known limitation (ADR-015) |
| L8 | No generation bound (max output tokens) reaches the provider; ADR-017 already states accepted-output limits do not bound provider cost | Adapter configuration gap |
| L9 | One pinned binding per host, and all engineering Agents share one profile; per-Agent models need several hosts | Intentional boundary; generalization deferred |
| L10 | No reusable file-based loader for model bindings; each application builds its own values | Convenience gap |
| L11 | No provider conformance suite across adapters | Verification gap |
| L12 | CR-1c: generative media uses private Core composition | Debt |

## 4. Model, provider, endpoint, deployment and hardware separation

| Concept | Meaning | Where it lives today | Recommendation |
| --- | --- | --- | --- |
| **Model identity** | Which model answers | `ModelId`; `chat_model`/`embedding_model` in settings; observed in results | Keep. Never a request field |
| **Provider protocol** | Wire protocol spoken | The settings **type** (`OllamaSettings`) | Keep the type as the protocol. Add one type per genuinely different protocol |
| **Provider instance** | Which configured provider produced a result | `ProviderId` | Keep. Name it per endpoint (for example `kisski-saia`, `local-vllm`) |
| **Execution endpoint** | Where requests go | `base_url` in settings | Keep |
| **Deployment location** | Whether content leaves the operator's machine | Not represented for models; media has `deployment` | **Add** a closed local/remote declaration that drives SEC-039 checks |
| **Hardware** | CPU, RTX, A100, H100 | Not represented; evaluation conditions record `hardware_class` | **Do not represent** in runtime configuration. Record only as evaluation evidence |

These distinctions are already separate fields, not one `provider` string. The
only missing concept with runtime consequences is deployment location, and it
matters for disclosure, not for dispatch. Hardware never changes LegoAI behavior,
so it does not belong in LegoAI runtime types.

## 5. Current extension seam: answers

**A. Can a second model provider be plugged into ModelPort without changing
domain contracts?** Yes, for a credential-free provider. A
`TrustedModelContribution` can supply any `ModelPort`; requests, results and
effects are unchanged, and the identity check uses the contribution's declared
model and provider IDs. ForgeAI's replay binding already proves the seam.

**B. What prevents configuration-driven switching?**
1. Only Ollama is a built-in settings type (L1). A second protocol needs
   composition-root code until it becomes a built-in settings type.
2. There is no governed Secret path (L2), so no authenticated provider can be
   configured at all.
3. Remote disclosure is not governed (L3).
4. Ollama-named offer helpers (L4) must be neutralized before a second built-in.
5. There is no shared configuration loader (L10). This is convenience, not
   correctness.

**C. Is a contract too provider-specific?** No domain contract is. Two small
precision gaps exist in the error vocabulary (L5) and adapter behavior (L6, L8).
Neither requires a request or result change.

**D. Is `TrustedModelContribution` the right seam?** It is the right seam for
*custom, experimental and test* providers, because it is trusted code. It is the
wrong seam for *configuration-only* switching, because configuration cannot
contain code (ADR-014 §3.6). Keep both: built-in settings types for qualified
protocols, trusted contributions for everything else.

**E. Are credentials, endpoint, timeout, model identity and purposes
represented cleanly?**
- Endpoint, timeout and model identity: yes.
- Purposes: yes for contributions. Built-in Ollama always declares both, and both
  model names are mandatory. A protocol without embeddings needs an optional
  embedding model, with purposes derived from it.
- Credentials: no, by design until ADR-010 is realized.

**F. When can the model switch under ADR-019?** Only when a host is opened.
Selection is captured once, pinned to the configuration revision, and there is
no live reload.

**G. Safety boundaries versus debt:**
- **Intentional (keep):** one pinned binding per host; no runtime routing,
  fallback or retry; closed purposes; contributions are code, never configuration;
  secrets never in configuration; thread and event-loop confinement; remote
  personal-image refusal (ADR-020).
- **Debt (fix in the slices below):** L1, L3 to L8, L10 to L12.
- **Blocked on an accepted decision being implemented:** L2 (ADR-010).

## 6. KISSKI integration modes

KISSKI is treated as two different integrations. Neither needs KISSKI-specific
LegoAI code.

### Mode A — hosted, OpenAI-compatible API

```
ForgeAI -> GovernedHost/ModelPort -> OpenAI-compatible adapter -> KISSKI hosted API
```

| Claim | Status |
| --- | --- |
| A generic OpenAI-compatible adapter needs no KISSKI-specific application code | **Inferred** from the protocol: endpoint, model and credential are configuration |
| KISSKI/SAIA exposes an OpenAI-compatible chat-completions API with API-key authentication | **Unverified operational assumption** (vendor documentation, not checked here) |
| Model catalog, embedding availability, context limits, rate limits | **Unverified** |
| Data-use, retention, logging and training terms for submitted content | **Unverified; blocks real-content use** under SEC-039 until declared |

Prerequisites: the OpenAI-compatible adapter, a governed credential reference and
a declared provider data-use profile.

### Mode B — raw KISSKI GPU or HPC allocation

```
Slurm GPU allocation -> inference server (vLLM or equivalent)
    -> OpenAI-compatible endpoint -> same generic adapter
```

| Claim | Status |
| --- | --- |
| LegoAI sees only an endpoint; the allocation and server lifecycle belong to deployment tooling | **Inferred architecture** (decided here) |
| Long-running inference servers are permitted in an allocation | **Unverified** |
| Compute-node networking: reachable directly, or only through an SSH tunnel via a login node | **Unverified** |
| Container runtime (for example Apptainer), vLLM installability, GPU types, job time limits | **Unverified** |

Consequences:
- The endpoint lives only as long as the job, so it is unsuitable for unattended
  use without operator tooling.
- An SSH tunnel to `localhost` does **not** make the deployment local.
  Deployment location is an operator declaration about where content is
  processed, not about the URL's host. Declaring a tunnelled KISSKI endpoint as
  local would bypass SEC-039 and ADR-020 and is prohibited.
- Server-side authentication (for example a server API key) is still a
  credential and still needs the governed Secret path.
- Mode B could also run Ollama. Today that would be configuration-only (change
  `base_url`), which is exactly why the L3 disclosure gap must close first.

## 7. Local GPU strategy

```
KISSKI H100 -> vLLM -> OpenAI-compatible adapter      (endpoint A)
owned RTX GPU -> vLLM -> SAME adapter                  (endpoint B)
```

Only the binding's endpoint, model name, provider ID, deployment declaration and
credential reference change. Nothing in the current design prevents this once the
adapter exists. Two cautions:
- **The same model name is not the same condition.** Different quantization,
  serving engine, context window or sampling defaults change behavior. Each
  endpoint is a new evaluation condition, and conformance proves the contract,
  not equal quality.
- A local Ollama on an owned GPU already works today by changing `base_url` only.

## 8. Hugging Face strategy

"Hugging Face" is three different things:

| Form | Protocol | Adapter |
| --- | --- | --- |
| HF weights served by vLLM, or by TGI's chat-completions API | OpenAI-compatible | **Reuse** the OpenAI-compatible adapter |
| HF Inference Endpoints or the hosted router that offers chat completions | OpenAI-compatible (vendor claim, unverified here) | **Reuse**, after qualification; it is a remote provider (SEC-039) |
| Native Transformers loaded in-process | Python library, not a network protocol | **Rejected for now.** It would add torch-scale dependencies, put GPU memory management inside the governed process, and break the effect model built around a remote call. Serve the weights with vLLM instead |
| Text-embeddings servers with their own native API | Native or OpenAI-compatible embeddings | Use the OpenAI-compatible embeddings route where offered; a native-API adapter only if a workload needs it |

No `HuggingFaceAdapter` is justified.

## 9. Colab and Kaggle

Classification: **experimental or development compute only. LegoAI does not know
about them.** LegoAI sees an endpoint; deployment tooling knows the notebook.

Limitations an operator must accept:
- **Networking.** Notebook runtimes are not normally reachable, so exposure needs a
  tunnel or relay service, which is another party that receives the traffic.
- **Lifetime.** Sessions are ephemeral and preemptible, so endpoints disappear
  mid-run (UNKNOWN effects).
- **Credentials.** Any tunnel token or server key is a credential needing the
  governed Secret path.
- **Reproducibility.** Hardware, drivers and library versions vary between
  sessions. Evaluation conditions must record them, and results are not
  comparable across sessions without that record.
- **Terms of use** may restrict serving. That is the operator's responsibility.

No production or customer workload should run on them. No LegoAI type,
configuration value or test fixture should name them.

## 10. Model-switching semantics

| Level | Supported today | Recommendation |
| --- | --- | --- |
| A. Configuration time (choose bindings) | Yes | Keep |
| B. Host-open time (select one binding) | Yes (ADR-019, ADR-014) | Keep. This is the primary switching mechanism |
| C. Execution or run level | Yes, by opening a new host per run | Keep; ForgeAI already opens a host per composition |
| D. Per-Agent binding inside one host | No | Deferred generalization (§11) |
| E. Per-call dynamic switching | No | **Rejected.** Task or model data must never choose a provider |

**Decision:** keep "one host per pinned binding". A governed model-binding
registry with runtime selection is rejected: it would reintroduce the runtime
routing ADR-019 excluded, and no workload needs it. Switching is easy because it
is configuration plus reopening, not because routing is dynamic.

## 11. Agent-specific model binding

- **Today:** possible only with several hosts (for example an analysis host and a
  coding host), each pinned to its own binding with its own grants and capacity.
  This works now, with no platform change, but duplicates authority configuration
  in the composition root.
- **The smallest generalization, when needed:** pin **one binding per
  `ModelRequirement` profile** at host open. Selection data would map profiles to
  binding IDs. The existing router already resolves by requirement, so this is
  still configuration-selected, still pinned, and still has no fallback.
- **Its cost:** the Agents must declare distinct profiles. Changing an Agent's
  `ModelRequirement` changes its definition fingerprint, so it is a new Agent
  behavior version and a new evaluation condition.
- **When:** only after a measured ForgeAI need, for example an independent
  Reviewer model justified by SEC-078 separation. It needs an ADR-019 addendum.
  It is not part of the first slices.

Automatic model routing remains out of scope.

## 12. Secret governance

- **Current state.** ADR-010 is Accepted; there is no Core realization (master
  roadmap G03). Model settings have no credential field. Media resolves
  `env:NAME` in an adapter-local resolver that the roadmap explicitly says does
  not meet the gate.
- **Classification: blocker** for any credentialed model provider (KISSKI hosted,
  any API-key endpoint, authenticated vLLM) and for MCP.
- **Recommended minimal realization** (implementation completion of ADR-010,
  local single-operator scope):
  1. A public, technology-neutral `SecretRef` value in the Secret Access section of
     `legoai.governance`: identity, owner scope, purpose and consumer. It holds no
     material, has a redacted representation and is never hashed into
     configuration identity as material.
  2. A resolution Port owned by Secret Access, and one reference realization in
     `legoai.reference.secret` backed by the operator process environment. It is
     qualified only as a local single-operator provider: just-in-time resolution
     per use, no cache, purpose and consumer checked, no enumeration.
  3. Adapters receive material only inside the protected call. It never enters
     requests, results, `ExecutionResult`, evidence, reports, logs or exceptions.
     Authentication failures map to Rejected (NONE).
  4. Tests: wrong purpose, wrong consumer, missing reference and redaction in
     every repr, exception and report.
  5. Generative media later replaces its adapter-local resolver with the same
     realization.
- Secrets never become application or task input. Environment variable names alone
  are not Secret identity (ADR-010 §6).

## 13. Failure and effect semantics

| Condition | OpenAI-compatible HTTP evidence | Mapping (recommended) |
| --- | --- | --- |
| Connection refused, DNS failure | No request sent | Preflight → NONE, potentially retryable (unchanged) |
| Authentication failure | 401/403, complete response | Rejected → NONE, terminal |
| Rate limit | 429, complete response | Rejected → NONE, **potentially retryable** (new refinement; no automatic retry) |
| Provider temporarily unavailable | 503, complete response | Rejected → NONE, **potentially retryable** |
| Other 5xx, gateway errors | 500/502/504, complete response | Rejected → NONE, terminal. The generation may have run, but no usable result exists; content was disclosed either way (§16 for remote) |
| Timeout, reset, truncated body | No reliable response | Uncertain → **UNKNOWN** (unchanged) |
| Cancellation | Caller cancelled after send | Existing Coordinator semantics; the thread-bridged request may continue (L7) |
| Malformed response, wrong shape | Complete 2xx | Rejected → NONE, terminal |
| Partial generation | 2xx with a length finish reason | **Rejected**, never success (closes L6) |
| Context limit | 400 with a context error | Rejected → NONE, terminal |
| Output limit | Operator-configured max output tokens; length finish | As partial generation |
| Unsupported feature | Not requestable: no ModelPort field exists for it | Not applicable |
| Unknown completion state | Any transport loss after send | UNKNOWN; never collapsed to NONE |
| Model identity mismatch | Response names a different model than the binding | Rejected (existing binding check) |

**Is the existing vocabulary sufficient?** Almost. The only addition is a way for
an adapter to say "complete rejection, potentially retryable". The smallest form
is a subclass of `ModelResponseRejectedError`, mapped to POTENTIALLY_RETRYABLE.
Existing catches keep working, and no automatic retry is introduced. Provider SDK
exceptions never escape the adapter; the recommended adapter uses the stdlib, as
Ollama's does, so no SDK is introduced at all.

## 14. Capability negotiation

- **Today:** a binding declares purposes; `model_execution(purpose)` fails with
  `PURPOSE_UNAVAILABLE` before dispatch when the purpose is missing. Structured
  output, tool calling, vision, streaming and multimodal output do not exist in
  ModelPort, so no provider can be asked for them and none appears to support
  them.
- **Correct by construction for now.** A provider is never assumed to support a
  capability because another one does: purposes come from the binding's own
  declaration.
- **Rule for later.** Each new capability (for example a JSON response mode or
  vision input) needs its own decision, an explicit per-binding declaration, a
  failure before dispatch when undeclared, and per-provider qualification.
  ADR-019 already states that broad Port shape is never compatibility evidence.
- **Embedding.** Purposes are derived from configuration. A binding without an
  embedding model is chat-only.

## 15. MCP relationship

**Model provider portability is not MCP.** ModelPort is model inference. MCP
exposes tools, resources and prompts from external servers. Model providers must
not be routed through MCP merely because MCP exists.

They should share:

| Concern | Shared mechanism |
| --- | --- |
| Configuration | Trusted operator configuration, pinned revisions; no import strings |
| Admission | Catalog publication of admitted contributions; advertised schemas never self-admit |
| Governance | Grants, current authorization at dispatch, closed failure categories |
| Secrets | The same ADR-010 realization (§12) |
| Observability | Safe identifiers only; no content, credentials or raw payloads |
| Effects | The same NONE/UNKNOWN/COMPLETED discipline and no automatic retry |

**Ordering:** MCP comes **after** the first OpenAI-compatible slice and the Secret
slice, and only when a named consumer needs it (roadmap G01). The Secret
realization is the shared prerequisite.

## 16. Generative media and Virtual Try-On

The same principle applies:

```
VTO application -> VirtualTryOnPort -> ComfyUI driver -> endpoint -> GPU
```

| | Reuse from the LLM architecture | Keep separate |
| --- | --- | --- |
| Ports | — | `TextToImagePort`, `VirtualTryOnPort`, `JobReconciliationPort` (submit, poll, reconcile and disclosure are not chat) |
| Protocol adapters | The protocol-not-platform rule: ComfyUI legacy and API v2 drivers already are protocol adapters | — |
| Secrets | The ADR-010 realization replaces the adapter-local `env:NAME` resolver | — |
| Deployment and disclosure | The same local/remote declaration and data-use admission concept | Media-specific upload, retention and deletion semantics (ADR-020) |
| Configuration | Shared semantics (endpoint, credential reference, deployment, provider identity) | Workflow approval, digests and model files remain media profile values |

**KISSKI for media:**
- **Text-to-image (no personal images):** permitted today in principle with
  `deployment = "remote"`, bearer auth and allowed origins. Credible
  qualification waits for the Secret realization, because the current resolver
  does not meet G03.
- **Virtual Try-On:** **blocked by ADR-020 §8.** Personal-image transfer to any
  remote deployment is refused until a provider profile verifies upload,
  retention and deletion semantics, an amended or superseding ADR permits it,
  and the operator explicitly opts in. KISSKI removes the hardware blocker, not
  the privacy blocker. A tunnel does not make KISSKI local (§6).
- **CR-1c** becomes more important. It is not needed to reach KISSKI, but the VTO
  portability proof ("same application, configuration-only change, public host")
  requires media to be composed through the public host first.

## 17. Option comparison

| Option | Application independence | Provider/infra replacement | Trust and safety | Cost | Verdict |
| --- | --- | --- | --- | --- | --- |
| **A.** Keep provider support contribution-specific | Yes | Every application writes provider code in its composition root; no reuse or qualification | Each contribution is unqualified operator code | Low now, high repeated | Rejected as the strategy; kept as the custom/test seam |
| **B.** Generic protocol adapters behind existing Ports, selected by typed configuration | Yes | Many endpoints per adapter; configuration-only between qualified protocols | Keeps ADR-014/019 pinning; adds the Secret and disclosure gates | One adapter per protocol plus two prerequisite slices | **Selected** |
| **C.** A universal provider abstraction above ModelPort and media Ports | Yes | Forces chat and job-based media into one shape | New owner, wider blast radius | High; duplicates existing Ports | Rejected: the existing Ports are already the abstraction |
| **D.** MCP as the universal layer | Weakens it: inference becomes a tool call | Indirect | Tool-schema admission semantics applied to inference; new effect ambiguity | High | Rejected (§15) |
| **E.** Platform-specific adapters (KISSKI, Colab, H100…) | Yes | One adapter per platform even when the protocol is identical | Repeats qualification per platform | Highest | Rejected; acceptable only for a genuinely unique protocol |

## 18. Selected architecture

```
Application domain                       (unchanged; imports no provider package)
    -> GovernedHost / ModelPort or media Port   (unchanged public contracts)
        -> protocol adapter              (Ollama | OpenAI-compatible | trusted contribution;
                                          ComfyUI legacy | Comfy API v2 for media)
            -> endpoint                  (base URL + model + provider ID + credential reference
                                          + deployment declaration)
                -> deployment / hardware (operator tooling; recorded as evaluation evidence)
```

Rules:
1. One adapter per genuinely different protocol. Platforms are endpoints.
2. A qualified protocol becomes a closed built-in settings type in
   `legoai.runtime.api`. Switching between qualified protocols, endpoints and
   models is configuration plus reopening the host.
3. Unqualified or custom providers remain `TrustedModelContribution` code.
4. Credentials only as governed Secret references (ADR-010).
5. Remote deployment requires a declared provider data-use profile, refused when
   unknown (SEC-039).
6. One pinned binding per host. Per-profile pinning only by a later addendum.
7. No SDK dependency, DI container, registry, marketplace, plugin DSL, dynamic
   import or runtime routing.

## 19. REUSE / EXTEND / CREATE

| Action | Item |
| --- | --- |
| **REUSE** | ModelPort, ChatRequest/Result, EmbeddingRequest/Result, ModelId, ProviderId, ModelRequirement, ModelBinding, the three adapter exceptions and their effect mapping, GovernedHost, `open_local_host`, `ModelBindingConfig`, `LocalHostConfig`, ADR-019 selection and pinning, Catalog/resolution/dispatch/Coordinator, `TrustedModelContribution`, the stdlib HTTP approach of the Ollama adapter, media Ports and drivers, evaluation `hardware_class` recording |
| **EXTEND** | `ModelBindingConfig.provider` union with one new built-in settings type; Rejected error with a retryable subclass and its recoverability mapping; provider-neutral names for the chat/embedding offer helpers (contract content unchanged); adapters detect length-truncated generations; optional operator max-output-tokens setting; media config uses the Core Secret realization |
| **CREATE** | `OpenAICompatibleSettings` (public value) and its adapter (`legoai.reference`); `SecretRef` plus a resolution Port and a local-environment reference realization (ADR-010 completion); a closed deployment declaration and provider data-use admission check; a provider conformance suite |

## 20. Public and private API consequences

| Item | Visibility |
| --- | --- |
| `OpenAICompatibleSettings` | **Public**, in `legoai.runtime.api`, beside `OllamaSettings` (ADR-014 addendum) |
| The OpenAI-compatible adapter class | **Private reference realization** in `legoai.reference`; applications never import it |
| `SecretRef` and the Secret resolution Port | **Public** in `legoai.governance` (Secret Access section, per ADR-002/ADR-010) |
| The environment-backed Secret realization | **Private reference realization** (`legoai.reference.secret`) |
| Deployment and data-use declaration values | **Public** configuration values in `legoai.runtime.api` |
| Retryable-rejection subclass | **Public** in `legoai.intelligence.model.ports` (adapter-facing) |
| Adapter registration | Not a registry. `runtime.local` gains one more closed `match` arm; `runtime.local` needs no redesign |

Target: **application domain imports no provider package.** Only composition or
configuration code names a settings type. Consumers never import provider-specific
types beyond the public settings values.

## 21. Configuration model

Reuse the existing typed values. Illustrative, not an implemented API:

```python
kisski = OpenAICompatibleSettings(
    base_url="https://<kisski-endpoint>/v1",    # operator value; unverified
    chat_model="<model>",
    embedding_model=None,                         # chat-only binding
    timeout_seconds=600,
    provider_id=ProviderId("kisski-hosted"),
    api_key=SecretRef(...),                       # ADR-010; never material
    deployment=ModelDeployment.REMOTE,            # drives SEC-039 admission
    data_use=ProviderDataUse(...),                # declared terms; unknown refuses
    max_output_tokens=4096,                       # operator bound
)
bindings = (
    ModelBindingConfig("local", ModelRequirement("engineering-reasoning"),
                       OllamaSettings(...)),
    ModelBindingConfig("kisski", ModelRequirement("engineering-reasoning"), kisski),
)
selection = {"revision": "<pinned>", "binding": "kisski"}   # unchanged ADR-019 shape
```

- **Provider profiles versus bindings.** The illustrative `provider_profiles` /
  `model_bindings` split is a file-format convenience. It can be expressed by a
  later strict loader that expands profiles into these settings values, following
  the media package's strict-TOML pattern. A second configuration system or a
  separate public `ProviderProfile` type is not needed now.
- **Field ownership.** Protocol is the settings type; endpoint, model, provider
  identity, credential reference and deployment are fields. Hardware is not a
  field.
- **Not claimed:** "any new provider by configuration only". A new protocol needs
  one adapter plus qualification. After that, applications select it by
  configuration.

## 22. Conformance strategy

### PROVIDER-CONFORMANCE (model)

The same test application (a small governed Chat Agent plus an embedding call)
and unchanged domain code run against:

| Binding | Mode |
| --- | --- |
| A. FixedModel or replay contribution | Offline |
| B. Ollama adapter against mocked HTTP | Offline |
| C. OpenAI-compatible adapter against a local stdlib fake server | Offline |
| D. OpenAI-compatible adapter against a real local endpoint (for example Ollama's own OpenAI-compatible route, or local vLLM) | Operator, live |
| E. KISSKI hosted | Operator, live, credentialed |
| F. KISSKI GPU or owned GPU through vLLM | Operator, live |

Assertions:
- identical public result types and governed `ExecutionResult` shape;
- an AST and import check that the application source imports no provider module
  and is byte-identical across runs;
- only the binding configuration differs;
- the same failure-to-effect matrix (§13), forced through the fake server for
  every row: refused, timeout, reset, 401, 429, 503, 500, malformed, length
  finish, context error, identity mismatch;
- no secret material in any repr, exception, report or log;
- a remote binding without a declared data-use profile is refused before any
  request.

It never asserts equal output quality. Live rows are qualification evidence for
that endpoint only.

### VTO-PORTABILITY (media; design only)

Same VTO application against A. a KISSKI GPU ComfyUI and B. an owned local GPU
ComfyUI. Assertions: application unchanged; same `TryOnRequest` input contract and
same output contract; same consent, disclosure and stripping semantics; only
provider configuration differs; workflow and model files stay in the approved
template and profile. **Precondition:** the ADR-020 amendment for row A, and CR-1c
for the public-host claim.

## 23. Concrete slice sequence

| Slice | Content | Depends on | Credentialed |
| --- | --- | --- | --- |
| **PORTABILITY-0** | This decision | — | No |
| **OPENAI-COMPATIBLE-MODEL-1** | Neutral offer helpers; `OpenAICompatibleSettings` (local deployment only, no credential yet); stdlib adapter for chat and optional embeddings; retryable-rejection subclass; length and identity rejection; max output tokens; offline fake-server tests (conformance rows A–C); optional operator live check against a local OpenAI-compatible endpoint | ADR-014 addendum (maintainer) | No |
| **SECRET-REF-1** | ADR-010 minimal realization (§12); wire `api_key` into the settings; tests for purpose, consumer and redaction | ADR-010 (accepted) | Enables |
| **REMOTE-MODEL-DISCLOSURE-1** | Deployment declaration plus data-use admission for remote bindings, for both Ollama and OpenAI-compatible settings; unknown terms refuse before any request | New ADR or ADR-014 addendum (maintainer) | — |
| **KISSKI-HOSTED-QUAL-1** | Operator live qualification of Mode A with synthetic content: connectivity, the identity check, the auth-failure and rate-limit mapping; no quality claim | The three slices above; verified KISSKI terms | Yes |
| **GPU-ENDPOINT-QUAL-1** | Mode B feasibility (operator-verified Slurm, networking and server facts), then the same adapter against a vLLM endpoint; later the identical run against an owned GPU | KISSKI-HOSTED-QUAL-1 | Yes, if the server is keyed |
| **PROVIDER-CONFORMANCE-1** | Promote §22 into consumer readiness. Offline rows ship with slice 1; live rows accrue | Slice 1 | — |
| **MEDIA-SECRET-1** | Media uses the Core Secret realization | SECRET-REF-1 | — |
| **MEDIA-REMOTE-T2I-QUAL-1** | KISSKI-hosted ComfyUI text-to-image (no personal images) | MEDIA-SECRET-1 | Yes |
| **CR-1c** | Media through the public host | — | — |
| **ADR-020 amendment decision** | Remote personal-image transfer with a verified provider profile and explicit opt-in | Maintainer decision; verified KISSKI retention and deletion facts | — |
| **VTO-3K** | VTO live qualification on KISSKI | CR-1c, ADR-020 amendment | Yes |
| *Later* | Per-profile binding pinning (ADR-019 addendum); strict model-binding file loader; MCP client | Measured need or named consumer | — |

## 24. R4 ordering recommendation

- **R4 is complete,** run locally on `qwen2.5-coder:14b`: decision C, stop rule
  `STOP_PROMPT_MODIFICATION_REASSESS_ANALYST_DESIGN`. Option A ("still run R4
  locally first") is moot.
- **Do not re-express R4 on KISSKI.** A KISSKI run changes provider, protocol,
  serving engine, quantization, hardware and possibly model. That is a different
  condition, not R4. Running the same Analyst there to look for a pass would be a
  model-change experiment after the stop rule. The model comparison already
  showed that scale did not resolve the same failure.
- **Ordering:**
  1. The Analyst design reassessment decision proceeds independently; it is
     design work and needs no compute.
  2. Portability slices proceed in parallel: OPENAI-COMPATIBLE-MODEL-1, then
     SECRET-REF-1, then REMOTE-MODEL-DISCLOSURE-1.
  3. Any later Analyst evaluation on KISSKI is a newly preregistered condition that
     records the environment, under whatever design the reassessment selects.
- No further multi-hour local CPU runs are recommended for the Analyst.

## 25. Risks and limitations

- **Hosted-provider drift.** Hosted models can change behind a stable name. The
  identity check binds the name, not the weights, so evaluation conditions must
  record observed identity and date.
- **Disclosure.** Remote inference sends repository content or personal data
  off-machine. The preventive check (§12, §16) is declaration-based; it does not
  verify a provider's actual practice.
- **Cost and quota.** There are no token budgets. Rejected-after-processing calls
  may still consume quota, and `EffectExtent.NONE` means no usable result, not no
  cost.
- **Cancellation (L7).** Remote calls continue after caller cancellation.
- **Compatibility is partial.** OpenAI-compatible servers differ in field support,
  error bodies and finish reasons. The adapter must parse only the minimal
  common subset and fail closed on anything else.
- **Mode B is unverified** operationally, and job-lifetime endpoints are fragile.
- **The local single-operator Secret realization** is not a vault: no rotation
  detection beyond re-reading at use, no custody guarantees.
- This assessment did not access KISSKI, run models or measure latency.

## 26. ADR implications

No ADR number is allocated here.

| ADR | Disposition | Reason |
| --- | --- | --- |
| **ADR-010** | **Implementation completion** | Accepted; needs the minimal realization in §12 before any credentialed provider or MCP |
| **ADR-014** | **Clarification/addendum** | §3.2 public surface gains `OpenAICompatibleSettings` and the deployment/data-use values; §6 gains the retryable-rejection recoverability refinement. One pinned binding per host is unchanged |
| **ADR-017** | **No change** | Agents keep using `ModelRequirement`; per-Agent models later change Agent definitions, not ADR-017 |
| **ADR-019** | **No change now; addendum later** | Selection, pinning and failure rules suffice for the first slices. Its secret statement is satisfied by SECRET-REF-1. Per-profile pinning (§11) would need an addendum |
| **ADR-020** | **Revision or amendment required** before remote VTO | §8 refuses remote personal-image transfer by decision |
| **New ADR (recommended, unnumbered)** | Remote model-provider disclosure admission | Enforces SEC-039 for model inference, as ADR-020 does for images. The maintainer may instead choose an ADR-014 addendum; allocation needs maintainer approval |

## 27. Status: ADR-014 addendum prepared (2026-10-07)

[ADR-014 §14](../adrs/ADR-014.md) (provider portability addendum) is **prepared
for maintainer decision; not accepted.** If accepted, it authorizes only
OPENAI-COMPATIBLE-MODEL-1: credential-free, `ModelDeployment.LOCAL` only, stdlib
adapter, optional embeddings, `max_output_tokens`, strict identity and truncation
rejection, and `ModelResponseRetryableRejectedError` for complete 429/503 replies.

Precision corrections, recorded in the addendum (§14.1):
- the composition-level identity check against the pinned binding covers chat
  only, not embeddings;
- the Ollama adapter declares its configured model name without reading the
  response's `model` field.

These refine §2 and §13 of this record; the decision itself is unchanged.

## 28. Status: ADR-014 addendum accepted (2026-10-07)

[ADR-014 §14](../adrs/ADR-014.md) (provider portability addendum) was **ACCEPTED**
on 2026-10-07 by explicit maintainer decision, exactly as proposed in §27.
**OPENAI-COMPATIBLE-MODEL-1 is now architecturally authorized** within ADR-014
§14.15: credential-free and `ModelDeployment.LOCAL` only. **No implementation has
happened yet.** SECRET-REF-1 and REMOTE-MODEL-DISCLOSURE-1 remain prerequisites
for any credentialed or remote provider.

## 29. OPENAI-COMPATIBLE-MODEL-1 implementation (2026-10-07)

Implemented under accepted ADR-014 §14; operator local validation pending.
The closed host union adds credential-free `OpenAICompatibleSettings` and the
required LOCAL/REMOTE declaration. REMOTE is refused before admission/construction.
The private stdlib adapter implements versioned-root chat (`stream: false`) and
optional embeddings, strict exact model identity, stop-only chat completion,
operator max_tokens, and the accepted failure matrix. Complete 429/503 replies
use the public retryable-rejection subtype; uncertain transport remains UNKNOWN.
No automatic retry or fallback is performed.

Neutral capability helpers retain both existing IDs and version 1.0.0. Ollama
wire behavior, Agent semantics and TrustedModelContribution remain unchanged.
Offline conformance rows A-C and the 52-phase
`validate_openai_compatible_model_1.py` qualify contracts only, not model quality.
See [composition and consumer details](../docs/model-composition.md).

Supported scope after qualification: credential-free LOCAL OpenAI-compatible
endpoints. Remote, credentials, KISSKI hosted, authenticated vLLM, cloud APIs,
automatic routing, retries and VTO are unsupported. No live provider was invoked.
No ADR was changed. Next planned slice after qualification: SECRET-REF-1,
separately authorized; REMOTE-MODEL-DISCLOSURE-1 remains required for remote use.
