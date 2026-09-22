"""LegoAI v0.1: the minimal production in-memory Governance Port
realizations (`InMemoryGrantRegistry`, `InMemoryApprovalRegistry`,
`InMemoryPolicyRegistry`) -- required so a real application can compose
`DeterministicAuthorizationEvaluator` without depending on test-only fakes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from legoai.governance.ports import PolicyCurrencyStatus, RevocationStatus
from legoai.governance.values import (
    Approval,
    ApprovalId,
    Grant,
    GrantId,
    PolicyRef,
    Principal,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import ApplicationId, OperationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    OperationRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.reference.governance import (
    InMemoryApprovalRegistry,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
)

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _principal(name: str) -> Principal:
    return Principal(PrincipalRef("issuer", PrincipalId(name)))


def _operation() -> OperationRef:
    return OperationRef(
        ConfigurationRef(
            ApplicationRef(
                ReferenceScope("owner", TenantId("t")), ApplicationId("app")
            ),
            "config",
        ),
        OperationId("op"),
        "configuration",
    )


def _grant() -> Grant:
    return Grant(
        GrantId("g1"),
        _principal("issuer"),
        _principal("grantee"),
        TenantContext(TenantId("t")),
        "action",
        "scope",
        False,
        _EPOCH,
        None,
    )


def _approval() -> Approval:
    return Approval(
        ApprovalId("a1"),
        _operation(),
        TenantContext(TenantId("t")),
        _principal("grantee"),
        _principal("approver"),
        1,
        _EPOCH,
        _EPOCH + timedelta(hours=1),
    )


def test_grant_registry_defaults_active_and_can_be_revoked() -> None:
    registry = InMemoryGrantRegistry()
    grant = _grant()
    assert registry.current_revocation_status(grant) is RevocationStatus.ACTIVE
    registry.revoke(grant.grant_id)
    assert registry.current_revocation_status(grant) is RevocationStatus.REVOKED


def test_approval_registry_tracks_and_consumes_uses() -> None:
    registry = InMemoryApprovalRegistry()
    approval = _approval()
    state = registry.current_use_state(approval)
    assert state is not None
    assert state.uses_recorded == 0

    consumed = registry.consume(approval)
    assert consumed.uses_recorded == 1
    assert registry.current_use_state(approval).uses_recorded == 1  # type: ignore[union-attr]


def test_policy_registry_defaults_current_and_can_be_superseded() -> None:
    registry = InMemoryPolicyRegistry()
    policy_ref = PolicyRef("issuer", "policy", Version(1, 0, 0))
    assert registry.current_status(policy_ref) is PolicyCurrencyStatus.CURRENT
    registry.supersede(policy_ref)
    assert registry.current_status(policy_ref) is PolicyCurrencyStatus.SUPERSEDED
