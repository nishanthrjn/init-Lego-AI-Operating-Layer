"""ADR-026 fitness controls: contracts, sole composition entry, no type leaks."""

import ast
import inspect
import typing
from pathlib import Path

import pytest

from legoai.execution.values import ExecutionContext
from legoai.reference.execution import ExecutionCoordinator
from legoai.runtime import api, local
from tests.architecture.test_consumer_private_boundaries import references
from tests.architecture.test_import_boundaries import violations

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ("legoai.reference", "legoai.runtime._composition")


def private_annotation(value: object) -> bool:
    return str(getattr(value, "__module__", "")).startswith(PRIVATE) or any(
        private_annotation(item) for item in typing.get_args(value)
    )


def forbidden_imports(source: str, module: str) -> bool:
    if module == "legoai.runtime.local" or module.startswith(PRIVATE):
        return False
    return any(target.startswith(PRIVATE) for target in references(source, module))


@pytest.mark.parametrize(
    ("module", "source", "forbidden"),
    [
        (
            "legoai.runtime.local",
            "from legoai.reference.execution import ExecutionCoordinator",
            False,
        ),
        (
            "legoai.runtime.api",
            "from legoai.reference.execution import ExecutionCoordinator",
            True,
        ),
        (
            "legoai.runtime.other",
            "from legoai.reference import execution as e",
            True,
        ),
        (
            "legoai.runtime.other",
            "from ._composition import model_governed",
            True,
        ),
        (
            "consumer.owner",
            "from legoai.runtime.local import open_governed_execution",
            False,
        ),
    ],
)
def test_import_rule_controls(module: str, source: str, forbidden: bool) -> None:
    assert forbidden_imports(source, module) is forbidden


def test_actual_public_modules_obey_single_composition_rule() -> None:
    root = ROOT / "src"
    for path in root.rglob("*.py"):
        module = ".".join(path.relative_to(root).with_suffix("").parts)
        assert not forbidden_imports(path.read_text(encoding="utf-8"), module), module


def test_public_annotations_and_negative_controls() -> None:
    assert private_annotation(ExecutionCoordinator)
    assert private_annotation(tuple[ExecutionCoordinator, ...])
    assert not private_annotation(ExecutionContext)
    assert not private_annotation(tuple[ExecutionContext, ...])
    targets: list[object] = [
        api.GovernedExecutionConfig,
        local.open_governed_execution,
        local.GovernedExecution.__init__,
    ]
    for name, value in vars(local.GovernedExecution).items():
        if not name.startswith("_"):
            if isinstance(value, property):
                assert value.fget is not None
                targets.append(value.fget)
            elif inspect.isfunction(value):
                targets.append(value)
    for target in targets:
        for annotation in typing.get_type_hints(target).values():
            assert not private_annotation(annotation), (target, annotation)


def test_api_contract_boundary_and_no_new_protocol_or_owner_dispatch() -> None:
    path = ROOT / "src/legoai/runtime/api.py"
    source = path.read_text(encoding="utf-8")
    assert "runtime-api" not in violations({"legoai.runtime.api": source})
    assert "runtime-api" in violations(
        {"legoai.runtime.api": "from legoai.runtime.local import GovernedExecution"}
    )
    config = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.ClassDef) and node.name == "GovernedExecutionConfig"
    )
    assert config.bases == []
    members = {
        name for name in vars(local.GovernedExecution) if not name.startswith("_")
    }
    assert members == {
        "configuration",
        "contribution",
        "establish",
        "coordinate",
        "claim",
        "settle",
        "revoke_authority",
        "retire_contribution",
        "close",
    }
