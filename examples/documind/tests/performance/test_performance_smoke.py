"""Basic practical performance smoke checks (task's own instruction: "do
not prematurely optimize; record obvious bottlenecks only"). These assert
generous upper bounds against a fake HTTP transport -- they catch an
accidental O(n^2)/blocking-the-loop regression, not real Ollama latency,
which depends entirely on the local machine's hardware and is out of this
suite's control.
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.request
from pathlib import Path
from unittest.mock import patch

from documind_app.app import DocuMindApplication
from documind_app.composition import DocuMindRuntime
from documind_app.config import DocuMindConfig

_MULTI_PAGE_TEXT = "\n\n".join(
    f"Paragraph {i}: LegoAI routes capability {i} through governed dispatch."
    for i in range(200)
)


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
        return _FakeResponse({"embeddings": [[1.0, 0.0] for _ in body["input"]]})
    return _FakeResponse({"message": {"content": "answer [1]."}})


def _config(tmp_path: Path) -> DocuMindConfig:
    return DocuMindConfig(
        base_url="http://localhost:11434",
        chat_model="llama3.2",
        embedding_model="nomic-embed-text",
        timeout_seconds=30.0,
        index_path=tmp_path / "index.sqlite3",
        tenant_id="local",
    )


def test_ingesting_a_multi_chunk_document_completes_quickly(tmp_path: Path) -> None:
    with patch("urllib.request.urlopen", side_effect=_fake_urlopen):

        async def scenario() -> None:
            runtime = DocuMindRuntime(_config(tmp_path))
            app = DocuMindApplication(runtime)
            sample = tmp_path / "large.txt"
            sample.write_text(_MULTI_PAGE_TEXT)

            started = time.monotonic()
            result = await app.ingest_path(sample)
            elapsed = time.monotonic() - started

            assert result.chunk_count > 3
            assert elapsed < 5.0, (
                f"ingestion took {elapsed:.2f}s against a fake transport"
            )

        asyncio.run(scenario())


def test_asking_a_question_over_many_chunks_completes_quickly(tmp_path: Path) -> None:
    with patch("urllib.request.urlopen", side_effect=_fake_urlopen):

        async def scenario() -> None:
            runtime = DocuMindRuntime(_config(tmp_path))
            app = DocuMindApplication(runtime)
            sample = tmp_path / "large.txt"
            sample.write_text(_MULTI_PAGE_TEXT)
            await app.ingest_path(sample)

            started = time.monotonic()
            result = await app.ask("How does LegoAI route capabilities?")
            elapsed = time.monotonic() - started

            assert result.answer
            assert elapsed < 5.0, (
                f"answering took {elapsed:.2f}s against a fake transport"
            )

        asyncio.run(scenario())
