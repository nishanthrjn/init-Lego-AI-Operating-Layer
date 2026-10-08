"""Chat-only configuration selection values; no invocation or authority.

Profiles and binding IDs are opaque, case-sensitive operator labels. They are
not provider names, endpoints or credentials. Model/provider IDs state the
configured expectation, distinct from the observed identities in ChatResult.
"""

from dataclasses import dataclass, field
from enum import Enum

from legoai.intelligence.model.values import ModelId, ProviderId
from legoai.kernel.identity import _validate
from legoai.kernel.references import ConfigurationRevisionRef


@dataclass(frozen=True, slots=True)
class ModelRequirement:
    """Logical Chat profile only; no provider choice or authorization grant."""

    profile: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.profile)
        if self.profile.isspace():
            raise ValueError("model profile must not be blank")


@dataclass(frozen=True, slots=True)
class ModelBinding:
    """Inert operator configuration, never a provider client or availability proof.

    `structured_output` declares that the admitted binding's adapter honors a
    `ChatRequest.response_format` requirement (ADR-022). It is a capability
    fact, never an authorization grant. Default False.
    """

    binding_id: str = field(repr=False)
    requirement: ModelRequirement
    model_id: ModelId
    provider_id: ProviderId
    structured_output: bool = False

    def __post_init__(self) -> None:
        _validate(self.binding_id)
        if self.binding_id.isspace():
            raise ValueError("model binding ID must not be blank")
        if type(self.requirement) is not ModelRequirement:
            raise TypeError("model binding requires ModelRequirement")
        if type(self.model_id) is not ModelId:
            raise TypeError("model binding requires ModelId")
        if type(self.provider_id) is not ProviderId:
            raise TypeError("model binding requires ProviderId")
        if type(self.structured_output) is not bool:
            raise TypeError("structured_output must be bool")


def _validate_bindings(bindings: tuple[ModelBinding, ...]) -> None:
    if type(bindings) is not tuple:
        raise TypeError("model bindings must be an immutable tuple")
    if len(bindings) > 256:
        raise ValueError("model configuration supports at most 256 bindings")
    seen: set[str] = set()
    for binding in bindings:
        if type(binding) is not ModelBinding:
            raise TypeError("model bindings require ModelBinding values")
        if binding.binding_id in seen:
            raise ValueError("duplicate model binding ID")
        seen.add(binding.binding_id)


class ModelRouteStatus(Enum):
    RESOLVED = "resolved"
    NO_MATCH = "no_match"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class ModelRouteDecision:
    """Exact configuration attribution and candidates in non-preference order.

    Construction validates shape, not configuration ownership, completeness or
    authority. The trusted router supplies all matches. No route grants a call.
    """

    requirement: ModelRequirement
    configuration_revision: ConfigurationRevisionRef
    candidates: tuple[ModelBinding, ...]

    def __post_init__(self) -> None:
        if type(self.requirement) is not ModelRequirement:
            raise TypeError("model route requires ModelRequirement")
        if type(self.configuration_revision) is not ConfigurationRevisionRef:
            raise TypeError("model route requires ConfigurationRevisionRef")
        _validate_bindings(self.candidates)
        if any(b.requirement != self.requirement for b in self.candidates):
            raise ValueError("model route candidates must match the requirement")

    @property
    def status(self) -> ModelRouteStatus:
        if not self.candidates:
            return ModelRouteStatus.NO_MATCH
        if len(self.candidates) == 1:
            return ModelRouteStatus.RESOLVED
        return ModelRouteStatus.AMBIGUOUS

    @property
    def selected(self) -> ModelBinding | None:
        """No selection exists for an absent or ambiguous route."""
        return self.candidates[0] if len(self.candidates) == 1 else None
