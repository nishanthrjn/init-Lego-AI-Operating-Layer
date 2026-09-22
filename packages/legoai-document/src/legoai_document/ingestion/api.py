"""document.ingestion v1 -- deterministic composition: parse -> chunk ->
embed -> index.

No Agent, no Workflow engine (task SS26): this is a plain async function
composing four already-independent capabilities in sequence. The only
effectful step is embedding (via the caller-supplied `governed_embed`,
already crossing LegoAI Core's governed path -- see
`legoai_document.embedding`'s own module docstring); parsing, chunking, and
local SQLite indexing are pure/local.

**Idempotency (task SS27):** re-ingesting the exact same
`(tenant_id, document_id)` first deletes every previously-indexed chunk for
that document, then indexes the new set -- correct even when the new chunk
count differs from the old one (a naive per-chunk-index REPLACE alone would
leave stale trailing chunks behind if the new document produced fewer
chunks). This is document-level idempotency, never a global exactly-once
claim (`legoai_document.embedding`'s `governed_embed` may itself be called
more than once across separate ingestion attempts; each successful
`ingest_document` call deterministically converges to "exactly this
document's current content, indexed").
"""

from __future__ import annotations

from legoai_document.chunking.api import chunk_text
from legoai_document.chunking.values import ChunkingRequest
from legoai_document.embedding.api import GovernedEmbed, embed_chunks
from legoai_document.embedding.values import ChunkReference
from legoai_document.ingestion.values import IngestionRequest, IngestionResult
from legoai_document.parsing.api import flatten_pages, parse_document
from legoai_document.parsing.values import DocumentParsingRequest
from legoai_document.retrieval.store import SQLiteRetrievalStore
from legoai_document.retrieval.values import IndexedChunk


async def ingest_document(
    request: IngestionRequest,
    governed_embed: GovernedEmbed,
    store: SQLiteRetrievalStore,
) -> IngestionResult:
    """Parse `request.content`, chunk the flattened text, embed each chunk
    through `governed_embed`, and index the result in `store`.

    An empty or whitespace-only document is a valid, non-error outcome
    (mirroring `document.chunking`'s own established "empty input is
    valid" behavior): `chunk_count`/`indexed_chunk_count` are both `0`, and
    no embedding call is made at all -- there is nothing to embed.

    Unsupported formats / malformed content propagate unchanged as
    `legoai_document.parsing`'s own typed exceptions
    (`UnsupportedDocumentFormatError`, `MalformedDocumentError`,
    `EncryptedDocumentError`); invalid chunk parameters propagate as
    `legoai_document.chunking`'s own `ChunkingValidationError`. This
    composition adds no new validation-error type of its own.
    """
    parsed = parse_document(DocumentParsingRequest(request.content, request.format))
    flattened_text = flatten_pages(parsed)

    chunking_result = chunk_text(
        ChunkingRequest(flattened_text, request.chunk_size, request.overlap)
    )

    store.delete_document(request.tenant_id, request.document_id)

    if len(chunking_result.chunks) == 0:
        return IngestionResult(request.document_id, len(parsed.pages), 0, 0, None, None)

    chunk_refs = tuple(
        ChunkReference(request.document_id, chunk.index)
        for chunk in chunking_result.chunks
    )
    texts = tuple(chunk.content for chunk in chunking_result.chunks)
    text_by_index = {chunk.index: chunk.content for chunk in chunking_result.chunks}

    embedding_result = await embed_chunks(chunk_refs, texts, governed_embed)

    for item in embedding_result.embeddings:
        store.index_chunk(
            IndexedChunk(
                request.tenant_id,
                request.document_id,
                item.chunk.chunk_index,
                text_by_index[item.chunk.chunk_index],
                item.vector,
            )
        )

    return IngestionResult(
        document_id=request.document_id,
        page_count=len(parsed.pages),
        chunk_count=len(chunking_result.chunks),
        indexed_chunk_count=len(embedding_result.embeddings),
        model_identity=embedding_result.model_identity.value,
        provider_identity=embedding_result.provider_identity.value,
    )
