"""Content-free classification of Coding and Reviewer replies (LQ1.2).

This measures the EXISTING output contract. It never repairs, strips fences,
normalizes or re-parses leniently: a fenced reply is RESPONSE_NOT_JSON.

The accept/reject verdict always comes from the real public validators
(`AgentOutputContract`, `RepositoryPath`, `FileChangeKind`, `FileChange`,
`RepositoryChangeSet`, `CodingProposal`; `ReviewFinding`, `ReviewDecision`,
`Review`). Only the ORDER of stages mirrors the private CodingAgent and
IndependentReviewer parsers, so a category names the first stage that
rejected the reply. Live classifications are cross-checked against ForgeAI's
own verdict (`diagnostics.py`); any disagreement is reported, never hidden.

A `Diagnosis` holds enums, counts and booleans only. Its fingerprint is a
one-way hash used in memory to confirm agreement and is never reported.
"""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from legoai_engineering.coding.definition import coding_definition
from legoai_engineering.coding.values import CodingProposal
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.mutation import (
    ContentDigest,
    FileChange,
    FileChangeKind,
    RepositoryChangeSet,
    digest_text,
)
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.reviewer.definition import reviewer_definition
from legoai_engineering.reviewer.values import (
    FindingCategory,
    FindingSeverity,
    Review,
    ReviewDecision,
    ReviewFinding,
)

# The exact field sets the runtime parsers require.
CODING_FIELDS = frozenset({"summary", "changes", "risks", "unknowns"})
CHANGE_FIELDS = frozenset({"path", "operation", "content", "reason"})
REVIEW_FIELDS = frozenset({"decision", "summary", "findings", "risks", "unknowns"})
FINDING_FIELDS = frozenset(
    {"category", "severity", "message", "evidence_refs", "required_action"}
)
MAX_ITEMS = 8

Targets = Mapping[str, tuple[FileChangeKind, ContentDigest | None]]


class CodingDiagnostic(StrEnum):
    """First rejecting stage of a Coding reply, in the runtime's stage order."""

    VALID = "valid"
    # AgentOutputContract (agent runtime), before the CodingAgent parser.
    OUTPUT_LIMIT = "output_limit"
    OUTPUT_TEXT_INVALID = "output_text_invalid"
    # CodingAgent parser.
    RESPONSE_NOT_JSON = "response_not_json"
    DUPLICATE_JSON_KEY = "duplicate_json_key"
    TOP_LEVEL_NOT_OBJECT = "top_level_not_object"
    TOP_LEVEL_FIELDS_INVALID = "top_level_fields_invalid"
    CHANGES_NOT_BOUNDED_ARRAY = "changes_not_bounded_array"
    CHANGE_ENTRY_NOT_OBJECT = "change_entry_not_object"
    CHANGE_FIELDS_INVALID = "change_fields_invalid"
    PATH_INVALID = "path_invalid"
    OPERATION_INVALID = "operation_invalid"
    PATH_NOT_REQUESTED_TARGET = "path_not_requested_target"
    OPERATION_TARGET_MISMATCH = "operation_target_mismatch"
    CONTENT_INVALID = "content_invalid"
    REASON_INVALID = "reason_invalid"
    CHANGES_EMPTY = "changes_empty"
    DUPLICATE_CHANGE_TARGET = "duplicate_change_target"
    CHANGESET_INVALID = "changeset_invalid"
    SUMMARY_INVALID = "summary_invalid"
    NARRATIVE_INVALID = "narrative_invalid"
    # CodingProposal constraints.
    CONTENT_LIMIT = "content_limit"
    PROPOSAL_CONSTRAINT_INVALID = "proposal_constraint_invalid"
    # Assigned only when reconciling with ForgeAI evidence (diagnostics.py).
    MODEL_FAILURE = "model_failure"
    OBSERVATION_UNAVAILABLE = "observation_unavailable"
    CLASSIFIER_DISAGREEMENT = "classifier_disagreement"


class ReviewDiagnostic(StrEnum):
    """First rejecting stage of a Reviewer reply, in the runtime's stage order."""

    VALID = "valid"
    OUTPUT_LIMIT = "output_limit"
    OUTPUT_TEXT_INVALID = "output_text_invalid"
    RESPONSE_NOT_JSON = "response_not_json"
    SCHEMA_INVALID = "schema_invalid"
    FINDING_INVALID = "finding_invalid"
    DECISION_INVALID = "decision_invalid"
    DECISION_INCONSISTENT = "decision_inconsistent"
    MODEL_FAILURE = "model_failure"
    OBSERVATION_UNAVAILABLE = "observation_unavailable"
    CLASSIFIER_DISAGREEMENT = "classifier_disagreement"


@dataclass(frozen=True, slots=True)
class OutputFeatures:
    """Structural facts about one reply: no text, keys or values from it."""

    response_bytes: int
    response_characters: int
    output_limit_hit: bool
    markdown_fence: bool
    json_parse_succeeded: bool
    top_level_type: str
    item_count: int | None = None
    missing_fields: int | None = None
    unexpected_fields: int | None = None
    content_bytes_max: int | None = None
    content_bytes_total: int | None = None


@dataclass(frozen=True, slots=True)
class Diagnosis:
    category: str
    features: OutputFeatures
    fingerprint: str | None = field(default=None, repr=False)


class _DuplicateKey(ValueError):
    pass


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey
        result[key] = value
    return result


def _size(text: str) -> int:
    return len(text.encode("utf-8", "surrogatepass"))


def _shape(value: object) -> str:
    if type(value) is dict:
        return "object"
    if type(value) is list:
        return "array"
    if type(value) is str:
        return "string"
    if type(value) is bool:
        return "boolean"
    if value is None:
        return "null"
    return "number"


def _oversized(text: str, maximum: int, *, empty: bool = False) -> bool:
    """The engineering text bound: nonblank unless `empty`, <= maximum."""
    if len(text) > maximum or (not empty and (not text or text.isspace())):
        return True
    try:
        return len(text.encode("utf-8")) > maximum
    except UnicodeEncodeError:
        return True


class _Builder:
    def __init__(self, output: str, max_bytes: int) -> None:
        self.bytes = _size(output)
        self.characters = len(output)
        self.limit = self.characters > max_bytes or self.bytes > max_bytes
        self.fence = output.lstrip().startswith("```")
        self.parsed = False
        self.shape = "none"
        self.items: int | None = None
        self.missing: int | None = None
        self.unexpected: int | None = None
        self.content: list[int] = []

    def fields(self, value: dict[str, object], expected: frozenset[str]) -> bool:
        self.missing = len(expected - set(value))
        self.unexpected = len(set(value) - expected)
        return set(value) == expected

    def done(self, category: StrEnum, fingerprint: str | None = None) -> Diagnosis:
        return Diagnosis(
            category.value,
            OutputFeatures(
                self.bytes,
                self.characters,
                self.limit,
                self.fence,
                self.parsed,
                self.shape,
                self.items,
                self.missing,
                self.unexpected,
                max(self.content) if self.content else None,
                sum(self.content) if self.content else None,
            ),
            fingerprint,
        )


def _digest(*parts: object) -> str:
    canonical = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8", "surrogatepass")).hexdigest()


def proposal_fingerprint(proposal: CodingProposal) -> str:
    """One-way identity of a parsed proposal; compared in memory, never reported."""
    return _digest(
        [
            [
                change.path.value,
                change.kind.value,
                None if change.expected is None else change.expected.value,
                change.text,
            ]
            for change in proposal.changeset.changes
        ],
        proposal.summary,
        list(proposal.reasons),
        list(proposal.risks),
        list(proposal.unknowns),
    )


def review_fingerprint(review: Review) -> str:
    """One-way identity of a parsed review; compared in memory, never reported."""
    return _digest(
        review.decision.value,
        review.summary,
        [
            [
                finding.category.value,
                finding.severity.value,
                finding.message,
                list(finding.evidence_refs),
                finding.required_action,
            ]
            for finding in review.findings
        ],
        list(review.risks),
        list(review.unknowns),
    )


def coding_targets(
    prompt: str,
) -> dict[str, tuple[FileChangeKind, ContentDigest | None]]:
    """The targets a CodingAgent request supplied: path -> (operation, digest).

    `prompt` is the CodingAgent's own request text (ForgeAI-built, trusted).
    Digests are recomputed exactly as CodingEvidence does; text is not kept.
    """
    value = json.loads(prompt)
    targets: dict[str, tuple[FileChangeKind, ContentDigest | None]] = {}
    for target in value["targets"]:
        current = target["current_text"]
        targets[target["path"]] = (
            FileChangeKind(target["operation"]),
            None if current is None else digest_text(current),
        )
    return targets


def classify_coding(output: str, targets: Targets) -> Diagnosis:
    """Classify a Coding reply against the targets of its own request."""
    C = CodingDiagnostic
    contract = coding_definition().output_contract
    built = _Builder(output, contract.max_bytes)
    try:
        contract.validate(output)
    except TypeError, ValueError:
        return built.done(C.OUTPUT_LIMIT if built.limit else C.OUTPUT_TEXT_INVALID)
    try:
        value: object = json.loads(output, object_pairs_hook=_unique)
    except _DuplicateKey:
        return built.done(C.DUPLICATE_JSON_KEY)
    except ValueError, RecursionError:
        return built.done(C.RESPONSE_NOT_JSON)
    built.parsed = True
    built.shape = _shape(value)
    if type(value) is not dict:
        return built.done(C.TOP_LEVEL_NOT_OBJECT)
    if not built.fields(value, CODING_FIELDS):
        return built.done(C.TOP_LEVEL_FIELDS_INVALID)
    raw_changes = value["changes"]
    if type(raw_changes) is list:
        built.items = len(raw_changes)
    if type(raw_changes) is not list or len(raw_changes) > MAX_ITEMS:
        return built.done(C.CHANGES_NOT_BOUNDED_ARRAY)
    changes: list[FileChange] = []
    reasons: list[str] = []
    for raw in raw_changes:
        if type(raw) is not dict:
            return built.done(C.CHANGE_ENTRY_NOT_OBJECT)
        if set(raw) != CHANGE_FIELDS:
            return built.done(C.CHANGE_FIELDS_INVALID)
        if type(raw["path"]) is not str:
            return built.done(C.PATH_INVALID)
        try:
            path = RepositoryPath(raw["path"])
        except TypeError, ValueError, WorkspaceError:
            return built.done(C.PATH_INVALID)
        if type(raw["operation"]) is not str:
            return built.done(C.OPERATION_INVALID)
        try:
            operation = FileChangeKind(raw["operation"])
        except ValueError:
            return built.done(C.OPERATION_INVALID)
        target = targets.get(path.value)
        if target is None:
            return built.done(C.PATH_NOT_REQUESTED_TARGET)
        if operation is not target[0]:
            return built.done(C.OPERATION_TARGET_MISMATCH)
        content = raw["content"]
        if type(content) is not str:
            return built.done(C.CONTENT_INVALID)
        built.content.append(_size(content))
        try:
            changes.append(FileChange(path, operation, target[1], content))
        except TypeError, ValueError, WorkspaceError:
            return built.done(C.CONTENT_INVALID)
        if type(raw["reason"]) is not str:
            return built.done(C.REASON_INVALID)
        reasons.append(raw["reason"])
    try:
        changeset = RepositoryChangeSet(tuple(changes))
    except TypeError, ValueError:
        if not changes:
            return built.done(C.CHANGES_EMPTY)
        folded = [change.path.value.casefold() for change in changes]
        if len(set(folded)) != len(folded):
            return built.done(C.DUPLICATE_CHANGE_TARGET)
        return built.done(C.CHANGESET_INVALID)
    summary = value["summary"]
    if type(summary) is not str:
        return built.done(C.SUMMARY_INVALID)
    narrative: list[tuple[str, ...]] = []
    for key in ("risks", "unknowns"):
        items = value[key]
        if (
            type(items) is not list
            or len(items) > MAX_ITEMS
            or any(type(item) is not str for item in items)
        ):
            return built.done(C.NARRATIVE_INVALID)
        narrative.append(tuple(items))
    try:
        proposal = CodingProposal(
            changeset, summary, tuple(reasons), narrative[0], narrative[1]
        )
    except TypeError, ValueError, WorkspaceError:
        # The verdict is the real constructor's; only the label is derived,
        # in CodingProposal's own check order.
        texts = [change.text or "" for change in changes]
        if any(_oversized(text, 8192, empty=True) for text in texts) or (
            sum(_size(text) for text in texts) > 24576
        ):
            return built.done(C.CONTENT_LIMIT)
        if _oversized(summary, 2048):
            return built.done(C.SUMMARY_INVALID)
        if any(_oversized(reason, 1024) for reason in reasons):
            return built.done(C.REASON_INVALID)
        if any(_oversized(item, 1024) for items in narrative for item in items):
            return built.done(C.NARRATIVE_INVALID)
        return built.done(C.PROPOSAL_CONSTRAINT_INVALID)
    return built.done(C.VALID, proposal_fingerprint(proposal))


def _text(value: object) -> str:
    if type(value) is not str:
        raise TypeError("text required")
    return value


def _items(value: object) -> list[object]:
    if type(value) is not list or len(value) > MAX_ITEMS:
        raise ValueError("bounded array required")
    return value


def classify_review(output: str) -> Diagnosis:
    """Classify a Reviewer reply in the IndependentReviewer's stage order."""
    R = ReviewDiagnostic
    contract = reviewer_definition().output_contract
    built = _Builder(output, contract.max_bytes)
    try:
        contract.validate(output)
    except TypeError, ValueError:
        return built.done(R.OUTPUT_LIMIT if built.limit else R.OUTPUT_TEXT_INVALID)
    try:
        value: object = json.loads(output, object_pairs_hook=_unique)
    except _DuplicateKey:
        return built.done(R.SCHEMA_INVALID)
    except ValueError, RecursionError:
        return built.done(R.RESPONSE_NOT_JSON)
    built.parsed = True
    built.shape = _shape(value)
    if type(value) is not dict or not built.fields(value, REVIEW_FIELDS):
        return built.done(R.SCHEMA_INVALID)
    raw_findings = value["findings"]
    if type(raw_findings) is list:
        built.items = len(raw_findings)
    try:
        findings_list = _items(raw_findings)
    except ValueError:
        return built.done(R.SCHEMA_INVALID)
    findings: list[ReviewFinding] = []
    for item in findings_list:
        if type(item) is not dict or set(item) != FINDING_FIELDS:
            return built.done(R.FINDING_INVALID)
        action = item["required_action"]
        try:
            findings.append(
                ReviewFinding(
                    FindingCategory(_text(item["category"])),
                    FindingSeverity(_text(item["severity"])),
                    _text(item["message"]),
                    tuple(_text(ref) for ref in _items(item["evidence_refs"])),
                    None if action is None else _text(action),
                )
            )
        except TypeError, ValueError:
            return built.done(R.FINDING_INVALID)
    try:
        decision = ReviewDecision(_text(value["decision"]))
    except TypeError, ValueError:
        return built.done(R.DECISION_INVALID)
    try:
        summary = _text(value["summary"])
        risks = tuple(_text(risk) for risk in _items(value["risks"]))
        unknowns = tuple(_text(unknown) for unknown in _items(value["unknowns"]))
    except TypeError, ValueError:
        return built.done(R.SCHEMA_INVALID)
    try:
        review = Review(decision, summary, tuple(findings), risks, unknowns)
    except TypeError, ValueError:
        # Verdict from the real constructor; label in Review's check order.
        if _oversized(summary, 2048) or any(
            _oversized(text, 1024) for text in (*risks, *unknowns)
        ):
            return built.done(R.SCHEMA_INVALID)
        blocking = any(f.severity is FindingSeverity.BLOCKING for f in findings)
        if (decision is ReviewDecision.CHANGES_REQUIRED) != blocking or (
            decision is ReviewDecision.INSUFFICIENT_EVIDENCE and not unknowns
        ):
            return built.done(R.DECISION_INCONSISTENT)
        return built.done(R.SCHEMA_INVALID)
    return built.done(R.VALID, review_fingerprint(review))
