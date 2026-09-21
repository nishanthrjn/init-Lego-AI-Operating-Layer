"""Gate-2 M3: ADR-007 SS9 -- Resource values describe a declared requirement
or accounting fact; they never mean capacity exists, a reservation
succeeded, a quota is available, or a resource-policy decision was made.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal
from typing import cast, get_type_hints

import pytest

from legoai.kernel.context import TenantContext
from legoai.kernel.identity import ApplicationId, OperationId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    OperationRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.resources.values import (
    ResourceAmountKind,
    ResourceClaim,
    ResourceClaimId,
    ResourceDimension,
    ResourceQuantity,
)

FORBIDDEN_RUNTIME_FIELDS = {
    "authorized",
    "is_authorized",
    "approved",
    "is_approved",
    "trusted",
    "admin",
    "available",
    "capacity_available",
    "reserved",
    "is_reserved",
    "unlimited",
    "grant",
    "approval",
    "policy",
}


def _operation(tenant: str, operation: str) -> OperationRef:
    return OperationRef(
        ConfigurationRef(
            ApplicationRef(
                ReferenceScope("composition", TenantId(tenant)), ApplicationId("app")
            ),
            "config",
        ),
        OperationId(operation),
        "configuration",
    )


def _quantity(
    *,
    magnitude: Decimal = Decimal("1"),
    kind: ResourceAmountKind = ResourceAmountKind.BOUND,
) -> ResourceQuantity:
    return ResourceQuantity(
        ResourceDimension("compute-seconds"),
        "second",
        Version(1, 0, 0),
        kind,
        magnitude,
    )


def _claim(*, tenant: str = "tenant", operation: str = "op") -> ResourceClaim:
    return ResourceClaim(
        ResourceClaimId("claim-1"),
        _operation(tenant, operation),
        TenantContext(TenantId(tenant)),
        _quantity(),
    )


# --- ResourceDimension -------------------------------------------------------


def test_resource_dimension_valid_and_opaque() -> None:
    value = ResourceDimension("compute-seconds")
    assert value == ResourceDimension("compute-seconds")
    assert "compute-seconds" not in repr(value)


@pytest.mark.parametrize("text", ["", "x" * 257])
def test_resource_dimension_length_rejected(text: str) -> None:
    with pytest.raises(ValueError, match="1–256"):
        ResourceDimension(text)


@pytest.mark.parametrize("value", [None, 1, True, [], {}, lambda: None])
def test_resource_dimension_no_coercion(value: object) -> None:
    with pytest.raises(TypeError, match="must be text"):
        ResourceDimension(cast(str, value))


def test_resource_dimension_is_not_a_closed_taxonomy() -> None:
    # No canonical enum members exist -- any accountable authority's own
    # identifier is accepted, not just a guessed common-system list.
    assert ResourceDimension("provider-calls") != ResourceDimension("compute-seconds")
    assert ResourceDimension("anything-an-authority-names") is not None


def test_resource_dimension_immutable() -> None:
    value = ResourceDimension("compute-seconds")
    with pytest.raises(FrozenInstanceError):
        setattr(value, "value", "changed")  # noqa: B010
    assert not hasattr(value, "__dict__")


# --- ResourceAmountKind -------------------------------------------------------


def test_resource_amount_kind_exact_five_canonical_members() -> None:
    assert {member.value for member in ResourceAmountKind} == {
        "estimate",
        "bound",
        "reservation",
        "actual",
        "correction",
    }
    assert len(ResourceAmountKind) == 5


# --- ResourceQuantity ---------------------------------------------------------


def test_resource_quantity_valid_construction() -> None:
    quantity = _quantity(magnitude=Decimal("2.5"))
    assert quantity.magnitude == Decimal("2.5")
    assert quantity == replace(quantity)


@pytest.mark.parametrize(
    "magnitude",
    [Decimal("-1"), Decimal("-0.0001"), Decimal("NaN"), Decimal("Infinity")],
)
def test_resource_quantity_rejects_negative_nan_and_infinite(
    magnitude: Decimal,
) -> None:
    with pytest.raises(ValueError):
        _quantity(magnitude=magnitude)


def test_resource_quantity_allows_zero() -> None:
    assert _quantity(magnitude=Decimal("0")).magnitude == Decimal("0")


@pytest.mark.parametrize("magnitude", [1, 1.0, True, "1", None, [], {}])
def test_resource_quantity_magnitude_rejects_non_decimal(magnitude: object) -> None:
    with pytest.raises(TypeError, match="must be Decimal"):
        _quantity(magnitude=cast(Decimal, magnitude))


@pytest.mark.parametrize("value", [None, 1, True, [], {}, lambda: None])
def test_resource_quantity_unit_rejects_non_text(value: object) -> None:
    with pytest.raises(TypeError):
        ResourceQuantity(
            ResourceDimension("compute-seconds"),
            cast(str, value),
            Version(1, 0, 0),
            ResourceAmountKind.BOUND,
            Decimal("1"),
        )


def test_resource_quantity_requires_typed_dimension_version_and_kind() -> None:
    with pytest.raises(TypeError, match="ResourceDimension"):
        ResourceQuantity(
            cast(ResourceDimension, "compute-seconds"),
            "second",
            Version(1, 0, 0),
            ResourceAmountKind.BOUND,
            Decimal("1"),
        )
    with pytest.raises(TypeError, match="Version"):
        ResourceQuantity(
            ResourceDimension("compute-seconds"),
            "second",
            cast(Version, "1.0.0"),
            ResourceAmountKind.BOUND,
            Decimal("1"),
        )
    with pytest.raises(TypeError, match="ResourceAmountKind"):
        ResourceQuantity(
            ResourceDimension("compute-seconds"),
            "second",
            Version(1, 0, 0),
            cast(ResourceAmountKind, "bound"),
            Decimal("1"),
        )


def test_resource_quantity_has_no_availability_or_authority_shortcut() -> None:
    names = {f.name for f in fields(ResourceQuantity)}
    assert names.isdisjoint(FORBIDDEN_RUNTIME_FIELDS)
    assert not any(hasattr(_quantity(), attr) for attr in FORBIDDEN_RUNTIME_FIELDS)


def test_resource_quantity_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(ResourceQuantity)
    for name, hint in hints.items():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object
        assert "Any" not in str(hint), f"{name} must not accept typing.Any"


def test_resource_quantity_rejects_callable_and_arbitrary_object_binding() -> None:
    quantity = _quantity()
    canaries: tuple[object, ...] = (lambda: None, object(), print, {"k": "v"})
    for field_name in ("dimension", "unit_version", "amount_kind"):
        for canary in canaries:
            with pytest.raises(TypeError):
                cast(Callable[..., object], replace)(quantity, **{field_name: canary})


def test_resource_quantity_immutable_and_stable_hash() -> None:
    quantity = _quantity()
    original_hash = hash(quantity)
    assert not hasattr(quantity, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(quantity, "magnitude", Decimal("9"))  # noqa: B010
    assert hash(quantity) == original_hash


# --- ResourceClaimId -----------------------------------------------------------


def test_resource_claim_id_is_not_operation_id() -> None:
    claim_id: object = ResourceClaimId("same-text")
    operation_id: object = OperationId("same-text")
    assert claim_id != operation_id
    assert len({claim_id, operation_id}) == 2
    assert repr(ResourceClaimId("sensitive-canary")) == "ResourceClaimId()"


# --- ResourceClaim -------------------------------------------------------------


def test_resource_claim_valid_construction() -> None:
    claim = _claim()
    assert claim.claim_id == ResourceClaimId("claim-1")
    assert claim == replace(claim)


def test_resource_claim_is_one_dimension_not_a_bundle() -> None:
    # A claim carries exactly one ResourceQuantity; no list/map field exists
    # to silently merge or aggregate multiple resource dimensions.
    claim = _claim()
    assert not hasattr(claim, "quantities")
    assert not hasattr(claim, "resources")
    assert isinstance(claim.quantity, ResourceQuantity)


def test_resource_claim_has_no_availability_authority_or_reservation_shortcut() -> None:
    names = {f.name for f in fields(ResourceClaim)}
    assert names.isdisjoint(FORBIDDEN_RUNTIME_FIELDS)
    assert not any(hasattr(_claim(), attr) for attr in FORBIDDEN_RUNTIME_FIELDS)


def test_resource_claim_tenant_mismatch_rejected() -> None:
    claim = _claim()
    with pytest.raises(ValueError, match="tenant mismatch"):
        replace(claim, tenant_context=TenantContext(TenantId("other")))


@pytest.mark.parametrize(
    "field_name", ["claim_id", "operation", "tenant_context", "quantity"]
)
def test_resource_claim_required_fields_reject_wrong_type(field_name: str) -> None:
    claim = _claim()
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, lambda: None, None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(claim, **{field_name: invalid})


def test_resource_claim_rejects_callable_and_arbitrary_object_binding() -> None:
    claim = _claim()
    canaries: tuple[object, ...] = (lambda: None, object(), print, {"k": "v"})
    for field_name in ("claim_id", "operation", "tenant_context", "quantity"):
        for canary in canaries:
            with pytest.raises(TypeError):
                cast(Callable[..., object], replace)(claim, **{field_name: canary})


def test_resource_claim_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(ResourceClaim)
    for name, hint in hints.items():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object
        assert "Any" not in str(hint), f"{name} must not accept typing.Any"


def test_resource_claim_immutable_and_stable_hash() -> None:
    claim = _claim()
    original_hash = hash(claim)
    assert not hasattr(claim, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(claim, "claim_id", ResourceClaimId("other"))  # noqa: B010
    assert hash(claim) == original_hash


def test_resource_claim_construction_does_not_prove_current_availability() -> None:
    claim = _claim()
    assert not any(
        hasattr(claim, attr)
        for attr in ("granted", "reservation_succeeded", "consumed", "quota_ok")
    )


def test_resource_claim_declared_vs_actual_amount_kind_distinct() -> None:
    declared = _claim()
    actual = replace(
        _claim(),
        claim_id=ResourceClaimId("claim-2"),
        quantity=_quantity(kind=ResourceAmountKind.ACTUAL, magnitude=Decimal("0.75")),
    )
    assert declared.quantity.amount_kind is ResourceAmountKind.BOUND
    assert actual.quantity.amount_kind is ResourceAmountKind.ACTUAL
    assert declared.quantity.magnitude != actual.quantity.magnitude


def test_resource_claim_is_not_execution_id_bound() -> None:
    # M3 binds only through the logical operation (Kernel OperationRef);
    # no ExecutionId field exists, preserving operation identity != execution identity.
    claim = _claim()
    assert not hasattr(claim, "execution_id")
