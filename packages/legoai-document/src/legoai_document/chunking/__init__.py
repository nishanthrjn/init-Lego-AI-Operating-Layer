"""Public surface of the document.chunking capability.

Deliberately exports only the supported names below -- no wildcard
re-export and no aggregate "import everything" module.
"""

from __future__ import annotations

from legoai_document.chunking.api import chunk_text
from legoai_document.chunking.errors import ChunkingValidationError
from legoai_document.chunking.values import Chunk, ChunkingRequest, ChunkingResult

__all__ = [
    "Chunk",
    "ChunkingRequest",
    "ChunkingResult",
    "ChunkingValidationError",
    "chunk_text",
]
