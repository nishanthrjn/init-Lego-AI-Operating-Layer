"""document.retrieval v1 -- hybrid (vector + lexical) search over a local
`SQLiteRetrievalStore`.

**Combination rule, stated explicitly (task SS22 -- document it, never claim
unevaluated state-of-the-art quality):** Reciprocal Rank Fusion.

    score(candidate) = sum over each ranked list L containing candidate of:
                            1 / (RRF_K + rank_in_L)

`RRF_K = 60`, a widely-used, parameter-light constant (Cormack, Clarke &
Buettcher 2009) chosen for its simplicity, not tuned/evaluated against this
project's own data. A candidate appearing in only one of the two ranked
lists is still scored, using only that list's contribution. Final
candidates are sorted by this combined score, descending, and truncated to
`RetrievalQuery.top_k`.

Retrieval performs no Model/Agent call -- `RetrievalQuery.embedding` must
already be the caller's own precomputed query embedding.
"""

from __future__ import annotations

from legoai_document.retrieval.errors import RetrievalValidationError
from legoai_document.retrieval.store import SQLiteRetrievalStore
from legoai_document.retrieval.values import (
    RetrievalCandidate,
    RetrievalQuery,
    RetrievalResult,
)

_RRF_K = 60


def hybrid_search(
    store: SQLiteRetrievalStore, query: RetrievalQuery
) -> RetrievalResult:
    """Score and rank chunks in `query.scope` against both `query.embedding`
    (vector) and `query.text` (lexical), combine via Reciprocal Rank Fusion
    (see module docstring), and return the top `query.top_k` candidates.

    Raises:
        RetrievalValidationError: `top_k <= 0`, empty `scope.tenant_id`, or
            an empty `embedding`.
    """
    if query.top_k <= 0:
        raise RetrievalValidationError("top_k must be a positive integer")
    if not query.scope.tenant_id:
        raise RetrievalValidationError("scope requires a non-empty tenant_id")
    if len(query.embedding) == 0:
        raise RetrievalValidationError("query requires a non-empty embedding")

    # A generous candidate pool per signal so RRF has real ranks to combine,
    # even when top_k is small.
    pool_size = max(query.top_k * 3, query.top_k)
    vector_hits = store.search_vector(query.scope, query.embedding, pool_size)
    lexical_hits = store.search_text(query.scope, query.text, pool_size)

    rrf_scores: dict[tuple[str, int], float] = {}
    text_by_key: dict[tuple[str, int], str] = {}
    vector_score_by_key: dict[tuple[str, int], float] = {}
    lexical_score_by_key: dict[tuple[str, int], float] = {}

    for rank, (document_id, chunk_index, text, score) in enumerate(
        vector_hits, start=1
    ):
        key = (document_id, chunk_index)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (_RRF_K + rank)
        text_by_key[key] = text
        vector_score_by_key[key] = score

    for rank, (document_id, chunk_index, text, score) in enumerate(
        lexical_hits, start=1
    ):
        key = (document_id, chunk_index)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (_RRF_K + rank)
        text_by_key[key] = text
        lexical_score_by_key[key] = score

    ordered_keys = sorted(
        rrf_scores.keys(), key=lambda key: rrf_scores[key], reverse=True
    )[: query.top_k]

    candidates = tuple(
        RetrievalCandidate(
            document_id=key[0],
            chunk_index=key[1],
            text=text_by_key[key],
            score=rrf_scores[key],
            rank=rank,
            vector_score=vector_score_by_key.get(key),
            lexical_score=lexical_score_by_key.get(key),
        )
        for rank, key in enumerate(ordered_keys, start=1)
    )
    return RetrievalResult(candidates)
