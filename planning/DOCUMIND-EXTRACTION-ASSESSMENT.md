# DocuMind → LegoAI Extraction Assessment

**Document:** `planning/DOCUMIND-EXTRACTION-ASSESSMENT.md`
**Status:** DRAFT — ANALYSIS ONLY, NO IMPLEMENTATION AUTHORIZED
**Authority chain respected:** intent.md → SPEC.md → ARCHITECTURE.md → CONTRACTS.md → PLUGIN-SPEC.md → SECURITY.md → EVALUATION.md → CONFORMANCE.md → ADRs (001–011, 015 Accepted = 12 Accepted; 012–013 Proposed/non-binding; 014 unallocated)
**Inputs:** `init-Lego-AI-Operating-Layer/*` (governing docs + `src/legoai` + tests), `DocuMind-SK/*` (Semantic Kernel implementation), `DocuMind-AgentFramework/*` (Microsoft Agent Framework implementation)
**Scope:** Analysis and classification only. No source moved, no adapters written, no C# translated, no LegoAI or DocuMind files modified.
**Companion artifacts:** [`planning/documind/CHUNKING-CAPABILITY-DESIGN.md`](documind/CHUNKING-CAPABILITY-DESIGN.md) — Batch 1, `document.chunking`, AUTHORIZED and implemented in `packages/legoai-document/`. [`planning/documind/DOCUMENT-PARSING-CAPABILITY-DESIGN.md`](documind/DOCUMENT-PARSING-CAPABILITY-DESIGN.md) — Batch 2, `document.parsing`, PROPOSED design (not yet implemented).

**Revision note (previous pass):** corrected the ADR acceptance count (§0, was miscounted as 13 of 14 — the correct count is 12 of 14 allocated ADRs Accepted), reclassified DocuMind's graceful-degradation DI wiring as a `REFERENCE_RUNTIME_VALIDATION_CASE` rather than an architecture gap (§21), sharpened the Answering placement to keep `document.answering` in the Document Pack and only its underlying primitives (Model, Retrieval, Execution, Artifact, Provenance) in Core (§9, §16.5), resolved Document Pack package placement per ADR-002 §13's existing "future integration distribution" mechanism rather than proposing a new `legoai.*` owner package (§17), and adopted a revised extraction sequence (§15/§23) that separates Retrieval and Rerank into sequential steps and moves the deterministic Ingestion Workflow ahead of the probabilistic Answering capability.

**Revision note (this pass — Batch 2 design):** hardens the `DocumentParsingCapability` classification to explicitly exclude OCR from v1 (previously described loosely as a "vision sub-capability" — direct source analysis of MAF's OCR fallback found it hides a fully probabilistic Model call behind a deterministic-looking return type, which is now recorded as a defect, not a feature to bundle in); records a new risk for the client-declared-content-type/silent-UTF-8-decoding-corruption defect found in both oracles; and records the expectation that `legoai-document` will gain its first runtime dependency (`pypdf`, recommended but not yet added) once `document.parsing` is implemented. No canonical LegoAI document was modified; no ADR was reopened; Batch 1 (`document.chunking`) was not touched.

---

## 0. Critical context that shapes every recommendation below

LegoAI is **not an executable runtime**. Per the LegoAI inventory:

- 8 canonical documents (intent, SPEC, ARCHITECTURE, CONTRACTS, PLUGIN-SPEC, SECURITY, EVALUATION, CONFORMANCE) are ACCEPTED and fully specify semantics, but **create no runtime code, schemas, wire formats, or technology choices by design**.
- **12 of 14** allocated ADRs are Accepted — ADR-001 through ADR-011 (11 ADRs) plus ADR-015 (1 ADR) = 12 Accepted, verified directly against each ADR file's `**Status:**` line and against `adrs/ADR-INDEX.md` §3 acceptance table. **ADR-012 (Plugin isolation for expanded threat scope) and ADR-013 (operational observation/diagnostic integration) remain Proposed** — not binding. **ADR-014 is unallocated** (reserved, not yet authored). *(Correction: an earlier pass of this assessment miscounted this as "13 of 14" — arithmetic error, corrected here after direct file inspection rather than trusting a prior summary.)*
- Actual code in `src/legoai/` is limited to Kernel value objects (`identity.py`, `context.py`, `references.py`, `versions.py`, `errors.py` [5 of 16 canonical error categories implemented], `effects.py`), a `Principal`/`OperationContext` governance stub, and a pure, I/O-free configuration-composition fixture proving ADR-003. **There is no Plugin loader, no Execution Coordination engine, no CapabilityResolver, no Port implementations, no Model/Agent/Workflow/Tool/Memory/Retriever runtime of any kind.** Gate 2 (first executable slice) has not been reached; `planning/GATE-1-FOUNDATION-IMPLEMENTATION.md` explicitly excludes Model/Agent/Team/Workflow/RAG/vector-store work from the current gate.

**Consequence for this assessment:** the canonical "wrap before rewrite" strangler sequence (§12 of the prompt) — `LegoAI Port → ExistingDocuMindAdapter → existing C# implementation` — cannot be wired into a live LegoAI runtime today because the Port/Adapter/Execution machinery it depends on does not exist yet. This assessment therefore:

1. Defines the **Port and Capability contracts** the two DocuMind repos provide behavioral evidence for, expressed in LegoAI's own vocabulary (Capability, CapabilityVersion, Port, Provider, Adapter) so they can be dropped into LegoAI's Document Pack / Intelligence Plane the moment Gate 2 opens the Execution/Resolver machinery.
2. Recommends the **first extraction batch** be a capability with the *fewest* cross-cutting dependencies (no Governance/Resource/Execution engine required to be useful standalone) — see §16.
3. Treats the two C# repositories strictly as **production evidence and behavioral oracles** — never as code to be moved or translated — consistent with §24 of the governing prompt (no third-party or DocuMind source enters LegoAI as-is).

---

## 1. Repository maps

### 1.1 LegoAI (`init-Lego-AI-Operating-Layer`)

```
intent.md, SPEC.md                     — foundational/canonical semantics (ACCEPTED)
architecture/ARCHITECTURE.md           — logical planes, dependency direction, enforcement boundaries (ACCEPTED)
contracts/CONTRACTS.md                 — per-family operation contracts, error/ack/retry semantics (ACCEPTED)
plugin-spec/PLUGIN-SPEC.md             — Plugin SPI, manifest model, lifecycle (ACCEPTED)
security/SECURITY.md                   — authZ/authN, tenancy, sandboxing, prompt-injection defenses (ACCEPTED)
evaluation/EVALUATION.md               — evaluation primitives & categories (ACCEPTED)
conformance/CONFORMANCE.md             — conformance judgment vocabulary & proof obligations (ACCEPTED)
adrs/ADR-001..011,015                  — Accepted; concrete reference-runtime choices (Python 3.14, package layout,
                                          config model, state-consistency, authZ integration, bootstrap admission,
                                          dispatch ordering, operation dedup, evidence custody, secret handling,
                                          release evidence, asyncio supervision)
adrs/ADR-012, ADR-013                  — Proposed, non-binding (Plugin isolation; observability integration)
src/legoai/kernel/                     — identity, context, references, versions, errors (partial), effects — value objects only
src/legoai/application/                — placeholder (values.py is a stub)
src/legoai/governance/                 — Principal, OperationContext value stub
src/legoai/reference/application/      — pure ADR-003 configuration-composition fixture (no I/O)
tests/                                 — architecture import-boundary tests, package-install test, unit tests for the above
planning/GATE-1-FOUNDATION-IMPLEMENTATION.md — current gate scope; explicitly excludes AI/Agent/Workflow/RAG work
```

No Document Pack, no Model/Agent/Workflow/Memory/Retriever/Tool package exists yet anywhere in this repo.

### 1.2 DocuMind-SK (Semantic Kernel implementation)

```
src/DocuMind.Domain          — Entities, Enums, Interfaces (zero package dependencies — clean abstractions)
src/DocuMind.Core            — Parsers/, Services/ (business logic; only place Semantic Kernel types appear)
src/DocuMind.Infrastructure  — Persistence (EF Core + Npgsql + pgvector), Repositories
src/DocuMind.Api             — Minimal API composition root (Program.cs), SK Kernel wiring
src/DocuMind.Web             — Blazor Server UI, pure HTTP client of Api (no project reference to Core/Domain/Infra)
tests/DocuMind.Tests         — only ChunkingService is tested; everything else untested
infra/                       — docker-compose (Postgres+pgvector only)
```

### 1.3 DocuMind-AgentFramework (Microsoft Agent Framework implementation)

```
src/DocuMind.Domain          — Entities, Enums, Interfaces, Models/GraphModels.cs (zero package dependencies)
src/DocuMind.Core            — Agents/ (new vs SK), Parsers/, Services/ — MAF types appear here and in Api
src/DocuMind.Infrastructure  — Persistence (EF Core + Npgsql + pgvector + Neo4j), Repositories, Identity/ (new vs SK)
src/DocuMind.Api             — Minimal API composition root, MAF AIAgent wiring, ASP.NET Identity, internal-key auth
src/DocuMind.Web             — Blazor Server UI, cookie auth, pure HTTP client of Api
tests/DocuMind.Tests         — only ChunkingService is tested; everything else untested
infra/                       — docker-compose (Postgres+pgvector, Neo4j, Caddy reverse proxy, internal network isolation)
```

Both DocuMind repos share **identical Domain-layer shape and near-identical Core pipeline structure** for the RAG core; MAF adds four capabilities (categorization, vision/OCR, knowledge graph, web-search tool-calling) plus voice/image-gen and real Identity/auth. This is the central fact driving the duplication analysis in §5.

---

## 2. Dependency maps (per repository)

**LegoAI (accepted, target state):** `Application/Intent → canonical public contracts → Kernel (identity/lifecycle/error/port semantics) ← Planes (Capability, Execution, Coordination, Tool/Action, Intelligence, Context/Memory/Knowledge, Artifact, Governance, Resource, Evaluation, Observability, Extension) ← Port implementations ← Adapters/Plugins ← concrete technology`. Explicitly forbidden: domain/Kernel meaning depending on concrete Adapter semantics; Agent owning authorization; Retrieval requiring Agent; Model depending on Workflow.

**DocuMind-SK dependency direction:** `Domain (no deps) ← Core (deps: Domain, Microsoft.SemanticKernel*, PdfPig) ← Infrastructure (deps: Domain, Core, Npgsql/pgvector) ← Api (deps: Core, Infrastructure, SK OpenAI connector)`. `Web` is a sibling with **no** project reference into the stack — pure HTTP client. This is a Clean/Onion layering that already happens to satisfy LegoAI's "stable abstractions must not depend on concrete adapters" principle at the Domain/Core boundary — `DocuMind.Domain.Interfaces` are dependency-free candidate Ports.

**DocuMind-AgentFramework dependency direction:** same shape (`Domain ← Core ← Infrastructure ← Api`, `Web` decoupled), with MAF (`Microsoft.Agents.AI`) and `Microsoft.Extensions.AI` entering only at `Core`/`Api`, and Neo4j/Identity entering only at `Infrastructure`/`Api`. Domain remains **zero-dependency** in both repos — the strongest evidence that the interfaces in `DocuMind.Domain.Interfaces` are genuinely framework-agnostic candidate Ports, not accidentally SK/MAF-shaped.

---

## 3. Semantic Kernel architecture summary

SK is used **narrowly**, as a thin connector layer, not as an orchestration framework:

- `Kernel.CreateBuilder()` wires exactly two things: `ITextEmbeddingGenerationService` (always Ollama `nomic-embed-text`, local) and chat completion (`AddOpenAIChatCompletion` pointed at Groq's OpenAI-compatible endpoint, or `AddOllamaChatCompletion` as fallback — decided once at DI time based on presence of `Groq:ApiKey`).
- `EmbeddingService` depends directly on SK's `ITextEmbeddingGenerationService`.
- `QueryService` depends directly on SK's `Kernel`, `IChatCompletionService`, and `ChatHistory` — but builds the system prompt as a **raw hand-written string**, not an SK prompt template (`.prompty`/`skprompt.txt`), and calls chat completion directly.
- **Zero use of**: `KernelFunction`, `KernelPlugin`, planners, SK memory/vector-store connectors (`ISemanticTextMemory`/`IVectorStore`), function-calling/tool-calling, structured output via SK.
- Retrieval and vector storage bypass SK entirely — hand-rolled EF Core raw SQL against pgvector + Postgres full-text, fused via Reciprocal Rank Fusion.

**Conclusion:** in this codebase, Semantic Kernel is functionally equivalent to a **Model Port realization** for two capabilities only — `model.embedding` and `model.chat-completion` — nothing else in the SK surface area is load-bearing.

---

## 4. Microsoft Agent Framework architecture summary

MAF is also used **narrowly**, and specifically does **not** exercise its orchestration primitives:

- Four `AIAgent` instances (`ChatClientAgent`), registered as `AddKeyedSingleton<AIAgent>` under `AgentNames` constants: `Answering`, `Categorizer`, `VisionExtractor`, `KnowledgeGraphExtractor`.
- Each is invoked **statelessly**, once per operation, via `RunAsync`/`RunStreamingAsync` with a manually constructed `List<ChatMessage>` — conversation history is reconstructed by `QueryService` from client-supplied history on every call, not via MAF's own thread/session state.
- **Zero use of**: `AgentThread`, checkpointing, `Workflow`/graph orchestration, handoff between agents, multi-agent coordination of any kind.
- The only genuine MAF-specific behavior exercised is **tool-calling**: `AIFunctionFactory.Create(IWebSearchService.SearchAsync)` attaches a `search_web` tool to the `Answering` agent, and only when Groq (not local Ollama) is the active chat backend — the code explicitly notes local Ollama's tool-calling is unreliable.
- `IChatClient`/`IEmbeddingGenerator<>` (from `Microsoft.Extensions.AI`, not MAF-specific) are used directly by `EmbeddingService`, `CohereReranker`, etc. — i.e., most of the non-agent code already depends on the *vendor-neutral* `Microsoft.Extensions.AI` abstraction rather than MAF proper.

**Conclusion:** in this codebase, an MAF "Agent" is functionally a **Model Port realization with an optional tool-attachment capability** — a single-turn, stateless model invocation wrapped in a name and an instruction string. It does not represent bounded autonomous planning, delegation, or multi-step goal pursuit in LegoAI's sense of "Agent" (SPEC §4.2).

---

## 5. Common-behavior analysis and duplication ranking

| Responsibility | SK implementation | MAF implementation | Divergence | Common contract candidate |
|---|---|---|---|---|
| Document parsing (PDF/text) | `PdfDocumentParser` (PdfPig only, no OCR) | `PdfDocumentParser` + `ImageDocumentParser` + OCR fallback via `VisionExtractor` agent for scanned PDFs | MAF adds OCR/vision fallback and image ingestion | `DocumentParsingCapability` — **revised** (see `DOCUMENT-PARSING-CAPABILITY-DESIGN.md`): OCR is explicitly **excluded** from v1, not a bundled "sub-capability." Detailed analysis of MAF's OCR fallback found it hides a fully probabilistic vision-Model call behind the same deterministic-looking `Task<string>` return type as the text-layer path — a caller cannot tell which produced a given result. A future `document.ocr` capability (name leaning only, not decided) would be designed and composed separately once independent evidence justifies it |
| Chunking | `ChunkingService` — 512-word/50-overlap sliding window | Byte-identical algorithm and tests | **None** — verified identical via near-identical unit tests in both repos | `ChunkingCapability` |
| Embeddings | SK `ITextEmbeddingGenerationService` → Ollama `nomic-embed-text` | `Microsoft.Extensions.AI.IEmbeddingGenerator<>` → Ollama `nomic-embed-text` | Framework wrapper differs; provider and model identical | `EmbeddingCapability` (ModelCapability realization) |
| Hybrid retrieval | Raw SQL RRF (pgvector + Postgres FTS) in `ChunkRepository` | Byte-identical pattern in `ChunkRepository` | **None** — neither uses SK/MAF for retrieval at all | `RetrieverCapability` (`retrieval.hybrid`) |
| Reranking | `CohereReranker`/`NoOpReranker`, raw HTTP | Identical pattern | **None** | `RerankCapability` (CapabilityProvider with graceful-degradation offer) |
| RAG answering | Direct `IChatCompletionService` call, manual `ChatHistory`, hand-written system prompt | `ChatClientAgent.RunAsync`/`RunStreamingAsync` with manually built message list, same prompt rules, same citation post-processing (regex strip, LaTeX cleanup) | SK models this as a **direct Model invocation**; MAF wraps the *same* logic in a stateless "Agent" — no behavioral difference, only a framework-imposed naming difference | `AnsweringCapability` — a `CapabilityRequirement` for `model.reasoning` + `model.structured-citation-output`, satisfiable via **either** a Direct invocation driver or a trivial single-turn Agent driver |
| Document ingestion orchestration | `IngestionService`: parse→chunk→embed→persist | `IngestionService`: parse→chunk→embed→persist→categorize→extract-KG | MAF adds two extra pipeline steps, each independently failure-isolated | `IngestionWorkflow` (deterministic Workflow; no Agent required per step) |
| Document categorization | Not present | `Categorizer` agent + `CategorizationService`, closed 8-category taxonomy | MAF-only | `DocumentClassificationCapability` (LegoAI Document Pack candidate; low priority — narrow, single-app taxonomy) |
| Knowledge graph extraction | Not present | `KnowledgeGraphExtractor` agent + `KnowledgeGraphService` + Neo4j, per-conversation scoped, custom truncation-tolerant JSON parser | MAF-only | `StructuredExtractionCapability` (graph-shaped); Neo4j coupling and conversation-scoping are DocuMind-specific for now |
| Web search tool | Not present | `TavilyWebSearchService`/`NoOpWebSearchService`, exposed as an `AIFunctionFactory` tool | MAF-only | `ToolCapability` — a generic `tool.web-search` realization; the *pattern* (Tool exposed to a Model via a typed function schema) is the reusable part, not the Tavily binding |
| Voice / image generation | Not present | `GeminiVoiceService`/`GeminiImageGenerationService` + NoOp fallbacks | MAF-only, single-provider, thin HTTP wrappers | Low priority — thin, single-vendor, low architectural insight |
| Graceful-degradation provider selection | Groq/Ollama chat fallback; Cohere/NoOp reranker fallback | Same, plus Tavily/NoOp, Gemini×2/NoOp | **Identical pattern**, repeated 2× (SK) and 5× (MAF) | **REFERENCE_RUNTIME_VALIDATION_CASE** (revised — see §21): not a component to extract, and not an architecture gap in LegoAI's specification. SPEC §7/C-04 and ARCHITECTURE.md's Capability Resolution module already fully specify the required behavior; DocuMind supplies four concrete, reusable **test scenarios** to validate LegoAI's still-unbuilt reference CapabilityResolver against once it exists |
| Identity/auth | None (no auth) | ASP.NET Identity + roles + internal-key header between Web/Api | MAF-only | DocuMind-specific; the *shape* (TrustBoundary between Web and Api, Principal via Identity) is illustrative but the concrete mechanism is not a reusable Port realization |

**Duplication ranking (highest extraction value first):** Chunking (identical, zero coupling) > Hybrid retrieval + reranking (identical, zero coupling) > Embedding wrapper (same provider, different framework wrapper — proves the Adapter seam) > Document parsing (near-identical, MAF superset via OCR) > RAG answering (same logic, different framework "shape" — Model vs Agent) > Ingestion orchestration (same core, MAF superset) > everything MAF-only (single-repo, no cross-implementation duplication signal, lower confidence that it generalizes).

---

## 6. Complete extraction matrix

Legend for classification: `KEEP_DOCUMIND`, `LEGOAI_CORE`, `LEGOAI_DOCUMENT`, `SEMANTIC_KERNEL_ADAPTER`, `MAF_ADAPTER`, `GENERIC_DOTNET_UTILITY`, `PYTHON_REIMPLEMENTATION_CANDIDATE`, `DUPLICATE`, `RETIRE`, `UNRESOLVED`.

| Component | Repo(s) | Project | Responsibility | Framework dep | App dep | Reusable? | Classification | Target LegoAI module | Migration risk | Dependencies | Tests | Recommended action | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `IDocumentParser`, `IChunkingService`, `IEmbeddingService`, `IReranker`, `IQueryService`, `IDocumentRepository`, `IChunkRepository` | SK+MAF | Domain | Candidate Ports | None (zero-dep project) | None | Yes | LEGOAI_DOCUMENT / LEGOAI_CORE (split — see §6.1) | Document Pack Port definitions | Low | None | Indirect (via impl tests) | Use as **evidence** for Port contract shape; do not copy interface text verbatim (C# syntax) | High |
| `ChunkingService` | SK+MAF (identical) | Core/Services | Sliding-window chunker | None | None | Yes | PYTHON_REIMPLEMENTATION_CANDIDATE | `legoai` Document Pack — `ChunkingCapability` | Low | None | Full (both repos) | **First-batch candidate — see §16** | High |
| `DocumentParserDispatcher` + `PdfDocumentParser` + `PlainTextParser` | SK+MAF | Core/Parsers | Content-type dispatch, PDF/text extraction | None (PdfPig is a local library, not a framework) | None | Yes | PYTHON_REIMPLEMENTATION_CANDIDATE | Document Pack — `DocumentParsingCapability` | Low-Medium | PdfPig equivalent in Python (e.g. pypdf/pdfminer) | None | Second-batch candidate | High |
| `ImageDocumentParser` + scanned-PDF OCR fallback | MAF only | Core/Parsers | Image/OCR ingestion via vision model | Indirect (via `VisionExtractor` agent) | None | Yes | LEGOAI_DOCUMENT (Model-vision-backed) | **Not** part of `document.parsing` (revised — see `DOCUMENT-PARSING-CAPABILITY-DESIGN.md` §14). A separate, not-yet-designed capability (tentative identity `document.ocr`, chosen over `vision.text_extraction` for technology-neutrality — deliberately undecided pending independent evidence) | Medium | Depends on ModelCapability(vision) existing | None | Defer until a second realization/consumer exists, same discipline already applied to Classification/Structured-Extraction | Medium |
| `EmbeddingService` | SK | Core/Services | Wraps SK `ITextEmbeddingGenerationService` | **SEMANTIC_KERNEL_ADAPTER** boundary | None | Yes (behavior), No (as-is code) | SEMANTIC_KERNEL_ADAPTER | Adapter behind LegoAI `ModelPort`/`EmbeddingCapability` | Low | SK | None | Evidence only; Python impl talks to Ollama directly, no SK | High |
| `EmbeddingService` | MAF | Core/Services | Wraps `Microsoft.Extensions.AI.IEmbeddingGenerator<>` | **MAF_ADAPTER**-adjacent (uses vendor-neutral `Microsoft.Extensions.AI`, not MAF proper) | None | Yes | GENERIC_DOTNET_UTILITY (`Microsoft.Extensions.AI` binding, not MAF-specific) | Adapter behind LegoAI `ModelPort`/`EmbeddingCapability` | Low | `Microsoft.Extensions.AI` | None | Evidence only | High |
| `ChunkRepository.HybridSearchAsync` (RRF vector+FTS) | SK+MAF (identical) | Infrastructure/Repositories | Hybrid retrieval | None | Postgres+pgvector | Yes | PYTHON_REIMPLEMENTATION_CANDIDATE | Document Pack / Core — `RetrieverCapability` (`retrieval.hybrid`) | Medium (SQL semantics must be preserved exactly) | Postgres+pgvector equivalent (e.g. psycopg + pgvector, or provider-neutral Retriever contract with a pgvector Adapter) | None (untested in both repos — **gap**) | Third-batch candidate; write conformance tests before/while porting since no oracle tests exist | Medium |
| `ChunkRepository.SearchSimilarAsync` (pure vector KNN) | SK+MAF (identical) | Infrastructure/Repositories | Pure vector search | None | Postgres+pgvector | No (dead code in both repos — never called) | RETIRE (do not migrate; note only) | — | — | — | None | Do not extract; both repos have this as unreachable code | High |
| `CohereReranker` / `NoOpReranker` | SK+MAF (identical) | Core/Services | Cross-encoder reranking + graceful fallback | None (raw HTTP) | Cohere API | Yes | PYTHON_REIMPLEMENTATION_CANDIDATE | Document Pack / Core — `RerankCapability` | Low | Cohere HTTP API equivalent | None | Third-batch candidate, alongside retrieval | High |
| `QueryService` (SK) | SK | Core/Services | RAG orchestration via direct Model invocation | **SEMANTIC_KERNEL_ADAPTER** (Kernel, IChatCompletionService, ChatHistory) | Citation formatting, LaTeX cleanup are DocuMind-specific presentation rules | Partial | Split: orchestration logic → LEGOAI_CORE/LEGOAI_DOCUMENT; SK plumbing → SEMANTIC_KERNEL_ADAPTER; prompt/citation formatting → KEEP_DOCUMIND | Execution Plane (Direct invocation) + Document Pack (`AnsweringCapability`) | Medium | Depends on Retriever + Rerank + ModelCapability(chat) all landing first | None (**gap** — RAG orchestration is completely untested in both repos) | Fourth-batch candidate; write behavioral tests capturing "same input → same citations" before porting | Medium |
| `QueryService` (MAF) | MAF | Core/Services | Same RAG orchestration via `AIAgent.RunAsync` | **MAF_ADAPTER** (`ChatClientAgent`, `Microsoft.Extensions.AI.ChatMessage`) | Same citation/LaTeX rules | Partial | Same split as above | Same | Medium | Same | None | Use both SK and MAF `QueryService` bodies as a **cross-implementation oracle** — behavior must match | Medium |
| `AnsweringAgent` instructions (system prompt text) | MAF only (SK inlines the same rules as a raw string in `QueryService`) | Core/Agents | Prompt content: citation rules, grounding, language-matching, no-LaTeX | None | Yes — DocuMind's citation/format conventions | No (DocuMind-specific prompt content), Yes (the *pattern* of externalizing instructions as a named, versioned asset) | KEEP_DOCUMIND (content) / informs LEGOAI's `Skill` concept (pattern) | — | Low | — | None | Keep in DocuMind; note as evidence that "Skill" (SPEC §4.5) is the right home for this kind of externalized instruction asset in future LegoAI apps | High |
| `IngestionService` | SK | Core/Services | parse→chunk→embed→persist orchestration | None directly (depends on abstractions) | None | Yes | PYTHON_REIMPLEMENTATION_CANDIDATE (as a deterministic Workflow) | Execution Plane / Workflow driver — `IngestionWorkflow` | Medium | Depends on all upstream capabilities landing | None (**gap**) | Fifth-batch, after Chunking/Parsing/Embedding/Retrieval exist in Python | Medium |
| `IngestionService` | MAF | Core/Services | Same + categorize + extract-KG steps, independently failure-isolated | Indirect (via agent-backed services) | None | Yes | Same as above, extended | Same | Medium-High | Same + `CategorizationCapability` + `StructuredExtractionCapability` | None | Same; MAF's per-step failure isolation pattern is worth preserving in the Workflow design | Medium |
| `CategorizerAgent` + `CategorizationService` | MAF only | Core/Agents, Core/Services | Fixed 8-category document classification | MAF_ADAPTER (agent wrapper) | Yes — DocuMind's specific taxonomy | Partial | KEEP_DOCUMIND (taxonomy) / LEGOAI_DOCUMENT (pattern: `DocumentClassificationCapability` with app-supplied taxonomy) | Document Pack (generalized, taxonomy-parameterized) | Low | ModelCapability(chat) | None | Low priority; defer past first 5 batches | Low-Medium |
| `KnowledgeGraphExtractor` + `KnowledgeGraphService` + `Neo4jGraphRepository` | MAF only | Core/Agents, Core/Services, Infrastructure | Entity/relationship extraction to graph, per-conversation scoped, truncation-tolerant JSON parsing | MAF_ADAPTER (agent) | Neo4j, conversation-scoping | Partial | LEGOAI_DOCUMENT (pattern: `StructuredExtractionCapability`) / KEEP_DOCUMIND (Neo4j binding, conversation scoping) | Document Pack (generalized) + a `RetrieverPort`/`KnowledgePort` graph realization | Medium-High | Neo4j equivalent, or provider-neutral graph Port | None | Defer — single-repo, higher coupling, no duplication evidence to cross-validate against | Low-Medium |
| `TavilyWebSearchService` / `NoOpWebSearchService` + `AIFunctionFactory` tool attachment | MAF only | Core/Services | Web search exposed as an agent tool | MAF_ADAPTER (tool schema generation) | Tavily API | Partial | LEGOAI_CORE (pattern: `ToolPort` realization + typed function-schema exposure) / KEEP_DOCUMIND (Tavily binding) | Tool/Action Plane — `ToolCapability` realization pattern | Low | Tavily HTTP API or any web-search provider | None | Useful evidence for how Tool Port should expose typed schemas to a Model; low priority for code, useful for contract design | Medium |
| `GeminiVoiceService`, `GeminiImageGenerationService` + NoOp fallbacks | MAF only | Core/Services | STT/TTS, text-to-image | None (raw HTTP) | Gemini API, single-vendor | Low | KEEP_DOCUMIND | — | Low | — | None | Not extracted — thin, single-vendor, low architectural insight; revisit only if a future LegoAI app needs voice/image capabilities | Low |
| Graceful-degradation DI wiring (Groq/Ollama, Cohere/NoOp, Tavily/NoOp, Gemini/NoOp) | SK+MAF | Api/Program.cs | Compile-time-conditional provider selection | None (plain DI) | Yes — hardcoded to these specific providers | No (as code) / Yes (as a gap signal) | UNRESOLVED — see §21 architecture-gap note | Informs future `CapabilityResolver` reference implementation | N/A | N/A | N/A | Do not extract as code; use as a **requirements input** for LegoAI's still-unimplemented Capability Resolution module | High |
| `DocumentRepository`, `ChunkRepository` (CRUD parts, excluding hybrid search) | SK+MAF (identical) | Infrastructure | EF Core CRUD over Postgres | None | EF Core, Npgsql | Low (ORM-specific plumbing) | GENERIC_DOTNET_UTILITY | — (Python persistence Adapter would be a fresh implementation, not a port of this code) | Low | — | None | Not extracted; persistence Adapter for LegoAI's ArtifactPort/state will be designed fresh in Python per ADR-004's owner-local consistency model | High |
| `DocuMindDbContext` + migrations | SK+MAF (near-identical) | Infrastructure | EF Core schema/migrations | None | EF Core | No | GENERIC_DOTNET_UTILITY | — | Low | — | None | Not extracted | High |
| ASP.NET Identity (`ApplicationUser`, `AppRoles`, internal-key middleware) | MAF only | Infrastructure/Identity, Api | AuthN, role seeding, Web↔Api shared-secret trust boundary | None (ASP.NET Identity) | Yes | Low | KEEP_DOCUMIND | — | Low | — | None | Illustrative of a TrustBoundary crossing (SPEC §4.9) but the mechanism itself (shared header secret) is not a Port-worthy pattern; do not extract | Medium |
| Blazor Web UI (`Home.razor`, `Login.razor`, `AdminUsers.razor`) | SK+MAF | Web | Presentation | None | Yes, entirely | No | KEEP_DOCUMIND | — | — | None | None | Out of scope for LegoAI (an Application concern, not a capability) | High |
| `QueryRecord` entity + DbSet | SK+MAF (identical) | Domain/Infrastructure | Query logging | — | — | No | RETIRE (dead code in both repos — never written to) | — | — | — | — | Flag to DocuMind maintainers as dead code; not a LegoAI concern | High |
| `docs/development.md`, `AGENTS.md`, ADR process artifacts | LegoAI | — | Engineering process | — | — | — | KEEP (LegoAI process asset) | — | — | — | — | No action | High |

### 6.1 Note on the Domain interfaces split

`IDocumentParser`, `IChunkingService`, `IEmbeddingService`, `IReranker` are **Document Pack**-shaped (LEGOAI_DOCUMENT) — they only make sense in a document-processing application. `IQueryService`'s underlying capability (retrieval-augmented answering) is **Core-Intelligence-Plane**-shaped (LEGOAI_CORE / Document Pack boundary) because "retrieval + generation with citations" is not document-specific per se, only its current callers are. `IDocumentRepository`/`IChunkRepository` are storage-shaped and map to a future `ArtifactPort`/state realization rather than a new named Port.

---

## 7. Duplication analysis (see also §5 table)

**Exact or near-exact duplicates across SK and MAF** (safe, high-confidence extraction targets, since two independent implementations already prove the contract is stable):
1. `ChunkingService` — byte-for-byte identical algorithm and near-identical tests.
2. `ChunkRepository.HybridSearchAsync` (RRF) and `SearchSimilarAsync` (dead in both) — identical SQL pattern.
3. `CohereReranker`/`NoOpReranker` — identical.
4. `DocumentParserDispatcher`/`PdfDocumentParser`/`PlainTextParser` — identical except MAF's added OCR fallback.
5. `IngestionService`'s core parse→chunk→embed→persist steps — identical; MAF appends two more steps.
6. `QueryService`'s retrieval→rerank→prompt→citation-postprocessing logic — identical business rules, different framework wrapper around the final model call.
7. The "graceful degradation via DI-time conditional registration" idiom — repeated independently in both repos for every optional external provider.

**Framework-driven duplication** (same responsibility, different framework surface, not different behavior): the Embedding wrapper (SK `ITextEmbeddingGenerationService` vs `Microsoft.Extensions.AI.IEmbeddingGenerator<>`) and the RAG-answering call (SK direct `IChatCompletionService` call vs MAF `ChatClientAgent.RunAsync`). These are the two most valuable specimens for proving LegoAI's Model/Agent-neutral contract design, because they are the *only* places where the two codebases genuinely diverge in shape while producing identical behavior.

**Business duplication**: none identified — no case where the two repos implement genuinely different business rules for the same nominal feature.

**Infrastructure duplication**: the Postgres/pgvector schema and EF Core repository pattern are duplicated at the code level but are not candidates for LegoAI extraction (persistence Adapters will be written fresh in Python per ADR-004).

---

## 8. DocuMind-specific components (KEEP_DOCUMIND)

- Blazor Web UI (both repos) — presentation layer, NotebookLM-style two-panel design, entirely product-specific.
- Prompt/instruction text for all agents (citation formatting rules, LaTeX-avoidance, grounding rules, categorization taxonomy, KG extraction schema) — DocuMind's specific conventions, though the *pattern* of externalizing instructions maps to LegoAI's `Skill` concept for future reuse.
- ASP.NET Identity, internal-key header auth, Docker Compose/Caddy topology — DocuMind's specific deployment and trust model.
- Gemini voice/image-generation bindings — single-vendor, low reuse value.
- Neo4j-backed, per-conversation-scoped knowledge graph — DocuMind's specific feature; the *extraction pattern* is noted as LEGOAI_DOCUMENT-worthy but the storage/scoping choices are product-specific.
- `QueryRecord` dead code, `UnitTest1.cs` placeholder tests — noted for DocuMind's own cleanup, not a LegoAI concern.

---

## 9–14. Classification group listings

These are drawn directly from §6; restated here per the required assessment structure.

**§9 LEGOAI_CORE candidates — generic primitives only, not `document.answering` itself:** the primitives that `document.answering` composes are Core-level and already exist as canonical concepts — `ModelCapability` (`model.reasoning`/chat-completion), `RetrieverCapability`'s general shape (though its *hybrid document* realization stays in the Document Pack — see §16.3), `Execution` (Direct-invocation driver, proven sufficient by the SK evidence), `Artifact`, and `Provenance`/`Evidence`. The RAG-answering orchestration *pattern itself* (Direct-invocation vs. trivial-Agent duality — proves I-04/I-13/DEC-01) and the Tool Port exposure pattern (typed function schema attached to a Model, evidenced by `AIFunctionFactory`/web-search tool) are Core-proving *evidence*, not proposals to add a generic "RAG answering" concept to Core — `document.answering` remains a Document Capability Pack capability (§16.5) until an independent, non-document consumer demonstrates the same composite is needed outside document Q&A. DocuMind's graceful-degradation DI wiring is **not** treated as a Core requirements gap — see the corrected classification in §21.

**§10 LEGOAI_DOCUMENT candidates:** `ChunkingCapability` (Batch 1, complete), `DocumentParsingCapability` (Batch 2 design complete — see `DOCUMENT-PARSING-CAPABILITY-DESIGN.md`; v1 = deterministic plain-text + text-bearing-PDF extraction only, OCR excluded and tracked as a separate, undesigned future capability), `RetrieverCapability` (`retrieval.hybrid`), `RerankCapability`, `AnsweringCapability` (retrieval+generation+citations), `IngestionWorkflow`, `DocumentClassificationCapability` (lower priority), `StructuredExtractionCapability` (graph-shaped, lower priority, single-repo evidence only).

**§11 SEMANTIC_KERNEL_ADAPTER candidates:** SK's `EmbeddingService` wrapper (`ITextEmbeddingGenerationService`), SK's `QueryService` chat-completion call (`Kernel`, `IChatCompletionService`, `ChatHistory`) — both are evidence for what a future **optional** SK Adapter behind LegoAI's `ModelPort` could look like, not code to import.

**§12 MAF_ADAPTER candidates:** MAF's `EmbeddingService` wrapper (technically `Microsoft.Extensions.AI`, MAF-adjacent), the four `ChatClientAgent` wrappers (`Answering`, `Categorizer`, `VisionExtractor`, `KnowledgeGraphExtractor`), the `AIFunctionFactory` tool-attachment mechanism — evidence for a future **optional** MAF Adapter behind LegoAI's `ModelPort`/`ToolPort`, not code to import.

**§13 Python reimplementation candidates (priority order):** (1) Chunking, (2) Document parsing (PDF/text; vision/OCR deferred), (3) Hybrid retrieval + reranking, (4) Embedding capability (Ollama-backed, framework-free), (5) Answering capability (Direct-invocation shape first; Agent-driver shape deferred until LegoAI has an Agent driver), (6) Ingestion workflow (after 1–4 exist).

**§14 Dead/obsolete candidates:** `QueryRecord` entity+DbSet (both repos, never written), `ChunkRepository.SearchSimilarAsync` pure-vector search (both repos, never called), `UnitTest1.cs` placeholder tests (both repos), an orphaned `DocumentSummary` migration column with no corresponding entity property (SK repo). None of these are LegoAI's concern to fix — flagged for DocuMind's own hygiene only, not touched here.

---

## 15. Extraction sequence (revised)

**Revision note:** the prior pass of this assessment scored these five candidates (§15 table below, retained for its per-candidate dimensions) but then applied an inconsistent order in §18/§23 — grouping Retrieval+Rerank as one combined batch and placing the deterministic Ingestion Workflow after the probabilistic Answering capability. This pass corrects that by evaluating the full seven-capability set explicitly against: minimum dependency count, deterministic-first development, testability, ability to form useful vertical slices, minimum framework coupling, and progressive introduction of probabilistic behavior (intent §12's own preferred escalation: deterministic code → deterministic workflow → model → agent).

Scoring dimensions (unchanged): reusability, framework independence, testability, dependency count, migration risk, business value, Python portability, ability to prove LegoAI's architecture.

| Rank | Candidate | Reusability | Framework independence | Testability | Dep. count | Migration risk | Business value | Python portability | Architecture-proving value |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Chunking** (`ChunkingCapability`) | High | Total (zero framework coupling in both repos) | Excellent (existing tests in both repos are a ready-made oracle) | None | Very low | Medium | Trivial | Low-medium (simple, but proves the whole pipeline end to end fastest) |
| 2 | **Document parsing** (`DocumentParsingCapability`, PDF+text only, OCR deferred) | High | High (PdfPig is a local library, not a framework) | Weak (no existing tests) — must write conformance tests first | Low (needs a Python PDF text-extraction library) | Low | Medium-high | High | Medium |
| 3 | **Embedding capability** (`EmbeddingCapability`, Ollama-backed) | High | This *is* the seam — SK and MAF each wrap it differently around the same provider | Weak (no existing tests) | Low (Ollama HTTP API) | Low | High | High | Very high — the cleanest possible demonstration of one `CapabilityVersion` with two independent framework-specific Adapters (`SEMANTIC_KERNEL_ADAPTER` vs `MAF_ADAPTER`) both realizing the same LegoAI `ModelPort` |
| 4 | **Hybrid retrieval** (`RetrieverCapability`) | High | Total (zero SK/MAF coupling in either repo — pure SQL) | Weak (no existing tests) — must write conformance tests capturing exact RRF behavior first | Medium (needs Embedding's output + Postgres+pgvector) | Medium | High | High | High — proves "Retrieval ≠ Agent" (I-14) directly |
| 5 | **Reranking** (`RerankCapability`) | High | Total (zero SK/MAF coupling — pure HTTP) | Weak (no existing tests) | Low-medium (Cohere API; consumes Retriever's output but has no structural dependency on it) | Low-medium | Medium | High | Medium — demonstrates optional-provider CapabilityResolution (§21.1 case #2) |
| 6 | **Ingestion Workflow** (`IngestionWorkflow`) | Medium-high | Total — pure orchestration, no new framework surface | Weak (no existing tests; both C# repos test only its constituent parts) | High (composes 1–3) | Medium | High — the first genuinely useful end-to-end vertical slice (upload → searchable) | Medium | High — proves a deterministic Workflow needs no Agent (I-13), and forms the last all-deterministic milestone before Answering |
| 7 | **Answering capability** (`AnsweringCapability`, Direct-invocation shape) | Medium-high | Low — this is where framework shape genuinely diverges (Model call vs. Agent wrapper) | Weak (no existing tests) — must capture citation/format behavior as an oracle first | Highest (depends on 3, 4, 5) | Medium-high | High | Medium | Very high — the single clearest specimen of DEC-01 (Operational Result ≠ canonical Outcome) and I-04/I-13 (Agent optional, reasoning ≠ authority); deliberately last because it is the only genuinely probabilistic capability in the pack |

**Why this order and not the prompt's alternative groupings:** Chunking and Parsing tie on zero dependency count and zero probabilism, but Chunking is smaller and already has a byte-identical, fully passing test oracle in both C# repos (§24), so it goes first. Embedding is promoted ahead of Retrieval/Rerank because Retrieval structurally consumes Embedding's output (§18 dependency graph) and because Embedding is the single best specimen for proving the SK-Adapter/MAF-Adapter duality (§6, §16.2) — sequencing it early lets that architectural proof land before the harder, untested retrieval work. Retrieval is sequenced before Rerank because Rerank is only meaningful applied to Retrieval's candidate list, even though neither has a hard code dependency on the other. Ingestion Workflow is deliberately promoted **ahead of** Answering (reversing the prior draft's order) because it is a pure composition of already-deterministic capabilities (1–3) — it introduces no new probabilism, forms the first complete, demonstrably useful vertical slice ("upload a document, have it become searchable"), and lets the Workflow driver itself be proven out while everything underneath it is still deterministic. Answering is last because it is the only capability in this set that is genuinely probabilistic (LLM generation) and the only one where the SK/MAF framework shapes actually diverge (§4–5) — per intent §12's escalation principle, probabilistic behavior should be introduced last, once the deterministic foundation beneath it is proven.

**Recommendation:** run candidates 1 and 3 as the first two implementation batches (in that order — Chunking now, Embedding once Chunking's conformance approach is proven), following the full seven-step sequence above thereafter. See §16 for full contract detail on Chunking, the companion [`CHUNKING-CAPABILITY-DESIGN.md`](documind/CHUNKING-CAPABILITY-DESIGN.md) for its complete implementation design, and §23 for the phased plan.

---

## 16. Proposed capability contracts (language-neutral)

### 16.1 `ChunkingCapability` (LEGOAI_DOCUMENT — Document Capability Pack, not Core)

Full detail, including the characterization table and Python API shape, is in the companion design document: [`planning/documind/CHUNKING-CAPABILITY-DESIGN.md`](documind/CHUNKING-CAPABILITY-DESIGN.md). Summary retained here for continuity:

- **Capability identity:** `document.chunking` (import root `legoai_document` — a separate, sibling import root to `legoai`, per §17's revised target architecture; **not** `legoai.document`)
- **Inputs:** document identity/reference, full extracted text (string), chunk size (word/token count, default 512), overlap (default 50)
- **Outputs:** ordered list of chunks, each with: chunk index, content, token/word count, source document reference, optional page number (declared but MAY be unset — evidence shows both DocuMind repos never populate it)
- **Errors:** `ValidationError` (empty/invalid input), no other categories apply — this is a pure, deterministic, effect-free computation
- **Artifact semantics:** chunk sets MAY be persisted as an ArtifactVersion at the caller's discretion; the capability itself performs no I/O
- **Configuration requirements:** chunk size, overlap — both MUST be explicit (no silent defaults hidden from the caller, per SPEC S-05)
- **Provider requirements:** none — pure computation, zero external dependencies
- **Resource requirements:** negligible CPU/memory; no Budget/Quota needed
- **Evidence requirements:** none beyond standard provenance (who requested it, which document revision)
- **Security/tenant requirements:** input text inherits the caller's TenantContext; the capability does not itself need tenant-aware storage since it holds no state
- **Evaluation requirements:** deterministic — golden-input/golden-output conformance tests suffice (no probabilistic evaluation needed)

### 16.2 `EmbeddingCapability` (LEGOAI_CORE, ModelCapability specialization)

- **Capability identity:** `model.embedding` (namespace `legoai.model`)
- **Inputs:** text or batch of texts; model/provider selection is a Provider-offer concern, not part of the request contract
- **Outputs:** vector(s) of declared dimensionality; the dimensionality itself is part of the `CapabilityVersion` contract (both DocuMind repos hardcode 768 for `nomic-embed-text` — this MUST be an explicit, checked property in LegoAI's version, not implicit)
- **Errors:** `ModelFailure` (invocation/output contract violation), `DependencyFailure` (provider unavailable), `BudgetExceeded` if token/cost limits apply
- **Artifact semantics:** embeddings are typically stored alongside their source chunk, not treated as independent Artifacts
- **Configuration requirements:** provider endpoint, model identity, batch size, per-call timeout (both DocuMind repos batch 5 embeddings per call with a 10-minute timeout — evidence that batching/timeout MUST be explicit CapabilityVersion-level configuration, not hardcoded)
- **Provider requirements:** at least one ModelCapability offer advertising `model.embedding`; DocuMind evidence shows exactly one provider (Ollama) is used in both repos — no multi-provider embedding fallback exists today, unlike chat completion
- **Resource requirements:** Budget/Quota MAY apply if a paid embedding provider is later used; DocuMind's local-Ollama-only choice sidesteps this today
- **Evidence requirements:** model identity + version MUST be recorded in provenance for every embedding produced (SPEC S-12) — neither DocuMind repo currently does this explicitly (embeddings are stored without recording which model/version produced them), which is a **gap** worth flagging to DocuMind, not a LegoAI defect
- **Security/tenant requirements:** output vectors are untrusted-provenance data like any Model output (SPEC §4.5 Model invariants) — do not treat as ground truth
- **Evaluation requirements:** embedding quality is normally assessed indirectly via downstream retrieval quality (recall@k), not directly — `EvaluationPlane`/`EVALUATION.md` §13 (information/retrieval evaluation) is the applicable category

### 16.3 `RetrieverCapability` (LEGOAI_DOCUMENT / LEGOAI_CORE boundary)

- **Capability identity:** `retrieval.hybrid` (namespace `legoai.retrieval`)
- **Inputs:** query text/embedding, candidate pool size (DocuMind evidence: top 25), optional metadata filters (DocuMind evidence: conversation-scope filter in the MAF repo)
- **Outputs:** ranked candidate list with scores and source attribution (SPEC §4.7 Retriever: "apply query semantics, access filtering, and result provenance")
- **Errors:** `DependencyFailure` (store unavailable), `ValidationError` (malformed query)
- **Artifact semantics:** none directly; operates over already-persisted chunk Artifacts
- **Configuration requirements:** fusion method (DocuMind evidence: Reciprocal Rank Fusion combining vector cosine similarity and Postgres full-text rank) MUST be an explicit, versioned property of the `CapabilityVersion`, not implicit in a specific SQL query
- **Provider requirements:** a vector-capable store and a text-search-capable store (DocuMind evidence: both currently the *same* Postgres+pgvector instance, but the capability contract MUST NOT assume that — SPEC I-01 replaceability test)
- **Resource requirements:** query latency/Budget MAY apply under load; not currently governed in DocuMind
- **Evidence requirements:** which chunks were returned and why (score/rank) MUST be attributable per SPEC S-12 — DocuMind's citation mechanism already partially satisfies this at the answering layer
- **Security/tenant requirements:** results MUST be filtered to the caller's tenant/scope before return (SPEC S-11) — DocuMind's conversation-scoping in the MAF repo is a narrow, single-app instance of this general requirement, not equivalent to full TenantContext isolation
- **Evaluation requirements:** SPEC/EVALUATION §13 retrieval evaluation category applies directly — recall/precision/relevance metrics, independent of any Agent or generation step (proves I-14: "Independent memory/retrieval usage does not construct an Agent or require generation")

### 16.4 `RerankCapability`

- **Capability identity:** `retrieval.rerank` (namespace `legoai.retrieval`)
- **Inputs:** query, candidate list, top-N
- **Outputs:** reordered subset of candidates with relevance scores
- **Errors:** `DependencyFailure`, graceful degradation to identity/truncation behavior is a valid, explicitly declared fallback offer (DocuMind's `NoOpReranker` is exactly this pattern) — but per SPEC C-04, this fallback MUST be a **declared acceptable behavior**, not a silent one
- **Provider requirements:** optional — the capability MUST be usable with zero rerank providers configured (both DocuMind repos already demonstrate this via `NoOpReranker`)

### 16.5 `AnsweringCapability` (deferred to batch 5 — contract sketched for completeness)

- **Capability identity:** `document.answering` — a `CompositeCapability` (SPEC §4.4) depending on `model.reasoning`, `retrieval.hybrid`, `retrieval.rerank`
- **Key design decision this capability must resolve, evidenced directly by the SK/MAF divergence:** the capability MUST be satisfiable by **either** a Direct capability invocation (SK's shape: build context, call Model once, return result — no Agent, no Goal, no Team) **or** an Agent driver (MAF's shape: same logic wrapped in a stateless single-turn Agent) — per DEC-01, neither path requires inventing a Goal/Team/Outcome. The contract MUST NOT bake in an assumption that answering requires an Agent.
- **Outputs:** answer text, ordered citation list (chunk reference + display index), latency
- **Errors:** `ModelFailure`, `DependencyFailure` (upstream retrieval/rerank failure)
- **Evidence requirements:** citations are the provenance mechanism (SPEC §4.11 Provenance) — DocuMind's `[n]`-style inline citation with a matching reference list is a concrete, reusable citation contract shape worth preserving

---

## 17. Target architecture (derived from actual evidence, not invented)

```
LegoAI Core (existing plane structure per ARCHITECTURE.md — unchanged by this assessment)
│
├── Intelligence Plane
│   └── Model Interaction module
│       └── ModelPort
│            ├── EmbeddingCapability (offer: Ollama-backed, evidenced by both DocuMind repos)
│            └── ChatCompletionCapability (offer: Groq/Ollama-backed, evidenced by both repos)
│
├── Execution Plane
│   └── Direct capability driver — proven sufficient for AnsweringCapability per SK evidence
│   └── (Agent driver — not exercised meaningfully by either DocuMind repo; MAF's agents are
│        stateless single-turn wrappers, not evidence for planning/delegation/multi-step autonomy)
│
├── Tool/Action Plane
│   └── Action Mediation module
│        └── ToolPort — evidenced by MAF's `AIFunctionFactory` web-search tool pattern

LegoAI Document Capability Pack (NEW — does not exist yet)
│  Package placement (resolved — see planning/documind/CHUNKING-CAPABILITY-DESIGN.md §"Package placement"
│  for the full evaluation): this is NOT a 13th `legoai.*` owner package and NOT placed under
│  `legoai.reference` — those are reserved for the canonical Core owners ADR-002 §5/§7.1 already
│  enumerates (kernel, application, capabilities, execution, tools, governance, resources, plugins,
│  observability, evidence, runtime, reference), none of which is "document." Document capabilities
│  are not SPEC-defined canonical concepts; they are an application-domain composition over Core
│  primitives. ADR-002 §13 already anticipates and authorizes exactly this case: "Future integration
│  distributions use their own import roots... They depend on documented Lego AI Ports/SPI, not
│  legoai.reference." The Document Pack therefore gets its OWN import root, proposed as `legoai_document`
│  (distribution `legoai-document`), living beside — not inside — the `legoai` distribution in the same
│  repository for solo-developer simplicity. Core never imports it; it may import Core's stable public
│  contracts once they exist, and needs none at all for its first capability (Chunking is pure). This is
│  a small implementation decision consistent with an already-accepted ADR, not a new ADR.
│
├── chunking        — ChunkingCapability (`document.chunking`)   [FIRST BATCH — see §16.1, §23, and the
│                      companion design doc]
├── parsing         — DocumentParsingCapability (PDF/text now; vision/OCR sub-capability later)
├── embedding       — EmbeddingCapability (thin wrapper around a ModelCapability(embedding) offer)
├── retrieval       — RetrieverCapability (hybrid vector+text)
├── rerank          — RerankCapability
├── ingestion       — IngestionWorkflow (deterministic composition of the above — ordered ahead of
│                      Answering; see the revised sequence in §15/§23)
└── answering       — AnsweringCapability (composite, the only genuinely probabilistic capability in
                       this pack; composes Core's ModelCapability/Execution/Artifact/Provenance
                       primitives plus this pack's own Retriever/Rerank — kept in the Document Pack,
                       not promoted to Core, until an independent non-document consumer needs it)

Adapters (all deferred — no Execution/Plugin engine exists to host them yet)
│
├── Semantic Kernel Adapter   — optional; realizes ModelPort using SK's Kernel/IChatCompletionService
├── Microsoft Agent Framework Adapter — optional; realizes ModelPort+ToolPort using AIAgent/ChatClientAgent
├── Ollama Adapter            — realizes ModelPort directly, no SK/MAF dependency (recommended default
│                                for the Python reference runtime, since neither framework is .NET-portable
│                                to Python and both DocuMind repos already treat their respective framework
│                                as a thin, replaceable wrapper around this same provider)
├── Postgres+pgvector Adapter — realizes RetrieverCapability's vector+text store requirement
└── Cohere Adapter            — realizes RerankCapability

Applications (future)
└── A LegoAI "document-ai" blueprint (intent §23) — composes Document Pack capabilities;
    NOT a copy of DocuMind's Web/Api/Identity/Blazor layers, which remain DocuMind-specific
```

**Why no C# Adapters are proposed for the Python reference runtime:** ADR-001 selects CPython 3.14 as the reference-runtime language; there is no accepted ADR authorizing in-process C#/.NET interop for the reference runtime. SK and MAF Adapters remain a **documented future option** (intent §39, "compatible with future .NET integration") but are not part of the near-term plan — the Python reference implementation should talk to Ollama/Groq/Postgres/Cohere directly, which both DocuMind repos already prove is architecturally sufficient (SK and MAF are both thin wrappers around exactly these same providers).

---

## 18. Migration dependency graph

```
ChunkingCapability (no deps)
        │
        ▼
DocumentParsingCapability (no deps on Chunking, but typically composed before it in a Workflow)
        │
        ▼
EmbeddingCapability (no deps on Chunking/Parsing, but consumes their output in practice)
        │
        ▼
RetrieverCapability  ──requires──▶  EmbeddingCapability (for query embedding) + persisted chunks
        │
        ▼
RerankCapability (optional dependency of Retriever's consumers, not of Retriever itself)
        │
        ├────────────────────────────────────────────┐
        ▼                                              ▼
IngestionWorkflow  ──requires──▶  DocumentParsingCapability   AnsweringCapability  ──requires──▶
  + ChunkingCapability + EmbeddingCapability                    RetrieverCapability + RerankCapability
  (+ optionally DocumentClassificationCapability,                + ChatCompletionCapability
   StructuredExtractionCapability once/if those are
   built — MAF evidence only, lower priority)
```

`IngestionWorkflow` and `AnsweringCapability` are independent branches with no dependency on each other — the graph itself does not force an order between them. §15's revised sequence orders `IngestionWorkflow` before `AnsweringCapability` anyway, on non-dependency grounds: it is the last purely deterministic milestone and forms a complete, demonstrably useful vertical slice before the pack's first genuinely probabilistic capability is introduced.

No cycles. `ChunkingCapability` and `DocumentParsingCapability` are the only nodes with zero upstream dependencies, confirming §15's ranking.

---

## 19. Cross-language strategy

Per intent §39/§49 and ADR-001, the Python reference implementation is canonical; C# is not translated line-by-line. For each capability:

1. Define the capability contract in language-neutral terms (§16 above) — done for the first five candidates.
2. Implement the Python reference realization idiomatically (e.g., `ChunkingCapability` as a pure function over `str`/`dataclass`, not a transliterated C# class hierarchy).
3. Treat the existing C# implementations (both SK and MAF repos) as **behavioral oracles**: for `ChunkingCapability`, the existing xUnit tests in both repos already enumerate the exact behavioral contract (empty input, overlap correctness, sequential indexing, DocumentId propagation) — the Python conformance suite should assert equivalent behavior, not equivalent code shape.
4. For capabilities with **no existing tests** in either C# repo (retrieval, rerank, embedding, answering, ingestion — see the "Tests" column in §6), the Python effort must **first write a conformance specification** (input/output pairs, edge cases) *before* porting, since there is currently no working oracle beyond reading the C# source. This is flagged as elevated risk in §29.
5. A future optional .NET compatibility layer (SK Adapter, MAF Adapter) may later re-implement the same canonical contract in C# for integration scenarios — but this is not part of the near-term plan (see §17).

---

## 20. Test/conformance strategy

Per CONFORMANCE.md's judgment vocabulary (conformant / nonconformant / not assessed / insufficient evidence / not applicable / unsupported scope — "partially conformant" is explicitly forbidden):

- **ChunkingCapability**: existing tests in both DocuMind repos are directly convertible into a conformance case set (empty text, short text, long text, overlap correctness, index sequencing, document-id propagation). This is the only candidate capability that starts with `conformant` reachable quickly.
- **DocumentParsingCapability, RetrieverCapability, RerankCapability, EmbeddingCapability, AnsweringCapability**: currently `not assessed` — no tests exist in either C# repo for any of these (confirmed by both inventory agents independently). Conformance work must start from a written specification of expected behavior (edge cases: empty document, scanned/image-only PDF, zero search results, tie-breaking in RRF, reranker unavailable, embedding provider timeout, citation index mismatch), not from reverse-engineering passing tests.
- Every Adapter (future SK/MAF/Ollama/Postgres/Cohere adapters) must independently satisfy CONFORMANCE.md §8's Port-level and Adapter-level proof obligations, including the mandatory negative cases (§21 CONF-064: e.g., provider failure must not silently map to success — DocuMind's own `NoOpReranker`/Ollama-fallback pattern already demonstrates *declared* degradation, which is conformant in spirit, but was never asserted by a test in either repo).

---

## 21. Architecture gaps found

| Gap | Classification | Justification |
|---|---|---|
| DocuMind's DI-time graceful-degradation wiring (Groq/Ollama, Cohere/NoOp, Tavily/NoOp, Gemini/NoOp) has no equivalent in LegoAI today because CapabilityResolver is unimplemented (Gate 2 not reached) | **REFERENCE_RUNTIME_VALIDATION_CASE** (revised classification — this is neither a new Core capability proposal nor an open architecture gap) | ARCHITECTURE.md and SPEC.md §7/C-04 already fully specify the CapabilityResolver's required behavior end to end. DocuMind contributes no new requirement — it contributes four concrete, reusable **test fixtures** (§21.1 below) that a future reference CapabilityResolver implementation must be validated against once Gate 2 opens. No amendment to accepted LegoAI documents is justified or needed. |
| DocuMind's per-conversation scoping (MAF repo) resembles but is not equivalent to LegoAI's TenantContext | APPLICATION_SPECIFIC | Conversation scope is a narrower, single-dimension partition invented for chat-session isolation, not a verified, externally-issued tenant boundary (SPEC S-10/S-11 require verified TenantContext with cross-tenant grant semantics). No gap in LegoAI; DocuMind simply hasn't needed full tenancy yet. |
| DocuMind's Web↔Api internal-key header is a TrustBoundary crossing with no formal Policy/Approval semantics behind it | APPLICATION_SPECIFIC | This is a minimal, ad hoc mechanism sufficient for DocuMind's own deployment topology; LegoAI's TrustBoundary/Policy/Authorization concepts already specify a considerably richer model (SPEC §4.9, SECURITY.md §6-7). No gap — DocuMind simply doesn't need the full model yet. |
| Neither DocuMind repo records model identity/version in provenance alongside produced embeddings or answers | APPLICATION_SPECIFIC / minor conformance gap in DocuMind itself, not LegoAI | SPEC S-12 requires this; it is a DocuMind implementation gap to flag to DocuMind's own maintainers, not evidence that LegoAI's Provenance concept (§4.11) is insufficiently specified — the opposite: LegoAI already requires more than DocuMind currently does. |
| Neither DocuMind repo has retrieval, rerank, embedding, or answering test coverage | UNCERTAIN (risk, not an architecture gap) | Affects extraction confidence (§29) but is not a LegoAI architecture question. |

**No accepted LegoAI document requires amendment based on this evidence.** The evidence instead validates several already-accepted decisions: DEC-01 (operational result ≠ canonical Outcome — SK's direct Model-invocation answering path is a clean real-world instance of this), I-13/I-14 (Agent and generation are optional for retrieval — both repos' retrieval code never touches an Agent or Model), and I-04 (reasoning must not create authority — neither repo's agents/models are ever granted unmediated tool/data access; the one tool exposed, web search, is a narrow, read-only, explicitly-attached function).

### 21.1 CapabilityResolver reference-runtime validation cases (from DocuMind evidence)

These are **test scenarios for a future reference CapabilityResolver implementation**, not a specification change and not code to extract now — the resolver itself does not exist yet (§0). Each scenario distinguishes **declared fallback** (an explicitly modeled, policy-visible degradation the resolver is allowed to select per SPEC C-04: "a fallback MUST have declared acceptable behavior and remain within all effective constraints") from **silent fallback** (an undeclared, invisible substitution — forbidden by C-04 regardless of whether the substitute happens to work).

| # | DocuMind evidence | Resolver scenario to validate | Declared vs. silent in DocuMind today |
|---|---|---|---|
| 1 | Groq chat-completion provider absent (`Groq:ApiKey` unset) → falls back to local Ollama chat model | Given a `model.chat-completion` requirement with a preferred remote provider offer and an eligible local-provider offer, when the preferred offer is unavailable, resolution MUST select the eligible alternative only if the caller's requirement explicitly permits degradation (e.g., an accepted quality/latency trade-off), and MUST record which offer was actually bound and why | **Declared in spirit, silent in mechanism**: the choice is made once at DI-composition time in C#, with no runtime-visible resolution record, no requirement object stating the acceptable degradation, and no per-request explanation of which provider served a given answer — i.e., DocuMind's *outcome* matches C-04's intent but its *mechanism* has no CapabilityResolution artifact, so it cannot itself be cited as a conformant resolver implementation |
| 2 | Cohere reranker absent (`Cohere:ApiKey` unset) → `NoOpReranker` (identity/truncation, not real reranking) | Resolution of an *optional* `retrieval.rerank` requirement with zero eligible providers MUST succeed with the requirement explicitly recorded as omitted (SPEC C-03: "optional requirements MAY be omitted with explicit reasons and resulting degradation"), not silently vanish from the caller's view | Same gap as #1 — DocuMind's behavior (skip reranking, return top-N as-is) is the *correct* shape for an optional requirement, but there is no `CapabilityResolution` record stating "rerank omitted, reason: no eligible provider" |
| 3 | Tavily web-search tool absent (`WebSearch:TavilyApiKey` unset) → `NoOpWebSearchService`, and the tool is never attached to the Answering agent at all in that case | Resolution of an optional `tool.web-search` dependency of a composite capability MUST propagate the omission to the composite's own advertised guarantees (SPEC §4.4 CompositeCapability: "MUST NOT hide provider coupling... define... failure/degradation behavior") — i.e., an Answering capability without web search MUST be able to state that its grounding guarantee is now narrower | DocuMind's MAF version already does this at the code level (the tool is conditionally attached) but the narrowed guarantee is not a caller-visible, resolvable fact — it is an implementation detail baked into DI wiring |
| 4 | Gemini voice/image-generation absent → `NoOpVoiceService`/`NoOpImageGenerationService`, both of which **throw** rather than degrade | Resolution MUST distinguish "capability unavailable, caller informed before invocation" from "capability nominally resolved, then fails at invocation time" — a `NoOp` implementation that throws on use is evidence that DocuMind conflates *resolution-time* unavailability with *invocation-time* failure; a conformant resolver must surface `CapabilityUnavailable` at resolution, not defer to a runtime `ModelFailure`/`ToolFailure` masquerading as a successful binding | **Silent** in the sense that matters: DocuMind reports success at DI-registration time and only fails when a request actually needs the missing feature, which is exactly the deferred-failure shape SPEC §7.2 step 8 and C-04 are designed to prevent at the resolution boundary |

These four scenarios should become literal `tests/contracts/capability_resolution/*` conformance cases once `legoai.capabilities`/`legoai.reference.resolution` exist (ADR-002 §7.1/§7.2) — they are recorded here so that work is not rediscovered from scratch later.

---

## 22. Risks and mitigations

| Risk | Mitigation |
|---|---|
| **Framework leakage** — accidentally shaping LegoAI's `ModelPort`/`ToolPort` contracts around SK or MAF-specific concepts | Both frameworks are proven, by this evidence, to be thin wrappers around a handful of provider calls (chat completion, embeddings, one tool-call mechanism). Design contracts against the *provider-level* behavior (Ollama/Groq/Cohere semantics), not the C# wrapper shapes; treat SK/MAF as optional future Adapters only. |
| **DocuMind-specific leakage** — citation formatting, LaTeX cleanup, prompt wording bleeding into canonical contracts | Keep these in DocuMind (§8); LegoAI's `AnsweringCapability` contract should specify citation *structure* (ordered list, chunk reference) without prescribing exact prompt text or output formatting rules. |
| **C#/Python semantic divergence** — porting behavior that was never actually tested in C# (retrieval, rerank, embedding, answering) | Write conformance specifications *before* porting untested capabilities (§20); do not assume the C# source is a correct oracle where no test exists. |
| **Duplicate runtime development** — building a parallel, redundant .NET reference runtime | Explicitly deferred (§17); ADR-001 already settles this — Python is the sole reference runtime for now. |
| **Circular dependencies** — capability contracts accidentally depending on each other cyclically | §18's dependency graph is acyclic by construction; re-verify with `tests/architecture/test_import_boundaries.py`-style checks once Python packages exist. |
| **Big-bang migration** — attempting to port the whole RAG pipeline at once | §23 phases work capability-by-capability, starting with the zero-dependency `ChunkingCapability`. |
| **Test loss** — losing the only existing behavioral oracle (ChunkingService tests) during translation | Port the test *cases*, not the test code, into the Python conformance suite as the first artifact, before writing the Python implementation (test-first against the known oracle). |
| **Provider SDK leakage** — Ollama/Cohere/Postgres specifics leaking into canonical capability contracts | §16 contracts are written in terms of capability behavior (embed text → vector; rank candidates → reordered list), not provider APIs; provider specifics belong exclusively in Adapters. |
| **Agent-framework dependency** — accidentally making LegoAI's Execution Plane assume an Agent is required for answering | §16.5 explicitly requires `AnsweringCapability` to be satisfiable via Direct invocation alone, per direct SK evidence that this already works in production. |
| **Premature generic abstraction** — over-generalizing `DocumentClassificationCapability`/`StructuredExtractionCapability` from single-repo (MAF-only) evidence | Both are explicitly deprioritized (§6, §15) pending either a second implementation or real cross-application demand; flagged UNCERTAIN rather than committed as CORE_REUSABLE. |
| **Performance regression** — Python reimplementation of hybrid SQL retrieval being slower than the tuned raw-SQL C# version | Preserve the RRF SQL strategy itself (it is a database-level algorithm, not a C#-specific one) in the Python Adapter; benchmark against the existing Postgres queries as a baseline during conformance testing. |
| **Security regression** — a permissive default retrieval/tool implementation weakening tenant isolation | Apply SPEC S-11/SECURITY §18 filtering requirements to `RetrieverCapability`'s contract explicitly (§16.3), even though DocuMind's own conversation-scoping is narrower than full tenancy. |
| **Tenant-context loss / Artifact-provenance loss** | §16 contracts explicitly require tenant propagation and model-identity provenance recording, closing the minor gaps noted in DocuMind itself (§21) rather than reproducing them in LegoAI. |
| **Logging/evidence regression** | Same as above — provenance requirements are stated as first-class parts of each capability contract, not left implicit as they are in DocuMind's current code. |
| **Client-declared, unverified content-type driving silent data corruption** (found during Batch 2's `DocumentParsingCapability` design — see `DOCUMENT-PARSING-CAPABILITY-DESIGN.md` §12) — both DocuMind repos select a parser purely by an unverified, client-supplied content-type string; because `.NET`'s default UTF-8 decoder uses replacement-character fallback rather than throwing, a mislabeled binary file parsed as text produces silently corrupted (not erroring) output that flows unremarked through the rest of the pipeline | `document.parsing` v1 formalizes format selection into a closed `DocumentFormat` enum resolved by the caller (removing the "unrecognized string silently matches nothing" failure mode) but does not attempt content sniffing; the residual "wrong-but-recognized format" risk is carried forward explicitly rather than silently inherited, and content-sniffing is noted as a plausible low-cost future hardening. |
| **First runtime dependency entering `legoai-document`** — Batch 1 shipped with zero runtime dependencies; `DocumentParsingCapability`'s PDF path will need a Python PDF library, changing that status | Evaluated deliberately in `DOCUMENT-PARSING-CAPABILITY-DESIGN.md` §17 (license, maintenance, native-dependency consequences); `pypdf` (BSD-3-Clause, pure Python) is recommended over `PyMuPDF` (AGPL-3.0, native dependency) specifically to avoid introducing copyleft-licensing or native-build-toolchain risk into a capability pack meant to be freely composed into arbitrary future applications. Not yet added — implementation-batch decision, not made in this design pass. |

---

## 23. Phased migration plan

**Phase 0 — Repository inventory (COMPLETE, this document).** Entry: none. Exit: this assessment accepted/reviewed.

**Phase 1 — Semantic comparison (COMPLETE, §3–7 above).** Exit: crosswalk table and duplication ranking produced.

**Phase 2 — Extraction classification (COMPLETE, §6).** Exit: every component has exactly one classification.

**Phase 3 — Capability contract definitions.** Files: the companion design artifact [`planning/documind/CHUNKING-CAPABILITY-DESIGN.md`](documind/CHUNKING-CAPABILITY-DESIGN.md) (created this pass) completes this phase for `document.chunking`. Changes: this is a PROPOSED Document-Pack-scoped design document, explicitly **not** a modification to canonical `contracts/CONTRACTS.md` (§0 of that document restates the Core/Document-Pack boundary). A later contract document for `EmbeddingCapability` follows the same pattern once Phase 5 for Chunking is complete. Exit: contract text reviewed against SPEC §2 shared semantic rules — done for Chunking in the companion document's design gate (§10 there).

**Phase 4 — First C# Adapter wrapping.** **Not applicable in the near term** (§17) — no Execution/Plugin engine exists to host an Adapter yet, and no accepted ADR authorizes .NET interop in the Python reference runtime. Skip until Gate 2+ and until intent §39's future .NET compatibility path is separately authorized by an ADR.

**Phase 5 — LegoAI capability extraction (Python), step 1: Chunking.** Entry: Phase 3 contract reviewed (companion document); package placement resolved (§17 — `legoai_document`, its own import root per ADR-002 §13, not a 13th `legoai.*` owner package). Files: new `legoai_document` package. Changes: implement `ChunkingCapability` as a pure Python function/dataclass pair. Tests: port the existing xUnit `ChunkingServiceTests` cases into the Python conformance suite first, then implement to satisfy them. Exit: full mypy/Ruff/pytest conformance per the same bar `src/legoai/kernel` already meets. Rollback: the capability is additive and has zero consumers yet — deletion is a clean rollback.

**Phase 6 — Python implementation of remaining capabilities, in the revised §15 order.** Step 2: `DocumentParsingCapability`. Step 3: `EmbeddingCapability` (the SK-Adapter/MAF-Adapter duality proof point). Step 4: `RetrieverCapability`. Step 5: `RerankCapability`. Step 6: `IngestionWorkflow` (composition of steps 1–3; the last purely deterministic milestone). Each step writes a conformance spec first since no C# oracle tests exist for any of these beyond Chunking (§20).

**Phase 7 — Cross-language conformance.** Only relevant once/if a future .NET Adapter is authorized; until then, "cross-language" reduces to "conformance between the C#-observed behavior (as documented, not as tested) and the Python implementation," tracked via the conformance specs written in Phase 6.

**Phase 8 — DocuMind migration.** Not authorized by this assessment. If pursued later, DocuMind would consume LegoAI's Python Document Pack only if DocuMind itself moves toward Python or LegoAI grows a .NET-consumable interface — neither is in scope now. DocuMind's C# repos remain independent products; this whole assessment treats them as read-only evidence sources, never as migration targets.

**Phase 9 — Step 7: `AnsweringCapability`.** Deliberately last, per §15's revised sequence — the only genuinely probabilistic capability in the pack, requiring an Execution Plane Direct-invocation driver to exist (not yet built — this is itself a LegoAI Core milestone independent of DocuMind) plus Phase 6's `RetrieverCapability`/`RerankCapability`.

**Phase 10 — Framework-specific cleanup.** Not applicable — no framework-specific code has been introduced into LegoAI by this plan (§17 explicitly avoids SK/MAF Adapters in the near term).

---

## 24. Recommended first migration batch (full detail per §28 of the governing prompt)

**Capability:** `ChunkingCapability`

- **Source repository:** both `DocuMind-SK` and `DocuMind-AgentFramework` (used jointly as dual oracles — the implementations are behaviorally identical)
- **Source projects:** `src/DocuMind.Core` (implementation), `src/DocuMind.Domain` (interface `IChunkingService`), `tests/DocuMind.Tests` (oracle tests)
- **Source files:**
  - `DocuMind-SK/src/DocuMind.Core/Services/ChunkingService.cs`
  - `DocuMind-SK/src/DocuMind.Domain/Interfaces/IChunkingService.cs`
  - `DocuMind-SK/tests/DocuMind.Tests/ChunkingServiceTests.cs`
  - `DocuMind-AgentFramework/src/DocuMind.Core/Services/ChunkingService.cs` (cross-check oracle — confirm identical behavior before finalizing the Python conformance spec)
  - `DocuMind-AgentFramework/tests/DocuMind.Tests/ChunkingServiceTests.cs` (cross-check oracle)
- **Source classes:** `ChunkingService : IChunkingService`, method `Chunk(Guid documentId, string fullText, int chunkSize = 512, int overlap = 50)`
- **Dependencies:** none (pure function over strings and primitives; only a `DocumentChunk` result shape depends on `DocuMind.Domain.Entities`)
- **Current tests:** 6 xUnit cases per repo (empty text → empty list; short text → single chunk with correct index/token-count; long text → multiple non-blank chunks; overlap correctness — consecutive chunks share overlapping words; DocumentId propagated to every chunk; sequential chunk indexing)
- **Proposed LegoAI contract:** §16.1 above and the full companion design ([`CHUNKING-CAPABILITY-DESIGN.md`](documind/CHUNKING-CAPABILITY-DESIGN.md)) — semantic identity `document.chunking`, namespace `legoai_document` (its own import root; **not** `legoai.document`, since `legoai.*` is reserved for ADR-002 §5's twelve canonical Core owner groups and Chunking is not one of them — see §17's revised target architecture)
- **Proposed Adapter boundary:** none needed for v1 — this is a pure computation capability with no external provider; a "Provider" in LegoAI's sense here is just the reference implementation itself (self-contained, no `Adapter` layer required, matching SPEC §4.4's allowance for direct capability use without inventing infrastructure that isn't needed)
- **Target location:** **resolved** — a new, separate `legoai_document` import root/distribution, sibling to (not nested inside) `legoai`, per ADR-002 §13's already-accepted "future integration distributions use their own import roots" mechanism. This required no new ADR; full evaluation of the three placement options is in the companion design document's package-placement section.
- **Python target:** a pure module exposing a function (or a small `Protocol`+implementation pair, consistent with `src/legoai/kernel`'s existing style of dataclasses/enums/Protocols per the Gate-1 tooling table) implementing sliding-window chunking with explicit `chunk_size`/`overlap` parameters and no hidden defaults beyond what the contract declares — see the companion document's Python API shape section for the exact proposed signature
- **New tests:** direct ports of the 6 xUnit cases above, expressed as pytest cases, run against both the Python implementation and (manually, once) cross-checked against the two C# implementations' actual output for a shared sample document to confirm behavioral parity before declaring the Python version conformant — see the companion document's full characterization table, including behaviors the existing C# tests do **not** cover
- **Migration order:** first — zero dependencies, existing oracle tests, lowest risk of all candidates identified in the revised §15 sequence
- **Rollback method:** the new package is purely additive with no consumers anywhere in the repository (Gate 1 has no Document Pack yet, and `legoai_document` is a separate import root that `legoai.*` never imports); rollback is simply removing the new package and its tests — no other code changes are entangled with it

---

## Completion

Per §26/§31 of the governing prompt, no source has been modified, no files moved, no adapters created, no C# translated, and no DocuMind or LegoAI canonical documents changed. Only this assessment file was written.
