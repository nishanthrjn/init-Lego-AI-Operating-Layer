"""MODEL-STRUCTURED-OUTPUT-1: capability declaration and fail-closed routing.

Uses the governed routed-chat environment; fake ModelPorts only, no network.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from legoai.execution.values import ExecutionState
from legoai.intelligence.model.routing import (
    ModelBinding,
    ModelRequirement,
    ModelRouteStatus,
)
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatResult,
    ChatRole,
    JsonObject,
    JsonString,
    ModelId,
    ProviderId,
    StructuredResponseFormat,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory
from legoai.kernel.identity import TenantId
from legoai.kernel.references import ConfigurationRevisionRef
from legoai.kernel.versions import Version
from legoai.plugins.values import PluginId
from legoai.reference.model import ollama_chat_capability_id, ollama_declaration
from legoai.reference.model_routing import DeterministicModelRouter
from legoai.runtime._composition.model_governed import (
    ConfiguredModelBinding,
    invoke_routed_chat,
)
from legoai.runtime.api import (
    ModelBindingConfig,
    ModelDeployment,
    ModelPurpose,
    OllamaSettings,
    OpenAICompatibleSettings,
    TrustedModelContribution,
)
from legoai.runtime.local import _realization
from tests.integration.composition.test_model_governed import (
    _Environment,
    _FakeModelPort,
    _target,
)
from tests.support.execution import ImmediateSecurityContextResolver

REQ = ModelRequirement("engineering-reasoning")
FORMAT = StructuredResponseFormat(JsonObject((("answer", JsonString()),), ("answer",)))


class _Recording(_FakeModelPort):
    def __init__(self) -> None:
        super().__init__(
            chat_result=ChatResult(
                '{"answer":"x"}',
                ModelId("fake-model"),
                ProviderId("fake-provider"),
                None,
            )
        )
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> ChatResult:
        self.requests.append(request)
        return await super().chat(request)


def _binding(capable: bool, binding_id: str = "reasoning") -> ModelBinding:
    return ModelBinding(
        binding_id, REQ, ModelId("fake-model"), ProviderId("fake-provider"), capable
    )


async def _run(
    capable: bool, request: ChatRequest, *, granted: bool = True
) -> tuple[object, ChatResult | None, _Recording, object]:
    declaration = replace(
        ollama_declaration(), plugin_id=PluginId("legoai.test", "fake-model-adapter")
    )
    env = _Environment(declaration=declaration)
    adapter = _Recording()
    revision = ConfigurationRevisionRef(_target(env.tenant), "r1", Version(1, 0, 0))
    binding = _binding(capable)
    route = DeterministicModelRouter(revision, (binding,)).route(
        REQ, TenantContext(TenantId(env.tenant))
    )
    configured = ConfiguredModelBinding(
        revision, binding, env._resolve(ollama_chat_capability_id()), adapter
    )
    coordinator = env.coordinator(
        ImmediateSecurityContextResolver(
            env.security_context(grant=env.grant() if granted else None)
        )
    )
    coordination = await coordinator.coordinate(
        env.coordination_request(configured.entry)
    )
    if not granted:
        return coordination, None, adapter, route
    execution, output = await invoke_routed_chat(
        coordinator, coordination, request, route, configured
    )
    return execution, output, adapter, route


def _chat(fmt: StructuredResponseFormat | None = None) -> ChatRequest:
    return ChatRequest((ChatMessage(ChatRole.USER, "hi"),), fmt)


# 1-7 routing


def test_ordinary_chat_uses_ordinary_binding() -> None:
    execution, output, adapter, _ = asyncio.run(_run(False, _chat()))
    assert execution.final_state is ExecutionState.SUCCEEDED  # type: ignore[attr-defined]
    assert output is not None and adapter.requests[0].response_format is None


def test_structured_request_reaches_capable_binding_with_format() -> None:
    execution, output, adapter, _ = asyncio.run(_run(True, _chat(FORMAT)))
    assert execution.final_state is ExecutionState.SUCCEEDED  # type: ignore[attr-defined]
    assert adapter.requests == [_chat(FORMAT)]
    assert adapter.requests[0].response_format is FORMAT


def test_structured_request_to_incapable_binding_fails_closed_typed() -> None:
    execution, output, adapter, route = asyncio.run(_run(False, _chat(FORMAT)))
    assert route.status is ModelRouteStatus.RESOLVED  # type: ignore[attr-defined]
    assert output is None and adapter.chat_calls == 0
    assert execution.final_state is ExecutionState.FAILED  # type: ignore[attr-defined]
    assert execution.effect is EffectExtent.NONE  # type: ignore[attr-defined]
    assert execution.error.category is ErrorCategory.VALIDATION_ERROR  # type: ignore[attr-defined]


def test_no_silent_downgrade_to_text() -> None:
    _, _, adapter, _ = asyncio.run(_run(False, _chat(FORMAT)))
    assert adapter.requests == []  # never re-sent without the requirement


def test_only_incapable_candidates_fail_and_capable_is_not_preferred() -> None:
    revision = ConfigurationRevisionRef(_target("tenant"), "r1", Version(1, 0, 0))
    router = DeterministicModelRouter(
        revision, (_binding(False, "plain"), _binding(True, "structured"))
    )
    route = router.route(REQ, TenantContext(TenantId("tenant")))
    # Existing semantics: two candidates are AMBIGUOUS. Capability never picks one.
    assert route.status is ModelRouteStatus.AMBIGUOUS and route.selected is None


def test_capable_candidate_selected_by_existing_policy() -> None:
    revision = ConfigurationRevisionRef(_target("tenant"), "r1", Version(1, 0, 0))
    route = DeterministicModelRouter(revision, (_binding(True),)).route(
        REQ, TenantContext(TenantId("tenant"))
    )
    assert route.status is ModelRouteStatus.RESOLVED and route.selected == _binding(
        True
    )


def test_no_new_fallback_surface() -> None:
    import inspect

    params = inspect.signature(DeterministicModelRouter.route).parameters
    assert list(params) == ["self", "requirement", "tenant_context"]
    execution, _, adapter, _ = asyncio.run(_run(False, _chat(FORMAT)))
    assert adapter.chat_calls == 0  # no alternative call of any kind


# 8-9 authority


def test_capability_grants_no_authority() -> None:
    coordination, _, adapter, _ = asyncio.run(_run(True, _chat(FORMAT), granted=False))
    assert coordination.outcome.value != "ready"  # type: ignore[attr-defined]
    assert adapter.chat_calls == 0


@pytest.mark.parametrize("fmt", [None, FORMAT])
def test_response_format_does_not_change_authorization(
    fmt: StructuredResponseFormat | None,
) -> None:
    denied, _, adapter, _ = asyncio.run(_run(True, _chat(fmt), granted=False))
    assert denied.outcome.value != "ready" and adapter.chat_calls == 0  # type: ignore[attr-defined]
    allowed, _, adapter, _ = asyncio.run(_run(True, _chat(fmt), granted=True))
    assert allowed.final_state is ExecutionState.SUCCEEDED  # type: ignore[attr-defined]


# Capability declaration by the admitted provider


def test_ollama_binding_declares_structured_output() -> None:
    binding, *_ = _realization(
        ModelBindingConfig(
            "ollama",
            REQ,
            OllamaSettings(
                "http://127.0.0.1:11434", "m", "e", 30.0, ProviderId("ollama")
            ),
        )
    )
    assert binding.structured_output is True


def test_openai_compatible_binding_does_not_declare() -> None:
    binding, *_ = _realization(
        ModelBindingConfig(
            "openai",
            REQ,
            OpenAICompatibleSettings(
                "http://127.0.0.1:8000/v1",
                "m",
                None,
                30.0,
                None,
                ProviderId("openai"),
                ModelDeployment.LOCAL,
            ),
        )
    )
    assert binding.structured_output is False


@pytest.mark.parametrize("declared", [False, True])
def test_trusted_contribution_declares_explicitly(declared: bool) -> None:
    contribution = TrustedModelContribution(
        PluginId("legoai.test", "x"),
        ProviderId("p"),
        ModelId("m"),
        frozenset({ModelPurpose.CHAT}),
        lambda: _Recording(),
        structured_output=declared,
    )
    binding, *_ = _realization(ModelBindingConfig("t", REQ, contribution))
    assert binding.structured_output is declared
    default = replace(contribution, structured_output=False)
    assert default.structured_output is False
    with pytest.raises(TypeError):
        replace(contribution, structured_output="yes")  # type: ignore[arg-type]
