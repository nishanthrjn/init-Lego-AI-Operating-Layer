"""F8b: private direct composition of already-safe Gate-1 pieces (Gate-1
plan SS13's "internal walking skeleton", composition-experiment half).

This is a composition **proof**, not the production runtime. It contains
no Execution, ExecutionContext, CapabilityResolver, Plugin admission/
activation, authorization enforcement, resource claim, or async
supervision -- none of Gate 2 exists here. ``compose_direct`` proves that:

    F2 configuration capture/composition
    + F7 inert Plugin/Capability declarations and pure compatibility analysis
    + the one F8b deterministic reference function (legoai.reference.deterministic)
    + F8a's safe, non-authoritative local observation

can be assembled by ordinary explicit Python construction into one
coherent typed result. Nothing here is exported from ``legoai.runtime`` or
``legoai.__init__``; the ``_composition`` package is private by naming and
by the fact that nothing outside this module and its tests imports it.

Compatibility stays analytical (F7 task SS8-9, carried forward here):
``analyze_compatibility`` returning ``UNIQUE_MATCH`` means only that one
inert declaration is compatible with the stated requirement. It never means
a Plugin is admitted, a Provider is activated, or execution is authorized.
This module additionally requires that the one matched declaration is
*this batch's own statically known* text-normalization declaration before
it will call the deterministic function at all (SS30-32: "this
correspondence exists only because F8b controls both sides privately") --
a ``UNIQUE_MATCH`` against an unrelated declaration this module has no
implementation for is reported as ``FIXTURE_MISMATCH``, never guessed at.

``NO_MATCH`` and ``AMBIGUOUS`` compatibility results are never resolved by
picking an implementation anyway; both are reported as explicit composition
outcomes that never invoke the deterministic function (SS28-29, SS51-52).

Diagnostic containment: an ``ObservationSinkPort`` failure is caught at
exactly the diagnostic boundary (``_emit_best_effort`` below) and never
changes ``compose_direct``'s semantic result. No other exception is ever
silently swallowed -- a genuine programmer error in configuration capture,
compatibility analysis, or normalization still propagates.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from legoai.application.values import (
    CapturedCandidate,
    ComposedConfiguration,
    EffectiveConfiguration,
)
from legoai.capabilities.values import CapabilityRequirement
from legoai.kernel.identity import TenantId
from legoai.kernel.references import ConfigurationRef
from legoai.kernel.versions import Version
from legoai.observability.ports import ObservationSinkPort
from legoai.observability.values import Observation, ObservationEventCode
from legoai.plugins.values import PluginDeclaration
from legoai.reference.application.configuration import compose_configuration
from legoai.reference.deterministic import (
    normalize_text,
    text_normalization_plugin_id,
    text_normalization_release,
)
from legoai.reference.resolution import (
    CompatibilityAnalysis,
    CompatibilityStatus,
    analyze_compatibility,
)


class CompositionStatus(Enum):
    """The composition-level outcomes this fixture actually distinguishes.
    None of these is an admission, activation, or authorization decision --
    see the module docstring."""

    COMPOSED = "composed"
    NO_COMPATIBLE_DECLARATION = "no_compatible_declaration"
    AMBIGUOUS_DECLARATION = "ambiguous_declaration"
    FIXTURE_MISMATCH = "fixture_mismatch"


@dataclass(frozen=True, slots=True)
class CompositionResult:
    """The narrow, reference-scoped proof result. Carries only enough to
    show configuration was selected, declarations were analyzed, and (when
    unambiguous and fixture-matched) the deterministic function ran --
    never admission/authorization/execution readiness."""

    status: CompositionStatus
    configuration: ComposedConfiguration
    compatibility: CompatibilityAnalysis
    normalized_text: str | None

    def __post_init__(self) -> None:
        if type(self.status) is not CompositionStatus:
            raise TypeError("composition result requires CompositionStatus")
        if type(self.configuration) is not ComposedConfiguration:
            raise TypeError("composition result requires ComposedConfiguration")
        if type(self.compatibility) is not CompatibilityAnalysis:
            raise TypeError("composition result requires CompatibilityAnalysis")
        if self.status is CompositionStatus.COMPOSED:
            if self.normalized_text is None or type(self.normalized_text) is not str:
                raise ValueError("composed result requires normalized_text")
        elif self.normalized_text is not None:
            raise ValueError(f"{self.status.value} result cannot carry normalized_text")


def _emit_best_effort(sink: ObservationSinkPort, observation: Observation) -> None:
    """Diagnostic-only emission: a sink failure is caught here, and only
    here -- it never propagates into or changes ``compose_direct``'s
    semantic result. This is not a general-purpose error-swallowing
    wrapper; nothing else in this module is guarded this broadly."""
    try:
        sink.emit(observation)
    except Exception:  # noqa: BLE001 -- diagnostic boundary only, see docstring
        pass


class _NoOpObservationSink:
    """Private no-op sink used only when the caller supplies none."""

    def emit(self, observation: Observation) -> None:
        return None


def compose_direct(
    *,
    target: ConfigurationRef,
    candidates: tuple[CapturedCandidate, ...],
    contract_version: Version,
    interpretation_version: Version,
    text: str,
    requirement: CapabilityRequirement,
    declarations: tuple[PluginDeclaration, ...],
    normalization_function: Callable[[str, EffectiveConfiguration], str] | None = None,
    sink: ObservationSinkPort | None = None,
    tenant_id: TenantId | None = None,
) -> CompositionResult:
    """Compose configuration, inert declaration analysis, the one known
    deterministic function, and safe observation into one typed result.

    ``normalization_function`` defaults to
    ``legoai.reference.deterministic.normalize_text``; a caller may supply
    a different pure callable with the identical signature to prove
    substitutability (Gate-1 plan SS13), without this module needing a
    second production implementation. ``sink`` defaults to a private no-op
    when omitted -- observation is always best-effort and never
    authoritative (see module docstring).

    ``tenant_id`` is accepted only as a safe correlation value for the
    emitted ``Observation``; it is never evaluated for authorization here
    (Gate 2 owns that).
    """
    active_sink = sink if sink is not None else _NoOpObservationSink()

    configuration = compose_configuration(
        target,
        candidates,
        contract_version=contract_version,
        interpretation_version=interpretation_version,
    )

    _emit_best_effort(
        active_sink,
        Observation(
            1,
            ObservationEventCode("composition.started"),
            "legoai.runtime._composition.direct",
            tenant_id=tenant_id,
        ),
    )

    compatibility = analyze_compatibility(requirement, declarations)

    normalized_text: str | None = None
    if compatibility.status is CompatibilityStatus.NO_MATCH:
        status = CompositionStatus.NO_COMPATIBLE_DECLARATION
    elif compatibility.status is CompatibilityStatus.AMBIGUOUS:
        status = CompositionStatus.AMBIGUOUS_DECLARATION
    else:
        candidate = compatibility.candidates[0]
        if (
            candidate.plugin_id == text_normalization_plugin_id()
            and candidate.release == text_normalization_release()
        ):
            function = (
                normalization_function
                if normalization_function is not None
                else normalize_text
            )
            normalized_text = function(text, configuration.effective)
            status = CompositionStatus.COMPOSED
        else:
            status = CompositionStatus.FIXTURE_MISMATCH

    _emit_best_effort(
        active_sink,
        Observation(
            1,
            ObservationEventCode(f"composition.{status.value}"),
            "legoai.runtime._composition.direct",
            tenant_id=tenant_id,
        ),
    )

    return CompositionResult(status, configuration, compatibility, normalized_text)
