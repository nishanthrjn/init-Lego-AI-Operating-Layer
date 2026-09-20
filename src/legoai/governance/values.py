"""Identity/Principal and explicit operation inputs, not established authority."""

from dataclasses import dataclass

from legoai.kernel.context import TenantContext
from legoai.kernel.identity import CorrelationId, RequestId, TraceId
from legoai.kernel.references import OperationRef, PrincipalRef


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
