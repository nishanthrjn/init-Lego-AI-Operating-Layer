"""Gate-2 M9: dispatch-arbitration operation request/result values and the
`DispatchArbiterPort` Protocol (ADR-007's exclusive-gate decision; ADR-002's
`legoai.execution` "checkpoint reference meaning" row realized by
`legoai.reference.execution`, ADR-002 line ~178: "Execution Coordinator,
direct driver and checkpoint records ... ADR-004/005/007/008/009").

Critical invariant (task's own framing): a dispatch decision is valid only
for the gate evaluation in which current state was checked. `DispatchDecision`
is a point-in-time fact, exactly like M4's `AuthorizationDecision` and M7's
`CapabilityResolution` before it -- "prepared earlier" is never "still valid
now". The arbiter (`legoai.reference.execution`) revalidates current
authorization, current Approval-use state, and current Catalog publication
*inside one exclusive gate* immediately before permitting dispatch; it never
reuses a historical decision.

The arbiter **decides**; it never **dispatches**. No `invoke`/`execute`/
`call_provider`/`activate` method exists anywhere in this module, and
`DispatchPermit` carries no callable, provider instance, adapter, or
runtime Plugin object -- only inert references to what was checked and
committed.

`DispatchRequest.resolved_entry` is a `CatalogEntry` (M6), not a
`CapabilityResolution` (M7, `legoai.reference.resolution`): a contract-layer
module must not import another owner's *reference* realization (ADR-002 SS9:
"Public contracts never import this implementation area"), so the caller
extracts the single resolved candidate from an already-`RESOLVED`
`CapabilityResolution` before constructing this request. This is a
structural simplification, not a functional gap: `CapabilityResolution`'s
own cardinality invariant already guarantees exactly one candidate when
`status is RESOLVED`.

**No exactly-once claim.** M9 makes no operation-ledger/dedup guarantee
beyond what ADR-008 already establishes elsewhere; `DispatchDecision`/
`DispatchPermit` carry `operation: OperationRef` for attribution only, not
as proof no equivalent dispatch has occurred or will occur. A persisted
Execution/dispatch ledger (closing that gap) is explicitly deferred to a
later batch.

**Resource claims are out of scope for this batch.** M3's `ResourceClaim`
values remain purely declarative; no `ResourcePort`/reservation mechanism
exists yet, and the first governed deterministic slice (F8b's
`normalize_text`) declares no resource requirement. `DispatchRequest`
therefore carries no resource field; a later batch introducing a genuine
resource-bearing capability must add that predicate then, not here.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol

from legoai.capabilities.ports import CatalogEntry
from legoai.evidence.ports import EvidenceId
from legoai.governance.ports import (
    AuthorizationDecision,
    AuthorizationOutcome,
    SecurityContext,
)
from legoai.kernel.errors import ErrorCategory
from legoai.kernel.references import OperationRef


class DispatchOutcome(Enum):
    """Exactly the outcomes this batch's predicate set can distinguish.
    `CONFLICT` (a persisted operation-ledger dedup fact) is deliberately not
    added: no such ledger exists yet in this reference slice (see module
    docstring's exactly-once disclaimer).
    """

    PERMITTED = "permitted"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class DispatchRequest:
    """An already-prepared candidate dispatch, bundling exactly what the
    gate must revalidate: `security_context` (current-authority facts to
    re-evaluate fresh -- never a cached decision) and `resolved_entry` (the
    single Catalog-published candidate an earlier `RESOLVED`
    `CapabilityResolution` identified). `required_evidence_ids` names
    already-custodied evidence (M8) the gate must confirm is still present
    -- ADR-007 SS6.1 step 5: "Obtain required pre-effect custody ...
    final applicability checks remain inside" the gate, i.e. custody itself
    happens during preparation, and the gate only confirms it.
    """

    security_context: SecurityContext
    resolved_entry: CatalogEntry
    required_evidence_ids: tuple[EvidenceId, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if type(self.security_context) is not SecurityContext:
            raise TypeError("dispatch request requires SecurityContext")
        if type(self.resolved_entry) is not CatalogEntry:
            raise TypeError("dispatch request requires CatalogEntry")
        if type(self.required_evidence_ids) is not tuple or any(
            type(evidence_id) is not EvidenceId
            for evidence_id in self.required_evidence_ids
        ):
            raise TypeError(
                "dispatch request required_evidence_ids must be an immutable "
                "tuple of EvidenceId"
            )
        if self.resolved_entry.tenant_context != self.security_context.tenant_context:
            raise ValueError("dispatch request tenant mismatch")


@dataclass(frozen=True, slots=True)
class DispatchPermit:
    """Inert permission to cross the next boundary under the exact
    committed facts -- never an executable binding. No callable, provider
    instance, adapter, or runtime Plugin object is representable here.
    Whether a permit may be used more than once (replay protection) is
    explicitly deferred to a later Coordinator/M10 batch: this value has no
    consumed/used flag of its own (mutable state inside an immutable value
    would be a contradiction, and the accepted plan does not yet define
    one-use enforcement).
    """

    operation: OperationRef
    resolved_entry: CatalogEntry
    catalog_revision: int
    security_decision: AuthorizationDecision
    granted_at: datetime

    def __post_init__(self) -> None:
        if type(self.operation) is not OperationRef:
            raise TypeError("dispatch permit requires OperationRef")
        if type(self.resolved_entry) is not CatalogEntry:
            raise TypeError("dispatch permit requires CatalogEntry")
        if type(self.catalog_revision) is not int or isinstance(
            self.catalog_revision, bool
        ):
            raise TypeError("dispatch permit catalog_revision must be an int")
        if self.catalog_revision < 0:
            raise ValueError("dispatch permit catalog_revision must be nonnegative")
        if type(self.security_decision) is not AuthorizationDecision:
            raise TypeError("dispatch permit requires AuthorizationDecision")
        if self.security_decision.outcome is not AuthorizationOutcome.ALLOWED:
            raise ValueError("dispatch permit requires an ALLOWED security decision")
        if type(self.granted_at) is not datetime:
            raise TypeError("dispatch permit granted_at must be datetime")
        if self.granted_at.tzinfo is None:
            raise ValueError("dispatch permit granted_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class DispatchDecision:
    """Immutable, point-in-time gate result. `permit` is present if and
    only if `outcome is PERMITTED`; `category` is present if and only if it
    is not. This decision proves only that the stated predicates held at
    `evaluated_at` under one exclusive gate evaluation -- never that they
    will still hold an instant later.
    """

    outcome: DispatchOutcome
    operation: OperationRef
    evaluated_at: datetime
    category: ErrorCategory | None
    permit: DispatchPermit | None

    def __post_init__(self) -> None:
        if type(self.outcome) is not DispatchOutcome:
            raise TypeError("dispatch decision requires DispatchOutcome")
        if type(self.operation) is not OperationRef:
            raise TypeError("dispatch decision requires OperationRef")
        if type(self.evaluated_at) is not datetime:
            raise TypeError("dispatch decision evaluated_at must be datetime")
        if self.evaluated_at.tzinfo is None:
            raise ValueError("dispatch decision evaluated_at must be timezone-aware")
        if self.category is not None and type(self.category) is not ErrorCategory:
            raise TypeError("dispatch decision category must be ErrorCategory or None")
        if self.permit is not None and type(self.permit) is not DispatchPermit:
            raise TypeError("dispatch decision permit must be DispatchPermit or None")
        if self.outcome is DispatchOutcome.PERMITTED:
            if self.category is not None:
                raise ValueError("permitted decision must not carry a category")
            if self.permit is None:
                raise ValueError("permitted decision requires a permit")
        else:
            if self.category is None:
                raise ValueError("non-permitted decision requires a category")
            if self.permit is not None:
                raise ValueError("non-permitted decision must not carry a permit")


class DispatchArbiterPort(Protocol):
    """The single external-facing dispatch-arbitration seam. Decides
    whether dispatch is permitted; it never performs the dispatch effect
    itself (no `execute`/`invoke` method exists anywhere in this contract).
    """

    def arbitrate(
        self, request: DispatchRequest, *, evaluated_at: datetime
    ) -> DispatchDecision: ...
