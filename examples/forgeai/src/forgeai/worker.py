"""RepositoryTaskWorker: one fixed, visible sequence per run; no retries.

The worker depends only on public LegoAI Ports, the Coding Agent and values.
The composition root chooses every adapter. The model proposes once; changes
are applied only through the authorized mutation Port and verified only
through the authorized (sandboxed) check Port.
"""

from dataclasses import dataclass, field, replace

from legoai.execution.values import ExecutionContext
from legoai_engineering.analyst.values import AcquisitionFailure
from legoai_engineering.authorization import EffectAuthorizationError
from legoai_engineering.checks.errors import CheckError
from legoai_engineering.checks.ports import EngineeringCheckPort
from legoai_engineering.checks.values import CheckOutcome, CheckRequest
from legoai_engineering.coding.api import CodingAgent
from legoai_engineering.coding.values import CodingRequest, CodingStatus
from legoai_engineering.git.errors import GitError
from legoai_engineering.git.ports import GitRepositoryPort
from legoai_engineering.git.values import GitRepositoryState
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.mutation_errors import (
    MutationApplyError,
    MutationConflict,
)
from legoai_engineering.repository.mutation_ports import RepositoryMutationPort

from forgeai.domain import (
    CheckRecord,
    TaskDisposition,
    TaskEvidence,
    TaskFailure,
    TaskRequest,
    TaskResult,
)
from forgeai.guard import WorkspaceGuard


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
        # 9. Success: applied, every configured check passed, HEAD intact.
        return TaskResult(task, TaskDisposition.SUCCEEDED, None, evidence)


def _rejected(
    task: TaskRequest, failure: TaskFailure, evidence: TaskEvidence
) -> TaskResult:
    return TaskResult(task, TaskDisposition.REJECTED, failure, evidence)
