"""LegoAI v0.1: end-to-end governed Model invocation proof -- the effectful
counterpart to `tests/integration/composition/test_governed_direct.py`.
Exercises the complete real path (Plugin lifecycle, Catalog publish,
resolution, current authorization, dispatch arbitration, Coordinator
READY/RUNNING) followed by a governed chat/embedding invocation, using a
fake `ModelPort` (no live Ollama/network required by default -- task SS17).
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from legoai.capabilities.ports import CatalogEntry
from legoai.capabilities.values import (
    CapabilityId,
    CapabilityRequirement,
    CapabilityVersionRange,
)
from legoai.execution.ports import (
    CoordinationOutcome,
    CoordinationRequest,
    ExecutionTransitionError,
    SecurityContextResolutionPort,
)
from legoai.execution.values import (
    ExecutionContext,
    ExecutionId,
    ExecutionState,
    SecurityContextRef,
)
from legoai.governance.ports import SecurityContext
from legoai.governance.values import Grant, GrantId, PolicyRef, Principal
from legoai.intelligence.model.ports import (
    ModelPreflightError,
    ModelResponseRejectedError,
    ModelResponseUncertainError,
)
from legoai.intelligence.model.routing import (
    ModelBinding,
    ModelRequirement,
    ModelRouteDecision,
    ModelRouteStatus,
)
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatResult,
    ChatRole,
    EmbeddingRequest,
    EmbeddingResult,
    ModelId,
    ProviderId,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory
from legoai.kernel.identity import (
    ApplicationId,
    CorrelationId,
    OperationId,
    PrincipalId,
    TenantId,
)
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.plugins.ports import PluginAdmissionId
from legoai.plugins.values import PluginDeclaration, PluginId
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.evidence import InMemoryEvidenceCustody
from legoai.reference.execution import (
    DeterministicDispatchArbiter,
    ExecutionCoordinator,
)
from legoai.reference.governance import DeterministicAuthorizationEvaluator
from legoai.reference.model import (
    ollama_chat_capability_id,
    ollama_declaration,
)
from legoai.reference.model_routing import DeterministicModelRouter
from legoai.reference.plugins import activate, admit, initialize, inspect, validate
from legoai.reference.resolution import ResolutionStatus, resolve
from legoai.runtime._composition.model_governed import (
    ConfiguredModelBinding,
    invoke_governed_chat,
    invoke_governed_embedding,
    invoke_routed_chat,
)
from tests.support.execution import ImmediateSecurityContextResolver
from tests.support.governance import (
    InMemoryApprovalUseFake,
    InMemoryGrantStateFake,
    InMemoryPolicyCurrencyFake,
)

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _principal(name: str) -> Principal:
    return Principal(PrincipalRef("identity-owner", PrincipalId(name)))


def _target(tenant: str = "tenant") -> ConfigurationRef:
    return ConfigurationRef(
        ApplicationRef(
            ReferenceScope("composition", TenantId(tenant)), ApplicationId("app")
        ),
        "config",
    )


def _operation(tenant: str = "tenant") -> OperationRef:
    return OperationRef(_target(tenant), OperationId("op"), "configuration")


class _Environment:
    def __init__(
        self, *, tenant: str = "tenant", declaration: PluginDeclaration | None = None
    ) -> None:
        self.tenant = tenant
        self.grantee = _principal("service")
        self.grant_state = InMemoryGrantStateFake()
        self.approval_use = InMemoryApprovalUseFake()
        self.policy_currency = InMemoryPolicyCurrencyFake()
        self.authorization = DeterministicAuthorizationEvaluator(
            self.grant_state, self.approval_use, self.policy_currency
        )
        self.catalog = InMemoryCatalog()
        self.evidence = InMemoryEvidenceCustody()
        self.arbiter = DeterministicDispatchArbiter(
            self.authorization, self.catalog, self.evidence, self.approval_use
        )

        if declaration is None:
            declaration = ollama_declaration()
        discovered = inspect(declaration)
        validation = validate(discovered, declaration, evaluated_at=_EPOCH)
        record = admit(
            validation,
            TenantContext(TenantId(tenant)),
            PluginAdmissionId("admission-ollama"),
            established_at=_EPOCH,
        )
        active_record = activate(
            initialize(record, established_at=_EPOCH), established_at=_EPOCH
        )
        self.chat_entry = self.catalog.publish(
            active_record, declaration, declaration.offers[0], established_at=_EPOCH
        )
        self.embedding_entry = self.catalog.publish(
            active_record, declaration, declaration.offers[1], established_at=_EPOCH
        )

    def _resolve(self, capability_id: CapabilityId) -> CatalogEntry:
        requirement = CapabilityRequirement(
            capability_id, CapabilityVersionRange(Version(1, 0, 0))
        )
        resolution = resolve(
            requirement,
            self.catalog.snapshot(TenantContext(TenantId(self.tenant))),
            resolved_at=_EPOCH,
        )
        assert resolution.status is ResolutionStatus.RESOLVED
        return resolution.candidates[0]

    def security_context(self, *, grant: Grant | None) -> SecurityContext:
        return SecurityContext(
            self.grantee,
            TenantContext(TenantId(self.tenant)),
            _operation(self.tenant),
            "invoke-capability",
            ollama_chat_capability_id().value,
            grant,
            None,
            PolicyRef("policy-owner", "policy", Version(1, 0, 0)),
            _EPOCH + timedelta(minutes=30),
        )

    def execution_context(self, *, execution_id: str = "exec-1") -> ExecutionContext:
        return ExecutionContext(
            ExecutionId(execution_id),
            _operation(self.tenant),
            TenantContext(TenantId(self.tenant)),
            SecurityContextRef("issuer", "ref-1"),
            CorrelationId("corr-1"),
            None,
            None,
            None,
        )

    def coordination_request(
        self, entry: CatalogEntry, *, execution_id: str = "exec-1"
    ) -> CoordinationRequest:
        return CoordinationRequest(
            self.execution_context(execution_id=execution_id), entry
        )

    def coordinator(
        self, resolver: SecurityContextResolutionPort
    ) -> ExecutionCoordinator:
        return ExecutionCoordinator(resolver, self.arbiter, clock=lambda: _EPOCH)

    def grant(self) -> Grant:
        return Grant(
            GrantId("grant-1"),
            _principal("issuer"),
            self.grantee,
            TenantContext(TenantId(self.tenant)),
            "invoke-capability",
            ollama_chat_capability_id().value,
            False,
            _EPOCH,
            _EPOCH + timedelta(days=1),
        )


class _FakeModelPort:
    def __init__(
        self,
        *,
        chat_result: ChatResult | None = None,
        chat_error: Exception | None = None,
        embedding_result: EmbeddingResult | None = None,
        embedding_error: Exception | None = None,
    ) -> None:
        self._chat_result = chat_result
        self._chat_error = chat_error
        self._embedding_result = embedding_result
        self._embedding_error = embedding_error
        self.chat_calls = 0
        self.embed_calls = 0

    async def chat(self, request: ChatRequest) -> ChatResult:
        self.chat_calls += 1
        if self._chat_error is not None:
            raise self._chat_error
        assert self._chat_result is not None
        return self._chat_result

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.embed_calls += 1
        if self._embedding_error is not None:
            raise self._embedding_error
        assert self._embedding_result is not None
        return self._embedding_result


def _chat_result() -> ChatResult:
    return ChatResult(
        "an answer", ModelId("llama3.2"), ProviderId("ollama-local"), None
    )


# --- success ------------------------------------------------------------------------


def test_governed_chat_succeeds_through_full_path() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = ImmediateSecurityContextResolver(
            env.security_context(grant=env.grant())
        )
        coordinator = env.coordinator(resolver)
        entry = env._resolve(ollama_chat_capability_id())

        coordination = await coordinator.coordinate(env.coordination_request(entry))
        assert coordination.outcome is CoordinationOutcome.READY

        adapter = _FakeModelPort(chat_result=_chat_result())
        request = ChatRequest((ChatMessage(ChatRole.USER, "hi"),))
        execution_result, chat_result = await invoke_governed_chat(
            coordinator, coordination, request, adapter
        )

        assert adapter.chat_calls == 1
        assert execution_result.final_state is ExecutionState.SUCCEEDED
        assert execution_result.effect is EffectExtent.COMPLETED
        assert chat_result is not None
        assert chat_result.content == "an answer"

    asyncio.run(scenario())


def test_governed_embedding_succeeds_through_full_path() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = ImmediateSecurityContextResolver(
            env.security_context(grant=env.grant())
        )
        coordinator = env.coordinator(resolver)
        entry = env._resolve(env.embedding_entry.offer.capability)

        coordination = await coordinator.coordinate(env.coordination_request(entry))
        assert coordination.outcome is CoordinationOutcome.READY

        vectors = EmbeddingResult(
            ((1.0, 2.0),), 2, ModelId("nomic-embed-text"), ProviderId("ollama-local")
        )
        adapter = _FakeModelPort(embedding_result=vectors)
        execution_result, embedding_result = await invoke_governed_embedding(
            coordinator, coordination, EmbeddingRequest(("hello",)), adapter
        )

        assert adapter.embed_calls == 1
        assert execution_result.final_state is ExecutionState.SUCCEEDED
        assert embedding_result is not None
        assert embedding_result.dimension == 2

    asyncio.run(scenario())


# --- zero-invocation / failure paths -------------------------------------------------


def test_governed_chat_authorization_denied_never_invokes() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=None))
        coordinator = env.coordinator(resolver)
        entry = env._resolve(ollama_chat_capability_id())

        coordination = await coordinator.coordinate(env.coordination_request(entry))
        assert coordination.outcome is CoordinationOutcome.REJECTED
        assert coordination.category is ErrorCategory.AUTHORIZATION_DENIED

        adapter = _FakeModelPort(chat_result=_chat_result())
        with pytest.raises(ValueError, match="READY"):
            await invoke_governed_chat(
                coordinator,
                coordination,
                ChatRequest((ChatMessage(ChatRole.USER, "hi"),)),
                adapter,
            )
        assert adapter.chat_calls == 0

    asyncio.run(scenario())


def test_governed_chat_preflight_error_maps_to_none_effect() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = ImmediateSecurityContextResolver(
            env.security_context(grant=env.grant())
        )
        coordinator = env.coordinator(resolver)
        entry = env._resolve(ollama_chat_capability_id())
        coordination = await coordinator.coordinate(env.coordination_request(entry))

        adapter = _FakeModelPort(chat_error=ModelPreflightError("refused"))
        execution_result, chat_result = await invoke_governed_chat(
            coordinator,
            coordination,
            ChatRequest((ChatMessage(ChatRole.USER, "hi"),)),
            adapter,
        )

        assert adapter.chat_calls == 1
        assert chat_result is None
        assert execution_result.final_state is ExecutionState.FAILED
        assert execution_result.effect is EffectExtent.NONE

    asyncio.run(scenario())


def test_governed_chat_uncertain_error_maps_to_unknown_effect() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = ImmediateSecurityContextResolver(
            env.security_context(grant=env.grant())
        )
        coordinator = env.coordinator(resolver)
        entry = env._resolve(ollama_chat_capability_id())
        coordination = await coordinator.coordinate(env.coordination_request(entry))

        adapter = _FakeModelPort(chat_error=ModelResponseUncertainError("timed out"))
        execution_result, chat_result = await invoke_governed_chat(
            coordinator,
            coordination,
            ChatRequest((ChatMessage(ChatRole.USER, "hi"),)),
            adapter,
        )

        assert chat_result is None
        assert execution_result.final_state is ExecutionState.FAILED
        assert execution_result.effect is EffectExtent.UNKNOWN

    asyncio.run(scenario())


def test_governed_chat_rejected_error_maps_to_none_effect() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = ImmediateSecurityContextResolver(
            env.security_context(grant=env.grant())
        )
        coordinator = env.coordinator(resolver)
        entry = env._resolve(ollama_chat_capability_id())
        coordination = await coordinator.coordinate(env.coordination_request(entry))

        adapter = _FakeModelPort(chat_error=ModelResponseRejectedError("model missing"))
        execution_result, chat_result = await invoke_governed_chat(
            coordinator,
            coordination,
            ChatRequest((ChatMessage(ChatRole.USER, "hi"),)),
            adapter,
        )

        assert chat_result is None
        assert execution_result.final_state is ExecutionState.FAILED
        assert execution_result.effect is EffectExtent.NONE

    asyncio.run(scenario())


def test_governed_chat_implementation_mismatch_never_invokes() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = ImmediateSecurityContextResolver(
            env.security_context(grant=env.grant())
        )
        coordinator = env.coordinator(resolver)
        # Resolve the embedding entry but attempt to invoke it as chat.
        entry = env._resolve(env.embedding_entry.offer.capability)
        coordination = await coordinator.coordinate(env.coordination_request(entry))
        assert coordination.outcome is CoordinationOutcome.READY

        adapter = _FakeModelPort(chat_result=_chat_result())
        execution_result, chat_result = await invoke_governed_chat(
            coordinator,
            coordination,
            ChatRequest((ChatMessage(ChatRole.USER, "hi"),)),
            adapter,
        )

        assert adapter.chat_calls == 0
        assert chat_result is None
        assert execution_result.final_state is ExecutionState.FAILED
        assert execution_result.error is not None
        assert execution_result.error.category is ErrorCategory.DEPENDENCY_FAILURE

    asyncio.run(scenario())


# --- replay / concurrency -------------------------------------------------------------


def test_concurrent_governed_chat_calls_only_one_reaches_provider() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = ImmediateSecurityContextResolver(
            env.security_context(grant=env.grant())
        )
        coordinator = env.coordinator(resolver)
        entry = env._resolve(ollama_chat_capability_id())
        coordination = await coordinator.coordinate(env.coordination_request(entry))

        adapter = _FakeModelPort(chat_result=_chat_result())
        request = ChatRequest((ChatMessage(ChatRole.USER, "hi"),))

        outcomes = await asyncio.gather(
            invoke_governed_chat(coordinator, coordination, request, adapter),
            invoke_governed_chat(coordinator, coordination, request, adapter),
            return_exceptions=True,
        )

        assert adapter.chat_calls == 1
        successes = [o for o in outcomes if not isinstance(o, BaseException)]
        failures = [o for o in outcomes if isinstance(o, Exception)]
        assert len(successes) == 1
        assert len(failures) == 1

    asyncio.run(scenario())


def _routed_binding(
    env: _Environment, adapter: _FakeModelPort
) -> tuple[ModelRouteDecision, ConfiguredModelBinding]:
    requirement = ModelRequirement("engineering-reasoning")
    binding = ModelBinding(
        "reasoning", requirement, ModelId("fake-model"), ProviderId("fake-provider")
    )
    revision = ConfigurationRevisionRef(_target(env.tenant), "r1", Version(1, 0, 0))
    route = DeterministicModelRouter(revision, (binding,)).route(
        requirement, TenantContext(TenantId(env.tenant))
    )
    assert route.status is ModelRouteStatus.RESOLVED
    assert adapter.chat_calls == 0
    entry = env._resolve(ollama_chat_capability_id())
    return route, ConfiguredModelBinding(revision, binding, entry, adapter)


def _routed_result() -> ChatResult:
    return ChatResult(
        "routed answer", ModelId("fake-model"), ProviderId("fake-provider"), None
    )


@pytest.mark.parametrize(
    ("error", "effect"),
    [
        (None, EffectExtent.COMPLETED),
        (ModelPreflightError("before send"), EffectExtent.NONE),
        (ModelResponseUncertainError("after send"), EffectExtent.UNKNOWN),
        (ModelResponseRejectedError("rejected"), EffectExtent.NONE),
    ],
)
def test_routed_chat_uses_governed_path_and_preserves_effects(
    error: Exception | None, effect: EffectExtent
) -> None:
    async def scenario() -> None:
        # A different admitted Plugin supplies the same chat contract. Neither
        # the logical requirement nor routing has to know its provider identity.
        declaration = replace(
            ollama_declaration(),
            plugin_id=PluginId("legoai.test", "fake-model-adapter"),
        )
        env = _Environment(declaration=declaration)
        adapter = _FakeModelPort(chat_result=_routed_result(), chat_error=error)
        route, configured = _routed_binding(env, adapter)
        coordinator = env.coordinator(
            ImmediateSecurityContextResolver(env.security_context(grant=env.grant()))
        )
        coordination = await coordinator.coordinate(
            env.coordination_request(configured.entry)
        )
        request = ChatRequest((ChatMessage(ChatRole.USER, "hi"),))
        execution, output = await invoke_routed_chat(
            coordinator, coordination, request, route, configured
        )
        assert adapter.chat_calls == 1
        assert adapter.embed_calls == 0
        assert execution.effect is effect
        if error is None:
            assert execution.final_state is ExecutionState.SUCCEEDED
            assert output == _routed_result()
        else:
            assert execution.final_state is ExecutionState.FAILED
            assert output is None
        with pytest.raises(ExecutionTransitionError):
            await invoke_routed_chat(
                coordinator, coordination, request, route, configured
            )
        assert adapter.chat_calls == 1

    asyncio.run(scenario())


def test_routed_selection_does_not_authorize_invocation() -> None:
    async def scenario() -> None:
        env = _Environment()
        adapter = _FakeModelPort(chat_result=_routed_result())
        route, configured = _routed_binding(env, adapter)
        coordinator = env.coordinator(
            ImmediateSecurityContextResolver(env.security_context(grant=None))
        )
        coordination = await coordinator.coordinate(
            env.coordination_request(configured.entry)
        )
        assert coordination.category is ErrorCategory.AUTHORIZATION_DENIED
        with pytest.raises(ValueError, match="READY"):
            await invoke_routed_chat(
                coordinator,
                coordination,
                ChatRequest((ChatMessage(ChatRole.USER, "hi"),)),
                route,
                configured,
            )
        assert adapter.chat_calls == 0

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "mismatch",
    [
        "revision",
        "model",
        "provider",
        "binding",
        "entry",
        "subject",
        "absent",
        "ambiguous",
    ],
)
def test_routed_mismatch_never_substitutes_or_invokes(mismatch: str) -> None:
    async def scenario() -> None:
        env = _Environment()
        adapter = _FakeModelPort(chat_result=_routed_result())
        route, configured = _routed_binding(env, adapter)
        original = configured
        if mismatch == "revision":
            configured = replace(
                configured,
                configuration_revision=replace(
                    configured.configuration_revision, revision="r2"
                ),
            )
        elif mismatch == "model":
            configured = replace(
                configured,
                binding=replace(configured.binding, model_id=ModelId("other")),
            )
        elif mismatch == "provider":
            configured = replace(
                configured,
                binding=replace(configured.binding, provider_id=ProviderId("other")),
            )
        elif mismatch == "binding":
            configured = replace(
                configured, binding=replace(configured.binding, binding_id="other")
            )
        elif mismatch == "entry":
            configured = replace(
                configured,
                entry=replace(
                    configured.entry, admission_id=PluginAdmissionId("other")
                ),
            )
        elif mismatch == "subject":
            revision = replace(
                configured.configuration_revision,
                configuration=replace(_target(), instance="other"),
            )
            route = replace(route, configuration_revision=revision)
            configured = replace(configured, configuration_revision=revision)
        elif mismatch == "absent":
            route = replace(route, candidates=())
        else:
            route = replace(
                route,
                candidates=(
                    configured.binding,
                    replace(configured.binding, binding_id="other"),
                ),
            )
        coordinator = env.coordinator(
            ImmediateSecurityContextResolver(env.security_context(grant=env.grant()))
        )
        coordination = await coordinator.coordinate(
            env.coordination_request(original.entry)
        )
        execution, output = await invoke_routed_chat(
            coordinator,
            coordination,
            ChatRequest((ChatMessage(ChatRole.USER, "hi"),)),
            route,
            configured,
        )
        assert output is None
        assert execution.final_state is ExecutionState.FAILED
        assert execution.effect is EffectExtent.NONE
        assert adapter.chat_calls == 0

    asyncio.run(scenario())


def test_routed_response_identity_mismatch_is_rejected_without_fallback() -> None:
    async def scenario() -> None:
        env = _Environment()
        adapter = _FakeModelPort(
            chat_result=replace(_routed_result(), model_identity=ModelId("wrong"))
        )
        route, configured = _routed_binding(env, adapter)
        coordinator = env.coordinator(
            ImmediateSecurityContextResolver(env.security_context(grant=env.grant()))
        )
        coordination = await coordinator.coordinate(
            env.coordination_request(configured.entry)
        )
        execution, output = await invoke_routed_chat(
            coordinator,
            coordination,
            ChatRequest((ChatMessage(ChatRole.USER, "hi"),)),
            route,
            configured,
        )
        assert output is None
        assert execution.final_state is ExecutionState.FAILED
        assert execution.effect is EffectExtent.NONE
        assert adapter.chat_calls == 1

    asyncio.run(scenario())


def test_routed_chat_and_existing_chat_share_the_same_invocation_claim() -> None:
    async def scenario() -> None:
        env = _Environment()
        adapter = _FakeModelPort(chat_result=_routed_result())
        route, configured = _routed_binding(env, adapter)
        coordinator = env.coordinator(
            ImmediateSecurityContextResolver(env.security_context(grant=env.grant()))
        )
        coordination = await coordinator.coordinate(
            env.coordination_request(configured.entry)
        )
        request = ChatRequest((ChatMessage(ChatRole.USER, "hi"),))
        results = await asyncio.gather(
            invoke_routed_chat(coordinator, coordination, request, route, configured),
            invoke_governed_chat(coordinator, coordination, request, adapter),
            return_exceptions=True,
        )
        assert adapter.chat_calls == 1
        assert (
            sum(isinstance(result, ExecutionTransitionError) for result in results) == 1
        )

    asyncio.run(scenario())


def test_configured_binding_rejects_wrong_tenant_and_operation_kind() -> None:
    env = _Environment()
    _, configured = _routed_binding(env, _FakeModelPort())
    with pytest.raises(ValueError, match="tenant"):
        replace(
            configured,
            entry=replace(
                configured.entry, tenant_context=TenantContext(TenantId("other"))
            ),
        )
    with pytest.raises(ValueError, match="chat"):
        replace(configured, entry=env.embedding_entry)


def test_routed_chat_requires_this_coordinators_actual_admission() -> None:
    async def scenario() -> None:
        env = _Environment()
        adapter = _FakeModelPort(chat_result=_routed_result())
        route, configured = _routed_binding(env, adapter)
        resolver = ImmediateSecurityContextResolver(
            env.security_context(grant=env.grant())
        )
        coordinator = env.coordinator(resolver)
        coordination = await coordinator.coordinate(
            env.coordination_request(configured.entry)
        )
        with pytest.raises(ExecutionTransitionError):
            await invoke_routed_chat(
                env.coordinator(resolver),
                coordination,
                ChatRequest((ChatMessage(ChatRole.USER, "hi"),)),
                route,
                configured,
            )
        assert adapter.chat_calls == 0

    asyncio.run(scenario())


def test_routed_mismatch_cannot_settle_an_inflight_invocation() -> None:
    async def scenario() -> None:
        started, finish = asyncio.Event(), asyncio.Event()

        class WaitingModel(_FakeModelPort):
            async def chat(self, request: ChatRequest) -> ChatResult:
                started.set()
                await finish.wait()
                return await super().chat(request)

        env = _Environment()
        adapter = WaitingModel(chat_result=_routed_result())
        route, configured = _routed_binding(env, adapter)
        coordinator = env.coordinator(
            ImmediateSecurityContextResolver(env.security_context(grant=env.grant()))
        )
        coordination = await coordinator.coordinate(
            env.coordination_request(configured.entry)
        )
        request = ChatRequest((ChatMessage(ChatRole.USER, "hi"),))
        async with asyncio.TaskGroup() as group:
            pending = group.create_task(
                invoke_routed_chat(
                    coordinator, coordination, request, route, configured
                )
            )
            await asyncio.wait_for(started.wait(), timeout=5)
            try:
                with pytest.raises(ExecutionTransitionError):
                    await invoke_routed_chat(
                        coordinator,
                        coordination,
                        request,
                        replace(route, candidates=()),
                        configured,
                    )
            finally:
                finish.set()
        assert pending.result()[0].final_state is ExecutionState.SUCCEEDED
        assert adapter.chat_calls == 1

    asyncio.run(scenario())
