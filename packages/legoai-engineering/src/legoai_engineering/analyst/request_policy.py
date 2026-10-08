"""Deterministic request policy: accept or reject a parsed sufficiency assessment.

The policy is application-controlled authority over what an assessment may
*request*. It never rewrites, repairs, drops, replaces or retries anything: the
assessment is read-only input and the decision is a separate value. It reads
only the assessment, its manifest and the policy. It performs no I/O and holds
no global state.

Path establishment (identity) and permission (scope, classification) are
separate checks. A path the model could see may still be refused.
Classification comes only from the application. Nothing here infers sensitivity
from path text or words.
"""

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum

from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    EvidenceRequestKind,
    EvidenceSufficiencyAssessment,
)
from legoai_engineering.repository.workspace import RepositoryPath

__all__ = [
    "POLICY_SCHEMA",
    "EvidenceClassification",
    "EvidenceRequestPolicy",
    "RequestDecision",
    "RequestViolation",
    "RequestViolationReason",
    "evaluate",
    "is_established",
    "known_paths",
]
POLICY_SCHEMA = "legoai-engineering/evidence-request-policy/1"
# Characters that continue a path name; a match bordered by one is a fragment.
_PATH_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-./\\~"
)


class EvidenceClassification(Enum):
    """Closed, application-assigned evidence classes."""

    ORDINARY = "ordinary"
    SENSITIVE = "sensitive"
    OPERATOR_ONLY = "operator_only"


class RequestViolationReason(Enum):
    PATH_NOT_ESTABLISHED = "path_not_established"
    OUTSIDE_REQUESTABLE_SCOPE = "outside_requestable_scope"
    CLASSIFICATION_NOT_GRANTED = "classification_not_granted"
    PATH_AS_CLARIFICATION_CHOICE = "path_as_clarification_choice"


def _parts(path: RepositoryPath) -> tuple[str, ...]:
    return tuple(path.value.split("/"))


def _within(path: RepositoryPath, root: RepositoryPath) -> bool:
    """Component-wise containment; `config` never contains `configuration/x`."""
    root_parts = _parts(root)
    return _parts(path)[: len(root_parts)] == root_parts


@dataclass(frozen=True, slots=True)
class EvidenceRequestPolicy:
    """Explicit application authority for named-evidence requests.

    - requestable_roots: directories a named request may point into. There are
      no globs and no implicit repository root; empty means no named request is
      permitted.
    - classifications: application-assigned classes for exact paths or
      directories. The most specific (longest) matching entry wins.
    - default_classification: class of a path no entry covers. None (the
      default) means unknown, which is never granted (fail closed).
    - granted: classes that may be requested (default: ordinary only).
    """

    requestable_roots: tuple[RepositoryPath, ...] = ()
    classifications: tuple[tuple[RepositoryPath, EvidenceClassification], ...] = field(
        default=(), repr=False
    )
    default_classification: EvidenceClassification | None = None
    granted: frozenset[EvidenceClassification] = frozenset(
        {EvidenceClassification.ORDINARY}
    )

    def __post_init__(self) -> None:
        if type(self.requestable_roots) is not tuple or any(
            type(r) is not RepositoryPath for r in self.requestable_roots
        ):
            raise TypeError("requestable roots must be a tuple of RepositoryPath")
        if len(set(self.requestable_roots)) != len(self.requestable_roots):
            raise ValueError("duplicate requestable root")
        if type(self.classifications) is not tuple or any(
            type(entry) is not tuple
            or len(entry) != 2
            or type(entry[0]) is not RepositoryPath
            or type(entry[1]) is not EvidenceClassification
            for entry in self.classifications
        ):
            raise TypeError("classifications must be (RepositoryPath, class) pairs")
        if len({p for p, _ in self.classifications}) != len(self.classifications):
            raise ValueError("duplicate classified path")
        if (
            self.default_classification is not None
            and type(self.default_classification) is not EvidenceClassification
        ):
            raise TypeError("default classification must be typed or None")
        if type(self.granted) is not frozenset or any(
            type(c) is not EvidenceClassification for c in self.granted
        ):
            raise TypeError("granted classes must be a frozenset of classifications")

    def classify(self, path: RepositoryPath) -> EvidenceClassification | None:
        matches = [
            (len(_parts(p)), c) for p, c in self.classifications if _within(path, p)
        ]
        return max(matches)[1] if matches else self.default_classification

    def in_scope(self, path: RepositoryPath) -> bool:
        return any(_within(path, root) for root in self.requestable_roots)

    def digest(self) -> str:
        """SHA-256 of the canonical effective policy (a one-way identity)."""
        canonical = {
            "schema": POLICY_SCHEMA,
            "requestable_roots": sorted(r.value for r in self.requestable_roots),
            "classifications": sorted(
                [p.value, c.value] for p, c in self.classifications
            ),
            "default_classification": self.default_classification.value
            if self.default_classification
            else None,
            "granted": sorted(c.value for c in self.granted),
        }
        encoded = json.dumps(canonical, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RequestViolation:
    index: int
    reason: RequestViolationReason
    # Present only for CLASSIFICATION_NOT_GRANTED; None means unknown class.
    classification: EvidenceClassification | None = None


@dataclass(frozen=True, slots=True)
class RequestDecision:
    """Separate from the assessment, which is never modified."""

    accepted: bool
    violations: tuple[RequestViolation, ...]
    request_kinds: tuple[EvidenceRequestKind, ...]
    policy_digest: str

    def __post_init__(self) -> None:
        if self.accepted == bool(self.violations):
            raise ValueError("accepted exactly when there are no violations")

    def audit(self) -> dict[str, object]:
        """Bounded, safe audit record: no paths, prose or model output."""
        return {
            "schema": POLICY_SCHEMA,
            "accepted": self.accepted,
            "policy_digest": self.policy_digest,
            "request_kinds": [k.value for k in self.request_kinds],
            "violations": [
                {
                    "index": v.index,
                    "reason": v.reason.value,
                    "classification": v.classification.value
                    if v.classification
                    else None,
                }
                for v in self.violations
            ],
        }


def known_paths(manifest: EvidenceManifest) -> frozenset[str]:
    """Repository identities known from trusted facts: supplied and declared."""
    supplied = {f.path for f in manifest.evidence.files}
    declared = {p.value for x in manifest.expectations for p in x.paths}
    return frozenset(supplied | declared)


def _occurs(path: str, text: str) -> bool:
    """`path` appears on its own: not inside a longer path or name."""
    start = text.find(path)
    while start != -1:
        end = start + len(path)
        before = text[start - 1] if start else ""
        after = text[end : end + 2]
        bounded_after = (
            not after
            or after[0] not in _PATH_CHARS
            or (after[0] == "." and (len(after) == 1 or after[1] not in _PATH_CHARS))
        )
        if before not in _PATH_CHARS and bounded_after:
            return True
        start = text.find(path, start + 1)
    return False


def is_established(path: RepositoryPath, manifest: EvidenceManifest) -> bool:
    """Exact identity visible at the Agent boundary; never inferred.

    Established by:
    - a supplied file;
    - an application-declared expectation;
    - a bounded exact occurrence in supplied evidence content.

    Imports, module names, layout conventions and guesses never establish a
    path.
    """
    if path.value in known_paths(manifest):
        return True
    return any(_occurs(path.value, f.text) for f in manifest.evidence.files)


def evaluate(
    assessment: EvidenceSufficiencyAssessment,
    manifest: EvidenceManifest,
    policy: EvidenceRequestPolicy,
) -> RequestDecision:
    """Accept or reject the assessment's requests. Pure; never modifies input."""
    if type(assessment) is not EvidenceSufficiencyAssessment:
        raise TypeError("parsed sufficiency assessment required")
    if type(manifest) is not EvidenceManifest:
        raise TypeError("evidence manifest required")
    if type(policy) is not EvidenceRequestPolicy:
        raise TypeError("evidence request policy required")
    if assessment.manifest.identity() != manifest.identity():
        raise ValueError("assessment does not belong to this manifest")
    known = known_paths(manifest)
    violations: list[RequestViolation] = []
    for index, request in enumerate(assessment.requests):
        if request.kind is EvidenceRequestKind.NAMED_EVIDENCE:
            if request.path is None:  # excluded by EvidenceRequest itself
                raise ValueError("named evidence request without a path")
            established = is_established(request.path, manifest)
            in_scope = policy.in_scope(request.path)
            if not established:
                violations.append(
                    RequestViolation(index, RequestViolationReason.PATH_NOT_ESTABLISHED)
                )
            if not in_scope:
                violations.append(
                    RequestViolation(
                        index, RequestViolationReason.OUTSIDE_REQUESTABLE_SCOPE
                    )
                )
            if established and in_scope:
                cls = policy.classify(request.path)
                if cls is None or cls not in policy.granted:
                    violations.append(
                        RequestViolation(
                            index,
                            RequestViolationReason.CLASSIFICATION_NOT_GRANTED,
                            cls,
                        )
                    )
        elif request.kind is EvidenceRequestKind.OPERATOR_CLARIFICATION and any(
            choice in known for choice in request.choices
        ):
            violations.append(
                RequestViolation(
                    index, RequestViolationReason.PATH_AS_CLARIFICATION_CHOICE
                )
            )
    return RequestDecision(
        not violations,
        tuple(violations),
        tuple(r.kind for r in assessment.requests),
        policy.digest(),
    )
