"""document.embedding v1 -- pair document chunks with vectors produced by
LegoAI Core's governed `model.embedding` capability.

This capability does **not** construct an `ExecutionCoordinator`,
`DispatchArbiter`, or Catalog itself, and does not import
`legoai.reference.*`/`legoai.runtime._composition.*` (Internal
implementations, per ADR-002's own package table -- see this package's
`tests/architecture/test_dependency_boundaries.py`). The actual governed
invocation is composed by the caller (the DocuMind application, which owns
composition-root responsibility for the whole vertical slice) and handed in
here as `governed_embed`: an already-wired async callable from
`legoai.intelligence.model.values.EmbeddingRequest` to `EmbeddingResult`,
having already crossed Catalog/authorization/dispatch/Coordinator. This
capability's own job is exactly what its module docstring in `values.py`
states: pairing, nothing else.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from legoai.intelligence.model.values import EmbeddingRequest, EmbeddingResult

from legoai_document.embedding.errors import DocumentEmbeddingValidationError
from legoai_document.embedding.values import (
    ChunkReference,
    DocumentChunkEmbedding,
    DocumentEmbeddingResult,
)

GovernedEmbed = Callable[[EmbeddingRequest], Awaitable[EmbeddingResult]]


async def embed_chunks(
    chunks: tuple[ChunkReference, ...],
    texts: tuple[str, ...],
    governed_embed: GovernedEmbed,
) -> DocumentEmbeddingResult:
    """Embed `texts` (positionally paired with `chunks`) through the
    caller-supplied governed embedding call, then pair each resulting
    vector back to its `ChunkReference`.

    Raises:
        DocumentEmbeddingValidationError: `chunks`/`texts` lengths differ,
            or either is empty.

    Ordering/count/dimension are Core's own already-enforced guarantees
    (`legoai.intelligence.model.values.EmbeddingResult`'s own construction
    validation) -- this function trusts `governed_embed`'s returned
    `EmbeddingResult` exactly as Core validated it, and pairs it back
    positionally without re-deriving those checks.
    """
    if len(chunks) != len(texts):
        raise DocumentEmbeddingValidationError(
            f"chunks ({len(chunks)}) and texts ({len(texts)}) must have the same length"
        )
    if len(chunks) == 0:
        raise DocumentEmbeddingValidationError(
            "embed_chunks requires at least one chunk"
        )

    result = await governed_embed(EmbeddingRequest(texts))

    embeddings = tuple(
        DocumentChunkEmbedding(chunk, vector)
        for chunk, vector in zip(chunks, result.vectors, strict=True)
    )
    return DocumentEmbeddingResult(
        embeddings, result.dimension, result.model_identity, result.provider_identity
    )
