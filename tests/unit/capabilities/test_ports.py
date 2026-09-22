"""Gate-2 M6: ADR-006 SS9 -- Catalog entries describe published/eligible
Capability offers; presence never means authorized, resource-available, or
trusted for dispatch.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime
from typing import cast, get_type_hints

import pytest

from legoai.capabilities.ports import CatalogEntry, CatalogSnapshot
from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import TenantId
from legoai.kernel.versions import Version
from legoai.plugins.ports import PluginAdmissionId
from legoai.plugins.values import PluginId

FORBIDDEN_RUNTIME_FIELDS = {
    "authorized",
    "approved",
    "available",
    "resource_available",
    "trusted",
    "active",
    "callable",
    "handler",
    "adapter",
    "provider",
    "factory",
    "connection",
    "instance",
    "secret",
    "credential",
}

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _entry(*, tenant: str = "tenant") -> CatalogEntry:
    return CatalogEntry(
        PluginId("legoai", "deterministic-fixture"),
        Version(0, 1, 0),
        CapabilityOffer(CapabilityId("text-normalize"), Version(1, 0, 0)),
        TenantContext(TenantId(tenant)),
        PluginAdmissionId("admission-1"),
        _EPOCH,
    )


# --- CatalogEntry ---------------------------------------------------------------


def test_catalog_entry_valid_construction() -> None:
    entry = _entry()
    assert entry == replace(entry)


def test_catalog_entry_published_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(_entry(), published_at=datetime(2026, 1, 1))


@pytest.mark.parametrize("invalid", ["2026-01-01", 1, True, [], {}, lambda: None])
def test_catalog_entry_published_at_rejects_non_datetime(invalid: object) -> None:
    with pytest.raises(TypeError, match="must be datetime"):
        replace(_entry(), published_at=cast(datetime, invalid))


@pytest.mark.parametrize(
    "field_name",
    ["plugin_id", "release", "offer", "tenant_context", "admission_id"],
)
def test_catalog_entry_required_fields_reject_wrong_type(field_name: str) -> None:
    entry = _entry()
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, lambda: None, None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(entry, **{field_name: invalid})


def test_catalog_entry_rejects_callable_and_arbitrary_object_binding() -> None:
    entry = _entry()
    canaries: tuple[object, ...] = (lambda: None, object(), print, {"k": "v"})
    for field_name in ("plugin_id", "offer", "tenant_context", "admission_id"):
        for canary in canaries:
            with pytest.raises(TypeError):
                cast(Callable[..., object], replace)(entry, **{field_name: canary})


def test_catalog_entry_has_no_authorization_or_availability_shortcut() -> None:
    names = {f.name for f in fields(CatalogEntry)}
    assert names.isdisjoint(FORBIDDEN_RUNTIME_FIELDS)
    assert not any(hasattr(_entry(), attr) for attr in FORBIDDEN_RUNTIME_FIELDS)


def test_catalog_entry_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(CatalogEntry)
    for name, hint in hints.items():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object
        assert "Any" not in str(hint), f"{name} must not accept typing.Any"


def test_catalog_entry_immutable_and_stable_hash() -> None:
    entry = _entry()
    original_hash = hash(entry)
    assert not hasattr(entry, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(entry, "release", Version(9, 9, 9))  # noqa: B010
    assert hash(entry) == original_hash


# --- CatalogSnapshot -----------------------------------------------------------


def test_catalog_snapshot_valid_construction() -> None:
    snapshot = CatalogSnapshot(1, TenantContext(TenantId("tenant")), (_entry(),))
    assert snapshot.revision == 1
    assert snapshot.entries == (_entry(),)


def test_catalog_snapshot_allows_empty_entries_and_zero_revision() -> None:
    snapshot = CatalogSnapshot(0, TenantContext(TenantId("tenant")))
    assert snapshot.entries == ()


def test_catalog_snapshot_revision_must_be_nonnegative() -> None:
    with pytest.raises(ValueError, match="nonnegative"):
        CatalogSnapshot(-1, TenantContext(TenantId("tenant")))


@pytest.mark.parametrize("invalid", ["raw", 1, True, [], {}, lambda: None, None])
def test_catalog_snapshot_rejects_wrong_type_tenant_context(invalid: object) -> None:
    with pytest.raises(TypeError, match="requires TenantContext"):
        CatalogSnapshot(0, cast(TenantContext, invalid))


@pytest.mark.parametrize("revision", [True, False, 1.0, "1", None])
def test_catalog_snapshot_revision_rejects_non_int(revision: object) -> None:
    with pytest.raises(TypeError, match="must be an int"):
        CatalogSnapshot(cast(int, revision), TenantContext(TenantId("tenant")))


def test_catalog_snapshot_entries_must_be_tuple_of_catalog_entry() -> None:
    with pytest.raises(TypeError, match="immutable tuple"):
        CatalogSnapshot(
            0,
            TenantContext(TenantId("tenant")),
            cast(tuple[CatalogEntry, ...], [_entry()]),
        )
    with pytest.raises(TypeError, match="immutable tuple"):
        CatalogSnapshot(
            0,
            TenantContext(TenantId("tenant")),
            cast(tuple[CatalogEntry, ...], (object(),)),
        )


def test_catalog_snapshot_immutable() -> None:
    snapshot = CatalogSnapshot(1, TenantContext(TenantId("tenant")))
    with pytest.raises(FrozenInstanceError):
        setattr(snapshot, "revision", 2)  # noqa: B010


def test_catalog_entry_does_not_embed_runtime_handle() -> None:
    entry = _entry()
    assert not hasattr(entry, "instance")
    assert not hasattr(entry, "handler")
    assert not hasattr(entry, "connection")
