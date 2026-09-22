"""Dependency-direction and isolation checks for the Document Capability
Pack. Mirrors the spirit of legoai-reference's own
tests/architecture/test_import_boundaries.py conventions, scoped to this
package's own concerns:

- legoai_document declares exactly the intended runtime dependency set
  (batch 1: none; batch 2 adds `pypdf` for document.parsing; v0.1 adds
  `legoai-reference` -- Core -- since document.embedding/retrieval/
  answering genuinely need governed Model invocation, per
  `planning/V0.1-DOCUMIND-IMPLEMENTATION-PLAN.md`) -- an explicit
  allowlist, so any future accidental dependency fails loudly rather than
  silently passing a weakened "just don't be empty" check.
- legoai_document does not import Semantic Kernel, Microsoft Agent
  Framework, any model-provider/OCR/vision SDK, database driver, or
  workflow engine -- v0.1's own Ollama/HTTP/persistence needs are entirely
  Core's responsibility (`legoai.reference.model`, composed by the
  DocuMind application, never imported by this pack).
- reportlab/pillow (used only to generate test fixtures during design
  verification) must never appear in production source.
- legoai_document may depend on Core's **stable public contracts only**
  (`legoai.kernel.*`, and each owner's `values`/`ports` submodules) --
  never `legoai.reference.*` (ADR-002's own package table: "Internal
  implementations") or `legoai.runtime._composition.*` (the private
  composition root). Governed invocation is composed by the caller (the
  DocuMind application) and handed to this pack's capabilities as an
  already-governed callable/result -- this pack never constructs an
  `ExecutionCoordinator`, `DispatchArbiter`, or Catalog itself.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

ALLOWED_RUNTIME_DEPENDENCY_NAMES = {"pypdf", "legoai-reference"}

ALLOWED_LEGOAI_SUBMODULES = {
    "legoai.kernel",
    "legoai.intelligence.model.values",
    "legoai.intelligence.model.ports",
    "legoai.execution.values",
    "legoai.execution.ports",
    "legoai.capabilities.values",
    "legoai.capabilities.ports",
    "legoai.governance.values",
    "legoai.governance.ports",
}

FORBIDDEN_LEGOAI_SUBMODULES = {
    "legoai.reference",
    "legoai.runtime",
}

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

ALLOWED_ROOTS = {"legoai_document", "__future__", "pypdf", "legoai"} | set(
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


def _imported_legoai_modules(source: str) -> set[str]:
    """Every fully-dotted `legoai.*` module actually named by an import
    statement (not just its top-level root) -- e.g. `legoai.reference.
    execution` for `import legoai.reference.execution as x` or
    `from legoai.reference.execution import ExecutionCoordinator`."""
    modules: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(
                alias.name
                for alias in node.names
                if alias.name.split(".")[0] == "legoai"
            )
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.level == 0
            and node.module.split(".")[0] == "legoai"
        ):
            modules.add(node.module)
    return modules


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


def test_legoai_core_dependency_limited_to_stable_public_contracts() -> None:
    # v0.1: legoai_document now depends on Core (document.embedding needs
    # ModelPort's values; document.retrieval/answering need Execution's
    # Coordination-result values) -- but only ever on each owner's
    # `values`/`ports` submodules and Kernel. Never on `legoai.reference.*`
    # (Internal implementations, per ADR-002's own package table) or
    # `legoai.runtime.*` (the private composition root) -- this pack never
    # constructs a Coordinator/Arbiter/Catalog itself; the caller (the
    # DocuMind application) composes those and hands this pack an
    # already-governed callable/result.
    src_root = _package_root() / "src"
    offenders: dict[str, set[str]] = {}
    for path in src_root.rglob("*.py"):
        modules = _imported_legoai_modules(path.read_text(encoding="utf-8"))
        forbidden = {
            module
            for module in modules
            if any(
                module == forbidden_root or module.startswith(f"{forbidden_root}.")
                for forbidden_root in FORBIDDEN_LEGOAI_SUBMODULES
            )
            or not any(
                module == allowed or module.startswith(f"{allowed}.")
                for allowed in ALLOWED_LEGOAI_SUBMODULES
            )
        }
        if forbidden:
            offenders[str(path.relative_to(src_root))] = forbidden
    assert offenders == {}
