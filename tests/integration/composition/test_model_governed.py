"""LegoAI v0.1: end-to-end governed Model invocation proof -- the effectful
counterpart to `tests/integration/composition/test_governed_direct.py`.
Exercises the complete real path (Plugin lifecycle, Catalog publish,
resolution, current authorization, dispatch arbitration, Coordinator
READY/RUNNING) followed by a governed chat/embedding invocation, using a
fake `ModelPort` (no live Ollama/network required by default -- task SS17).
"""

from __future__ import annotations

import asyncio
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
    OperationRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.plugins.ports import PluginAdmissionId
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
from legoai.reference.plugins import activate, admit, initialize, inspect, validate
from legoai.reference.resolution import ResolutionStatus, resolve
from legoai.runtime._composition.model_governed import (
    invoke_governed_chat,
    invoke_governed_embedding,
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
    def __init__(self, *, tenant: str = "tenant") -> None:
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
