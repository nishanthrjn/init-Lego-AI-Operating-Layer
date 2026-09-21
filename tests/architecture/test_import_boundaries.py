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
                    if (
                        name.startswith("legoai.application.")
                        and name != "legoai.application.ports"
                        and not (
                            target == "legoai.kernel"
                            or target.startswith("legoai.kernel.")
                            or target == "legoai.application"
                            or target.startswith("legoai.application.")
                        )
                    ):
                        errors.add("application-owner")
                    if (
                        name.startswith("legoai.application.")
                        and name != "legoai.application.ports"
                        and any(
                            target == f"legoai.application.{layer}"
                            or target.startswith(f"legoai.application.{layer}.")
                            for layer in ("ports", "reference", "runtime")
                        )
                    ):
                        errors.add("values-layer")
                    if name == "legoai.application.ports" and not any(
                        target == allowed or target.startswith(allowed + ".")
                        for allowed in (
                            "legoai.kernel",
                            "legoai.application.values",
                            "legoai.evidence.values",
                            "legoai.governance.values",
                        )
                    ):
                        errors.add("application-port")
                    if name.startswith("legoai.evidence.") and not any(
                        target == allowed or target.startswith(allowed + ".")
                        for allowed in ("legoai.kernel", "legoai.evidence.values")
                    ):
                        errors.add("evidence-owner")
                    if (
                        name.startswith("legoai.reference.application.")
                        and name
                        not in {
                            "legoai.reference.application.records",
                            "legoai.reference.application.migrations",
                        }
                        and not (
                            target == "legoai.kernel"
                            or target.startswith("legoai.kernel.")
                            or target == "legoai.application.values"
                            or target.startswith("legoai.application.values.")
                            or target == "legoai.reference.application"
                            or target.startswith("legoai.reference.application.")
                        )
                    ):
                        errors.add("reference-owner")
                    if name in {
                        "legoai.reference.application.records",
                        "legoai.reference.application.migrations",
                    }:
                        allowed_modules = (
                            (
                                "legoai.kernel",
                                "legoai.application.values",
                                "legoai.application.ports",
                                "legoai.evidence.values",
                                "legoai.governance.values",
                            )
                            if name.endswith(".records")
                            else (
                                "legoai.kernel.identity",
                                "legoai.reference.application.records",
                            )
                        )
                        if not any(
                            target == allowed or target.startswith(allowed + ".")
                            for allowed in allowed_modules
                        ):
                            errors.add("record-owner")
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
            "from legoai.governance.values import Principal",
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
    root = Path(__file__).resolve().parents[2] / "src" / "legoai"
    for relative in ("application/values.py", "reference/application/configuration.py"):
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


@pytest.mark.parametrize(
    ("module", "source", "reason"),
    [
        (
            "legoai.application.ports",
            "import tests.support.configuration_store",
            "test-import",
        ),
        (
            "legoai.application.ports",
            "import legoai.reference.application.configuration",
            "application-port",
        ),
        (
            "legoai.application.values",
            "import legoai.evidence.values",
            "application-owner",
        ),
        (
            "legoai.evidence.values",
            "import legoai.application.values",
            "evidence-owner",
        ),
        ("legoai.evidence.values", "import legoai.governance.values", "evidence-owner"),
        ("legoai.kernel.identity", "import legoai.evidence.values", "kernel-owner"),
    ],
)
def test_f4_boundaries(module: str, source: str, reason: str) -> None:
    assert reason in violations({module: source})


def test_f4_inward_graph_and_no_persistence() -> None:
    assert not violations(
        {
            "legoai.application.ports": "from legoai.evidence.values import SourceRequirement\nfrom legoai.governance.values import OperationContext\nfrom legoai.application.values import ComposedConfiguration",
            "legoai.evidence.values": "from legoai.kernel.references import ReferenceScope",
        }
    )
    root = Path(__file__).resolve().parents[2]
    files = (
        list((root / "src").rglob("*.py"))
        + list((root / "tests/support").rglob("*.py"))
        + list((root / "tests/contracts").rglob("*.py"))
    )
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                assert not {alias.name.split(".")[0] for alias in node.names} & {
                    "sqlite3",
                    *({"json"} if path.name != "records.py" else set()),
                }
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in {"sqlite3"} | (
                    {"json"} if path.name != "records.py" else set()
                )


@pytest.mark.parametrize(
    "source",
    [
        "from legoai.reference.application.configuration import compose_configuration",
        "import legoai.runtime",
        "import legoai.reference.application.sqlite_store",
    ],
)
def test_f5_records_no_runtime_or_recomposition(source: str) -> None:
    assert "record-owner" in violations(
        {"legoai.reference.application.records": source}
    )


def test_f5_data_only_modules() -> None:
    root = Path(__file__).resolve().parents[2] / "src/legoai/reference/application"
    for name in ("records.py", "migrations.py"):
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not {alias.name.split(".")[0] for alias in node.names} & {
                    "pickle",
                    "marshal",
                    "shelve",
                    "sqlite3",
                }
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in {
                    "pickle",
                    "marshal",
                    "shelve",
                    "sqlite3",
                }
            if isinstance(node, ast.Name):
                assert node.id not in {"eval", "exec", "literal_eval", "open"}
