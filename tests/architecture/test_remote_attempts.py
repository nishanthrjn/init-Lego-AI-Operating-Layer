"""REMOTE-ATTEMPT-CUSTODY-1 ownership: the Model invocation plane's store.

No transport, provider adapter, Secret material, consumer or retry path; the
public runtime, ModelPort and request types are unchanged.
"""

import ast
import dataclasses
from pathlib import Path

from legoai.intelligence.model.values import ChatRequest, EmbeddingRequest

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "src/legoai/reference/_remote_attempts.py"
COMPOSITION = ROOT / "src/legoai/runtime/_composition/remote_attempt.py"


def _imports(path: Path) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.add(node.module)
    return targets


def _identifiers(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name.lower())
        elif isinstance(node, ast.Name):
            names.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            names.add(node.attr.lower())
    return names


def test_no_transport_provider_consumer_or_material_imports() -> None:
    for path in (STORE, COMPOSITION):
        imports = _imports(path)
        assert not {t.split(".")[0] for t in imports} & {
            "socket",
            "ssl",
            "urllib",
            "http",
            "httpx",
            "requests",
            "asyncio",
        }, path
        assert not any(
            t.startswith("legoai.reference.model")
            or t == "legoai.reference.secret"
            or "forgeai" in t
            or "engineering" in t
            for t in imports
        ), path


def test_no_retry_resend_or_scheduler_path() -> None:
    for path in (STORE, COMPOSITION):
        names = _identifiers(path)
        for word in ("retry", "resend", "requeue", "schedule", "fallback", "queued"):
            assert not any(word in name for name in names), (path, word)


def test_only_the_invocation_plane_reaches_the_store() -> None:
    importers = set()
    for path in sorted((ROOT / "src").rglob("*.py")):
        if any(t == "legoai.reference._remote_attempts" for t in _imports(path)):
            importers.add(path.relative_to(ROOT).as_posix())
    assert importers == {
        "src/legoai/runtime/_composition/remote_attempt.py",
        # CREDENTIAL-HTTPS-T2: the invocation plane claims and settles.
        "src/legoai/runtime/_composition/credential_https.py",
        # OPENAI-COMPATIBLE-REMOTE-1: the REMOTE plane intends and settles.
        "src/legoai/runtime/_composition/remote_model.py",
    }
    for adapter in (
        "model.py",
        "model_openai_compatible.py",
        "model_fake.py",
        "secret.py",
    ):
        assert "_remote_attempts" not in (
            ROOT / "src/legoai/reference" / adapter
        ).read_text(encoding="utf-8")
    for public in ("src/legoai/runtime/api.py", "src/legoai/runtime/local.py"):
        assert "remote_attempt" not in (ROOT / public).read_text(encoding="utf-8")


def test_model_port_and_requests_unchanged() -> None:
    def fields(value: type) -> set[str]:
        return {f.name for f in dataclasses.fields(value)}

    assert fields(ChatRequest) == {"messages", "response_format"}
    assert fields(EmbeddingRequest) == {"inputs"}
    ports = ROOT / "src/legoai/intelligence/model/ports.py"
    assert not any("remote_attempt" in name for name in _identifiers(ports))
    assert not any("attempt" in t for t in _imports(ports))


def test_store_schema_holds_no_content_columns() -> None:
    from legoai.reference._remote_attempts import _schema

    schema = _schema().lower()
    for word in (
        "prompt",
        "content",
        "message",
        "response_body",
        "header",
        "material",
        "token",
    ):
        assert word not in schema, word
