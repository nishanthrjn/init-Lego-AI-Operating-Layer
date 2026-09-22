"""Mutation conflicts and honest partial/uncertain I/O outcomes."""

from enum import Enum

from legoai_engineering.repository.mutation import RepositoryMutationResult
from legoai_engineering.repository.workspace import RepositoryPath


class MutationConflictReason(Enum):
    EXISTS = "create target already exists"
    MISSING = "update/delete target is missing"
    STALE = "target digest differs from precondition"


class MutationConflict(RuntimeError):
    def __init__(self, reason: MutationConflictReason, path: RepositoryPath) -> None:
        if (
            type(reason) is not MutationConflictReason
            or type(path) is not RepositoryPath
        ):
            raise TypeError("conflict requires typed reason and relative path")
        self.reason = reason
        self.path = path
        super().__init__(reason.value)


class MutationApplyError(RuntimeError):
    """No automatic retry. Inspect confirmed, uncertain and leftover state first.

    A failed final syscall is conservatively uncertain. Original exceptions and
    cleanup failures are retained as causes for trusted diagnostics only.
    """

    def __init__(
        self,
        completed: RepositoryMutationResult,
        uncertain: RepositoryPath | None,
        temporary_paths: tuple[RepositoryPath, ...],
    ) -> None:
        if type(completed) is not RepositoryMutationResult:
            raise TypeError("apply error requires typed completed result")
        if uncertain is not None and type(uncertain) is not RepositoryPath:
            raise TypeError("uncertain target requires RepositoryPath or None")
        if type(temporary_paths) is not tuple or any(
            type(path) is not RepositoryPath for path in temporary_paths
        ):
            raise TypeError("temporary paths require a tuple of RepositoryPath")
        if len(temporary_paths) > 128:
            raise ValueError("too many temporary paths")
        self.completed = completed
        self.uncertain = uncertain
        self.temporary_paths = temporary_paths
        super().__init__(
            "repository mutation failed; inspect effect state before retry"
        )
