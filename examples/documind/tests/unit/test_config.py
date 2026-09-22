"""DocuMindConfig environment-variable binding: defaults and overrides."""

from __future__ import annotations

from pathlib import Path

import pytest

from documind_app.config import DocuMindConfig


def test_defaults_when_no_environment_set(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "LEGOAI_DOCUMIND_OLLAMA_BASE_URL",
        "LEGOAI_DOCUMIND_CHAT_MODEL",
        "LEGOAI_DOCUMIND_EMBEDDING_MODEL",
        "LEGOAI_DOCUMIND_TIMEOUT_SECONDS",
        "LEGOAI_DOCUMIND_INDEX_PATH",
        "LEGOAI_DOCUMIND_TENANT_ID",
    ):
        monkeypatch.delenv(name, raising=False)

    config = DocuMindConfig.from_environment()

    assert config.base_url == "http://localhost:11434"
    assert config.chat_model == "llama3.2"
    assert config.embedding_model == "nomic-embed-text"
    assert config.timeout_seconds == 60.0
    assert config.index_path == Path(".legoai-documind/index.sqlite3")
    assert config.tenant_id == "local"


def test_environment_overrides_are_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEGOAI_DOCUMIND_OLLAMA_BASE_URL", "http://example:1234")
    monkeypatch.setenv("LEGOAI_DOCUMIND_CHAT_MODEL", "custom-chat")
    monkeypatch.setenv("LEGOAI_DOCUMIND_EMBEDDING_MODEL", "custom-embed")
    monkeypatch.setenv("LEGOAI_DOCUMIND_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("LEGOAI_DOCUMIND_INDEX_PATH", "/tmp/custom-index.sqlite3")
    monkeypatch.setenv("LEGOAI_DOCUMIND_TENANT_ID", "acme")

    config = DocuMindConfig.from_environment()

    assert config.base_url == "http://example:1234"
    assert config.chat_model == "custom-chat"
    assert config.embedding_model == "custom-embed"
    assert config.timeout_seconds == 12.5
    assert config.index_path == Path("/tmp/custom-index.sqlite3")
    assert config.tenant_id == "acme"
