"""Offline ADR-014 consumer: public imports only, no private wiring or Grants.

The composition root below is the only place that sees operator configuration
and the trusted fake ModelPort. `answer` is application code: it depends only
on the public `GovernedHost` contract and owner values.
"""

import asyncio
from datetime import UTC, datetime, timedelta

from legoai.execution.agent.ports import AgentDefinition, AgentRequest
from legoai.execution.agent.values import AgentId, AgentOutputContract
from legoai.governance.values import GrantId, PolicyRef
from legoai.intelligence.model.ports import ModelPort
from legoai.intelligence.model.routing import ModelRequirement
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ModelId,
    ProviderId,
)
from legoai.kernel.identity import ApplicationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.plugins.values import PluginId
from legoai.runtime.api import (
    GovernedHost,
    LocalHostConfig,
    ModelBindingConfig,
    ModelPurpose,
    OperatorGrant,
    TrustedModelContribution,
)
from legoai.runtime.local import open_local_host

PROFILE = ModelRequirement("analysis")


class OfflineModel:
    """Demonstration-only trusted ModelPort; performs no network operation."""

    async def chat(self, request: ChatRequest) -> ChatResult:
        return ChatResult(
            "A bounded Agent result.", ModelId("offline"), ProviderId("demo"), None
        )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        raise NotImplementedError("Chat-only demo")


def open_demo_host() -> GovernedHost:
    """Composition root: operator configuration plus trusted code."""
    now = datetime.now(UTC)
    target = ConfigurationRef(
        ApplicationRef(
            ReferenceScope("operator", TenantId("demo")), ApplicationId("demo")
        ),
        "models",
    )

    def construct() -> ModelPort:
        return OfflineModel()

    config = LocalHostConfig(
        ConfigurationRevisionRef(target, "r1", Version(1, 0, 0)),
        PrincipalRef("operator", PrincipalId("service")),
        PolicyRef("operator", "demo", Version(1, 0, 0)),
        (
            OperatorGrant(
                GrantId("demo-chat"),
                "invoke-capability",
                ModelPurpose.CHAT.capability_id.value,
                now - timedelta(seconds=1),
                now + timedelta(minutes=5),
            ),
        ),
        (
            ModelBindingConfig(
                "offline",
                PROFILE,
                TrustedModelContribution(
                    PluginId("legoai.demo", "offline"),
                    ProviderId("demo"),
                    ModelId("offline"),
                    frozenset({ModelPurpose.CHAT}),
                    construct,
                ),
            ),
        ),
        max_executions=8,
    )
    return open_local_host(config, {"revision": "r1", "binding": "offline"})


async def answer(host: GovernedHost, text: str) -> tuple[str, str | None]:
    """Application code: public contracts only."""
    definition = AgentDefinition(
        AgentId("analysis"),
        Version(1, 0, 0),
        "Analyze the supplied text.",
        PROFILE,
        AgentOutputContract(64),
        128,
        512,
    )
    context = host.model_execution(ModelPurpose.CHAT)
    result = await host.agent_runtime().run(definition, AgentRequest(context, text))
    return result.status.value, result.output


async def main() -> None:
    status, output = await answer(open_demo_host(), "Explain this bounded example.")
    print(status)
    print(output)


if __name__ == "__main__":
    asyncio.run(main())
