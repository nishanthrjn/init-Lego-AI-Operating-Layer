"""Gate-2 M2: ADR-005 SS9.1 / SECURITY SEC-022, SEC-031 -- Grant, Approval and
PolicyRef are immutable structural records of what was granted/requested,
never proof that authority currently remains valid.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta
from typing import cast, get_type_hints

import pytest

from legoai.governance.values import (
    Approval,
    ApprovalId,
    Grant,
    GrantId,
    PolicyRef,
    Principal,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import ApplicationId, OperationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    OperationRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version

FORBIDDEN_AUTHORITY_FIELDS = {
    "authorized",
    "is_authorized",
    "approved",
    "is_approved",
    "trusted",
    "admin",
    "is_admin",
    "permissions",
    "permission",
    "roles",
    "role",
    "password",
    "token",
    "secret",
    "credential",
}

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _principal(name: str) -> Principal:
    return Principal(PrincipalRef("identity-owner", PrincipalId(name)))


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


def _grant(*, tenant: str = "tenant") -> Grant:
    return Grant(
        GrantId("grant-1"),
        _principal("issuer"),
        _principal("grantee"),
        TenantContext(TenantId(tenant)),
        "publish-configuration",
        "app:config",
        False,
        _EPOCH,
        _EPOCH + timedelta(days=1),
    )


def _approval(*, tenant: str = "tenant", operation: str = "op") -> Approval:
    return Approval(
        ApprovalId("approval-1"),
        _operation(tenant, operation),
        TenantContext(TenantId(tenant)),
        _principal("requester"),
        _principal("approver"),
        1,
        _EPOCH,
        _EPOCH + timedelta(hours=1),
    )


# --- PolicyRef ---------------------------------------------------------------


def test_policy_ref_valid_and_opaque() -> None:
    ref = PolicyRef("policy-owner", "retention-policy", Version(1, 0, 0))
    assert ref == PolicyRef("policy-owner", "retention-policy", Version(1, 0, 0))
    assert not any(
        hasattr(ref, attr) for attr in ("allowed", "rule", "evaluate", "decision")
    )
    assert "policy-owner" not in repr(ref)
    assert "retention-policy" not in repr(ref)


@pytest.mark.parametrize("value", [None, 1, True, [], {}, lambda: None])
def test_policy_ref_rejects_non_text(value: object) -> None:
    with pytest.raises(TypeError):
        PolicyRef(cast(str, value), "policy", Version(1, 0, 0))
    with pytest.raises(TypeError):
        PolicyRef("issuer", cast(str, value), Version(1, 0, 0))


def test_policy_ref_requires_version_type() -> None:
    with pytest.raises(TypeError, match="Version"):
        PolicyRef("issuer", "policy", cast(Version, "1.0.0"))


def test_policy_ref_immutable() -> None:
    ref = PolicyRef("issuer", "policy", Version(1, 0, 0))
    with pytest.raises(FrozenInstanceError):
        setattr(ref, "policy_id", "changed")  # noqa: B010
    assert not hasattr(ref, "__dict__")


# --- GrantId / ApprovalId identity distinction --------------------------------


def test_grant_id_and_approval_id_are_not_each_other_or_operation_id() -> None:
    grant_id: object = GrantId("same-text")
    approval_id: object = ApprovalId("same-text")
    operation_id: object = OperationId("same-text")
    assert len({grant_id, approval_id, operation_id}) == 3
    assert grant_id != approval_id
    assert repr(GrantId("sensitive-canary")) == "GrantId()"
    assert repr(ApprovalId("sensitive-canary")) == "ApprovalId()"


# --- Grant ---------------------------------------------------------------------


def test_grant_valid_construction() -> None:
    grant = _grant()
    assert grant.grant_id == GrantId("grant-1")
    assert grant.delegable is False
    assert grant == replace(grant)


def test_grant_is_not_a_bare_authority_boolean() -> None:
    names = {f.name for f in fields(Grant)}
    assert names.isdisjoint(FORBIDDEN_AUTHORITY_FIELDS)
    assert not any(hasattr(_grant(), attr) for attr in FORBIDDEN_AUTHORITY_FIELDS)


def test_grant_expiry_must_be_after_valid_from_and_timezone_aware() -> None:
    grant = _grant()
    with pytest.raises(ValueError, match="after valid_from"):
        replace(grant, expires_at=_EPOCH)
    with pytest.raises(ValueError, match="after valid_from"):
        replace(grant, expires_at=_EPOCH - timedelta(seconds=1))
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(grant, valid_from=datetime(2026, 1, 1))
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(grant, expires_at=datetime(2026, 1, 2))
    assert replace(grant, expires_at=None).expires_at is None


@pytest.mark.parametrize("invalid", ["2026-01-01", 1, True, [], {}, lambda: None])
def test_grant_valid_from_rejects_non_datetime(invalid: object) -> None:
    with pytest.raises(TypeError, match="valid_from must be datetime"):
        replace(_grant(), valid_from=cast(datetime, invalid))


@pytest.mark.parametrize("invalid", ["2026-01-01", 1, True, [], {}, lambda: None])
def test_grant_expires_at_rejects_non_datetime(invalid: object) -> None:
    with pytest.raises(TypeError, match="expires_at must be datetime or None"):
        replace(_grant(), expires_at=cast(datetime, invalid))


def test_grant_action_and_resource_scope_are_opaque_non_empty_text() -> None:
    with pytest.raises(ValueError, match="1–256"):
        replace(_grant(), action="")
    with pytest.raises(TypeError):
        replace(_grant(), action=cast(str, {"resource": "app", "verb": "publish"}))


@pytest.mark.parametrize(
    "field_name", ["grant_id", "issuer", "grantee", "tenant_context"]
)
def test_grant_required_fields_reject_wrong_type(field_name: str) -> None:
    grant = _grant()
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, lambda: None, None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(grant, **{field_name: invalid})


def test_grant_delegable_must_be_bool() -> None:
    invalid_inputs: tuple[object, ...] = (1, 0, "true", None, [], {})
    for invalid in invalid_inputs:
        with pytest.raises(TypeError, match="delegable must be a bool"):
            cast(Callable[..., object], replace)(_grant(), delegable=invalid)


def test_grant_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(Grant)
    for name, hint in hints.items():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object
        assert "Any" not in str(hint), f"{name} must not accept typing.Any"


def test_grant_rejects_callable_and_arbitrary_object_binding() -> None:
    grant = _grant()
    canaries: tuple[object, ...] = (lambda: None, object(), print, {"k": "v"})
    for field_name in ("grant_id", "issuer", "grantee", "tenant_context"):
        for canary in canaries:
            with pytest.raises(TypeError):
                cast(Callable[..., object], replace)(grant, **{field_name: canary})


def test_grant_immutable_and_stable_hash() -> None:
    grant = _grant()
    original_hash = hash(grant)
    assert not hasattr(grant, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(grant, "delegable", True)  # noqa: B010
    assert hash(grant) == original_hash


def test_grant_construction_does_not_prove_current_validity() -> None:
    # A structurally valid Grant carries no field asserting it is unrevoked,
    # still active, or that its issuer currently retains issuing authority.
    grant = _grant()
    assert not any(
        hasattr(grant, attr)
        for attr in ("revoked", "is_revoked", "currently_valid", "active")
    )


# --- Approval --------------------------------------------------------------


def test_approval_valid_construction() -> None:
    approval = _approval()
    assert approval.max_uses == 1
    assert approval == replace(approval)


def test_approval_is_not_bare_approved_boolean() -> None:
    names = {f.name for f in fields(Approval)}
    assert names.isdisjoint(FORBIDDEN_AUTHORITY_FIELDS)
    assert not any(hasattr(_approval(), attr) for attr in FORBIDDEN_AUTHORITY_FIELDS)


def test_approval_has_no_consumption_or_remaining_use_state() -> None:
    # M2 models only the declared ceiling; consumption is later owner state.
    approval = _approval()
    assert not any(
        hasattr(approval, attr)
        for attr in ("remaining_uses", "consumed", "consumed_uses", "used")
    )


@pytest.mark.parametrize("max_uses", [0, -1, -100])
def test_approval_max_uses_must_be_positive(max_uses: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        replace(_approval(), max_uses=max_uses)


@pytest.mark.parametrize("max_uses", [True, False, 1.0, "1", None])
def test_approval_max_uses_rejects_non_int(max_uses: object) -> None:
    with pytest.raises(TypeError, match="must be an int"):
        cast(Callable[..., object], replace)(_approval(), max_uses=max_uses)


def test_approval_expiry_must_be_after_valid_from_and_timezone_aware() -> None:
    approval = _approval()
    with pytest.raises(ValueError, match="after valid_from"):
        replace(approval, expires_at=_EPOCH)
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(approval, valid_from=datetime(2026, 1, 1))
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(approval, expires_at=datetime(2026, 1, 1, 1))
    with pytest.raises(TypeError, match="expires_at must be datetime"):
        cast(Callable[..., object], replace)(approval, expires_at=None)


@pytest.mark.parametrize("invalid", ["2026-01-01", 1, True, [], {}, lambda: None])
def test_approval_valid_from_rejects_non_datetime(invalid: object) -> None:
    with pytest.raises(TypeError, match="valid_from must be datetime"):
        replace(_approval(), valid_from=cast(datetime, invalid))


def test_approval_tenant_mismatch_rejected() -> None:
    approval = _approval()
    with pytest.raises(ValueError, match="tenant mismatch"):
        replace(approval, tenant_context=TenantContext(TenantId("other")))


@pytest.mark.parametrize(
    "field_name",
    ["approval_id", "operation", "tenant_context", "requester", "approver"],
)
def test_approval_required_fields_reject_wrong_type(field_name: str) -> None:
    approval = _approval()
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, lambda: None, None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(approval, **{field_name: invalid})


def test_approval_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(Approval)
    for name, hint in hints.items():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object
        assert "Any" not in str(hint), f"{name} must not accept typing.Any"


def test_approval_rejects_callable_and_arbitrary_object_binding() -> None:
    approval = _approval()
    canaries: tuple[object, ...] = (lambda: None, object(), print, {"k": "v"})
    for field_name in ("approval_id", "operation", "tenant_context", "requester"):
        for canary in canaries:
            with pytest.raises(TypeError):
                cast(Callable[..., object], replace)(approval, **{field_name: canary})


def test_approval_immutable_and_stable_hash() -> None:
    approval = _approval()
    original_hash = hash(approval)
    assert not hasattr(approval, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(approval, "max_uses", 5)  # noqa: B010
    assert hash(approval) == original_hash


# --- Principal vs Grant vs Approval structural distinction --------------------


def test_principal_cannot_stand_in_for_grant_or_approval() -> None:
    principal = _principal("someone")
    with pytest.raises(TypeError):
        Grant(
            GrantId("g1"),
            principal,
            principal,
            cast(TenantContext, principal),
            "action",
            "scope",
            False,
            _EPOCH,
            None,
        )
    with pytest.raises(TypeError):
        replace(_grant(), issuer=cast(Principal, GrantId("not-a-principal")))
    with pytest.raises(TypeError):
        replace(_approval(), requester=cast(Principal, ApprovalId("not-a-principal")))


def test_grant_and_approval_are_structurally_distinct() -> None:
    grant: object = _grant()
    approval: object = _approval()
    assert type(grant) is not type(approval)
    assert not hasattr(grant, "max_uses")
    assert not hasattr(approval, "delegable")
    assert grant != approval
