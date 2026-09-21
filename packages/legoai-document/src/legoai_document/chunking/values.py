"""Immutable value types for the document.chunking capability.

These types carry only what the pure chunking computation itself produces
or consumes. Document identity, tenant scope, persistence keys, timestamps,
Artifact references and provider/model metadata are deliberately absent:
they belong to a caller's Execution/orchestration layer, not to this
capability's semantic result. See CHUNKING-CAPABILITY-DESIGN.md SS2-3, SS9.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkingRequest:
    """Immutable input to the document.chunking capability.

    ``chunk_size`` and ``overlap`` are measured in ASCII-space-delimited
    words, not tokens (see :mod:`legoai_document.chunking.api`).
    """

    text: str
    chunk_size: int = 512
    overlap: int = 50


@dataclass(frozen=True, slots=True)
class Chunk:
    """A single chunk produced by document.chunking.

    ``word_count`` is the number of ASCII-space-delimited words in
    ``content``; it is not an LLM-tokenizer token count.
    """

    index: int
    content: str
    word_count: int


@dataclass(frozen=True, slots=True)
class ChunkingResult:
    """Immutable, order-stable output of document.chunking."""

    chunks: tuple[Chunk, ...]
