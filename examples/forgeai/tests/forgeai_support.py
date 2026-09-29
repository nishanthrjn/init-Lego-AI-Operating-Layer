"""Shared test harness: fixture repositories, operator configs and fakes.

The fake sandbox answers with the CR-2b runner envelope, so the real
SandboxedEngineeringChecks adapter still maps every outcome; real Docker runs
are in the separately marked end-to-end tests.
"""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from legoai.runtime.api import ModelBindingConfig
from legoai_engineering.coding.values import CodingTarget
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.sandbox.errors import SandboxError
from legoai_engineering.sandbox.ports import CancellationSignal
from legoai_engineering.sandbox.values import SandboxRequest, SandboxResult

from demo import FIXTURE, OBJECTIVE, TARGETS, create_repository
from forgeai.cli import ReplayModel, replay_binding
from forgeai.composition import ForgeAIConfig, local_profile
from forgeai.domain import TaskRequest

GIT_EXECUTABLE = shutil.which("git")
PROPOSAL = (FIXTURE / "proposal.json").read_text(encoding="utf-8")


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


def config(
    root: Path,
    model: ReplayModel,
    *,
    denied: frozenset[str] = frozenset(),
    editable: tuple[str, ...] = TARGETS,
    extra: tuple[ModelBindingConfig, ...] = (),
    binding: str = "replay",
    docker: Path | None = None,
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
            "exit": self.exits[index],
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
