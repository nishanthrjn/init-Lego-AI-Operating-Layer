"""ADR-002: F0/F1 import policy, including type-only imports and re-exports.

This small source checker is a development control, not hostile-code isolation.
Synthetic graphs are parsed as text, never written to executable import paths.
"""

import ast
import sys
from pathlib import Path

import pytest


def violations(sources: dict[str, str]) -> set[str]:
    errors: set[str] = set()
    edges: dict[str, set[str]] = {name: set() for name in sources}
    for name, source in sources.items():
        tree = ast.parse(source)
        package = name.removesuffix(".__init__")
        if name.endswith(".__init__"):
            if any(
                not (
                    isinstance(n, ast.Expr)
                    and isinstance(n.value, ast.Constant)
                    and isinstance(n.value.value, str)
                )
                for n in tree.body
            ):
                errors.add("initializer")
        else:
            package = name.rpartition(".")[0]
        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if any(alias.name == "*" for alias in node.names):
                    errors.add("star")
                base = node.module or ""
                if node.level:
                    parts = package.split(".")
                    if node.level > len(parts):
                        errors.add("relative-escape")
                        continue
                    base = ".".join(
                        parts[: len(parts) - node.level + 1] + ([base] if base else [])
                    )
                targets = [base] + [f"{base}.{a.name}" for a in node.names]
            elif isinstance(node, (ast.Name, ast.Attribute)):
                identifier = node.id if isinstance(node, ast.Name) else node.attr
                if identifier in {
                    "__import__",
                    "eval",
                    "exec",
                    "compile",
                }:
                    errors.add("dynamic")
            for target in targets:
                root = target.split(".")[0]
                if root in {"importlib", "runpy", "pkgutil", "ctypes"} or target.rsplit(
                    ".", 1
                )[-1] in {"__import__", "eval", "exec", "compile"}:
                    errors.add("dynamic")
                if root in {"tests", "test_support"}:
                    errors.add("test-import")
                elif root == "legoai":
                    if name.startswith("legoai.application.") and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.application"
                        or target.startswith("legoai.application.")
                        # ADR-002 SS9.2: Application's allowed-foreign-targets row
                        # includes G (Governance) and O (Evidence/Observability).
                        # F4 is the first real consumer of both; only these two
                        # are widened here, not the full ADR-002 maximum.
                        or target == "legoai.governance"
                        or target.startswith("legoai.governance.")
                        or target == "legoai.evidence"
                        or target.startswith("legoai.evidence.")
                    ):
                        errors.add("application-owner")
                    if name.startswith("legoai.application.") and any(
                        target == f"legoai.application.{layer}"
                        or target.startswith(f"legoai.application.{layer}.")
                        for layer in ("ports", "reference", "runtime")
                    ):
                        errors.add("values-layer")
                    if name.startswith("legoai.reference.application.") and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.application.values"
                        or target.startswith("legoai.application.values.")
                        or target == "legoai.reference.application"
                        or target.startswith("legoai.reference.application.")
                    ):
                        errors.add("reference-owner")
                    if name.startswith("legoai.kernel.") and not (
                        target == "legoai.kernel" or target.startswith("legoai.kernel.")
                    ):
                        errors.add("kernel-owner")
                    if name.startswith("legoai.governance.") and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.governance"
                        or target.startswith("legoai.governance.")
                    ):
                        errors.add("governance-owner")
                    if name.startswith("legoai.governance.") and any(
                        target == f"legoai.governance.{layer}"
                        or target.startswith(f"legoai.governance.{layer}.")
                        for layer in ("ports", "reference", "runtime")
                    ):
                        errors.add("values-layer")
                    if name.startswith("legoai.evidence.") and not (
                        target == "legoai.kernel"
                        or target.startswith("legoai.kernel.")
                        or target == "legoai.evidence"
                        or target.startswith("legoai.evidence.")
                    ):
                        # F4 gives evidence.values only Kernel, deliberately
                        # stricter than ADR-002's G-inclusive maximum for O,
                        # matching the Gate-1 plan's own narrower F4 scope.
                        errors.add("evidence-owner")
                    if name.startswith("legoai.evidence.") and any(
                        target == f"legoai.evidence.{layer}"
                        or target.startswith(f"legoai.evidence.{layer}.")
                        for layer in ("ports", "reference", "runtime")
                    ):
                        errors.add("values-layer")
                elif root not in sys.stdlib_module_names:
                    errors.add("external")
                if target in sources:
                    edges[name].add(target)
                if f"{target}.__init__" in sources:
                    edges[name].add(f"{target}.__init__")

    def visit(name: str, active: set[str], done: set[str]) -> None:
        if name in active:
            errors.add("cycle")
            return
        if name in done:
            return
        active.add(name)
        for target in edges[name]:
            visit(target, active, done)
        active.remove(name)
        done.add(name)

    done: set[str] = set()
    for name in edges:
        visit(name, set(), done)
    return errors


def test_production_boundaries() -> None:
    root = Path(__file__).resolve().parents[2] / "src"
    sources = {
        ".".join(p.relative_to(root).with_suffix("").parts): p.read_text(
            encoding="utf-8"
        )
        for p in root.rglob("*.py")
    }
    assert sources
    assert violations(sources) == set()


@pytest.mark.parametrize(
    ("source", "reason"),
    [
        ("import legoai.reference", "kernel-owner"),
        ("from ..reference import adapter", "kernel-owner"),
        ("import tests.support", "test-import"),
        (
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n import legoai.runtime",
            "kernel-owner",
        ),
        ("from dataclasses import *", "star"),
        ("import importlib as loader", "dynamic"),
        ("__import__('legoai.reference')", "dynamic"),
        ("loader = __import__\nloader('legoai.reference')", "dynamic"),
        ("from builtins import __import__ as loader", "dynamic"),
        ("import ctypes", "dynamic"),
        ("import provider_sdk", "external"),
    ],
)
def test_checker_rejects(source: str, reason: str) -> None:
    assert reason in violations({"legoai.kernel.identity": source})


def test_reexport_and_initializer() -> None:
    assert violations(
        {
            "legoai.kernel.identity": "from .bridge import secret",
            "legoai.kernel.bridge": "from legoai.reference import secret",
            "legoai.__init__": "from legoai.kernel import identity",
        }
    ) == {"kernel-owner", "initializer"}


def test_cycle() -> None:
    assert "cycle" in violations(
        {"legoai.kernel.a": "from . import b", "legoai.kernel.b": "from . import a"}
    )


def test_valid_graph() -> None:
    assert not violations(
        {
            "legoai.__init__": '"""Inert."""',
            "legoai.kernel.identity": "from dataclasses import dataclass",
        }
    )


@pytest.mark.parametrize(
    "owner", ["application", "reference", "runtime", "resources.values"]
)
def test_governance_owner_boundary(owner: str) -> None:
    assert violations({"legoai.governance.values": f"import legoai.{owner}"}) == {
        "governance-owner"
    }


def test_kernel_cannot_import_governance() -> None:
    assert violations(
        {"legoai.kernel.context": "from legoai.governance.values import Principal"}
    ) == {"kernel-owner"}


def test_governance_values_cannot_import_ports_via_helper() -> None:
    assert "values-layer" in violations(
        {"legoai.governance.values": "from .ports import check"}
    )
    assert "governance-owner" in violations(
        {
            "legoai.governance.values": "from .pure import Principal",
            "legoai.governance.pure": "from legoai.resources.values import Balance",
        }
    )


def test_governance_inward_graph() -> None:
    assert not violations(
        {
            "legoai.governance.__init__": '"""Inert."""',
            "legoai.governance.values": "from legoai.kernel.context import TenantContext",
            "legoai.kernel.context": "from .identity import TenantId",
            "legoai.kernel.identity": "from dataclasses import dataclass",
        }
    )


def test_no_ambient_context_or_module_state() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert not any(
            isinstance(node, (ast.Assign, ast.AnnAssign)) for node in tree.body
        ), path
        assert not any(
            isinstance(node, (ast.Global, ast.Nonlocal)) for node in ast.walk(tree)
        ), path
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not {alias.name.split(".")[0] for alias in node.names} & {
                    "contextvars",
                    "threading",
                }, path

            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in {
                    "contextvars",
                    "threading",
                }, path


@pytest.mark.parametrize(
    ("module", "source", "reason"),
    [
        (
            "legoai.application.values",
            "from legoai.reference.application import configuration",
            "application-owner",
        ),
        (
            "legoai.application.values",
            "from legoai.resources.values import Balance",
            "application-owner",
        ),
        ("legoai.application.values", "from .ports import Store", "values-layer"),
        (
            "legoai.reference.application.configuration",
            "import legoai.runtime",
            "reference-owner",
        ),
        (
            "legoai.reference.application.configuration",
            "import legoai.reference.governance",
            "reference-owner",
        ),
        (
            "legoai.reference.application.configuration",
            "import provider_sdk",
            "external",
        ),
        ("legoai.kernel.context", "import legoai.application.values", "kernel-owner"),
    ],
)
def test_f2_boundaries(module: str, source: str, reason: str) -> None:
    assert reason in violations({module: source})


def test_f2_cycle_and_indirect_import() -> None:
    assert {"application-owner", "cycle"} <= violations(
        {
            "legoai.application.values": "from .helper import Value",
            "legoai.application.helper": "from legoai.reference.application.configuration import compose",
            "legoai.reference.application.configuration": "from legoai.application.values import Value",
        }
    )


def test_f2_pure_module_dependencies() -> None:
    # Scoped to reference/application/configuration.py only: F4 deliberately
    # extends application/values.py beyond F2's original pure-fixture scope
    # (it now legitimately imports OwnerRevision/ConfigurationRevisionRef for
    # the operation/result/duty model) -- see test_f4_boundaries below for
    # values.py's own, F4-scoped import constraints.
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    for relative in ("reference/application/configuration.py",):
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] in {
                    "dataclasses",
                    "enum",
                    "typing",
                    "legoai",
                }
                assert not {alias.name for alias in node.names} & {
                    "OwnerRevision",
                    "ConfigurationRevisionRef",
                    "OperationContext",
                }
            if isinstance(node, ast.Import):
                assert all(
                    alias.name.split(".")[0]
                    in {"dataclasses", "enum", "typing", "legoai"}
                    for alias in node.names
                )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"open", "print", "input"}


# --- F4: evidence-owner boundary, and application's widened (but still
# narrow) access to evidence/governance -----------------------------------


@pytest.mark.parametrize(
    "owner", ["application", "reference", "runtime", "resources.values", "capabilities"]
)
def test_evidence_owner_boundary(owner: str) -> None:
    assert violations({"legoai.evidence.values": f"import legoai.{owner}"}) == {
        "evidence-owner"
    }


def test_evidence_values_cannot_import_ports_via_helper() -> None:
    assert "values-layer" in violations(
        {"legoai.evidence.values": "from .ports import check"}
    )
    assert "evidence-owner" in violations(
        {
            "legoai.evidence.values": "from .pure import Requirement",
            "legoai.evidence.pure": "from legoai.governance.values import Principal",
        }
    )


def test_evidence_inward_graph() -> None:
    assert not violations(
        {
            "legoai.evidence.__init__": '"""Inert."""',
            "legoai.evidence.values": "from legoai.kernel.references import ConfigurationRevisionRef",
            "legoai.kernel.references": "from .identity import ApplicationId",
            "legoai.kernel.identity": "from dataclasses import dataclass",
        }
    )


def test_kernel_cannot_import_evidence() -> None:
    assert violations(
        {
            "legoai.kernel.provenance": "from legoai.evidence.values import EvidenceRequirement"
        }
    ) == {"kernel-owner"}


@pytest.mark.parametrize(
    ("module", "source", "reason"),
    [
        (
            "legoai.application.values",
            "from legoai.evidence.values import EvidenceRequirement",
            None,
        ),
        (
            "legoai.application.values",
            "from legoai.governance.values import Principal",
            None,
        ),
        (
            "legoai.application.values",
            "from legoai.capabilities.values import Requirement",
            "application-owner",
        ),
        (
            "legoai.application.values",
            "from legoai.execution.values import ExecutionId",
            "application-owner",
        ),
        (
            "legoai.application.values",
            "from legoai.plugins.values import PluginId",
            "application-owner",
        ),
    ],
)
def test_f4_boundaries(module: str, source: str, reason: str | None) -> None:
    result = violations({module: source})
    if reason is None:
        assert "application-owner" not in result
    else:
        assert reason in result


def test_application_ports_does_not_depend_on_reference_implementation() -> None:
    assert "application-owner" in violations(
        {
            "legoai.application.ports": "from legoai.reference.application import configuration"
        }
    )


def test_test_support_configuration_store_is_rejected_as_production_import() -> None:
    assert "test-import" in violations(
        {
            "legoai.application.values": "from tests.support.configuration_store import InMemoryConfigurationStore"
        }
    )


def test_no_database_driver_imported_by_production_source() -> None:
    # sqlite3 is stdlib, so the generic "external" check does not catch it --
    # F4/F5 introduce no real persistence yet (that is F6a's scope), so no
    # production module may import it or any other database driver.
    forbidden_db_roots = {
        "sqlite3",
        "psycopg",
        "psycopg2",
        "asyncpg",
        "sqlalchemy",
        "pymongo",
        "redis",
    }
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    offenders: dict[str, set[str]] = {}
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found |= {
                    alias.name.split(".")[0] for alias in node.names
                } & forbidden_db_roots
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in forbidden_db_roots:
                    found.add(node.module.split(".")[0])
        if found:
            offenders[str(path.relative_to(root))] = found
    assert offenders == {}


def test_no_ai_or_agent_framework_imported_by_production_source() -> None:
    forbidden_ai_roots = {
        "semantic_kernel",
        "agent_framework",
        "openai",
        "anthropic",
        "ollama",
        "langchain",
        "langgraph",
    }
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    offenders: dict[str, set[str]] = {}
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found |= {
                    alias.name.split(".")[0] for alias in node.names
                } & forbidden_ai_roots
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in forbidden_ai_roots:
                    found.add(node.module.split(".")[0])
        if found:
            offenders[str(path.relative_to(root))] = found
    assert offenders == {}


def test_no_documind_or_document_pack_import_by_core() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            roots: set[str] = set()
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots = {node.module.split(".")[0]}
            if roots & {"legoai_document", "documind"}:
                offenders.append(str(path.relative_to(root)))
    assert offenders == []
