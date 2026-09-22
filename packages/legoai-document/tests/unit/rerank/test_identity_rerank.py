"""document.rerank unit tests -- pure, no network, no provider."""

from __future__ import annotations

import pytest

from legoai_document.rerank import (
    RerankCandidate,
    RerankRequest,
    RerankValidationError,
    identity_rerank,
)


def _candidates(n: int) -> tuple[RerankCandidate, ...]:
    return tuple(
        RerankCandidate(f"doc-{i}", 0, f"text {i}", score=float(n - i))
        for i in range(n)
    )


def test_identity_rerank_preserves_order_and_truncates() -> None:
    request = RerankRequest("query", _candidates(5), top_n=3)
    result = identity_rerank(request)

    assert len(result.candidates) == 3
    assert [c.document_id for c in result.candidates] == ["doc-0", "doc-1", "doc-2"]
    assert [c.rank for c in result.candidates] == [1, 2, 3]
    assert result.reranker == "identity-truncation"


def test_identity_rerank_never_reorders() -> None:
    # A deliberately "wrong" incoming order (ascending score) must remain
    # untouched -- identity means identity, not "fix the order for you".
    candidates = (
        RerankCandidate("doc-low", 0, "low score first", score=0.1),
        RerankCandidate("doc-high", 0, "high score second", score=0.9),
    )
    result = identity_rerank(RerankRequest("q", candidates, top_n=2))
    assert [c.document_id for c in result.candidates] == ["doc-low", "doc-high"]


def test_identity_rerank_top_n_larger_than_candidates_returns_all() -> None:
    result = identity_rerank(RerankRequest("q", _candidates(2), top_n=10))
    assert len(result.candidates) == 2


def test_identity_rerank_empty_candidates_returns_empty_result() -> None:
    result = identity_rerank(RerankRequest("q", (), top_n=5))
    assert result.candidates == ()
    assert result.reranker == "identity-truncation"


def test_identity_rerank_rejects_non_positive_top_n() -> None:
    with pytest.raises(RerankValidationError, match="top_n"):
        identity_rerank(RerankRequest("q", _candidates(3), top_n=0))
    with pytest.raises(RerankValidationError, match="top_n"):
        identity_rerank(RerankRequest("q", _candidates(3), top_n=-1))
