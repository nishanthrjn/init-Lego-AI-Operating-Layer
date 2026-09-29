"""N. Dependency direction and public-API-only boundaries for ForgeAI."""

import ast
import tomllib
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = PACKAGE / "src" / "forgeai"
REPOSITORY = PACKAGE.parents[1]

# Domain and application layers: values, Ports and the Coding Agent only.
INNER = {"domain", "worker", "guard"}
FORBIDDEN_INNER = (
    "legoai.runtime.local",
    "legoai.intelligence.model.ports",
    "legoai_engineering.repository.local",
    "legoai_engineering.repository.mutation_local",
    "legoai_engineering.checks.local",
    "legoai_engineering.checks.sandboxed",
    "legoai_engineering.git.local",
    "legoai_engineering.sandbox.docker",
    "forgeai.composition",
    "forgeai.cli",
)
FORBIDDEN_EVERYWHERE = (
    "subprocess",
    "socket",
    "shutil.rmtree",
    "legoai.reference",
    "legoai.runtime._composition",
    "legoai_engineering.checks.local",  # model-written code never runs on host
    "httpx",
    "requests",
    "ollama",
    "openai",
    "docker",
)
STDLIB_INNER = {"dataclasses", "enum", "threading"}
WRITES = {
    "write_text",
    "write_bytes",
    "unlink",
    "rename",
    "replace",
    "mkdir",
    "rmdir",
    "touch",
    "system",
    "popen",
}


def modules() -> dict[str, ast.Module]:
    return {
        path.stem: ast.parse(path.read_text(encoding="utf-8"))
        for path in sorted(SOURCE.glob("*.py"))
    }


def imports(tree: ast.Module, *, strict: bool = True) -> list[tuple[str, list[str]]]:
    found: list[tuple[str, list[str]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, []) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if strict:
                assert node.level == 0 and node.module, "relative imports unsupported"
            if node.level == 0 and node.module:
                found.append((node.module, [alias.name for alias in node.names]))
    return found


def test_package_layout_is_the_expected_small_set() -> None:
    assert set(modules()) == {
        "__init__",
        "domain",
        "guard",
        "worker",
        "composition",
        "cli",
    }


@pytest.mark.parametrize("name", ["domain", "guard", "worker", "composition", "cli"])
def test_public_legoai_only_and_no_private_names(name: str) -> None:
    for module, names in imports(modules()[name]):
        assert not module.startswith(FORBIDDEN_EVERYWHERE), (name, module)
        if module.startswith(("legoai", "forgeai")):
            assert not any(part.startswith("_") for part in module.split(".")), module
            assert not any(item.startswith("_") for item in names), (module, names)
        if name in INNER:
            assert not module.startswith(FORBIDDEN_INNER), (name, module)
            if not module.startswith(("legoai", "forgeai")):
                assert module in STDLIB_INNER, (name, module)
                assert module != "threading" or name == "guard"


@pytest.mark.parametrize("name", ["domain", "guard", "worker", "composition", "cli"])
def test_no_effects_grants_or_global_state(name: str) -> None:
    tree = modules()[name]
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in WRITES, (name, node.attr)
        if isinstance(node, ast.Name):
            assert node.id not in {"open", "eval", "exec", "__import__"}, name
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"Grant", "SecurityContext", "Approval"}, name
        if isinstance(node, ast.keyword) and node.arg == "shell":
            pytest.fail(f"{name}: shell argument")
    for statement in tree.body:
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            value = statement.value
            assert not isinstance(value, (ast.List, ast.Dict, ast.Set)), name
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                assert value.func.id in {"frozenset"}, (name, value.func.id)
        if isinstance(statement, ast.Global):
            pytest.fail(f"{name}: global statement")


def test_only_the_composition_root_opens_the_host_or_builds_adapters() -> None:
    owners = {
        name
        for name, tree in modules().items()
        for module, _ in imports(tree)
        if module
        in {
            "legoai.runtime.local",
            "legoai_engineering.sandbox.docker",
            "legoai_engineering.checks.sandboxed",
            "legoai_engineering.repository.mutation_local",
            "legoai_engineering.git.local",
        }
    }
    assert owners == {"composition"}


def test_worker_depends_on_ports_and_the_coding_agent() -> None:
    names = {module for module, _ in imports(modules()["worker"])}
    assert {
        "legoai_engineering.git.ports",
        "legoai_engineering.checks.ports",
        "legoai_engineering.repository.mutation_ports",
        "legoai_engineering.coding.api",
    } <= names


def test_legoai_never_imports_forgeai() -> None:
    roots = [REPOSITORY / "src" / "legoai"] + sorted(
        (REPOSITORY / "packages").glob("*/src")
    )
    assert roots[0].is_dir(), "run from the repository checkout"
    for root in roots:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for module, _ in imports(tree, strict=False):
                assert module.split(".")[0] != "forgeai", path


def test_dependencies_on_legoai_are_explicit() -> None:
    with (PACKAGE / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    assert project["dependencies"] == [
        "legoai-reference==0.1.0.dev0",
        "legoai-engineering[analyst]==0.1.0.dev0",
    ]
