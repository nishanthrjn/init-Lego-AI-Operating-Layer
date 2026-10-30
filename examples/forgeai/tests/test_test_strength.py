"""Differential gate contracts; real Docker cases require explicit opt-in."""

import asyncio
import json
import os
import shutil
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    Clock,
    FakeSandbox,
    LoggedReplay,
    config,
    git_executable,
    proposal,
    repository,
    task,
)
from legoai_engineering.checks.values import CheckKind, CheckRequest
from legoai_engineering.coding.values import CodingTarget
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.sandbox.docker import DockerSandbox, DockerSandboxConfig
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure
from legoai_engineering.sandbox.ports import CancellationSignal, SandboxExecutionPort
from legoai_engineering.sandbox.values import SandboxRequest, SandboxResult
from test_line_endings import fixture

from batch import Git, run_batch
from forgeai.cli import _parse, summarize
from forgeai.composition import (
    ForgeAIConfig,
    OriginalSourceOverlay,
    prepare_run,
    utc_now,
)
from forgeai.domain import (
    OperatorDecision,
    ProposalReview,
    ReworkTrigger,
    TaskDisposition,
    TaskFailure,
    TaskRequest,
    TaskResult,
)
from forgeai.guard import WorkspaceGuard
from forgeai.policy import ApprovalPolicy
from forgeai.report import ModelBindingKind, run_report


class ObservedSandbox(FakeSandbox):
    def __init__(
        self,
        exits: tuple[int, ...],
        *,
        clock: Clock | None = None,
        fail_at: int | None = None,
    ) -> None:
        super().__init__(exits)
        self.inputs: list[dict[str, str]] = []
        self.clock = clock
        self.fail_at = fail_at

    def execute(
        self, request: SandboxRequest, cancellation: CancellationSignal | None = None
    ) -> SandboxResult:
        self.inputs.append({item.path: item.text for item in request.files})
        if self.fail_at == self.calls:
            self.calls += 1
            raise SandboxError(SandboxFailure.RUNTIME_UNAVAILABLE)
        result = super().execute(request, cancellation)
        if self.clock is not None and self.calls == 3:
            self.clock.now += timedelta(hours=2)
        return result


def rework(output: str) -> str:
    value = json.loads(output)
    value["changes"][0]["content"] += "\n# rework candidate\n"
    value["changes"][1]["content"] += "\n# test rework\n"
    return json.dumps(value)


def execute(
    root: Path,
    sandbox: SandboxExecutionPort,
    outputs: tuple[str, ...],
    *,
    enabled: bool = True,
    selected: TaskRequest | None = None,
    clock: Clock | None = None,
    without_pytest: bool = False,
) -> tuple[TaskResult, LoggedReplay, list[ProposalReview]]:
    model = LoggedReplay([], *outputs)
    request = selected or task()
    cfg = replace(
        config(root, model, editable=tuple(t.path.value for t in request.targets)),
        test_strength=enabled,
    )
    if without_pytest:
        cfg = replace(cfg, check_plan=cfg.check_plan[:2])
    approvals: list[ProposalReview] = []

    def approve(value: ProposalReview) -> OperatorDecision:
        approvals.append(value)
        return OperatorDecision.approve(value)

    prepared = prepare_run(
        cfg,
        WorkspaceGuard(),
        approve=approve,
        sandbox=sandbox,
        confirm_context=lambda _: True,
        clock=clock if clock is not None else utc_now,
    )
    result = asyncio.run(prepared.worker.run(request, prepared.context))
    return result, model, approvals


@pytest.mark.parametrize("ending", ["\n", "\r\n"])
@pytest.mark.parametrize("overlay_exit", [1, 2])
def test_discriminating_stages_original_bytes(
    tmp_path: Path, ending: str, overlay_exit: int
) -> None:
    root = fixture(tmp_path, ending)
    original = (root / "src/inventory/stock.py").read_bytes()
    sandbox = ObservedSandbox((0, 0, 0, overlay_exit))
    result, model, approvals = execute(root, sandbox, (proposal(), REVIEW_ACCEPT))
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert model.calls == 2 and sandbox.calls == 4 and len(approvals) == 1
    assert result.evidence.latest.test_strength.value == "DISCRIMINATING"
    staged = sandbox.inputs[3]
    assert staged["src/inventory/stock.py"].encode("utf-8") == original
    assert (
        staged["tests/test_stock.py"].encode("utf-8")
        == (root / "tests/test_stock.py").read_bytes()
    )
    spec = json.loads(staged["__legoai_check__.json"])
    assert spec["targets"] == ["tests/test_stock.py"]


@pytest.mark.parametrize("first_exit", [0, 5])
@pytest.mark.parametrize("second_exit", [0, 1])
def test_strength_rework_is_bounded_and_uses_original_source(
    tmp_path: Path, first_exit: int, second_exit: int
) -> None:
    root = repository(tmp_path)
    original = (root / "src/inventory/stock.py").read_bytes()
    sandbox = ObservedSandbox((0, 0, 0, first_exit, 0, 0, 0, second_exit))
    second = rework(proposal())
    result, model, approvals = execute(
        root, sandbox, (proposal(), second, REVIEW_ACCEPT)
    )
    assert result.evidence.rework_trigger is ReworkTrigger.TEST_STRENGTH
    assert result.evidence.attempts[0].review is None
    assert result.evidence.attempts[0].test_strength.value == "NOT_DISCRIMINATING"
    assert len(approvals) == 2 and sandbox.calls == 8
    assert any("add or correct tests" in text for text in approvals[1].feedback)
    assert sandbox.inputs[7]["src/inventory/stock.py"].encode() == original
    assert sandbox.inputs[6]["src/inventory/stock.py"].encode() != original
    if second_exit == 1:
        assert result.disposition is TaskDisposition.SUCCEEDED
        assert model.calls == 3
    else:
        assert result.failure is TaskFailure.TESTS_NOT_DISCRIMINATING
        assert result.evidence.latest.review is None and model.calls == 2
        assert "WARNING: changes remain in the working tree" in summarize(result)
    report = run_report(result, ModelBindingKind.REPLAY)
    assert report["rework_trigger"] == "TEST_STRENGTH"
    assert report["failure"] == (None if second_exit else "TESTS_NOT_DISCRIMINATING")
    assert (
        sandbox.inputs[7]["tests/test_stock.py"].encode()
        == (root / "tests/test_stock.py").read_bytes()
    )


def test_created_source_is_absent_from_overlay(tmp_path: Path) -> None:
    root = repository(tmp_path)
    value = json.loads(proposal())
    value["changes"][0].update(
        path="src/inventory/created.py", operation="create", content="VALUE = 1\n"
    )
    value["changes"][1]["content"] = (
        "from inventory.created import VALUE\n\ndef test_created() -> None:\n"
        "    assert VALUE == 1\n"
    )
    selected = replace(
        task(),
        targets=(
            CodingTarget(
                RepositoryPath("src/inventory/created.py"), FileChangeKind.CREATE
            ),
            task().targets[1],
        ),
    )
    sandbox = ObservedSandbox((0, 0, 0, 2))
    result, _, _ = execute(
        root, sandbox, (json.dumps(value), REVIEW_ACCEPT), selected=selected
    )
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert "src/inventory/created.py" in sandbox.inputs[2]
    assert "src/inventory/created.py" not in sandbox.inputs[3]
    assert "from inventory.created" in sandbox.inputs[3]["tests/test_stock.py"]
    cfg = config(root, LoggedReplay([], proposal()))
    overlay = OriginalSourceOverlay(
        LocalRepositoryWorkspace(LocalWorkspaceRoot(root), cfg.workspace_policy),
        {RepositoryPath("src/inventory/created.py"): None},
    )
    with pytest.raises(WorkspaceError):
        overlay.read_text(RepositoryPath("src/inventory/created.py"))


@pytest.mark.parametrize("mode", ["tests", "src", "no_pytest"])
def test_not_applicable_does_not_execute(tmp_path: Path, mode: str) -> None:
    root = repository(tmp_path)
    value = json.loads(proposal())
    review = json.loads(REVIEW_ACCEPT)
    if mode != "no_pytest":
        value["changes"] = [
            c for c in value["changes"] if c["path"].startswith(mode + "/")
        ]
        review["summary"] = "The single-file candidate is accepted."
        review["findings"] = []
    sandbox = ObservedSandbox((0,))
    result, _, _ = execute(
        root,
        sandbox,
        (json.dumps(value), json.dumps(review)),
        without_pytest=mode == "no_pytest",
    )
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert result.evidence.latest.test_strength.value == "NOT_APPLICABLE"
    assert sandbox.calls == (2 if mode == "no_pytest" else 3)


@pytest.mark.parametrize("error", ["sandbox", "exit", "expired"])
def test_strength_errors_never_rework(tmp_path: Path, error: str) -> None:
    root = repository(tmp_path)
    clock = Clock()
    sandbox = ObservedSandbox(
        (0, 0, 0, 3),
        clock=clock if error == "expired" else None,
        fail_at=3 if error == "sandbox" else None,
    )
    result, model, _ = execute(root, sandbox, (proposal(),), clock=clock)
    assert result.failure is (
        TaskFailure.CHECK_DENIED if error == "expired" else TaskFailure.CHECK_ERROR
    )
    assert sandbox.calls == (3 if error == "expired" else 4)
    assert model.calls == 1 and result.evidence.rework_trigger is None
    assert result.evidence.latest.review is None
    assert result.evidence.latest.test_strength.value == "NOT_RUN"


def test_flag_off_keeps_existing_flow(tmp_path: Path) -> None:
    root = repository(tmp_path)
    sandbox = ObservedSandbox((0,))
    result, model, _ = execute(
        root, sandbox, (proposal(), REVIEW_ACCEPT), enabled=False
    )
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert sandbox.calls == 3 and model.calls == 2
    assert result.evidence.latest.test_strength.value == "NOT_RUN"
    assert result.evidence.latest.strength_check is None
    assert "test strength" not in summarize(result).lower()
    assert "test_strength" not in summarize(result)


def test_earlier_gate_leaves_strength_not_run(tmp_path: Path) -> None:
    root = repository(tmp_path)
    sandbox = ObservedSandbox((0,))
    result, _, _ = execute(root, sandbox, ("invalid json",))
    assert result.failure is TaskFailure.PROPOSAL_INVALID
    assert sandbox.calls == 0
    assert result.evidence.latest.test_strength.value == "NOT_RUN"
    assert result.evidence.latest.strength_check is None


def test_cli_and_policy_are_opt_in() -> None:
    arguments = [
        "run",
        "--repo",
        ".",
        "--task",
        "guard",
        "--target",
        "src/a.py:update",
    ]
    _, baseline = _parse(arguments)
    _, enabled = _parse([*arguments, "--test-strength"])
    assert baseline.test_strength is False and enabled.test_strength is True
    assert ApprovalPolicy().require_test_strength is False
    assert ApprovalPolicy(require_test_strength=True).require_test_strength is True
    with pytest.raises(ValueError):
        ApprovalPolicy(require_test_strength=1)  # type: ignore[arg-type]


def test_batch_strength_failure_makes_no_commit(tmp_path: Path) -> None:
    root = repository(tmp_path)
    directory = tmp_path / "inputs"
    directory.mkdir()
    (directory / "first.json").write_text(proposal(), encoding="utf-8")
    (directory / "second.json").write_text(rework(proposal()), encoding="utf-8")
    policy = directory / "policy.toml"
    policy.write_text("require_test_strength = true\n", encoding="utf-8")
    tasks = directory / "tasks.toml"
    tasks.write_text(
        'base = "HEAD"\nbinding = "replay"\n[[task]]\nid = "T1"\n'
        'objective = "Guard stock"\n'
        'targets = ["src/inventory/stock.py", "tests/test_stock.py"]\n'
        'replay = ["first.json", "second.json"]\n',
        encoding="utf-8",
    )
    sandbox = ObservedSandbox((0,))
    result = asyncio.run(
        run_batch(
            root,
            tasks,
            policy,
            tmp_path / "output",
            git=Git(git_executable()),
            docker=git_executable(),
            sandbox=sandbox,
            out=lambda _: None,
        )
    )
    assert result.stopped == "TESTS_NOT_DISCRIMINATING"
    assert result.commits == () and sandbox.calls == 8


class CountedDocker:
    def __init__(self, cfg: ForgeAIConfig) -> None:
        self.inner = DockerSandbox(
            DockerSandboxConfig(cfg.docker_executable, cfg.sandbox_image),
            cfg.sandbox_policy,
        )
        self.calls = 0

    def execute(
        self, request: SandboxRequest, cancellation: CancellationSignal | None = None
    ) -> SandboxResult:
        self.calls += 1
        return self.inner.execute(request, cancellation)


@pytest.mark.skipif(
    os.environ.get("LEGOAI_QUALIFY_TEST_STRENGTH") != "1",
    reason="explicit real-Docker qualification only",
)
@pytest.mark.parametrize("vacuous", [False, True], ids=["discriminating", "vacuous"])
def test_real_docker_strength(tmp_path: Path, vacuous: bool) -> None:
    root = repository(tmp_path)
    output = json.loads(proposal())
    if vacuous:
        output["changes"][1]["content"] = (
            "from inventory.stock import reserve\n\n\ndef test_reserve() -> None:\n"
            "    assert reserve(10, 3) == 7\n"
        )
    first = json.dumps(output)
    model = (
        LoggedReplay([], first, rework(first), REVIEW_ACCEPT)
        if vacuous
        else LoggedReplay([], first, REVIEW_ACCEPT)
    )
    executable = shutil.which("docker")
    assert executable is not None, "Docker and qualified image must be available"
    cfg = replace(config(root, model, docker=Path(executable)), test_strength=True)
    # Isolate the differential pytest contract from unrelated formatting tools.
    cfg = replace(
        cfg, check_plan=(CheckRequest(CheckKind.PYTEST, (RepositoryPath("tests"),)),)
    )
    sandbox = CountedDocker(cfg)
    prepared = prepare_run(
        cfg,
        WorkspaceGuard(),
        approve=OperatorDecision.approve,
        confirm_context=lambda _: True,
        sandbox=sandbox,
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    assert sandbox.calls == (4 if vacuous else 2)
    assert result.failure is (TaskFailure.TESTS_NOT_DISCRIMINATING if vacuous else None)
    assert result.disposition is (
        TaskDisposition.FAILED if vacuous else TaskDisposition.SUCCEEDED
    )
