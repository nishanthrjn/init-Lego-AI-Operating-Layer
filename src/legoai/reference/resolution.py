"""F7: pure Capability compatibility analysis (PLUGIN-SPEC PLG-017-020,
PLG-038, PLG-065; Gate-1 plan SS16).

This module is **not** the future runtime ``CapabilityResolver``
(PLUGIN-SPEC PLG-065's ``Resolution`` row; Gate-2). Function names are
deliberately analytical (``analyze_*``, never ``resolve``) to avoid implying
an executable binding: this batch instantiates no Provider, authorizes
nothing, admits no Plugin, activates nothing, and returns no callable or
object usable to invoke anything (PLUGIN-SPEC PLG-038: "Eligible is not
selected; selected is not authorized"). Input is a requirement plus a
sequence of already-constructed, already-valid ``PluginDeclaration``
values; output is inert reference/descriptor data only.

Ambiguity is a first-class, expected outcome, not an error to paper over.
When more than one declared offer satisfies a requirement, this module
returns every one of them as ``AMBIGUOUS`` -- it never silently picks the
first, highest-version, or alphabetically-first candidate (PLUGIN-SPEC
PLG-019: "Numeric version overlap ... does not prove behavior, trust,
isolation or recovery suitability"; this batch's own SS19 instruction).
Selecting one candidate among several is later, separately governed
Resolution/admission work this batch does not implement.
"""

from dataclasses import dataclass
from enum import Enum

from legoai.capabilities.values import CapabilityRequirement
from legoai.kernel.versions import Version
from legoai.plugins.values import PluginDeclaration, PluginId


class CompatibilityStatus(Enum):
    """The three analyzable outcomes PLUGIN-SPEC actually distinguishes
    (PLG-038, PLG-065's Resolution row). There is no fourth "invalid
    declaration" status here: a structurally invalid ``PluginDeclaration``
    cannot be constructed at all (``legoai.plugins.values``), so by the
    time analysis runs every input declaration is already valid."""

    NO_MATCH = "no_match"
    UNIQUE_MATCH = "unique_match"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class CandidateOffer:
    """One compatible offer found during analysis, attributed to its
    declaring Plugin and release. Not a selection, binding, or
    authorization -- see the module docstring."""

    plugin_id: PluginId
    release: Version
    capability_version: Version

    def __post_init__(self) -> None:
        if type(self.plugin_id) is not PluginId:
            raise TypeError("candidate offer requires PluginId")
        if type(self.release) is not Version:
            raise TypeError("candidate offer requires a release Version")
        if type(self.capability_version) is not Version:
            raise TypeError("candidate offer requires a capability Version")


@dataclass(frozen=True, slots=True)
class CompatibilityAnalysis:
    """The retained analysis fact for one requirement: its status and the
    exact candidates found. ``candidates`` is empty for ``NO_MATCH``,
    exactly one entry for ``UNIQUE_MATCH``, and two or more for
    ``AMBIGUOUS`` -- deterministically ordered (never set/dict iteration
    order) so repeated analysis of the same inputs is stable."""

    requirement: CapabilityRequirement
    status: CompatibilityStatus
    candidates: tuple[CandidateOffer, ...]

    def __post_init__(self) -> None:
        if type(self.requirement) is not CapabilityRequirement:
            raise TypeError("analysis requires CapabilityRequirement")
        if type(self.status) is not CompatibilityStatus:
            raise TypeError("analysis requires CompatibilityStatus")
        if type(self.candidates) is not tuple or any(
            type(candidate) is not CandidateOffer for candidate in self.candidates
        ):
            raise TypeError("candidates must be an immutable tuple of CandidateOffer")
        expected = {
            CompatibilityStatus.NO_MATCH: 0,
            CompatibilityStatus.UNIQUE_MATCH: 1,
        }.get(self.status)
        if expected is not None and len(self.candidates) != expected:
            raise ValueError(
                f"{self.status.value} requires exactly {expected} candidate(s)"
            )
        if self.status is CompatibilityStatus.AMBIGUOUS and len(self.candidates) < 2:
            raise ValueError("ambiguous status requires at least two candidates")


def _candidate_sort_key(candidate: CandidateOffer) -> tuple[str, str, int, int, int]:
    return (
        candidate.plugin_id.namespace,
        candidate.plugin_id.local_id,
        candidate.release.major,
        candidate.release.minor,
        candidate.release.patch,
    )


def analyze_compatibility(
    requirement: CapabilityRequirement,
    declarations: tuple[PluginDeclaration, ...],
) -> CompatibilityAnalysis:
    """Find every declared offer across ``declarations`` that satisfies
    ``requirement``. Pure and deterministic: the same inputs always yield
    the same ``CompatibilityAnalysis``, in the same candidate order."""
    if type(requirement) is not CapabilityRequirement:
        raise TypeError("analyze_compatibility requires CapabilityRequirement")
    if type(declarations) is not tuple or any(
        type(declaration) is not PluginDeclaration for declaration in declarations
    ):
        raise TypeError(
            "analyze_compatibility requires an immutable tuple of PluginDeclaration"
        )
    candidates = [
        CandidateOffer(declaration.plugin_id, declaration.release, offer.version)
        for declaration in declarations
        for offer in declaration.offers
        if offer.capability == requirement.capability
        and requirement.version_range.contains(offer.version)
    ]
    candidates.sort(key=_candidate_sort_key)
    ordered = tuple(candidates)
    if not ordered:
        status = CompatibilityStatus.NO_MATCH
    elif len(ordered) == 1:
        status = CompatibilityStatus.UNIQUE_MATCH
    else:
        status = CompatibilityStatus.AMBIGUOUS
    return CompatibilityAnalysis(requirement, status, ordered)


def analyze_requirements(
    requirements: tuple[CapabilityRequirement, ...],
    declarations: tuple[PluginDeclaration, ...],
) -> tuple[CompatibilityAnalysis, ...]:
    """Analyze several requirements against the same declared offers,
    preserving one independent fact per requirement. One requirement being
    ``NO_MATCH`` never suppresses, overrides, or is flattened into another
    requirement's ``UNIQUE_MATCH`` -- there is no invented whole-set
    success/failure verdict here (this batch's own SS42 instruction)."""
    if type(requirements) is not tuple or any(
        type(requirement) is not CapabilityRequirement for requirement in requirements
    ):
        raise TypeError(
            "analyze_requirements requires an immutable tuple of CapabilityRequirement"
        )
    return tuple(
        analyze_compatibility(requirement, declarations) for requirement in requirements
    )
