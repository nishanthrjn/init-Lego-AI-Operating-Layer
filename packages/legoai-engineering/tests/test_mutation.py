"""M4 preconditions, exact effects, boundary failures and partial application."""

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from legoai_engineering.git.local import (
    GitReadPolicy,
    LocalGitExecutable,
    LocalGitRepository,
)
from legoai_engineering.git.values import GitChange
from legoai_engineering.repository.errors import (
    WorkspaceBoundaryError,
    WorkspaceError,
    WorkspaceFailure,
)
from legoai_engineering.repository.local import LocalWorkspaceRoot
from legoai_engineering.repository.mutation import (
    ContentDigest,
    FileChange,
    FileChangeKind,
    RepositoryChangeSet,
    digest_text,
)
from legoai_engineering.repository.mutation_errors import (
    MutationApplyError,
    MutationConflict,
    MutationConflictReason,
)
from legoai_engineering.repository.mutation_local import LocalRepositoryMutation
from legoai_engineering.repository.mutation_ports import RepositoryMutationPort
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy


def policy() -> WorkspacePolicy:
    return WorkspacePolicy(4096, 1024, 128, 8, (".venv",))


def adapter(root: Path) -> LocalRepositoryMutation:
    return LocalRepositoryMutation(LocalWorkspaceRoot(root), policy())


def create(path: str, text: str) -> FileChange:
    return FileChange(RepositoryPath(path), FileChangeKind.CREATE, None, text)


def update(path: str, old: str, new: str) -> FileChange:
    return FileChange(
        RepositoryPath(path), FileChangeKind.UPDATE, digest_text(old), new
    )


def delete(path: str, old: str) -> FileChange:
    return FileChange(
        RepositoryPath(path), FileChangeKind.DELETE, digest_text(old), None
    )


def test_mixed_success_preserves_exact_bytes_and_order(tmp_path: Path) -> None:
    root = tmp_path / "workspace with spaces"
    root.mkdir()
    (root / "old.txt").write_bytes(b"old\r\n")
    (root / "gone.txt").write_bytes(b"remove")
    port: RepositoryMutationPort = adapter(root)
    changes = RepositoryChangeSet(
        (
            create("café file.txt", "😀\r\nnext\n"),
            update("old.txt", "old\r\n", "new\n"),
            delete("gone.txt", "remove"),
        )
    )
    result = port.apply(changes)
    assert [item.path for item in result.applied] == [
        item.path for item in changes.changes
    ]
    assert (root / "café file.txt").read_bytes() == "😀\r\nnext\n".encode()
    assert (root / "old.txt").read_bytes() == b"new\n"
    assert not (root / "gone.txt").exists()
    assert result.applied[0].before is None
    assert result.applied[0].after == digest_text("😀\r\nnext\n")
    assert result.applied[1].before == digest_text("old\r\n")
    assert result.applied[2].after is None
    assert not list(root.glob(".legoai-*.tmp"))


@pytest.mark.parametrize("name", ["--help", "$(command)", "file;rm", ".hidden"])
def test_names_are_data_and_empty_content_supported(tmp_path: Path, name: str) -> None:
    adapter(tmp_path).apply(RepositoryChangeSet((create(name, ""),)))
    assert (tmp_path / name).read_bytes() == b""


@pytest.mark.parametrize("kind", [FileChangeKind.UPDATE, FileChangeKind.DELETE])
def test_stale_and_missing_are_conflicts(tmp_path: Path, kind: FileChangeKind) -> None:
    change = FileChange(
        RepositoryPath("a"),
        kind,
        digest_text("old"),
        "new" if kind is FileChangeKind.UPDATE else None,
    )
    with pytest.raises(MutationConflict) as caught:
        adapter(tmp_path).apply(RepositoryChangeSet((change,)))
    assert caught.value.reason is MutationConflictReason.MISSING
    (tmp_path / "a").write_bytes(b"externally changed")
    with pytest.raises(MutationConflict) as caught:
        adapter(tmp_path).apply(RepositoryChangeSet((change,)))
    assert caught.value.reason is MutationConflictReason.STALE
    assert (tmp_path / "a").read_bytes() == b"externally changed"


def test_create_existing_conflict(tmp_path: Path) -> None:
    (tmp_path / "a").write_bytes(b"existing")
    with pytest.raises(MutationConflict) as caught:
        adapter(tmp_path).apply(RepositoryChangeSet((create("a", "new"),)))
    assert caught.value.reason is MutationConflictReason.EXISTS
    assert (tmp_path / "a").read_bytes() == b"existing"


def test_create_publication_never_overwrites_late_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = os.link

    def late_create(source: Path, target: Path) -> None:
        target.write_bytes(b"external")
        original(source, target)

    monkeypatch.setattr(os, "link", late_create)
    with pytest.raises(MutationApplyError) as caught:
        adapter(tmp_path).apply(RepositoryChangeSet((create("a", "proposal"),)))
    assert caught.value.completed.applied == ()
    assert caught.value.uncertain == RepositoryPath("a")
    assert isinstance(caught.value.__cause__, FileExistsError)
    assert (tmp_path / "a").read_bytes() == b"external"
    assert not list(tmp_path.glob(".legoai-*.tmp"))


def test_all_preconditions_checked_before_preparation(tmp_path: Path) -> None:
    (tmp_path / "b").write_bytes(b"changed")
    before = tuple(tmp_path.iterdir())
    with pytest.raises(MutationConflict):
        adapter(tmp_path).apply(
            RepositoryChangeSet((create("a", "new"), update("b", "old", "new")))
        )
    assert tuple(tmp_path.iterdir()) == before
    assert (tmp_path / "b").read_bytes() == b"changed"


@pytest.mark.parametrize("kind", list(FileChangeKind))
def test_directory_targets_rejected(tmp_path: Path, kind: FileChangeKind) -> None:
    (tmp_path / "directory").mkdir()
    change = FileChange(
        RepositoryPath("directory"),
        kind,
        None if kind is FileChangeKind.CREATE else digest_text(""),
        None if kind is FileChangeKind.DELETE else "x",
    )
    with pytest.raises(WorkspaceError) as caught:
        adapter(tmp_path).apply(RepositoryChangeSet((change,)))
    assert caught.value.reason is WorkspaceFailure.NOT_FILE
    assert (tmp_path / "directory").is_dir()


def test_missing_parent_and_policy_exclusion(tmp_path: Path) -> None:
    for path, reason in (
        ("missing/child", WorkspaceFailure.MISSING),
        (".venv/child", WorkspaceFailure.EXCLUDED),
    ):
        with pytest.raises(WorkspaceError) as caught:
            adapter(tmp_path).apply(RepositoryChangeSet((create(path, "x"),)))
        assert caught.value.reason is reason
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("path", ["../a", "/a", "C:/a", "a\\b", "//server/share"])
def test_path_escape_rejected_inertly(path: str) -> None:
    with pytest.raises(WorkspaceBoundaryError):
        create(path, "x")


@pytest.mark.parametrize(
    "path", [".git", ".git/config", ".GIT/HEAD", "nested/.git/index"]
)
def test_git_paths_rejected_inertly(path: str) -> None:
    with pytest.raises(WorkspaceError) as caught:
        create(path, "x")
    assert caught.value.reason is WorkspaceFailure.EXCLUDED


def test_gitfile_and_custom_metadata_roots_rejected(tmp_path: Path) -> None:
    root = tmp_path / "worktree"
    root.mkdir()
    (root / ".git").write_bytes(b"gitdir: ../metadata\n")
    with pytest.raises(WorkspaceError) as caught:
        adapter(root).apply(RepositoryChangeSet((create("a", "x"),)))
    assert caught.value.reason is WorkspaceFailure.EXCLUDED
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    (metadata / "HEAD").write_bytes(b"ref: refs/heads/main\n")
    (metadata / "objects").mkdir()
    (metadata / "objects" / "sub").mkdir()
    for directory in (metadata, metadata / "objects" / "sub"):
        with pytest.raises(WorkspaceError) as caught:
            adapter(directory).apply(RepositoryChangeSet((create("config", "x"),)))
        assert caught.value.reason is WorkspaceFailure.EXCLUDED
    assert not (metadata / "config").exists()


@pytest.mark.parametrize("content", ["a\0b", "\ud800"])
def test_invalid_payload_encoding_rejected_before_io(content: str) -> None:
    with pytest.raises(WorkspaceError):
        create("a", content)


def test_payload_policy_and_total_bounds(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        create("a", "x" * 65_537)
    with pytest.raises(ValueError):
        RepositoryChangeSet(tuple(create(str(i), "x" * 65_536) for i in range(17)))
    port = LocalRepositoryMutation(
        LocalWorkspaceRoot(tmp_path), WorkspacePolicy(4, 4, 10, 2, ())
    )
    with pytest.raises(WorkspaceError) as caught:
        port.apply(RepositoryChangeSet((create("a", "ééé"),)))
    assert caught.value.reason is WorkspaceFailure.LIMIT
    port.apply(RepositoryChangeSet((create("a", "éé"),)))
    assert (tmp_path / "a").read_bytes() == "éé".encode()


@pytest.mark.parametrize("names", [("a", "a"), ("a", "A"), ("a", "a/b")])
def test_ambiguous_targets_rejected(names: tuple[str, str]) -> None:
    with pytest.raises(ValueError):
        RepositoryChangeSet(tuple(create(name, "x") for name in names))


def test_values_types_digest_and_immutability() -> None:
    assert digest_text("").value == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    assert digest_text("a\r\n") != digest_text("a\n")
    change = create("sensitive-path", "sensitive-content")
    with pytest.raises(FrozenInstanceError):
        change.text = "bad"  # type: ignore[misc]
    assert "sensitive" not in repr(change)
    with pytest.raises(TypeError):
        RepositoryChangeSet([change])  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        RepositoryChangeSet(())
    with pytest.raises(ValueError):
        replace(change, kind=FileChangeKind.UPDATE)
    with pytest.raises(ValueError):
        ContentDigest("z" * 64)


def test_mid_apply_failure_reports_prefix_and_uncertainty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "b").write_bytes(b"old")

    def denied(source: Path, target: Path) -> None:
        raise PermissionError("sensitive-host-path")

    monkeypatch.setattr(os, "replace", denied)
    with pytest.raises(MutationApplyError) as caught:
        adapter(tmp_path).apply(
            RepositoryChangeSet((create("a", "new"), update("b", "old", "new")))
        )
    error = caught.value
    assert [item.path.value for item in error.completed.applied] == ["a"]
    assert error.uncertain == RepositoryPath("b")
    assert error.temporary_paths == ()
    assert isinstance(error.__cause__, PermissionError)
    assert "sensitive" not in str(error)
    assert (tmp_path / "a").read_bytes() == b"new"
    assert (tmp_path / "b").read_bytes() == b"old"
    assert not list(tmp_path.glob(".legoai-*.tmp"))


def test_preparation_failure_changes_no_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = tempfile.mkstemp
    calls = 0

    def fail_second(*, prefix: str, suffix: str, dir: Path) -> tuple[int, str]:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disk full")
        return original(prefix=prefix, suffix=suffix, dir=dir)

    monkeypatch.setattr(tempfile, "mkstemp", fail_second)
    with pytest.raises(MutationApplyError) as caught:
        adapter(tmp_path).apply(
            RepositoryChangeSet((create("a", "a"), create("b", "b")))
        )
    assert caught.value.completed.applied == ()
    assert caught.value.uncertain is None
    assert caught.value.temporary_paths == ()
    assert list(tmp_path.iterdir()) == []


def test_cleanup_failure_is_reported_even_after_completed_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = Path.unlink

    def deny_temporary(path: Path, missing_ok: bool = False) -> None:
        if path.name.startswith(".legoai-"):
            raise PermissionError("cleanup denied")
        original(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", deny_temporary)
    with pytest.raises(MutationApplyError) as caught:
        adapter(tmp_path).apply(RepositoryChangeSet((create("a", "new"),)))
    assert len(caught.value.completed.applied) == 1
    assert caught.value.uncertain is None
    assert len(caught.value.temporary_paths) == 1
    assert (tmp_path / "a").read_bytes() == b"new"
    leftover = tmp_path / caught.value.temporary_paths[0].value
    assert leftover.read_bytes() == b"new"
    original(leftover)


def test_late_change_detected_before_any_target_application(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "b").write_bytes(b"old")
    original = tempfile.mkstemp

    def change_during_preparation(
        *, prefix: str, suffix: str, dir: Path
    ) -> tuple[int, str]:
        (tmp_path / "b").write_bytes(b"newer")
        return original(prefix=prefix, suffix=suffix, dir=dir)

    monkeypatch.setattr(tempfile, "mkstemp", change_during_preparation)
    with pytest.raises(MutationApplyError) as caught:
        adapter(tmp_path).apply(
            RepositoryChangeSet((create("a", "new"), update("b", "old", "bad")))
        )
    assert isinstance(caught.value.__cause__, MutationConflict)
    assert caught.value.completed.applied == ()
    assert caught.value.uncertain is None
    assert not (tmp_path / "a").exists()
    assert (tmp_path / "b").read_bytes() == b"newer"
    assert not list(tmp_path.glob(".legoai-*.tmp"))


@pytest.mark.parametrize("data", [b"\xff", b"\0", b"x" * 4097])
def test_existing_content_must_be_bounded_utf8(tmp_path: Path, data: bytes) -> None:
    (tmp_path / "a").write_bytes(data)
    with pytest.raises(WorkspaceError):
        adapter(tmp_path).apply(RepositoryChangeSet((delete("a", ""),)))
    assert (tmp_path / "a").read_bytes() == data


def test_bom_is_not_added_and_explicit_bom_is_preserved(tmp_path: Path) -> None:
    adapter(tmp_path).apply(
        RepositoryChangeSet((create("plain", "x"), create("bom", "\ufeffx")))
    )
    assert (tmp_path / "plain").read_bytes() == b"x"
    assert (tmp_path / "bom").read_bytes() == b"\xef\xbb\xbfx"


def test_mutation_example(tmp_path: Path) -> None:
    example = Path(__file__).resolve().parents[1] / "examples" / "mutation_intake.py"
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(example)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == ["update: greeting.txt", "hello LegoAI"]
    assert list(tmp_path.iterdir()) == []


def test_symlink_target_parent_and_root_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    private = outside / "private"
    private.write_bytes(b"private")
    root = tmp_path / "root"
    root.mkdir()
    try:
        (root / "file-link").symlink_to(private)
        (root / "dir-link").symlink_to(outside, target_is_directory=True)
        (tmp_path / "root-link").symlink_to(root, target_is_directory=True)
    except OSError as error:
        if sys.platform == "win32" and error.winerror == 1314:
            pytest.skip("Windows symlink privilege unavailable; enable Developer Mode")
        raise
    for change in (
        update("file-link", "private", "bad"),
        delete("dir-link/private", "private"),
        create("dir-link/new", "bad"),
    ):
        with pytest.raises(WorkspaceBoundaryError):
            adapter(root).apply(RepositoryChangeSet((change,)))
    with pytest.raises(WorkspaceBoundaryError):
        adapter(tmp_path / "root-link").apply(
            RepositoryChangeSet((create("a", "bad"),))
        )
    assert private.read_bytes() == b"private"
    assert not (outside / "new").exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction boundary")
def test_windows_junction_mutation_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "private").write_bytes(b"private")
    junction = root / "junction"
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    try:
        with pytest.raises(WorkspaceBoundaryError):
            adapter(root).apply(
                RepositoryChangeSet((update("junction/private", "private", "bad"),))
            )
    finally:
        junction.rmdir()
    assert (outside / "private").read_bytes() == b"private"


def test_hardlink_rejected(tmp_path: Path) -> None:
    (tmp_path / "a").write_bytes(b"old")
    os.link(tmp_path / "a", tmp_path / "b")
    with pytest.raises(WorkspaceBoundaryError):
        adapter(tmp_path).apply(RepositoryChangeSet((update("a", "old", "bad"),)))
    assert (tmp_path / "b").read_bytes() == b"old"


def test_git_status_after_create_update_delete(tmp_path: Path) -> None:
    executable = shutil.which("git")
    assert executable is not None, "M4 integration qualification requires Git"
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }
    if os.name == "nt":
        environment["SystemRoot"] = os.environ["SystemRoot"]

    def git(*args: str) -> None:
        subprocess.run(
            [executable, *args],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            check=True,
            timeout=15,
        )

    git("init", "--initial-branch=main", "--template=")
    git("config", "--local", "user.name", "M4 Fixture")
    git("config", "--local", "user.email", "m4@example.invalid")
    (tmp_path / "updated").write_bytes(b"old")
    (tmp_path / "deleted").write_bytes(b"old")
    git("add", "--all")
    git("commit", "-m", "fixture")
    reader = LocalGitRepository(
        LocalWorkspaceRoot(tmp_path),
        LocalGitExecutable(Path(executable)),
        GitReadPolicy(5, 262_144, 128, 4096),
    )
    assert reader.inspect().entries == ()
    index = (tmp_path / ".git" / "index").read_bytes()
    adapter(tmp_path).apply(
        RepositoryChangeSet(
            (
                create("created", "new"),
                update("updated", "old", "new"),
                delete("deleted", "old"),
            )
        )
    )
    entries = {item.path.value: item for item in reader.inspect().entries}
    assert entries["created"].untracked
    assert entries["updated"].worktree is GitChange.MODIFIED
    assert entries["deleted"].worktree is GitChange.DELETED
    assert all(item.index is GitChange.UNCHANGED for item in entries.values())
    assert (tmp_path / ".git" / "index").read_bytes() == index
