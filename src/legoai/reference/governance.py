"""Gate-2 M4: deterministic reference realization of `AuthorizationPort`.

`DeterministicAuthorizationEvaluator` performs only the checks a
`SecurityContext`'s own already-typed facts make possible: exact grantee/
tenant/action/resource-scope/time-interval matching against the supplied
candidate `Grant`, exact operation/tenant/requester/time-interval matching
against the supplied candidate `Approval`, and current-state confirmation
through the three supporting Ports (`GrantStatePort`, `ApprovalUsePort`,
`PolicyCurrencyPort`). It contains no Grant/Approval/Policy *lookup*: the
caller supplies the exact candidate values already found elsewhere.

Fail-closed throughout: an unknown revocation/use/policy-currency state
never becomes `ALLOWED`, and no permissive fallback exists for a missing
Grant, missing/mismatched Approval binding, or unavailable dependency.
This is one instant's evaluation only -- ADR-007 SS12.1 still requires
current revalidation at the actual dispatch boundary.
"""

from contextlib import nullcontext
from dataclasses import dataclass

from legoai.governance.ports import (
    ApprovalUsePort,
    ApprovalUseState,
    AuthorizationDecision,
    AuthorizationOutcome,
    GrantStatePort,
    PolicyCurrencyPort,
    PolicyCurrencyStatus,
    RevocationStatus,
    SecurityContext,
)
from legoai.governance.values import Approval, ApprovalId, Grant, GrantId, PolicyRef
from legoai.kernel.errors import ErrorCategory
from legoai.reference._secret_domain import _OrderingDomain


def _denied(context: SecurityContext, category: ErrorCategory) -> AuthorizationDecision:
    return AuthorizationDecision(
        AuthorizationOutcome.DENIED,
        context.operation,
        context.established_at,
        category,
        context.grant.grant_id if context.grant is not None else None,
        context.approval.approval_id if context.approval is not None else None,
        context.policy_ref,
    )


def _unavailable(
    context: SecurityContext, category: ErrorCategory
) -> AuthorizationDecision:
    return AuthorizationDecision(
        AuthorizationOutcome.UNAVAILABLE,
        context.operation,
        context.established_at,
        category,
        context.grant.grant_id if context.grant is not None else None,
        context.approval.approval_id if context.approval is not None else None,
        context.policy_ref,
    )


def _grant_covers(context: SecurityContext, grant: Grant) -> bool:
    if grant.grantee != context.principal:
        return False
    if grant.tenant_context != context.tenant_context:
        return False
    if grant.action != context.action or grant.resource_scope != context.resource_scope:
        return False
    if context.established_at < grant.valid_from:
        return False
    if grant.expires_at is not None and context.established_at >= grant.expires_at:
        return False
    return True


def _approval_covers(context: SecurityContext, approval: Approval) -> bool:
    # No separate tenant_context comparison: Approval.__post_init__ and
    # SecurityContext.__post_init__ both already enforce
    # operation.scope.tenant_id == tenant_context.tenant_id, so an exact
    # operation match above already implies exact tenant_context equality.
    if approval.operation != context.operation:
        return False
    if approval.requester != context.principal:
        return False
    if context.established_at < approval.valid_from:
        return False
    if context.established_at >= approval.expires_at:
        return False
    return True


@dataclass(frozen=True, slots=True)
class DeterministicAuthorizationEvaluator:
    """Reference `AuthorizationPort` realization composed from three
    already-established supporting Ports. Deterministic and side-effect
    free: the only inputs are `evaluate`'s `context` argument and the
    injected Ports' own current-state answers.
    """

    grant_state: GrantStatePort
    approval_use: ApprovalUsePort
    policy_currency: PolicyCurrencyPort

    def evaluate(self, context: SecurityContext) -> AuthorizationDecision:
        if type(context) is not SecurityContext:
            raise TypeError("evaluate requires SecurityContext")

        if context.grant is None:
            return _denied(context, ErrorCategory.AUTHORIZATION_DENIED)
        if not _grant_covers(context, context.grant):
            return _denied(context, ErrorCategory.AUTHORIZATION_DENIED)

        revocation = self.grant_state.current_revocation_status(context.grant)
        if revocation is RevocationStatus.REVOKED:
            return _denied(context, ErrorCategory.AUTHORIZATION_DENIED)
        if revocation is RevocationStatus.UNKNOWN:
            return _unavailable(context, ErrorCategory.DEPENDENCY_FAILURE)

        currency = self.policy_currency.current_status(context.policy_ref)
        if currency is PolicyCurrencyStatus.SUPERSEDED:
            return _denied(context, ErrorCategory.POLICY_VIOLATION)
        if currency is PolicyCurrencyStatus.UNKNOWN:
            return _unavailable(context, ErrorCategory.DEPENDENCY_FAILURE)

        if context.approval is not None:
            if not _approval_covers(context, context.approval):
                return _denied(context, ErrorCategory.AUTHORIZATION_DENIED)
            use_state = self.approval_use.current_use_state(context.approval)
            if use_state is None:
                return _unavailable(context, ErrorCategory.DEPENDENCY_FAILURE)
            if use_state.uses_recorded >= context.approval.max_uses:
                return _denied(context, ErrorCategory.AUTHORIZATION_DENIED)

        return AuthorizationDecision(
            AuthorizationOutcome.ALLOWED,
            context.operation,
            context.established_at,
            None,
            context.grant.grant_id,
            context.approval.approval_id if context.approval is not None else None,
            context.policy_ref,
        )


class InMemoryGrantRegistry:
    """LegoAI v0.1: the minimal production `GrantStatePort` realization no
    prior Gate-2 batch shipped -- only test fakes existed
    (`tests/support/governance.py`), which are not part of the installed
    package and therefore unusable by a real application. Any application
    composing the governed runtime needs *some* realization of this Port;
    this one is generic Core infrastructure (task's own "reuse before
    invention" principle), not DocuMind-specific, and is added here rather
    than duplicated inside the DocuMind application.

    Process-lifetime only: revocations recorded here do not survive
    restart. This mirrors `InMemoryCatalog`/`InMemoryEvidenceCustody`'s own
    already-accepted scope exactly -- no new persistence claim is made.
    """

    def __init__(self, *, _domain: _OrderingDomain | None = None) -> None:
        if _domain is not None and type(_domain) is not _OrderingDomain:
            raise TypeError("qualified ordering domain required")
        self._domain = _domain
        self._revoked: set[GrantId] = set()

    def revoke(self, grant_id: GrantId) -> None:
        with self._domain.enter() if self._domain else nullcontext():
            self._revoked.add(grant_id)

    def current_revocation_status(self, grant: Grant) -> RevocationStatus:
        if grant.grant_id in self._revoked:
            return RevocationStatus.REVOKED
        return RevocationStatus.ACTIVE


class InMemoryApprovalRegistry:
    """LegoAI v0.1: the minimal production realization of both
    `ApprovalUsePort` (read) and `ApprovalConsumptionPort` (commit) --
    process-lifetime in-memory use counts, mirroring
    `InMemoryGrantRegistry`'s own scope exactly. `consume` trusts the
    caller (the dispatch arbiter, under its own exclusive gate) to have
    already checked eligibility, per `ApprovalConsumptionPort`'s own
    documented contract.

    With an explicitly injected Stage-A domain, every consumption participates
    and exhaustion refuses. The private already-held operation checks domain
    ownership; credential-free no-argument construction keeps its old contract.
    """

    def __init__(self, *, _domain: _OrderingDomain | None = None) -> None:
        if _domain is not None and type(_domain) is not _OrderingDomain:
            raise TypeError("qualified ordering domain required")
        self._domain = _domain
        self._uses: dict[ApprovalId, int] = {}

    def current_use_state(self, approval: Approval) -> ApprovalUseState | None:
        return ApprovalUseState(
            approval.approval_id, self._uses.get(approval.approval_id, 0)
        )

    def consume(self, approval: Approval) -> ApprovalUseState:
        with self._domain.enter() if self._domain else nullcontext():
            return self._consume(approval)

    def _consume(self, approval: Approval) -> ApprovalUseState:
        if self._domain is not None:
            self._domain.held()
        current = self._uses.get(approval.approval_id, 0)
        if self._domain is not None and current >= approval.max_uses:
            raise PermissionError("Approval exhausted")
        self._uses[approval.approval_id] = current + 1
        return ApprovalUseState(approval.approval_id, current + 1)


class InMemoryPolicyRegistry:
    """LegoAI v0.1: the minimal production `PolicyCurrencyPort`
    realization. Every `PolicyRef` not explicitly marked superseded is
    reported current -- an intentionally permissive default appropriate for
    a single-operator local example, never claimed as a substitute for a
    real Policy Decision realization."""

    def __init__(self, *, _domain: _OrderingDomain | None = None) -> None:
        if _domain is not None and type(_domain) is not _OrderingDomain:
            raise TypeError("qualified ordering domain required")
        self._domain = _domain
        self._superseded: set[PolicyRef] = set()

    def supersede(self, policy_ref: PolicyRef) -> None:
        with self._domain.enter() if self._domain else nullcontext():
            self._superseded.add(policy_ref)

    def current_status(self, policy_ref: PolicyRef) -> PolicyCurrencyStatus:
        if policy_ref in self._superseded:
            return PolicyCurrencyStatus.SUPERSEDED
        return PolicyCurrencyStatus.CURRENT
