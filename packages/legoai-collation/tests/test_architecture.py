"""Pack-local boundaries; runnable from an extracted source distribution.

Checks that need the LegoAI repository root (such as Core never importing
this pack) live in the repository's own architecture tests.
"""

import ast
import re
from pathlib import Path

import legoai_collation

PACK = Path(__file__).resolve().parents[1]
SOURCE = PACK / "src" / "legoai_collation"
ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "decimal",
    "enum",
    "re",
    "typing",
    "legoai_collation",
}
ALLOWED_TOP_LEVEL = (
    ast.Expr,
    ast.Import,
    ast.ImportFrom,
    ast.FunctionDef,
    ast.ClassDef,
    ast.Assign,
    ast.AnnAssign,
    ast.TypeAlias,
)
FORBIDDEN_CALLS = {"open", "print", "input", "exec", "eval", "compile", "__import__"}


def modules() -> list[Path]:
    found = sorted(SOURCE.rglob("*.py"))
    assert found, "package source tree is missing"
    return found


def test_only_pure_standard_library_imports() -> None:
    for path in modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0, f"{path.name}: use absolute imports"
                roots = {(node.module or "").split(".")[0]}
            else:
                continue
            assert roots <= ALLOWED_IMPORTS, f"{path.name}: {sorted(roots)}"


def test_modules_are_inert_and_perform_no_io() -> None:
    for path in modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for statement in tree.body:
            assert isinstance(statement, ALLOWED_TOP_LEVEL), (
                f"{path.name}: {type(statement)}"
            )
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in FORBIDDEN_CALLS, (
                    f"{path.name}: {node.func.id}"
                )
            if isinstance(node, ast.Global | ast.Nonlocal):
                raise AssertionError(f"{path.name}: mutable module state")


def test_public_surface_is_explicit() -> None:
    exported = set(legoai_collation.__all__)
    assert all(hasattr(legoai_collation, name) for name in exported)
    assert not any(name.startswith("_") for name in exported)
    assert {"collate_field", "Reading", "Collation", "normalize"} <= exported


def test_pack_files_contain_no_machine_specific_paths() -> None:
    # Split literals so this file does not match its own pattern.
    homes = "|".join(re.escape("/" + name + "/") for name in ("home", "Users"))
    absolute = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/][A-Za-z]|" + homes)
    files = [
        *PACK.glob("src/**/*.py"),
        *PACK.glob("tests/*.py"),
        *PACK.glob("examples/*.py"),
        PACK / "README.md",
        PACK / "pyproject.toml",
    ]
    for path in files:
        if path.is_file():
            assert not absolute.search(path.read_text(encoding="utf-8")), path.name
