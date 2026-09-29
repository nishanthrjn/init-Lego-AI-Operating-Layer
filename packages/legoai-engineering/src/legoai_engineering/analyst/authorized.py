"""Trusted read-for-analysis wiring; never selected by the model."""

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
from legoai_engineering.analyst.values import (
    AcquisitionFailure,
    EvidenceAcquisitionError,
    RepositoryEvidence,
    _paths,
)
from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.ports import RepositoryWorkspacePort
from legoai_engineering.repository.workspace import RepositoryPath

REPOSITORY_READ_ACTION = "read-for-model-analysis"


@dataclass(frozen=True, slots=True)
class AuthorizedRepositoryEvidence:
    """Operator association, not a new permission issuer or capability registry.

    The operator binds workspace_reference to this explicit workspace Port and
    allowed paths. Existing Governance validates current grant/policy per read.
    The grant action must cover read-for-model-analysis. Approvals are unsupported
    rather than consumed without a dispatch owner. M2 synchronous I/O and trusted
    stable-workspace limitations remain; no atomic repository snapshot is claimed.
    """

    workspace_reference: ConfigurationRef
    workspace: RepositoryWorkspacePort = field(repr=False)
    security_context: SecurityContext = field(repr=False)
    authorization: AuthorizationPort = field(repr=False)
    allowed_paths: tuple[RepositoryPath, ...]
    clock: Callable[[], datetime] = field(repr=False)

    def __post_init__(self) -> None:
        _bind(self.workspace_reference, self.security_context, REPOSITORY_READ_ACTION)
        _paths(self.allowed_paths)

    def _authorize(self, tenant: TenantContext) -> None:
        if tenant != self.security_context.tenant_context:
            raise EvidenceAcquisitionError(AcquisitionFailure.DENIED)
        outcome = _evaluate(self.security_context, self.authorization, self.clock)
        if outcome is AuthorizationOutcome.UNAVAILABLE:
            raise EvidenceAcquisitionError(AcquisitionFailure.UNAVAILABLE)
        if outcome is not AuthorizationOutcome.ALLOWED:
            raise EvidenceAcquisitionError(AcquisitionFailure.DENIED)

    async def acquire(
        self, targets: tuple[RepositoryPath, ...], tenant: TenantContext
    ) -> RepositoryEvidence:
        _paths(targets)
        if type(tenant) is not TenantContext:
            raise TypeError("evidence reader requires TenantContext")
        if any(p not in self.allowed_paths for p in targets):
            raise EvidenceAcquisitionError(AcquisitionFailure.DENIED)
        files = []
        for path in sorted(targets, key=lambda p: p.value):
            self._authorize(tenant)
            try:
                text = self.workspace.read_text(path)
            except WorkspaceError as error:
                reason = (
                    AcquisitionFailure.BOUNDARY
                    if error.reason is WorkspaceFailure.BOUNDARY
                    else AcquisitionFailure.BUDGET
                    if error.reason is WorkspaceFailure.LIMIT
                    else AcquisitionFailure.UNAVAILABLE
                )
                raise EvidenceAcquisitionError(reason) from None
            if text.path != path.value:
                raise ValueError("workspace returned a different path")
            files.append(text)
            try:
                # Enforce aggregate limits incrementally, before another read.
                RepositoryEvidence(tuple(files))
            except TypeError, ValueError:
                raise EvidenceAcquisitionError(AcquisitionFailure.BUDGET) from None
        self._authorize(tenant)
        return RepositoryEvidence(tuple(files))
