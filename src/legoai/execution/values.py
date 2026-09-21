"""Gate-2 M1: Execution-owned semantic values -- what an Execution *is
described as*, not how it is created, authorized, admitted, resourced,
dispatched, invoked, retried, cancelled, supervised or persisted.

This module realizes the public `legoai.execution` value vocabulary named by
ADR-002 SS3.1 (row `legoai.execution`), ADR-015 SS2's exact canonical
Execution state list, and ADR-008 SS4.1's identity-domain distinctions. It
contains no runtime behavior: no Coordinator, no admission, no dispatch, no
persistence and no asyncio. Those are separate, later Gate-2 batches under
`legoai.reference.execution` and the private `legoai.runtime` composition
root (`planning/GATE-2-IMPLEMENTATION-PLAN.md` SS20-21).

`ExecutionId` is a distinct identity from the logical `OperationId`/
`OperationRef` (Kernel; ADR-008 SS4.1): one logical operation may have
several linked Execution attempts, and an Execution attempt never
substitutes for -- or is aliased to -- its logical operation identity.

`SecurityContextRef` is an opaque reference to a security context
established elsewhere (ADR-005 SS10.1: an owner-issued, operation-bound
context reference, never a bearer credential or a consumer-supplied copy).
Holding this reference is not proof that the referenced authorization
currently remains valid: ADR-007 SS12.1 requires demonstrable current
revalidation at the actual dispatch boundary regardless of what any retained
reference says. This value carries no permission, grant, role, policy
decision or credential material -- embedding any of those here would let a
structurally valid value stand in for authority Governance has not (or no
longer) granted. `legoai.governance` is deliberately not imported by this
module: ADR-002 SS9's `values.py` rule ("It does not import another owner's
values") forbids embedding a foreign owner's value (such as `Principal`)
directly in this owner's public values; a later Port-layer batch composes
Execution and Governance references without merging their value modules.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorDetail
from legoai.kernel.identity import CorrelationId, TraceId, _validate
from legoai.kernel.references import OperationRef


class ExecutionState(Enum):
    """The exact ten canonical Execution states (ADR-015 SS2).

    No other state exists here. Technical observations such as queue entry,
    worker assignment, cancellation signalling or shutdown phase are not
    canonical states and must never be added to this enum.
    """

    CREATED = "created"
    ADMITTED = "admitted"
    RUNNING = "running"
    WAITING = "waiting"
    SUSPENDED = "suspended"
    CANCELLING = "cancelling"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ExecutionId:
    """One Execution attempt; not an OperationId, OwnerRevision or retry count.

    Callers supply the identity; no random generation, wall clock or global
    counter exists here. ADR-008 SS4.1: a genuine execution retry is a
    *linked new* Execution minted by whatever owns admission, never by this
    value type.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class SecurityContextRef:
    """Opaque reference to a security context established elsewhere.

    See module docstring for the reference-versus-proof distinction. `issuer`
    identifies the accountable owner that issued the referenced context;
    `reference` is an opaque locator only, never raw credential, permission,
    role or policy content.
    """

    issuer: str = field(repr=False)
    reference: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.issuer)
        _validate(self.reference)


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Immutable Execution admission/attempt context.

    The field set is limited to what is canonically justified for a
    values-only Gate-2 batch: ADR-015 SS2 ("Execution context, admission,
    attempts, scheduling intent, cancellation"), ADR-005 SS7 ("Each
    Execution pins exactly one effective TenantContext") and ADR-007 SS8
    (deadline propagation). Resource, Approval and admitted-candidate
    references are deliberately excluded: `legoai.resources` and Plugin/
    Catalog admission do not exist yet, and adding placeholder fields for
    them now would make this a convenience context bag rather than a
    canonically justified value (Gate-2 plan SS12).
    """

    execution_id: ExecutionId
    operation: OperationRef
    tenant_context: TenantContext
    security_context_ref: SecurityContextRef
    correlation_id: CorrelationId
    trace_id: TraceId | None
    deadline: datetime | None
    causation: OperationRef | None

    def __post_init__(self) -> None:
        if type(self.execution_id) is not ExecutionId:
            raise TypeError("execution context requires ExecutionId")
        if type(self.operation) is not OperationRef:
            raise TypeError("execution context requires OperationRef")
        if type(self.tenant_context) is not TenantContext:
            raise TypeError("execution context requires TenantContext")
        if type(self.security_context_ref) is not SecurityContextRef:
            raise TypeError("execution context requires SecurityContextRef")
        if type(self.correlation_id) is not CorrelationId:
            raise TypeError("execution context requires CorrelationId")
        if self.trace_id is not None and type(self.trace_id) is not TraceId:
            raise TypeError("execution context trace must be TraceId or None")
        if self.deadline is not None:
            if type(self.deadline) is not datetime:
                raise TypeError("execution context deadline must be datetime or None")
            if self.deadline.tzinfo is None:
                raise ValueError("execution context deadline must be timezone-aware")
        if self.causation is not None and type(self.causation) is not OperationRef:
            raise TypeError("execution context causation must be OperationRef or None")
        tenant = self.tenant_context.tenant_id
        if self.operation.scope.tenant_id != tenant or (
            self.causation is not None and self.causation.scope.tenant_id != tenant
        ):
            raise ValueError("execution context reference tenant mismatch")
        if self.causation == self.operation:
            raise ValueError("operation cannot cause itself")


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Recorded terminal Execution outcome facts; this value invokes nothing.

    `final_state` is restricted to the four canonical terminal states
    (ADR-015 SS2: succeeded/failed/cancelled/rejected -- "Rejected remains
    limited to never-begun work with no admitted protected execution
    effect", which is enforced here as `REJECTED` requiring
    `EffectExtent.NONE`). `effect` reuses Kernel's `EffectExtent` unchanged,
    preserving `UNKNOWN` as distinct from `NONE`. `error` reuses Kernel's
    `ErrorDetail` unchanged; no new error hierarchy is introduced.

    `ExecutionResult` is not the canonical application/domain Outcome (SPEC
    DEC-01): a later batch may have it reference an Outcome where canonically
    required, but this value never collapses Outcome meaning into itself.
    """

    execution_id: ExecutionId
    final_state: ExecutionState
    effect: EffectExtent
    error: ErrorDetail | None

    def __post_init__(self) -> None:
        if type(self.execution_id) is not ExecutionId:
            raise TypeError("execution result requires ExecutionId")
        if type(self.final_state) is not ExecutionState:
            raise TypeError("execution result requires ExecutionState")
        if self.final_state not in (
            ExecutionState.SUCCEEDED,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
            ExecutionState.REJECTED,
        ):
            raise ValueError("execution result final_state must be a terminal state")
        if type(self.effect) is not EffectExtent:
            raise TypeError("execution result requires EffectExtent")
        if self.error is not None and type(self.error) is not ErrorDetail:
            raise TypeError("execution result error must be ErrorDetail or None")
        if (
            self.final_state is ExecutionState.REJECTED
            and self.effect is not EffectExtent.NONE
        ):
            raise ValueError("rejected execution result must have EffectExtent.NONE")
