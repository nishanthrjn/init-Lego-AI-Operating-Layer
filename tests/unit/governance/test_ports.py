"""Gate-2 M4: ADR-005 SS10.1 / ADR-007 SS12.1 -- `SecurityContext` and
`AuthorizationDecision` are immutable point-in-time values, never proof of
current or future validity by themselves.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta
from typing import cast, get_type_hints

import pytest

from legoai.governance.ports import (
    ApprovalUseState,
    AuthorizationDecision,
    AuthorizationOutcome,
    PolicyCurrencyStatus,
    RevocationStatus,
    SecurityContext,
)
from legoai.governance.values import (
    ApprovalId,
    Grant,
    GrantId,
    PolicyRef,
    Principal,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.errors import ErrorCategory
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
    "permissions",
    "roles",
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


def _context(*, tenant: str = "tenant", operation: str = "op") -> SecurityContext:
    return SecurityContext(
        _principal("grantee"),
        TenantContext(TenantId(tenant)),
        _operation(tenant, operation),
        "publish-configuration",
        "app:config",
        _grant(tenant=tenant),
        None,
        PolicyRef("policy-owner", "retention-policy", Version(1, 0, 0)),
        _EPOCH,
    )


def _decision(
    *, outcome: AuthorizationOutcome = AuthorizationOutcome.ALLOWED
) -> AuthorizationDecision:
    return AuthorizationDecision(
        outcome,
        _operation("tenant", "op"),
        _EPOCH,
        None
        if outcome is AuthorizationOutcome.ALLOWED
        else ErrorCategory.AUTHORIZATION_DENIED,
        GrantId("grant-1") if outcome is AuthorizationOutcome.ALLOWED else None,
        None,
        None,
    )


# --- status enums -------------------------------------------------------------


def test_revocation_status_and_policy_currency_and_outcome_members() -> None:
    assert {m.value for m in RevocationStatus} == {"active", "revoked", "unknown"}
    assert {m.value for m in PolicyCurrencyStatus} == {
        "current",
        "superseded",
        "unknown",
    }
    assert {m.value for m in AuthorizationOutcome} == {
        "allowed",
        "denied",
        "unavailable",
    }


# --- ApprovalUseState -----------------------------------------------------------


def test_approval_use_state_valid_construction() -> None:
    state = ApprovalUseState(ApprovalId("a1"), 0)
    assert state.uses_recorded == 0


@pytest.mark.parametrize("uses", [-1, -100])
def test_approval_use_state_rejects_negative(uses: int) -> None:
    with pytest.raises(ValueError, match="nonnegative"):
        ApprovalUseState(ApprovalId("a1"), uses)


@pytest.mark.parametrize("uses", [True, False, 1.0, "1", None])
def test_approval_use_state_rejects_non_int(uses: object) -> None:
    with pytest.raises(TypeError, match="must be an int"):
        ApprovalUseState(ApprovalId("a1"), cast(int, uses))


@pytest.mark.parametrize("invalid", [None, 1, True, [], {}, lambda: None])
def test_approval_use_state_rejects_wrong_approval_id_type(invalid: object) -> None:
    with pytest.raises(TypeError, match="requires ApprovalId"):
        ApprovalUseState(cast(ApprovalId, invalid), 0)


def test_approval_use_state_immutable() -> None:
    state = ApprovalUseState(ApprovalId("a1"), 0)
    with pytest.raises(FrozenInstanceError):
        setattr(state, "uses_recorded", 1)  # noqa: B010


# --- SecurityContext -----------------------------------------------------------


def test_security_context_valid_construction() -> None:
    context = _context()
    assert context.grant is not None
    assert context.approval is None
    assert context == replace(context)


def test_security_context_tenant_mismatch_rejected() -> None:
    context = _context()
    with pytest.raises(ValueError, match="tenant mismatch"):
        replace(context, tenant_context=TenantContext(TenantId("other")))


def test_security_context_established_at_must_be_timezone_aware() -> None:
    context = _context()
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(context, established_at=datetime(2026, 1, 1))


@pytest.mark.parametrize("invalid", ["2026-01-01", 1, True, [], {}, lambda: None])
def test_security_context_established_at_rejects_non_datetime(invalid: object) -> None:
    with pytest.raises(TypeError, match="must be datetime"):
        replace(_context(), established_at=cast(datetime, invalid))


def test_security_context_accepts_none_grant_and_none_approval() -> None:
    context = replace(_context(), grant=None)
    assert context.grant is None
    assert replace(context, approval=None).approval is None


def test_security_context_has_no_bare_authority_field() -> None:
    names = {f.name for f in fields(SecurityContext)}
    assert names.isdisjoint(FORBIDDEN_AUTHORITY_FIELDS)
    assert not any(hasattr(_context(), attr) for attr in FORBIDDEN_AUTHORITY_FIELDS)


def test_security_context_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(SecurityContext)
    for name, hint in hints.items():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object
        assert "Any" not in str(hint), f"{name} must not accept typing.Any"


@pytest.mark.parametrize(
    "field_name",
    ["principal", "tenant_context", "operation", "policy_ref"],
)
def test_security_context_required_fields_reject_wrong_type(field_name: str) -> None:
    context = _context()
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, lambda: None, None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(context, **{field_name: invalid})


def test_security_context_rejects_callable_and_arbitrary_object_binding() -> None:
    context = _context()
    canaries: tuple[object, ...] = (lambda: None, object(), print, {"k": "v"})
    for field_name in ("principal", "tenant_context", "operation", "grant", "approval"):
        for canary in canaries:
            with pytest.raises(TypeError):
                cast(Callable[..., object], replace)(context, **{field_name: canary})


def test_security_context_immutable_and_stable_hash() -> None:
    context = _context()
    original_hash = hash(context)
    assert not hasattr(context, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(context, "established_at", _EPOCH)  # noqa: B010
    assert hash(context) == original_hash


def test_security_context_presence_does_not_prove_current_validity() -> None:
    context = _context()
    assert not any(
        hasattr(context, attr)
        for attr in ("valid", "currently_valid", "unrevoked", "unconsumed")
    )


# --- AuthorizationDecision -------------------------------------------------------


def test_authorization_decision_valid_allowed_construction() -> None:
    decision = _decision(outcome=AuthorizationOutcome.ALLOWED)
    assert decision.category is None


def test_authorization_decision_valid_denied_construction() -> None:
    decision = _decision(outcome=AuthorizationOutcome.DENIED)
    assert decision.category is ErrorCategory.AUTHORIZATION_DENIED


def test_authorization_decision_allowed_must_not_carry_category() -> None:
    with pytest.raises(ValueError, match="must not carry a category"):
        AuthorizationDecision(
            AuthorizationOutcome.ALLOWED,
            _operation("tenant", "op"),
            _EPOCH,
            ErrorCategory.AUTHORIZATION_DENIED,
            None,
            None,
            None,
        )


@pytest.mark.parametrize(
    "outcome", [AuthorizationOutcome.DENIED, AuthorizationOutcome.UNAVAILABLE]
)
def test_authorization_decision_non_allowed_requires_category(
    outcome: AuthorizationOutcome,
) -> None:
    with pytest.raises(ValueError, match="requires a category"):
        AuthorizationDecision(
            outcome, _operation("tenant", "op"), _EPOCH, None, None, None, None
        )


def test_authorization_decision_evaluated_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        AuthorizationDecision(
            AuthorizationOutcome.ALLOWED,
            _operation("tenant", "op"),
            datetime(2026, 1, 1),
            None,
            GrantId("g1"),
            None,
            None,
        )


@pytest.mark.parametrize(
    ("field_name", "invalid", "match"),
    [
        ("outcome", "allowed", "requires AuthorizationOutcome"),
        ("operation", "op", "requires OperationRef"),
        ("evaluated_at", "2026-01-01", "evaluated_at must be datetime"),
        ("category", "denied", "category must be ErrorCategory or None"),
        ("considered_grant", "g1", "considered_grant must be GrantId or None"),
        (
            "considered_approval",
            "a1",
            "considered_approval must be ApprovalId or None",
        ),
        ("considered_policy", "p1", "considered_policy must be PolicyRef or None"),
    ],
)
def test_authorization_decision_fields_reject_wrong_type(
    field_name: str, invalid: object, match: str
) -> None:
    decision = _decision()
    with pytest.raises(TypeError, match=match):
        cast(Callable[..., object], replace)(decision, **{field_name: invalid})


def test_authorization_decision_does_not_claim_future_validity() -> None:
    decision = _decision()
    assert not any(
        hasattr(decision, attr)
        for attr in ("valid_forever", "authorized_for_dispatch", "permanent")
    )


def test_authorization_decision_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(AuthorizationDecision)
    for name, hint in hints.items():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object
        assert "Any" not in str(hint), f"{name} must not accept typing.Any"


def test_authorization_decision_immutable_and_stable_hash() -> None:
    decision = _decision()
    original_hash = hash(decision)
    assert not hasattr(decision, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(decision, "outcome", AuthorizationOutcome.DENIED)  # noqa: B010
    assert hash(decision) == original_hash
