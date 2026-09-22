"""Gate-2 M8: ADR-009 -- Evidence != Observation != log != trace != model
explanation != private chain-of-thought. EvidenceRequirement != EvidenceRecord;
a record's mere construction never commits it (that is the Port's job).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime
from typing import cast, get_type_hints

import pytest

from legoai.evidence.ports import EvidenceId, EvidenceRecord
from legoai.governance.ports import AuthorizationDecision, AuthorizationOutcome
from legoai.governance.values import Principal
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import (
    ApplicationId,
    OperationId,
    PrincipalId,
    TenantId,
)
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version

FORBIDDEN_RUNTIME_FIELDS = {
    "chain_of_thought",
    "hidden_reasoning",
    "private_reasoning",
    "scratchpad",
    "reasoning",
    "password",
    "token",
    "secret",
    "credential",
    "authorization_header",
    "private_key",
    "callable",
    "handler",
    "adapter",
    "connection",
    "logger",
}

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _principal(name: str) -> Principal:
    return Principal(PrincipalRef("identity-owner", PrincipalId(name)))


def _configuration_revision(tenant: str = "tenant") -> ConfigurationRevisionRef:
    return ConfigurationRevisionRef(
        ConfigurationRef(
            ApplicationRef(
                ReferenceScope("composition", TenantId(tenant)), ApplicationId("app")
            ),
            "config",
        ),
        "r1",
        Version(0, 1, 0),
    )


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


def _authorization_decision(tenant: str = "tenant") -> AuthorizationDecision:
    return AuthorizationDecision(
        AuthorizationOutcome.ALLOWED,
        _operation(tenant),
        _EPOCH,
        None,
        None,
        None,
        None,
    )


def _record_with_configuration_subject(*, tenant: str = "tenant") -> EvidenceRecord:
    return EvidenceRecord(
        EvidenceId("evidence-1"),
        _configuration_revision(tenant),
        _principal("issuer"),
        TenantContext(TenantId(tenant)),
        "source submission received",
        _EPOCH,
    )


def _record_with_authorization_subject(*, tenant: str = "tenant") -> EvidenceRecord:
    return EvidenceRecord(
        EvidenceId("evidence-2"),
        _authorization_decision(tenant),
        _principal("issuer"),
        TenantContext(TenantId(tenant)),
        "authorization evaluated",
        _EPOCH,
    )


# --- EvidenceId ----------------------------------------------------------------


def test_evidence_id_is_not_operation_id() -> None:
    evidence_id: object = EvidenceId("same-text")
    operation_id: object = OperationId("same-text")
    assert evidence_id != operation_id
    assert len({evidence_id, operation_id}) == 2
    assert repr(EvidenceId("sensitive-canary")) == "EvidenceId()"


@pytest.mark.parametrize("value", [None, 1, True, [], {}, lambda: None])
def test_evidence_id_no_coercion(value: object) -> None:
    with pytest.raises(TypeError, match="must be text"):
        EvidenceId(cast(str, value))


# --- EvidenceRecord: valid construction for both subject types -----------------


def test_evidence_record_valid_with_configuration_revision_subject() -> None:
    record = _record_with_configuration_subject()
    assert type(record.subject) is ConfigurationRevisionRef
    assert record == replace(record)


def test_evidence_record_valid_with_authorization_decision_subject() -> None:
    record = _record_with_authorization_subject()
    assert type(record.subject) is AuthorizationDecision


def test_evidence_record_rejects_other_subject_types() -> None:
    with pytest.raises(TypeError, match="subject must be"):
        EvidenceRecord(
            EvidenceId("e1"),
            cast(ConfigurationRevisionRef, "not-a-real-subject"),
            _principal("issuer"),
            TenantContext(TenantId("tenant")),
            "content",
            _EPOCH,
        )


# --- tenant consistency ---------------------------------------------------------


def test_evidence_record_subject_tenant_mismatch_rejected() -> None:
    with pytest.raises(ValueError, match="tenant mismatch"):
        EvidenceRecord(
            EvidenceId("e1"),
            _configuration_revision("tenant-a"),
            _principal("issuer"),
            TenantContext(TenantId("tenant-b")),
            "content",
            _EPOCH,
        )
    with pytest.raises(ValueError, match="tenant mismatch"):
        EvidenceRecord(
            EvidenceId("e2"),
            _authorization_decision("tenant-a"),
            _principal("issuer"),
            TenantContext(TenantId("tenant-b")),
            "content",
            _EPOCH,
        )


# --- structural validation ------------------------------------------------------


def test_evidence_record_recorded_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(_record_with_configuration_subject(), recorded_at=datetime(2026, 1, 1))


@pytest.mark.parametrize("invalid", ["2026-01-01", 1, True, [], {}, lambda: None])
def test_evidence_record_recorded_at_rejects_non_datetime(invalid: object) -> None:
    with pytest.raises(TypeError, match="must be datetime"):
        replace(
            _record_with_configuration_subject(), recorded_at=cast(datetime, invalid)
        )


def test_evidence_record_content_reference_rejects_empty() -> None:
    with pytest.raises(ValueError, match="1–256"):
        replace(_record_with_configuration_subject(), content_reference="")


@pytest.mark.parametrize("field_name", ["evidence_id", "issuer", "tenant_context"])
def test_evidence_record_required_fields_reject_wrong_type(field_name: str) -> None:
    record = _record_with_configuration_subject()
    invalid_inputs: tuple[object, ...] = ("raw", True, [], {}, 1, lambda: None, None)
    for invalid in invalid_inputs:
        with pytest.raises(TypeError):
            cast(Callable[..., object], replace)(record, **{field_name: invalid})


def test_evidence_record_rejects_callable_and_arbitrary_object_binding() -> None:
    record = _record_with_configuration_subject()
    canaries: tuple[object, ...] = (lambda: None, object(), print, {"k": "v"})
    for field_name in ("evidence_id", "issuer", "tenant_context", "subject"):
        for canary in canaries:
            with pytest.raises(TypeError):
                cast(Callable[..., object], replace)(record, **{field_name: canary})


def test_evidence_record_has_no_forbidden_field() -> None:
    names = {f.name for f in fields(EvidenceRecord)}
    assert names.isdisjoint(FORBIDDEN_RUNTIME_FIELDS)
    record = _record_with_configuration_subject()
    assert not any(hasattr(record, attr) for attr in FORBIDDEN_RUNTIME_FIELDS)


def test_evidence_record_has_no_arbitrary_payload_or_dict_field() -> None:
    hints = get_type_hints(EvidenceRecord)
    for name, hint in hints.items():
        assert hint is not dict
        assert getattr(hint, "__origin__", None) is not dict
        assert hint is not object
        assert "Any" not in str(hint), f"{name} must not accept typing.Any"


def test_evidence_record_immutable_and_stable_hash() -> None:
    record = _record_with_configuration_subject()
    original_hash = hash(record)
    assert not hasattr(record, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(record, "content_reference", "changed")  # noqa: B010
    assert hash(record) == original_hash


def test_evidence_record_does_not_carry_secret_material_field() -> None:
    record = _record_with_configuration_subject()
    for attr in ("password", "token", "secret", "credential", "authorization_header"):
        assert not hasattr(record, attr)


def test_historical_authorization_evidence_does_not_reauthorize() -> None:
    # Recording that an ALLOWED decision occurred is only a historical fact:
    # the record has no field that could be reinterpreted as current
    # authority, and no method exists to "re-apply" it.
    record = _record_with_authorization_subject()
    assert not hasattr(record, "authorize")
    assert not hasattr(record, "reauthorize")
    assert not hasattr(record, "currently_valid")
