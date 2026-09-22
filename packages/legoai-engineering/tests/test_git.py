"""M3 contracts and real temporary-repository observations; user-run only."""

import os
import shutil
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from legoai_engineering.git._config import check_config
from legoai_engineering.git._parse import check_index, parse_status
from legoai_engineering.git._process import GitCommand, capture
from legoai_engineering.git.errors import GitError, GitFailure
from legoai_engineering.git.local import (
    GitReadPolicy,
    LocalGitExecutable,
    LocalGitRepository,
)
from legoai_engineering.git.ports import GitRepositoryPort
from legoai_engineering.git.values import (
    GitChange,
    GitCommitId,
    GitHead,
    GitHeadKind,
    GitRepositoryState,
    GitStatusEntry,
)
from legoai_engineering.repository.errors import WorkspaceBoundaryError
from legoai_engineering.repository.local import LocalWorkspaceRoot
from legoai_engineering.repository.workspace import RepositoryPath


@pytest.fixture
def git() -> Path:
    found = shutil.which("git")
    if found is None:
        pytest.fail("M3 qualification requires an installed Git executable")
    return Path(found).absolute()


def setup_git(git: Path, root: Path, *args: str) -> str:
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
    }
    if os.name == "nt":
        environment["SystemRoot"] = os.environ["SystemRoot"]
    result = subprocess.run(
        [str(git), *args],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path, git: Path) -> Path:
    root = tmp_path / "repository with spaces"
    root.mkdir()
    setup_git(git, root, "init", "--initial-branch=main", "--template=")
    setup_git(git, root, "config", "--local", "user.name", "M3 Fixture")
    setup_git(git, root, "config", "--local", "user.email", "m3@example.invalid")
    return root


def adapter(root: Path, git: Path) -> LocalGitRepository:
    return LocalGitRepository(
        LocalWorkspaceRoot(root),
        LocalGitExecutable(git),
        GitReadPolicy(5, 262_144, 4096, 4096),
    )


def commit(root: Path, git: Path) -> str:
    setup_git(git, root, "add", "--all")
    setup_git(git, root, "commit", "-m", "fixture")
    return setup_git(git, root, "rev-parse", "HEAD")


def snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


def test_unborn_clean_attached_detached_and_no_mutation(
    repository: Path, git: Path
) -> None:
    port: GitRepositoryPort = adapter(repository, git)
    before = snapshot(repository)
    initial = port.inspect()
    assert initial == GitRepositoryState(GitHead(GitHeadKind.UNBORN, "main", None), ())
    assert snapshot(repository) == before
    (repository / "tracked.txt").write_text("original\n", encoding="utf-8")
    oid = commit(repository, git)
    before = snapshot(repository)
    clean = port.inspect()
    assert clean.head == GitHead(GitHeadKind.ATTACHED, "main", GitCommitId(oid))
    assert clean.entries == ()
    assert snapshot(repository) == before
    setup_git(git, repository, "checkout", "--detach", oid)
    before = snapshot(repository)
    detached = port.inspect()
    assert detached.head == GitHead(GitHeadKind.DETACHED, None, GitCommitId(oid))
    assert snapshot(repository) == before


def test_status_columns_paths_order_ignored_and_no_mutation(
    repository: Path, git: Path
) -> None:
    for name in ("both.txt", "deleted.txt", "staged-delete.txt", "modified.txt"):
        (repository / name).write_text("original\n", encoding="utf-8")
    (repository / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    commit(repository, git)
    (repository / "both.txt").write_text("staged\n", encoding="utf-8")
    (repository / "staged-delete.txt").unlink()
    (repository / "new.txt").write_text("new\n", encoding="utf-8")
    setup_git(git, repository, "add", "--all")
    (repository / "both.txt").write_text("unstaged\n", encoding="utf-8")
    (repository / "modified.txt").write_text("modified\n", encoding="utf-8")
    (repository / "deleted.txt").unlink()
    hostile_names = (
        "--dangerous-name.txt",
        "sp ace.txt",
        "café.txt",
        "$(touch SENTINEL).txt",
    )
    for name in hostile_names:
        (repository / name).write_text("untracked\n", encoding="utf-8")
    (repository / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    before = snapshot(repository)
    state = adapter(repository, git).inspect()
    assert snapshot(repository) == before
    paths = [entry.path.value for entry in state.entries]
    assert paths == sorted(paths)
    status = {entry.path.value: entry for entry in state.entries}
    assert "ignored.txt" not in status
    assert not (repository / "SENTINEL").exists()
    assert status["both.txt"].index is GitChange.MODIFIED
    assert status["both.txt"].worktree is GitChange.MODIFIED
    assert status["modified.txt"].index is GitChange.UNCHANGED
    assert status["modified.txt"].worktree is GitChange.MODIFIED
    assert status["new.txt"].index is GitChange.ADDED
    assert status["deleted.txt"].worktree is GitChange.DELETED
    assert status["staged-delete.txt"].index is GitChange.DELETED
    assert all(status[name].untracked for name in hostile_names)


def test_environment_cannot_redirect_or_write(
    repository: Path, git: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trace = tmp_path / "trace-secret.txt"
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "wrong"))
    monkeypatch.setenv("GIT_TRACE", str(trace))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "secret-helper")
    assert adapter(repository, git).inspect().head.kind is GitHeadKind.UNBORN
    assert not trace.exists()


def test_detection_and_no_parent_discovery(
    repository: Path, git: Path, tmp_path: Path
) -> None:
    missing = adapter(repository, tmp_path / "missing-git.exe")
    with pytest.raises(GitError) as caught:
        missing.inspect()
    assert caught.value.reason is GitFailure.UNAVAILABLE
    child = repository / "child"
    child.mkdir()
    with pytest.raises(GitError) as caught:
        adapter(child, git).inspect()
    assert caught.value.reason is GitFailure.NOT_REPOSITORY
    (child / ".git").mkdir()
    with pytest.raises(GitError) as caught:
        adapter(child, git).inspect()
    assert caught.value.reason is GitFailure.INVALID_REPOSITORY


def test_gitfile_bare_and_nested_are_explicitly_unsupported(
    tmp_path: Path, repository: Path, git: Path
) -> None:
    gitfile_root = tmp_path / "gitfile"
    gitfile_root.mkdir()
    (gitfile_root / ".git").write_text("gitdir: ../outside\n", encoding="utf-8")
    bare = tmp_path / "bare"
    bare.mkdir()
    setup_git(git, bare, "init", "--bare", "--template=")
    nested = repository / "nested"
    nested.mkdir()
    setup_git(git, nested, "init", "--template=")
    for root in (gitfile_root, bare, repository):
        with pytest.raises(GitError) as caught:
            adapter(root, git).inspect()
        assert caught.value.reason is GitFailure.UNSUPPORTED


def test_actual_linked_worktree_is_rejected(
    repository: Path, git: Path, tmp_path: Path
) -> None:
    (repository / "a").write_text("a", encoding="utf-8")
    commit(repository, git)
    linked = tmp_path / "linked worktree"
    setup_git(git, repository, "worktree", "add", "--detach", str(linked))
    before = snapshot(repository)
    with pytest.raises(GitError) as caught:
        adapter(linked, git).inspect()
    assert caught.value.reason is GitFailure.UNSUPPORTED
    assert snapshot(repository) == before


@pytest.mark.parametrize("name", ["alternates", "Alternates"])
def test_external_object_storage_rejected_before_git(
    name: str, repository: Path, git: Path, tmp_path: Path
) -> None:
    info = repository / ".git" / "objects" / "info"
    (info / name).write_text(str(tmp_path / "outside"), encoding="utf-8")
    with pytest.raises(GitError) as caught:
        adapter(repository, git).inspect()
    assert caught.value.reason is GitFailure.UNSUPPORTED


@pytest.mark.parametrize(
    "config",
    [
        "[include]\npath = /outside\n",
        '[includeIf "gitdir:*"]\npath = /outside\n',
        "[core]\nfsmonitor = !secret-helper\n",
        "[core]\nworktree = /outside\n",
        '[filter "evil"]\nprocess = secret-helper\n',
        "[extensions]\npartialclone = origin\n",
        "[core]\nbare = true\n",
        "[core]\nfilemode = true\\\nfalse\n",
    ],
)
def test_config_rejected_before_process(
    config: str, repository: Path, git: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repository / ".git" / "config").write_text(config, encoding="utf-8")

    def denied(*args: str) -> bytes:
        pytest.fail("unsupported config reached Git execution")

    monkeypatch.setattr("legoai_engineering.git.local.capture", denied)
    with pytest.raises(GitError) as caught:
        adapter(repository, git).inspect()
    assert caught.value.reason is GitFailure.UNSUPPORTED


def test_corruption_command_failure_and_status_entry_limit(
    repository: Path, git: Path
) -> None:
    for name in ("a", "b"):
        (repository / name).write_text("x", encoding="utf-8")
    limited = LocalGitRepository(
        LocalWorkspaceRoot(repository),
        LocalGitExecutable(git),
        GitReadPolicy(5, 4096, 1, 4096),
    )
    with pytest.raises(GitError) as caught:
        limited.inspect()
    assert caught.value.reason is GitFailure.ENTRY_LIMIT
    (repository / ".git" / "HEAD").write_text("broken HEAD\n", encoding="utf-8")
    with pytest.raises(GitError) as caught:
        adapter(repository, git).inspect()
    assert caught.value.reason is GitFailure.COMMAND
    assert "broken" not in str(caught.value)


@pytest.mark.parametrize("size", [40, 64, 96])
def test_opaque_commit_identity(size: int) -> None:
    assert GitCommitId("a" * size).value == "a" * size


def test_public_value_invariants() -> None:
    policy = GitReadPolicy(1, 10, 1, 1)
    with pytest.raises(TypeError):
        replace(policy, timeout_seconds=True)
    with pytest.raises(ValueError):
        replace(policy, max_output_bytes=0)
    with pytest.raises(ValueError):
        GitCommitId("0" * 40)
    with pytest.raises(ValueError):
        GitHead(GitHeadKind.DETACHED, "main", GitCommitId("a" * 40))
    with pytest.raises(ValueError):
        GitHead(GitHeadKind.ATTACHED, "main", None)
    entry = GitStatusEntry(
        RepositoryPath("a"), GitChange.UNCHANGED, GitChange.UNCHANGED, True
    )
    with pytest.raises(FrozenInstanceError):
        entry.untracked = False  # type: ignore[misc]
    with pytest.raises(ValueError):
        GitRepositoryState(GitHead(GitHeadKind.UNBORN, "main", None), (entry, entry))


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        (b"\xff\0", GitFailure.DECODE),
        (b"unterminated", GitFailure.FORMAT),
        (b"# branch.head main\0", GitFailure.FORMAT),
        (b"u conflict\0", GitFailure.UNSUPPORTED),
        (b"2 rename\0", GitFailure.UNSUPPORTED),
        (b"! ignored\0", GitFailure.FORMAT),
    ],
)
def test_parser_fails_without_partial_results(data: bytes, reason: GitFailure) -> None:
    with pytest.raises(GitError) as caught:
        parse_status(data, 10)
    assert caught.value.reason is reason


def test_unsupported_paths_and_index_entries_fail_closed() -> None:
    with pytest.raises(WorkspaceBoundaryError):
        parse_status(b"? line\nbreak\0", 10)
    for mode, stage in (("160000", "0"), ("120000", "0"), ("100644", "2")):
        record = f"{mode} {'a' * 40} {stage}\tpath\0".encode()
        with pytest.raises(GitError) as caught:
            check_index(record, 10)
        assert caught.value.reason is GitFailure.UNSUPPORTED


@pytest.mark.parametrize(
    ("script", "reason"),
    [
        ("import time; time.sleep(10)", GitFailure.TIMEOUT),
        (
            "import sys; sys.stdout.buffer.write(b'x' * 1000000)",
            GitFailure.OUTPUT_LIMIT,
        ),
        (
            "import sys; sys.stderr.buffer.write(b'x' * 1000000)",
            GitFailure.OUTPUT_LIMIT,
        ),
        ("import sys; sys.stderr.write('secret'); sys.exit(2)", GitFailure.COMMAND),
        ("import sys; sys.stderr.write('warning')", GitFailure.COMMAND),
        ("import sys; sys.stdout.buffer.write(b'x' * 128)", None),
    ],
)
def test_real_child_capture_is_bounded(
    script: str,
    reason: GitFailure | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = subprocess.Popen
    children: list[subprocess.Popen[bytes]] = []

    def controlled_child(
        args: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        stdin: int,
        stdout: int,
        stderr: int,
        shell: bool,
        bufsize: int,
    ) -> subprocess.Popen[bytes]:
        assert shell is False
        assert args[-3:] == ["ls-files", "--stage", "-z"]
        assert "PATH" not in env and env["GIT_OPTIONAL_LOCKS"] == "0"
        child = original(
            [sys.executable, "-I", "-c", script],
            cwd=cwd,
            env=env,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            shell=shell,
            bufsize=bufsize,
        )
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", controlled_child)
    if reason is None:
        data = capture(Path(sys.executable), tmp_path, 1, 128, GitCommand.INDEX)
        assert data == b"x" * 128
    else:
        with pytest.raises(GitError) as caught:
            capture(Path(sys.executable), tmp_path, 1, 128, GitCommand.INDEX)
        assert caught.value.reason is reason
        assert "secret" not in str(caught.value)
    assert all(child.poll() is not None for child in children)
    assert all(child.stdout is not None and child.stdout.closed for child in children)
    assert all(child.stderr is not None and child.stderr.closed for child in children)


def test_config_accepts_only_documented_inert_subset() -> None:
    check_config(
        "[core]\nrepositoryformatversion = 1\nbare = false\n"
        "[extensions]\nobjectformat = sha256\n"
        '[remote "origin"]\nurl = https://example.invalid/repository\n'
        "fetch = +refs/heads/*:refs/remotes/origin/*\n"
        '[branch "main"]\nremote = origin\nmerge = refs/heads/main\n'
    )


def test_sha256_commit(repository: Path, git: Path) -> None:
    root = repository / "sha256"
    root.mkdir()
    setup_git(
        git,
        root,
        "init",
        "--object-format=sha256",
        "--initial-branch=main",
        "--template=",
    )
    setup_git(git, root, "config", "--local", "user.name", "M3 Fixture")
    setup_git(git, root, "config", "--local", "user.email", "m3@example.invalid")
    (root / "a").write_text("a", encoding="utf-8")
    oid = commit(root, git)
    assert len(oid) == 64
    assert adapter(root, git).inspect().head.commit == GitCommitId(oid)


def test_staged_rename_is_delete_and_add(repository: Path, git: Path) -> None:
    (repository / "old").write_text("content", encoding="utf-8")
    commit(repository, git)
    (repository / "old").rename(repository / "new")
    setup_git(git, repository, "add", "--all")
    state = adapter(repository, git).inspect()
    assert [(entry.path.value, entry.index) for entry in state.entries] == [
        ("new", GitChange.ADDED),
        ("old", GitChange.DELETED),
    ]


def test_hardlink_boundary_applies_before_git(repository: Path, git: Path) -> None:
    source = repository / "a"
    source.write_text("text", encoding="utf-8")
    os.link(source, repository / "b")
    with pytest.raises(WorkspaceBoundaryError):
        adapter(repository, git).inspect()


def test_scan_budget(repository: Path, git: Path) -> None:
    port = LocalGitRepository(
        LocalWorkspaceRoot(repository),
        LocalGitExecutable(git),
        GitReadPolicy(5, 4096, 10, 1),
    )
    with pytest.raises(GitError) as caught:
        port.inspect()
    assert caught.value.reason is GitFailure.ENTRY_LIMIT


def test_upstream_config_is_inert(repository: Path, git: Path) -> None:
    (repository / "a").write_text("a", encoding="utf-8")
    commit(repository, git)
    setup_git(git, repository, "config", "--local", "branch.main.remote", ".")
    setup_git(
        git, repository, "config", "--local", "branch.main.merge", "refs/heads/main"
    )
    state = adapter(repository, git).inspect()
    assert state.head.branch == "main" and state.entries == ()


def test_example_accepts_supplied_repository(repository: Path, git: Path) -> None:
    assert git.is_file()
    example = Path(__file__).resolve().parents[1] / "examples" / "git_intake.py"
    before = snapshot(repository)
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(example), str(repository)],
        cwd=repository,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [
        "head: unborn",
        "branch: main",
        "commit: -",
        "changes: 0",
    ]
    assert snapshot(repository) == before
