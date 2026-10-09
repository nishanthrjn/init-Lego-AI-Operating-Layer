"""Explicit trusted wiring of the Agent-owned Port to qualified governed Chat."""

from dataclasses import dataclass, field

from legoai.execution.agent.ports import AgentChatResult
from legoai.execution.ports import CoordinationOutcome, CoordinationRequest
from legoai.execution.values import ExecutionContext, ExecutionResult
from legoai.intelligence.model.routing import ModelRouteDecision
from legoai.intelligence.model.values import ChatRequest
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorDetail, Recoverability
from legoai.reference.execution import ExecutionCoordinator
from legoai.runtime._composition.disclosure import DisclosureCheck
from legoai.runtime._composition.model_governed import (
    ConfiguredModelBinding,
    invoke_routed_chat,
)


@dataclass(frozen=True, slots=True)
class GovernedAgentChat:
    coordinator: ExecutionCoordinator = field(repr=False)
    configured: ConfiguredModelBinding = field(repr=False)

    async def invoke(
        self,
        context: ExecutionContext,
        route: ModelRouteDecision,
        request: ChatRequest,
        check: DisclosureCheck | None = None,
    ) -> AgentChatResult:
        """`check` (ADR-024) is supplied only by the host, for REMOTE bindings,
        from this exact execution's minted declaration."""
        if (
            type(context) is not ExecutionContext
            or type(route) is not ModelRouteDecision
        ):
            raise TypeError("Agent invocation requires context and route")
        if type(request) is not ChatRequest:
            raise TypeError("Agent invocation requires ChatRequest")
        if route.selected is None:
            raise ValueError("Agent invocation requires a unique route")
        coordination = await self.coordinator.coordinate(
            CoordinationRequest(context, self.configured.entry)
        )
        if coordination.outcome is not CoordinationOutcome.READY:
            error = None
            if coordination.category is not None:
                error = ErrorDetail(coordination.category, Recoverability.TERMINAL, ())
            return AgentChatResult(
                ExecutionResult(
                    coordination.execution_id,
                    coordination.state,
                    EffectExtent.NONE,
                    error,
                ),
                None,
            )
        if check is not None and check.context != context:
            raise ValueError("disclosure check belongs to another execution")
        execution, response = await invoke_routed_chat(
            self.coordinator, coordination, request, route, self.configured, check
        )
        return AgentChatResult(execution, response)
