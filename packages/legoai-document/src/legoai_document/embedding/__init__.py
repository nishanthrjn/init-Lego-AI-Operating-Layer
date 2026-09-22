"""Public surface of the document.embedding capability.

Deliberately exports only the supported names below -- no wildcard
re-export and no aggregate "import everything" module.
"""

from __future__ import annotations

from legoai_document.embedding.api import GovernedEmbed, embed_chunks
from legoai_document.embedding.errors import DocumentEmbeddingValidationError
from legoai_document.embedding.values import (
    ChunkReference,
    DocumentChunkEmbedding,
    DocumentEmbeddingResult,
)

__all__ = [
    "ChunkReference",
    "DocumentChunkEmbedding",
    "DocumentEmbeddingResult",
    "DocumentEmbeddingValidationError",
    "GovernedEmbed",
    "embed_chunks",
]
