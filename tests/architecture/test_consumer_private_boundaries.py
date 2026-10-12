"""Cross-distribution private-import ratchet; debt is not conformance permission.

Complements the Core dependency matrix and consumer-specific AST tests. Static
imports and imported-module attribute access are covered, not dynamic Python.
See LEGOAI-ARCHITECTURE-DESIGN-CONFORMANCE-AUDIT-1 for debt ownership.
"""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MEDIA = "packages/legoai-generative-media/src/legoai_generative_media/"
ASSESSMENT = "examples/assessment_starter/backend/src/assessment_starter/"

# Exact module edges, never a whole-file or whole-package exemption. Removal
# also fails until the corresponding debt entry is retired deliberately.
DEBT = {
    ASSESSMENT + "model_factory.py": {"legoai.reference.model"},
    ASSESSMENT + "model.py": {"legoai.reference.model_fake"},
    ASSESSMENT + "fixtures.py": {"legoai.reference.model_fake"},
    # Historical, explicitly technical/offline examples, not public host recipes.
    "examples/model_port.py": {"legoai.reference.model_fake"},
    "examples/model_routing.py": {"legoai.reference.model_routing"},
    "examples/agent.py": {
        "legoai.reference.agent",
        "legoai.reference.catalog",
        "legoai.reference.evidence",
        "legoai.reference.execution",
        "legoai.reference.governance",
        "legoai.reference.model",
        "legoai.reference.model_routing",
        "legoai.reference.plugins",
        "legoai.runtime._composition.agent",
        "legoai.runtime._composition.model_governed",
    },
}


def references(source: str, module: str) -> set[str]:
    """Resolve import aliases/relative imports without importing audited code."""
    tree = ast.parse(source)
    found: set[str] = set()
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                found.add(item.name)
                aliases[item.asname or item.name.split(".")[0]] = (
                    item.name if item.asname else item.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                package = module.split(".")[: -node.level]
                base = ".".join(package + ([base] if base else []))
            found.add(base)
            for item in node.names:
                target = f"{base}.{item.name}"
                found.add(target)
                aliases[item.asname or item.name] = target
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            parts = [node.attr]
            current: ast.expr = node.value
            while isinstance(current, ast.Attribute):
                parts.insert(0, current.attr)
                current = current.value
            if isinstance(current, ast.Name) and current.id in aliases:
                found.add(".".join([aliases[current.id], *parts]))
    return found


def private_edges(source: str, module: str) -> set[str]:
    owner = module.split(".")[0]
    edges: set[str] = set()
    for target in references(source, module):
        parts = target.split(".")
        if not parts[0].startswith("legoai") or parts[0] == owner:
            continue
        if parts[:2] == ["legoai", "reference"]:
            edges.add(".".join(parts[:3]))
        elif parts[:3] == ["legoai", "runtime", "_composition"]:
            edges.add(".".join(parts[:4]))
        else:
            for index, part in enumerate(parts[1:], 1):
                if part.startswith("_"):
                    edges.add(".".join(parts[: index + 1]))
                    break
    # A parent import is redundant when a more specific forbidden edge exists.
    return {
        edge
        for edge in edges
        if not any(other.startswith(edge + ".") for other in edges)
    }


def production_sources() -> dict[Path, str]:
    roots = [ROOT / "src", ROOT / ASSESSMENT]
    roots.extend((ROOT / "packages").glob("*/src"))
    roots.extend((ROOT / "examples").glob("*/src"))
    paths = {path for root in roots for path in root.rglob("*.py")}
    paths.update((ROOT / "examples").glob("*.py"))
    return {path: path.read_text(encoding="utf-8") for path in sorted(paths)}


def module_name(path: Path) -> str:
    parts = path.relative_to(ROOT).with_suffix("").parts
    if "src" in parts:
        parts = parts[parts.index("src") + 1 :]
    return ".".join(parts)


def test_cross_distribution_private_edges_do_not_grow() -> None:
    observed = {
        path.relative_to(ROOT).as_posix(): edges
        for path, source in production_sources().items()
        if (edges := private_edges(source, module_name(path)))
    }
    assert observed == DEBT, "Review new edges or retire resolved audit debt"


def test_reusable_python_packages_never_import_consumer_applications() -> None:
    for path, source in production_sources().items():
        module = module_name(path)
        if module.split(".")[0].startswith("legoai"):
            assert consumer_edges(source, module) == set(), path


def test_media_has_no_private_core_edges() -> None:
    for path in (ROOT / MEDIA).rglob("*.py"):
        assert private_edges(path.read_text(encoding="utf-8"), module_name(path)) == set()


@pytest.mark.parametrize(
    "source",
    [
        "from legoai.reference.execution import ExecutionCoordinator",
        "from legoai.runtime._composition import direct",
        "from legoai import reference\nreference.catalog.InMemoryCatalog()",
    ],
)
def test_media_private_import_negative_controls(source: str) -> None:
    assert private_edges(source, "legoai_generative_media.local_host")


def consumer_edges(source: str, module: str) -> set[str]:
    applications = {"forgeai", "documind_app", "assessment_starter"}
    roots = {target.split(".")[0] for target in references(source, module)}
    return roots & applications


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import legoai.reference.catalog as c", "legoai.reference.catalog"),
        ("from legoai.reference import catalog", "legoai.reference.catalog"),
        ("from legoai import reference", "legoai.reference"),
        (
            "from legoai.runtime import _composition as c",
            "legoai.runtime._composition",
        ),
        (
            "import legoai.runtime.local as host\nhost._secret()",
            "legoai.runtime.local._secret",
        ),
        (
            "from legoai_engineering.analyst.sufficiency_agent import _serialize",
            "legoai_engineering.analyst.sufficiency_agent._serialize",
        ),
    ],
)
def test_forbidden_private_controls(source: str, expected: str) -> None:
    assert private_edges(source, "consumer.app") == {expected}


@pytest.mark.parametrize(
    ("module", "source"),
    [
        ("consumer.app", "from legoai.runtime.local import open_local_host"),
        (
            "legoai_generative_media.local_host",
            "from legoai.runtime.local import open_governed_execution",
        ),
        (
            "legoai_generative_media.local_host",
            "from legoai.runtime.api import GovernedExecutionConfig",
        ),
        ("legoai_generative_media.service", "from .local_host import prepare_local"),
        ("consumer.app", "from legoai.intelligence.model.ports import ModelPort"),
        ("legoai.runtime.local", "from legoai.reference.catalog import Catalog"),
        ("legoai_engineering.checks.local", "from ._commands import _arguments"),
    ],
)
def test_allowed_public_and_owner_internal_controls(module: str, source: str) -> None:
    assert private_edges(source, module) == set()


def test_relative_dependency_control() -> None:
    assert "legoai_engineering.checks._commands._arguments" in references(
        "from ._commands import _arguments as arguments",
        "legoai_engineering.checks.local",
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import forgeai.domain as domain\ndomain.TaskRequest()", {"forgeai"}),
        ("from documind_app import app", {"documind_app"}),
        ("from assessment_starter.core import config", {"assessment_starter"}),
        ("from legoai.intelligence.model.ports import ModelPort", set()),
    ],
)
def test_consumer_edge_controls(source: str, expected: set[str]) -> None:
    assert consumer_edges(source, "legoai.fake") == expected
