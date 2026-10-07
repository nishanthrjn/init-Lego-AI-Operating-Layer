"""Accepted addendum and private realization boundaries; no live provider."""

import ast
import inspect
import sys
from pathlib import Path

from legoai.runtime import api
from tests.architecture.test_import_boundaries import violations
from tests.integration.composition.test_openai_compatible import application

ROOT = Path(__file__).resolve().parents[2]


def test_accepted_adr() -> None:
    text = (ROOT / "adrs/ADR-014.md").read_text(encoding="utf-8")
    addendum = text.split("## 14. Provider portability addendum", 1)[1]
    assert "**Status: ACCEPTED 2026-10-07" in addendum
    assert "`stream: false`" in addendum
    assert "POST {base_url}/chat/completions" in addendum


def test_private_stdlib_adapter_no_credentials() -> None:
    path = ROOT / "src/legoai/reference/model_openai_compatible.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(n.name.split(".")[0] for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module.split(".")[0])
        if isinstance(node, ast.Name):
            assert node.id not in {"getenv", "environ", "SecretRef", "api_key"}
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"getenv", "environ"}
    assert imports <= sys.stdlib_module_names | {"legoai"}
    assert "os" not in imports
    assert not hasattr(api, "OpenAICompatibleModelAdapter")
    assert not hasattr(api, "model_chat_offer")
    for module in ("model_openai_compatible", "model_capabilities"):
        assert "reference-owner" in violations(
            {
                "legoai.reference."
                + module: "from legoai.runtime.local import open_local_host"
            }
        )


def test_neutral_helper_migration() -> None:
    for name in (
        "runtime/local.py",
        "runtime/_composition/model_selection.py",
        "runtime/_composition/model_governed.py",
    ):
        text = (ROOT / "src/legoai" / name).read_text(encoding="utf-8")
        assert "model_capabilities import" in text
        assert "ollama_chat_offer" not in text
        assert "ollama_embedding_offer" not in text
    text = (ROOT / "src/legoai/reference/model.py").read_text(encoding="utf-8")
    assert "model_capabilities import" in text
    assert 'CapabilityId("legoai.intelligence.model.chat")' not in text


def test_application_provider_independence() -> None:
    source = inspect.getsource(application)
    assert "reference" not in source
    assert "OpenAI" not in source and "Ollama" not in source
    assert not any(
        isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(ast.parse(source))
    )
    assert (
        inspect.signature(application).parameters["host"].annotation is api.GovernedHost
    )
