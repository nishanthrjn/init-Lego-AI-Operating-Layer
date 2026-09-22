"""Gate-2 M6: deterministic in-memory reference realization of `CatalogPort`.

No persistence, no filesystem/network I/O, no background refresh/watcher
task, no asyncio. `InMemoryCatalog` guards its internal list only against
the ordinary single-threaded call sequence a reference/test process makes;
it makes **no concurrency or thread-safety claim** (task SS36) -- a later
persisted realization (ADR-004-style, mirroring F6a's SQLite store) would
own that guarantee against its own storage, not this value's shape.

`revision` is a simple in-memory monotonic counter shared across all
tenants for attribution/ordering only -- it is not, and must never be
mistaken for, an ADR-004 expected-revision concurrency guard (the same
scope limitation already accepted for M5's `PluginLifecycleRecord.revision`
and M3/M2's deferred Budget/Quota/revocation-store persistence). Because it
is only an opaque ordering counter and never appears in `CatalogSnapshot`
except as an attribution field, publishing to Tenant A's catalog never
discloses Tenant B's entries: `snapshot`/`query` filter strictly by the
tenant supplied by the caller.
"""

from datetime import datetime

from legoai.capabilities.ports import (
    CatalogEntry,
    CatalogPublicationError,
    CatalogSnapshot,
)
from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.kernel.context import TenantContext
from legoai.kernel.versions import Version
from legoai.plugins.ports import PluginLifecycleRecord, PluginLifecycleState
from legoai.plugins.values import PluginDeclaration, PluginId


def _entry_sort_key(
    entry: CatalogEntry,
) -> tuple[str, str, int, int, int, str, int, int, int]:
    return (
        entry.plugin_id.namespace,
        entry.plugin_id.local_id,
        entry.release.major,
        entry.release.minor,
        entry.release.patch,
        entry.offer.capability.value,
        entry.offer.version.major,
        entry.offer.version.minor,
        entry.offer.version.patch,
    )


class InMemoryCatalog:
    """Deterministic reference `CatalogPort` realization. Construction
    publishes nothing and holds an empty entry list.
    """

    def __init__(self) -> None:
        self._entries: list[CatalogEntry] = []
        self._revision = 0

    def publish(
        self,
        record: PluginLifecycleRecord,
        declaration: PluginDeclaration,
        offer: CapabilityOffer,
        *,
        established_at: datetime,
    ) -> CatalogEntry:
        if type(record) is not PluginLifecycleRecord:
            raise TypeError("publish requires PluginLifecycleRecord")
        if type(declaration) is not PluginDeclaration:
            raise TypeError("publish requires PluginDeclaration")
        if type(offer) is not CapabilityOffer:
            raise TypeError("publish requires CapabilityOffer")
        if record.state is not PluginLifecycleState.ACTIVE:
            raise CatalogPublicationError(
                f"lifecycle state {record.state.value} is not publication-eligible"
            )
        if (
            record.plugin_id != declaration.plugin_id
            or record.release != declaration.release
        ):
            raise CatalogPublicationError(
                "lifecycle record does not correspond to the declaration"
            )
        if offer not in declaration.offers:
            raise CatalogPublicationError(
                "offer is not present in the given declaration"
            )
        entry = CatalogEntry(
            declaration.plugin_id,
            declaration.release,
            offer,
            record.tenant_context,
            record.admission_id,
            established_at,
        )
        for existing in self._entries:
            if (
                existing.plugin_id == entry.plugin_id
                and existing.release == entry.release
                and existing.offer == entry.offer
                and existing.tenant_context == entry.tenant_context
            ):
                raise CatalogPublicationError("exact entry is already published")
        self._entries.append(entry)
        self._revision += 1
        return entry

    def withdraw(
        self,
        plugin_id: PluginId,
        release: Version,
        offer: CapabilityOffer,
        tenant_context: TenantContext,
    ) -> None:
        if type(plugin_id) is not PluginId:
            raise TypeError("withdraw requires PluginId")
        if type(release) is not Version:
            raise TypeError("withdraw requires a release Version")
        if type(offer) is not CapabilityOffer:
            raise TypeError("withdraw requires CapabilityOffer")
        if type(tenant_context) is not TenantContext:
            raise TypeError("withdraw requires TenantContext")
        remaining = [
            entry
            for entry in self._entries
            if not (
                entry.plugin_id == plugin_id
                and entry.release == release
                and entry.offer == offer
                and entry.tenant_context == tenant_context
            )
        ]
        if len(remaining) == len(self._entries):
            raise CatalogPublicationError("no matching published entry to withdraw")
        self._entries = remaining
        self._revision += 1

    def snapshot(self, tenant_context: TenantContext) -> CatalogSnapshot:
        if type(tenant_context) is not TenantContext:
            raise TypeError("snapshot requires TenantContext")
        scoped = tuple(
            sorted(
                (e for e in self._entries if e.tenant_context == tenant_context),
                key=_entry_sort_key,
            )
        )
        return CatalogSnapshot(self._revision, tenant_context, scoped)

    def query(
        self, tenant_context: TenantContext, capability: CapabilityId
    ) -> tuple[CatalogEntry, ...]:
        if type(tenant_context) is not TenantContext:
            raise TypeError("query requires TenantContext")
        if type(capability) is not CapabilityId:
            raise TypeError("query requires CapabilityId")
        matching = (
            entry
            for entry in self._entries
            if entry.tenant_context == tenant_context
            and entry.offer.capability == capability
        )
        return tuple(sorted(matching, key=_entry_sort_key))
