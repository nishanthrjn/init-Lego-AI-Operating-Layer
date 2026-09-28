"""Offline examples only: fake Model behind the public ADR-014 local host.

Operator configuration (grants, selection, capacity) and the trusted fake
ModelPort live here, at the example's composition root. Engineering
specializations receive only public contracts: an `AgentRuntimePort`, an
`ExecutionContext` minted by the host, and (for readers) a host-issued
`SecurityContext` plus `AuthorizationPort`.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from legoai.execution.agent.ports import AgentRuntimePort
from legoai.execution.values import ExecutionContext
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

NOW = datetime(2026, 1, 1, tzinfo=UTC)
READ_ACTION = "read-for-model-analysis"
WORKSPACE = "workspace"
_ACTIVE = (NOW, NOW + timedelta(hours=1))
_EXPIRED = (NOW - timedelta(hours=2), NOW - timedelta(hours=1))


class StaticModel:
    """Demonstration-only ModelPort; performs no network or tool operation."""

    def __init__(self, output: str) -> None:
        self.output = output
        self.calls = 0
        self.last_request: ChatRequest | None = None
        self.error: Exception | None = None

    async def chat(self, request: ChatRequest) -> ChatResult:
        self.calls += 1
        self.last_request = request
        if self.error is not None:
            raise self.error
        return ChatResult(self.output, ModelId("static"), ProviderId("demo"), None)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        raise NotImplementedError("Chat-only demo")


@dataclass(frozen=True)
class GovernedDemo:
    host: GovernedHost
    runtime: AgentRuntimePort
    context: ExecutionContext
    model: StaticModel
    configuration: ConfigurationRef


def create_governed_demo(
    output: str,
    *,
    route_count: int = 1,
    model_allowed: bool = True,
    read_allowed: bool = True,
) -> GovernedDemo:
    """Open one host for one demo run.

    `route_count` 1 routes the engineering profile; 0 configures a different
    profile so routing finds no match. The public host pins exactly one selected
    binding, so an ambiguous route cannot be configured through it. Denied
    authority is modelled as a configured but expired operator grant.
    """
    if route_count not in (0, 1):
        raise ValueError("the public local host pins exactly one binding")
    tenant = TenantId("demo")
    target = ConfigurationRef(
        ApplicationRef(ReferenceScope("operator", tenant), ApplicationId("demo")),
        "models",
    )
    model = StaticModel(output)

    def construct() -> ModelPort:
        return model

    profile = "engineering-reasoning" if route_count else "unrouted-profile"
    config = LocalHostConfig(
        ConfigurationRevisionRef(target, "r1", Version(1, 0, 0)),
        PrincipalRef("operator", PrincipalId("service")),
        PolicyRef("operator", "demo", Version(1, 0, 0)),
        (
            OperatorGrant(
                GrantId("demo"),
                "invoke-capability",
                ModelPurpose.CHAT.capability_id.value,
                *(_ACTIVE if model_allowed else _EXPIRED),
            ),
            OperatorGrant(
                GrantId("read"),
                READ_ACTION,
                WORKSPACE,
                *(_ACTIVE if read_allowed else _EXPIRED),
            ),
        ),
        (
            ModelBindingConfig(
                "static",
                ModelRequirement(profile),
                TrustedModelContribution(
                    PluginId("legoai.demo", "static"),
                    ProviderId("demo"),
                    ModelId("static"),
                    frozenset({ModelPurpose.CHAT}),
                    construct,
                ),
            ),
        ),
        max_executions=64,
    )
    host = open_local_host(
        config, {"revision": "r1", "binding": "static"}, clock=lambda: NOW
    )
    return GovernedDemo(
        host,
        host.agent_runtime(),
        host.model_execution(ModelPurpose.CHAT),
        model,
        target,
    )
