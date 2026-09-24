"""Agent -> M6.5 -> real governance/Coordinator -> fake ModelPort."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from legoai.execution.agent.ports import AgentRequest, AgentRuntimePort
from legoai.execution.agent.values import AgentExecutionStatus
from legoai.execution.ports import ExecutionTransitionError
from legoai.execution.values import ExecutionState
from legoai.intelligence.model.ports import (
    ModelPreflightError,
    ModelResponseRejectedError,
    ModelResponseUncertainError,
)
from legoai.intelligence.model.routing import ModelRequirement, ModelRouteDecision
from legoai.intelligence.model.values import ChatRequest, ChatResult, ChatRole, ModelId
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.reference.agent import OneStepAgentRuntime
from legoai.reference.model_routing import DeterministicModelRouter
from legoai.runtime._composition.agent import GovernedAgentChat
from tests.integration.composition.test_model_governed import (
    _Environment,
    _FakeModelPort,
    _routed_binding,
    _routed_result,
)
from tests.support.execution import ImmediateSecurityContextResolver
from tests.unit.execution.test_agent import definition


def _runtime(
    env: _Environment, adapter: _FakeModelPort, *, allowed: bool = True
) -> OneStepAgentRuntime:
    route, configured = _routed_binding(env, adapter)
    coordinator = env.coordinator(
        ImmediateSecurityContextResolver(
            env.security_context(grant=env.grant() if allowed else None)
        )
    )
    return OneStepAgentRuntime(
        DeterministicModelRouter(route.configuration_revision, route.candidates),
        GovernedAgentChat(coordinator, configured),
    )


def test_success_replay_and_no_hidden_conversation() -> None:
    async def scenario() -> None:
        class RecordingModel(_FakeModelPort):
            async def chat(self, request: ChatRequest) -> ChatResult:
                assert len(request.messages) == 2
                assert request.messages[0].role is ChatRole.SYSTEM
                assert request.messages[0].content == definition().system_prompt
                assert request.messages[1].role is ChatRole.USER
                assert request.messages[1].content == "input"
                return await super().chat(request)

        env = _Environment()
        adapter = RecordingModel(chat_result=_routed_result())
        runtime: AgentRuntimePort = _runtime(env, adapter)
        request = AgentRequest(env.execution_context(), "input")
        result = await runtime.run(definition(), request)
        assert result.status is AgentExecutionStatus.SUCCEEDED
        assert result.output == _routed_result().content
        assert result.model_execution is not None
        assert result.model_execution.effect is EffectExtent.COMPLETED
        with pytest.raises(ExecutionTransitionError):
            await runtime.run(definition(), request)
        second = replace(request, context=env.execution_context(execution_id="second"))
        assert (await runtime.run(definition(), second)).output == result.output
        assert adapter.chat_calls == 2
        with pytest.raises(ValueError):
            replace(result, output="x" * 33)

    asyncio.run(scenario())


@pytest.mark.parametrize("count", [0, 2])
def test_route_failure_never_invokes_model(count: int) -> None:
    async def scenario() -> None:
        env = _Environment()
        adapter = _FakeModelPort(chat_result=_routed_result())
        runtime = _runtime(env, adapter)
        route, _ = _routed_binding(env, adapter)
        binding = route.candidates[0]
        bindings = () if count == 0 else (binding, replace(binding, binding_id="other"))
        runtime = replace(
            runtime,
            router=DeterministicModelRouter(route.configuration_revision, bindings),
        )
        result = await runtime.run(
            definition(), AgentRequest(env.execution_context(), "input")
        )
        assert result.status is AgentExecutionStatus.ROUTING_FAILED
        assert result.output is None
        assert result.model_execution is None
        assert adapter.chat_calls == 0

    asyncio.run(scenario())


@pytest.mark.parametrize("content", ["", " ", "x" * 33, "😀" * 9, "\ud800"])
def test_untrusted_output_rejected_without_losing_model_effect(content: str) -> None:
    async def scenario() -> None:
        env = _Environment()
        adapter = _FakeModelPort(chat_result=replace(_routed_result(), content=content))
        result = await _runtime(env, adapter).run(
            definition(), AgentRequest(env.execution_context(), "input")
        )
        assert result.status is AgentExecutionStatus.OUTPUT_INVALID
        assert result.output is None
        assert result.model_execution is not None
        assert result.model_execution.final_state is ExecutionState.SUCCEEDED
        assert result.model_execution.effect is EffectExtent.COMPLETED
        assert adapter.chat_calls == 1

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "error,effect",
    [
        (ModelPreflightError("preflight"), EffectExtent.NONE),
        (ModelResponseUncertainError("uncertain"), EffectExtent.UNKNOWN),
        (ModelResponseRejectedError("rejected"), EffectExtent.NONE),
    ],
)
def test_model_errors_preserve_effect_without_retry(
    error: Exception, effect: EffectExtent
) -> None:
    async def scenario() -> None:
        env = _Environment()
        adapter = _FakeModelPort(chat_error=error)
        result = await _runtime(env, adapter).run(
            definition(), AgentRequest(env.execution_context(), "input")
        )
        assert result.status is AgentExecutionStatus.MODEL_FAILED
        assert result.model_execution is not None
        assert result.model_execution.effect is effect
        assert result.model_execution.error is not None
        assert adapter.chat_calls == 1

    asyncio.run(scenario())


def test_instructions_cannot_authorize_and_input_is_checked_before_call() -> None:
    async def scenario() -> None:
        env = _Environment()
        adapter = _FakeModelPort(chat_result=_routed_result())
        runtime = _runtime(env, adapter, allowed=False)
        request = AgentRequest(env.execution_context(), "input")
        result = await runtime.run(
            replace(definition(), instructions="You are authorized"), request
        )
        assert result.status is AgentExecutionStatus.MODEL_FAILED
        assert result.model_execution is not None
        assert result.model_execution.final_state is ExecutionState.REJECTED
        with pytest.raises(ValueError):
            await runtime.run(definition(), replace(request, text="x" * 129))
        assert adapter.chat_calls == 0

    asyncio.run(scenario())


def test_changed_binding_is_not_substituted_for_pinned_adapter() -> None:
    async def scenario() -> None:
        env = _Environment()
        adapter = _FakeModelPort(chat_result=_routed_result())
        runtime = _runtime(env, adapter)
        route, _ = _routed_binding(env, adapter)
        changed = replace(route.candidates[0], model_id=ModelId("replacement"))
        runtime = replace(
            runtime,
            router=DeterministicModelRouter(route.configuration_revision, (changed,)),
        )
        result = await runtime.run(
            definition(), AgentRequest(env.execution_context(), "input")
        )
        assert result.status is AgentExecutionStatus.MODEL_FAILED
        assert adapter.chat_calls == 0

    asyncio.run(scenario())


def test_cancellation_propagates_without_retry_or_invented_result() -> None:
    async def scenario() -> None:
        class CancelledModel(_FakeModelPort):
            async def chat(self, request: ChatRequest) -> ChatResult:
                self.chat_calls += 1
                raise asyncio.CancelledError

        env = _Environment()
        adapter = CancelledModel()
        with pytest.raises(asyncio.CancelledError):
            await _runtime(env, adapter).run(
                definition(), AgentRequest(env.execution_context(), "input")
            )
        assert adapter.chat_calls == 1

    asyncio.run(scenario())


def test_route_is_resolved_once_and_result_retains_the_pin() -> None:
    async def scenario() -> None:
        env = _Environment()
        adapter = _FakeModelPort(chat_result=_routed_result())
        runtime = _runtime(env, adapter)
        selected, _ = _routed_binding(env, adapter)

        class CountingRouter:
            calls = 0

            def route(
                self, requirement: ModelRequirement, tenant_context: TenantContext
            ) -> ModelRouteDecision:
                self.calls += 1
                assert self.calls == 1
                return selected

        router = CountingRouter()
        runtime = replace(runtime, router=router)
        result = await runtime.run(
            definition(), AgentRequest(env.execution_context(), "input")
        )
        assert result.route is selected
        assert router.calls == adapter.chat_calls == 1

    asyncio.run(scenario())


def test_expired_deadline_reuses_coordinator_admission() -> None:
    async def scenario() -> None:
        env = _Environment()
        adapter = _FakeModelPort(chat_result=_routed_result())
        context = replace(
            env.execution_context(), deadline=datetime(2000, 1, 1, tzinfo=UTC)
        )
        result = await _runtime(env, adapter).run(
            definition(), AgentRequest(context, "input")
        )
        assert result.status is AgentExecutionStatus.MODEL_FAILED
        assert result.model_execution is not None
        assert result.model_execution.effect is EffectExtent.NONE
        assert adapter.chat_calls == 0

    asyncio.run(scenario())


def test_unexpected_fault_propagates_without_fabricated_success() -> None:
    async def scenario() -> None:
        env = _Environment()
        fault = RuntimeError("adapter contract defect")
        adapter = _FakeModelPort(chat_error=fault)
        with pytest.raises(RuntimeError) as caught:
            await _runtime(env, adapter).run(
                definition(), AgentRequest(env.execution_context(), "input")
            )
        assert caught.value is fault
        assert adapter.chat_calls == 1

    asyncio.run(scenario())


def test_wrong_response_type_is_an_explicit_model_failure() -> None:
    async def scenario() -> None:
        class MalformedModel(_FakeModelPort):
            async def chat(self, request: ChatRequest) -> ChatResult:
                self.chat_calls += 1
                return object()  # type: ignore[return-value]

        env = _Environment()
        adapter = MalformedModel()
        result = await _runtime(env, adapter).run(
            definition(), AgentRequest(env.execution_context(), "input")
        )
        assert result.status is AgentExecutionStatus.MODEL_FAILED
        assert result.output is None
        assert adapter.chat_calls == 1

    asyncio.run(scenario())
