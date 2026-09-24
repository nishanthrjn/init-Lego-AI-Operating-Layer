"""Offline contract evidence for foundational Model reuse and adapter failures."""

import asyncio
import http.client
import urllib.error
from dataclasses import replace
from unittest.mock import patch

import pytest

from legoai.intelligence.model.ports import (
    ModelPort,
    ModelPreflightError,
    ModelResponseRejectedError,
    ModelResponseUncertainError,
)
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatResult,
    ChatRole,
    EmbeddingRequest,
    EmbeddingResult,
    ModelId,
    ProviderId,
)
from legoai.reference.model import OllamaModelAdapter, OllamaModelConfig
from legoai.reference.model_fake import FixedModel

REQUEST = ChatRequest((ChatMessage(ChatRole.USER, "question"),))
RESULT = ChatResult("answer", ModelId("fixture"), ProviderId("offline"), None)


def config() -> OllamaModelConfig:
    return OllamaModelConfig("http://localhost:11434", "chat", "embed", 5.0)


async def consume(model: ModelPort) -> str:
    return (await model.chat(REQUEST)).content


def test_consumer_uses_fake_without_io() -> None:
    first, second = FixedModel(RESULT), FixedModel(RESULT)
    with patch(
        "urllib.request.urlopen", side_effect=AssertionError("network forbidden")
    ):
        assert asyncio.run(consume(first)) == "answer"
    assert first.chat_calls == 1
    assert second.chat_calls == 0


def test_embedding_fixture_obeys_existing_contract() -> None:
    embedding = EmbeddingResult(((1.0,),), 1, ModelId("fixture"), ProviderId("offline"))
    model: ModelPort = FixedModel(RESULT, embedding)
    assert asyncio.run(model.embed(EmbeddingRequest(("text",)))) == embedding
    with pytest.raises(ModelResponseRejectedError):
        asyncio.run(model.embed(EmbeddingRequest(("one", "two"))))
    with pytest.raises(ModelPreflightError):
        asyncio.run(FixedModel(RESULT).embed(EmbeddingRequest(("text",))))


@pytest.mark.parametrize(
    "timeout", [float("nan"), float("inf"), -float("inf"), 0, -1, True]
)
def test_invalid_timeout_rejected_before_io(timeout: float) -> None:
    with pytest.raises(TypeError):
        replace(config(), timeout_seconds=timeout)


@pytest.mark.parametrize(
    "url",
    [
        "file:///private",
        "ftp://localhost",
        "http://",
        "http://user:secret@localhost",
        "http://localhost?token=secret",
        "http://localhost#secret",
        "http://localhost:bad",
        "http://localhost:0",
        "http://local host",
        "http://[invalid",
    ],
)
def test_invalid_endpoint_fails_safely(url: str) -> None:
    with pytest.raises(TypeError) as caught:
        replace(config(), base_url=url)
    assert url not in str(caught.value)


@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError("private"),
        ConnectionResetError("private"),
        http.client.IncompleteRead(b"private"),
        http.client.RemoteDisconnected("private"),
        urllib.error.URLError(ConnectionResetError("private")),
    ],
)
def test_transport_failure_preserves_uncertainty(failure: Exception) -> None:
    model = OllamaModelAdapter(config(), ProviderId("local"))
    with patch("urllib.request.urlopen", side_effect=failure) as transport:
        with pytest.raises(ModelResponseUncertainError) as caught:
            asyncio.run(consume(model))
    assert caught.value.__cause__ is failure
    assert "private" not in str(caught.value)
    assert transport.call_count == 1


class Response:
    status = 200

    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *args: object) -> None:
        pass


@pytest.mark.parametrize("body", [b"\xff", b"not json", b"[]", b'{"message": {}}'])
def test_invalid_response_is_owned_error(body: bytes) -> None:
    with patch("urllib.request.urlopen", return_value=Response(body)):
        with pytest.raises(ModelResponseRejectedError):
            asyncio.run(consume(OllamaModelAdapter(config(), ProviderId("local"))))


def test_adapter_and_fake_are_substitutable_and_timeout_is_explicit() -> None:
    with patch(
        "urllib.request.urlopen",
        return_value=Response(b'{"message":{"content":"answer"}}'),
    ) as transport:
        assert asyncio.run(
            consume(OllamaModelAdapter(config(), ProviderId("local")))
        ) == asyncio.run(consume(FixedModel(RESULT)))
    assert transport.call_args.kwargs["timeout"] == 5.0


def test_provider_error_body_is_not_disclosed_or_read() -> None:
    error = urllib.error.HTTPError("http://localhost", 500, "private", None, None)  # type: ignore[arg-type]
    with (
        patch.object(error, "read", side_effect=AssertionError("must not read")),
        patch("urllib.request.urlopen", side_effect=error),
    ):
        with pytest.raises(ModelResponseRejectedError) as caught:
            asyncio.run(consume(OllamaModelAdapter(config(), ProviderId("local"))))
    assert "private" not in str(caught.value)
    assert "500" in str(caught.value)


@pytest.mark.parametrize("url", ["http://localhost/\u00e9", "http://localhost/\ud800"])
def test_endpoint_encoding_is_validated(url: str) -> None:
    with pytest.raises(TypeError):
        replace(config(), base_url=url)


def test_unrepresentable_timeout_is_configuration_failure() -> None:
    with pytest.raises(TypeError):
        replace(config(), timeout_seconds=10**400)
