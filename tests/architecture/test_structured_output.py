"""MODEL-STRUCTURED-OUTPUT-1 architecture guards (ADR-022)."""

import ast
import dataclasses
import subprocess
from pathlib import Path

from legoai.intelligence.model import routing, values

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "legoai"
BASE = "3916451"  # request policy H1 qualification recorded
CONTRACT = [
    SRC / "intelligence/model/values.py",
    SRC / "intelligence/model/routing.py",
    SRC / "intelligence/model/ports.py",
]


def _imports(path: Path) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def test_core_contract_imports_no_provider() -> None:
    for path in CONTRACT:
        for module in _imports(path):
            assert not module.startswith(("legoai.reference", "legoai.runtime")), path
            assert "ollama" not in module and "openai" not in module, path


def test_no_provider_specific_field_names_in_core_api() -> None:
    names = {
        f.name
        for cls in (
            values.ChatRequest,
            values.StructuredResponseFormat,
            values.JsonObject,
            values.JsonString,
            values.JsonArray,
            routing.ModelBinding,
        )
        for f in dataclasses.fields(cls)
    }
    assert not names & {
        "format",
        "grammar",
        "options",
        "extra_body",
        "json_mode",
        "ollama",
        "openai",
    }
    assert "structured_output" in names and "response_format" in names


def test_agent_contracts_do_not_import_providers() -> None:
    for path in (SRC / "execution/agent").rglob("*.py"):
        for module in _imports(path):
            assert "reference.model" not in module and "ollama" not in module, path


def test_adapters_depend_on_core_not_reverse() -> None:
    adapter = _imports(SRC / "reference/model.py")
    assert "legoai.intelligence.model.values" in adapter
    for path in CONTRACT:
        assert "legoai.reference.model" not in _imports(path)


def test_no_evaluator_dependency_in_core() -> None:
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "safety_eval" not in text and "forgeai" not in text.lower(), path


def test_safety_eval3_unchanged() -> None:
    path = "examples/forgeai/evaluation/analyst_sufficiency_safety_eval3"
    assert _git("diff", "--name-only", BASE, "--", path) == ""
    assert _git("status", "--porcelain", "--", path) == ""


def test_h1_request_policy_unchanged() -> None:
    for path in (
        "packages/legoai-engineering/src/legoai_engineering/analyst/request_policy.py",
        "examples/forgeai/evaluation/analyst_evidence_loop",
        "examples/forgeai/evaluation/analyst_sufficiency_hardening_h1",
    ):
        assert _git("diff", "--name-only", BASE, "--", path) == ""
        assert _git("status", "--porcelain", "--", path) == ""


def test_agent_definition_and_output_contract_unchanged() -> None:
    for path in ("src/legoai/execution/agent", "src/legoai/reference/agent.py"):
        assert _git("diff", "--name-only", BASE, "--", path) == ""
