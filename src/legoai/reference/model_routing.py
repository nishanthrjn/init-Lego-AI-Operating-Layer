"""Pure exact-profile routing over one immutable operator configuration."""

from dataclasses import dataclass

from legoai.intelligence.model.routing import (
    ModelBinding,
    ModelRequirement,
    ModelRouteDecision,
    _validate_bindings,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.references import ConfigurationRevisionRef


@dataclass(frozen=True, slots=True)
class DeterministicModelRouter:
    """Configured availability only; no discovery, health check, preference or I/O.

    The operator supplies an exact revision and 0–256 bindings, and must never
    assign that revision to different configuration. New configuration means a
    new router/revision; prior decisions remain pinned to their original values.
    """

    configuration_revision: ConfigurationRevisionRef
    bindings: tuple[ModelBinding, ...]

    def __post_init__(self) -> None:
        if type(self.configuration_revision) is not ConfigurationRevisionRef:
            raise TypeError("model router requires ConfigurationRevisionRef")
        _validate_bindings(self.bindings)

    def route(
        self, requirement: ModelRequirement, tenant_context: TenantContext
    ) -> ModelRouteDecision:
        if type(requirement) is not ModelRequirement:
            raise TypeError("model routing requires ModelRequirement")
        if type(tenant_context) is not TenantContext:
            raise TypeError("model routing requires explicit TenantContext")
        scope = self.configuration_revision.configuration.application.scope
        if tenant_context.tenant_id != scope.tenant_id:
            raise ValueError("model routing tenant does not match configuration")
        return ModelRouteDecision(
            requirement,
            self.configuration_revision,
            tuple(b for b in self.bindings if b.requirement == requirement),
        )
