"""Immutable value types for the document.retrieval capability.

Retrieval does NOT invoke a Model or Agent (task's own instruction, matching
`planning/DOCUMIND-EXTRACTION-ASSESSMENT.md` SS16.3): a `RetrievalQuery`
already carries a pre-computed `embedding` -- the caller (an answering
composition) is responsible for obtaining it via `document.embedding`
first. This capability is a pure, local scoring/ranking computation over an
already-populated store.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetrievalScope:
    """Mandatory tenant scope plus an optional document-id filter. Every
    store query is filtered to exactly this scope before any scoring runs
    -- never a post-filter over unscoped results (task SS23)."""

    tenant_id: str
    document_ids: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    """`embedding` is the caller's already-computed query embedding
    (`document.embedding`'s job, not this capability's) -- `text` is the
    same query in its original textual form, used for the lexical half of
    hybrid search."""

    scope: RetrievalScope
    text: str
    embedding: tuple[float, ...]
    top_k: int = 5


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    """One ranked result. `vector_score`/`lexical_score` are the two raw
    per-signal scores (each `None` if that signal did not rank this
    candidate at all); `score` is the final combined Reciprocal Rank Fusion
    value actually used for `rank` ordering (see
    `legoai_document.retrieval.api`'s module docstring for the exact,
    explicit combination rule -- never an unstated/implicit one)."""

    document_id: str
    chunk_index: int
    text: str
    score: float
    rank: int
    vector_score: float | None
    lexical_score: float | None


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    candidates: tuple[RetrievalCandidate, ...]


@dataclass(frozen=True, slots=True)
class IndexedChunk:
    """One chunk to persist for later retrieval. Re-indexing the exact same
    `(tenant_id, document_id, chunk_index)` replaces the prior row -- never
    duplicates it (task SS27's ingestion-idempotency requirement)."""

    tenant_id: str
    document_id: str
    chunk_index: int
    text: str
    embedding: tuple[float, ...]
