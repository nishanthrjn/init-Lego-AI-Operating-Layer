"""OPENAI-COMPATIBLE-REMOTE-1 boundaries.

Contracts unchanged; one protocol adapter and parser for LOCAL and REMOTE;
the REMOTE plane owns no policy, TLS or parsing; only the host composes it;
no retry, fallback, provider-specific branch or ambient input anywhere.
"""

import ast
import dataclasses
import typing
from pathlib import Path

from legoai.execution.agent.ports import AgentRequest
from legoai.governance.secret import SecretRef
from legoai.intelligence.model.values import ChatRequest, EmbeddingRequest
from legoai.runtime.api import OpenAICompatibleSettings

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src/legoai"
PLANE = SRC / "runtime/_composition/remote_model.py"
ADAPTER = SRC / "reference/model_openai_compatible.py"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _imports(path: Path) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.add(node.module)
    return targets


def _names(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name.lower())
        elif isinstance(node, ast.Name):
            names.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            names.add(node.attr.lower())
    return names


def test_public_contracts_unchanged() -> None:
    def fields(value: type) -> set[str]:
        return {f.name for f in dataclasses.fields(value)}

    assert fields(ChatRequest) == {"messages", "response_format"}
    assert fields(EmbeddingRequest) == {"inputs"}
    assert fields(AgentRequest) == {"context", "text"}
    ports = (SRC / "intelligence/model/ports.py").read_text(encoding="utf-8")
    assert "remote" not in ports.lower() and "secret" not in ports.lower()


def test_settings_carry_only_a_secret_reference() -> None:
    hints = typing.get_type_hints(OpenAICompatibleSettings)
    assert hints["bearer_credential"] == SecretRef | None
    default = {f.name: f for f in dataclasses.fields(OpenAICompatibleSettings)}
    assert default["bearer_credential"].default is None
    assert default["bearer_credential"].repr is False
    for name in hints:
        assert not {"api_key", "token", "authorization", "password"} & {name}


def test_one_protocol_parser_for_local_and_remote() -> None:
    tree = _tree(ADAPTER)
    loads = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "loads"
    ]
    assert len(loads) == 1  # `_payload`: the one JSON decoding of a response
    adapters = [
        n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and "Adapter" in n.name
    ]
    assert [a.name for a in adapters] == ["OpenAICompatibleModelAdapter"]
    # The adapter never sees a credential, header, Secret or attempt.
    text = ADAPTER.read_text(encoding="utf-8")
    for word in ("Authorization", "Bearer", "SecretRef", "_remote_attempts"):
        assert word not in text, word
    assert not any("secret" in t or "credential" in t for t in _imports(ADAPTER))


def test_plane_owns_no_policy_tls_or_parsing() -> None:
    names = _names(PLANE)
    for word in (
        "evaluate_disclosure",
        "retry",
        "fallback",
        "resend",
        "environ",
        "getenv",
        "loads",
        "wrap_bio",
        "sslobject",
    ):
        assert not any(word in name for name in names), word
    imports = _imports(PLANE)
    assert not {t.split(".")[0] for t in imports} & {
        "os",
        "socket",
        "asyncio",
        "threading",
        "urllib",
        "http",
        "json",
        "logging",
    }
    assert "legoai.reference.model_openai_compatible" not in imports


def test_only_the_host_composes_the_plane() -> None:
    importers = set()
    for path in sorted(SRC.rglob("*.py")):
        if "legoai.runtime._composition.remote_model" in _imports(path):
            importers.add(path.relative_to(ROOT).as_posix())
    assert importers == {
        "src/legoai/runtime/local.py",
        # Typed pass-through of the host's plane on the governed paths.
        "src/legoai/runtime/_composition/agent.py",
        "src/legoai/runtime/_composition/model_governed.py",
        # PROVIDER-MODEL-DISCOVERY-1 reuses the shared exact-use request and
        # fault recording; it never composes or calls the Model plane.
        "src/legoai/runtime/_composition/provider_discovery.py",
    }


def test_no_provider_specific_identifiers_or_sdks_in_core() -> None:
    for path in SRC.rglob("*.py"):
        lowered = path.read_text(encoding="utf-8").lower()
        assert "kisski" not in lowered, path
    for path in (PLANE, SRC / "runtime/local.py", SRC / "runtime/api.py"):
        roots = {t.split(".")[0] for t in _imports(path)}
        assert not roots & {"openai", "anthropic", "httpx", "requests", "aiohttp"}
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "\ndependencies = []\n" in pyproject


def test_engineering_and_forgeai_do_not_reach_remote_internals() -> None:
    for consumer in (
        ROOT / "packages/legoai-engineering/src",
        ROOT / "examples/forgeai/src",
    ):
        for path in consumer.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for word in (
                "remote_model",
                "RemoteModelRuntime",
                "bearer_credential",
                "open_credential_source",
                "_credential_https",
            ):
                assert word not in text, (path, word)
