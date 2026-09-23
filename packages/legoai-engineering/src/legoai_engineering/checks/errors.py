"""Execution failures, separate from completed checks finding problems."""

from enum import Enum


class CheckFailure(Enum):
    UNAVAILABLE = "configured engineering executable unavailable"
    IO = "engineering process I/O failed"
    TIMEOUT = "engineering process deadline exceeded"
    OUTPUT_LIMIT = "engineering process output limit exceeded"
    CLEANUP = "engineering process termination could not be confirmed"


class CheckError(RuntimeError):
    """No retry or no-effect claim; repository code may already have run.

    Messages omit diagnostics and environment. Chained OS causes are for trusted
    operators and may contain host paths. CLEANUP requires operator inspection.
    """

    def __init__(self, reason: CheckFailure) -> None:
        if type(reason) is not CheckFailure:
            raise TypeError("check error requires CheckFailure")
        self.reason = reason
        super().__init__(reason.value)
