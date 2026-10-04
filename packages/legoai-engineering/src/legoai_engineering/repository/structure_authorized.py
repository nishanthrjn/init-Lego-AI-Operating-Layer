"""DISCOVERY-1 trusted local acquisition: current authority, two bounded passes."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from legoai.governance.ports import (
    AuthorizationOutcome,
    AuthorizationPort,
    SecurityContext,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.references import ConfigurationRef

from legoai_engineering._authority import _bind, _evaluate
from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.ports import RepositoryWorkspacePort
from legoai_engineering.repository.structure import (
    RepositoryStructure,
    RepositoryStructurePolicy,
    StructureError,
    StructureFailure,
    _path,
)
from legoai_engineering.repository.workspace import (
    WorkspaceEntry,
    WorkspaceEntryKind,
)

REPOSITORY_STRUCTURE_ACTION = "read-structure-for-model-analysis"


@dataclass(frozen=True, slots=True)
class AuthorizedRepositoryStructure:
    """No model, content reads, retries or writes. No atomic snapshot promise.

    Composition binds the workspace to this reference and approved policy; its
    listing adapter must use <=512 scanned entries per directory and no hidden
    exclusions beyond the structure policy. The unchanged Port cannot attest
    adapter configuration. Synchronous I/O retains M2's lack of hard deadlines.
    """

    workspace_reference: ConfigurationRef = field(repr=False)
    workspace: RepositoryWorkspacePort = field(repr=False)
    security_context: SecurityContext = field(repr=False)
    authorization: AuthorizationPort = field(repr=False)
    policy: RepositoryStructurePolicy = field(repr=False)
    clock: Callable[[], datetime] = field(repr=False)

    def __post_init__(self) -> None:
        try:
            _bind(
                self.workspace_reference,
                self.security_context,
                REPOSITORY_STRUCTURE_ACTION,
            )
            if type(self.policy) is not RepositoryStructurePolicy or not callable(
                self.clock
            ):
                raise ValueError("invalid structure composition")
            if not callable(
                getattr(self.workspace, "list_entries", None)
            ) or not callable(getattr(self.authorization, "evaluate", None)):
                raise ValueError("invalid structure dependency")
        except (TypeError, ValueError) as error:
            raise StructureError(StructureFailure.CONFIGURATION_INVALID) from error

    def _authorize(self, tenant: TenantContext) -> None:
        if (
            type(tenant) is not TenantContext
            or tenant != self.security_context.tenant_context
        ):
            raise StructureError(StructureFailure.AUTHORIZATION_DENIED)
        outcome = _evaluate(self.security_context, self.authorization, self.clock)
        if outcome is AuthorizationOutcome.UNAVAILABLE:
            raise StructureError(StructureFailure.AUTHORITY_UNAVAILABLE)
        if outcome is not AuthorizationOutcome.ALLOWED:
            raise StructureError(StructureFailure.AUTHORIZATION_DENIED)

    def acquire(self, tenant: TenantContext) -> RepositoryStructure:
        """Release only two equal complete maps and a fresh final ALLOW.

        Failure never returns partial data. Earlier authorized listings cannot
        be undone. Consumers must separately authorize any later disclosure.
        """
        first = self._pass(tenant)
        second = self._pass(tenant)
        if first != second:
            raise StructureError(StructureFailure.STRUCTURE_CHANGED)
        self._authorize(tenant)
        return second

    def _pass(self, tenant: TenantContext) -> RepositoryStructure:
        pending = sorted(self.policy.roots, key=lambda p: p.value)
        entries = [WorkspaceEntry(p, WorkspaceEntryKind.DIRECTORY) for p in pending]
        RepositoryStructure(self.policy, tuple(entries))
        seen = {p.value.casefold() for p in pending}
        calls = 0
        while pending:
            if calls >= self.policy.max_list_calls:
                raise StructureError(StructureFailure.STRUCTURE_LIMIT_EXCEEDED)
            directory = pending.pop(0)
            self._authorize(tenant)
            calls += 1
            try:
                children = self.workspace.list_entries(directory)
            except WorkspaceError as error:
                reason = {
                    WorkspaceFailure.BOUNDARY: StructureFailure.BOUNDARY_VIOLATION,
                    WorkspaceFailure.EXCLUDED: StructureFailure.BOUNDARY_VIOLATION,
                    WorkspaceFailure.LIMIT: StructureFailure.STRUCTURE_LIMIT_EXCEEDED,
                    WorkspaceFailure.CHANGED: StructureFailure.STRUCTURE_CHANGED,
                    WorkspaceFailure.NOT_FILE: StructureFailure.UNSUPPORTED_ENTRY,
                    WorkspaceFailure.NOT_DIRECTORY: StructureFailure.UNSUPPORTED_ENTRY,
                    WorkspaceFailure.DECODE: StructureFailure.UNSUPPORTED_ENTRY,
                    WorkspaceFailure.BINARY: StructureFailure.UNSUPPORTED_ENTRY,
                }.get(error.reason, StructureFailure.WORKSPACE_UNAVAILABLE)
                raise StructureError(reason) from error
            if type(children) is not tuple:
                raise StructureError(StructureFailure.UNSUPPORTED_ENTRY)
            if len(children) > 512:
                raise StructureError(StructureFailure.STRUCTURE_LIMIT_EXCEEDED)
            for child in children:
                if (
                    type(child) is not WorkspaceEntry
                    or type(child.kind) is not WorkspaceEntryKind
                ):
                    raise StructureError(StructureFailure.UNSUPPORTED_ENTRY)
                _path(child.path)
                if child.path.value.rpartition("/")[0] != directory.value:
                    raise StructureError(StructureFailure.BOUNDARY_VIOLATION)
                alias = child.path.value.casefold()
                if alias in seen:
                    raise StructureError(StructureFailure.BOUNDARY_VIOLATION)
                seen.add(alias)
                if self.policy.excludes(child.path):
                    continue
                entries.append(child)
                # Check depth/entry/byte budgets before another listing. Include
                # roots and discovered directories; no traversal completeness
                # claim is made until both complete passes have succeeded.
                RepositoryStructure(
                    self.policy, tuple(sorted(entries, key=lambda e: e.path.value))
                )
                if child.kind is WorkspaceEntryKind.DIRECTORY:
                    pending.append(child.path)
            pending.sort(key=lambda p: p.value)
        return RepositoryStructure(
            self.policy, tuple(sorted(entries, key=lambda e: e.path.value))
        )
