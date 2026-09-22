"""document.retrieval unit tests -- real SQLite (a temp file per test), no
network, no Core dependency exercised here (pure local computation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from legoai_document.retrieval import (
    IndexedChunk,
    RetrievalQuery,
    RetrievalScope,
    RetrievalStoreError,
    RetrievalValidationError,
    SQLiteRetrievalStore,
    hybrid_search,
)


def _store(tmp_path: Path) -> SQLiteRetrievalStore:
    return SQLiteRetrievalStore(tmp_path / "index.sqlite3")


def _index(
    store: SQLiteRetrievalStore,
    tenant: str,
    document_id: str,
    chunks: list[tuple[str, tuple[float, ...]]],
) -> None:
    for index, (text, vector) in enumerate(chunks):
        store.index_chunk(IndexedChunk(tenant, document_id, index, text, vector))


def test_hybrid_search_ranks_by_combined_vector_and_lexical_signal(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    _index(
        store,
        "tenant-a",
        "doc-1",
        [
            ("the cat sat on the mat", (1.0, 0.0)),
            ("dogs are loyal animals", (0.0, 1.0)),
            ("cats and dogs are both pets", (0.7, 0.7)),
        ],
    )

    query = RetrievalQuery(RetrievalScope("tenant-a"), "cat", (1.0, 0.0), top_k=2)
    result = hybrid_search(store, query)

    assert len(result.candidates) == 2
    top = result.candidates[0]
    assert top.text == "the cat sat on the mat"
    assert top.rank == 1
    assert top.vector_score is not None
    assert top.lexical_score is not None


def test_hybrid_search_respects_tenant_scope(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _index(store, "tenant-a", "doc-1", [("secret tenant a content", (1.0, 0.0))])
    _index(store, "tenant-b", "doc-1", [("secret tenant b content", (1.0, 0.0))])

    result = hybrid_search(
        store, RetrievalQuery(RetrievalScope("tenant-a"), "secret", (1.0, 0.0), top_k=5)
    )

    assert len(result.candidates) == 1
    assert "tenant a" in result.candidates[0].text


def test_hybrid_search_respects_document_id_filter(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _index(store, "tenant-a", "doc-1", [("about apples", (1.0, 0.0))])
    _index(store, "tenant-a", "doc-2", [("about oranges", (1.0, 0.0))])

    result = hybrid_search(
        store,
        RetrievalQuery(
            RetrievalScope("tenant-a", document_ids=("doc-1",)),
            "about",
            (1.0, 0.0),
            top_k=5,
        ),
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].document_id == "doc-1"


def test_hybrid_search_no_match_returns_empty_result(tmp_path: Path) -> None:
    store = _store(tmp_path)
    result = hybrid_search(
        store, RetrievalQuery(RetrievalScope("tenant-a"), "anything", (1.0,), top_k=5)
    )
    assert result.candidates == ()


def test_hybrid_search_rejects_invalid_query(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(RetrievalValidationError, match="top_k"):
        hybrid_search(store, RetrievalQuery(RetrievalScope("t"), "q", (1.0,), top_k=0))
    with pytest.raises(RetrievalValidationError, match="tenant_id"):
        hybrid_search(store, RetrievalQuery(RetrievalScope(""), "q", (1.0,), top_k=1))
    with pytest.raises(RetrievalValidationError, match="embedding"):
        hybrid_search(store, RetrievalQuery(RetrievalScope("t"), "q", (), top_k=1))


def test_reindexing_same_chunk_replaces_not_duplicates(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.index_chunk(IndexedChunk("tenant-a", "doc-1", 0, "version one", (1.0, 0.0)))
    store.index_chunk(IndexedChunk("tenant-a", "doc-1", 0, "version two", (0.0, 1.0)))

    result = hybrid_search(
        store,
        RetrievalQuery(RetrievalScope("tenant-a"), "version", (0.0, 1.0), top_k=5),
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].text == "version two"


def test_delete_document_removes_its_chunks(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _index(store, "tenant-a", "doc-1", [("chunk one", (1.0,)), ("chunk two", (1.0,))])
    store.delete_document("tenant-a", "doc-1")

    result = hybrid_search(
        store, RetrievalQuery(RetrievalScope("tenant-a"), "chunk", (1.0,), top_k=5)
    )
    assert result.candidates == ()


def test_corrupted_store_file_raises_retrieval_store_error(tmp_path: Path) -> None:
    corrupt_path = tmp_path / "corrupt.sqlite3"
    corrupt_path.write_bytes(b"not a valid sqlite database at all, just garbage bytes")
    with pytest.raises(RetrievalStoreError):
        SQLiteRetrievalStore(corrupt_path)
