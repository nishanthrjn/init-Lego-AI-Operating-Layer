"""ForgeAI-1 task vocabulary: immutable values only, no effects.

A task carries intent only: objective, bounded targets and constraints. Every
infrastructure choice (repository root, model, grants, sandbox, checks) is
operator configuration held by the composition root, never task data.
"""

from dataclasses import dataclass, field
from enum import Enum

from legoai.execution.agent.values import AgentExecutionStatus
from legoai.kernel.effects import EffectExtent
from legoai_engineering.analyst.values import AcquisitionFailure
from legoai_engineering.authorization import EffectAuthorizationFailure
from legoai_engineering.checks.errors import CheckFailure
from legoai_engineering.checks.values import CheckOutcome, CheckRequest, CheckResult
from legoai_engineering.coding.values import CodingProposal, CodingStatus, CodingTarget
from legoai_engineering.git.errors import GitFailure
from legoai_engineering.git.values import GitRepositoryState
from legoai_engineering.repository.mutation import RepositoryMutationResult
from legoai_engineering.repository.mutation_errors import MutationConflictReason
from legoai_engineering.repository.workspace import RepositoryPath

LIMITATIONS = (
    "Checks ran in the qualified sandbox; a pass is an observed contained "
    "outcome, not proof that the change is correct.",
    "Check results do not identify exactly which files were copied into the "
    "sandbox; only the configured check requests are recorded.",
    "Git state is operator evidence only and was never disclosed to the model.",
)


def _text(value: object, maximum: int) -> None:
    if type(value) is not str:
        raise TypeError("task text requires str")
    if not value or value.isspace():
        raise ValueError("task text must not be blank")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        raise ValueError("task text must be UTF-8") from None
    if size > maximum:
        raise ValueError("task text exceeds its byte limit")


@dataclass(frozen=True, slots=True)
class TaskRequest:
    """One bounded coding task: what to change, never how or where to run it."""

    objective: str = field(repr=False)
    targets: tuple[CodingTarget, ...]
    constraints: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        _text(self.objective, 2048)
        if type(self.targets) is not tuple or not 1 <= len(self.targets) <= 8:
            raise ValueError("a task requires one to eight targets")
        if any(type(target) is not CodingTarget for target in self.targets):
            raise TypeError("task targets require CodingTarget")
        paths = [target.path.value.casefold() for target in self.targets]
        if len(set(paths)) != len(paths) or any(
            other.startswith(path + "/")
            for path in paths
            for other in paths
            if path != other
        ):
            raise ValueError("duplicate, case-alias or nested task targets")
        if type(self.constraints) is not tuple or len(self.constraints) > 8:
            raise ValueError("a task allows at most eight constraints")
        for constraint in self.constraints:
            _text(constraint, 1024)


class TaskDisposition(Enum):
    """SUCCEEDED requires applied changes, all checks PASSED and an intact HEAD."""

    SUCCEEDED = "succeeded"
    # Refused before any model call or repository effect.
    REJECTED = "rejected"
    # Work started (model called, possibly files changed) but did not succeed.
    FAILED = "failed"


class TaskFailure(Enum):
    """Closed reasons; each names the step that stopped the run."""

    WORKSPACE_BUSY = "another run holds this workspace"
    REPOSITORY_UNAVAILABLE = "initial Git state could not be observed"
    UNSUPPORTED_REPOSITORY = "repository has no commit to anchor the run"
    DIRTY_START = "repository has pre-existing changes"
    EVIDENCE_DENIED = "repository read authorization denied"
    EVIDENCE_UNAVAILABLE = "bounded repository evidence could not be acquired"
    MODEL_FAILED = "the model call did not complete"
    PROPOSAL_INVALID = "the model output was not a valid proposal"
    MUTATION_DENIED = "change application was not authorized; nothing written"
    MUTATION_CONFLICT = "a change precondition failed; nothing written"
    MUTATION_PARTIAL = "change application failed; effects may be partial"
    CHECK_DENIED = "check execution was not authorized"
    CHECK_ERROR = "a check could not complete (infrastructure)"
    CHECKS_FAILED = "a configured check reported findings"
    FINAL_STATE_UNAVAILABLE = "final Git state could not be observed"
    HEAD_CHANGED = "HEAD changed during the run"
    UNEXPECTED_CHANGES = "working tree differs from the applied changes"


_REJECTIONS = frozenset(
    {
        TaskFailure.WORKSPACE_BUSY,
        TaskFailure.REPOSITORY_UNAVAILABLE,
        TaskFailure.UNSUPPORTED_REPOSITORY,
        TaskFailure.DIRTY_START,
        TaskFailure.EVIDENCE_DENIED,
        TaskFailure.EVIDENCE_UNAVAILABLE,
    }
)


@dataclass(frozen=True, slots=True)
class CheckRecord:
    """One configured check: its result, or why it produced none."""

    request: CheckRequest
    result: CheckResult | None
    error: CheckFailure | EffectAuthorizationFailure | None = None
    workspace_error: bool = False

    def __post_init__(self) -> None:
        if type(self.request) is not CheckRequest:
            raise TypeError("check record requires CheckRequest")
        failed = self.error is not None or self.workspace_error
        if (self.result is None) != failed:
            raise ValueError("check record needs exactly a result or a failure")
        if self.result is not None and (
            type(self.result) is not CheckResult
            or self.result.kind is not self.request.kind
        ):
            raise ValueError("check result does not match its request")

    @property
    def passed(self) -> bool:
        return self.result is not None and self.result.outcome is CheckOutcome.PASSED


@dataclass(frozen=True, slots=True)
class TaskEvidence:
    """Bounded per-run record composed from existing LegoAI result values.

    Holds no exception objects, environment, host paths or runtime handles.
    """

    run_id: str
    start: GitRepositoryState | None = None
    start_failure: GitFailure | None = None
    coding_status: CodingStatus | None = None
    acquisition_failure: AcquisitionFailure | None = None
    agent_status: AgentExecutionStatus | None = None
    model_effect: EffectExtent | None = None
    proposal: CodingProposal | None = field(default=None, repr=False)
    applied: RepositoryMutationResult | None = None
    mutation_denial: EffectAuthorizationFailure | None = None
    conflict: MutationConflictReason | None = None
    conflict_path: RepositoryPath | None = None
    uncertain: RepositoryPath | None = None
    temporary_paths: tuple[RepositoryPath, ...] = ()
    planned_checks: tuple[CheckRequest, ...] = ()
    checks: tuple[CheckRecord, ...] = ()
    final: GitRepositoryState | None = None
    final_failure: GitFailure | None = None
    limitations: tuple[str, ...] = LIMITATIONS

    def __post_init__(self) -> None:
        _text(self.run_id, 256)
        if len(self.planned_checks) > 8 or len(self.checks) > len(self.planned_checks):
            raise ValueError("check evidence exceeds the configured plan")
        if any(
            record.request != planned
            for record, planned in zip(self.checks, self.planned_checks, strict=False)
        ):
            raise ValueError("check evidence must follow the configured order")
        if len(self.temporary_paths) > 128:
            raise ValueError("too many temporary paths")

    @property
    def changed_paths(self) -> tuple[RepositoryPath, ...]:
        if self.applied is None:
            return ()
        return tuple(change.path for change in self.applied.applied)


@dataclass(frozen=True, slots=True)
class TaskResult:
    task: TaskRequest = field(repr=False)
    disposition: TaskDisposition
    failure: TaskFailure | None
    evidence: TaskEvidence = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.task) is not TaskRequest:
            raise TypeError("task result requires TaskRequest")
        if type(self.disposition) is not TaskDisposition:
            raise TypeError("task result requires TaskDisposition")
        if type(self.evidence) is not TaskEvidence:
            raise TypeError("task result requires TaskEvidence")
        evidence = self.evidence
        if self.disposition is TaskDisposition.SUCCEEDED:
            if self.failure is not None:
                raise ValueError("a successful task carries no failure")
            if (
                evidence.applied is None
                or evidence.final is None
                or evidence.start is None
                or len(evidence.checks) != len(evidence.planned_checks)
                or not evidence.planned_checks
                or not all(record.passed for record in evidence.checks)
                or evidence.final.head != evidence.start.head
            ):
                raise ValueError("success requires applied changes and passed checks")
            return
        if type(self.failure) is not TaskFailure:
            raise TypeError("an unsuccessful task requires TaskFailure")
        rejected = self.failure in _REJECTIONS
        if rejected != (self.disposition is TaskDisposition.REJECTED):
            raise ValueError("disposition does not match the failure step")
        if rejected and (
            evidence.agent_status is not None
            or evidence.proposal is not None
            or evidence.applied is not None
            or evidence.checks
        ):
            raise ValueError("a rejected task cannot carry model or effect evidence")
