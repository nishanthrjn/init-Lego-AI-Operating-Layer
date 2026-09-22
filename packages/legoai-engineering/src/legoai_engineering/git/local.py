"""Read-only Git reference adapter for a trusted, stable local namespace."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from legoai_engineering.git._config import check_config
from legoai_engineering.git._parse import check_index, parse_status
from legoai_engineering.git._process import GitCommand, capture
from legoai_engineering.git.errors import GitError, GitFailure
from legoai_engineering.git.values import GitRepositoryState
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.workspace import (
    RepositoryPath,
    WorkspaceEntryKind,
    WorkspacePolicy,
)


@dataclass(frozen=True, slots=True)
class GitReadPolicy:
    """Finite per-process capture/time and whole-workspace admission budgets."""

    timeout_seconds: int
    max_output_bytes: int
    max_status_entries: int
    max_scan_entries: int

    def __post_init__(self) -> None:
        for value, ceiling in (
            (self.timeout_seconds, 60),
            (self.max_output_bytes, 1_048_576),
            (self.max_status_entries, 4096),
            (self.max_scan_entries, 65_536),
        ):
            if type(value) is not int:
                raise TypeError("Git limits require int")
            if not 1 <= value <= ceiling:
                raise ValueError("Git limit outside supported range")


@dataclass(frozen=True, slots=True)
class LocalGitExecutable:
    """Explicit trusted host executable, selected by application composition."""

    path: Path = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.path) is not type(Path()):
            raise TypeError("Git executable requires a native Path")
        if (
            not self.path.is_absolute()
            or ".." in self.path.parts
            or self.path.drive.startswith("\\\\")
        ):
            raise ValueError("Git executable requires an absolute path")
        if os.name == "nt" and self.path.suffix.lower() != ".exe":
            raise ValueError("Windows Git executable must be an exe, not a script")


class LocalGitRepository:
    """Construction is inert; inspect binds/checks M2 before a fixed Git call."""

    __slots__ = ("_root", "_executable", "_policy")

    def __init__(
        self,
        root: LocalWorkspaceRoot,
        executable: LocalGitExecutable,
        policy: GitReadPolicy,
    ) -> None:
        if type(root) is not LocalWorkspaceRoot:
            raise TypeError("Git repository requires LocalWorkspaceRoot")
        if type(executable) is not LocalGitExecutable:
            raise TypeError("Git repository requires LocalGitExecutable")
        if type(policy) is not GitReadPolicy:
            raise TypeError("Git repository requires GitReadPolicy")
        self._root = root
        self._executable = executable
        self._policy = policy

    def inspect(self) -> GitRepositoryState:
        if not self._executable.path.is_file():
            raise GitError(GitFailure.UNAVAILABLE)
        workspace = LocalRepositoryWorkspace(
            self._root, WorkspacePolicy(262_144, 65_536, 4096, 32, ())
        )
        root_entries = workspace.list_entries(None)
        marker = next(
            (entry for entry in root_entries if entry.path.value == ".git"), None
        )
        if marker is None:
            names = {entry.path.value for entry in root_entries}
            if {"HEAD", "objects", "refs"} <= names:
                raise GitError(GitFailure.UNSUPPORTED)  # Bare layout.
            raise GitError(GitFailure.NOT_REPOSITORY)
        if marker.kind is not WorkspaceEntryKind.DIRECTORY:
            # Worktree/gitfile may point outside root; never follow it.
            raise GitError(GitFailure.UNSUPPORTED)
        pending = [
            entry.path
            for entry in root_entries
            if entry.kind is WorkspaceEntryKind.DIRECTORY
        ]
        count = len(root_entries)
        if count > self._policy.max_scan_entries:
            raise GitError(GitFailure.ENTRY_LIMIT)
        while pending:
            directory = pending.pop()
            entries = workspace.list_entries(directory)
            count += len(entries)
            if count > self._policy.max_scan_entries:
                raise GitError(GitFailure.ENTRY_LIMIT)
            for entry in entries:
                name = entry.path.value.casefold()
                if name.endswith("/.git") or name == ".gitmodules":
                    raise GitError(GitFailure.UNSUPPORTED)
                if name in {
                    ".git/commondir",
                    ".git/config.worktree",
                    ".git/shallow",
                    ".git/objects/info/alternates",
                    ".git/objects/info/http-alternates",
                    ".git/worktrees",
                    ".git/modules",
                    ".git/info/grafts",
                } or (name.startswith(".git/") and name.endswith(".promisor")):
                    raise GitError(GitFailure.UNSUPPORTED)
                if entry.kind is WorkspaceEntryKind.DIRECTORY:
                    pending.append(entry.path)
        if any(entry.path.value.casefold() == ".gitmodules" for entry in root_entries):
            raise GitError(GitFailure.UNSUPPORTED)
        metadata = {
            entry.path.value: entry.kind
            for entry in workspace.list_entries(RepositoryPath(".git"))
        }
        for name, kind in (
            ("HEAD", WorkspaceEntryKind.FILE),
            ("config", WorkspaceEntryKind.FILE),
            ("objects", WorkspaceEntryKind.DIRECTORY),
            ("refs", WorkspaceEntryKind.DIRECTORY),
        ):
            if metadata.get(".git/" + name) is not kind:
                raise GitError(GitFailure.INVALID_REPOSITORY)
        config = workspace.read_text(RepositoryPath(".git/config"))
        check_config(config.text)
        head = workspace.read_text(RepositoryPath(".git/HEAD")).text.strip()
        if head == "ref: refs/heads/(detached)":
            # Porcelain uses this spelling as its detached-HEAD sentinel.
            raise GitError(GitFailure.UNSUPPORTED)
        index = capture(
            self._executable.path,
            self._root.path,
            self._policy.timeout_seconds,
            self._policy.max_output_bytes,
            GitCommand.INDEX,
        )
        check_index(index, self._policy.max_scan_entries)
        data = capture(
            self._executable.path,
            self._root.path,
            self._policy.timeout_seconds,
            self._policy.max_output_bytes,
            GitCommand.STATUS,
        )
        workspace.list_entries(None)  # Retain M2 root-identity check after Git.
        return parse_status(data, self._policy.max_status_entries)
