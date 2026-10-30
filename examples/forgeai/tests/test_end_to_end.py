"""Full offline fixture task with the real Docker sandbox (no network model).

Public host -> replay ModelPort contribution -> Coding Agent -> authorized
mutation -> authorized SandboxedEngineeringChecks on the qualified image ->
Git -> replay IndependentReviewer (ACCEPT) -> TaskResult. Windows + Docker Desktop reference scope; fails, never
skips, when Docker is missing there.
"""

import asyncio
import json
import os
import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    REVIEW_CHANGES,
    REWORK,
    approve,
    config,
    proposal,
    replay,
    repository,
    task,
)
from legoai_engineering.checks.errors import CheckFailure
from legoai_engineering.checks.values import CheckKind, CheckOutcome
from legoai_engineering.repository.mutation import (
    RepositoryChangeSet,
    RepositoryMutationResult,
)
from legoai_engineering.repository.mutation_ports import RepositoryMutationPort
from legoai_engineering.reviewer.values import ReviewDecision, ReviewStatus
from legoai_engineering.sandbox.docker import (
    DockerSandbox,
    DockerSandboxConfig,
    SandboxImage,
)
from legoai_engineering.sandbox.ports import CancellationSignal
from legoai_engineering.sandbox.values import (
    SandboxRequest,
    SandboxResult,
)

from forgeai.cli import ReplayModel
from forgeai.composition import ForgeAIConfig, prepare_run
from forgeai.domain import ReworkTrigger, TaskDisposition, TaskFailure, TaskResult
from forgeai.guard import WorkspaceGuard

pytestmark = pytest.mark.skipif(
    os.name != "nt", reason="Windows Desktop reference scope"
)


def docker() -> Path:
    executable = shutil.which("docker")
    assert executable is not None, "ForgeAI Docker tests require Docker; no skip"
    return Path(executable)


class CountingSandbox:
    def __init__(self, inner: DockerSandbox) -> None:
        self.inner = inner
        self.calls = 0

    def execute(
        self, request: SandboxRequest, cancellation: CancellationSignal | None = None
    ) -> SandboxResult:
        self.calls += 1
        return self.inner.execute(request, cancellation)


class CountingMutation:
    def __init__(self, inner: RepositoryMutationPort) -> None:
        self.inner = inner
        self.calls = 0

    def apply(self, changeset: RepositoryChangeSet) -> RepositoryMutationResult:
        self.calls += 1
        return self.inner.apply(changeset)


def run(
    cfg: ForgeAIConfig,
) -> tuple[TaskResult, CountingSandbox, CountingMutation]:
    sandbox = CountingSandbox(
        DockerSandbox(
            DockerSandboxConfig(cfg.docker_executable, SandboxImage.PYTHON_CHECKS),
            cfg.sandbox_policy,
        )
    )
    prepared = prepare_run(
        cfg,
        WorkspaceGuard(),
        confirm_context=lambda inventory: True,
        approve=approve,
        sandbox=sandbox,
    )
    mutation = CountingMutation(prepared.worker.mutation)
    worker = replace(prepared.worker, mutation=mutation)
    return asyncio.run(worker.run(task(), prepared.context)), sandbox, mutation


def test_fixture_task_succeeds_in_the_real_sandbox(tmp_path: Path) -> None:
    root = repository(tmp_path)
    model = replay()
    result, sandbox, mutation = run(config(root, model, docker=docker()))
    evidence = result.evidence
    assert result.disposition is TaskDisposition.SUCCEEDED, result
    assert model.calls == 2 and mutation.calls == 1 and sandbox.calls == 3
    assert [r.request.kind for r in evidence.checks] == [
        CheckKind.RUFF_CHECK,
        CheckKind.MYPY,
        CheckKind.PYTEST,
    ]
    assert all(
        r.result and r.result.outcome is CheckOutcome.PASSED for r in evidence.checks
    )
    assert evidence.start is not None and evidence.final is not None
    assert evidence.final.head == evidence.start.head
    assert evidence.proposal is not None
    for change in evidence.proposal.changeset.changes:
        assert (root / change.path.value).read_bytes().decode("utf-8") == change.text
    assert not list(root.rglob("__pycache__")), "checks must not run on the host"
    review = evidence.review
    assert review is not None and review.status is ReviewStatus.COMPLETED
    assert evidence.review_decision is ReviewDecision.ACCEPT


def test_sandbox_finding_fails_the_task(tmp_path: Path) -> None:
    root = repository(tmp_path)
    changes = proposal_with_wrong_test()
    # v0.1: the real finding consumes the single rework; the scripted rework
    # repeats the wrong test, so the real checks fail again and the run stops.
    rework_coding = json.loads(changes)
    rework_coding["changes"][0]["content"] += "\n# Rework retains the wrong test.\n"
    model = ReplayModel(changes, json.dumps(rework_coding))
    result, sandbox, _ = run(config(root, model, docker=docker()))
    assert result.disposition is TaskDisposition.FAILED
    assert result.failure is TaskFailure.CHECKS_FAILED
    assert sandbox.calls == 6 and model.calls == 2
    assert result.evidence.rework_trigger is ReworkTrigger.CHECK_FINDINGS
    # A real sandbox finding never reaches the reviewer.
    assert result.evidence.review is None
    assert all(attempt.review is None for attempt in result.evidence.attempts)
    outcomes = {
        r.request.kind: r.result.outcome for r in result.evidence.checks if r.result
    }
    assert outcomes[CheckKind.PYTEST] is CheckOutcome.FAILED
    assert outcomes[CheckKind.RUFF_CHECK] is CheckOutcome.PASSED


def test_missing_docker_is_check_infrastructure_error(tmp_path: Path) -> None:
    root = repository(tmp_path)
    missing = tmp_path / "missing" / "docker.exe"
    result, _, _ = run(config(root, replay(), docker=missing))
    assert result.failure is TaskFailure.CHECK_ERROR
    assert [r.error for r in result.evidence.checks] == [CheckFailure.UNAVAILABLE]
    assert result.evidence.applied is not None


def proposal_with_wrong_test() -> str:
    value = json.loads(proposal())
    tests = value["changes"][1]
    tests["content"] = tests["content"].replace(
        "assert reserve(5, 5) == 0", "assert reserve(5, 5) == 1"
    )
    return json.dumps(value)


def test_rework_then_accept_in_the_real_sandbox(tmp_path: Path) -> None:
    # ForgeAI-3: review #1 CHANGES_REQUIRED -> one rework -> real checks
    # again -> review #2 ACCEPT. Four model calls, two applies, six checks.
    root = repository(tmp_path)
    model = ReplayModel(proposal(), REVIEW_CHANGES, REWORK, REVIEW_ACCEPT)
    result, sandbox, mutation = run(config(root, model, docker=docker()))
    evidence = result.evidence
    assert result.disposition is TaskDisposition.SUCCEEDED, result
    assert model.calls == 4 and mutation.calls == 2 and sandbox.calls == 6
    first, second = evidence.attempts
    assert first.review_decision is ReviewDecision.CHANGES_REQUIRED
    assert second.review_decision is ReviewDecision.ACCEPT
    assert all(
        r.result and r.result.outcome is CheckOutcome.PASSED
        for attempt in evidence.attempts
        for r in attempt.checks
    )
    assert evidence.start is not None and evidence.final is not None
    assert evidence.final.head == evidence.start.head
    for attempt in evidence.attempts:
        assert attempt.proposal is not None
    final = {
        change.path.value: change.text
        for attempt in evidence.attempts
        if attempt.proposal is not None
        for change in attempt.proposal.changeset.changes
    }
    for path, text in final.items():
        assert (root / path).read_bytes().decode("utf-8") == text
    assert not list(root.rglob("__pycache__")), "checks must not run on the host"


def test_rework_check_finding_stops_before_second_review(tmp_path: Path) -> None:
    root = repository(tmp_path)
    broken = json.loads(REWORK)
    broken["changes"][0]["content"] = broken["changes"][0]["content"].replace(
        '(5, 6, "requested units exceed available stock")',
        '(5, 6, "requested units must be positive")',
    )
    model = ReplayModel(proposal(), REVIEW_CHANGES, json.dumps(broken), REVIEW_ACCEPT)
    result, sandbox, mutation = run(config(root, model, docker=docker()))
    assert result.failure is TaskFailure.CHECKS_FAILED
    assert model.calls == 3 and mutation.calls == 2 and sandbox.calls == 6
    second = result.evidence.attempts[1]
    assert second.review is None
    outcomes = {r.request.kind: r.result.outcome for r in second.checks if r.result}
    assert outcomes[CheckKind.PYTEST] is CheckOutcome.FAILED
