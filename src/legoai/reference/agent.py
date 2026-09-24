"""Stateless one-step Agent driver; only typed Ports cross owner boundaries."""

from dataclasses import dataclass, field

from legoai.execution.agent.ports import (
    AgentChatPort,
    AgentChatResult,
    AgentDefinition,
    AgentRequest,
    AgentResult,
)
from legoai.execution.agent.values import AgentExecutionStatus, _text
from legoai.execution.values import ExecutionState
from legoai.intelligence.model.ports import ModelRouterPort
from legoai.intelligence.model.routing import ModelRouteDecision
from legoai.intelligence.model.values import ChatMessage, ChatRequest, ChatRole


@dataclass(frozen=True, slots=True)
class OneStepAgentRuntime:
    router: ModelRouterPort = field(repr=False)
    governed_chat: AgentChatPort = field(repr=False)

    async def run(
        self, definition: AgentDefinition, request: AgentRequest
    ) -> AgentResult:
        if type(definition) is not AgentDefinition or type(request) is not AgentRequest:
            raise TypeError("Agent run requires AgentDefinition and AgentRequest")
        _text(request.text, definition.max_input_bytes)
        route = self.router.route(
            definition.model_requirement, request.context.tenant_context
        )
        if type(route) is not ModelRouteDecision:
            raise TypeError("router must return ModelRouteDecision")
        if (
            route.requirement != definition.model_requirement
            or route.configuration_revision.configuration
            != request.context.operation.subject
        ):
            raise ValueError("route does not match requested requirement/configuration")
        if route.selected is None:
            return AgentResult(
                definition,
                request.context.execution_id,
                route,
                AgentExecutionStatus.ROUTING_FAILED,
                None,
                None,
            )
        chat = ChatRequest(
            (
                ChatMessage(ChatRole.SYSTEM, definition.system_prompt),
                ChatMessage(ChatRole.USER, request.text),
            )
        )
        outcome = await self.governed_chat.invoke(request.context, route, chat)
        if type(outcome) is not AgentChatResult:
            raise TypeError("Agent Chat boundary must return AgentChatResult")
        output = None
        if outcome.execution.final_state is not ExecutionState.SUCCEEDED:
            status = AgentExecutionStatus.MODEL_FAILED
        else:
            assert outcome.response is not None
            try:
                definition.output_contract.validate(outcome.response.content)
            except TypeError, ValueError:
                status = AgentExecutionStatus.OUTPUT_INVALID
            else:
                status = AgentExecutionStatus.SUCCEEDED
                output = outcome.response.content
        return AgentResult(
            definition,
            request.context.execution_id,
            route,
            status,
            outcome.execution,
            output,
        )
