"""Offline M7 technical composition, not a public authoring facade."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from legoai.execution.agent.ports import AgentDefinition, AgentRequest
from legoai.execution.agent.values import AgentId, AgentOutputContract
from legoai.execution.values import ExecutionContext, ExecutionId, SecurityContextRef
from legoai.governance.ports import SecurityContext
from legoai.governance.values import Grant, GrantId, PolicyRef, Principal
from legoai.intelligence.model.routing import ModelBinding, ModelRequirement
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ModelId,
    ProviderId,
)
from legoai.kernel.context import TenantContext
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
from legoai.plugins.values import PluginId
from legoai.reference.agent import OneStepAgentRuntime
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.evidence import InMemoryEvidenceCustody
from legoai.reference.execution import (
    DeterministicDispatchArbiter,
    ExecutionCoordinator,
    StaticSecurityContextRegistry,
)
from legoai.reference.governance import (
    DeterministicAuthorizationEvaluator,
    InMemoryApprovalRegistry,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
)
from legoai.reference.model import ollama_chat_capability_id, ollama_declaration
from legoai.reference.model_routing import DeterministicModelRouter
from legoai.reference.plugins import activate, admit, initialize, inspect, validate
from legoai.runtime._composition.agent import GovernedAgentChat
from legoai.runtime._composition.model_governed import ConfiguredModelBinding


class StaticModel:
    """Demonstration-only ModelPort; performs no network or tool operation."""

    async def chat(self, request: ChatRequest) -> ChatResult:
        return ChatResult(
            "A bounded Agent result.", ModelId("static"), ProviderId("demo"), None
        )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        raise NotImplementedError("Chat-only demo")


async def main() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    version = Version(1, 0, 0)
    tenant = TenantContext(TenantId("demo"))
    target = ConfigurationRef(
        ApplicationRef(
            ReferenceScope("operator", tenant.tenant_id), ApplicationId("demo")
        ),
        "models",
    )
    operation = OperationRef(target, OperationId("analyze"), "configuration")
    revision = ConfigurationRevisionRef(target, "r1", version)
    requirement = ModelRequirement("analysis")
    binding = ModelBinding("static", requirement, ModelId("static"), ProviderId("demo"))
    # Reuse the existing v1 Chat capability, supplied by an explicit fake Plugin.
    # The historical declaration helper constructs data, never an Ollama client.
    declaration = replace(
        ollama_declaration(), plugin_id=PluginId("legoai.demo", "static")
    )
    catalog = InMemoryCatalog()
    record = admit(
        validate(inspect(declaration), declaration, evaluated_at=now),
        tenant,
        PluginAdmissionId("demo"),
        established_at=now,
    )
    record = activate(initialize(record, established_at=now), established_at=now)
    entry = catalog.publish(
        record, declaration, declaration.offers[0], established_at=now
    )
    principal = Principal(PrincipalRef("operator", PrincipalId("service")))
    grant = Grant(
        GrantId("demo"),
        principal,
        principal,
        tenant,
        "invoke-capability",
        ollama_chat_capability_id().value,
        False,
        now,
        now + timedelta(hours=1),
    )
    security = SecurityContext(
        principal,
        tenant,
        operation,
        "invoke-capability",
        ollama_chat_capability_id().value,
        grant,
        None,
        PolicyRef("operator", "demo", version),
        now,
    )
    security_ref = SecurityContextRef("operator", "demo")
    resolver = StaticSecurityContextRegistry()
    resolver.register(security_ref, security)
    approvals = InMemoryApprovalRegistry()
    arbiter = DeterministicDispatchArbiter(
        DeterministicAuthorizationEvaluator(
            InMemoryGrantRegistry(), approvals, InMemoryPolicyRegistry()
        ),
        catalog,
        InMemoryEvidenceCustody(),
        approvals,
    )
    runtime = OneStepAgentRuntime(
        DeterministicModelRouter(revision, (binding,)),
        GovernedAgentChat(
            ExecutionCoordinator(resolver, arbiter, clock=lambda: now),
            ConfiguredModelBinding(revision, binding, entry, StaticModel()),
        ),
    )
    definition = AgentDefinition(
        AgentId("analysis"),
        version,
        "Analyze the supplied text.",
        requirement,
        AgentOutputContract(64),
        128,
        512,
    )
    request = AgentRequest(
        ExecutionContext(
            ExecutionId("demo"),
            operation,
            tenant,
            security_ref,
            CorrelationId("demo"),
            None,
            None,
            None,
        ),
        "Explain this bounded example.",
    )
    result = await runtime.run(definition, request)
    print(result.status.value)
    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
