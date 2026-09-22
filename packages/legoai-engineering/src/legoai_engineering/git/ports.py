"""One bounded semantic observation, never arbitrary Git arguments."""

from typing import Protocol

from legoai_engineering.git.values import GitRepositoryState


class GitRepositoryPort(Protocol):
    def inspect(self) -> GitRepositoryState:
        """Read HEAD and changed/untracked paths; fail without partial results.

        GitError and M2 WorkspaceError preserve distinct failure categories.
        Synchronous; no retries or atomic-snapshot promise. Admission and
        disclosure authorization remain the trusted runtime's responsibility.
        """
        ...
