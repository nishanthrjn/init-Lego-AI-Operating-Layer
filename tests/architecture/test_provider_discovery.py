"""PROVIDER-MODEL-DISCOVERY-1 boundaries (ADR-024 §22).

Discovery is a private operator/provider-setup seam: outside ModelPort and
every request type, no disclosure policy or evidence, no production importer,
no provider-specific identifiers, one fixed path, no retry or routing.
"""

import ast
import dataclasses
from pathlib import Path

from legoai.governance.disclosure import DisclosureAdmission
from legoai.governance.provider_control import ProviderDiscoveryAdmission

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src/legoai"
SEAM = SRC / "runtime/_composition/provider_discovery.py"
VALUES = SRC / "governance/provider_control.py"


def _imports(path: Path) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.add(node.module)
    return targets


def _names(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name.lower())
        elif isinstance(node, ast.Name):
            names.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            names.add(node.attr.lower())
    return names


def test_model_port_and_requests_have_no_discovery() -> None:
    ports = (SRC / "intelligence/model/ports.py").read_text(encoding="utf-8")
    assert "list_models" not in ports and "discover" not in ports.lower()


def test_seam_has_no_production_importer() -> None:
    for path in SRC.rglob("*.py"):
        if path == SEAM:
            continue
        imports = _imports(path)
        assert "legoai.runtime._composition.provider_discovery" not in imports, path


def test_seam_owns_no_disclosure_policy_or_evidence() -> None:
    imports = _imports(SEAM)
    assert "legoai.governance.disclosure" not in imports
    assert "legoai.runtime._composition.disclosure" not in imports
    assert not any(t.startswith("legoai.evidence") for t in imports)
    names = _names(SEAM)
    for word in (
        "disclosureobservation",
        "evaluate_disclosure",
        "retry",
        "fallback",
        "route",
        "environ",
        "getenv",
        "loads",
    ):
        assert not any(word in name for name in names), word
    assert not {t.split(".")[0] for t in imports} & {
        "os",
        "socket",
        "asyncio",
        "threading",
        "urllib",
        "http",
        "json",
        "logging",
    }


def test_authorities_are_structurally_distinct() -> None:
    assert not issubclass(ProviderDiscoveryAdmission, DisclosureAdmission)
    assert not issubclass(DisclosureAdmission, ProviderDiscoveryAdmission)
    fields = {f.name for f in dataclasses.fields(ProviderDiscoveryAdmission)}
    assert not fields & {"classes", "models", "bindings", "repositories", "purposes"}
    # The values module imports only kernel identity, Secret references and
    # the shared endpoint normalization; it evaluates no disclosure policy.
    imports = {t for t in _imports(VALUES) if t.startswith("legoai")}
    assert imports == {
        "legoai.governance.disclosure",
        "legoai.governance.secret",
        "legoai.kernel.identity",
    }
    assert "evaluate_disclosure" not in _names(VALUES)


def test_no_provider_specific_identifiers_in_core() -> None:
    for path in SRC.rglob("*.py"):
        lowered = path.read_text(encoding="utf-8").lower()
        for word in ("kisski", "gwdg", "academiccloud"):
            assert word not in lowered, (path, word)


def test_path_is_fixed_not_caller_supplied() -> None:
    tree = ast.parse(SEAM.read_text(encoding="utf-8"))
    function = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "discover_remote_models"
    )
    parameters = {a.arg for a in function.args.args + function.args.kwonlyargs}
    assert not parameters & {"path", "url", "method", "body", "headers"}
