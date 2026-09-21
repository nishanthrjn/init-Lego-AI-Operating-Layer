# Chunking Capability — Implementation Design

**Document:** `planning/documind/CHUNKING-CAPABILITY-DESIGN.md`
**Status:** PROPOSED — IMPLEMENTATION DESIGN
**This is NOT a canonical LegoAI Core specification.** It defines a single proposed reusable **Document Capability Pack** capability, derived from DocuMind evidence, subordinate to and constrained by (but not amending) `intent.md`, `SPEC.md`, `ARCHITECTURE.md`, `CONTRACTS.md`, and ADR-001/002.
**Parent document:** [`planning/DOCUMIND-EXTRACTION-ASSESSMENT.md`](../DOCUMIND-EXTRACTION-ASSESSMENT.md) §16.1, §24
**Source evidence:** `DocuMind-SK/src/DocuMind.Core/Services/ChunkingService.cs`, `DocuMind-SK/tests/DocuMind.Tests/ChunkingServiceTests.cs`, `DocuMind-AgentFramework/src/DocuMind.Core/Services/ChunkingService.cs`, `DocuMind-AgentFramework/tests/DocuMind.Tests/ChunkingServiceTests.cs` — all four files read directly for this design (not summarized secondhand); the SK and MAF implementations are **byte-for-byte identical**, as are their test suites.

---

## 0. Canonical boundary this document respects

```text
Canonical LegoAI Core contracts  (contracts/CONTRACTS.md — ACCEPTED, technology-neutral, applies to every application)
        ≠
Document Capability Pack contracts  (this document — PROPOSED, applies only to document-processing applications)
```

`document.chunking` is a Document Capability Pack concern. Nothing in this document is added to, or implied to amend, `contracts/CONTRACTS.md`, `SPEC.md`, or any accepted ADR. The capability is designed to be **usable by** a future LegoAI application (via Core's canonical Capability/Port/Execution mechanisms once they exist) without being **part of** Core. Promotion to Core would require an independent, non-document consumer demonstrating the same abstraction is universally needed — no such evidence exists today (only two document-processing applications have been inspected, and both need it for the same reason).

---

## 1. Identity

**Proposed semantic identity:** `document.chunking`

This is retained from the parent assessment rather than replaced. Alternatives considered and rejected:

- `text.chunking` — rejected: too broad: the current evidence (word-based sliding window over already-extracted plain text) is specifically a *document-processing* concern, not a generic text-utility concern; naming it generically would invite premature Core promotion before independent evidence exists.
- `document.split` / `document.segment` — rejected: "chunking" is already the term both DocuMind implementations, their tests, and the interface (`IChunkingService`, `ChunkingService.Chunk`) use consistently; changing vocabulary without a reason adds translation cost for zero benefit.
- `document.chunking.sliding_window` — rejected for the *capability* identity (over-specifies the algorithm inside the name, which belongs in versioning — see §11 — not identity), but the fact is preserved as the initial `CapabilityVersion`'s documented algorithm.

**Namespace / import root:** `legoai_document` (see §"Package placement" below) — **not** `legoai.document`.

---

## Package placement

Evaluated per ADR-002 (package structure) and the current repository state.

### Options evaluated

**Option A — `src/legoai/document/`** (a 13th sibling package under the `legoai` import namespace, alongside `kernel`, `application`, `capabilities`, `execution`, `tools`, `governance`, `resources`, `plugins`, `observability`, `evidence`, `runtime`, `reference`)

Rejected. ADR-002 §5 states: *"There are 12 initial direct-child package groups under `legoai`... `kernel`, `application`, `capabilities`, `execution`, `tools`, `governance`, `resources`, `plugins`, `observability`, `evidence`, `runtime`, and `reference`."* Every one of these maps 1:1 to a canonical logical owner already named in `ARCHITECTURE.md`'s plane structure and `SPEC.md`'s concept catalog. `document.chunking` is not a canonical SPEC concept — no `Document`, `Chunk`, or `DocumentChunk` concept exists anywhere in SPEC's concept catalog (§4). Placing it under `legoai.*` would misrepresent a document-processing application capability as a 13th canonical Core owner, blurring exactly the boundary §0 above exists to keep sharp, and would contradict ADR-002 §7.1's closing rule: *"Permissions below are exhaustive when combined with §9: omitted dependencies are forbidden."* ADR-002's reserved-future-locations table (§7.3) also confirms this: it lists `legoai.coordination`, `legoai.execution.workflow/agent/participation`, `legoai.intelligence.model/skill`, `legoai.information.context/memory/knowledge/retrieval`, `legoai.artifacts`, `legoai.events`, `legoai.evaluation`, `legoai.conformance` — every one of these is a direct realization of an ARCHITECTURE.md plane. There is no reserved `legoai.document` (or any "capability pack") location anywhere in that table. Its absence is not an oversight to fix by adding one; it reflects that capability packs are architecturally a different kind of thing than canonical owners, per §13 below.

**Option B — a separate `legoai-document` distribution/package**

Selected, with one refinement: ADR-002 §13 explicitly already defines this mechanism, so this is not a new decision invented here — it is the *application* of an existing one. Quoting ADR-002 §13 directly: *"Future integration distributions use their own import roots and contain their Adapter and owning Plugin declaration. They depend on documented Lego AI Ports/SPI, not `legoai.reference`. A future first-party optional module can be isolated from base imports, but its dependency/install strategy must be explicit."* A Document Capability Pack is precisely this kind of "future integration distribution" — it is first-party (written by the same maintainer), optional (a non-document LegoAI application need not install it), and it must depend only on Core's *public* contracts, never on `legoai.reference` internals.

**Option C — another ADR-002-consistent extension mechanism already defined by the repository**

This is the same answer as B, restated: ADR-002 §13's "future integration distribution" pattern *is* the already-defined extension mechanism. There is no third, different mechanism to consider — B and C converge on one answer once ADR-002 §13 is read carefully. `legoai.reference.deterministic` (ADR-002 §7.2, "one deterministic reference CapabilityProvider/Adapter realization... exact capability chosen later") was considered and rejected as a fit: that slot is reserved for a single reference realization of an *already-canonical* Port, gated by an existing ADR ("Relevant P1 gates"), and explicitly warns against "implicit AI/coordination imports or self-admission" for exactly this kind of open-ended extension — it is not a general-purpose home for arbitrary new capability domains.

### Decision

**Placement: a new, separate import root `legoai_document` (proposed distribution name `legoai-document`), living beside — not inside — the `legoai-reference` distribution, in the same repository.**

Evaluated against the required criteria:

- **Dependency direction:** `legoai_document` MAY depend on `legoai`'s stable public contracts (`legoai.kernel`, and later `legoai.capabilities`/`legoai.execution` once they exist and once this pack needs them). `legoai.*` (Core) MUST NOT and does not depend on `legoai_document` — satisfied trivially today since nothing in `legoai_document` exists yet and Core has no reason to reference a document-specific package.
- **Optionality:** a LegoAI application with no document-processing need never installs `legoai_document`. Satisfied by construction — separate distribution, separate install.
- **Independent consumability:** `legoai_document.chunking` is usable standalone (see §5, Effects — it needs nothing else at all). Satisfied.
- **Package/distribution overhead:** for a single pure function, a full second PyPI-style distribution is more packaging ceremony than the capability currently justifies. This is accepted as a **known, bounded cost**, not ignored: the repository can start `legoai_document` as a second `src/`-layout package in the *same* repository/workspace (no separate git repo, no separate CI pipeline, no separate release cadence required on day one — ADR-002 §13 explicitly states "no extras syntax, workspace manager or build tool is selected here," leaving this open). The distribution boundary matters for *import-root separation and dependency-direction enforcement*, not for operational overhead; a solo developer can develop both packages in one editable checkout.
- **Solo-developer complexity:** minimized by deferring all packaging-mechanics decisions (single distribution with two top-level import packages vs. two distributions vs. a monorepo with two `pyproject.toml`s) to whenever `legoai_document` actually needs its own dependency set (e.g., a PDF-parsing library) that Core's base install must never pull in — which is not yet, since Chunking has zero dependencies.
- **Future capability packs (vision/video/3D):** this decision generalizes cleanly — each becomes its own sibling import root (`legoai_vision`, `legoai_video`, etc.), never a subpackage of `legoai.*`, following the same ADR-002 §13 mechanism. This was a deciding factor: Option A would need to be revisited for every future pack; Option B/C's answer does not.
- **Installing Core does not install Document dependencies:** satisfied by construction — Chunking has zero dependencies today, and even a future document-parsing library (e.g., a PDF library) would live only in `legoai_document`'s own dependency closure, never Core's, matching ADR-002 §13's mandatory exclusion: *"The base distribution's dependency closure MUST exclude AI frameworks, Model SDKs, external Workflow engines, vector/database drivers, MCP libraries and observation backends."*
- **Document Pack depends inward on Core; Core never depends outward on it:** satisfied — see dependency direction above.

**Is a new ADR required? No.** ADR-002 §13 already authorizes exactly this pattern for exactly this situation ("future integration distributions use their own import roots... depend on documented Lego AI Ports/SPI, not `legoai.reference`"). No accepted ADR is contradicted; ADR-002 is not reopened. This is recorded here as **a small implementation decision applying an already-accepted mechanism**, consistent with AGENTS.md's instruction that "significant architecture decisions require an ADR" — this is not one, because the architecture decision (how first-party extensions are isolated from Core) was already made in ADR-002 §13.

---

## 2. Inputs

Derived strictly from the actual C# signature — `Chunk(Guid documentId, string fullText, int chunkSize = 512, int overlap = 50)` — with one deliberate change explained in §9 (document identity is **not** part of the pure capability's input; see below).

| Input | Derived from | Notes |
|---|---|---|
| `text` | `fullText` parameter | The full extracted document text to be split. Required. |
| `chunk_size` | `chunkSize` parameter, default `512` | Measured in **words**, not tokens (see §11 — this is a versioning-relevant fact, not an implementation detail). Both C# repos use word-count, not any real tokenizer. |
| `overlap` | `overlap` parameter, default `50` | Measured in the same unit as `chunk_size` (words). |

**Not carried into the capability's input:** `documentId`. In the C# code this exists purely to stamp every output `DocumentChunk.DocumentId` with the caller-supplied value — it plays no role in the chunking computation itself (the algorithm never reads it). Per the entity-separation requirement (§9), correlating chunks back to a source document is the **caller's** responsibility (e.g., the future `IngestionWorkflow`), not part of this capability's semantic contract. No speculative input parameters have been added beyond what the C# behavior and tests demonstrate.

---

## 3. Outputs

The C# code conflates three things in one `DocumentChunk` class: the pure computation's result, the EF Core persistence entity, and (implicitly) the unit of content a caller might later store as an Artifact. This design explicitly separates them, per §9's requirement.

### 3.1 Capability semantic result (this document's concern)

A `ChunkingResult` is an ordered sequence of `Chunk` values. Each `Chunk` carries exactly what the pure algorithm computes and nothing the caller must supply after the fact:

| Field | Source | Notes |
|---|---|---|
| `index` | `ChunkIndex` in C# | Zero-based, sequential, gapless (proven by the `Chunk_ChunkIndexesAreSequential` test in both repos). |
| `content` | `Content` in C# | The joined word-slice text. |
| `word_count` | `TokenCount` in C# | Deliberately renamed — see §11: the C# name `TokenCount` is misleading, since it is a plain word count, not an LLM-tokenizer token count. Preserving the misleading name in a new language-neutral contract would import a naming defect, not a behavioral one; the *value* (word count of the slice) is preserved exactly, only the label is corrected. |

**Not included:** `Id` (a persistence-only surrogate key — see §3.2), `DocumentId` (caller's correlation concern — see §9), `CreatedAt` (a persistence timestamp, not a fact about the chunking computation — see §3.2), `PageNumber` (present as an always-`null` field on the C# entity because neither DocuMind repo's `ChunkingService` ever populates it — the current algorithm operates over already-flattened, page-boundary-erased text; there is no page information available to attach at this stage of either pipeline. Omitted here rather than carried forward as a permanently-null placeholder field, per the instruction not to copy the C# structure blindly).

### 3.2 Persisted document-chunk entity (NOT this capability's concern)

A future `IngestionWorkflow` or persistence Adapter is responsible for taking a `ChunkingResult` and producing whatever row/record shape its storage Adapter needs (a surrogate ID, the owning document's identity, a creation timestamp, and — if the parsing stage that precedes chunking in a future pipeline is page-aware — a page number attached by that stage, not by Chunking). This capability has no opinion on primary keys, foreign keys, or storage schema.

### 3.3 Artifact representation (NOT this capability's concern)

Per SPEC §4.8, an Artifact/ArtifactVersion would be the right representation if a caller chooses to preserve a chunk set as a durable, versioned work product. Whether and how a `ChunkingResult` becomes an ArtifactVersion is an orchestration decision made by whatever composes this capability (a future `IngestionWorkflow`), not a concern of the pure capability itself, consistent with SPEC §4.4's allowance for capability use without inventing Artifact machinery that a given call does not need.

---

## 4. Validation

Each case below states the **actual current C# behavior** (verified by direct source reading, both repos, byte-identical) and whether it is test-covered.

| Case | Current C# behavior (verified from source) | Test-covered? | Decision for the Python capability |
|---|---|---|---|
| Empty string (`""`) | `string.IsNullOrWhiteSpace` guard → returns empty list | Yes (`Chunk_EmptyText_ReturnsEmptyList`, both repos) | **Decided**: empty input → empty result, no error. |
| Whitespace-only content (e.g. `"   "`, `"\n\n"`) | Same guard (`IsNullOrWhiteSpace` covers this identically to empty) → empty list | No test uses literal whitespace-only input, but the guard condition unambiguously covers it | **Decided by source, not independently tested** — same behavior as empty. A characterization test should be added to make this explicit rather than relying on an inference from the guard's name. |
| `chunk_size <= 0` | **Not guarded.** `chunk_size == 0`: first slice is empty (`words[index..index]`), an empty chunk is emitted, then `index` becomes negative on the next iteration and slicing with a negative computed bound throws `ArgumentOutOfRangeException` in .NET's range-indexer. `chunk_size < 0`: throws immediately on the first slice (`Math.Min(index + chunkSize, length)` is negative, and a negative computed range bound is invalid). | No test exercises this | **UNDECIDED — REQUIRES CHARACTERIZATION.** The C# behavior here is not a considered design (it is an unguarded crash), so it is not being treated as an authoritative oracle for this case. A `ValidationError` at the capability boundary is the SPEC-consistent recommendation (SPEC §10 canonical error model), but this is a recommendation for the eventual characterization decision, not something silently adopted as already-decided in this document. |
| `overlap < 0` | **Not guarded.** `index += chunk_size - overlap` becomes `chunk_size + abs(overlap)`, i.e., a larger forward step than `chunk_size` — words between the end of one slice and the start of the next are silently skipped and never appear in any chunk. No exception; the function returns a result, just an incomplete one. | No test exercises this | **UNDECIDED — REQUIRES CHARACTERIZATION.** This is a silent-coverage-gap defect in the oracle (SPEC C-04's anti-silent-degradation principle applies to capability *resolution*, but the same spirit argues against silently dropping input content without signaling it). Recommend `ValidationError`, but explicitly not adopted as decided behavior here. |
| `overlap >= chunk_size` | **Not guarded.** `index += chunk_size - overlap` is `≤ 0`, so `index` never advances past its current position (or moves backward). The `while (index < words.Length)` loop **never terminates** for any non-empty input — this is an unbounded-loop defect in both C# implementations. | No test exercises this | **UNDECIDED — REQUIRES CHARACTERIZATION**, with an explicit flag: this is a genuine defect in the oracle, not a behavior to preserve. The Python capability MUST NOT reproduce an infinite loop; recommend rejecting with `ValidationError` when `overlap >= chunk_size`, subject to a deliberate characterization decision before implementation, not silently invented as final here. |
| Unicode text (e.g. CJK characters, combining diacritics, emoji) | The word-splitting is `fullText.Split(' ', StringSplitOptions.RemoveEmptyEntries)` — splitting **only on the single ASCII space character U+0020**, not general Unicode whitespace. Non-breaking space (U+00A0), ideographic space (U+3000), tabs, and newlines are **not** split points and remain glued to whichever token they are adjacent to. Multi-byte/combining Unicode sequences inside a "word" are preserved intact since .NET string slicing operates on the already-split array elements, not on raw byte offsets. | No test uses non-ASCII or non-space-whitespace input | **Decided by source, characterization required to confirm exact parity.** This is a subtle, easy-to-get-wrong porting hazard: a naive Python port using `text.split()` (which splits on *any* Unicode whitespace) would silently diverge from the C# oracle for any input containing tabs, newlines, or non-ASCII spaces. The Python implementation MUST use an ASCII-space-only split (e.g. `text.split(" ")` with empty-string filtering, matching `RemoveEmptyEntries`) to preserve behavioral parity, not `text.split()`. This is flagged explicitly rather than "fixed," because changing it would be an undocumented behavior change relative to the oracle, not a bug fix within this capability's current scope. |
| Very large input (e.g. a multi-megabyte document) | No explicit handling; the algorithm is a single pass building an array and a list, O(n) in words for both time and memory. No chunking or streaming of the input itself. | No test exercises this | **Not characterized.** No performance threshold is invented here (see §12) — only a benchmark input size is proposed for future measurement. |

---

## 5. Determinism

The capability MUST be **fully deterministic**: identical `(text, chunk_size, overlap)` inputs MUST always produce identical, order-stable output. This is directly evidenced by the C# algorithm containing no randomness, no wall-clock dependency in its *computation* (the C# entity's `CreatedAt = DateTime.UtcNow` is a persistence-stamping side effect on the *entity*, never inspected as part of the chunking computation's correctness, and is excluded from this capability's output per §3.1/§3.2), and no external I/O. Determinism is a **required property of every `CapabilityVersion`** of `document.chunking` — any future variant (e.g., a sentence-aware or token-aware chunker) that introduces non-determinism (e.g., a model-based boundary detector with sampling) would need a different documented determinism guarantee, which is itself a versioning-relevant fact (§11).

---

## 6. Effects

Confirmed directly from the C# source and this design's scope:

- **Pure:** yes — output depends only on declared inputs.
- **Stateless:** yes — no instance fields, no shared mutable state (`ChunkingService` in C# holds no fields at all).
- **Effect-free:** yes — no I/O, no logging required for correctness, no network calls.
- **No provider required:** yes — confirmed in the parent assessment (§16.1); this is why no Adapter is proposed (below).
- **No Adapter required:** yes — there is nothing to adapt to; a "Provider" in LegoAI's sense would only be meaningful if there were multiple substitutable realizations behind a Port, and the current, sole realization is the algorithm itself.
- **No persistence required:** yes — see §3, persistence is explicitly out of scope for this capability.

---

## 7. Tenant / security

Per SPEC S-10, every operational entity has exactly one tenant scope, and this MUST NOT be forced into a pure function's signature as a speculative parameter. The resolution used here: **`document.chunking` itself carries no `TenantContext` parameter.** Tenant scoping is a property of the surrounding `Execution`/`ExecutionContext` (SPEC §4.6) that invokes this capability, not of the capability's pure computation — a chunking algorithm applied to a string cannot violate tenant isolation on its own, because it neither reads nor writes any tenant-scoped store. The caller (a future direct-invocation `Execution` or `IngestionWorkflow` step) is responsible for ensuring the `text` it passes in was itself retrieved under proper tenant authorization, and for tagging any *persisted* result with the correct tenant scope at the point persistence actually happens (§3.2) — this capability sits entirely upstream of that boundary. This keeps the capability genuinely reusable (SPEC I-01's replaceability test: nothing about "chunk this string" logically requires knowing whose tenant it belongs to) without weakening SPEC S-10/S-11, since no cross-tenant disclosure or storage occurs inside the capability at all.

---

## 8. Provenance

Per SPEC S-12/§4.11, the question is which facts belong to the **caller/execution envelope** versus the **algorithm itself**:

- **Belongs to the Execution envelope (caller's responsibility), not this capability:** which document produced the input text, which document revision, who/what requested the chunking, when it was requested, which downstream Artifact (if any) the result became part of.
- **Belongs to the capability's own contract (this document's responsibility):** the exact `CapabilityVersion` used (§11) — because different versions may chunk the same text differently (e.g., word-count vs. token-count semantics), so *which version ran* is itself a provenance-relevant fact that only the capability can state authoritatively, and MUST be recorded by the caller alongside its own execution provenance.

This capability produces no provenance record of its own; it returns a result and lets its `CapabilityVersion` identity be recorded by whatever `Execution` invoked it, consistent with SPEC E-07 ("Completion MUST preserve operational result, produced ArtifactVersion references... resource accounting") being an `Execution`-level obligation, not an obligation invented redundantly inside every pure capability.

---

## 9. Versioning

Per SPEC §11 (V-01 through V-09), a breaking change to a `CapabilityVersion` is one that changes valid inputs, weakens guarantees, or alters observable behavior incompatibly. Evaluated against the concrete examples the design brief raised:

| Candidate change | Would it require a new `CapabilityVersion`? | Reasoning |
|---|---|---|
| **Tokenization method** (word-count → real LLM-tokenizer token count) | **Yes — new major version.** | Changes the meaning of `chunk_size`/`overlap`/`word_count` (renamed `token_count` under a real tokenizer) and changes chunk boundaries for the same input text. Output for identical input would differ. This is exactly the kind of change SPEC V-03 calls breaking: "broadening outputs beyond the existing consumer contract" / "changing... semantics incompatibly." |
| **Chunk-size semantics** (word-count window → character-count window) | **Yes — new major version.** | Same reasoning — changes what `chunk_size` measures and therefore changes every chunk boundary for existing inputs. |
| **Overlap semantics** (word-count overlap → percentage-based overlap) | **Yes — new major version.** | Same reasoning. |
| **Sentence-aware boundaries** (never split mid-sentence, even if it changes chunk length) | **Yes — new major version** (or a distinct sibling capability, not merely a version bump — see §13). | This is a fundamentally different guarantee (boundary respects sentence structure vs. pure word count) that would produce different, non-comparable output for the same input. |
| **Word-vs-token counting for the *reported* `word_count` field only, with chunk boundaries unchanged** | **Minor version at most, likely not even that — should be resolved by simply choosing the correct field name up front (§3.1 already does this: `word_count`, not `TokenCount`), not by future version churn.** | If chunk boundaries themselves don't change, only the label/meaning of a reported metadata field changes — but this should be settled correctly in the *first* version rather than deferred, which §3.1 does. |
| **Bug-fix behavior for the currently-UNDECIDED validation cases (§4)** (e.g., deciding `chunk_size <= 0` raises `ValidationError`) | **Patch-level, within the first version — not a breaking change**, provided it is settled *before* the first release rather than changed after callers depend on the crash-prone behavior. | SPEC V-02: "patch for corrections that do not alter valid observable obligations" — since no valid caller could have been relying on an infinite loop or a crash as a *feature*, fixing these before v1.0.0 ships is a correction, not a breaking change. This is exactly why §4's UNDECIDED items must be resolved during implementation (§10), not deferred past the first release. |

---

## 10. Performance

**Benchmark inputs proposed (not thresholds):**

- A short document (~1 page, ~500 words) — representative of the `Chunk_ShortText_ReturnsSingleChunk` test scale.
- A medium document (~50 pages, ~25,000 words) — representative of a typical PDF report.
- A large document (~1,000 pages, ~500,000 words) — representative of the "very large input" case flagged as uncharacterized in §4.

**No performance threshold (latency, throughput, or memory ceiling) is specified here.** The C# implementation provides no benchmark evidence to derive one from (no performance test exists in either repo), and inventing a numeric SLA without evidence would violate the instruction not to fabricate requirements. A future characterization pass should *measure* the Python implementation against these three input sizes and record the results as evidence, not as a target chosen in advance.

---

## 11. Extension boundaries

The following are **explicitly out of scope** for `document.chunking` v1, to be introduced only as a separate provider, a new `CapabilityVersion`, or a distinct sibling capability if and when real evidence (a second, different consumer need) requires them — not spec­ulatively now:

- **Semantic chunking** (boundary decisions based on embedding-similarity drift) — no evidence in either DocuMind repo; both use fixed word-count windows exclusively.
- **Sentence-embedding-aware chunking** — same; no evidence.
- **LLM-based chunking** (a model deciding boundaries) — same; would also violate this capability's determinism requirement (§5) unless carefully constrained, which is itself a reason to treat it as a distinct capability rather than a mode of this one.
- **Multimodal chunking** (splitting content that mixes text with images/tables as first-class chunk members) — no evidence; both DocuMind pipelines flatten documents to plain text *before* chunking runs, and any table/image handling happens upstream in a separate parsing/vision step (§6, `DocumentParsingCapability`/vision sub-capability in the parent assessment), never inside `ChunkingService` itself in either repo.

---

## 12. Characterization test table

Built directly from reading `DocuMind-SK/tests/DocuMind.Tests/ChunkingServiceTests.cs` and `DocuMind-AgentFramework/tests/DocuMind.Tests/ChunkingServiceTests.cs` (identical files) against the source in §4 above.

| Case | Input | Parameters | Expected output properties | Covered by SK test? | Covered by MAF test? | Additional characterization required? |
|---|---|---|---|---|---|---|
| Empty text | `""` | defaults (512/50) | Empty result list | Yes (`Chunk_EmptyText_ReturnsEmptyList`) | Yes (identical test) | No |
| Short text, single chunk | 100 repeated words | `chunk_size=512` (default overlap 50) | Exactly one chunk; `index == 0`; `word_count == 100` | Yes (`Chunk_ShortText_ReturnsSingleChunk`) | Yes | No |
| Long text, multiple chunks | 1000 repeated words | `chunk_size=100, overlap=10` | More than one chunk; no chunk has blank/whitespace-only content | Yes (`Chunk_LongText_ProducesMultipleChunks`) | Yes | No |
| Overlap correctness | 200 uniquely-numbered words (`word1`…`word200`) | `chunk_size=100, overlap=20` | The last 20 words of chunk 0 exactly equal the first 20 words of chunk 1 | Yes (`Chunk_WithOverlap_ConsecutiveChunksShareWords`) | Yes | No |
| Document-identity correlation | 500 repeated words, fixed `documentId` | `chunk_size=100, overlap=10` | Every chunk carries the same `documentId` | Yes (`Chunk_AllChunksHaveCorrectDocumentId`) | Yes | **Not applicable to the pure capability** — this test verifies an entity-tagging behavior this design deliberately excludes from the capability's own contract (§2, §9). The equivalent guarantee ("whatever correlation value a caller attaches, it round-trips unchanged") is trivial once the caller performs the attachment itself and needs no capability-level test. |
| Sequential chunk indexing | 500 repeated words | `chunk_size=100, overlap=10` | `index` values are exactly `0, 1, 2, ...` with no gaps | Yes (`Chunk_ChunkIndexesAreSequential`) | Yes | No |
| Whitespace-only content | e.g. `"   \n\t  "` | defaults | Empty result list (same code path as empty text) | No | No | **Yes** — add explicitly; behavior is unambiguous from source but not independently proven by an existing test. |
| `chunk_size <= 0` | any non-empty text | `chunk_size=0` or negative | **UNDECIDED** (§4) — current oracle crashes or degenerates | No | No | **Yes** — must be characterized and decided before implementation (§10 gate). |
| `overlap < 0` | any non-empty text | negative `overlap` | **UNDECIDED** (§4) — current oracle silently skips words | No | No | **Yes** — must be characterized and decided before implementation. |
| `overlap >= chunk_size` | any non-empty text | e.g. `chunk_size=50, overlap=50` | **UNDECIDED** (§4) — current oracle hangs (infinite loop defect) | No | No | **Yes** — must be characterized and decided before implementation; MUST NOT reproduce the hang. |
| Unicode / non-ASCII-whitespace text | text containing tabs, newlines, CJK characters, or U+00A0/U+3000 spaces | defaults | ASCII-space-only splitting preserved; non-space whitespace does not create a split point | No | No | **Yes** — must be added to lock in intentional parity with the oracle's actual (if surprising) behavior, specifically to prevent a well-intentioned Python port from "fixing" this with a general `.split()`. |
| Very large input | ~500,000-word document | defaults | Completes in linear time; no crash | No | No | Not required for correctness sign-off, but a benchmark measurement (§10) should be taken once implemented. |

**All existing tested behavior (6 cases) is preserved as-is** in the proposed design. **Five additional characterization cases** are identified as gaps in the existing oracle, three of which (`chunk_size<=0`, `overlap<0`, `overlap>=chunk_size`) expose genuine defects in the C# reference rather than well-defined behavior to replicate — these three block the implementation gate (§14) until explicitly decided.

---

## 13. Python API shape (proposed, not implemented)

**Comparison of the three candidate shapes**, evaluated against this capability's actual properties (pure, no I/O, no mutable state, no Adapter, no Provider, deterministic — §6):

| Shape | Fit for this capability | Verdict |
|---|---|---|
| **Pure function** | A function whose entire behavior is "map these inputs to this output" is the direct, idiomatic expression of a pure computation. No state to encapsulate, no polymorphism to express (there is exactly one realization), no lifecycle to manage. | **Selected.** |
| **Protocol + implementation** | A `Protocol` earns its keep when a Port must admit *multiple substitutable realizations* behind a stable interface (e.g., `EmbeddingCapability` behind an SK-Adapter and an MAF-Adapter — parent assessment §16.2). `document.chunking` has exactly one realization today and no Provider/Adapter concept applies at all (§6). Introducing a `Protocol` now would be exactly the "speculative abstraction" AGENTS.md and ADR-002 §11 warn against ("No generic `common`... package is allocated... Promotion to a shared primitive requires... explicit dependency review"). | Rejected for now — revisit only if/when a second, genuinely different chunking realization (§11) is actually built and needs to be swapped behind a common interface. |
| **Callable capability object** (a class with `__call__` or a `.run()` method, perhaps carrying configuration as instance state) | Would only be justified if the capability needed to hold configuration across multiple invocations, manage a resource (a connection, a loaded model), or participate in a registry/lifecycle. None of these apply — `chunk_size`/`overlap` are per-call parameters, not session-level configuration, and there is no resource to hold open. | Rejected — would introduce object lifecycle and state management for a function that has none. |

### Proposed public signature and value types (no implementation body)

```python
# legoai_document/chunking/values.py

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkingRequest:
    """Immutable input to the document.chunking capability."""
    text: str
    chunk_size: int = 512
    overlap: int = 50


@dataclass(frozen=True, slots=True)
class Chunk:
    """A single chunk produced by document.chunking. Carries no persistence
    or document-correlation fields -- see the parent design document's
    entity-separation section."""
    index: int
    content: str
    word_count: int


@dataclass(frozen=True, slots=True)
class ChunkingResult:
    """Immutable, ordered output of document.chunking."""
    chunks: tuple[Chunk, ...]


# legoai_document/chunking/api.py

def chunk_text(request: ChunkingRequest) -> ChunkingResult:
    """Split request.text into overlapping word-count windows.

    Deterministic, pure, effect-free (see design doc SS5-6).
    Raises ValidationError-equivalent for chunk_size <= 0, overlap < 0,
    or overlap >= chunk_size, pending the characterization decision in
    design doc SS4/SS12 -- exact error type is a Core-contract question,
    not decided in this pack-level document.
    """
    ...
```

No implementation body is provided, per the design-gate scope of this document. The exact exception type raised for the three UNDECIDED validation cases is deliberately left unresolved here (see §14) rather than invented.

---

## 14. Implementation gate

```text
READY_TO_IMPLEMENT_CHUNKING = NO
```

**Blockers (must all clear before flipping to YES):**

1. **Three UNDECIDED validation behaviors (§4, §12) are not yet resolved:** `chunk_size <= 0`, `overlap < 0`, and `overlap >= chunk_size`. The C# oracle's actual behavior for these cases ranges from silent data loss to an unbounded-loop defect — none of it is fit to characterize as intended behavior. A deliberate decision (recommended: raise a validation-category error for all three, consistent with SPEC §10's canonical error model) must be made and recorded — by whoever authorizes implementation — before code is written, not discovered mid-implementation.
2. **Exact exception/error type is not yet chosen.** This document deliberately stops at "a validation-category error" without picking a concrete Python exception type or committing to a specific `legoai` Core error contract dependency, since that is a Core-contract-level decision (whether `legoai_document` depends on `legoai.kernel.errors` at all, given today it needs zero Core dependencies) that should be made deliberately, not implicitly, when implementation is authorized.
3. **Packaging mechanics for `legoai_document` are not yet chosen** (single distribution with a second top-level import package vs. two separate distributions vs. some other layout) — §"Package placement" resolves the *architectural* question (separate import root, ADR-002 §13 mechanism) but explicitly defers the *mechanical* packaging choice, consistent with ADR-002 itself deferring build-tool/workspace-manager choices.

**Already resolved (not blockers):**

- Package placement is resolved (§"Package placement" — separate import root `legoai_document`, no new ADR needed).
- Capability boundary is resolved (§0, §2, §3 — Core/Document-Pack split, request/result/entity/Artifact separation).
- Existing behavior (the 6 tested cases) is fully characterized (§12).
- No accepted ADR is contradicted (§"Package placement" decision section).
- Dependency direction is valid (§"Package placement" — inward-only, Core untouched).

**Once blockers 1–3 are explicitly decided** (a short follow-up decision, not a redesign — the options are already laid out in §4 and §14 above), this gate should be re-evaluated and can reasonably flip to `YES` without further architectural work.
