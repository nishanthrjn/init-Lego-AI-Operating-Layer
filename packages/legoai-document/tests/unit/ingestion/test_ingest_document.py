"""document.ingestion composition tests -- fake governed_embed, real SQLite
temp store, no network/live Ollama."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from legoai.intelligence.model.values import (
    EmbeddingRequest,
    EmbeddingResult,
    ModelId,
    ProviderId,
)

from legoai_document.ingestion import IngestionRequest, ingest_document
from legoai_document.parsing.errors import UnsupportedDocumentFormatError
from legoai_document.parsing.values import DocumentFormat
from legoai_document.retrieval import (
    RetrievalQuery,
    RetrievalScope,
    SQLiteRetrievalStore,
    hybrid_search,
)


async def _fake_governed_embed(request: EmbeddingRequest) -> EmbeddingResult:
    vectors = tuple((float(i), 0.0) for i in range(len(request.inputs)))
    return EmbeddingResult(
        vectors, 2, ModelId("fake-model"), ProviderId("fake-provider")
    )


def test_ingest_document_success_indexes_all_chunks(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = SQLiteRetrievalStore(tmp_path / "index.sqlite3")
        request = IngestionRequest(
            "tenant-a",
            "doc-1",
            b"one two three four five six seven eight nine ten",
            DocumentFormat.TEXT,
            chunk_size=3,
            overlap=0,
        )

        result = await ingest_document(request, _fake_governed_embed, store)

        assert result.document_id == "doc-1"
        assert result.page_count == 1
        assert result.chunk_count == 4  # 10 words / 3 per chunk, no overlap
        assert result.indexed_chunk_count == 4
        assert result.model_identity == "fake-model"
        assert result.provider_identity == "fake-provider"

        found = hybrid_search(
            store,
            RetrievalQuery(RetrievalScope("tenant-a"), "one", (0.0, 0.0), top_k=10),
        )
        assert len(found.candidates) == 4

    asyncio.run(scenario())


def test_ingest_empty_document_produces_zero_chunks_without_embedding(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        calls = 0

        async def counting_embed(request: EmbeddingRequest) -> EmbeddingResult:
            nonlocal calls
            calls += 1
            return await _fake_governed_embed(request)

        store = SQLiteRetrievalStore(tmp_path / "index.sqlite3")
        request = IngestionRequest("tenant-a", "doc-empty", b"", DocumentFormat.TEXT)

        result = await ingest_document(request, counting_embed, store)

        assert result.chunk_count == 0
        assert result.indexed_chunk_count == 0
        assert result.model_identity is None
        assert result.provider_identity is None
        assert calls == 0

    asyncio.run(scenario())


def test_reingesting_same_document_replaces_not_duplicates(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = SQLiteRetrievalStore(tmp_path / "index.sqlite3")
        first = IngestionRequest(
            "tenant-a",
            "doc-1",
            b"a b c d e f",
            DocumentFormat.TEXT,
            chunk_size=2,
            overlap=0,
        )
        await ingest_document(first, _fake_governed_embed, store)

        # Re-ingest with fewer chunks than before -- stale trailing chunks
        # from the first ingestion must not linger.
        second = IngestionRequest(
            "tenant-a", "doc-1", b"x y", DocumentFormat.TEXT, chunk_size=2, overlap=0
        )
        result = await ingest_document(second, _fake_governed_embed, store)

        assert result.chunk_count == 1
        found = hybrid_search(
            store,
            RetrievalQuery(RetrievalScope("tenant-a"), "x", (0.0, 0.0), top_k=10),
        )
        assert len(found.candidates) == 1
        assert found.candidates[0].text == "x y"

    asyncio.run(scenario())


def test_ingest_unsupported_format_propagates_parsing_error(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = SQLiteRetrievalStore(tmp_path / "index.sqlite3")
        request = IngestionRequest(
            "tenant-a",
            "doc-1",
            b"content",
            "unsupported-format",  # type: ignore[arg-type]
            chunk_size=512,
            overlap=50,
        )
        with pytest.raises(UnsupportedDocumentFormatError):
            await ingest_document(request, _fake_governed_embed, store)

    asyncio.run(scenario())
