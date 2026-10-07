"""Advisory sufficiency contracts; no model, acquisition, authority or progression.

Manifest declarations and source-role bindings are supplied judgments. Checking
their presence cannot prove semantic completeness or the truth of an answer.
"""

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum

from legoai_engineering.analyst.values import RepositoryEvidence, _paths, _text
from legoai_engineering.repository.workspace import RepositoryPath

__all__ = [
    "EvidenceClarification",
    "EvidenceManifest",
    "EvidenceRequest",
    "EvidenceRequestKind",
    "EvidenceSufficiencyAssessment",
    "EvidenceSufficiencyError",
    "EvidenceSufficiencyResult",
    "GoverningSourceExpectation",
    "SufficiencyDisposition",
    "SufficiencyFailure",
]


def _items[T](values: tuple[T, ...], kind: type[T]) -> None:
    if type(values) is not tuple or len(values) > 8:
        raise ValueError("expected a tuple of at most eight items")
    if any(type(value) is not kind for value in values):
        raise TypeError("unexpected item type")
    if len(set(values)) != len(values):
        raise ValueError("duplicate items")


def _label(value: str) -> None:
    _text(value, 64)
    if not value.isascii() or any(not (c.isalnum() or c in "-_") for c in value):
        raise ValueError("invalid declaration identifier")


def _digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class SufficiencyDisposition(Enum):
    SUFFICIENT = "sufficient"
    MISSING_GOVERNING_EVIDENCE = "missing_governing_evidence"
    UNRESOLVED_AMBIGUITY = "unresolved_ambiguity"


class EvidenceRequestKind(Enum):
    NAMED_EVIDENCE = "named_evidence"
    SOURCE_ROLE = "source_role"
    OPERATOR_CLARIFICATION = "operator_clarification"


@dataclass(frozen=True, slots=True)
class EvidenceRequest:
    """An untrusted proposal. Descriptions/choices are never parsed as paths."""

    kind: EvidenceRequestKind
    description: str = field(repr=False)
    path: RepositoryPath | None = field(default=None, repr=False)
    choices: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if type(self.kind) is not EvidenceRequestKind:
            raise TypeError("request kind required")
        _text(self.description, 1024)
        _items(self.choices, str)
        for choice in self.choices:
            _text(choice, 256)
        if self.kind is EvidenceRequestKind.NAMED_EVIDENCE:
            if type(self.path) is not RepositoryPath or self.choices:
                raise ValueError("named evidence requires only a path")
            _paths((self.path,))
        elif self.path is not None:
            raise ValueError("only named evidence may carry a path")
        elif self.kind is EvidenceRequestKind.SOURCE_ROLE and self.choices:
            raise ValueError("source role cannot carry clarification choices")
        elif len(self.choices) == 1:
            raise ValueError("clarification needs zero or at least two choices")

    def _identity(self) -> object:
        return [
            self.kind.value,
            self.description,
            self.path.value if self.path is not None else None,
            self.choices,
        ]


@dataclass(frozen=True, slots=True)
class GoverningSourceExpectation:
    """Declared requirement, with an explicit supplied binding for source roles.

    Named requirements are matched by their exact path, not an alternative
    binding. A role binding asserts relevance; software only checks membership.
    """

    key: str = field(repr=False)
    request: EvidenceRequest = field(repr=False)
    supplied_paths: tuple[RepositoryPath, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        _label(self.key)
        if type(self.request) is not EvidenceRequest:
            raise TypeError("evidence request required")
        if self.request.kind is EvidenceRequestKind.OPERATOR_CLARIFICATION:
            raise ValueError("clarification is not a governing source")
        _paths(self.supplied_paths, empty=True)
        if (
            self.request.kind is EvidenceRequestKind.NAMED_EVIDENCE
            and self.supplied_paths
        ):
            raise ValueError("named requirement cannot substitute another source")

    @property
    def paths(self) -> tuple[RepositoryPath, ...]:
        return (
            (self.request.path,)
            if self.request.path is not None
            else self.supplied_paths
        )


@dataclass(frozen=True, slots=True)
class EvidenceClarification:
    """Explicit operator state, not a read or an authorization decision."""

    key: str = field(repr=False)
    request: EvidenceRequest = field(repr=False)
    answer: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        _label(self.key)
        if (
            type(self.request) is not EvidenceRequest
            or self.request.kind is not EvidenceRequestKind.OPERATOR_CLARIFICATION
        ):
            raise ValueError("operator clarification request required")
        if self.answer is not None:
            _text(self.answer, 1024)
            if self.request.choices and self.answer not in self.request.choices:
                raise ValueError("answer is not a declared choice")


@dataclass(frozen=True, slots=True)
class EvidenceManifest:
    """Exact supplied observations and declared prerequisites, not completeness.

    Provenance is a bounded caller-provided workspace/observation label, not
    authenticated provenance. Unknowns here are unresolved prerequisite claims,
    not the residual-risk unknowns in the existing final analysis contract.
    """

    question: str = field(repr=False)
    evidence: RepositoryEvidence = field(repr=False)
    provenance: str = field(repr=False)
    expectations: tuple[GoverningSourceExpectation, ...] = field(default=(), repr=False)
    clarifications: tuple[EvidenceClarification, ...] = field(default=(), repr=False)
    unknowns: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        _text(self.question, 2048)
        _text(self.provenance, 256)
        if type(self.evidence) is not RepositoryEvidence:
            raise TypeError("repository evidence required")
        _items(self.expectations, GoverningSourceExpectation)
        _items(self.clarifications, EvidenceClarification)
        _items(self.unknowns, str)
        for unknown in self.unknowns:
            _text(unknown, 1024)
        keys = [x.key for x in self.expectations] + [x.key for x in self.clarifications]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate declaration identifier")
        sources = [
            (x.request.kind, x.request.path or x.request.description)
            for x in self.expectations
        ]
        if len(set(sources)) != len(sources):
            raise ValueError("duplicate governing expectation")
        supplied = {f.path for f in self.evidence.files}
        if any(
            p.value not in supplied for x in self.expectations for p in x.supplied_paths
        ):
            raise ValueError("source-role binding is not supplied evidence")

    @property
    def evidence_identity(self) -> str:
        return _digest(
            ["analyst-evidence/1", [(f.path, f.text) for f in self.evidence.files]]
        )

    def identity(self) -> str:
        """Canonical UTF-8 SHA-256 attribution; no filesystem/model operation.

        This digest is not permission, a snapshot, or a confidentiality device.
        No public manifest/assessment wire format is introduced in this slice.
        """
        return _digest(
            [
                "analyst-sufficiency-manifest/1",
                self.question,
                self.evidence_identity,
                self.provenance,
                [
                    [x.key, x.request._identity(), sorted(p.value for p in x.paths)]
                    for x in sorted(self.expectations, key=lambda x: x.key)
                ],
                [
                    [x.key, x.request._identity(), x.answer]
                    for x in sorted(self.clarifications, key=lambda x: x.key)
                ],
                sorted(self.unknowns),
            ]
        )

    def missing_expectations(self) -> tuple[str, ...]:
        supplied = {f.path for f in self.evidence.files}
        return tuple(
            sorted(
                x.key
                for x in self.expectations
                if not x.paths or any(p.value not in supplied for p in x.paths)
            )
        )


class SufficiencyFailure(Enum):
    INVALID_OUTPUT = "invalid_output"
    MODEL_FAILURE = "model_failure"
    ACQUISITION_DENIED = "acquisition_denied"
    EVIDENCE_UNAVAILABLE = "evidence_unavailable"
    AUTHORIZATION_FAILURE = "authorization_failure"
    BUDGET_EXHAUSTED = "budget_exhausted"
    STALE_ASSESSMENT = "stale_assessment"
    PREREQUISITES_UNMET = "prerequisites_unmet"


class EvidenceSufficiencyError(ValueError):
    def __init__(self, reason: SufficiencyFailure) -> None:
        if type(reason) is not SufficiencyFailure:
            raise TypeError("sufficiency failure required")
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyAssessment:
    """Scripted/advisory judgment. validate_for checks prerequisites, not truth.

    Neither construction nor validation invokes a consumer or grants progression.
    The application must check against current inputs and obtain operator review.
    """

    manifest: EvidenceManifest = field(repr=False)
    disposition: SufficiencyDisposition
    explanation: str = field(repr=False)
    governing_sources: tuple[RepositoryPath, ...] = field(default=(), repr=False)
    requests: tuple[EvidenceRequest, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if type(self.manifest) is not EvidenceManifest:
            raise TypeError("evidence manifest required")
        if type(self.disposition) is not SufficiencyDisposition:
            raise TypeError("sufficiency disposition required")
        _text(self.explanation, 2048)
        _paths(self.governing_sources, empty=True)
        _items(self.requests, EvidenceRequest)
        supplied = {f.path for f in self.manifest.evidence.files}
        if any(p.value not in supplied for p in self.governing_sources):
            raise ValueError("governing citation is not supplied evidence")
        if self.disposition is SufficiencyDisposition.SUFFICIENT:
            if self.requests or not self.governing_sources:
                raise ValueError("sufficient requires citations and no requests")
        elif self.disposition is SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE:
            if not any(
                r.kind is not EvidenceRequestKind.OPERATOR_CLARIFICATION
                for r in self.requests
            ):
                raise ValueError(
                    "missing governing evidence requires an evidence request"
                )
        elif not any(
            r.kind is EvidenceRequestKind.OPERATOR_CLARIFICATION for r in self.requests
        ):
            raise ValueError("ambiguity requires a clarification request")
        self.validate_for(self.manifest)

    def validate_for(self, current: EvidenceManifest) -> None:
        if type(current) is not EvidenceManifest:
            raise TypeError("current evidence manifest required")
        if self.manifest.identity() != current.identity():
            raise EvidenceSufficiencyError(SufficiencyFailure.STALE_ASSESSMENT)
        if self.disposition is SufficiencyDisposition.SUFFICIENT and (
            current.missing_expectations()
            or current.unknowns
            or any(c.answer is None for c in current.clarifications)
        ):
            raise EvidenceSufficiencyError(SufficiencyFailure.PREREQUISITES_UNMET)


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyResult:
    """Exactly one semantic assessment OR operational failure; no invocation."""

    assessment: EvidenceSufficiencyAssessment | None = field(default=None, repr=False)
    failure: SufficiencyFailure | None = None

    def __post_init__(self) -> None:
        if (self.assessment is None) == (self.failure is None):
            raise ValueError("exactly one assessment or failure required")
        if (
            self.assessment is not None
            and type(self.assessment) is not EvidenceSufficiencyAssessment
        ):
            raise TypeError("typed sufficiency assessment required")
        if self.failure is not None and type(self.failure) is not SufficiencyFailure:
            raise TypeError("typed operational failure required")
