# legoai-document

**Lego AI Document Capability Pack** — an optional, independently installable, first-party capability pack for document-processing applications built on the Lego AI Operating Layer.

This is **not** part of Lego AI Core. Core has no dependency on this package, and this package depends on Core only where a specific capability genuinely needs it (see below — the current capability needs nothing from Core at all). See `planning/documind/CHUNKING-CAPABILITY-DESIGN.md` in the `legoai-reference` repository for the full design rationale, including why this lives as a separate distribution rather than inside the `legoai` import namespace.

## Current capability

- **`document.chunking`** — deterministic, sliding-window word-count text chunking. Pure, stateless, effect-free: no I/O, no persistence, no network access, no external provider.

No other capability is implemented yet. This package does not depend on and does not implement any part of Semantic Kernel, Microsoft Agent Framework, any model-provider SDK, a database driver, or a workflow engine — `document.chunking` needs none of them, and future capabilities that do need such dependencies will not be added to this capability's own dependency closure without deliberate review.

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

## Independence from AI/model/agent frameworks

This package has **zero runtime dependencies** in its first release. It is deliberately framework- and provider-neutral: nothing in `document.chunking` requires choosing, installing, or configuring a language model, an agent runtime, a vector store, or a database. Future capabilities added to this pack (document parsing, embeddings, retrieval, etc.) are expected to introduce their own, separately scoped dependencies only as each capability is actually implemented — never speculatively, and never in a way that changes what installing `document.chunking` alone requires.

## Running the tests

From the `legoai-document` directory:

```sh
uv run --locked --no-sync python -m pytest
uv run --locked --no-sync python -m mypy src tests
uv run --locked --no-sync ruff check .
uv run --locked --no-sync ruff format --check .
```
