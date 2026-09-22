"""document.answering composition tests -- fake governed_embed/governed_chat,
real SQLite temp store, no network/live Ollama."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ModelId,
    ProviderId,
)

from legoai_document.answering import AnsweringRequest, answer_question
from legoai_document.answering.api import GovernedChat
from legoai_document.retrieval import IndexedChunk, SQLiteRetrievalStore


async def _fake_embed(request: EmbeddingRequest) -> EmbeddingResult:
    vectors = tuple((1.0, 0.0) for _ in request.inputs)
    return EmbeddingResult(
        vectors, 2, ModelId("fake-embed-model"), ProviderId("fake-provider")
    )


def _fake_chat(content: str) -> GovernedChat:
    async def chat(request: ChatRequest) -> ChatResult:
        return ChatResult(
            content, ModelId("fake-chat-model"), ProviderId("fake-provider"), None
        )

    return chat


def _store_with_one_chunk(tmp_path: Path) -> SQLiteRetrievalStore:
    store = SQLiteRetrievalStore(tmp_path / "index.sqlite3")
    store.index_chunk(
        IndexedChunk(
            "tenant-a", "doc-1", 0, "the sky is blue during the day", (1.0, 0.0)
        )
    )
    return store


def test_answer_question_returns_answer_with_citation(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = _store_with_one_chunk(tmp_path)
        chat_calls = 0

        async def counting_chat(request: ChatRequest) -> ChatResult:
            nonlocal chat_calls
            chat_calls += 1
            assert "[1]" in request.messages[1].content
            return ChatResult(
                "The sky is blue [1].",
                ModelId("fake-chat-model"),
                ProviderId("fake-provider"),
                None,
            )

        result = await answer_question(
            AnsweringRequest("tenant-a", "What color is the sky?"),
            store,
            _fake_embed,
            counting_chat,
        )

        assert chat_calls == 1
        assert result.answer == "The sky is blue [1]."
        assert len(result.citations) == 1
        assert result.citations[0].index == 1
        assert result.citations[0].document_id == "doc-1"
        assert result.provenance.model_identity == "fake-chat-model"
        assert result.provenance.reranker == "identity-truncation"
        assert result.provenance.retrieval_candidate_count == 1

    asyncio.run(scenario())


def test_answer_question_no_supporting_context_never_calls_chat(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = SQLiteRetrievalStore(tmp_path / "index.sqlite3")  # empty store
        chat_calls = 0

        async def counting_chat(request: ChatRequest) -> ChatResult:
            nonlocal chat_calls
            chat_calls += 1
            raise AssertionError("must not be called: no supporting context")

        result = await answer_question(
            AnsweringRequest("tenant-a", "anything at all"),
            store,
            _fake_embed,
            counting_chat,
        )

        assert chat_calls == 0
        assert result.answer == "No supporting context was found for this question."
        assert result.citations == ()
        assert result.provenance.reranker == "none"

    asyncio.run(scenario())


def test_answer_question_respects_tenant_scope(tmp_path: Path) -> None:
    async def scenario() -> None:
        store = SQLiteRetrievalStore(tmp_path / "index.sqlite3")
        store.index_chunk(
            IndexedChunk("tenant-b", "doc-1", 0, "tenant b secret content", (1.0, 0.0))
        )
        chat_calls = 0

        async def counting_chat(request: ChatRequest) -> ChatResult:
            nonlocal chat_calls
            chat_calls += 1
            raise AssertionError("must not be called: wrong tenant scope")

        result = await answer_question(
            AnsweringRequest("tenant-a", "secret"), store, _fake_embed, counting_chat
        )

        assert chat_calls == 0
        assert "No supporting context" in result.answer

    asyncio.run(scenario())


def test_answer_question_context_budget_always_includes_top_candidate(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        store = SQLiteRetrievalStore(tmp_path / "index.sqlite3")
        long_text = "word " * 2000
        store.index_chunk(IndexedChunk("tenant-a", "doc-1", 0, long_text, (1.0, 0.0)))
        store.index_chunk(
            IndexedChunk("tenant-a", "doc-1", 1, "short chunk", (1.0, 0.0))
        )

        result = await answer_question(
            AnsweringRequest(
                "tenant-a", "word", max_context_characters=10, rerank_top_n=2
            ),
            store,
            _fake_embed,
            _fake_chat("answer"),
        )

        # The first (top-ranked) candidate is always included even though it
        # alone exceeds the tiny budget; nothing further is added.
        assert len(result.citations) == 1

    asyncio.run(scenario())


def test_answer_question_denied_governed_embed_propagates() -> None:
    async def scenario() -> None:
        async def failing_embed(request: EmbeddingRequest) -> EmbeddingResult:
            raise RuntimeError("governed dispatch denied")

        with pytest.raises(RuntimeError, match="denied"):
            await answer_question(
                AnsweringRequest("tenant-a", "q"),
                SQLiteRetrievalStore(":memory:"),
                failing_embed,
                _fake_chat("unreachable"),
            )

    asyncio.run(scenario())
