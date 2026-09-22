"""Inert text changesets and exact-byte SHA-256 preconditions."""

import hashlib
from dataclasses import dataclass, field
from enum import Enum

from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath


def _text_bytes(text: str) -> bytes:
    RepositoryText("payload", text)
    if "\0" in text:
        raise WorkspaceError(WorkspaceFailure.BINARY)
    try:
        return text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise WorkspaceError(WorkspaceFailure.DECODE) from error


@dataclass(frozen=True, slots=True)
class ContentDigest:
    """SHA-256 of exact UTF-8 bytes; neither authentication nor authorization."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.value) is not str:
            raise TypeError("content digest requires str")
        if len(self.value) != 64 or any(
            char not in "0123456789abcdef" for char in self.value
        ):
            raise ValueError("content digest requires lowercase SHA-256 hex")


def digest_text(text: str) -> ContentDigest:
    """Hash bounded exact text, preserving CR/LF and any explicit BOM character."""
    return ContentDigest(hashlib.sha256(_text_bytes(text)).hexdigest())


class FileChangeKind(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


def _mutation_path(path: RepositoryPath) -> None:
    if type(path) is not RepositoryPath:
        raise TypeError("mutation requires RepositoryPath")
    _text_bytes(path.value)
    if any(part.casefold() == ".git" for part in path.value.split("/")):
        raise WorkspaceError(WorkspaceFailure.EXCLUDED)


@dataclass(frozen=True, slots=True)
class FileChange:
    path: RepositoryPath
    kind: FileChangeKind
    expected: ContentDigest | None
    text: str | None = field(repr=False)

    def __post_init__(self) -> None:
        _mutation_path(self.path)
        if type(self.kind) is not FileChangeKind:
            raise TypeError("file change requires FileChangeKind")
        if self.expected is not None and type(self.expected) is not ContentDigest:
            raise TypeError("precondition requires ContentDigest or None")
        if (self.expected is None) != (self.kind is FileChangeKind.CREATE):
            raise ValueError("update/delete require a digest; create requires absence")
        if (self.text is None) != (self.kind is FileChangeKind.DELETE):
            raise ValueError("create/update require text; delete has no payload")
        if self.text is not None:
            _text_bytes(self.text)


@dataclass(frozen=True, slots=True)
class RepositoryChangeSet:
    """1–128 independent targets, applied in declared order; <=1 MiB payload."""

    changes: tuple[FileChange, ...]

    def __post_init__(self) -> None:
        if type(self.changes) is not tuple or any(
            type(change) is not FileChange for change in self.changes
        ):
            raise TypeError("changes require an immutable tuple of FileChange")
        if not 1 <= len(self.changes) <= 128:
            raise ValueError("changeset requires 1..128 changes")
        paths = [change.path.value.casefold() for change in self.changes]
        if len(set(paths)) != len(paths) or any(
            other.startswith(path + "/")
            for path in paths
            for other in paths
            if path != other
        ):
            raise ValueError("duplicate, case-alias or ancestor targets unsupported")
        payload_bytes = sum(
            len(_text_bytes(change.text))
            for change in self.changes
            if change.text is not None
        )
        if payload_bytes > 1_048_576:
            raise ValueError("changeset payload exceeds 1048576 bytes")


@dataclass(frozen=True, slots=True)
class FileChangeResult:
    path: RepositoryPath
    kind: FileChangeKind
    before: ContentDigest | None
    after: ContentDigest | None

    def __post_init__(self) -> None:
        _mutation_path(self.path)
        if type(self.kind) is not FileChangeKind:
            raise TypeError("change result requires FileChangeKind")
        for digest in (self.before, self.after):
            if digest is not None and type(digest) is not ContentDigest:
                raise TypeError("result digest requires ContentDigest or None")
        if (self.before is None) != (self.kind is FileChangeKind.CREATE):
            raise ValueError("invalid before digest")
        if (self.after is None) != (self.kind is FileChangeKind.DELETE):
            raise ValueError("invalid after digest")


@dataclass(frozen=True, slots=True)
class RepositoryMutationResult:
    """Confirmed completed changes in request order; no timestamps or host paths."""

    applied: tuple[FileChangeResult, ...]

    def __post_init__(self) -> None:
        if type(self.applied) is not tuple or any(
            type(item) is not FileChangeResult for item in self.applied
        ):
            raise TypeError("result requires an immutable tuple of FileChangeResult")
        if len(self.applied) > 128:
            raise ValueError("too many change results")
        paths = [item.path.value.casefold() for item in self.applied]
        if len(set(paths)) != len(paths):
            raise ValueError("duplicate change results")
