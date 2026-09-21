"""Gate-2 M1: ADR-015 SS2 / ADR-008 SS4.1 -- Execution values describe, they
do not create, authorize, admit, resource, dispatch, invoke, retry, cancel,
supervise or persist an Execution.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime
from typing import cast, get_type_hints

import pytest

from legoai.execution.values import (
    ExecutionContext,
    ExecutionId,
    ExecutionResult,
    ExecutionState,
    SecurityContextRef,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorCause, ErrorDetail, Recoverability
from legoai.kernel.identity import (
    ApplicationId,
    CorrelationId,
    OperationId,
    TenantId,
    TraceId,
)
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    OperationRef,
    ReferenceScope,
)

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
    "grants",
    "grant",
    "roles",
    "role",
    "policy",
    "policies",
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


def _context(*, tenant: str = "tenant", operation: str = "op") -> ExecutionContext:
    return ExecutionContext(
        ExecutionId("execution-1"),
        _operation(tenant, operation),
        TenantContext(TenantId(tenant)),
        SecurityContextRef("identity-owner", "context-ref-1"),
        CorrelationId("correlation"),
        TraceId("trace"),
        datetime(2026, 1, 1, tzinfo=UTC),
        None,
    )


# --- ExecutionState ---------------------------------------------------------


def test_execution_state_exact_ten_canonical_members() -> None:
    assert {member.value for member in ExecutionState} == {
        "created",
        "admitted",
        "running",
        "waiting",
        "suspended",
        "cancelling",
        "succeeded",
        "failed",
        "cancelled",
        "rejected",
    }
    assert len(ExecutionState) == 10


# --- ExecutionId -------------------------------------------------------------


def test_execution_id_valid() -> None:
    value = ExecutionId("exec-1")
    assert value.value == "exec-1"
    assert value == ExecutionId("exec-1")
    assert hash(value) == hash(ExecutionId("exec-1"))


@pytest.mark.parametrize("text", ["", "x" * 257])
def test_execution_id_length_rejected(text: str) -> None:
    with pytest.raises(ValueError, match="1–256"):
        ExecutionId(text)


@pytest.mark.parametrize("value", [None, 1, True, b"abc", [], {}, lambda: None])
def test_execution_id_no_coercion(value: object) -> None:
    with pytest.raises(TypeError, match="must be text"):
        ExecutionId(cast(str, value))


def test_execution_id_immutable_and_representation_omits_text() -> None:
    value = ExecutionId("sensitive-canary")
    original_hash = hash(value)
    with pytest.raises(FrozenInstanceError):
        setattr(value, "value", "changed")  # noqa: B010
    assert not hasattr(value, "__dict__")
    assert hash(value) == original_hash
    assert repr(value) == "ExecutionId()"


def test_execution_id_is_not_operation_id() -> None:
    execution_id: object = ExecutionId("same-text")
    operation_id: object = OperationId("same-text")
    assert execution_id != operation_id
    assert operation_id != execution_id
    assert len({execution_id, operation_id}) == 2


# --- SecurityContextRef ------------------------------------------------------


def test_security_context_ref_valid_and_opaque() -> None:
    value = SecurityContextRef("identity-owner", "ref-1")
    assert value == SecurityContextRef("identity-owner", "ref-1")
    assert not any(
        hasattr(value, attr)
        for attr in (
            "authorized",
            "permissions",
            "grants",
            "roles",
            "principal",
            "credential",
            "secret",
        )
    )
    assert "identity-owner" not in repr(value)
    assert "ref-1" not in repr(value)


@pytest.mark.parametrize("value", [None, 1, True, [], {}, object(), lambda: None])
def test_security_context_ref_rejects_non_text_and_grant_shaped_objects(
    value: object,
) -> None:
    with pytest.raises(TypeError):
        SecurityContextRef(cast(str, value), "ref")
    with pytest.raises(TypeError):
        SecurityContextRef("issuer", cast(str, value))


def test_security_context_ref_immutable() -> None:
    value = SecurityContextRef("issuer", "ref")
    with pytest.raises(FrozenInstanceError):
        setattr(value, "reference", "changed")  # noqa: B010
    assert not hasattr(value, "__dict__")


# --- ExecutionContext ---------------------------------------------------------


def test_execution_context_valid_construction() -> None:
    value = _context()
    assert value.execution_id == ExecutionId("execution-1")
    assert value.causation is None
    assert value == replace(value)


def test_execution_context_tenant_mismatch_rejected() -> None:
    value = _context()
    with pytest.raises(ValueError, match="tenant mismatch"):
        replace(value, tenant_context=TenantContext(TenantId("other")))
    with pytest.raises(ValueError, match="tenant mismatch"):
        replace(value, causation=_operation("other", "parent"))


def test_execution_context_self_causation_rejected() -> None:
    value = _context()
    with pytest.raises(ValueError, match="itself"):
        replace(value, causation=value.operation)


def test_execution_context_accepts_valid_distinct_causation() -> None:
    value = _context()
    parent = _operation("tenant", "parent-op")
    assert replace(value, causation=parent).causation == parent


def test_execution_context_deadline_must_be_timezone_aware() -> None:
    value = _context()
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(value, deadline=datetime(2026, 1, 1))
    assert replace(value, deadline=None).deadline is None


@pytest.mark.parametrize("invalid", ["2026-01-01", 1, True, [], {}, lambda: None])
def test_execution_context_deadline_rejects_non_datetime(invalid: object) -> None:
    with pytest.raises(TypeError, match="must be datetime or None"):
        replace(_context(), deadline=cast(datetime, invalid))


def test_execution_context_deadline_not_acquired_from_wall_clock() -> None:
    # Constructing without a deadline never reads the clock; None is preserved.
    value = replace(_context(), deadline=None)
    assert value.deadline is None


@pytest.mark.parametrize(
    "field_name",
    [
        "execution_id",
        "operation",
        "tenant_context",
        "security_context_ref",
        "correlation_id",
    ],
)
def test_execution_context_required_fields_reject_wrong_type(field_name: str) -> None:
    value = _context()
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, lambda: None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(value, **{field_name: invalid})
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(value, **{field_name: None})


@pytest.mark.parametrize("field_name", ["trace_id", "causation"])
def test_execution_context_optional_fields_accept_none_but_reject_wrong_type(
    field_name: str,
) -> None:
    value = _context()
    assert cast(Callable[..., object], replace)(value, **{field_name: None})
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, lambda: None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(value, **{field_name: invalid})


def test_execution_context_immutable_and_stable_hash() -> None:
    value = _context()
    original_hash = hash(value)
    assert not hasattr(value, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(value, "execution_id", ExecutionId("other"))  # noqa: B010
    assert hash(value) == original_hash


def test_execution_context_has_no_bare_authorization_field() -> None:
    names = {field.name for field in fields(ExecutionContext)}
    assert names.isdisjoint(FORBIDDEN_AUTHORITY_FIELDS)
    value = _context()
    assert not any(hasattr(value, attr) for attr in FORBIDDEN_AUTHORITY_FIELDS)


def test_execution_context_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(ExecutionContext)
    for name, hint in hints.items():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object
        text = str(hint)
        assert "Any" not in text, f"{name} must not accept typing.Any"


def test_execution_context_rejects_callable_and_arbitrary_object_binding() -> None:
    value = _context()
    canaries: tuple[object, ...] = (lambda: None, object(), print, {"k": "v"})
    for field_name in (
        "execution_id",
        "operation",
        "tenant_context",
        "security_context_ref",
    ):
        for canary in canaries:
            with pytest.raises(TypeError):
                cast(Callable[..., object], replace)(value, **{field_name: canary})


# --- ExecutionResult ---------------------------------------------------------


def _error() -> ErrorDetail:
    cause = ErrorCause(
        ErrorCategory.VALIDATION_ERROR, _operation("tenant", "op"), "record-key"
    )
    return ErrorDetail(
        ErrorCategory.VALIDATION_ERROR, Recoverability.TERMINAL, (cause,)
    )


def test_execution_result_valid_construction() -> None:
    result = ExecutionResult(
        ExecutionId("execution-1"),
        ExecutionState.SUCCEEDED,
        EffectExtent.COMPLETED,
        None,
    )
    assert result.final_state is ExecutionState.SUCCEEDED
    assert result.effect is EffectExtent.COMPLETED
    assert result.error is None


def test_execution_result_preserves_unknown_effect_distinct_from_none() -> None:
    unknown = ExecutionResult(
        ExecutionId("e1"), ExecutionState.FAILED, EffectExtent.UNKNOWN, _error()
    )
    none_effect = ExecutionResult(
        ExecutionId("e2"), ExecutionState.FAILED, EffectExtent.NONE, _error()
    )
    assert unknown.effect is EffectExtent.UNKNOWN
    assert unknown.effect != none_effect.effect


@pytest.mark.parametrize(
    "state",
    [
        ExecutionState.CREATED,
        ExecutionState.ADMITTED,
        ExecutionState.RUNNING,
        ExecutionState.WAITING,
        ExecutionState.SUSPENDED,
        ExecutionState.CANCELLING,
    ],
)
def test_execution_result_rejects_nonterminal_state(state: ExecutionState) -> None:
    with pytest.raises(ValueError, match="terminal state"):
        ExecutionResult(ExecutionId("e1"), state, EffectExtent.NONE, None)


def test_execution_result_rejected_requires_no_effect() -> None:
    with pytest.raises(ValueError, match="EffectExtent.NONE"):
        ExecutionResult(
            ExecutionId("e1"),
            ExecutionState.REJECTED,
            EffectExtent.COMPLETED,
            None,
        )
    result = ExecutionResult(
        ExecutionId("e1"), ExecutionState.REJECTED, EffectExtent.NONE, None
    )
    assert result.effect is EffectExtent.NONE


@pytest.mark.parametrize("field_name", ["execution_id", "final_state", "effect"])
def test_execution_result_required_fields_reject_wrong_type(field_name: str) -> None:
    result = ExecutionResult(
        ExecutionId("e1"), ExecutionState.SUCCEEDED, EffectExtent.COMPLETED, None
    )
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, lambda: None, None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(result, **{field_name: invalid})


def test_execution_result_error_field_rejects_wrong_type() -> None:
    result = ExecutionResult(
        ExecutionId("e1"), ExecutionState.SUCCEEDED, EffectExtent.COMPLETED, None
    )
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, lambda: None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(result, **{"error": invalid})
    assert replace(result, error=_error()).error == _error()


def test_execution_result_immutable_and_stable_hash() -> None:
    result = ExecutionResult(
        ExecutionId("e1"), ExecutionState.SUCCEEDED, EffectExtent.COMPLETED, None
    )
    original_hash = hash(result)
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(result, "effect", EffectExtent.UNKNOWN)  # noqa: B010
    assert hash(result) == original_hash


def test_execution_result_is_not_outcome() -> None:
    result = ExecutionResult(
        ExecutionId("e1"), ExecutionState.SUCCEEDED, EffectExtent.COMPLETED, None
    )
    assert not hasattr(result, "outcome")
    assert type(result).__name__ != "Outcome"


def test_execution_result_has_no_bare_authorization_field() -> None:
    names = {field.name for field in fields(ExecutionResult)}
    assert names.isdisjoint(FORBIDDEN_AUTHORITY_FIELDS)


def test_execution_result_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(ExecutionResult)
    for name, hint in hints.items():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object
        assert "Any" not in str(hint), f"{name} must not accept typing.Any"
