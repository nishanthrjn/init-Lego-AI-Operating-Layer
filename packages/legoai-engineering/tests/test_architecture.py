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
        "coding.definition": {
            "legoai.execution.agent.ports",
            "legoai.execution.agent.values",
            "legoai.intelligence.model.routing",
            "legoai.kernel.versions",
        },
        "coding.values": {
            "enum",
            "legoai.execution.agent.ports",
            "legoai.execution.agent.values",
            "legoai.execution.values",
            "legoai_engineering.analyst.values",
            "legoai_engineering.coding.definition",
            "legoai_engineering.repository.mutation",
            "legoai_engineering.repository.workspace",
        },
        "coding.api": {
            "json", "typing",
            "legoai.execution.agent.ports",
            "legoai.execution.agent.values",
            "legoai.kernel.context",
            "legoai_engineering.analyst.values",
            "legoai_engineering.coding.definition",
            "legoai_engineering.coding.values",
            "legoai_engineering.repository.errors",
            "legoai_engineering.repository.mutation",
            "legoai_engineering.repository.workspace",
        },
        "coding._composition": {
            "legoai.kernel.context",
            "legoai_engineering.analyst._composition",
            "legoai_engineering.analyst.values",
            "legoai_engineering.coding.values",
            "legoai_engineering.repository.errors",
            "legoai_engineering.repository.mutation",
            "legoai_engineering.repository.workspace",
        },
        "reviewer.definition": {
            "legoai.execution.agent.ports",
            "legoai.execution.agent.values",
            "legoai.intelligence.model.routing",
            "legoai.kernel.versions",
        },
        "reviewer.values": {
            "enum",
            "legoai.execution.agent.ports",
            "legoai.execution.agent.values",
            "legoai.execution.values",
            "legoai_engineering.reviewer.definition",
        },
        "reviewer.api": {
            "json",
            "legoai.execution.agent.ports",
            "legoai.execution.agent.values",
            "legoai_engineering.reviewer.definition",
            "legoai_engineering.reviewer.values",
        },
        "analyst.values": {
            "enum",
            "legoai.execution.agent.ports",
            "legoai.execution.agent.values",
            "legoai.execution.values",
            "legoai_engineering.repository.workspace",
        },
        "analyst.api": {
            "json",
            "typing",
            "legoai.execution.agent.ports",
            "legoai.execution.agent.values",
            "legoai.intelligence.model.routing",
            "legoai.kernel.context",
            "legoai.kernel.versions",
            "legoai_engineering.analyst.values",
            "legoai_engineering.repository.workspace",
            "legoai_engineering.repository.errors",
        },
        "analyst._composition": {
            "collections.abc",
            "datetime",
            "legoai.governance.ports",
            "legoai.kernel.context",
            "legoai.kernel.references",
            "legoai_engineering.analyst.values",
            "legoai_engineering.repository.errors",
            "legoai_engineering.repository.ports",
            "legoai_engineering.repository.workspace",
        },
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
        "mutation": {
            "hashlib",
            "enum",
            "legoai_engineering.repository.errors",
            "legoai_engineering.repository.workspace",
        },
        "mutation_ports": {"typing", "legoai_engineering.repository.mutation"},
        "mutation_errors": {
            "enum",
            "legoai_engineering.repository.mutation",
            "legoai_engineering.repository.workspace",
        },
        "mutation_local": {
            "os",
            "stat",
            "tempfile",
            "pathlib",
            "legoai_engineering.repository.errors",
            "legoai_engineering.repository.local",
            "legoai_engineering.repository.mutation",
            "legoai_engineering.repository.mutation_errors",
            "legoai_engineering.repository.workspace",
        },
        "git.errors": {"enum"},
        "git.values": {"enum", "legoai_engineering.repository.workspace"},
        "git.ports": {"typing", "legoai_engineering.git.values"},
        "git._config": {"legoai_engineering.git.errors"},
        "git._parse": {
            "legoai_engineering.git.errors",
            "legoai_engineering.git.values",
            "legoai_engineering.repository.workspace",
        },
        "git._process": {
            "os",
            "subprocess",
            "time",
            "enum",
            "pathlib",
            "legoai_engineering.git.errors",
        },
        "git.local": {
            "os",
            "pathlib",
            "legoai_engineering.git._config",
            "legoai_engineering.git._parse",
            "legoai_engineering.git._process",
            "legoai_engineering.git.errors",
            "legoai_engineering.git.values",
            "legoai_engineering.repository.local",
            "legoai_engineering.repository.workspace",
        },
        "checks.values": {"enum", "legoai_engineering.repository.workspace"},
        "checks.errors": {"enum"},
        "checks.ports": {"typing", "legoai_engineering.checks.values"},
        "checks._process": {
            "os",
            "subprocess",
            "time",
            "pathlib",
            "legoai_engineering.checks.errors",
            "legoai_engineering.checks.values",
        },
        "checks.local": {
            "os",
            "pathlib",
            "legoai_engineering.checks._process",
            "legoai_engineering.checks.values",
            "legoai_engineering.repository.errors",
            "legoai_engineering.repository.local",
            "legoai_engineering.repository.workspace",
        },
        "sandbox.values": {"legoai_engineering.repository.workspace"},
        "sandbox.errors": {"enum"},
        "sandbox.ports": {"typing", "legoai_engineering.sandbox.values"},
        "sandbox._process": {
            "os",
            "subprocess",
            "time",
            "pathlib",
            "legoai_engineering.sandbox.errors",
            "legoai_engineering.sandbox.ports",
        },
        "sandbox.docker": {
            "base64",
            "json",
            "os",
            "tempfile",
            "time",
            "uuid",
            "pathlib",
            "typing",
            "legoai_engineering.sandbox._process",
            "legoai_engineering.sandbox._programs",
            "legoai_engineering.sandbox.errors",
            "legoai_engineering.sandbox.ports",
            "legoai_engineering.sandbox.values",
        },
    }
    allowed.update(additions.get(module, set()))
    errors: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if module.startswith("coding.") and (
            (isinstance(node, ast.Attribute) and node.attr in {"apply", "check"})
            or (isinstance(node, ast.Name) and node.id in {"apply", "check"})
        ):
            errors.add("coding-cannot-apply-or-check")
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
            if not (module == "mutation_local" and node.attr == "unlink"):
                errors.add(node.attr)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
            ):
                if (
                    module
                    not in {"git._process", "checks._process", "sandbox._process"}
                    or node.func.attr != "Popen"
                ):
                    errors.add("unsupported-process-call")
                keywords = {item.arg: item.value for item in node.keywords}
                shell = keywords.get("shell")
                if not isinstance(shell, ast.Constant) or shell.value is not False:
                    errors.add("shell-must-be-false")
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
                and node.func.attr
                not in (
                    {"read", "write", "set_blocking"}
                    if module == "sandbox._process"
                    else {"read", "set_blocking"}
                    if module in {"git._process", "checks._process"}
                    else (
                        {"fstat", "fdopen", "close", "chmod", "link", "replace"}
                        if module == "mutation_local"
                        else {"fstat", "scandir"}
                    )
                )
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
        module = (
            path.parent.name + "." + path.stem
            if path.parent.name in {"git", "checks", "sandbox", "analyst", "reviewer", "coding"}
            else path.stem
        )
        assert not import_violations(source, module), path
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
        "import legoai_engineering.repository.mutation",
        "from legoai_engineering.repository.mutation_ports import RepositoryMutationPort",
        "import legoai_engineering.checks.ports",
        "import legoai_engineering.sandbox.docker",
        "import legoai_engineering.git.local",
        "from legoai_engineering.repository.local import LocalRepositoryWorkspace",
        "import subprocess",
        "import os",
        "import openai",
        "import langgraph",
        "from legoai.intelligence.model.ports import ModelPort",
        "import legoai.reference.model",
        "import legoai.reference.agent",
    ],
)
def test_analyst_cannot_import_effectful_implementations(source: str) -> None:
    for module in ("analyst.api", "analyst.values", "analyst._composition"):
        assert import_violations(source, module)


@pytest.mark.parametrize(
    "source",
    [
        "from legoai_engineering.repository.mutation_ports import RepositoryMutationPort",
        "import legoai_engineering.repository.mutation",
        "import legoai_engineering.repository.mutation_local",
        "import legoai_engineering.repository.local",
        "import legoai_engineering.checks.ports",
        "import legoai_engineering.sandbox.docker",
        "import legoai_engineering.git.local",
        "import legoai.governance.values",
        "from legoai.intelligence.model.ports import ModelPort",
        "import legoai.reference.model",
        "import subprocess",
        "import os",
        "import openai",
        "import langgraph",
        "open('a.py')",
        "path.write_text('replacement')",
    ],
)
def test_reviewer_effectful_imports_and_calls_are_forbidden(source: str) -> None:
    for module in ("reviewer.api", "reviewer.values", "reviewer.definition"):
        assert import_violations(source, module)


@pytest.mark.parametrize("source", [
    "from legoai_engineering.repository.mutation_ports import RepositoryMutationPort",
    "from legoai_engineering.repository.mutation_local import LocalRepositoryMutation",
    "import legoai_engineering.repository.local",
    "import legoai_engineering.checks.local",
    "import legoai_engineering.sandbox.ports",
    "import legoai_engineering.sandbox.docker",
    "import legoai_engineering.git.local",
    "import legoai_engineering.reviewer.api",
    "from legoai.intelligence.model.ports import ModelPort",
    "import legoai.reference.model", "import openai", "import langgraph",
    "import subprocess", "writer.apply(changes)", "apply(changes)",
    "checks.check(request)", "path.write_text('code')", "open('file', 'w')",
])
def test_coding_can_propose_but_cannot_apply_or_execute(source: str) -> None:
    for module in ("coding.api", "coding.values", "coding.definition", "coding._composition"):
        assert import_violations(source, module)


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
    for module in ("values", "workspace", "ports", "git.values", "git.ports"):
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
import subprocess, time, tempfile, hashlib, uuid, json, base64, binascii
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
    import legoai_engineering.git.values
    import legoai_engineering.git.ports
    from legoai_engineering.git.local import (
        LocalGitRepository, LocalGitExecutable, GitReadPolicy,
    )
    from legoai_engineering.repository.local import LocalWorkspaceRoot
    from legoai_engineering.repository.mutation import (
        FileChange, FileChangeKind, RepositoryChangeSet,
    )
    from legoai_engineering.repository.mutation_local import LocalRepositoryMutation
    import legoai_engineering.repository.mutation_ports
    from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy
    LocalRepositoryMutation(
        LocalWorkspaceRoot(pathlib.Path(sys.executable).parent),
        WorkspacePolicy(128, 128, 10, 3, ()),
    )
    RepositoryChangeSet((FileChange(
        RepositoryPath('a'), FileChangeKind.CREATE, None, 'x'
    ),))
    LocalGitRepository(
        LocalWorkspaceRoot(pathlib.Path(sys.executable).parent),
        LocalGitExecutable(pathlib.Path(sys.executable)),
        GitReadPolicy(1, 128, 10, 10),
    )
    from legoai_engineering.checks.local import LocalCheckTools, LocalEngineeringChecks
    from legoai_engineering.checks.values import CheckKind, CheckPolicy, CheckRequest
    import legoai_engineering.checks.ports
    suffix = '.exe' if os.name == 'nt' else ''
    base = pathlib.Path(sys.executable).parent
    LocalEngineeringChecks(
        LocalWorkspaceRoot(base),
        LocalCheckTools(*(base / (name + suffix) for name in ('pytest', 'ruff', 'mypy'))),
        CheckPolicy(),
    )
    CheckRequest(CheckKind.PYTEST, (RepositoryPath('tests'),))
    from legoai_engineering.sandbox.docker import DockerSandbox, DockerSandboxConfig
    from legoai_engineering.sandbox.values import SandboxPolicy, SandboxRequest
    import legoai_engineering.sandbox.ports
    DockerSandbox(DockerSandboxConfig(base / 'docker.exe'), SandboxPolicy())
    SandboxRequest('print(1)')
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


def test_git_process_and_public_surface_are_closed() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "legoai_engineering" / "git"
    tree = ast.parse((root / "_process.py").read_text(encoding="utf-8"))
    commands = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "args"
            and node.func.attr == "extend"
        ):
            argument = node.args[0]
            assert isinstance(argument, ast.List)
            assert all(isinstance(item, ast.Constant) for item in argument.elts)
            first = argument.elts[0]
            assert isinstance(first, ast.Constant)
            assert isinstance(first.value, str)
            commands.append(first.value)
    assert sorted(commands) == ["ls-files", "status"]
    for file in ("ports.py", "local.py"):
        tree = ast.parse((root / file).read_text(encoding="utf-8"))
        public = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        }
        assert public == {"inspect"}
    assert import_violations("subprocess.Popen(args, shell=True)", "git._process")
    assert import_violations("subprocess.Popen(args)", "git._process")
    assert import_violations("subprocess.run(args, shell=False)", "git._process")
    assert import_violations("import legoai_engineering.git.local", "git.values")


def test_mutation_boundaries_and_public_surface() -> None:
    root = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "legoai_engineering"
        / "repository"
    )
    for name in ("mutation", "mutation_ports", "mutation_errors", "mutation_local"):
        assert import_violations("import subprocess", name)
        assert import_violations("import legoai_engineering.git.local", name)
        assert import_violations("import legoai.reference.execution", name)
        assert import_violations("import openai", name)
        assert import_violations("import forgeai", name)
    for name in ("mutation", "mutation_ports", "mutation_errors"):
        assert import_violations("import legoai_engineering.repository.local", name)
        assert import_violations("os.replace(a, b)", name)
    for name in ("mutation_ports", "mutation_local"):
        tree = ast.parse((root / (name + ".py")).read_text(encoding="utf-8"))
        public = [
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.FunctionDef) and not item.name.startswith("_")
        ]
        assert [item.name for item in public] == ["apply"]
        method = public[0]
        assert [arg.arg for arg in method.args.args] == ["self", "changeset"]
        annotation = method.args.args[1].annotation
        assert annotation is not None
        assert ast.unparse(annotation) == "RepositoryChangeSet"


def test_check_surface_is_semantic_and_process_use_is_private() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "legoai_engineering"
    for name in ("ports", "local"):
        tree = ast.parse((root / "checks" / (name + ".py")).read_text("utf-8"))
        public = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        ]
        assert [node.name for node in public] == ["check"]
        assert [arg.arg for arg in public[0].args.args] == ["self", "request"]
        annotation = public[0].args.args[1].annotation
        assert annotation is not None
        assert ast.unparse(annotation) == "CheckRequest"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text("utf-8"))
        for node in ast.walk(tree):
            if path.parent.name != "checks" and isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("legoai_engineering.checks")
            if isinstance(node, ast.arg):
                assert node.arg not in {"extra_args", "command_string"}
    for name in ("checks.local", "checks.values", "checks.ports"):
        assert import_violations("import subprocess", name)
        assert import_violations("import legoai.reference.execution", name)
        assert import_violations("import openai", name)
    assert import_violations("subprocess.Popen(args, shell=True)", "checks._process")
    assert import_violations("subprocess.Popen(args)", "checks._process")
    assert import_violations("os.system('bad')", "checks._process")
