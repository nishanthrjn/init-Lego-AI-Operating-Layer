"""Hostile data remains data; failures disclose no submitted payload."""

import json
from dataclasses import replace
from typing import cast
from unittest.mock import patch

import pytest

from legoai.application.ports import SourceDutyPlan
from legoai.kernel.errors import ErrorCategory
from legoai.reference.application import records
from tests.contracts.test_configuration_store import command, published, subject
from tests.support.configuration_store import ConfigurationStoreFake
from tests.support.record_fixtures import committed, pending


def result_bytes() -> bytes:
    data = records.encode_publication_result(committed())
    assert isinstance(data, bytes)
    return data


def object_at(root: object, path: str) -> dict[str, object]:
    value = root
    for key in path.split(".") if path else ():
        if isinstance(value, list):
            value = value[int(key)]
        else:
            assert isinstance(value, dict)
            value = value[key]
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def changed(path: str, key: str, value: object, *, remove: bool = False) -> bytes:
    root: object = json.loads(result_bytes())
    target = object_at(root, path)
    if remove:
        del target[key]
    else:
        target[key] = value
    return json.dumps(root).encode()


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"{",
        b"[]",
        b"null",
        b"true",
        b"123",
        b'"text"',
        b"\xff",
        b'{"a":1,"a":2}',
        b'{"a":{"secret":"first","secret":"second"}}',
        b'{"a":1,"\\u0061":2}',
        b'{"a":NaN}',
        b'{"a":Infinity}',
        b'{"a":-Infinity}',
        b'{"a":1.5}',
        b'{"a":1e9999}',
        b'{"a":9223372036854775808}',
        b'{"a":-9223372036854775809}',
        b'{"a":' + b"9" * 100 + b"}",
        b'{"\\ud800":1}',
        b'{"__class__":"subprocess.Popen"}',
    ],
)
def test_malformed_data(data: bytes) -> None:
    outcome = records.decode_publication_result(data)
    assert isinstance(outcome, records.RecordFailure)
    assert outcome.error.category is ErrorCategory.VALIDATION_ERROR


@pytest.mark.parametrize(
    ("path", "key", "value"),
    [
        ("", "record_kind", "unknown"),
        ("", "record_kind", "published_configuration"),
        ("", "record_schema_version", True),
        ("", "reader_contract_version", False),
        ("", "subject", None),
        ("", "payload", []),
        ("", "credential", "sensitive-marker"),
        ("subject.application.scope", "tenant_id", "foreign"),
        ("subject.application.scope", "owner", ""),
        ("subject", "instance", "x" * 257),
        ("subject", "instance", "\ud800"),
        ("payload", "effect", "partial"),
        ("payload", "effect", "none"),
        ("payload", "effect", "unknown"),
        ("payload", "effect", "invented"),
        ("payload", "stage", "running"),
        ("payload.coverage", "extent", "complete_forever"),
        ("payload.coverage.subject.application.scope", "tenant_id", "foreign"),
        ("payload.record.head.revision", "value", -1),
        ("payload.record.head.revision", "value", True),
        ("payload.record.head.selected.configuration", "instance", "foreign"),
        ("payload.record.original", "observed_at", "2026-09-21"),
        ("payload.record.original", "observed_at", "2026-09-21T00:00:00.000000+01:00"),
        ("payload.record.original", "observed_at", "2026-99-21T00:00:00.000000+00:00"),
        ("payload.record.original", "uncertainty_microseconds", True),
        ("payload.record.original.context", "tenant_id", "foreign"),
        ("payload.record.original.context", "request_id", 5),
        ("payload.record.original.context.operation", "subject_kind", "arbitrary"),
        ("payload.record.original.descriptor", "expected", None),
        ("payload.record.original.descriptor", "expected", {"kind": "latest"}),
        ("payload.record.original.descriptor", "source_duty", []),
        ("payload.record.original.descriptor.source_duty", "applicability", "skip"),
        (
            "payload.record.original.descriptor.candidate.effective",
            "max_input_length",
            True,
        ),
        (
            "payload.record.original.descriptor.candidate.effective",
            "normalization_mode",
            "arbitrary",
        ),
        (
            "payload.record.original.descriptor.candidate.effective",
            "allowed_whitespace",
            " ",
        ),
        (
            "payload.record.original.descriptor.candidate.effective",
            "allowed_whitespace",
            [" "] * 7,
        ),
        (
            "payload.record.original.descriptor.candidate.sources.0",
            "layer",
            "arbitrary",
        ),
        (
            "payload.record.original.descriptor.candidate.sources.0.provenance",
            "source_id",
            "",
        ),
        (
            "payload.record.original.descriptor.candidate.sources.0.values",
            "max_input_length",
            "123",
        ),
    ],
)
def test_closed_fields_types_scopes_and_enums(
    path: str, key: str, value: object
) -> None:
    outcome = records.decode_publication_result(changed(path, key, value))
    assert isinstance(outcome, records.RecordFailure)
    assert "sensitive-marker" not in repr(outcome)
    assert not hasattr(outcome, "payload")


@pytest.mark.parametrize(
    ("path", "key"),
    [
        ("", "record_kind"),
        ("", "reader_contract_version"),
        ("payload.record.original.descriptor.candidate.effective", "max_input_length"),
        (
            "payload.record.original.descriptor.candidate.sources.0.values",
            "allowed_whitespace",
        ),
        ("payload.record", "predecessor"),
        ("payload.record.original.context", "causation"),
    ],
)
def test_missing_is_not_null_or_default(path: str, key: str) -> None:
    assert isinstance(
        records.decode_publication_result(changed(path, key, None, remove=True)),
        records.RecordFailure,
    )


@pytest.mark.parametrize(
    ("path", "key", "value"),
    [
        ("", "record_schema_version", 2),
        ("", "reader_contract_version", 2),
        (
            "payload.record.original.descriptor",
            "contract_version",
            {"major": 9, "minor": 0, "patch": 0},
        ),
        (
            "payload.record.original.descriptor.candidate.effective",
            "interpretation_version",
            {"major": 9, "minor": 0, "patch": 0},
        ),
    ],
)
def test_unsupported_interpretation_fails_without_migration(
    path: str, key: str, value: object
) -> None:
    outcome = records.decode_publication_result(changed(path, key, value))
    assert isinstance(outcome, records.RecordFailure)
    assert outcome.error.category is ErrorCategory.VERSION_MISMATCH


def test_preparse_limits_and_escaped_strings() -> None:
    with patch.object(
        json, "loads", side_effect=AssertionError("must reject before parse")
    ):
        for data in (
            b" " * 65537,
            b"[" * 33 + b"0" + b"]" * 33,
            b"[" + b"0," * 5000 + b"0]",
        ):
            outcome = records.decode_publication_result(data)
            assert isinstance(outcome, records.RecordFailure)
            assert outcome.problem is records.RecordProblem.LIMIT
    exact_limit = result_bytes()
    exact_limit += b" " * (65536 - len(exact_limit))
    assert records.decode_publication_result(exact_limit) == committed()
    # Braces, quotes and escaped backslashes inside opaque strings are data.
    value = committed()
    source = value.record.original.descriptor.candidate.sources[1]
    source = replace(
        source, provenance=replace(source.provenance, source_id='[{}]"\\' * 30)
    )
    candidate = replace(
        value.record.original.descriptor.candidate,
        sources=(value.record.original.descriptor.candidate.sources[0], source),
    )
    value = replace(
        value,
        record=replace(
            value.record,
            original=replace(
                value.record.original,
                descriptor=replace(
                    value.record.original.descriptor, candidate=candidate
                ),
            ),
        ),
    )
    encoded = records.encode_publication_result(value)
    assert (
        isinstance(encoded, bytes)
        and records.decode_publication_result(encoded) == value
    )


def test_collection_limits_and_duplicate_smuggling() -> None:
    root: object = json.loads(result_bytes())
    candidate = object_at(root, "payload.record.original.descriptor.candidate")
    candidate["sources"] = cast(list[object], candidate["sources"]) * 2
    assert isinstance(
        records.decode_publication_result(json.dumps(root).encode()),
        records.RecordFailure,
    )
    root = json.loads(result_bytes())
    plan = object_at(root, "payload.record.original.descriptor.source_duty")
    plan["requirements"] = cast(list[object], plan["requirements"]) * 9
    assert isinstance(
        records.decode_publication_result(json.dumps(root).encode()),
        records.RecordFailure,
    )
    data = result_bytes().replace(
        b'"effect":"completed"', b'"effect":"none","effect":"completed"'
    )
    assert isinstance(records.decode_publication_result(data), records.RecordFailure)


@pytest.mark.parametrize(
    "status", ["satisfied", "failed", "requires intervention", "running", "claimed"]
)
def test_duty_status_vocabulary_does_not_fabricate_repair(status: str) -> None:
    data = records.encode_pending_source_duty(pending())
    assert isinstance(data, bytes)
    raw = json.loads(data)
    raw["payload"]["status"] = status
    outcome = records.decode_pending_source_duty(json.dumps(raw).encode())
    assert isinstance(outcome, records.RecordFailure)
    assert outcome.problem is (
        records.RecordProblem.UNSUPPORTED
        if status in {"satisfied", "failed", "requires intervention"}
        else records.RecordProblem.MALFORMED
    )


def test_wrong_input_and_no_secret_extension() -> None:
    value: object
    for value in (None, "{}", bytearray(b"{}"), {}):
        outcome = records.decode_publication_result(cast(bytes, value))
        assert isinstance(outcome, records.RecordFailure)
    for field in ("__class__", "module", "type", "metadata", "api_key"):
        data = changed("payload", field, "sensitive-marker")
        outcome = records.decode_publication_result(data)
        assert isinstance(outcome, records.RecordFailure)
        assert "sensitive-marker" not in str(outcome) + repr(outcome.error)


def test_encoding_enforces_interpretation_and_numeric_bounds() -> None:
    value = committed()
    command = replace(value.record.original, uncertainty_microseconds=2**63)
    failed = records.encode_publication_result(
        replace(value, record=replace(value.record, original=command))
    )
    assert isinstance(failed, records.RecordFailure)


def test_utf8_preservation_and_encoding_size_bound() -> None:
    target = subject(tenant="租户", application="é", instance="𐐀", owner="композиция")
    value = published(ConfigurationStoreFake("unicode"), command(target, "operation"))
    data = records.encode_publication_result(value)
    assert isinstance(data, bytes)
    assert "租户".encode() in data
    assert records.decode_publication_result(data) == value
    target = subject(
        tenant="𐐀" * 256, application="𐐀" * 256, instance="𐐀" * 256, owner="𐐀" * 256
    )
    value = published(
        ConfigurationStoreFake("bounded"), command(target, "operation", duty=True)
    )
    plan = value.record.original.descriptor.source_duty
    assert isinstance(plan, SourceDutyPlan)
    requirement = plan.requirements[0]
    requirements = tuple(
        replace(
            requirement,
            requirement=replace(
                requirement.requirement, identity="𐐀" * 255 + str(index)
            ),
            guarantee=replace(requirement.guarantee, identity="𐐀" * 256),
        )
        for index in range(8)
    )
    original = replace(
        value.record.original,
        descriptor=replace(
            value.record.original.descriptor,
            source_duty=replace(plan, requirements=requirements),
        ),
    )
    value = replace(value, record=replace(value.record, original=original))
    data = records.encode_publication_result(value)
    assert (
        isinstance(data, records.RecordFailure)
        and data.problem is records.RecordProblem.LIMIT
    )


def test_surrogate_encoding_rejected() -> None:
    value = committed()
    plan = value.record.original.descriptor.source_duty
    assert isinstance(plan, SourceDutyPlan)
    # A legal nominal value with a surrogate has no supported UTF-8 representation.
    command = replace(
        value.record.original,
        descriptor=replace(
            value.record.original.descriptor,
            requester=replace(
                value.record.original.descriptor.requester, issuer="\ud800"
            ),
        ),
        context=replace(
            value.record.original.context,
            acting_principal=replace(
                value.record.original.context.acting_principal,
                reference=replace(
                    value.record.original.descriptor.requester, issuer="\ud800"
                ),
            ),
            originating_requester=replace(
                value.record.original.context.originating_requester,
                reference=replace(
                    value.record.original.descriptor.requester, issuer="\ud800"
                ),
            ),
        ),
    )
    failed = records.encode_publication_result(
        replace(value, record=replace(value.record, original=command))
    )
    assert isinstance(failed, records.RecordFailure)
