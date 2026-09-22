"""LegoAI v0.1: end-to-end DocuMind proof -- ingest a sample document and
ask a question, exercising the full real path (composition root, Catalog
publish/resolve, authorization, dispatch, Coordinator, governed Model
invocation, document.ingestion, document.answering) with a fake HTTP
transport standing in for Ollama (task SS17/SS81: no live Ollama/network
required by the default suite).
"""

from __future__ import annotations

import asyncio
import json
import urllib.request
from pathlib import Path
from unittest.mock import patch

from legoai_document.retrieval.values import RetrievalScope

from documind_app.app import DocuMindApplication
from documind_app.composition import DocuMindRuntime
from documind_app.config import DocuMindConfig

_EMBED_VECTOR = [1.0, 0.0, 0.0]


class _FakeResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self._body = json.dumps(body).encode("utf-8")
        self.status = 200

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _fake_urlopen(
    request: urllib.request.Request, timeout: float | None = None
) -> _FakeResponse:
    url = request.full_url
    assert isinstance(request.data, bytes)
    body = json.loads(request.data)
    if url.endswith("/api/embed"):
        return _FakeResponse({"embeddings": [_EMBED_VECTOR for _ in body["input"]]})
    if url.endswith("/api/chat"):
        return _FakeResponse(
            {"message": {"content": "LegoAI routes every call through governance [1]."}}
        )
    raise AssertionError(f"unexpected URL: {url}")


def _config(tmp_path: Path) -> DocuMindConfig:
    return DocuMindConfig(
        base_url="http://localhost:11434",
        chat_model="llama3.2",
        embedding_model="nomic-embed-text",
        timeout_seconds=30.0,
        index_path=tmp_path / "index.sqlite3",
        tenant_id="local",
    )


def test_ingest_then_ask_returns_cited_answer(tmp_path: Path) -> None:
    with patch("urllib.request.urlopen", side_effect=_fake_urlopen):

        async def scenario() -> None:
            runtime = DocuMindRuntime(_config(tmp_path))
            app = DocuMindApplication(runtime)

            sample = tmp_path / "sample.md"
            sample.write_text(
                "# Governance\n\nLegoAI routes every capability call through "
                "a Catalog, authorization, and a dispatch arbiter before any "
                "provider is invoked."
            )

            ingestion_result = await app.ingest_path(sample)
            assert ingestion_result.chunk_count > 0
            assert ingestion_result.indexed_chunk_count == ingestion_result.chunk_count
            assert ingestion_result.model_identity == "nomic-embed-text"

            answering_result = await app.ask("How does LegoAI route capability calls?")
            assert "governance" in answering_result.answer.lower()
            assert len(answering_result.citations) >= 1
            assert answering_result.provenance.model_identity == "llama3.2"
            assert answering_result.provenance.provider_identity == "ollama-local"

        asyncio.run(scenario())


def test_reingesting_same_document_does_not_duplicate_chunks(tmp_path: Path) -> None:
    with patch("urllib.request.urlopen", side_effect=_fake_urlopen):

        async def scenario() -> None:
            runtime = DocuMindRuntime(_config(tmp_path))
            app = DocuMindApplication(runtime)

            sample = tmp_path / "sample.txt"
            sample.write_text("first version of the document")

            first = await app.ingest_path(sample)
            sample.write_text("second, shorter text")
            second = await app.ingest_path(sample)

            assert second.chunk_count >= 1
            rows = app.store.search_text(RetrievalScope("local"), "second", top_k=10)
            assert all(row[0] == str(sample) for row in rows)
            assert first.document_id == second.document_id

        asyncio.run(scenario())
