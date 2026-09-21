"""F7: inert Capability declaration values (PLUGIN-SPEC PLG-006, PLG-011,
PLG-015-020, PLG-040; ADR-002 SS7/SS9.2, Capabilities/C plane).

These are static semantic *facts about* capability compatibility -- never an
executable capability, provider implementation, or callable/interface
binding. A ``CapabilityOffer`` is what a Plugin release declares it can
satisfy (PLG-040); a ``CapabilityRequirement`` is what a consumer needs
(PLG-015-016). They are kept structurally distinct rather than one dataclass
with nullable fields, matching PLUGIN-SPEC's own "Requirement ≠ Offer"
framing.

Scope narrowing (Gate-1 plan SS14's exact F7 file list; this batch's own
"smallest coherent next batch" instruction): this module models only
Capability identity/version and the exact/ranged version-compatibility
facts PLG-008/PLG-019 require for pure compatibility analysis. It does not
model Provider identity (PLG-014) as a concept distinct from the owning
Plugin -- an offer's provenance is the ``PluginDeclaration`` that contains
it (``legoai.plugins.values``), which is sufficient identity attribution
for this batch's compatibility analysis; a separate ``ProviderId`` is added
only when a real Gate-2 consumer needs Provider-vs-Plugin distinctness.
Health, tenant, resource, trust, permission, extension, and conformance-
evidence declarations (PLG-012, PLG-028-030, PLG-057-062) are likewise
entirely absent: none has a real consumer in this batch, and Gate-1's own
anti-overengineering rule is not to add a module without one.

No field accepts a callable, class, module, or any other executable value
(F7's hard "no executable inactive binding" exit criterion) -- every field
is a Kernel identity/version primitive or bounded text, structurally
incapable of carrying implementation.

Version compatibility uses only ``Version``'s already-accepted lexicographic
ordering (``legoai.kernel.versions``) applied to an explicit, caller-stated
inclusive/exclusive minimum/maximum range (PLG-008: "ranges with
inclusive/exclusive bounds and prerelease handling"). No semver caret/tilde
shorthand, no implicit 0.x compatibility inference, and no prerelease
handling beyond what ``Version`` itself already supports (none) is invented
here.
"""

from dataclasses import dataclass, field

from legoai.kernel.identity import _validate
from legoai.kernel.versions import Version


@dataclass(frozen=True, slots=True)
class CapabilityId:
    """Opaque Capability identity (PLUGIN-SPEC PLG-006).

    Construction does not declare, register, or verify anything about the
    named capability; it is an inert reference to be matched, not an
    assertion that the capability exists or is governed.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class CapabilityVersionRange:
    """An explicit, inclusive/exclusive-bounded acceptable version range
    (PLG-008). ``maximum=None`` means unbounded above; there is no
    unbounded-below form -- a requirement always states an explicit floor.

    An exact single-version requirement is expressed as
    ``CapabilityVersionRange(v, True, v, True)``; no separate "exact version"
    type is introduced for that case.
    """

    minimum: Version
    minimum_inclusive: bool = True
    maximum: Version | None = None
    maximum_inclusive: bool = True

    def __post_init__(self) -> None:
        if type(self.minimum) is not Version:
            raise TypeError("version range requires a Version minimum")
        if type(self.minimum_inclusive) is not bool:
            raise TypeError("minimum_inclusive must be a bool")
        if self.maximum is not None and type(self.maximum) is not Version:
            raise TypeError("maximum must be Version or None")
        if type(self.maximum_inclusive) is not bool:
            raise TypeError("maximum_inclusive must be a bool")
        if self.maximum is not None:
            if self.minimum > self.maximum:
                raise ValueError("version range minimum exceeds maximum")
            if self.minimum == self.maximum and not (
                self.minimum_inclusive and self.maximum_inclusive
            ):
                raise ValueError("version range excludes its only boundary value")

    def contains(self, version: Version) -> bool:
        """Whether ``version`` falls within this explicit range.

        Pure ordering comparison only -- never semver-style compatibility
        inference, and never true for a version outside the stated bounds
        regardless of shared major/minor components.
        """
        if type(version) is not Version:
            raise TypeError("contains requires a Version")
        if self.minimum_inclusive:
            if version < self.minimum:
                return False
        elif version <= self.minimum:
            return False
        if self.maximum is not None:
            if self.maximum_inclusive:
                if version > self.maximum:
                    return False
            elif version >= self.maximum:
                return False
        return True


@dataclass(frozen=True, slots=True)
class CapabilityRequirement:
    """What a consumer needs (PLG-015-016): an exact Capability identity and
    an acceptable version range. Declaring a requirement grants no
    authority and reserves nothing -- it is an input to later, separately
    governed resolution/admission (PLG-038: "eligible is not selected;
    selected is not authorized").
    """

    capability: CapabilityId
    version_range: CapabilityVersionRange

    def __post_init__(self) -> None:
        if type(self.capability) is not CapabilityId:
            raise TypeError("requirement requires CapabilityId")
        if type(self.version_range) is not CapabilityVersionRange:
            raise TypeError("requirement requires CapabilityVersionRange")


@dataclass(frozen=True, slots=True)
class CapabilityOffer:
    """What a Plugin release declares it can satisfy (PLG-040): an exact
    Capability identity and exact version. Attribution to the declaring
    Plugin/release is structural -- via containment in that
    ``PluginDeclaration.offers`` (``legoai.plugins.values``), never
    duplicated here. A syntactically valid offer is not eligible, selected,
    trusted, or admitted (PLG-038); this value carries none of those facts.
    """

    capability: CapabilityId
    version: Version

    def __post_init__(self) -> None:
        if type(self.capability) is not CapabilityId:
            raise TypeError("offer requires CapabilityId")
        if type(self.version) is not Version:
            raise TypeError("offer requires an exact Version")
