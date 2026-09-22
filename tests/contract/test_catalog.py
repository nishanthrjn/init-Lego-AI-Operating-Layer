"""Gate-2 M6 contract suite for `CatalogPort` (ADR-006 SS9): only an active
lifecycle publishes; publication is inert; multiple providers of the same
Capability are all preserved; M6 never ranks or selects (M7's job).

Parametrized over realization factories so a later alternative `CatalogPort`
implementation can be added to `REALIZATION_FACTORIES` without duplicating
these cases.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

import pytest

from legoai.capabilities.ports import CatalogPort, CatalogPublicationError
from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import TenantId
from legoai.kernel.versions import Version
from legoai.plugins.ports import (
    PluginAdmissionId,
    PluginLifecycleRecord,
    PluginLifecycleState,
)
from legoai.plugins.values import PluginDeclaration, PluginId
from legoai.reference.catalog import InMemoryCatalog

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _build_in_memory() -> CatalogPort:
    return InMemoryCatalog()


REALIZATION_FACTORIES: tuple[Callable[[], CatalogPort], ...] = (_build_in_memory,)


def _tenant(name: str = "tenant") -> TenantContext:
    return TenantContext(TenantId(name))


def _declaration(
    namespace: str = "legoai",
    local_id: str = "fixture",
    *,
    offers: tuple[CapabilityOffer, ...] = (),
) -> PluginDeclaration:
    return PluginDeclaration(
        PluginId(namespace, local_id), Version(0, 1, 0), offers, ()
    )


def _offer(
    capability: str = "text-normalize", version: Version | None = None
) -> CapabilityOffer:
    return CapabilityOffer(CapabilityId(capability), version or Version(1, 0, 0))


def _record(
    *, tenant: str = "tenant", plugin_id: PluginId, state: PluginLifecycleState
) -> PluginLifecycleRecord:
    return PluginLifecycleRecord(
        PluginAdmissionId("admission-1"),
        plugin_id,
        Version(0, 1, 0),
        TenantContext(TenantId(tenant)),
        state,
        1,
        _EPOCH,
    )


@pytest.mark.parametrize("factory", REALIZATION_FACTORIES)
class TestCatalogContract:
    def test_publish_active_declaration_becomes_visible(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        declaration = _declaration(offers=(offer,))
        record = _record(
            plugin_id=declaration.plugin_id, state=PluginLifecycleState.ACTIVE
        )
        entry = catalog.publish(record, declaration, offer, established_at=_EPOCH)
        snapshot = catalog.snapshot(_tenant())
        assert entry in snapshot.entries

    @pytest.mark.parametrize(
        "state",
        [
            PluginLifecycleState.DISCOVERED,
            PluginLifecycleState.VALIDATED,
            PluginLifecycleState.INITIALIZED,
            PluginLifecycleState.DEGRADED,
            PluginLifecycleState.STOPPING,
            PluginLifecycleState.FAILED,
            PluginLifecycleState.STOPPED,
            PluginLifecycleState.RETIRED,
        ],
    )
    def test_publish_rejects_every_non_active_state(
        self, factory: Callable[[], CatalogPort], state: PluginLifecycleState
    ) -> None:
        catalog = factory()
        offer = _offer()
        declaration = _declaration(offers=(offer,))
        record = _record(plugin_id=declaration.plugin_id, state=state)
        with pytest.raises(CatalogPublicationError, match="not publication-eligible"):
            catalog.publish(record, declaration, offer, established_at=_EPOCH)

    def test_publish_rejects_mismatched_declaration(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        declaration = _declaration(offers=(offer,))
        other_declaration = _declaration("legoai", "other", offers=(offer,))
        record = _record(
            plugin_id=declaration.plugin_id, state=PluginLifecycleState.ACTIVE
        )
        with pytest.raises(CatalogPublicationError, match="does not correspond"):
            catalog.publish(record, other_declaration, offer, established_at=_EPOCH)

    def test_publish_rejects_offer_not_in_declaration(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        declared_offer = _offer()
        undeclared_offer = _offer("other-capability")
        declaration = _declaration(offers=(declared_offer,))
        record = _record(
            plugin_id=declaration.plugin_id, state=PluginLifecycleState.ACTIVE
        )
        with pytest.raises(CatalogPublicationError, match="not present"):
            catalog.publish(
                record, declaration, undeclared_offer, established_at=_EPOCH
            )

    def test_exact_duplicate_publication_rejected(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        declaration = _declaration(offers=(offer,))
        record = _record(
            plugin_id=declaration.plugin_id, state=PluginLifecycleState.ACTIVE
        )
        catalog.publish(record, declaration, offer, established_at=_EPOCH)
        with pytest.raises(CatalogPublicationError, match="already published"):
            catalog.publish(record, declaration, offer, established_at=_EPOCH)

    def test_multiple_providers_of_same_capability_all_preserved(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        first_declaration = _declaration("legoai", "provider-a", offers=(offer,))
        second_declaration = _declaration("legoai", "provider-b", offers=(offer,))
        first_record = _record(
            plugin_id=first_declaration.plugin_id, state=PluginLifecycleState.ACTIVE
        )
        second_record = _record(
            plugin_id=second_declaration.plugin_id, state=PluginLifecycleState.ACTIVE
        )
        catalog.publish(first_record, first_declaration, offer, established_at=_EPOCH)
        catalog.publish(second_record, second_declaration, offer, established_at=_EPOCH)
        results = catalog.query(_tenant(), offer.capability)
        assert len(results) == 2
        assert {entry.plugin_id for entry in results} == {
            first_declaration.plugin_id,
            second_declaration.plugin_id,
        }

    def test_query_does_not_rank_or_select(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        newer_offer = _offer(version=Version(2, 0, 0))
        declaration = _declaration(offers=(offer, newer_offer))
        record = _record(
            plugin_id=declaration.plugin_id, state=PluginLifecycleState.ACTIVE
        )
        catalog.publish(record, declaration, offer, established_at=_EPOCH)
        catalog.publish(record, declaration, newer_offer, established_at=_EPOCH)
        results = catalog.query(_tenant(), offer.capability)
        assert len(results) == 2
        assert {r.offer.version for r in results} == {
            Version(1, 0, 0),
            Version(2, 0, 0),
        }

    def test_query_ordering_deterministic_regardless_of_insertion_order(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        offer = _offer()
        decl_a = _declaration("legoai", "zzz-last", offers=(offer,))
        decl_b = _declaration("legoai", "aaa-first", offers=(offer,))
        rec_a = _record(plugin_id=decl_a.plugin_id, state=PluginLifecycleState.ACTIVE)
        rec_b = _record(plugin_id=decl_b.plugin_id, state=PluginLifecycleState.ACTIVE)

        catalog_1 = factory()
        catalog_1.publish(rec_a, decl_a, offer, established_at=_EPOCH)
        catalog_1.publish(rec_b, decl_b, offer, established_at=_EPOCH)
        order_1 = [
            e.plugin_id.local_id for e in catalog_1.query(_tenant(), offer.capability)
        ]

        catalog_2 = factory()
        catalog_2.publish(rec_b, decl_b, offer, established_at=_EPOCH)
        catalog_2.publish(rec_a, decl_a, offer, established_at=_EPOCH)
        order_2 = [
            e.plugin_id.local_id for e in catalog_2.query(_tenant(), offer.capability)
        ]

        assert order_1 == order_2 == ["aaa-first", "zzz-last"]

    def test_tenant_isolation_no_cross_tenant_leak(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        declaration = _declaration(offers=(offer,))
        record_tenant_a = _record(
            plugin_id=declaration.plugin_id,
            state=PluginLifecycleState.ACTIVE,
            tenant="tenant-a",
        )
        catalog.publish(record_tenant_a, declaration, offer, established_at=_EPOCH)
        assert catalog.query(_tenant("tenant-a"), offer.capability) != ()
        assert catalog.query(_tenant("tenant-b"), offer.capability) == ()
        assert catalog.snapshot(_tenant("tenant-b")).entries == ()

    def test_withdraw_removes_entry_without_lifecycle_mutation(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        declaration = _declaration(offers=(offer,))
        record = _record(
            plugin_id=declaration.plugin_id, state=PluginLifecycleState.ACTIVE
        )
        catalog.publish(record, declaration, offer, established_at=_EPOCH)
        catalog.withdraw(declaration.plugin_id, declaration.release, offer, _tenant())
        assert catalog.snapshot(_tenant()).entries == ()
        assert record.state is PluginLifecycleState.ACTIVE

    def test_withdraw_nonexistent_entry_raises(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        declaration = _declaration(offers=(offer,))
        with pytest.raises(CatalogPublicationError, match="no matching"):
            catalog.withdraw(
                declaration.plugin_id, declaration.release, offer, _tenant()
            )

    def test_snapshot_revision_increases_on_publish_and_withdraw(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        declaration = _declaration(offers=(offer,))
        record = _record(
            plugin_id=declaration.plugin_id, state=PluginLifecycleState.ACTIVE
        )
        before = catalog.snapshot(_tenant()).revision
        catalog.publish(record, declaration, offer, established_at=_EPOCH)
        after_publish = catalog.snapshot(_tenant()).revision
        assert after_publish > before
        catalog.withdraw(declaration.plugin_id, declaration.release, offer, _tenant())
        after_withdraw = catalog.snapshot(_tenant()).revision
        assert after_withdraw > after_publish

    def test_publish_rejects_wrong_type_arguments(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        declaration = _declaration(offers=(offer,))
        record = _record(
            plugin_id=declaration.plugin_id, state=PluginLifecycleState.ACTIVE
        )
        with pytest.raises(TypeError, match="PluginLifecycleRecord"):
            catalog.publish(
                cast(PluginLifecycleRecord, object()),
                declaration,
                offer,
                established_at=_EPOCH,
            )
        with pytest.raises(TypeError, match="PluginDeclaration"):
            catalog.publish(
                record, cast(PluginDeclaration, object()), offer, established_at=_EPOCH
            )
        with pytest.raises(TypeError, match="CapabilityOffer"):
            catalog.publish(
                record,
                declaration,
                cast(CapabilityOffer, object()),
                established_at=_EPOCH,
            )

    def test_withdraw_rejects_wrong_type_arguments(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        declaration = _declaration(offers=(offer,))
        with pytest.raises(TypeError, match="PluginId"):
            catalog.withdraw(
                cast(PluginId, object()), declaration.release, offer, _tenant()
            )
        with pytest.raises(TypeError, match="release Version"):
            catalog.withdraw(
                declaration.plugin_id, cast(Version, object()), offer, _tenant()
            )
        with pytest.raises(TypeError, match="CapabilityOffer"):
            catalog.withdraw(
                declaration.plugin_id,
                declaration.release,
                cast(CapabilityOffer, object()),
                _tenant(),
            )
        with pytest.raises(TypeError, match="TenantContext"):
            catalog.withdraw(
                declaration.plugin_id,
                declaration.release,
                offer,
                cast(TenantContext, object()),
            )

    def test_snapshot_and_query_reject_wrong_type_arguments(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        with pytest.raises(TypeError, match="TenantContext"):
            catalog.snapshot(cast(TenantContext, object()))
        with pytest.raises(TypeError, match="TenantContext"):
            catalog.query(cast(TenantContext, object()), _offer().capability)
        with pytest.raises(TypeError, match="CapabilityId"):
            catalog.query(_tenant(), cast(CapabilityId, object()))

    def test_published_entry_is_inert_no_executable_binding(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        declaration = _declaration(offers=(offer,))
        record = _record(
            plugin_id=declaration.plugin_id, state=PluginLifecycleState.ACTIVE
        )
        entry = catalog.publish(record, declaration, offer, established_at=_EPOCH)
        for attr in (
            "provider",
            "callable",
            "handler",
            "adapter",
            "instance",
            "connection",
        ):
            assert not hasattr(entry, attr)
        assert not callable(entry)

    def test_catalog_presence_does_not_imply_authorization(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        declaration = _declaration(offers=(offer,))
        record = _record(
            plugin_id=declaration.plugin_id, state=PluginLifecycleState.ACTIVE
        )
        entry = catalog.publish(record, declaration, offer, established_at=_EPOCH)
        assert not hasattr(entry, "authorized")
        assert not hasattr(entry, "approved")

    def test_catalog_presence_does_not_imply_resource_availability(
        self, factory: Callable[[], CatalogPort]
    ) -> None:
        catalog = factory()
        offer = _offer()
        declaration = _declaration(offers=(offer,))
        record = _record(
            plugin_id=declaration.plugin_id, state=PluginLifecycleState.ACTIVE
        )
        entry = catalog.publish(record, declaration, offer, established_at=_EPOCH)
        assert not hasattr(entry, "resource_available")
        assert not hasattr(entry, "available")
