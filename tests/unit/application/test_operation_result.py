"""F4: operation/result/duty value tests (ADR-003/004/008/009)."""

from __future__ import annotations

import pytest

from legoai.application.values import (
    ComposedConfiguration,
    ConfigurationPublicationOperation,
    ConfigurationPublicationResult,
    ConfigurationSourceSubmissionDuty,
    OperationStage,
)
from legoai.evidence.values import EvidenceRequirement
from legoai.governance.values import Principal
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorDetail, Recoverability
from legoai.kernel.identity import ApplicationId, OperationId, PrincipalId, TenantId
from legoai.kernel.provenance import DutyId, DutyKind
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    OwnerRevision,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.reference.application.configuration import compose_configuration

VERSION = Version(0, 1, 0)


def _target(
    tenant: str = "t1",
    owner: str = "owner1",
    app: str = "app1",
    instance: str = "inst1",
) -> ConfigurationRef:
    scope = ReferenceScope(owner, TenantId(tenant))
    return ConfigurationRef(ApplicationRef(scope, ApplicationId(app)), instance)


def _operation_ref(target: ConfigurationRef, op_id: str = "op1") -> OperationRef:
    return OperationRef(target, OperationId(op_id), "test-fixture")


def _principal(pid: str = "p1") -> Principal:
    return Principal(PrincipalRef("issuer1", PrincipalId(pid)))


def _candidate(target: ConfigurationRef) -> ComposedConfiguration:
    return compose_configuration(
        target, (), contract_version=VERSION, interpretation_version=VERSION
    )


def _duty_id() -> DutyId:
    return DutyId("duty-1")


class TestConfigurationPublicationOperation:
    def test_valid_construction_with_expected_absence(self) -> None:
        target = _target()
        op = ConfigurationPublicationOperation(
            operation=_operation_ref(target),
            target=target,
            expected_revision=None,
            candidate=_candidate(target),
            requested_by=_principal(),
        )
        assert op.expected_revision is None

    def test_valid_construction_with_expected_revision(self) -> None:
        target = _target()
        expected = OwnerRevision(target, 3)
        op = ConfigurationPublicationOperation(
            operation=_operation_ref(target),
            target=target,
            expected_revision=expected,
            candidate=_candidate(target),
            requested_by=_principal(),
        )
        assert op.expected_revision == expected

    def test_operation_subject_must_match_target(self) -> None:
        target = _target()
        other = _target(instance="other")
        with pytest.raises(ValueError):
            ConfigurationPublicationOperation(
                operation=_operation_ref(other),
                target=target,
                expected_revision=None,
                candidate=_candidate(target),
                requested_by=_principal(),
            )

    def test_expected_revision_subject_mismatch_rejected(self) -> None:
        target = _target()
        other = _target(instance="other")
        with pytest.raises(ValueError):
            ConfigurationPublicationOperation(
                operation=_operation_ref(target),
                target=target,
                expected_revision=OwnerRevision(other, 1),
                candidate=_candidate(target),
                requested_by=_principal(),
            )

    def test_candidate_target_mismatch_rejected(self) -> None:
        target = _target()
        other = _target(instance="other")
        with pytest.raises(ValueError):
            ConfigurationPublicationOperation(
                operation=_operation_ref(target),
                target=target,
                expected_revision=None,
                candidate=_candidate(other),
                requested_by=_principal(),
            )

    def test_wrong_types_rejected(self) -> None:
        target = _target()
        with pytest.raises(TypeError):
            ConfigurationPublicationOperation(
                operation="not-a-ref",  # type: ignore[arg-type]
                target=target,
                expected_revision=None,
                candidate=_candidate(target),
                requested_by=_principal(),
            )
        with pytest.raises(TypeError):
            ConfigurationPublicationOperation(
                operation=_operation_ref(target),
                target=target,
                expected_revision=None,
                candidate=_candidate(target),
                requested_by="not-a-principal",  # type: ignore[arg-type]
            )

    def test_frozen(self) -> None:
        target = _target()
        op = ConfigurationPublicationOperation(
            operation=_operation_ref(target),
            target=target,
            expected_revision=None,
            candidate=_candidate(target),
            requested_by=_principal(),
        )
        with pytest.raises(AttributeError):
            op.target = _target(instance="other")  # type: ignore[misc]  # noqa: B010


class TestConfigurationPublicationResult:
    def test_committed_result_valid(self) -> None:
        target = _target()
        op = _operation_ref(target)
        head = OwnerRevision(target, 1)
        published = ConfigurationRevisionRef(target, "r1", VERSION)
        result = ConfigurationPublicationResult(
            operation=op,
            stage=OperationStage.COMMITTED,
            resulting_revision=head,
            published=published,
            effect=EffectExtent.COMPLETED,
            error=None,
            duties=(_duty_id(),),
        )
        assert result.stage is OperationStage.COMMITTED

    def test_committed_result_cannot_carry_error(self) -> None:
        target = _target()
        with pytest.raises(ValueError):
            ConfigurationPublicationResult(
                operation=_operation_ref(target),
                stage=OperationStage.COMMITTED,
                resulting_revision=OwnerRevision(target, 1),
                published=ConfigurationRevisionRef(target, "r1", VERSION),
                effect=EffectExtent.COMPLETED,
                error=ErrorDetail(ErrorCategory.CONFLICT, Recoverability.TERMINAL, ()),
                duties=(),
            )

    def test_committed_result_requires_revision_and_published(self) -> None:
        target = _target()
        with pytest.raises(ValueError):
            ConfigurationPublicationResult(
                operation=_operation_ref(target),
                stage=OperationStage.COMMITTED,
                resulting_revision=None,
                published=None,
                effect=EffectExtent.COMPLETED,
                error=None,
                duties=(),
            )

    def test_rejected_result_requires_error(self) -> None:
        target = _target()
        with pytest.raises(ValueError):
            ConfigurationPublicationResult(
                operation=_operation_ref(target),
                stage=OperationStage.REJECTED,
                resulting_revision=None,
                published=None,
                effect=EffectExtent.NONE,
                error=None,
                duties=(),
            )

    def test_rejected_result_cannot_carry_revision(self) -> None:
        target = _target()
        with pytest.raises(ValueError):
            ConfigurationPublicationResult(
                operation=_operation_ref(target),
                stage=OperationStage.REJECTED,
                resulting_revision=OwnerRevision(target, 1),
                published=None,
                effect=EffectExtent.NONE,
                error=ErrorDetail(ErrorCategory.CONFLICT, Recoverability.TERMINAL, ()),
                duties=(),
            )

    def test_rejected_result_cannot_carry_duties(self) -> None:
        target = _target()
        with pytest.raises(ValueError):
            ConfigurationPublicationResult(
                operation=_operation_ref(target),
                stage=OperationStage.REJECTED,
                resulting_revision=None,
                published=None,
                effect=EffectExtent.NONE,
                error=ErrorDetail(ErrorCategory.CONFLICT, Recoverability.TERMINAL, ()),
                duties=(_duty_id(),),
            )

    def test_published_and_revision_subject_must_match(self) -> None:
        target = _target()
        other = _target(instance="other")
        with pytest.raises(ValueError):
            ConfigurationPublicationResult(
                operation=_operation_ref(target),
                stage=OperationStage.COMMITTED,
                resulting_revision=OwnerRevision(target, 1),
                published=ConfigurationRevisionRef(other, "r1", VERSION),
                effect=EffectExtent.COMPLETED,
                error=None,
                duties=(),
            )

    def test_effect_extent_independent_of_stage(self) -> None:
        # UNKNOWN effect is representable on a committed result (SS9 of
        # design: effect/coverage is a separate axis from stage/error).
        target = _target()
        result = ConfigurationPublicationResult(
            operation=_operation_ref(target),
            stage=OperationStage.COMMITTED,
            resulting_revision=OwnerRevision(target, 1),
            published=ConfigurationRevisionRef(target, "r1", VERSION),
            effect=EffectExtent.UNKNOWN,
            error=None,
            duties=(),
        )
        assert result.effect is EffectExtent.UNKNOWN

    def test_duties_must_be_tuple_of_duty_id(self) -> None:
        target = _target()
        with pytest.raises(TypeError):
            ConfigurationPublicationResult(
                operation=_operation_ref(target),
                stage=OperationStage.COMMITTED,
                resulting_revision=OwnerRevision(target, 1),
                published=ConfigurationRevisionRef(target, "r1", VERSION),
                effect=EffectExtent.COMPLETED,
                error=None,
                duties=["not-a-duty-id"],  # type: ignore[arg-type]
            )

    def test_frozen(self) -> None:
        target = _target()
        result = ConfigurationPublicationResult(
            operation=_operation_ref(target),
            stage=OperationStage.COMMITTED,
            resulting_revision=OwnerRevision(target, 1),
            published=ConfigurationRevisionRef(target, "r1", VERSION),
            effect=EffectExtent.COMPLETED,
            error=None,
            duties=(),
        )
        with pytest.raises(AttributeError):
            result.stage = OperationStage.REJECTED  # type: ignore[misc]  # noqa: B010


class TestConfigurationSourceSubmissionDuty:
    def _valid_duty(
        self, target: ConfigurationRef | None = None
    ) -> ConfigurationSourceSubmissionDuty:
        target = target or _target()
        published = ConfigurationRevisionRef(target, "r1", VERSION)
        op = _operation_ref(target)
        return ConfigurationSourceSubmissionDuty(
            duty_id=_duty_id(),
            kind=DutyKind("source-submission"),
            operation=op,
            published=published,
            responsible_principal=_principal(),
            tenant_context=TenantContext(target.application.scope.tenant_id),
            requirement=EvidenceRequirement(published, "evidence needed"),
        )

    def test_valid_construction(self) -> None:
        duty = self._valid_duty()
        assert duty.kind == DutyKind("source-submission")

    def test_operation_subject_must_match_published_configuration(self) -> None:
        target = _target()
        other = _target(instance="other")
        published = ConfigurationRevisionRef(target, "r1", VERSION)
        with pytest.raises(ValueError):
            ConfigurationSourceSubmissionDuty(
                duty_id=_duty_id(),
                kind=DutyKind("source-submission"),
                operation=_operation_ref(other),
                published=published,
                responsible_principal=_principal(),
                tenant_context=TenantContext(target.application.scope.tenant_id),
                requirement=EvidenceRequirement(published, "evidence needed"),
            )

    def test_tenant_mismatch_rejected(self) -> None:
        target = _target()
        published = ConfigurationRevisionRef(target, "r1", VERSION)
        with pytest.raises(ValueError):
            ConfigurationSourceSubmissionDuty(
                duty_id=_duty_id(),
                kind=DutyKind("source-submission"),
                operation=_operation_ref(target),
                published=published,
                responsible_principal=_principal(),
                tenant_context=TenantContext(TenantId("wrong-tenant")),
                requirement=EvidenceRequirement(published, "evidence needed"),
            )

    def test_requirement_subject_mismatch_rejected(self) -> None:
        target = _target()
        published = ConfigurationRevisionRef(target, "r1", VERSION)
        other_published = ConfigurationRevisionRef(target, "r2", VERSION)
        with pytest.raises(ValueError):
            ConfigurationSourceSubmissionDuty(
                duty_id=_duty_id(),
                kind=DutyKind("source-submission"),
                operation=_operation_ref(target),
                published=published,
                responsible_principal=_principal(),
                tenant_context=TenantContext(target.application.scope.tenant_id),
                requirement=EvidenceRequirement(other_published, "evidence needed"),
            )

    def test_wrong_types_rejected(self) -> None:
        target = _target()
        published = ConfigurationRevisionRef(target, "r1", VERSION)
        with pytest.raises(TypeError):
            ConfigurationSourceSubmissionDuty(
                duty_id="not-a-duty-id",  # type: ignore[arg-type]
                kind=DutyKind("source-submission"),
                operation=_operation_ref(target),
                published=published,
                responsible_principal=_principal(),
                tenant_context=TenantContext(target.application.scope.tenant_id),
                requirement=EvidenceRequirement(published, "evidence needed"),
            )

    def test_frozen(self) -> None:
        duty = self._valid_duty()
        with pytest.raises(AttributeError):
            duty.duty_id = DutyId("other")  # type: ignore[misc]  # noqa: B010


class TestOperationStage:
    def test_exactly_two_members(self) -> None:
        assert {member.name for member in OperationStage} == {"COMMITTED", "REJECTED"}
