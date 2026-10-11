# legoai-document

**Lego AI Document Capability Pack** — an optional, independently installable, first-party capability pack for document-processing applications built on the Lego AI Operating Layer.

This is **not** part of Lego AI Core. Core has no dependency on this package.
Parsing and chunking remain independently usable; embedding and answering use
Core Model values through caller-supplied governed callables. See
`planning/documind/CHUNKING-CAPABILITY-DESIGN.md` for the original extraction
rationale and `examples/documind` for the current public-host composition.

## Current capabilities

- **`document.chunking`** — deterministic, sliding-window word-count text chunking. Pure, stateless, effect-free: no I/O, no persistence, no network access, no external provider.
- **`document.parsing`** — deterministic text extraction for `TEXT`, `MARKDOWN`, `HTML` (strict UTF-8 decode, content preserved exactly as-is) and text-bearing `PDF` (one page of extracted text per physical PDF page, via [`pypdf`](https://pypi.org/project/pypdf/)). **No OCR, no vision models, no LLMs are used anywhere in this capability.** A blank or image-only PDF page returns empty text — that is a valid, successful result, never an error.

- **`document.embedding`** — chunk embedding through an injected governed callable.
- **`document.ingestion`** — document processing and local index storage.
- **`document.retrieval`** — hybrid vector/lexical search over `SQLiteRetrievalStore`.
- **`document.rerank`** — deterministic identity/truncation with a callable seam.
- **`document.answering`** — bounded context, governed chat and citations.

The package uses `pypdf` internally for parsing and standard-library SQLite for
the local retrieval store. It imports no model-provider SDK or workflow engine.
The retrieval/ingestion/answering signatures currently name the concrete SQLite
store; arbitrary storage substitution is not a supported Port contract. This
inventory describes implementation, not new quality or runtime qualification.

### `document.parsing`'s guarantees and limits

`document.parsing` guarantees: page separation (one `ParsedPage` per physical page, blank pages included, never omitted), stable zero-based page order, and text exactly as the underlying parsing library (`pypdf`) extracts it — with no additional LegoAI-side normalization, trimming, or reformatting.

It does **not** guarantee: reconstruction of the original visual layout, multi-column reading order, table/cell structure, font/style fidelity, or exact source line-wrap geometry. Complex PDF layouts (multi-column documents, tables) have not been characterized against this capability and may not extract in a naturally readable order.

### Relationship to `document.chunking`

`document.parsing` and `document.chunking` are independently usable and never import each other. A typical caller composes them itself:

```python
from legoai_document.parsing import (
    DocumentFormat,
    DocumentParsingRequest,
    parse_document,
    flatten_pages,
)
from legoai_document.chunking import ChunkingRequest, chunk_text

parsed = parse_document(
    DocumentParsingRequest(content=pdf_bytes, format=DocumentFormat.PDF)
)
chunks = chunk_text(ChunkingRequest(text=flatten_pages(parsed)))
```

Neither capability requires the other to be installed or used.

## Installation (development)

From the `legoai-document` directory:

```sh
uv sync --locked --group dev --no-install-project
uv sync --locked --group dev --no-build-isolation
```

Or, using an editable pip install into an existing environment:

```sh
pip install -e packages/legoai-document
```

## Minimal usage

```python
from legoai_document.chunking import ChunkingRequest, chunk_text

result = chunk_text(
    ChunkingRequest(text="some long document text ...", chunk_size=512, overlap=50)
)

for chunk in result.chunks:
    print(chunk.index, chunk.word_count, chunk.content[:40])
```

Invalid parameters (`chunk_size <= 0`, `overlap < 0`, or `overlap >= chunk_size`) raise `legoai_document.chunking.ChunkingValidationError` before any computation happens — they are never silently accepted.

```python
from legoai_document.parsing import (
    DocumentFormat,
    DocumentParsingRequest,
    parse_document,
)

with open("report.pdf", "rb") as f:
    content = f.read()

parsed = parse_document(
    DocumentParsingRequest(content=content, format=DocumentFormat.PDF)
)

for page in parsed.pages:
    print(page.index, repr(page.text[:60]))
```

Invalid parameters raise, without silently accepting bad input: `UnsupportedDocumentFormatError` for a format with no v1 realization, `MalformedDocumentError` for corrupt/truncated content or invalid UTF-8 in a text-like format, and `EncryptedDocumentError` for a PDF that needs a password (there is no password support in v1).

## Independence from AI/model/agent frameworks

`document.chunking` has **zero runtime dependencies**. `document.parsing` adds exactly one: [`pypdf`](https://pypi.org/project/pypdf/) (BSD-3-Clause, pure Python, no native/compiled component), used only for PDF text extraction — never exposed in this package's public API. Neither capability requires choosing, installing, or configuring a language model, an agent runtime, OCR, a vector store, or a database. Future capabilities added to this pack (embeddings, retrieval, etc.) are expected to introduce their own, separately scoped dependencies only as each capability is actually implemented — never speculatively, and never in a way that changes what installing an unrelated capability in this pack requires.

## Running the tests

From the `legoai-document` directory:

```sh
uv run --locked --no-sync python -m pytest
uv run --locked --no-sync python -m mypy src tests
uv run --locked --no-sync ruff check .
uv run --locked --no-sync ruff format --check .
```
