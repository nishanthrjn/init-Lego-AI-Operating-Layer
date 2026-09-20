"""Scoped locators without lookup, issuance, accessibility or authority.

Opaque text uses the identity module's local 1-256 code-point bound. Kind is
carried by the record type; no unversioned reference silently means latest.
"""

from dataclasses import dataclass, field

from legoai.kernel.identity import (
    ApplicationId,
    OperationId,
    PrincipalId,
    TenantId,
    _validate,
)
from legoai.kernel.versions import Version


@dataclass(frozen=True, slots=True)
class ReferenceScope:
    """Explicit accountable owner and operational tenant, not verified scope."""

    owner: str = field(repr=False)
    tenant_id: TenantId

    def __post_init__(self) -> None:
        _validate(self.owner)
        if type(self.tenant_id) is not TenantId:
            raise TypeError("scope requires TenantId")


@dataclass(frozen=True, slots=True)
class PrincipalRef:
    """Identity-owner-issued designation; tenant eligibility is separate."""

    issuer: str = field(repr=False)
    principal_id: PrincipalId

    def __post_init__(self) -> None:
        _validate(self.issuer)
        if type(self.principal_id) is not PrincipalId:
            raise TypeError("principal reference requires PrincipalId")


@dataclass(frozen=True, slots=True)
class ApplicationRef:
    scope: ReferenceScope
    application_id: ApplicationId

    def __post_init__(self) -> None:
        if type(self.scope) is not ReferenceScope:
            raise TypeError("application reference requires ReferenceScope")
        if type(self.application_id) is not ApplicationId:
            raise TypeError("application reference requires ApplicationId")


@dataclass(frozen=True, slots=True)
class ApplicationRevisionRef:
    application: ApplicationRef
    revision: str = field(repr=False)
    contract_version: Version

    def __post_init__(self) -> None:
        if type(self.application) is not ApplicationRef:
            raise TypeError("application revision requires ApplicationRef")
        _validate(self.revision)
        if type(self.contract_version) is not Version:
            raise TypeError("application revision requires Version")


@dataclass(frozen=True, slots=True)
class ConfigurationRef:
    """Configuration-instance locator, not captured configuration or selection."""

    application: ApplicationRef
    instance: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.application) is not ApplicationRef:
            raise TypeError("configuration reference requires ApplicationRef")
        _validate(self.instance)


@dataclass(frozen=True, slots=True)
class ConfigurationRevisionRef:
    """Exact opaque owner-issued R; constructing this does not publish R."""

    configuration: ConfigurationRef
    revision: str = field(repr=False)
    contract_version: Version

    def __post_init__(self) -> None:
        if type(self.configuration) is not ConfigurationRef:
            raise TypeError("configuration revision requires ConfigurationRef")
        _validate(self.revision)
        if type(self.contract_version) is not Version:
            raise TypeError("configuration revision requires Version")


@dataclass(frozen=True, slots=True)
class OwnerRevision:
    """Scoped equality guard H. Only the owner defines/allocates successors.

    F1's consumer is the Application-scoped configuration head. Its typed
    subject retains owner, tenant, Application and instance; other mutable
    subject kinds are unsupported until a consumer requires them. No ordering,
    arithmetic, timestamp or global allocation is provided.
    """

    subject: ConfigurationRef
    value: int

    def __post_init__(self) -> None:
        if type(self.subject) is not ConfigurationRef:
            raise TypeError("owner revision requires ConfigurationRef")
        if type(self.value) is not int:
            raise TypeError("owner revision must be an integer")
        if self.value < 1:
            raise ValueError("owner revision must be positive")


@dataclass(frozen=True, slots=True)
class OperationRef:
    """ADR-008 logical operation within owner/contract/tenant/subject scope."""

    subject: ApplicationRef | ConfigurationRef
    operation_id: OperationId
    contract_identity: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.subject) not in (ApplicationRef, ConfigurationRef):
            raise TypeError(
                "operation reference requires ApplicationRef or ConfigurationRef"
            )
        if type(self.operation_id) is not OperationId:
            raise TypeError("operation reference requires OperationId")
        _validate(self.contract_identity)

    @property
    def scope(self) -> ReferenceScope:
        """Scope of the typed subject; no resolution or authority lookup."""
        if isinstance(self.subject, ConfigurationRef):
            return self.subject.application.scope
        return self.subject.scope
