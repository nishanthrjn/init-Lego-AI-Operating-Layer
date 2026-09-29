"""Current authorization immediately before an M4 write (ADR-018 CR-3)."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from legoai.governance.ports import AuthorizationPort, SecurityContext
from legoai.kernel.references import ConfigurationRef

from legoai_engineering._authority import _bind, _require
from legoai_engineering.repository.mutation import (
    RepositoryChangeSet,
    RepositoryMutationResult,
)
from legoai_engineering.repository.mutation_ports import RepositoryMutationPort

REPOSITORY_MUTATION_ACTION = "apply-repository-changes"


@dataclass(frozen=True, slots=True)
class AuthorizedRepositoryMutation:
    """RepositoryMutationPort decorator; the inner adapter still owns the write.

    The operator binds workspace_reference to the inner adapter's workspace.
    Every apply evaluates current Governance for apply-repository-changes on
    that workspace, then calls the inner adapter exactly once. Denial raises
    EffectAuthorizationError before any write. Approval-bearing contexts are
    refused. M4 validation, preconditions, errors and partial-effect reporting
    pass through unchanged; there is no retry, rollback or scope argument.
    """

    workspace_reference: ConfigurationRef
    mutation: RepositoryMutationPort = field(repr=False)
    security_context: SecurityContext = field(repr=False)
    authorization: AuthorizationPort = field(repr=False)
    clock: Callable[[], datetime] = field(repr=False)

    def __post_init__(self) -> None:
        _bind(
            self.workspace_reference,
            self.security_context,
            REPOSITORY_MUTATION_ACTION,
        )
        if not callable(getattr(self.mutation, "apply", None)):
            raise TypeError("authorized mutation requires RepositoryMutationPort")
        if not callable(getattr(self.authorization, "evaluate", None)):
            raise TypeError("authorized mutation requires AuthorizationPort")
        if not callable(self.clock):
            raise TypeError("authorized mutation requires a clock")

    def apply(self, changeset: RepositoryChangeSet) -> RepositoryMutationResult:
        if type(changeset) is not RepositoryChangeSet:
            raise TypeError("authorized mutation requires RepositoryChangeSet")
        _require(self.security_context, self.authorization, self.clock)
        return self.mutation.apply(changeset)
