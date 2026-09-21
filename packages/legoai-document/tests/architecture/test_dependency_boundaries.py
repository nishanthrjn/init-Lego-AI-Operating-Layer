"""Dependency-direction and isolation checks for the Document Capability
Pack. Mirrors the spirit of legoai-reference's own
tests/architecture/test_import_boundaries.py conventions, scoped to this
package's own concerns:

- legoai_document declares exactly the intended runtime dependency set
  (batch 1: none; batch 2 adds `pypdf` for document.parsing -- see
  DOCUMENT-PARSING-CAPABILITY-DESIGN.md SS17/SS18a) -- an explicit
  allowlist, so any future accidental dependency fails loudly rather than
  silently passing a weakened "just don't be empty" check.
- legoai_document does not import Semantic Kernel, Microsoft Agent
  Framework, any model-provider/OCR/vision SDK, database driver, or
  workflow engine -- neither Chunking nor Parsing requires any of them
  (CHUNKING-CAPABILITY-DESIGN.md SS"Package placement";
  DOCUMENT-PARSING-CAPABILITY-DESIGN.md SS14 excludes OCR from v1 entirely).
- reportlab/pillow (used only to generate test fixtures during design
  verification) must never appear in production source.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

ALLOWED_RUNTIME_DEPENDENCY_NAMES = {"pypdf"}

FORBIDDEN_ROOTS = {
    # Agent/orchestration frameworks
    "semantic_kernel",
    "agent_framework",
    "autogen",
    "langgraph",
    "langchain",
    "crewai",
    # Model-provider / OCR / vision SDKs
    "openai",
    "anthropic",
    "google",
    "cohere",
    "ollama",
    "pytesseract",
    "easyocr",
    # Database / vector-store drivers
    "psycopg",
    "psycopg2",
    "asyncpg",
    "sqlalchemy",
    "neo4j",
    "pgvector",
    "pymongo",
    "redis",
    # Workflow engines
    "airflow",
    "prefect",
    "temporalio",
    "dagster",
    # Fixture-generation-only tooling (design-verification, never production)
    "reportlab",
    "PIL",
}

ALLOWED_ROOTS = {"legoai_document", "__future__", "pypdf"} | set(
    sys.stdlib_module_names
)


def _imported_roots(source: str) -> set[str]:
    roots: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def _package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _declared_dependency_names(specifiers: list[str]) -> set[str]:
    # Extract the bare package name from a PEP 508 requirement string
    # (e.g. "pypdf>=6.19.0,<7" -> "pypdf"), without needing a full PEP 508
    # parser for this narrow, internal check.
    names = set()
    for spec in specifiers:
        name = spec
        for sep in ("[", ">=", "<=", "==", "!=", "~=", ">", "<", " "):
            name = name.split(sep, 1)[0]
        names.add(name.strip())
    return names


def test_declared_runtime_dependencies_match_allowlist() -> None:
    pyproject = tomllib.loads(
        (_package_root() / "pyproject.toml").read_text(encoding="utf-8")
    )
    declared = _declared_dependency_names(pyproject["project"]["dependencies"])
    assert declared == ALLOWED_RUNTIME_DEPENDENCY_NAMES


def test_no_forbidden_framework_or_provider_imports() -> None:
    src_root = _package_root() / "src"
    offenders: dict[str, set[str]] = {}
    for path in src_root.rglob("*.py"):
        roots = _imported_roots(path.read_text(encoding="utf-8"))
        forbidden = roots & FORBIDDEN_ROOTS
        if forbidden:
            offenders[str(path.relative_to(src_root))] = forbidden
    assert offenders == {}


def test_only_allowed_import_roots_used() -> None:
    src_root = _package_root() / "src"
    offenders: dict[str, set[str]] = {}
    for path in src_root.rglob("*.py"):
        roots = _imported_roots(path.read_text(encoding="utf-8"))
        disallowed = roots - ALLOWED_ROOTS
        if disallowed:
            offenders[str(path.relative_to(src_root))] = disallowed
    assert offenders == {}


def test_no_dependency_on_legoai_core() -> None:
    # legoai_document MAY depend on legoai's stable public contracts in the
    # future, but batch 1 (Chunking) needs none at all -- confirm that
    # remains true rather than silently acquiring a Core dependency.
    src_root = _package_root() / "src"
    offenders: list[str] = []
    for path in src_root.rglob("*.py"):
        roots = _imported_roots(path.read_text(encoding="utf-8"))
        if "legoai" in roots:
            offenders.append(str(path.relative_to(src_root)))
    assert offenders == []
