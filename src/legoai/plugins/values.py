"""F7: inert Plugin declaration values (PLUGIN-SPEC PLG-004-014, PLG-063;
ADR-002 SS7/SS9.2, Plugins/X plane).

A Plugin **declaration** is inert descriptive data. Constructing or
analyzing one MUST NOT import an implementation, execute code, grant
authority, activate anything, or register anything globally (PLUGIN-SPEC
PLG-004, PLG-021-023: "A conforming Plugin declaration is not an Actor,
Service, Agent, Adapter, Provider, or deployment instance"; "Inspection
MUST NOT execute activation callbacks or initialization effects").
Explicitly, and matching this batch's own hard exit criterion:

    Plugin declaration ≠ Plugin instance
    Plugin declaration ≠ admitted Plugin
    Plugin declaration ≠ activated Plugin
    Plugin declaration ≠ trusted Plugin

Scope narrowing (Gate-1 plan SS14's exact F7 file list; PLUGIN-SPEC's full
PLG-063 semantic manifest is deliberately NOT modeled here): this module
represents only Plugin identity, release version, and declared Capability
offers/requirements -- the minimum PLUGIN-SPEC facts a pure compatibility
analysis (``legoai.reference.resolution``) actually consumes. Owner/
publisher/namespace-authority, metadata, configuration contract, lifecycle
contract, health semantics, permissions/trust, tenant/isolation,
extensions, resource requirements, Secret requirements, and realization
references (PLG-063's full Required/Conditional rows) are intentionally
absent: none has a real consumer in this batch, and none is needed to
prove "no executable inactive binding" or pure compatibility matching.
Adding them without a consumer would violate Gate-1's own anti-
overengineering rule. They arrive with Catalog/Lifecycle admission
(Gate-2), which this batch does not implement.

Deliberately excluded field: any implementation locator (module path,
class name, entry point, factory, command, URL, executable). PLUGIN-SPEC
allows "realization references" only conditionally (PLG-063, "C"), and even
then only as an inert identifier a real admission process would resolve
later -- this batch has no such consumer, so the field is omitted entirely
rather than represented-but-unused. Omitting it outright is safer than
representing it inertly: there is then no field an implementer could later
be tempted to resolve/import "just this once."
"""

from dataclasses import dataclass, field

from legoai.capabilities.values import (
    CapabilityId,
    CapabilityOffer,
    CapabilityRequirement,
)
from legoai.kernel.identity import _validate
from legoai.kernel.versions import Version


@dataclass(frozen=True, slots=True)
class PluginId:
    """Stable Plugin identity: namespace plus local identity (PLG-006).

    Identity does not derive from a package name, repository, executable
    path, artifact location, or deployment address -- both fields here are
    opaque accountable text, not a filesystem or import location.
    """

    namespace: str = field(repr=False)
    local_id: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.namespace)
        _validate(self.local_id)


@dataclass(frozen=True, slots=True)
class PluginDeclaration:
    """One immutable Plugin release's declared identity and Capability
    facts (PLG-004, PLG-009, PLG-011, PLG-040). Constructing this value
    performs no discovery, inspection side effect, validation report,
    admission, or activation (PLG-021-024) -- it is pure data.

    Duplicate offers for the exact same ``(capability, version)`` pair
    within one declaration are rejected as a contradictory/meaningless
    declaration (SS25 of this batch's task); two *different* versions of
    the same Capability from one release are permitted since PLUGIN-SPEC
    does not prohibit it and this value has no basis to invent that
    restriction.
    """

    plugin_id: PluginId
    release: Version
    offers: tuple[CapabilityOffer, ...] = field(default_factory=tuple)
    requirements: tuple[CapabilityRequirement, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if type(self.plugin_id) is not PluginId:
            raise TypeError("declaration requires PluginId")
        if type(self.release) is not Version:
            raise TypeError("declaration requires a release Version")
        if type(self.offers) is not tuple or any(
            type(offer) is not CapabilityOffer for offer in self.offers
        ):
            raise TypeError("offers must be an immutable tuple of CapabilityOffer")
        if type(self.requirements) is not tuple or any(
            type(requirement) is not CapabilityRequirement
            for requirement in self.requirements
        ):
            raise TypeError(
                "requirements must be an immutable tuple of CapabilityRequirement"
            )
        seen: set[tuple[CapabilityId, Version]] = set()
        for offer in self.offers:
            key = (offer.capability, offer.version)
            if key in seen:
                raise ValueError("duplicate offer for the same capability and version")
            seen.add(key)
