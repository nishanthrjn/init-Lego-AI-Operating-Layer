"""Workspace failures with safe messages and explicit machine-readable reasons."""

from enum import Enum


class WorkspaceFailure(Enum):
    BOUNDARY = "workspace boundary violation"
    MISSING = "workspace path not found"
    NOT_DIRECTORY = "workspace path is not a directory"
    NOT_FILE = "workspace path is not a regular file"
    EXCLUDED = "workspace path excluded by policy"
    LIMIT = "workspace operation exceeds configured limit"
    DECODE = "workspace content is not strict UTF-8"
    BINARY = "workspace content contains NUL"
    CHANGED = "workspace changed during operation"
    IO = "workspace I/O failed"


class WorkspaceError(RuntimeError):
    """Local adapter failure, not a canonical execution/effect result.

    Chained OS causes are retained for trusted diagnostics and may contain
    absolute paths. Do not send raw tracebacks to untrusted callers.
    """

    def __init__(self, reason: WorkspaceFailure) -> None:
        if type(reason) is not WorkspaceFailure:
            raise TypeError("workspace error requires WorkspaceFailure")
        self.reason = reason
        super().__init__(reason.value)


class WorkspaceBoundaryError(WorkspaceError):
    """Invalid target syntax or a forbidden link/boundary crossing."""

    def __init__(self) -> None:
        super().__init__(WorkspaceFailure.BOUNDARY)
