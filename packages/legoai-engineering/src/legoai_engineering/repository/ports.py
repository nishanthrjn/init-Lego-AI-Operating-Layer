"""Replaceable synchronous acquisition boundary for an already-bound workspace."""

from typing import Protocol

from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath, WorkspaceEntry


class RepositoryWorkspacePort(Protocol):
    """Read-only acquisition; runtime admission/authorization are separate.

    Failures raise WorkspaceError; invalid Python argument types raise TypeError.
    Lists are complete for the requested directory under explicit exclusions,
    sorted by relative path, or fail without a partial result on limit/I/O error.
    Reads return bounded M1 RepositoryText with strict UTF-8 and preserved newlines.
    Calls never retry. This synchronous subset offers no hard I/O deadline or
    cancellation guarantee; a remote/async realization needs its own contract.
    """

    def list_entries(
        self, directory: RepositoryPath | None
    ) -> tuple[WorkspaceEntry, ...]:
        """List one directory; explicit None denotes this bound workspace root."""
        ...

    def read_text(self, path: RepositoryPath) -> RepositoryText:
        """Read one regular file; no raw host-path or byte-stream API."""
        ...
