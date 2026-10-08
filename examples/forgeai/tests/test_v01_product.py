"""ForgeAI v0.1 product behavior: supervised CLI and the pre-mutation approval.

Offline: the deterministic replay model and the fake sandbox (real Docker runs
are covered by the clean-install and end-to-end tests). No live model is used.
"""

import ast
import asyncio
import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    REVIEW_CHANGES,
    REWORK,
    LoggedMutation,
    LoggedReplay,
    LoggedSandbox,
    config,
    git_executable,
    proposal,
    replay,
    repository,
    snapshot,
    task,
)
from legoai.intelligence.model.ports import ModelResponseUncertainError
from legoai_engineering.sandbox.errors import SandboxFailure

from demo import OBJECTIVE, TARGETS
from forgeai.cli import (
    ReplayModel,
    ollama_ready,
    reporter,
    summarize,
    terminal_approver,
)
from forgeai.cli import main as cli_main
from forgeai.composition import prepare_run, sandbox_readiness
from forgeai.domain import (
    OperatorDecision,
    ProposalReview,
    TaskDisposition,
    TaskFailure,
    TaskResult,
)
from forgeai.guard import WorkspaceGuard

SOURCE = Path(__file__).resolve().parents[1] / "src" / "forgeai"
DOCKER = shutil.which("docker")  # path only; never executed by these tests
needs_docker_path = pytest.mark.skipif(DOCKER is None, reason="Docker CLI path")


def main(argv: list[str], **options: Any) -> int:
    """The CLI with Docker readiness stubbed ready unless a test sets it."""
    options.setdefault("ready", lambda config: None)
    return cli_main(argv, **options)


def supervised(
    root: Path,
    *outputs: str | Exception,
    answers: tuple[str, ...] = ("y", "y"),
    exits: tuple[int, ...] = (0, 0, 0),
    approver: Any = None,
) -> tuple[TaskResult, list[str], list[str], LoggedMutation, LoggedReplay]:
    """One run through the real worker with the CLI's approver and reporter."""
    log: list[str] = []
    out: list[str] = []
    replies = iter(answers)

    def ask(prompt: str) -> str:
        log.append("approval")
        out.append(prompt)
        return next(replies)

    model = LoggedReplay(log, *outputs)
    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        approve=approver or terminal_approver(ask, out.append),
        progress=reporter(out.append),
        sandbox=LoggedSandbox(log, exits),
    )
    mutation = LoggedMutation(log, prepared.worker.mutation)
    worker = replace(prepared.worker, mutation=mutation)
    result = asyncio.run(worker.run(task(), prepared.context))
    return result, log, out, mutation, model


def cli(root: Path, tmp_path: Path, *extra: str) -> list[str]:
    recorded = tmp_path / "proposal.json"
    recorded.write_text(proposal(), encoding="utf-8")
    arguments = ["run", "--repo", str(root), "--task", OBJECTIVE]
    arguments += ["--binding", "replay", "--replay", str(recorded)]
    arguments += ["--docker", str(DOCKER), *extra]
    for target in TARGETS:
        arguments += ["--target", target]
    return arguments


def git_clean(root: Path) -> bool:
    status = subprocess.run(
        [str(git_executable()), "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return status.stdout == ""


# CLI surface


@needs_docker_path
def test_run_syntax_parses_and_shows_scope_before_any_model_call(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    out: list[str] = []
    code = main(cli(root, tmp_path), ask=lambda prompt: "n", out=out.append)
    text = "\n".join(out)
    assert code == 1
    for line in (
        f"repository: {root.resolve()}",
        "  - src/inventory/stock.py (update)",
        "  - tests/test_stock.py (update)",
        "checks: ruff_check, mypy, pytest",
        "model: replay (recorded outputs; not a live model)",
        "Nothing is written until you approve the proposal.",
    ):
        assert line in text
    # Scope first, then the proposal, then the decision.
    assert text.index("editable targets") < text.index("Proposal (attempt 1, id ")


@needs_docker_path
@pytest.mark.parametrize(
    "answer",
    ["n", "", "no", "maybe", EOFError(), KeyboardInterrupt()],
    ids=["n", "empty", "no", "other", "eof", "ctrl-c"],
)
def test_decline_eof_and_ctrl_c_write_nothing(
    tmp_path: Path, answer: str | BaseException
) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    out: list[str] = []

    def ask(prompt: str) -> str:
        if isinstance(answer, BaseException):
            raise answer
        return answer

    assert main(cli(root, tmp_path), ask=ask, out=out.append) == 1
    text = "\n".join(out)
    assert "reason: the operator did not approve the proposal; nothing written" in text
    assert "approval: declined; no file was written, checked or reviewed" in text
    assert "WARNING" not in text
    assert snapshot(root) == before and git_clean(root)


@needs_docker_path
def test_non_interactive_never_approves(tmp_path: Path) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    out: list[str] = []
    assert main(cli(root, tmp_path), ask=None, out=out.append) == 1
    assert any("approval is never automatic" in line for line in out)
    assert snapshot(root) == before


@needs_docker_path
def test_legacy_syntax_still_requires_approval(tmp_path: Path) -> None:
    root = repository(tmp_path)
    arguments = cli(root, tmp_path)[1:]
    arguments[0:4] = [str(root), "--objective", OBJECTIVE]
    out: list[str] = []
    assert main(arguments, ask=lambda prompt: "n", out=out.append) == 1
    assert any("operator did not approve" in line for line in out)


@needs_docker_path
def test_dirty_repository_rejected_before_model(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "untracked.txt").write_text("x\n", encoding="utf-8")
    out: list[str] = []
    asked: list[str] = []
    code = main(cli(root, tmp_path), ask=asked.append, out=out.append)
    assert code == 2 and not asked
    assert "reason: repository has pre-existing changes" in out[-1]


@needs_docker_path
def test_missing_or_non_git_repository_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main(cli(tmp_path / "missing", tmp_path), ask=None)
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(SystemExit):
        main(cli(plain, tmp_path), ask=None)


@needs_docker_path
def test_invalid_target_rejected_at_parse(tmp_path: Path) -> None:
    root = repository(tmp_path)
    for bad in ("../outside.py", "src/a.py:delete", "/abs.py"):
        with pytest.raises(SystemExit):
            main([*cli(root, tmp_path), "--target", bad], ask=None)


@needs_docker_path
def test_unavailable_ollama_fails_before_any_model_call(tmp_path: Path) -> None:
    # Port 9 (discard) is closed locally: refused, nothing inferred.
    message = ollama_ready("http://127.0.0.1:9", "qwen2.5-coder:7b", 2.0)
    assert message is not None and "not reachable" in message
    root = repository(tmp_path)
    arguments = cli(root, tmp_path)
    arguments[arguments.index("replay")] = "ollama"
    with pytest.raises(SystemExit):
        main([*arguments, "--ollama-url", "http://127.0.0.1:9"], ask=None)


# Approval boundary


def test_approval_yes_applies_then_checks_then_reviews(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, log, out, mutation, _ = supervised(root, proposal(), REVIEW_ACCEPT)
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert log == ["model", "approval", "apply", "check", "check", "check", "model"]
    text = "\n".join(out)
    assert "  update src/inventory/stock.py (" in text
    assert "    why: Reject negative stock" in text
    # The exact patch is shown before approval (v0.1 supervision slice).
    assert "--- proposed patch (exactly what will be written) ---" in text
    assert (
        "+++ b/src/inventory/stock.py" in text and "+        raise ValueError(" in text
    )
    assert text.index("--- end of patch ---") < text.index("Apply this proposal?")
    assert [line for line in out if line.startswith("[")] == [
        "[1/7] Repository verified",
        "[2/7] Proposal generated",
        "[3/7] Waiting for approval",
        "[4/7] Changes applied",
        "[5/7] Checks completed",
        "[6/7] Review completed",
    ]


def test_decline_runs_no_mutation_checks_or_review(tmp_path: Path) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    result, log, _, mutation, model = supervised(
        root, proposal(), REVIEW_ACCEPT, answers=("n",)
    )
    assert result.failure is TaskFailure.PROPOSAL_DECLINED
    assert result.disposition is TaskDisposition.FAILED
    assert log == ["model", "approval"] and mutation.calls == 0
    assert model.calls == 1  # the reviewer was never called
    assert result.evidence.latest.approval is False
    assert snapshot(root) == before and git_clean(root)


@pytest.mark.parametrize("kind", ["other-identity", "wrong-type", "raises"])
def test_approval_is_bound_to_the_exact_proposal(tmp_path: Path, kind: str) -> None:
    root = repository(tmp_path)

    def approver(review: ProposalReview) -> object:
        if kind == "raises":
            raise RuntimeError("approver failed")
        if kind == "wrong-type":
            return True
        return OperatorDecision(True, review.identity[:1])

    result, log, _, mutation, _ = supervised(
        root, proposal(), REVIEW_ACCEPT, approver=approver
    )
    assert result.failure is TaskFailure.PROPOSAL_DECLINED
    assert mutation.calls == 0 and "check" not in log


def test_proposal_cannot_widen_the_target_set(tmp_path: Path) -> None:
    root = repository(tmp_path)
    value = json.loads(proposal())
    extra = dict(value["changes"][0], path="src/inventory/extra.py")
    extra["operation"] = "create"
    widened = json.dumps({**value, "changes": [*value["changes"], extra]})
    result, log, _, mutation, _ = supervised(root, widened)
    assert result.failure is TaskFailure.PROPOSAL_INVALID
    assert "approval" not in log and mutation.calls == 0


def test_rework_is_approved_separately_and_bounded(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, log, out, mutation, _ = supervised(
        root, proposal(), REVIEW_CHANGES, REWORK, REVIEW_ACCEPT
    )
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert log.count("approval") == 2 and mutation.calls == 2
    assert any(line.startswith("[rework]") for line in out)
    assert "[2/7] Proposal generated (attempt 2)" in out


def test_second_changes_required_is_terminal(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, log, out, _, model = supervised(
        root, proposal(), REVIEW_CHANGES, REWORK, REVIEW_CHANGES
    )
    assert result.failure is TaskFailure.REVIEW_CHANGES_REQUIRED
    assert model.calls == 4 and log.count("approval") == 2
    assert "WARNING: changes remain in the working tree" in summarize(result)


def test_declined_rework_stops_with_attempt_one_changes_in_place(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    result, log, _, mutation, _ = supervised(
        root, proposal(), REVIEW_CHANGES, REWORK, answers=("y", "n")
    )
    assert result.failure is TaskFailure.PROPOSAL_DECLINED
    assert mutation.calls == 1
    text = summarize(result, root)
    assert "WARNING: changes remain in the working tree" in text


# Final result UX


def test_success_summary_is_complete_and_bounded(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, *_ = supervised(root, proposal(), REVIEW_ACCEPT)
    text = summarize(result, root)
    lines = text.splitlines()
    assert lines[0] == "disposition: succeeded"
    for expected in (
        "attempt count: 1",
        "changed files: src/inventory/stock.py, tests/test_stock.py",
        "check pytest: passed",
        "review: accept",
        "blocking findings: 0",
        "unknown: The proposal was not executed by the model.",
    ):
        assert expected in lines
    assert any(line.startswith("final HEAD: unchanged") for line in lines)
    assert any(line.startswith("run: ") for line in lines)
    assert f"inspect: git -C {root} diff --" in text
    assert "WARNING" not in text and "raise ValueError" not in text


def test_check_failure_warns_changes_remain(tmp_path: Path) -> None:
    root = repository(tmp_path)
    # Attempt-1 findings consume the rework; the rework's checks fail again.
    result, *_ = supervised(root, proposal(), REWORK, exits=(0, 0, 1))
    text = summarize(result, root)
    assert result.failure is TaskFailure.CHECKS_FAILED and result.evidence.reworked
    assert "check pytest: failed" in text
    assert "WARNING: changes remain in the working tree" in text
    assert "src/inventory/stock.py" in text.split("WARNING")[1]


def test_invalid_model_output_is_readable_and_writes_nothing(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, log, *_ = supervised(root, "not a proposal")
    text = summarize(result, root)
    assert "reason: the model output was not a valid proposal" in text
    assert "approval" not in log and "WARNING" not in text


def test_reviewer_failure_is_readable_and_warns(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, *_ = supervised(
        root, proposal(), ModelResponseUncertainError("review response lost")
    )
    text = summarize(result, root)
    assert result.failure is TaskFailure.REVIEW_FAILED
    assert "reason: the review model call did not complete" in text
    assert "WARNING: changes remain in the working tree" in text


# Analyst exclusion and provider neutrality


def test_v01_runtime_has_no_analyst_or_evaluator_dependency() -> None:
    forbidden = (
        "legoai_engineering.analyst.sufficiency",
        "legoai_engineering.analyst.request_policy",
        "analyst_",
        "forgeai_eval",
        "evaluation",
    )
    for path in SOURCE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(forbidden), (path.name, node.module)
                names = {alias.name for alias in node.names}
                assert not names & {
                    "RepositoryAnalyst",
                    "repository_analyst_definition",
                }
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, forgeai.cli, forgeai.composition; "
            "print('\\n'.join(sorted(sys.modules)))",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    loaded = probe.stdout.splitlines()
    assert not any("sufficiency" in m or "request_policy" in m for m in loaded)
    assert not any(m.startswith(("analyst_", "forgeai_eval")) for m in loaded)


def test_ollama_route_is_configuration_only() -> None:
    text = (SOURCE / "cli.py").read_text(encoding="utf-8")
    assert "qwen" not in (SOURCE / "worker.py").read_text(encoding="utf-8")
    assert "qwen" not in (SOURCE / "domain.py").read_text(encoding="utf-8")
    assert '"--ollama-model", default="qwen2.5-coder:7b"' in text


# Docker readiness precheck (before any model call or effect)


@needs_docker_path
@pytest.mark.parametrize(
    ("failure", "action"),
    [
        (SandboxFailure.RUNTIME_UNAVAILABLE, "Start Docker Desktop"),
        (SandboxFailure.ENVIRONMENT_UNAVAILABLE, "never pulls or builds images"),
        (SandboxFailure.UNSUPPORTED, "Linux engine"),
        (SandboxFailure.TIMEOUT, "could not be confirmed"),
    ],
)
def test_docker_not_ready_refuses_before_any_model_call_or_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: SandboxFailure,
    action: str,
) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    calls: list[str] = []

    async def chat(self: ReplayModel, request: object) -> object:
        calls.append("model")
        raise AssertionError("model called before readiness")

    monkeypatch.setattr(ReplayModel, "chat", chat)
    out: list[str] = []

    def ask(prompt: str) -> str:
        calls.append("ask")
        return "y"

    code = main(
        cli(root, tmp_path),
        ask=ask,
        out=out.append,
        ready=lambda config: failure,
    )
    text = "\n".join(out)
    assert code == 2 and calls == []
    assert text.startswith("startup refused: ") and action in text
    assert "no model was called and nothing was written" in text
    assert "[1/7]" not in text and "Proposal" not in text and "Traceback" not in text
    assert snapshot(root) == before and git_clean(root)


@needs_docker_path
def test_readiness_runs_before_scope_and_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path)
    order: list[str] = []
    original = ReplayModel.chat

    async def chat(self: ReplayModel, request: object) -> object:
        order.append("model")
        return await original(self, request)  # type: ignore[arg-type]

    monkeypatch.setattr(ReplayModel, "chat", chat)

    def ready(config: object) -> None:
        order.append("ready")

    def out(line: str) -> None:
        if line.startswith("ForgeAI v0.1"):
            order.append("scope")

    assert main(cli(root, tmp_path), ask=lambda p: "n", out=out, ready=ready) == 1
    assert order == ["ready", "scope", "model"]


def test_adapter_reports_missing_or_invalid_docker_cli(tmp_path: Path) -> None:
    root = repository(tmp_path)
    missing = config(root, replay(), docker=tmp_path / "missing" / "docker.exe")
    assert sandbox_readiness(missing) is SandboxFailure.RUNTIME_UNAVAILABLE
    not_docker = config(root, replay(), docker=git_executable())
    assert sandbox_readiness(not_docker) is SandboxFailure.RUNTIME_UNAVAILABLE


@needs_docker_path
def test_real_docker_desktop_is_ready_for_the_checks_image(tmp_path: Path) -> None:
    """Qualified environment: metadata-only readiness; no workload runs."""
    root = repository(tmp_path)
    assert sandbox_readiness(config(root, replay(), docker=Path(str(DOCKER)))) is None


def test_readiness_stays_in_the_composition_root() -> None:
    for name in ("cli", "domain", "worker", "review", "guard"):
        text = (SOURCE / f"{name}.py").read_text(encoding="utf-8")
        assert "sandbox.docker" not in text and "subprocess" not in text, name
    composition = (SOURCE / "composition.py").read_text(encoding="utf-8")
    assert "verify_ready()" in composition and "subprocess" not in composition
