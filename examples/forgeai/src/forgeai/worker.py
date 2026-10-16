"""RepositoryTaskWorker: one fixed, visible sequence per run; no retries.

The worker depends only on public LegoAI Ports, the two Agents and values.
The composition root chooses every adapter. An attempt is: one Coding Agent
proposal, authorized application, the configured sandboxed checks, a Git
integrity check and, only if every deterministic gate passed, one independent
review. A run has attempt 1 and at most one rework attempt 2, which is
terminal. The single rework budget is consumed by exactly one trigger: the
attempt-1 checks completed and reported only code findings (no review of that
candidate), or review #1 completed with CHANGES_REQUIRED. Check execution
failures never trigger a rework. There is no loop: at most 2 proposals, 2
applies, 2 check batches and 2 reviews.
Review findings reach the Coding Agent only as bounded labeled text; they
never authorize, patch, apply or rerun anything themselves.

Every validated proposal is shown to the operator before mutation. Only an
OperatorDecision that approves the exact proposal identity lets it be applied;
a decline, a mismatched identity, a wrong type or an approver error writes
nothing and runs no check or review. Model output can never approve itself:
the decision comes only from the composition root's approver.
"""

from collections.abc import Callable
from dataclasses import dataclass, field, replace

from legoai.execution.agent.values import AgentId
from legoai.execution.values import ExecutionContext
from legoai.runtime.api import HostError
from legoai_engineering.analyst.api import RepositoryEvidencePort
from legoai_engineering.analyst.values import (
    AcquisitionFailure,
    EvidenceAcquisitionError,
)
from legoai_engineering.authorization import EffectAuthorizationError
from legoai_engineering.checks.errors import CheckError
from legoai_engineering.checks.ports import EngineeringCheckPort
from legoai_engineering.checks.values import CheckOutcome, CheckRequest
from legoai_engineering.coding.api import CodingAgent
from legoai_engineering.coding.values import (
    CodingProposal,
    CodingRequest,
    CodingStatus,
)
from legoai_engineering.git.errors import GitError
from legoai_engineering.git.ports import GitRepositoryPort
from legoai_engineering.git.values import GitRepositoryState
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.mutation import ContentDigest, digest_text
from legoai_engineering.repository.mutation_errors import (
    MutationApplyError,
    MutationConflict,
)
from legoai_engineering.repository.mutation_ports import RepositoryMutationPort
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.reviewer.api import IndependentReviewer
from legoai_engineering.reviewer.values import (
    ReviewDecision,
    ReviewRequest,
    ReviewStatus,
    SubmissionFailure,
)
from legoai_engineering.sandbox.errors import SandboxError
from legoai_engineering.sandbox.prepared import PreparationError

from forgeai.domain import (
    AttemptEvidence,
    CheckRecord,
    OperatorDecision,
    ProposalReview,
    ReviewInputFailure,
    ReworkTrigger,
    RunStage,
    TaskDisposition,
    TaskEvidence,
    TaskFailure,
    TaskRequest,
    TaskResult,
    proposal_identity,
)
from forgeai.guard import WorkspaceGuard
from forgeai.repository_context import (
    ContextOutcome,
    ContextPreflight,
    ContextReason,
    preflight_context,
)
from forgeai.review import (
    check_rework_constraints,
    checks_material,
    file_material,
    material_ids,
    render_proposal,
    rework_constraints,
    rework_targets,
)


@dataclass(frozen=True, slots=True)
class RepositoryTaskWorker:
    """Bound to exactly one workspace for its lifetime; holds no run state."""

    workspace: str
    guard: WorkspaceGuard = field(repr=False)
    git: GitRepositoryPort = field(repr=False)
    agent: CodingAgent = field(repr=False)
    mutation: RepositoryMutationPort = field(repr=False)
    checks: EngineeringCheckPort = field(repr=False)
    check_plan: tuple[CheckRequest, ...]
    reviewer: IndependentReviewer = field(repr=False)
    reader: RepositoryEvidencePort = field(repr=False)
    review_criteria: tuple[str, ...]
    fresh_context: Callable[[ExecutionContext], ExecutionContext] = field(repr=False)
    approve: Callable[[ProposalReview], OperatorDecision] = field(repr=False)
    progress: Callable[[RunStage, int], None] = field(
        default=lambda stage, attempt: None, repr=False
    )
    prepare_checks: Callable[[], EngineeringCheckPort] | None = field(
        default=None, repr=False
    )
    admit_model: Callable[[TaskRequest], bool] | None = field(default=None, repr=False)

    confirm_context: Callable[[ContextPreflight], bool] | None = field(
        default=None, repr=False
    )

    def __post_init__(self) -> None:
        if type(self.workspace) is not str or not self.workspace:
            raise TypeError("worker requires a workspace key")
        if type(self.guard) is not WorkspaceGuard:
            raise TypeError("worker requires WorkspaceGuard")
        if type(self.agent) is not CodingAgent:
            raise TypeError("worker requires CodingAgent")
        for port, method in (
            (self.git, "inspect"),
            (self.mutation, "apply"),
            (self.checks, "check"),
        ):
            if not callable(getattr(port, method, None)):
                raise TypeError(f"worker requires a Port providing {method}")
        if (
            type(self.check_plan) is not tuple
            or not 1 <= len(self.check_plan) <= 8
            or any(type(item) is not CheckRequest for item in self.check_plan)
        ):
            raise ValueError("worker requires one to eight configured checks")
        if type(self.reviewer) is not IndependentReviewer:
            raise TypeError("worker requires IndependentReviewer")
        if not callable(getattr(self.reader, "acquire", None)):
            raise TypeError("worker requires a RepositoryEvidencePort")
        if (
            type(self.review_criteria) is not tuple
            or not 1 <= len(self.review_criteria) <= 8
            or any(type(item) is not str for item in self.review_criteria)
        ):
            raise ValueError("worker requires one to eight review criteria")
        if not callable(self.fresh_context):
            raise TypeError("worker requires a fresh Chat context factory")
        if not callable(self.approve) or not callable(self.progress):
            raise TypeError("worker requires an operator approver and progress")
        if self.prepare_checks is not None and not callable(self.prepare_checks):
            raise TypeError("preparation must be a trusted composition callback")
        if self.confirm_context is not None and not callable(self.confirm_context):
            raise TypeError("context confirmation must be a trusted callback")
        if self.admit_model is not None and not callable(self.admit_model):
            raise TypeError("model admission must be a trusted composition callback")

    async def run(self, task: TaskRequest, context: ExecutionContext) -> TaskResult:
        if type(task) is not TaskRequest:
            raise TypeError("worker requires TaskRequest")
        if type(context) is not ExecutionContext:
            raise TypeError("worker requires ExecutionContext")
        evidence = TaskEvidence(
            context.execution_id.value, planned_checks=self.check_plan
        )
        if not self.guard.acquire(self.workspace):
            return _rejected(task, TaskFailure.WORKSPACE_BUSY, evidence)
        try:
            # The guard is held for the whole run, including any rework.
            return await self._run(task, context, evidence)
        finally:
            self.guard.release(self.workspace)

    @staticmethod
    def _stop(
        task: TaskRequest, failure: TaskFailure, evidence: TaskEvidence
    ) -> TaskResult:
        return TaskResult(task, TaskDisposition.FAILED, failure, evidence)

    def _observe(self) -> GitRepositoryState | GitError | WorkspaceError:
        try:
            return self.git.inspect()
        except (GitError, WorkspaceError) as error:
            return error

    def _finish(
        self, task: TaskRequest, failure: TaskFailure, evidence: TaskEvidence
    ) -> TaskResult:
        # After an effect, observe the final state (read-only) before stopping.
        final = self._observe()
        item = evidence.latest
        if isinstance(final, GitRepositoryState):
            item = replace(item, final=final)
        elif isinstance(final, GitError):
            item = replace(item, final_failure=final.reason)
        return self._stop(task, failure, _set(evidence, item))

    async def _run(
        self, task: TaskRequest, context: ExecutionContext, evidence: TaskEvidence
    ) -> TaskResult:
        # Initial Git state; a run requires a committed, clean start.
        start = self._observe()
        if not isinstance(start, GitRepositoryState):
            observed = start.reason if isinstance(start, GitError) else None
            return _rejected(
                task,
                TaskFailure.REPOSITORY_UNAVAILABLE,
                replace(evidence, start_failure=observed),
            )
        evidence = replace(evidence, start=start)
        if start.head.commit is None:
            return _rejected(task, TaskFailure.UNSUPPORTED_REPOSITORY, evidence)
        if start.entries:
            return _rejected(task, TaskFailure.DIRTY_START, evidence)
        self.progress(RunStage.REPOSITORY_VERIFIED, 0)
        request = CodingRequest(
            task.objective, task.targets, task.constraints, context, task.context
        )
        inventory = await preflight_context(self.agent.evidence_reader, request)
        evidence = replace(evidence, context_preflight=inventory)
        if inventory.outcome is ContextOutcome.CONTEXT_INCOMPLETE:
            if inventory.reason is ContextReason.DENIED:
                failure = TaskFailure.EVIDENCE_DENIED
            elif inventory.reason in {
                ContextReason.ACQUISITION_FAILED,
                ContextReason.EVIDENCE_MISMATCH,
            }:
                failure = TaskFailure.CONTEXT_PREFLIGHT_FAILED
            else:
                failure = TaskFailure.CONTEXT_INCOMPLETE
            return _rejected(task, failure, evidence)
        try:
            confirmed = (
                self.confirm_context is not None
                and self.confirm_context(inventory) is True
            )
        except (Exception, KeyboardInterrupt):
            confirmed = False
        if not confirmed:
            return _rejected(task, TaskFailure.CONTEXT_DECLINED, evidence)
        evidence = replace(evidence, context_confirmed=True)

        worker = self
        if self.prepare_checks is not None:
            try:
                worker = replace(
                    self, checks=self.prepare_checks(), prepare_checks=None
                )
            except PreparationError as error:
                return _rejected(
                    task,
                    TaskFailure.CHECK_ENVIRONMENT_UNAVAILABLE,
                    replace(evidence, preparation_failure=error.reason),
                )
            except SandboxError as error:
                return _rejected(
                    task,
                    TaskFailure.CHECK_ENVIRONMENT_UNAVAILABLE,
                    replace(evidence, preparation_infrastructure_failure=error.reason),
                )
            # Preparation must not change the source checkout or anchor.
            after = self._observe()
            if not isinstance(after, GitRepositoryState) or after != start:
                return _rejected(task, TaskFailure.REPOSITORY_UNAVAILABLE, evidence)
        if self.admit_model is not None and not self.admit_model(task):
            return _rejected(task, TaskFailure.MODEL_DISCLOSURE_REFUSED, evidence)
        first = await worker._attempt(
            task,
            CodingRequest(
                task.objective, task.targets, task.constraints, context, task.context
            ),
            context,
            evidence,
        )
        if isinstance(first, TaskResult):
            return first
        # Attempt 1 consumed the single rework budget (check findings or
        # review #1 CHANGES_REQUIRED): exactly one rework.
        return await worker._rework(task, context, first)

    async def _rework(
        self, task: TaskRequest, context: ExecutionContext, evidence: TaskEvidence
    ) -> TaskResult:
        trigger = evidence.rework_trigger
        assert trigger is not None
        try:
            # Same scope, objective and operator-selected read-only context;
            # current content is re-read by the Coding Agent's authorized
            # evidence reader, never reused. Feedback is text only: it can
            # never add a target or a context file.
            targets = rework_targets(task.targets, evidence.changed_paths)
            if trigger is ReworkTrigger.CHECK_FINDINGS:
                constraints = check_rework_constraints(
                    task.constraints, evidence.latest.checks
                )
            else:
                review = evidence.latest.review
                assert review is not None and review.review is not None
                constraints = rework_constraints(
                    task.constraints, review.review, evidence.latest.checks
                )
            CodingRequest(task.objective, targets, constraints, context, task.context)
        except ValueError:
            return self._stop(task, TaskFailure.REWORK_INPUT_FAILED, evidence)
        try:
            rework_context = self.fresh_context(context)
        except HostError:
            reworked = replace(
                evidence, attempts=(*evidence.attempts, AttemptEvidence(2))
            )
            return self._stop(task, TaskFailure.MODEL_FAILED, reworked)
        self.progress(
            RunStage.CHECK_REWORK_STARTED
            if trigger is ReworkTrigger.CHECK_FINDINGS
            else RunStage.REWORK_STARTED,
            2,
        )
        second = await self._attempt(
            task,
            CodingRequest(
                task.objective, targets, constraints, rework_context, task.context
            ),
            context,
            evidence,
        )
        # Attempt 2 is terminal by construction: it never returns evidence.
        assert isinstance(second, TaskResult)
        return second

    async def _attempt(
        self,
        task: TaskRequest,
        request: CodingRequest,
        context: ExecutionContext,
        evidence: TaskEvidence,
    ) -> TaskResult | TaskEvidence:
        """One attempt. Returns evidence (not a result) only when this is
        attempt 1 and it consumed the rework budget: its checks reported only
        code findings, or its review completed with CHANGES_REQUIRED."""
        number = len(evidence.attempts) + 1
        evidence = replace(
            evidence, attempts=(*evidence.attempts, AttemptEvidence(number))
        )
        start = evidence.start
        assert start is not None
        coding = await self.agent.propose(request)
        item = replace(
            evidence.latest,
            coding_status=coding.status,
            acquisition_failure=coding.acquisition_failure,
        )
        evidence = _set(evidence, item)
        if coding.status is CodingStatus.INVALID_REQUEST:
            denied = coding.acquisition_failure is AcquisitionFailure.DENIED
            failure = (
                TaskFailure.EVIDENCE_DENIED
                if denied
                else TaskFailure.EVIDENCE_UNAVAILABLE
            )
            if number == 1:
                return _rejected(task, failure, evidence)
            return self._stop(task, failure, evidence)
        agent = coding.agent_result
        assert agent is not None
        item = replace(
            item,
            agent_status=agent.status,
            coding_diagnostic=coding.diagnostic,
            model_effect=(
                agent.model_execution.effect
                if agent.model_execution is not None
                else None
            ),
        )
        evidence = _set(evidence, item)
        if coding.status is not CodingStatus.SUCCEEDED or coding.proposal is None:
            failure = (
                TaskFailure.PROPOSAL_INVALID
                if coding.status is CodingStatus.OUTPUT_INVALID
                else TaskFailure.MODEL_FAILED
            )
            return self._stop(task, failure, evidence)
        item = replace(item, proposal=coding.proposal)
        evidence = _set(evidence, item)
        self.progress(RunStage.PROPOSAL_GENERATED, number)

        # Operator approval of this exact proposal before any effect.
        identity = proposal_identity(coding.proposal)
        assert coding.evidence is not None
        current = {
            file.target.path: file.current.text if file.current else None
            for file in coding.evidence.files
        }
        before = tuple(
            current[change.path] for change in coding.proposal.changeset.changes
        )
        self.progress(RunStage.AWAITING_APPROVAL, number)
        try:
            review = ProposalReview(
                number,
                coding.proposal,
                identity,
                before,
                evidence.rework_trigger if number == 2 else None,
                request.constraints[len(task.constraints) :] if number == 2 else (),
            )
            decision = self.approve(review)
        except Exception:
            decision = None  # an approver failure never approves
        approved = (
            type(decision) is OperatorDecision
            and decision.approved is True
            and decision.identity == identity
        )
        item = replace(item, approval=approved)
        evidence = _set(evidence, item)
        if not approved:
            return self._stop(task, TaskFailure.PROPOSAL_DECLINED, evidence)

        # Apply through the authorized mutation Port; never retried.
        try:
            applied = self.mutation.apply(coding.proposal.changeset)
        except EffectAuthorizationError as error:
            item = replace(item, mutation_denial=error.reason)
            return self._finish(task, TaskFailure.MUTATION_DENIED, _set(evidence, item))
        except MutationConflict as error:
            item = replace(item, conflict=error.reason, conflict_path=error.path)
            return self._finish(
                task, TaskFailure.MUTATION_CONFLICT, _set(evidence, item)
            )
        except MutationApplyError as error:
            item = replace(
                item,
                applied=error.completed,
                uncertain=error.uncertain,
                temporary_paths=error.temporary_paths,
            )
            return self._finish(
                task, TaskFailure.MUTATION_PARTIAL, _set(evidence, item)
            )
        item = replace(item, applied=applied)
        evidence = _set(evidence, item)
        self.progress(RunStage.CHANGES_APPLIED, number)

        # Configured checks, in order, through the authorized Port. Findings
        # are results and later checks still run; any failure to run stops.
        records: list[CheckRecord] = []
        for check in self.check_plan:
            try:
                result = self.checks.check(check)
            except EffectAuthorizationError as error:
                records.append(CheckRecord(check, None, error.reason))
                item = replace(item, checks=tuple(records))
                return self._finish(
                    task, TaskFailure.CHECK_DENIED, _set(evidence, item)
                )
            except CheckError as error:
                records.append(CheckRecord(check, None, error.reason))
                item = replace(item, checks=tuple(records))
                return self._finish(task, TaskFailure.CHECK_ERROR, _set(evidence, item))
            except WorkspaceError:
                records.append(CheckRecord(check, None, workspace_error=True))
                item = replace(item, checks=tuple(records))
                return self._finish(task, TaskFailure.CHECK_ERROR, _set(evidence, item))
            records.append(CheckRecord(check, result))
        item = replace(item, checks=tuple(records))
        evidence = _set(evidence, item)
        self.progress(RunStage.CHECKS_COMPLETED, number)

        # Git integrity: HEAD unchanged and only this run's applied paths differ.
        final = self._observe()
        if not isinstance(final, GitRepositoryState):
            observed = final.reason if isinstance(final, GitError) else None
            item = replace(item, final_failure=observed)
            return self._stop(
                task, TaskFailure.FINAL_STATE_UNAVAILABLE, _set(evidence, item)
            )
        item = replace(item, final=final)
        evidence = _set(evidence, item)
        if final.head != start.head:
            return self._stop(task, TaskFailure.HEAD_CHANGED, evidence)
        if {entry.path for entry in final.entries} != set(evidence.changed_paths):
            return self._stop(task, TaskFailure.UNEXPECTED_CHANGES, evidence)
        if any(
            record.result is None or record.result.outcome is not CheckOutcome.PASSED
            for record in records
        ):
            if number == 1 and evidence.findings_reworkable_for(1):
                # Code findings, not an execution failure: the single rework.
                return replace(evidence, rework_trigger=ReworkTrigger.CHECK_FINDINGS)
            return self._stop(task, TaskFailure.CHECKS_FAILED, evidence)
        # Independent review, only after every deterministic gate passed.
        assert evidence.gates_passed
        return await self._review(
            task, context, coding.proposal, agent.definition.agent_id, evidence
        )

    async def _review(
        self,
        task: TaskRequest,
        context: ExecutionContext,
        proposal: CodingProposal,
        producer: AgentId,
        evidence: TaskEvidence,
    ) -> TaskResult | TaskEvidence:
        number = len(evidence.attempts)
        materials = material_ids(evidence.changed_paths)
        item = replace(evidence.latest, review_materials=materials)
        evidence = _set(evidence, item)
        # Final contents of every file changed in this run, through the same
        # authorized read boundary.
        try:
            read = await self.reader.acquire(
                tuple(path for _, path in materials), context.tenant_context
            )
        except EvidenceAcquisitionError as error:
            reason = (
                ReviewInputFailure.READ_DENIED
                if error.reason is AcquisitionFailure.DENIED
                else ReviewInputFailure.READ_UNAVAILABLE
            )
            item = replace(item, review_input_failure=reason)
            return self._stop(
                task, TaskFailure.REVIEW_INPUT_FAILED, _set(evidence, item)
            )
        texts = {file.path: file.text for file in read.files}
        expected: dict[RepositoryPath, ContentDigest | None] = {}
        for attempt in evidence.attempts:
            if attempt.applied is not None:
                for change in attempt.applied.applied:
                    expected[change.path] = change.after
        if any(
            digest is not None and digest_text(texts.get(path.value, "")) != digest
            for path, digest in expected.items()
        ):
            # The reviewed text must be exactly the applied text.
            return self._stop(task, TaskFailure.UNEXPECTED_CHANGES, evidence)
        try:
            proposal_text = render_proposal(
                proposal, materials, number, evidence.rework_trigger
            )
            supporting = (
                checks_material(item.checks),
                *(
                    file_material(material, path, texts[path.value])
                    for material, path in materials
                ),
            )
            # Validate the full request before any context is minted.
            ReviewRequest(
                producer,
                task.objective,
                self.review_criteria,
                proposal_text,
                supporting,
                context,
            )
        except ValueError:
            item = replace(
                item, review_input_failure=ReviewInputFailure.MATERIAL_BOUNDS
            )
            return self._stop(
                task, TaskFailure.REVIEW_INPUT_FAILED, _set(evidence, item)
            )
        # A fresh governed Chat execution; no earlier context is reused.
        try:
            review_context = self.fresh_context(context)
        except HostError:
            return self._stop(task, TaskFailure.REVIEW_FAILED, evidence)
        result = await self.reviewer.review(
            ReviewRequest(
                producer,
                task.objective,
                self.review_criteria,
                proposal_text,
                supporting,
                review_context,
            )
        )
        item = replace(item, review=result)
        evidence = _set(evidence, item)
        self.progress(RunStage.REVIEW_COMPLETED, number)
        if result.status is ReviewStatus.INVALID_SUBMISSION:
            budget = result.submission_failure is SubmissionFailure.CONTEXT_BUDGET
            reason = (
                ReviewInputFailure.CONTEXT_BUDGET
                if budget
                else ReviewInputFailure.MATERIAL_BOUNDS
            )
            item = replace(item, review_input_failure=reason)
            return self._stop(
                task, TaskFailure.REVIEW_INPUT_FAILED, _set(evidence, item)
            )
        if result.status is ReviewStatus.MODEL_FAILURE:
            return self._stop(task, TaskFailure.REVIEW_FAILED, evidence)
        if result.status is ReviewStatus.OUTPUT_INVALID:
            return self._stop(task, TaskFailure.REVIEW_OUTPUT_INVALID, evidence)
        decision = evidence.review_decision
        if decision is ReviewDecision.CHANGES_REQUIRED:
            if number == 1:
                # The caller may start the single rework.
                return replace(
                    evidence, rework_trigger=ReworkTrigger.REVIEW_CHANGES_REQUIRED
                )
            return self._stop(task, TaskFailure.REVIEW_CHANGES_REQUIRED, evidence)
        if decision is ReviewDecision.INSUFFICIENT_EVIDENCE:
            return self._stop(task, TaskFailure.REVIEW_INSUFFICIENT_EVIDENCE, evidence)
        # Success: every deterministic gate passed and the review accepted.
        return TaskResult(task, TaskDisposition.SUCCEEDED, None, evidence)


def _set(evidence: TaskEvidence, item: AttemptEvidence) -> TaskEvidence:
    """Replace the latest attempt's record."""
    return replace(evidence, attempts=(*evidence.attempts[:-1], item))


def _rejected(
    task: TaskRequest, failure: TaskFailure, evidence: TaskEvidence
) -> TaskResult:
    return TaskResult(task, TaskDisposition.REJECTED, failure, evidence)
