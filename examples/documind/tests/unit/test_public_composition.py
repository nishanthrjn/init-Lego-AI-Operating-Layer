"""ADR-014: DocuMind composes through the public local governed host only."""

from __future__ import annotations

import ast
import asyncio
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from legoai.intelligence.model.values import ChatMessage, ChatRequest, ChatRole

from documind_app.composition import DocuMindRuntime, GovernedInvocationError
from documind_app.config import DocuMindConfig

_SOURCE = Path(__file__).resolve().parents[2] / "src" / "documind_app"


def _config(tmp_path: Path, base_url: str = "http://localhost:11434") -> DocuMindConfig:
    return DocuMindConfig(
        base_url=base_url,
        chat_model="llama3.2",
        embedding_model="nomic-embed-text",
        timeout_seconds=30.0,
        index_path=tmp_path / "index.sqlite3",
        tenant_id="local",
    )


def test_application_imports_no_core_internals_or_authority() -> None:
    for path in sorted(_SOURCE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                assert not module.startswith(
                    ("legoai.reference", "legoai.runtime._composition")
                ), (path.name, module)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"Grant", "SecurityContext"}, path.name


def test_opening_the_runtime_contacts_no_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def denied(*args: object, **kwargs: object) -> object:
        raise AssertionError("provider contacted while composing")

    monkeypatch.setattr(urllib.request, "urlopen", denied)
    runtime = DocuMindRuntime(_config(tmp_path))
    assert runtime.published_capabilities() == (
        "legoai.intelligence.model.chat",
        "legoai.intelligence.model.embedding",
    )


def test_invalid_operator_settings_fail_as_governed_error(tmp_path: Path) -> None:
    with pytest.raises(GovernedInvocationError, match="INVALID_CONFIGURATION"):
        DocuMindRuntime(_config(tmp_path, base_url="ftp://user:pw@host"))


def test_provider_refusal_is_reported_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def refused(
        request: urllib.request.Request, timeout: float | None = None
    ) -> object:
        calls.append(request.full_url)
        raise urllib.error.URLError(ConnectionRefusedError())

    monkeypatch.setattr(urllib.request, "urlopen", refused)

    async def scenario() -> None:
        runtime = DocuMindRuntime(_config(tmp_path))
        request = ChatRequest((ChatMessage(ChatRole.USER, "hello"),))
        with pytest.raises(GovernedInvocationError, match="DEPENDENCY_FAILURE"):
            await runtime.governed_chat(request)

    asyncio.run(scenario())
    assert len(calls) == 1
