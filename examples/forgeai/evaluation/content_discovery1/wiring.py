"""Public-host governed offline replay; grants are read/structure/Chat only."""

from datetime import UTC, datetime, timedelta

from forgeai.cli import ReplayModel, replay_binding
from legoai_engineering.analyst.authorized import REPOSITORY_READ_ACTION
from legoai_engineering.repository.structure_authorized import (
    REPOSITORY_STRUCTURE_ACTION,
)

from legoai.governance.values import GrantId, PolicyRef
from legoai.intelligence.model.values import ChatRequest, ChatResult
from legoai.kernel.identity import ApplicationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.runtime.api import (
    GovernedHost,
    LocalHostConfig,
    ModelPurpose,
    OperatorGrant,
)
from legoai.runtime.local import open_local_host

NOW = datetime(2026, 10, 4, tzinfo=UTC)


class Replay(ReplayModel):
    def __init__(self, output: str) -> None:
        super().__init__(output)
        self.requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> ChatResult:
        self.requests.append(request)
        return await super().chat(request)


def host_for(
    model: Replay, *, read_allowed: bool = True
) -> tuple[GovernedHost, ConfigurationRef]:
    target = ConfigurationRef(
        ApplicationRef(
            ReferenceScope("operator", TenantId("content-eval")),
            ApplicationId("content-eval"),
        ),
        "workspace",
    )
    grants = tuple(
        OperatorGrant(
            GrantId(str(i)),
            action,
            scope,
            NOW - timedelta(hours=2),
            NOW + timedelta(hours=1)
            if read_allowed or action != REPOSITORY_READ_ACTION
            else NOW - timedelta(hours=1),
        )
        for i, (action, scope) in enumerate(
            (
                (REPOSITORY_READ_ACTION, "workspace"),
                (REPOSITORY_STRUCTURE_ACTION, "workspace"),
                ("invoke-capability", ModelPurpose.CHAT.capability_id.value),
            )
        )
    )
    config = LocalHostConfig(
        ConfigurationRevisionRef(target, "r1", Version(1, 0, 0)),
        PrincipalRef("operator", PrincipalId("evaluation")),
        PolicyRef("operator", "content-eval", Version(1, 0, 0)),
        grants,
        (replay_binding(model),),
        max_executions=8,
    )
    return open_local_host(
        config, {"revision": "r1", "binding": "replay"}, clock=lambda: NOW
    ), target
