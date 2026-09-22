"""Gate-2 M8: ADR-009 -- deterministic in-memory Evidence custody. Historical
evidence of an authorization decision must remain readable after the
underlying Grant is revoked, without itself re-authorizing anything: current
authority is a live M4 concern this module never re-derives.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from legoai.evidence.ports import EvidenceConflictError, EvidenceId, EvidenceRecord
from legoai.evidence.values import EvidenceRequirement
from legoai.governance.ports import (
    AuthorizationDecision,
    AuthorizationOutcome,
    SecurityContext,
)
from legoai.governance.values import (
    Grant,
    GrantId,
    PolicyRef,
    Principal,
)
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
from legoai.reference.evidence import InMemoryEvidenceCustody, satisfies_requirement
from legoai.reference.governance import DeterministicAuthorizationEvaluator
from tests.support.governance import (
    InMemoryApprovalUseFake,
    InMemoryGrantStateFake,
    InMemoryPolicyCurrencyFake,
)

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


def _record(
    evidence_id: str, subject: object, *, tenant: str = "tenant"
) -> EvidenceRecord:
    return EvidenceRecord(
        EvidenceId(evidence_id),
        subject,  # type: ignore[arg-type]
        _principal("issuer"),
        TenantContext(TenantId(tenant)),
        "recorded content",
        _EPOCH,
    )


# --- record / read exact ---------------------------------------------------------


def test_record_then_read_exact() -> None:
    custody = InMemoryEvidenceCustody()
    record = _record("e1", _configuration_revision())
    custody.record(record)
    result = custody.read(EvidenceId("e1"), TenantContext(TenantId("tenant")))
    assert result == record


def test_read_missing_evidence_returns_none() -> None:
    custody = InMemoryEvidenceCustody()
    assert (
        custody.read(EvidenceId("missing"), TenantContext(TenantId("tenant"))) is None
    )


def test_read_does_not_substitute_latest_or_similar() -> None:
    custody = InMemoryEvidenceCustody()
    custody.record(_record("e1", _configuration_revision()))
    custody.record(_record("e2", _configuration_revision()))
    # Requesting "e3" (never recorded) must never fall back to e1/e2.
    assert custody.read(EvidenceId("e3"), TenantContext(TenantId("tenant"))) is None


# --- append-only / duplicate semantics ------------------------------------------


def test_exact_equivalent_resubmission_is_idempotent() -> None:
    custody = InMemoryEvidenceCustody()
    record = _record("e1", _configuration_revision())
    first = custody.record(record)
    second = custody.record(record)
    assert first == second == record


def test_conflicting_resubmission_raises_and_does_not_overwrite() -> None:
    custody = InMemoryEvidenceCustody()
    original = _record("e1", _configuration_revision())
    custody.record(original)
    conflicting = EvidenceRecord(
        EvidenceId("e1"),
        _configuration_revision(),
        _principal("issuer"),
        TenantContext(TenantId("tenant")),
        "a materially different content reference",
        _EPOCH,
    )
    with pytest.raises(EvidenceConflictError, match="different content"):
        custody.record(conflicting)
    # The original committed record must remain exactly as first recorded.
    assert custody.read(EvidenceId("e1"), TenantContext(TenantId("tenant"))) == original


def test_record_rejects_wrong_type_argument() -> None:
    custody = InMemoryEvidenceCustody()
    with pytest.raises(TypeError, match="record requires EvidenceRecord"):
        custody.record(cast(EvidenceRecord, object()))


def test_read_rejects_wrong_type_arguments() -> None:
    custody = InMemoryEvidenceCustody()
    with pytest.raises(TypeError, match="read requires EvidenceId"):
        custody.read(cast(EvidenceId, object()), TenantContext(TenantId("tenant")))
    with pytest.raises(TypeError, match="read requires TenantContext"):
        custody.read(EvidenceId("e1"), cast(TenantContext, object()))


def test_construction_does_not_commit_evidence() -> None:
    custody = InMemoryEvidenceCustody()
    _record("e1", _configuration_revision())  # constructed, never recorded
    assert custody.read(EvidenceId("e1"), TenantContext(TenantId("tenant"))) is None


# --- tenant isolation ------------------------------------------------------------


def test_tenant_isolation_no_cross_tenant_read() -> None:
    custody = InMemoryEvidenceCustody()
    record = _record("e1", _configuration_revision("tenant-a"), tenant="tenant-a")
    custody.record(record)
    assert custody.read(EvidenceId("e1"), TenantContext(TenantId("tenant-a"))) == record
    assert custody.read(EvidenceId("e1"), TenantContext(TenantId("tenant-b"))) is None


# --- exact subject / requirement satisfaction -----------------------------------


def test_exact_subject_operation_a_does_not_satisfy_operation_b() -> None:
    subject_a = _configuration_revision()
    subject_b = ConfigurationRevisionRef(
        subject_a.configuration, "r2", Version(0, 1, 0)
    )
    requirement_a = EvidenceRequirement(subject_a, "needs evidence for r1")
    record_b = _record("e1", subject_b)
    assert satisfies_requirement(requirement_a, record_b) is False


def test_matching_record_satisfies_requirement() -> None:
    subject = _configuration_revision()
    requirement = EvidenceRequirement(subject, "needs evidence")
    record = _record("e1", subject)
    assert satisfies_requirement(requirement, record) is True


def test_authorization_subject_record_never_satisfies_configuration_requirement() -> (
    None
):
    requirement = EvidenceRequirement(_configuration_revision(), "needs evidence")
    authorization_decision = AuthorizationDecision(
        AuthorizationOutcome.ALLOWED, _operation(), _EPOCH, None, None, None, None
    )
    record = _record("e1", authorization_decision)
    assert satisfies_requirement(requirement, record) is False


def test_satisfies_requirement_rejects_wrong_type_arguments() -> None:
    with pytest.raises(TypeError, match="EvidenceRequirement"):
        satisfies_requirement(object(), _record("e1", _configuration_revision()))  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="EvidenceRecord"):
        satisfies_requirement(
            EvidenceRequirement(_configuration_revision(), "x"),
            object(),  # type: ignore[arg-type]
        )


# --- historical authorization evidence survives revocation (task SS68) ---------


def test_historical_authorization_evidence_survives_grant_revocation_but_does_not_reauthorize() -> (
    None
):
    grantee = _principal("service")
    grant = Grant(
        GrantId("grant-1"),
        _principal("issuer"),
        grantee,
        TenantContext(TenantId("tenant")),
        "publish-configuration",
        "app:config",
        False,
        _EPOCH,
        _EPOCH + timedelta(days=1),
    )
    grant_state = InMemoryGrantStateFake()
    approval_use = InMemoryApprovalUseFake()
    policy_currency = InMemoryPolicyCurrencyFake()
    evaluator = DeterministicAuthorizationEvaluator(
        grant_state, approval_use, policy_currency
    )

    policy_ref = PolicyRef("policy-owner", "policy", Version(1, 0, 0))
    security_context = SecurityContext(
        grantee,
        TenantContext(TenantId("tenant")),
        _operation(),
        "publish-configuration",
        "app:config",
        grant,
        None,
        policy_ref,
        _EPOCH + timedelta(minutes=30),
    )
    decision = evaluator.evaluate(security_context)
    assert decision.outcome is AuthorizationOutcome.ALLOWED

    custody = InMemoryEvidenceCustody()
    evidence = _record("e1", decision)
    custody.record(evidence)

    # Now revoke the Grant in the live current-authority fake.
    grant_state.revoke(GrantId("grant-1"))

    # Historical evidence remains exactly readable...
    retrieved = custody.read(EvidenceId("e1"), TenantContext(TenantId("tenant")))
    assert retrieved is not None
    assert cast(AuthorizationDecision, retrieved.subject).outcome is (
        AuthorizationOutcome.ALLOWED
    )

    # ...but a *new* current-authority evaluation now correctly denies.
    new_decision = evaluator.evaluate(security_context)
    assert new_decision.outcome is AuthorizationOutcome.DENIED

    # The stored historical record is untouched by the new denial.
    still_retrieved = custody.read(EvidenceId("e1"), TenantContext(TenantId("tenant")))
    assert still_retrieved is not None
    assert cast(AuthorizationDecision, still_retrieved.subject).outcome is (
        AuthorizationOutcome.ALLOWED
    )
