"""SYNTHETIC schema 1 -> 2 only; no real historical release/upgrade claim."""

import json
from dataclasses import replace
from typing import cast

import pytest

from legoai.reference.application import migrations as m
from legoai.reference.application import records as r
from tests.support.record_fixtures import committed


def synthetic_transform(data: bytes) -> bytes:
    obj = json.loads(data)
    obj["record_schema_version"] = 2
    obj["reader_contract_version"] = 2
    obj["payload"] = {"synthetic_content": obj["payload"]}
    return json.dumps(obj, sort_keys=True).encode()


def synthetic_reader(data: bytes) -> r.OwnerRecord | r.RecordFailure:
    obj = json.loads(data)
    if obj["record_schema_version"] != 2 or obj["reader_contract_version"] != 2:
        return r.RecordFailure(r.RecordProblem.UNSUPPORTED)
    obj["record_schema_version"] = 1
    obj["reader_contract_version"] = 1
    obj["payload"] = obj["payload"]["synthetic_content"]
    return r.decode_publication_result(json.dumps(obj).encode())


def transition() -> m.MigrationTransition:
    artifact = (
        b"SYNTHETIC: wrap result payload in synthetic_content; schema/reader 1 -> 2"
    )
    descriptor = m.MigrationDescriptor(
        "composition",
        "synthetic-1-to-2",
        r.RecordKind.PUBLICATION_RESULT,
        1,
        2,
        1,
        2,
        m.artifact_fingerprint(artifact),
    )
    return m.MigrationTransition(
        descriptor,
        artifact,
        synthetic_transform,
        r.decode_publication_result,
        synthetic_reader,
    )


def data() -> bytes:
    encoded = r.encode_publication_result(committed(update=True))
    assert isinstance(encoded, bytes)
    return encoded


def test_synthetic_representation_preserves_exact_meaning() -> None:
    step = transition()
    original = data()
    result = m.prepare_migration(
        original,
        selected=step.descriptor,
        registry=m.MigrationRegistry((step,)),
        observed=m.MigrationObservation(1, 1, True, None),
    )
    assert isinstance(result, m.PreparedMigration)
    assert result.marker.stage is m.MigrationStage.PREPARED
    assert original == data()
    assert result.data != original
    assert synthetic_reader(result.data) == r.decode_publication_result(original)
    assert isinstance(r.decode_publication_result(result.data), r.RecordFailure)
    assert m.supported_migrations().transitions == ()
    # Runtime registry has no fabricated previous release.
    assert isinstance(
        m.prepare_migration(
            original,
            selected=step.descriptor,
            registry=m.supported_migrations(),
            observed=m.MigrationObservation(1, 1, True, None),
        ),
        r.RecordFailure,
    )


@pytest.mark.parametrize(
    ("schema", "reader", "complete", "marker_stage", "expected"),
    [
        (1, 1, True, None, m.MigrationDecision.PREPARE),
        (1, 1, False, None, m.MigrationDecision.INTERVENTION),
        (2, 2, True, m.MigrationStage.COMMITTED, m.MigrationDecision.VALIDATE_TARGET),
        (2, 2, True, None, m.MigrationDecision.INTERVENTION),
        (2, 2, False, m.MigrationStage.COMMITTED, m.MigrationDecision.INTERVENTION),
        (2, 2, True, m.MigrationStage.PREPARED, m.MigrationDecision.INTERVENTION),
        (1, 1, True, m.MigrationStage.COMMITTED, m.MigrationDecision.INTERVENTION),
        (2, 1, True, m.MigrationStage.COMMITTED, m.MigrationDecision.INTERVENTION),
        (3, 3, True, m.MigrationStage.COMMITTED, m.MigrationDecision.INTERVENTION),
    ],
)
def test_interruption_decisions(
    schema: int,
    reader: int,
    complete: bool,
    marker_stage: m.MigrationStage | None,
    expected: m.MigrationDecision,
) -> None:
    step = transition()
    marker = (
        None
        if marker_stage is None
        else m.MigrationMarker(step.descriptor, marker_stage)
    )
    observed = m.MigrationObservation(schema, reader, complete, marker)
    assert m.assess_migration(step.descriptor, observed) is expected
    calls: list[bytes] = []

    def transform(value: bytes) -> bytes:
        calls.append(value)
        return synthetic_transform(value)

    selected = replace(step, transform=transform)
    result = m.prepare_migration(
        data(),
        selected=step.descriptor,
        registry=m.MigrationRegistry((selected,)),
        observed=observed,
    )
    if expected is m.MigrationDecision.PREPARE:
        assert isinstance(result, m.PreparedMigration) and len(calls) == 1
    else:
        assert isinstance(result, r.RecordFailure) and calls == []


def test_fingerprint_identity_and_preconditions() -> None:
    step = transition()
    assert (
        m.artifact_fingerprint(b"abc")
        == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    for artifact in (b"", b"x" * 65537, cast(bytes, "bytes required")):
        with pytest.raises(ValueError):
            m.artifact_fingerprint(artifact)
    with pytest.raises(ValueError):
        replace(step, reviewed_artifact=b"different")
    with pytest.raises(ValueError):
        m.MigrationRegistry((step, step))
    with pytest.raises(ValueError):
        m.MigrationRegistry(
            (
                step,
                replace(
                    step, descriptor=replace(step.descriptor, migration_id="other")
                ),
            )
        )
    with pytest.raises(ValueError):
        replace(step.descriptor, target_schema=1)
    with pytest.raises(ValueError):
        replace(step.descriptor, source_reader=3)
    with pytest.raises(ValueError):
        replace(step.descriptor, source_schema=True)
    with pytest.raises(ValueError):
        replace(step.descriptor, fingerprint="X" * 64)
    changed = replace(step.descriptor, fingerprint="0" * 64)
    observed = m.MigrationObservation(
        2, 2, True, m.MigrationMarker(changed, m.MigrationStage.COMMITTED)
    )
    assert (
        m.assess_migration(step.descriptor, observed)
        is m.MigrationDecision.INTERVENTION
    )
    assert isinstance(
        m.prepare_migration(
            data(),
            selected=changed,
            registry=m.MigrationRegistry((step,)),
            observed=m.MigrationObservation(1, 1, True, None),
        ),
        r.RecordFailure,
    )
    # A complete-source assertion cannot replace envelope preconditions.
    assert isinstance(
        m.prepare_migration(
            synthetic_transform(data()),
            selected=step.descriptor,
            registry=m.MigrationRegistry((step,)),
            observed=m.MigrationObservation(1, 1, True, None),
        ),
        r.RecordFailure,
    )


@pytest.mark.parametrize(
    "failure", ["semantic", "exception", "reader", "scope", "header", "source"]
)
def test_failed_transform_never_returns_partial_or_success(failure: str) -> None:
    step = transition()

    def transform(value: bytes) -> bytes:
        if failure == "exception":
            raise RuntimeError("private-payload-marker")
        transformed = synthetic_transform(value)
        if failure == "semantic":
            obj = json.loads(transformed)
            obj["payload"]["synthetic_content"]["record"]["original"]["context"][
                "request_id"
            ] = "changed"
            return json.dumps(obj).encode()
        if failure == "header":
            return value
        return transformed

    def bad_reader(value: bytes) -> r.RecordFailure:
        return r.RecordFailure(r.RecordProblem.MALFORMED)

    selected = replace(step, transform=transform)
    if failure == "reader":
        selected = replace(selected, target_reader=bad_reader)
    if failure == "source":
        selected = replace(selected, source_reader=bad_reader)
    if failure == "scope":
        selected = replace(
            selected, descriptor=replace(selected.descriptor, owner="foreign")
        )
    result = m.prepare_migration(
        data(),
        selected=selected.descriptor,
        registry=m.MigrationRegistry((selected,)),
        observed=m.MigrationObservation(1, 1, True, None),
    )
    assert isinstance(result, r.RecordFailure)
    assert "private-payload-marker" not in repr(result)


def test_prepared_is_not_committed() -> None:
    step = transition()
    with pytest.raises(ValueError):
        m.PreparedMigration(
            data(), m.MigrationMarker(step.descriptor, m.MigrationStage.COMMITTED)
        )
