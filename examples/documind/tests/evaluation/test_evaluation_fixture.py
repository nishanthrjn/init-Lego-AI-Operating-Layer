"""Small deterministic evaluation fixture (task's own instruction: "release
confidence, not research benchmarking"): two sample documents, four known
questions, and the document each question's top citation must come from.

Uses a deterministic keyword-count fake embedding (not a real embedding
model) so retrieval behavior is reproducible and this test needs no live
Ollama instance -- it is checking that ingestion -> retrieval -> rerank ->
citation-building correctly threads source identity through the whole
pipeline, not evaluating real embedding-model quality.
"""

from __future__ import annotations

import asyncio
import json
import urllib.request
from pathlib import Path
from unittest.mock import patch

from documind_app.app import DocuMindApplication
from documind_app.composition import DocuMindRuntime
from documind_app.config import DocuMindConfig

_TESTDATA = Path(__file__).resolve().parents[2] / "testdata"

_KEYWORDS = (
    "governance",
    "catalog",
    "authorization",
    "execution",
    "lifecycle",
    "dispatch",
    "retrieval",
    "embedding",
)


def _keyword_embedding(text: str) -> list[float]:
    lowered = text.lower()
    return [float(lowered.count(keyword)) + 0.01 for keyword in _KEYWORDS]


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
    assert isinstance(request.data, bytes)
    body = json.loads(request.data)
    if request.full_url.endswith("/api/embed"):
        vectors = [_keyword_embedding(text) for text in body["input"]]
        return _FakeResponse({"embeddings": vectors})
    if request.full_url.endswith("/api/chat"):
        return _FakeResponse({"message": {"content": "See the cited context."}})
    raise AssertionError(f"unexpected URL: {request.full_url}")


def _config(tmp_path: Path) -> DocuMindConfig:
    return DocuMindConfig(
        base_url="http://localhost:11434",
        chat_model="llama3.2",
        embedding_model="nomic-embed-text",
        timeout_seconds=30.0,
        index_path=tmp_path / "index.sqlite3",
        tenant_id="local",
    )


_CASES = (
    ("What role does the Catalog play in LegoAI governance?", "lego-ai-overview.md"),
    (
        "What are the states an Execution moves through in its lifecycle?",
        "legoai-execution-model.md",
    ),
    (
        "What does the dispatch arbiter check before issuing a permit?",
        "legoai-execution-model.md",
    ),
    (
        "What retrieval approach does the Document Capability Pack use?",
        "lego-ai-overview.md",
    ),
)


def test_citations_come_from_the_expected_source_document(tmp_path: Path) -> None:
    with patch("urllib.request.urlopen", side_effect=_fake_urlopen):

        async def scenario() -> None:
            runtime = DocuMindRuntime(_config(tmp_path))
            app = DocuMindApplication(runtime)

            for filename in ("lego-ai-overview.md", "legoai-execution-model.md"):
                await app.ingest_path(_TESTDATA / filename)

            for question, expected_document in _CASES:
                result = await app.ask(question)
                assert result.citations, f"no citations for: {question}"
                top_citation = result.citations[0]
                assert top_citation.document_id.endswith(expected_document), (
                    f"question {question!r} expected top citation from "
                    f"{expected_document!r}, got {top_citation.document_id!r}"
                )

        asyncio.run(scenario())
