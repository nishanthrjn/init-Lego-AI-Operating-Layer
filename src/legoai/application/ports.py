"""Internal configuration-owner semantic storage boundary (Gate-1 F4).

No live authorization: the operating owner must enforce ADR-005 before reads,
retransmission disclosure and mutation. These are internal semantic components,
not a complete operational CTR-011 error envelope or a public runtime API.
Values crossing owners are composed here under ADR-002, never in owner leaves.
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
    ConfigurationRef, ConfigurationRevisionRef, OperationRef, OwnerRevision,
    PrincipalRef, ReferenceScope,
)
from legoai.kernel.versions import Version


class ExpectedAbsence(Enum):
    ABSENT = "expected absence"


class NoSourceDuty(Enum):
    NOT_APPLICABLE = "post-commit source duty not applicable"


class ObligationStatus(Enum):
    PENDING = "pending"
    SATISFIED = "satisfied"
    FAILED = "failed"
    REQUIRES_INTERVENTION = "requires intervention"


class DutyAction(Enum):
    SUBMIT_SOURCE_FACT = "submit exact source fact under requirement"


class CoverageExtent(Enum):
    INTACT_STORE_LIFETIME = "all submissions during intact non-restored store lifetime"
    UNKNOWN = "coverage unknown"


class AcknowledgmentStage(Enum):
    """Owner-result stage, NOT a canonical Execution lifecycle state."""

    OWNER_COMMIT = "owner commit"


def _positive(value: int) -> None:
    if type(value) is not int:
        raise TypeError("revision or limit must be an integer")
    if value < 1:
        raise ValueError("revision or limit must be positive")


@dataclass(frozen=True, slots=True)
class SourceDutyPlan:
    responsible: PrincipalRef
    reconciliation_authority: PrincipalRef
    requirements: tuple[SourceRequirement, ...]

    def __post_init__(self) -> None:
        if type(self.responsible) is not PrincipalRef or type(self.reconciliation_authority) is not PrincipalRef:
            raise TypeError("duty requires explicit Principal references")
        if type(self.requirements) is not tuple:
            raise TypeError("requirements must be an immutable tuple")
        if not 1 <= len(self.requirements) <= 8:
            raise ValueError("duty requires 1-8 requirements")
        if any(type(item) is not SourceRequirement for item in self.requirements):
            raise TypeError("invalid requirement value")
        if len({item.requirement for item in self.requirements}) != len(self.requirements):
            raise ValueError("duplicate requirement reference")


@dataclass(frozen=True, slots=True)
class PublicationDescriptor:
    """Exact semantic equivalence; kind is this publication-specific record type.

    Request/correlation/trace/time are excluded. Provenance, original requester,
    expected guard and source duties ARE material even for equal settings.
    Version fields name the publication contract and its equality interpretation.
    """

    candidate: ComposedConfiguration
    requester: PrincipalRef
    expected: ExpectedAbsence | OwnerRevision
    source_duty: NoSourceDuty | SourceDutyPlan
    contract_version: Version
    equivalence_version: Version

    def __post_init__(self) -> None:
        if type(self.candidate) is not ComposedConfiguration or type(self.requester) is not PrincipalRef:
            raise TypeError("publication requires captured configuration and requester")
        if type(self.expected) not in (ExpectedAbsence, OwnerRevision):
            raise TypeError("expected absence or scoped OwnerRevision required")
        if isinstance(self.expected, OwnerRevision) and self.expected.subject != self.candidate.target:
            raise ValueError("expected head subject mismatch")
        if type(self.source_duty) not in (NoSourceDuty, SourceDutyPlan):
            raise TypeError("explicit source duty applicability required")
        if type(self.contract_version) is not Version or type(self.equivalence_version) is not Version:
            raise TypeError("publication versions must be Version values")
        if isinstance(self.source_duty, SourceDutyPlan):
            for item in self.source_duty.requirements:
                if item.requirement.scope.tenant_id != self.candidate.target.application.scope.tenant_id:
                    raise ValueError("source duty tenant mismatch")


@dataclass(frozen=True, slots=True)
class PublishConfiguration:
    descriptor: PublicationDescriptor
    context: OperationContext
    observed_at: datetime
    uncertainty_microseconds: int

    def __post_init__(self) -> None:
        if type(self.descriptor) is not PublicationDescriptor or type(self.context) is not OperationContext:
            raise TypeError("publication requires descriptor and explicit context")
        if self.context.operation.subject != self.descriptor.candidate.target:
            raise ValueError("publication operation subject mismatch")
        if self.context.operation.contract_identity != "configuration-publication":
            raise ValueError("unsupported publication operation contract")
        if self.context.originating_requester.reference != self.descriptor.requester:
            raise ValueError("original requester mismatch")
        _utc(self.observed_at)
        if type(self.uncertainty_microseconds) is not int:
            raise TypeError("observation uncertainty must be an integer")
        if self.uncertainty_microseconds < 0:
            raise ValueError("observation uncertainty cannot be negative")


@dataclass(frozen=True, slots=True)
class Coverage:
    """Qualification scope, not eternal retention or proof against store rollback.

    INTACT_STORE_LIFETIME covers all submissions since this store's creation,
    only while intact/non-restored. Fake scope ends at teardown; it supports no
    crash/restart guarantee. Operating intervals require later qualification.
    """

    store_id: str = field(repr=False)
    subject: ConfigurationRef
    extent: CoverageExtent

    def __post_init__(self) -> None:
        _validate(self.store_id)
        if type(self.subject) is not ConfigurationRef or type(self.extent) is not CoverageExtent:
            raise TypeError("coverage requires subject and explicit extent")


@dataclass(frozen=True, slots=True)
class DutyRef:
    subject: ConfigurationRef
    obligation_id: ObligationId

    def __post_init__(self) -> None:
        if type(self.subject) is not ConfigurationRef or type(self.obligation_id) is not ObligationId:
            raise TypeError("duty requires subject and ObligationId")


@dataclass(frozen=True, slots=True)
class ObligationRevision:
    reference: DutyRef
    value: int

    def __post_init__(self) -> None:
        if type(self.reference) is not DutyRef:
            raise TypeError("obligation revision requires DutyRef")
        _positive(self.value)


@dataclass(frozen=True, slots=True)
class ConfigurationHead:
    revision: OwnerRevision
    selected: ConfigurationRevisionRef

    def __post_init__(self) -> None:
        if type(self.revision) is not OwnerRevision or type(self.selected) is not ConfigurationRevisionRef:
            raise TypeError("head requires distinct H and R")
        if self.revision.subject != self.selected.configuration:
            raise ValueError("head subject mismatch")


@dataclass(frozen=True, slots=True)
class PublishedConfiguration:
    head: ConfigurationHead
    original: PublishConfiguration
    predecessor: ConfigurationRevisionRef | None
    duty: DutyRef | None

    def __post_init__(self) -> None:
        if type(self.head) is not ConfigurationHead or type(self.original) is not PublishConfiguration:
            raise TypeError("published record requires head and original intent")
        subject = self.original.descriptor.candidate.target
        if self.head.revision.subject != subject:
            raise ValueError("published subject mismatch")
        if self.head.selected.contract_version != self.original.descriptor.candidate.effective.contract_version:
            raise ValueError("published interpretation mismatch")
        if self.predecessor is not None:
            if type(self.predecessor) is not ConfigurationRevisionRef:
                raise TypeError("predecessor must be exact revision or explicit absence")
            if self.predecessor.configuration != subject or self.predecessor == self.head.selected:
                raise ValueError("invalid predecessor")
        expected = self.original.descriptor.expected
        if isinstance(expected, OwnerRevision):
            if self.predecessor is None or self.head.revision.value != expected.value + 1:
                raise ValueError("publication must be a scoped head successor")
        elif self.predecessor is not None or self.head.revision.value != 1:
            raise ValueError("creation must produce first head without predecessor")
        if self.duty is not None and type(self.duty) is not DutyRef:
            raise TypeError("duty must be DutyRef or explicit absence")
        if isinstance(self.original.descriptor.source_duty, SourceDutyPlan) != (self.duty is not None):
            raise ValueError("duty applicability mismatch")
        if self.duty is not None and self.duty.subject != subject:
            raise ValueError("published duty subject mismatch")


@dataclass(frozen=True, slots=True)
class PublicationResult:
    record: PublishedConfiguration
    coverage: Coverage

    def __post_init__(self) -> None:
        if type(self.record) is not PublishedConfiguration or type(self.coverage) is not Coverage:
            raise TypeError("retained result requires record and coverage")
        if self.record.head.revision.subject != self.coverage.subject:
            raise ValueError("result coverage subject mismatch")

    @property
    def stage(self) -> AcknowledgmentStage:
        return AcknowledgmentStage.OWNER_COMMIT

    @property
    def effect(self) -> EffectExtent:
        return EffectExtent.COMPLETED


@dataclass(frozen=True, slots=True)
class StorageFailure:
    """Unretained outcome; effect concerns this request's attempted mutation.

    A rejected conflicting duplicate does not erase its earlier committed effect.
    UNKNOWN requires reconciliation, never blind retry. Full operational error
    attribution and current disclosure controls belong to the operating owner.
    """

    subject: ConfigurationRef
    error: ErrorDetail
    effect: EffectExtent

    def __post_init__(self) -> None:
        if type(self.subject) is not ConfigurationRef or type(self.error) is not ErrorDetail:
            raise TypeError("failure requires safe error and subject")
        if type(self.effect) is not EffectExtent:
            raise TypeError("failure requires EffectExtent")
        if self.effect not in (EffectExtent.NONE, EffectExtent.UNKNOWN):
            raise ValueError("atomic failure extent must be none or unknown")


@dataclass(frozen=True, slots=True)
class HeadQuery:
    subject: ConfigurationRef

    def __post_init__(self) -> None:
        if type(self.subject) is not ConfigurationRef:
            raise TypeError("head query requires ConfigurationRef")


@dataclass(frozen=True, slots=True)
class RevisionQuery:
    reference: ConfigurationRevisionRef

    def __post_init__(self) -> None:
        if type(self.reference) is not ConfigurationRevisionRef:
            raise TypeError("historical query requires exact revision")


@dataclass(frozen=True, slots=True)
class OperationQuery:
    operation: OperationRef

    def __post_init__(self) -> None:
        if type(self.operation) is not OperationRef:
            raise TypeError("status query requires OperationRef")
        if type(self.operation.subject) is not ConfigurationRef or self.operation.contract_identity != "configuration-publication":
            raise ValueError("status query requires scoped configuration publication")


@dataclass(frozen=True, slots=True)
class LookupAbsence:
    """Absence is established ONLY with qualified complete coverage, not None."""

    query: HeadQuery | RevisionQuery | OperationQuery
    coverage: Coverage

    def __post_init__(self) -> None:
        if type(self.coverage) is not Coverage:
            raise TypeError("lookup requires explicit coverage")
        if isinstance(self.query, HeadQuery):
            subject = self.query.subject
        elif isinstance(self.query, RevisionQuery):
            subject = self.query.reference.configuration
        elif isinstance(self.query, OperationQuery):
            subject = self.query.operation.subject
        else:
            raise TypeError("absence requires a typed lookup query")
        if subject != self.coverage.subject:
            raise ValueError("lookup coverage subject mismatch")


@dataclass(frozen=True, slots=True)
class PendingSourceDuty:
    """Source fact is the exact published record; no Evidence identity/receipt.

    No repair method exists. Initial observation time/uncertainty is preserved in
    the publication; no subsequent observation or last custody/error is invented.
    """

    revision: ObligationRevision
    source: PublishedConfiguration

    def __post_init__(self) -> None:
        if type(self.revision) is not ObligationRevision or type(self.source) is not PublishedConfiguration:
            raise TypeError("pending duty requires revision and exact source fact")
        if self.source.duty != self.revision.reference or self.revision.value != 1:
            raise ValueError("pending source duty requires initial matching revision")

    @property
    def status(self) -> ObligationStatus:
        return ObligationStatus.PENDING

    @property
    def next_safe_action(self) -> DutyAction:
        return DutyAction.SUBMIT_SOURCE_FACT


@dataclass(frozen=True, slots=True)
class DutyKey:
    """Binary lexicographic key within tenant/owner; never a database rowid."""

    application_id: ApplicationId
    instance: str = field(repr=False)
    created_head: int
    obligation_id: ObligationId

    def __post_init__(self) -> None:
        if type(self.application_id) is not ApplicationId or type(self.obligation_id) is not ObligationId:
            raise TypeError("duty key requires nominal identities")
        _validate(self.instance)
        _positive(self.created_head)

    def ordering(self) -> tuple[str, str, int, str]:
        return (self.application_id.value, self.instance, self.created_head, self.obligation_id.value)


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
        if type(self.scope) is not ReferenceScope or type(self.status) is not ObligationStatus or type(self.query_version) is not Version:
            raise TypeError("cursor requires explicit query scope/status/version")
        if type(self.last) is not DutyKey:
            raise TypeError("cursor requires semantic key")
        if self.subject is not None:
            if type(self.subject) is not ConfigurationRef:
                raise TypeError("cursor subject must be ConfigurationRef")
            if self.subject.application.scope != self.scope or self.subject.application.application_id != self.last.application_id or self.subject.instance != self.last.instance:
                raise ValueError("cursor subject/key scope mismatch")


@dataclass(frozen=True, slots=True)
class DutyQuery:
    scope: ReferenceScope
    status: ObligationStatus
    limit: int
    query_version: Version
    subject: ConfigurationRef | None
    cursor: DutyCursor | None

    def __post_init__(self) -> None:
        if type(self.scope) is not ReferenceScope or type(self.status) is not ObligationStatus or type(self.query_version) is not Version:
            raise TypeError("duty query requires explicit scope/status/version")
        _positive(self.limit)
        if self.limit > 128:
            raise ValueError("duty page limit exceeds 128")
        if self.subject is not None:
            if type(self.subject) is not ConfigurationRef:
                raise TypeError("query subject must be ConfigurationRef")
            if self.subject.application.scope != self.scope:
                raise ValueError("query subject scope mismatch")
        if self.cursor is not None:
            if type(self.cursor) is not DutyCursor:
                raise TypeError("query cursor must be DutyCursor")
            if (self.cursor.scope, self.cursor.status, self.cursor.query_version, self.cursor.subject) != (self.scope, self.status, self.query_version, self.subject):
                raise ValueError("cursor cannot cross query scope/status/version")


@dataclass(frozen=True, slots=True)
class DutyPage:
    query: DutyQuery
    duties: tuple[PendingSourceDuty, ...]
    continuation: DutyCursor | None

    def __post_init__(self) -> None:
        if type(self.query) is not DutyQuery or type(self.duties) is not tuple:
            raise TypeError("duty page requires query and immutable duties")
        if len(self.duties) > self.query.limit:
            raise ValueError("page exceeds requested bound")
        for duty in self.duties:
            if type(duty) is not PendingSourceDuty:
                raise TypeError("page contains invalid duty")
            subject = duty.revision.reference.subject
            if subject.application.scope != self.query.scope or duty.status is not self.query.status or (self.query.subject is not None and subject != self.query.subject):
                raise ValueError("page duty scope/status mismatch")
        if self.continuation is not None:
            if type(self.continuation) is not DutyCursor:
                raise TypeError("page continuation must be DutyCursor")
            if not self.duties:
                raise ValueError("empty page cannot continue")
            DutyQuery(self.query.scope, self.query.status, self.query.limit, self.query.query_version, self.query.subject, self.continuation)


@dataclass(frozen=True, slots=True)
class DutyQueryFailure:
    query: DutyQuery
    error: ErrorDetail

    def __post_init__(self) -> None:
        if type(self.query) is not DutyQuery or type(self.error) is not ErrorDetail:
            raise TypeError("duty failure requires query and safe error")


class ConfigurationOwnerStore(Protocol):
    """Atomic configuration publication and scoped, bounded retained queries.

    Equivalent retained O precedes stale-H checks. New O requires qualified
    coverage and its original guard. Successful publication retains head/history/
    result/required pending duty together. Rejections are not retained commits.
    Exact reads never return latest or recompose. No delete/repair/rollback APIs.
    Calls are synchronous; implementations declare their wait/failure boundaries.
    Pages are current observations: quiescent paging is complete; live mutations
    can require a fresh scan. Store mismatch invalidates a cursor; restart starts
    a fresh scan. No current authority or persistence proof comes from this type.
    """

    def publish(self, command: PublishConfiguration) -> PublicationResult | StorageFailure: ...
    def get_head(self, query: HeadQuery) -> ConfigurationHead | LookupAbsence | StorageFailure: ...
    def get_revision(self, query: RevisionQuery) -> PublishedConfiguration | LookupAbsence | StorageFailure: ...
    def get_operation_result(self, query: OperationQuery) -> PublicationResult | LookupAbsence | StorageFailure: ...
    def list_obligations(self, query: DutyQuery) -> DutyPage | DutyQueryFailure: ...
