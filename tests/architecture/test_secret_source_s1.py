"""SECRET-SOURCE-S1 boundaries: no ambient, CLI, network or provider source.

The operator-provisioned source lives behind Secret Access in the private
reference realization; configuration, settings and requests carry no
plaintext, and provider adapters do not touch Secret material.
"""

import ast
import dataclasses
import typing
from pathlib import Path

from legoai.execution.agent.ports import AgentRequest
from legoai.intelligence.model.values import ChatRequest, EmbeddingRequest
from legoai.runtime.api import (
    LocalHostConfig,
    ModelBindingConfig,
    OllamaSettings,
    OpenAICompatibleSettings,
    RemoteDisclosureConfig,
    TrustedModelContribution,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    ROOT / "src/legoai/reference/secret.py",
    ROOT / "src/legoai/runtime/_composition/secret.py",
)


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
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _strings(path: Path) -> list[str]:
    tree = _tree(path)
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def test_no_ambient_environment_or_cli_source() -> None:
    for path in SOURCES:
        names = _names(path)
        assert not names & {"environ", "getenv", "putenv", "argv", "ArgumentParser"}
        assert not {t.split(".")[0] for t in _imports(path)} & {
            "os",
            "argparse",
            "dotenv",
            "configparser",
            "tomllib",
            "json",
            "keyring",
        }, path


def test_no_network_transport_or_persistence_in_the_source() -> None:
    forbidden = {
        "socket",
        "ssl",
        "urllib",
        "http",
        "httpx",
        "requests",
        "sqlite3",
        "pickle",
        "shelve",
        "logging",
        "tempfile",
    }
    for path in SOURCES:
        assert not {t.split(".")[0] for t in _imports(path)} & forbidden, path
    source = _imports(ROOT / "src/legoai/reference/secret.py")
    assert not any(
        t.startswith(
            ("legoai.runtime", "legoai.intelligence", "legoai.reference.model")
        )
        or "forgeai" in t
        or "engineering" in t
        for t in source
    )


def test_no_provider_specific_semantics() -> None:
    for path in SOURCES:
        for text in _strings(path):
            lowered = text.lower()
            for word in ("kisski", "openai", "forgeai", "bearer ", "authorization"):
                assert word not in lowered, (path, text)


def test_configuration_settings_and_requests_carry_no_plaintext() -> None:
    suspicious = ("api_key", "token", "secret", "password", "credential", "bearer")
    for value in (
        LocalHostConfig,
        ModelBindingConfig,
        OllamaSettings,
        OpenAICompatibleSettings,
        TrustedModelContribution,
        RemoteDisclosureConfig,
        ChatRequest,
        EmbeddingRequest,
        AgentRequest,
    ):
        hints = typing.get_type_hints(value)
        for field in dataclasses.fields(value):
            # A plaintext credential would be text; numeric bounds such as
            # `max_output_tokens` carry no material.
            textual = str in typing.get_args(hints[field.name]) or hints[
                field.name
            ] in (str, bytes, bytearray)
            assert not (
                textual and any(word in field.name.lower() for word in suspicious)
            ), (value.__name__, field.name)
    assert _fields(ChatRequest) == {"messages", "response_format"}
    assert _fields(EmbeddingRequest) == {"inputs"}
    assert _fields(AgentRequest) == {"context", "text"}


def _fields(value: type) -> set[str]:
    return {field.name for field in dataclasses.fields(value)}


def test_provider_adapters_do_not_touch_secret_material() -> None:
    for adapter in ("model.py", "model_openai_compatible.py", "model_fake.py"):
        imports = _imports(ROOT / "src/legoai/reference" / adapter)
        assert not any("secret" in t for t in imports), adapter
        assert "Authorization" not in (
            ROOT / "src/legoai/reference" / adapter
        ).read_text(encoding="utf-8"), adapter


def test_hidden_input_is_the_only_bootstrap() -> None:
    composition = ROOT / "src/legoai/runtime/_composition/secret.py"
    assert "getpass" in _imports(composition)
    # Material enters only through `provision`; no other S1 entry point.
    tree = _tree(ROOT / "src/legoai/reference/secret.py")
    source_class = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef) and n.name == "_ProvisionedSecretSource"
    )
    public = {
        n.name
        for n in source_class.body
        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
    }
    assert public == {"provision", "retire", "close", "status"}
