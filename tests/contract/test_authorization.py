"""Gate-2 M4 contract suite for `AuthorizationPort` (ADR-005/ADR-007):
"authorized now" is a point-in-time fact, never proof of future dispatch
validity, and an unresolvable current-state fact must never become ALLOWED.

Parametrized over realization factories so a later alternative
`AuthorizationPort` implementation can be added to `REALIZATION_FACTORIES`
without duplicating these cases.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from legoai.governance.ports import (
    AuthorizationOutcome,
    AuthorizationPort,
    SecurityContext,
)
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
from legoai.kernel.identity import ApplicationId, OperationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    OperationRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.reference.governance import DeterministicAuthorizationEvaluator
from tests.support.governance import (
    InMemoryApprovalUseFake,
    InMemoryGrantStateFake,
    InMemoryPolicyCurrencyFake,
)

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _principal(name: str) -> Principal:
    return Principal(PrincipalRef("identity-owner", PrincipalId(name)))


def _operation(tenant: str, operation: str) -> OperationRef:
    return OperationRef(
        ConfigurationRef(
            ApplicationRef(
                ReferenceScope("composition", TenantId(tenant)), ApplicationId("app")
            ),
            "config",
        ),
        OperationId(operation),
        "configuration",
    )


def _grant(*, tenant: str = "tenant", grantee: Principal | None = None) -> Grant:
    return Grant(
        GrantId("grant-1"),
        _principal("issuer"),
        grantee if grantee is not None else _principal("grantee"),
        TenantContext(TenantId(tenant)),
        "publish-configuration",
        "app:config",
        False,
        _EPOCH,
        _EPOCH + timedelta(days=1),
    )


def _approval(
    *, tenant: str = "tenant", operation: str = "op", requester: Principal | None = None
) -> Approval:
    return Approval(
        ApprovalId("approval-1"),
        _operation(tenant, operation),
        TenantContext(TenantId(tenant)),
        requester if requester is not None else _principal("grantee"),
        _principal("approver"),
        1,
        _EPOCH,
        _EPOCH + timedelta(hours=1),
    )


def _policy_ref() -> PolicyRef:
    return PolicyRef("policy-owner", "retention-policy", Version(1, 0, 0))


class _Fakes:
    def __init__(self) -> None:
        self.grant_state = InMemoryGrantStateFake()
        self.approval_use = InMemoryApprovalUseFake()
        self.policy_currency = InMemoryPolicyCurrencyFake()


def _build_deterministic() -> tuple[AuthorizationPort, _Fakes]:
    fakes = _Fakes()
    evaluator: AuthorizationPort = DeterministicAuthorizationEvaluator(
        fakes.grant_state, fakes.approval_use, fakes.policy_currency
    )
    return evaluator, fakes


REALIZATION_FACTORIES: tuple[Callable[[], tuple[AuthorizationPort, _Fakes]], ...] = (
    _build_deterministic,
)


def _context(
    *,
    tenant: str = "tenant",
    operation: str = "op",
    principal: Principal | None = None,
    grant: Grant | None | object = "default",
    approval: Approval | None = None,
    policy_ref: PolicyRef | None = None,
    established_at: datetime = _EPOCH + timedelta(minutes=30),
) -> SecurityContext:
    actual_principal = principal if principal is not None else _principal("grantee")
    actual_grant = (
        _grant(tenant=tenant, grantee=actual_principal) if grant == "default" else grant
    )
    return SecurityContext(
        actual_principal,
        TenantContext(TenantId(tenant)),
        _operation(tenant, operation),
        "publish-configuration",
        "app:config",
        actual_grant,  # type: ignore[arg-type]
        approval,
        policy_ref if policy_ref is not None else _policy_ref(),
        established_at,
    )


@pytest.mark.parametrize("factory", REALIZATION_FACTORIES)
class TestAuthorizationContract:
    def test_allowed_when_grant_covers_and_state_current(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, _ = factory()
        decision = port.evaluate(_context())
        assert decision.outcome is AuthorizationOutcome.ALLOWED
        assert decision.category is None
        assert decision.considered_grant == GrantId("grant-1")

    def test_denied_when_no_grant_supplied(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, _ = factory()
        decision = port.evaluate(_context(grant=None))
        assert decision.outcome is AuthorizationOutcome.DENIED
        assert decision.category is ErrorCategory.AUTHORIZATION_DENIED
        assert decision.considered_grant is None

    def test_denied_when_grantee_does_not_match_principal(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, _ = factory()
        other_grant = _grant(grantee=_principal("someone-else"))
        decision = port.evaluate(_context(grant=other_grant))
        assert decision.outcome is AuthorizationOutcome.DENIED
        assert decision.category is ErrorCategory.AUTHORIZATION_DENIED

    def test_denied_when_action_or_resource_scope_mismatched(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, _ = factory()
        grant = replace(_grant(), action="delete-configuration")
        decision = port.evaluate(_context(grant=grant))
        assert decision.outcome is AuthorizationOutcome.DENIED
        assert decision.category is ErrorCategory.AUTHORIZATION_DENIED

    def test_cross_tenant_grant_does_not_authorize(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, _ = factory()
        grant = _grant(tenant="other-tenant")
        decision = port.evaluate(_context(grant=grant))
        assert decision.outcome is AuthorizationOutcome.DENIED
        assert decision.category is ErrorCategory.AUTHORIZATION_DENIED

    @pytest.mark.parametrize(
        ("offset", "expect_allowed"),
        [
            (timedelta(seconds=-1), False),  # before valid_from
            (timedelta(0), True),  # exactly valid_from (inclusive)
            (timedelta(hours=23, minutes=59, seconds=59), True),  # just before expiry
            (timedelta(days=1), False),  # exactly expires_at (exclusive)
            (timedelta(days=1, seconds=1), False),  # after expires_at
        ],
    )
    def test_grant_time_interval_boundaries(
        self,
        factory: Callable[[], tuple[AuthorizationPort, _Fakes]],
        offset: timedelta,
        expect_allowed: bool,
    ) -> None:
        port, _ = factory()
        decision = port.evaluate(_context(established_at=_EPOCH + offset))
        if expect_allowed:
            assert decision.outcome is AuthorizationOutcome.ALLOWED
        else:
            assert decision.outcome is AuthorizationOutcome.DENIED
            assert decision.category is ErrorCategory.AUTHORIZATION_DENIED

    def test_revoked_grant_denies(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        fakes.grant_state.revoke(GrantId("grant-1"))
        decision = port.evaluate(_context())
        assert decision.outcome is AuthorizationOutcome.DENIED
        assert decision.category is ErrorCategory.AUTHORIZATION_DENIED

    def test_unknown_revocation_state_fails_closed_unavailable(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        fakes.grant_state.mark_unknown(GrantId("grant-1"))
        decision = port.evaluate(_context())
        assert decision.outcome is AuthorizationOutcome.UNAVAILABLE
        assert decision.category is ErrorCategory.DEPENDENCY_FAILURE

    def test_superseded_policy_denies(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        fakes.policy_currency.supersede(_policy_ref())
        decision = port.evaluate(_context())
        assert decision.outcome is AuthorizationOutcome.DENIED
        assert decision.category is ErrorCategory.POLICY_VIOLATION

    def test_unknown_policy_currency_fails_closed_unavailable(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        fakes.policy_currency.mark_unknown(_policy_ref())
        decision = port.evaluate(_context())
        assert decision.outcome is AuthorizationOutcome.UNAVAILABLE
        assert decision.category is ErrorCategory.DEPENDENCY_FAILURE

    def test_different_policy_version_not_silently_substituted(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        fakes.policy_currency.supersede(_policy_ref())
        newer = replace(_policy_ref(), version=Version(2, 0, 0))
        decision = port.evaluate(_context(policy_ref=newer))
        assert decision.outcome is AuthorizationOutcome.ALLOWED

    def test_evaluate_rejects_non_security_context(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, _ = factory()
        with pytest.raises(TypeError, match="requires SecurityContext"):
            port.evaluate(object())  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("offset", "expect_allowed"),
        [
            (timedelta(seconds=-1), False),  # before approval valid_from
            (timedelta(0), True),  # exactly valid_from (inclusive)
            (timedelta(minutes=59, seconds=59), True),  # just before expiry
            (timedelta(hours=1), False),  # exactly expires_at (exclusive)
            (timedelta(hours=1, seconds=1), False),  # after expires_at
        ],
    )
    def test_approval_time_interval_boundaries(
        self,
        factory: Callable[[], tuple[AuthorizationPort, _Fakes]],
        offset: timedelta,
        expect_allowed: bool,
    ) -> None:
        port, fakes = factory()
        approval = _approval()
        fakes.approval_use.set_uses(ApprovalId("approval-1"), 0)
        # Grant window is deliberately wider than the approval window and
        # starts earlier, so only the approval boundary is under test.
        wide_grant = replace(
            _grant(), valid_from=_EPOCH - timedelta(days=1), expires_at=None
        )
        decision = port.evaluate(
            _context(
                grant=wide_grant, approval=approval, established_at=_EPOCH + offset
            )
        )
        if expect_allowed:
            assert decision.outcome is AuthorizationOutcome.ALLOWED
        else:
            assert decision.outcome is AuthorizationOutcome.DENIED
            assert decision.category is ErrorCategory.AUTHORIZATION_DENIED

    def test_allowed_with_valid_approval(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        approval = _approval()
        fakes.approval_use.set_uses(ApprovalId("approval-1"), 0)
        decision = port.evaluate(_context(approval=approval))
        assert decision.outcome is AuthorizationOutcome.ALLOWED
        assert decision.considered_approval == ApprovalId("approval-1")

    def test_approval_bound_to_different_operation_does_not_authorize(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        approval = _approval(operation="a-different-op")
        fakes.approval_use.set_uses(ApprovalId("approval-1"), 0)
        decision = port.evaluate(_context(approval=approval))
        assert decision.outcome is AuthorizationOutcome.DENIED
        assert decision.category is ErrorCategory.AUTHORIZATION_DENIED

    def test_approval_bound_to_different_tenant_does_not_authorize(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        approval = _approval(tenant="other-tenant")
        fakes.approval_use.set_uses(ApprovalId("approval-1"), 0)
        decision = port.evaluate(_context(approval=approval))
        assert decision.outcome is AuthorizationOutcome.DENIED
        assert decision.category is ErrorCategory.AUTHORIZATION_DENIED

    def test_approval_bound_to_different_requester_does_not_authorize(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        approval = _approval(requester=_principal("someone-else"))
        fakes.approval_use.set_uses(ApprovalId("approval-1"), 0)
        decision = port.evaluate(_context(approval=approval))
        assert decision.outcome is AuthorizationOutcome.DENIED
        assert decision.category is ErrorCategory.AUTHORIZATION_DENIED

    def test_approval_uses_exhausted_denies(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        approval = _approval()
        fakes.approval_use.set_uses(ApprovalId("approval-1"), 1)  # == max_uses
        decision = port.evaluate(_context(approval=approval))
        assert decision.outcome is AuthorizationOutcome.DENIED
        assert decision.category is ErrorCategory.AUTHORIZATION_DENIED

    def test_approval_use_state_over_max_also_denies(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        approval = _approval()
        fakes.approval_use.set_uses(ApprovalId("approval-1"), 5)
        decision = port.evaluate(_context(approval=approval))
        assert decision.outcome is AuthorizationOutcome.DENIED

    def test_unknown_approval_use_state_fails_closed_unavailable(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, _ = factory()
        approval = _approval()
        decision = port.evaluate(_context(approval=approval))
        assert decision.outcome is AuthorizationOutcome.UNAVAILABLE
        assert decision.category is ErrorCategory.DEPENDENCY_FAILURE

    def test_approval_does_not_mutate_max_uses(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        approval = _approval()
        fakes.approval_use.set_uses(ApprovalId("approval-1"), 0)
        port.evaluate(_context(approval=approval))
        assert approval.max_uses == 1

    def test_decision_is_immutable_point_in_time_snapshot(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        first = port.evaluate(_context())
        fakes.grant_state.revoke(GrantId("grant-1"))
        assert first.outcome is AuthorizationOutcome.ALLOWED
        second = port.evaluate(_context())
        assert second.outcome is AuthorizationOutcome.DENIED

    def test_repeated_evaluation_is_deterministic(
        self, factory: Callable[[], tuple[AuthorizationPort, _Fakes]]
    ) -> None:
        port, fakes = factory()
        fakes.approval_use.set_uses(ApprovalId("approval-1"), 0)
        approval = _approval()
        first = port.evaluate(_context(approval=approval))
        second = port.evaluate(_context(approval=approval))
        assert first == second
