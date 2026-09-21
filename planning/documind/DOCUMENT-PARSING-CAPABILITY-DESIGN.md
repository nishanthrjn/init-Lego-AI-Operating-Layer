# Document Parsing Capability — Implementation Design

**Document:** `planning/documind/DOCUMENT-PARSING-CAPABILITY-DESIGN.md`
**Status:** PROPOSED — IMPLEMENTATION DESIGN
**This is NOT a canonical LegoAI Core specification.** It defines a single proposed reusable **Document Capability Pack** capability, derived from DocuMind evidence, subordinate to and constrained by (but not amending) `intent.md`, `SPEC.md`, `ARCHITECTURE.md`, `CONTRACTS.md`, and the accepted ADRs.
**Parent documents:** [`planning/DOCUMIND-EXTRACTION-ASSESSMENT.md`](../DOCUMIND-EXTRACTION-ASSESSMENT.md), [`planning/documind/CHUNKING-CAPABILITY-DESIGN.md`](CHUNKING-CAPABILITY-DESIGN.md) (Batch 1, complete and accepted — consumed here only as a downstream API, not modified)
**Batch 1 status:** `document.chunking` remains untouched by this document.

---

## 1. Source evidence

All four source files below were read directly for this design, not summarized secondhand:

**Semantic Kernel (`DocuMind-SK`):**
- `src/DocuMind.Domain/Interfaces/IDocumentParser.cs`
- `src/DocuMind.Core/Parsers/DocumentParserDispatcher.cs`
- `src/DocuMind.Core/Parsers/PdfDocumentParser.cs`
- `src/DocuMind.Core/Parsers/PlainTextParser.cs`
- `src/DocuMind.Core/Services/IngestionService.cs` (sole caller)
- `src/DocuMind.Api/Program.cs` (`/api/documents/ingest` endpoint — the sole path bytes/content-type reach the parser from)
- `src/DocuMind.Domain/Entities/Document.cs` (persistence entity, for entity-separation analysis)

**Microsoft Agent Framework (`DocuMind-AgentFramework`):**
- `src/DocuMind.Domain/Interfaces/IDocumentParser.cs`
- `src/DocuMind.Core/Parsers/DocumentParserDispatcher.cs`
- `src/DocuMind.Core/Parsers/PdfDocumentParser.cs`
- `src/DocuMind.Core/Parsers/PlainTextParser.cs`
- `src/DocuMind.Core/Parsers/ImageDocumentParser.cs`
- `src/DocuMind.Core/Services/VisionExtractionService.cs`
- `src/DocuMind.Core/Agents/VisionExtractorAgent.cs`
- `src/DocuMind.Domain/Interfaces/IVisionExtractionService.cs`
- `src/DocuMind.Core/Services/IngestionService.cs` (sole caller)
- `src/DocuMind.Api/Program.cs` (`/api/documents/ingest` endpoint)

**Confirmed:** neither repo's test project contains any test referencing `PdfDocumentParser`, `PlainTextParser`, `ImageDocumentParser`, or `DocumentParserDispatcher` (`grep` across both `tests/` trees returns nothing) — the parent assessment's "no parser tests exist" finding is reconfirmed directly, not merely repeated from a prior summary.

---

## 2. Current SK behavior (exact, from source)

- **Interface:** `IDocumentParser.ParseAsync(Stream fileStream, CancellationToken ct) -> Task<string>`. No `contentType` parameter on `ParseAsync` itself (only on `CanParse`).
- **Dispatch (`DocumentParserDispatcher.GetParser`):** first-match-wins linear scan over registered `IDocumentParser`s by `CanParse(contentType)`; throws `NotSupportedException` (listing the registered parser type names) if none match. Selection is purely by an exact-string match against a small closed set of literal content-type strings — no extension fallback, no content sniffing.
- **`PlainTextParser`:** matches `"text/plain"`, `"text/markdown"`, `"text/html"` (exact string equality). Reads via `new StreamReader(fileStream, Encoding.UTF8)` then `ReadToEndAsync(ct)` — cancellation-aware, preserves the input exactly as decoded (every original newline, all leading/trailing whitespace), no HTML/Markdown structural interpretation at all (HTML tags are returned as literal text). `StreamReader`'s default `detectEncodingFromByteOrderMarks: true` means a UTF-8 BOM (if present) is silently stripped, and a non-UTF-8 BOM (e.g., UTF-16) would *override* the explicitly requested `Encoding.UTF8` — this is standard but easy-to-miss .NET `StreamReader` behavior, not something the DocuMind code deliberately chose.
- **`PdfDocumentParser`:** matches `"application/pdf"`, `"pdf"` (exact string equality, note the second literal is bare `pdf`, not a real MIME type — evidence the match list was hand-written ad hoc, not derived from a MIME registry). Opens PdfPig directly from the stream (`PdfDocument.Open(fileStream)`, no upfront buffering). For each page: calls `page.GetWords()` (all words for the *entire page*, in PdfPig's internal reading order) and joins them with a single space into **one flattened line per page** — this discards any original line/paragraph breaks *within* a page; it is not a per-line extraction. A page is skipped entirely (contributes nothing) if its joined text is all-whitespace (`string.IsNullOrWhiteSpace`); non-blank pages are separated by one blank line (`AppendLine(line); AppendLine();`). The whole result is `.Trim()`-ed at the end. **`ct` (`CancellationToken`) is accepted but never used** inside this parser — PdfPig extraction cannot be cancelled once started. The whole method body is synchronous work wrapped in `Task.FromResult(...)` — there is no genuine `await` anywhere in this parser (a "fake async" method).
- **Caller (`IngestionService.IngestAsync`):** builds a `Document` entity and sets `FileSizeBytes = fileStream.Length` **before** parsing — this requires the incoming stream to be seekable/length-known (true for the ASP.NET Core `IFormFile.OpenReadStream()` used at the call site, but not declared as a requirement by `IDocumentParser`'s own signature). After parsing: `rawText = rawText.Replace("\0", " ").Trim(); rawText = new string(rawText.Where(c => c != '\0').ToArray());` — the second line is dead code (the first `Replace` already removes every `\0`; the follow-up filter can never remove anything). A blanket `catch (Exception ex)` around the whole parse→chunk→embed→persist pipeline logs, marks the `Document` `Failed` with `ChunkCount = 0`, and **rethrows the original, unclassified exception** — no error category is preserved past this boundary (any parser-library exception type is indistinguishable from a chunking, embedding, or persistence failure by the time it reaches the API).
- **Input origin (`Program.cs`):** the API accepts `multipart/form-data`, reads the uploaded `IFormFile`, and passes `file.OpenReadStream()`, `file.FileName`, and `file.ContentType ?? "application/octet-stream"` into `IngestAsync`. **The content type used for parser selection is entirely client-declared** (the browser/HTTP client sets it) — there is no server-side verification against the file's actual bytes or its `file.FileName` extension. No request body size limit is configured in source (Kestrel/ASP.NET Core framework defaults apply implicitly, not a deliberate application-level control).

---

## 3. Current MAF behavior (exact, from source)

Everything in §2 applies identically **except** the following divergences:

- **Interface signature changed:** `IDocumentParser.ParseAsync(Stream fileStream, string contentType, CancellationToken ct) -> Task<string>` — MAF's interface adds `contentType` directly to `ParseAsync` (SK's does not). This is required because `ImageDocumentParser` needs the declared content type *inside* parsing (to pick the correct media type to hand to the vision model), not just for dispatch.
- **`PlainTextParser`:** byte-for-byte identical to SK's.
- **`PdfDocumentParser` is substantially different:**
  1. Fully buffers the input stream into a `byte[]` first (`CopyToAsync(ms, ct)`), rather than streaming directly into PdfPig — the bytes are needed twice (once for text-layer extraction, potentially again for image rasterization).
  2. Runs the *same* PdfPig word-join text-layer extraction as SK (identical page loop, identical single-space word-join, identical blank-page skip, identical trim) — but now via a private `ExtractTextLayer` helper that additionally returns the number of pages iterated.
  3. **Scanned/image-only PDF detection heuristic:** if `pageCount > 0 && text.Length >= pageCount * 20` (an average of at least 20 characters per page), the deterministic text-layer result is returned. Otherwise (little or no extractable text — including the `pageCount == 0` case, which always fails this condition and therefore always falls through), the parser falls back to **OCR via a vision model**, described in §14 below.
  4. Malformed PDFs still throw uncaught from `PdfDocument.Open(pdfBytes)` before the heuristic is ever evaluated — no fallback for a PDF that fails to open at all, only for one that opens but yields little/no text.
- **`ImageDocumentParser` (new in MAF, no SK equivalent):** matches `image/jpeg`, `image/jpg` (mapped to `image/jpeg`), `image/png`, `image/webp` via a small dictionary lookup. Fully buffers the stream to `byte[]`, then unconditionally calls the vision service on the whole image — there is no deterministic path for images at all; every image is 100% probabilistic-model-dependent.
- **Caller (`IngestionService.IngestAsync`):** same parse→chunk→embed→persist shape as SK, plus two additional independently-failure-isolated steps after persistence (categorization, knowledge-graph extraction — both out of scope for this capability, tracked separately in the parent assessment). Same dead-code double-null-strip. Same blanket `catch (Exception)` swallowing error category. Additionally threads a `Guid? conversationId` through for per-conversation scoping (a DocuMind-specific, application-level concern, not relevant to parsing).
- **Input origin (`Program.cs`):** identical multipart-form-data pattern to SK; same client-declared, unverified content type; no explicit size limit.

---

## 4. Divergence analysis

| Aspect | SK | MAF | Classification |
|---|---|---|---|
| `ParseAsync` signature | no `contentType` param | adds `contentType` param | Accidental — driven by `ImageDocumentParser`'s implementation need, not a deliberate contract decision; not worth preserving either shape verbatim |
| PDF text-layer algorithm (page loop, word-join, blank-page skip, trim) | Yes | Yes, identical | Intentional (as coded) for the *deterministic* path — but see §9 for why "one flattened line per page" itself is classified as an accidental byproduct, not an intended requirement |
| PDF stream handling | streamed directly into PdfPig | fully buffered to `byte[]` first | Accidental difference — MAF's buffering is a consequence of needing the bytes twice (text + possible rasterization), not an independent design choice about streaming vs. buffering |
| Scanned-PDF / OCR fallback | absent — empty/near-empty PDFs silently produce near-empty output, `IngestionService` "succeeds" with zero or near-zero chunks | present — falls back to a vision model | MAF's addition is a genuine, evidenced feature; SK's absence is a **gap**, not a considered "no OCR" decision (there is no comment or check in SK acknowledging or rejecting the scanned-PDF case at all) |
| Image file parsing | absent | present (`ImageDocumentParser`) | MAF-only feature |
| Cancellation | plain-text path is cancellation-aware; PDF path ignores `ct` entirely (both repos) | same | Defect (consistent across both repos) — not a considered "PDF parsing is uncancellable" decision, simply an unused parameter |
| Error handling | uncaught library exceptions bubble to a blanket `catch (Exception)` at the ingestion boundary, losing category | same | Defect (consistent across both repos) |
| Content-type trust | fully client-declared, unverified | same | Defect/security gap (consistent across both repos) — see §17 |

**Overall:** the deterministic text-extraction core (plain text; PDF text-layer via word-join) is **identical** in both repos, exactly as with Batch 1's Chunking finding. MAF is a strict superset that adds one genuinely new, evidenced concern (OCR/vision fallback for image content) layered *on top of*, not *instead of*, the same deterministic core.

---

## 5. Proposed capability identity

**`document.parsing`** (namespace `legoai_document`, package `legoai_document.parsing` — see §19).

No alternative name was seriously competitive: "parsing" is the term both DocuMind codebases already use consistently (`IDocumentParser`, `DocumentParserDispatcher`, `PdfDocumentParser`), and "document.parsing" mirrors the already-accepted "document.chunking" naming style from Batch 1.

---

## 6. v1 scope

```text
document.parsing
    ├── plain text   (text/plain, text/markdown, text/html — treated as opaque text,
    │                 no Markdown/HTML structural interpretation, matching current behavior)
    └── text-bearing PDF   (PDF pages containing an extractable text layer)
```

Both paths are **deterministic** (§15). No probabilistic/Model-backed extraction of any kind is part of `document.parsing` v1.

## 7. Explicitly deferred scope

- **OCR / scanned-PDF fallback / image file parsing** — see §14 for full analysis. Not designed or contracted in this batch at all (deliberately, not merely "not yet implemented" — see the reasoning in §14 for why even naming its eventual contract is premature here).
- **Document classification, structured/knowledge-graph extraction, table extraction, layout analysis** — already tracked and deferred in the parent assessment (§6 extraction matrix); nothing new to add here.
- **Chunking, embeddings, retrieval, persistence, Artifact creation** — explicitly out of this capability's boundary; see §10 and §20.
- **Content sniffing / magic-byte verification of declared format** — considered in §12 and explicitly deferred as a future low-cost hardening, not built now.
- **File-size limits / resource quotas** — explicitly a governed Execution/Resource-Policy concern (SPEC §4.10), not invented inside this pure(ish) capability; see §17.

---

## 8. Three distinct concerns, kept separate

```text
document ingestion / source acquisition   (HTTP upload, multipart form handling, IFormFile —
                                            entirely DocuMind-specific, entirely out of scope here)
        ≠
document format parsing                   (bytes + declared format -> extracted text structure —
                                            THIS capability)
        ≠
OCR / vision extraction                    (image bytes -> text via a probabilistic Model call —
                                            explicitly deferred, §14)
```

**Does current DocuMind code conflate these?** Partially, and only in MAF: `PdfDocumentParser.ParseAsync` in MAF silently *decides*, inside what is nominally a "parsing" call, whether to run a deterministic extraction or invoke a vision model — the caller (`IngestionService`) cannot tell which happened, since both paths return the same `Task<string>` with no signal of which extraction method produced it. SK does not conflate parsing with OCR (it simply has no OCR at all). "Document ingestion/source acquisition" (the HTTP multipart handling in `Program.cs`) is already cleanly separated from parsing in both repos — the parser only ever sees a `Stream`/content-type, never touches HTTP concerns directly. This capability's boundary (§6/§9) restores the same separation MAF's PDF path currently breaks.

---

## 9. Request/result model

Three distinct types are kept separate, per the same discipline Batch 1 applied to Chunking:

```text
DocumentParsingRequest / ParsedDocument   (this capability's pure semantic request/result)
        ≠
DocuMind's persistence entity (Document, with Id/TenantId-equivalent/CreatedAt/ChunkCount/etc.)
        ≠
Artifact / ArtifactVersion   (SPEC SS4.8 — a caller's choice, if/when it wants to preserve a
                              parsed result durably; this capability performs no persistence
                              and returns no Artifact reference)
```

### Page-boundary decision: page-aware, not flattened

**Decision: `ParsedDocument` carries `pages: tuple[ParsedPage, ...]`, each `ParsedPage` carrying `index: int` and `text: str`. There is no flattened-string field stored on the result itself; a caller that wants one derives it via `flatten_pages()` (§18).**

This is not adopted merely because it seemed more sophisticated — it is justified by concrete, already-identified evidence:

1. **A real, already-diagnosed defect this directly fixes.** The parent assessment (§6/§21) independently found that `DocumentChunk.PageNumber` is declared on both DocuMind C# entities but is **always null**, because `ChunkingService` operates on already-flattened text with no page information available to it. That defect traces directly back to this parsing stage discarding page boundaries. Preserving them here is a prerequisite for ever fixing it (not something this batch fixes — Chunking is not being modified, per this task's constraint — but a page-aware `ParsedDocument` is what would make a *future*, still-undesigned page-aware chunking variant possible without redesigning parsing again).
2. **Zero extra cost.** Both PdfPig (C#) and the Python candidates evaluated in §16 already iterate page-by-page internally; the current C# code *throws away* information the library hands it for free (page identity), it does not avoid computing it.
3. **One-way information loss otherwise.** A caller that wants flattened text can always derive it cheaply from page-aware data (`"\n\n".join(p.text for p in pages)`); the reverse — recovering page boundaries from an already-flattened string — is impossible. Preferring the reversible, richer representation when the cost is zero is the conservative choice.
4. **Blank pages become simple, not special-cased.** Both C# oracles must explicitly skip blank pages to avoid a stray double-blank-line artifact in their flattened output. A page-aware result has no such artifact to avoid — a blank page is naturally represented as `ParsedPage(index=N, text="")`, preserving the true physical page count and indices. This is classified as an **accidental byproduct of the flattening approach**, not an independently intended requirement, and is not being replicated.

**Plain text / Markdown / HTML sources** have no native page concept. They are represented as a single `ParsedPage(index=0, text=<entire decoded content>)` — this is not a fiction; it is the correct reading of "how many pages does this text file have" (exactly one, containing everything).

### A second, related decision: line breaks within a page are preserved, not collapsed

Reading `PdfDocumentParser.ExtractTextLayer` closely (both repos, identical): `page.GetWords()` returns *all* words for an entire page as a flat sequence, and the code joins them with a single space — `string.Join(" ", words.Select(w => w.Text))` — into **one line per page**, regardless of how many original lines/paragraphs the page actually had. This is not something PdfPig forces; it is a consequence of this specific, minimal usage of the library (PdfPig can expose line/text-block structure through other APIs the code does not use). There is no comment or test suggesting this was a deliberate "flatten every page to one line" requirement — it reads as the simplest thing that could plausibly work, not a decision.

This matters concretely for Batch 1: Chunking's characterized behavior (`CHUNKING-CAPABILITY-DESIGN.md` §12) treats `"a\nb"` as **one word**, since it only splits on ASCII space. If Parsing collapses `"Hello\nWorld"` into `"Hello World"` (two words, space-joined) versus preserving the literal `"Hello\nWorld"` (one word, by Chunking's own characterized rule), the choice made here changes Chunking's observable word counts for real PDF content — this is a genuine cross-capability interaction, not a cosmetic detail.

**Decision:** v1's PDF text-layer extraction preserves natural line breaks within a page (a low-cost, well-justified improvement over the C# oracle's coarser behavior), rather than joining every word in a page with a single space. This is recorded as a **deliberate, documented divergence from the oracle**, not an oversight — the oracle's single-line-per-page behavior is classified `ACCIDENTAL_LIBRARY_BEHAVIOR`, not intended contract, for exactly the reasons above. (Plain-text sources already preserve every original line break under both oracles today — this decision simply makes PDF behavior consistent with that, rather than introducing a PDF-specific asymmetry.)

---

## 10. Entity separation (explicit)

`ParsedPage`/`ParsedDocument` deliberately exclude every field from DocuMind's `Document` persistence entity that is not itself a semantic parsing output:

**Excluded (persistence/caller concerns, not parsing outputs):** `Id`, `DocumentId`/tenant-equivalent identity, `FileName` (a caller correlation detail, exactly like Batch 1 excluded `document_id` from `Chunk` — see §11 for why `filename` is excluded from the *request* too), `ContentType`/`FileSizeBytes` (caller-observable facts about the *input*, not outputs of parsing), `UploadedAt`/`ProcessedAt`/`CreatedAt` (persistence timestamps), `Status`, `ChunkCount` (a downstream capability's concern), `Category` (a different, deferred capability), `ConversationId` (DocuMind-specific application scoping), any `Embedding`/vector field, any navigation/collection property linking to chunks.

**Included (genuine parsing outputs only):** page index, page text.

---

## 11. Input representation

Four options were compared:

| Option | Fit | Verdict |
|---|---|---|
| **A — `parse_document(data: bytes, ...)`** loose positional args | Simple, but scatters related parameters (bytes + format) across a positional signature rather than one cohesive value, inconsistent with Batch 1's `ChunkingRequest` style | Rejected as the top-level shape, but its core insight (bytes, not a stream) is correct — folded into Option C |
| **B — `parse_document(stream: BinaryIO, ...)`** | Mirrors the C# `Stream` parameter, but introduces resource-ownership/lifetime/disposal questions the C# code itself does not cleanly answer (who closes the stream? can it be read twice?) — and both DocuMind repos' own MAF implementation ends up fully buffering the stream to `byte[]` anyway before doing anything useful with it (`CopyToAsync(ms, ct)`), which is direct evidence that "bytes" is the real working representation both algorithms want, and `Stream` is only a delivery mechanism inherited from ASP.NET Core's upload API, not a deliberate capability-level design choice | Rejected |
| **C — `parse_document(request: DocumentParsingRequest)`** wrapping a byte payload plus a declared format | Matches Batch 1's single-immutable-request-object style exactly; avoids all stream lifetime/ownership ambiguity; keeps the capability a plain value-in/value-out function, consistent with "no I/O" (§14, §15) | **Selected** |
| **D — filesystem paths** | Couples a reusable capability to local-filesystem availability, which a future non-local caller (an HTTP upload buffered in memory, an object-storage payload, a message-queue attachment) may not have at all; rejected outright per intent's cloud/deployment neutrality (intent §38) and this capability's own goal of being usable independently of any particular ingestion transport | Rejected |

**Decision: Option C.** `DocumentParsingRequest(content: bytes, format: DocumentFormat)` — see §18 for the exact shape. `filename` is deliberately **excluded** from the request (not merely "optional"): it plays no role in the pure computation (format is resolved by the caller before this capability is ever called — see §12), and including it would repeat exactly the `document_id`-in-`ChunkingRequest` mistake Batch 1's design explicitly avoided (a caller-side correlation/diagnostic detail masquerading as a computation input). A caller that wants filename-qualified error messages can attach that context itself when it catches a `DocumentParsingError` (§13) — the exception's payload does not need to originate inside this capability.

**Large-document tradeoff, noted not solved:** a bytes-based signature requires the whole document resident in memory, matching what both DocuMind repos already effectively do (full buffering) for anything beyond the simplest streaming text case. A future memory-efficient Adapter could still stream internally as an implementation detail as long as it satisfies the same observable `DocumentParsingRequest -> ParsedDocument` contract; that is an Adapter concern, not a reason to complicate the capability's public shape now, especially since large-input performance is explicitly a benchmark concern, not an SLA (§16 of the Chunking design already established this precedent; §"Performance" below does the same here).

---

## 12. Format-selection mechanism

**Observed current behavior (both repos):** parser selection is driven entirely by an exact match against a small, hand-written set of literal content-type strings (`"application/pdf"`, `"pdf"`, `"text/plain"`, `"text/markdown"`, `"text/html"`, plus MAF's image MIME types), sourced from the **client-declared, unverified** `IFormFile.ContentType` header. There is no extension fallback and no content sniffing anywhere in either repo.

**A concrete, evidenced risk this creates:** `PlainTextParser` decodes with `Encoding.UTF8`, whose default decoder uses **replacement-character fallback**, not an exception, for invalid byte sequences. If a caller mislabels a PDF as `text/plain` (or any binary file as a text type), `PlainTextParser` would **not** throw — it would silently return a string full of U+FFFD replacement characters, which then flows unremarked through chunking, embedding, and answering with no signal anything went wrong. This is a real, silent-corruption failure mode enabled directly by trusting an unverified, caller-supplied string for both dispatch *and* decoding behavior. It is classified as a **defect**, not a considered risk acceptance (nothing in the source acknowledges or guards against it).

**Decision — a bounded combination, not a MIME string, not content sniffing:**

`document.parsing` v1 accepts an explicit, closed **`DocumentFormat` enum** (`PLAIN_TEXT`, `MARKDOWN`, `HTML`, `PDF`) as part of the request, rather than accepting an arbitrary MIME string directly. Resolving a raw MIME/content-type string (or a file extension, or sniffed bytes) into one of these four values is the **caller's** responsibility — exactly mirroring what DocuMind's own dispatcher already does today, just formalized into a closed set instead of open string literals scattered through parser classes. This:

- Makes "unsupported format" a total, exhaustively-checkable function over a small `Enum` rather than a fallible string-matching cascade that can silently fail to match a validly-intended-but-differently-spelled MIME string.
- Does **not** solve the "wrong-but-recognized format label" class of bug (a caller can still declare `PDF` for a file that is not actually a PDF) — that residual risk is carried forward explicitly (§17), not hidden.
- Deliberately avoids building "a complex universal file-type framework for two formats" — content sniffing (e.g., checking for a `%PDF-` magic-byte header) is noted as a plausible, low-cost future hardening a caller or a thin dispatch layer could add later, but is out of scope for v1's capability contract itself.

---

## 13. Error model

Four pack-local exceptions, matching the categories the task brief itself proposed evaluating, kept to a single shallow hierarchy (mirroring Batch 1's minimal-surface discipline, but here the distinctions are genuinely actionable, not invented for their own sake):

```python
class DocumentParsingError(ValueError):
    """Base for all document.parsing failures."""

class UnsupportedDocumentFormatError(DocumentParsingError):
    """Raised when the declared DocumentFormat has no v1 realization (e.g. an image format)."""

class MalformedDocumentError(DocumentParsingError):
    """Raised when declared-format content cannot be parsed as that format."""

class EncryptedDocumentError(DocumentParsingError):
    """Raised when a PDF is password-protected/encrypted and cannot be read without one."""
```

**Why `EncryptedDocumentError` earns its own category (unlike a deeper hierarchy this design avoids):** unlike the current C# oracle (which does not distinguish this case — a PdfPig exception for an encrypted PDF is just another uncaught exception), the Python library candidates evaluated in §16 (`pypdf` in particular) can reliably distinguish "this PDF is encrypted and unreadable without a password" from "this PDF is generically corrupt." That is a real, user-actionable difference ("we need a password" vs. "this file appears damaged") worth surfacing distinctly. This is a **deliberate improvement over the oracle**, not a replication of oracle behavior — recorded here explicitly rather than silently introduced.

**Future mapping (not implemented here):** at a future governed Execution boundary, `UnsupportedDocumentFormatError` maps most naturally to SPEC's `CapabilityUnavailable`/`ValidationError` boundary depending on framing (an unsupported *format* is closer to a capability-scope limitation than a malformed request); `MalformedDocumentError` and `EncryptedDocumentError` both map to SPEC's `ValidationError` category (an input-contract violation) per SPEC §10's canonical error model. Exactly as with `ChunkingValidationError` in Batch 1, this mapping is **not implemented** in this batch.

---

## 14. OCR boundary — full analysis

Answering the eight questions directly, from `VisionExtractionService.cs`, `VisionExtractorAgent.cs`, and `PdfDocumentParser.cs` (MAF):

1. **How is "no extractable PDF text" detected?** A heuristic: average characters-per-page `>= 20`, computed as `text.Length >= pageCount * 20` over the *already-extracted* text-layer result. A zero-page PDF always fails this check (since `pageCount > 0` is required) and therefore always falls through to the OCR path, even though there is nothing meaningful for OCR to do with zero pages.
2. **Per-page or whole-document?** Per-page — each page is rasterized independently (`PDFtoImage.Conversion.ToImagesAsync`) and OCR'd independently, then the results are concatenated with blank-line separators (the same flattening pattern as the deterministic path).
3. **Is the Agent merely a model wrapper here?** Yes, unambiguously — `VisionExtractionService.ExtractTextAsync` builds one `ChatMessage` containing a fixed text instruction plus the image as `DataContent`, and calls `_visionAgent.RunAsync([message])` **once**, statelessly, per image. There is no tool use, no multi-turn interaction, no `AgentThread`. This is a single Model invocation wearing an "Agent" name, exactly matching the finding already recorded in the parent assessment for the Answering capability.
4. **What prompt/model/schema?** A fixed instruction string (`VisionExtractorAgent.Instructions`): "transcribe all text exactly as it appears... preserve reading order, line breaks, table/column structure as plain text... if no readable text, respond with exactly: `[NO TEXT FOUND]`." Output is raw, unstructured text — no JSON schema, no structured output. The sentinel string `[NO TEXT FOUND]` is mapped to an empty string by the service.
5. **What happens when OCR fails (an exception)?** Nothing catches it inside `VisionExtractionService` or `PdfDocumentParser.ExtractViaVisionAsync` — an exception (network failure, model error, etc.) propagates uncaught all the way to `IngestionService`'s blanket `catch (Exception)`, which marks the **entire document** `Failed`.
6. **Is OCR failure fatal or degraded?** Both, depending on *kind* of failure, and the distinction is not surfaced anywhere: a thrown exception is fatal to the whole ingestion (per #5). A **non-throwing but low-quality/empty** result (an illegible or blank page) is silently treated as a successful-but-empty contribution — no error, no warning, no flag; the page's text is simply absent from the final output with no way to tell "this page had no text" apart from "this page failed to OCR cleanly."
7. **Does OCR preserve page provenance?** No — OCR'd page text is concatenated into the same flat string as the deterministic path, with the same information loss described in §9. This is strictly worse for OCR than for deterministic extraction, because OCR results carry inherent uncertainty that page-level attribution would help a downstream consumer reason about (e.g., "this sentence came from an OCR'd page, treat with more caution") — currently impossible to recover once flattened.
8. **Does the parser API hide probabilistic work behind a deterministic-looking signature?** **Yes, confirmed.** `IDocumentParser.ParseAsync` returns `Task<string>` identically whether the text came from deterministic PdfPig word extraction or from a fully probabilistic vision-model call — a caller cannot distinguish which happened, and no metadata is returned indicating "this text is Model-generated" versus "this text is a literal transcript of an embedded text layer." This directly conflicts with SPEC §4.5's Model invariants ("Model output is untrusted data") and with intent Principle #9 ("AI is optional" / the deterministic-to-probabilistic escalation should be an observable, deliberate choice, not something silently embedded one layer down).

### Recommendation: OCR does **not** belong in `document.parsing` v1

The strong default from the task brief is confirmed by the evidence, not merely assumed:

```text
DocumentParsingCapability v1  =  deterministic text extraction only
OCR / Vision                  =  a separate, later-designed capability, composed by a caller/workflow
```

**On naming the eventual OCR capability — deliberately not decided here.** Two candidates were weighed:

- `document.ocr` — names the *purpose* (extract text from a document image) without committing to a *mechanism*; a future deterministic OCR engine (e.g., a traditional pattern-matching OCR library) and a future vision-Model-backed realization (as DocuMind's MAF version already demonstrates) could both be valid `CapabilityVersion`s or `Provider`s under this one purpose-named capability, each declaring its own determinism guarantee — consistent with how `model.chat-completion` does not name a vendor.
- `vision.text_extraction` — names the *mechanism* (a vision model), which would be a misnomer if a non-vision-model OCR provider were ever added, and ties the capability's identity to one technology family rather than one purpose.

`document.ocr` is the better-reasoned candidate *if and when* this capability is designed, precisely because it stays technology-neutral the same way this document's own §5 naming does. **However, per this batch's own discipline (already applied to Classification and Structured Extraction in the parent assessment), a capability with exactly one realization, evidenced by exactly one application, is not designed or contracted here** — only the eventual identity is recorded as a leaning, not a decision, to avoid rediscovering this reasoning later without repeating the analysis.

---

## 15. Determinism

| Path | Classification |
|---|---|
| Plain text / Markdown / HTML decoding | **Deterministic** — pure byte-to-text decoding, no model, no external call |
| PDF text-layer extraction | **Deterministic** — given a fixed library version, identical input bytes always yield identical output (library version pinning is itself a version-relevant fact, exactly as tokenization choice was for Chunking — see §22) |
| OCR / vision extraction | **Probabilistic** — explicitly excluded from v1 (§14); if and when it exists, it MUST be a separately identified, separately invoked capability so its non-deterministic guarantee is never silently inherited by `document.parsing`'s deterministic contract |

`document.parsing` v1's `CapabilityVersion` declares an unconditional determinism guarantee for both of its realized paths — this is only honest because OCR is excluded; reintroducing OCR *inside* this capability later (rather than as a separate composed capability) would silently invalidate that guarantee, which is exactly the failure mode identified in MAF's oracle (§14, question 8) and exactly why OCR must not be added to this capability's v1 or any same-named future version without a new major `CapabilityVersion` that explicitly revises the determinism declaration (§22).

---

## 16. Security review

Document parsing is an **untrusted-input boundary** — analyzed explicitly, not assumed safe:

| Concern | Assessment |
|---|---|
| Malformed files | Relies entirely on the chosen library's own robustness (§ dependency table below); this design claims no additional validation or sandboxing beyond surfacing a `MalformedDocumentError` when the library itself detects and reports a failure |
| Parser bombs (decompression bombs, deeply nested PDF object graphs) | **Not defended against.** This is a known category of PDF-library vulnerability class; this design does not claim protection. Library selection (§17) weighs known security history as one factor, but a genuine defense (resource-bounded parsing, sandboxed execution) is out of scope — the repository's own `ADR-012` ("Isolation mechanism for expanded Plugin threat scope") is the more appropriate future home for this, and it remains Proposed/non-binding today |
| Oversized documents / resource exhaustion | No size limit is enforced by this capability (matching the oracle, which also has none at the application level). This is treated as a governed Execution/Resource-Policy responsibility (SPEC §4.10 Budget/Quota/Limit) to be enforced **before** this capability is invoked, not invented here as a fabricated threshold |
| Embedded objects / JavaScript / interactive actions | Out of scope by construction, not by an added defense: this design only ever performs *text extraction*, never interactive rendering or script execution, so PDF JavaScript/actions are never executed or even inspected. This holds only because the chosen library usage stays confined to text extraction — a future capability that adds richer PDF features must re-examine this |
| Filesystem/path injection | Not applicable — the bytes-based input decision (§11, Option C) never accepts a caller-supplied filesystem path, closing this class of risk off by construction |
| External references (network fetches triggered by content) | Not applicable in v1 — no HTML/Markdown structural interpretation occurs (§6); content is treated as opaque text, so nothing dereferences an `<img src="...">` or similar |
| Encrypted documents | Detected and reported as `EncryptedDocumentError` rather than an opaque parser exception (an improvement over the oracle, §13) — but no attempt is made to decrypt, brute-force, or otherwise process an encrypted document |
| Memory limits | Both DocuMind oracles fully buffer entire documents into memory; this design's bytes-based contract (§11) shares that same characteristic by construction — no streaming/backpressure exists at the capability level |
| Parser library vulnerabilities | Standard hygiene (pinned version, monitored advisories) recommended; not something a capability-level *design* can guarantee beyond the dependency choice itself |
| Content-type/format trust | Carried forward explicitly as a residual risk from §12: a caller can still declare the *wrong* (but validly-shaped) `DocumentFormat` for real content; this design formalizes format selection into a closed enum (removing the "unrecognized string silently falls through" bug class) but does **not** verify the declared format against actual byte content — that remains the caller's responsibility unless a future magic-byte-sniffing hardening is added |

No sandboxing, resource isolation, or content verification is claimed that does not exist in this design.

---

## 17. Python dependency options

**This is an implementation-dependency decision, not a Core architecture decision**, evaluated for Python 3.14 fitness, licensing, maintenance, security posture, and native-dependency consequences. Current (2026) status verified via web search, not assumed from training data alone.

| Library | License | Pure Python | Maintenance (2026) | Fit for v1 (basic sequential text-layer extraction only) |
|---|---|---|---|---|
| **`pypdf`** | BSD-3-Clause (permissive) | Yes — no native/compiled dependency | Active; steady releases since the current maintainer took over in April 2022 | **Good** — functionally the closest match to what the C# oracle already does (basic, non-layout-aware text extraction); permissive license carries no redistribution obligations for a capability pack meant to be freely composed into arbitrary future LegoAI applications |
| `pdfminer.six` | MIT (permissive) | Yes | Active | Good, but more granular/complex (character/line/font-level access) than v1's scope needs; equally permissive to `pypdf`, no clear advantage for this narrow use case |
| `PyMuPDF` (`fitz`) | **AGPL-3.0**, with a separate paid commercial license available from Artifex | **No** — wraps the native MuPDF C library | Active, fastest of the group by a wide margin (benchmarked ~10x faster than pdfminer.six-based tools on large batches) | **Rejected as the v1 default.** AGPL-3.0 is a strong copyleft license: distributing or network-serving software that uses it can obligate releasing the complete application source under AGPL terms. That is a serious, avoidable risk for a capability pack explicitly intended to be composed into arbitrary — including potentially closed-source — future LegoAI applications (intent §41, "Escape Hatches," presumes *voluntary*, explicit opt-in to reduced portability/licensing constraints, not one silently inherited from a default dependency). The native dependency also breaks `legoai-document`'s current pure-Python, zero-native-dependency posture established in Batch 1 |
| `pdfplumber` | MIT (built on `pdfminer.six`) | Yes | Active | Unnecessary for v1 — its main advantage (table extraction) is explicitly out of scope (§7); heavier than needed for basic text extraction |

**Recommendation: `pypdf`.** BSD-3-Clause avoids any copyleft obligation; pure Python preserves the zero-native-dependency posture `legoai-document` already has after Batch 1; active maintenance and a straightforward per-page `extract_text()` API match v1's narrow scope; and it can distinguish an encrypted-PDF failure from a generically malformed one (§13), which the C# oracle's library usage does not attempt at all. Speed (PyMuPDF's main advantage) is not a stated requirement anywhere in the evidence, and the license/native-dependency cost is not justified by an unevidenced performance need.

This recommendation is **not implemented** in this batch — no dependency is added to `packages/legoai-document/pyproject.toml` here (§26 hard stop).

Sources consulted: [Python PDF library comparison (2026)](https://www.nutrient.io/blog/best-python-pdf-libraries/), [PyMuPDF vs pdfplumber (2026): the speed-vs-license tradeoff](https://pdfmux.com/blog/pymupdf-vs-pdfplumber/), [pdfplumber vs PyMuPDF vs pypdf](https://subhajitbhar.com/blog/pdf-extraction/pdfplumber-vs-pymupdf-vs-pypdf2/), [PyMuPDF PyPI license notice](https://pypi.org/project/pymupdf/).

---

## 18. Proposed Python API (signatures only — no implementation)

Consistent with Batch 1's style: frozen, slotted dataclasses; a plain `Enum`; free functions, not a `Parser`/`Service`/`Manager` object (there is no state to encapsulate and, for the deterministic v1 paths, no Provider/Adapter substitution to abstract behind a `Protocol` yet — the same reasoning Batch 1 applied to reject a `Protocol` for Chunking applies here for the same reason: exactly one realization per format today).

```python
# legoai_document/parsing/values.py

from dataclasses import dataclass
from enum import Enum


class DocumentFormat(Enum):
    """Closed set of formats document.parsing v1 can realize.
    Resolving a MIME type / extension into one of these is the caller's
    responsibility (SS12) -- this capability trusts the declared value."""
    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


@dataclass(frozen=True, slots=True)
class DocumentParsingRequest:
    """Immutable input to document.parsing. No filename/document-identity
    field -- see SS11 for why that is a deliberate exclusion, not an
    oversight."""
    content: bytes
    format: DocumentFormat


@dataclass(frozen=True, slots=True)
class ParsedPage:
    """A single page's extracted text. index is zero-based. A non-paginated
    source (plain text/Markdown/HTML) is represented as exactly one page."""
    index: int
    text: str


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Immutable, page-ordered output of document.parsing."""
    pages: tuple[ParsedPage, ...]


# legoai_document/parsing/errors.py

class DocumentParsingError(ValueError):
    """Base for all document.parsing failures."""


class UnsupportedDocumentFormatError(DocumentParsingError):
    """Raised when the declared DocumentFormat has no v1 realization."""


class MalformedDocumentError(DocumentParsingError):
    """Raised when declared-format content cannot be parsed as that format."""


class EncryptedDocumentError(DocumentParsingError):
    """Raised when a PDF is encrypted/password-protected and unreadable
    without a password."""


# legoai_document/parsing/api.py

def parse_document(request: DocumentParsingRequest) -> ParsedDocument:
    """Extract page-ordered text from request.content per request.format.

    Deterministic, pure with respect to its declared inputs; no OCR, no
    network access, no persistence (SS14-15).

    Raises:
        UnsupportedDocumentFormatError: format has no v1 realization.
        MalformedDocumentError: content cannot be parsed as the declared format.
        EncryptedDocumentError: a PDF is encrypted and unreadable without a password.
    """
    ...


def flatten_pages(document: ParsedDocument, separator: str = "\n\n") -> str:
    """Project a ParsedDocument to a single string, joining page texts with
    separator. A convenience derivation, not stored data -- see SS20 for why
    this lives here rather than depending on legoai_document.chunking."""
    ...
```

No implementation body is provided, per this task's design-only scope.

---

## 19. Package placement

**`packages/legoai-document/src/legoai_document/parsing/`** — a new sibling subpackage next to the existing `chunking/`, inside the *same* distribution established in Batch 1. No new distribution is created; Core is not touched.

No architectural contradiction was found that would require otherwise: this capability shares every placement rationale Batch 1 already established for `legoai_document` as a whole (ADR-002 §13's "future integration distribution" mechanism; not a canonical SPEC concept; optional; Core has no outward dependency on it). The only new fact introduced by this capability — a first runtime dependency (`pypdf`, §17, not yet added) — does not change that reasoning: ADR-002 §13 already anticipates first-party optional modules having "its dependency/install strategy... explicit," which `legoai-document`'s own `pyproject.toml` already accommodates (adding a dependency there remains entirely isolated from Core's base install, which still has zero dependencies and no reason to ever import `legoai_document`).

---

## 20. Interaction with Chunking

```text
caller / workflow
        │
        ▼
   parse_document(DocumentParsingRequest(...))  →  ParsedDocument
        │
        ▼
   project desired text  (e.g. flatten_pages(parsed) -> str, or the caller's
                           own page-aware projection)
        │
        ▼
   chunk_text(ChunkingRequest(text=<projected str>, ...))  →  ChunkingResult
```

**Chunking does not import `legoai_document.parsing`, and `legoai_document.parsing` does not import `legoai_document.chunking`.** The composition above is entirely the caller's/a future workflow's responsibility — exactly the same "capability-oriented, not pipeline-oriented" discipline intent Principle #8 requires ("An application MUST NOT require [X] merely to use [Y]"). `flatten_pages` lives in `legoai_document.parsing` (§18) because it operates purely on `ParsedDocument`/`ParsedPage`, which `parsing` already owns — it returns a plain `str` and has no need to know `ChunkingRequest` exists. Each capability remains independently installable and independently usable: a caller can chunk arbitrary text with no parser ever having run, and a caller can parse a document and do something with the pages other than chunk them (e.g., a future page-aware capability, or direct display) without ever calling `chunk_text`.

---

## 21. Testing design (to be written, not written in this batch)

- **Unit tests** for `parse_document` over each supported `DocumentFormat`, covering the fixture set in §23.
- **Fixture-based characterization tests**, ported from the table in §23/§24 — asserting the *decided* v1 behaviors (page-aware output, line-break preservation, blank-page representation, closed-enum format handling) precisely, not merely "it returns something."
- **Negative/error cases**: unsupported format, malformed PDF, encrypted PDF — one test per exception type at minimum, using programmatically-constructed fixtures (§23), never real customer/DocuMind documents.
- **Deterministic-parity tests**: the same input parsed twice yields byte-identical `ParsedDocument` output (mirrors Batch 1's `test_same_request_produces_same_result`).
- **Package architecture tests**: `legoai_document.parsing` does not import `legoai_document.chunking` (and vice versa); `legoai` Core does not import `legoai_document` (extends Batch 1's existing `test_core_does_not_import_pack.py` — no new test needed there, since it already scans all of Core, but `parsing`'s own forbidden-import list should extend Batch 1's `test_dependency_boundaries.py` pattern to allow `pypdf` once it is actually added, while still forbidding every other framework/provider named in the parent assessment).
- **Dependency tests**: once `pypdf` is added, a test should confirm it is the *only* new runtime dependency (no transitive surprise like an unexpected native wheel).
- **Regression tests against Chunking**: a small integration-style test demonstrating the composition in §20 end-to-end (parse a fixture, flatten it, feed it to `chunk_text`, assert the result is sane) — this exercises the *interaction*, without either capability importing the other.

None of the above are described as formal LegoAI conformance evidence — no conformance suite exists yet for any Port this capability might eventually realize, consistent with CONFORMANCE.md's own distinction between ordinary tests and conformance proof.

---

## 22. Versioning

Per SPEC §11 (mirroring Batch 1's treatment for Chunking):

| Candidate change | New `CapabilityVersion` required? | Reasoning |
|---|---|---|
| Changing the page-aware shape itself (e.g., redefining "page" as a section/paragraph rather than a literal physical page) | **Yes — major.** | Changes the meaning of `ParsedPage.index`/count for identical input |
| Whitespace-normalization policy changes (e.g., deciding to strip each page's text) | **Yes — major**, if it changes output for existing inputs | Same reasoning as Batch 1's chunk-size-semantics entry |
| `flatten_pages`'s default separator | Minor, but should still be treated as a compatibility-relevant detail for callers depending on the exact joined string | Low-stakes since it is a projection helper, not the stored result, but not free to change silently either |
| Including OCR by default in a future `document.parsing` release | **Yes — major, or (preferred, per SS14) a wholly separate capability**, never a silent addition | Would invalidate the unconditional determinism guarantee (SS15); SPEC C-04 forbids silent behavioral fallback of this kind |
| Swapping the underlying PDF library (e.g., `pypdf` → `pdfminer.six` later) | **Conformance-relevant, not automatically a version bump** | Per SS6's instruction not to encode any one library's semantics as canonical: a provider swap MUST preserve the documented v1 observable contract (word/line extraction behavior, page boundaries) to remain the *same* `CapabilityVersion`; if it cannot, it must ship as a new version, not a silent library upgrade |
| Word/page ordering changes | **Yes — major**, if it changes existing-input output | Ordinary breaking-change rule (SPEC V-03) |
| Adding new optional metadata fields (e.g., a future `ParsedPage.rotation`) | Minor/additive, provided existing required fields and their meanings are unchanged | Standard additive-compatibility rule |

---

## 23. Characterization fixtures (design, not execution of a full test suite)

**Methodology note (transparency, not a shortcut taken silently):** the deterministic behaviors below (plain-text decoding; the PDF word-join/blank-line/trim algorithm; the blank-page skip) are derived with high confidence directly from the C# source shown in §2/§3 — they do not require running the .NET code to predict correctly, since the logic involved is simple and fully traceable by inspection. Genuinely library-internal details that cannot be predicted from source alone (the *exact* exception type PdfPig raises for a malformed vs. an encrypted PDF) are marked `UNDECIDED — REQUIRES LIVE VERIFICATION` rather than guessed, consistent with the instruction not to infer behavior from library names. A full dotnet test harness execution against these fixtures was judged disproportionate to a design-and-characterization batch and was not performed; it is recommended as a concrete pre-implementation task (§25).

| # | Fixture | Construction | Predicted SK result | Predicted MAF result | Same/different | Classification |
|---|---|---|---|---|---|---|
| 1 | Empty UTF-8 text file | `b""`, format `text/plain` | `""` (StreamReader on empty stream reads empty string) | Identical | Same | Intentional (as coded) |
| 2 | Simple ASCII text | `b"Hello world"`, `text/plain` | `"Hello world"` (unchanged) | Identical | Same | Intentional |
| 3 | Unicode UTF-8 text | `"café 日本語 😀".encode("utf-8")`, `text/plain` | Exact string preserved (StreamReader decodes UTF-8 correctly; BOM absent here so no interference) | Identical | Same | Intentional |
| 4 | Multiline text | `b"line1\nline2\nline3"`, `text/plain` | All newlines preserved exactly (`ReadToEndAsync` performs no normalization) | Identical | Same | Intentional |
| 5 | Leading/trailing whitespace text | `b"  \n  hello  \n  "`, `text/plain` | Preserved exactly, no trimming (`PlainTextParser` never calls `.Trim()`) | Identical | Same | Intentional |
| 6 | One-page text PDF (constructible via `pypdf.PdfWriter` adding one text-bearing page, at fixture-authoring time) | Programmatic, ASCII text content | One flattened line (all words space-joined), no internal line breaks preserved, `.Trim()`-ed | Identical text-layer result (same algorithm); MAF additionally evaluates the OCR heuristic first but a real text page comfortably exceeds 20 chars/page, so the deterministic result is returned | Same observable output | Intentional (word-join) as coded; classified `ACCIDENTAL_LIBRARY_BEHAVIOR` for the *line-collapsing side effect* specifically (SS9) — this capability's v1 will not replicate the line-collapse |
| 7 | Multi-page PDF (3 pages, distinct text per page) | Programmatic | Pages joined with one blank line between each, in order, all internal line breaks within each page collapsed to spaces, whole result trimmed | Identical (text-layer path) | Same | Same classification as #6 |
| 8 | PDF containing a blank page (e.g., page 2 of 3 has no text) | Programmatic | Blank page contributes nothing to the flattened output — invisible; only 2 blank-line-separated blocks appear even though 3 pages exist | Identical, unless the *whole* PDF's average falls under the OCR threshold (unlikely for 2 real pages of text among 3) | Same (assuming the other two pages carry normal text) | `ACCIDENTAL_LIBRARY_BEHAVIOR` — a byproduct of flattening (SS9); v1's page-aware design instead represents this fixture's blank page as `ParsedPage(index=1, text="")`, preserving the true 3-page structure |
| 9 | PDF with Unicode text | Programmatic, non-ASCII glyphs | PdfPig decodes embedded font encoding to Unicode text; output preserved as extracted (exact fidelity depends on the PDF's font/encoding, not on this parsing code) | Identical | Same | Intentional (library-dependent fidelity, not a DocuMind code choice either way) |
| 10 | Image-only/scanned PDF (a PDF with a rasterized page image and no text layer) | Programmatic (embed a page image, no text objects) | `PdfDocumentParser` (SK) returns `""` (all pages are blank text) — the document is silently ingested with **zero chunks**, no error, no warning | `PdfDocumentParser` (MAF) hits the `pageCount>0 && text.Length < pageCount*20` branch and falls back to OCR — a real vision-model call | **Different** — this is precisely the gap identified in §4: SK has no considered "no OCR" decision, it simply silently degrades | SK path: **DEFECT** (silent, unsignaled data loss); MAF path: **INTENTIONAL_BEHAVIOR** for invoking OCR at all, but **UNDECIDED** regarding whether the 20-chars/page threshold itself is a considered value or an arbitrary constant (no comment or evidence justifies the specific number 20) |
| 11 | Malformed PDF (truncated/corrupt byte stream, not a valid PDF at all) | Programmatic (e.g., `b"%PDF-1.4\ncorrupted garbage"`) | `PdfDocument.Open` throws; exception type and message are PdfPig-internal | Same — MAF's `ExtractTextLayer` calls the identical `PdfDocument.Open`, throwing before the OCR heuristic is ever reached | Same (both throw, uncaught, at the same call) | `UNDECIDED — REQUIRES LIVE VERIFICATION` for the exact PdfPig exception type; the *fact* that both throw uncaught, unclassified exceptions is confirmed by source reading, independent of the exact type |
| 12 | Encrypted/password-protected PDF | Programmatic (e.g., via `pypdf.PdfWriter.encrypt(...)` at fixture-authoring time, or a minimal hand-built encrypted PDF) | `PdfDocument.Open` most likely throws a PdfPig-specific encryption-related exception (PdfPig does have some encryption support, but a fixture using an unsupported encryption scheme or simply not supplying credentials would fail) | Same call path | Same (uncaught exception, uncategorized by DocuMind code either way) | `UNDECIDED — REQUIRES LIVE VERIFICATION` for the exact exception type/whether PdfPig can open *any* encrypted PDF without a password; the DocuMind code itself makes no attempt to distinguish this case regardless of the exact mechanism |
| 13 | Unsupported extension/content type (e.g., `application/zip`) | N/A — just a `contentType` string | `DocumentParserDispatcher.GetParser` throws `NotSupportedException` naming the unmatched content type and listing registered parser class names | Identical (`DocumentParserDispatcher` is byte-for-byte identical in both repos) | Same | Intentional |
| 14 | Empty PDF (zero pages, if constructible) | Programmatic (a minimal valid PDF with an empty page tree — constructible via most PDF-writing libraries, though some may refuse to write a literally zero-page document, in which case a 1-page PDF with a blank page substitutes for #8's purpose and this case is noted as possibly not independently constructible) | SK: `pdf.GetPages()` yields nothing, result `""`, zero chunks, no error | MAF: `pageCount == 0`, always fails the OCR-threshold check, falls to `ExtractViaVisionAsync`, which iterates zero rasterized images and returns `""` — a wasted OCR-path invocation that does nothing observable | Same *output* (`""`), different *internal path taken* (MAF makes a vacuous OCR attempt SK never would) | SK: **DEFECT** (silent empty success, same as #10); MAF: **ACCIDENTAL** (the zero-page case unnecessarily but harmlessly enters the OCR branch — not a considered decision, just a consequence of the `pageCount > 0` guard's phrasing) |
| 15 | Very large PDF/document (e.g., 1,000+ pages) | Programmatic generation, or a large public-domain document — **benchmark scenario only, not an SLA**, per this task's explicit instruction | No special handling either way — both repos fully process every page in a single synchronous/buffered pass; larger input means proportionally more time and memory, with no chunked/streaming behavior at any point | Same, plus MAF's extra full-byte-array buffering step | Same shape, no distinct behavior to characterize beyond scale | Not applicable (performance-only, no correctness claim) |

No customer/private DocuMind documents were used or needed — every fixture above is either trivial literal bytes or a small, programmatically-constructible PDF.

---

## 24. Extraction assessment cross-references

The parent assessment (`DOCUMIND-EXTRACTION-ASSESSMENT.md`) is updated minimally (see the accompanying diff) to reflect: the OCR-boundary finding hardening from "deferred, low priority" to "explicitly excluded from `document.parsing` v1, with a leaning-but-undecided future identity"; the first concrete runtime-dependency expectation for `legoai-document` (currently documented as "zero dependencies," which Batch 1 satisfied and this batch's *design* does not yet change); and a risk entry for the client-declared-content-type / silent-decoding-corruption defect found in both oracles.

---

## 25. Risks

| Risk | Mitigation |
|---|---|
| Line-break-preservation decision (SS9) diverges from both oracles and has zero existing tests to validate against | Treated explicitly as a *deliberate, justified* divergence, not a silent one; flagged for characterization testing before implementation, and its cross-capability effect on Chunking's word counts is called out explicitly (SS9) rather than discovered later |
| Exact PdfPig exception types for malformed/encrypted PDFs are unverified (no live execution performed) | Recorded as `UNDECIDED — REQUIRES LIVE VERIFICATION` (SS23, fixtures #11-12) rather than guessed; recommended as a concrete pre-implementation task |
| `pypdf`'s exact text-extraction fidelity (word ordering, whitespace handling) for complex PDFs is not yet empirically compared against PdfPig's | This is exactly why SS6 insists PdfPig semantics are not canonical — v1's *contract* (page-aware, line-preserving text) is defined independently of any one library's quirks; conformance against the contract, not byte-parity with PdfPig, is the bar |
| The 20-characters-per-page OCR-fallback threshold in MAF is unexplained/possibly arbitrary | Irrelevant to this batch's scope (OCR is excluded), but flagged so it is not silently absorbed into a future OCR capability's design as if it were a considered value |
| No file-size/resource limit exists at any layer today | Explicitly deferred to a future governed Execution/Resource-Policy responsibility (SS16); not fabricated here |
| A future `pypdf` addition will be `legoai-document`'s first runtime dependency, changing its "zero dependencies" status established in Batch 1 | Expected and consistent with Batch 1's own design (`CHUNKING-CAPABILITY-DESIGN.md` §"Independence from AI/model/agent frameworks" already anticipates "future capabilities... introduce their own, separately scoped dependencies only as each capability is actually implemented"); the parent assessment is updated to reflect this expectation (§24) |

---

## 26. Implementation gate

```text
READY_TO_IMPLEMENT_DOCUMENT_PARSING = NO
```

**Blockers:**

1. **Live verification of PdfPig's exact exception types for malformed and encrypted PDFs has not been performed** (§23, fixtures #11-12) — needed to confirm `MalformedDocumentError`/`EncryptedDocumentError` can be raised on genuinely distinguishable conditions once a Python library is actually exercised, and to confirm the chosen Python library (`pypdf`, tentatively) raises comparably distinguishable exceptions for the same fixture set.
2. **The line-break-preservation decision (§9) has not been characterization-tested against real PDF fixtures** — it is a well-reasoned design decision, not yet an empirically verified one, since no fixtures have actually been run through any parser (C# or Python) in this batch.
3. **`pypdf` has not been added to `packages/legoai-document`'s dependencies, and its actual API surface (`PdfReader`, page iteration, `extract_text()` behavior, exception classes) has not been confirmed against the version that will actually be pinned** — the dependency recommendation (§17) is a licensing/maintenance-based decision, not yet a verified API-fitness one.
4. **The 15 fixtures in §23 exist only as a design table, not as committed fixture files or executable tests.**

**Already resolved (not blockers):**

- Capability identity, v1 scope, and deferred scope (§5-7).
- The three-concerns separation (§8) and the request/result/entity separation (§9-10).
- Input representation (§11 — Option C, bytes + closed enum).
- Format-selection mechanism (§12 — closed `DocumentFormat` enum, no sniffing).
- Error model shape (§13 — four exceptions, no deeper hierarchy).
- OCR boundary decision (§14 — excluded from v1; future identity leaning recorded, not committed).
- Determinism declaration (§15).
- Security assumptions documented without overclaiming (§16).
- Dependency *direction* (Adapter-free, no Core dependency, §19) — though not the dependency *addition* itself (blocker 3).
- Package placement (§19 — confirmed, no new distribution, no Core change, no architectural contradiction found).
- Interaction with Chunking (§20 — one-directional composition, no cross-import).
- Versioning triggers identified in advance (§22).

Once blockers 1-4 are resolved — via a short, concrete pre-implementation task that adds `pypdf` to the dev environment, writes the fixtures in §23 as real files/bytes, and runs them through both a prototype `pypdf`-based parser and (where feasible) the existing C# parsers to confirm exact exception types — this gate should be re-evaluated and can reasonably flip to `YES` without further architectural work, exactly as Batch 1's three blockers were resolved by a narrow follow-up decision rather than a redesign.
