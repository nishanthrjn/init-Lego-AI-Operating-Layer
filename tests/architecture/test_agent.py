"""M7 owner dependency and bypass controls; not hostile-code isolation."""

import ast
from pathlib import Path

import pytest


def _violations(module: str, source: str) -> set[str]:
    common = {"dataclasses", "enum", "typing"}
    allowed = {
        "execution.agent.values": {"legoai.kernel.identity"},
        "execution.agent.ports": {
            "legoai.execution.agent.values",
            "legoai.execution.values",
            "legoai.intelligence.model.routing",
            "legoai.intelligence.model.values",
            "legoai.kernel.versions",
        },
        "reference.agent": {
            "legoai.execution.agent.ports",
            "legoai.execution.agent.values",
            "legoai.execution.values",
            "legoai.intelligence.model.ports",
            "legoai.intelligence.model.routing",
            "legoai.intelligence.model.values",
        },
        "runtime._composition.agent": {
            "legoai.execution.agent.ports",
            "legoai.execution.ports",
            "legoai.execution.values",
            "legoai.intelligence.model.routing",
            "legoai.intelligence.model.values",
            "legoai.kernel.effects",
            "legoai.kernel.errors",
            "legoai.reference.execution",
            "legoai.runtime._composition.model_governed",
        },
    }[module] | common
    errors: set[str] = set()
    tree = ast.parse(source)
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
            errors.add("module-state")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name not in allowed for alias in node.names):
                errors.add("dependency")
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module not in allowed:
                errors.add("dependency")
            if any(alias.name in {"ModelPort", "*"} for alias in node.names):
                errors.add("bypass")
            if node.module == "legoai.intelligence.model.ports" and any(
                alias.name != "ModelRouterPort" for alias in node.names
            ):
                errors.add("bypass")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in {
                "chat",
                "embed",
            }:
                errors.add("bypass")
            if isinstance(node.func, ast.Name) and node.func.id in {
                "open",
                "eval",
                "exec",
                "__import__",
                "getattr",
            }:
                errors.add("bypass")
    return errors


@pytest.mark.parametrize(
    "module",
    [
        "execution.agent.values",
        "execution.agent.ports",
        "reference.agent",
        "runtime._composition.agent",
    ],
)
def test_agent_module_boundaries(module: str) -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    path = root.joinpath(*module.split(".")).with_suffix(".py")
    source = path.read_text(encoding="utf-8")
    assert _violations(module, source) == set()


@pytest.mark.parametrize(
    "source",
    [
        "from legoai.intelligence.model.ports import ModelPort",
        "from legoai.reference.model import OllamaModelAdapter",
        "import legoai_engineering",
        "import importlib",
        "import os",
        "import openai",
        "import langgraph",
        "import crewai",
        "import legoai.execution.workflow",
        "import legoai.coordination",
        "adapter.chat(request)",
        "adapter.embed(request)",
        "registry = {}",
        "router.route(requirement, tenant)",
        "__import__('provider')",
        "getattr(adapter, 'chat')(request)",
        "open('secret')",
    ],
)
def test_driver_rejects_provider_tools_frameworks_and_bypass(source: str) -> None:
    assert _violations("reference.agent", source)


def test_contracts_have_no_provider_or_runtime_fields() -> None:
    from dataclasses import fields

    from legoai.execution.agent.ports import AgentDefinition, AgentRequest

    assert {item.name for item in fields(AgentDefinition)} == {
        "agent_id",
        "behavior_version",
        "instructions",
        "model_requirement",
        "output_contract",
        "max_input_bytes",
        "max_prompt_bytes",
    }
    assert {item.name for item in fields(AgentRequest)} == {"context", "text"}
