"""Real-Docker fixture validity: every task is solvable and every oracle bites.

For each frozen fixture: the unmodified template FAILS its hidden acceptance
tests, and the reference solution, run through the unchanged ForgeAI flow with
real sandboxed checks, SUCCEEDS and PASSES them. Windows + Docker Desktop
reference scope; fails, never skips, when Docker is missing there.
"""

import os
import shutil
from pathlib import Path

import pytest
from eval_support import REVIEW_ACCEPT, fixture_set, reference
from forgeai_support import LoggedReplay, git_executable
from legoai.runtime.api import ModelBindingConfig
from legoai_engineering.checks.values import CheckPolicy
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.workspace import WorkspacePolicy
from legoai_engineering.sandbox.docker import (
    DockerSandbox,
    DockerSandboxConfig,
    SandboxImage,
)
from legoai_engineering.sandbox.values import SandboxPolicy

from forgeai.cli import replay_binding
from forgeai_eval.fixtures import Fixture, provision
from forgeai_eval.hidden import HiddenOutcome, run_hidden
from forgeai_eval.runner import RunSettings, evaluate_run

pytestmark = pytest.mark.skipif(
    os.name != "nt", reason="Windows Desktop reference scope"
)

IDS = ["stock-validation", "pager-boundaries", "temperature-units", "text-slug"]


def docker() -> Path:
    executable = shutil.which("docker")
    assert executable is not None, "LQ1 Docker tests require Docker; no skip"
    return Path(executable)


def sandbox() -> DockerSandbox:
    return DockerSandbox(
        DockerSandboxConfig(docker(), SandboxImage.PYTHON_CHECKS),
        SandboxPolicy(timeout_seconds=180, max_output_bytes=1_048_576),
    )


def by_id(fixture_id: str) -> Fixture:
    return next(f for f in fixture_set().fixtures if f.fixture_id == fixture_id)


@pytest.mark.parametrize("fixture_id", IDS)
def test_unmodified_template_fails_hidden_tests(
    tmp_path: Path, fixture_id: str
) -> None:
    item = by_id(fixture_id)
    repo = provision(item, tmp_path / "repo", git_executable())
    result = run_hidden(
        LocalRepositoryWorkspace(
            LocalWorkspaceRoot(repo),
            WorkspacePolicy(262_144, 65_536, 4096, 32, (".git",)),
        ),
        item.hidden_files(),
        sandbox(),
        CheckPolicy(timeout_seconds=120),
    )
    assert result.outcome is HiddenOutcome.FAILED, result


@pytest.mark.parametrize("fixture_id", IDS)
def test_reference_solution_succeeds_and_passes_hidden_tests(
    tmp_path: Path, fixture_id: str
) -> None:
    item = by_id(fixture_id)
    model = LoggedReplay([], reference(item), REVIEW_ACCEPT)

    def bindings(fixture: Fixture) -> tuple[tuple[ModelBindingConfig, ...], str]:
        return (replay_binding(model),), "replay"

    settings = RunSettings(
        bindings=bindings, git=git_executable(), docker=docker(), workdir=tmp_path
    )
    run = evaluate_run(item, 1, settings)
    assert run.task_result.disposition.value == "succeeded", run.task_result
    assert run.hidden.outcome is HiddenOutcome.PASSED, run.hidden
    assert model.calls == 2
    assert not list((tmp_path / f"{fixture_id}-1").rglob("__pycache__"))
