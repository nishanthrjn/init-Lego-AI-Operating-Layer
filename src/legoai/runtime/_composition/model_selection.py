"""Private, trusted operator composition for one configured Chat contribution.

Input data selects an existing binding; it never imports code, admits a Plugin,
issues configuration revisions or grants authority. Factories are supplied by
trusted host wiring and must perform no I/O. Admission/activation and Catalog
publication remain prerequisites owned elsewhere.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from legoai.capabilities.ports import CatalogEntry, CatalogPort
from legoai.capabilities.values import CapabilityRequirement
from legoai.intelligence.model.ports import ModelPort
from legoai.intelligence.model.routing import ModelBinding, ModelRouteDecision
from legoai.kernel.references import ConfigurationRevisionRef
from legoai.plugins.ports import PluginLifecycleRecord, PluginLifecycleState
from legoai.reference.model import ollama_chat_offer
from legoai.reference.resolution import CapabilityResolution, resolve
from legoai.runtime._composition.model_governed import ConfiguredModelBinding


class CompositionFailure(Enum):
    INVALID_CONFIGURATION = "invalid_configuration"
    UNKNOWN_BINDING = "unknown_binding"
    STALE_CONFIGURATION = "stale_configuration"
    UNAVAILABLE_PROVIDER = "unavailable_provider"
    INCOMPATIBLE_PROVIDER = "incompatible_provider"
    INACTIVE_PLUGIN = "inactive_plugin"
    ACTIVATION_MISMATCH = "activation_mismatch"
    MISSING_DEPENDENCY = "missing_dependency"
    INITIALIZATION_FAILURE = "initialization_failure"


class ModelCompositionError(ValueError):
    """Safe category; chained constructor causes are restricted diagnostics."""

    def __init__(self, failure: CompositionFailure) -> None:
        self.failure = failure
        super().__init__(failure.value)


@dataclass(frozen=True, slots=True)
class DesiredModelBinding:
    """Captured selection data, not a configuration publication or authority."""

    configuration_revision: ConfigurationRevisionRef
    binding_id: str

    def __post_init__(self) -> None:
        if type(self.configuration_revision) is not ConfigurationRevisionRef:
            raise TypeError("selection requires ConfigurationRevisionRef")
        if (
            type(self.binding_id) is not str
            or not self.binding_id.strip()
            or len(self.binding_id) > 256
        ):
            raise ModelCompositionError(CompositionFailure.INVALID_CONFIGURATION)


def capture_model_selection(
    data: Mapping[str, object], *, pinned_revision: ConfigurationRevisionRef
) -> DesiredModelBinding:
    """Closed two-field input; the owner supplies the expected exact revision.

    File/environment parsing belongs at the host boundary. No environment is
    read here. A matching string cannot publish or authorize a revision.
    """
    if type(pinned_revision) is not ConfigurationRevisionRef:
        raise TypeError("capture requires an owner-supplied configuration revision")
    if set(data) != {"revision", "binding"}:
        raise ModelCompositionError(CompositionFailure.INVALID_CONFIGURATION)
    revision, binding = data["revision"], data["binding"]
    if type(revision) is not str or type(binding) is not str:
        raise ModelCompositionError(CompositionFailure.INVALID_CONFIGURATION)
    if revision != pinned_revision.revision:
        raise ModelCompositionError(CompositionFailure.STALE_CONFIGURATION)
    return DesiredModelBinding(pinned_revision, binding)


@dataclass(frozen=True, slots=True)
class ModelContribution:
    """Host-owned exact realization association; never deserialized from data.

    Activation is the existing Lifecycle record, including its admission and
    transition revision. This does not invent a separate activation identity.
    The host must supply current records and withdraw disabled contributions.
    The factory captures immutable non-secret settings for this exact revision.
    Changed settings require a new configuration and lifecycle treatment.
    """

    configuration_revision: ConfigurationRevisionRef
    binding: ModelBinding
    entry: CatalogEntry
    activation: PluginLifecycleRecord
    construct: Callable[[], ModelPort] = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.configuration_revision) is not ConfigurationRevisionRef:
            raise TypeError("contribution requires ConfigurationRevisionRef")
        if (
            type(self.binding) is not ModelBinding
            or type(self.entry) is not CatalogEntry
        ):
            raise TypeError("contribution requires ModelBinding and CatalogEntry")
        if type(self.activation) is not PluginLifecycleRecord:
            raise TypeError("contribution requires PluginLifecycleRecord")
        if not callable(self.construct):
            raise TypeError("contribution requires an operator-supplied constructor")
        scope = self.configuration_revision.configuration.application.scope
        if scope.tenant_id != self.entry.tenant_context.tenant_id:
            raise ModelCompositionError(CompositionFailure.ACTIVATION_MISMATCH)
        if (
            self.activation.plugin_id != self.entry.plugin_id
            or self.activation.release != self.entry.release
            or self.activation.admission_id != self.entry.admission_id
            or self.activation.tenant_context != self.entry.tenant_context
        ):
            raise ModelCompositionError(CompositionFailure.ACTIVATION_MISMATCH)


@dataclass(frozen=True, slots=True)
class ComposedModel:
    """Retained resolution plus exact realization; not an invocation permit."""

    resolution: CapabilityResolution
    activation: PluginLifecycleRecord
    route: ModelRouteDecision
    configured: ConfiguredModelBinding


def compose_model(
    requirement: CapabilityRequirement,
    desired: DesiredModelBinding,
    *,
    catalog: CatalogPort,
    contributions: tuple[ModelContribution, ...],
    resolved_at: datetime,
) -> ComposedModel:
    """Select only a compatible published contribution, then construct once.

    The complete resolver result is retained even when multiple compatible
    offers exist: explicit configuration selects, never catalog ordering.
    No retries, fallback, imports, network calls or Plugin lifecycle transitions.
    Constructors must be bounded local construction; this is not a supervisor
    for arbitrary Plugin initialization effects.
    """
    if type(requirement) is not CapabilityRequirement:
        raise TypeError("composition requires CapabilityRequirement")
    if type(desired) is not DesiredModelBinding:
        raise TypeError("composition requires DesiredModelBinding")
    if type(contributions) is not tuple or any(
        type(item) is not ModelContribution for item in contributions
    ):
        raise TypeError("composition requires an immutable contribution tuple")
    if len(contributions) > 256:
        raise ModelCompositionError(CompositionFailure.INVALID_CONFIGURATION)
    keys = [
        (item.configuration_revision, item.binding.binding_id) for item in contributions
    ]
    if len(set(keys)) != len(keys):
        raise ModelCompositionError(CompositionFailure.INVALID_CONFIGURATION)
    named = tuple(
        item for item in contributions if item.binding.binding_id == desired.binding_id
    )
    if not named:
        raise ModelCompositionError(CompositionFailure.UNKNOWN_BINDING)
    matching = tuple(
        item
        for item in named
        if item.configuration_revision == desired.configuration_revision
    )
    if not matching:
        raise ModelCompositionError(CompositionFailure.STALE_CONFIGURATION)
    selected = matching[0]
    if selected.activation.state is not PluginLifecycleState.ACTIVE:
        raise ModelCompositionError(CompositionFailure.INACTIVE_PLUGIN)
    snapshot = catalog.snapshot(selected.entry.tenant_context)
    if selected.entry not in snapshot.entries:
        raise ModelCompositionError(CompositionFailure.UNAVAILABLE_PROVIDER)
    resolution = resolve(requirement, snapshot, resolved_at=resolved_at)
    if selected.entry not in resolution.candidates:
        raise ModelCompositionError(CompositionFailure.INCOMPATIBLE_PROVIDER)
    # ConfiguredModelBinding supports precisely the existing v1 Chat offer.
    # Validate this before executing even a trusted constructor.
    if selected.entry.offer != ollama_chat_offer():
        raise ModelCompositionError(CompositionFailure.INCOMPATIBLE_PROVIDER)
    try:
        adapter = selected.construct()
        if not callable(getattr(adapter, "chat", None)) or not callable(
            getattr(adapter, "embed", None)
        ):
            raise TypeError("constructor did not supply ModelPort methods")
    except ImportError as error:
        raise ModelCompositionError(CompositionFailure.MISSING_DEPENDENCY) from error
    except Exception as error:
        raise ModelCompositionError(
            CompositionFailure.INITIALIZATION_FAILURE
        ) from error
    configured = ConfiguredModelBinding(
        desired.configuration_revision, selected.binding, selected.entry, adapter
    )
    route = ModelRouteDecision(
        selected.binding.requirement,
        desired.configuration_revision,
        (selected.binding,),
    )
    return ComposedModel(resolution, selected.activation, route, configured)
