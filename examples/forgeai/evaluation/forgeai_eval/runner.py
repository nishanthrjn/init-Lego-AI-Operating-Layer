"""Evaluation runs: provision, run the unchanged ForgeAI flow, then the oracle.

ForgeAI is consumed exactly as an external application would: through
`forgeai.composition.local_profile` / `run_task` and the public LegoAI host.
The harness adds only timing, the post-run hidden acceptance tests and, when
an observation log is configured, the content-free LQ1.2 reply observations.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from legoai.runtime.api import ModelBindingConfig
from legoai_engineering.checks.values import CheckPolicy
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.sandbox.docker import (
    DockerSandbox,
    DockerSandboxConfig,
    SandboxImage,
)
from legoai_engineering.sandbox.ports import SandboxExecutionPort
from legoai_engineering.sandbox.values import SandboxPolicy

from forgeai.composition import local_profile, run_task
from forgeai.domain import TaskResult
from forgeai.guard import WorkspaceGuard
from forgeai_eval.fixtures import Fixture, FixtureSet, provision
from forgeai_eval.hidden import HiddenOutcome, HiddenResult, run_hidden
from forgeai_eval.observer import Observation, ObservationLog

REQUIRED_METADATA = (
    "mode",
    "provider",
    "binding",
    "model_name",
    "model_digest",
    "ollama_version",
    "forgeai_commit",
    "fixture_set",
    "fixture_revision",
    "fixture_digest",
    "hidden_revision",
    "hidden_digest",
    "hardware_class",
    "platform",
    "started_at",
)


@dataclass(frozen=True, slots=True)
class RunMetadata:
    """Operator-supplied and harness-recorded identity of one evaluation."""

    mode: str
    provider: str
    binding: str
    model_name: str
    model_digest: str
    ollama_version: str
    forgeai_commit: str
    fixture_set: str
    fixture_revision: str
    fixture_digest: str
    hidden_revision: str
    hidden_digest: str
    hardware_class: str
    platform: str
    started_at: str
    repetitions: int

    def missing(self) -> tuple[str, ...]:
        absent = [
            name
            for name in REQUIRED_METADATA
            if not isinstance(getattr(self, name), str)
            or not getattr(self, name).strip()
        ]
        if type(self.repetitions) is not int or self.repetitions < 1:
            absent.append("repetitions")
        return tuple(absent)


@dataclass(frozen=True, slots=True)
class FixtureRun:
    """One fixture repetition: the typed ForgeAI result plus the oracle."""

    fixture_id: str
    repetition: int
    task_result: TaskResult = field(repr=False)
    hidden: HiddenResult
    run_seconds: float
    hidden_seconds: float
    # LQ1.2: None when the run was not observed; else whether every call of
    # this run was captured before the run closed.
    observations: tuple[Observation, ...] = ()
    observation_complete: bool | None = None


BindingFactory = Callable[[Fixture], tuple[tuple[ModelBindingConfig, ...], str]]


@dataclass(frozen=True, slots=True)
class RunSettings:
    """Operator configuration for one evaluation; never task data."""

    bindings: BindingFactory
    git: Path
    docker: Path
    workdir: Path
    hidden_policy: CheckPolicy = CheckPolicy(timeout_seconds=120)
    forgeai_sandbox: SandboxExecutionPort | None = None
    hidden_sandbox: Callable[[], SandboxExecutionPort] | None = None
    observations: ObservationLog | None = None
    # Bounded wait for a call still in flight after ForgeAI returned (only
    # after the adapter's own timeout); should exceed the observer's margin.
    observation_wait_seconds: float = 30.0

    def oracle_sandbox(self) -> SandboxExecutionPort:
        if self.hidden_sandbox is not None:
            return self.hidden_sandbox()
        return DockerSandbox(
            DockerSandboxConfig(self.docker, SandboxImage.PYTHON_CHECKS),
            SandboxPolicy(timeout_seconds=180, max_output_bytes=1_048_576),
        )


def evaluate_run(
    fixture: Fixture, repetition: int, settings: RunSettings
) -> FixtureRun:
    root = provision(
        fixture, settings.workdir / f"{fixture.fixture_id}-{repetition}", settings.git
    )
    bindings, binding = settings.bindings(fixture)
    config = local_profile(
        root,
        tuple(target.path for target in fixture.task.targets),
        bindings=bindings,
        binding=binding,
        git_executable=settings.git,
        docker_executable=settings.docker,
        now=datetime.now(UTC),
    )
    if settings.observations is not None:
        settings.observations.drain()  # nothing earlier belongs to this run
    started = time.perf_counter()
    result = asyncio.run(
        run_task(
            config, fixture.task, WorkspaceGuard(), sandbox=settings.forgeai_sandbox
        )
    )
    run_seconds = time.perf_counter() - started
    observations: tuple[Observation, ...] = ()
    complete: bool | None = None
    if settings.observations is not None:
        observations, complete = settings.observations.drain(
            settings.observation_wait_seconds
        )
    hidden_started = time.perf_counter()
    if result.evidence.changed_paths:
        hidden = run_hidden(
            LocalRepositoryWorkspace(LocalWorkspaceRoot(root), config.workspace_policy),
            fixture.hidden_files(),
            settings.oracle_sandbox(),
            settings.hidden_policy,
        )
    else:
        hidden = HiddenResult(HiddenOutcome.NOT_RUN, error="no change applied")
    return FixtureRun(
        fixture.fixture_id,
        repetition,
        result,
        hidden,
        run_seconds,
        time.perf_counter() - hidden_started,
        observations,
        complete,
    )


def evaluate(
    fixtures: FixtureSet, repetitions: int, settings: RunSettings
) -> tuple[tuple[FixtureRun, ...], float]:
    """Every fixture, `repetitions` times, sequentially; returns runs and seconds."""
    if type(repetitions) is not int or repetitions < 1:
        raise ValueError("repetitions must be a positive integer")
    started = time.perf_counter()
    runs = tuple(
        evaluate_run(fixture, repetition, settings)
        for fixture in fixtures.fixtures
        for repetition in range(1, repetitions + 1)
    )
    return runs, time.perf_counter() - started
