"""Maintainer opt-in: replay models and actual qualified GENERIC Docker checks."""

import asyncio
import json
import os
from dataclasses import replace
from pathlib import Path

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    REWORK,
    LoggedMutation,
    LoggedReplay,
    config,
    proposal,
    repository,
    snapshot,
    task,
)
from legoai.kernel.context import TenantContext
from legoai_engineering.checks.values import CheckKind
from legoai_engineering.coding.values import CodingEvidence, CodingTarget
from legoai_engineering.repository.mutation_authorized import (
    REPOSITORY_MUTATION_ACTION,
)
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.sandbox.docker import (
    DockerSandbox,
    DockerSandboxConfig,
    SandboxImage,
)
from legoai_engineering.sandbox.ports import CancellationSignal
from legoai_engineering.sandbox.values import SandboxRequest, SandboxResult
from test_end_to_end import docker
from test_v01_check_rework import b011_proposal

from forgeai.composition import prepare_run
from forgeai.domain import (
    CheckProfile,
    OperatorDecision,
    ProposalReview,
    TaskDisposition,
    TaskFailure,
)
from forgeai.guard import WorkspaceGuard
from forgeai.repository_context import ContextPreflight, inventory_digest

pytestmark = pytest.mark.skipif(
    os.environ.get("LEGOAI_QUALIFY_FORGEAI_V02_SANDBOX") != "1",
    reason="requires explicit real-sandbox maintainer validator",
)


class ObservedDocker:
    """Delegation only: every result comes from the real adapter."""

    def __init__(self, inner: DockerSandbox, events: list[str]) -> None:
        self.inner = inner
        self.events = events
        self.calls = 0

    def execute(
        self, request: SandboxRequest, cancellation: CancellationSignal | None = None
    ) -> SandboxResult:
        self.calls += 1
        self.events.append("check")
        return self.inner.execute(request, cancellation)


@pytest.mark.parametrize("rework", [False, True], ids=["success", "check_rework"])
def test_confirmed_lifecycle_real_sandbox(tmp_path: Path, rework: bool) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    events: list[str] = []
    outputs = (
        (b011_proposal(), REWORK, REVIEW_ACCEPT)
        if rework
        else (proposal(), REVIEW_ACCEPT)
    )
    model = LoggedReplay(events, *outputs)
    cfg = config(root, model, docker=docker(), context=("pyproject.toml",))
    assert cfg.check_profile is CheckProfile.GENERIC
    assert cfg.sandbox_image is SandboxImage.PYTHON_CHECKS
    real = DockerSandbox(
        DockerSandboxConfig(cfg.docker_executable, SandboxImage.PYTHON_CHECKS),
        cfg.sandbox_policy,
    )
    sandbox = ObservedDocker(real, events)
    confirmed: list[ContextPreflight] = []

    def confirm(value: ContextPreflight) -> bool:
        confirmed.append(value)
        events.append("context")
        return True

    def approve(value: ProposalReview) -> OperatorDecision:
        events.append("approval")
        return OperatorDecision.approve(value)

    prepared = prepare_run(
        cfg,
        WorkspaceGuard(),
        approve=approve,
        confirm_context=confirm,
        sandbox=sandbox,
    )
    inner = prepared.worker.agent.evidence_reader
    acquired: list[CodingEvidence] = []

    class ObservedReads:
        async def acquire(
            self,
            targets: tuple[CodingTarget, ...],
            tenant: TenantContext,
            references: tuple[RepositoryPath, ...] = (),
        ) -> CodingEvidence:
            value = await inner.acquire(targets, tenant, references)
            acquired.append(value)
            return value

    mutation = LoggedMutation(events, prepared.worker.mutation)
    worker = replace(
        prepared.worker,
        mutation=mutation,
        agent=replace(prepared.worker.agent, evidence_reader=ObservedReads()),
    )
    selected = replace(task(), context=cfg.context_paths)
    result = asyncio.run(worker.run(selected, prepared.context))
    assert result.disposition is TaskDisposition.SUCCEEDED, result
    count = 2 if rework else 1
    cycle = ["context", "model", "approval", "apply", "check", "check", "check"]
    assert events == cycle * count + ["model"]
    assert model.calls == count + 1
    assert mutation.calls == count and sandbox.calls == 3 * count
    assert len(acquired) == 2 * count  # preflight + fresh read; no third read
    assert len(confirmed) == len(result.evidence.context_confirmations) == count
    for index, decision in enumerate(result.evidence.context_confirmations):
        assert decision.confirmed
        assert decision.binding.inventory == inventory_digest(confirmed[index])
        assert acquired[2 * index] == acquired[2 * index + 1]
        bundle = acquired[2 * index + 1]
        payload = json.loads(model.requests[index].messages[-1].content)
        assert payload["targets"] == [
            {
                "path": f.target.path.value,
                "operation": f.target.operation.value,
                "current_text": f.current.text if f.current else None,
            }
            for f in bundle.files
        ]
        assert bundle.references is not None
        assert payload["read_only_context"] == [
            {"path": f.path, "text": f.text} for f in bundle.references.files
        ]
    expected_kinds = [CheckKind.RUFF_CHECK, CheckKind.MYPY, CheckKind.PYTEST]
    for attempt in result.evidence.attempts:
        assert [c.request for c in attempt.checks] == list(worker.check_plan)
        assert [c.request.kind for c in attempt.checks] == expected_kinds
        assert attempt.approval and attempt.applied is not None
    assert all(c.passed for c in result.evidence.checks)
    if rework:
        first, second = result.evidence.attempts
        assert first.review is None and second.review is not None
        assert [c.request.kind for c in first.checks if not c.passed] == [
            CheckKind.RUFF_CHECK
        ]
        assert result.evidence.context_confirmations[0].binding.identity != (
            result.evidence.context_confirmations[1].binding.identity
        )
        assert acquired[0] != acquired[2]
    assert result.evidence.start is not None and result.evidence.final is not None
    assert result.evidence.start.head == result.evidence.final.head
    assert set(result.evidence.changed_paths) == {t.path for t in selected.targets}
    assert {e.path for e in worker.git.inspect().entries} == set(
        result.evidence.changed_paths
    )
    after = snapshot(root)
    assert set(after) == set(before)
    changed = {path for path in before if before[path] != after[path]}
    assert changed == {t.path.value for t in selected.targets}
    assert worker.guard.acquire(worker.workspace)
    worker.guard.release(worker.workspace)


@pytest.mark.parametrize("stop", ["context", "stale", "approval", "denial"])
def test_negative_pre_effect_no_docker(tmp_path: Path, stop: str) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    events: list[str] = []
    model = LoggedReplay(events, proposal(), REVIEW_ACCEPT)
    denied = (
        frozenset({REPOSITORY_MUTATION_ACTION}) if stop == "denial" else frozenset()
    )
    cfg = config(root, model, docker=docker(), denied=denied)
    sandbox = ObservedDocker(
        DockerSandbox(
            DockerSandboxConfig(cfg.docker_executable, SandboxImage.PYTHON_CHECKS),
            cfg.sandbox_policy,
        ),
        events,
    )

    def confirm(value: ContextPreflight) -> bool:
        if stop == "stale":
            (root / value.inventory[0].path.value).write_text("# changed\n")
        return stop != "context"

    def approve(value: ProposalReview) -> OperatorDecision:
        return (
            OperatorDecision.decline(value)
            if stop == "approval"
            else OperatorDecision.approve(value)
        )

    prepared = prepare_run(
        cfg,
        WorkspaceGuard(),
        approve=approve,
        confirm_context=confirm,
        sandbox=sandbox,
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    expected = {
        "context": TaskFailure.CONTEXT_DECLINED,
        "stale": TaskFailure.CONTEXT_STALE,
        "approval": TaskFailure.PROPOSAL_DECLINED,
        "denial": TaskFailure.MUTATION_DENIED,
    }
    assert result.failure is expected[stop]
    assert sandbox.calls == 0
    assert model.calls == (0 if stop in {"context", "stale"} else 1)
    assert all(a.applied is None and a.review is None for a in result.evidence.attempts)
    if stop != "stale":
        assert snapshot(root) == before
    assert prepared.worker.guard.acquire(prepared.worker.workspace)
    prepared.worker.guard.release(prepared.worker.workspace)
