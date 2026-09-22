"""Errors for the document.embedding capability -- pack-local, mirroring
Batch 1/2's discipline (`ChunkingValidationError`, parsing's own error
types): shallow, exact, never a generic catch-all.
"""

from __future__ import annotations


class DocumentEmbeddingValidationError(Exception):
    """The chunk/text pairing supplied to `embed_chunks` is malformed
    (mismatched lengths, empty chunk list) -- a caller precondition
    violation, never a provider/network failure."""
