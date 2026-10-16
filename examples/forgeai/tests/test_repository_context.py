"""Explicit context is read-only data; confirmation never supplies authority."""

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest
from forgeai_support import FakeSandbox, approve, config, replay, repository, snapshot
from forgeai_support import task as task_request
from legoai_engineering.analyst.values import (
    AcquisitionFailure,
    EvidenceAcquisitionError,
)
from legoai_engineering.coding.values import CodingRequest
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.workspace import RepositoryPath

from forgeai.cli import terminal_context_confirmer
from forgeai.composition import prepare_run
from forgeai.domain import TaskFailure, TaskRequest
from forgeai.guard import WorkspaceGuard
from forgeai.repository_context import (
    ContextOutcome,
    ContextReason,
    context_summary,
    preflight_context,
)


def test_inventory_is_stable_read_only_and_does_not_invoke(tmp_path: Path) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    model = replay()
    sandbox = FakeSandbox()
    prepared = prepare_run(
        config(root, model), WorkspaceGuard(), approve=approve, sandbox=sandbox
    )
    task = task_request()
    request = CodingRequest(task.objective, task.targets, (), prepared.context)
    first = asyncio.run(preflight_context(prepared.worker.agent.evidence_reader, request))
    second = asyncio.run(preflight_context(prepared.worker.agent.evidence_reader, request))
    assert first == second
    assert first.outcome is ContextOutcome.READY_FOR_CONTEXT_CONFIRMATION
    assert [item.path.value for item in first.inventory] == sorted(
        target.path.value for target in task.targets
    )
    assert all(item.exists and item.digest for item in first.inventory)
    assert "def " not in context_summary(first)
    assert model.calls == sandbox.calls == 0 and snapshot(root) == before
    # No implicit confirmation, even when all required context exists.
    result = asyncio.run(prepared.worker.run(task, prepared.context))
    assert result.failure is TaskFailure.CONTEXT_DECLINED
    assert result.evidence.context_preflight == first
    assert not result.evidence.attempts and not result.evidence.context_confirmed
    assert model.calls == sandbox.calls == 0 and snapshot(root) == before


@pytest.mark.parametrize("required", ["missing.py", "src/inventory"])
def test_missing_or_directory_stops_before_preparation_and_agents(
    tmp_path: Path, required: str
) -> None:
    root = repository(tmp_path)
    model = replay()
    sandbox = FakeSandbox()
    cfg = replace(config(root, model), context_paths=(RepositoryPath(required),))
    prepared = prepare_run(cfg, WorkspaceGuard(), approve=approve, sandbox=sandbox)

    def forbidden(*args: object) -> bool:
        pytest.fail("incomplete context must stop before later steps")

    worker = replace(
        prepared.worker,
        confirm_context=forbidden,
        admit_model=forbidden,
        prepare_checks=forbidden,
    )
    task = replace(task_request(), context=cfg.context_paths)
    result = asyncio.run(worker.run(task, prepared.context))
    assert result.failure is TaskFailure.CONTEXT_INCOMPLETE
    assert result.evidence.context_preflight is not None
    assert result.evidence.context_preflight.reason is ContextReason.UNAVAILABLE
    assert result.evidence.attempts == ()
    assert model.calls == sandbox.calls == 0


def test_scope_is_not_expanded_by_existing_required_file(tmp_path: Path) -> None:
    root = repository(tmp_path)
    model = replay()
    prepared = prepare_run(
        config(root, model), WorkspaceGuard(), approve=approve, sandbox=FakeSandbox()
    )
    task = replace(task_request(), context=(RepositoryPath("pyproject.toml"),))
    result = asyncio.run(prepared.worker.run(task, prepared.context))
    assert result.failure is TaskFailure.EVIDENCE_DENIED
    assert result.evidence.context_preflight is not None
    assert result.evidence.context_preflight.reason is ContextReason.DENIED
    assert not result.evidence.attempts and model.calls == 0


@pytest.mark.parametrize(
    "path", ["../secret", "./a.py", "/a.py", "C:/a.py", "a\\b", "NUL"]
)
def test_portable_path_boundary(path: str) -> None:
    with pytest.raises(WorkspaceError):
        RepositoryPath(path)


@pytest.mark.parametrize(
    "paths",
    [("a.py", "A.py"), ("a.py", "a.py"), tuple(f"c{i}.py" for i in range(9))],
)
def test_invalid_context_is_invalid_task_not_model_failure(
    paths: tuple[str, ...],
) -> None:
    task = task_request()
    with pytest.raises(ValueError):
        TaskRequest(task.objective, task.targets, (), tuple(map(RepositoryPath, paths)))


@pytest.mark.parametrize("failure", list(AcquisitionFailure) + [None])
def test_safe_closed_acquisition_failures(
    tmp_path: Path, failure: AcquisitionFailure | None
) -> None:
    root = repository(tmp_path)
    prepared = prepare_run(
        config(root, replay()), WorkspaceGuard(), approve=approve, sandbox=FakeSandbox()
    )

    class FailingReader:
        async def acquire(self, *args: object) -> object:
            if failure is not None:
                raise EvidenceAcquisitionError(failure)
            raise OSError("SECRET-CANARY raw provider/body exception")

    task = task_request()
    request = CodingRequest(task.objective, task.targets, (), prepared.context)
    result = asyncio.run(
        preflight_context(FailingReader(), request)  # type: ignore[arg-type]
    )
    assert result.outcome is ContextOutcome.CONTEXT_INCOMPLETE
    assert result.reason is (
        ContextReason[failure.name] if failure else ContextReason.ACQUISITION_FAILED
    )
    assert not result.inventory and "SECRET-CANARY" not in repr(result)
    assert "SECRET-CANARY" not in context_summary(result)


def test_confirmation_does_not_grant_disclosure_or_mutation(tmp_path: Path) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    model = replay()
    order: list[str] = []

    def confirm(inventory: object) -> bool:
        order.append("context")
        return True

    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        approve=approve,
        sandbox=FakeSandbox(),
        confirm_context=confirm,
    )

    def refuse(task: TaskRequest) -> bool:
        order.append("disclosure")
        return False

    result = asyncio.run(
        replace(prepared.worker, admit_model=refuse).run(task_request(), prepared.context)
    )
    assert order == ["context", "disclosure"]
    assert result.failure is TaskFailure.MODEL_DISCLOSURE_REFUSED
    assert model.calls == 0 and snapshot(root) == before


def test_terminal_confirmation_requires_explicit_yes(tmp_path: Path) -> None:
    root = repository(tmp_path)
    prepared = prepare_run(
        config(root, replay()), WorkspaceGuard(), approve=approve, sandbox=FakeSandbox()
    )
    task = task_request()
    inventory = asyncio.run(
        preflight_context(
            prepared.worker.agent.evidence_reader,
            CodingRequest(task.objective, task.targets, (), prepared.context),
        )
    )
    output: list[str] = []
    for answer in ("", "n", "maybe"):
        def reply(prompt: str, value: str = answer) -> str:
            return value

        confirm = terminal_context_confirmer(reply, output.append)
        assert not confirm(inventory)
    assert not terminal_context_confirmer(None, output.append)(inventory)
    assert terminal_context_confirmer(lambda prompt: "yes", output.append)(inventory)


def test_cancellation_is_not_relabelled_as_incomplete(tmp_path: Path) -> None:
    root = repository(tmp_path)
    prepared = prepare_run(
        config(root, replay()), WorkspaceGuard(), approve=approve, sandbox=FakeSandbox()
    )

    class CancelledReader:
        async def acquire(self, *args: object) -> object:
            raise asyncio.CancelledError

    task = task_request()
    request = CodingRequest(task.objective, task.targets, (), prepared.context)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            preflight_context(CancelledReader(), request)  # type: ignore[arg-type]
        )


def test_existing_link_does_not_grant_access(tmp_path: Path) -> None:
    root = repository(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_text("SECRET-CANARY\n", encoding="utf-8")
    linked = root / "linked.py"
    try:
        linked.symlink_to(outside)
    except OSError:
        pytest.skip("creating a symlink requires platform permission")
    model = replay()
    cfg = replace(config(root, model), context_paths=(RepositoryPath("linked.py"),))
    prepared = prepare_run(cfg, WorkspaceGuard(), approve=approve, sandbox=FakeSandbox())
    task = task_request()
    result = asyncio.run(
        preflight_context(
            prepared.worker.agent.evidence_reader,
            CodingRequest(
                task.objective, task.targets, (), prepared.context, cfg.context_paths
            ),
        )
    )
    assert result.reason is ContextReason.BOUNDARY
    assert "SECRET-CANARY" not in context_summary(result) and model.calls == 0
