"""Operator-only sequential batches in a disposable clone; ADR-028 Proposed."""

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from legoai_engineering.coding.values import CodingTarget
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.sandbox.ports import SandboxExecutionPort

from demo import git_environment
from forgeai.cli import ReplayModel, ollama_binding, replay_binding, safe
from forgeai.composition import (
    discover_guidance,
    local_profile,
    prepare_run,
    sandbox_readiness,
)
from forgeai.domain import (
    CheckProfile,
    OperatorDecision,
    ProposalReview,
    TaskDisposition,
    TaskRequest,
    TaskResult,
)
from forgeai.guard import WorkspaceGuard
from forgeai.guidance import GuidanceRefusal, guidance_candidates, guidance_summary
from forgeai.policy import (
    DEFAULT_FORBIDDEN_NAMES,
    ApprovalPolicy,
    evaluate,
    exact_context_confirmer,
    policy_approver,
)
from forgeai.report import ModelBindingKind, encode_report, run_report


@dataclass(frozen=True, slots=True)
class BatchTask:
    identifier: str
    request: TaskRequest
    replay: tuple[str, ...]
    discover_guidance: bool


@dataclass(frozen=True, slots=True)
class TaskList:
    base: str
    binding: str
    ollama_model: str
    check_profile: CheckProfile
    tasks: tuple[BatchTask, ...]


@dataclass(frozen=True, slots=True)
class BatchSummary:
    branch: str
    base_sha: str
    commits: tuple[str, ...]
    dispositions: tuple[tuple[str, str], ...]
    stopped: str | None


def _read(path: Path, limit: int = 262144) -> str:
    with path.open("rb") as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("operator input exceeds byte bound")
    return raw.decode("utf-8")


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or any(type(item) is not str for item in value):
        raise ValueError("expected a string array")
    return tuple(value)


def _string(value: object) -> str:
    if type(value) is not str or not value or any(ord(c) < 32 for c in value):
        raise ValueError("expected nonempty single-line text")
    return value


def _integer(value: object) -> int:
    if type(value) is not int:
        raise ValueError("expected an integer")
    return value


def _boolean(value: object) -> bool:
    if type(value) is not bool:
        raise ValueError("expected a boolean")
    return value


def load_policy(path: Path) -> ApprovalPolicy:
    data = tomllib.loads(_read(path))
    if set(data) - {
        "max_changed_files",
        "max_total_bytes",
        "allow_create",
        "forbidden_names",
        "forbidden_prefixes",
        "require_review_accept",
        "max_tasks",
        "max_batch_minutes",
        "require_test_strength",
    }:
        raise ValueError("unknown policy field")
    return ApprovalPolicy(
        max_changed_files=_integer(data.get("max_changed_files", 8)),
        max_total_bytes=_integer(data.get("max_total_bytes", 24576)),
        allow_create=_boolean(data.get("allow_create", False)),
        forbidden_names=DEFAULT_FORBIDDEN_NAMES
        | frozenset(_strings(data.get("forbidden_names", []))),
        forbidden_prefixes=_strings(data.get("forbidden_prefixes", [])),
        require_review_accept=_boolean(data.get("require_review_accept", True)),
        max_tasks=_integer(data.get("max_tasks", 20)),
        max_batch_minutes=_integer(data.get("max_batch_minutes", 60)),
        require_test_strength=_boolean(data.get("require_test_strength", False)),
    )


def load_tasks(path: Path, policy: ApprovalPolicy) -> TaskList:
    data = tomllib.loads(_read(path))
    if set(data) - {"base", "binding", "ollama_model", "check_profile", "task"}:
        raise ValueError("unknown task-list field")
    binding = _string(data.get("binding"))
    if binding not in {"replay", "ollama"}:
        raise ValueError("only replay and local Ollama are admitted; REMOTE excluded")
    base = _string(data.get("base", "HEAD"))
    if base.startswith("-"):
        raise ValueError("base cannot be an option")
    model = _string(data.get("ollama_model", "qwen2.5-coder:14b"))
    profile = CheckProfile(_string(data.get("check_profile", "generic")))
    entries = data.get("task")
    if not isinstance(entries, list) or not 1 <= len(entries) <= policy.max_tasks:
        raise ValueError("task count exceeds policy or task list is empty")
    tasks: list[BatchTask] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) - {
            "id",
            "objective",
            "targets",
            "context",
            "constraints",
            "replay",
            "discover_guidance",
        }:
            raise ValueError("invalid task table")
        identifier = _string(entry.get("id"))
        if len(identifier) > 64 or any(
            char
            not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for char in identifier
        ):
            raise ValueError("task id requires 1..64 ASCII letters, digits, _ or -")
        targets = []
        for target in _strings(entry.get("targets")):
            create = target.endswith(":create")
            name = target[:-7] if create else target
            targets.append(
                CodingTarget(
                    RepositoryPath(name),
                    FileChangeKind.CREATE if create else FileChangeKind.UPDATE,
                )
            )
        request = TaskRequest(
            _string(entry.get("objective")),
            tuple(targets),
            _strings(entry.get("constraints", [])),
            tuple(RepositoryPath(item) for item in _strings(entry.get("context", []))),
        )
        outputs = []
        recordings = _strings(entry.get("replay", []))
        if (binding == "replay" and not 1 <= len(recordings) <= 4) or (
            binding != "replay" and recordings
        ):
            raise ValueError(
                "replay requires 1..4 recordings, local Ollama requires none"
            )
        for recording in recordings:
            relative = Path(recording)
            if relative.is_absolute() or relative.drive:
                raise ValueError("replay paths must be relative to the task file")
            outputs.append(_read(path.parent / relative))
        tasks.append(
            BatchTask(
                identifier,
                request,
                tuple(outputs),
                _boolean(entry.get("discover_guidance", False)),
            )
        )
    if len({task.identifier for task in tasks}) != len(tasks):
        raise ValueError("task ids must be unique")
    return TaskList(base, binding, model, profile, tuple(tasks))


@dataclass(frozen=True, slots=True)
class Git:
    executable: Path

    def run(self, repository: Path, *arguments: str) -> str:
        environment = git_environment()
        # Even status must not refresh the operator's index or run fsmonitor.
        environment["GIT_OPTIONAL_LOCKS"] = "0"
        environment["GIT_TERMINAL_PROMPT"] = "0"
        environment["GIT_LITERAL_PATHSPECS"] = "1"
        result = subprocess.run(
            [str(self.executable), "-c", "core.fsmonitor=false", *arguments],
            cwd=repository,
            env=environment,
            check=True,
            capture_output=True,
            timeout=120,
            shell=False,
        )
        return result.stdout.decode("utf-8").strip()


def _commit(
    git: Git, workspace: Path, branch: str, task: BatchTask, result: TaskResult
) -> str:
    if result.disposition is not TaskDisposition.SUCCEEDED:
        raise ValueError("only SUCCEEDED results may be committed")
    if git.run(workspace, "branch", "--show-current") != branch:
        raise ValueError("dedicated branch changed")
    before = git.run(workspace, "rev-parse", "HEAD")
    if result.evidence.start is None or result.evidence.start.head.commit is None:
        raise ValueError("missing run start identity")
    if before != result.evidence.start.head.commit.value:
        raise ValueError("HEAD changed after the run")
    paths = sorted(
        {
            change.path.value
            for attempt in result.evidence.attempts
            if attempt.applied is not None
            for change in attempt.applied.applied
        }
    )
    if not paths or git.run(workspace, "diff", "--cached", "--name-only", "-z"):
        raise ValueError("missing applied paths or unexpected staged changes")
    git.run(workspace, "add", "--", *paths)
    staged = set(
        filter(
            None,
            git.run(workspace, "diff", "--cached", "--name-only", "-z").split("\0"),
        )
    )
    if not staged or not staged <= set(paths):
        raise ValueError("staged paths do not match applied evidence")
    message = f"forgeai(batch): {task.identifier} {task.request.objective[:60]}"
    git.run(
        workspace,
        "-c",
        "user.name=ForgeAI batch",
        "-c",
        "user.email=batch@forgeai.invalid",
        "commit",
        "--no-gpg-sign",
        "-m",
        message,
        "-m",
        "ForgeAI-Run: " + result.evidence.run_id,
    )
    head = git.run(workspace, "rev-parse", "HEAD")
    if (
        git.run(workspace, "status", "--porcelain=v1", "--untracked-files=all")
        or git.run(workspace, "rev-list", "--parents", "-n", "1", "HEAD")
        != f"{head} {before}"
        or git.run(workspace, "rev-list", "--count", before + "..HEAD") != "1"
    ):
        raise ValueError("commit did not advance exactly once to a clean tree")
    return head


def review_commands(
    repository: Path, workspace: Path, base: str, branch: str
) -> tuple[str, ...]:
    # PowerShell single-quote escaping; these strings are printed, never executed.
    def quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    clone = quote(str(workspace))
    return (
        f"git -C {clone} log --oneline {base}..HEAD",
        f"git -C {clone} diff {base}..HEAD",
        "Optional operator import: git -C "
        + quote(str(repository))
        + f" fetch {clone} {branch}:{branch}",
        "Cleanup: delete " + quote(str(workspace.parent)) + " yourself when done.",
    )


def recording_approver(
    policy: ApprovalPolicy,
    evaluations: list[dict[str, object]],
) -> Callable[[ProposalReview], OperatorDecision]:
    approver = policy_approver(policy)

    def approve(review: ProposalReview) -> OperatorDecision:
        decision = approver(review)
        evaluation = evaluate(policy, review)
        evaluations.append(
            {
                "attempt": review.attempt,
                "approved": decision.approved,
                "rules": {rule.value: passed for rule, passed in evaluation.outcomes},
            }
        )
        return decision

    return approve


async def run_batch(
    repository: Path,
    tasks_file: Path,
    policy_file: Path,
    out_dir: Path,
    *,
    git: Git,
    docker: Path,
    uv: Path | None = None,
    sandbox: SandboxExecutionPort | None = None,
    out: Callable[[str], None] = print,
    json_report: bool = False,
    monotonic: Callable[[], float] = time.monotonic,
) -> BatchSummary:
    """Validate before creating anything; keep partial state on every failure.

    `sandbox` is a trusted Python test seam only, never a CLI/configuration option.
    """
    policy = load_policy(policy_file)
    task_list = load_tasks(tasks_file, policy)
    repository = repository.resolve(strict=True)
    original_output = out_dir
    out_dir = out_dir.resolve()
    if (
        original_output.is_symlink()
        or out_dir.exists()
        or out_dir.is_relative_to(repository)
    ):
        raise ValueError("output must be new and outside the operator repository")
    if not out_dir.parent.is_dir() or not (repository / ".git").is_dir():
        raise ValueError(
            "existing output parent and standalone operator repository required"
        )
    if (
        Path(git.run(repository, "rev-parse", "--show-toplevel")).resolve()
        != repository
    ):
        raise ValueError("operator repository must be its root")
    if git.run(repository, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ValueError("operator repository is dirty")
    base_sha = git.run(
        repository, "rev-parse", "--verify", task_list.base + "^{commit}"
    )
    if len(base_sha) not in {40, 64} or any(
        c not in "0123456789abcdef" for c in base_sha
    ):
        raise ValueError("invalid resolved base")
    branch = (
        "forgeai/batch-"
        + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid4().hex[:8]
    )
    if git.run(
        repository, "for-each-ref", "--format=%(refname)", "refs/heads/" + branch
    ):
        raise ValueError("batch branch already exists")
    workspace = out_dir / "workspace"
    deadline = monotonic() + policy.max_batch_minutes * 60
    commits: list[str] = []
    dispositions: list[tuple[str, str]] = []
    stopped = None
    out_dir.mkdir()
    try:
        git.run(
            out_dir,
            "clone",
            "--no-hardlinks",
            "--template=",
            str(repository),
            str(workspace),
        )
        git.run(workspace, "remote", "remove", "origin")
        git.run(workspace, "switch", "--create", branch, base_sha)
        if (
            git.run(workspace, "rev-parse", "HEAD") != base_sha
            or git.run(workspace, "status", "--porcelain=v1", "--untracked-files=all")
            or git.run(workspace, "remote")
            or not (workspace / ".git").is_dir()
        ):
            raise ValueError("clone isolation or starting state failed")
        with (out_dir / "batch-report.jsonl").open(
            "x", encoding="utf-8", newline="\n"
        ) as report:
            for task in task_list.tasks:
                if monotonic() >= deadline:
                    stopped = "batch deadline reached; no new task started"
                    break
                binding = (
                    replay_binding(ReplayModel(*task.replay))
                    if task_list.binding == "replay"
                    else ollama_binding(
                        "http://127.0.0.1:11434", task_list.ollama_model, 120.0
                    )
                )
                request = task.request
                config = local_profile(
                    workspace,
                    tuple(target.path for target in request.targets),
                    bindings=(binding,),
                    binding=task_list.binding,
                    git_executable=git.executable,
                    docker_executable=docker,
                    now=datetime.now(UTC),
                    context_paths=request.context,
                    check_profile=task_list.check_profile,
                    test_strength=policy.require_test_strength,
                    uv_executable=uv,
                )
                if task.discover_guidance:
                    inventory = await discover_guidance(
                        config, guidance_candidates(request)
                    )
                    if isinstance(inventory, GuidanceRefusal):
                        dispositions.append((task.identifier, "GUIDANCE_REFUSED"))
                        stopped = inventory.value
                        break
                    out(guidance_summary(inventory))
                    request = replace(
                        request, context=request.context + inventory.included_paths
                    )
                    config = replace(config, context_paths=request.context)
                if sandbox is None and config.check_profile is CheckProfile.GENERIC:
                    failure = sandbox_readiness(config)
                    if failure is not None:
                        dispositions.append((task.identifier, "SANDBOX_UNAVAILABLE"))
                        stopped = failure.value
                        break
                evaluations: list[dict[str, object]] = []
                prepared = prepare_run(
                    config,
                    WorkspaceGuard(),
                    approve=recording_approver(policy, evaluations),
                    confirm_context=exact_context_confirmer(
                        tuple(target.path for target in request.targets)
                        + request.context
                    ),
                    preflight=out,
                    progress=lambda stage, attempt: out(f"{stage.value}: {attempt}"),
                    sandbox=sandbox,
                )
                result = await prepared.worker.run(request, prepared.context)
                kind = ModelBindingKind[task_list.binding.upper()]
                payload = run_report(result, kind)
                payload["batch_task_id"] = task.identifier
                payload["policy_evaluations"] = evaluations
                encoded = encode_report(payload)
                report.write(encoded + "\n")
                report.flush()
                dispositions.append((task.identifier, result.disposition.name))
                if json_report:
                    out(encoded)
                if result.disposition is not TaskDisposition.SUCCEEDED:
                    stopped = (
                        result.failure.name if result.failure else "unsuccessful task"
                    )
                    break
                commits.append(_commit(git, workspace, branch, task, result))
    except Exception as error:
        # No retry or rollback: a failed commit can have happened. Retain evidence.
        stopped = (
            "operator step failed: " + type(error).__name__ + ": " + safe(str(error))
        )
        out("Batch stopped; clone retained; inspect HEAD for partial commit effects.")
    summary = BatchSummary(
        branch, base_sha, tuple(commits), tuple(dispositions), stopped
    )
    out("branch: " + branch)
    out("commits: " + json.dumps(commits))
    out("dispositions: " + json.dumps(dispositions))
    if stopped:
        out("stopped: " + stopped)
    for command in review_commands(repository, workspace, base_sha, branch):
        out(command)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo", "tasks", "policy", "out-dir"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--json-report", action="store_true")
    args = parser.parse_args(argv)
    executable = shutil.which("git")
    docker = shutil.which("docker")
    uv = shutil.which("uv")
    if executable is None or docker is None:
        parser.error("Git and the qualified Docker sandbox must already be installed")
    try:
        summary = asyncio.run(
            run_batch(
                args.repo,
                args.tasks.resolve(),
                args.policy.resolve(),
                args.out_dir,
                git=Git(Path(executable).resolve()),
                docker=Path(docker).resolve(),
                uv=Path(uv).resolve() if uv else None,
                json_report=args.json_report,
                out=lambda message: print(safe(message)),
            )
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print("Batch refused: " + safe(str(error)))
        return 2
    return 1 if summary.stopped else 0


if __name__ == "__main__":
    sys.exit(main())
