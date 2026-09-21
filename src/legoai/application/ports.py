"""F4 internal configuration-owner storage semantics, not a public runtime API.

Operating owners must enforce current ADR-005 access before every mutation/read,
including retained-result disclosure. Construction or Protocol conformance does
not establish authority, custody or durability. Cross-owner records belong here
under ADR-002; Application values remain independent of Evidence/Governance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol

from legoai.application.values import ComposedConfiguration
from legoai.evidence.values import SourceRequirement, _utc
from legoai.governance.values import OperationContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorDetail
from legoai.kernel.identity import ApplicationId, ObligationId, _validate
from legoai.kernel.references import (
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    OwnerRevision,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version


def _require(value: object, kind: type[object]) -> None:
    """Local exact-type validation; no authority or reflective construction."""
    if type(value) is not kind:
        raise TypeError("incorrect configuration contract value type")


def _positive(value: int) -> None:
    _require(value, int)
    if value < 1:
        raise ValueError("revision or limit must be positive")


class ExpectedAbsence(Enum):
    ABSENT = "expected absence"


class NoSourceDuty(Enum):
    NOT_APPLICABLE = "post-commit duty explicitly not applicable"


class ObligationStatus(Enum):
    PENDING = "pending"
    SATISFIED = "satisfied"
    FAILED = "failed"
    REQUIRES_INTERVENTION = "requires intervention"


class DutyAction(Enum):
    SUBMIT_SOURCE_FACT = "submit exact source fact under pinned requirements"


class CoverageExtent(Enum):
    INTACT_STORE_LIFETIME = "all submissions during intact non-restored store lifetime"
    UNKNOWN = "coverage unknown"


class AcknowledgmentStage(Enum):
    """Owner-result acknowledgment, NOT a canonical Execution lifecycle state."""

    OWNER_COMMIT = "owner commit"


@dataclass(frozen=True, slots=True)
class SourceDutyPlan:
    responsible: PrincipalRef
    reconciliation_authority: PrincipalRef
    requirements: tuple[SourceRequirement, ...]

    def __post_init__(self) -> None:
        _require(self.responsible, PrincipalRef)
        _require(self.reconciliation_authority, PrincipalRef)
        _require(self.requirements, tuple)
        if not 1 <= len(self.requirements) <= 8:
            raise ValueError("duty requires 1-8 requirements")
        for item in self.requirements:
            _require(item, SourceRequirement)
        if len({item.requirement for item in self.requirements}) != len(
            self.requirements
        ):
            raise ValueError("duplicate requirement reference")


@dataclass(frozen=True, slots=True)
class PublicationDescriptor:
    """Deterministic equality defines exact operation meaning (ADR-008).

    Kind is this publication-specific record type. Source provenance, requester,
    original guard, versions and duty requirement order are material. Transport
    request/trace/correlation/time are NOT material. No hash/JSON/repr comparison.
    """

    candidate: ComposedConfiguration
    requester: PrincipalRef
    expected: ExpectedAbsence | OwnerRevision
    source_duty: NoSourceDuty | SourceDutyPlan
    contract_version: Version
    equivalence_version: Version

    def __post_init__(self) -> None:
        _require(self.candidate, ComposedConfiguration)
        _require(self.requester, PrincipalRef)
        _require(self.contract_version, Version)
        _require(self.equivalence_version, Version)
        if type(self.expected) not in (ExpectedAbsence, OwnerRevision):
            raise TypeError("expected absence or scoped OwnerRevision required")
        if (
            isinstance(self.expected, OwnerRevision)
            and self.expected.subject != self.candidate.target
        ):
            raise ValueError("expected head subject mismatch")
        if type(self.source_duty) not in (NoSourceDuty, SourceDutyPlan):
            raise TypeError("explicit duty applicability required")
        if isinstance(self.source_duty, SourceDutyPlan):
            for requirement in self.source_duty.requirements:
                if (
                    requirement.requirement.scope.tenant_id
                    != self.candidate.target.application.scope.tenant_id
                ):
                    raise ValueError("duty tenant mismatch")


@dataclass(frozen=True, slots=True)
class PublishConfiguration:
    descriptor: PublicationDescriptor
    context: OperationContext
    observed_at: datetime
    uncertainty_microseconds: int

    def __post_init__(self) -> None:
        _require(self.descriptor, PublicationDescriptor)
        _require(self.context, OperationContext)
        if self.context.operation.subject != self.descriptor.candidate.target:
            raise ValueError("publication subject mismatch")
        if self.context.operation.contract_identity != "configuration-publication":
            raise ValueError("unsupported operation contract")
        if self.context.originating_requester.reference != self.descriptor.requester:
            raise ValueError("original requester mismatch")
        _utc(self.observed_at)
        _require(self.uncertainty_microseconds, int)
        if self.uncertainty_microseconds < 0:
            raise ValueError("negative observation uncertainty")


@dataclass(frozen=True, slots=True)
class Coverage:
    """Complete coverage only for the declared intact store lifetime.

    Fake lifetime ends at teardown and covers no crashes. A later operating
    backend must qualify its retention/failure scope before asserting completeness;
    this label alone proves neither freshness nor resistance to restored images.
    """

    store_id: str = field(repr=False)
    subject: ConfigurationRef
    extent: CoverageExtent

    def __post_init__(self) -> None:
        _validate(self.store_id)
        _require(self.subject, ConfigurationRef)
        _require(self.extent, CoverageExtent)


@dataclass(frozen=True, slots=True)
class DutyRef:
    subject: ConfigurationRef
    obligation_id: ObligationId

    def __post_init__(self) -> None:
        _require(self.subject, ConfigurationRef)
        _require(self.obligation_id, ObligationId)


@dataclass(frozen=True, slots=True)
class ObligationRevision:
    reference: DutyRef
    value: int

    def __post_init__(self) -> None:
        _require(self.reference, DutyRef)
        _positive(self.value)


@dataclass(frozen=True, slots=True)
class ConfigurationHead:
    revision: OwnerRevision
    selected: ConfigurationRevisionRef

    def __post_init__(self) -> None:
        _require(self.revision, OwnerRevision)
        _require(self.selected, ConfigurationRevisionRef)
        if self.revision.subject != self.selected.configuration:
            raise ValueError("head subject mismatch")


@dataclass(frozen=True, slots=True)
class PublishedConfiguration:
    head: ConfigurationHead
    original: PublishConfiguration
    predecessor: ConfigurationRevisionRef | None
    duty: DutyRef | None

    def __post_init__(self) -> None:
        _require(self.head, ConfigurationHead)
        _require(self.original, PublishConfiguration)
        subject = self.original.descriptor.candidate.target
        if self.head.revision.subject != subject:
            raise ValueError("published subject mismatch")
        if (
            self.head.selected.contract_version
            != self.original.descriptor.candidate.effective.contract_version
        ):
            raise ValueError("published interpretation mismatch")
        if self.predecessor is not None:
            _require(self.predecessor, ConfigurationRevisionRef)
            if (
                self.predecessor.configuration != subject
                or self.predecessor == self.head.selected
            ):
                raise ValueError("invalid predecessor")
        expected = self.original.descriptor.expected
        if isinstance(expected, OwnerRevision):
            if (
                self.predecessor is None
                or self.head.revision.value != expected.value + 1
            ):
                raise ValueError("publication must be a scoped successor")
        elif self.predecessor is not None or self.head.revision.value != 1:
            raise ValueError("creation requires first head and no predecessor")
        if self.duty is not None:
            _require(self.duty, DutyRef)
            if self.duty.subject != subject:
                raise ValueError("duty subject mismatch")
        if isinstance(self.original.descriptor.source_duty, SourceDutyPlan) != (
            self.duty is not None
        ):
            raise ValueError("duty applicability mismatch")


@dataclass(frozen=True, slots=True)
class PublicationResult:
    record: PublishedConfiguration
    coverage: Coverage

    def __post_init__(self) -> None:
        _require(self.record, PublishedConfiguration)
        _require(self.coverage, Coverage)
        if self.record.head.revision.subject != self.coverage.subject:
            raise ValueError("result coverage scope mismatch")

    @property
    def stage(self) -> AcknowledgmentStage:
        return AcknowledgmentStage.OWNER_COMMIT

    @property
    def effect(self) -> EffectExtent:
        return EffectExtent.COMPLETED


@dataclass(frozen=True, slots=True)
class StorageFailure:
    """Unretained response; not a complete operational CTR-011 error envelope.

    NONE concerns this request's attempted mutation, not an earlier conflicting
    operation's committed effect. UNKNOWN calls for reconciliation, never blind
    retry. Operating owner supplies safe correlation/time/disclosure handling.
    """

    subject: ConfigurationRef
    error: ErrorDetail
    effect: EffectExtent

    def __post_init__(self) -> None:
        _require(self.subject, ConfigurationRef)
        _require(self.error, ErrorDetail)
        _require(self.effect, EffectExtent)
        if self.effect not in (EffectExtent.NONE, EffectExtent.UNKNOWN):
            raise ValueError("atomic failure extent must be none or unknown")


@dataclass(frozen=True, slots=True)
class HeadQuery:
    subject: ConfigurationRef

    def __post_init__(self) -> None:
        _require(self.subject, ConfigurationRef)


@dataclass(frozen=True, slots=True)
class RevisionQuery:
    reference: ConfigurationRevisionRef

    def __post_init__(self) -> None:
        _require(self.reference, ConfigurationRevisionRef)


@dataclass(frozen=True, slots=True)
class OperationQuery:
    operation: OperationRef

    def __post_init__(self) -> None:
        _require(self.operation, OperationRef)
        if (
            type(self.operation.subject) is not ConfigurationRef
            or self.operation.contract_identity != "configuration-publication"
        ):
            raise ValueError("status requires configuration publication scope")


@dataclass(frozen=True, slots=True)
class LookupAbsence:
    """Missing result: known absence ONLY when coverage explicitly establishes it."""

    query: HeadQuery | RevisionQuery | OperationQuery
    coverage: Coverage

    def __post_init__(self) -> None:
        _require(self.coverage, Coverage)
        if type(self.query) is HeadQuery:
            subject = self.query.subject
        elif type(self.query) is RevisionQuery:
            subject = self.query.reference.configuration
        elif type(self.query) is OperationQuery:
            operation_subject = self.query.operation.subject
            if not isinstance(operation_subject, ConfigurationRef):
                raise ValueError("configuration operation scope required")
            subject = operation_subject
        else:
            raise TypeError("absence requires a typed query")
        if subject != self.coverage.subject:
            raise ValueError("lookup coverage scope mismatch")


@dataclass(frozen=True, slots=True)
class PendingSourceDuty:
    """Exact source fact, NOT an Evidence record or custody receipt.

    Requirements, responsible Principal, reconciliation authority and observation
    time/uncertainty are retained through the original publication. No repair or
    later observations are fabricated; initial status/revision only.
    """

    revision: ObligationRevision
    source: PublishedConfiguration

    def __post_init__(self) -> None:
        _require(self.revision, ObligationRevision)
        _require(self.source, PublishedConfiguration)
        if self.source.duty != self.revision.reference or self.revision.value != 1:
            raise ValueError("pending duty requires matching initial revision")

    @property
    def status(self) -> ObligationStatus:
        return ObligationStatus.PENDING

    @property
    def next_safe_action(self) -> DutyAction:
        return DutyAction.SUBMIT_SOURCE_FACT


@dataclass(frozen=True, slots=True)
class DutyKey:
    """Binary lexicographic continuation key, never a database rowid."""

    application_id: ApplicationId
    instance: str = field(repr=False)
    created_head: int
    obligation_id: ObligationId

    def __post_init__(self) -> None:
        _require(self.application_id, ApplicationId)
        _require(self.obligation_id, ObligationId)
        _validate(self.instance)
        _positive(self.created_head)

    def ordering(self) -> tuple[str, str, int, str]:
        return (
            self.application_id.value,
            self.instance,
            self.created_head,
            self.obligation_id.value,
        )


@dataclass(frozen=True, slots=True)
class DutyCursor:
    store_id: str = field(repr=False)
    scope: ReferenceScope
    status: ObligationStatus
    query_version: Version
    subject: ConfigurationRef | None
    last: DutyKey

    def __post_init__(self) -> None:
        _validate(self.store_id)
        _require(self.scope, ReferenceScope)
        _require(self.status, ObligationStatus)
        _require(self.query_version, Version)
        _require(self.last, DutyKey)
        if self.subject is not None:
            _require(self.subject, ConfigurationRef)
            if (
                self.subject.application.scope != self.scope
                or self.subject.application.application_id != self.last.application_id
                or self.subject.instance != self.last.instance
            ):
                raise ValueError("cursor subject/key mismatch")


@dataclass(frozen=True, slots=True)
class DutyQuery:
    scope: ReferenceScope
    status: ObligationStatus
    limit: int
    query_version: Version
    subject: ConfigurationRef | None
    cursor: DutyCursor | None

    def __post_init__(self) -> None:
        _require(self.scope, ReferenceScope)
        _require(self.status, ObligationStatus)
        _require(self.query_version, Version)
        _positive(self.limit)
        if self.limit > 128:
            raise ValueError("page limit exceeds 128")
        if self.subject is not None:
            _require(self.subject, ConfigurationRef)
            if self.subject.application.scope != self.scope:
                raise ValueError("query subject scope mismatch")
        if self.cursor is not None:
            _require(self.cursor, DutyCursor)
            if (
                self.cursor.scope,
                self.cursor.status,
                self.cursor.query_version,
                self.cursor.subject,
            ) != (self.scope, self.status, self.query_version, self.subject):
                raise ValueError("cursor cannot cross scope/status/query version")


@dataclass(frozen=True, slots=True)
class DutyPage:
    query: DutyQuery
    duties: tuple[PendingSourceDuty, ...]
    continuation: DutyCursor | None

    def __post_init__(self) -> None:
        _require(self.query, DutyQuery)
        _require(self.duties, tuple)
        if len(self.duties) > self.query.limit:
            raise ValueError("page exceeds bound")
        previous = (
            self.query.cursor.last.ordering() if self.query.cursor is not None else None
        )
        for duty in self.duties:
            _require(duty, PendingSourceDuty)
            subject = duty.revision.reference.subject
            if (
                subject.application.scope != self.query.scope
                or duty.status is not self.query.status
                or (self.query.subject is not None and subject != self.query.subject)
            ):
                raise ValueError("page duty scope/status mismatch")
            key = DutyKey(
                subject.application.application_id,
                subject.instance,
                duty.source.head.revision.value,
                duty.revision.reference.obligation_id,
            )
            if previous is not None and key.ordering() <= previous:
                raise ValueError("page keys must strictly advance")
            previous = key.ordering()
        if self.continuation is not None:
            _require(self.continuation, DutyCursor)
            if (
                previous is None
                or not self.duties
                or self.continuation.last.ordering() != previous
            ):
                raise ValueError("continuation must bind last returned key")
            DutyQuery(
                self.query.scope,
                self.query.status,
                self.query.limit,
                self.query.query_version,
                self.query.subject,
                self.continuation,
            )
            if (
                self.query.cursor is not None
                and self.query.cursor.store_id != self.continuation.store_id
            ):
                raise ValueError("page continuation store mismatch")


@dataclass(frozen=True, slots=True)
class DutyQueryFailure:
    query: DutyQuery
    error: ErrorDetail

    def __post_init__(self) -> None:
        _require(self.query, DutyQuery)
        _require(self.error, ErrorDetail)


class ConfigurationOwnerStore(Protocol):
    """Owner-local atomic head/history/result/duty publication and bounded reads.

    Equivalent retained O precedes stale-H checks. New O requires original guard
    and qualified coverage. No rejected request becomes a retained commit.
    Historical reads never return latest or recompose. No delete/repair/rollback.
    Synchronous implementations declare wait/failure coverage; no hidden retry.
    Pages are current observations, complete in quiescent state only; a fresh
    scan is required after restart or live key/status movement.
    """

    def publish(
        self, command: PublishConfiguration
    ) -> PublicationResult | StorageFailure: ...
    def get_head(
        self, query: HeadQuery
    ) -> ConfigurationHead | LookupAbsence | StorageFailure: ...
    def get_revision(
        self, query: RevisionQuery
    ) -> PublishedConfiguration | LookupAbsence | StorageFailure: ...
    def get_operation_result(
        self, query: OperationQuery
    ) -> PublicationResult | LookupAbsence | StorageFailure: ...
    def list_obligations(self, query: DutyQuery) -> DutyPage | DutyQueryFailure: ...
