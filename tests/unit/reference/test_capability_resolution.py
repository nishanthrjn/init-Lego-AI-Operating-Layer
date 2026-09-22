"""Gate-2 M7: runtime Capability resolution over published, tenant-scoped
Catalog state (ADR-002's `legoai.reference.resolution` "Resolution
snapshots/closure/results" row). A `RESOLVED` result means only that one
published offer satisfies the requirement under this resolver's semantics
-- never that the caller may invoke it, that resources are available, or
that current authority has been checked.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime
from typing import cast, get_type_hints

import pytest

from legoai.capabilities.ports import CatalogEntry, CatalogSnapshot
from legoai.capabilities.values import (
    CapabilityId,
    CapabilityOffer,
    CapabilityRequirement,
    CapabilityVersionRange,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import TenantId
from legoai.kernel.versions import Version
from legoai.plugins.ports import PluginAdmissionId
from legoai.plugins.values import PluginDeclaration, PluginId
from legoai.reference.resolution import (
    CapabilityResolution,
    ResolutionStatus,
    analyze_compatibility,
    resolve,
)

FORBIDDEN_RUNTIME_FIELDS = {
    "authorized",
    "approved",
    "trusted",
    "grant",
    "approval",
    "available",
    "reserved",
    "capacity",
    "callable",
    "handler",
    "adapter",
    "provider",
    "factory",
    "instance",
    "connection",
}

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)
TEXT_NORMALIZE = CapabilityId("text.normalize")


def _requirement(
    minimum: Version | None = None, maximum: Version | None = None
) -> CapabilityRequirement:
    return CapabilityRequirement(
        TEXT_NORMALIZE,
        CapabilityVersionRange(minimum or Version(1, 0, 0), True, maximum, True),
    )


def _entry(
    *,
    namespace: str = "legoai",
    local_id: str = "fixture",
    tenant: str = "tenant",
    offer_version: Version | None = None,
    capability: CapabilityId = TEXT_NORMALIZE,
) -> CatalogEntry:
    return CatalogEntry(
        PluginId(namespace, local_id),
        Version(0, 1, 0),
        CapabilityOffer(capability, offer_version or Version(1, 0, 0)),
        TenantContext(TenantId(tenant)),
        PluginAdmissionId("admission-1"),
        _EPOCH,
    )


def _snapshot(
    entries: tuple[CatalogEntry, ...], *, revision: int = 1, tenant: str = "tenant"
) -> CatalogSnapshot:
    return CatalogSnapshot(revision, TenantContext(TenantId(tenant)), entries)


# --- ResolutionStatus ---------------------------------------------------------


def test_resolution_status_exact_three_members() -> None:
    assert {m.value for m in ResolutionStatus} == {"no_match", "resolved", "ambiguous"}


# --- resolve(): unique / no-match / ambiguous -----------------------------------


def test_resolve_unique_candidate() -> None:
    entry = _entry()
    snapshot = _snapshot((entry,))
    resolution = resolve(_requirement(), snapshot, resolved_at=_EPOCH)
    assert resolution.status is ResolutionStatus.RESOLVED
    assert resolution.candidates == (entry,)
    assert resolution.catalog_revision == 1
    assert resolution.tenant_context == snapshot.tenant_context


def test_resolve_no_match_when_catalog_empty() -> None:
    resolution = resolve(_requirement(), _snapshot(()), resolved_at=_EPOCH)
    assert resolution.status is ResolutionStatus.NO_MATCH
    assert resolution.candidates == ()


def test_resolve_no_match_does_not_fall_back_outside_range() -> None:
    entry = _entry(offer_version=Version(0, 9, 0))
    resolution = resolve(_requirement(), _snapshot((entry,)), resolved_at=_EPOCH)
    assert resolution.status is ResolutionStatus.NO_MATCH


def test_resolve_no_match_wrong_capability() -> None:
    entry = _entry(capability=CapabilityId("other.capability"))
    resolution = resolve(_requirement(), _snapshot((entry,)), resolved_at=_EPOCH)
    assert resolution.status is ResolutionStatus.NO_MATCH


def test_resolve_ambiguous_preserves_all_candidates_no_selection() -> None:
    entry_a = _entry(local_id="provider-a")
    entry_b = _entry(local_id="provider-b")
    resolution = resolve(
        _requirement(), _snapshot((entry_a, entry_b)), resolved_at=_EPOCH
    )
    assert resolution.status is ResolutionStatus.AMBIGUOUS
    assert len(resolution.candidates) == 2
    assert set(resolution.candidates) == {entry_a, entry_b}


def test_resolve_ambiguous_with_multiple_compatible_versions_no_ranking() -> None:
    lower = _entry(local_id="a", offer_version=Version(1, 0, 0))
    higher = _entry(local_id="a", offer_version=Version(1, 5, 0))
    resolution = resolve(_requirement(), _snapshot((lower, higher)), resolved_at=_EPOCH)
    assert resolution.status is ResolutionStatus.AMBIGUOUS
    # Neither the higher version nor the "first" entry is silently preferred.
    assert set(resolution.candidates) == {lower, higher}


def test_resolve_same_plugin_multiple_offers_both_counted_if_both_match() -> None:
    same_plugin_two_offers = (
        _entry(local_id="multi", offer_version=Version(1, 0, 0)),
        _entry(local_id="multi", offer_version=Version(1, 1, 0)),
    )
    resolution = resolve(
        _requirement(), _snapshot(same_plugin_two_offers), resolved_at=_EPOCH
    )
    assert resolution.status is ResolutionStatus.AMBIGUOUS
    assert len(resolution.candidates) == 2


# --- version-range exactness -----------------------------------------------------


def test_resolve_rejects_version_outside_upper_bound() -> None:
    requirement = _requirement(Version(1, 0, 0), Version(1, 5, 0))
    entry = _entry(offer_version=Version(2, 0, 0))
    resolution = resolve(requirement, _snapshot((entry,)), resolved_at=_EPOCH)
    assert resolution.status is ResolutionStatus.NO_MATCH


def test_resolve_accepts_version_within_bounds() -> None:
    requirement = _requirement(Version(1, 0, 0), Version(1, 5, 0))
    entry = _entry(offer_version=Version(1, 5, 0))
    resolution = resolve(requirement, _snapshot((entry,)), resolved_at=_EPOCH)
    assert resolution.status is ResolutionStatus.RESOLVED


# --- tenant isolation ------------------------------------------------------------


def test_resolve_ignores_entries_from_other_tenant_defense_in_depth() -> None:
    # Even though CatalogSnapshot is already tenant-scoped by construction,
    # resolve() defensively validates every candidate's tenant (task SS40).
    other_tenant_entry = _entry(tenant="other-tenant")
    with pytest.raises(ValueError, match="tenant does not match"):
        # Constructing a snapshot that (incorrectly) claims tenant "tenant"
        # while holding an "other-tenant" entry must be rejected by the
        # resolution's own defensive validation, not silently accepted.
        CapabilityResolution(
            _requirement(),
            TenantContext(TenantId("tenant")),
            ResolutionStatus.RESOLVED,
            (other_tenant_entry,),
            1,
            _EPOCH,
        )


def test_resolve_same_capability_different_tenant_not_visible() -> None:
    tenant_a_entry = _entry(tenant="tenant-a")
    snapshot_b = _snapshot((), tenant="tenant-b")
    resolution = resolve(_requirement(), snapshot_b, resolved_at=_EPOCH)
    assert resolution.status is ResolutionStatus.NO_MATCH
    assert tenant_a_entry not in resolution.candidates


# --- deterministic ordering -------------------------------------------------------


def test_resolve_ordering_independent_of_insertion_order() -> None:
    entry_a = _entry(local_id="zzz-last")
    entry_b = _entry(local_id="aaa-first")
    first = resolve(_requirement(), _snapshot((entry_a, entry_b)), resolved_at=_EPOCH)
    second = resolve(_requirement(), _snapshot((entry_b, entry_a)), resolved_at=_EPOCH)
    assert [c.plugin_id.local_id for c in first.candidates] == [
        c.plugin_id.local_id for c in second.candidates
    ]
    assert [c.plugin_id.local_id for c in first.candidates] == ["aaa-first", "zzz-last"]


# --- exactness / attribution -------------------------------------------------------


def test_resolve_preserves_exact_release_and_offer_version() -> None:
    entry = _entry(offer_version=Version(1, 2, 3))
    resolution = resolve(_requirement(), _snapshot((entry,)), resolved_at=_EPOCH)
    assert resolution.candidates[0].release == Version(0, 1, 0)
    assert resolution.candidates[0].offer.version == Version(1, 2, 3)


def test_resolve_carries_exact_catalog_revision() -> None:
    entry = _entry()
    resolution = resolve(
        _requirement(), _snapshot((entry,), revision=42), resolved_at=_EPOCH
    )
    assert resolution.catalog_revision == 42


def test_resolve_repeatable_given_identical_inputs() -> None:
    entry = _entry()
    snapshot = _snapshot((entry,))
    first = resolve(_requirement(), snapshot, resolved_at=_EPOCH)
    second = resolve(_requirement(), snapshot, resolved_at=_EPOCH)
    assert first == second


# --- static (F7) vs runtime (M7) distinction ------------------------------------


def test_runtime_resolve_is_not_equivalent_to_static_analyze_compatibility() -> None:
    # An arbitrary declaration never published to any Catalog is visible to
    # F7's analyze_compatibility (it only needs a declaration, not
    # publication) but invisible to M7's resolve() (published-only, tenant-
    # scoped). This is the concrete difference the module docstring names.
    unpublished_declaration = PluginDeclaration(
        PluginId("legoai", "unpublished"),
        Version(0, 1, 0),
        (CapabilityOffer(TEXT_NORMALIZE, Version(1, 0, 0)),),
        (),
    )
    static_analysis = analyze_compatibility(_requirement(), (unpublished_declaration,))
    assert static_analysis.candidates != ()  # F7 sees it: no publication needed

    empty_catalog_snapshot = _snapshot(())
    runtime_resolution = resolve(
        _requirement(), empty_catalog_snapshot, resolved_at=_EPOCH
    )
    assert runtime_resolution.status is ResolutionStatus.NO_MATCH  # M7 does not


# --- no dispatch/authorization/resource shortcuts --------------------------------


def test_capability_resolution_has_no_authorization_or_resource_or_executable_field() -> (
    None
):
    names = {f.name for f in fields(CapabilityResolution)}
    assert names.isdisjoint(FORBIDDEN_RUNTIME_FIELDS)
    resolution = resolve(_requirement(), _snapshot((_entry(),)), resolved_at=_EPOCH)
    assert not any(hasattr(resolution, attr) for attr in FORBIDDEN_RUNTIME_FIELDS)
    for candidate in resolution.candidates:
        assert not any(hasattr(candidate, attr) for attr in FORBIDDEN_RUNTIME_FIELDS)


def test_capability_resolution_result_is_not_callable_and_has_no_dispatch_method() -> (
    None
):
    resolution = resolve(_requirement(), _snapshot((_entry(),)), resolved_at=_EPOCH)
    assert not callable(resolution)
    for name in ("invoke", "execute", "dispatch", "call_provider", "activate"):
        assert not hasattr(resolution, name)


def test_capability_resolution_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(CapabilityResolution)
    for name, hint in hints.items():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object
        assert "Any" not in str(hint), f"{name} must not accept typing.Any"


def test_capability_resolution_rejects_callable_and_arbitrary_object_binding() -> None:
    resolution = resolve(_requirement(), _snapshot((_entry(),)), resolved_at=_EPOCH)
    canaries: tuple[object, ...] = (lambda: None, object(), print, {"k": "v"})
    for field_name in ("requirement", "tenant_context", "status"):
        for canary in canaries:
            with pytest.raises(TypeError):
                cast(Callable[..., object], replace)(resolution, **{field_name: canary})


# --- structural validation --------------------------------------------------------


def test_resolve_rejects_wrong_type_arguments() -> None:
    with pytest.raises(TypeError, match="CapabilityRequirement"):
        resolve(object(), _snapshot(()), resolved_at=_EPOCH)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="CatalogSnapshot"):
        resolve(_requirement(), object(), resolved_at=_EPOCH)  # type: ignore[arg-type]


def test_resolve_resolved_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        resolve(
            _requirement(), _snapshot((_entry(),)), resolved_at=datetime(2026, 1, 1)
        )


@pytest.mark.parametrize("invalid", ["2026-01-01", 1, True, [], {}, lambda: None])
def test_resolve_resolved_at_rejects_non_datetime(invalid: object) -> None:
    with pytest.raises(TypeError, match="must be datetime"):
        resolve(
            _requirement(), _snapshot((_entry(),)), resolved_at=cast(datetime, invalid)
        )


def test_capability_resolution_rejects_wrong_candidate_count_for_status() -> None:
    entry = _entry()
    with pytest.raises(ValueError, match="requires exactly"):
        CapabilityResolution(
            _requirement(),
            TenantContext(TenantId("tenant")),
            ResolutionStatus.NO_MATCH,
            (entry,),
            1,
            _EPOCH,
        )
    with pytest.raises(ValueError, match="requires exactly"):
        CapabilityResolution(
            _requirement(),
            TenantContext(TenantId("tenant")),
            ResolutionStatus.RESOLVED,
            (),
            1,
            _EPOCH,
        )
    with pytest.raises(ValueError, match="at least two"):
        CapabilityResolution(
            _requirement(),
            TenantContext(TenantId("tenant")),
            ResolutionStatus.AMBIGUOUS,
            (entry,),
            1,
            _EPOCH,
        )


def test_capability_resolution_rejects_candidate_mismatching_requirement() -> None:
    wrong_capability_entry = _entry(capability=CapabilityId("other"))
    with pytest.raises(ValueError, match="capability does not match"):
        CapabilityResolution(
            _requirement(),
            TenantContext(TenantId("tenant")),
            ResolutionStatus.RESOLVED,
            (wrong_capability_entry,),
            1,
            _EPOCH,
        )
    out_of_range_entry = _entry(offer_version=Version(0, 1, 0))
    with pytest.raises(ValueError, match="does not satisfy requirement range"):
        CapabilityResolution(
            _requirement(),
            TenantContext(TenantId("tenant")),
            ResolutionStatus.RESOLVED,
            (out_of_range_entry,),
            1,
            _EPOCH,
        )


def test_capability_resolution_rejects_wrong_type_candidates() -> None:
    with pytest.raises(TypeError, match="immutable tuple of CatalogEntry"):
        CapabilityResolution(
            _requirement(),
            TenantContext(TenantId("tenant")),
            ResolutionStatus.NO_MATCH,
            cast(tuple[CatalogEntry, ...], [_entry()]),
            1,
            _EPOCH,
        )
    with pytest.raises(TypeError, match="immutable tuple of CatalogEntry"):
        CapabilityResolution(
            _requirement(),
            TenantContext(TenantId("tenant")),
            ResolutionStatus.NO_MATCH,
            cast(tuple[CatalogEntry, ...], (object(),)),
            1,
            _EPOCH,
        )


@pytest.mark.parametrize("invalid", [True, False, 1.0, "1", None])
def test_capability_resolution_catalog_revision_rejects_non_int(
    invalid: object,
) -> None:
    with pytest.raises(TypeError, match="must be an int"):
        CapabilityResolution(
            _requirement(),
            TenantContext(TenantId("tenant")),
            ResolutionStatus.NO_MATCH,
            (),
            cast(int, invalid),
            _EPOCH,
        )


@pytest.mark.parametrize("invalid", ["2026-01-01", 1, True, [], {}, lambda: None])
def test_capability_resolution_resolved_at_rejects_non_datetime(
    invalid: object,
) -> None:
    with pytest.raises(TypeError, match="must be datetime"):
        CapabilityResolution(
            _requirement(),
            TenantContext(TenantId("tenant")),
            ResolutionStatus.NO_MATCH,
            (),
            1,
            cast(datetime, invalid),
        )


def test_capability_resolution_resolved_at_must_be_timezone_aware_when_constructed_directly() -> (
    None
):
    with pytest.raises(ValueError, match="timezone-aware"):
        CapabilityResolution(
            _requirement(),
            TenantContext(TenantId("tenant")),
            ResolutionStatus.NO_MATCH,
            (),
            1,
            datetime(2026, 1, 1),
        )


def test_capability_resolution_catalog_revision_must_be_nonnegative() -> None:
    with pytest.raises(ValueError, match="nonnegative"):
        CapabilityResolution(
            _requirement(),
            TenantContext(TenantId("tenant")),
            ResolutionStatus.NO_MATCH,
            (),
            -1,
            _EPOCH,
        )


def test_capability_resolution_immutable_and_stable_hash() -> None:
    resolution = resolve(_requirement(), _snapshot((_entry(),)), resolved_at=_EPOCH)
    original_hash = hash(resolution)
    assert not hasattr(resolution, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(resolution, "status", ResolutionStatus.NO_MATCH)  # noqa: B010
    assert hash(resolution) == original_hash
