"""document.embedding contract tests -- pure, using a fake `governed_embed`
callable (no Core Coordinator/Catalog/network required)."""

from __future__ import annotations

import asyncio

import pytest
from legoai.intelligence.model.values import (
    EmbeddingRequest,
    EmbeddingResult,
    ModelId,
    ProviderId,
)

from legoai_document.embedding import (
    ChunkReference,
    DocumentEmbeddingValidationError,
    embed_chunks,
)


async def _fake_governed_embed(request: EmbeddingRequest) -> EmbeddingResult:
    vectors = tuple((float(i), float(i) + 0.5) for i in range(len(request.inputs)))
    return EmbeddingResult(
        vectors, 2, ModelId("fake-model"), ProviderId("fake-provider")
    )


def test_embed_chunks_pairs_vectors_positionally() -> None:
    async def scenario() -> None:
        chunks = (ChunkReference("doc-1", 0), ChunkReference("doc-1", 1))
        texts = ("first chunk", "second chunk")

        result = await embed_chunks(chunks, texts, _fake_governed_embed)

        assert len(result.embeddings) == 2
        assert result.embeddings[0].chunk == chunks[0]
        assert result.embeddings[0].vector == (0.0, 0.5)
        assert result.embeddings[1].chunk == chunks[1]
        assert result.embeddings[1].vector == (1.0, 1.5)
        assert result.dimension == 2
        assert result.model_identity.value == "fake-model"
        assert result.provider_identity.value == "fake-provider"

    asyncio.run(scenario())


def test_embed_chunks_rejects_mismatched_lengths() -> None:
    async def scenario() -> None:
        with pytest.raises(DocumentEmbeddingValidationError, match="same length"):
            await embed_chunks(
                (ChunkReference("doc-1", 0),), ("a", "b"), _fake_governed_embed
            )

    asyncio.run(scenario())


def test_embed_chunks_rejects_empty_input() -> None:
    async def scenario() -> None:
        with pytest.raises(
            DocumentEmbeddingValidationError, match="at least one chunk"
        ):
            await embed_chunks((), (), _fake_governed_embed)

    asyncio.run(scenario())


def test_embed_chunks_calls_governed_embed_exactly_once() -> None:
    async def scenario() -> None:
        calls = 0

        async def counting_embed(request: EmbeddingRequest) -> EmbeddingResult:
            nonlocal calls
            calls += 1
            return await _fake_governed_embed(request)

        await embed_chunks(
            (ChunkReference("doc-1", 0),), ("only chunk",), counting_embed
        )
        assert calls == 1

    asyncio.run(scenario())


def test_embed_chunks_propagates_governed_embed_failure() -> None:
    async def scenario() -> None:
        async def failing_embed(request: EmbeddingRequest) -> EmbeddingResult:
            raise RuntimeError("provider unavailable")

        with pytest.raises(RuntimeError, match="provider unavailable"):
            await embed_chunks(
                (ChunkReference("doc-1", 0),), ("only chunk",), failing_embed
            )

    asyncio.run(scenario())
