"""Mutation authority is separate from the read-only workspace Port."""

from typing import Protocol

from legoai_engineering.repository.mutation import (
    RepositoryChangeSet,
    RepositoryMutationResult,
)


class RepositoryMutationPort(Protocol):
    def apply(self, changeset: RepositoryChangeSet) -> RepositoryMutationResult:
        """Preflight all changes, then apply in request order without retries.

        Validation/precondition failure before preparation changes no target.
        Final I/O can partially apply: MutationApplyError retains known effects
        and uncertainty. No multi-file transaction or crash rollback is promised.
        Authorization, deadlines and governed dispatch belong to the runtime.
        """
        ...
