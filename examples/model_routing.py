"""Offline logical Chat selection; no provider, Agent or invocation is started."""

from legoai.intelligence.model.ports import ModelRouterPort
from legoai.intelligence.model.routing import ModelBinding, ModelRequirement
from legoai.intelligence.model.values import ModelId, ProviderId
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import ApplicationId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.reference.model_routing import DeterministicModelRouter


def main() -> None:
    tenant = TenantContext(TenantId("example"))
    revision = ConfigurationRevisionRef(
        ConfigurationRef(
            ApplicationRef(
                ReferenceScope("example-operator", tenant.tenant_id),
                ApplicationId("routing-example"),
            ),
            "models",
        ),
        "r1",
        Version(1, 0, 0),
    )
    requirement = ModelRequirement("engineering-reasoning")
    binding = ModelBinding(
        "reasoning-local",
        requirement,
        ModelId("demo-model"),
        ProviderId("demo-provider"),
    )
    router: ModelRouterPort = DeterministicModelRouter(revision, (binding,))
    decision = router.route(requirement, tenant)
    selected = decision.selected
    assert selected is not None
    print(f"{requirement.profile}: {decision.status.value}")
    print(
        f"{selected.binding_id}: {selected.provider_id.value}/{selected.model_id.value}"
    )
    print(f"configuration: {decision.configuration_revision.revision}")


if __name__ == "__main__":
    main()
