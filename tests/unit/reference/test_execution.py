"""Gate-2 M9: ADR-007 SS6.2 -- the exclusive dispatch gate revalidates
current authorization, current Approval-use state and current Catalog
publication *at gate evaluation time*, never reusing a historical decision.
"prepared earlier" is never "still valid now".
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest

from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.evidence.ports import EvidenceId, EvidenceRecord
from legoai.execution.ports import DispatchOutcome, DispatchRequest
from legoai.governance.ports import RevocationStatus, SecurityContext
from legoai.governance.values import (
    Approval as ApprovalValue,
)
from legoai.governance.values import (
    ApprovalId as ApprovalIdValue,
)
from legoai.governance.values import Grant, GrantId, PolicyRef, Principal
from legoai.kernel.context import TenantContext
from legoai.kernel.errors import ErrorCategory
from legoai.kernel.identity import (
    ApplicationId,
    OperationId,
    PrincipalId,
    TenantId,
)
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.plugins.ports import PluginAdmissionId
from legoai.plugins.values import PluginDeclaration, PluginId
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.evidence import InMemoryEvidenceCustody
from legoai.reference.execution import DeterministicDispatchArbiter
from legoai.reference.governance import DeterministicAuthorizationEvaluator
from legoai.reference.plugins import activate, admit, initialize, inspect, validate
from tests.support.governance import (
    InMemoryApprovalUseFake,
    InMemoryGrantStateFake,
    InMemoryPolicyCurrencyFake,
)

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)
CAPABILITY = CapabilityId("text.normalize")


def _principal(name: str) -> Principal:
    return Principal(PrincipalRef("identity-owner", PrincipalId(name)))


def _operation(tenant: str = "tenant") -> OperationRef:
    return OperationRef(
        ConfigurationRef(
            ApplicationRef(
                ReferenceScope("composition", TenantId(tenant)), ApplicationId("app")
            ),
            "config",
        ),
        OperationId("op"),
        "configuration",
    )


def _policy_ref() -> PolicyRef:
    return PolicyRef("policy-owner", "policy", Version(1, 0, 0))


def _grant(*, tenant: str = "tenant", grantee: Principal) -> Grant:
    return Grant(
        GrantId("grant-1"),
        _principal("issuer"),
        grantee,
        TenantContext(TenantId(tenant)),
        "invoke-capability",
        "text.normalize",
        False,
        _EPOCH,
        _EPOCH + timedelta(days=1),
    )


class _Environment:
    """Wires one arbiter with its own governance/catalog/evidence fakes and
    publishes one ACTIVE fixture Plugin's offer, ready to be resolved and
    dispatched against."""

    def __init__(self, *, tenant: str = "tenant") -> None:
        self.tenant = tenant
        self.grantee = _principal("service")
        self.grant_state = InMemoryGrantStateFake()
        self.approval_use = InMemoryApprovalUseFake()
        self.policy_currency = InMemoryPolicyCurrencyFake()
        self.authorization = DeterministicAuthorizationEvaluator(
            self.grant_state, self.approval_use, self.policy_currency
        )
        self.catalog = InMemoryCatalog()
        self.evidence = InMemoryEvidenceCustody()
        self.arbiter = DeterministicDispatchArbiter(
            self.authorization, self.catalog, self.evidence, self.approval_use
        )
        declaration = PluginDeclaration(
            PluginId("legoai", "fixture"),
            Version(0, 1, 0),
            (CapabilityOffer(CAPABILITY, Version(1, 0, 0)),),
            (),
        )
        discovered = inspect(declaration)
        validation = validate(discovered, declaration, evaluated_at=_EPOCH)
        record = admit(
            validation,
            TenantContext(TenantId(tenant)),
            PluginAdmissionId("admission-1"),
            established_at=_EPOCH,
        )
        # Directly promote to ACTIVE for this test fixture (M5 transitions
        # are exercised elsewhere; only the end state matters here).
        active_record = activate(
            initialize(record, established_at=_EPOCH), established_at=_EPOCH
        )
        self.entry = self.catalog.publish(
            active_record, declaration, declaration.offers[0], established_at=_EPOCH
        )

    def security_context(
        self, *, grant: Grant | None, approval: ApprovalValue | None = None
    ) -> SecurityContext:
        return SecurityContext(
            self.grantee,
            TenantContext(TenantId(self.tenant)),
            _operation(self.tenant),
            "invoke-capability",
            "text.normalize",
            grant,
            approval,
            _policy_ref(),
            _EPOCH + timedelta(minutes=30),
        )

    def request(
        self, *, grant: Grant | None, approval: ApprovalValue | None = None
    ) -> DispatchRequest:
        return DispatchRequest(
            self.security_context(grant=grant, approval=approval), self.entry
        )


# --- happy path ------------------------------------------------------------------


def test_permitted_when_all_predicates_hold() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    decision = env.arbiter.arbitrate(env.request(grant=grant), evaluated_at=_EPOCH)
    assert decision.outcome is DispatchOutcome.PERMITTED
    assert decision.permit is not None
    assert decision.permit.resolved_entry == env.entry


def test_permit_carries_current_catalog_revision() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    decision = env.arbiter.arbitrate(env.request(grant=grant), evaluated_at=_EPOCH)
    assert decision.permit is not None
    snapshot = env.catalog.snapshot(TenantContext(TenantId(env.tenant)))
    assert decision.permit.catalog_revision == snapshot.revision


# --- current-authority revalidation (never a cached decision) ------------------


def test_denied_when_no_grant_supplied() -> None:
    env = _Environment()
    decision = env.arbiter.arbitrate(env.request(grant=None), evaluated_at=_EPOCH)
    assert decision.outcome is DispatchOutcome.DENIED
    assert decision.category is ErrorCategory.AUTHORIZATION_DENIED


def test_grant_revoked_before_gate_denies_even_though_prepared_when_active() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    # "Prepared" while the Grant was active; then revoked before the gate runs.
    request = env.request(grant=grant)
    env.grant_state.revoke(GrantId("grant-1"))
    decision = env.arbiter.arbitrate(request, evaluated_at=_EPOCH)
    assert decision.outcome is DispatchOutcome.DENIED
    assert decision.category is ErrorCategory.AUTHORIZATION_DENIED


def test_unknown_revocation_state_fails_closed_unavailable() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    env.grant_state.mark_unknown(GrantId("grant-1"))
    decision = env.arbiter.arbitrate(env.request(grant=grant), evaluated_at=_EPOCH)
    assert decision.outcome is DispatchOutcome.UNAVAILABLE
    assert decision.category is ErrorCategory.DEPENDENCY_FAILURE


# --- Catalog/resolution staleness -----------------------------------------------


def test_withdrawn_entry_is_stale_not_silently_permitted() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    request = env.request(grant=grant)
    env.catalog.withdraw(
        env.entry.plugin_id,
        env.entry.release,
        env.entry.offer,
        TenantContext(TenantId(env.tenant)),
    )
    decision = env.arbiter.arbitrate(request, evaluated_at=_EPOCH)
    assert decision.outcome is DispatchOutcome.STALE
    assert decision.category is ErrorCategory.CONFLICT


def test_catalog_revision_advancing_without_withdrawal_still_permits() -> None:
    # A revision bump from an unrelated publish must not itself invalidate
    # a still-published candidate: currentness means "still published", not
    # "identical revision number".
    env = _Environment()
    other_declaration = PluginDeclaration(
        PluginId("legoai", "other"),
        Version(0, 1, 0),
        (CapabilityOffer(CapabilityId("other.capability"), Version(1, 0, 0)),),
        (),
    )
    other_discovered = inspect(other_declaration)
    other_validation = validate(
        other_discovered, other_declaration, evaluated_at=_EPOCH
    )
    other_record = admit(
        other_validation,
        TenantContext(TenantId(env.tenant)),
        PluginAdmissionId("admission-2"),
        established_at=_EPOCH,
    )
    other_active = activate(
        initialize(other_record, established_at=_EPOCH), established_at=_EPOCH
    )
    env.catalog.publish(
        other_active,
        other_declaration,
        other_declaration.offers[0],
        established_at=_EPOCH,
    )
    grant = _grant(grantee=env.grantee)
    decision = env.arbiter.arbitrate(env.request(grant=grant), evaluated_at=_EPOCH)
    assert decision.outcome is DispatchOutcome.PERMITTED


# --- evidence presence -----------------------------------------------------------


def test_missing_required_evidence_fails_closed_unavailable() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    request = DispatchRequest(
        env.security_context(grant=grant), env.entry, (EvidenceId("never-recorded"),)
    )
    decision = env.arbiter.arbitrate(request, evaluated_at=_EPOCH)
    assert decision.outcome is DispatchOutcome.UNAVAILABLE
    assert decision.category is ErrorCategory.DEPENDENCY_FAILURE


def test_present_required_evidence_permits() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    subject = ConfigurationRevisionRef(
        ConfigurationRef(
            ApplicationRef(
                ReferenceScope("composition", TenantId(env.tenant)),
                ApplicationId("app"),
            ),
            "config",
        ),
        "r1",
        Version(0, 1, 0),
    )
    record = EvidenceRecord(
        EvidenceId("ev1"),
        subject,
        _principal("issuer"),
        TenantContext(TenantId(env.tenant)),
        "source submitted",
        _EPOCH,
    )
    env.evidence.record(record)
    request = DispatchRequest(
        env.security_context(grant=grant), env.entry, (EvidenceId("ev1"),)
    )
    decision = env.arbiter.arbitrate(request, evaluated_at=_EPOCH)
    assert decision.outcome is DispatchOutcome.PERMITTED


# --- Approval revalidation/consumption ------------------------------------------


def test_approval_exhausted_denies() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    approval = ApprovalValue(
        ApprovalIdValue("approval-1"),
        _operation(env.tenant),
        TenantContext(TenantId(env.tenant)),
        env.grantee,
        _principal("approver"),
        1,
        _EPOCH,
        _EPOCH + timedelta(hours=1),
    )
    env.approval_use.set_uses(ApprovalIdValue("approval-1"), 1)
    decision = env.arbiter.arbitrate(
        env.request(grant=grant, approval=approval), evaluated_at=_EPOCH
    )
    assert decision.outcome is DispatchOutcome.DENIED


def test_approval_consumed_on_permit_and_second_use_then_denied() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    approval = ApprovalValue(
        ApprovalIdValue("approval-1"),
        _operation(env.tenant),
        TenantContext(TenantId(env.tenant)),
        env.grantee,
        _principal("approver"),
        1,
        _EPOCH,
        _EPOCH + timedelta(hours=1),
    )
    env.approval_use.set_uses(ApprovalIdValue("approval-1"), 0)
    first = env.arbiter.arbitrate(
        env.request(grant=grant, approval=approval), evaluated_at=_EPOCH
    )
    assert first.outcome is DispatchOutcome.PERMITTED
    second = env.arbiter.arbitrate(
        env.request(grant=grant, approval=approval), evaluated_at=_EPOCH
    )
    assert second.outcome is DispatchOutcome.DENIED


def test_approval_does_not_mutate_immutable_max_uses() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    approval = ApprovalValue(
        ApprovalIdValue("approval-1"),
        _operation(env.tenant),
        TenantContext(TenantId(env.tenant)),
        env.grantee,
        _principal("approver"),
        1,
        _EPOCH,
        _EPOCH + timedelta(hours=1),
    )
    env.approval_use.set_uses(ApprovalIdValue("approval-1"), 0)
    env.arbiter.arbitrate(
        env.request(grant=grant, approval=approval), evaluated_at=_EPOCH
    )
    assert approval.max_uses == 1


# --- race tests: no TOCTOU gap ---------------------------------------------------


def test_concurrent_last_use_race_at_most_one_permitted() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    approval = ApprovalValue(
        ApprovalIdValue("approval-1"),
        _operation(env.tenant),
        TenantContext(TenantId(env.tenant)),
        env.grantee,
        _principal("approver"),
        1,
        _EPOCH,
        _EPOCH + timedelta(hours=1),
    )
    env.approval_use.set_uses(ApprovalIdValue("approval-1"), 0)
    barrier = threading.Barrier(2)
    outcomes: list[DispatchOutcome] = []
    lock = threading.Lock()

    def attempt() -> None:
        barrier.wait(timeout=5)
        decision = env.arbiter.arbitrate(
            env.request(grant=grant, approval=approval), evaluated_at=_EPOCH
        )
        with lock:
            outcomes.append(decision.outcome)

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert len(outcomes) == 2
    assert outcomes.count(DispatchOutcome.PERMITTED) == 1
    assert outcomes.count(DispatchOutcome.DENIED) == 1


def test_concurrent_requests_no_double_consumption_across_many_threads() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    approval = ApprovalValue(
        ApprovalIdValue("approval-1"),
        _operation(env.tenant),
        TenantContext(TenantId(env.tenant)),
        env.grantee,
        _principal("approver"),
        3,
        _EPOCH,
        _EPOCH + timedelta(hours=1),
    )
    env.approval_use.set_uses(ApprovalIdValue("approval-1"), 0)
    thread_count = 10
    barrier = threading.Barrier(thread_count)
    outcomes: list[DispatchOutcome] = []
    lock = threading.Lock()

    def attempt() -> None:
        barrier.wait(timeout=5)
        decision = env.arbiter.arbitrate(
            env.request(grant=grant, approval=approval), evaluated_at=_EPOCH
        )
        with lock:
            outcomes.append(decision.outcome)

    threads = [threading.Thread(target=attempt) for _ in range(thread_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert len(outcomes) == thread_count
    assert outcomes.count(DispatchOutcome.PERMITTED) == 3
    assert outcomes.count(DispatchOutcome.DENIED) == thread_count - 3


def test_concurrent_grant_revocation_race_never_permits_after_revoke_wins() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    ready = threading.Event()
    proceed = threading.Event()
    result: list[DispatchOutcome] = []

    original_status = env.grant_state.current_revocation_status

    def instrumented_status(g: Grant) -> RevocationStatus:
        ready.set()
        proceed.wait(timeout=5)
        return original_status(g)

    env.grant_state.current_revocation_status = instrumented_status  # type: ignore[assignment]

    def dispatch_attempt() -> None:
        decision = env.arbiter.arbitrate(env.request(grant=grant), evaluated_at=_EPOCH)
        result.append(decision.outcome)

    thread = threading.Thread(target=dispatch_attempt)
    thread.start()
    assert ready.wait(timeout=5)
    env.grant_state.revoke(GrantId("grant-1"))
    proceed.set()
    thread.join(timeout=5)

    assert result == [DispatchOutcome.DENIED]


# --- no executable/dispatch side effect -----------------------------------------


def test_arbitrate_performs_no_external_effect_or_catalog_mutation() -> None:
    env = _Environment()
    grant = _grant(grantee=env.grantee)
    before = env.catalog.snapshot(TenantContext(TenantId(env.tenant)))
    env.arbiter.arbitrate(env.request(grant=grant), evaluated_at=_EPOCH)
    after = env.catalog.snapshot(TenantContext(TenantId(env.tenant)))
    assert before.entries == after.entries
    assert before.revision == after.revision


def test_arbitrate_rejects_wrong_type_arguments() -> None:
    env = _Environment()
    with pytest.raises(TypeError, match="DispatchRequest"):
        env.arbiter.arbitrate(object(), evaluated_at=_EPOCH)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="must be datetime"):
        env.arbiter.arbitrate(
            env.request(grant=_grant(grantee=env.grantee)),
            evaluated_at="now",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        env.arbiter.arbitrate(
            env.request(grant=_grant(grantee=env.grantee)),
            evaluated_at=datetime(2026, 1, 1),
        )
