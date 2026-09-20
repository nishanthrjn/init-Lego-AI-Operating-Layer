"""ADR-002: static F0 import policy, including type-only imports and re-exports.

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
                    if name.startswith("legoai.kernel.") and not (
                        target == "legoai.kernel" or target.startswith("legoai.kernel.")
                    ):
                        errors.add("kernel-owner")
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
