"""OPENAI-COMPATIBLE-REMOTE-1: one wire contract for LOCAL and REMOTE.

The adapter's injected exchange receives exactly the request LOCAL HTTP
would send and its complete response goes through the same status mapping and
parser. No network: the exchange here is a trusted in-process stand-in.
"""

import asyncio
import json
from typing import Any

import pytest

from legoai.intelligence.model.ports import (
    ModelPreflightError,
    ModelResponseRejectedError,
    ModelResponseRetryableRejectedError,
    ModelResponseUncertainError,
)
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatRole,
    EmbeddingRequest,
    ModelId,
    ProviderId,
)
from legoai.reference.model_openai_compatible import (
    OpenAICompatibleModelAdapter,
    OpenAICompatibleModelConfig,
)

CONFIG = OpenAICompatibleModelConfig(
    "https://models.example.org/v1", "model-a", "embed-a", 5.0, 9
)
CHAT = json.dumps(
    {
        "model": "model-a",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "hi"},
                "finish_reason": "stop",
            }
        ],
    }
).encode()


class Exchange:
    def __init__(self, status: int = 200, body: bytes = CHAT) -> None:
        self.status, self.body = status, body
        self.calls: list[tuple[str, bytes]] = []

    def __call__(self, path: str, body: bytes) -> tuple[int, bytes]:
        self.calls.append((path, body))
        return self.status, self.body


def adapter(exchange: Any) -> OpenAICompatibleModelAdapter:
    return OpenAICompatibleModelAdapter(
        CONFIG, ProviderId("remote-endpoint"), exchange=exchange
    )


def chat() -> ChatRequest:
    return ChatRequest((ChatMessage(ChatRole.USER, "hello"),))


def test_exchange_receives_the_exact_local_wire_request() -> None:
    exchange = Exchange()
    result = asyncio.run(adapter(exchange).chat(chat()))
    assert result.content == "hi" and result.model_identity == ModelId("model-a")
    ((path, body),) = exchange.calls
    assert path == "/chat/completions"
    assert json.loads(body) == {
        "model": "model-a",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "max_tokens": 9,
    }


def test_embedding_exchange_and_shared_parser() -> None:
    body = json.dumps(
        {"model": "embed-a", "data": [{"index": 0, "embedding": [1, 2.5]}]}
    ).encode()
    exchange = Exchange(body=body)
    result = asyncio.run(adapter(exchange).embed(EmbeddingRequest(("x",))))
    assert result.vectors == ((1.0, 2.5),)
    assert exchange.calls[0][0] == "/embeddings"
    assert json.loads(exchange.calls[0][1]) == {"model": "embed-a", "input": ["x"]}


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, ModelResponseRejectedError),
        (403, ModelResponseRejectedError),
        (404, ModelResponseRejectedError),
        (500, ModelResponseRejectedError),
        (302, ModelResponseRejectedError),
        (429, ModelResponseRetryableRejectedError),
        (503, ModelResponseRetryableRejectedError),
    ],
)
def test_status_mapping_is_the_local_mapping(status: int, error: type) -> None:
    secret_echo = b'{"error":"CANARY-ECHO-1"}'
    with pytest.raises(error) as raised:
        asyncio.run(adapter(Exchange(status, secret_echo)).chat(chat()))
    assert "CANARY-ECHO" not in repr(raised.value)
    assert raised.value.__cause__ is None


@pytest.mark.parametrize(
    "body", [b"not json", b"[]", b'{"model":"other","choices":[]}', b"NaN"]
)
def test_complete_2xx_is_still_parsed_and_rejected(body: bytes) -> None:
    with pytest.raises(ModelResponseRejectedError) as raised:
        asyncio.run(adapter(Exchange(200, body)).chat(chat()))
    assert raised.value.__cause__ is None and raised.value.__context__ is None


@pytest.mark.parametrize(
    "error", [ModelPreflightError("x"), ModelResponseUncertainError("y")]
)
def test_exchange_errors_propagate_unchanged(error: Exception) -> None:
    def exchange(path: str, body: bytes) -> tuple[int, bytes]:
        raise error

    with pytest.raises(type(error)):
        asyncio.run(adapter(exchange).chat(chat()))


def test_preflight_refusals_never_reach_the_exchange() -> None:
    exchange = Exchange()
    no_embedding = OpenAICompatibleModelConfig(
        "https://models.example.org/v1", "model-a", None, 5.0, None
    )
    with pytest.raises(ModelPreflightError):
        asyncio.run(
            OpenAICompatibleModelAdapter(
                no_embedding, ProviderId("p"), exchange=exchange
            ).embed(EmbeddingRequest(("x",)))
        )
    assert exchange.calls == []


def test_exchange_must_be_callable() -> None:
    with pytest.raises(TypeError):
        OpenAICompatibleModelAdapter(CONFIG, ProviderId("p"), exchange=object())  # type: ignore[arg-type]
