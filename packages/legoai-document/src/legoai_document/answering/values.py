"""Immutable value types for the document.answering composite capability."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnsweringRequest:
    tenant_id: str
    question: str
    top_k: int = 5
    rerank_top_n: int = 5
    max_context_characters: int = 4000


@dataclass(frozen=True, slots=True)
class Citation:
    """One `[n]`-style citation. `index` matches the `[n]` marker used in
    the context block the model was instructed to cite -- built directly
    from an actually-retrieved chunk, never parsed out of the model's own
    text (task SS30: no generated citation may lack a retrieved source)."""

    index: int
    document_id: str
    chunk_index: int
    text: str


@dataclass(frozen=True, slots=True)
class AnswerProvenance:
    """Enough provenance to identify what actually produced this answer
    (task SS31) -- never hidden chain-of-thought (task's own instruction,
    and consistent with Gate-2's own established discipline)."""

    model_identity: str
    provider_identity: str
    reranker: str
    retrieval_candidate_count: int


@dataclass(frozen=True, slots=True)
class AnsweringResult:
    answer: str
    citations: tuple[Citation, ...]
    provenance: AnswerProvenance
