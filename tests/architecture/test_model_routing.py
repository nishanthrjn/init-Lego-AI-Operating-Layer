"""M6.5 pure boundary controls; these are not hostile Python isolation."""

import ast
from dataclasses import fields
from pathlib import Path

import pytest

from legoai.intelligence.model.routing import ModelBinding, ModelRequirement
from legoai.intelligence.model.values import ModelId, ProviderId
from tests.architecture.test_import_boundaries import violations


def _pure_violations(source: str) -> set[str]:
    tree = ast.parse(source)
    errors: set[str] = set()
    allowed_modules = {
        "dataclasses",
        "enum",
        "legoai.kernel.identity",
        "legoai.kernel.references",
        "legoai.kernel.context",
        "legoai.intelligence.model.values",
        "legoai.intelligence.model.routing",
    }
    for statement in tree.body:
        if not isinstance(
            statement,
            (ast.Import, ast.ImportFrom, ast.ClassDef, ast.FunctionDef, ast.Expr),
        ) or (
            isinstance(statement, ast.Expr)
            and not (
                isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            )
        ):
            errors.add("module-state-or-effect")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name not in allowed_modules for alias in node.names):
                errors.add("import")
        if isinstance(node, ast.ImportFrom):
            if node.level or node.module not in allowed_modules:
                errors.add("import")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id not in {
                    "dataclass",
                    "field",
                    "type",
                    "len",
                    "set",
                    "any",
                    "tuple",
                    "_validate",
                    "_validate_bindings",
                    "TypeError",
                    "ValueError",
                    "ModelRouteDecision",
                }:
                    errors.add("call")
            elif not (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in {"add", "isspace"}
            ):
                errors.add("call")
    return errors


def test_routing_has_only_pure_contract_dependencies_and_calls() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    for relative in ("intelligence/model/routing.py", "reference/model_routing.py"):
        source = (root / relative).read_text(encoding="utf-8")
        assert _pure_violations(source) == set()


@pytest.mark.parametrize(
    "source",
    [
        "import socket",
        "import os",
        "import importlib",
        "from legoai.intelligence.model.ports import ModelPort",
        "from legoai.execution.ports import DispatchPermit",
        "from legoai.governance.ports import AuthorizationPort",
        "from legoai.intelligence.agent import Agent",
        "import legoai.workflow",
        "import legoai.team",
        "registry = {}",
        "adapter.chat(request)",
        "adapter.embed(request)",
        "open('file')",
        "__import__('provider')",
    ],
)
def test_purity_control_rejects_io_invocation_authority_and_global_state(
    source: str,
) -> None:
    assert _pure_violations(source)


@pytest.mark.parametrize(
    "module",
    ["legoai.intelligence.model.routing", "legoai.reference.model_routing"],
)
@pytest.mark.parametrize(
    "target",
    [
        "legoai.reference.model",
        "legoai.reference.execution",
        "legoai.execution.values",
        "legoai.governance.ports",
        "legoai.runtime._composition.model_governed",
        "legoai.intelligence.agent",
        "legoai.workflow",
        "legoai.team",
    ],
)
def test_routing_cannot_import_runtime_or_other_owners(
    module: str, target: str
) -> None:
    assert violations({module: f"import {target}"})


def test_generic_values_expose_only_typed_inert_selection_data() -> None:
    assert {f.name for f in fields(ModelRequirement)} == {"profile"}
    assert {f.name: f.type for f in fields(ModelBinding)} == {
        "binding_id": str,
        "requirement": ModelRequirement,
        "model_id": ModelId,
        "provider_id": ProviderId,
    }
