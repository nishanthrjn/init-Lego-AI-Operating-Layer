"""Same selection and transport cases run in source and standalone exports."""

import asyncio
import json
import urllib.error
from email.message import Message
from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from assessment_starter.core.config import Settings
from assessment_starter.main import create_app
from assessment_starter.model import (
    ChatMessage,
    ChatRequest,
    ChatRole,
    FixedModel,
    ModelResponseUncertainError,
)
from assessment_starter.model_factory import make_model

REQUEST = ChatRequest((ChatMessage(ChatRole.USER, "Hello"),))


class Response:
    status = 200

    def __init__(
        self, body: bytes = b'{"message":{"content":"Real adapter fixture"}}'
    ) -> None:
        self.body = body

    def read(self, maximum: int = -1) -> bytes:
        return self.body if maximum < 0 else self.body[:maximum]

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *args: object) -> None:
        pass


def selected() -> Settings:
    return Settings.from_environment(
        {
            "MODEL_PROVIDER": "ollama",
            "OLLAMA_MODEL": "installed-chat",
            "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
            "MODEL_TIMEOUT_SECONDS": "7",
        }
    )


def test_default_is_fixed_and_construction_never_connects() -> None:
    with patch("urllib.request.urlopen", side_effect=AssertionError("No startup I/O")):
        offline = make_model(Settings.from_environment({}))
        live = make_model(selected())
    assert isinstance(offline, FixedModel)
    assert not isinstance(live, FixedModel)
    assert "offline answer" in asyncio.run(offline.chat(REQUEST)).content


def test_selected_model_flows_through_real_adapter() -> None:
    with patch("urllib.request.urlopen", return_value=Response()) as transport:
        with TestClient(create_app(selected())) as client:
            response = client.post("/api/v1/ask", json={"question": "Hello"})
    assert response.json() == {"answer": "Real adapter fixture"}
    outgoing = transport.call_args.args[0]
    assert outgoing.full_url == "http://127.0.0.1:11434/api/chat"
    assert json.loads(outgoing.data) == {
        "model": "installed-chat",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }
    assert transport.call_args.kwargs["timeout"] == 7.0
    assert transport.call_count == 1


@pytest.mark.parametrize(
    "environment",
    [
        {"MODEL_PROVIDER": "unknown"},
        {"MODEL_PROVIDER": "ollama"},
        {"MODEL_PROVIDER": "ollama", "OLLAMA_MODEL": "   "},
        {"MODEL_TIMEOUT_SECONDS": "not-a-number"},
        {"MODEL_TIMEOUT_SECONDS": "nan"},
        {"MODEL_TIMEOUT_SECONDS": "inf"},
        {"MODEL_TIMEOUT_SECONDS": "0"},
        {"MODEL_TIMEOUT_SECONDS": "301"},
        {"OLLAMA_BASE_URL": "file:///private"},
        {"OLLAMA_BASE_URL": "http://user:secret@localhost"},
    ],
)
def test_invalid_settings_fail_before_io(environment: dict[str, str]) -> None:
    with patch(
        "urllib.request.urlopen", side_effect=AssertionError("No configuration I/O")
    ):
        with pytest.raises(ValueError):
            Settings.from_environment(environment)


@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError("private"),
        urllib.error.URLError(ConnectionRefusedError("private")),
        urllib.error.HTTPError(
            "http://localhost", 500, "private", Message(), BytesIO(b"private")
        ),
    ],
)
def test_api_provider_failures_are_safe_and_not_retried(failure: Exception) -> None:
    with patch("urllib.request.urlopen", side_effect=failure) as transport:
        with TestClient(create_app(selected())) as client:
            response = client.post("/api/v1/ask", json={"question": "Hello"})
    assert response.status_code == 502
    assert "private" not in response.text
    assert "Model request failed" in response.json()["detail"]
    assert transport.call_count == 1


@pytest.mark.parametrize("body", [b"not json", b"[]", b'{"message":{"content":9}}'])
def test_unusable_provider_response_is_502(body: bytes) -> None:
    with patch("urllib.request.urlopen", return_value=Response(body)):
        with TestClient(create_app(selected())) as client:
            assert (
                client.post("/api/v1/ask", json={"question": "Hello"}).status_code
                == 502
            )


def test_timeout_keeps_uncertainty_at_model_boundary() -> None:
    with patch("urllib.request.urlopen", side_effect=TimeoutError("private")):
        with pytest.raises(ModelResponseUncertainError):
            asyncio.run(make_model(selected()).chat(REQUEST))


def test_injected_model_overrides_selection() -> None:
    model = make_model(Settings())
    with patch(
        "urllib.request.urlopen", side_effect=AssertionError("Injected model must win")
    ):
        with TestClient(create_app(selected(), model=model)) as client:
            response = client.post("/api/v1/ask", json={"question": "Hello"})
    assert "offline answer" in response.json()["answer"]
