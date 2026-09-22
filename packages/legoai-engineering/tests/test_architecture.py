"""Independent pack, pure implementation and concrete intake consumer boundaries."""

import ast
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest


def import_violations(source: str, module: str = "") -> set[str]:
    """Closed per-module imports; only the local adapter may perform file I/O."""
    allowed = {
        "dataclasses",
        "legoai_engineering.repository.values",
    }
    additions = {
        "errors": {"enum"},
        "workspace": {"enum", "legoai_engineering.repository.errors"},
        "ports": {"typing", "legoai_engineering.repository.workspace"},
        "local": {
            "os",
            "stat",
            "sys",
            "pathlib",
            "legoai_engineering.repository.errors",
            "legoai_engineering.repository.workspace",
        },
    }
    allowed.update(additions.get(module, set()))
    errors: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            errors.update(
                alias.name for alias in node.names if alias.name not in allowed
            )
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module not in allowed:
                errors.add(node.module or "relative")
            if any(alias.name == "*" for alias in node.names):
                errors.add("star")
            if node.module == "os":
                errors.add("os-from-import")
        elif isinstance(node, ast.Attribute) and node.attr in {
            "system",
            "popen",
            "spawnl",
            "execv",
            "write_text",
            "write_bytes",
            "unlink",
            "rename",
            "mkdir",
            "cwd",
            "getcwd",
        }:
            errors.add(node.attr)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "open" and (
                not node.args
                or not isinstance(node.args[0], ast.Constant)
                or node.args[0].value != "rb"
                or node.keywords
            ):
                errors.add("non-readonly-open")
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and node.func.attr not in {"fstat", "scandir"}
            ):
                errors.add("unsupported-os-call")
        elif isinstance(node, ast.Name) and node.id in {
            "__import__",
            "open",
            "eval",
            "exec",
            "compile",
        }:
            errors.add(node.id)
    return errors


def test_source_boundaries_and_inert_initializers() -> None:
    root = Path(__file__).resolve().parents[1]
    for path in (root / "src").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert not import_violations(source, path.stem), path
        if path.name == "__init__.py":
            assert all(
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
                for node in ast.parse(source).body
            )
    with (root / "pyproject.toml").open("rb") as stream:
        assert tomllib.load(stream)["project"]["dependencies"] == []


@pytest.mark.parametrize(
    "source",
    [
        "import documind_app",
        "from forgeai import app",
        "from legoai.reference.execution import ExecutionCoordinator",
        "from legoai.runtime._composition import direct",
        "import openai",
        "import subprocess",
        "import socket",
        "if False:\n    import langgraph",
        "__import__('os')",
        "open('repository')",
    ],
)
def test_forbidden_dependencies_are_detected(source: str) -> None:
    assert import_violations(source)
    assert import_violations(source, "local")


@pytest.mark.parametrize(
    "source",
    [
        "import os\nos.system('bad')",
        "from os import system",
        "Path.cwd()",
        "path.write_text('bad')",
        "import legoai_engineering.repository.local",
    ],
)
def test_no_io_leak_into_values_or_ports(source: str) -> None:
    for module in ("values", "workspace", "ports"):
        assert import_violations(source, module)


@pytest.mark.parametrize(
    "source", ["path.open('wb')", "os.remove('a')", "os.system('bad')"]
)
def test_local_adapter_cannot_write_or_launch_processes(source: str) -> None:
    assert import_violations(source, "local")


def test_core_does_not_import_engineering_pack() -> None:
    root = Path(__file__).resolve().parents[3]
    core = root / "src" / "legoai"
    assert core.is_dir(), "run this repository boundary check from the checkout"
    for path in core.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                assert not any(
                    alias.name.split(".")[0] == "legoai_engineering"
                    for alias in node.names
                ), path
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] != "legoai_engineering", path


def test_import_and_inspection_have_no_external_effects(tmp_path: Path) -> None:
    script = """
import dataclasses, os, sys, threading, logging, pathlib, stat, enum, typing
from unittest.mock import patch
threads = tuple(threading.enumerate())
handlers = tuple(logging.getLogger().handlers)
def denied(*args, **kwargs):
    raise AssertionError('unexpected side effect')
def audit(event, args):
    if event == 'open':
        path, mode, flags = args
        if not isinstance(path, str) or not path.endswith(('.py', '.pyc')):
            raise AssertionError('non-code file access')
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise AssertionError('write')
    if event.startswith(('socket.', 'subprocess.', 'sqlite3.')):
        raise AssertionError(event)
sys.addaudithook(audit)
with (
    patch.object(threading.Thread, 'start', denied),
    patch.object(os, 'getenv', denied),
    patch.object(type(os.environ), '__getitem__', denied),
):
    from legoai_engineering.repository.api import inspect_text
    from legoai_engineering.repository.values import InspectionRequest, RepositoryText
    import legoai_engineering.repository.errors
    import legoai_engineering.repository.workspace
    import legoai_engineering.repository.ports
    import legoai_engineering.repository.local
    assert inspect_text(InspectionRequest((RepositoryText('a', 'x'),), 'x', 1)).matches
assert tuple(threading.enumerate()) == threads
assert tuple(logging.getLogger().handlers) == handlers
"""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert list(tmp_path.iterdir()) == []


def test_intake_consumer(tmp_path: Path) -> None:
    example = Path(__file__).resolve().parents[1] / "examples" / "repository_intake.py"
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(example)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "pyproject.toml:2:1"
