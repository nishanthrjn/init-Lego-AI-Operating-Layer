"""document.rerank v1 -- identity/truncation reference reranker.

**Explicitly declared v0.1 behavior (task SS24-25 -- graceful degradation
must be declared, never silent):** `identity_rerank` does not reorder its
input at all. It preserves the incoming candidate order (assumed to already
be meaningfully ranked by the caller -- e.g. `document.retrieval`'s own RRF
ordering) and truncates to `request.top_n`. This is the same
`NoOpReranker`/identity-reranking pattern both original DocuMind
applications already treat as a legitimate, explicitly-selected behavior
when no rerank provider is configured -- not an accidental placeholder.
`RerankResult.reranker` is always exactly `"identity-truncation"` for this
function, so a caller/answering composition can see plainly which behavior
actually ran.

A future provider-backed reranker (Cohere or otherwise) would be a
*different*, separately named function conforming to the same `Reranker`
callable shape -- not introduced in this v0.1 slice (task SS24: "do not
introduce Cohere merely to make v0.1 look richer").
"""

from __future__ import annotations

from collections.abc import Callable

from legoai_document.rerank.errors import RerankValidationError
from legoai_document.rerank.values import RerankedCandidate, RerankRequest, RerankResult

Reranker = Callable[[RerankRequest], RerankResult]

_IDENTITY_TRUNCATION = "identity-truncation"


def identity_rerank(request: RerankRequest) -> RerankResult:
    """Preserve `request.candidates`' incoming order; truncate to
    `request.top_n`. Never invokes a Model/network provider -- this is a
    pure, deterministic, effect-free computation.

    Raises:
        RerankValidationError: `top_n <= 0`.
    """
    if request.top_n <= 0:
        raise RerankValidationError("top_n must be a positive integer")

    truncated = request.candidates[: request.top_n]
    reranked = tuple(
        RerankedCandidate(
            document_id=candidate.document_id,
            chunk_index=candidate.chunk_index,
            text=candidate.text,
            score=candidate.score,
            rank=rank,
        )
        for rank, candidate in enumerate(truncated, start=1)
    )
    return RerankResult(reranked, _IDENTITY_TRUNCATION)
