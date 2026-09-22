"""Immutable semantic results independent of the local Git implementation."""

from dataclasses import dataclass, field
from enum import Enum

from legoai_engineering.repository.workspace import RepositoryPath


@dataclass(frozen=True, slots=True)
class GitCommitId:
    """Opaque lowercase hexadecimal identity, not tied to SHA-1 length."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.value) is not str:
            raise TypeError("commit identity requires str")
        if (
            not 1 <= len(self.value) <= 128
            or any(char not in "0123456789abcdef" for char in self.value)
            or not self.value.strip("0")
        ):
            raise ValueError("invalid commit identity")


class GitHeadKind(Enum):
    ATTACHED = "attached"
    DETACHED = "detached"
    UNBORN = "unborn"


@dataclass(frozen=True, slots=True)
class GitHead:
    kind: GitHeadKind
    branch: str | None = field(repr=False)
    commit: GitCommitId | None

    def __post_init__(self) -> None:
        if type(self.kind) is not GitHeadKind:
            raise TypeError("HEAD kind requires GitHeadKind")
        if self.branch is not None:
            if type(self.branch) is not str:
                raise TypeError("branch requires str or None")
            if not 1 <= len(self.branch) <= 240 or any(
                ord(char) < 33 or ord(char) == 127 for char in self.branch
            ):
                raise ValueError("unsupported branch label")
        if self.commit is not None and type(self.commit) is not GitCommitId:
            raise TypeError("commit requires GitCommitId or None")
        if (self.branch is None) != (self.kind is GitHeadKind.DETACHED):
            raise ValueError("branch does not agree with HEAD kind")
        if (self.commit is None) != (self.kind is GitHeadKind.UNBORN):
            raise ValueError("commit does not agree with HEAD kind")


class GitChange(Enum):
    UNCHANGED = "."
    MODIFIED = "M"
    ADDED = "A"
    DELETED = "D"
    TYPE_CHANGED = "T"


@dataclass(frozen=True, slots=True)
class GitStatusEntry:
    path: RepositoryPath
    index: GitChange
    worktree: GitChange
    untracked: bool

    def __post_init__(self) -> None:
        if type(self.path) is not RepositoryPath:
            raise TypeError("status path requires RepositoryPath")
        if type(self.index) is not GitChange or type(self.worktree) is not GitChange:
            raise TypeError("status changes require GitChange")
        if type(self.untracked) is not bool:
            raise TypeError("untracked requires bool")
        unchanged = self.index is self.worktree is GitChange.UNCHANGED
        if self.untracked != unchanged:
            raise ValueError("tracked status must describe a change")


@dataclass(frozen=True, slots=True)
class GitRepositoryState:
    head: GitHead
    entries: tuple[GitStatusEntry, ...]

    def __post_init__(self) -> None:
        if type(self.head) is not GitHead:
            raise TypeError("repository state requires GitHead")
        if type(self.entries) is not tuple or any(
            type(entry) is not GitStatusEntry for entry in self.entries
        ):
            raise TypeError("status requires a tuple of GitStatusEntry")
        if len(self.entries) > 4096:
            raise ValueError("too many status entries")
        paths = tuple(entry.path.value for entry in self.entries)
        if paths != tuple(sorted(set(paths))):
            raise ValueError("status paths must be unique and sorted")
