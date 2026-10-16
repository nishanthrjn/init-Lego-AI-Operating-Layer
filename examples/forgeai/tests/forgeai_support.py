"""Shared test harness: fixture repositories, operator configs and fakes.

The fake sandbox answers with the CR-2b runner envelope, so the real
SandboxedEngineeringChecks adapter still maps every outcome; real Docker runs
are in the separately marked end-to-end tests.
"""

import asyncio
import json
import shutil
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from legoai.intelligence.model.values import ChatRequest, ChatResult
from legoai.runtime.api import ModelBindingConfig
from legoai_engineering.analyst.values import RepositoryEvidence
from legoai_engineering.coding.values import CodingTarget
from legoai_engineering.repository.mutation import (
    FileChangeKind,
    RepositoryChangeSet,
    RepositoryMutationResult,
)
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.sandbox.errors import SandboxError
from legoai_engineering.sandbox.ports import CancellationSignal
from legoai_engineering.sandbox.values import SandboxRequest, SandboxResult

from demo import FIXTURE, OBJECTIVE, TARGETS, create_repository
from forgeai.cli import ReplayModel, replay_binding
from forgeai.composition import (
    ForgeAIConfig,
    PreparedRun,
    local_profile,
    prepare_run,
    utc_now,
)
from forgeai.domain import OperatorDecision, ProposalReview, TaskRequest, TaskResult
from forgeai.guard import WorkspaceGuard
from forgeai.worker import RepositoryTaskWorker

GIT_EXECUTABLE = shutil.which("git")
PROPOSAL = (FIXTURE / "proposal.json").read_text(encoding="utf-8")
REVIEW_ACCEPT = (FIXTURE / "review_accept.json").read_text(encoding="utf-8")
REWORK = (FIXTURE / "proposal_rework.json").read_text(encoding="utf-8")
REVIEW_CHANGES = (FIXTURE / "review_changes_required.json").read_text(encoding="utf-8")
REVIEW_INSUFFICIENT = (FIXTURE / "review_insufficient.json").read_text(encoding="utf-8")


def approve(review: ProposalReview) -> OperatorDecision:
    """Explicit test-operator approval of the exact proposal shown."""
    return OperatorDecision.approve(review)


def confirm_context_then_decline(prompt: str) -> str:
    """Confirm inventory, then exercise the separate mutation-refusal gate."""
    return "y" if prompt.startswith("Confirm") else "n"


def git_executable() -> Path:
    assert GIT_EXECUTABLE is not None, "ForgeAI tests require Git"
    return Path(GIT_EXECUTABLE)


def repository(tmp_path: Path, name: str = "repo") -> Path:
    return create_repository(tmp_path / name, git_executable())


def task() -> TaskRequest:
    return TaskRequest(
        OBJECTIVE,
        tuple(CodingTarget(RepositoryPath(t), FileChangeKind.UPDATE) for t in TARGETS),
        ("Keep the public function signature unchanged.",),
    )


def proposal(**changes: object) -> str:
    value = json.loads(PROPOSAL)
    value.update(changes)
    return json.dumps(value)


def replay(
    output: str | None = None, review: str | Exception | None = None
) -> ReplayModel:
    """Recorded outputs in call order: Coding Agent proposal, then review."""
    return ReplayModel(
        output if output is not None else proposal(),
        review if review is not None else REVIEW_ACCEPT,
    )


def config(
    root: Path,
    model: ReplayModel,
    *,
    denied: frozenset[str] = frozenset(),
    editable: tuple[str, ...] = TARGETS,
    extra: tuple[ModelBindingConfig, ...] = (),
    binding: str = "replay",
    docker: Path | None = None,
    context: tuple[str, ...] = (),
) -> ForgeAIConfig:
    return local_profile(
        root,
        tuple(RepositoryPath(path) for path in editable),
        bindings=(replay_binding(model), *extra),
        binding=binding,
        git_executable=git_executable(),
        docker_executable=docker or git_executable(),
        now=datetime.now(UTC),
        denied_actions=denied,
        context_paths=tuple(RepositoryPath(path) for path in context),
    )


class FakeSandbox:
    """SandboxExecutionPort double: scripted exit codes or one infrastructure error."""

    def __init__(
        self, exits: tuple[int, ...] = (0, 0, 0), error: SandboxError | None = None
    ) -> None:
        self.exits = exits
        self.error = error
        self.calls = 0

    def execute(
        self, request: SandboxRequest, cancellation: CancellationSignal | None = None
    ) -> SandboxResult:
        index = self.calls
        self.calls += 1
        if self.error is not None:
            raise self.error
        body = {
            "status": "completed",
            "exit": self.exits[index % len(self.exits)],  # script repeats per batch
            "stdout": "",
            "stderr": "",
        }
        return SandboxResult(0, json.dumps(body).encode(), b"")


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


class Clock:
    def __init__(self) -> None:
        self.now = datetime.now(UTC)

    def __call__(self) -> datetime:
        return self.now


class LoggedReplay(ReplayModel):
    """Replay model that logs call order and records each request."""

    def __init__(
        self,
        log: list[str],
        *outputs: str | Exception,
        after_first: Clock | None = None,
        advance_after: int = 1,
    ) -> None:
        super().__init__(*outputs)
        self.log = log
        self.requests: list[ChatRequest] = []
        self.after_first = after_first
        self.advance_after = advance_after

    async def chat(self, request: ChatRequest) -> ChatResult:
        self.log.append("model")
        self.requests.append(request)
        try:
            return await super().chat(request)
        finally:
            if self.after_first is not None and self.calls == self.advance_after:
                self.after_first.now += timedelta(hours=2)


class LoggedSandbox(FakeSandbox):
    def __init__(self, log: list[str], exits: tuple[int, ...] = (0, 0, 0)) -> None:
        super().__init__(exits)
        self.log = log

    def execute(self, request, cancellation=None):  # type: ignore[no-untyped-def]
        self.log.append("check")
        return super().execute(request, cancellation)


class LoggedMutation:
    def __init__(self, log: list[str], inner: object) -> None:
        self.log = log
        self.inner = inner
        self.calls = 0

    def apply(self, changeset: RepositoryChangeSet) -> RepositoryMutationResult:
        self.log.append("apply")
        self.calls += 1
        return self.inner.apply(changeset)  # type: ignore[attr-defined,no-any-return]


class SpyReader:
    def __init__(self, inner: object) -> None:
        self.inner = inner
        self.requests: list[tuple[RepositoryPath, ...]] = []

    async def acquire(self, targets, tenant):  # type: ignore[no-untyped-def]
        self.requests.append(targets)
        result: RepositoryEvidence = await self.inner.acquire(targets, tenant)  # type: ignore[attr-defined]
        return result


def logged_run(
    root: Path,
    *outputs: str | Exception,
    exits: tuple[int, ...] = (0, 0, 0),
    cfg: ForgeAIConfig | None = None,
    clock: Clock | None = None,
    advance: bool = False,
    advance_after: int = 1,
) -> tuple[TaskResult, LoggedReplay, list[str], LoggedMutation, SpyReader]:
    log: list[str] = []
    model = LoggedReplay(
        log,
        *outputs,
        after_first=clock if advance else None,
        advance_after=advance_after,
    )
    base = cfg or config(root, model)
    if cfg is not None:
        base = replace(
            base,
            host=replace(
                base.host,
                bindings=config(root, model).host.bindings,
            ),
        )
    prepared: PreparedRun = prepare_run(
        base,
        WorkspaceGuard(),
        confirm_context=lambda inventory: True,
        approve=approve,
        sandbox=LoggedSandbox(log, exits),
        clock=clock if clock is not None else utc_now,
    )
    mutation = LoggedMutation(log, prepared.worker.mutation)
    reader = SpyReader(prepared.worker.reader)
    worker: RepositoryTaskWorker = replace(
        prepared.worker, mutation=mutation, reader=reader
    )
    result = asyncio.run(worker.run(task(), prepared.context))
    return result, model, log, mutation, reader
