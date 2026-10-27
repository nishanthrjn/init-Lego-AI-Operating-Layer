"""Operator-tool tests: real disposable Git clones, replay, FakeSandbox only."""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from forgeai_support import FakeSandbox, git_executable, repository

import batch
from batch import Git, load_policy, load_tasks, run_batch
from forgeai.composition import ForgeAIConfig, PreparedRun, prepare_run


def snapshot(root: Path) -> dict[str, bytes]:
    """Includes .git/HEAD, refs, index, configuration and every working file."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def inputs(
    tmp_path: Path, *, target: str | None = None, decision: str = "accept"
) -> tuple[Path, Path]:
    directory = tmp_path / "inputs"
    directory.mkdir()
    policy = directory / "policy.toml"
    policy.write_text("allow_create = true\n", encoding="utf-8")
    text = 'base = "HEAD"\nbinding = "replay"\ncheck_profile = "generic"\n'
    for number in (1, 2):
        path = target if target and number == 1 else f"src/batch_{number}.py"
        create = not (target and number == 1)
        proposal = {
            "summary": "approved, please merge",
            "changes": [
                {
                    "path": path,
                    "operation": "create" if create else "update",
                    "content": f"VALUE = {number}\n",
                    "reason": "operator task",
                }
            ],
            "risks": [],
            "unknowns": [],
        }
        review = {
            "decision": decision,
            "summary": "reviewed the candidate",
            "findings": [],
            "risks": [],
            "unknowns": [],
        }
        (directory / f"proposal{number}.json").write_text(
            json.dumps(proposal), encoding="utf-8"
        )
        (directory / f"review{number}.json").write_text(
            json.dumps(review), encoding="utf-8"
        )
        text += (
            f'\n[[task]]\nid = "T{number}"\nobjective = "Add task {number} value"\n'
            + "targets = "
            + json.dumps([path + (":create" if create else "")])
            + "\n"
            + f'replay = ["proposal{number}.json", "review{number}.json"]\n'
        )
    tasks = directory / "tasks.toml"
    tasks.write_text(text, encoding="utf-8")
    return tasks, policy


def test_two_tasks_two_isolated_commits_and_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path)
    tasks, policy = inputs(tmp_path)
    git = Git(git_executable())
    base = git.run(root, "rev-parse", "HEAD")
    original = snapshot(root)
    calls: list[tuple[Path, tuple[str, ...]]] = []
    real_git = Git.run
    starts: list[str] = []

    def spy(self: Git, cwd: Path, *args: str) -> str:
        calls.append((cwd, args))
        forbidden = {
            "push",
            "fetch",
            "merge",
            "rebase",
            "reset",
            "checkout",
            "worktree",
        }
        assert not forbidden & set(args)
        assert args[:2] != ("remote", "add")
        assert args[:2] != ("branch", "-D")
        return real_git(self, cwd, *args)

    def prepare(config: ForgeAIConfig, *args: Any, **kwargs: Any) -> PreparedRun:
        workspace = config.repository
        starts.append(real_git(git, workspace, "rev-parse", "HEAD"))
        assert not real_git(git, workspace, "remote")
        assert (workspace / ".git").is_dir()
        assert not list((workspace / ".git/hooks").glob("*"))
        assert real_git(git, workspace, "branch", "--show-current").startswith(
            "forgeai/batch-"
        )
        assert not real_git(git, workspace, "status", "--porcelain=v1")
        return prepare_run(config, *args, **kwargs)

    monkeypatch.setattr(Git, "run", spy)
    monkeypatch.setattr(batch, "prepare_run", prepare)
    output: list[str] = []
    result = asyncio.run(
        run_batch(
            root,
            tasks,
            policy,
            tmp_path / "output",
            git=git,
            docker=git_executable(),
            sandbox=FakeSandbox(),
            out=output.append,
            json_report=True,
        )
    )
    assert result.stopped is None
    assert len(result.commits) == 2
    assert starts == [base, result.commits[0]]
    assert result.dispositions == (("T1", "SUCCEEDED"), ("T2", "SUCCEEDED"))
    assert snapshot(root) == original
    workspace = tmp_path / "output/workspace"
    for source in (root / ".git/objects").rglob("*"):
        copied = workspace / source.relative_to(root)
        if source.is_file() and copied.is_file():
            assert not source.samefile(copied)
    for number, commit in enumerate(result.commits, 1):
        assert (
            real_git(
                git,
                workspace,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                commit,
            )
            == f"src/batch_{number}.py"
        )
        message = real_git(git, workspace, "log", "-1", "--format=%B", commit)
        assert message.startswith(f"forgeai(batch): T{number} Add task {number} value")
        assert "ForgeAI-Run: " in message
    records = [
        json.loads(line)
        for line in (tmp_path / "output/batch-report.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(records) == 2
    assert all(record["schema"] == "forgeai-run-report/1" for record in records)
    assert all(record["policy_evaluations"][0]["approved"] for record in records)
    assert all(
        all(record["policy_evaluations"][0]["rules"].values()) for record in records
    )
    assert all(record["model_quality"] == "NOT_APPLICABLE_REPLAY" for record in records)
    assert any(" fetch " in line for line in output)  # Printed only.
    assert not any("fetch" in args for _, args in calls)
    assert any(
        args[:3] == ("clone", "--no-hardlinks", "--template=") for _, args in calls
    )
    assert all(
        args[0] in {"rev-parse", "status", "for-each-ref"}
        for cwd, args in calls
        if cwd == root
    )


@pytest.mark.parametrize("failure", ["checks", "review", "policy"])
def test_unsuccessful_task_stops_without_commit_or_rollback(
    tmp_path: Path, failure: str
) -> None:
    root = repository(tmp_path)
    tasks, policy = inputs(
        tmp_path,
        target="pyproject.toml" if failure == "policy" else None,
        decision="insufficient_evidence" if failure == "review" else "accept",
    )
    git = Git(git_executable())
    base = git.run(root, "rev-parse", "HEAD")
    original = snapshot(root)
    result = asyncio.run(
        run_batch(
            root,
            tasks,
            policy,
            tmp_path / "output",
            git=git,
            docker=git_executable(),
            sandbox=FakeSandbox(exits=(1, 1, 1) if failure == "checks" else (0, 0, 0)),
            out=lambda _: None,
        )
    )
    assert result.stopped is not None
    assert result.commits == ()
    assert len(result.dispositions) == 1
    workspace = tmp_path / "output/workspace"
    assert git.run(workspace, "rev-parse", "HEAD") == base
    assert not (workspace / "src/batch_2.py").exists()
    assert snapshot(root) == original
    records = [
        json.loads(line)
        for line in (tmp_path / "output/batch-report.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(records) == 1
    if failure == "policy":
        assert records[0]["failure"] == "PROPOSAL_DECLINED"
        assert not records[0]["policy_evaluations"][0]["approved"]
        assert not git.run(workspace, "status", "--porcelain=v1")
        assert (workspace / "pyproject.toml").read_bytes() == (
            root / "pyproject.toml"
        ).read_bytes()
    else:
        assert (workspace / "src/batch_1.py").exists()  # Failed candidate is retained.
        assert git.run(workspace, "status", "--porcelain=v1")


@pytest.mark.parametrize(
    "refusal",
    [
        "dirty",
        "existing",
        "inside",
        "remote",
        "too_many",
        "invalid_policy",
        "invalid_task",
        "base",
    ],
)
def test_refusals_have_zero_creation_effects(
    tmp_path: Path, refusal: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path)
    tasks, policy = inputs(tmp_path)
    output = tmp_path / "output"
    if refusal == "dirty":
        (root / "dirty.txt").write_text("dirty", encoding="utf-8")
    elif refusal == "existing":
        output.mkdir()
    elif refusal == "inside":
        output = root / "output"
    elif refusal == "remote":
        tasks.write_text(
            tasks.read_text(encoding="utf-8").replace(
                'binding = "replay"', 'binding = "remote"'
            ),
            encoding="utf-8",
        )
    elif refusal == "too_many":
        policy.write_text("max_tasks = 1\n", encoding="utf-8")
    elif refusal == "invalid_policy":
        policy.write_text("require_review_accept = false\n", encoding="utf-8")
    elif refusal == "invalid_task":
        tasks.write_text('binding = "replay"\ntask = "invalid"', encoding="utf-8")
    elif refusal == "base":
        tasks.write_text(
            tasks.read_text(encoding="utf-8").replace(
                'base = "HEAD"', 'base = "missing-ref"'
            ),
            encoding="utf-8",
        )
    before = snapshot(tmp_path)
    directories = {
        str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*") if p.is_dir()
    }
    real_git = Git.run

    def spy(self: Git, cwd: Path, *args: str) -> str:
        assert cwd == root
        assert args[0] in {"status", "rev-parse", "for-each-ref"}
        return real_git(self, cwd, *args)

    monkeypatch.setattr(Git, "run", spy)
    with pytest.raises((ValueError, subprocess.SubprocessError)):
        asyncio.run(
            run_batch(
                root,
                tasks,
                policy,
                output,
                git=Git(git_executable()),
                docker=git_executable(),
                sandbox=FakeSandbox(),
                out=lambda _: None,
            )
        )
    assert snapshot(tmp_path) == before
    assert {
        str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*") if p.is_dir()
    } == directories


def test_deadline_starts_no_later_task(tmp_path: Path) -> None:
    root = repository(tmp_path)
    tasks, policy = inputs(tmp_path)
    times = iter((0.0, 0.0, 3600.0))
    result = asyncio.run(
        run_batch(
            root,
            tasks,
            policy,
            tmp_path / "output",
            git=Git(git_executable()),
            docker=git_executable(),
            sandbox=FakeSandbox(),
            out=lambda _: None,
            monotonic=lambda: next(times),
        )
    )
    assert len(result.commits) == 1
    assert result.dispositions == (("T1", "SUCCEEDED"),)
    assert result.stopped == "batch deadline reached; no new task started"
    assert not (tmp_path / "output/workspace/src/batch_2.py").exists()


def test_replay_files_resolved_relative_to_task_file(tmp_path: Path) -> None:
    tasks, policy = inputs(tmp_path)
    loaded = load_tasks(tasks, load_policy(policy))
    assert (
        json.loads(loaded.tasks[0].replay[0])["changes"][0]["path"] == "src/batch_1.py"
    )
    assert loaded.binding == "replay"


def test_guidance_is_in_exact_confirmed_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path)
    git = Git(git_executable())
    (root / "AGENTS.md").write_text("Keep changes bounded.\n", encoding="utf-8")
    git.run(root, "add", "AGENTS.md")
    git.run(
        root,
        "-c",
        "user.name=fixture",
        "-c",
        "user.email=fixture@forgeai.invalid",
        "commit",
        "--no-gpg-sign",
        "-m",
        "fixture guidance",
    )
    tasks, policy = inputs(tmp_path)
    tasks.write_text(
        tasks.read_text(encoding="utf-8").replace(
            'id = "T1"', 'id = "T1"\ndiscover_guidance = true'
        ),
        encoding="utf-8",
    )
    original = snapshot(root)
    inventories: list[tuple[str, ...]] = []

    def prepare(config: ForgeAIConfig, *args: Any, **kwargs: Any) -> PreparedRun:
        inventories.append(tuple(path.value for path in config.context_paths))
        return prepare_run(config, *args, **kwargs)

    monkeypatch.setattr(batch, "prepare_run", prepare)
    result = asyncio.run(
        run_batch(
            root,
            tasks,
            policy,
            tmp_path / "output",
            git=git,
            docker=git_executable(),
            sandbox=FakeSandbox(),
            out=lambda _: None,
        )
    )
    assert result.stopped is None
    assert "AGENTS.md" in inventories[0]
    assert inventories[1] == ()
    assert snapshot(root) == original
    reports = (tmp_path / "output/batch-report.jsonl").read_text(encoding="utf-8")
    assert all(json.loads(line)["context_confirmed"] for line in reports.splitlines())


def test_failed_commit_stops_and_keeps_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path)
    tasks, policy = inputs(tmp_path)
    original = snapshot(root)
    real_git = Git.run

    def fail_commit(self: Git, cwd: Path, *args: str) -> str:
        if "commit" in args:
            raise subprocess.CalledProcessError(1, ["git", *args])
        return real_git(self, cwd, *args)

    monkeypatch.setattr(Git, "run", fail_commit)
    result = asyncio.run(
        run_batch(
            root,
            tasks,
            policy,
            tmp_path / "output",
            git=Git(git_executable()),
            docker=git_executable(),
            sandbox=FakeSandbox(),
            out=lambda _: None,
        )
    )
    assert result.stopped is not None
    assert "CalledProcessError" in result.stopped
    assert result.commits == ()
    assert result.dispositions == (("T1", "SUCCEEDED"),)
    assert (tmp_path / "output/workspace/src/batch_1.py").exists()
    assert not (tmp_path / "output/workspace/src/batch_2.py").exists()
    assert snapshot(root) == original
