"""First-failure structural diagnosis of RepositoryAnalyst 1.0.0 replies.

Mirrors `legoai_engineering.analyst.api._parse` and `RepositoryAnalysisResult`
stage by stage, splitting CONTENT-DISCOVERY-1Q's coarse categories:

1. ADR-021 representation, then `json.loads` with duplicate-key rejection;
2. top level must be an object with exactly the six contract fields;
3. `status`;
4. `findings` (array, then each entry);
5. `RepositoryAnalysis(...)` arguments in evaluation order: `summary`,
   `relevant_files`, `risks`, `unknowns`; then its own bounds checks;
6. the insufficient-evidence rule; 7. evidence membership.

Only the first failing stage is the category. Structural observations (field
counts, missing contract field names, unexpected-field *count*, the JSON type of
each required field, a closed status value) never include reply text, values
or unexpected key names. Accept/reject verdicts come from the real public value
constructors; every call is cross-checked against the Analyst's own verdict.
Nothing is repaired, coerced, defaulted or retried.
"""

import json
from dataclasses import dataclass
from enum import StrEnum

from legoai_engineering.analyst.values import (
    RepositoryAnalysis,
    RepositoryAnalysisStatus,
    RepositoryFinding,
)
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.workspace import RepositoryPath

# Canonical order of the closed contract vocabulary (definition prompt order).
CONTRACT = ("status", "summary", "relevant_files", "findings", "risks", "unknowns")
FINDING_FIELDS = frozenset({"text", "paths"})
ANSWERS = frozenset({"succeeded", "insufficient_evidence"})
_WHITESPACE = " \t\r\n"
_FENCE = "```"


class Stage(StrEnum):
    VALID = "valid"
    OUTPUT_CONTRACT_INVALID = "output_contract_invalid"
    RESPONSE_NOT_JSON = "response_not_json"
    DUPLICATE_KEY = "duplicate_key"
    TOP_LEVEL_NOT_OBJECT = "top_level_not_object"
    FIELD_SET_INVALID = "field_set_invalid"
    STATUS_INVALID = "status_invalid"
    FINDINGS_SHAPE_INVALID = "findings_shape_invalid"
    FINDING_ENTRY_INVALID = "finding_entry_invalid"
    SUMMARY_TYPE_INVALID = "summary_type_invalid"
    RELEVANT_FILES_SHAPE_INVALID = "relevant_files_shape_invalid"
    RISKS_SHAPE_INVALID = "risks_shape_invalid"
    UNKNOWNS_SHAPE_INVALID = "unknowns_shape_invalid"
    SUMMARY_BOUNDS_INVALID = "summary_bounds_invalid"
    RELEVANT_FILES_DUPLICATE = "relevant_files_duplicate"
    NARRATIVE_BOUNDS_INVALID = "narrative_bounds_invalid"
    INSUFFICIENT_INCONSISTENT = "insufficient_inconsistent"
    MEMBERSHIP_INVALID = "membership_invalid"
    MODEL_FAILURE = "model_failure"
    CLASSIFIER_DISAGREEMENT = "classifier_disagreement"


# Each fine stage refines exactly one CONTENT-DISCOVERY-1Q category.
COARSE = {
    Stage.VALID: "valid",
    Stage.OUTPUT_CONTRACT_INVALID: "output_contract_invalid",
    Stage.RESPONSE_NOT_JSON: "response_not_json",
    Stage.DUPLICATE_KEY: "schema_invalid",
    Stage.TOP_LEVEL_NOT_OBJECT: "schema_invalid",
    Stage.FIELD_SET_INVALID: "schema_invalid",
    Stage.STATUS_INVALID: "status_invalid",
    Stage.FINDINGS_SHAPE_INVALID: "finding_invalid",
    Stage.FINDING_ENTRY_INVALID: "finding_invalid",
    Stage.SUMMARY_TYPE_INVALID: "schema_invalid",
    Stage.RELEVANT_FILES_SHAPE_INVALID: "relevant_files_invalid",
    Stage.RISKS_SHAPE_INVALID: "schema_invalid",
    Stage.UNKNOWNS_SHAPE_INVALID: "schema_invalid",
    Stage.SUMMARY_BOUNDS_INVALID: "bounds_invalid",
    Stage.RELEVANT_FILES_DUPLICATE: "relevant_files_invalid",
    Stage.NARRATIVE_BOUNDS_INVALID: "bounds_invalid",
    Stage.INSUFFICIENT_INCONSISTENT: "insufficient_inconsistent",
    Stage.MEMBERSHIP_INVALID: "membership_invalid",
    Stage.MODEL_FAILURE: "model_failure",
    Stage.CLASSIFIER_DISAGREEMENT: "classifier_disagreement",
}


@dataclass(frozen=True)
class Diagnosis:
    """Content-free first-failure view of one reply."""

    stage: Stage
    representation: str  # raw | fenced_json | fenced_unlabelled | other | none
    expected_field_count: int | None = None
    actual_field_count: int | None = None
    missing_required_fields: tuple[str, ...] | None = None
    unexpected_field_count: int | None = None
    field_types: dict[str, str] | None = None
    status_value: str | None = None  # closed: answer value, other, non_string

    def as_record(self) -> dict[str, object]:
        return {
            "stage": self.stage.value,
            "representation": self.representation,
            "expected_field_count": self.expected_field_count,
            "actual_field_count": self.actual_field_count,
            "missing_required_fields": None
            if self.missing_required_fields is None
            else list(self.missing_required_fields),
            "unexpected_field_count": self.unexpected_field_count,
            "field_types": self.field_types,
            "status_value": self.status_value,
        }


class _Duplicate(ValueError):
    pass


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _Duplicate
        result[key] = value
    return result


def representation(reply: str) -> tuple[str, str]:
    """ADR-021 decoding, mirrored exactly: (document text, representation)."""
    trimmed = reply.strip(_WHITESPACE)
    if not trimmed.startswith(_FENCE):
        return reply, "raw"
    lines = trimmed.split("\n")
    opening = lines[0].removesuffix("\r")
    if len(lines) >= 3 and lines[-1] == _FENCE and opening in {_FENCE, _FENCE + "json"}:
        kind = "fenced_json" if opening == _FENCE + "json" else "fenced_unlabelled"
        return "\n".join(lines[1:-1]), kind
    return reply, "other"


def json_type(value: object) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if value is None:
        return "null"
    return "number"


def _strings(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) <= 8
        and all(isinstance(item, str) for item in value)
    )


def _paths(value: object) -> tuple[RepositoryPath, ...] | None:
    if not _strings(value):
        return None
    assert isinstance(value, list)
    try:
        return tuple(RepositoryPath(item) for item in value)
    except TypeError, ValueError, WorkspaceError:
        return None


def _oversized(text: str, limit: int) -> bool:
    """The Analyst text bound: nonblank and at most `limit` characters/bytes."""
    if not text or len(text) > limit or text.isspace():
        return True
    try:
        return len(text.encode("utf-8")) > limit
    except UnicodeEncodeError:
        return True


def diagnose(reply: str, supplied: frozenset[str]) -> Diagnosis:
    """The first stage at which the unchanged Analyst rejects `reply`."""
    document, kind = representation(reply)
    try:
        value = json.loads(document, object_pairs_hook=_unique)
    except _Duplicate:
        return Diagnosis(Stage.DUPLICATE_KEY, kind)
    except ValueError, RecursionError:
        return Diagnosis(Stage.RESPONSE_NOT_JSON, kind)
    if not isinstance(value, dict):
        return Diagnosis(Stage.TOP_LEVEL_NOT_OBJECT, kind)
    status_raw = value.get("status")
    if "status" not in value:
        status_value = None
    elif isinstance(status_raw, str):
        status_value = status_raw if status_raw in ANSWERS else "other"
    else:
        status_value = "non_string"
    missing = tuple(f for f in CONTRACT if f not in value)
    unexpected = sum(1 for key in value if key not in CONTRACT)
    types = {f: json_type(value[f]) if f in value else "missing" for f in CONTRACT}

    def at(stage: Stage) -> Diagnosis:
        return Diagnosis(
            stage,
            kind,
            len(CONTRACT),
            len(value),
            missing,
            unexpected,
            types,
            status_value,
        )

    if set(value) != set(CONTRACT):
        return at(Stage.FIELD_SET_INVALID)
    try:
        status = RepositoryAnalysisStatus(status_raw)
    except ValueError:
        return at(Stage.STATUS_INVALID)
    if status.value not in ANSWERS:
        return at(Stage.STATUS_INVALID)
    findings_raw = value["findings"]
    if not isinstance(findings_raw, list) or len(findings_raw) > 8:
        return at(Stage.FINDINGS_SHAPE_INVALID)
    findings = []
    for item in findings_raw:
        if not isinstance(item, dict) or set(item) != FINDING_FIELDS:
            return at(Stage.FINDING_ENTRY_INVALID)
        paths = _paths(item["paths"])
        if not isinstance(item["text"], str) or paths is None:
            return at(Stage.FINDING_ENTRY_INVALID)
        try:
            findings.append(RepositoryFinding(item["text"], paths))
        except TypeError, ValueError:
            return at(Stage.FINDING_ENTRY_INVALID)
    summary = value["summary"]
    if not isinstance(summary, str):
        return at(Stage.SUMMARY_TYPE_INVALID)
    relevant = _paths(value["relevant_files"])
    if relevant is None:
        return at(Stage.RELEVANT_FILES_SHAPE_INVALID)
    if not _strings(value["risks"]):
        return at(Stage.RISKS_SHAPE_INVALID)
    if not _strings(value["unknowns"]):
        return at(Stage.UNKNOWNS_SHAPE_INVALID)
    risks, unknowns = tuple(value["risks"]), tuple(value["unknowns"])
    try:
        analysis = RepositoryAnalysis(
            summary, relevant, tuple(findings), risks, unknowns
        )
    except TypeError, ValueError:
        # Verdict from the real constructor; label in its own check order.
        if _oversized(summary, 2048):
            return at(Stage.SUMMARY_BOUNDS_INVALID)
        folded = [p.value.casefold() for p in relevant]
        if len(set(folded)) != len(folded):
            return at(Stage.RELEVANT_FILES_DUPLICATE)
        return at(Stage.NARRATIVE_BOUNDS_INVALID)
    if status is RepositoryAnalysisStatus.INSUFFICIENT_EVIDENCE and (
        not analysis.unknowns or analysis.findings
    ):
        return at(Stage.INSUFFICIENT_INCONSISTENT)
    cited = (*analysis.relevant_files, *(p for f in analysis.findings for p in f.paths))
    if any(p.value not in supplied for p in cited):
        return at(Stage.MEMBERSHIP_INVALID)
    return at(Stage.VALID)
