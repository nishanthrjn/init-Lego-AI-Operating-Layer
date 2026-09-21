"""Single-threaded semantic fake. No persistence, crash or authorization proof."""

from dataclasses import dataclass
from heapq import nsmallest

from legoai.application.ports import (
    ConfigurationHead,
    Coverage,
    CoverageExtent,
    DutyCursor,
    DutyKey,
    DutyPage,
    DutyQuery,
    DutyQueryFailure,
    DutyRef,
    ExpectedAbsence,
    HeadQuery,
    LookupAbsence,
    ObligationRevision,
    OperationQuery,
    PendingSourceDuty,
    PublicationResult,
    PublishConfiguration,
    PublishedConfiguration,
    RevisionQuery,
    SourceDutyPlan,
    StorageFailure,
)
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorDetail, Recoverability
from legoai.kernel.identity import ObligationId, _validate
from legoai.kernel.references import (
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    OwnerRevision,
)
from legoai.kernel.versions import Version


@dataclass(frozen=True)
class _State:
    heads: dict[ConfigurationRef, ConfigurationHead]
    history: dict[ConfigurationRevisionRef, PublishedConfiguration]
    results: dict[OperationRef, PublicationResult]
    duties: dict[DutyRef, PendingSourceDuty]


def _error(category: ErrorCategory) -> ErrorDetail:
    return ErrorDetail(category, Recoverability.UNKNOWN, ())


def _failure(subject: ConfigurationRef, category: ErrorCategory) -> StorageFailure:
    return StorageFailure(subject, _error(category), EffectExtent.NONE)


def _key(duty: PendingSourceDuty) -> DutyKey:
    subject = duty.revision.reference.subject
    return DutyKey(
        subject.application.application_id,
        subject.instance,
        duty.source.head.revision.value,
        duty.revision.reference.obligation_id,
    )


class ConfigurationStoreFake:
    """Test-only owner; staged maps published in one state swap.

    No waits, automatic retries, shared-thread safety, I/O, restoration or expiry.
    A new fake is a new store lifetime, never a fallback for a missing old store.
    Deterministic allocation is test-only; vectors must not assume its format.
    """

    def __init__(self, store_id: str) -> None:
        _validate(store_id)
        self._store_id = store_id
        self._state = _State({}, {}, {}, {})

    def _coverage(self, subject: ConfigurationRef) -> Coverage:
        return Coverage(self._store_id, subject, CoverageExtent.INTACT_STORE_LIFETIME)

    def publish(
        self, command: PublishConfiguration
    ) -> PublicationResult | StorageFailure:
        descriptor = command.descriptor
        subject = descriptor.candidate.target
        operation = command.context.operation
        retained = self._state.results.get(operation)
        # ADR-008: duplicate meaning BEFORE testing the original precondition.
        if retained is not None:
            if retained.record.original.descriptor == descriptor:
                return retained
            return _failure(subject, ErrorCategory.CONFLICT)
        if descriptor.contract_version != Version(
            0, 1, 0
        ) or descriptor.equivalence_version != Version(0, 1, 0):
            return _failure(subject, ErrorCategory.VERSION_MISMATCH)
        head = self._state.heads.get(subject)
        if descriptor.expected is ExpectedAbsence.ABSENT:
            if head is not None:
                return _failure(subject, ErrorCategory.CONFLICT)
        elif head is None or head.revision != descriptor.expected:
            return _failure(subject, ErrorCategory.CONFLICT)
        number = 1 if head is None else head.revision.value + 1
        if number > 2**63 - 1:
            return _failure(subject, ErrorCategory.CONFLICT)
        revision = ConfigurationRevisionRef(
            subject,
            f"fixture-r-{number}",
            descriptor.candidate.effective.contract_version,
        )
        new_head = ConfigurationHead(OwnerRevision(subject, number), revision)
        duty_ref = (
            DutyRef(subject, ObligationId(f"fixture-duty-{number}"))
            if isinstance(descriptor.source_duty, SourceDutyPlan)
            else None
        )
        record = PublishedConfiguration(
            new_head, command, head.selected if head is not None else None, duty_ref
        )
        result = PublicationResult(record, self._coverage(subject))
        heads = self._state.heads | {subject: new_head}
        history = self._state.history | {revision: record}
        results = self._state.results | {operation: result}
        duties = self._state.duties.copy()
        if duty_ref is not None:
            duties[duty_ref] = PendingSourceDuty(
                ObligationRevision(duty_ref, 1), record
            )
        self._state = _State(heads, history, results, duties)
        return result

    def get_head(
        self, query: HeadQuery
    ) -> ConfigurationHead | LookupAbsence | StorageFailure:
        head = self._state.heads.get(query.subject)
        return (
            head
            if head is not None
            else LookupAbsence(query, self._coverage(query.subject))
        )

    def get_revision(
        self, query: RevisionQuery
    ) -> PublishedConfiguration | LookupAbsence | StorageFailure:
        subject = query.reference.configuration
        if query.reference.contract_version != Version(0, 1, 0):
            return _failure(subject, ErrorCategory.VERSION_MISMATCH)
        record = self._state.history.get(query.reference)
        return (
            record
            if record is not None
            else LookupAbsence(query, self._coverage(subject))
        )

    def get_operation_result(
        self, query: OperationQuery
    ) -> PublicationResult | LookupAbsence | StorageFailure:
        subject = query.operation.subject
        assert isinstance(subject, ConfigurationRef)  # guaranteed by query constructor
        result = self._state.results.get(query.operation)
        return (
            result
            if result is not None
            else LookupAbsence(query, self._coverage(subject))
        )

    def list_obligations(self, query: DutyQuery) -> DutyPage | DutyQueryFailure:
        if query.query_version != Version(0, 1, 0):
            return DutyQueryFailure(query, _error(ErrorCategory.VERSION_MISMATCH))
        if query.cursor is not None and query.cursor.store_id != self._store_id:
            return DutyQueryFailure(query, _error(ErrorCategory.VALIDATION_ERROR))
        last = query.cursor.last.ordering() if query.cursor is not None else None
        selected = nsmallest(
            query.limit + 1,
            (
                duty
                for duty in self._state.duties.values()
                if duty.revision.reference.subject.application.scope == query.scope
                and duty.status is query.status
                and (
                    query.subject is None
                    or duty.revision.reference.subject == query.subject
                )
                and (last is None or _key(duty).ordering() > last)
            ),
            key=lambda duty: _key(duty).ordering(),
        )
        page = tuple(selected[: query.limit])
        continuation = None
        if len(selected) > query.limit:
            continuation = DutyCursor(
                self._store_id,
                query.scope,
                query.status,
                query.query_version,
                query.subject,
                _key(page[-1]),
            )
        return DutyPage(query, page, continuation)
