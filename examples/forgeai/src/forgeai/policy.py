"""Pure operator batch policy; never reads configuration or performs effects."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.workspace import RepositoryPath

from forgeai.domain import OperatorDecision, ProposalReview, proposal_identity
from forgeai.repository_context import ContextOutcome, ContextPreflight

DEFAULT_FORBIDDEN_NAMES = frozenset(
    {
        "pyproject.toml",
        "uv.lock",
        "poetry.lock",
        "requirements*.txt",
        "setup.py",
        "setup.cfg",
        "Pipfile",
        "Pipfile.lock",
        "package.json",
        "package-lock.json",
        "Dockerfile",
        ".env*",
        ".github",
        ".gitlab-ci*",
    }
)


@dataclass(frozen=True, slots=True)
class ApprovalPolicy:
    max_changed_files: int = 8
    max_total_bytes: int = 24576
    allow_create: bool = False
    forbidden_names: frozenset[str] = DEFAULT_FORBIDDEN_NAMES
    forbidden_prefixes: tuple[str, ...] = ()
    require_review_accept: bool = True
    max_tasks: int = 20
    max_batch_minutes: int = 60

    def __post_init__(self) -> None:
        for value, maximum in (
            (self.max_changed_files, 8),
            (self.max_total_bytes, 24576),
            (self.max_tasks, 20),
            (self.max_batch_minutes, 480),
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("policy limit outside its closed range")
        if (
            type(self.allow_create) is not bool
            or self.require_review_accept is not True
        ):
            raise ValueError("boolean create permission and mandatory review required")
        if (
            type(self.forbidden_names) is not frozenset
            or not DEFAULT_FORBIDDEN_NAMES <= self.forbidden_names
            or len(self.forbidden_names) > 128
        ):
            raise ValueError("forbidden names may only extend the defaults")
        for name in self.forbidden_names:
            if (
                type(name) is not str
                or not name
                or len(name) > 255
                or any(char in name for char in "/\\?[]\x00\r\n")
            ):
                raise ValueError("forbidden names are basenames with optional *")
        if (
            type(self.forbidden_prefixes) is not tuple
            or len(self.forbidden_prefixes) > 128
        ):
            raise ValueError("bounded immutable prefixes required")
        for prefix in self.forbidden_prefixes:
            RepositoryPath(prefix)


class PolicyRule(Enum):
    IDENTITY = "identity"
    FILE_COUNT = "file_count"
    TOTAL_BYTES = "total_bytes"
    OPERATIONS = "operations"
    FORBIDDEN_NAMES = "forbidden_names"
    FORBIDDEN_PREFIXES = "forbidden_prefixes"
    REVIEW_REQUIRED = "review_required"
    EVALUATION = "evaluation"


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    outcomes: tuple[tuple[PolicyRule, bool], ...]

    @property
    def approved(self) -> bool:
        return tuple(rule for rule, _ in self.outcomes) == tuple(PolicyRule) and all(
            passed is True for _, passed in self.outcomes
        )


def _matches(name: str, pattern: str) -> bool:
    """Case-insensitive basename glob; only * is special."""
    pieces = pattern.casefold().split("*")
    name = name.casefold()
    if len(pieces) == 1:
        return name == pieces[0]
    if not name.startswith(pieces[0]) or not name.endswith(pieces[-1]):
        return False
    position = len(pieces[0])
    for piece in pieces[1:-1]:
        found = name.find(piece, position)
        if found < 0:
            return False
        position = found + len(piece)
    return position <= len(name) - len(pieces[-1])


def evaluate(policy: ApprovalPolicy, review: ProposalReview) -> PolicyEvaluation:
    """Evaluate proposal gates, not the later independent review outcome."""
    try:
        if type(policy) is not ApprovalPolicy or type(review) is not ProposalReview:
            raise TypeError("typed policy and validated review required")
        changes = review.proposal.changeset.changes
        paths = tuple(change.path.value for change in changes)
        passed = (
            review.identity == proposal_identity(review.proposal),
            1 <= len(changes) <= policy.max_changed_files,
            sum(len((change.text or "").encode("utf-8")) for change in changes)
            <= policy.max_total_bytes,
            all(
                change.kind is FileChangeKind.UPDATE
                or (policy.allow_create and change.kind is FileChangeKind.CREATE)
                for change in changes
            ),
            not any(
                _matches(part, pattern)
                for path in paths
                for part in path.split("/")
                for pattern in policy.forbidden_names
            ),
            not any(
                path.casefold() == prefix.casefold()
                or path.casefold().startswith(prefix.casefold() + "/")
                for path in paths
                for prefix in policy.forbidden_prefixes
            ),
            policy.require_review_accept is True,
            True,
        )
        return PolicyEvaluation(tuple(zip(PolicyRule, passed, strict=True)))
    except Exception:
        return PolicyEvaluation(tuple((rule, False) for rule in PolicyRule))


def policy_approver(
    policy: ApprovalPolicy,
) -> Callable[[ProposalReview], OperatorDecision]:
    def approve(review: ProposalReview) -> OperatorDecision:
        try:
            return OperatorDecision(evaluate(policy, review).approved, review.identity)
        except Exception:
            return OperatorDecision(False, ())

    return approve


def exact_context_confirmer(
    expected_paths: tuple[RepositoryPath, ...],
) -> Callable[[ContextPreflight], bool]:
    expected = frozenset(path.value for path in expected_paths)

    def confirm(preflight: ContextPreflight) -> bool:
        try:
            return (
                type(preflight) is ContextPreflight
                and preflight.outcome is ContextOutcome.READY_FOR_CONTEXT_CONFIRMATION
                and frozenset(item.path.value for item in preflight.inventory)
                == expected
            )
        except Exception:
            return False

    return confirm
