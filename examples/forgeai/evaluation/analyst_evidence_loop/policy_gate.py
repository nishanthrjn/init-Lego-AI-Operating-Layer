"""ForgeAI composition point for the deterministic request policy (H1).

Agent result → structural/domain validation (EvidenceSufficiencyAssessment) →
request policy (this gate) → operator review and progression (EvidenceSequence).

The gate wraps an unchanged EvidenceSequence. An assessment the policy rejects
is never forwarded: it cannot be reviewed as accepted, cannot drive acquisition
and cannot progress. The rejection is terminal for the gated sequence, with no
retry or Agent re-run. The assessment is never modified, and every decision
stays observable.
"""

from collections.abc import Mapping
from typing import cast

from legoai_engineering.analyst.request_policy import (
    EvidenceClassification,
    EvidenceRequestPolicy,
    RequestDecision,
    evaluate,
)
from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    EvidenceSufficiencyResult,
)
from legoai_engineering.repository.workspace import RepositoryPath

from analyst_evidence_loop.sequence import (
    ClarificationSelection,
    EvidenceSequence,
    Observation,
    OperatorReview,
    PathSelection,
)
from legoai.execution.values import ExecutionId

__all__ = ["PolicyGatedSequence", "RequestPolicyRejected", "policy_from_config"]
_KEYS = {"requestable_roots", "classifications", "default_classification", "granted"}


class RequestPolicyRejected(RuntimeError):
    """A rejected decision blocks review, acquisition and progression."""

    def __init__(self, decision: RequestDecision) -> None:
        self.decision = decision
        super().__init__("REQUEST_POLICY_REJECTED")


def policy_from_config(raw: Mapping[str, object]) -> EvidenceRequestPolicy:
    """Typed policy from application configuration; strict and closed.

    Expected keys:
    - `requestable_roots`: list of paths;
    - `classifications`: mapping of path to class;
    - `default_classification`: class or null;
    - `granted`: list of classes.

    A missing configuration is an error, never "allow everything".
    """
    if not isinstance(raw, Mapping) or set(raw) != _KEYS:
        raise ValueError(
            "request policy configuration requires exactly " + repr(sorted(_KEYS))
        )
    roots = cast(list[str], raw["requestable_roots"])
    classes = cast(dict[str, str], raw["classifications"])
    default = cast(str | None, raw["default_classification"])
    granted = cast(list[str], raw["granted"])
    if not isinstance(roots, list) or not isinstance(classes, dict):
        raise ValueError("roots must be a list and classifications a mapping")
    if not isinstance(granted, list):
        raise ValueError("granted must be a list")
    return EvidenceRequestPolicy(
        tuple(RepositoryPath(r) for r in roots),
        tuple(
            (RepositoryPath(p), EvidenceClassification(c))
            for p, c in sorted(classes.items())
        ),
        EvidenceClassification(default) if default is not None else None,
        frozenset(EvidenceClassification(c) for c in granted),
    )


class PolicyGatedSequence:
    """EvidenceSequence behind the request policy. The policy is required."""

    def __init__(
        self, sequence: EvidenceSequence, policy: EvidenceRequestPolicy
    ) -> None:
        if type(sequence) is not EvidenceSequence:
            raise TypeError("evidence sequence required")
        if type(policy) is not EvidenceRequestPolicy:
            raise TypeError("request policy required; there is no permissive default")
        self._sequence = sequence
        self._policy = policy
        self._decisions: list[RequestDecision] = []
        self._rejected: RequestDecision | None = None

    @property
    def decisions(self) -> tuple[RequestDecision, ...]:
        return tuple(self._decisions)

    @property
    def rejected(self) -> RequestDecision | None:
        return self._rejected

    def observe(self) -> Observation:
        return self._sequence.observe()

    def _blocked(self) -> None:
        if self._rejected is not None:
            raise RequestPolicyRejected(self._rejected)

    def assess(self, identity: ExecutionId, result: object) -> Observation:
        self._blocked()
        current: EvidenceManifest = self._sequence.observe().manifest
        if (
            type(result) is EvidenceSufficiencyResult
            and result.assessment is not None
            and result.assessment.manifest.identity() == current.identity()
        ):
            decision = evaluate(result.assessment, current, self._policy)
            self._decisions.append(decision)
            if not decision.accepted:
                self._rejected = decision
                return self._sequence.observe()  # never forwarded to review
        # Failures, stale or untyped results keep the sequence's own handling.
        return self._sequence.assess(identity, result)

    def progress(
        self, review: OperatorReview, current: EvidenceManifest
    ) -> Observation:
        self._blocked()
        return self._sequence.progress(review, current)

    async def advance(
        self,
        review: OperatorReview,
        current: EvidenceManifest,
        *,
        paths: tuple[PathSelection, ...] = (),
        clarification: ClarificationSelection | None = None,
    ) -> Observation:
        self._blocked()
        return await self._sequence.advance(
            review, current, paths=paths, clarification=clarification
        )
