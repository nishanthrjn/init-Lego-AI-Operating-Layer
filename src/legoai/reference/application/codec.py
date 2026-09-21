"""F5: durable JSON representation for the Application Composition owner's F4
values (LOCAL-PERSISTENCE-REALIZATION.md SS7.2, SS10; ADR-004/008/009).

This module is representation only. It does not open a database connection,
execute SQL, run a migration against live storage, or orchestrate recovery --
those are F6a's scope. It exists so a future SQLite Adapter can encode/decode
exact F4 meaning into the ``record_json``/``descriptor_json``/``result_json``/
``duty_json`` TEXT columns the accepted persistence decision names, without
inventing storage semantics inside that Adapter.

Version model
-------------
Three distinct version concepts appear near this boundary and must never be
confused:

* ``Version`` (``legoai.kernel.versions``) -- the domain contract/interpretation
  triple (e.g. a configuration contract version). Unrelated to storage format.
* ``OwnerRevision`` (H) / ``ConfigurationRevisionRef`` (R) -- F4's owner-local
  mutation guard and immutable content identity. Never serialized under one
  ambiguous ``revision`` field; see ``head_revision`` and
  ``configuration_revision_id`` below.
* :class:`RecordSchemaVersion` -- introduced by this module. Tracks only how a
  *durable JSON envelope shape* is written and read. It says nothing about
  domain meaning and is not compared against ``Version``, H, or R.

Compatibility policy
---------------------
Every top-level record is a JSON object declaring ``record_kind`` and
``record_schema_version`` plus a **closed** field set (LOCAL-PERSISTENCE-
REALIZATION.md SS10: "First schema has a closed field set; no catch-all
executable extension bag"). An unknown field, an unsupported
``record_schema_version``, a missing required field, or a malformed nested
value all fail closed -- decoding never falls back to a current/default
interpretation of historical data. Only one record schema version (1) exists
for every record kind defined here today; no synthetic prior version is
fabricated to exercise migration machinery that has no real case yet
(Gate-1 plan's own anti-overengineering stance). Every ``decode_*`` function
below is the seam a real future transition would extend -- each currently
only accepts the one supported version and fails closed otherwise.

Codec ownership
----------------
Canonical values (``legoai.application.values``, ``legoai.evidence.values``,
``legoai.governance.values``, ``legoai.kernel.*``) remain persistence-agnostic:
none of them gain ``to_dict``/``from_dict``/``to_json``/``from_json`` methods.
All encode/decode responsibility lives here, at the Application Composition
owner's reference-persistence boundary (ADR-002 SS7.2 names
``legoai.reference.application`` as this owner's realization location).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from legoai.application.values import (
    CapturedCandidate,
    ComposedConfiguration,
    ConfigurationPublicationOperation,
    ConfigurationPublicationResult,
    ConfigurationSourceSubmissionDuty,
    EffectiveConfiguration,
    NormalizationMode,
    NormalizationPatch,
    OperationStage,
    SourceLayer,
    SourceProvenance,
)
from legoai.evidence.values import EvidenceRequirement
from legoai.governance.values import Principal
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorCause, ErrorDetail, Recoverability
from legoai.kernel.identity import (
    ApplicationId,
    OperationId,
    PrincipalId,
    TenantId,
)
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

type JsonRecord = dict[str, Any]


# --------------------------------------------------------------------------
# Exception surface (LOCAL-PERSISTENCE-REALIZATION.md SS10; F5 SS13)
# --------------------------------------------------------------------------


class RepresentationError(ValueError):
    """Base for every F5 decode/validation failure. Never raised directly."""


class MalformedRepresentationError(RepresentationError):
    """Invalid JSON syntax, duplicate object keys, non-finite numbers, or
    input exceeding the bounded size/depth preflight -- a syntax-level defect
    the caller cannot repair by reinterpreting field meaning."""


class UnsupportedRepresentationVersionError(RepresentationError):
    """``record_schema_version`` is not one this reader supports.

    Never interpreted as the current version; the caller must use a reader
    that actually supports the stored version, or accept the record as
    unavailable (LOCAL-PERSISTENCE-REALIZATION.md SS6, "Unsupported version").
    """


class InvalidRepresentationError(RepresentationError):
    """Well-formed JSON that fails structural or semantic validation: missing
    required field, unknown field, wrong field type, or an invalid semantic
    value once decoded values reach a domain constructor."""


# --------------------------------------------------------------------------
# Storage representation version (distinct from Version/H/R; see module docstring)
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RecordSchemaVersion:
    """Durable JSON envelope schema version for one record kind.

    Not a domain ``Version``, not H, not R, not a Plugin/Application/Artifact
    version. Comparing this to any of those is a defect in the caller, not a
    supported compatibility check.
    """

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int:
            raise TypeError("record schema version must be an integer")
        if self.value < 1:
            raise ValueError("record schema version must be positive")


def current_schema_version() -> RecordSchemaVersion:
    """The one record schema version every encoder below currently writes."""
    return RecordSchemaVersion(1)


def max_record_bytes() -> int:
    """Bounded UTF-8 byte preflight limit (test fixture bound, not a runtime
    contract limit; LOCAL-PERSISTENCE-REALIZATION.md SS4.3/SS17)."""
    return 65536


def max_record_depth() -> int:
    """Bounded nesting-depth limit enforced before trusting parsed JSON."""
    return 16


class _RecordKind(Enum):
    OWNER_HEAD = "application_configuration_owner_head"
    PUBLISHED_REVISION = "application_configuration_published_revision"
    REVISION_CONTENT = "application_configuration_revision_content"
    PUBLICATION_OPERATION = "application_configuration_publication_operation"
    PUBLICATION_RESULT = "application_configuration_publication_result"
    SOURCE_SUBMISSION_DUTY = "application_configuration_source_submission_duty"


# --------------------------------------------------------------------------
# Strict JSON text layer (LOCAL-PERSISTENCE-REALIZATION.md SS10)
# --------------------------------------------------------------------------


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise MalformedRepresentationError(f"duplicate object key {key!r}")
        seen.add(key)
        result[key] = value
    return result


def _reject_non_finite(token: str) -> float:
    raise MalformedRepresentationError(f"non-finite numeric token {token!r}")


def _check_depth(value: object, remaining: int, *, context: str = "record") -> None:
    if remaining < 0:
        raise MalformedRepresentationError(f"{context} exceeds maximum nesting depth")
    if type(value) is dict:
        for key, nested in cast("dict[str, object]", value).items():
            _check_depth(nested, remaining - 1, context=f"{context}.{key}")
    elif type(value) is list:
        for index, nested in enumerate(cast("list[object]", value)):
            _check_depth(nested, remaining - 1, context=f"{context}[{index}]")


def dumps(record: JsonRecord) -> str:
    """Render one already-built record envelope as canonical UTF-8 JSON text.

    Sorted keys and fixed separators make fixtures reproducible byte-for-byte
    (LOCAL-PERSISTENCE-REALIZATION.md SS10); this is not a cryptographic
    canonicalization and carries no ordering/hashing authority (F5 SS20).
    """
    if type(record) is not dict:
        raise TypeError("record must be a built-in dictionary")
    return json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)


def loads(text: str) -> JsonRecord:
    """Parse durable JSON text into a plain record dict with strict decoding.

    Rejects duplicate object keys, non-finite numbers, oversize input, and
    excessive nesting before returning. Does not know any record kind's
    field shape -- callers still run the matching ``decode_*`` validation.
    """
    if type(text) is not str:
        raise MalformedRepresentationError("record text must be a built-in string")
    if len(text.encode("utf-8")) > max_record_bytes():
        raise MalformedRepresentationError("record exceeds the maximum byte bound")
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except json.JSONDecodeError as exc:
        raise MalformedRepresentationError(str(exc)) from exc
    _check_depth(parsed, max_record_depth())
    if type(parsed) is not dict:
        raise MalformedRepresentationError("top-level record must be a JSON object")
    return cast("JsonRecord", parsed)


# --------------------------------------------------------------------------
# Field-level helpers (closed-field, exact-type validation)
# --------------------------------------------------------------------------


def _require_object(record: object, context: str) -> JsonRecord:
    if type(record) is not dict:
        raise InvalidRepresentationError(f"{context} must be a JSON object")
    return cast("JsonRecord", record)


def _closed_fields(record: JsonRecord, allowed: frozenset[str], context: str) -> None:
    missing = allowed - record.keys()
    if missing:
        raise InvalidRepresentationError(
            f"{context} missing required field(s): {sorted(missing)}"
        )
    extra = record.keys() - allowed
    if extra:
        raise InvalidRepresentationError(
            f"{context} has unknown field(s): {sorted(extra)}"
        )


def _require_str(record: JsonRecord, key: str, context: str) -> str:
    value = record[key]
    if type(value) is not str:
        raise InvalidRepresentationError(f"{context}.{key} must be text")
    return value


def _require_int(record: JsonRecord, key: str, context: str) -> int:
    value = record[key]
    if type(value) is not int:
        raise InvalidRepresentationError(f"{context}.{key} must be an integer")
    return value


def _require_str_or_none(record: JsonRecord, key: str, context: str) -> str | None:
    value = record[key]
    if value is None:
        return None
    if type(value) is not str:
        raise InvalidRepresentationError(f"{context}.{key} must be text or null")
    return value


def _require_int_or_none(record: JsonRecord, key: str, context: str) -> int | None:
    value = record[key]
    if value is None:
        return None
    if type(value) is not int:
        raise InvalidRepresentationError(f"{context}.{key} must be an integer or null")
    return value


def _require_str_tuple_or_none(
    record: JsonRecord, key: str, context: str
) -> tuple[str, ...] | None:
    value = record[key]
    if value is None:
        return None
    if type(value) is not list:
        raise InvalidRepresentationError(f"{context}.{key} must be an array or null")
    items = cast("list[object]", value)
    for item in items:
        if type(item) is not str:
            raise InvalidRepresentationError(f"{context}.{key} elements must be text")
    return tuple(cast("list[str]", items))


def _build(context: str, ctor: Any, *args: object) -> Any:
    try:
        return ctor(*args)
    except (TypeError, ValueError) as exc:
        raise InvalidRepresentationError(f"{context}: {exc}") from exc


def _require_kind_and_version(
    record: JsonRecord, expected_kind: _RecordKind, context: str
) -> None:
    if "record_kind" not in record or "record_schema_version" not in record:
        raise InvalidRepresentationError(
            f"{context} missing record_kind or record_schema_version"
        )
    kind = record["record_kind"]
    if type(kind) is not str:
        raise InvalidRepresentationError(f"{context}.record_kind must be text")
    if kind != expected_kind.value:
        raise InvalidRepresentationError(
            f"{context} has record_kind {kind!r}, expected {expected_kind.value!r}"
        )
    version = record["record_schema_version"]
    if type(version) is not int:
        raise InvalidRepresentationError(
            f"{context}.record_schema_version must be an integer"
        )
    if version != current_schema_version().value:
        raise UnsupportedRepresentationVersionError(
            f"{context} has unsupported record_schema_version {version}"
        )


# --------------------------------------------------------------------------
# Nested-value codecs (leaves first; none of these are top-level records)
# --------------------------------------------------------------------------


def _encode_version(value: Version) -> JsonRecord:
    return {"major": value.major, "minor": value.minor, "patch": value.patch}


def _decode_version(record: object, context: str) -> Version:
    obj = _require_object(record, context)
    _closed_fields(obj, frozenset({"major", "minor", "patch"}), context)
    major = _require_int(obj, "major", context)
    minor = _require_int(obj, "minor", context)
    patch = _require_int(obj, "patch", context)
    return cast(Version, _build(context, Version, major, minor, patch))


def _encode_scope(value: ReferenceScope) -> JsonRecord:
    return {"owner": value.owner, "tenant_id": value.tenant_id.value}


def _decode_scope(record: object, context: str) -> ReferenceScope:
    obj = _require_object(record, context)
    _closed_fields(obj, frozenset({"owner", "tenant_id"}), context)
    owner = _require_str(obj, "owner", context)
    tenant_id = _build(context, TenantId, _require_str(obj, "tenant_id", context))
    return cast(ReferenceScope, _build(context, ReferenceScope, owner, tenant_id))


def _encode_application_ref(value: ApplicationRef) -> JsonRecord:
    return {
        "scope": _encode_scope(value.scope),
        "application_id": value.application_id.value,
    }


def _decode_application_ref(record: object, context: str) -> ApplicationRef:
    obj = _require_object(record, context)
    _closed_fields(obj, frozenset({"scope", "application_id"}), context)
    scope = _decode_scope(obj["scope"], f"{context}.scope")
    application_id = _build(
        context, ApplicationId, _require_str(obj, "application_id", context)
    )
    return cast(ApplicationRef, _build(context, ApplicationRef, scope, application_id))


def _encode_configuration_ref(value: ConfigurationRef) -> JsonRecord:
    return {
        "application": _encode_application_ref(value.application),
        "instance": value.instance,
    }


def _decode_configuration_ref(record: object, context: str) -> ConfigurationRef:
    obj = _require_object(record, context)
    _closed_fields(obj, frozenset({"application", "instance"}), context)
    application = _decode_application_ref(obj["application"], f"{context}.application")
    instance = _require_str(obj, "instance", context)
    return cast(
        ConfigurationRef, _build(context, ConfigurationRef, application, instance)
    )


def _encode_operation_ref(value: OperationRef) -> JsonRecord:
    if type(value.subject) is ApplicationRef:
        subject_kind = "application"
        subject = _encode_application_ref(value.subject)
    else:
        subject_kind = "configuration"
        subject = _encode_configuration_ref(cast(ConfigurationRef, value.subject))
    return {
        "subject_kind": subject_kind,
        "subject": subject,
        "operation_id": value.operation_id.value,
        "contract_identity": value.contract_identity,
    }


def _decode_operation_ref(record: object, context: str) -> OperationRef:
    obj = _require_object(record, context)
    _closed_fields(
        obj,
        frozenset({"subject_kind", "subject", "operation_id", "contract_identity"}),
        context,
    )
    subject_kind = _require_str(obj, "subject_kind", context)
    if subject_kind == "application":
        subject: ApplicationRef | ConfigurationRef = _decode_application_ref(
            obj["subject"], f"{context}.subject"
        )
    elif subject_kind == "configuration":
        subject = _decode_configuration_ref(obj["subject"], f"{context}.subject")
    else:
        raise InvalidRepresentationError(
            f"{context}.subject_kind must be 'application' or 'configuration'"
        )
    operation_id = _build(
        context, OperationId, _require_str(obj, "operation_id", context)
    )
    contract_identity = _require_str(obj, "contract_identity", context)
    return cast(
        OperationRef,
        _build(context, OperationRef, subject, operation_id, contract_identity),
    )


def _encode_configuration_revision_ref(value: ConfigurationRevisionRef) -> JsonRecord:
    return {
        "configuration": _encode_configuration_ref(value.configuration),
        "configuration_revision_id": value.revision,
        "contract_version": _encode_version(value.contract_version),
    }


def _decode_configuration_revision_ref(
    record: object, context: str
) -> ConfigurationRevisionRef:
    obj = _require_object(record, context)
    _closed_fields(
        obj,
        frozenset({"configuration", "configuration_revision_id", "contract_version"}),
        context,
    )
    configuration = _decode_configuration_ref(
        obj["configuration"], f"{context}.configuration"
    )
    revision_id = _require_str(obj, "configuration_revision_id", context)
    contract_version = _decode_version(
        obj["contract_version"], f"{context}.contract_version"
    )
    return cast(
        ConfigurationRevisionRef,
        _build(
            context,
            ConfigurationRevisionRef,
            configuration,
            revision_id,
            contract_version,
        ),
    )


def _encode_owner_revision(value: OwnerRevision) -> JsonRecord:
    return {
        "subject": _encode_configuration_ref(value.subject),
        "head_revision": value.value,
    }


def _decode_owner_revision(record: object, context: str) -> OwnerRevision:
    obj = _require_object(record, context)
    _closed_fields(obj, frozenset({"subject", "head_revision"}), context)
    subject = _decode_configuration_ref(obj["subject"], f"{context}.subject")
    head_revision = _require_int(obj, "head_revision", context)
    return cast(OwnerRevision, _build(context, OwnerRevision, subject, head_revision))


def _encode_principal_ref(value: PrincipalRef) -> JsonRecord:
    return {"issuer": value.issuer, "principal_id": value.principal_id.value}


def _decode_principal_ref(record: object, context: str) -> PrincipalRef:
    obj = _require_object(record, context)
    _closed_fields(obj, frozenset({"issuer", "principal_id"}), context)
    issuer = _require_str(obj, "issuer", context)
    principal_id = _build(
        context, PrincipalId, _require_str(obj, "principal_id", context)
    )
    return cast(PrincipalRef, _build(context, PrincipalRef, issuer, principal_id))


def _encode_principal(value: Principal) -> JsonRecord:
    return {"reference": _encode_principal_ref(value.reference)}


def _decode_principal(record: object, context: str) -> Principal:
    obj = _require_object(record, context)
    _closed_fields(obj, frozenset({"reference"}), context)
    reference = _decode_principal_ref(obj["reference"], f"{context}.reference")
    return cast(Principal, _build(context, Principal, reference))


def _encode_tenant_context(value: TenantContext) -> JsonRecord:
    return {"tenant_id": value.tenant_id.value}


def _decode_tenant_context(record: object, context: str) -> TenantContext:
    obj = _require_object(record, context)
    _closed_fields(obj, frozenset({"tenant_id"}), context)
    tenant_id = _build(context, TenantId, _require_str(obj, "tenant_id", context))
    return cast(TenantContext, _build(context, TenantContext, tenant_id))


def _encode_evidence_requirement(value: EvidenceRequirement) -> JsonRecord:
    return {
        "subject": _encode_configuration_revision_ref(value.subject),
        "description": value.description,
    }


def _decode_evidence_requirement(record: object, context: str) -> EvidenceRequirement:
    obj = _require_object(record, context)
    _closed_fields(obj, frozenset({"subject", "description"}), context)
    subject = _decode_configuration_revision_ref(obj["subject"], f"{context}.subject")
    description = _require_str(obj, "description", context)
    return cast(
        EvidenceRequirement,
        _build(context, EvidenceRequirement, subject, description),
    )


def _encode_source_provenance(value: SourceProvenance) -> JsonRecord:
    return {
        "owner": value.owner,
        "source_id": value.source_id,
        "source_revision": value.source_revision,
        "contract_version": _encode_version(value.contract_version),
        "interpretation_version": _encode_version(value.interpretation_version),
    }


def _decode_source_provenance(record: object, context: str) -> SourceProvenance:
    obj = _require_object(record, context)
    _closed_fields(
        obj,
        frozenset(
            {
                "owner",
                "source_id",
                "source_revision",
                "contract_version",
                "interpretation_version",
            }
        ),
        context,
    )
    owner = _require_str(obj, "owner", context)
    source_id = _require_str(obj, "source_id", context)
    source_revision = _require_str(obj, "source_revision", context)
    contract_version = _decode_version(
        obj["contract_version"], f"{context}.contract_version"
    )
    interpretation_version = _decode_version(
        obj["interpretation_version"], f"{context}.interpretation_version"
    )
    return cast(
        SourceProvenance,
        _build(
            context,
            SourceProvenance,
            owner,
            source_id,
            source_revision,
            contract_version,
            interpretation_version,
        ),
    )


def _encode_normalization_patch(value: NormalizationPatch) -> JsonRecord:
    return {
        "max_input_length": value.max_input_length,
        "normalization_mode": (
            value.normalization_mode.value
            if value.normalization_mode is not None
            else None
        ),
        "allowed_whitespace": (
            list(value.allowed_whitespace)
            if value.allowed_whitespace is not None
            else None
        ),
    }


def _decode_normalization_patch(record: object, context: str) -> NormalizationPatch:
    obj = _require_object(record, context)
    _closed_fields(
        obj,
        frozenset({"max_input_length", "normalization_mode", "allowed_whitespace"}),
        context,
    )
    max_input_length = _require_int_or_none(obj, "max_input_length", context)
    mode_text = _require_str_or_none(obj, "normalization_mode", context)
    allowed_modes = frozenset(member.value for member in NormalizationMode)
    if mode_text is not None and mode_text not in allowed_modes:
        raise InvalidRepresentationError(
            f"{context}.normalization_mode has unknown value {mode_text!r}"
        )
    mode = NormalizationMode(mode_text) if mode_text is not None else None
    allowed_whitespace = _require_str_tuple_or_none(obj, "allowed_whitespace", context)
    return cast(
        NormalizationPatch,
        _build(context, NormalizationPatch, max_input_length, mode, allowed_whitespace),
    )


def _encode_captured_candidate(value: CapturedCandidate) -> JsonRecord:
    return {
        "target": _encode_configuration_ref(value.target),
        "provenance": _encode_source_provenance(value.provenance),
        "layer": value.layer.value,
        "values": _encode_normalization_patch(value.values),
    }


def _decode_captured_candidate(record: object, context: str) -> CapturedCandidate:
    obj = _require_object(record, context)
    _closed_fields(obj, frozenset({"target", "provenance", "layer", "values"}), context)
    target = _decode_configuration_ref(obj["target"], f"{context}.target")
    provenance = _decode_source_provenance(obj["provenance"], f"{context}.provenance")
    layer_text = _require_str(obj, "layer", context)
    allowed_layers = frozenset(member.value for member in SourceLayer)
    if layer_text not in allowed_layers:
        raise InvalidRepresentationError(
            f"{context}.layer has unknown value {layer_text!r}"
        )
    layer = SourceLayer(layer_text)
    patch = _decode_normalization_patch(obj["values"], f"{context}.values")
    return cast(
        CapturedCandidate,
        _build(context, CapturedCandidate, target, provenance, layer, patch),
    )


def _encode_effective_configuration(value: EffectiveConfiguration) -> JsonRecord:
    return {
        "contract_version": _encode_version(value.contract_version),
        "interpretation_version": _encode_version(value.interpretation_version),
        "max_input_length": value.max_input_length,
        "normalization_mode": value.normalization_mode.value,
        "allowed_whitespace": list(value.allowed_whitespace),
    }


def _decode_effective_configuration(
    record: object, context: str
) -> EffectiveConfiguration:
    obj = _require_object(record, context)
    _closed_fields(
        obj,
        frozenset(
            {
                "contract_version",
                "interpretation_version",
                "max_input_length",
                "normalization_mode",
                "allowed_whitespace",
            }
        ),
        context,
    )
    contract_version = _decode_version(
        obj["contract_version"], f"{context}.contract_version"
    )
    interpretation_version = _decode_version(
        obj["interpretation_version"], f"{context}.interpretation_version"
    )
    max_input_length = _require_int(obj, "max_input_length", context)
    mode_text = _require_str(obj, "normalization_mode", context)
    allowed_modes = frozenset(member.value for member in NormalizationMode)
    if mode_text not in allowed_modes:
        raise InvalidRepresentationError(
            f"{context}.normalization_mode has unknown value {mode_text!r}"
        )
    mode = NormalizationMode(mode_text)
    whitespace = _require_str_tuple_or_none(obj, "allowed_whitespace", context)
    if whitespace is None:
        raise InvalidRepresentationError(
            f"{context}.allowed_whitespace must be an array"
        )
    return cast(
        EffectiveConfiguration,
        _build(
            context,
            EffectiveConfiguration,
            contract_version,
            interpretation_version,
            max_input_length,
            mode,
            whitespace,
        ),
    )


def _encode_error_cause(value: ErrorCause) -> JsonRecord:
    return {
        "category": value.category.value,
        "operation": _encode_operation_ref(value.operation),
        "record_key": value.record_key,
    }


def _decode_error_cause(record: object, context: str) -> ErrorCause:
    obj = _require_object(record, context)
    _closed_fields(obj, frozenset({"category", "operation", "record_key"}), context)
    category_text = _require_str(obj, "category", context)
    allowed_categories = frozenset(member.value for member in ErrorCategory)
    if category_text not in allowed_categories:
        raise InvalidRepresentationError(
            f"{context}.category has unknown value {category_text!r}"
        )
    category = ErrorCategory(category_text)
    operation = _decode_operation_ref(obj["operation"], f"{context}.operation")
    record_key = _require_str(obj, "record_key", context)
    return cast(
        ErrorCause, _build(context, ErrorCause, category, operation, record_key)
    )


def _encode_error_detail(value: ErrorDetail) -> JsonRecord:
    return {
        "category": value.category.value,
        "recoverability": value.recoverability.value,
        "causes": [_encode_error_cause(cause) for cause in value.causes],
    }


def _decode_error_detail(record: object, context: str) -> ErrorDetail:
    obj = _require_object(record, context)
    _closed_fields(obj, frozenset({"category", "recoverability", "causes"}), context)
    category_text = _require_str(obj, "category", context)
    allowed_categories = frozenset(member.value for member in ErrorCategory)
    if category_text not in allowed_categories:
        raise InvalidRepresentationError(
            f"{context}.category has unknown value {category_text!r}"
        )
    category = ErrorCategory(category_text)
    recoverability_text = _require_str(obj, "recoverability", context)
    allowed_recoverability = frozenset(member.value for member in Recoverability)
    if recoverability_text not in allowed_recoverability:
        raise InvalidRepresentationError(
            f"{context}.recoverability has unknown value {recoverability_text!r}"
        )
    recoverability = Recoverability(recoverability_text)
    causes_raw = obj["causes"]
    if type(causes_raw) is not list:
        raise InvalidRepresentationError(f"{context}.causes must be an array")
    causes = tuple(
        _decode_error_cause(item, f"{context}.causes[{index}]")
        for index, item in enumerate(cast("list[object]", causes_raw))
    )
    return cast(
        ErrorDetail, _build(context, ErrorDetail, category, recoverability, causes)
    )


# --------------------------------------------------------------------------
# Top-level records (LOCAL-PERSISTENCE-REALIZATION.md SS7.2 table rows)
# --------------------------------------------------------------------------


def encode_owner_head(value: OwnerRevision) -> JsonRecord:
    """``application_config_head`` row content: the mutable owner head H."""
    if type(value) is not OwnerRevision:
        raise TypeError("encode_owner_head requires OwnerRevision")
    return {
        "record_kind": _RecordKind.OWNER_HEAD.value,
        "record_schema_version": current_schema_version().value,
        **_encode_owner_revision(value),
    }


def decode_owner_head(record: JsonRecord) -> OwnerRevision:
    context = "owner_head"
    obj = _require_object(record, context)
    _require_kind_and_version(obj, _RecordKind.OWNER_HEAD, context)
    _closed_fields(
        obj,
        frozenset({"record_kind", "record_schema_version", "subject", "head_revision"}),
        context,
    )
    inner = {"subject": obj["subject"], "head_revision": obj["head_revision"]}
    return _decode_owner_revision(inner, context)


def encode_published_revision(value: ConfigurationRevisionRef) -> JsonRecord:
    """The exact immutable R currently published for one configuration owner."""
    if type(value) is not ConfigurationRevisionRef:
        raise TypeError("encode_published_revision requires ConfigurationRevisionRef")
    return {
        "record_kind": _RecordKind.PUBLISHED_REVISION.value,
        "record_schema_version": current_schema_version().value,
        **_encode_configuration_revision_ref(value),
    }


def decode_published_revision(record: JsonRecord) -> ConfigurationRevisionRef:
    context = "published_revision"
    obj = _require_object(record, context)
    _require_kind_and_version(obj, _RecordKind.PUBLISHED_REVISION, context)
    _closed_fields(
        obj,
        frozenset(
            {
                "record_kind",
                "record_schema_version",
                "configuration",
                "configuration_revision_id",
                "contract_version",
            }
        ),
        context,
    )
    inner = {
        "configuration": obj["configuration"],
        "configuration_revision_id": obj["configuration_revision_id"],
        "contract_version": obj["contract_version"],
    }
    return _decode_configuration_revision_ref(inner, context)


def encode_revision_content(value: ComposedConfiguration) -> JsonRecord:
    """``application_config_revision.record_json``: immutable historical content."""
    if type(value) is not ComposedConfiguration:
        raise TypeError("encode_revision_content requires ComposedConfiguration")
    return {
        "record_kind": _RecordKind.REVISION_CONTENT.value,
        "record_schema_version": current_schema_version().value,
        "target": _encode_configuration_ref(value.target),
        "effective": _encode_effective_configuration(value.effective),
        "sources": [_encode_captured_candidate(source) for source in value.sources],
    }


def decode_revision_content(record: JsonRecord) -> ComposedConfiguration:
    context = "revision_content"
    obj = _require_object(record, context)
    _require_kind_and_version(obj, _RecordKind.REVISION_CONTENT, context)
    _closed_fields(
        obj,
        frozenset(
            {"record_kind", "record_schema_version", "target", "effective", "sources"}
        ),
        context,
    )
    target = _decode_configuration_ref(obj["target"], f"{context}.target")
    effective = _decode_effective_configuration(
        obj["effective"], f"{context}.effective"
    )
    sources_raw = obj["sources"]
    if type(sources_raw) is not list:
        raise InvalidRepresentationError(f"{context}.sources must be an array")
    sources = tuple(
        _decode_captured_candidate(item, f"{context}.sources[{index}]")
        for index, item in enumerate(cast("list[object]", sources_raw))
    )
    return cast(
        ComposedConfiguration,
        _build(context, ComposedConfiguration, target, effective, sources),
    )


def encode_publication_operation(
    value: ConfigurationPublicationOperation,
) -> JsonRecord:
    """The retained semantic descriptor beside a publication result (SS8.2)."""
    if type(value) is not ConfigurationPublicationOperation:
        raise TypeError(
            "encode_publication_operation requires ConfigurationPublicationOperation"
        )
    return {
        "record_kind": _RecordKind.PUBLICATION_OPERATION.value,
        "record_schema_version": current_schema_version().value,
        "operation": _encode_operation_ref(value.operation),
        "target": _encode_configuration_ref(value.target),
        "expected_revision": (
            _encode_owner_revision(value.expected_revision)
            if value.expected_revision is not None
            else None
        ),
        "candidate": encode_revision_content(value.candidate),
        "requested_by": _encode_principal(value.requested_by),
    }


def decode_publication_operation(
    record: JsonRecord,
) -> ConfigurationPublicationOperation:
    context = "publication_operation"
    obj = _require_object(record, context)
    _require_kind_and_version(obj, _RecordKind.PUBLICATION_OPERATION, context)
    _closed_fields(
        obj,
        frozenset(
            {
                "record_kind",
                "record_schema_version",
                "operation",
                "target",
                "expected_revision",
                "candidate",
                "requested_by",
            }
        ),
        context,
    )
    operation = _decode_operation_ref(obj["operation"], f"{context}.operation")
    target = _decode_configuration_ref(obj["target"], f"{context}.target")
    expected_raw = obj["expected_revision"]
    expected_revision = (
        _decode_owner_revision(expected_raw, f"{context}.expected_revision")
        if expected_raw is not None
        else None
    )
    candidate = decode_revision_content(
        _require_object(obj["candidate"], f"{context}.candidate")
    )
    requested_by = _decode_principal(obj["requested_by"], f"{context}.requested_by")
    return cast(
        ConfigurationPublicationOperation,
        _build(
            context,
            ConfigurationPublicationOperation,
            operation,
            target,
            expected_revision,
            candidate,
            requested_by,
        ),
    )


def encode_publication_result(value: ConfigurationPublicationResult) -> JsonRecord:
    """``application_config_result``: the retained owner-commit outcome."""
    if type(value) is not ConfigurationPublicationResult:
        raise TypeError(
            "encode_publication_result requires ConfigurationPublicationResult"
        )
    return {
        "record_kind": _RecordKind.PUBLICATION_RESULT.value,
        "record_schema_version": current_schema_version().value,
        "operation": _encode_operation_ref(value.operation),
        "stage": value.stage.value,
        "resulting_revision": (
            _encode_owner_revision(value.resulting_revision)
            if value.resulting_revision is not None
            else None
        ),
        "published": (
            _encode_configuration_revision_ref(value.published)
            if value.published is not None
            else None
        ),
        "effect": value.effect.value,
        "error": _encode_error_detail(value.error) if value.error is not None else None,
        "duties": [duty.value for duty in value.duties],
    }


def decode_publication_result(record: JsonRecord) -> ConfigurationPublicationResult:
    context = "publication_result"
    obj = _require_object(record, context)
    _require_kind_and_version(obj, _RecordKind.PUBLICATION_RESULT, context)
    _closed_fields(
        obj,
        frozenset(
            {
                "record_kind",
                "record_schema_version",
                "operation",
                "stage",
                "resulting_revision",
                "published",
                "effect",
                "error",
                "duties",
            }
        ),
        context,
    )
    operation = _decode_operation_ref(obj["operation"], f"{context}.operation")
    stage_text = _require_str(obj, "stage", context)
    allowed_stages = frozenset(member.value for member in OperationStage)
    if stage_text not in allowed_stages:
        raise InvalidRepresentationError(
            f"{context}.stage has unknown value {stage_text!r}"
        )
    stage = OperationStage(stage_text)
    resulting_raw = obj["resulting_revision"]
    resulting_revision = (
        _decode_owner_revision(resulting_raw, f"{context}.resulting_revision")
        if resulting_raw is not None
        else None
    )
    published_raw = obj["published"]
    published = (
        _decode_configuration_revision_ref(published_raw, f"{context}.published")
        if published_raw is not None
        else None
    )
    effect_text = _require_str(obj, "effect", context)
    allowed_effects = frozenset(member.value for member in EffectExtent)
    if effect_text not in allowed_effects:
        raise InvalidRepresentationError(
            f"{context}.effect has unknown value {effect_text!r}"
        )
    effect = EffectExtent(effect_text)
    error_raw = obj["error"]
    error = (
        _decode_error_detail(error_raw, f"{context}.error")
        if error_raw is not None
        else None
    )
    duties_raw = obj["duties"]
    if type(duties_raw) is not list:
        raise InvalidRepresentationError(f"{context}.duties must be an array")
    duty_ids: list[DutyId] = []
    for index, item in enumerate(cast("list[object]", duties_raw)):
        if type(item) is not str:
            raise InvalidRepresentationError(f"{context}.duties[{index}] must be text")
        duty_ids.append(_build(f"{context}.duties[{index}]", DutyId, item))
    duties = tuple(duty_ids)
    return cast(
        ConfigurationPublicationResult,
        _build(
            context,
            ConfigurationPublicationResult,
            operation,
            stage,
            resulting_revision,
            published,
            effect,
            error,
            duties,
        ),
    )


def encode_source_submission_duty(
    value: ConfigurationSourceSubmissionDuty,
) -> JsonRecord:
    """``application_config_obligation.duty_json``: one outstanding duty."""
    if type(value) is not ConfigurationSourceSubmissionDuty:
        raise TypeError(
            "encode_source_submission_duty requires ConfigurationSourceSubmissionDuty"
        )
    return {
        "record_kind": _RecordKind.SOURCE_SUBMISSION_DUTY.value,
        "record_schema_version": current_schema_version().value,
        "duty_id": value.duty_id.value,
        "kind": value.kind.value,
        "operation": _encode_operation_ref(value.operation),
        "published": _encode_configuration_revision_ref(value.published),
        "responsible_principal": _encode_principal(value.responsible_principal),
        "tenant_context": _encode_tenant_context(value.tenant_context),
        "requirement": _encode_evidence_requirement(value.requirement),
    }


def decode_source_submission_duty(
    record: JsonRecord,
) -> ConfigurationSourceSubmissionDuty:
    context = "source_submission_duty"
    obj = _require_object(record, context)
    _require_kind_and_version(obj, _RecordKind.SOURCE_SUBMISSION_DUTY, context)
    _closed_fields(
        obj,
        frozenset(
            {
                "record_kind",
                "record_schema_version",
                "duty_id",
                "kind",
                "operation",
                "published",
                "responsible_principal",
                "tenant_context",
                "requirement",
            }
        ),
        context,
    )
    duty_id = _build(context, DutyId, _require_str(obj, "duty_id", context))
    kind = _build(context, DutyKind, _require_str(obj, "kind", context))
    operation = _decode_operation_ref(obj["operation"], f"{context}.operation")
    published = _decode_configuration_revision_ref(
        obj["published"], f"{context}.published"
    )
    responsible_principal = _decode_principal(
        obj["responsible_principal"], f"{context}.responsible_principal"
    )
    tenant_context = _decode_tenant_context(
        obj["tenant_context"], f"{context}.tenant_context"
    )
    requirement = _decode_evidence_requirement(
        obj["requirement"], f"{context}.requirement"
    )
    return cast(
        ConfigurationSourceSubmissionDuty,
        _build(
            context,
            ConfigurationSourceSubmissionDuty,
            duty_id,
            kind,
            operation,
            published,
            responsible_principal,
            tenant_context,
            requirement,
        ),
    )
