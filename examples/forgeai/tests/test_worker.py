"""B-L, O-Q. RepositoryTaskWorker over the real public host, Git and mutation.

Checks go through the real authorized SandboxedEngineeringChecks with a fake
SandboxExecutionPort; individual Ports are replaced only to inject failures.
"""

import asyncio
import threading
from dataclasses import replace
from pathlib import Path

import pytest
from forgeai_support import (
    FakeSandbox,
    config,
    proposal,
    repository,
    snapshot,
    task,
)
from legoai_engineering.analyst.authorized import REPOSITORY_READ_ACTION
from legoai_engineering.analyst.values import AcquisitionFailure
from legoai_engineering.authorization import EffectAuthorizationFailure
from legoai_engineering.checks.authorized import ENGINEERING_CHECK_ACTION
from legoai_engineering.checks.errors import CheckFailure
from legoai_engineering.checks.values import CheckKind, CheckOutcome
from legoai_engineering.git.errors import GitError, GitFailure
from legoai_engineering.git.values import (
    GitChange,
    GitCommitId,
    GitHead,
    GitHeadKind,
    GitRepositoryState,
    GitStatusEntry,
)
from legoai_engineering.repository.mutation import (
    FileChangeKind,
    FileChangeResult,
    RepositoryChangeSet,
    RepositoryMutationResult,
    digest_text,
)
from legoai_engineering.repository.mutation_authorized import (
    REPOSITORY_MUTATION_ACTION,
)
from legoai_engineering.repository.mutation_errors import (
    MutationApplyError,
    MutationConflict,
    MutationConflictReason,
)
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure

from forgeai.cli import ReplayModel, replay_binding
from forgeai.composition import ForgeAIConfig, PreparedRun, prepare_run
from forgeai.domain import TaskDisposition, TaskFailure, TaskResult
from forgeai.guard import WorkspaceGuard
from forgeai.worker import RepositoryTaskWorker


def prepared(
    cfg: ForgeAIConfig,
    sandbox: FakeSandbox,
    guard: WorkspaceGuard | None = None,
) -> PreparedRun:
    return prepare_run(cfg, guard or WorkspaceGuard(), sandbox=sandbox)


def run(run: PreparedRun, worker: RepositoryTaskWorker | None = None) -> TaskResult:
    return asyncio.run((worker or run.worker).run(task(), run.context))


def execute(
    root: Path,
    output: str | None = None,
    *,
    sandbox: FakeSandbox | None = None,
    **options: object,
) -> tuple[TaskResult, ReplayModel, FakeSandbox]:
    model = ReplayModel(output or proposal())
    sandbox = sandbox or FakeSandbox()
    result = run(prepared(config(root, model, **options), sandbox))  # type: ignore[arg-type]
    return result, model, sandbox


def assert_untouched(root: Path, before: dict[str, bytes]) -> None:
    assert snapshot(root) == before


# --- C/K/L. Success path -----------------------------------------------------


def test_success_applies_once_checks_in_order_and_records_state(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, model, sandbox = execute(root)
    evidence = result.evidence
    assert result.disposition is TaskDisposition.SUCCEEDED and result.failure is None
    assert model.calls == 1 and sandbox.calls == 3
    assert [r.request.kind for r in evidence.checks] == [
        CheckKind.RUFF_CHECK,
        CheckKind.MYPY,
        CheckKind.PYTEST,
    ]
    assert all(
        r.result and r.result.outcome is CheckOutcome.PASSED for r in evidence.checks
    )
    assert [p.value for p in evidence.changed_paths] == [
        "src/inventory/stock.py",
        "tests/test_stock.py",
    ]
    assert evidence.start is not None and evidence.final is not None
    assert evidence.final.head == evidence.start.head
    assert {e.path.value for e in evidence.final.entries} == {
        "src/inventory/stock.py",
        "tests/test_stock.py",
    }
    assert evidence.proposal is not None
    text = (root / "src/inventory/stock.py").read_text(encoding="utf-8")
    assert "requested units exceed available stock" in text
    assert evidence.run_id.startswith("exec-")


# --- B. Clean-start gate -----------------------------------------------------


@pytest.mark.parametrize("change", ["modified", "untracked"])
def test_dirty_start_is_rejected_before_model(tmp_path: Path, change: str) -> None:
    root = repository(tmp_path)
    if change == "modified":
        (root / "tests/test_stock.py").write_text("# local edit\n", encoding="utf-8")
    else:
        (root / "notes.txt").write_text("scratch\n", encoding="utf-8")
    before = snapshot(root)
    result, model, sandbox = execute(root)
    assert result.disposition is TaskDisposition.REJECTED
    assert result.failure is TaskFailure.DIRTY_START
    assert model.calls == 0 and sandbox.calls == 0
    assert_untouched(root, before)


def test_non_repository_and_unborn_head_are_rejected(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "a.py").write_text("x = 1\n", encoding="utf-8")
    result, model, _ = execute(plain)
    assert result.failure is TaskFailure.REPOSITORY_UNAVAILABLE
    assert result.evidence.start_failure is GitFailure.NOT_REPOSITORY
    assert model.calls == 0

    root = repository(tmp_path)
    prepared_run = prepared(config(root, ReplayModel(proposal())), FakeSandbox())
    unborn = GitRepositoryState(GitHead(GitHeadKind.UNBORN, "main", None), ())
    worker = replace(prepared_run.worker, git=StaticGit(unborn))
    result = run(prepared_run, worker)
    assert result.disposition is TaskDisposition.REJECTED
    assert result.failure is TaskFailure.UNSUPPORTED_REPOSITORY


# --- D. Proposal / evidence failures ----------------------------------------


def test_invalid_model_output_stops_before_any_write(tmp_path: Path) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    result, model, sandbox = execute(root, "not a proposal")
    assert result.disposition is TaskDisposition.FAILED
    assert result.failure is TaskFailure.PROPOSAL_INVALID
    assert model.calls == 1 and sandbox.calls == 0
    assert result.evidence.applied is None and result.evidence.proposal is None
    assert_untouched(root, before)


def test_model_denied_is_model_failure_without_provider_call(tmp_path: Path) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    result, model, _ = execute(root, denied=frozenset({"invoke-capability"}))
    assert result.failure is TaskFailure.MODEL_FAILED
    assert model.calls == 0
    assert_untouched(root, before)


def test_read_denial_and_out_of_scope_targets_are_rejected(tmp_path: Path) -> None:
    root = repository(tmp_path)
    for options in (
        {"denied": frozenset({REPOSITORY_READ_ACTION})},
        {"editable": ("src/inventory/stock.py",)},
    ):
        result, model, _ = execute(root, **options)
        assert result.disposition is TaskDisposition.REJECTED
        assert result.failure is TaskFailure.EVIDENCE_DENIED
        assert result.evidence.acquisition_failure is AcquisitionFailure.DENIED
        assert model.calls == 0


def test_oversized_target_is_evidence_unavailable(tmp_path: Path) -> None:
    root = repository(tmp_path)
    prepared_run = prepared(config(root, ReplayModel(proposal())), FakeSandbox())
    (root / "src/inventory/stock.py").write_text("x = 1\n" * 2000, encoding="utf-8")
    start = GitRepositoryState(
        GitHead(GitHeadKind.ATTACHED, "main", GitCommitId("ab" * 20)), ()
    )
    result = run(prepared_run, replace(prepared_run.worker, git=StaticGit(start)))
    assert result.failure is TaskFailure.EVIDENCE_UNAVAILABLE
    assert result.evidence.acquisition_failure is AcquisitionFailure.BUDGET


# --- E/F/J. Mutation ---------------------------------------------------------


def test_denied_mutation_writes_nothing_and_runs_no_checks(tmp_path: Path) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    result, model, sandbox = execute(
        root, denied=frozenset({REPOSITORY_MUTATION_ACTION})
    )
    assert result.disposition is TaskDisposition.FAILED
    assert result.failure is TaskFailure.MUTATION_DENIED
    assert result.evidence.mutation_denial is EffectAuthorizationFailure.DENIED
    assert model.calls == 1 and sandbox.calls == 0
    assert result.evidence.final is not None and result.evidence.final.entries == ()
    assert_untouched(root, before)


class FailingMutation:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    def apply(self, changeset: RepositoryChangeSet) -> RepositoryMutationResult:
        self.calls += 1
        raise self.error


def test_conflict_and_partial_apply_are_reported_without_retry(tmp_path: Path) -> None:
    path = RepositoryPath("src/inventory/stock.py")
    partial = RepositoryMutationResult(
        (
            FileChangeResult(
                path, FileChangeKind.UPDATE, digest_text("a"), digest_text("b")
            ),
        )
    )
    cases = (
        (
            MutationConflict(MutationConflictReason.STALE, path),
            TaskFailure.MUTATION_CONFLICT,
        ),
        (
            MutationApplyError(partial, RepositoryPath("tests/test_stock.py"), ()),
            TaskFailure.MUTATION_PARTIAL,
        ),
    )
    for index, (error, failure) in enumerate(cases):
        root = repository(tmp_path, f"repo{index}")
        sandbox = FakeSandbox()
        prepared_run = prepared(config(root, ReplayModel(proposal())), sandbox)
        mutation = FailingMutation(error)
        result = run(prepared_run, replace(prepared_run.worker, mutation=mutation))
        assert result.failure is failure
        assert mutation.calls == 1 and sandbox.calls == 0
        if failure is TaskFailure.MUTATION_CONFLICT:
            assert result.evidence.conflict is MutationConflictReason.STALE
            assert result.evidence.conflict_path == path
        else:
            assert result.evidence.applied == partial
            assert result.evidence.uncertain == RepositoryPath("tests/test_stock.py")
        assert result.evidence.final is not None


def test_real_stale_precondition_is_a_conflict(tmp_path: Path) -> None:
    root = repository(tmp_path)
    prepared_run = prepared(config(root, ReplayModel(proposal())), FakeSandbox())
    inner = prepared_run.worker.mutation

    class EditThenApply:
        def apply(self, changeset: RepositoryChangeSet) -> RepositoryMutationResult:
            (root / "src/inventory/stock.py").write_text("edited\n", encoding="utf-8")
            return inner.apply(changeset)

    result = run(prepared_run, replace(prepared_run.worker, mutation=EditThenApply()))
    assert result.failure is TaskFailure.MUTATION_CONFLICT
    assert result.evidence.conflict is MutationConflictReason.STALE
    assert (root / "tests/test_stock.py").read_text(encoding="utf-8").count("def ") == 1


# --- G/H/I. Checks -----------------------------------------------------------


def test_check_finding_fails_task_but_keeps_changes_and_runs_all(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    result, _, sandbox = execute(root, sandbox=FakeSandbox((0, 1, 1)))
    assert result.disposition is TaskDisposition.FAILED
    assert result.failure is TaskFailure.CHECKS_FAILED
    assert sandbox.calls == 3
    outcomes = [r.result.outcome for r in result.evidence.checks if r.result]
    assert outcomes == [CheckOutcome.PASSED, CheckOutcome.FAILED, CheckOutcome.FAILED]
    assert result.evidence.applied is not None and result.evidence.final is not None


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        (SandboxFailure.RUNTIME_UNAVAILABLE, CheckFailure.UNAVAILABLE),
        (SandboxFailure.TIMEOUT, CheckFailure.TIMEOUT),
        (SandboxFailure.RESOURCE_LIMIT, CheckFailure.RESOURCE_LIMIT),
        (SandboxFailure.CANCELLED, CheckFailure.CANCELLED),
        (SandboxFailure.UNSUPPORTED, CheckFailure.CONFINEMENT),
    ],
)
def test_sandbox_infrastructure_failure_is_check_error(
    tmp_path: Path, reason: SandboxFailure, expected: CheckFailure
) -> None:
    root = repository(tmp_path)
    sandbox = FakeSandbox(error=SandboxError(reason))
    result, _, _ = execute(root, sandbox=sandbox)
    assert result.failure is TaskFailure.CHECK_ERROR
    assert sandbox.calls == 1
    assert [r.error for r in result.evidence.checks] == [expected]
    assert result.evidence.applied is not None


def test_denied_check_starts_no_sandbox(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, _, sandbox = execute(root, denied=frozenset({ENGINEERING_CHECK_ACTION}))
    assert result.failure is TaskFailure.CHECK_DENIED
    assert sandbox.calls == 0
    assert [r.error for r in result.evidence.checks] == [
        EffectAuthorizationFailure.DENIED
    ]


# --- K/L. Final Git state ----------------------------------------------------


class StaticGit:
    def __init__(self, *states: GitRepositoryState | GitError) -> None:
        self.states = list(states)

    def inspect(self) -> GitRepositoryState:
        state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        if isinstance(state, GitError):
            raise state
        return state


class ThenGit:
    """Real first observation, scripted final observation."""

    def __init__(self, real: object, final: GitRepositoryState | GitError) -> None:
        self.real = real
        self.final = final
        self.calls = 0

    def inspect(self) -> GitRepositoryState:
        self.calls += 1
        if self.calls == 1:
            return self.real.inspect()  # type: ignore[attr-defined,no-any-return]
        if isinstance(self.final, GitError):
            raise self.final
        return self.final


@pytest.mark.parametrize("case", ["head", "extra", "unavailable"])
def test_final_state_integrity(tmp_path: Path, case: str) -> None:
    root = repository(tmp_path)
    prepared_run = prepared(config(root, ReplayModel(proposal())), FakeSandbox())
    real = prepared_run.worker.git
    start = real.inspect()
    assert start.head.commit is not None
    entries = tuple(
        GitStatusEntry(
            RepositoryPath(p), GitChange.UNCHANGED, GitChange.MODIFIED, False
        )
        for p in ("src/inventory/stock.py", "tests/test_stock.py")
    )
    final: GitRepositoryState | GitError
    if case == "head":
        final = GitRepositoryState(
            GitHead(GitHeadKind.ATTACHED, "main", GitCommitId("cd" * 20)), entries
        )
        expected = TaskFailure.HEAD_CHANGED
    elif case == "extra":
        extra = GitStatusEntry(
            RepositoryPath("zz.py"), GitChange.UNCHANGED, GitChange.UNCHANGED, True
        )
        final = GitRepositoryState(start.head, (*entries, extra))
        expected = TaskFailure.UNEXPECTED_CHANGES
    else:
        final = GitError(GitFailure.TIMEOUT)
        expected = TaskFailure.FINAL_STATE_UNAVAILABLE
    result = run(prepared_run, replace(prepared_run.worker, git=ThenGit(real, final)))
    assert result.disposition is TaskDisposition.FAILED
    assert result.failure is expected
    if case == "unavailable":
        assert result.evidence.final_failure is GitFailure.TIMEOUT


# --- O. Configuration / provider substitution --------------------------------


def test_binding_switch_is_configuration_only(tmp_path: Path) -> None:
    first, second = ReplayModel(proposal()), ReplayModel(proposal())
    alternate = replace(replay_binding(second), binding_id="replay-alt")
    for name, model in (("replay", first), ("replay-alt", second)):
        root = repository(tmp_path, name)
        cfg = config(root, first, extra=(alternate,), binding=name)
        result = run(prepared(cfg, FakeSandbox()))
        assert result.disposition is TaskDisposition.SUCCEEDED
        assert model.calls == 1
    assert first.calls == 1 and second.calls == 1


# --- P/Q. Run isolation and same-workspace policy ---------------------------


def test_two_workspaces_run_concurrently_and_stay_isolated(tmp_path: Path) -> None:
    roots = [repository(tmp_path, f"w{index}") for index in range(2)]
    guard = WorkspaceGuard()
    models = [ReplayModel(proposal()) for _ in roots]
    results: dict[int, TaskResult] = {}
    barrier = threading.Barrier(2)

    def worker(index: int) -> None:
        run_ = prepared(config(roots[index], models[index]), FakeSandbox(), guard)
        barrier.wait()
        results[index] = run(run_)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    assert set(results) == {0, 1}
    assert all(r.disposition is TaskDisposition.SUCCEEDED for r in results.values())
    assert results[0].evidence.run_id != results[1].evidence.run_id
    assert [m.calls for m in models] == [1, 1]


def test_same_workspace_second_run_is_refused(tmp_path: Path) -> None:
    root = repository(tmp_path)
    guard = WorkspaceGuard()
    model = ReplayModel(proposal())
    prepared_run = prepared(config(root, model), FakeSandbox(), guard)
    assert guard.acquire(prepared_run.worker.workspace)
    before = snapshot(root)
    result = run(prepared_run)
    assert result.disposition is TaskDisposition.REJECTED
    assert result.failure is TaskFailure.WORKSPACE_BUSY
    assert model.calls == 0
    assert_untouched(root, before)
    guard.release(prepared_run.worker.workspace)
    assert run(prepared_run).disposition is TaskDisposition.SUCCEEDED


def test_guard_is_released_after_every_run(tmp_path: Path) -> None:
    root = repository(tmp_path)
    guard = WorkspaceGuard()
    prepared_run = prepared(config(root, ReplayModel("invalid")), FakeSandbox(), guard)
    assert run(prepared_run).failure is TaskFailure.PROPOSAL_INVALID
    assert guard.acquire(prepared_run.worker.workspace)
