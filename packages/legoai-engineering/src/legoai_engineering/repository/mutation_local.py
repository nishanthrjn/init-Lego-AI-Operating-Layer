"""Bounded mutation in a trusted stable namespace; not a filesystem transaction."""

import os
import stat
import tempfile
from pathlib import Path

from legoai_engineering.repository.errors import (
    WorkspaceBoundaryError,
    WorkspaceError,
    WorkspaceFailure,
)
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
    _checked_chain,
    _identity,
    _io_error,
)
from legoai_engineering.repository.mutation import (
    FileChange,
    FileChangeKind,
    FileChangeResult,
    RepositoryChangeSet,
    RepositoryMutationResult,
    _text_bytes,
    digest_text,
)
from legoai_engineering.repository.mutation_errors import (
    MutationApplyError,
    MutationConflict,
    MutationConflictReason,
)
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy


def _administration(directory: Path) -> None:
    """Reject metadata roots and gitfiles without resolving any Git pointer.

    Ancestor probes are fixed-name lstat only; no directory enumeration or
    content acquisition outside the supplied root. Corrupt/custom metadata
    without these markers is outside the supported host provisioning contract.
    """
    if any(part.casefold() == ".git" for part in directory.parts):
        raise WorkspaceError(WorkspaceFailure.EXCLUDED)
    if len(directory.parts) > 128:
        raise WorkspaceError(WorkspaceFailure.LIMIT)
    for parent in (directory, *directory.parents):
        _checked_chain(parent)
        found: set[str] = set()
        for name in (
            ".git",
            "HEAD",
            "objects",
            "refs",
            "commondir",
            "gitdir",
            "config",
        ):
            try:
                info = (parent / name).lstat()
            except FileNotFoundError:
                continue
            found.add(name)
            if name == ".git" and not stat.S_ISDIR(info.st_mode):
                raise WorkspaceError(WorkspaceFailure.EXCLUDED)
        if "HEAD" in found and found & {
            "objects",
            "refs",
            "commondir",
            "gitdir",
            "config",
        }:
            raise WorkspaceError(WorkspaceFailure.EXCLUDED)


def _preflight(
    workspace: LocalRepositoryWorkspace, change: FileChange, policy: WorkspacePolicy
) -> tuple[Path, int | None]:
    # Private reuse inside the repository owner keeps M2 containment authoritative.
    workspace._validate_path(change.path)
    prefix, _, leaf = change.path.value.rpartition("/")
    parent_path = RepositoryPath(prefix) if prefix else None
    parent, parent_info = workspace._target(parent_path)
    if not stat.S_ISDIR(parent_info.st_mode):
        raise WorkspaceError(WorkspaceFailure.NOT_DIRECTORY)
    _administration(parent)
    if change.text is not None:
        if (
            len(change.text) > policy.max_text_chars
            or len(_text_bytes(change.text)) > policy.max_read_bytes
        ):
            raise WorkspaceError(WorkspaceFailure.LIMIT)
        label_prefix = prefix + "/" if prefix else ""
        RepositoryPath(label_prefix + ".legoai-" + "x" * 8 + ".tmp")
    try:
        target, info = workspace._target(change.path)
    except FileNotFoundError:
        if change.kind is not FileChangeKind.CREATE:
            raise MutationConflict(
                MutationConflictReason.MISSING, change.path
            ) from None
        return parent / leaf, None
    if not stat.S_ISREG(info.st_mode):
        raise WorkspaceError(WorkspaceFailure.NOT_FILE)
    if info.st_nlink != 1:
        raise WorkspaceBoundaryError()
    if not info.st_mode & stat.S_IWUSR:
        raise WorkspaceError(WorkspaceFailure.EXCLUDED)
    if change.kind is FileChangeKind.CREATE:
        raise MutationConflict(MutationConflictReason.EXISTS, change.path)
    current = workspace.read_text(change.path)
    if digest_text(current.text) != change.expected:
        raise MutationConflict(MutationConflictReason.STALE, change.path)
    return target, stat.S_IMODE(info.st_mode)


class LocalRepositoryMutation:
    """Inert construction; apply binds M2 and checks every precondition first.

    WorkspacePolicy's byte/character limits apply to old AND new contents.
    No Git invocation, generic write helper, retries, or authority claims.
    """

    __slots__ = ("_root", "_policy")

    def __init__(self, root: LocalWorkspaceRoot, policy: WorkspacePolicy) -> None:
        if type(root) is not LocalWorkspaceRoot or type(policy) is not WorkspacePolicy:
            raise TypeError("mutation requires LocalWorkspaceRoot and WorkspacePolicy")
        self._root = root
        self._policy = policy

    def apply(self, changeset: RepositoryChangeSet) -> RepositoryMutationResult:
        if type(changeset) is not RepositoryChangeSet:
            raise TypeError("mutation requires RepositoryChangeSet")
        try:
            workspace = LocalRepositoryWorkspace(self._root, self._policy)
            for change in changeset.changes:
                _preflight(workspace, change, self._policy)
        except OSError as error:
            raise _io_error(error) from error
        completed: list[FileChangeResult] = []
        temporary: dict[int, tuple[Path, RepositoryPath, tuple[int, int] | None]] = {}
        uncertain: RepositoryPath | None = None
        failure: Exception | None = None
        cleanup_failures: list[Exception] = []
        try:
            for number, change in enumerate(changeset.changes):
                if change.text is None:
                    continue
                target, mode = _preflight(workspace, change, self._policy)
                prefix = change.path.value.rpartition("/")[0]
                label_prefix = prefix + "/" if prefix else ""
                descriptor, name = tempfile.mkstemp(
                    prefix=".legoai-", suffix=".tmp", dir=target.parent
                )
                temp = Path(name)
                relative = RepositoryPath(label_prefix + temp.name)
                temporary[number] = (temp, relative, None)
                try:
                    temporary[number] = (
                        temp,
                        relative,
                        _identity(os.fstat(descriptor)),
                    )
                    stream = os.fdopen(descriptor, "wb")
                except BaseException:
                    os.close(descriptor)
                    raise
                with stream:
                    data = _text_bytes(change.text)
                    if stream.write(data) != len(data):
                        raise OSError("incomplete temporary write")
                    stream.flush()
                if mode is not None:
                    os.chmod(temp, mode)
            # All proposals must still hold after preparation and before dispatch.
            for change in changeset.changes:
                _preflight(workspace, change, self._policy)
            for number, change in enumerate(changeset.changes):
                target, _ = _preflight(workspace, change, self._policy)
                result = FileChangeResult(
                    change.path,
                    change.kind,
                    change.expected,
                    digest_text(change.text) if change.text is not None else None,
                )
                if change.kind is FileChangeKind.DELETE:
                    uncertain = change.path
                    target.unlink()
                else:
                    temp, relative, identity = temporary[number]
                    checked, info = workspace._target(relative)
                    if (
                        checked != temp
                        or _identity(info) != identity
                        or info.st_nlink != 1
                    ):
                        raise WorkspaceError(WorkspaceFailure.CHANGED)
                    uncertain = change.path
                    if change.kind is FileChangeKind.CREATE:
                        # A hardlink never replaces an existing destination name.
                        os.link(temp, target)
                    else:
                        os.replace(temp, target)
                        del temporary[number]
                completed.append(result)
                uncertain = None
                if number in temporary:
                    temp, _, _ = temporary[number]
                    temp.unlink()
                    del temporary[number]
        except Exception as error:
            failure = error
        finally:
            for number, (temp, relative, identity) in tuple(temporary.items()):
                try:
                    checked, info = workspace._target(relative)
                    if checked != temp or (
                        identity is not None and _identity(info) != identity
                    ):
                        raise WorkspaceError(WorkspaceFailure.CHANGED)
                    temp.unlink()
                    del temporary[number]
                except Exception as error:
                    cleanup_failures.append(error)
        result_set = RepositoryMutationResult(tuple(completed))
        if failure is not None or cleanup_failures:
            causes = ([failure] if failure is not None else []) + cleanup_failures
            cause = (
                causes[0]
                if len(causes) == 1
                else ExceptionGroup("mutation and temporary cleanup failures", causes)
            )
            raise MutationApplyError(
                result_set, uncertain, tuple(item[1] for item in temporary.values())
            ) from cause
        return result_set
