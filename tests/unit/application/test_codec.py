"""F5: durable JSON representation round-trip/corruption/version tests.

Structured for direct reuse once F6a adds a real SQLite Adapter: every
``encode_*``/``decode_*`` pair here proves the same contract that Adapter must
uphold when reading/writing ``record_json``/``descriptor_json``/`
`result_json``/``duty_json`` TEXT columns (LOCAL-PERSISTENCE-REALIZATION.md
SS7.2, SS10).
"""

from __future__ import annotations

import copy
import json

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
from legoai.reference.application import codec
from legoai.reference.application.configuration import compose_configuration

VERSION = Version(0, 1, 0)


def _target(
    tenant: str = "t1", owner: str = "owner1", app: str = "app1", instance: str = "i1"
) -> ConfigurationRef:
    scope = ReferenceScope(owner, TenantId(tenant))
    return ConfigurationRef(ApplicationRef(scope, ApplicationId(app)), instance)


def _operation(target: ConfigurationRef, op_id: str = "op1") -> OperationRef:
    return OperationRef(target, OperationId(op_id), "codec-fixture")


def _principal(pid: str = "p1") -> Principal:
    return Principal(PrincipalRef("issuer1", PrincipalId(pid)))


def _candidate(target: ConfigurationRef) -> ComposedConfiguration:
    return compose_configuration(
        target, (), contract_version=VERSION, interpretation_version=VERSION
    )


def _published(
    target: ConfigurationRef, revision: str = "r1"
) -> ConfigurationRevisionRef:
    return ConfigurationRevisionRef(target, revision, VERSION)


def _duty(target: ConfigurationRef) -> ConfigurationSourceSubmissionDuty:
    published = _published(target)
    return ConfigurationSourceSubmissionDuty(
        duty_id=DutyId("duty-1"),
        kind=DutyKind("source-submission"),
        operation=_operation(target),
        published=published,
        responsible_principal=_principal(),
        tenant_context=TenantContext(target.application.scope.tenant_id),
        requirement=EvidenceRequirement(published, "evidence needed"),
    )


# --------------------------------------------------------------------------
# Round-trip: value -> encode -> decode -> equal semantic value
# --------------------------------------------------------------------------


def test_owner_head_round_trip() -> None:
    target = _target()
    value = OwnerRevision(target, 3)
    record = codec.encode_owner_head(value)
    assert record["record_kind"] == "application_configuration_owner_head"
    assert record["record_schema_version"] == 1
    assert codec.decode_owner_head(record) == value


def test_published_revision_round_trip() -> None:
    target = _target()
    value = _published(target)
    record = codec.encode_published_revision(value)
    assert codec.decode_published_revision(record) == value


def test_revision_content_round_trip() -> None:
    target = _target()
    value = _candidate(target)
    record = codec.encode_revision_content(value)
    assert codec.decode_revision_content(record) == value


def test_publication_operation_round_trip_with_expected_revision() -> None:
    target = _target()
    value = ConfigurationPublicationOperation(
        operation=_operation(target),
        target=target,
        expected_revision=OwnerRevision(target, 2),
        candidate=_candidate(target),
        requested_by=_principal(),
    )
    record = codec.encode_publication_operation(value)
    assert codec.decode_publication_operation(record) == value


def test_publication_operation_round_trip_with_expected_absence() -> None:
    target = _target()
    value = ConfigurationPublicationOperation(
        operation=_operation(target),
        target=target,
        expected_revision=None,
        candidate=_candidate(target),
        requested_by=_principal(),
    )
    record = codec.encode_publication_operation(value)
    assert record["expected_revision"] is None
    assert codec.decode_publication_operation(record) == value


def test_publication_result_round_trip_committed() -> None:
    target = _target()
    value = ConfigurationPublicationResult(
        operation=_operation(target),
        stage=OperationStage.COMMITTED,
        resulting_revision=OwnerRevision(target, 1),
        published=_published(target),
        effect=EffectExtent.COMPLETED,
        error=None,
        duties=(DutyId("duty-1"), DutyId("duty-2")),
    )
    record = codec.encode_publication_result(value)
    assert codec.decode_publication_result(record) == value


def test_publication_result_round_trip_rejected() -> None:
    target = _target()
    value = ConfigurationPublicationResult(
        operation=_operation(target),
        stage=OperationStage.REJECTED,
        resulting_revision=None,
        published=None,
        effect=EffectExtent.NONE,
        error=ErrorDetail(
            ErrorCategory.CONFLICT, Recoverability.REQUIRES_INTERVENTION, ()
        ),
        duties=(),
    )
    record = codec.encode_publication_result(value)
    assert codec.decode_publication_result(record) == value


def test_source_submission_duty_round_trip() -> None:
    target = _target()
    value = _duty(target)
    record = codec.encode_source_submission_duty(value)
    assert codec.decode_source_submission_duty(record) == value


def test_text_layer_round_trip() -> None:
    target = _target()
    record = codec.encode_owner_head(OwnerRevision(target, 1))
    text = codec.dumps(record)
    assert isinstance(text, str)
    assert codec.loads(text) == record


# --------------------------------------------------------------------------
# Effect uncertainty must round-trip exactly, including unknown
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "effect",
    [
        EffectExtent.NONE,
        EffectExtent.PARTIAL,
        EffectExtent.COMPLETED,
        EffectExtent.UNKNOWN,
    ],
)
def test_effect_extent_round_trips_every_member(effect: EffectExtent) -> None:
    target = _target()
    stage = OperationStage.COMMITTED
    value = ConfigurationPublicationResult(
        operation=_operation(target),
        stage=stage,
        resulting_revision=OwnerRevision(target, 1),
        published=_published(target),
        effect=effect,
        error=None,
        duties=(),
    )
    record = codec.encode_publication_result(value)
    assert record["effect"] == effect.value
    decoded = codec.decode_publication_result(record)
    assert decoded.effect is effect


# --------------------------------------------------------------------------
# H and R must never share a field name or be conflated on decode
# --------------------------------------------------------------------------


def test_head_and_published_revision_use_distinct_field_names() -> None:
    target = _target()
    head_record = codec.encode_owner_head(OwnerRevision(target, 5))
    published_record = codec.encode_published_revision(_published(target, "r5"))
    assert "head_revision" in head_record
    assert "revision" not in head_record
    assert "configuration_revision_id" in published_record
    assert "revision" not in published_record
    assert head_record.keys().isdisjoint({"configuration_revision_id"})
    assert published_record.keys().isdisjoint({"head_revision"})


# --------------------------------------------------------------------------
# Operation-result recovery: decode reconstructs recorded meaning, no recompute
# --------------------------------------------------------------------------


def test_decoded_result_is_recorded_meaning_not_recomputed() -> None:
    target = _target()
    # A REJECTED result whose resulting_revision would be "wrong" if some
    # decoder recomputed anything from current state -- it must come back
    # exactly as stored.
    value = ConfigurationPublicationResult(
        operation=_operation(target),
        stage=OperationStage.REJECTED,
        resulting_revision=None,
        published=None,
        effect=EffectExtent.NONE,
        error=ErrorDetail(ErrorCategory.CONFLICT, Recoverability.TERMINAL, ()),
        duties=(),
    )
    record = codec.encode_publication_result(value)
    decoded_once = codec.decode_publication_result(record)
    decoded_twice = codec.decode_publication_result(copy.deepcopy(record))
    assert decoded_once == decoded_twice == value


# --------------------------------------------------------------------------
# Corrupt / invalid representation fixtures fail closed
# --------------------------------------------------------------------------


def test_missing_record_schema_version_fails() -> None:
    target = _target()
    record = codec.encode_owner_head(OwnerRevision(target, 1))
    del record["record_schema_version"]
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_owner_head(record)


def test_unsupported_record_schema_version_fails_closed() -> None:
    target = _target()
    record = codec.encode_owner_head(OwnerRevision(target, 1))
    record["record_schema_version"] = 999
    with pytest.raises(codec.UnsupportedRepresentationVersionError):
        codec.decode_owner_head(record)


def test_wrong_record_kind_rejected() -> None:
    target = _target()
    record = codec.encode_owner_head(OwnerRevision(target, 1))
    record["record_kind"] = "application_configuration_published_revision"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_owner_head(record)


def test_wrong_type_for_head_revision_rejected() -> None:
    target = _target()
    record = codec.encode_owner_head(OwnerRevision(target, 1))
    record["head_revision"] = "1"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_owner_head(record)


def test_bool_rejected_where_integer_required() -> None:
    target = _target()
    record = codec.encode_owner_head(OwnerRevision(target, 1))
    record["head_revision"] = True
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_owner_head(record)


def test_missing_required_id_field_rejected() -> None:
    target = _target()
    record = codec.encode_source_submission_duty(_duty(target))
    del record["duty_id"]
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_source_submission_duty(record)


def test_unknown_field_rejected_closed_schema() -> None:
    target = _target()
    record = codec.encode_owner_head(OwnerRevision(target, 1))
    record["extra_unspecified_field"] = "surprise"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_owner_head(record)


def test_unknown_effect_status_value_rejected_not_defaulted() -> None:
    target = _target()
    record = codec.encode_publication_result(
        ConfigurationPublicationResult(
            operation=_operation(target),
            stage=OperationStage.COMMITTED,
            resulting_revision=OwnerRevision(target, 1),
            published=_published(target),
            effect=EffectExtent.UNKNOWN,
            error=None,
            duties=(),
        )
    )
    record["effect"] = "not-a-real-effect-status"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_publication_result(record)


def test_invalid_revision_semantic_mismatch_after_decode_rejected() -> None:
    # published.configuration must match resulting_revision.subject; corrupt
    # the nested published instance field so the domain constructor itself
    # rejects it -- proving "invalid semantic value after decode" fails
    # closed rather than silently constructing an inconsistent value.
    target = _target()
    other = _target(instance="other")
    record = codec.encode_publication_result(
        ConfigurationPublicationResult(
            operation=_operation(target),
            stage=OperationStage.COMMITTED,
            resulting_revision=OwnerRevision(target, 1),
            published=_published(target),
            effect=EffectExtent.COMPLETED,
            error=None,
            duties=(),
        )
    )
    record["published"]["configuration"] = codec.encode_owner_head(
        OwnerRevision(other, 1)
    )["subject"]
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_publication_result(record)


def test_malformed_nested_record_rejected() -> None:
    target = _target()
    record = codec.encode_source_submission_duty(_duty(target))
    record["operation"] = "not-an-object"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_source_submission_duty(record)


def test_duplicate_object_key_rejected_at_text_layer() -> None:
    text = '{"a": 1, "a": 2}'
    with pytest.raises(codec.MalformedRepresentationError):
        codec.loads(text)


def test_duplicate_object_key_rejected_in_nested_object() -> None:
    text = '{"outer": {"a": 1, "a": 2}}'
    with pytest.raises(codec.MalformedRepresentationError):
        codec.loads(text)


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_numbers_rejected(token: str) -> None:
    with pytest.raises(codec.MalformedRepresentationError):
        codec.loads(f'{{"value": {token}}}')


def test_oversize_record_rejected() -> None:
    huge = "x" * (codec.max_record_bytes() + 1)
    with pytest.raises(codec.MalformedRepresentationError):
        codec.loads(json.dumps({"padding": huge}))


def test_excessive_nesting_rejected() -> None:
    nested: dict[str, object] = {"leaf": 1}
    for _ in range(codec.max_record_depth() + 5):
        nested = {"wrap": nested}
    with pytest.raises(codec.MalformedRepresentationError):
        codec.loads(json.dumps(nested))


def test_malformed_json_syntax_rejected() -> None:
    with pytest.raises(codec.MalformedRepresentationError):
        codec.loads("{not valid json")


def test_top_level_non_object_rejected() -> None:
    with pytest.raises(codec.MalformedRepresentationError):
        codec.loads("[1, 2, 3]")


def test_wrong_top_level_type_for_encode_rejected() -> None:
    with pytest.raises(TypeError):
        codec.encode_owner_head("not-an-owner-revision")  # type: ignore[arg-type]


def test_dumps_rejects_non_dict_input() -> None:
    with pytest.raises(TypeError):
        codec.dumps(["not", "a", "dict"])  # type: ignore[arg-type]


def test_loads_rejects_non_str_input() -> None:
    with pytest.raises(codec.MalformedRepresentationError):
        codec.loads(b"{}")  # type: ignore[arg-type]


def test_record_kind_wrong_type_rejected() -> None:
    target = _target()
    record = codec.encode_owner_head(OwnerRevision(target, 1))
    record["record_kind"] = 12345
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_owner_head(record)


def test_record_schema_version_wrong_type_rejected() -> None:
    target = _target()
    record = codec.encode_owner_head(OwnerRevision(target, 1))
    record["record_schema_version"] = "1"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_owner_head(record)


def test_missing_record_kind_key_entirely_rejected() -> None:
    target = _target()
    record = codec.encode_owner_head(OwnerRevision(target, 1))
    del record["record_kind"]
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_owner_head(record)


def test_operation_ref_unknown_subject_kind_rejected() -> None:
    target = _target()
    record = codec.encode_publication_result(
        ConfigurationPublicationResult(
            operation=_operation(target),
            stage=OperationStage.COMMITTED,
            resulting_revision=OwnerRevision(target, 1),
            published=_published(target),
            effect=EffectExtent.COMPLETED,
            error=None,
            duties=(),
        )
    )
    record["operation"]["subject_kind"] = "unrecognized"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_publication_result(record)


def test_normalization_mode_unknown_value_rejected() -> None:
    target = _target()
    record = codec.encode_revision_content(_candidate(target))
    record["effective"]["normalization_mode"] = "not-a-real-mode"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_revision_content(record)


def test_source_layer_unknown_value_rejected() -> None:
    target = _target()
    record = codec.encode_revision_content(_candidate(target))
    record["sources"][0]["layer"] = "not-a-real-layer"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_revision_content(record)


def test_error_category_unknown_value_rejected() -> None:
    target = _target()
    record = codec.encode_publication_result(
        ConfigurationPublicationResult(
            operation=_operation(target),
            stage=OperationStage.REJECTED,
            resulting_revision=None,
            published=None,
            effect=EffectExtent.NONE,
            error=ErrorDetail(ErrorCategory.CONFLICT, Recoverability.TERMINAL, ()),
            duties=(),
        )
    )
    record["error"]["category"] = "not-a-real-category"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_publication_result(record)


def test_recoverability_unknown_value_rejected() -> None:
    target = _target()
    record = codec.encode_publication_result(
        ConfigurationPublicationResult(
            operation=_operation(target),
            stage=OperationStage.REJECTED,
            resulting_revision=None,
            published=None,
            effect=EffectExtent.NONE,
            error=ErrorDetail(ErrorCategory.CONFLICT, Recoverability.TERMINAL, ()),
            duties=(),
        )
    )
    record["error"]["recoverability"] = "not-a-real-recoverability"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_publication_result(record)


def test_stage_unknown_value_rejected() -> None:
    target = _target()
    record = codec.encode_publication_result(
        ConfigurationPublicationResult(
            operation=_operation(target),
            stage=OperationStage.COMMITTED,
            resulting_revision=OwnerRevision(target, 1),
            published=_published(target),
            effect=EffectExtent.COMPLETED,
            error=None,
            duties=(),
        )
    )
    record["stage"] = "not-a-real-stage"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_publication_result(record)


def test_duties_wrong_element_type_rejected() -> None:
    target = _target()
    record = codec.encode_publication_result(
        ConfigurationPublicationResult(
            operation=_operation(target),
            stage=OperationStage.COMMITTED,
            resulting_revision=OwnerRevision(target, 1),
            published=_published(target),
            effect=EffectExtent.COMPLETED,
            error=None,
            duties=(DutyId("duty-1"),),
        )
    )
    record["duties"] = [123]
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_publication_result(record)


def test_causes_wrong_container_type_rejected() -> None:
    target = _target()
    record = codec.encode_publication_result(
        ConfigurationPublicationResult(
            operation=_operation(target),
            stage=OperationStage.REJECTED,
            resulting_revision=None,
            published=None,
            effect=EffectExtent.NONE,
            error=ErrorDetail(ErrorCategory.CONFLICT, Recoverability.TERMINAL, ()),
            duties=(),
        )
    )
    record["error"]["causes"] = "not-a-list"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_publication_result(record)


def test_sources_wrong_container_type_rejected() -> None:
    target = _target()
    record = codec.encode_revision_content(_candidate(target))
    record["sources"] = "not-a-list"
    with pytest.raises(codec.InvalidRepresentationError):
        codec.decode_revision_content(record)


# --------------------------------------------------------------------------
# None / empty / missing distinctions must survive round-trip
# --------------------------------------------------------------------------


def test_normalization_patch_none_versus_empty_tuple_distinction_preserved() -> None:
    target = _target()
    candidate_with_defaults_only = _candidate(target)
    # The default-only ComposedConfiguration's sole source carries every
    # field populated (defaults), so exercise the sources[0].values fields
    # directly through the nested captured-candidate codec instead.
    from legoai.application.values import NormalizationPatch  # noqa: PLC0415

    patch_missing = NormalizationPatch(None, None, None)
    patch_empty_whitespace = NormalizationPatch(10, None, ())

    from legoai.reference.application.codec import (  # noqa: PLC0415
        _decode_normalization_patch,
        _encode_normalization_patch,
    )

    missing_record = _encode_normalization_patch(patch_missing)
    assert missing_record["allowed_whitespace"] is None
    assert _decode_normalization_patch(missing_record, "ctx") == patch_missing

    empty_record = _encode_normalization_patch(patch_empty_whitespace)
    assert empty_record["allowed_whitespace"] == []
    assert _decode_normalization_patch(empty_record, "ctx") == patch_empty_whitespace
    assert patch_missing != patch_empty_whitespace
    assert candidate_with_defaults_only.sources  # sanity: fixture still valid


# --------------------------------------------------------------------------
# Representation version is a distinct concept from domain Version/H/R
# --------------------------------------------------------------------------


def test_record_schema_version_type_is_distinct_from_domain_version() -> None:
    assert codec.RecordSchemaVersion(1) != Version(0, 1, 0)  # type: ignore[comparison-overlap]
    with pytest.raises(TypeError):
        codec.RecordSchemaVersion("1")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        codec.RecordSchemaVersion(0)


def test_current_schema_version_matches_every_encoder() -> None:
    target = _target()
    records = [
        codec.encode_owner_head(OwnerRevision(target, 1)),
        codec.encode_published_revision(_published(target)),
        codec.encode_revision_content(_candidate(target)),
        codec.encode_source_submission_duty(_duty(target)),
    ]
    for record in records:
        assert record["record_schema_version"] == codec.current_schema_version().value
