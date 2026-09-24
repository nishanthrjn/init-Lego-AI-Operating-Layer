"""Bounded review submissions and opinions, distinct from approval and Evidence."""

from dataclasses import dataclass, field
from enum import Enum

from legoai.execution.agent.ports import AgentResult
from legoai.execution.agent.values import AgentExecutionStatus, AgentId
from legoai.execution.values import ExecutionContext

from legoai_engineering.reviewer.definition import reviewer_definition


def _text(value: str, maximum: int) -> None:
    if type(value) is not str:
        raise TypeError("review text requires str")
    if not value or len(value) > maximum or value.isspace():
        raise ValueError("review text is blank or oversized")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        raise ValueError("review text must be UTF-8") from None
    if size > maximum:
        raise ValueError("review text exceeds byte limit")


def _strings(values: tuple[str, ...], *, minimum: int = 0) -> None:
    if type(values) is not tuple:
        raise TypeError("review strings require tuple")
    if not minimum <= len(values) <= 8:
        raise ValueError("review collection outside supported bounds")
    for value in values:
        _text(value, 1024)


def _material_id(value: str) -> None:
    _text(value, 64)
    if any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in value):
        raise ValueError("material ID requires lowercase ASCII letters, digits, - or _")


@dataclass(frozen=True, slots=True)
class ReviewMaterial:
    """Supplied supporting text; an ID is neither a path nor canonical Evidence."""

    material_id: str
    text: str = field(repr=False)

    def __post_init__(self) -> None:
        _material_id(self.material_id)
        if self.material_id == "proposal":
            raise ValueError("proposal is reserved for the work product")
        _text(self.text, 4096)


@dataclass(frozen=True, slots=True)
class ReviewRequest:
    """Trusted caller supplies attribution and authorizes disclosure, not the model."""

    producer: AgentId
    objective: str = field(repr=False)
    criteria: tuple[str, ...] = field(repr=False)
    proposal: str = field(repr=False)
    evidence: tuple[ReviewMaterial, ...] = field(repr=False)
    context: ExecutionContext

    def __post_init__(self) -> None:
        if (
            type(self.producer) is not AgentId
            or type(self.context) is not ExecutionContext
        ):
            raise TypeError("review requires producer AgentId and ExecutionContext")
        _text(self.objective, 2048)
        _strings(self.criteria, minimum=1)
        _text(self.proposal, 8192)
        if type(self.evidence) is not tuple:
            raise TypeError("review evidence requires tuple")
        if len(self.evidence) > 8:
            raise ValueError("at most eight supporting items are accepted")
        if any(type(item) is not ReviewMaterial for item in self.evidence):
            raise TypeError("review evidence requires ReviewMaterial")
        if len({item.material_id for item in self.evidence}) != len(self.evidence):
            raise ValueError("duplicate supporting IDs")
        size = len(self.proposal.encode("utf-8")) + sum(
            len(item.text.encode("utf-8")) for item in self.evidence
        )
        if size > 24576:
            raise ValueError("review material exceeds aggregate byte limit")


class ReviewDecision(Enum):
    ACCEPT = "accept"
    CHANGES_REQUIRED = "changes_required"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class FindingCategory(Enum):
    CORRECTNESS = "correctness"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    TESTING = "testing"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"


class FindingSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    category: FindingCategory
    severity: FindingSeverity
    message: str = field(repr=False)
    evidence_refs: tuple[str, ...]
    required_action: str | None = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.category) is not FindingCategory
            or type(self.severity) is not FindingSeverity
        ):
            raise TypeError("finding requires category and severity")
        _text(self.message, 1024)
        _strings(self.evidence_refs, minimum=1)
        for reference in self.evidence_refs:
            _material_id(reference)
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("duplicate finding references")
        if self.severity is FindingSeverity.BLOCKING:
            if self.required_action is None:
                raise ValueError("blocking finding requires action")
            _text(self.required_action, 1024)
        elif self.required_action is not None:
            raise ValueError("only blocking findings carry required actions")


@dataclass(frozen=True, slots=True)
class Review:
    """Model opinion; never an Approval, authorization or Workflow transition."""

    decision: ReviewDecision
    summary: str = field(repr=False)
    findings: tuple[ReviewFinding, ...]
    risks: tuple[str, ...] = field(repr=False)
    unknowns: tuple[str, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.decision) is not ReviewDecision:
            raise TypeError("review requires ReviewDecision")
        _text(self.summary, 2048)
        if type(self.findings) is not tuple or len(self.findings) > 8:
            raise ValueError("review supports at most eight findings")
        if any(type(f) is not ReviewFinding for f in self.findings):
            raise TypeError("review requires ReviewFinding")
        _strings(self.risks)
        _strings(self.unknowns)
        blocking = any(f.severity is FindingSeverity.BLOCKING for f in self.findings)
        if (self.decision is ReviewDecision.CHANGES_REQUIRED) != blocking:
            raise ValueError("review decision contradicts blocking findings")
        if self.decision is ReviewDecision.INSUFFICIENT_EVIDENCE and not self.unknowns:
            raise ValueError("insufficient evidence requires an explicit unknown")


class ReviewStatus(Enum):
    COMPLETED = "completed"
    INVALID_SUBMISSION = "invalid_submission"
    MODEL_FAILURE = "model_failure"
    OUTPUT_INVALID = "output_invalid"


class SubmissionFailure(Enum):
    SELF_REVIEW = "self_review"
    CONTEXT_BUDGET = "context_budget"


@dataclass(frozen=True, slots=True)
class ReviewResult:
    status: ReviewStatus
    request: ReviewRequest = field(repr=False)
    agent_result: AgentResult | None
    review: Review | None
    submission_failure: SubmissionFailure | None = None

    def __post_init__(self) -> None:
        if (
            type(self.status) is not ReviewStatus
            or type(self.request) is not ReviewRequest
        ):
            raise TypeError("review result requires status and request")
        definition = reviewer_definition()
        if self.status is ReviewStatus.INVALID_SUBMISSION:
            if (
                type(self.submission_failure) is not SubmissionFailure
                or self.agent_result is not None
                or self.review is not None
            ):
                raise ValueError("invalid submission cannot carry a model invocation")
            if self.submission_failure is SubmissionFailure.SELF_REVIEW and (
                self.request.producer != definition.agent_id
            ):
                raise ValueError("self-review failure requires matching identities")
            return
        if self.submission_failure is not None:
            raise ValueError("submission failure requires invalid status")
        if self.request.producer == definition.agent_id:
            raise ValueError("producer cannot be its independent reviewer")
        agent = self.agent_result
        if type(agent) is not AgentResult:
            raise TypeError("review requires Agent attribution")
        if (
            agent.definition != definition
            or agent.execution_id != self.request.context.execution_id
        ):
            raise ValueError("review Agent attribution mismatch")
        if self.status is ReviewStatus.COMPLETED:
            if (
                agent.status is not AgentExecutionStatus.SUCCEEDED
                or type(self.review) is not Review
            ):
                raise ValueError(
                    "completed review requires valid Agent output and review"
                )
            supplied = {
                "proposal",
                *(item.material_id for item in self.request.evidence),
            }
            if any(
                ref not in supplied
                for f in self.review.findings
                for ref in f.evidence_refs
            ):
                raise ValueError("finding cites unsupplied material")
        else:
            if self.review is not None:
                raise ValueError("failed review cannot carry an opinion")
            allowed = (
                {AgentExecutionStatus.MODEL_FAILED, AgentExecutionStatus.ROUTING_FAILED}
                if self.status is ReviewStatus.MODEL_FAILURE
                else {
                    AgentExecutionStatus.SUCCEEDED,
                    AgentExecutionStatus.OUTPUT_INVALID,
                }
            )
            if agent.status not in allowed:
                raise ValueError("review status contradicts Agent outcome")
