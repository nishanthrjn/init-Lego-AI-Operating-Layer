"""ADR-024 REMOTE-DISCLOSURE-GOVERNANCE-1 ownership and boundaries.

Governance owns the disclosure values and pure evaluator; runtime consumes
them for host configuration only. No invocation gate, carrier, adapter policy
or consumer (Engineering/ForgeAI) dependency exists in this slice.
"""

import ast
import dataclasses
from pathlib import Path

from legoai.execution.agent.ports import AgentRequest
from legoai.intelligence.model.values import ChatRequest, EmbeddingRequest
from tests.architecture.test_import_boundaries import violations

ROOT = Path(__file__).resolve().parents[2]
MODULE = "legoai.governance.disclosure"


def _imports(path: Path) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.add(node.module)
    return targets


def _importers(root: Path) -> set[str]:
    return {
        path.relative_to(ROOT).as_posix()
        for path in sorted(root.rglob("*.py"))
        if "__pycache__" not in path.parts
        and any(t == MODULE or t.startswith(MODULE + ".") for t in _imports(path))
    }


def test_governance_disclosure_depends_only_on_kernel_and_stdlib() -> None:
    imported = _imports(ROOT / "src/legoai/governance/disclosure.py")
    assert {t for t in imported if t.startswith("legoai")} == {
        "legoai.kernel.effects",
        "legoai.kernel.identity",
        "legoai.kernel.references",
    }
    for source in (
        "from legoai.runtime.api import ModelPurpose",
        "from legoai.runtime.local import open_local_host",
        "from legoai.intelligence.model.values import ProviderId",
        "from legoai.reference.model import OllamaModelAdapter",
    ):
        assert violations({MODULE: source}), source


def test_runtime_api_may_consume_disclosure_values() -> None:
    source = "from legoai.governance.disclosure import DisclosureAdmission"
    assert "runtime-api" not in violations({"legoai.runtime.api": source})


def test_only_trusted_runtime_and_evidence_paths_import_disclosure() -> None:
    # REMOTE-DISCLOSURE-GATE-1: host configuration and carrier (api, local),
    # the private gate and the governed Model path that calls it, and the
    # Evidence owner's typed subject. Never the Agent runtime, a provider
    # adapter or any reference realization.
    assert _importers(ROOT / "src") == {
        "src/legoai/evidence/ports.py",
        # T2 reuses `endpoint_parts` normalization only; no policy evaluation.
        "src/legoai/reference/_credential_https.py",
        "src/legoai/runtime/_composition/disclosure.py",
        "src/legoai/runtime/_composition/model_governed.py",
        "src/legoai/runtime/_composition/remote_attempt.py",
        "src/legoai/runtime/api.py",
        "src/legoai/runtime/local.py",
    }


def test_engineering_and_forgeai_do_not_depend_on_disclosure() -> None:
    for consumer in (
        ROOT / "packages/legoai-engineering/src",
        ROOT / "examples/forgeai/src",
    ):
        assert _importers(consumer) == set(), consumer


def test_gate_records_but_never_reads_evidence_or_rewrites_content() -> None:
    gate = (ROOT / "src/legoai/runtime/_composition/disclosure.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(gate)
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    # Evidence is written through the ADR-009 custody Port and never read
    # back as admission state.
    assert "record" in calls and "read" not in calls
    for path in (
        ROOT / "src/legoai/governance/disclosure.py",
        ROOT / "src/legoai/runtime/_composition/disclosure.py",
        ROOT / "src/legoai/runtime/_composition/model_governed.py",
    ):
        names = _identifiers(path)
        for word in ("redact", "declassif", "downgrade", "sanitiz", "rewrite"):
            assert not any(word in name for name in names), (path, word)


def _identifiers(path: Path) -> set[str]:
    """Every defined or referenced name (code, not prose), lowercased."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name.lower())
        elif isinstance(node, ast.Name):
            names.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            names.add(node.attr.lower())
    return names


def test_only_the_host_binds_declarations_to_executions() -> None:
    importers = {
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / "src").rglob("*.py"))
        if any(t == "legoai.runtime._composition.disclosure" for t in _imports(path))
    }
    assert importers == {
        "src/legoai/runtime/_composition/agent.py",
        "src/legoai/runtime/_composition/model_governed.py",
        # Builds an attempt from an admitted check; binds no declaration.
        "src/legoai/runtime/_composition/remote_attempt.py",
        "src/legoai/runtime/local.py",
    }
    # Provider adapters never see or evaluate disclosure policy.
    for adapter in (
        "src/legoai/reference/model.py",
        "src/legoai/reference/model_openai_compatible.py",
        "src/legoai/reference/model_fake.py",
    ):
        path = ROOT / adapter
        assert not any("disclos" in t for t in _imports(path)), adapter
        assert not any("disclos" in n for n in _identifiers(path)), adapter


def test_model_visible_requests_and_ports_are_unchanged() -> None:
    def names(value: type) -> set[str]:
        return {f.name for f in dataclasses.fields(value)}

    assert names(ChatRequest) == {"messages", "response_format"}
    assert names(EmbeddingRequest) == {"inputs"}
    assert names(AgentRequest) == {"context", "text"}
    ports = (ROOT / "src/legoai/intelligence/model/ports.py").read_text(
        encoding="utf-8"
    )
    assert "disclos" not in ports.lower()
