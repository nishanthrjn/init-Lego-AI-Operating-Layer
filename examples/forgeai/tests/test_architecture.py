"""N. Dependency direction and public-API-only boundaries for ForgeAI."""

import ast
import tomllib
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = PACKAGE / "src" / "forgeai"
REPOSITORY = PACKAGE.parents[1]

# Domain and application layers: values, Ports and the Coding Agent only.
INNER = {"domain", "worker", "guard", "review", "repository_context"}
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
STDLIB_INNER = {"collections.abc", "dataclasses", "enum", "threading"}
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
        "repository_context",
        "guard",
        "review",
        "worker",
        "composition",
        "cli",
        "remote",
        "provider",
        "provider_cli",
    }


@pytest.mark.parametrize(
    "name",
    [
        "domain",
        "repository_context",
        "guard",
        "review",
        "worker",
        "composition",
        "cli",
        "remote",
        "provider",
        "provider_cli",
    ],
)
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


@pytest.mark.parametrize(
    "name",
    [
        "domain",
        "repository_context",
        "guard",
        "review",
        "worker",
        "composition",
        "cli",
        "remote",
        "provider",
        "provider_cli",
    ],
)
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


def test_review_material_never_renders_git_or_calls_agents() -> None:
    # Git is operator-only; review.py is pure rendering over supplied values.
    for module, _ in imports(modules()["review"]):
        assert not module.startswith("legoai_engineering.git"), module
        assert not module.endswith(".api"), module


def test_review_stage_cannot_mutate_check_or_rework() -> None:
    tree = modules()["worker"]
    stage = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_review"
    )
    calls = {
        node.func.attr
        for node in ast.walk(stage)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not calls & {"apply", "check", "propose", "inspect"}, calls
    assert "review" in calls and "acquire" in calls


def test_reviewer_is_composed_from_the_agent_runtime_only() -> None:
    constructions = [
        node
        for node in ast.walk(modules()["composition"])
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "IndependentReviewer"
    ]
    assert len(constructions) == 1
    assert [ast.unparse(arg) for arg in constructions[0].args] == ["runtime"]
    assert not constructions[0].keywords


def test_no_workflow_team_or_locator_constructs() -> None:
    for name, tree in modules().items():
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                lowered = node.name.lower()
                assert not any(
                    word in lowered
                    for word in ("workflow", "team", "orchestrat", "locator")
                ), (name, node.name)


def test_remote_is_public_composition_without_platform_branches() -> None:
    forbidden = {
        "kaggle",
        "colab",
        "huggingface",
        "kisski",
        "together",
        "runpod",
        "vast",
        "lambda",
        "modal",
    }
    for name, tree in modules().items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                strings = {
                    part.value.lower()
                    for part in ast.walk(node)
                    if isinstance(part, ast.Constant) and isinstance(part.value, str)
                }
                assert not strings & forbidden, (name, strings)
            if isinstance(node, ast.ClassDef):
                assert node.name not in {
                    "ForgeAIModelPort",
                    "RemoteCodingModel",
                    "CloudModelPort",
                }
    for name in INNER:
        assert not any(
            module.startswith("forgeai.remote")
            for module, _ in imports(modules()[name])
        )


def _calls(node: ast.AST, name: str) -> list[ast.Call]:
    return [
        item
        for item in ast.walk(node)
        if isinstance(item, ast.Call)
        and isinstance(item.func, ast.Attribute)
        and item.func.attr == name
    ]


def _method(tree: ast.Module, name: str) -> ast.AST:
    return next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


def test_rework_is_structurally_bounded_to_one_cycle() -> None:
    # ForgeAI-3: no loop can produce more than 2 proposals or 2 reviews. The
    # attempt method is called once for attempt 1 and once for the rework.
    tree = modules()["worker"]
    assert not any(isinstance(node, ast.While) for node in ast.walk(tree))
    assert len(_calls(tree, "_attempt")) == 2
    assert len(_calls(tree, "_rework")) == 1
    assert len(_calls(_method(tree, "_run"), "_rework")) == 1
    assert len(_calls(tree, "propose")) == 1
    assert len(_calls(tree, "review")) == 1
    for name in ("_attempt", "_review", "_rework"):
        assert not _calls(_method(tree, name), "_run"), name
    assert not _calls(_method(tree, "_attempt"), "_attempt")
    assert not _calls(_method(tree, "_review"), "_attempt")
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and not isinstance(node.iter, ast.Tuple):
            assert ast.unparse(node.iter) in {
                "self.check_plan",
                "evidence.attempts",
                "attempt.applied.applied",
            }, ast.unparse(node.iter)


def test_review_findings_never_drive_effects_directly() -> None:
    worker = (SOURCE / "worker.py").read_text(encoding="utf-8")
    assert "required_action" not in worker
    review = modules()["review"]
    uses = [
        node
        for node in ast.walk(review)
        if isinstance(node, ast.Attribute) and node.attr == "required_action"
    ]
    # Only rendered into labeled constraint text.
    assert len(uses) == 1


def test_no_configurable_attempt_or_retry_count() -> None:
    tree = modules()["composition"]
    config = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "ForgeAIConfig"
    )
    names = [
        target.target.id
        for target in config.body
        if isinstance(target, ast.AnnAssign) and isinstance(target.target, ast.Name)
    ]
    assert not [n for n in names if "retr" in n or "attempt" in n or "cycle" in n]


def test_provider_entry_points_cannot_construct_mutation_or_agents() -> None:
    tree = modules()["composition"]
    for name in ("provider_session", "summarize_provider_file"):
        node = _method(tree, name)
        called = {
            part.func.id
            for part in ast.walk(node)
            if isinstance(part, ast.Call) and isinstance(part.func, ast.Name)
        }
        assert not called & {
            "CodingAgent",
            "LocalRepositoryMutation",
            "AuthorizedRepositoryMutation",
            "DockerSandbox",
            "LocalGitRepository",
            "prepare_run",
            "run_task",
        }
        strings = {
            part.value
            for part in ast.walk(node)
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
        }
        assert "repository-mutation" not in strings
    for name in ("provider", "provider_cli"):
        assert not any(
            module.startswith(("subprocess", "socket", "http", "os"))
            for module, _ in imports(modules()[name])
        )
