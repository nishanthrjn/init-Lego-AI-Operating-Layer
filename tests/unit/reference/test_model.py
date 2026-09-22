"""LegoAI v0.1: `OllamaModelAdapter` contract tests using a fake HTTP
transport -- no network, no live Ollama instance required (task SS17: the
default suite must not require Ollama running). Live-Ollama tests are a
separate, opt-in-marked module.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
from io import BytesIO
from unittest.mock import patch

import pytest

from legoai.intelligence.model.ports import (
    ModelPreflightError,
    ModelResponseRejectedError,
    ModelResponseUncertainError,
)
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatRole,
    EmbeddingRequest,
    ProviderId,
)
from legoai.reference.model import OllamaModelAdapter, OllamaModelConfig


def _config() -> OllamaModelConfig:
    return OllamaModelConfig(
        base_url="http://localhost:11434",
        chat_model="llama3.2",
        embedding_model="nomic-embed-text",
        timeout_seconds=30.0,
    )


class _FakeResponse:
    def __init__(self, body: dict[str, object], status: int = 200) -> None:
        self._body = json.dumps(body).encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _http_error(status: int, body: dict[str, object]) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "http://localhost:11434/api/chat",
        status,
        "error",
        {},  # type: ignore[arg-type]
        BytesIO(json.dumps(body).encode("utf-8")),
    )


def _adapter() -> OllamaModelAdapter:
    return OllamaModelAdapter(_config(), ProviderId("ollama-local"))


# --- chat --------------------------------------------------------------------------


def test_chat_success_returns_typed_result_with_provenance() -> None:
    async def scenario() -> None:
        response = _FakeResponse(
            {
                "message": {"role": "assistant", "content": "hello there"},
                "prompt_eval_count": 12,
                "eval_count": 4,
            }
        )
        with patch("urllib.request.urlopen", return_value=response):
            result = await _adapter().chat(
                ChatRequest((ChatMessage(ChatRole.USER, "hi"),))
            )
        assert result.content == "hello there"
        assert result.model_identity.value == "llama3.2"
        assert result.provider_identity.value == "ollama-local"
        assert result.usage is not None
        assert result.usage.prompt_tokens == 12
        assert result.usage.completion_tokens == 4

    asyncio.run(scenario())


def test_chat_rejects_wrong_type_argument() -> None:
    async def scenario() -> None:
        with pytest.raises(TypeError, match="ChatRequest"):
            await _adapter().chat(object())  # type: ignore[arg-type]

    asyncio.run(scenario())


def test_chat_missing_message_content_is_rejected() -> None:
    async def scenario() -> None:
        response = _FakeResponse({"message": {"role": "assistant"}})
        with patch("urllib.request.urlopen", return_value=response):
            with pytest.raises(ModelResponseRejectedError):
                await _adapter().chat(ChatRequest((ChatMessage(ChatRole.USER, "hi"),)))

    asyncio.run(scenario())


def test_chat_model_missing_404_is_rejected() -> None:
    async def scenario() -> None:
        error = _http_error(404, {"error": 'model "llama3.2" not found, try pulling it first'})
        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(ModelResponseRejectedError, match="not found"):
                await _adapter().chat(ChatRequest((ChatMessage(ChatRole.USER, "hi"),)))

    asyncio.run(scenario())


def test_chat_connection_refused_is_preflight_error() -> None:
    async def scenario() -> None:
        error = urllib.error.URLError(ConnectionRefusedError("refused"))
        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(ModelPreflightError):
                await _adapter().chat(ChatRequest((ChatMessage(ChatRole.USER, "hi"),)))

    asyncio.run(scenario())


def test_chat_timeout_is_uncertain_error() -> None:
    async def scenario() -> None:
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with pytest.raises(ModelResponseUncertainError):
                await _adapter().chat(ChatRequest((ChatMessage(ChatRole.USER, "hi"),)))

    asyncio.run(scenario())


def test_chat_malformed_json_is_rejected() -> None:
    async def scenario() -> None:
        class _BadResponse(_FakeResponse):
            def read(self) -> bytes:
                return b"not json"

        with patch("urllib.request.urlopen", return_value=_BadResponse({})):
            with pytest.raises(ModelResponseRejectedError):
                await _adapter().chat(ChatRequest((ChatMessage(ChatRole.USER, "hi"),)))

    asyncio.run(scenario())


# --- embed -------------------------------------------------------------------------


def test_embed_success_validates_and_returns_result() -> None:
    async def scenario() -> None:
        response = _FakeResponse({"embeddings": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]})
        with patch("urllib.request.urlopen", return_value=response):
            result = await _adapter().embed(EmbeddingRequest(("a", "b")))
        assert result.dimension == 3
        assert result.vectors == ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
        assert result.model_identity.value == "nomic-embed-text"

    asyncio.run(scenario())


def test_embed_rejects_wrong_type_argument() -> None:
    async def scenario() -> None:
        with pytest.raises(TypeError, match="EmbeddingRequest"):
            await _adapter().embed(object())  # type: ignore[arg-type]

    asyncio.run(scenario())


def test_embed_wrong_vector_count_is_rejected() -> None:
    """Live-verified DocuMind evidence: a scalar empty-string request can
    return fewer vectors than requested (EMBEDDING-CAPABILITY-DESIGN.md
    SS9/SS25). The Adapter must not silently accept a short result."""

    async def scenario() -> None:
        response = _FakeResponse({"embeddings": [[1.0, 2.0]]})
        with patch("urllib.request.urlopen", return_value=response):
            with pytest.raises(ModelResponseRejectedError, match="vectors"):
                await _adapter().embed(EmbeddingRequest(("a", "b")))

    asyncio.run(scenario())


def test_embed_inconsistent_dimension_is_rejected() -> None:
    async def scenario() -> None:
        response = _FakeResponse({"embeddings": [[1.0, 2.0], [3.0, 4.0, 5.0]]})
        with patch("urllib.request.urlopen", return_value=response):
            with pytest.raises(ModelResponseRejectedError, match="inconsistent"):
                await _adapter().embed(EmbeddingRequest(("a", "b")))

    asyncio.run(scenario())


def test_embed_non_finite_component_is_rejected() -> None:
    async def scenario() -> None:
        response = _FakeResponse({"embeddings": [[1.0, float("nan")]]})
        with patch("urllib.request.urlopen", return_value=response):
            with pytest.raises(ModelResponseRejectedError, match="non-finite"):
                await _adapter().embed(EmbeddingRequest(("a",)))

    asyncio.run(scenario())


def test_embed_empty_batch_returns_empty_result_without_calling_provider_shape_check() -> (
    None
):
    async def scenario() -> None:
        response = _FakeResponse({"embeddings": []})
        with patch("urllib.request.urlopen", return_value=response):
            result = await _adapter().embed(EmbeddingRequest(()))
        assert result.vectors == ()

    asyncio.run(scenario())


def test_embed_server_error_is_rejected() -> None:
    async def scenario() -> None:
        error = _http_error(500, {"error": "internal error"})
        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(ModelResponseRejectedError):
                await _adapter().embed(EmbeddingRequest(("a",)))

    asyncio.run(scenario())


def test_embed_connection_refused_is_preflight_error() -> None:
    async def scenario() -> None:
        error = urllib.error.URLError(ConnectionRefusedError("refused"))
        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(ModelPreflightError):
                await _adapter().embed(EmbeddingRequest(("a",)))

    asyncio.run(scenario())


def test_ollama_config_requires_all_fields_positive_and_nonempty() -> None:
    with pytest.raises(TypeError):
        OllamaModelConfig("", "m", "e", 1.0)
    with pytest.raises(TypeError):
        OllamaModelConfig("http://x", "m", "e", 0)
    with pytest.raises(TypeError):
        OllamaModelConfig("http://x", "m", "e", -1.0)
