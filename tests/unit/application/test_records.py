"""F5 semantic preservation, independently of stable rendering."""

import json
from dataclasses import replace
from typing import cast
from unittest.mock import patch

import pytest

from legoai.application.ports import (
    CoverageExtent,
    PublicationResult,
    PublishedConfiguration,
)
from legoai.kernel.identity import CorrelationId, OperationId, RequestId, TraceId
from legoai.kernel.references import ConfigurationRef, OperationRef
from legoai.reference.application import records
from tests.support.record_fixtures import committed, pending


@pytest.mark.parametrize("update", [False, True])
@pytest.mark.parametrize("duty", [False, True])
def test_publication_round_trip(update: bool, duty: bool) -> None:
    value = committed(update=update, duty=duty)
    data = records.encode_publication_result(value)
    assert isinstance(data, bytes)
    decoded = records.decode_publication_result(data)
    assert decoded == value
    assert records.encode_publication_result(value) == data
    assert records.encode_publication_result(decoded) == data
    revision = records.encode_published_configuration(value.record)
    assert isinstance(revision, bytes)
    restored = records.decode_published_configuration(revision)
    assert restored == value.record
    assert records.encode_published_configuration(restored) == revision
    assert records.record_subject(value) == records.record_subject(value.record)
    # Text layout is not equivalence or identity. Reordered keys/whitespace work.
    alternate = json.dumps(json.loads(data), indent=2).encode()
    assert alternate != data
    assert records.decode_publication_result(alternate) == value


def test_pending_and_unknown_coverage_round_trip() -> None:
    duty = pending()
    data = records.encode_pending_source_duty(duty)
    assert isinstance(data, bytes)
    restored = records.decode_pending_source_duty(data)
    assert restored == duty
    assert records.record_subject(duty) == duty.revision.reference.subject
    assert records.encode_pending_source_duty(duty) == data
    result = committed()
    unknown = replace(
        result, coverage=replace(result.coverage, extent=CoverageExtent.UNKNOWN)
    )
    data = records.encode_publication_result(unknown)
    assert isinstance(data, bytes)
    assert records.decode_publication_result(data) == unknown


def test_diagnostics_retained_without_changing_descriptor() -> None:
    result = committed()
    context = result.record.original.context
    assert isinstance(context.operation.subject, ConfigurationRef)
    causation = OperationRef(
        context.operation.subject.application,
        OperationId("cause"),
        "application-maintenance",
    )
    changed = replace(
        result.record.original,
        context=replace(
            context,
            request_id=RequestId("different"),
            trace_id=None,
            correlation_id=CorrelationId("different"),
            causation=causation,
        ),
    )
    value = replace(result.record, original=changed)
    data = records.encode_published_configuration(value)
    assert isinstance(data, bytes)
    restored = records.decode_published_configuration(data)
    assert isinstance(restored, PublishedConfiguration)
    assert restored == value
    assert restored.original.descriptor == result.record.original.descriptor
    assert restored.original.context != result.record.original.context
    # Also exercise configuration-scoped causation and non-null TraceId.
    changed = replace(
        changed,
        context=replace(
            changed.context,
            trace_id=TraceId("trace"),
            causation=replace(causation, subject=context.operation.subject),
        ),
    )
    value = replace(value, original=changed)
    data = records.encode_published_configuration(value)
    assert (
        isinstance(data, bytes)
        and records.decode_published_configuration(data) == value
    )


def test_historical_defaults_never_recomposed() -> None:
    result = committed(update=True)
    data = records.encode_publication_result(result)
    assert isinstance(data, bytes)
    # A future composer may change or fail entirely; reading is independent.
    with patch(
        "legoai.reference.application.configuration.compose_configuration",
        side_effect=AssertionError("current defaults must not be consulted"),
    ):
        decoded = records.decode_publication_result(data)
    assert decoded == result
    assert isinstance(decoded, PublicationResult)
    assert (
        decoded.record.original.descriptor.candidate.effective.max_input_length == 123
    )
    assert (
        decoded.record.original.descriptor.candidate.effective.allowed_whitespace == ()
    )


def test_mutable_fixture_cannot_rewrite_encoded_history() -> None:
    result = committed()
    data = records.encode_publication_result(result)
    assert isinstance(data, bytes)
    fixture = json.loads(data)
    fixture["payload"]["record"]["original"]["descriptor"]["candidate"][
        "sources"
    ].clear()
    assert records.decode_publication_result(data) == result


def test_record_family_and_input_types() -> None:
    result = committed()
    data = records.encode_publication_result(result)
    assert isinstance(data, bytes)
    assert isinstance(
        records.decode_published_configuration(data), records.RecordFailure
    )
    assert isinstance(records.decode_pending_source_duty(data), records.RecordFailure)
    assert isinstance(
        records.encode_publication_result(cast(PublicationResult, {})),
        records.RecordFailure,
    )
    with pytest.raises(TypeError):
        records.record_subject(cast(records.OwnerRecord, {}))
    with pytest.raises(TypeError):
        records.RecordFailure(cast(records.RecordProblem, "invalid"))
