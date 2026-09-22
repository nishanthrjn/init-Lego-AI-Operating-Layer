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
from datetime import datetime
from enum import Enum

from legoai.capabilities.ports import CatalogEntry, CatalogSnapshot
from legoai.capabilities.values import CapabilityRequirement
from legoai.kernel.context import TenantContext
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


# --- Gate-2 M7: runtime Capability resolution over published Catalog state ---
#
# Everything above this line is F7 and is unchanged by this addition. What
# follows is the *runtime* resolver ADR-002 assigns to this same module
# ("Resolution snapshots/closure/results"), distinct from F7's static
# analysis in three concrete ways:
#
#   1. Input is a `CatalogSnapshot` (M6) -- already tenant-scoped, already
#      published-only -- never an arbitrary caller-supplied sequence of
#      `PluginDeclaration` values. Only entries that actually cleared
#      Plugin admission/activation and Catalog publication are considered;
#      `resolve()` never inspects M5 lifecycle records or re-runs
#      validation/admission to "find more candidates".
#   2. Output (`CapabilityResolution`) carries the exact `CatalogSnapshot`
#      revision and tenant scope it was computed against, so a later
#      consumer can detect staleness -- F7's `CompatibilityAnalysis` has no
#      such notion because it is not tied to any published/mutable state.
#   3. `ResolutionStatus` names remain analytically identical to F7's
#      `CompatibilityStatus` (a `RESOLVED` unique match is exactly as
#      non-authoritative as F7's `UNIQUE_MATCH`) but are a *distinct* type:
#      collapsing the two would blur "this declaration is compatible in the
#      abstract" with "this exact published, tenant-scoped offer is the
#      unique runtime candidate right now".
#
# The compatibility *rule* itself is reused, not reimplemented:
# `requirement.version_range.contains(...)` (the same `CapabilityVersionRange`
# method `analyze_compatibility` calls above) is the only matching logic;
# this section adds no independent version-range algorithm.
#
# `resolve()` is a pure function of its two arguments plus the caller-
# supplied `resolved_at` -- no Catalog query, Plugin discovery, provider
# loading, clock read, or I/O of any kind. No `CapabilityResolutionPort` is
# defined: unlike M4's Governance current-authority facts, this operation
# has no external dependency to seam behind a Protocol (the same reasoning
# already documented for M5's pure lifecycle-transition functions).
#
# Critical invariant (task SS3): a `RESOLVED` result means only that one
# published offer's capability/version satisfies the stated requirement
# under this resolver's semantics. It does not mean the caller may invoke
# it, that resources are available, that dispatch may proceed, or that
# current authority has been checked -- ADR-005/007 revalidation remains a
# later, separate stage this module does not perform.


class ResolutionStatus(Enum):
    """Analytically identical to `CompatibilityStatus` above, but a
    distinct type: a runtime `RESOLVED` is not F7's `UNIQUE_MATCH` renamed,
    because it is computed only over already-published, tenant-scoped
    Catalog entries at one exact revision.
    """

    NO_MATCH = "no_match"
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"


def _resolution_candidate_sort_key(
    entry: CatalogEntry,
) -> tuple[str, str, int, int, int, int, int, int]:
    return (
        entry.plugin_id.namespace,
        entry.plugin_id.local_id,
        entry.release.major,
        entry.release.minor,
        entry.release.patch,
        entry.offer.version.major,
        entry.offer.version.minor,
        entry.offer.version.patch,
    )


@dataclass(frozen=True, slots=True)
class CapabilityResolution:
    """The retained runtime resolution fact for one requirement against one
    exact Catalog snapshot. `candidates` are `CatalogEntry` references (M6)
    -- never copies, never a new wrapper type duplicating their fields, and
    never anything carrying a callable/provider/adapter/handle. Deterministic
    ordering is presentation/reproducibility only, never a preference or
    ranking signal: multiple compatible candidates always remain
    `AMBIGUOUS`, with no highest-version/first-published/alphabetical
    tie-break.

    `tenant_context` and `catalog_revision` are carried explicitly so a
    later consumer (e.g. ADR-007's dispatch gate) can detect that the
    Catalog has moved on since this resolution was computed -- this module
    does not itself define a staleness *policy*, only preserves the fact
    needed to evaluate one later.
    """

    requirement: CapabilityRequirement
    tenant_context: TenantContext
    status: ResolutionStatus
    candidates: tuple[CatalogEntry, ...]
    catalog_revision: int
    resolved_at: datetime

    def __post_init__(self) -> None:
        if type(self.requirement) is not CapabilityRequirement:
            raise TypeError("resolution requires CapabilityRequirement")
        if type(self.tenant_context) is not TenantContext:
            raise TypeError("resolution requires TenantContext")
        if type(self.status) is not ResolutionStatus:
            raise TypeError("resolution requires ResolutionStatus")
        if type(self.candidates) is not tuple or any(
            type(candidate) is not CatalogEntry for candidate in self.candidates
        ):
            raise TypeError("candidates must be an immutable tuple of CatalogEntry")
        if type(self.catalog_revision) is not int or isinstance(
            self.catalog_revision, bool
        ):
            raise TypeError("resolution catalog_revision must be an int")
        if self.catalog_revision < 0:
            raise ValueError("resolution catalog_revision must be nonnegative")
        if type(self.resolved_at) is not datetime:
            raise TypeError("resolution resolved_at must be datetime")
        if self.resolved_at.tzinfo is None:
            raise ValueError("resolution resolved_at must be timezone-aware")
        expected = {
            ResolutionStatus.NO_MATCH: 0,
            ResolutionStatus.RESOLVED: 1,
        }.get(self.status)
        if expected is not None and len(self.candidates) != expected:
            raise ValueError(
                f"{self.status.value} requires exactly {expected} candidate(s)"
            )
        if self.status is ResolutionStatus.AMBIGUOUS and len(self.candidates) < 2:
            raise ValueError("ambiguous status requires at least two candidates")
        for candidate in self.candidates:
            if candidate.tenant_context != self.tenant_context:
                raise ValueError("candidate tenant does not match resolution tenant")
            if candidate.offer.capability != self.requirement.capability:
                raise ValueError("candidate capability does not match requirement")
            if not self.requirement.version_range.contains(candidate.offer.version):
                raise ValueError("candidate version does not satisfy requirement range")


def resolve(
    requirement: CapabilityRequirement,
    snapshot: CatalogSnapshot,
    *,
    resolved_at: datetime,
) -> CapabilityResolution:
    """Find every Catalog-published, tenant-scoped entry in `snapshot` that
    satisfies `requirement`. Pure and deterministic: the same requirement
    and snapshot always yield the same `CapabilityResolution`, in the same
    candidate order, regardless of the snapshot's own internal entry order.

    Considers only `snapshot.entries` -- it does not query a live
    `CatalogPort`, inspect Plugin lifecycle records, or re-run admission.
    """
    if type(requirement) is not CapabilityRequirement:
        raise TypeError("resolve requires CapabilityRequirement")
    if type(snapshot) is not CatalogSnapshot:
        raise TypeError("resolve requires CatalogSnapshot")
    if type(resolved_at) is not datetime:
        raise TypeError("resolve resolved_at must be datetime")
    if resolved_at.tzinfo is None:
        raise ValueError("resolve resolved_at must be timezone-aware")
    candidates = [
        entry
        for entry in snapshot.entries
        if entry.offer.capability == requirement.capability
        and requirement.version_range.contains(entry.offer.version)
    ]
    candidates.sort(key=_resolution_candidate_sort_key)
    ordered = tuple(candidates)
    if not ordered:
        status = ResolutionStatus.NO_MATCH
    elif len(ordered) == 1:
        status = ResolutionStatus.RESOLVED
    else:
        status = ResolutionStatus.AMBIGUOUS
    return CapabilityResolution(
        requirement,
        snapshot.tenant_context,
        status,
        ordered,
        snapshot.revision,
        resolved_at,
    )
