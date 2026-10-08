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
    assert {t for t in imported if t.startswith("legoai")} == {"legoai.kernel.identity"}
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


def test_only_host_configuration_and_validation_import_disclosure() -> None:
    # No invocation gate or carrier yet: the governed Model path, the Agent
    # runtime and every provider adapter remain free of disclosure policy.
    assert _importers(ROOT / "src") == {
        "src/legoai/runtime/api.py",
        "src/legoai/runtime/local.py",
    }


def test_engineering_and_forgeai_do_not_depend_on_disclosure() -> None:
    for consumer in (
        ROOT / "packages/legoai-engineering/src",
        ROOT / "examples/forgeai/src",
    ):
        assert _importers(consumer) == set(), consumer


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
