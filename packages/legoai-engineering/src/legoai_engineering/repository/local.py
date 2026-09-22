"""Bounded local workspace adapter for trusted, stable filesystem namespaces.

This is not an OS sandbox or a public governed invocation facade. Hostile
concurrent directory/mount mutation and network filesystems are unsupported.
"""

import os
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path

from legoai_engineering.repository.errors import (
    WorkspaceBoundaryError,
    WorkspaceError,
    WorkspaceFailure,
)
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import (
    RepositoryPath,
    WorkspaceEntry,
    WorkspaceEntryKind,
    WorkspacePolicy,
)


@dataclass(frozen=True, slots=True)
class LocalWorkspaceRoot:
    """Explicit host configuration, not canonical identity or an authority grant."""

    path: Path = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.path) is not type(Path()):
            raise TypeError("local root requires a native concrete Path")
        if not self.path.is_absolute() or ".." in self.path.parts:
            raise WorkspaceBoundaryError()
        if self.path.drive.startswith("\\\\"):
            raise WorkspaceBoundaryError()  # UNC/device namespaces unsupported.


def _identity(info: os.stat_result) -> tuple[int, int]:
    if info.st_ino == 0:
        raise WorkspaceError(WorkspaceFailure.IO)
    return info.st_dev, info.st_ino


def _reject_link(info: os.stat_result) -> None:
    if stat.S_ISLNK(info.st_mode):
        raise WorkspaceBoundaryError()
    if sys.platform == "win32":
        if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise WorkspaceBoundaryError()


def _checked_chain(path: Path) -> os.stat_result:
    """Check ancestors before touching children; never intentionally follow links."""
    for parent in reversed(path.parents):
        info = parent.lstat()
        _reject_link(info)
        if not stat.S_ISDIR(info.st_mode):
            raise WorkspaceError(WorkspaceFailure.NOT_DIRECTORY)
    info = path.lstat()
    _reject_link(info)
    return info


def _io_error(error: OSError) -> WorkspaceError:
    if isinstance(error, FileNotFoundError):
        return WorkspaceError(WorkspaceFailure.MISSING)
    if isinstance(error, NotADirectoryError):
        return WorkspaceError(WorkspaceFailure.NOT_DIRECTORY)
    return WorkspaceError(WorkspaceFailure.IO)


class LocalRepositoryWorkspace:
    """No discovery at import; construction explicitly validates the supplied root.

    All methods recheck root identity and link-free containment. These checks
    detect ordinary replacement; they cannot lock a hostile filesystem namespace.
    """

    __slots__ = ("_root", "_root_identity", "_policy")

    def __init__(self, root: LocalWorkspaceRoot, policy: WorkspacePolicy) -> None:
        if type(root) is not LocalWorkspaceRoot:
            raise TypeError("workspace requires LocalWorkspaceRoot")
        if type(policy) is not WorkspacePolicy:
            raise TypeError("workspace requires WorkspacePolicy")
        try:
            info = _checked_chain(root.path)
            if not stat.S_ISDIR(info.st_mode):
                raise WorkspaceError(WorkspaceFailure.NOT_DIRECTORY)
            canonical = root.path.resolve(strict=True)
            if _identity(_checked_chain(canonical)) != _identity(info):
                raise WorkspaceError(WorkspaceFailure.CHANGED)
        except OSError as error:
            raise _io_error(error) from error
        self._root = canonical
        self._root_identity = _identity(info)
        self._policy = policy

    def _validate_path(self, path: RepositoryPath) -> None:
        if type(path) is not RepositoryPath:
            raise TypeError("workspace operation requires RepositoryPath")
        parts = path.value.split("/")
        if len(parts) > self._policy.max_depth:
            raise WorkspaceError(WorkspaceFailure.LIMIT)
        excluded = {name.casefold() for name in self._policy.excluded_names}
        if any(part.casefold() in excluded for part in parts):
            raise WorkspaceError(WorkspaceFailure.EXCLUDED)

    def _target(self, path: RepositoryPath | None) -> tuple[Path, os.stat_result]:
        if path is not None:
            self._validate_path(path)
        root_info = _checked_chain(self._root)
        if _identity(root_info) != self._root_identity:
            raise WorkspaceError(WorkspaceFailure.CHANGED)
        target = self._root if path is None else self._root / path.value
        info = _checked_chain(target)
        resolved = target.resolve(strict=True)
        if not resolved.is_relative_to(self._root):
            raise WorkspaceBoundaryError()
        if info.st_dev != root_info.st_dev:
            raise WorkspaceBoundaryError()
        return target, info

    def list_entries(
        self, directory: RepositoryPath | None
    ) -> tuple[WorkspaceEntry, ...]:
        try:
            target, before = self._target(directory)
            if not stat.S_ISDIR(before.st_mode):
                raise WorkspaceError(WorkspaceFailure.NOT_DIRECTORY)
            entries: list[WorkspaceEntry] = []
            excluded = {name.casefold() for name in self._policy.excluded_names}
            # scandir is consumed incrementally; Path.iterdir may materialize a
            # whole directory before yielding. Count even excluded entries.
            with os.scandir(target) as scan:
                for count, entry in enumerate(scan, start=1):
                    if count > self._policy.max_entries:
                        raise WorkspaceError(WorkspaceFailure.LIMIT)
                    if entry.name.casefold() in excluded:
                        continue
                    prefix = "" if directory is None else directory.value + "/"
                    relative = RepositoryPath(prefix + entry.name)
                    _, info = self._target(relative)
                    if stat.S_ISDIR(info.st_mode):
                        kind = WorkspaceEntryKind.DIRECTORY
                    elif stat.S_ISREG(info.st_mode):
                        if info.st_nlink != 1:
                            raise WorkspaceBoundaryError()
                        kind = WorkspaceEntryKind.FILE
                    else:
                        raise WorkspaceError(WorkspaceFailure.NOT_FILE)
                    entries.append(WorkspaceEntry(relative, kind))
            _, after = self._target(directory)
            if (
                _identity(before) != _identity(after)
                or before.st_mtime_ns != after.st_mtime_ns
            ):
                raise WorkspaceError(WorkspaceFailure.CHANGED)
            return tuple(sorted(entries, key=lambda item: item.path.value))
        except OSError as error:
            raise _io_error(error) from error

    def read_text(self, path: RepositoryPath) -> RepositoryText:
        if type(path) is not RepositoryPath:
            raise TypeError("workspace read requires RepositoryPath")
        try:
            target, before = self._target(path)
            if not stat.S_ISREG(before.st_mode):
                raise WorkspaceError(WorkspaceFailure.NOT_FILE)
            if before.st_nlink != 1:
                raise WorkspaceBoundaryError()
            if before.st_size > self._policy.max_read_bytes:
                raise WorkspaceError(WorkspaceFailure.LIMIT)
            with target.open("rb") as stream:
                opened = os.fstat(stream.fileno())
                _reject_link(opened)
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or opened.st_nlink != 1
                    or _identity(opened) != _identity(before)
                ):
                    raise WorkspaceError(WorkspaceFailure.CHANGED)
                _, current = self._target(path)
                if _identity(current) != _identity(opened):
                    raise WorkspaceError(WorkspaceFailure.CHANGED)
                data = stream.read(self._policy.max_read_bytes + 1)
                after = os.fstat(stream.fileno())
            _, final = self._target(path)
            if len(data) > self._policy.max_read_bytes:
                raise WorkspaceError(WorkspaceFailure.LIMIT)
            if (
                _identity(final) != _identity(before)
                or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns
                or len(data) != after.st_size
            ):
                raise WorkspaceError(WorkspaceFailure.CHANGED)
        except OSError as error:
            raise _io_error(error) from error
        if b"\x00" in data:
            raise WorkspaceError(WorkspaceFailure.BINARY)
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise WorkspaceError(WorkspaceFailure.DECODE) from error
        if len(text) > self._policy.max_text_chars:
            raise WorkspaceError(WorkspaceFailure.LIMIT)
        return RepositoryText(path.value, text)
