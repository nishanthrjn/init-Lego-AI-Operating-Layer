"""Agent operation records and explicit governed invocation boundary."""

from dataclasses import dataclass, field
from typing import Protocol

from legoai.execution.agent.values import (
    AgentExecutionStatus,
    AgentId,
    AgentOutputContract,
    _bound,
    _text,
)
from legoai.execution.values import (
    ExecutionContext,
    ExecutionId,
    ExecutionResult,
    ExecutionState,
)
from legoai.intelligence.model.routing import ModelRequirement, ModelRouteDecision
from legoai.intelligence.model.values import ChatRequest, ChatResult
from legoai.kernel.versions import Version


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    """Versioned single-step behavior. Instructions confer no permissions."""

    agent_id: AgentId
    behavior_version: Version
    instructions: str = field(repr=False)
    model_requirement: ModelRequirement
    output_contract: AgentOutputContract
    max_input_bytes: int
    max_prompt_bytes: int

    def __post_init__(self) -> None:
        if (
            type(self.agent_id) is not AgentId
            or type(self.behavior_version) is not Version
        ):
            raise TypeError("Agent definition requires identity and behavior version")
        if type(self.model_requirement) is not ModelRequirement:
            raise TypeError("Agent definition requires ModelRequirement")
        if type(self.output_contract) is not AgentOutputContract:
            raise TypeError("Agent definition requires AgentOutputContract")
        _text(self.instructions, 16384)
        _bound(self.max_input_bytes, 65536)
        _bound(self.max_prompt_bytes, 131072)
        # Include the exact deterministic contract instruction in the budget.
        prompt_size = len(self.system_prompt.encode("utf-8")) + self.max_input_bytes
        if prompt_size > self.max_prompt_bytes:
            raise ValueError("prompt budget cannot accommodate configured input")

    @property
    def system_prompt(self) -> str:
        return (
            self.instructions
            + "\nReturn nonblank UTF-8 text of at most "
            + str(self.output_contract.max_bytes)
            + " bytes."
        )


@dataclass(frozen=True, slots=True)
class AgentRequest:
    context: ExecutionContext
    text: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.context) is not ExecutionContext:
            raise TypeError("Agent request requires ExecutionContext")
        _text(self.text, 65536)


@dataclass(frozen=True, slots=True)
class AgentChatResult:
    """Internal Port response; model content is still untrusted Agent input."""

    execution: ExecutionResult
    response: ChatResult | None = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.execution) is not ExecutionResult:
            raise TypeError("governed Chat requires ExecutionResult")
        if self.response is not None and type(self.response) is not ChatResult:
            raise TypeError("governed Chat response must be ChatResult or None")
        success = self.execution.final_state is ExecutionState.SUCCEEDED
        if success != (self.response is not None):
            raise ValueError("governed Chat output must correspond to success")


@dataclass(frozen=True, slots=True)
class AgentResult:
    definition: AgentDefinition
    execution_id: ExecutionId
    route: ModelRouteDecision
    status: AgentExecutionStatus
    model_execution: ExecutionResult | None
    output: str | None = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.definition) is not AgentDefinition
            or type(self.execution_id) is not ExecutionId
        ):
            raise TypeError("Agent result requires definition and ExecutionId")
        if (
            type(self.route) is not ModelRouteDecision
            or type(self.status) is not AgentExecutionStatus
        ):
            raise TypeError("Agent result requires route and status")
        if self.route.requirement != self.definition.model_requirement:
            raise ValueError("Agent result route requirement mismatch")
        if self.status is AgentExecutionStatus.ROUTING_FAILED:
            if (
                self.route.selected is not None
                or self.model_execution is not None
                or self.output is not None
            ):
                raise ValueError("routing failure cannot contain invocation or output")
            return
        if (
            self.route.selected is None
            or type(self.model_execution) is not ExecutionResult
        ):
            raise ValueError(
                "Agent invocation outcome requires selected route and execution"
            )
        if self.model_execution.execution_id != self.execution_id:
            raise ValueError("Agent result execution identity mismatch")
        success = self.model_execution.final_state is ExecutionState.SUCCEEDED
        if self.status is AgentExecutionStatus.MODEL_FAILED:
            if success or self.output is not None:
                raise ValueError("model failure cannot carry successful output")
        elif not success:
            raise ValueError(
                "Agent output validation requires successful model execution"
            )
        elif self.status is AgentExecutionStatus.OUTPUT_INVALID:
            if self.output is not None:
                raise ValueError("invalid output must not be returned")
        else:
            if self.output is None:
                raise ValueError("successful Agent result requires output")
            self.definition.output_contract.validate(self.output)


class AgentChatPort(Protocol):
    """Trusted governed boundary, not an arbitrary ModelPort callback.

    Must match the pinned route, authorize and coordinate this exact context,
    claim invocation once, preserve effects, and never retry or fall back.
    Unexpected errors/cancellation propagate without invented settlement.
    """

    async def invoke(
        self, context: ExecutionContext, route: ModelRouteDecision, request: ChatRequest
    ) -> AgentChatResult: ...


class AgentRuntimePort(Protocol):
    async def run(
        self, definition: AgentDefinition, request: AgentRequest
    ) -> AgentResult: ...
