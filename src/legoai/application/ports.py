"""Owner-specific storage boundary for the Application Composition
configuration owner (ADR-003/004/008/009; Gate-1 plan SS6, SS9.1).

Not a generic repository, UnitOfWork, or database Port: every operation
below models one specific owner behavior the Gate-1 plan names, not generic
CRUD. This module defines the Protocol contract only -- no realization
(neither the in-memory test fake under ``tests/support`` nor a future F6a
SQLite adapter) lives here, and no transaction object is exposed publicly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from legoai.application.values import (
    ComposedConfiguration,
    ConfigurationPublicationOperation,
    ConfigurationPublicationResult,
    ConfigurationSourceSubmissionDuty,
)
from legoai.kernel.references import (
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    OwnerRevision,
)


class UnknownRevisionError(LookupError):
    """Raised when an exact requested configuration revision is unavailable.

    Never substituted with the current/latest revision (SPEC S-03; ADR-004
    "exact reference lookup"): a caller asking for a specific historical
    revision either gets that exact revision or this explicit failure.
    """


@runtime_checkable
class ConfigurationStorePort(Protocol):
    """Synchronous owner-local storage boundary for one configuration owner.

    One call at a time in this reference contract; no pooling, transaction
    object, or SQL concept is part of the Protocol itself -- only the
    semantic operations Gate-1 SS6/SS9.1 name.
    """

    def current_head(self, target: ConfigurationRef) -> OwnerRevision | None:
        """The owner-issued head revision H used for conditional-mutation
        guards, or None if target has never been published (a real, valid
        state, not a missing/unavailable one). H is distinct from the
        immutable content revision R returned by current_published: H
        guards *mutation*, R identifies *exact meaning* (Gate-1 SS9.1)."""
        ...

    def current_published(
        self, target: ConfigurationRef
    ) -> ConfigurationRevisionRef | None:
        """The exact immutable content revision R currently published for
        target, or None if target has never been published."""
        ...

    def read_revision(
        self, revision: ConfigurationRevisionRef
    ) -> ComposedConfiguration:
        """Exact historical meaning for one immutable published revision.

        Raises UnknownRevisionError if that exact revision is unavailable;
        never returns the current/latest revision as a substitute.
        """
        ...

    def publish(
        self, operation: ConfigurationPublicationOperation
    ) -> ConfigurationPublicationResult:
        """Conditionally publish under operation.expected_revision (or
        explicit expected absence).

        If operation.operation was already committed under this exact
        identity, returns that original retained result unchanged -- it does
        not create a second commit and does not fail merely because the head
        has since advanced (ADR-008 operation equivalence; lost-acknowledgment
        recovery). If the currently published revision does not match
        operation.expected_revision, returns a REJECTED result carrying a
        Conflict-category error -- the stale attempt is never silently
        superseded or silently accepted.
        """
        ...

    def operation_result(
        self, operation: OperationRef
    ) -> ConfigurationPublicationResult | None:
        """Retained result for a previously submitted operation, or None if
        this exact operation was never committed. Pure read-only inquiry;
        never attempts a new publish."""
        ...

    def outstanding_duties(
        self, target: ConfigurationRef
    ) -> tuple[ConfigurationSourceSubmissionDuty, ...]:
        """Bounded listing of outstanding duties within target's owner
        scope. Scope-filtered: a duty belonging to a different tenant or
        application is never returned."""
        ...
