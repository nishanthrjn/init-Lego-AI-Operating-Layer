"""PARSER-DIAGNOSTICS-1: closed, content-free labels for rejected Agent replies.

Observation only. EvidenceSufficiencyAgent 1.0.0 stays authoritative: this
module never parses a reply into a semantic result, never retries and never
changes a failure. It runs in the child, after the Agent has already returned
INVALID_OUTPUT or PREREQUISITES_UNMET, on the same attempt's final reply held
transiently in memory, and returns only closed enums. Reply text is never
returned, stored, logged or sent to the parent.

The replay follows the Agent parser's order (document, decode, field set,
requests, disposition, explanation, governing sources, assessment) using only
the public value constructors, so each label names a rule the reply actually
violated. With several simultaneous violations the label identifies one real
violation, not necessarily the parser's first. If the replay accepts a reply
the Agent rejected, the label is UNKNOWN_INVALID_OUTPUT with disagreement.
"""

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    EvidenceRequest,
    EvidenceRequestKind,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyError,
    SufficiencyDisposition,
    SufficiencyFailure,
)
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.workspace import RepositoryPath

from legoai.execution.agent.ports import AgentResult
from legoai.execution.agent.values import AgentExecutionStatus

FIELDS = frozenset({"disposition", "explanation", "governing_sources", "requests"})
REQUEST_FIELDS = frozenset({"kind", "description", "path", "choices"})
DIAGNOSED = frozenset(
    {SufficiencyFailure.INVALID_OUTPUT, SufficiencyFailure.PREREQUISITES_UNMET}
)
_WHITESPACE = " \t\r\n"
_FENCE = "```"
_INVALID = (ValueError, TypeError, RecursionError, WorkspaceError)


class RejectionCode(StrEnum):
    CORE_OUTPUT_CONTRACT = "CORE_OUTPUT_CONTRACT"
    NON_JSON_DOCUMENT = "NON_JSON_DOCUMENT"
    MULTIPLE_JSON_DOCUMENTS = "MULTIPLE_JSON_DOCUMENTS"
    JSON_DECODE_INVALID = "JSON_DECODE_INVALID"
    DUPLICATE_JSON_KEY = "DUPLICATE_JSON_KEY"
    FIELD_SET_INVALID = "FIELD_SET_INVALID"
    FIELD_TYPE_INVALID = "FIELD_TYPE_INVALID"
    DISPOSITION_INVALID = "DISPOSITION_INVALID"
    GOVERNING_SOURCES_INVALID = "GOVERNING_SOURCES_INVALID"
    REQUEST_SET_INVALID = "REQUEST_SET_INVALID"
    REQUEST_KIND_INVALID = "REQUEST_KIND_INVALID"
    REQUEST_PATH_INVALID = "REQUEST_PATH_INVALID"
    REQUEST_CHOICES_INVALID = "REQUEST_CHOICES_INVALID"
    VALUE_BOUND_EXCEEDED = "VALUE_BOUND_EXCEEDED"
    DISPOSITION_REQUEST_INCOHERENT = "DISPOSITION_REQUEST_INCOHERENT"
    PREREQUISITES_UNMET = "PREREQUISITES_UNMET"
    UNKNOWN_INVALID_OUTPUT = "UNKNOWN_INVALID_OUTPUT"


class LengthClass(StrEnum):
    """UTF-8 bytes of the final reply. Blank or >32768-byte replies are rejected
    and discarded by the Core output contract, so their length is UNAVAILABLE."""

    SMALL = "SMALL"  # 1-1024
    MEDIUM = "MEDIUM"  # 1025-8192
    LARGE = "LARGE"  # 8193-32768
    UNAVAILABLE = "UNAVAILABLE"


class Branch(StrEnum):
    CORE_OUTPUT_CONTRACT = "CORE_OUTPUT_CONTRACT"
    AGENT_PARSE = "AGENT_PARSE"
    AGENT_PREREQUISITES = "AGENT_PREREQUISITES"


@dataclass(frozen=True, slots=True)
class OutputDiagnosis:
    code: RejectionCode
    length: LengthClass
    branch: Branch
    disagreement: bool

    def __post_init__(self) -> None:
        if (
            type(self.code) is not RejectionCode
            or type(self.length) is not LengthClass
            or type(self.branch) is not Branch
            or type(self.disagreement) is not bool
        ):
            raise TypeError("closed output diagnosis required")

    def record(self) -> dict[str, Any]:
        return {
            "invalid_output_rejection_code": self.code.value,
            "output_length_class": self.length.value,
            "invalid_output_branch": self.branch.value,
            "diagnostic_disagreement": self.disagreement,
        }


class _Duplicate(ValueError):
    pass


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _Duplicate("duplicate key")
        result[key] = value
    return result


def document(reply: str) -> str:
    """ADR-021 outer envelope, mirrored exactly (parity-tested)."""
    trimmed = reply.strip(_WHITESPACE)
    if not trimmed.startswith(_FENCE):
        return reply
    lines = trimmed.split("\n")
    if (
        len(lines) < 3
        or lines[0].removesuffix("\r") not in {_FENCE, _FENCE + "json"}
        or lines[-1] != _FENCE
    ):
        return reply
    return "\n".join(lines[1:-1])


def length_class(reply: str | None) -> LengthClass:
    if reply is None:
        return LengthClass.UNAVAILABLE
    size = len(reply.encode("utf-8", errors="surrogatepass"))
    if size <= 1024:
        return LengthClass.SMALL
    if size <= 8192:
        return LengthClass.MEDIUM
    return LengthClass.LARGE


def _decode_failure(text: str) -> RejectionCode:
    stripped = text.strip(_WHITESPACE)
    decoder = json.JSONDecoder(object_pairs_hook=_unique)
    try:
        _, end = decoder.raw_decode(stripped)
    except _Duplicate:
        return RejectionCode.DUPLICATE_JSON_KEY
    except ValueError, RecursionError:
        if not stripped or stripped[0] not in "{[":
            return RejectionCode.NON_JSON_DOCUMENT
        return RejectionCode.JSON_DECODE_INVALID
    rest = stripped[end:].strip(_WHITESPACE)
    try:
        decoder.raw_decode(rest)
    except ValueError, RecursionError:
        return RejectionCode.NON_JSON_DOCUMENT
    return RejectionCode.MULTIPLE_JSON_DOCUMENTS


def _rejects(build: Any) -> bool:
    try:
        build()
    except _INVALID:
        return True
    return False


def _probe_choice(choice: str) -> bool:
    other = "probe" if choice != "probe" else "probe-2"
    return _rejects(
        lambda: EvidenceRequest(
            EvidenceRequestKind.OPERATOR_CLARIFICATION, "probe", None, (choice, other)
        )
    )


def _request_failure(
    kind: EvidenceRequestKind,
    description: str,
    path: RepositoryPath | None,
    choices: tuple[str, ...],
) -> RejectionCode:
    """EvidenceRequest construction failed; name the violated public rule."""
    if _rejects(
        lambda: EvidenceRequest(EvidenceRequestKind.OPERATOR_CLARIFICATION, description)
    ):
        return RejectionCode.VALUE_BOUND_EXCEEDED
    if len(set(choices)) != len(choices):
        return RejectionCode.REQUEST_CHOICES_INVALID
    if any(_probe_choice(c) for c in choices):
        return RejectionCode.VALUE_BOUND_EXCEEDED
    if kind is EvidenceRequestKind.NAMED_EVIDENCE:
        if path is None:
            return RejectionCode.REQUEST_PATH_INVALID
        if choices:
            return RejectionCode.REQUEST_CHOICES_INVALID
        return RejectionCode.REQUEST_PATH_INVALID
    if path is not None:
        return RejectionCode.REQUEST_PATH_INVALID
    if choices:  # source_role with choices, or a single clarification choice
        return RejectionCode.REQUEST_CHOICES_INVALID
    return RejectionCode.UNKNOWN_INVALID_OUTPUT


def _assessment_failure(
    manifest: EvidenceManifest,
    explanation: str,
    sources: tuple[RepositoryPath, ...],
    requests: tuple[EvidenceRequest, ...],
) -> RejectionCode:
    """Assessment construction failed; name the violated public rule."""
    clarify = EvidenceRequest(EvidenceRequestKind.OPERATOR_CLARIFICATION, "probe")
    role = EvidenceRequest(EvidenceRequestKind.SOURCE_ROLE, "probe")
    if _rejects(
        lambda: EvidenceSufficiencyAssessment(
            manifest,
            SufficiencyDisposition.UNRESOLVED_AMBIGUITY,
            explanation,
            (),
            (clarify,),
        )
    ):
        return RejectionCode.VALUE_BOUND_EXCEEDED
    if _rejects(
        lambda: EvidenceSufficiencyAssessment(
            manifest,
            SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE,
            "probe",
            sources,
            (role,),
        )
    ):
        return RejectionCode.GOVERNING_SOURCES_INVALID
    if len(set(requests)) != len(requests):
        return RejectionCode.REQUEST_SET_INVALID
    return RejectionCode.DISPOSITION_REQUEST_INCOHERENT


def classify_reply(reply: str, manifest: EvidenceManifest) -> RejectionCode | None:
    """Replay of the Agent parse order. None means the replay accepted the reply."""
    text = document(reply)
    try:
        value = json.loads(text, object_pairs_hook=_unique)
    except _Duplicate:
        return RejectionCode.DUPLICATE_JSON_KEY
    except ValueError, RecursionError:
        return _decode_failure(text)
    if type(value) is not dict or set(value) != FIELDS:
        return RejectionCode.FIELD_SET_INVALID
    raw_requests = value["requests"]
    if type(raw_requests) is not list:
        return RejectionCode.FIELD_TYPE_INVALID
    if len(raw_requests) > 8:
        return RejectionCode.REQUEST_SET_INVALID
    requests: list[EvidenceRequest] = []
    for item in raw_requests:
        if type(item) is not dict or set(item) != REQUEST_FIELDS:
            return RejectionCode.REQUEST_SET_INVALID
        kind, description = item["kind"], item["description"]
        raw_path, raw_choices = item["path"], item["choices"]
        if type(kind) is not str:
            return RejectionCode.REQUEST_SET_INVALID
        try:
            request_kind = EvidenceRequestKind(kind)
        except ValueError:
            return RejectionCode.REQUEST_KIND_INVALID
        if type(description) is not str:
            return RejectionCode.REQUEST_SET_INVALID
        path: RepositoryPath | None = None
        if raw_path is not None:
            if type(raw_path) is not str:
                return RejectionCode.REQUEST_PATH_INVALID
            try:
                path = RepositoryPath(raw_path)
            except _INVALID:
                return RejectionCode.REQUEST_PATH_INVALID
        if type(raw_choices) is not list or len(raw_choices) > 8:
            return RejectionCode.REQUEST_CHOICES_INVALID
        if any(type(c) is not str for c in raw_choices):
            return RejectionCode.REQUEST_CHOICES_INVALID
        choices = tuple(str(c) for c in raw_choices)
        try:
            requests.append(EvidenceRequest(request_kind, description, path, choices))
        except _INVALID:
            return _request_failure(request_kind, description, path, choices)
    disposition = value["disposition"]
    if type(disposition) is not str:
        return RejectionCode.FIELD_TYPE_INVALID
    try:
        parsed = SufficiencyDisposition(disposition)
    except ValueError:
        return RejectionCode.DISPOSITION_INVALID
    explanation = value["explanation"]
    if type(explanation) is not str:
        return RejectionCode.FIELD_TYPE_INVALID
    raw_sources = value["governing_sources"]
    if type(raw_sources) is not list:
        return RejectionCode.FIELD_TYPE_INVALID
    if len(raw_sources) > 8 or any(type(p) is not str for p in raw_sources):
        return RejectionCode.GOVERNING_SOURCES_INVALID
    try:
        sources = tuple(RepositoryPath(str(p)) for p in raw_sources)
    except _INVALID:
        return RejectionCode.GOVERNING_SOURCES_INVALID
    try:
        EvidenceSufficiencyAssessment(
            manifest, parsed, explanation, sources, tuple(requests)
        )
    except EvidenceSufficiencyError as error:
        if error.reason is SufficiencyFailure.PREREQUISITES_UNMET:
            return RejectionCode.PREREQUISITES_UNMET
        return RejectionCode.UNKNOWN_INVALID_OUTPUT
    except _INVALID:
        return _assessment_failure(manifest, explanation, sources, tuple(requests))
    return None


def diagnose(
    failure: SufficiencyFailure | None,
    agent: AgentResult | None,
    manifest: EvidenceManifest,
) -> OutputDiagnosis | None:
    """Label an already-returned INVALID_OUTPUT/PREREQUISITES_UNMET; else None."""
    if failure not in DIAGNOSED:
        return None
    if agent is None:
        return OutputDiagnosis(
            RejectionCode.UNKNOWN_INVALID_OUTPUT,
            LengthClass.UNAVAILABLE,
            Branch.AGENT_PARSE,
            True,
        )
    if agent.status is AgentExecutionStatus.OUTPUT_INVALID:
        return OutputDiagnosis(
            RejectionCode.CORE_OUTPUT_CONTRACT,
            LengthClass.UNAVAILABLE,
            Branch.CORE_OUTPUT_CONTRACT,
            failure is not SufficiencyFailure.INVALID_OUTPUT,
        )
    reply = agent.output
    length = length_class(reply)
    try:
        code = classify_reply(reply, manifest) if reply is not None else None
    except Exception:  # the classifier must never change the authoritative result
        code = None
    if failure is SufficiencyFailure.PREREQUISITES_UNMET:
        agrees = code is RejectionCode.PREREQUISITES_UNMET
        return OutputDiagnosis(
            RejectionCode.PREREQUISITES_UNMET
            if agrees
            else RejectionCode.UNKNOWN_INVALID_OUTPUT,
            length,
            Branch.AGENT_PREREQUISITES,
            not agrees,
        )
    if code is None or code is RejectionCode.PREREQUISITES_UNMET:
        return OutputDiagnosis(
            RejectionCode.UNKNOWN_INVALID_OUTPUT, length, Branch.AGENT_PARSE, True
        )
    return OutputDiagnosis(code, length, Branch.AGENT_PARSE, False)
