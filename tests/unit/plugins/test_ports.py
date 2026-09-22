"""Gate-2 M5: ADR-006 SS8 -- discovered != inspected != validated != admitted
!= initialized != activated != catalog-published. Values here describe
lifecycle facts; none of them is itself an admission, activation, or
Catalog entry.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime
from typing import cast, get_type_hints

import pytest

from legoai.kernel.context import TenantContext
from legoai.kernel.identity import OperationId, TenantId
from legoai.kernel.versions import Version
from legoai.plugins.ports import (
    DiscoveredPluginRef,
    PluginAdmissionId,
    PluginLifecycleRecord,
    PluginLifecycleState,
    ValidationOutcome,
    ValidationResult,
)
from legoai.plugins.values import PluginId

FORBIDDEN_RUNTIME_FIELDS = {
    "authorized",
    "approved",
    "admitted",
    "active",
    "is_active",
    "trusted",
    "callable",
    "handler",
    "adapter",
    "provider",
    "factory",
    "secret",
    "credential",
}

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _plugin_id() -> PluginId:
    return PluginId("legoai", "deterministic-fixture")


def _discovered() -> DiscoveredPluginRef:
    return DiscoveredPluginRef(_plugin_id(), Version(0, 1, 0))


def _record(*, tenant: str = "tenant") -> PluginLifecycleRecord:
    return PluginLifecycleRecord(
        PluginAdmissionId("admission-1"),
        _plugin_id(),
        Version(0, 1, 0),
        TenantContext(TenantId(tenant)),
        PluginLifecycleState.VALIDATED,
        1,
        _EPOCH,
    )


# --- PluginLifecycleState -----------------------------------------------------


def test_plugin_lifecycle_state_exact_nine_canonical_members() -> None:
    assert {m.value for m in PluginLifecycleState} == {
        "discovered",
        "validated",
        "initialized",
        "active",
        "degraded",
        "stopping",
        "failed",
        "stopped",
        "retired",
    }
    assert len(PluginLifecycleState) == 9


# --- ValidationOutcome ----------------------------------------------------------


def test_validation_outcome_exact_two_members() -> None:
    assert {m.value for m in ValidationOutcome} == {"compatible", "incompatible"}


# --- PluginAdmissionId ------------------------------------------------------------


def test_plugin_admission_id_is_not_plugin_id_execution_id_or_operation_id() -> None:
    admission_id: object = PluginAdmissionId("same-text")
    operation_id: object = OperationId("same-text")
    assert admission_id != operation_id
    assert len({admission_id, operation_id}) == 2
    assert repr(PluginAdmissionId("sensitive-canary")) == "PluginAdmissionId()"


@pytest.mark.parametrize("value", [None, 1, True, [], {}, lambda: None])
def test_plugin_admission_id_no_coercion(value: object) -> None:
    with pytest.raises(TypeError, match="must be text"):
        PluginAdmissionId(cast(str, value))


# --- DiscoveredPluginRef -----------------------------------------------------------


def test_discovered_plugin_ref_valid_construction() -> None:
    ref = _discovered()
    assert ref.plugin_id == _plugin_id()
    assert ref == replace(ref)


@pytest.mark.parametrize("field_name", ["plugin_id", "release"])
def test_discovered_plugin_ref_rejects_wrong_type(field_name: str) -> None:
    ref = _discovered()
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, None, lambda: None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(ref, **{field_name: invalid})


# --- ValidationResult ---------------------------------------------------------


def test_validation_result_valid_construction() -> None:
    result = ValidationResult(_discovered(), ValidationOutcome.COMPATIBLE, _EPOCH)
    assert result.outcome is ValidationOutcome.COMPATIBLE


def test_validation_result_evaluated_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        ValidationResult(
            _discovered(), ValidationOutcome.COMPATIBLE, datetime(2026, 1, 1)
        )


@pytest.mark.parametrize("invalid", ["2026-01-01", 1, True, [], {}, lambda: None])
def test_validation_result_evaluated_at_rejects_non_datetime(invalid: object) -> None:
    with pytest.raises(TypeError, match="must be datetime"):
        ValidationResult(
            _discovered(), ValidationOutcome.COMPATIBLE, cast(datetime, invalid)
        )


@pytest.mark.parametrize("field_name", ["discovered", "outcome"])
def test_validation_result_rejects_wrong_type(field_name: str) -> None:
    result = ValidationResult(_discovered(), ValidationOutcome.COMPATIBLE, _EPOCH)
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, None, lambda: None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(result, **{field_name: invalid})


def test_validation_result_has_no_admission_shortcut() -> None:
    names = {f.name for f in fields(ValidationResult)}
    assert names.isdisjoint(FORBIDDEN_RUNTIME_FIELDS)
    result = ValidationResult(_discovered(), ValidationOutcome.COMPATIBLE, _EPOCH)
    assert not any(hasattr(result, attr) for attr in FORBIDDEN_RUNTIME_FIELDS)


def test_validation_result_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(ValidationResult)
    for hint in hints.values():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object


def test_validation_result_immutable() -> None:
    result = ValidationResult(_discovered(), ValidationOutcome.COMPATIBLE, _EPOCH)
    with pytest.raises(FrozenInstanceError):
        setattr(result, "outcome", ValidationOutcome.INCOMPATIBLE)  # noqa: B010


# --- PluginLifecycleRecord -----------------------------------------------------


def test_plugin_lifecycle_record_valid_construction() -> None:
    record = _record()
    assert record.state is PluginLifecycleState.VALIDATED
    assert record.revision == 1
    assert record == replace(record)


def test_plugin_lifecycle_record_revision_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        replace(_record(), revision=0)
    with pytest.raises(ValueError, match="positive"):
        replace(_record(), revision=-1)


@pytest.mark.parametrize("revision", [True, False, 1.0, "1", None])
def test_plugin_lifecycle_record_revision_rejects_non_int(revision: object) -> None:
    with pytest.raises(TypeError, match="must be an int"):
        cast(Callable[..., object], replace)(_record(), revision=revision)


def test_plugin_lifecycle_record_established_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(_record(), established_at=datetime(2026, 1, 1))


@pytest.mark.parametrize("invalid", ["2026-01-01", 1, True, [], {}, lambda: None])
def test_plugin_lifecycle_record_established_at_rejects_non_datetime(
    invalid: object,
) -> None:
    with pytest.raises(TypeError, match="must be datetime"):
        replace(_record(), established_at=cast(datetime, invalid))


@pytest.mark.parametrize(
    "field_name",
    ["admission_id", "plugin_id", "release", "tenant_context", "state"],
)
def test_plugin_lifecycle_record_required_fields_reject_wrong_type(
    field_name: str,
) -> None:
    record = _record()
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, lambda: None, None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(record, **{field_name: invalid})


def test_plugin_lifecycle_record_rejects_callable_and_arbitrary_object_binding() -> (
    None
):
    record = _record()
    canaries: tuple[object, ...] = (lambda: None, object(), print, {"k": "v"})
    for field_name in ("admission_id", "plugin_id", "tenant_context", "state"):
        for canary in canaries:
            with pytest.raises(TypeError):
                cast(Callable[..., object], replace)(record, **{field_name: canary})


def test_plugin_lifecycle_record_has_no_activation_or_authority_shortcut() -> None:
    names = {f.name for f in fields(PluginLifecycleRecord)}
    assert names.isdisjoint(FORBIDDEN_RUNTIME_FIELDS)
    assert not any(hasattr(_record(), attr) for attr in FORBIDDEN_RUNTIME_FIELDS)


def test_plugin_lifecycle_record_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(PluginLifecycleRecord)
    for name, hint in hints.items():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object
        assert "Any" not in str(hint), f"{name} must not accept typing.Any"


def test_plugin_lifecycle_record_immutable_and_stable_hash() -> None:
    record = _record()
    original_hash = hash(record)
    assert not hasattr(record, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(record, "state", PluginLifecycleState.ACTIVE)  # noqa: B010
    assert hash(record) == original_hash


def test_plugin_lifecycle_record_does_not_embed_declaration() -> None:
    # A separate runtime/admission representation: no PluginDeclaration
    # object is embedded, only plugin_id/release references (task SS4/SS9).
    record = _record()
    assert not hasattr(record, "declaration")
    assert not hasattr(record, "offers")
    assert not hasattr(record, "requirements")
