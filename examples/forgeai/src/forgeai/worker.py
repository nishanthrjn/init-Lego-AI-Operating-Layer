"""RepositoryTaskWorker: one fixed, visible sequence per run; no retries.

The worker depends only on public LegoAI Ports, the two Agents and values.
The composition root chooses every adapter. The model proposes once; changes
are applied only through the authorized mutation Port and verified only
through the authorized (sandboxed) check Port. Only a candidate that passed
every deterministic gate is reviewed, once, by the independent reviewer; its
opinion can withhold success but never authorizes, edits or reruns anything.
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
from legoai_engineering.repository.mutation import digest_text
from legoai_engineering.repository.mutation_errors import (
    MutationApplyError,
    MutationConflict,
)
from legoai_engineering.repository.mutation_ports import RepositoryMutationPort
from legoai_engineering.reviewer.api import IndependentReviewer
from legoai_engineering.reviewer.values import (
    ReviewDecision,
    ReviewRequest,
    ReviewStatus,
    SubmissionFailure,
)

from forgeai.domain import (
    CheckRecord,
    ReviewInputFailure,
    TaskDisposition,
    TaskEvidence,
    TaskFailure,
    TaskRequest,
    TaskResult,
)
from forgeai.guard import WorkspaceGuard
from forgeai.review import (
    checks_material,
    file_material,
    material_ids,
    render_proposal,
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
    review_context: Callable[[ExecutionContext], ExecutionContext] = field(repr=False)

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
        if not callable(self.review_context):
            raise TypeError("worker requires a review context factory")

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
        if isinstance(final, GitRepositoryState):
            evidence = replace(evidence, final=final)
        elif isinstance(final, GitError):
            evidence = replace(evidence, final_failure=final.reason)
        return TaskResult(task, TaskDisposition.FAILED, failure, evidence)

    async def _run(
        self, task: TaskRequest, context: ExecutionContext, evidence: TaskEvidence
    ) -> TaskResult:
        # 1-2. Initial Git state; ForgeAI-1 requires a committed, clean start.
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

        # 3-5. Authorized bounded evidence and exactly one Coding Agent call.
        coding = await self.agent.propose(
            CodingRequest(task.objective, task.targets, task.constraints, context)
        )
        evidence = replace(
            evidence,
            coding_status=coding.status,
            acquisition_failure=coding.acquisition_failure,
        )
        if coding.status is CodingStatus.INVALID_REQUEST:
            denied = coding.acquisition_failure is AcquisitionFailure.DENIED
            return _rejected(
                task,
                TaskFailure.EVIDENCE_DENIED
                if denied
                else TaskFailure.EVIDENCE_UNAVAILABLE,
                evidence,
            )
        agent = coding.agent_result
        assert agent is not None
        evidence = replace(
            evidence,
            agent_status=agent.status,
            model_effect=(
                agent.model_execution.effect
                if agent.model_execution is not None
                else None
            ),
        )
        if coding.status is not CodingStatus.SUCCEEDED or coding.proposal is None:
            failure = (
                TaskFailure.PROPOSAL_INVALID
                if coding.status is CodingStatus.OUTPUT_INVALID
                else TaskFailure.MODEL_FAILED
            )
            return self._stop(task, failure, evidence)
        evidence = replace(evidence, proposal=coding.proposal)

        # 6. Apply through the authorized mutation Port; never retried.
        try:
            applied = self.mutation.apply(coding.proposal.changeset)
        except EffectAuthorizationError as error:
            return self._finish(
                task,
                TaskFailure.MUTATION_DENIED,
                replace(evidence, mutation_denial=error.reason),
            )
        except MutationConflict as error:
            return self._finish(
                task,
                TaskFailure.MUTATION_CONFLICT,
                replace(evidence, conflict=error.reason, conflict_path=error.path),
            )
        except MutationApplyError as error:
            return self._finish(
                task,
                TaskFailure.MUTATION_PARTIAL,
                replace(
                    evidence,
                    applied=error.completed,
                    uncertain=error.uncertain,
                    temporary_paths=error.temporary_paths,
                ),
            )
        evidence = replace(evidence, applied=applied)

        # 7. Configured checks, in order, through the authorized Port. Findings
        # are results and later checks still run; any failure to run stops.
        records: list[CheckRecord] = []
        for request in self.check_plan:
            try:
                result = self.checks.check(request)
            except EffectAuthorizationError as error:
                records.append(CheckRecord(request, None, error.reason))
                evidence = replace(evidence, checks=tuple(records))
                return self._finish(task, TaskFailure.CHECK_DENIED, evidence)
            except CheckError as error:
                records.append(CheckRecord(request, None, error.reason))
                evidence = replace(evidence, checks=tuple(records))
                return self._finish(task, TaskFailure.CHECK_ERROR, evidence)
            except WorkspaceError:
                records.append(CheckRecord(request, None, workspace_error=True))
                evidence = replace(evidence, checks=tuple(records))
                return self._finish(task, TaskFailure.CHECK_ERROR, evidence)
            records.append(CheckRecord(request, result))
        evidence = replace(evidence, checks=tuple(records))

        # 8. Final Git state: HEAD must be unchanged and only applied paths differ.
        final = self._observe()
        if not isinstance(final, GitRepositoryState):
            observed = final.reason if isinstance(final, GitError) else None
            return self._stop(
                task,
                TaskFailure.FINAL_STATE_UNAVAILABLE,
                replace(evidence, final_failure=observed),
            )
        evidence = replace(evidence, final=final)
        if final.head != start.head:
            return self._stop(task, TaskFailure.HEAD_CHANGED, evidence)
        if {entry.path for entry in final.entries} != set(evidence.changed_paths):
            return self._stop(task, TaskFailure.UNEXPECTED_CHANGES, evidence)
        if any(
            record.result is None or record.result.outcome is not CheckOutcome.PASSED
            for record in records
        ):
            return self._stop(task, TaskFailure.CHECKS_FAILED, evidence)
        # 9. Independent review, only after every deterministic gate passed.
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
    ) -> TaskResult:
        materials = material_ids(evidence.changed_paths)
        evidence = replace(evidence, review_materials=materials)
        # Final applied contents, through the same authorized read boundary.
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
            return self._stop(
                task,
                TaskFailure.REVIEW_INPUT_FAILED,
                replace(evidence, review_input_failure=reason),
            )
        texts = {file.path: file.text for file in read.files}
        assert evidence.applied is not None
        if any(
            change.after is not None
            and digest_text(texts.get(change.path.value, "")) != change.after
            for change in evidence.applied.applied
        ):
            # The reviewed text must be exactly the applied text.
            return self._stop(task, TaskFailure.UNEXPECTED_CHANGES, evidence)
        try:
            proposal_text = render_proposal(proposal, materials)
            supporting = (
                checks_material(evidence.checks),
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
            return self._stop(
                task,
                TaskFailure.REVIEW_INPUT_FAILED,
                replace(
                    evidence, review_input_failure=ReviewInputFailure.MATERIAL_BOUNDS
                ),
            )
        # A fresh governed Chat execution; the Coding context is never reused.
        try:
            review_context = self.review_context(context)
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
        evidence = replace(evidence, review=result)
        if result.status is ReviewStatus.INVALID_SUBMISSION:
            budget = result.submission_failure is SubmissionFailure.CONTEXT_BUDGET
            reason = (
                ReviewInputFailure.CONTEXT_BUDGET
                if budget
                else ReviewInputFailure.MATERIAL_BOUNDS
            )
            return self._stop(
                task,
                TaskFailure.REVIEW_INPUT_FAILED,
                replace(evidence, review_input_failure=reason),
            )
        if result.status is ReviewStatus.MODEL_FAILURE:
            return self._stop(task, TaskFailure.REVIEW_FAILED, evidence)
        if result.status is ReviewStatus.OUTPUT_INVALID:
            return self._stop(task, TaskFailure.REVIEW_OUTPUT_INVALID, evidence)
        decision = evidence.review_decision
        if decision is ReviewDecision.CHANGES_REQUIRED:
            return self._stop(task, TaskFailure.REVIEW_CHANGES_REQUIRED, evidence)
        if decision is ReviewDecision.INSUFFICIENT_EVIDENCE:
            return self._stop(task, TaskFailure.REVIEW_INSUFFICIENT_EVIDENCE, evidence)
        # 10. Success: every deterministic gate passed and the review accepted.
        return TaskResult(task, TaskDisposition.SUCCEEDED, None, evidence)


def _rejected(
    task: TaskRequest, failure: TaskFailure, evidence: TaskEvidence
) -> TaskResult:
    return TaskResult(task, TaskDisposition.REJECTED, failure, evidence)
