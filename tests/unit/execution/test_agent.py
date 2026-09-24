"""M7 bounded definition/request/result contracts."""

from dataclasses import FrozenInstanceError, replace

import pytest

from legoai.execution.agent.ports import AgentDefinition, AgentRequest
from legoai.execution.agent.values import AgentId, AgentOutputContract
from legoai.intelligence.model.routing import ModelRequirement
from legoai.kernel.versions import Version
from tests.integration.composition.test_model_governed import _Environment


def definition() -> AgentDefinition:
    return AgentDefinition(
        AgentId("analysis"),
        Version(1, 0, 0),
        "Analyze the supplied text.",
        ModelRequirement("engineering-reasoning"),
        AgentOutputContract(32),
        128,
        512,
    )


@pytest.mark.parametrize(
    "text",
    ["", " ", "x" * 16385, "\ud800"],
    ids=["empty", "blank", "oversized", "invalid-utf8"],
)
def test_definition_rejects_invalid_instructions(text: str) -> None:
    with pytest.raises(ValueError):
        replace(definition(), instructions=text)


@pytest.mark.parametrize("limit", [0, -1, 65537])
def test_output_limit_range(limit: int) -> None:
    with pytest.raises(ValueError):
        AgentOutputContract(limit)


def test_exact_types_and_context_budget() -> None:
    with pytest.raises(TypeError):
        AgentOutputContract(True)
    with pytest.raises(TypeError):
        replace(definition(), model_requirement="provider")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        replace(definition(), max_prompt_bytes=128)
    with pytest.raises(TypeError):
        AgentRequest(None, "text")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        AgentRequest(_Environment().execution_context(), 7)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "text",
    ["", "\n", "x" * 65537, "\ud800"],
    ids=["empty", "blank", "oversized", "invalid-utf8"],
)
def test_request_rejects_invalid_text(text: str) -> None:
    with pytest.raises(ValueError):
        AgentRequest(_Environment().execution_context(), text)


def test_utf8_bytes_and_immutability() -> None:
    contract = AgentOutputContract(4)
    contract.validate("😀")
    with pytest.raises(ValueError):
        contract.validate("😀x")
    with pytest.raises(TypeError):
        contract.validate(b"text")  # type: ignore[arg-type]
    configured = definition()
    assert not hasattr(configured, "__dict__")
    with pytest.raises(FrozenInstanceError):
        configured.instructions = "changed"  # type: ignore[misc]
