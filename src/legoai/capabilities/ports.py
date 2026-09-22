"""Gate-2 M6: Catalog operation request/result values and the `CatalogPort`
Protocol (ADR-002's `ports.py` category; ADR-002 line 176: "Catalog records
and scoped offer/eligibility projections | C row; own Catalog Port").

Preserve throughout (ADR-006 SS9; task SS2/SS4/SS5):

    Plugin lifecycle state != Catalog publication != Capability resolution
    != authorization != executable binding

Catalog presence means "published and eligible for consideration" -- never
"authorized for this caller", "resource-available", "trusted", or "safe to
dispatch". `CatalogEntry` carries no callable, provider instance, adapter,
factory, connection, or runtime handle; it is exactly as inert as the
`PluginDeclaration`/`CapabilityOffer` it republishes (ADR-002 SS9.2's C-row
permits importing X/Plugins precisely so this attribution can be preserved
structurally, per `CapabilityOffer`'s own docstring: "Attribution to the
declaring Plugin/release is structural ... never duplicated here").

Publication eligibility (ADR-006 SS9: "Ordinary eligibility requires an
active activation, or a degraded activation whose contributions still meet
every hard requirement, plus current suitability and required evidence"):
this batch's reference realization supports only the unconditional case --
`PluginLifecycleState.ACTIVE`. `DEGRADED` eligibility additionally requires
a "hard requirement"/"current suitability"/"required evidence" check this
Gate-2 batch has no accepted typed representation for yet (Evidence custody
is explicitly M8); admitting `DEGRADED` here would either fabricate that
missing check or silently treat "degraded" as unconditionally eligible,
neither of which this batch is authorized to do. `DEGRADED` publication is
therefore an explicit, documented gap for a later batch, not a silent
omission.

No `CapabilityResolver`, ranking, or selection lives here (M7's job): a
query returns every matching entry in a stable but non-preferential order,
and multiple Plugins offering the identical Capability are all preserved.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.kernel.context import TenantContext
from legoai.kernel.versions import Version
from legoai.plugins.ports import PluginAdmissionId, PluginLifecycleRecord
from legoai.plugins.values import PluginDeclaration, PluginId


class CatalogPublicationError(ValueError):
    """A publish/withdraw request cannot be satisfied structurally: an
    ineligible lifecycle state, a plugin_id/release mismatch between the
    lifecycle record and the declaration, an offer not actually present in
    that declaration, or an exact duplicate publication. Not itself a
    Plugin failure category -- a caller precondition violation, mirroring
    `plugins.ports.LifecycleTransitionError`'s role for M5.
    """


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """One immutable published Capability offer, attributed to its exact
    declaring Plugin/release and admission (task SS9/SS10/SS42). Never a
    callable, provider instance, adapter, factory, connection, or runtime
    handle -- publication is descriptive, not activation, resolution, or
    authorization.
    """

    plugin_id: PluginId
    release: Version
    offer: CapabilityOffer
    tenant_context: TenantContext
    admission_id: PluginAdmissionId
    published_at: datetime

    def __post_init__(self) -> None:
        if type(self.plugin_id) is not PluginId:
            raise TypeError("catalog entry requires PluginId")
        if type(self.release) is not Version:
            raise TypeError("catalog entry requires a release Version")
        if type(self.offer) is not CapabilityOffer:
            raise TypeError("catalog entry requires CapabilityOffer")
        if type(self.tenant_context) is not TenantContext:
            raise TypeError("catalog entry requires TenantContext")
        if type(self.admission_id) is not PluginAdmissionId:
            raise TypeError("catalog entry requires PluginAdmissionId")
        if type(self.published_at) is not datetime:
            raise TypeError("catalog entry published_at must be datetime")
        if self.published_at.tzinfo is None:
            raise ValueError("catalog entry published_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    """An immutable, exact-revision view of one tenant's currently
    published entries. `entries` ordering is deterministic for stability
    only -- it is never a preference/ranking signal (task SS27/SS26; M7
    owns resolution).
    """

    revision: int
    tenant_context: TenantContext
    entries: tuple[CatalogEntry, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if type(self.revision) is not int or isinstance(self.revision, bool):
            raise TypeError("catalog snapshot revision must be an int")
        if self.revision < 0:
            raise ValueError("catalog snapshot revision must be nonnegative")
        if type(self.tenant_context) is not TenantContext:
            raise TypeError("catalog snapshot requires TenantContext")
        if type(self.entries) is not tuple or any(
            type(entry) is not CatalogEntry for entry in self.entries
        ):
            raise TypeError("catalog snapshot entries must be an immutable tuple")


class CatalogPort(Protocol):
    """The Catalog owner's exact operations (ADR-006 SS9). No generic
    `register(obj)`/`get(name)`/`all()`: every method names the precise
    Catalog responsibility it performs.
    """

    def publish(
        self,
        record: PluginLifecycleRecord,
        declaration: PluginDeclaration,
        offer: CapabilityOffer,
        *,
        established_at: datetime,
    ) -> CatalogEntry: ...

    def withdraw(
        self,
        plugin_id: PluginId,
        release: Version,
        offer: CapabilityOffer,
        tenant_context: TenantContext,
    ) -> None: ...

    def snapshot(self, tenant_context: TenantContext) -> CatalogSnapshot: ...

    def query(
        self, tenant_context: TenantContext, capability: CapabilityId
    ) -> tuple[CatalogEntry, ...]: ...
