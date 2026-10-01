"""LQ1 boundaries: evaluation is outside the runtime and uses public APIs only."""

import ast
import tomllib
from pathlib import Path

import pytest

EVALUATION = Path(__file__).resolve().parents[1]
FORGEAI = EVALUATION.parent
HARNESS = sorted((EVALUATION / "forgeai_eval").glob("*.py")) + [EVALUATION / "run.py"]


def imports(path: Path) -> list[tuple[str, list[str]]]:
    found: list[tuple[str, list[str]]] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.extend((alias.name, []) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.module, [alias.name for alias in node.names]))
    return found


def test_evaluation_is_not_packaged_in_the_runtime_wheel() -> None:
    with (FORGEAI / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)
    assert project["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "src/forgeai"
    ]
    sdist = project["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
    assert not any("evaluation" in item for item in sdist)


def test_runtime_never_imports_the_harness() -> None:
    for path in (FORGEAI / "src" / "forgeai").glob("*.py"):
        for module, _ in imports(path):
            assert not module.startswith("forgeai_eval"), path.name


@pytest.mark.parametrize("path", HARNESS, ids=lambda p: p.name)
def test_harness_uses_public_apis_only(path: Path) -> None:
    for module, names in imports(path):
        if module.startswith(("legoai", "forgeai.")) or module == "forgeai":
            assert not any(p.startswith("_") for p in module.split(".")), module
            assert not any(n.startswith("_") for n in names), (module, names)
            assert not module.startswith(
                ("legoai.reference", "legoai.runtime._composition")
            )
        assert module.split(".")[0] not in {"openai", "ollama", "httpx", "requests"}


def test_hidden_tests_never_execute_on_the_host() -> None:
    for path in HARNESS:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        uses_subprocess = any(module == "subprocess" for module, _ in imports(path))
        if uses_subprocess:
            # Only fixture provisioning and commit identity run Git.
            assert path.name in {"fixtures.py", "run.py"}, path.name
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert node.value not in {"pytest", "python -m pytest"}, path.name
    hidden = (EVALUATION / "forgeai_eval" / "hidden.py").read_text(encoding="utf-8")
    assert "SandboxedEngineeringChecks" in hidden
    assert "LocalEngineeringChecks" not in hidden


def test_harness_names_only_read_only_ollama_endpoints() -> None:
    # The live chat path belongs to ForgeAI's binding; the harness itself only
    # observes the server (LQ1.1 preflight), and never pulls or mutates it.
    for path in HARNESS:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value.startswith("/api/"):
                    assert node.value in {"/api/version", "/api/tags"}, path.name


def test_no_target_discovery_workflow_team_or_new_agent() -> None:
    for path in HARNESS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                lowered = node.name.lower()
                assert not any(
                    word in lowered
                    for word in ("workflow", "team", "benchmarkregistry", "leaderboard")
                ), node.name
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "AgentDefinition", path.name
        for module, _ in imports(path):
            assert "agent.ports" not in module and "analyst.api" not in module
    # Listings are used only by the oracle overlay, never disclosed to a model.
    for path in HARNESS:
        if "list_entries" in path.read_text(encoding="utf-8"):
            assert path.name == "hidden.py", path.name
