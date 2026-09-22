"""Immutable value types for the document.rerank capability.

Deliberately independent of `legoai_document.retrieval`'s own candidate
type: rerank is a reusable capability over *any* ranked candidate list, not
exclusively this pack's own retrieval output (SPEC's Retriever/Rerank
separation, task's own instruction). A caller (the answering composition)
converts a `RetrievalCandidate` into a `RerankCandidate` at that boundary.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RerankCandidate:
    """One candidate to (re)rank, with its incoming score/rank preserved as
    input -- rerank may use, ignore, or replace it depending on the
    reranker actually configured."""

    document_id: str
    chunk_index: int
    text: str
    score: float


@dataclass(frozen=True, slots=True)
class RerankRequest:
    query_text: str
    candidates: tuple[RerankCandidate, ...]
    top_n: int = 5


@dataclass(frozen=True, slots=True)
class RerankedCandidate:
    document_id: str
    chunk_index: int
    text: str
    score: float
    rank: int


@dataclass(frozen=True, slots=True)
class RerankResult:
    """`reranker` explicitly declares which reranking behavior actually
    produced this result (task SS25: graceful degradation must be an
    explicitly declared acceptable behavior, never a silent fallback)."""

    candidates: tuple[RerankedCandidate, ...]
    reranker: str
