"""Content-free structural classification of RepositoryAnalyst replies.

Mirrors the stage order of the unchanged Analyst: ADR-021 representation,
duplicate-key JSON, exact fields, status, findings, analysis values, the
insufficient-evidence rule and finally evidence membership. Accept/reject
verdicts come from the real public value constructors; the harness also
cross-checks every classification against the Analyst's own result, so a
mismatch is reported as `classifier_disagreement`, never hidden. Nothing is
repaired, retried or re-parsed leniently, and no reply text is retained.
"""

import json
from enum import StrEnum

from legoai_engineering.analyst.values import (
    RepositoryAnalysis,
    RepositoryAnalysisStatus,
    RepositoryFinding,
)
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.workspace import RepositoryPath

FIELDS = frozenset(
    {"status", "summary", "relevant_files", "findings", "risks", "unknowns"}
)
FINDING_FIELDS = frozenset({"text", "paths"})
ANSWERS = {
    RepositoryAnalysisStatus.SUCCEEDED,
    RepositoryAnalysisStatus.INSUFFICIENT_EVIDENCE,
}
_WHITESPACE = " \t\r\n"
_FENCE = "```"


class Category(StrEnum):
    VALID = "valid"
    OUTPUT_CONTRACT_INVALID = "output_contract_invalid"
    RESPONSE_NOT_JSON = "response_not_json"
    SCHEMA_INVALID = "schema_invalid"
    STATUS_INVALID = "status_invalid"
    FINDING_INVALID = "finding_invalid"
    RELEVANT_FILES_INVALID = "relevant_files_invalid"
    BOUNDS_INVALID = "bounds_invalid"
    INSUFFICIENT_INCONSISTENT = "insufficient_inconsistent"
    MEMBERSHIP_INVALID = "membership_invalid"
    MODEL_FAILURE = "model_failure"
    CLASSIFIER_DISAGREEMENT = "classifier_disagreement"


class _Duplicate(ValueError):
    pass


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _Duplicate
        result[key] = value
    return result


def _document(reply: str) -> str:
    """ADR-021 representation, mirrored exactly (see _json_document)."""
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


def _items(value: object) -> list[object] | None:
    return value if isinstance(value, list) and len(value) <= 8 else None


def _texts(value: object) -> tuple[str, ...] | None:
    items = _items(value)
    if items is None or not all(isinstance(i, str) for i in items):
        return None
    return tuple(str(i) for i in items)


def _paths(value: object) -> tuple[RepositoryPath, ...] | None:
    texts = _texts(value)
    if texts is None:
        return None
    try:
        return tuple(RepositoryPath(t) for t in texts)
    except TypeError, ValueError, WorkspaceError:
        return None


Classified = tuple[Category, str | None, tuple[str, ...] | None]


def classify(reply: str, supplied: frozenset[str]) -> Classified:
    """(category, answered status, structured relevant_files) for one reply."""
    try:
        value = json.loads(_document(reply), object_pairs_hook=_unique)
    except _Duplicate:
        return Category.SCHEMA_INVALID, None, None
    except ValueError, RecursionError:
        return Category.RESPONSE_NOT_JSON, None, None
    if not isinstance(value, dict) or set(value) != FIELDS:
        return Category.SCHEMA_INVALID, None, None
    if not isinstance(value["status"], str):
        return Category.STATUS_INVALID, None, None
    try:
        status = RepositoryAnalysisStatus(value["status"])
    except ValueError:
        return Category.STATUS_INVALID, None, None
    if status not in ANSWERS:
        return Category.STATUS_INVALID, None, None
    findings_raw = _items(value["findings"])
    if findings_raw is None:
        return Category.FINDING_INVALID, None, None
    findings = []
    for raw in findings_raw:
        if not isinstance(raw, dict) or set(raw) != FINDING_FIELDS:
            return Category.FINDING_INVALID, None, None
        paths = _paths(raw["paths"])
        if not isinstance(raw["text"], str) or paths is None:
            return Category.FINDING_INVALID, None, None
        try:
            findings.append(RepositoryFinding(raw["text"], paths))
        except TypeError, ValueError:
            return Category.FINDING_INVALID, None, None
    if not isinstance(value["summary"], str):
        return Category.SCHEMA_INVALID, None, None
    relevant = _paths(value["relevant_files"])
    if relevant is None:
        return Category.RELEVANT_FILES_INVALID, None, None
    risks, unknowns = _texts(value["risks"]), _texts(value["unknowns"])
    if risks is None or unknowns is None:
        return Category.SCHEMA_INVALID, None, None
    try:
        analysis = RepositoryAnalysis(
            value["summary"], relevant, tuple(findings), risks, unknowns
        )
    except TypeError, ValueError:
        # Verdict from the real constructor; label in its own check order.
        folded = [p.value.casefold() for p in relevant]
        if len(set(folded)) != len(folded):
            return Category.RELEVANT_FILES_INVALID, None, None
        return Category.BOUNDS_INVALID, None, None
    if status is RepositoryAnalysisStatus.INSUFFICIENT_EVIDENCE and (
        not analysis.unknowns or analysis.findings
    ):
        return Category.INSUFFICIENT_INCONSISTENT, None, None
    cited = (*analysis.relevant_files, *(p for f in analysis.findings for p in f.paths))
    if any(p.value not in supplied for p in cited):
        return Category.MEMBERSHIP_INVALID, None, None
    return (
        Category.VALID,
        status.value,
        tuple(sorted(p.value for p in analysis.relevant_files)),
    )
