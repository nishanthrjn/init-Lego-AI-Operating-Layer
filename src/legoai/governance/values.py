"""Identity/Principal and explicit operation inputs, not established authority.

Gate-2 M2 adds the bounded-authority vocabulary named by ADR-005 SS9.1
(Grant), CONTRACTS SS15.2/SECURITY SEC-031 (Approval), and SECURITY SEC-022
(a policy-authority reference). These are immutable structural records of
what was granted/requested, never a current-validity proof: none of
`Grant`, `Approval` or `PolicyRef` asserts that its subject is still valid,
unrevoked, unconsumed or currently authenticated -- that is a later
enforcement-boundary check against live owner state (ADR-005 SS12,
ADR-007 SS6.2), deliberately out of scope for this values-only batch. No
`AuthorizationPort`, decision evaluator, or `allowed`/`authorized` boolean
lives here.
"""

from dataclasses import dataclass, field
from datetime import datetime

from legoai.kernel.context import TenantContext
from legoai.kernel.identity import CorrelationId, RequestId, TraceId, _validate
from legoai.kernel.references import OperationRef, PrincipalRef
from legoai.kernel.versions import Version


@dataclass(frozen=True, slots=True)
class Principal:
    """Identity-owner designation of a subject, requiring external verification.

    This value carries no authentication status, tenant membership or grants.
    """

    reference: PrincipalRef

    def __post_init__(self) -> None:
        if type(self.reference) is not PrincipalRef:
            raise TypeError("principal requires PrincipalRef")


@dataclass(frozen=True, slots=True)
class OperationContext:
    """Synthetic non-delegated administrative context anchor, not ExecutionContext.

    None causation explicitly denotes a root; None trace requests later receiver
    assignment. This does not satisfy the full operational CTR-005 envelope.
    Contract/subject/revision inputs belong to the consuming owner request.
    """

    operation: OperationRef
    request_id: RequestId
    correlation_id: CorrelationId
    trace_id: TraceId | None
    tenant_context: TenantContext
    acting_principal: Principal
    originating_requester: Principal
    causation: OperationRef | None

    def __post_init__(self) -> None:
        if type(self.operation) is not OperationRef:
            raise TypeError("context requires OperationRef")
        if type(self.request_id) is not RequestId:
            raise TypeError("context requires RequestId")
        if type(self.correlation_id) is not CorrelationId:
            raise TypeError("context requires CorrelationId")
        if self.trace_id is not None and type(self.trace_id) is not TraceId:
            raise TypeError("context trace must be TraceId or None")
        if type(self.tenant_context) is not TenantContext:
            raise TypeError("context requires TenantContext")
        if (
            type(self.acting_principal) is not Principal
            or type(self.originating_requester) is not Principal
        ):
            raise TypeError("context requires explicit Principals")
        if self.acting_principal != self.originating_requester:
            raise ValueError("delegated contexts are unsupported in F1")
        if self.causation is not None and type(self.causation) is not OperationRef:
            raise TypeError("causation must be OperationRef or explicit root None")
        tenant = self.tenant_context.tenant_id
        if self.operation.scope.tenant_id != tenant or (
            self.causation is not None and self.causation.scope.tenant_id != tenant
        ):
            raise ValueError("context reference tenant mismatch")
        if self.causation == self.operation:
            raise ValueError("operation cannot cause itself")


@dataclass(frozen=True, slots=True)
class GrantId:
    """Opaque Grant identity; construction issues no authority."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class ApprovalId:
    """Opaque Approval identity; construction records no decision."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class PolicyRef:
    """Opaque reference to a policy rule set maintained elsewhere (SEC-022).

    This is not the rule content and not a decision: it identifies an
    accountable issuing authority and an exact versioned policy identity for
    a later evaluator to consult. No rule text, callable, or `allowed`
    outcome is carried here.
    """

    issuer: str = field(repr=False)
    policy_id: str = field(repr=False)
    version: Version

    def __post_init__(self) -> None:
        _validate(self.issuer)
        _validate(self.policy_id)
        if type(self.version) is not Version:
            raise TypeError("policy reference requires Version")


@dataclass(frozen=True, slots=True)
class Grant:
    """Bounded authority issued by an entitled Principal (ADR-005 SS9.1; CTR
    "Permission issued by an entitled authority, bounded by subject, action,
    resources, validity, and delegation conditions").

    `action` and `resource_scope` are opaque validated text, not a
    `resource:verb` syntax: ADR-005 SS9.1 explicitly declines to select a
    universal ACL schema. This value is a record of what was issued; it is
    not proof the Grant is still valid, unrevoked, or that its issuer
    currently retains issuing authority -- ADR-005 SS12 requires that check
    against live Grant-owner state at each protected boundary, not here.
    """

    grant_id: GrantId
    issuer: Principal
    grantee: Principal
    tenant_context: TenantContext
    action: str = field(repr=False)
    resource_scope: str = field(repr=False)
    delegable: bool
    valid_from: datetime
    expires_at: datetime | None

    def __post_init__(self) -> None:
        if type(self.grant_id) is not GrantId:
            raise TypeError("grant requires GrantId")
        if type(self.issuer) is not Principal or type(self.grantee) is not Principal:
            raise TypeError("grant requires explicit Principals")
        if type(self.tenant_context) is not TenantContext:
            raise TypeError("grant requires TenantContext")
        _validate(self.action)
        _validate(self.resource_scope)
        if type(self.delegable) is not bool:
            raise TypeError("grant delegable must be a bool")
        if type(self.valid_from) is not datetime:
            raise TypeError("grant valid_from must be datetime")
        if self.valid_from.tzinfo is None:
            raise ValueError("grant valid_from must be timezone-aware")
        if self.expires_at is not None:
            if type(self.expires_at) is not datetime:
                raise TypeError("grant expires_at must be datetime or None")
            if self.expires_at.tzinfo is None:
                raise ValueError("grant expires_at must be timezone-aware")
            if self.expires_at <= self.valid_from:
                raise ValueError("grant expires_at must be after valid_from")


@dataclass(frozen=True, slots=True)
class Approval:
    """Bounded, non-replayable Approval decision request/context (CONTRACTS
    SS15.2; SECURITY SEC-031: "Approval MUST bind exact action semantics,
    target/resources, tenant, acting/requesting Principal ... eligible
    approver authority ... validity ... and allowed-use count").

    `max_uses` is the immutable declared ceiling only; remaining/consumed
    use is later owner-arbitrated state (CONTRACTS `consume_approval`), not
    tracked by this value. SEC-031 requires an explicit bound -- "no
    implicit unlimited default" -- so both `max_uses` and `expires_at` are
    mandatory here, unlike `Grant`'s optional expiry.
    """

    approval_id: ApprovalId
    operation: OperationRef
    tenant_context: TenantContext
    requester: Principal
    approver: Principal
    max_uses: int
    valid_from: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if type(self.approval_id) is not ApprovalId:
            raise TypeError("approval requires ApprovalId")
        if type(self.operation) is not OperationRef:
            raise TypeError("approval requires OperationRef")
        if type(self.tenant_context) is not TenantContext:
            raise TypeError("approval requires TenantContext")
        if (
            type(self.requester) is not Principal
            or type(self.approver) is not Principal
        ):
            raise TypeError("approval requires explicit Principals")
        if type(self.max_uses) is not int or isinstance(self.max_uses, bool):
            raise TypeError("approval max_uses must be an int")
        if self.max_uses < 1:
            raise ValueError("approval max_uses must be positive")
        if type(self.valid_from) is not datetime:
            raise TypeError("approval valid_from must be datetime")
        if self.valid_from.tzinfo is None:
            raise ValueError("approval valid_from must be timezone-aware")
        if type(self.expires_at) is not datetime:
            raise TypeError("approval expires_at must be datetime")
        if self.expires_at.tzinfo is None:
            raise ValueError("approval expires_at must be timezone-aware")
        if self.expires_at <= self.valid_from:
            raise ValueError("approval expires_at must be after valid_from")
        if self.operation.scope.tenant_id != self.tenant_context.tenant_id:
            raise ValueError("approval reference tenant mismatch")
