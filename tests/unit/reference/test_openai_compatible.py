"""ADR-014 minimal wire and conservative failure matrix, offline only."""

import asyncio
import socket
import urllib.error
import urllib.request
from unittest.mock import patch

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
from tests.support.openai_http import Script, chat_payload, embedding_payload, server

CHAT = ChatRequest(
    (ChatMessage(ChatRole.SYSTEM, "system"), ChatMessage(ChatRole.USER, "hello"))
)
EMBED = EmbeddingRequest(("first", "second"))


def adapter(
    url: str, *, tokens: int | None = None, timeout: float = 1.0
) -> OpenAICompatibleModelAdapter:
    return OpenAICompatibleModelAdapter(
        OpenAICompatibleModelConfig(url, "chat-model", "embed-model", timeout, tokens),
        ProviderId("local-endpoint"),
    )


@pytest.mark.parametrize("tokens", [None, 23])
@pytest.mark.parametrize("trailing_slash", [False, True])
def test_chat_minimal_wire(tokens: int | None, trailing_slash: bool) -> None:
    script = Script(chat_payload())
    with server(script) as url:
        result = asyncio.run(
            adapter(url + ("/" if trailing_slash else ""), tokens=tokens).chat(CHAT)
        )
    assert result.content == "hello"
    assert result.model_identity == ModelId("chat-model")
    assert result.provider_identity == ProviderId("local-endpoint")
    assert result.usage is None
    path, headers, body = script.requests[0]
    assert len(script.requests) == 1
    assert path == "/v1/chat/completions"
    assert "/v1/v1/" not in path
    assert "authorization" not in {name.lower() for name in headers}
    expected = {
        "model": "chat-model",
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "hello"},
        ],
        "stream": False,
    }
    if tokens is not None:
        expected["max_tokens"] = tokens
    assert body == expected


def test_exact_versioned_url_regression() -> None:
    # Exact operator example without occupying a fixed port.
    with patch(
        "urllib.request.OpenerDirector.open",
        side_effect=urllib.error.URLError(ConnectionRefusedError()),
    ) as call:
        with pytest.raises(ModelPreflightError):
            asyncio.run(adapter("http://127.0.0.1:8000/v1").chat(CHAT))
    assert (
        call.call_args.args[0].full_url == "http://127.0.0.1:8000/v1/chat/completions"
    )
    assert call.call_count == 1


@pytest.mark.parametrize(
    "usage, expected",
    [
        ({"prompt_tokens": 3, "completion_tokens": 2}, (3, 2)),
        ({"prompt_tokens": -1, "completion_tokens": True}, (None, None)),
        ({}, (None, None)),
        ({"prompt_tokens": "3", "completion_tokens": 1.5}, (None, None)),
    ],
)
def test_optional_usage(
    usage: dict[str, object], expected: tuple[int | None, int | None]
) -> None:
    payload = chat_payload()
    payload["usage"] = usage
    with server(Script(payload)) as url:
        result = asyncio.run(adapter(url).chat(CHAT))
    assert result.usage is not None
    assert (result.usage.prompt_tokens, result.usage.completion_tokens) == expected


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        {"model": "other", "choices": []},
        b"{broken",
        b'data: {"choices": []}\n\ndata: [DONE]\n',
        {"choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}]},
        *(
            {"model": "chat-model", "choices": value}
            for value in ([], [1], [1, 2], None)
        ),
        *(
            {
                "model": "chat-model",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "hello"},
                        "finish_reason": finish,
                    }
                ],
            }
            for finish in ("length", "tool_calls", "content_filter", None)
        ),
        {
            "model": "chat-model",
            "choices": [{"message": {"role": "assistant", "content": "hello"}}],
        },
        *(
            {
                "model": "chat-model",
                "choices": [{"message": message, "finish_reason": "stop"}],
            }
            for message in (
                None,
                {},
                {"role": "assistant", "content": None},
                {"role": "assistant", "content": 1},
                {"role": "user", "content": "hello"},
                {"content": "hello"},
                {"role": "assistant", "content": "hello", "tool_calls": []},
            )
        ),
    ],
)
def test_chat_rejections_no_streaming(payload: object) -> None:
    script = Script(payload)
    with server(script) as url, pytest.raises(ModelResponseRejectedError) as error:
        asyncio.run(adapter(url).chat(CHAT))
    assert type(error.value) is ModelResponseRejectedError
    assert len(script.requests) == 1


@pytest.mark.parametrize("status", [302, 400, 401, 403, 404, 429, 500, 502, 503, 504])
@pytest.mark.parametrize("embedding", [False, True])
def test_http_status(status: int, embedding: bool) -> None:
    script = Script(b"PRIVATE_PROVIDER_BODY", status)
    expected = (
        ModelResponseRetryableRejectedError
        if status in (429, 503)
        else ModelResponseRejectedError
    )
    with server(script) as url, pytest.raises(expected) as error:
        model = adapter(url)
        asyncio.run(model.embed(EMBED) if embedding else model.chat(CHAT))
    assert type(error.value) is expected
    assert "PRIVATE_PROVIDER_BODY" not in str(error.value)
    assert len(script.requests) == 1  # no Retry-After handling, redirect or retry


@pytest.mark.parametrize("mode", ["timeout", "reset", "truncated"])
@pytest.mark.parametrize("status", [200, 429, 503])
def test_uncertain_response(mode: str, status: int) -> None:
    script = Script(b'{"partial":', status, mode)
    with server(script) as url, pytest.raises(ModelResponseUncertainError):
        asyncio.run(adapter(url, timeout=0.05).chat(CHAT))
    assert len(script.requests) == 1


def test_connection_refused() -> None:
    # Bound but not listening: port cannot be reused by another local server.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        url = f"http://127.0.0.1:{sock.getsockname()[1]}/v1"
        with pytest.raises(ModelPreflightError):
            asyncio.run(adapter(url, timeout=5.0).chat(CHAT))


def test_dns_failure_and_ambiguous_transport() -> None:
    for cause, expected in (
        (socket.gaierror(), ModelPreflightError),
        (OSError(), ModelResponseUncertainError),
    ):
        with (
            patch(
                "urllib.request.OpenerDirector.open",
                side_effect=urllib.error.URLError(cause),
            ),
            pytest.raises(expected),
        ):
            asyncio.run(adapter("http://unused.invalid/v1").chat(CHAT))


def test_embedding_wire_and_identity() -> None:
    script = Script(embedding_payload())
    with server(script) as url:
        result = asyncio.run(adapter(url).embed(EMBED))
    assert result.vectors == ((1.0, 0.0), (0.0, 1.0))
    assert result.dimension == 2
    assert result.model_identity == ModelId("embed-model")
    assert result.provider_identity == ProviderId("local-endpoint")
    assert script.requests[0][0] == "/v1/embeddings"
    assert script.requests[0][2] == {
        "model": "embed-model",
        "input": ["first", "second"],
    }


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        [1, 2],
        [{"embedding": [1]}, {"index": 1, "embedding": [2]}],
        [{"index": 0, "embedding": [1]}, {"index": 0, "embedding": [2]}],
        [{"index": 1, "embedding": [1]}, {"index": 0, "embedding": [2]}],
        [{"index": False, "embedding": [1]}, {"index": 1, "embedding": [2]}],
        [{"index": 0, "embedding": [1]}, {"index": 1, "embedding": [2, 3]}],
        *(
            [{"index": 0, "embedding": [value]}, {"index": 1, "embedding": [1]}]
            for value in (
                float("nan"),
                float("inf"),
                -float("inf"),
                True,
                "1",
                None,
                10**400,
            )
        ),
        [{"index": 0, "embedding": []}, {"index": 1, "embedding": []}],
    ],
)
def test_embedding_invalid_vectors(data: object) -> None:
    with (
        server(Script({"model": "embed-model", "data": data})) as url,
        pytest.raises(ModelResponseRejectedError),
    ):
        asyncio.run(adapter(url).embed(EMBED))


@pytest.mark.parametrize("payload", [b"{bad", {}, {"model": "wrong", "data": []}])
def test_embedding_invalid_identity(payload: object) -> None:
    with server(Script(payload)) as url, pytest.raises(ModelResponseRejectedError):
        asyncio.run(adapter(url).embed(EMBED))


def test_empty_embeddings() -> None:
    with server(Script({"model": "embed-model", "data": []})) as url:
        result = asyncio.run(adapter(url).embed(EmbeddingRequest(())))
    assert result.vectors == () and result.dimension == 0


@pytest.mark.parametrize("model", [None, "wrong-model", "CHAT-MODEL", 7])
@pytest.mark.parametrize("embedding", [False, True])
def test_exact_response_identity_only(model: object, embedding: bool) -> None:
    # Every other field is valid: this isolates identity validation.
    payload = embedding_payload() if embedding else chat_payload()
    if model is None:
        del payload["model"]
    else:
        payload["model"] = model
    with server(Script(payload)) as url, pytest.raises(ModelResponseRejectedError):
        instance = adapter(url)
        asyncio.run(instance.embed(EMBED) if embedding else instance.chat(CHAT))


def test_no_ambient_proxy_lookup() -> None:
    script = Script(chat_payload())
    with (
        server(script) as url,
        patch(
            "urllib.request.getproxies",
            side_effect=AssertionError("ambient proxy lookup"),
        ),
    ):
        asyncio.run(adapter(url).chat(CHAT))
    assert len(script.requests) == 1


@pytest.mark.parametrize(
    "raw",
    [
        b'{"PRIVATE_PROVIDER_BODY":',
        b'{"model":"wrong","model":"chat-model","choices":[]}',
        b'{"model":"chat-model","extra":NaN}',
    ],
)
def test_malformed_json_has_no_body_exception_chain(raw: bytes) -> None:
    with server(Script(raw)) as url, pytest.raises(ModelResponseRejectedError) as error:
        asyncio.run(adapter(url).chat(CHAT))
    assert error.value.__cause__ is None
    assert error.value.__context__ is None
    assert "PRIVATE_PROVIDER_BODY" not in str(error.value)
