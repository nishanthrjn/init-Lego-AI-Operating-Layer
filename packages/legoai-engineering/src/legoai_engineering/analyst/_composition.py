"""Trusted read-for-analysis wiring; never selected by the model."""

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime

from legoai.governance.ports import (
    AuthorizationDecision,
    AuthorizationOutcome,
    AuthorizationPort,
    SecurityContext,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.references import ConfigurationRef

from legoai_engineering.analyst.values import (
    AcquisitionFailure,
    EvidenceAcquisitionError,
    RepositoryEvidence,
    _paths,
)
from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.ports import RepositoryWorkspacePort
from legoai_engineering.repository.workspace import RepositoryPath


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
        if type(self.workspace_reference) is not ConfigurationRef:
            raise TypeError("evidence reader requires workspace ConfigurationRef")
        if type(self.security_context) is not SecurityContext:
            raise TypeError("evidence reader requires SecurityContext")
        _paths(self.allowed_paths)
        security = self.security_context
        if (
            security.operation.subject != self.workspace_reference
            or security.action != "read-for-model-analysis"
            or security.resource_scope != self.workspace_reference.instance
            or security.approval is not None
        ):
            raise ValueError("unsupported repository read authorization scope")

    def _authorize(self, tenant: TenantContext) -> None:
        if tenant != self.security_context.tenant_context:
            raise EvidenceAcquisitionError(AcquisitionFailure.DENIED)
        context = replace(self.security_context, established_at=self.clock())
        decision = self.authorization.evaluate(context)
        if type(decision) is not AuthorizationDecision:
            raise TypeError("authorization must return AuthorizationDecision")
        if (
            decision.operation != context.operation
            or decision.evaluated_at != context.established_at
        ):
            raise EvidenceAcquisitionError(AcquisitionFailure.DENIED)
        if decision.outcome is AuthorizationOutcome.UNAVAILABLE:
            raise EvidenceAcquisitionError(AcquisitionFailure.UNAVAILABLE)
        if decision.outcome is not AuthorizationOutcome.ALLOWED:
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
