"""Gate-2 M3: Resource-owned semantic values -- the vocabulary needed to
describe a resource requirement or a resource-accounting fact, not to
allocate, reserve, consume, meter, bill or enforce anything.

This module realizes the minimum subset of ADR-007 SS9's quantity model and
CONTRACTS' `reserve_resource`/`consume_resource` input shape that a values-
only Gate-2 batch can canonically justify. It contains no runtime behavior:
no `ResourcePort`, no allocation/reservation engine, no quota/budget service,
no capacity discovery. Those remain later, separately authorized batches
(ADR-007 SS9 names Resource Admission and Accounting as their owner).

Critical distinction preserved throughout (task SS2/SS6): a `ResourceClaim`
constructed here is a declared requirement or a recorded accounting fact --
never proof that capacity exists, that a reservation succeeded, that a
quota is available, or that a resource-policy decision was made. Those are
later owner-committed facts under a `ResourcePort` this batch does not
define (ADR-007 SS6.1-SS6.2, SS9.3).

`ResourceDimension` is deliberately an open, opaque identifier rather than a
closed enumeration of common systems (compute/memory/network/tokens/...):
ADR-007 SS3/SS14 explicitly states "No resource quantum, currency, tariff,
numeric precision... is selected. Q-06 parameters must be supplied by
their accountable authority for each supported resource dimension" -- an
enum guessed from common systems would silently invent that authority's
answer.

Budget/Quota/Limit (ADR-007 SS9.1) are deliberately **not** modeled here.
Those are allocation/policy constraint concepts owned by the later Resource
Admission and Accounting realization; their meaning depends on window/
reset/occupancy semantics that are runtime accounting concerns, not needed
merely to describe a declared claim. Likewise, ADR-007 SS9's "precision/
rounding and uncertainty or explicit unknown" axis is not modeled: no
canonical document defines its concrete value shape yet, and a guessed
shape would risk exactly the invented-taxonomy problem this module avoids
for dimensions.

This module deliberately imports only Kernel: ADR-002 SS9's `values.py`
rule ("It does not import another owner's values") applies here exactly as
it did for `execution.values` (M1) and `governance.values` (M2), even
though ADR-002 SS9.2's R-row foreign-*contract*-target table (for a future
`ports.py`) would separately permit Governance/Observability. `Grant`,
`Approval` and `ExecutionId` are therefore not referenced by this module;
`ResourceClaim` binds to the logical operation via Kernel's `OperationRef`
only, preserving `operation identity != execution identity`.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from legoai.kernel.context import TenantContext
from legoai.kernel.identity import _validate
from legoai.kernel.references import OperationRef
from legoai.kernel.versions import Version


@dataclass(frozen=True, slots=True)
class ResourceDimension:
    """Opaque resource dimension identity; construction claims no capacity.

    Not a closed enum of compute/memory/network/tokens/... -- see module
    docstring. Callers supply the accountable authority's own identifier.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


class ResourceAmountKind(Enum):
    """ADR-007 SS9's exact "amount kind" vocabulary. No additional kind is
    invented, and none of these implies the amount is currently available,
    granted, or authoritative -- that is a later owner-committed fact.
    """

    ESTIMATE = "estimate"
    BOUND = "bound"
    RESERVATION = "reservation"
    ACTUAL = "actual"
    CORRECTION = "correction"


@dataclass(frozen=True, slots=True)
class ResourceQuantity:
    """One resource dimension's amount (ADR-007 SS9: "Every quantity
    identifies dimension, unit and definition version, nonnegative
    magnitude ... amount kind").

    `unit` is opaque validated text, not a closed unit taxonomy, for the
    same reason `dimension` is opaque. `unit_version` reuses Kernel's
    generic `Version` (already reused generically for `contract_version`/
    `interpretation_version` in Gate-1 and for `PolicyRef` in Gate-2 M2),
    avoiding a redundant unit-definition-version type. `magnitude` is a
    `Decimal` to avoid float NaN/Infinity ambiguity; it must be finite and
    nonnegative. This value never means the amount is available, reserved,
    or actually consumed -- only `amount_kind` states which kind of fact it
    represents, and that fact still requires later owner commitment to
    become authoritative.
    """

    dimension: ResourceDimension
    unit: str = field(repr=False)
    unit_version: Version
    amount_kind: ResourceAmountKind
    magnitude: Decimal

    def __post_init__(self) -> None:
        if type(self.dimension) is not ResourceDimension:
            raise TypeError("resource quantity requires ResourceDimension")
        _validate(self.unit)
        if type(self.unit_version) is not Version:
            raise TypeError("resource quantity requires Version")
        if type(self.amount_kind) is not ResourceAmountKind:
            raise TypeError("resource quantity requires ResourceAmountKind")
        if type(self.magnitude) is not Decimal:
            raise TypeError("resource quantity magnitude must be Decimal")
        if self.magnitude.is_nan() or self.magnitude.is_infinite():
            raise ValueError("resource quantity magnitude must be finite")
        if self.magnitude < 0:
            raise ValueError("resource quantity magnitude must be nonnegative")


@dataclass(frozen=True, slots=True)
class ResourceClaimId:
    """Opaque ResourceClaim identity; construction reserves nothing."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


@dataclass(frozen=True, slots=True)
class ResourceClaim:
    """Immutable declared resource requirement or accounting fact for one
    operation, tenant and resource dimension (ADR-007 SS6.1 step 2:
    "Establish resource dimensions/units, known upper bounds ...";
    CONTRACTS `reserve_resource`: "Exact operation/effect, units/upper
    bound ... expected authority revision").

    One claim represents exactly one resource dimension (`quantity`), not a
    bundle: ADR-007 SS9.1's "Multi-dimension bound" scenario is a dispatch-
    time requirement that *every* mandatory dimension be covered by its own
    claim, not a reason to merge dimensions into one record -- doing so
    would let a later reader misread a merged CPU-plus-memory quantity as a
    single, silently aggregated amount.

    Constructing this value is never itself a grant, a successful
    reservation, a proof of available capacity, or an authorization
    decision (task SS6/SS16/SS17): it carries no `available`, `reserved`,
    `authorized` or `approved` field, and no `ResourcePort` exists yet to
    commit it as an owner fact.
    """

    claim_id: ResourceClaimId
    operation: OperationRef
    tenant_context: TenantContext
    quantity: ResourceQuantity

    def __post_init__(self) -> None:
        if type(self.claim_id) is not ResourceClaimId:
            raise TypeError("resource claim requires ResourceClaimId")
        if type(self.operation) is not OperationRef:
            raise TypeError("resource claim requires OperationRef")
        if type(self.tenant_context) is not TenantContext:
            raise TypeError("resource claim requires TenantContext")
        if type(self.quantity) is not ResourceQuantity:
            raise TypeError("resource claim requires ResourceQuantity")
        if self.operation.scope.tenant_id != self.tenant_context.tenant_id:
            raise ValueError("resource claim reference tenant mismatch")
