"""Gate-2 M4: Governance Port protocols and their operation request/result
values -- a current-authority *evaluation seam*, never an authorization
engine, policy DSL, or dispatch mechanism.

Critical distinctions preserved throughout (ADR-005 SS3, SS12; ADR-007
SS12.1):

    identity != authentication != Principal != acting authority
    != Grant != Approval != Policy != current authorization decision
    != historical authorization evidence

`SecurityContext` is an immutable, point-in-time bundle of already-
established facts (who, which tenant, which operation/action, which
candidate Grant/Approval/PolicyRef) -- never itself an authorization
decision or proof of current validity. `AuthorizationDecision` is the
result of evaluating that bundle *at one instant*: "authorized now" is not
"authorized for dispatch later". ADR-007 SS6.2/SS12.1 still requires full
current-fact revalidation inside the exclusive dispatch gate, regardless of
any decision produced here.

Fail-closed discipline: an unresolvable current-state fact (unknown
revocation status, unknown approval-use state, unknown policy currency)
produces `AuthorizationOutcome.UNAVAILABLE`, never a fabricated `ALLOWED`.
`UNAVAILABLE` and `DENIED` are kept distinct so a genuine denial is never
confused with an infrastructure/dependency failure (CONTRACTS' Base error
table; SECURITY SEC-081).

This module deliberately does **not** import `legoai.execution.values`.
ADR-002's G-row allowed foreign targets (K, R, O) do not include E, and
`legoai.execution.values` (Gate-2 M1) does not import Governance either.
Mapping an Execution-held `SecurityContextRef` to the `SecurityContext`
defined here is therefore explicitly a later composition-layer concern
(only the "Application"/public-runtime-consumer plane, ADR-002 SS9.2, is
permitted to import both), not something this batch builds.

No Grant lookup, Approval consumption, policy rule evaluation, dispatch,
Plugin admission, or Resource allocation exists here. `Grant.max_uses`/
`Approval` values themselves are never mutated: `ApprovalUseState` is a
separate, owner-arbitrated current fact.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol

from legoai.governance.values import (
    Approval,
    ApprovalId,
    Grant,
    GrantId,
    PolicyRef,
    Principal,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.errors import ErrorCategory
from legoai.kernel.identity import _validate
from legoai.kernel.references import OperationRef


class RevocationStatus(Enum):
    """Current Grant revocation state -- a live fact, never part of the
    immutable `Grant` value itself (Gate-2 M2 deliberately omitted it)."""

    ACTIVE = "active"
    REVOKED = "revoked"
    UNKNOWN = "unknown"


class PolicyCurrencyStatus(Enum):
    """Whether an exact `PolicyRef` is still the current/active version for
    its `policy_id` -- not an evaluation of rule content."""

    CURRENT = "current"
    SUPERSEDED = "superseded"
    UNKNOWN = "unknown"


class AuthorizationOutcome(Enum):
    """A decision is never reduced to a bare bool: `UNAVAILABLE` is kept
    distinct from `DENIED` so infrastructure failure is never mistaken for,
    or converted into, a denial or an allow."""

    ALLOWED = "allowed"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ApprovalUseState:
    """Current recorded use count for one Approval (CONTRACTS
    `consume_approval`: "Approval becomes consumed only when all allowed
    uses exhausted"). This is owner-arbitrated live state, never a mutation
    of `Approval.max_uses`; M4 only reads it, never decrements it.
    """

    approval_id: ApprovalId
    uses_recorded: int

    def __post_init__(self) -> None:
        if type(self.approval_id) is not ApprovalId:
            raise TypeError("approval use state requires ApprovalId")
        if type(self.uses_recorded) is not int or isinstance(self.uses_recorded, bool):
            raise TypeError("approval use state uses_recorded must be an int")
        if self.uses_recorded < 0:
            raise ValueError("approval use state uses_recorded must be nonnegative")


@dataclass(frozen=True, slots=True)
class SecurityContext:
    """Immutable, point-in-time bundle of already-established authority
    facts for one candidate action (task SS15). Not an authorization
    decision, and its existence never means the referenced Grant is
    unrevoked, the Approval is unconsumed, or the Policy is current --
    `AuthorizationPort.evaluate` still checks all three against live state.

    `action`/`resource_scope` are opaque validated text, mirroring `Grant`'s
    own shape (ADR-005 SS9.1's explicit refusal to select a universal ACL
    syntax), so they can be compared exactly against a candidate `Grant`.
    """

    principal: Principal
    tenant_context: TenantContext
    operation: OperationRef
    action: str = field(repr=False)
    resource_scope: str = field(repr=False)
    grant: Grant | None
    approval: Approval | None
    policy_ref: PolicyRef
    established_at: datetime

    def __post_init__(self) -> None:
        if type(self.principal) is not Principal:
            raise TypeError("security context requires Principal")
        if type(self.tenant_context) is not TenantContext:
            raise TypeError("security context requires TenantContext")
        if type(self.operation) is not OperationRef:
            raise TypeError("security context requires OperationRef")
        _validate(self.action)
        _validate(self.resource_scope)
        if self.grant is not None and type(self.grant) is not Grant:
            raise TypeError("security context grant must be Grant or None")
        if self.approval is not None and type(self.approval) is not Approval:
            raise TypeError("security context approval must be Approval or None")
        if type(self.policy_ref) is not PolicyRef:
            raise TypeError("security context requires PolicyRef")
        if type(self.established_at) is not datetime:
            raise TypeError("security context established_at must be datetime")
        if self.established_at.tzinfo is None:
            raise ValueError("security context established_at must be timezone-aware")
        if self.operation.scope.tenant_id != self.tenant_context.tenant_id:
            raise ValueError("security context reference tenant mismatch")


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    """Immutable, point-in-time evaluation result. "authorized now" is not
    "authorized for dispatch later": ADR-007 SS12.1 requires current
    revalidation at the actual dispatch boundary regardless of this value.

    `category` is `None` only when `outcome` is `ALLOWED`; every `DENIED`
    or `UNAVAILABLE` outcome carries an existing Kernel `ErrorCategory`,
    never a free-form reason string (task SS36's information-leak concern).
    `considered_*` fields retain enough reference to know what was
    evaluated (task SS32) without retaining Policy rule content or
    Evidence-grade custody -- that remains M8.
    """

    outcome: AuthorizationOutcome
    operation: OperationRef
    evaluated_at: datetime
    category: ErrorCategory | None
    considered_grant: GrantId | None
    considered_approval: ApprovalId | None
    considered_policy: PolicyRef | None

    def __post_init__(self) -> None:
        if type(self.outcome) is not AuthorizationOutcome:
            raise TypeError("authorization decision requires AuthorizationOutcome")
        if type(self.operation) is not OperationRef:
            raise TypeError("authorization decision requires OperationRef")
        if type(self.evaluated_at) is not datetime:
            raise TypeError("authorization decision evaluated_at must be datetime")
        if self.evaluated_at.tzinfo is None:
            raise ValueError(
                "authorization decision evaluated_at must be timezone-aware"
            )
        if self.category is not None and type(self.category) is not ErrorCategory:
            raise TypeError(
                "authorization decision category must be ErrorCategory or None"
            )
        if self.outcome is AuthorizationOutcome.ALLOWED and self.category is not None:
            raise ValueError("allowed decision must not carry a category")
        if self.outcome is not AuthorizationOutcome.ALLOWED and self.category is None:
            raise ValueError("denied or unavailable decision requires a category")
        if (
            self.considered_grant is not None
            and type(self.considered_grant) is not GrantId
        ):
            raise TypeError("considered_grant must be GrantId or None")
        if (
            self.considered_approval is not None
            and type(self.considered_approval) is not ApprovalId
        ):
            raise TypeError("considered_approval must be ApprovalId or None")
        if (
            self.considered_policy is not None
            and type(self.considered_policy) is not PolicyRef
        ):
            raise TypeError("considered_policy must be PolicyRef or None")


class GrantStatePort(Protocol):
    """Current Grant revocation state -- an external owner fact, never
    derived from the immutable `Grant` value's own fields."""

    def current_revocation_status(self, grant: Grant) -> RevocationStatus: ...


class ApprovalUsePort(Protocol):
    """Current Approval use-count state. Returning `None` means the state
    is unknown -- callers must treat that as unavailable, never as zero
    uses."""

    def current_use_state(self, approval: Approval) -> ApprovalUseState | None: ...


class PolicyCurrencyPort(Protocol):
    """Whether an exact `PolicyRef` is still current for its `policy_id`."""

    def current_status(self, policy_ref: PolicyRef) -> PolicyCurrencyStatus: ...


class AuthorizationPort(Protocol):
    """The single external-facing current-authority evaluation seam.
    Answers "was this exact context authorized at this exact instant" --
    never "is this authorized forever", and never dispatches anything.
    """

    def evaluate(self, context: SecurityContext) -> AuthorizationDecision: ...
