# Document Parsing Capability — Implementation Design

**Document:** `planning/documind/DOCUMENT-PARSING-CAPABILITY-DESIGN.md`
**Status:** AUTHORIZED — IMPLEMENTED (`document.parsing` in `packages/legoai-document/src/legoai_document/parsing/`)
**This is NOT a canonical LegoAI Core specification.** It defines a single proposed reusable **Document Capability Pack** capability, derived from DocuMind evidence, subordinate to and constrained by (but not amending) `intent.md`, `SPEC.md`, `ARCHITECTURE.md`, `CONTRACTS.md`, and the accepted ADRs.
**Parent documents:** [`planning/DOCUMIND-EXTRACTION-ASSESSMENT.md`](../DOCUMIND-EXTRACTION-ASSESSMENT.md), [`planning/documind/CHUNKING-CAPABILITY-DESIGN.md`](CHUNKING-CAPABILITY-DESIGN.md) (Batch 1, complete and accepted — consumed here only as a downstream API, not modified)
**Batch 1 status:** `document.chunking` remains untouched by this document.
**Live-verification evidence:** [`planning/documind/parsing-verification/`](parsing-verification/) — fixtures, verification scripts, and captured `results-*.txt` outputs backing every finding in this document tagged `VERIFIED`. See §1a below for methodology.

---

## 1a. Live verification methodology (this pass)

The findings in §11-14, §17, §23, and §26 below were previously either derived-with-high-confidence from source reading or explicitly marked `UNDECIDED — REQUIRES LIVE VERIFICATION`. This pass closes that gap with real, reproducible execution:

- **`pypdf` 6.19.0** was installed in an isolated verification venv (never added to `legoai-document`'s own dependencies) and exercised against 16 fixtures via `planning/documind/parsing-verification/py/verify_pypdf.py`.
- **DocuMind-SK's actual `PdfDocumentParser`/`PlainTextParser`** were exercised, unmodified, via a throwaway console app that project-references `DocuMind-SK`'s `DocuMind.Core`/`DocuMind.Domain` projects read-only (`parsing-verification/dotnet-sk/Verify/`).
- **DocuMind-AgentFramework's actual `PdfDocumentParser`/`PlainTextParser`** were exercised the same way (`parsing-verification/dotnet-maf/Verify/`). The OCR fallback branch was exercised only with an offline, canned `IVisionExtractionService` stub, confirming *whether* the branch is reached, never invoking a real network/paid model call — OCR content quality remains explicitly out of scope (§14).
- Every fixture is tiny, synthetic, programmatically generated, and non-private (`parsing-verification/fixtures/`, `generate_fixtures.py`).

Every claim below tagged **VERIFIED** was produced by one of these three runs, captured in `parsing-verification/results-{pypdf,sk,maf}.txt`. Claims tagged **DESIGN DECISION** are choices made given the verified evidence, not facts the evidence alone determines. Claims tagged **RESIDUAL RISK** are known, accepted gaps this verification does not close.

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

### Exception mapping — VERIFIED, fully resolved

Live verification (`parsing-verification/results-pypdf.txt`) confirms `pypdf` 6.19.0 exposes exactly the exception granularity needed, with no guessing required:

| pypdf exception (verified) | MRO (verified) | Fixture that produced it | Maps to |
|---|---|---|---|
| `pypdf.errors.PdfStreamError` | `PdfStreamError → PdfReadError → PyPdfError → Exception` | Truncated PDF (`"Stream has ended unexpectedly"`) | `MalformedDocumentError` |
| `pypdf.errors.PdfReadError` | `PdfReadError → PyPdfError → Exception` | Garbage/no-xref PDF (`"startxref not found"`) | `MalformedDocumentError` |
| `pypdf.errors.FileNotDecryptedError` | `FileNotDecryptedError → PdfReadError → PyPdfError → Exception` | Encrypted PDF, no password / wrong password, raised on `.pages` access or `.extract_text()` | `EncryptedDocumentError` |
| (no PDF-library exception at all — a plain Python `UnicodeDecodeError`) | `UnicodeDecodeError → ValueError → Exception` | Invalid UTF-8 bytes declared as `PLAIN_TEXT`/`MARKDOWN`/`HTML` | `MalformedDocumentError` |

**VERIFIED — `FileNotDecryptedError` is a subclass of `PdfReadError`, so it MUST be caught first (more specific before more general) to correctly discriminate encrypted-from-generically-malformed** — otherwise a broad `except PdfReadError` would silently swallow the encrypted case as a generic malformed one. `PdfReader(...)` construction itself does **not** raise for an encrypted PDF (VERIFIED — it succeeds and sets `is_encrypted = True`); the exception is only raised lazily, the first time `.pages` or `.extract_text()` is accessed without a valid password.

**DESIGN DECISION — no blanket `except Exception`.** Per instruction, only the three known `pypdf` exception types above are caught explicitly; any other exception from `pypdf` (or elsewhere) is allowed to propagate un-wrapped rather than being silently reclassified, using exception chaining where a pack-local exception is raised in response to a caught one:

```python
try:
    reader = PdfReader(io.BytesIO(request.content))
    pages = list(reader.pages)  # FileNotDecryptedError raised here if encrypted
except FileNotDecryptedError as exc:
    raise EncryptedDocumentError(
        "PDF is encrypted and cannot be read without a valid password"
    ) from exc
except PdfReadError as exc:  # includes PdfStreamError (subclass)
    raise MalformedDocumentError(f"PDF could not be parsed: {exc}") from exc
```

For text-family formats:

```python
try:
    text = request.content.decode("utf-8")  # strict -- see SS "Text decoding semantics"
except UnicodeDecodeError as exc:
    raise MalformedDocumentError("content is not valid UTF-8") from exc
```

`raise ... from exc` (exception chaining, PEP 3134) preserves the original `pypdf`/stdlib exception as `__cause__` for diagnostics, while the public API surface exposes only the four pack-local exception types — no raw `pypdf` exception class is ever part of `document.parsing`'s public contract, per instruction.

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

### VERIFIED — a new, concrete finding: the 20-chars/page heuristic misfires on a genuinely valid, mostly-textual PDF

Live verification (`parsing-verification/results-maf.txt`) surfaced something the source-reading pass in the previous design gate could not: fixture `10_blank_page_middle.pdf` — three pages, two with normal text ("First page has text." / "Third page has text.") and one genuinely blank page in the middle — **triggers MAF's OCR fallback**. The deterministic text-layer extraction yields 44 characters over 3 pages (an average of ~14.7 chars/page), which falls below the `>= 20` threshold, even though **two of the three pages have perfectly good, real text** and only one page is genuinely blank (a normal, unremarkable document structure — e.g., a report with an intentional blank separator page). This was confirmed by instrumenting the verification harness's stub `IVisionExtractionService` to throw if invoked for this fixture — it *was* invoked.

This is stronger evidence than the earlier, source-reading-only analysis provided: the threshold is not merely "possibly arbitrary" (§25 of the original design gate) — it is **demonstrably too aggressive for ordinary documents containing even one blank or sparse page**, meaning MAF's current oracle would route a real, valid, English-language multi-page document through an unnecessary (and, in production, costly and latency-adding) OCR call. This is now recorded as a confirmed **DEFECT** in the oracle's heuristic, not merely an unexplained constant — and it further strengthens (rather than merely reiterates) the decision to exclude any per-page-average text-density heuristic from `document.parsing` v1 entirely. A future `document.ocr`-composing workflow would need a materially better trigger condition than "average characters per page" if it wants to avoid this same false-positive class.

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

Document parsing is an **untrusted-input boundary** — analyzed explicitly, not assumed safe. Tags reflect this pass's live-verification status.

| Concern | Assessment | Status |
|---|---|---|
| Malformed files | `pypdf` VERIFIED to raise distinguishable `PdfStreamError`/`PdfReadError` for the two malformed fixtures tried (truncated, garbage/no-xref) — mapped to `MalformedDocumentError` (§13). No additional validation or sandboxing beyond this is claimed | VERIFIED (mapping) |
| Parser bombs (decompression bombs, deeply nested PDF object graphs) | **Not defended against**, and not tested for in this pass (constructing a genuine parser-bomb fixture safely was judged out of scope for a design-verification gate). This is a known category of PDF-library vulnerability class; this design does not claim protection. The repository's own `ADR-012` ("Isolation mechanism for expanded Plugin threat scope") is the more appropriate future home for this, and it remains Proposed/non-binding today | RESIDUAL RISK |
| Oversized documents / resource exhaustion | No size limit is enforced by this capability (matching the oracle, which also has none at the application level, VERIFIED by source reading in the prior pass). Treated as a governed Execution/Resource-Policy responsibility (SPEC §4.10) to be enforced **before** this capability is invoked | RESIDUAL RISK |
| Embedded objects / JavaScript / interactive actions | Out of scope by construction: this design only ever performs *text extraction* via `pypdf`'s `extract_text()`, never interactive rendering or script execution. Not independently verified in this pass (no fixture with embedded JavaScript was constructed), but consistent with `pypdf`'s documented scope as a manipulation/extraction library, not a rendering engine | DESIGN DECISION (scope), not independently verified |
| Filesystem/path injection | Not applicable — the bytes-based input decision (§11) never accepts a caller-supplied filesystem path | DESIGN DECISION (closed off by construction) |
| External references (network fetches triggered by content) | Not applicable in v1 — no HTML/Markdown structural interpretation occurs (§6, and §18a's strict-UTF-8-decode-only confirmation); content is treated as opaque text | DESIGN DECISION |
| Encrypted documents | **VERIFIED**: `PdfReader` construction succeeds silently for an encrypted PDF (does not raise); `FileNotDecryptedError` is raised only lazily, on first page/text access. Detected and reported as `EncryptedDocumentError` (§13) — an improvement over the oracle, which VERIFIED throws an uncaught `PdfDocumentEncryptedException` with no distinct handling. No attempt is made to decrypt, brute-force, or otherwise process an encrypted document | VERIFIED |
| Memory limits | Both DocuMind oracles VERIFIED to fully buffer documents into memory (MAF explicitly via `CopyToAsync`/`ToArray()`, confirmed in prior source-reading pass); this design's bytes-based contract (§11) shares that characteristic by construction | DESIGN DECISION (accepted tradeoff) |
| Parser library vulnerabilities | Standard hygiene (pinned version, monitored advisories) recommended; `pypdf` 6.19.0's own advisory history was not independently audited in this pass beyond the license/maintenance research in §17 | RESIDUAL RISK |
| Content-type/format trust | A caller can still declare the *wrong* (but validly-shaped) `DocumentFormat` for real content; format selection is a closed enum (§12) but content is never sniffed against the declared format | RESIDUAL RISK |
| Invalid-UTF-8 silent corruption | **VERIFIED as a real defect in both oracles** (§18a) and **closed** by this design's strict-UTF-8-decode decision (raises `MalformedDocumentError` instead of silently substituting replacement characters) | VERIFIED + closed by design decision |

No sandboxing, resource isolation, malware scanning, PDF sanitization, CPU isolation, or memory quota is claimed anywhere in this design. Hostile PDFs, resource exhaustion, pathological object graphs, and very large content streams remain explicit residual risks, to be bounded later by LegoAI's Resource/Execution controls (SPEC §4.10, and `ADR-012` once accepted), not by this capability itself.

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

Sources consulted for the initial (non-live) research: [Python PDF library comparison (2026)](https://www.nutrient.io/blog/best-python-pdf-libraries/), [PyMuPDF vs pdfplumber (2026): the speed-vs-license tradeoff](https://pdfmux.com/blog/pymupdf-vs-pdfplumber/), [pdfplumber vs PyMuPDF vs pypdf](https://subhajitbhar.com/blog/pdf-extraction/pdfplumber-vs-pymupdf-vs-pypdf2/), [PyMuPDF PyPI license notice](https://pypi.org/project/pymupdf/).

### VERIFIED — installed-package metadata (this pass)

`pypdf` was actually installed (`uv venv --python 3.14`, `uv pip install pypdf`) and its metadata inspected directly, not assumed from PyPI's web page:

| Property | VERIFIED value |
|---|---|
| Version resolved | `6.19.0` (latest at verification time) |
| `License-Expression` (SPDX metadata field) | `BSD-3-Clause` — confirms the web-research finding directly from the installed package, not secondhand |
| Native/compiled artifacts | **None** — confirmed no `.pyd`/`.so` files anywhere under the installed package tree; `Summary` metadata self-describes as "A pure-python PDF library" |
| `Requires-Python` support | `3.14` explicitly listed as a supported classifier (`Programming Language :: Python :: 3.14`), alongside 3.9-3.13 |
| Runtime dependencies (base install, no extras) | **Zero mandatory dependencies** on Python ≥3.11 (the only unconditional entry, `typing_extensions >= 4.0`, is gated to `python_version < '3.11'` and therefore does not apply on 3.14; all other `requires-dist` entries are `extra ==` optional groups — `crypto`, `image`, `full`, `dev`, `docs`, `fonts`, `rtl-text` — none pulled in by a base install) |

**DESIGN DECISION — no optional extras are needed for v1.** `pypdf`'s `crypto`/`cryptodome` extras add support for additional PDF encryption algorithms beyond what the base install handles; the verified `FileNotDecryptedError` behavior (§13) already covers v1's requirement (detecting and reporting encryption, not decrypting arbitrary schemes) without them. The `image`/`fonts`/`rtl-text` extras are for PDF *creation*/advanced-layout features, irrelevant to text extraction. Installing only the base package (zero mandatory dependencies) is therefore both sufficient and consistent with `legoai-document`'s minimal-dependency posture.

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

## 18a. Live-verified semantic decisions

### Text decoding semantics — VERIFIED defect confirmed, DESIGN DECISION made

**VERIFIED (both C# oracles, `parsing-verification/results-{sk,maf}.txt`):** feeding invalid UTF-8 bytes (fixture `15_invalid_utf8.txt`, `b"\xff\xfe\x00\x80not valid utf-8"`) through `PlainTextParser` in **both** SK and MAF does **not** throw — `StreamReader(fileStream, Encoding.UTF8)` silently substitutes U+FFFD replacement characters for the invalid bytes and returns a corrupted-but-successful string (`"耀潮⁴慶楬⁤瑵ⵦ�"` — mangled, not an error). This confirms, with live evidence rather than inference, the silent-corruption defect flagged in §12/§25 of the original design pass.

**VERIFIED (Python stdlib, `parsing-verification/results-pypdf.txt` run alongside):** `bytes.decode("utf-8")` (strict mode, the default) raises `UnicodeDecodeError` for the same invalid byte sequence — `UnicodeDecodeError('utf-8', b'\xff\xfe\x00\x80not valid utf-8', 0, 1, 'invalid start byte')` — and this is confirmed to be a `ValueError` subclass (`isinstance(e, ValueError) == True`). All seven valid-UTF-8 text fixtures (empty, ASCII, Unicode, multiline, leading/trailing whitespace, Markdown, HTML) decode via strict `utf-8` with byte-for-byte content fidelity confirmed (exact string equality checked programmatically, not eyeballed).

**DESIGN DECISION (adopted as instructed, confirmed not contradicted by evidence):** for `PLAIN_TEXT`, `MARKDOWN`, and `HTML`, v1 semantics are exactly:

```text
content bytes → UTF-8 strict decode → text preserved as-is
```

No replacement decoding, no HTML stripping, no Markdown rendering/sanitization, no whitespace or newline normalization. Invalid UTF-8 bytes raise `MalformedDocumentError` (chained from the underlying `UnicodeDecodeError`, per §13). This is a **deliberate divergence from both oracles**, not a replication — the oracles' silent corruption is the behavior being fixed, not preserved.

### Page-aware semantics — VERIFIED against real generated PDFs

**VERIFIED:** `pypdf`'s `PdfReader(io.BytesIO(...)).pages` is a proper sequence — `len()` and integer indexing both confirmed working — and `PageObject.extract_text()` **always returns `str`, never `None`**, confirmed across every fixture tried (a genuinely blank page, an image-only page, and normal text pages all returned `str`, with the blank/image-only ones returning `""` specifically, not `None`). This directly resolves what would otherwise have been a defensive-`None`-check question in the implementation.

**DESIGN DECISION (indexing):** zero-based, per repository convention — Batch 1's `Chunk.index` is zero-based (confirmed by re-reading `CHUNKING-CAPABILITY-DESIGN.md` §3.1/§12 and its shipped implementation in `packages/legoai-document/src/legoai_document/chunking/values.py`), and `pypdf`'s own `reader.pages` is itself zero-indexed. `ParsedPage.index` being zero-based is therefore consistent both with this repository's own established convention and with the underlying library's native indexing — no conversion/off-by-one translation layer is needed between them.

**VERIFIED (page ordering and non-merging):** fixture `09_multi_page_text.pdf` (3 distinct pages, each with unique, page-identifying text) round-tripped through `pypdf` with each page's `extract_text()` returning exactly and only that page's own content, in the correct order (`page 0` → "Page one...", `page 1` → "Page two...", `page 2` → "Page three..."), with no cross-page merging or reordering observed.

### Blank-page behavior — VERIFIED and confirmed against the design's stated preference

**VERIFIED:** fixture `10_blank_page_middle.pdf` (page 0 and page 2 have text, page 1 has no text objects at all) — `pypdf` reports **3 pages** (`len(reader.pages) == 3`), and `reader.pages[1].extract_text()` returns `""` (confirmed `is_none=False`, `is_empty_str=True`) rather than raising or omitting the page. This directly supports, with live evidence, §9/§13 of the original design's stated preference:

```text
ParsedPage(index=1, text="")
```

**not** page omission — the page-index/count correspondence with the source PDF's true physical structure is preserved exactly, which is the entire point of the page-aware provenance goal (§9). Note this is a `pypdf`-level confirmation of the *library's* behavior; `document.parsing`'s own implementation must still explicitly choose to include every page pypdf reports (including empty-text ones) in `ParsedDocument.pages` rather than filtering them out — that remains a straightforward implementation instruction, not something the library forces either way.

### Image-only PDF behavior — VERIFIED, decision confirmed

**VERIFIED:** fixture `12_image_only.pdf` (a syntactically valid PDF containing only a rasterized image, no text objects) — `PdfReader` construction succeeds, `len(reader.pages) == 1`, and `extract_text()` returns `""` (confirmed empty string, not `None`, not an exception). No hang, no error, no attempted OCR of any kind — `pypdf` performs pure, deterministic text-layer extraction and correctly reports "no text found" as a successful, empty result.

**DESIGN DECISION (confirmed, not contradicted):**

```text
A syntactically valid image-only PDF returns ParsedDocument with preserved pages,
whose text is the empty string -- NOT a MalformedDocumentError.
```

`empty extracted text ≠ parsing failure`. This is recorded explicitly so a future implementer is not tempted to treat "no text on this page" as an error condition — it is a normal, valid, deterministic outcome. OCR (recovering text from such a page) remains entirely out of v1 scope and belongs to a future composed capability (§14).

### Line-break / page-boundary guarantee — VERIFIED, and a materially better finding than expected

**VERIFIED — the single most significant finding of this verification pass:** `pypdf`'s `extract_text()` **already preserves intra-page line breaks naturally**, with no special handling needed. Fixture `09_multi_page_text.pdf` (each page written with two separate text-drawing operations, i.e., two visual lines per page) produced, per page: `'Page one line A\nPage one line B\n'` — a literal `\n` between the two lines, plus a trailing `\n`. This means the line-break-preservation design decision from the original design gate (§9 — "v1's PDF text-layer extraction preserves natural line breaks within a page... a deliberate, documented divergence from the oracle") is **not an extra implementation burden layered on top of `pypdf`** — it is `pypdf`'s own default behavior, in direct contrast to PdfPig's word-join approach that the C# oracle specifically chose. Choosing `pypdf` and simply calling `extract_text()` per page, without any additional post-processing, already satisfies the design decision.

**DESIGN DECISION — the capability's guarantee is scoped precisely, per instruction:**

```text
document.parsing v1 GUARANTEES:
  - page separation (each physical page's text is independently accessible)
  - extracted text order as provided by the parsing library (pypdf), including
    its natural line-break placement
  - no additional LegoAI-side normalization, stripping, or reformatting of
    extracted text

document.parsing v1 does NOT guarantee:
  - reconstruction of original visual layout, columns, or multi-column reading order
  - reconstruction of tables or their cell/row/column structure
  - exact original line-wrap geometry (pypdf's line breaks reflect its own text-
    positioning heuristics, not a promise of pixel-perfect fidelity to the source)
```

This distinguishes the **provider/library extraction result** (`pypdf`'s specific behavior, which could change if the library's internal heuristics change between versions, or if a future `CapabilityVersion` swaps libraries per §22's conformance-preservation requirement) from the **capability's semantic guarantee** (page separation and no LegoAI-introduced distortion) — exactly the distinction §6/§22 already required this document to maintain.

### Dependency declaration strategy — resolved per existing repository policy, not invented

**Policy found (not invented):** every existing `pyproject.toml` in this repository (`legoai-reference` and `legoai-document`, both examined directly) uses **exact `==` pins** for its `[dependency-groups] dev` tooling (`"pytest==9.1.1"`, `"mypy==2.3.1"`, `"ruff==0.16.8"`, etc.), while `uv.lock` separately records the full exact resolution. Neither existing `pyproject.toml` has ever declared a `[project.dependencies]` entry for a real runtime library (`dependencies = []` in both) — **this repository has no established precedent for runtime-library version-range syntax**, because Batch 1 introduced zero runtime dependencies.

**DESIGN DECISION, applying ordinary PyPA convention in the absence of a local override (not a new policy invented for this task):** the exact `==` pinning convention observed applies to **dev-tooling reproducibility** (a deliberate, solo-developer-burden-reducing choice per ADR-002's own reasoning), which is a different concern from a **published library's compatibility constraint** — the latter is what other consumers' dependency resolvers see and must not be pinned so tightly that it forces version conflicts across an ecosystem. Recommended, once implementation is authorized:

```toml
[project]
dependencies = ["pypdf>=6.19.0,<7"]
```

— `>=6.19.0` because that is the exact verified-working version (§17); `<7` because `pypdf` follows a major-version-for-breaking-changes convention, so excluding an unreleased, unverified major version is the conservative default. `uv.lock` continues to record the exact resolved version (`6.19.0` today) for this repository's own reproducible dev/build environment, exactly as it already does for the dev-tooling group — the two concerns (compatibility range vs. exact resolution) remain properly separated, per instruction.

---

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

## 23. Characterization fixtures — VERIFIED (live execution, this pass)

**Methodology (updated from the original design pass):** all 16 fixtures below were actually generated (`parsing-verification/py/generate_fixtures.py`) and actually run against both DocuMind repos' real, unmodified parsers and against `pypdf` 6.19.0 (`parsing-verification/results-{sk,maf,pypdf}.txt`). Nothing below is predicted from source reading alone anymore — every SK/MAF/`pypdf` result is a captured, reproducible observation. The two items the original design gate flagged `UNDECIDED — REQUIRES LIVE VERIFICATION` (exact malformed/encrypted exception types) are now fully resolved.

| # | Fixture | Construction | VERIFIED SK result | VERIFIED MAF result | VERIFIED pypdf result | Classification |
|---|---|---|---|---|---|---|
| 1 | Empty UTF-8 text file | `b""` | `""`, length 0 | Identical | `""` (decode) | Intentional |
| 2 | ASCII text | `b"Hello world"` | `"Hello world"` | Identical | Identical | Intentional |
| 3 | Unicode UTF-8 text | `"café 日本語 😀"` encoded | Exact string preserved (`café 日本語 😀` surrogate-pair JSON repr) | Identical | Exact string preserved (`in` membership checks confirmed) | Intentional |
| 4 | Multiline text | `b"line1\nline2\nline3"` | Preserved exactly | Identical | Preserved exactly | Intentional |
| 5 | Leading/trailing whitespace | `b"  \n  hello  \n  "` | Preserved exactly, no trimming | Identical | Preserved exactly (`==` equality confirmed) | Intentional |
| 6 | Markdown, opaque | `# Heading\n\n*emphasis*...` | Preserved verbatim, no rendering | Identical | N/A (pypdf not used for text formats) | Intentional |
| 7 | HTML, opaque | `<html><body>...` | Preserved verbatim, no tag stripping | Identical | N/A | Intentional |
| 8 | One-page text PDF | reportlab, 1 line | `"Hello world from page one."` (length 26, no trailing newline — `.Trim()`-ed) | Identical | `'Hello world from page one.\n'` (pypdf keeps a trailing `\n`; PdfPig-based code strips it via `.Trim()`) | Intentional, both correct for their own contract |
| 9 | Multi-page text PDF | reportlab, 3 pages, 2 lines on pages 1-2 | `"Page one line A Page one line B\r\n\r\nPage two line A Page two line B\r\n\r\nPage three only line"` — **intra-page lines joined with a single space** (PdfPig word-join), pages separated by `\r\n\r\n` | Identical | Per page: `'Page one line A\nPage one line B\n'`, `'Page two line A\nPage two line B\n'`, `'Page three only line\n'` — **intra-page lines separated by `\n`**, pages independently addressable | **Confirms §18a's key finding**: `pypdf` preserves line breaks pypdf's own extraction naturally; PdfPig's word-join in the DocuMind code discards them — this is a DocuMind-code artifact (§9), not a PdfPig limitation either (PdfPig can expose line structure through other APIs the code doesn't use) |
| 10 | PDF with a blank page in the middle (3 pages, page 2 blank) | reportlab, page 2 has zero text-drawing calls | `"First page has text.\r\n\r\nThird page has text."` — the blank page is **completely invisible**, no trace it ever existed | **Triggers the OCR fallback** — `10/44` chars over 3 pages = ~14.7 avg, below the 20/page threshold, so MAF's stub `IVisionExtractionService` was invoked (confirmed via the deliberately-throwing `NoCallVisionExtractionService` in the harness) | `len(reader.pages) == 3`; page 1 (index 1, the blank one) returns `''` (confirmed `is_none=False`, `is_empty_str=True`); pages 0 and 2 return their real text | SK: **DEFECT** (page silently erased, no trace). MAF: **DEFECT, newly confirmed live** (§14 — a legitimate 2-of-3-pages-textual document incorrectly routed to OCR). `pypdf`: confirms the page-aware design's blank-page representation is directly supported by the library with zero extra work |
| 11 | PDF with Unicode text | reportlab, `café naïve über` | `"Unicode: café naïve über"` — preserved correctly | Identical | Preserved correctly (`in` membership checks on café/naïve/über all `True`) | Intentional; both libraries handle this correctly |
| 12 | Image-only PDF (rasterized image, no text objects) | reportlab + Pillow, one drawn raster image, no text | `""`, length 0 — **document silently "succeeds" with zero extractable text, no error, no warning** | Falls back to OCR (stub invoked, confirmed `WasInvoked == True`; stub output returned, not a real model call) | `len(reader.pages) == 1`; `extract_text()` returns `''` (confirmed empty string, not `None`, no exception) | SK: **DEFECT** (silent, unsignaled empty result). MAF: **INTENTIONAL_BEHAVIOR** for invoking OCR here (this is exactly the case the heuristic is meant to catch). `pypdf`: confirms v1's chosen behavior (empty text, not an error) is correct and requires no special-casing |
| 13 | Malformed/truncated PDF (first third of a valid PDF's bytes) | Byte-truncation of fixture #8 | **THREW**: `UglyToad.PdfPig.Core.PdfDocumentFormatException`: *"Could not find the startxref within the last 452 characters."* | Identical exception (MAF calls the same `PdfDocument.Open` before its OCR heuristic is ever reached) | **THREW**: `pypdf.errors.PdfStreamError` (`PdfStreamError → PdfReadError → PyPdfError → Exception`): *"Stream has ended unexpectedly"* | Both ecosystems raise clean, well-named, distinguishable exceptions for this case — **RESOLVED**, no longer UNDECIDED. Both C# and Python map cleanly to `MalformedDocumentError` |
| 13b | Malformed PDF (syntactically garbage body, no valid xref at all) | Hand-written `b"%PDF-1.4\\nthis is not a real pdf body...\\n%%EOF"` | **THREW**: `UglyToad.PdfPig.Core.PdfDocumentFormatException`: *"Could not find the startxref within the last 49 characters."* | Identical | **THREW**: `pypdf.errors.PdfReadError` (`PdfReadError → PyPdfError → Exception`): *"startxref not found"* | Same resolution as #13 |
| 14 | Encrypted PDF (user + owner password set via `pypdf.PdfWriter.encrypt`) | `pypdf.PdfWriter`, user password `secret123` | **THREW**: `UglyToad.PdfPig.Exceptions.PdfDocumentEncryptedException`: *"The document was encrypted and none of the provided passwords were the user or owner password."* — thrown at `PdfDocument.Open`, immediately, no partial success | Identical (same call path, same exception, before the OCR heuristic) | `PdfReader(...)` construction **succeeds** (does not raise); `is_encrypted == True`; accessing `.pages` or `.extract_text()` **THROWS**: `pypdf.errors.FileNotDecryptedError` (`FileNotDecryptedError → PdfReadError → PyPdfError → Exception`): *"File has not been decrypted"*. `decrypt("wrong-password")` returns `0` (fail) and subsequent access still raises `FileNotDecryptedError`. `decrypt("secret123")` (the correct user password) returns `1` and subsequent `extract_text()` succeeds, returning the original text correctly | Both ecosystems distinguish encryption cleanly — **RESOLVED, no longer UNDECIDED**. Notable divergence: PdfPig raises at *construction*; `pypdf` raises lazily at *first access* — the v1 implementation must account for this by catching `FileNotDecryptedError` around page/text access, not only around `PdfReader(...)` construction (§13's mapping code reflects this) |
| 15 | Invalid UTF-8 bytes declared as a text format | `b"\xff\xfe\x00\x80not valid utf-8"` | **Did NOT throw** — `StreamReader(..., Encoding.UTF8)` silently substituted replacement characters: `"耀潮⁴慶楬⁤瑵ⵦ�"` (garbled, wrong, but no error) | Identical silent corruption | `bytes.decode("utf-8")` (strict) **THREW**: `UnicodeDecodeError('utf-8', b'\xff\xfe\x00\x80not valid utf-8', 0, 1, 'invalid start byte')`, confirmed `isinstance(exc, ValueError)` | **Confirms the defect (§18a) and validates the fix**: both C# oracles silently corrupt data; Python's own stdlib strict decoding — which this design adopts — correctly raises instead, mapped to `MalformedDocumentError` |

**Not re-verified in this pass (unchanged from the original design gate, both explicitly out of this task's required fixture list):** an "empty PDF, zero pages" case and a "very large document" performance benchmark. Neither blocks the exception-mapping or format-decision findings above; both remain minor, explicitly deferred items (§25).

No customer/private DocuMind documents were used — every fixture is either trivial literal bytes or a small, programmatically-constructed PDF, all captured in `parsing-verification/fixtures/`.

---

## 24. Extraction assessment cross-references

The parent assessment (`DOCUMIND-EXTRACTION-ASSESSMENT.md`) was updated minimally in the previous (design) pass to reflect: the OCR-boundary finding hardening from "deferred, low priority" to "explicitly excluded from `document.parsing` v1, with a leaning-but-undecided future identity"; the first concrete runtime-dependency expectation for `legoai-document`; and a risk entry for the client-declared-content-type / silent-decoding-corruption defect found in both oracles. This pass adds one further minimal update: the OCR-heuristic-misfire finding (§14, §23 #10) as a strengthened, live-verified version of that same risk entry, and the implementation-gate status change to `YES`.

---

## 25. Risks

| Risk | Status | Mitigation |
|---|---|---|
| Line-break-preservation decision (§9) diverges from both oracles | **Resolved, and turned out favorably** | VERIFIED (§18a, §23 #9): `pypdf`'s `extract_text()` preserves intra-page line breaks as its own default behavior — the design decision requires no special implementation effort, it falls out of choosing `pypdf` and calling its API normally |
| Exact PdfPig/`pypdf` exception types for malformed/encrypted PDFs were unverified | **Resolved** | VERIFIED live (§13, §23 #13-14): `PdfDocumentFormatException`/`PdfDocumentEncryptedException` (PdfPig, C#) and `PdfStreamError`/`PdfReadError`/`FileNotDecryptedError` (`pypdf`, Python) are all real, distinguishable, captured exception types with a settled mapping to the two pack-local exceptions |
| `pypdf`'s exact text-extraction fidelity for complex PDFs not empirically compared against PdfPig's | **Partially resolved; residual for complex layouts** | VERIFIED for the fixtures tested (§23): output differs from PdfPig by design (line breaks preserved vs. collapsed) and this is the intended, better behavior, not a defect to reconcile. Fidelity for genuinely complex layouts (multi-column, tables, rotated text) was not tested — this remains a residual risk for future, richer fixtures, not blocking v1's narrow scope |
| The 20-characters-per-page OCR-fallback threshold in MAF is unexplained/possibly arbitrary | **Confirmed worse than "unexplained" — now demonstrated to misfire** | VERIFIED live (§14, §23 #10): a genuine, ordinary 3-page document with only one blank page trips the threshold and is incorrectly routed to OCR. Irrelevant to this batch's scope (OCR is excluded from v1), but now a stronger, evidenced argument against ever reusing this specific heuristic in a future OCR capability |
| No file-size/resource limit exists at any layer today | Unchanged — explicit residual risk | Explicitly deferred to a future governed Execution/Resource-Policy responsibility (§16); not fabricated here |
| A future `pypdf` addition will be `legoai-document`'s first runtime dependency | Unchanged — expected, not yet applied | Constraint strategy resolved (§18a: `pypdf>=6.19.0,<7`); still not added to `pyproject.toml` in this batch (§14 hard stop of the live-verification task) |
| Parser-bomb / pathological-PDF resource exhaustion | Unchanged — explicit residual risk, not tested | Not evaluated in this pass (constructing such a fixture safely was judged out of scope for a design-verification gate); recorded in §16 as a residual risk for `ADR-012`'s future scope |

---

## 26. Implementation gate

```text
READY_TO_IMPLEMENT_DOCUMENT_PARSING = YES
```

All items the previous design gate listed as blockers are now resolved with live, reproducible evidence rather than predictions:

1. ~~Live verification of exact exception types for malformed and encrypted PDFs~~ — **Resolved.** Both PdfPig (C#) and `pypdf` (Python) exception types are captured and mapped (§13, §23 #13-14).
2. ~~Line-break-preservation decision untested against real PDF fixtures~~ — **Resolved.** Verified directly, and found to be `pypdf`'s own default behavior, not an extra implementation burden (§18a, §23 #9).
3. ~~`pypdf` API surface unconfirmed~~ — **Resolved.** `PdfReader(BytesIO)`, `.is_encrypted`, `.pages` (sequence, zero-indexed), `PageObject.extract_text() -> str` (never `None`), and `.decrypt(password)` are all confirmed against the actual installed 6.19.0 package (§17 VERIFIED metadata, §18a, §23).
4. ~~Fixtures exist only as a design table~~ — **Resolved.** All 16 fixtures exist as real, committed, reproducible files under `planning/documind/parsing-verification/fixtures/`, generated by `generate_fixtures.py`, and exercised by both the Python and C# verification harnesses.

**Gate criteria, re-checked against the instruction's exact list:**

- pypdf import/API verified — YES (§17, §18a).
- Malformed exception mapping verified — YES (§13, §23 #13-14).
- Encrypted behavior verified — YES (§13, §23 #14) — including the important nuance that `PdfReader` construction succeeds silently and the exception is raised lazily on first page/text access, now reflected in the mapping code (§13).
- Fixtures created and exercised — YES (§23, all 16, against real SK/MAF/`pypdf` runs).
- Page semantics settled — YES (§18a: zero-based, matching Batch 1's convention and `pypdf`'s own).
- Line/newline guarantee settled — YES (§18a: page separation + library-provided order guaranteed; visual layout/table/column reconstruction explicitly NOT guaranteed).
- Strict UTF-8 behavior settled — YES (§18a: strict decode, `MalformedDocumentError` on failure, verified against both valid and invalid fixtures).
- Image-only semantics settled — YES (§18a, §23 #12: empty text is a valid successful result, not an error).
- Dependency declaration strategy settled — YES (§18a: `pypdf>=6.19.0,<7` in `[project.dependencies]`, exact version in `uv.lock`, following existing repository convention rather than inventing one).
- No canonical contradiction — YES (unchanged from the original design gate; nothing in this verification pass touched or contradicted any canonical document, ADR, or Batch 1).

**Residual items that do not block `YES`** (carried forward as ordinary implementation-time considerations, not architectural blockers): complex-layout fidelity (multi-column/table PDFs) is untested; parser-bomb/resource-exhaustion defenses remain explicitly out of scope (§16); a true zero-page PDF and a large-document performance benchmark were not constructed in this pass (§23).

---

## 27. Implementation status (Batch 2 — complete)

**This is not a canonical Core specification change; it records what was built, matching the design above exactly, with no architectural deviation.**

`document.parsing` is implemented at `packages/legoai-document/src/legoai_document/parsing/{__init__.py, values.py, errors.py, api.py}`, alongside Batch 1's `chunking/` in the same distribution. Public surface: `DocumentFormat` (`TEXT`/`MARKDOWN`/`HTML`/`PDF`), `DocumentParsingRequest`, `ParsedPage`, `ParsedDocument` (all frozen/slotted dataclasses), `DocumentParsingError`/`UnsupportedDocumentFormatError`/`MalformedDocumentError`/`EncryptedDocumentError`, `parse_document()`, `flatten_pages()` — exactly the signatures in §18/§18a, no additions, no omissions.

**Dependency:** `pypdf>=6.19.0,<7` added to `[project.dependencies]`; `uv.lock` resolved and pinned to the exact verified `6.19.0`. This is `legoai-document`'s first runtime dependency; confirmed via a wheel build that `Requires-Dist: pypdf<7,>=6.19.0` is the only declared dependency, and via a clean-environment install that exactly two packages (`legoai-document`, `pypdf`) are installed — no `reportlab`/`pillow`/OCR/model-SDK ever entered the production dependency graph.

**Behavior implemented exactly as designed and verified:** strict UTF-8 decoding for `TEXT`/`MARKDOWN`/`HTML` (raising `MalformedDocumentError` chained from `UnicodeDecodeError` on invalid bytes); one `ParsedPage` per physical PDF page including blank/image-only pages (`text == ""`, never omitted); `FileNotDecryptedError` caught before the broader `PdfReadError` (correctly, since it is a subclass) and mapped to `EncryptedDocumentError`; `PdfStreamError`/`PdfReadError` mapped to `MalformedDocumentError`; no blanket `except Exception` anywhere; every raised pack-local exception is chained (`raise ... from exc`) to its underlying `pypdf`/stdlib cause; no `pypdf` type appears in the public API.

**Regression test for the DocuMind defect (§19 of the implementation task):** `test_blank_page_is_preserved_not_omitted` in `tests/unit/parsing/test_parse_pdf.py` uses the same `10_blank_page_middle.pdf` fixture that was live-confirmed (§14, §23 #10) to trip MAF's 20-characters-per-page OCR heuristic, and asserts the deterministic parser succeeds, preserves all three pages including the blank one, and (structurally, since no OCR/model/network dependency exists anywhere in this package) never invokes OCR.

**Test suite:** 41 new tests across `test_parse_text_like.py`, `test_parse_pdf.py`, `test_values_and_invariants.py`, `test_flatten_pages.py` (`tests/unit/parsing/`), reusing the same 16 fixtures from `planning/documind/parsing-verification/fixtures/` copied into `tests/fixtures/parsing/` so the package's test suite is self-contained. `tests/architecture/test_dependency_boundaries.py` was extended (not weakened): the former "zero runtime dependencies" assertion is now an explicit allowlist (`{"pypdf"}`), and `FORBIDDEN_ROOTS`/`ALLOWED_ROOTS` were extended to cover OCR SDKs and fixture-generation-only tooling (`reportlab`, `PIL`) that must never appear in production source. `tests/architecture/test_core_does_not_import_pack.py` required no changes (its scan already covers the whole Core tree).

**Verification results:** 268 passed, 64 skipped (unchanged skip set from Batch 1), 100% statement and branch coverage on both `chunking` and `parsing`; `mypy --strict` clean across 19 source files with zero `# type: ignore` needed for `pypdf`'s own types; `ruff check`/`ruff format --check` clean; LegoAI Core's own 150 tests and its mypy/ruff checks remain unaffected and green.

**Deviations from the approved design:** none of substance — only automatic `ruff format` whitespace reflow.

**Deferred (unchanged from §25/§26):** complex-layout (multi-column/table) fidelity untested; parser-bomb/resource-exhaustion defenses out of scope; zero-page-PDF and large-document performance benchmarks not constructed; a future `document.ocr` capability remains undesigned; DocuMind's confirmed MAF OCR-heuristic defect was recorded (§14, §23 #10; parent assessment) but **not fixed in DocuMind**, per instruction that both DocuMind repositories remain read-only reference oracles.
