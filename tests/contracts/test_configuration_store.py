"""Reusable owner-contract vectors. No fake internals or allocation format oracle."""

from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from typing import cast

import pytest

from legoai.application.ports import (
    AcknowledgmentStage,
    ConfigurationOwnerStore,
    Coverage,
    CoverageExtent,
    DutyAction,
    DutyPage,
    DutyQuery,
    DutyQueryFailure,
    DutyRef,
    ExpectedAbsence,
    HeadQuery,
    LookupAbsence,
    NoSourceDuty,
    ObligationRevision,
    ObligationStatus,
    OperationQuery,
    PublicationDescriptor,
    PublicationResult,
    PublishConfiguration,
    RevisionQuery,
    SourceDutyPlan,
    StorageFailure,
)
from legoai.application.values import SourceLayer, SourceProvenance
from legoai.evidence.values import GuaranteeRef, RequirementRef, SourceRequirement
from legoai.governance.values import OperationContext, Principal
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorDetail, Recoverability
from legoai.kernel.identity import (
    ApplicationId,
    CorrelationId,
    ObligationId,
    OperationId,
    PrincipalId,
    RequestId,
    TenantId,
    TraceId,
)
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    OperationRef,
    OwnerRevision,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.reference.application.configuration import (
    capture_candidate,
    compose_configuration,
)


def subject(
    tenant: str = "tenant",
    application: str = "app",
    instance: str = "config",
    owner: str = "composition",
) -> ConfigurationRef:
    return ConfigurationRef(
        ApplicationRef(
            ReferenceScope(owner, TenantId(tenant)), ApplicationId(application)
        ),
        instance,
    )


def command(
    target: ConfigurationRef,
    operation: str,
    expected: ExpectedAbsence | OwnerRevision = ExpectedAbsence.ABSENT,
    duty: bool = False,
    raw: object = None,
) -> PublishConfiguration:
    version = Version(0, 1, 0)
    principal = Principal(PrincipalRef("identity", PrincipalId("requester")))
    candidate = capture_candidate(
        {} if raw is None else raw,
        target=target,
        provenance=SourceProvenance("source", "input", "revision-1", version, version),
        layer=SourceLayer.BASE,
    )
    composed = compose_configuration(
        target, (candidate,), contract_version=version, interpretation_version=version
    )
    requirement_scope = ReferenceScope(
        "requirements", target.application.scope.tenant_id
    )
    plan = (
        SourceDutyPlan(
            principal.reference,
            principal.reference,
            (
                SourceRequirement(
                    RequirementRef(requirement_scope, "post-commit-source", version),
                    GuaranteeRef(requirement_scope, "qualified-custody", version),
                    datetime(2026, 10, 1, tzinfo=UTC),
                    datetime(2027, 1, 1, tzinfo=UTC),
                ),
            ),
        )
        if duty
        else NoSourceDuty.NOT_APPLICABLE
    )
    descriptor = PublicationDescriptor(
        composed, principal.reference, expected, plan, version, version
    )
    context = OperationContext(
        OperationRef(target, OperationId(operation), "configuration-publication"),
        RequestId("request"),
        CorrelationId("correlation"),
        TraceId("trace"),
        TenantContext(target.application.scope.tenant_id),
        principal,
        principal,
        None,
    )
    return PublishConfiguration(
        descriptor, context, datetime(2026, 9, 21, tzinfo=UTC), 0
    )


def published(
    store: ConfigurationOwnerStore, intent: PublishConfiguration
) -> PublicationResult:
    result = store.publish(intent)
    assert isinstance(result, PublicationResult)
    assert result.stage is AcknowledgmentStage.OWNER_COMMIT
    assert result.effect is EffectExtent.COMPLETED
    return result


def conflict(result: PublicationResult | StorageFailure) -> None:
    assert isinstance(result, StorageFailure)
    assert result.error.category is ErrorCategory.CONFLICT
    assert result.effect is EffectExtent.NONE


def query(target: ConfigurationRef, limit: int = 2) -> DutyQuery:
    return DutyQuery(
        target.application.scope,
        ObligationStatus.PENDING,
        limit,
        Version(0, 1, 0),
        None,
        None,
    )


def test_publication_history_and_lost_ack(
    store_factory: Callable[[str], ConfigurationOwnerStore],
) -> None:
    store = store_factory("history")
    target = subject()
    first = published(store, command(target, "first"))
    assert first.record.head.revision == OwnerRevision(target, 1)
    assert first.record.predecessor is None and first.record.duty is None
    lost = command(
        target, "lost", first.record.head.revision, True, {"normalization_mode": "trim"}
    )
    second = published(store, lost)
    third = published(store, command(target, "third", second.record.head.revision))
    assert third.record.head.revision.value == 3
    assert second.record.predecessor == first.record.head.selected
    assert third.record.predecessor == second.record.head.selected
    assert store.publish(lost) == second  # old H1, now H3: original H2/R2, not H4
    assert store.get_head(HeadQuery(target)) == third.record.head
    assert (
        store.get_revision(RevisionQuery(second.record.head.selected)) == second.record
    )
    assert store.get_operation_result(OperationQuery(lost.context.operation)) == second
    with pytest.raises(FrozenInstanceError):
        setattr(second.record.head.revision, "value", 50)  # noqa: B010
    conflict(store.publish(command(target, "stale", first.record.head.revision)))
    assert store.get_head(HeadQuery(target)) == third.record.head
    assert isinstance(
        store.get_operation_result(
            OperationQuery(command(target, "stale").context.operation)
        ),
        LookupAbsence,
    )


def test_expected_absence_and_diagnostics(
    store_factory: Callable[[str], ConfigurationOwnerStore],
) -> None:
    store = store_factory("absence")
    intent = command(subject(), "original")
    first = published(store, intent)
    conflict(store.publish(command(subject(), "new")))
    again = replace(
        intent,
        context=replace(
            intent.context,
            request_id=RequestId("new-request"),
            trace_id=TraceId("new-trace"),
            correlation_id=CorrelationId("new-correlation"),
        ),
        observed_at=datetime(2026, 9, 22, tzinfo=UTC),
    )
    assert store.publish(again) == first
    assert store.get_operation_result(OperationQuery(intent.context.operation)) == first
    assert first.record.original.context.request_id == RequestId("request")


@pytest.mark.parametrize(
    "change",
    ["expected", "requester", "source", "effective", "contract", "equivalence", "duty"],
)
def test_conflicting_meaning(
    store_factory: Callable[[str], ConfigurationOwnerStore], change: str
) -> None:
    store = store_factory("conflict")
    intent = command(subject(), "operation")
    first = published(store, intent)
    descriptor = intent.descriptor
    context = intent.context
    if change == "expected":
        descriptor = replace(descriptor, expected=first.record.head.revision)
    elif change == "requester":
        principal = Principal(PrincipalRef("identity", PrincipalId("other")))
        descriptor = replace(descriptor, requester=principal.reference)
        context = replace(
            context, acting_principal=principal, originating_requester=principal
        )
    elif change == "source":
        defaults, base = descriptor.candidate.sources
        base = replace(
            base, provenance=replace(base.provenance, source_revision="revision-2")
        )
        descriptor = replace(
            descriptor,
            candidate=replace(descriptor.candidate, sources=(defaults, base)),
        )
        assert descriptor.candidate.effective == intent.descriptor.candidate.effective
    elif change == "effective":
        descriptor = command(
            subject(), "operation", raw={"normalization_mode": "trim"}
        ).descriptor
    elif change == "contract":
        descriptor = replace(descriptor, contract_version=Version(0, 2, 0))
    elif change == "equivalence":
        descriptor = replace(descriptor, equivalence_version=Version(0, 2, 0))
    else:
        descriptor = command(subject(), "operation", duty=True).descriptor
    conflict(store.publish(replace(intent, descriptor=descriptor, context=context)))
    assert store.get_head(HeadQuery(subject())) == first.record.head
    assert store.get_operation_result(OperationQuery(intent.context.operation)) == first


@pytest.mark.parametrize(
    "other",
    [
        subject("other"),
        subject(application="other"),
        subject(instance="other"),
        subject(owner="other"),
    ],
)
def test_scoped_ids_and_no_foreign_disclosure(
    store_factory: Callable[[str], ConfigurationOwnerStore], other: ConfigurationRef
) -> None:
    store = store_factory("scopes")
    first = published(store, command(subject(), "same"))
    assert isinstance(store.get_head(HeadQuery(other)), LookupAbsence)
    assert isinstance(
        store.get_operation_result(
            OperationQuery(command(other, "same").context.operation)
        ),
        LookupAbsence,
    )
    wrong_ref = replace(first.record.head.selected, configuration=other)
    assert isinstance(store.get_revision(RevisionQuery(wrong_ref)), LookupAbsence)
    second = published(store, command(other, "same"))
    assert first.record.head.selected != second.record.head.selected
    assert store.get_revision(RevisionQuery(first.record.head.selected)) == first.record


def test_missing_unsupported_and_coverage(
    store_factory: Callable[[str], ConfigurationOwnerStore],
) -> None:
    store = store_factory("coverage")
    intent = command(subject(), "not-committed")
    absent = store.get_operation_result(OperationQuery(intent.context.operation))
    assert isinstance(absent, LookupAbsence)
    assert absent.coverage.extent is CoverageExtent.INTACT_STORE_LIFETIME
    unknown = replace(
        absent, coverage=Coverage("unqualified", subject(), CoverageExtent.UNKNOWN)
    )
    assert unknown != absent
    unavailable = StorageFailure(
        subject(),
        ErrorDetail(
            ErrorCategory.DEPENDENCY_FAILURE, Recoverability.REQUIRES_INTERVENTION, ()
        ),
        EffectExtent.UNKNOWN,
    )
    assert unavailable.effect is EffectExtent.UNKNOWN
    unsupported = replace(
        intent, descriptor=replace(intent.descriptor, contract_version=Version(9, 0, 0))
    )
    failed = store.publish(unsupported)
    assert (
        isinstance(failed, StorageFailure)
        and failed.error.category is ErrorCategory.VERSION_MISMATCH
    )
    assert isinstance(store.get_head(HeadQuery(subject())), LookupAbsence)
    result = published(store, intent)
    wrong_reader = replace(
        result.record.head.selected, contract_version=Version(9, 0, 0)
    )
    failure = store.get_revision(RevisionQuery(wrong_reader))
    assert (
        isinstance(failure, StorageFailure)
        and failure.error.category is ErrorCategory.VERSION_MISMATCH
    )
    assert isinstance(
        store.get_revision(
            RevisionQuery(replace(result.record.head.selected, revision="missing"))
        ),
        LookupAbsence,
    )


def test_pending_duties_and_keyset_pages(
    store_factory: Callable[[str], ConfigurationOwnerStore],
) -> None:
    store = store_factory("duties")
    target = subject()
    expected: ExpectedAbsence | OwnerRevision = ExpectedAbsence.ABSENT
    expected_refs = set()
    for index in range(5):
        result = published(store, command(target, f"op-{index}", expected, True))
        expected = result.record.head.revision
        expected_refs.add(result.record.duty)
    # Another subject participates in tenant/owner discovery, not exact-subject pages.
    extra = published(store, command(subject(application="z"), "extra", duty=True))
    expected_refs.add(extra.record.duty)
    published(store, command(subject("other"), "foreign", duty=True))
    request = query(target)
    seen = []
    initial_cursor = None
    for _ in range(4):
        page = store.list_obligations(request)
        assert isinstance(page, DutyPage)
        assert len(page.duties) <= 2
        for duty in page.duties:
            assert duty.status is ObligationStatus.PENDING and duty.revision.value == 1
            assert duty.next_safe_action is DutyAction.SUBMIT_SOURCE_FACT
            assert duty.source.duty == duty.revision.reference
            assert isinstance(
                duty.source.original.descriptor.source_duty, SourceDutyPlan
            )
            assert not hasattr(duty, "receipt") and not hasattr(duty, "custody")
            seen.append(duty.revision.reference)
        if page.continuation is None:
            break
        initial_cursor = initial_cursor or page.continuation
        request = replace(request, cursor=page.continuation)
    else:
        pytest.fail("quiescent pages did not terminate")
    assert len(seen) == len(set(seen)) == 6
    assert set(seen) == expected_refs
    assert initial_cursor is not None
    for changed in (
        {"scope": ReferenceScope("composition", TenantId("other"))},
        {"scope": ReferenceScope("other-owner", TenantId("tenant"))},
        {"status": ObligationStatus.FAILED},
        {"query_version": Version(0, 2, 0)},
        {"subject": subject(application="different")},
    ):
        with pytest.raises(ValueError):
            replace(query(target), cursor=initial_cursor, **changed)
    foreign = store_factory("different-store")
    failed = foreign.list_obligations(replace(query(target), cursor=initial_cursor))
    assert isinstance(failed, DutyQueryFailure)
    assert failed.error.category is ErrorCategory.VALIDATION_ERROR
    subset = store.list_obligations(replace(query(target, 128), subject=target))
    assert isinstance(subset, DutyPage) and len(subset.duties) == 5
    empty = store.list_obligations(
        replace(query(target), status=ObligationStatus.SATISFIED)
    )
    assert (
        isinstance(empty, DutyPage) and not empty.duties and empty.continuation is None
    )
    unsupported = store.list_obligations(
        replace(query(target), query_version=Version(9, 0, 0))
    )
    assert isinstance(unsupported, DutyQueryFailure)


def test_capture_remains_immutable_through_publication(
    store_factory: Callable[[str], ConfigurationOwnerStore],
) -> None:
    store = store_factory("capture")
    whitespace = [" ", "\t"]
    raw: dict[str, object] = {"allowed_whitespace": whitespace}
    intent = command(subject(), "capture", raw=raw)
    whitespace.clear()
    raw.clear()
    result = published(store, intent)
    assert result.record.original.descriptor.candidate.effective.allowed_whitespace == (
        " ",
        "\t",
    )
    assert not any(
        hasattr(store, name)
        for name in ("delete", "rollback", "mark_satisfied", "claim_duty")
    )


def test_contract_validation_and_deep_immutability(
    store_factory: Callable[[str], ConfigurationOwnerStore],
) -> None:
    intent = command(subject(), "validation", duty=True)
    plan = intent.descriptor.source_duty
    assert isinstance(plan, SourceDutyPlan)
    requirement = plan.requirements[0]
    store = store_factory("validation")
    result = published(store, intent)
    page = store.list_obligations(query(subject()))
    assert isinstance(page, DutyPage)
    duty = page.duties[0]
    # Deliberately cross typing boundaries only to exercise public validation.
    invalid: tuple[tuple[object, dict[str, object]], ...] = (
        (plan, {"requirements": []}),
        (plan, {"requirements": ()}),
        (plan, {"requirements": (requirement, requirement)}),
        (plan, {"requirements": (requirement,) * 9}),
        (requirement, {"due_at": datetime(2026, 1, 1)}),
        (requirement, {"retain_until": datetime(2025, 1, 1, tzinfo=UTC)}),
        (requirement, {"requirement": requirement.guarantee}),
        (
            requirement,
            {
                "guarantee": replace(
                    requirement.guarantee,
                    scope=ReferenceScope("requirements", TenantId("foreign")),
                )
            },
        ),
        (requirement.requirement, {"version": "0.1.0"}),
        (requirement.guarantee, {"scope": "tenant"}),
        (intent, {"uncertainty_microseconds": True}),
        (intent, {"uncertainty_microseconds": -1}),
        (intent, {"context": command(subject("foreign"), "validation").context}),
        (intent.descriptor, {"expected": OwnerRevision(subject("foreign"), 1)}),
        (intent.descriptor, {"expected": 0}),
        (intent.descriptor, {"source_duty": None}),
        (
            intent.descriptor,
            {
                "source_duty": replace(
                    plan,
                    requirements=(
                        replace(
                            requirement,
                            requirement=replace(
                                requirement.requirement,
                                scope=ReferenceScope(
                                    "requirements", TenantId("foreign")
                                ),
                            ),
                            guarantee=replace(
                                requirement.guarantee,
                                scope=ReferenceScope(
                                    "requirements", TenantId("foreign")
                                ),
                            ),
                        ),
                    ),
                )
            },
        ),
        (result.record.head, {"revision": OwnerRevision(subject("foreign"), 1)}),
        (result.record, {"predecessor": result.record.head.selected}),
        (result.record, {"duty": None}),
        (result.record, {"duty": DutyRef(subject("foreign"), ObligationId("duty"))}),
        (result, {"coverage": replace(result.coverage, subject=subject("foreign"))}),
        (duty, {"revision": ObligationRevision(duty.revision.reference, 2)}),
        (duty.revision, {"value": True}),
        (duty.revision, {"value": 0}),
        (query(subject()), {"limit": True}),
        (query(subject()), {"limit": 0}),
        (query(subject()), {"limit": 129}),
        (query(subject()), {"subject": subject("foreign")}),
        (page, {"duties": list(page.duties)}),
        (page, {"duties": (duty, duty)}),
        (page, {"query": query(subject("foreign"))}),
    )
    unchecked_replace = cast(Callable[..., object], replace)
    for value, changes in invalid:
        with pytest.raises((TypeError, ValueError)):
            unchecked_replace(value, **changes)
    for value in (
        intent,
        plan,
        requirement,
        result,
        result.record,
        duty,
        duty.revision,
    ):
        assert hash(value) == hash(value)
        with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
            setattr(value, "injected", True)  # noqa: B010
    for extent in (EffectExtent.PARTIAL, EffectExtent.COMPLETED):
        with pytest.raises(ValueError):
            StorageFailure(
                subject(),
                ErrorDetail(ErrorCategory.CONFLICT, Recoverability.UNKNOWN, ()),
                extent,
            )
    assert cast(object, ObligationId("same")) != OperationId("same")
    assert cast(object, requirement.requirement) != requirement.guarantee
    assert {status.value for status in ObligationStatus} == {
        "pending",
        "satisfied",
        "failed",
        "requires intervention",
    }


def test_cursor_page_integrity(
    store_factory: Callable[[str], ConfigurationOwnerStore],
) -> None:
    store = store_factory("cursor-integrity")
    first = published(store, command(subject(), "one", duty=True))
    published(store, command(subject(), "two", first.record.head.revision, True))
    page = store.list_obligations(query(subject(), 1))
    assert isinstance(page, DutyPage) and page.continuation is not None
    cursor = page.continuation
    with pytest.raises(ValueError):
        replace(page, duties=())
    with pytest.raises(ValueError):
        replace(
            page,
            continuation=replace(cursor, last=replace(cursor.last, created_head=9)),
        )
    with pytest.raises(ValueError):
        replace(cursor, subject=subject(application="wrong"))
    with pytest.raises(ValueError):
        replace(page, query=replace(page.query, cursor=cursor))
    next_page = store.list_obligations(replace(page.query, cursor=cursor))
    assert isinstance(next_page, DutyPage)
    wrong_store = replace(
        cursor,
        store_id="other",
        last=replace(
            cursor.last,
            created_head=2,
            obligation_id=next_page.duties[0].revision.reference.obligation_id,
        ),
    )
    with pytest.raises(ValueError):
        replace(next_page, continuation=wrong_store)
