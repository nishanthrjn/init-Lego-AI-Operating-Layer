"""ForgeAI task vocabulary (ForgeAI-3): immutable values only, no effects.

A task carries intent only: objective, bounded targets and constraints. Every
infrastructure choice (repository root, model, grants, sandbox, checks) is
operator configuration held by the composition root, never task data.
"""

from dataclasses import dataclass, field
from enum import Enum

from legoai.execution.agent.values import AgentExecutionStatus
from legoai.kernel.effects import EffectExtent
from legoai_engineering.agent_output import OutputDiagnostic
from legoai_engineering.analyst.values import AcquisitionFailure
from legoai_engineering.authorization import EffectAuthorizationFailure
from legoai_engineering.checks.errors import CheckFailure
from legoai_engineering.checks.values import CheckOutcome, CheckRequest, CheckResult
from legoai_engineering.coding.values import CodingProposal, CodingStatus, CodingTarget
from legoai_engineering.git.errors import GitFailure
from legoai_engineering.git.values import GitRepositoryState
from legoai_engineering.repository.mutation import (
    RepositoryChangeSet,
    RepositoryMutationResult,
    digest_text,
)
from legoai_engineering.repository.mutation_errors import MutationConflictReason
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.reviewer.values import (
    ReviewDecision,
    ReviewResult,
    ReviewStatus,
)
from legoai_engineering.sandbox.errors import SandboxFailure
from legoai_engineering.sandbox.prepared import PreparationFailure

from forgeai.repository_context import (
    ContextConfirmation,
    ContextPreflight,
    inventory_digest,
)

LIMITATIONS = (
    "Checks ran in the qualified sandbox; a pass is an observed contained "
    "outcome, not proof that the change is correct.",
    "Check results do not identify exactly which files were copied into the "
    "sandbox; only the configured check requests are recorded.",
    "Git state is operator evidence only and was never disclosed to the model.",
    "The independent review is a model opinion from a distinct Agent "
    "definition on the same configured model binding; it is not proof of "
    "correctness, independence of model weights, or authorization.",
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
    """One bounded coding task: what to change, never how or where to run it.

    `context` names operator-selected files disclosed read-only to the Coding
    Agent. It is disclosure, not write scope: only `targets` are editable, and
    a path cannot be both.
    """

    objective: str = field(repr=False)
    targets: tuple[CodingTarget, ...]
    constraints: tuple[str, ...] = field(default=(), repr=False)
    context: tuple[RepositoryPath, ...] = ()

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
        if type(self.context) is not tuple or len(self.context) > 8:
            raise ValueError("a task allows at most eight read-only context files")
        if any(type(path) is not RepositoryPath for path in self.context):
            raise TypeError("task context requires RepositoryPath")
        keys = [path.value.casefold() for path in self.context]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate or case-alias read-only context files")
        if any(
            part.startswith(".")
            for path in self.context
            for part in path.value.split("/")
        ):
            raise ValueError("read-only context excludes hidden path components")
        if set(keys) & set(paths):
            raise ValueError(
                "a path cannot be both an editable target and read-only context"
            )


MAX_ATTEMPTS = 2  # the initial proposal plus exactly one rework; not configurable


class TaskDisposition(Enum):
    """SUCCEEDED requires the latest attempt to pass every gate and review."""

    SUCCEEDED = "succeeded"
    # Refused before any model call or repository effect.
    REJECTED = "rejected"
    # Work started (model called, possibly files changed) but did not succeed.
    FAILED = "failed"


class CheckProfile(Enum):
    GENERIC = "generic"
    PROJECT = "project"


class TaskFailure(Enum):
    """Closed reasons; each names the step that stopped the run."""

    WORKSPACE_BUSY = "another run holds this workspace"
    REPOSITORY_UNAVAILABLE = "initial Git state could not be observed"
    UNSUPPORTED_REPOSITORY = "repository has no commit to anchor the run"
    DIRTY_START = "repository has pre-existing changes"
    MODEL_DISCLOSURE_REFUSED = "remote model disclosure was not approved for this task"
    CHECK_ENVIRONMENT_UNAVAILABLE = (
        "check environment preparation failed before model invocation"
    )
    CONTEXT_INCOMPLETE = "required repository context is incomplete"
    CONTEXT_DECLINED = "repository context was not confirmed"
    CONTEXT_PREFLIGHT_FAILED = "repository context acquisition failed"
    EVIDENCE_DENIED = "repository read authorization denied"
    EVIDENCE_UNAVAILABLE = "bounded repository evidence could not be acquired"
    CONTEXT_STALE = "confirmed repository context no longer matches"
    MODEL_FAILED = "the model call did not complete"
    PROPOSAL_INVALID = "the model output was not a valid proposal"
    # The operator did not approve the validated proposal (or could not be
    # asked); nothing was written, checked or reviewed.
    PROPOSAL_DECLINED = "the operator did not approve the proposal; nothing written"
    MUTATION_DENIED = "change application was not authorized; nothing written"
    MUTATION_CONFLICT = "a change precondition failed; nothing written"
    MUTATION_PARTIAL = "change application failed; effects may be partial"
    CHECK_DENIED = "check execution was not authorized"
    CHECK_ERROR = "a check could not complete (infrastructure)"
    CHECKS_FAILED = "a configured check reported findings"
    FINAL_STATE_UNAVAILABLE = "final Git state could not be observed"
    HEAD_CHANGED = "HEAD changed during the run"
    UNEXPECTED_CHANGES = "working tree differs from the applied changes"
    # The review could not complete (execution failure, not an opinion).
    REVIEW_INPUT_FAILED = "review material could not be assembled within bounds"
    REVIEW_FAILED = "the review model call did not complete"
    REVIEW_OUTPUT_INVALID = "the reviewer output was not a valid review"
    # The review completed and withheld acceptance (opinion).
    REVIEW_CHANGES_REQUIRED = "the independent review requires changes"
    REVIEW_INSUFFICIENT_EVIDENCE = "the independent review found evidence insufficient"
    # Review #1 required changes but its findings did not fit a bounded rework.
    REWORK_INPUT_FAILED = "rework feedback does not fit a bounded rework request"


class ReviewInputFailure(Enum):
    READ_DENIED = "authorized read of changed files was denied"
    READ_UNAVAILABLE = "changed files could not be read within bounds"
    MATERIAL_BOUNDS = "review material exceeds the reviewer contract bounds"
    CONTEXT_BUDGET = "serialized review exceeds the reviewer context budget"


_REJECTIONS = frozenset(
    {
        TaskFailure.CONTEXT_INCOMPLETE,
        TaskFailure.CONTEXT_DECLINED,
        TaskFailure.CONTEXT_PREFLIGHT_FAILED,
        TaskFailure.WORKSPACE_BUSY,
        TaskFailure.REPOSITORY_UNAVAILABLE,
        TaskFailure.UNSUPPORTED_REPOSITORY,
        TaskFailure.DIRTY_START,
        TaskFailure.CHECK_ENVIRONMENT_UNAVAILABLE,
        TaskFailure.MODEL_DISCLOSURE_REFUSED,
        TaskFailure.EVIDENCE_DENIED,
        TaskFailure.EVIDENCE_UNAVAILABLE,
        TaskFailure.CONTEXT_STALE,
    }
)


class ReworkTrigger(Enum):
    """What consumed the run's single rework budget (at most one per run)."""

    CHECK_FINDINGS = "deterministic checks reported code findings"
    REVIEW_CHANGES_REQUIRED = "the independent review required changes"


class RunStage(Enum):
    """Operator-visible progress; presentation only, never control flow."""

    REPOSITORY_VERIFIED = "repository verified"
    PROPOSAL_GENERATED = "proposal generated"
    AWAITING_APPROVAL = "waiting for approval"
    CHANGES_APPLIED = "changes applied"
    CHECKS_COMPLETED = "checks completed"
    REVIEW_COMPLETED = "review completed"
    REWORK_STARTED = "rework started"
    CHECK_REWORK_STARTED = "check-feedback rework started"


type ProposalIdentity = tuple[tuple[str, str, str | None, str | None], ...]


def proposal_identity(proposal: CodingProposal) -> ProposalIdentity:
    """Exact change-set identity: path, kind, precondition and content digest.

    Approval is bound to this value; a different change set never matches.
    """
    return changeset_identity(proposal.changeset)


def changeset_identity(changeset: RepositoryChangeSet) -> ProposalIdentity:
    """The same identity computed from the change set handed to mutation."""
    return tuple(
        (
            change.path.value,
            change.kind.value,
            change.expected.value if change.expected is not None else None,
            digest_text(change.text).value if change.text is not None else None,
        )
        for change in changeset.changes
    )


@dataclass(frozen=True, slots=True)
class ProposalReview:
    """What the operator is asked to approve: one validated proposal.

    `before` holds, per change, the exact current text the proposal's
    precondition digest was computed from (None for a create). It is
    verified against that digest, so a preview diffed from it shows the
    change the mutation preconditions will enforce.
    """

    attempt: int
    proposal: CodingProposal = field(repr=False)
    identity: ProposalIdentity = field(repr=False)
    before: tuple[str | None, ...] = field(repr=False)
    # For a rework: what triggered it and the exact bounded feedback the
    # Coding Agent received, shown so the operator sees what drove the change.
    rework: ReworkTrigger | None = None
    feedback: tuple[str, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if type(self.proposal) is not CodingProposal:
            raise TypeError("proposal review requires CodingProposal")
        if self.identity != proposal_identity(self.proposal):
            raise ValueError("proposal review identity mismatch")
        changes = self.proposal.changeset.changes
        if type(self.before) is not tuple or len(self.before) != len(changes):
            raise ValueError("proposal review needs one current text per change")
        for change, text in zip(changes, self.before, strict=True):
            if change.expected is None:
                if text is not None:
                    raise ValueError("a created file has no current text")
            elif type(text) is not str or digest_text(text) != change.expected:
                raise ValueError("current text does not match the precondition")
        if self.rework is not None and type(self.rework) is not ReworkTrigger:
            raise TypeError("rework trigger requires ReworkTrigger")
        if (self.rework is None and self.feedback) or (
            type(self.feedback) is not tuple
            or any(type(item) is not str for item in self.feedback)
        ):
            raise ValueError("only a rework proposal carries feedback text")


@dataclass(frozen=True, slots=True)
class OperatorDecision:
    """The operator's answer, bound to the exact proposal identity shown."""

    approved: bool
    identity: ProposalIdentity = field(repr=False)

    @classmethod
    def approve(cls, review: ProposalReview) -> OperatorDecision:
        return cls(True, review.identity)

    @classmethod
    def decline(cls, review: ProposalReview) -> OperatorDecision:
        return cls(False, review.identity)


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
class AttemptEvidence:
    """One proposal attempt within a run: 1 = initial, 2 = the single rework.

    Holds that attempt's Coding, mutation, check, Git and review values only.
    """

    number: int
    coding_status: CodingStatus | None = None
    acquisition_failure: AcquisitionFailure | None = None
    agent_status: AgentExecutionStatus | None = None
    # Why the Coding Agent output was rejected (display-safe; no model text).
    coding_diagnostic: OutputDiagnostic | None = None
    model_effect: EffectExtent | None = None
    proposal: CodingProposal | None = field(default=None, repr=False)
    # None: not asked (no valid proposal); True/False: the operator's decision.
    approval: bool | None = None
    applied: RepositoryMutationResult | None = None
    mutation_denial: EffectAuthorizationFailure | None = None
    conflict: MutationConflictReason | None = None
    conflict_path: RepositoryPath | None = None
    uncertain: RepositoryPath | None = None
    temporary_paths: tuple[RepositoryPath, ...] = ()
    checks: tuple[CheckRecord, ...] = ()
    final: GitRepositoryState | None = None
    final_failure: GitFailure | None = None
    review_input_failure: ReviewInputFailure | None = None
    review_materials: tuple[tuple[str, RepositoryPath], ...] = ()
    review: ReviewResult | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if type(self.number) is not int or not 1 <= self.number <= MAX_ATTEMPTS:
            raise ValueError("attempt number must be 1 or 2")
        if self.coding_diagnostic is not None and (
            type(self.coding_diagnostic) is not OutputDiagnostic
            or self.coding_status is not CodingStatus.OUTPUT_INVALID
        ):
            raise ValueError("only rejected coding output carries a diagnostic")
        if len(self.checks) > 8:
            raise ValueError("check evidence exceeds the configured plan")
        if len(self.temporary_paths) > 128:
            raise ValueError("too many temporary paths")
        if len(self.review_materials) > 8:
            raise ValueError("too many review materials")
        if self.review is not None and type(self.review) is not ReviewResult:
            raise TypeError("review evidence requires ReviewResult")

    @property
    def review_decision(self) -> ReviewDecision | None:
        if self.review is None or self.review.review is None:
            return None
        return self.review.review.decision


@dataclass(frozen=True, slots=True)
class TaskEvidence:
    """Bounded per-run record composed from existing LegoAI result values.

    One run id for the whole task; `attempts` holds at most two attempts. The
    single-value properties below report the latest attempt. Holds no
    exception objects, environment, host paths or runtime handles.
    """

    run_id: str
    start: GitRepositoryState | None = None
    start_failure: GitFailure | None = None
    planned_checks: tuple[CheckRequest, ...] = ()
    attempts: tuple[AttemptEvidence, ...] = ()
    # The single rework budget: which event consumed it, if any.
    rework_trigger: ReworkTrigger | None = None
    limitations: tuple[str, ...] = LIMITATIONS
    context_preflight: ContextPreflight | None = None
    context_confirmed: bool = False
    context_confirmations: tuple[ContextConfirmation, ...] = ()
    preparation_failure: PreparationFailure | None = None
    preparation_infrastructure_failure: SandboxFailure | None = None

    def __post_init__(self) -> None:
        _text(self.run_id, 256)
        if (
            type(self.context_confirmations) is not tuple
            or len(self.context_confirmations) > 2
            or any(
                type(item) is not ContextConfirmation
                for item in self.context_confirmations
            )
        ):
            raise ValueError("at most two typed context decisions required")
        if (
            self.context_preflight is not None
            and type(self.context_preflight) is not ContextPreflight
        ):
            raise TypeError("context evidence requires ContextPreflight")
        if type(self.context_confirmed) is not bool:
            raise TypeError("context confirmation requires bool")
        if self.context_confirmed and (
            self.context_preflight is None or self.context_preflight.reason is not None
        ):
            raise ValueError("confirmation requires ready context")
        if self.context_confirmed and (
            not self.context_confirmations
            or not self.context_confirmations[-1].confirmed
            or self.context_preflight is None
            or self.context_confirmations[-1].binding.inventory
            != inventory_digest(self.context_preflight)
        ):
            raise ValueError("confirmed evidence requires its exact decision")

        if (
            self.preparation_failure is not None
            and type(self.preparation_failure) is not PreparationFailure
        ):
            raise TypeError("preparation failure requires PreparationFailure")
        if (
            self.preparation_infrastructure_failure is not None
            and type(self.preparation_infrastructure_failure) is not SandboxFailure
        ):
            raise TypeError(
                "preparation infrastructure failure requires SandboxFailure"
            )
        if (
            self.preparation_failure is not None
            or self.preparation_infrastructure_failure is not None
        ) and (self.attempts or self.rework_trigger is not None):
            raise ValueError("preparation failure precedes all attempts and rework")
        if len(self.planned_checks) > 8:
            raise ValueError("check evidence exceeds the configured plan")
        if type(self.attempts) is not tuple or len(self.attempts) > MAX_ATTEMPTS:
            raise ValueError("a run has at most two attempts")
        for index, attempt in enumerate(self.attempts, 1):
            if type(attempt) is not AttemptEvidence or attempt.number != index:
                raise ValueError("attempts must be numbered 1 and 2 in order")
            if len(attempt.checks) > len(self.planned_checks) or any(
                record.request != planned
                for record, planned in zip(
                    attempt.checks, self.planned_checks, strict=False
                )
            ):
                raise ValueError("check evidence must follow the configured order")
        if self.rework_trigger is not None and (
            type(self.rework_trigger) is not ReworkTrigger
        ):
            raise TypeError("rework trigger requires ReworkTrigger")
        trigger = self.rework_trigger
        if trigger is None and len(self.attempts) == MAX_ATTEMPTS:
            # Pre-v0.1 evidence: a rework could only follow review #1.
            trigger = ReworkTrigger.REVIEW_CHANGES_REQUIRED
        if trigger is ReworkTrigger.REVIEW_CHANGES_REQUIRED and (
            not self.attempts
            or self.attempts[0].review_decision is not ReviewDecision.CHANGES_REQUIRED
        ):
            raise ValueError("rework requires review #1 to require changes")
        if trigger is ReworkTrigger.CHECK_FINDINGS and not (
            self.attempts
            and self.findings_reworkable_for(1)
            and self.attempts[0].review is None
        ):
            raise ValueError("check rework requires attempt-1 code findings")

    @property
    def latest(self) -> AttemptEvidence:
        return self.attempts[-1] if self.attempts else AttemptEvidence(1)

    @property
    def reworked(self) -> bool:
        return len(self.attempts) == MAX_ATTEMPTS

    def changed_through(self, attempt: int) -> tuple[RepositoryPath, ...]:
        """Paths applied by attempts 1..attempt, in first-application order."""
        paths: list[RepositoryPath] = []
        for item in self.attempts[:attempt]:
            if item.applied is not None:
                for change in item.applied.applied:
                    if change.path not in paths:
                        paths.append(change.path)
        return tuple(paths)

    def gates_passed_for(self, attempt: int) -> bool:
        """Every deterministic gate passed for that attempt's candidate."""
        if not 1 <= attempt <= len(self.attempts):
            return False
        item = self.attempts[attempt - 1]
        return (
            item.applied is not None
            and self.start is not None
            and item.final is not None
            and bool(self.planned_checks)
            and len(item.checks) == len(self.planned_checks)
            and all(record.passed for record in item.checks)
            and item.final.head == self.start.head
            and {entry.path for entry in item.final.entries}
            == set(self.changed_through(attempt))
        )

    def findings_reworkable_for(self, attempt: int) -> bool:
        """The attempt's checks all completed and reported only code findings.

        Every planned check produced a result, at least one did not pass, and
        every one that did not pass is FAILED (the tool completed and reported
        findings). Interrupted, no-tests, error or missing results are
        execution failures, never findings. Git integrity must also hold.
        """
        if not 1 <= attempt <= len(self.attempts):
            return False
        item = self.attempts[attempt - 1]
        results = [record.result for record in item.checks]
        return (
            item.applied is not None
            and self.start is not None
            and item.final is not None
            and bool(self.planned_checks)
            and len(item.checks) == len(self.planned_checks)
            and all(result is not None for result in results)
            and any(not record.passed for record in item.checks)
            and all(
                result.outcome in {CheckOutcome.PASSED, CheckOutcome.FAILED}
                for result in results
                if result is not None
            )
            and item.final.head == self.start.head
            and {entry.path for entry in item.final.entries}
            == set(self.changed_through(attempt))
        )

    @property
    def gates_passed(self) -> bool:
        return self.gates_passed_for(len(self.attempts))

    @property
    def changed_paths(self) -> tuple[RepositoryPath, ...]:
        return self.changed_through(len(self.attempts))

    # Latest-attempt views (ForgeAI-1/2 vocabulary).
    @property
    def coding_status(self) -> CodingStatus | None:
        return self.latest.coding_status

    @property
    def acquisition_failure(self) -> AcquisitionFailure | None:
        return self.latest.acquisition_failure

    @property
    def agent_status(self) -> AgentExecutionStatus | None:
        return self.latest.agent_status

    @property
    def model_effect(self) -> EffectExtent | None:
        return self.latest.model_effect

    @property
    def proposal(self) -> CodingProposal | None:
        return self.latest.proposal

    @property
    def applied(self) -> RepositoryMutationResult | None:
        return self.latest.applied

    @property
    def mutation_denial(self) -> EffectAuthorizationFailure | None:
        return self.latest.mutation_denial

    @property
    def conflict(self) -> MutationConflictReason | None:
        return self.latest.conflict

    @property
    def conflict_path(self) -> RepositoryPath | None:
        return self.latest.conflict_path

    @property
    def uncertain(self) -> RepositoryPath | None:
        return self.latest.uncertain

    @property
    def temporary_paths(self) -> tuple[RepositoryPath, ...]:
        return self.latest.temporary_paths

    @property
    def checks(self) -> tuple[CheckRecord, ...]:
        return self.latest.checks

    @property
    def final(self) -> GitRepositoryState | None:
        return self.latest.final

    @property
    def final_failure(self) -> GitFailure | None:
        return self.latest.final_failure

    @property
    def review_input_failure(self) -> ReviewInputFailure | None:
        return self.latest.review_input_failure

    @property
    def review_materials(self) -> tuple[tuple[str, RepositoryPath], ...]:
        return self.latest.review_materials

    @property
    def review(self) -> ReviewResult | None:
        return self.latest.review

    @property
    def review_decision(self) -> ReviewDecision | None:
        return self.latest.review_decision


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
        for attempt in evidence.attempts:
            if attempt.approval is False and (
                attempt.applied is not None
                or attempt.mutation_denial is not None
                or attempt.conflict is not None
                or attempt.checks
                or attempt.review is not None
            ):
                raise ValueError("a declined proposal has no effect or later step")
        if self.failure is TaskFailure.PROPOSAL_DECLINED and (
            evidence.latest.approval is not False or evidence.latest.proposal is None
        ):
            raise ValueError("a declined run records the declined proposal")
        for number, attempt in enumerate(evidence.attempts, 1):
            reviewed = attempt.review is not None or attempt.review_input_failure
            if reviewed and not evidence.gates_passed_for(number):
                raise ValueError("review evidence requires every deterministic gate")
        if self.disposition is TaskDisposition.SUCCEEDED:
            if self.failure is not None:
                raise ValueError("a successful task carries no failure")
            if not evidence.gates_passed:
                raise ValueError("success requires applied changes and passed checks")
            if (
                evidence.review is None
                or evidence.review.status is not ReviewStatus.COMPLETED
                or evidence.review_decision is not ReviewDecision.ACCEPT
            ):
                raise ValueError("success requires a completed ACCEPT review")
            return
        if type(self.failure) is not TaskFailure:
            raise TypeError("an unsuccessful task requires TaskFailure")
        if self.failure is TaskFailure.REWORK_INPUT_FAILED and (
            len(evidence.attempts) != 1
            or (
                evidence.latest.review_decision is not ReviewDecision.CHANGES_REQUIRED
                and not evidence.findings_reworkable_for(1)
            )
        ):
            raise ValueError("rework input failure follows attempt 1 only")
        if self.disposition is TaskDisposition.REJECTED:
            if self.failure not in _REJECTIONS:
                raise ValueError("disposition does not match the failure step")
            if len(evidence.attempts) > 1 or (
                evidence.agent_status is not None
                or evidence.proposal is not None
                or evidence.applied is not None
                or evidence.checks
            ):
                raise ValueError(
                    "a rejected task cannot carry model or effect evidence"
                )
        elif self.failure in _REJECTIONS and not (
            evidence.reworked
            and self.failure
            in {
                TaskFailure.EVIDENCE_DENIED,
                TaskFailure.EVIDENCE_UNAVAILABLE,
                TaskFailure.CONTEXT_INCOMPLETE,
                TaskFailure.CONTEXT_DECLINED,
                TaskFailure.CONTEXT_STALE,
            }
        ):
            # Pre-effect refusals are REJECTED, except the rework's own reads.
            raise ValueError("disposition does not match the failure step")
