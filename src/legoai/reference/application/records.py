"""Owner-local schema 1 / reader 1 JSON, independent of semantic Versions.

Only three durable families have consumers: revision, committed result and
pending duty. Descriptors/coverage are nested; heads remain relational and query
cursors are not durable state. Bytes are reproducible, never operation identity.
All failures are payload-free values; no repair, lookup, recomposition or I/O.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import NoReturn, cast

from legoai.application.ports import (
    AcknowledgmentStage,
    ConfigurationHead,
    Coverage,
    CoverageExtent,
    DutyAction,
    DutyRef,
    ExpectedAbsence,
    NoSourceDuty,
    ObligationRevision,
    ObligationStatus,
    PendingSourceDuty,
    PublicationDescriptor,
    PublicationResult,
    PublishConfiguration,
    PublishedConfiguration,
    SourceDutyPlan,
)
from legoai.application.values import (
    CapturedCandidate,
    ComposedConfiguration,
    EffectiveConfiguration,
    NormalizationMode,
    NormalizationPatch,
    SourceLayer,
    SourceProvenance,
)
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
    ConfigurationRevisionRef,
    OperationRef,
    OwnerRevision,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version


class RecordKind(Enum):
    PUBLISHED_CONFIGURATION = "published_configuration"
    PUBLICATION_RESULT = "publication_result"
    PENDING_SOURCE_DUTY = "pending_source_duty"


class RecordProblem(Enum):
    MALFORMED = "malformed owner record"
    UNSUPPORTED = "unsupported owner record interpretation"
    LIMIT = "owner record qualification bound exceeded"


@dataclass(frozen=True, slots=True)
class RecordFailure:
    problem: RecordProblem

    def __post_init__(self) -> None:
        if type(self.problem) is not RecordProblem:
            raise TypeError("record failure requires RecordProblem")

    @property
    def error(self) -> ErrorDetail:
        category = (
            ErrorCategory.VERSION_MISMATCH
            if self.problem is RecordProblem.UNSUPPORTED
            else ErrorCategory.VALIDATION_ERROR
        )
        return ErrorDetail(category, Recoverability.REQUIRES_INTERVENTION, ())


type OwnerRecord = PublishedConfiguration | PublicationResult | PendingSourceDuty


class _Invalid(ValueError):
    def __init__(self, problem: RecordProblem = RecordProblem.MALFORMED) -> None:
        super().__init__(problem.value)
        self.problem = problem


def _object(value: object, fields: str) -> dict[str, object]:
    if type(value) is not dict:
        raise _Invalid()
    result = cast(dict[str, object], value)
    if set(result) != set(fields.split()):
        raise _Invalid()
    return result


def _text(value: object) -> str:
    if type(value) is not str:
        raise _Invalid()
    value.encode("utf-8", errors="strict")  # also rejects escaped lone surrogates
    return value


def _integer(value: object, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= 2**63 - 1:
        raise _Invalid()
    return value


def _sequence(value: object, maximum: int) -> list[object]:
    if type(value) is not list:
        raise _Invalid()
    if len(value) > maximum:
        raise _Invalid(RecordProblem.LIMIT)
    return cast(list[object], value)


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _Invalid()
        _text(key)
        result[key] = value
    return result


def _reject_number(value: str) -> NoReturn:
    raise _Invalid()


def _parse_integer(value: str) -> int:
    if len(value.lstrip("-")) > 19:
        raise _Invalid(RecordProblem.LIMIT)
    number = int(value)
    if not -(2**63) <= number <= 2**63 - 1:
        raise _Invalid(RecordProblem.LIMIT)
    return number


def _preflight(text: str) -> None:
    """Bound depth/tokens before json.loads; string/escape aware, not a parser.

    json.loads still owns grammar validation. Counts value/string starts and
    punctuation; limit 8192 and depth 32 are local qualification protections.
    """
    depth = tokens = 0
    quoted = escaped = atom = False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
            continue
        if character == '"':
            quoted = True
            atom = False
            tokens += 1
        elif character in "{}[]:,":
            atom = False
            tokens += 1
            if character in "{[":
                depth += 1
                if depth > 32:
                    raise _Invalid(RecordProblem.LIMIT)
            elif character in "}]":
                depth -= 1
        elif character in " \t\r\n":
            atom = False
        elif not atom:
            atom = True
            tokens += 1
        if tokens > 8192:
            raise _Invalid(RecordProblem.LIMIT)


def _parse(data: bytes) -> object:
    if type(data) is not bytes:
        raise _Invalid()
    if len(data) > 65536:
        raise _Invalid(RecordProblem.LIMIT)
    text = data.decode("utf-8", errors="strict")
    _preflight(text)
    # This hook only rejects duplicate data keys; no object/class construction.
    value: object = json.loads(
        text,
        object_pairs_hook=_pairs,
        parse_constant=_reject_number,
        parse_float=_reject_number,
        parse_int=_parse_integer,
    )
    return value


def _version(value: Version) -> dict[str, object]:
    return {"major": value.major, "minor": value.minor, "patch": value.patch}


def _read_version(value: object, *, fixture: bool = False) -> Version:
    obj = _object(value, "major minor patch")
    result = Version(
        _integer(obj["major"]), _integer(obj["minor"]), _integer(obj["patch"])
    )
    if fixture and result != Version(0, 1, 0):
        raise _Invalid(RecordProblem.UNSUPPORTED)
    return result


def _scope(value: ReferenceScope) -> dict[str, object]:
    return {"owner": value.owner, "tenant_id": value.tenant_id.value}


def _read_scope(value: object) -> ReferenceScope:
    obj = _object(value, "owner tenant_id")
    return ReferenceScope(_text(obj["owner"]), TenantId(_text(obj["tenant_id"])))


def _application(value: ApplicationRef) -> dict[str, object]:
    return {"scope": _scope(value.scope), "application_id": value.application_id.value}


def _read_application(value: object) -> ApplicationRef:
    obj = _object(value, "scope application_id")
    return ApplicationRef(
        _read_scope(obj["scope"]), ApplicationId(_text(obj["application_id"]))
    )


def _subject(value: ConfigurationRef) -> dict[str, object]:
    return {"application": _application(value.application), "instance": value.instance}


def _read_subject(value: object) -> ConfigurationRef:
    obj = _object(value, "application instance")
    return ConfigurationRef(
        _read_application(obj["application"]), _text(obj["instance"])
    )


def _revision(value: ConfigurationRevisionRef) -> dict[str, object]:
    return {
        "configuration": _subject(value.configuration),
        "revision": value.revision,
        "contract_version": _version(value.contract_version),
    }


def _read_revision(value: object) -> ConfigurationRevisionRef:
    obj = _object(value, "configuration revision contract_version")
    return ConfigurationRevisionRef(
        _read_subject(obj["configuration"]),
        _text(obj["revision"]),
        _read_version(obj["contract_version"], fixture=True),
    )


def _owner_revision(value: OwnerRevision) -> dict[str, object]:
    return {"subject": _subject(value.subject), "value": value.value}


def _read_owner_revision(value: object) -> OwnerRevision:
    obj = _object(value, "subject value")
    return OwnerRevision(_read_subject(obj["subject"]), _integer(obj["value"], 1))


def _principal(value: PrincipalRef) -> dict[str, object]:
    return {"issuer": value.issuer, "principal_id": value.principal_id.value}


def _read_principal(value: object) -> PrincipalRef:
    obj = _object(value, "issuer principal_id")
    return PrincipalRef(_text(obj["issuer"]), PrincipalId(_text(obj["principal_id"])))


def _operation(value: OperationRef) -> dict[str, object]:
    is_config = isinstance(value.subject, ConfigurationRef)
    return {
        "subject_kind": "configuration" if is_config else "application",
        "subject": _subject(value.subject)
        if isinstance(value.subject, ConfigurationRef)
        else _application(value.subject),
        "operation_id": value.operation_id.value,
        "contract_identity": value.contract_identity,
    }


def _read_operation(value: object) -> OperationRef:
    obj = _object(value, "subject_kind subject operation_id contract_identity")
    kind = _text(obj["subject_kind"])
    if kind == "configuration":
        subject: ConfigurationRef | ApplicationRef = _read_subject(obj["subject"])
    elif kind == "application":
        subject = _read_application(obj["subject"])
    else:
        raise _Invalid()
    return OperationRef(
        subject,
        OperationId(_text(obj["operation_id"])),
        _text(obj["contract_identity"]),
    )


def _context(value: OperationContext) -> dict[str, object]:
    return {
        "operation": _operation(value.operation),
        "request_id": value.request_id.value,
        "correlation_id": value.correlation_id.value,
        "trace_id": None if value.trace_id is None else value.trace_id.value,
        "tenant_id": value.tenant_context.tenant_id.value,
        "acting_principal": _principal(value.acting_principal.reference),
        "originating_requester": _principal(value.originating_requester.reference),
        "causation": None if value.causation is None else _operation(value.causation),
    }


def _read_context(value: object) -> OperationContext:
    obj = _object(
        value,
        "operation request_id correlation_id trace_id tenant_id acting_principal originating_requester causation",
    )
    return OperationContext(
        _read_operation(obj["operation"]),
        RequestId(_text(obj["request_id"])),
        CorrelationId(_text(obj["correlation_id"])),
        None if obj["trace_id"] is None else TraceId(_text(obj["trace_id"])),
        TenantContext(TenantId(_text(obj["tenant_id"]))),
        Principal(_read_principal(obj["acting_principal"])),
        Principal(_read_principal(obj["originating_requester"])),
        None if obj["causation"] is None else _read_operation(obj["causation"]),
    )


def _provenance(value: SourceProvenance) -> dict[str, object]:
    return {
        "owner": value.owner,
        "source_id": value.source_id,
        "source_revision": value.source_revision,
        "contract_version": _version(value.contract_version),
        "interpretation_version": _version(value.interpretation_version),
    }


def _read_provenance(value: object) -> SourceProvenance:
    obj = _object(
        value, "owner source_id source_revision contract_version interpretation_version"
    )
    return SourceProvenance(
        _text(obj["owner"]),
        _text(obj["source_id"]),
        _text(obj["source_revision"]),
        _read_version(obj["contract_version"], fixture=True),
        _read_version(obj["interpretation_version"], fixture=True),
    )


def _patch(value: NormalizationPatch) -> dict[str, object]:
    # Required null fields encode captured absence, never a decoder default.
    return {
        "max_input_length": value.max_input_length,
        "normalization_mode": None
        if value.normalization_mode is None
        else value.normalization_mode.value,
        "allowed_whitespace": None
        if value.allowed_whitespace is None
        else list(value.allowed_whitespace),
    }


def _read_whitespace(value: object) -> tuple[str, ...]:
    return tuple(_text(item) for item in _sequence(value, 6))


def _read_patch(value: object) -> NormalizationPatch:
    obj = _object(value, "max_input_length normalization_mode allowed_whitespace")
    return NormalizationPatch(
        None
        if obj["max_input_length"] is None
        else _integer(obj["max_input_length"], 1),
        None
        if obj["normalization_mode"] is None
        else NormalizationMode(_text(obj["normalization_mode"])),
        None
        if obj["allowed_whitespace"] is None
        else _read_whitespace(obj["allowed_whitespace"]),
    )


def _candidate(value: CapturedCandidate) -> dict[str, object]:
    return {
        "target": _subject(value.target),
        "provenance": _provenance(value.provenance),
        "layer": value.layer.value,
        "values": _patch(value.values),
    }


def _read_candidate(value: object) -> CapturedCandidate:
    obj = _object(value, "target provenance layer values")
    return CapturedCandidate(
        _read_subject(obj["target"]),
        _read_provenance(obj["provenance"]),
        SourceLayer(_text(obj["layer"])),
        _read_patch(obj["values"]),
    )


def _effective(value: EffectiveConfiguration) -> dict[str, object]:
    return {
        "contract_version": _version(value.contract_version),
        "interpretation_version": _version(value.interpretation_version),
        "max_input_length": value.max_input_length,
        "normalization_mode": value.normalization_mode.value,
        "allowed_whitespace": list(value.allowed_whitespace),
    }


def _read_effective(value: object) -> EffectiveConfiguration:
    obj = _object(
        value,
        "contract_version interpretation_version max_input_length normalization_mode allowed_whitespace",
    )
    return EffectiveConfiguration(
        _read_version(obj["contract_version"], fixture=True),
        _read_version(obj["interpretation_version"], fixture=True),
        _integer(obj["max_input_length"], 1),
        NormalizationMode(_text(obj["normalization_mode"])),
        _read_whitespace(obj["allowed_whitespace"]),
    )


def _composed(value: ComposedConfiguration) -> dict[str, object]:
    return {
        "target": _subject(value.target),
        "effective": _effective(value.effective),
        "sources": [_candidate(item) for item in value.sources],
    }


def _read_composed(value: object) -> ComposedConfiguration:
    obj = _object(value, "target effective sources")
    return ComposedConfiguration(
        _read_subject(obj["target"]),
        _read_effective(obj["effective"]),
        tuple(_read_candidate(item) for item in _sequence(obj["sources"], 3)),
    )


def _requirement(value: SourceRequirement) -> dict[str, object]:
    return {
        "requirement": {
            "scope": _scope(value.requirement.scope),
            "identity": value.requirement.identity,
            "version": _version(value.requirement.version),
        },
        "guarantee": {
            "scope": _scope(value.guarantee.scope),
            "identity": value.guarantee.identity,
            "version": _version(value.guarantee.version),
        },
        "due_at": value.due_at.isoformat(timespec="microseconds"),
        "retain_until": value.retain_until.isoformat(timespec="microseconds"),
    }


def _read_time(value: object) -> datetime:
    text = _text(value)
    # Closed fixed-width UTC grammar: YYYY-MM-DDTHH:MM:SS.ffffff+00:00.
    if (
        len(text) != 32
        or text[10] != "T"
        or text[19] != "."
        or not text.endswith("+00:00")
    ):
        raise _Invalid()
    result = datetime.fromisoformat(text)
    if result.isoformat(timespec="microseconds") != text:
        raise _Invalid()
    return result


def _read_requirement(value: object) -> SourceRequirement:
    obj = _object(value, "requirement guarantee due_at retain_until")
    requirement = _object(obj["requirement"], "scope identity version")
    guarantee = _object(obj["guarantee"], "scope identity version")
    return SourceRequirement(
        RequirementRef(
            _read_scope(requirement["scope"]),
            _text(requirement["identity"]),
            _read_version(requirement["version"]),
        ),
        GuaranteeRef(
            _read_scope(guarantee["scope"]),
            _text(guarantee["identity"]),
            _read_version(guarantee["version"]),
        ),
        _read_time(obj["due_at"]),
        _read_time(obj["retain_until"]),
    )


def _plan(value: NoSourceDuty | SourceDutyPlan) -> dict[str, object]:
    if value is NoSourceDuty.NOT_APPLICABLE:
        return {"applicability": "not_applicable"}
    return {
        "applicability": "required",
        "responsible": _principal(value.responsible),
        "reconciliation_authority": _principal(value.reconciliation_authority),
        "requirements": [_requirement(item) for item in value.requirements],
    }


def _read_plan(value: object) -> NoSourceDuty | SourceDutyPlan:
    if type(value) is not dict:
        raise _Invalid()
    obj = cast(dict[str, object], value)
    if obj.get("applicability") == "not_applicable":
        _object(obj, "applicability")
        return NoSourceDuty.NOT_APPLICABLE
    obj = _object(
        obj, "applicability responsible reconciliation_authority requirements"
    )
    if obj["applicability"] != "required":
        raise _Invalid()
    return SourceDutyPlan(
        _read_principal(obj["responsible"]),
        _read_principal(obj["reconciliation_authority"]),
        tuple(_read_requirement(item) for item in _sequence(obj["requirements"], 8)),
    )


def _descriptor(value: PublicationDescriptor) -> dict[str, object]:
    expected = (
        {"kind": "absence"}
        if value.expected is ExpectedAbsence.ABSENT
        else {"kind": "head", "revision": _owner_revision(value.expected)}
    )
    return {
        "candidate": _composed(value.candidate),
        "requester": _principal(value.requester),
        "expected": expected,
        "source_duty": _plan(value.source_duty),
        "contract_version": _version(value.contract_version),
        "equivalence_version": _version(value.equivalence_version),
    }


def _read_descriptor(value: object) -> PublicationDescriptor:
    obj = _object(
        value,
        "candidate requester expected source_duty contract_version equivalence_version",
    )
    raw = obj["expected"]
    if type(raw) is not dict:
        raise _Invalid()
    expected = cast(dict[str, object], raw)
    guard: ExpectedAbsence | OwnerRevision
    if expected.get("kind") == "absence":
        _object(expected, "kind")
        guard = ExpectedAbsence.ABSENT
    else:
        _object(expected, "kind revision")
        if expected["kind"] != "head":
            raise _Invalid()
        guard = _read_owner_revision(expected["revision"])
    return PublicationDescriptor(
        _read_composed(obj["candidate"]),
        _read_principal(obj["requester"]),
        guard,
        _read_plan(obj["source_duty"]),
        _read_version(obj["contract_version"], fixture=True),
        _read_version(obj["equivalence_version"], fixture=True),
    )


def _command(value: PublishConfiguration) -> dict[str, object]:
    return {
        "descriptor": _descriptor(value.descriptor),
        "context": _context(value.context),
        "observed_at": value.observed_at.isoformat(timespec="microseconds"),
        "uncertainty_microseconds": value.uncertainty_microseconds,
    }


def _read_command(value: object) -> PublishConfiguration:
    obj = _object(value, "descriptor context observed_at uncertainty_microseconds")
    return PublishConfiguration(
        _read_descriptor(obj["descriptor"]),
        _read_context(obj["context"]),
        _read_time(obj["observed_at"]),
        _integer(obj["uncertainty_microseconds"]),
    )


def _duty_ref(value: DutyRef) -> dict[str, object]:
    return {
        "subject": _subject(value.subject),
        "obligation_id": value.obligation_id.value,
    }


def _read_duty_ref(value: object) -> DutyRef:
    obj = _object(value, "subject obligation_id")
    return DutyRef(
        _read_subject(obj["subject"]), ObligationId(_text(obj["obligation_id"]))
    )


def _published(value: PublishedConfiguration) -> dict[str, object]:
    return {
        "head": {
            "revision": _owner_revision(value.head.revision),
            "selected": _revision(value.head.selected),
        },
        "original": _command(value.original),
        "predecessor": None
        if value.predecessor is None
        else _revision(value.predecessor),
        "duty": None if value.duty is None else _duty_ref(value.duty),
    }


def _read_published(value: object) -> PublishedConfiguration:
    obj = _object(value, "head original predecessor duty")
    head = _object(obj["head"], "revision selected")
    return PublishedConfiguration(
        ConfigurationHead(
            _read_owner_revision(head["revision"]), _read_revision(head["selected"])
        ),
        _read_command(obj["original"]),
        None if obj["predecessor"] is None else _read_revision(obj["predecessor"]),
        None if obj["duty"] is None else _read_duty_ref(obj["duty"]),
    )


def _coverage(value: Coverage) -> dict[str, object]:
    return {
        "store_id": value.store_id,
        "subject": _subject(value.subject),
        "extent": value.extent.value,
    }


def _read_coverage(value: object) -> Coverage:
    obj = _object(value, "store_id subject extent")
    return Coverage(
        _text(obj["store_id"]),
        _read_subject(obj["subject"]),
        CoverageExtent(_text(obj["extent"])),
    )


def _result(value: PublicationResult) -> dict[str, object]:
    return {
        "record": _published(value.record),
        "coverage": _coverage(value.coverage),
        "stage": value.stage.value,
        "effect": value.effect.value,
    }


def _read_result(value: object) -> PublicationResult:
    obj = _object(value, "record coverage stage effect")
    stage = AcknowledgmentStage(_text(obj["stage"]))
    extent = EffectExtent(_text(obj["effect"]))
    if (
        stage is not AcknowledgmentStage.OWNER_COMMIT
        or extent is not EffectExtent.COMPLETED
    ):
        raise _Invalid()
    return PublicationResult(
        _read_published(obj["record"]), _read_coverage(obj["coverage"])
    )


def _duty(value: PendingSourceDuty) -> dict[str, object]:
    return {
        "revision": {
            "reference": _duty_ref(value.revision.reference),
            "value": value.revision.value,
        },
        "source": _published(value.source),
        "status": value.status.value,
        "next_safe_action": value.next_safe_action.value,
    }


def _read_duty(value: object) -> PendingSourceDuty:
    obj = _object(value, "revision source status next_safe_action")
    status = ObligationStatus(_text(obj["status"]))
    if status is not ObligationStatus.PENDING:
        # Recognized vocabulary, but F4 has no repaired-duty semantic value yet.
        raise _Invalid(RecordProblem.UNSUPPORTED)
    DutyAction(_text(obj["next_safe_action"]))  # closed vocabulary has one F4 action
    revision = _object(obj["revision"], "reference value")
    return PendingSourceDuty(
        ObligationRevision(
            _read_duty_ref(revision["reference"]), _integer(revision["value"], 1)
        ),
        _read_published(obj["source"]),
    )


def record_subject(value: OwnerRecord) -> ConfigurationRef:
    """Exact semantic key for the later store's independent key cross-check."""
    if type(value) is PublishedConfiguration:
        return value.head.revision.subject
    if type(value) is PublicationResult:
        return value.record.head.revision.subject
    if type(value) is PendingSourceDuty:
        return value.revision.reference.subject
    raise TypeError("expected configuration owner record")


def _decode(data: bytes, expected: RecordKind) -> OwnerRecord | RecordFailure:
    try:
        obj = _object(
            _parse(data),
            "record_kind record_schema_version reader_contract_version subject payload",
        )
        kind = RecordKind(_text(obj["record_kind"]))
        if kind is not expected:
            raise _Invalid()
        if (
            _integer(obj["record_schema_version"], 1) != 1
            or _integer(obj["reader_contract_version"], 1) != 1
        ):
            raise _Invalid(RecordProblem.UNSUPPORTED)
        subject = _read_subject(obj["subject"])
        value: OwnerRecord
        if kind is RecordKind.PUBLISHED_CONFIGURATION:
            value = _read_published(obj["payload"])
        elif kind is RecordKind.PUBLICATION_RESULT:
            value = _read_result(obj["payload"])
        else:
            value = _read_duty(obj["payload"])
        if record_subject(value) != subject:
            raise _Invalid()
        return value
    except _Invalid as error:
        return RecordFailure(error.problem)
    except ValueError, TypeError, RecursionError, OverflowError:
        # Includes UTF-8, JSON and nominal constructor failures. Never retain the
        # exception, traceback, path or submitted value in the returned result.
        return RecordFailure(RecordProblem.MALFORMED)


def _encode(value: OwnerRecord, kind: RecordKind) -> bytes | RecordFailure:
    try:
        if (
            type(value) is PublishedConfiguration
            and kind is RecordKind.PUBLISHED_CONFIGURATION
        ):
            payload = _published(value)
        elif type(value) is PublicationResult and kind is RecordKind.PUBLICATION_RESULT:
            payload = _result(value)
        elif (
            type(value) is PendingSourceDuty and kind is RecordKind.PENDING_SOURCE_DUTY
        ):
            payload = _duty(value)
        else:
            raise _Invalid()
        envelope = {
            "record_kind": kind.value,
            "record_schema_version": 1,
            "reader_contract_version": 1,
            "subject": _subject(record_subject(value)),
            "payload": payload,
        }
        data = json.dumps(
            envelope,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        ).encode("utf-8", errors="strict")
        # Same bounds and supported interpretations apply on write and read.
        checked = _decode(data, kind)
        return checked if isinstance(checked, RecordFailure) else data
    except _Invalid as error:
        return RecordFailure(error.problem)
    except ValueError, TypeError, RecursionError, OverflowError:
        return RecordFailure(RecordProblem.MALFORMED)


def encode_published_configuration(
    value: PublishedConfiguration,
) -> bytes | RecordFailure:
    return _encode(value, RecordKind.PUBLISHED_CONFIGURATION)


def decode_published_configuration(
    data: bytes,
) -> PublishedConfiguration | RecordFailure:
    return cast(
        PublishedConfiguration | RecordFailure,
        _decode(data, RecordKind.PUBLISHED_CONFIGURATION),
    )


def encode_publication_result(value: PublicationResult) -> bytes | RecordFailure:
    return _encode(value, RecordKind.PUBLICATION_RESULT)


def decode_publication_result(data: bytes) -> PublicationResult | RecordFailure:
    return cast(
        PublicationResult | RecordFailure, _decode(data, RecordKind.PUBLICATION_RESULT)
    )


def encode_pending_source_duty(value: PendingSourceDuty) -> bytes | RecordFailure:
    return _encode(value, RecordKind.PENDING_SOURCE_DUTY)


def decode_pending_source_duty(data: bytes) -> PendingSourceDuty | RecordFailure:
    return cast(
        PendingSourceDuty | RecordFailure, _decode(data, RecordKind.PENDING_SOURCE_DUTY)
    )
