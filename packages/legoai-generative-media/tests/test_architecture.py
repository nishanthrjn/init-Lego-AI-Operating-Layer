import ast
from pathlib import Path


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
