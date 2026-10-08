"""MODEL-STRUCTURED-OUTPUT-1: adapter mapping and fail-closed backstops (ADR-022).

Fake HTTP transport only; no network or live provider.
"""

import asyncio
import copy
import json
from typing import Any
from unittest.mock import patch

import pytest

from legoai.intelligence.model.ports import ModelPreflightError
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatResult,
    ChatRole,
    JsonArray,
    JsonObject,
    JsonString,
    ModelId,
    ProviderId,
    StructuredResponseFormat,
)
from legoai.reference.model import OllamaModelAdapter, OllamaModelConfig
from legoai.reference.model_fake import FixedModel
from legoai.reference.model_openai_compatible import (
    OpenAICompatibleModelAdapter,
    OpenAICompatibleModelConfig,
)

MESSAGES = (ChatMessage(ChatRole.SYSTEM, "rules"), ChatMessage(ChatRole.USER, "hi"))


def schema() -> StructuredResponseFormat:
    return StructuredResponseFormat(
        JsonObject(
            (
                ("status", JsonString(enum=("ok", "fail"))),
                ("note", JsonString(max_length=64, nullable=True)),
                ("items", JsonArray(JsonString(max_length=16), max_items=4)),
            ),
            ("status", "items"),
        )
    )


class _Capture:
    """Records the JSON body the adapter would send; returns a fixed reply."""

    def __init__(self, reply: dict[str, object]) -> None:
        self.reply = json.dumps(reply).encode("utf-8")
        self.bodies: list[dict[str, Any]] = []

    def __call__(self, request: Any, timeout: float) -> _Capture:
        self.bodies.append(json.loads(request.data))
        return self

    status = 200

    def read(self) -> bytes:
        return self.reply

    def __enter__(self) -> _Capture:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _ollama() -> OllamaModelAdapter:
    return OllamaModelAdapter(
        OllamaModelConfig(
            "http://localhost:11434", "llama3.2", "nomic-embed-text", 30.0
        ),
        ProviderId("ollama-local"),
    )


def _send(request: ChatRequest) -> dict[str, Any]:
    capture = _Capture({"message": {"role": "assistant", "content": '{"status":"ok"}'}})
    with patch("urllib.request.urlopen", capture):
        result = asyncio.run(_ollama().chat(request))
    assert result.content == '{"status":"ok"}'  # text, exactly as returned
    return capture.bodies[0]


# Ollama mapping A-H


def test_a_no_response_format_request_unchanged() -> None:
    body = _send(ChatRequest(MESSAGES))
    assert body == {
        "model": "llama3.2",
        "messages": [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "hi"},
        ],
        "stream": False,
    }
    assert "format" not in body


def test_b_object_schema_mapped_to_format() -> None:
    body = _send(ChatRequest(MESSAGES, schema()))
    assert set(body) == {"model", "messages", "stream", "format"}
    assert body["format"] == schema().json_schema()
    assert body["format"]["type"] == "object"
    assert body["format"]["additionalProperties"] is False


def test_c_enum_preserved() -> None:
    fmt = _send(ChatRequest(MESSAGES, schema()))["format"]
    assert fmt["properties"]["status"]["enum"] == ["ok", "fail"]


def test_d_arrays_preserved() -> None:
    fmt = _send(ChatRequest(MESSAGES, schema()))["format"]
    assert fmt["properties"]["items"] == {
        "type": "array",
        "items": {"type": "string", "maxLength": 16},
        "maxItems": 4,
    }


def test_e_required_preserved() -> None:
    assert _send(ChatRequest(MESSAGES, schema()))["format"]["required"] == [
        "status",
        "items",
    ]


def test_f_bounds_and_nullable_preserved() -> None:
    note = _send(ChatRequest(MESSAGES, schema()))["format"]["properties"]["note"]
    assert note == {"type": ["string", "null"], "maxLength": 64}


def test_g_caller_object_unchanged() -> None:
    request = ChatRequest(MESSAGES, schema())
    before = copy.deepcopy(request)
    first = request.response_format.json_schema()  # type: ignore[union-attr]
    _send(request)
    assert request == before
    assert request.response_format.json_schema() == first  # type: ignore[union-attr]


def test_h_unsupported_schema_rejected_before_dispatch() -> None:
    capture = _Capture({})
    with patch("urllib.request.urlopen", capture):
        with pytest.raises((TypeError, ValueError)):
            ChatRequest(
                MESSAGES, StructuredResponseFormat(JsonObject((("Bad", JsonString()),)))
            )
    assert capture.bodies == []


def test_ollama_structured_reply_is_not_parsed_by_core() -> None:
    capture = _Capture({"message": {"role": "assistant", "content": "not json at all"}})
    with patch("urllib.request.urlopen", capture):
        result = asyncio.run(_ollama().chat(ChatRequest(MESSAGES, schema())))
    assert result.content == "not json at all"  # consumers parse and validate


# Fail-closed backstops (no silent downgrade)


def test_openai_compatible_refuses_structured_request_before_send() -> None:
    adapter = OpenAICompatibleModelAdapter(
        OpenAICompatibleModelConfig("http://127.0.0.1:8000/v1", "m", None, 30.0, None),
        ProviderId("openai-local"),
    )
    capture = _Capture({})
    with patch("urllib.request.urlopen", capture):
        with pytest.raises(ModelPreflightError, match="structured output"):
            asyncio.run(adapter.chat(ChatRequest(MESSAGES, schema())))
    assert capture.bodies == []


def test_fixed_model_remains_incapable_and_unchanged_for_text() -> None:
    model = FixedModel(ChatResult("x", ModelId("m"), ProviderId("p"), None))
    with pytest.raises(ModelPreflightError, match="structured output"):
        asyncio.run(model.chat(ChatRequest(MESSAGES, schema())))
    assert model.chat_calls == 0
    assert asyncio.run(model.chat(ChatRequest(MESSAGES))).content == "x"
    assert model.chat_calls == 1
