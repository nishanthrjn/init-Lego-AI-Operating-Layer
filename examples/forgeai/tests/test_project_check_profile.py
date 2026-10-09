"""Environment preparation is a startup gate, never a code-finding/rework trigger."""

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest
from forgeai_support import (
    FakeSandbox,
    approve,
    config,
    proposal,
    replay,
    repository,
    snapshot,
    task,
)
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure
from legoai_engineering.sandbox.prepared import PreparationError, PreparationFailure

from forgeai.cli import _parse, main
from forgeai.composition import prepare_run
from forgeai.domain import (
    CheckProfile,
    OperatorDecision,
    ProposalReview,
    TaskDisposition,
    TaskFailure,
)
from forgeai.guard import WorkspaceGuard


@pytest.mark.parametrize("reason", list(PreparationFailure))
def test_preparation_failure_has_zero_model_approval_mutation_and_rework(
    tmp_path: Path,
    reason: PreparationFailure,
) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    model = replay()
    sandbox = FakeSandbox()
    approvals: list[object] = []

    def approve_spy(review: ProposalReview) -> OperatorDecision:
        approvals.append(review)
        return approve(review)

    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        approve=approve_spy,
        sandbox=sandbox,
    )

    def fail():  # type: ignore[no-untyped-def]
        raise PreparationError(reason)

    worker = replace(prepared.worker, prepare_checks=fail)
    result = asyncio.run(worker.run(task(), prepared.context))
    assert result.disposition is TaskDisposition.REJECTED
    assert result.failure is TaskFailure.CHECK_ENVIRONMENT_UNAVAILABLE
    assert result.evidence.preparation_failure is reason
    assert not result.evidence.attempts and result.evidence.rework_trigger is None
    assert model.calls == sandbox.calls == 0
    assert not approvals
    assert snapshot(root) == before


def test_preparation_infrastructure_is_not_a_check_failure(tmp_path: Path) -> None:
    root = repository(tmp_path)
    model = replay()
    prepared = prepare_run(
        config(root, model), WorkspaceGuard(), approve=approve, sandbox=FakeSandbox()
    )

    def fail():  # type: ignore[no-untyped-def]
        raise SandboxError(SandboxFailure.RUNTIME_UNAVAILABLE)

    result = asyncio.run(
        replace(prepared.worker, prepare_checks=fail).run(task(), prepared.context)
    )
    assert (
        result.evidence.preparation_infrastructure_failure
        is SandboxFailure.RUNTIME_UNAVAILABLE
    )
    assert result.evidence.preparation_failure is None
    assert model.calls == 0


def test_generic_default_and_explicit_project_selection(tmp_path: Path) -> None:
    root = repository(tmp_path)
    cfg = config(root, replay())
    assert cfg.check_profile is CheckProfile.GENERIC
    prepared = prepare_run(
        cfg, WorkspaceGuard(), approve=approve, sandbox=FakeSandbox()
    )
    assert prepared.worker.prepare_checks is None
    project = prepare_run(
        replace(cfg, check_profile=CheckProfile.PROJECT),
        WorkspaceGuard(),
        approve=approve,
        sandbox=FakeSandbox(),
    )
    assert project.worker.prepare_checks is not None
    _, args = _parse(
        [
            "run",
            "--repo",
            str(root),
            "--task",
            "test",
            "--target",
            "src/inventory/stock.py:update",
        ]
    )
    assert args.check_profile == "generic"
    with pytest.raises(SystemExit):
        _parse(
            [
                "run",
                "--repo",
                str(root),
                "--task",
                "test",
                "--check-profile",
                "arbitrary-image",
            ]
        )


def test_dirty_repository_does_not_start_preparation(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "dirty.txt").write_text("dirty")
    prepared = prepare_run(
        config(root, replay()), WorkspaceGuard(), approve=approve, sandbox=FakeSandbox()
    )

    def forbidden():  # type: ignore[no-untyped-def]
        pytest.fail("preparation before repository validation")

    result = asyncio.run(
        replace(prepared.worker, prepare_checks=forbidden).run(task(), prepared.context)
    )
    assert result.failure is TaskFailure.DIRTY_START


def test_project_composition_refuses_missing_lock_without_fallback(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    model = replay()
    cfg = replace(
        config(root, model),
        check_profile=CheckProfile.PROJECT,
        uv_executable=tmp_path / "uv.exe",
    )
    sandbox = FakeSandbox()
    prepared = prepare_run(cfg, WorkspaceGuard(), approve=approve, sandbox=sandbox)
    before = snapshot(root)
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    assert result.evidence.preparation_failure is PreparationFailure.LOCK_REQUIRED
    assert result.failure is TaskFailure.CHECK_ENVIRONMENT_UNAVAILABLE
    assert model.calls == sandbox.calls == 0
    assert snapshot(root) == before


def test_successful_preparation_precedes_model_and_keeps_guard(tmp_path: Path) -> None:
    root = repository(tmp_path)
    model = replay()
    guard = WorkspaceGuard()
    sandbox = FakeSandbox()
    prepared = prepare_run(config(root, model), guard, approve=approve, sandbox=sandbox)
    events: list[str] = []

    def ready():  # type: ignore[no-untyped-def]
        assert model.calls == 0 and sandbox.calls == 0
        assert not guard.acquire(prepared.worker.workspace)
        events.append("prepared")
        return prepared.worker.checks

    result = asyncio.run(
        replace(prepared.worker, prepare_checks=ready).run(task(), prepared.context)
    )
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert events == ["prepared"] and model.calls == 2 and sandbox.calls == 3
    assert guard.acquire(prepared.worker.workspace)
    guard.release(prepared.worker.workspace)


def test_model_cannot_change_profile_or_installation_command(tmp_path: Path) -> None:
    root = repository(tmp_path)
    model = replay(
        proposal(check_profile="project", install_command="pip install evil")
    )
    cfg = config(root, model)
    prepared = prepare_run(
        cfg, WorkspaceGuard(), approve=approve, sandbox=FakeSandbox()
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    assert result.failure is TaskFailure.PROPOSAL_INVALID
    assert cfg.check_profile is CheckProfile.GENERIC
    assert not result.evidence.checks and result.evidence.applied is None


def test_cli_project_preflight_refuses_before_docker_probe_or_approval(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    output = tmp_path / "reply.json"
    output.write_text(proposal())
    messages: list[str] = []

    def forbidden(*args):  # type: ignore[no-untyped-def]
        pytest.fail("startup must fail on metadata before Docker or approval")

    code = main(
        [
            "run",
            "--repo",
            str(root),
            "--task",
            "bounded task",
            "--target",
            "src/inventory/stock.py",
            "--binding",
            "replay",
            "--replay",
            str(output),
            "--check-profile",
            "project",
        ],
        ask=forbidden,
        ready=forbidden,
        out=messages.append,
    )
    assert code == 2
    assert "environment preparation: lock_required" in messages[-1]
