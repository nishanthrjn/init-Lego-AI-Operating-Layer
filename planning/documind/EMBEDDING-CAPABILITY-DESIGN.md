# Embedding Capability — Implementation Design

**Document:** `planning/documind/EMBEDDING-CAPABILITY-DESIGN.md`
**Status:** PROPOSED — IMPLEMENTATION DESIGN (implementation blocked — see §22, §27)
**This is NOT a canonical LegoAI Core specification.** It analyzes DocuMind evidence to propose a **LegoAI Core** capability (not a Document Capability Pack capability — see §7, the central finding of this document), subordinate to and constrained by (but not amending) `intent.md`, `SPEC.md`, `ARCHITECTURE.md`, `CONTRACTS.md`, and the accepted ADRs.
**Parent documents:** [`planning/DOCUMIND-EXTRACTION-ASSESSMENT.md`](../DOCUMIND-EXTRACTION-ASSESSMENT.md), [`planning/documind/CHUNKING-CAPABILITY-DESIGN.md`](CHUNKING-CAPABILITY-DESIGN.md) (Batch 1), [`planning/documind/DOCUMENT-PARSING-CAPABILITY-DESIGN.md`](DOCUMENT-PARSING-CAPABILITY-DESIGN.md) (Batch 2) — both complete, accepted, and untouched by this analysis.

---

## 1. Source evidence

Read directly for this design (not summarized secondhand):

**DocuMind-SK:** `src/DocuMind.Domain/Interfaces/IEmbeddingService.cs`, `src/DocuMind.Core/Services/EmbeddingService.cs`, `src/DocuMind.Api/Program.cs` (Ollama/Kernel wiring), `src/DocuMind.Infrastructure/Persistence/DocuMindDbContext.cs` (vector column).

**DocuMind-AgentFramework:** `src/DocuMind.Domain/Interfaces/IEmbeddingService.cs`, `src/DocuMind.Core/Services/EmbeddingService.cs`, `src/DocuMind.Api/Program.cs`, `src/DocuMind.Infrastructure/Persistence/DocuMindDbContext.cs`.

**LegoAI Core:** `adrs/ADR-002.md` (package structure — read in full for this decision), current `src/legoai/` tree (confirmed: only `kernel/`, `application/`, `governance/`, `reference/` exist; no `capabilities/`, `execution/`, or `intelligence/` package exists anywhere in the repository).

**Live provider evidence:** a local Ollama instance was already running with `nomic-embed-text` already pulled (`embedding_length: 768` per its own `/api/tags` metadata) — exercised read-only via its documented `/api/embed` HTTP endpoint; no model was installed or pulled for this task. See §25.

---

## 2. SK behavior (exact, from source)

`IEmbeddingService.EmbedAsync(string, ct)` / `EmbedChunksAsync(List<DocumentChunk>, ct)`. Implementation wraps `Microsoft.SemanticKernel.Embeddings.ITextEmbeddingGenerationService`, wired in `Program.cs` via SK's `AddOllamaTextEmbeddingGeneration(ollamaEmbedModel, new Uri(ollamaEndpoint))` — an SK-specific extension method, but its underlying transport is SK's own Ollama connector talking the same Ollama HTTP API characterized in §25. Config: `Ollama:Endpoint` (default `http://localhost:11434`), `Ollama:EmbeddingModel` (default `nomic-embed-text`) — both externalized, not hardcoded in business logic. `EmbedChunksAsync` batches chunks in groups of `const int batchSize = 5` (a bare code literal, not configuration-bound). Each call (single or batch) wraps a **fresh** `CancellationTokenSource(TimeSpan.FromMinutes(10))` — the caller-supplied `ct` parameter is **never linked to this new token source and is otherwise unused** inside the method body. No validation of input (empty string/list), no validation of the returned embedding count or dimension, no NaN/Infinity check — `embeddings[j].ToArray()` is indexed positionally with zero defensive checking.

## 3. Microsoft.Extensions.AI / MAF behavior (exact, from source)

**Confirmed: Microsoft Agent Framework is not materially involved in embedding at all.** The only import in `DocuMind-AgentFramework`'s `EmbeddingService.cs` beyond `DocuMind.Domain`/`.Entities` is `using Microsoft.Extensions.AI;` — no `Microsoft.Agents.AI` namespace, no `AIAgent`, no agent construct of any kind appears anywhere in this file. The interface (`IEmbeddingGenerator<string, Embedding<float>>`) and result type (`Embedding<float>`) are both part of `Microsoft.Extensions.AI`, a vendor-neutral, Microsoft-published abstraction package usable with or without any agent framework — this is the same conclusion the parent assessment already reached in general terms, now confirmed with direct, line-by-line source reading rather than inference. `Program.cs` registers the concrete implementation as `new OllamaApiClient(new Uri(ollamaEndpoint), ollamaEmbedModel)` — `OllamaApiClient` is from the third-party `OllamaSharp` package (a .NET Ollama client implementing `Microsoft.Extensions.AI`'s interfaces), not any Microsoft Agent Framework type. The algorithm itself (`EmbedAsync`/`EmbedChunksAsync`, batch size 5, per-call 10-minute `CancellationTokenSource` ignoring the passed `ct`) is **line-for-line structurally identical** to SK's, substituting `GenerateAsync`/`.Vector` for `GenerateEmbeddingAsync`/`.ToArray()`-on-the-`Embedding` object.

**Correction to the parent assessment's classification:** embedding in the MAF repository should be classified as a `GENERIC_DOTNET_UTILITY` (`Microsoft.Extensions.AI` binding) exactly as the assessment's extraction matrix already stated — this document confirms that classification directly from source rather than by inference, and explicitly rules out any `MAF_ADAPTER` framing for embedding specifically (a fabricated `MAFEmbeddingAdapter` would misrepresent what is actually a plain `Microsoft.Extensions.AI` + `OllamaSharp` binding).

---

## 4. Semantic commonality

Both implementations reduce to exactly the same three-step shape, independent of which .NET abstraction wraps it:

```text
text or ordered batch of text
        ↓
call a configured embedding model via an HTTP-based local Ollama instance
        ↓
ordered float-vector result(s), one per input, same dimension
```

Every difference between the two repositories (`ITextEmbeddingGenerationService` vs. `IEmbeddingGenerator<string, Embedding<float>>`, `.ToArray()` vs. `.Vector.ToArray()`) is a **framework-shape** difference, not a **semantic** one — the model, endpoint, batch size, timeout value, and lack of validation are all identical.

## 5. Framework differences (and why they don't matter here)

| Aspect | SK | Microsoft.Extensions.AI (MAF repo) |
|---|---|---|
| Interface | `ITextEmbeddingGenerationService` (SK-specific) | `IEmbeddingGenerator<string, Embedding<float>>` (vendor-neutral) |
| Concrete binding | SK's own Ollama connector (`AddOllamaTextEmbeddingGeneration`) | `OllamaSharp.OllamaApiClient` |
| Result shape | `IList<ReadOnlyMemory<float>>`-like, `.ToArray()` | `GeneratedEmbeddings<Embedding<float>>`, `.Vector.ToArray()` |
| Batch call | `GenerateEmbeddingsAsync(List<string>)` | `GenerateAsync(List<string>)` |

Neither difference changes the wire protocol actually spoken to the provider (both ultimately call Ollama's HTTP embedding endpoint), the model used, the batch size, the timeout, or the complete absence of response validation. A LegoAI capability contract modeled on either framework's specific interface would import an accidental, provider-connector-shaped constraint that the actual semantic capability does not require — exactly the framework-leakage risk the parent assessment's risk table already anticipated in general terms.

---

## 6. Capability identity

**`model.embedding`** — matching intent.md's own example vocabulary (intent §7 lists `model.embedding` explicitly as a representative capability identity) and SPEC's `ModelCapability` concept (§4.5: "a Capability specialization for model behavior, such as interpreting a modality or producing constrained output"). No alternative name was seriously considered: this is not a new concept requiring naming-space evaluation the way `document.chunking`/`document.parsing` were — it is naming a capability intent.md itself already anticipated by name.

---

## 7. Core vs. Document Pack placement — the central finding of this document

**This is a fundamentally different placement question than Batch 1/2 faced, and it resolves the opposite way.**

Chunking and Parsing were correctly placed in `legoai_document` because neither is a canonical SPEC concept — SPEC's concept catalog (§4) has no `Chunk` or `Document` entry, and ADR-002 §13 explicitly provides a "future integration distribution" mechanism precisely for capabilities that are not canonical Core owners.

**Embedding is different: `Model` and `ModelCapability` are themselves canonical SPEC concepts (§4.5), and ADR-002 already allocates a specific, named future location for exactly this capability:**

> `legoai.intelligence.model` | Model Interaction descriptors, validation/usage, Model Port | I row | Agent/Workflow, Evaluation, SDK implementation | Public values/Ports; future independent Model slice (ADR-002 §7.3)

and separately, ADR-002 §15 ("Future independent and composed slices — Model without Agent") states:

> `legoai.intelligence.model.ports` imports its own values, Kernel and only needed I-permitted leaf values. The `intelligence` parent imports neither `model` nor `skill` eagerly. A Model Adapter imports that Port; an outer permitted consumer obtains governed Execution attribution and invokes it.

This confirms, from the canonical package-structure ADR itself, that embedding's correct architectural home is **inside `legoai.*` (Core), at `legoai.intelligence.model`**, realized through a Model Port with Adapters (an Ollama Adapter being the first candidate) beneath it — not a first-party optional distribution alongside `legoai_document`. Placing `EmbeddingCapability` in `legoai_document` merely because DocuMind happens to be the evidence source would misrepresent a cross-application Core capability as a document-specific one — exactly the mistake this task instructed against, and directly supported by ADR-002's own text, not merely general reasoning: embeddings are evidenced by DocuMind here but are equally applicable to images, recommendations, code search, memory, and multimodal applications the same way `ModelCapability` is written to be modality-neutral in SPEC.

**The consequence of this correct placement is that implementation is currently blocked** — see §22 and §27. `legoai.intelligence.model` is a listed but not-yet-created package: ADR-002 §5's 12 initial groups (`kernel`, `application`, `capabilities`, `execution`, `tools`, `governance`, `resources`, `plugins`, `observability`, `evidence`, `runtime`, `reference`) do not include `intelligence`, and the current repository (confirmed by direct directory listing) has created only `kernel/`, `application/`, `governance/`, and `reference/` so far — not even `capabilities/` or `execution/`, both of which are among the 12 *initial* groups and are themselves prerequisites `legoai.intelligence.model` would need (per ADR-002 §9's dependency matrix, Intelligence depends on Kernel and its own C-row/I-row permitted values, which in turn presumes the Capability Catalog machinery exists).

---

## 8. Request/result model

Three distinct types, matching the same discipline Batch 1/2 established:

```text
EmbeddingRequest / EmbeddingResult   (this capability's pure semantic request/result)
        ≠
ModelIdentity / ProviderIdentity / dimension provenance   (§10 — belongs to the result, but as
                                                             declared facts, not business metadata)
        ≠
persisted vector column (pgvector) / retrieval index entry / chunk association   (a consumer's
                                                             concern entirely — §18)
```

No `document_id`, `chunk_id`, `tenant_id`, `timestamp`, or persistence key belongs on the request or result — mirroring exactly why `ChunkingRequest`/`ParsedPage` excluded analogous fields in Batch 1/2.

## 9. Single/batch semantics

**Decision: one canonical operation, over an ordered collection, with no separate single-item entry point.**

Both DocuMind implementations expose separate `EmbedAsync(text)` and `EmbedChunksAsync(list)` methods only because their underlying SDK interfaces (`ITextEmbeddingGenerationService`/`IEmbeddingGenerator<>`) happen to expose both a scalar and list overload — this is a **provider-SDK-shape artifact**, not evidence of two distinct semantic operations. Live verification (§25) confirms Ollama's own `/api/embed` endpoint already treats scalar and array input uniformly at the HTTP level (a single string is accepted, but the response is always the same `embeddings: [...]` list shape) with one important, evidenced exception: a **scalar** `""` empty-string request returns zero embeddings, while the **same** empty string inside an array returns one embedding, alongside any other non-empty siblings, correctly. This is direct evidence *against* exposing a scalar/singular request shape at all: a single canonical request over `tuple[str, ...]` (even for a single string, `("only one",)`) avoids this provider-level scalar/array asymmetry entirely, by construction, rather than needing to special-case it. `EmbeddingRequest(inputs: tuple[str, ...])` is therefore both simpler *and* safer than mirroring DocuMind's two-method shape.

## 10. Dimensionality — must not be hardcoded

**Confirmed defect, live-verified:** both DocuMind persistence schemas hardcode `vector(768)` as a literal Postgres column type (`DocuMindDbContext.cs`, both repos), matching `nomic-embed-text`'s actual dimension (confirmed via `/api/tags`: `"embedding_length": 768`) — but nothing in either `EmbeddingService` validates that the *actual* returned vector's length is 768, or reacts if `Ollama:EmbeddingModel` were reconfigured to a different-dimension model. A model swap would only surface as a Postgres-level dimension-mismatch error at the *persistence* layer, several steps removed from the actual cause.

**Decision: dimensionality is an observed, validated property of the *result*, never a constant baked into the capability contract.** `EmbeddingResult` carries a `dimension: int` field, and the capability's implementation MUST validate that every returned vector has exactly that length (§17/§18) before returning successfully — raising a validation-category failure otherwise, rather than letting a downstream, unrelated system (a vector-store schema) be the first place a dimension mismatch becomes visible. `768` never appears as a literal anywhere in the capability's own contract; it is a fact about the currently-configured model, discoverable at runtime, not a universal constant.

## 11. Model/provider provenance

Per this task's explicit instruction, and consistent with SPEC S-12 (material facts must be traceable) and SPEC §4.5 (Model output is untrusted, but its identity/version must be attributable): `EmbeddingResult` (or its governing `CapabilityResolution`/`Execution`, once those exist — see §22) must make the following facts available to a caller wishing to record provenance:

- **model identity** (e.g., `"nomic-embed-text"`) — a declared fact about which model produced the vectors, not inferred after the fact;
- **provider identity** (e.g., an Ollama Adapter instance/endpoint identity) — distinct from model identity, since the same model name could in principle be served by different providers;
- **embedding dimension** (§10) — observed from the actual response, not assumed;
- **capability version** — which `CapabilityVersion` of `model.embedding` was invoked (relevant once versioning per §31 actually matters).

**Explicitly not included on the pure `EmbeddingResult` itself:** timestamps, tenant identity, business document IDs — these belong to the surrounding `ExecutionContext`/`Execution` envelope (SPEC §4.6), exactly as Batch 1/2 kept correlation/persistence facts out of their pure results. The distinction the task draws (embedding semantic result vs. execution/provenance envelope) is the same request/result-vs-entity separation already established twice; provenance fields that genuinely describe *what produced this result* (model/provider/dimension/version) belong on the result because they are facts about the computation itself, not caller-side bookkeeping — this is a narrower, deliberate exception to the "keep the result minimal" rule, not a reopening of it.

## 12. Provider protocol options

Live-verified (§25) against Ollama's own current documentation and a running instance:

| Option | Assessment |
|---|---|
| **Direct HTTP against `/api/embed`** | Ollama's own documentation states: *"New integrations should use the `/api/embed` endpoint for its batching support and improved feature set."* Confirmed live: accepts `{"model": ..., "input": [...]}`, returns `{"model": ..., "embeddings": [[...], ...], total_duration, load_duration, prompt_eval_count}` — the latter three fields are directly useful resource/latency accounting data (§24) that neither DocuMind implementation currently captures at all. |
| Legacy `/api/embeddings` (singular) | Documented as superseded by `/api/embed`; not evaluated further given Ollama's own stated preference. |
| Official `ollama` Python package | Wraps the same HTTP API (`ollama.embed(model=..., input=[...])`); adds a dependency whose own internal HTTP client choice and versioning this project would not control, for no capability the raw HTTP protocol doesn't already provide directly. |
| OpenAI-compatible `/v1/embeddings` route | Ollama also exposes this for OpenAI-SDK compatibility; rejected as the *primary* protocol choice because it is a compatibility shim layered on top of Ollama's native API, not Ollama's own preferred/most-capable interface (per Ollama's own documentation guidance above) — using it would mean paying an unnecessary translation layer to reach the same underlying capability. |

**Recommendation: direct HTTP against the native `/api/embed` endpoint**, from inside an Ollama-specific Adapter — not through any additional SDK. This mirrors Batch 2's `pypdf` decision process (evaluate the smallest dependency that satisfies the verified contract) but concludes differently here: **no new dependency is even needed for the *protocol* choice itself** — only an HTTP client capable of the request. The exact HTTP client library (a stdlib-only synchronous client vs. a minimal async-capable dependency consistent with ADR-015's asyncio-based Execution supervision model) is deliberately **not selected here** — it is an implementation-batch decision, exactly as `pypdf`'s exact version was only pinned once Parsing was actually authorized, not during its design gate.

## 13. Configuration

Provider configuration (endpoint, model identity, timeout, batch size) is **Adapter/Provider configuration, not part of the semantic `EmbeddingRequest`/`EmbeddingResult` contract** — consistent with §9's principle and with SPEC's Provider/CapabilityProvider distinction (SPEC §4.4: "advertising versioned offers and operational conditions"). DocuMind's own `Ollama:Endpoint`/`Ollama:EmbeddingModel` externalization (already configuration-bound, not hardcoded in business logic) is good evidence this separation is already halfway achieved in the oracle — LegoAI's design simply formalizes it as a canonical boundary (Capability contract vs. Provider configuration) rather than an incidental `appsettings.json` convention.

## 14. Secrets

**`EmbeddingRequest` MUST NOT carry an API-key/secret field.** Live evidence: a local Ollama instance requires no authentication at all for `/api/embed` — the current DocuMind evidence base has zero secret-bearing embedding calls. A future remote/hosted embedding provider (were one ever added) would resolve any required credential through LegoAI's own accepted Secret architecture (SPEC §4.9 `Secret`, referenced by the governing Provider/Adapter, never embedded in the semantic request) — this capability's semantics must not assume a secret exists, and must not invent a generic credential field "just in case."

## 15. Timeout behavior

**Characterized exactly, live-confirmed as an implementation detail, not adopted as canonical semantics:** both DocuMind implementations wrap **every single call** (whether embedding one string or one batch of five) in a **fresh** `CancellationTokenSource(TimeSpan.FromMinutes(10))`, and — critically — **never link the caller-supplied `ct` parameter to it at all**. This means: (a) the 10-minute figure is a per-call ceiling, not a per-batch-run or whole-ingestion ceiling; (b) it is applied identically regardless of whether the underlying content is one short chunk or the largest chunk in the batch, suggesting it was chosen as a generous, un-tuned upper bound ("large PDFs take longer to embed on CPU," per the adjacent `Program.cs` comment) rather than a deliberately measured value; and (c) a caller's own cancellation request is **silently ignored** — a confirmed defect, not a design choice, since the parameter exists in the signature but is dead on arrival. **Decision: 10 minutes is not adopted as any kind of LegoAI default.** Timeout is Provider/Adapter configuration (§13), and the capability's own execution boundary (once Execution exists — §22) is what should honor a caller's cancellation request, correctly this time.

## 16. Batch-size behavior

**Confirmed via source, both repos: `const int batchSize = 5;` is a bare literal inside `EmbeddingService`, not read from configuration, not documented as provider-required, and not present anywhere in `appsettings`.** Nothing in Ollama's `/api/embed` documentation imposes a batch-size ceiling of 5 — the live-verified request in §25 successfully embedded a batch of 3 in one call with no indication a larger batch would fail; Ollama's documentation describes `/api/embed`'s batching support as a *feature*, not a constrained one. **Decision: batch size is Provider/Adapter tuning, not a `CapabilityVersion` property.** `EmbeddingRequest` carries no batch-size field at all — if a future Adapter implementation needs to chunk a very large `inputs` tuple into smaller provider calls for its own operational reasons (memory, provider-specific limits), that chunking is entirely an Adapter-internal concern, invisible to the capability's public contract, and must preserve exact input-to-output ordering across any internal chunking it performs (§9's ordering guarantee is a *capability*-level promise, regardless of how many provider calls the Adapter uses to fulfill it).

## 17. Failure/exception model (conceptual — canonical mapping, not implemented)

Per this task's explicit instruction, and consistent with the current state of `src/legoai/kernel/errors.py` (only 5 of SPEC's 16 canonical error categories are implemented so far, confirmed unchanged since Batch 1's own reading of this file), **no new Core error machinery is added or forced into completion by this design.** Failure modes are characterized and conceptually mapped, for a *future* implementation to realize once the canonical error surface and the `model.embedding` Port both exist:

| Failure | Live/source evidence | Conceptual SPEC category |
|---|---|---|
| Connection refused (provider unreachable) | Not exercised live (would require stopping the running Ollama instance, which this task's "do not change system state materially" instruction counsels against); characterized from HTTP semantics — a connection failure at the transport layer | `DependencyFailure` |
| Model missing | **Live-verified** (§25): HTTP 404, body `{"error": "model \"...\" not found, try pulling it first"}` | `CapabilityUnavailable` (the specific offer is not currently servable) or `DependencyFailure`, depending on framing at the governed boundary |
| HTTP timeout | Characterized from DocuMind's own (defective) 10-minute `CancellationTokenSource` pattern (§15); not independently reproduced live | `DeadlineExceeded` |
| HTTP 4xx (other than model-missing) | Not exercised live beyond the 404 case above; Ollama's error body shape (`{"error": "..."}`) is consistent across its documented error responses | `ValidationError` (a malformed request) |
| HTTP 5xx | Not exercised live (would require inducing a server-side failure) | `DependencyFailure` |
| Malformed JSON / missing `embeddings` field | Not observed live (the real endpoint always returned well-formed JSON in every case tried); must still be defensively checked, since "the SDK/HTTP call succeeded" is not the same as "the response is well-formed" (this task's own instruction: "do not treat provider output as trusted solely because the SDK returned successfully") | `DependencyFailure` (a contract violation by the provider) |
| Wrong result count | **Confirmed possible in principle** by the scalar-empty-string anomaly (§9, §25) — a provider can return fewer entries than requested under some input shapes | `DependencyFailure`, detected by the capability's own mandatory count-check (§18) |
| Wrong dimension | Not observed live (every call in this session returned uniformly 768-dimensional vectors, consistent with one fixed model); must still be defensively checked (§10, §18) | `DependencyFailure` |
| NaN/Infinity in a vector | Not observed live | `DependencyFailure`, detected by the capability's own mandatory numeric validation (§18) |

**Recommendation for a future implementation:** a small number of shallow, pack/Core-local exceptions (mirroring Batch 1/2's discipline — e.g., an `EmbeddingProviderError` for transport/dependency failures and an `EmbeddingValidationError` for contract violations detected by the capability's own response validation), each mappable at a future governed Execution boundary to the categories above — not implemented in this design-only batch, and not forced into `legoai.kernel.errors` prematurely.

## 18. Response validation (mandatory, regardless of which provider is behind the Adapter)

Per this task's explicit instruction and directly justified by live evidence (§9, §25 — the scalar-empty-string count anomaly is not hypothetical, it was observed), a conformant implementation MUST validate, before returning success:

- `len(result_vectors) == len(request.inputs)` — **mandatory**, given live-confirmed evidence that at least one provider request shape can violate this;
- every vector has length `== dimension` (a single, uniform, observed dimension across the whole result) — **mandatory** (§10);
- `dimension > 0` — **mandatory**;
- every element is a finite real number (no `NaN`, no `Infinity`) — **mandatory**, defensively, even though not observed live, per the instruction not to trust a successful SDK/HTTP call as sufficient proof of a well-formed payload.

None of these checks were present in either DocuMind implementation — this is a **deliberate improvement** over the oracle, directly motivated by the live-verified evidence that the provider's own count-preservation guarantee is not absolute across every input shape.

## 19. Determinism

**Live-verified (§25):** two identical input strings within the same batch call produced byte-identical vectors. This supports a **qualified** determinism guarantee, not an unconditional one: *"for a fixed model identity, provider, and configuration, identical input text is expected to produce identical (or, across model/runtime upgrades, at least embedding-space-compatible) output vectors — not a permanent, universal bit-for-bit guarantee across all time, since the provider or model version is free to change independently of the capability contract."* This mirrors Chunking's own determinism section's spirit (a capability-level guarantee scoped to what evidence actually supports) rather than promising more than a model-serving stack can honestly commit to. Model/provider identity provenance (§11) is what makes this qualification meaningful and checkable by a caller — without recording *which* model/version produced a given vector, "determinism" would be an unverifiable claim.

## 20. Persistence/retrieval boundary

`EmbeddingCapability` produces vectors only. It must not depend on Postgres, pgvector, EF Core, retrieval logic, or `DocumentChunk`/any document-specific entity — exactly the reasoning already applied to keep Chunking and Parsing free of persistence concerns, now stated for a capability whose evidence source happens to be even more tightly coupled to persistence in the oracle (both DocuMind `EmbeddingService.EmbedChunksAsync` methods take and mutate `List<DocumentChunk>` directly, reaching directly into a domain-entity list). The LegoAI capability's request/result types (§8) contain no chunk, document, or storage concept at all — a caller (a future `IngestionWorkflow`, or any other consumer — clustering, recommendations, memory, deduplication) is responsible for taking `EmbeddingResult.vectors` and pairing them with whatever it is embedding, then persisting that pairing however it chooses. This is precisely why placing this capability in Core (§7) rather than `legoai_document` matters in practice, not merely in principle: a `legoai_document`-scoped design would make it easy to accidentally reach for a document-shaped result even when the actual computation has nothing document-specific about it.

## 21. Retrieval boundary

`EmbeddingCapability ≠ RetrieverCapability`, maintained explicitly: embedding produces vectors from text; retrieval performs query/storage/ranking semantics over already-embedded content (tracked separately in the parent assessment, still unimplemented). Neither should import the other — a future `RetrieverCapability` would *consume* `model.embedding` (to embed a query) as one of its own dependencies, exactly as SPEC's Retriever entry already implies ("MUST NOT require... generation," §4.7) without embedding importing anything about retrieval in the other direction.

---

## 22. Implementation placement — the blocker

Per ADR-002's own package map (§7), the canonical location for this capability's Port/values is:

```text
legoai.intelligence.model.values     (public, owner-defined records)
legoai.intelligence.model.ports      (public Port protocol + operation request/result definitions)
legoai.reference.model (or similar)  (first-party Ollama-backed reference realization, per ADR-002 §7.2's
                                       reference-realization pattern — an exact analogous slot to
                                       legoai.reference.execution/legoai.reference.tools etc.)
```

**None of these exist.** Confirmed directly (not inferred): `src/legoai/` currently contains only `kernel/`, `application/`, `governance/`, `reference/` (the last holding only the ADR-003 configuration-composition fixture from Gate 1/F2 — no `reference.model` submodule). `intelligence` is not among ADR-002 §5's 12 *initial* groups; it is explicitly a **§7.3 "reserved future logical location"** — meaning ADR-002 itself already anticipated this package would be created later, gated on "future independent Model slice" being an authorized unit of work, not something to scaffold opportunistically while implementing one capability.

**This differs materially from Batch 1/2's situation.** Chunking and Parsing found a *legal, already-authorized* escape hatch (ADR-002 §13's "future integration distribution" mechanism) precisely because they are *not* canonical Core concepts — nothing in ADR-002 needed to be created first. Embedding *is* a canonical Core concept whose home ADR-002 has already named but not yet built. There is no equivalent escape hatch for a canonical Core capability: building `legoai.intelligence.model` merely to unblock this one capability would be "building the runtime prematurely" — exactly what this task's §28 instructs against — because `legoai.intelligence.model`'s own dependency matrix (ADR-002 §9) presumes `legoai.capabilities` (Capability Catalog/Resolution) and plausibly `legoai.execution` (for governed invocation attribution) are meaningful, and neither of those exists yet either.

**What this means concretely:** this design can be fully specified (as this document does), but a legally-placed, ADR-002-conformant implementation cannot begin until a deliberate, separately-authorized decision creates at least a minimal `legoai.intelligence.model` values/ports slice — which is itself a Core milestone independent of DocuMind extraction work, not something this extraction program should trigger as a side effect of wanting to port one more capability.

---

## 23. Test strategy (designed now, to be run once implementation is authorized)

Three clearly separated tiers, per instruction:

- **Pure contract tests** (no network, no provider): construction/validation of `EmbeddingRequest`/`EmbeddingResult` value types; the count/dimension/finite-number invariants (§18) exercised against a small deterministic **test double** (§24) that returns known, fixed vectors for known strings — covering single input, batch input, ordering preservation, duplicate-input handling, empty batch (`inputs=()`  → `EmbeddingResult(vectors=(), dimension=0 or undefined — to be decided at implementation time)`), Unicode input, and the count-mismatch/dimension-mismatch/NaN/Infinity validation-failure paths (all constructible without any real provider, by having the fake return deliberately wrong shapes on demand).
- **Provider Adapter tests** (network to a local Ollama instance, environment-gated/skippable): the actual Ollama HTTP Adapter exercised against a real endpoint — single string, batch, Unicode, the live-confirmed scalar-empty-string anomaly (§9), missing-model 404 handling, and (if feasible without inducing real infrastructure failure) a deliberately-wrong endpoint to characterize connection-refused behavior. Skipped automatically when no local Ollama instance is reachable, exactly as this task's own live-verification step had to tolerate "unavailable" as a valid outcome rather than fabricating results.
- **Live integration tests**: explicitly optional/opt-in only, not part of ordinary CI, given they depend on an external, stateful local service being present with a specific model already pulled.

## 24. Versioning

| Candidate change | New `CapabilityVersion`? | Reasoning |
|---|---|---|
| Scalar → batch request semantics | N/A — v1 is batch-shaped from the start (§9), never scalar | — |
| Output-order change | **Yes — major.** | Ordering is an explicit guarantee (§9); changing it breaks every existing caller's positional pairing |
| Dimension-semantics change (e.g., allowing variable per-vector dimension within one result) | **Yes — major.** | Contradicts §10/§18's uniform-dimension validation, a stated guarantee |
| Model identity becoming implicit (not recorded in the result) | **Yes — major, and should simply not happen.** | Directly regresses §11's provenance requirement |
| Allowing multimodal inputs (image/audio embeddings via the same request type) | **New capability, not a version bump** — see §26 | `model.embedding` as scoped here is text-only; multimodal input would change the request's fundamental shape, not merely its guarantees |
| Vector normalization (e.g., always L2-normalizing output) | **Yes — version-relevant**, and must be an explicit, declared property of the `CapabilityVersion`, not silently inherited from a specific provider's default (Ollama's `/api/embed` is documented to return L2-normalized vectors already — §25 — but this is a *provider* fact, not a *capability* guarantee, unless and until the capability contract explicitly adopts it) | |
| Numeric representation change (e.g., float32 → float64, or a quantized/int8 representation) | **Yes — major.** | Changes the meaning of every downstream consumer's stored/compared vectors |
| Failure-semantics change (e.g., what previously raised now degrades) | **Yes**, per the same rule Batch 1/2 already established | Consistent with SPEC V-03 |

## 25. Live verification evidence

A local Ollama instance was found already running, with `nomic-embed-text` already pulled — no model was installed or pulled for this task; all calls below are read-only characterization against pre-existing local state.

| Case | Result |
|---|---|
| Single string, scalar `input` | HTTP 200; `embeddings` is a **list containing one vector** (768-dim) — the API's response shape is uniformly list-based regardless of scalar/array request input |
| Batch of 3 strings | HTTP 200; `embeddings` has exactly 3 entries, each 768-dim, in input order; response also includes `model`, `total_duration`, `load_duration`, `prompt_eval_count` — directly useful, currently-uncaptured resource/latency accounting data (§17 table, future `EmbeddingResult` provenance candidate beyond the minimum in §11) |
| **Scalar `input: ""`** (empty string, alone) | HTTP 200; **`embeddings: []`** — zero results for one requested input. **This is the count-mismatch defect class** motivating §18's mandatory validation |
| Scalar `input: "   "` (whitespace-only) | HTTP 200; **one** 768-dim vector returned — whitespace-only is embedded normally, unlike empty string |
| Array `input: []` (empty batch) | HTTP 200; `embeddings: []` — sensible, symmetric empty-in/empty-out |
| Array `input: ["first", "", "third"]` (empty string *inside* a non-empty batch) | HTTP 200; **3** embeddings returned, one per input including the empty string — the anomaly is specific to a *wholly* empty scalar/array request, not to an empty string merely present alongside others |
| Array `input: ["", ""]` (array of only empty strings) | HTTP 200; **2** embeddings returned (both real, non-zero, identical to each other) — confirms the anomaly is specific to the **scalar** wire form, not to empty strings generally; directly justifies §9's "always use array form, even for one input" decision |
| Unicode string (`café 日本語 😀`) | HTTP 200; one 768-dim vector, no error |
| Duplicate strings within one batch | HTTP 200; **byte-identical** vectors for the two identical inputs — supports §19's qualified determinism claim |
| Nonexistent model name | **HTTP 404**, body `{"error": "model \"this-model-does-not-exist\" not found, try pulling it first"}` — a clean, structured, machine-readable error shape |
| Actual model dimension | Confirmed via `/api/tags`: `nomic-embed-text` reports `"embedding_length": 768"` directly in its own metadata — matching DocuMind's hardcoded `vector(768)`, but demonstrating the dimension is *discoverable from the provider itself*, not something that needs to be hardcoded anywhere |

**Not exercised live** (per instruction, to avoid fabricating results or destabilizing the running instance): connection-refused/provider-down, malformed-JSON response, wrong-dimension response, NaN/Infinity in a real response, and a deliberately-oversized batch — none of these are safely inducible against a real, otherwise-healthy local Ollama instance without either stopping it or crafting adversarial input the live service cannot organically produce; each remains a defensively-coded, evidence-motivated check (§18) rather than a live-observed case.

---

## 26. Unresolved questions

- Exact HTTP client library for the eventual Adapter (§12) — deliberately deferred to the implementation batch, exactly as `pypdf`'s version was.
- Whether `EmbeddingResult` should declare vector normalization as part of its contract, given Ollama's `/api/embed` already returns L2-normalized vectors by default (§25) — deferred until a second provider's behavior is evidenced, to avoid encoding one provider's default as if it were universal (mirrors the same discipline that kept `document.ocr` undesigned in Batch 2 pending a second realization).
- What `EmbeddingResult` should contain for a genuinely empty `inputs` tuple (`vectors=()`, and `dimension` = 0, `None`, or omitted?) — a small, concrete decision better made once the implementation batch can check it against the same care Batch 1 applied to its own empty-input case, not invented here.
- Exact minimal shape of `legoai.intelligence.model`'s first slice (§22) — this is the actual blocking decision, and is explicitly out of scope for this document to resolve, since resolving it requires a separate, dedicated Core-architecture decision, not a DocuMind-extraction design document.

## 27. Implementation gate

```text
READY_TO_IMPLEMENT_EMBEDDING = NO
```

**This is a legitimate, evidence-grounded outcome, not an incomplete analysis** — every semantic, contractual, and behavioral question this task asked has been resolved (see the section-by-section decisions above); the blocker is architectural placement, not design uncertainty.

**Blockers (all trace to one root cause):**

1. **`legoai.intelligence.model` (the canonical Core location for this capability's Port/values, per ADR-002 §7.3/§15) does not exist.** Neither do its prerequisite initial-group packages `legoai.capabilities` or `legoai.execution` (confirmed by direct directory listing: only `kernel/`, `application/`, `governance/`, `reference/` exist today).
2. **No ADR-002-consistent escape hatch applies**, unlike Batch 1/2: `Model`/`ModelCapability` are canonical SPEC concepts (§4.5), so the "future integration distribution" mechanism (ADR-002 §13) that legitimately homed `document.chunking`/`document.parsing` outside `legoai.*` does not apply here — this capability's contract genuinely belongs inside Core.
3. **Creating `legoai.intelligence.model` now, solely to unblock this one capability, would be building Core runtime prematurely** (this task's own §28 instruction), since that package's own dependency matrix presumes Capability Catalog and (for governed invocation attribution) Execution machinery that do not exist yet either — a minimal `legoai.intelligence.model` slice is itself a deliberate, separately-scoped Core milestone, not a byproduct of DocuMind extraction.

**Already resolved (not blockers — this design is otherwise complete):**

- Capability identity (§6), Core-vs-Document-Pack placement rationale (§7), request/result contract (§8-9), dimensionality semantics (§10), model/provider provenance (§11), provider protocol recommendation (§12), configuration/secrets boundaries (§13-14), timeout/batch-size classification as Provider-not-Capability concerns (§15-16), conceptual exception mapping (§17), mandatory response-validation rules directly motivated by live-observed evidence (§18), qualified determinism guarantee (§19), persistence/retrieval boundary (§20-21), test strategy (§23), versioning triggers (§24).
- No canonical LegoAI document was found to contradict anything in this design; no ADR required reopening; this document proposes no amendment to any accepted document.

Once a separate, deliberately-authorized decision creates a minimal `legoai.intelligence.model` values/ports slice (itself outside this extraction program's scope to trigger), this design's request/result contract, validation rules, and Ollama Adapter design can proceed to implementation without further architectural rework.
