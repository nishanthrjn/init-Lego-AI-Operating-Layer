"""M2 limits, acquisition semantics and read-only workspace boundary contracts."""

import os
import subprocess
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import BinaryIO, cast

import pytest

from legoai_engineering.repository.api import inspect_text
from legoai_engineering.repository.errors import (
    WorkspaceBoundaryError,
    WorkspaceError,
    WorkspaceFailure,
)
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.ports import RepositoryWorkspacePort
from legoai_engineering.repository.values import InspectionRequest
from legoai_engineering.repository.workspace import (
    RepositoryPath,
    WorkspaceEntry,
    WorkspaceEntryKind,
    WorkspacePolicy,
)


@pytest.fixture
def policy() -> WorkspacePolicy:
    return WorkspacePolicy(4096, 1024, 20, 5, (".git", ".venv", "__pycache__"))


def adapter(root: Path, policy: WorkspacePolicy) -> LocalRepositoryWorkspace:
    return LocalRepositoryWorkspace(LocalWorkspaceRoot(root), policy)


def assert_reason(
    error: pytest.ExceptionInfo[WorkspaceError], reason: WorkspaceFailure
) -> None:
    assert error.value.reason is reason


def test_root_errors_and_binding(tmp_path: Path, policy: WorkspacePolicy) -> None:
    workspace = adapter(tmp_path, policy)
    assert workspace.list_entries(None) == ()
    with pytest.raises(WorkspaceError) as missing:
        adapter(tmp_path / "missing", policy)
    assert_reason(missing, WorkspaceFailure.MISSING)
    assert isinstance(missing.value.__cause__, FileNotFoundError)
    file = tmp_path / "file"
    file.write_bytes(b"x")
    with pytest.raises(WorkspaceError) as not_directory:
        adapter(file, policy)
    assert_reason(not_directory, WorkspaceFailure.NOT_DIRECTORY)
    with pytest.raises(WorkspaceBoundaryError):
        LocalWorkspaceRoot(Path("relative"))
    with pytest.raises(WorkspaceBoundaryError):
        LocalWorkspaceRoot(tmp_path / ".." / "outside")


@pytest.mark.parametrize(
    "value",
    [
        "../secret",
        "nested/../../secret",
        "/absolute",
        "C:/absolute",
        "C:drive-relative",
        "\\rooted",
        "nested\\..\\secret",
        "nested/..\\secret",
        "//server/share",
        "\\\\?\\C:\\secret",
        "a:stream",
        "a//b",
        "a/./b",
        "a\x00",
        "name.",
        "name ",
        "NUL.txt",
        "COM1",
        "LPT¹.txt",
        "a?b",
    ],
)
def test_escape_and_windows_alias_syntax_rejected(value: str) -> None:
    with pytest.raises(WorkspaceBoundaryError):
        RepositoryPath(value)


def test_outside_file_never_read(tmp_path: Path, policy: WorkspacePolicy) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "private.txt"
    outside.write_text("outside", encoding="utf-8")
    workspace = adapter(root, policy)
    for candidate in ("../private.txt", outside.as_posix(), "..\\private.txt"):
        with pytest.raises(WorkspaceBoundaryError):
            workspace.read_text(RepositoryPath(candidate))


def test_read_utf8_preserves_content_and_reuses_m1(
    tmp_path: Path, policy: WorkspacePolicy, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "src").mkdir()
    source = tmp_path / "src" / "a.py"
    content = "😀needle\r\nneedle\n"
    source.write_bytes(content.encode("utf-8"))
    workspace: RepositoryWorkspacePort = adapter(tmp_path, policy)
    monkeypatch.chdir(tmp_path.parent)
    text = workspace.read_text(RepositoryPath("src/a.py"))
    assert text.path == "src/a.py"
    assert text.text == content
    result = inspect_text(InspectionRequest((text,), "needle", 10))
    assert [(match.line, match.column) for match in result.matches] == [(1, 2), (2, 1)]
    assert source.read_bytes() == content.encode("utf-8")
    source.write_bytes(b"")
    assert workspace.read_text(RepositoryPath("src/a.py")).text == ""
    source.write_bytes(b"\xef\xbb\xbfhello")
    assert workspace.read_text(RepositoryPath("src/a.py")).text == "\ufeffhello"


def test_read_failures(tmp_path: Path, policy: WorkspacePolicy) -> None:
    workspace = adapter(tmp_path, policy)
    with pytest.raises(WorkspaceError) as missing:
        workspace.read_text(RepositoryPath("absent"))
    assert_reason(missing, WorkspaceFailure.MISSING)
    (tmp_path / "directory").mkdir()
    with pytest.raises(WorkspaceError) as directory:
        workspace.read_text(RepositoryPath("directory"))
    assert_reason(directory, WorkspaceFailure.NOT_FILE)
    for content, reason in (
        (b"\xff", WorkspaceFailure.DECODE),
        (b"a\x00b", WorkspaceFailure.BINARY),
        (b"x" * 4097, WorkspaceFailure.LIMIT),
        ("é".encode() * 1025, WorkspaceFailure.LIMIT),
    ):
        (tmp_path / "file").write_bytes(content)
        with pytest.raises(WorkspaceError) as failure:
            workspace.read_text(RepositoryPath("file"))
        assert_reason(failure, reason)
        assert str(tmp_path) not in str(failure.value)


def test_exact_byte_and_character_bounds(tmp_path: Path) -> None:
    (tmp_path / "file").write_bytes("éé".encode())
    policy = WorkspacePolicy(4, 2, 1, 1, ())
    assert adapter(tmp_path, policy).read_text(RepositoryPath("file")).text == "éé"
    with pytest.raises(WorkspaceError) as limit:
        adapter(tmp_path, replace(policy, max_read_bytes=3)).read_text(
            RepositoryPath("file")
        )
    assert_reason(limit, WorkspaceFailure.LIMIT)


def test_listing_order_exclusions_and_no_recursion(
    tmp_path: Path, policy: WorkspacePolicy
) -> None:
    for name in ("z.txt", ".config", "a.txt"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "child").write_bytes(b"x")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "private").write_bytes(b"x")
    workspace = adapter(tmp_path, policy)
    entries = workspace.list_entries(None)
    assert tuple(entry.path.value for entry in entries) == (
        ".config",
        "a.txt",
        "nested",
        "z.txt",
    )
    assert entries[2].kind is WorkspaceEntryKind.DIRECTORY
    assert workspace.list_entries(RepositoryPath("nested")) == (
        WorkspaceEntry(RepositoryPath("nested/child"), WorkspaceEntryKind.FILE),
    )
    with pytest.raises(WorkspaceError) as excluded:
        workspace.read_text(RepositoryPath(".GIT/private"))
    assert_reason(excluded, WorkspaceFailure.EXCLUDED)
    with pytest.raises(WorkspaceError) as not_directory:
        workspace.list_entries(RepositoryPath("a.txt"))
    assert_reason(not_directory, WorkspaceFailure.NOT_DIRECTORY)


def test_scan_and_depth_limits_fail_without_partial_results(
    tmp_path: Path, policy: WorkspacePolicy
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "a").write_bytes(b"x")
    assert (
        len(adapter(tmp_path, replace(policy, max_entries=2)).list_entries(None)) == 1
    )
    with pytest.raises(WorkspaceError) as limit:
        adapter(tmp_path, replace(policy, max_entries=1)).list_entries(None)
    assert_reason(limit, WorkspaceFailure.LIMIT)
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "file").write_bytes(b"x")
    workspace = adapter(tmp_path, replace(policy, max_depth=1))
    with pytest.raises(WorkspaceError) as depth:
        workspace.read_text(RepositoryPath("nested/file"))
    assert_reason(depth, WorkspaceFailure.LIMIT)
    with pytest.raises(WorkspaceError):
        workspace.list_entries(RepositoryPath("nested"))


def make_symlink(link: Path, target: Path, *, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as error:
        if sys.platform == "win32" and error.winerror == 1314:
            pytest.skip("Windows symlink privilege unavailable; enable Developer Mode")
        raise


def test_symlink_file_directory_and_root_escape(
    tmp_path: Path, policy: WorkspacePolicy
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "private").write_bytes(b"outside")
    root = tmp_path / "root"
    root.mkdir()
    workspace = adapter(root, policy)
    make_symlink(root / "link", outside / "private")
    with pytest.raises(WorkspaceBoundaryError):
        workspace.read_text(RepositoryPath("link"))
    with pytest.raises(WorkspaceBoundaryError):
        workspace.list_entries(None)
    make_symlink(root / "linked-dir", outside, directory=True)
    with pytest.raises(WorkspaceBoundaryError):
        workspace.read_text(RepositoryPath("linked-dir/private"))
    with pytest.raises(WorkspaceBoundaryError):
        adapter(root / "linked-dir", policy)
    make_symlink(root / "dangling", outside / "missing")
    with pytest.raises(WorkspaceBoundaryError):
        workspace.read_text(RepositoryPath("dangling"))


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction boundary")
def test_windows_junction_escape(tmp_path: Path, policy: WorkspacePolicy) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "private").write_bytes(b"outside")
    root = tmp_path / "root"
    root.mkdir()
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
        assert junction.is_junction()
        workspace = adapter(root, policy)
        with pytest.raises(WorkspaceBoundaryError):
            workspace.read_text(RepositoryPath("junction/private"))
        with pytest.raises(WorkspaceBoundaryError):
            workspace.list_entries(None)
    finally:
        junction.rmdir()  # Remove the link only; never traverse/delete its target.
    assert (outside / "private").read_bytes() == b"outside"


def test_hardlink_rejected(tmp_path: Path, policy: WorkspacePolicy) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    (root / "alias").hardlink_to(outside)
    with pytest.raises(WorkspaceBoundaryError):
        adapter(root, policy).read_text(RepositoryPath("alias"))


def test_file_replacement_before_read_is_detected(
    tmp_path: Path, policy: WorkspacePolicy, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "file"
    target.write_bytes(b"original")
    replacement = tmp_path / "replacement"
    replacement.write_bytes(b"different")
    workspace = adapter(tmp_path, policy)
    original_open = Path.open

    def swap(path: Path, mode: str) -> BinaryIO:
        assert mode == "rb"
        target.rename(tmp_path / "old")
        replacement.rename(target)
        return cast(BinaryIO, original_open(path, "rb"))

    monkeypatch.setattr(Path, "open", swap)
    with pytest.raises(WorkspaceError) as changed:
        workspace.read_text(RepositoryPath("file"))
    assert_reason(changed, WorkspaceFailure.CHANGED)


def test_root_replacement_invalidates_bound_workspace(
    tmp_path: Path, policy: WorkspacePolicy
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    workspace = adapter(root, policy)
    root.rename(tmp_path / "old-root")
    root.mkdir()
    (root / "file").write_bytes(b"new workspace")
    with pytest.raises(WorkspaceError) as changed:
        workspace.read_text(RepositoryPath("file"))
    assert_reason(changed, WorkspaceFailure.CHANGED)


def test_permission_failure_preserves_cause(
    tmp_path: Path, policy: WorkspacePolicy, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "file").write_bytes(b"x")
    workspace = adapter(tmp_path, policy)

    def denied(path: Path, mode: str) -> BinaryIO:
        raise PermissionError("denied by fixture")

    monkeypatch.setattr(Path, "open", denied)
    with pytest.raises(WorkspaceError) as failure:
        workspace.read_text(RepositoryPath("file"))
    assert_reason(failure, WorkspaceFailure.IO)
    assert isinstance(failure.value.__cause__, PermissionError)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX special-file boundary")
def test_fifo_is_rejected_without_open(tmp_path: Path, policy: WorkspacePolicy) -> None:
    if sys.platform != "win32":
        os.mkfifo(tmp_path / "pipe")
        with pytest.raises(WorkspaceError) as failure:
            adapter(tmp_path, policy).read_text(RepositoryPath("pipe"))
        assert_reason(failure, WorkspaceFailure.NOT_FILE)


def test_values_types_and_immutability(tmp_path: Path, policy: WorkspacePolicy) -> None:
    with pytest.raises(TypeError):
        RepositoryPath(1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(policy, max_entries=True)
    with pytest.raises(ValueError):
        replace(policy, max_text_chars=65_537)
    with pytest.raises(ValueError):
        replace(policy, max_read_bytes=0)
    with pytest.raises(TypeError):
        replace(policy, excluded_names=[])  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        replace(policy, excluded_names=(".git", ".GIT"))
    with pytest.raises(ValueError):
        replace(policy, excluded_names=("a/b",))
    with pytest.raises(FrozenInstanceError):
        policy.max_entries = 3  # type: ignore[misc]
    workspace = adapter(tmp_path, policy)
    with pytest.raises(TypeError):
        workspace.read_text("a")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        workspace.read_text(None)  # type: ignore[arg-type]
    assert str(tmp_path) not in repr(LocalWorkspaceRoot(tmp_path))


def test_workspace_example(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.14"\n', encoding="utf-8"
    )
    example = Path(__file__).resolve().parents[1] / "examples" / "workspace_intake.py"
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(example), str(tmp_path)],
        cwd=tmp_path.parent,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "pyproject.toml:2:1"
