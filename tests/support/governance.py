"""Deterministic in-memory Gate-2 M4 Port fakes for tests only.

These are not production reference realizations: no persistence, no
network, no external identity/policy provider. They exist solely to give
`DeterministicAuthorizationEvaluator` (and its own contract tests)
explicit, controllable current-state answers for revocation, approval-use
and policy-currency.
"""

from __future__ import annotations

from legoai.governance.ports import (
    ApprovalUseState,
    PolicyCurrencyStatus,
    RevocationStatus,
)
from legoai.governance.values import Approval, ApprovalId, Grant, GrantId, PolicyRef


class InMemoryGrantStateFake:
    """Explicit revoked/unknown sets; anything else answers ACTIVE."""

    def __init__(self) -> None:
        self._revoked: set[GrantId] = set()
        self._unknown: set[GrantId] = set()

    def revoke(self, grant_id: GrantId) -> None:
        self._revoked.add(grant_id)

    def mark_unknown(self, grant_id: GrantId) -> None:
        self._unknown.add(grant_id)

    def current_revocation_status(self, grant: Grant) -> RevocationStatus:
        if grant.grant_id in self._unknown:
            return RevocationStatus.UNKNOWN
        if grant.grant_id in self._revoked:
            return RevocationStatus.REVOKED
        return RevocationStatus.ACTIVE


class InMemoryApprovalUseFake:
    """Explicit recorded-use counts; missing entries answer unknown (`None`)."""

    def __init__(self) -> None:
        self._uses: dict[ApprovalId, int] = {}

    def set_uses(self, approval_id: ApprovalId, uses: int) -> None:
        self._uses[approval_id] = uses

    def current_use_state(self, approval: Approval) -> ApprovalUseState | None:
        if approval.approval_id not in self._uses:
            return None
        return ApprovalUseState(approval.approval_id, self._uses[approval.approval_id])


class InMemoryPolicyCurrencyFake:
    """Explicit superseded/unknown sets, keyed by the exact `PolicyRef`
    (including version); anything else answers CURRENT."""

    def __init__(self) -> None:
        self._superseded: set[PolicyRef] = set()
        self._unknown: set[PolicyRef] = set()

    def supersede(self, policy_ref: PolicyRef) -> None:
        self._superseded.add(policy_ref)

    def mark_unknown(self, policy_ref: PolicyRef) -> None:
        self._unknown.add(policy_ref)

    def current_status(self, policy_ref: PolicyRef) -> PolicyCurrencyStatus:
        if policy_ref in self._unknown:
            return PolicyCurrencyStatus.UNKNOWN
        if policy_ref in self._superseded:
            return PolicyCurrencyStatus.SUPERSEDED
        return PolicyCurrencyStatus.CURRENT
