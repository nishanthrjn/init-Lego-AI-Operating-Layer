"""Immutable value types for the document.embedding capability.

Distinct from `legoai.intelligence.model`'s generic embedding capability
(this pack's `EMBEDDING-CAPABILITY-DESIGN.md` SS20-21's own boundary): this
module's role is *pairing* -- associating each already-produced vector back
with the exact chunk it embedded -- never re-defining what an embedding
request/result means at the Model level. `ChunkReference` carries only what
identifies a chunk for this pairing; it is not a persistence key, a
retrieval-index row, or a document entity.
"""

from __future__ import annotations

from dataclasses import dataclass

from legoai.intelligence.model.values import ModelId, ProviderId


@dataclass(frozen=True, slots=True)
class ChunkReference:
    """Identifies exactly one chunk within one document, for pairing a
    vector back to its source -- nothing more (no persistence key, no
    tenant, no timestamp)."""

    document_id: str
    chunk_index: int


@dataclass(frozen=True, slots=True)
class DocumentChunkEmbedding:
    """One chunk paired with its embedding vector."""

    chunk: ChunkReference
    vector: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class DocumentEmbeddingResult:
    """Ordered, chunk-paired embedding output. `model_identity`/
    `provider_identity`/`dimension` are the same declared facts
    `legoai.intelligence.model.values.EmbeddingResult` already carries,
    passed through unchanged -- never re-derived or duplicated with a
    different meaning."""

    embeddings: tuple[DocumentChunkEmbedding, ...]
    dimension: int
    model_identity: ModelId
    provider_identity: ProviderId
