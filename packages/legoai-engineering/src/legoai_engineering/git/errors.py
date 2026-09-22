"""Safe public failure vocabulary for Git observation."""

from enum import Enum


class GitFailure(Enum):
    UNAVAILABLE = "Git executable unavailable"
    NOT_REPOSITORY = "workspace root is not a Git repository"
    INVALID_REPOSITORY = "invalid Git repository structure"
    UNSUPPORTED = "unsupported Git repository configuration or layout"
    COMMAND = "Git observation command failed"
    TIMEOUT = "Git observation timed out"
    OUTPUT_LIMIT = "Git observation output exceeded its bound"
    ENTRY_LIMIT = "Git observation entry bound exceeded"
    DECODE = "Git observation is not strict UTF-8"
    FORMAT = "unexpected Git observation format"
    IO = "Git observation I/O failed"


class GitError(RuntimeError):
    """No raw stderr, environment or host path in the public message."""

    def __init__(self, reason: GitFailure, *, returncode: int | None = None) -> None:
        if type(reason) is not GitFailure:
            raise TypeError("Git failure requires GitFailure")
        if returncode is not None:
            if type(returncode) is not int:
                raise TypeError("Git return code requires int or None")
            if reason is not GitFailure.COMMAND:
                raise ValueError("return code is only valid for command failure")
        self.reason = reason
        self.returncode = returncode
        super().__init__(reason.value)
