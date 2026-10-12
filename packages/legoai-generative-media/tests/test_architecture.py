import ast
from pathlib import Path

import pytest


def test_no_core_import_of_optional_package() -> None:
    repo = Path(__file__).resolve().parents[3]
    for path in (repo / "src" / "legoai").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert "generative_media" not in (node.module or "")
            if isinstance(node, ast.Import):
                assert all("generative_media" not in alias.name for alias in node.names)


def test_no_runtime_launch_or_dynamic_imports() -> None:
    root = Path(__file__).resolve().parents[1] / "src"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(
                    a.name not in ("subprocess", "importlib", "requests")
                    for a in node.names
                )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ("eval", "exec", "__import__")


def test_image_byte_paths_never_log_or_print() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "legoai_generative_media"
    for name in (
        "png.py",
        "values.py",
        "transfer.py",
        "drivers/legacy.py",
        "tryon.py",
        "virtual_try_on.py",
    ):
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(a.name != "logging" for a in node.names), name
            if isinstance(node, ast.ImportFrom):
                assert node.module != "logging", name
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "print", name


def test_application_contracts_carry_no_provider_types() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "legoai_generative_media"
    for name in ("ports.py", "values.py"):
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not any(
                    part in module
                    for part in (
                        "drivers",
                        "comfyui",
                        "transfer",
                        "http",
                        "service",
                        "tryon",
                        "virtual_try_on",
                        "workflow",
                    )
                ), (name, module)


def credential_environment_access(source: str) -> bool:
    """Supplement behavior tests: catch both direct and imported env access."""
    tree = ast.parse(source)
    aliases = {"os"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            aliases.update(a.asname or a.name for a in node.names if a.name == "os")
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            if any(
                a.name in {"environ", "getenv", "environb", "getenvb"} for a in node.names
            ):
                return True
    return any(
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in aliases
        and node.attr in {"environ", "getenv", "environb", "getenvb"}
        for node in ast.walk(tree)
    )


@pytest.mark.parametrize(
    "source, forbidden",
    [
        ('import os; value = os.environ.get("TOKEN")', True),
        ('import os as system; value = system.getenv("TOKEN")', True),
        ("from os import environ as environment", True),
        ('ref = "env:NAME"', False),
        ('import os; path = os.path.join("a", "b")', False),
    ],
)
def test_environment_rule_controls(source: str, forbidden: bool) -> None:
    assert credential_environment_access(source) is forbidden


def test_media_credential_entry_points_do_not_read_environment() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "legoai_generative_media"
    # Deliberately scoped to credential entry points, not unrelated environment use.
    for name in ("config.py", "service.py", "http.py"):
        assert not credential_environment_access(
            (root / name).read_text(encoding="utf-8")
        )
