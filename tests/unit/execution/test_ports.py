"""Gate-2 M9: ADR-007 SS6.2 -- DispatchRequest/DispatchDecision/DispatchPermit
describe a dispatch-arbitration fact, never the dispatch effect itself.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime
from typing import cast, get_type_hints

import pytest

from legoai.capabilities.ports import CatalogEntry
from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.evidence.ports import EvidenceId
from legoai.execution.ports import (
    CoordinationOutcome,
    CoordinationRequest,
    CoordinationResult,
    DispatchDecision,
    DispatchOutcome,
    DispatchPermit,
    DispatchRequest,
    GovernedInvocationResult,
    SecurityContextResolutionPort,
)
from legoai.execution.values import (
    ExecutionContext,
    ExecutionId,
    ExecutionResult,
    ExecutionState,
    SecurityContextRef,
)
from legoai.governance.ports import (
    AuthorizationDecision,
    AuthorizationOutcome,
    SecurityContext,
)
from legoai.governance.values import PolicyRef, Principal
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorDetail, Recoverability
from legoai.kernel.identity import (
    ApplicationId,
    CorrelationId,
    OperationId,
    PrincipalId,
    TenantId,
)
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    OperationRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.plugins.ports import PluginAdmissionId
from legoai.plugins.values import PluginId

FORBIDDEN_RUNTIME_FIELDS = {
    "callable",
    "handler",
    "adapter",
    "provider",
    "factory",
    "connection",
    "instance",
    "authorized",
    "available",
}

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _principal(name: str) -> Principal:
    return Principal(PrincipalRef("identity-owner", PrincipalId(name)))


def _operation(tenant: str = "tenant") -> OperationRef:
    return OperationRef(
        ConfigurationRef(
            ApplicationRef(
                ReferenceScope("composition", TenantId(tenant)), ApplicationId("app")
            ),
            "config",
        ),
        OperationId("op"),
        "configuration",
    )


def _security_context(*, tenant: str = "tenant") -> SecurityContext:
    return SecurityContext(
        _principal("grantee"),
        TenantContext(TenantId(tenant)),
        _operation(tenant),
        "invoke-capability",
        "text.normalize",
        None,
        None,
        PolicyRef("policy-owner", "policy", Version(1, 0, 0)),
        _EPOCH,
    )


def _catalog_entry(*, tenant: str = "tenant") -> CatalogEntry:
    return CatalogEntry(
        PluginId("legoai", "fixture"),
        Version(0, 1, 0),
        CapabilityOffer(CapabilityId("text.normalize"), Version(1, 0, 0)),
        TenantContext(TenantId(tenant)),
        PluginAdmissionId("admission-1"),
        _EPOCH,
    )


def _allowed_decision(*, tenant: str = "tenant") -> AuthorizationDecision:
    return AuthorizationDecision(
        AuthorizationOutcome.ALLOWED, _operation(tenant), _EPOCH, None, None, None, None
    )


def _request(*, tenant: str = "tenant") -> DispatchRequest:
    return DispatchRequest(
        _security_context(tenant=tenant), _catalog_entry(tenant=tenant)
    )


def _permit(*, tenant: str = "tenant") -> DispatchPermit:
    return DispatchPermit(
        _operation(tenant),
        _catalog_entry(tenant=tenant),
        1,
        _allowed_decision(tenant=tenant),
        _EPOCH,
    )


def _execution_context(
    *, tenant: str = "tenant", deadline: datetime | None = None
) -> ExecutionContext:
    return ExecutionContext(
        ExecutionId("exec-1"),
        _operation(tenant),
        TenantContext(TenantId(tenant)),
        SecurityContextRef("issuer", "ref-1"),
        CorrelationId("corr-1"),
        None,
        deadline,
        None,
    )


def _coordination_request(
    *, tenant: str = "tenant", deadline: datetime | None = None
) -> CoordinationRequest:
    return CoordinationRequest(
        _execution_context(tenant=tenant, deadline=deadline),
        _catalog_entry(tenant=tenant),
    )


# --- DispatchOutcome -----------------------------------------------------------


def test_dispatch_outcome_exact_four_members() -> None:
    assert {m.value for m in DispatchOutcome} == {
        "permitted",
        "denied",
        "unavailable",
        "stale",
    }


# --- DispatchRequest -------------------------------------------------------------


def test_dispatch_request_valid_construction() -> None:
    request = _request()
    assert request.required_evidence_ids == ()
    assert request == replace(request)


def test_dispatch_request_accepts_required_evidence_ids() -> None:
    request = replace(_request(), required_evidence_ids=(EvidenceId("e1"),))
    assert request.required_evidence_ids == (EvidenceId("e1"),)


def test_dispatch_request_tenant_mismatch_rejected() -> None:
    with pytest.raises(ValueError, match="tenant mismatch"):
        DispatchRequest(
            _security_context(tenant="tenant-a"), _catalog_entry(tenant="tenant-b")
        )


def test_dispatch_request_rejects_wrong_type_evidence_ids() -> None:
    with pytest.raises(TypeError, match="immutable"):
        replace(
            _request(),
            required_evidence_ids=cast("tuple[EvidenceId, ...]", [EvidenceId("e1")]),
        )
    with pytest.raises(TypeError, match="immutable"):
        replace(
            _request(),
            required_evidence_ids=cast("tuple[EvidenceId, ...]", (object(),)),
        )


@pytest.mark.parametrize("field_name", ["security_context", "resolved_entry"])
def test_dispatch_request_required_fields_reject_wrong_type(field_name: str) -> None:
    request = _request()
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, lambda: None, None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(request, **{field_name: invalid})


def test_dispatch_request_immutable() -> None:
    request = _request()
    with pytest.raises(FrozenInstanceError):
        setattr(request, "resolved_entry", _catalog_entry())  # noqa: B010


# --- DispatchPermit -------------------------------------------------------------


def test_dispatch_permit_valid_construction() -> None:
    permit = _permit()
    assert permit.catalog_revision == 1


def test_dispatch_permit_requires_allowed_security_decision() -> None:
    denied_decision = AuthorizationDecision(
        AuthorizationOutcome.DENIED,
        _operation(),
        _EPOCH,
        ErrorCategory.AUTHORIZATION_DENIED,
        None,
        None,
        None,
    )
    with pytest.raises(ValueError, match="ALLOWED"):
        DispatchPermit(_operation(), _catalog_entry(), 1, denied_decision, _EPOCH)


def test_dispatch_permit_catalog_revision_must_be_nonnegative() -> None:
    with pytest.raises(ValueError, match="nonnegative"):
        replace(_permit(), catalog_revision=-1)


def test_dispatch_permit_granted_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(_permit(), granted_at=datetime(2026, 1, 1))


@pytest.mark.parametrize(
    "field_name",
    [
        "operation",
        "resolved_entry",
        "catalog_revision",
        "security_decision",
        "granted_at",
    ],
)
def test_dispatch_permit_required_fields_reject_wrong_type(field_name: str) -> None:
    permit = _permit()
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, lambda: None, None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(permit, **{field_name: invalid})


def test_dispatch_permit_has_no_executable_field() -> None:
    names = {f.name for f in fields(DispatchPermit)}
    assert names.isdisjoint(FORBIDDEN_RUNTIME_FIELDS)
    permit = _permit()
    assert not any(hasattr(permit, attr) for attr in FORBIDDEN_RUNTIME_FIELDS)
    assert not callable(permit)
    for method_name in ("invoke", "execute", "dispatch", "call_provider", "activate"):
        assert not hasattr(permit, method_name)


def test_dispatch_permit_immutable() -> None:
    permit = _permit()
    with pytest.raises(FrozenInstanceError):
        setattr(permit, "catalog_revision", 2)  # noqa: B010


# --- DispatchDecision ------------------------------------------------------------


@pytest.mark.parametrize(
    ("field_name", "invalid", "match"),
    [
        ("outcome", "permitted", "requires DispatchOutcome"),
        ("operation", "op", "requires OperationRef"),
        ("evaluated_at", "2026-01-01", "evaluated_at must be datetime"),
        ("category", "denied", "category must be ErrorCategory or None"),
        ("permit", "permit", "permit must be DispatchPermit or None"),
    ],
)
def test_dispatch_decision_fields_reject_wrong_type(
    field_name: str, invalid: object, match: str
) -> None:
    decision = DispatchDecision(
        DispatchOutcome.DENIED,
        _operation(),
        _EPOCH,
        ErrorCategory.AUTHORIZATION_DENIED,
        None,
    )
    with pytest.raises(TypeError, match=match):
        cast(Callable[..., object], replace)(decision, **{field_name: invalid})


def test_dispatch_decision_evaluated_at_must_be_timezone_aware() -> None:
    decision = DispatchDecision(
        DispatchOutcome.DENIED,
        _operation(),
        _EPOCH,
        ErrorCategory.AUTHORIZATION_DENIED,
        None,
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(decision, evaluated_at=datetime(2026, 1, 1))


def test_dispatch_decision_permitted_requires_permit_and_no_category() -> None:
    decision = DispatchDecision(
        DispatchOutcome.PERMITTED, _operation(), _EPOCH, None, _permit()
    )
    assert decision.permit is not None


def test_dispatch_decision_permitted_rejects_category() -> None:
    with pytest.raises(ValueError, match="must not carry a category"):
        DispatchDecision(
            DispatchOutcome.PERMITTED,
            _operation(),
            _EPOCH,
            ErrorCategory.AUTHORIZATION_DENIED,
            _permit(),
        )


def test_dispatch_decision_permitted_requires_permit() -> None:
    with pytest.raises(ValueError, match="requires a permit"):
        DispatchDecision(DispatchOutcome.PERMITTED, _operation(), _EPOCH, None, None)


@pytest.mark.parametrize(
    "outcome",
    [DispatchOutcome.DENIED, DispatchOutcome.UNAVAILABLE, DispatchOutcome.STALE],
)
def test_dispatch_decision_non_permitted_requires_category(
    outcome: DispatchOutcome,
) -> None:
    with pytest.raises(ValueError, match="requires a category"):
        DispatchDecision(outcome, _operation(), _EPOCH, None, None)


def test_dispatch_decision_non_permitted_rejects_permit() -> None:
    with pytest.raises(ValueError, match="must not carry a permit"):
        DispatchDecision(
            DispatchOutcome.DENIED,
            _operation(),
            _EPOCH,
            ErrorCategory.AUTHORIZATION_DENIED,
            _permit(),
        )


def test_dispatch_decision_has_no_executable_field() -> None:
    decision = DispatchDecision(
        DispatchOutcome.DENIED,
        _operation(),
        _EPOCH,
        ErrorCategory.AUTHORIZATION_DENIED,
        None,
    )
    names = {f.name for f in fields(DispatchDecision)}
    assert names.isdisjoint(FORBIDDEN_RUNTIME_FIELDS)
    for method_name in ("invoke", "execute", "dispatch", "call_provider", "activate"):
        assert not hasattr(decision, method_name)


def test_dispatch_decision_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(DispatchDecision)
    for name, hint in hints.items():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object
        assert "Any" not in str(hint), f"{name} must not accept typing.Any"


def test_dispatch_decision_immutable_and_stable_hash() -> None:
    decision = DispatchDecision(
        DispatchOutcome.PERMITTED, _operation(), _EPOCH, None, _permit()
    )
    original_hash = hash(decision)
    assert not hasattr(decision, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(decision, "outcome", DispatchOutcome.DENIED)  # noqa: B010
    assert hash(decision) == original_hash


def test_dispatch_decision_does_not_claim_future_validity() -> None:
    decision = DispatchDecision(
        DispatchOutcome.PERMITTED, _operation(), _EPOCH, None, _permit()
    )
    assert not any(
        hasattr(decision, attr)
        for attr in ("valid_forever", "permanent", "still_valid")
    )


# --- Gate-2 M10: CoordinationRequest ---------------------------------------------


def test_coordination_request_valid_construction() -> None:
    request = _coordination_request()
    assert request.required_evidence_ids == ()
    assert request == replace(request)


def test_coordination_request_tenant_mismatch_rejected() -> None:
    with pytest.raises(ValueError, match="tenant mismatch"):
        CoordinationRequest(
            _execution_context(tenant="tenant-a"), _catalog_entry(tenant="tenant-b")
        )


@pytest.mark.parametrize("field_name", ["context", "resolved_entry"])
def test_coordination_request_required_fields_reject_wrong_type(
    field_name: str,
) -> None:
    request = _coordination_request()
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, lambda: None, None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(request, **{field_name: invalid})


def test_coordination_request_rejects_wrong_type_evidence_ids() -> None:
    with pytest.raises(TypeError, match="immutable"):
        replace(
            _coordination_request(),
            required_evidence_ids=cast("tuple[EvidenceId, ...]", [EvidenceId("e1")]),
        )


def test_coordination_request_immutable() -> None:
    request = _coordination_request()
    with pytest.raises(FrozenInstanceError):
        setattr(request, "resolved_entry", _catalog_entry())  # noqa: B010


# --- Gate-2 M10: CoordinationOutcome / CoordinationResult ------------------------


def test_coordination_outcome_exact_three_members() -> None:
    assert {member.value for member in CoordinationOutcome} == {
        "ready",
        "rejected",
        "cancelled",
    }


def test_coordination_result_ready_requires_running_and_permit() -> None:
    result = CoordinationResult(
        ExecutionId("exec-1"),
        CoordinationOutcome.READY,
        ExecutionState.RUNNING,
        _permit(),
        None,
    )
    assert result.permit is not None

    with pytest.raises(ValueError, match="requires ExecutionState.RUNNING"):
        CoordinationResult(
            ExecutionId("exec-1"),
            CoordinationOutcome.READY,
            ExecutionState.ADMITTED,
            _permit(),
            None,
        )
    with pytest.raises(ValueError, match="requires a permit"):
        CoordinationResult(
            ExecutionId("exec-1"),
            CoordinationOutcome.READY,
            ExecutionState.RUNNING,
            None,
            None,
        )
    with pytest.raises(ValueError, match="must not carry a category"):
        CoordinationResult(
            ExecutionId("exec-1"),
            CoordinationOutcome.READY,
            ExecutionState.RUNNING,
            _permit(),
            ErrorCategory.AUTHORIZATION_DENIED,
        )


def test_coordination_result_rejected_requires_category_and_no_permit() -> None:
    result = CoordinationResult(
        ExecutionId("exec-1"),
        CoordinationOutcome.REJECTED,
        ExecutionState.REJECTED,
        None,
        ErrorCategory.DEADLINE_EXCEEDED,
    )
    assert result.category is ErrorCategory.DEADLINE_EXCEEDED

    with pytest.raises(ValueError, match="requires ExecutionState.REJECTED"):
        CoordinationResult(
            ExecutionId("exec-1"),
            CoordinationOutcome.REJECTED,
            ExecutionState.CANCELLED,
            None,
            ErrorCategory.DEADLINE_EXCEEDED,
        )
    with pytest.raises(ValueError, match="requires a category"):
        CoordinationResult(
            ExecutionId("exec-1"),
            CoordinationOutcome.REJECTED,
            ExecutionState.REJECTED,
            None,
            None,
        )
    with pytest.raises(ValueError, match="must not carry a permit"):
        CoordinationResult(
            ExecutionId("exec-1"),
            CoordinationOutcome.REJECTED,
            ExecutionState.REJECTED,
            _permit(),
            ErrorCategory.DEADLINE_EXCEEDED,
        )


def test_coordination_result_cancelled_carries_neither_permit_nor_category() -> None:
    result = CoordinationResult(
        ExecutionId("exec-1"),
        CoordinationOutcome.CANCELLED,
        ExecutionState.CANCELLED,
        None,
        None,
    )
    assert result.permit is None
    assert result.category is None

    with pytest.raises(ValueError, match="requires ExecutionState.CANCELLED"):
        CoordinationResult(
            ExecutionId("exec-1"),
            CoordinationOutcome.CANCELLED,
            ExecutionState.REJECTED,
            None,
            None,
        )
    with pytest.raises(ValueError, match="must not carry a permit"):
        CoordinationResult(
            ExecutionId("exec-1"),
            CoordinationOutcome.CANCELLED,
            ExecutionState.CANCELLED,
            _permit(),
            None,
        )
    with pytest.raises(ValueError, match="must not carry a category"):
        CoordinationResult(
            ExecutionId("exec-1"),
            CoordinationOutcome.CANCELLED,
            ExecutionState.CANCELLED,
            None,
            ErrorCategory.DEADLINE_EXCEEDED,
        )


@pytest.mark.parametrize(
    "field_name", ["execution_id", "outcome", "state", "permit", "category"]
)
def test_coordination_result_rejects_wrong_type(field_name: str) -> None:
    result = CoordinationResult(
        ExecutionId("exec-1"),
        CoordinationOutcome.REJECTED,
        ExecutionState.REJECTED,
        None,
        ErrorCategory.DEADLINE_EXCEEDED,
    )
    with pytest.raises(TypeError):
        cast(Callable[..., object], replace)(result, **{field_name: "not-valid"})


def test_coordination_result_has_no_executable_field() -> None:
    result = CoordinationResult(
        ExecutionId("exec-1"),
        CoordinationOutcome.READY,
        ExecutionState.RUNNING,
        _permit(),
        None,
    )
    names = {f.name for f in fields(CoordinationResult)}
    assert names.isdisjoint(FORBIDDEN_RUNTIME_FIELDS)
    for method_name in ("invoke", "execute", "dispatch", "call_provider", "activate"):
        assert not hasattr(result, method_name)


def test_coordination_result_immutable() -> None:
    result = CoordinationResult(
        ExecutionId("exec-1"),
        CoordinationOutcome.CANCELLED,
        ExecutionState.CANCELLED,
        None,
        None,
    )
    with pytest.raises(FrozenInstanceError):
        setattr(result, "outcome", CoordinationOutcome.READY)  # noqa: B010


# --- Gate-2 M10: SecurityContextResolutionPort -----------------------------------


def test_security_context_resolution_port_resolve_is_async() -> None:
    import inspect

    assert inspect.iscoroutinefunction(SecurityContextResolutionPort.resolve)


# --- Gate-2 M11: GovernedInvocationResult ----------------------------------------


def _succeeded_execution_result() -> ExecutionResult:
    return ExecutionResult(
        ExecutionId("exec-1"), ExecutionState.SUCCEEDED, EffectExtent.COMPLETED, None
    )


def _failed_execution_result() -> ExecutionResult:
    return ExecutionResult(
        ExecutionId("exec-1"),
        ExecutionState.FAILED,
        EffectExtent.NONE,
        ErrorDetail(ErrorCategory.EXECUTION_FAILURE, Recoverability.TERMINAL, ()),
    )


def test_governed_invocation_result_succeeded_requires_output() -> None:
    result = GovernedInvocationResult(_succeeded_execution_result(), "normalized")
    assert result.output == "normalized"

    with pytest.raises(ValueError, match="requires output"):
        GovernedInvocationResult(_succeeded_execution_result(), None)


def test_governed_invocation_result_non_succeeded_rejects_output() -> None:
    result = GovernedInvocationResult(_failed_execution_result(), None)
    assert result.output is None

    with pytest.raises(ValueError, match="must not carry output"):
        GovernedInvocationResult(_failed_execution_result(), "unexpected")


def test_governed_invocation_result_rejects_wrong_type_execution_result() -> None:
    with pytest.raises(TypeError, match="requires ExecutionResult"):
        GovernedInvocationResult(object(), None)  # type: ignore[arg-type]


def test_governed_invocation_result_rejects_wrong_type_output() -> None:
    with pytest.raises(TypeError, match="output must be str or None"):
        GovernedInvocationResult(_succeeded_execution_result(), 12345)  # type: ignore[arg-type]


def test_governed_invocation_result_immutable() -> None:
    result = GovernedInvocationResult(_succeeded_execution_result(), "normalized")
    with pytest.raises(FrozenInstanceError):
        setattr(result, "output", "changed")  # noqa: B010
