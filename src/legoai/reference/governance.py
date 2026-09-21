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

from dataclasses import dataclass

from legoai.governance.ports import (
    ApprovalUsePort,
    AuthorizationDecision,
    AuthorizationOutcome,
    GrantStatePort,
    PolicyCurrencyPort,
    PolicyCurrencyStatus,
    RevocationStatus,
    SecurityContext,
)
from legoai.governance.values import Approval, Grant
from legoai.kernel.errors import ErrorCategory


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
