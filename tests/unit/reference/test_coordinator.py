"""Gate-2 M10: `ExecutionCoordinator` orchestrates one admitted Execution up
to -- never across -- the ADR-007 dispatch boundary M9's
`DeterministicDispatchArbiter` already gates. It performs no capability
invocation; "ready" means a `DispatchPermit` was obtained and handed off
inert, nothing more.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.execution.ports import (
    CoordinationOutcome,
    CoordinationRequest,
    ExecutionTransitionError,
    SecurityContextResolutionPort,
)
from legoai.execution.values import (
    ExecutionContext,
    ExecutionId,
    ExecutionState,
    SecurityContextRef,
)
from legoai.governance.ports import SecurityContext
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
    CorrelationId,
    OperationId,
    PrincipalId,
    TenantId,
)
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    OperationRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.plugins.ports import PluginAdmissionId
from legoai.plugins.values import PluginDeclaration, PluginId
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.evidence import InMemoryEvidenceCustody
from legoai.reference.execution import (
    DeterministicDispatchArbiter,
    ExecutionCoordinator,
)
from legoai.reference.governance import DeterministicAuthorizationEvaluator
from legoai.reference.plugins import activate, admit, initialize, inspect, validate
from tests.support.execution import (
    HangingSecurityContextResolver,
    ImmediateSecurityContextResolver,
    ReleasableSecurityContextResolver,
)
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
    """Mirrors `tests/unit/reference/test_execution.py`'s own `_Environment`
    exactly (same M4/M5/M6 pipeline), adding only the `ExecutionCoordinator`
    and its `SecurityContextRef` bridge -- proving M10 integrates with the
    *real* M9 arbiter, never a re-implementation of its locking.
    """

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

    def execution_context(
        self,
        *,
        execution_id: str = "exec-1",
        deadline: datetime | None = None,
    ) -> ExecutionContext:
        return ExecutionContext(
            ExecutionId(execution_id),
            _operation(self.tenant),
            TenantContext(TenantId(self.tenant)),
            SecurityContextRef("issuer", "ref-1"),
            CorrelationId("corr-1"),
            None,
            deadline,
            None,
        )

    def coordination_request(
        self,
        *,
        execution_id: str = "exec-1",
        deadline: datetime | None = None,
    ) -> CoordinationRequest:
        return CoordinationRequest(
            self.execution_context(execution_id=execution_id, deadline=deadline),
            self.entry,
        )

    def coordinator(
        self, resolver: SecurityContextResolutionPort
    ) -> ExecutionCoordinator:
        return ExecutionCoordinator(resolver, self.arbiter, clock=lambda: _EPOCH)


def _owned_tasks(before: frozenset[asyncio.Task[object]]) -> set[asyncio.Task[object]]:
    return set(asyncio.all_tasks()) - before


# --- happy path --------------------------------------------------------------------


def test_ready_when_permitted() -> None:
    async def scenario() -> None:
        env = _Environment()
        grant = _grant(grantee=env.grantee)
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=grant))
        coordinator = env.coordinator(resolver)
        before = frozenset(asyncio.all_tasks())

        result = await coordinator.coordinate(env.coordination_request())

        assert result.outcome is CoordinationOutcome.READY
        assert result.state is ExecutionState.RUNNING
        assert result.permit is not None
        assert result.permit.resolved_entry == env.entry
        assert result.category is None
        assert await coordinator.current_state(ExecutionId("exec-1")) is (
            ExecutionState.RUNNING
        )
        assert _owned_tasks(before) == set()

    asyncio.run(scenario())


# --- current-authority revalidation (never a cached decision) ---------------------


def test_rejected_when_no_grant_supplied() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=None))
        coordinator = env.coordinator(resolver)

        result = await coordinator.coordinate(env.coordination_request())

        assert result.outcome is CoordinationOutcome.REJECTED
        assert result.state is ExecutionState.REJECTED
        assert result.permit is None
        assert result.category is ErrorCategory.AUTHORIZATION_DENIED

    asyncio.run(scenario())


def test_rejected_when_grant_revoked_before_coordination() -> None:
    async def scenario() -> None:
        env = _Environment()
        grant = _grant(grantee=env.grantee)
        env.grant_state.revoke(GrantId("grant-1"))
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=grant))
        coordinator = env.coordinator(resolver)

        result = await coordinator.coordinate(env.coordination_request())

        assert result.outcome is CoordinationOutcome.REJECTED
        assert result.category is ErrorCategory.AUTHORIZATION_DENIED

    asyncio.run(scenario())


def test_rejected_when_catalog_entry_withdrawn() -> None:
    async def scenario() -> None:
        env = _Environment()
        grant = _grant(grantee=env.grantee)
        env.catalog.withdraw(
            env.entry.plugin_id,
            env.entry.release,
            env.entry.offer,
            TenantContext(TenantId(env.tenant)),
        )
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=grant))
        coordinator = env.coordinator(resolver)

        result = await coordinator.coordinate(env.coordination_request())

        assert result.outcome is CoordinationOutcome.REJECTED
        assert result.category is ErrorCategory.CONFLICT

    asyncio.run(scenario())


def test_rejected_when_security_context_unresolvable() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = ImmediateSecurityContextResolver(None)
        coordinator = env.coordinator(resolver)

        result = await coordinator.coordinate(env.coordination_request())

        assert result.outcome is CoordinationOutcome.REJECTED
        assert result.category is ErrorCategory.DEPENDENCY_FAILURE

    asyncio.run(scenario())


# --- deadline enforcement -----------------------------------------------------------


def test_rejected_when_deadline_already_expired_without_arbitrating() -> None:
    async def scenario() -> None:
        env = _Environment()

        class _ExplodingResolver:
            async def resolve(
                self, ref: SecurityContextRef, tenant_context: TenantContext
            ) -> SecurityContext | None:
                raise AssertionError("must not be called: deadline already expired")

        coordinator = ExecutionCoordinator(
            _ExplodingResolver(), env.arbiter, clock=lambda: _EPOCH
        )
        request = env.coordination_request(deadline=_EPOCH - timedelta(seconds=1))

        result = await coordinator.coordinate(request)

        assert result.outcome is CoordinationOutcome.REJECTED
        assert result.category is ErrorCategory.DEADLINE_EXCEEDED

    asyncio.run(scenario())


def test_rejected_when_deadline_expires_during_supervised_wait() -> None:
    async def scenario() -> None:
        env = _Environment()
        release = asyncio.Event()  # never set
        resolver = ReleasableSecurityContextResolver(release=release)
        # Real wall-clock deadline: use datetime.now(UTC) so the relative
        # delay handed to asyncio.timeout is a small positive real value.
        real_now = datetime.now(UTC)
        coordinator = ExecutionCoordinator(
            resolver, env.arbiter, clock=lambda: real_now
        )
        request = env.coordination_request(
            deadline=real_now + timedelta(milliseconds=50)
        )
        before = frozenset(asyncio.all_tasks())

        result = await coordinator.coordinate(request)

        assert result.outcome is CoordinationOutcome.REJECTED
        assert result.category is ErrorCategory.DEADLINE_EXCEEDED
        assert resolver.entered.is_set()
        assert _owned_tasks(before) == set()

    asyncio.run(scenario())


# --- child failure containment -------------------------------------------------------


def test_child_failure_is_rejected_never_running() -> None:
    async def scenario() -> None:
        env = _Environment()
        release = asyncio.Event()
        release.set()
        resolver = ReleasableSecurityContextResolver(
            release=release, error=RuntimeError("boom")
        )
        coordinator = env.coordinator(resolver)
        before = frozenset(asyncio.all_tasks())

        result = await coordinator.coordinate(env.coordination_request())

        assert result.outcome is CoordinationOutcome.REJECTED
        assert result.category is ErrorCategory.EXECUTION_FAILURE
        assert _owned_tasks(before) == set()

    asyncio.run(scenario())


# --- cancellation ---------------------------------------------------------------------


def test_cancellation_before_running_marks_cancelled_and_propagates() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = HangingSecurityContextResolver()
        coordinator = env.coordinator(resolver)
        before = frozenset(asyncio.all_tasks())

        task = asyncio.ensure_future(coordinator.coordinate(env.coordination_request()))
        await resolver.entered.wait()
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert await coordinator.current_state(ExecutionId("exec-1")) is (
            ExecutionState.CANCELLED
        )
        assert _owned_tasks(before) == set()

    asyncio.run(scenario())


def test_cancellation_after_ready_has_no_effect_no_reintroduced_window() -> None:
    """ADR-007 requires immediate handoff: `coordinate` performs no await
    between obtaining a PERMITTED decision and returning, so there is no
    window for a post-permit cancellation to land inside this Coordinator.
    Cancelling the already-completed task is simply a documented no-op.
    """

    async def scenario() -> None:
        env = _Environment()
        grant = _grant(grantee=env.grantee)
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=grant))
        coordinator = env.coordinator(resolver)

        task = asyncio.ensure_future(coordinator.coordinate(env.coordination_request()))
        result = await task

        cancelled = task.cancel()  # task already done: no-op, returns False

        assert cancelled is False
        assert result.outcome is CoordinationOutcome.READY
        assert await coordinator.current_state(ExecutionId("exec-1")) is (
            ExecutionState.RUNNING
        )

    asyncio.run(scenario())


# --- Approval last-use race: Coordinator respects M9, duplicates no locking ----------


def test_two_coordinations_race_for_last_approval_use() -> None:
    async def scenario() -> None:
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
        security_context = env.security_context(grant=grant, approval=approval)

        class _YieldingResolver:
            async def resolve(
                self, ref: SecurityContextRef, tenant_context: TenantContext
            ) -> SecurityContext | None:
                await asyncio.sleep(0)
                return security_context

        coordinator_a = ExecutionCoordinator(
            _YieldingResolver(), env.arbiter, clock=lambda: _EPOCH
        )
        coordinator_b = ExecutionCoordinator(
            _YieldingResolver(), env.arbiter, clock=lambda: _EPOCH
        )
        request_a = env.coordination_request(execution_id="exec-a")
        request_b = env.coordination_request(execution_id="exec-b")

        result_a, result_b = await asyncio.gather(
            coordinator_a.coordinate(request_a),
            coordinator_b.coordinate(request_b),
        )

        outcomes = {result_a.outcome, result_b.outcome}
        assert outcomes == {CoordinationOutcome.READY, CoordinationOutcome.REJECTED}
        ready = result_a if result_a.outcome is CoordinationOutcome.READY else result_b
        rejected = (
            result_b if result_a.outcome is CoordinationOutcome.READY else result_a
        )
        assert ready.permit is not None
        assert rejected.category is ErrorCategory.AUTHORIZATION_DENIED

    asyncio.run(scenario())


# --- construction inertness ------------------------------------------------------------


def test_coordinate_rejects_wrong_type_argument() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = ImmediateSecurityContextResolver(None)
        coordinator = env.coordinator(resolver)

        with pytest.raises(TypeError, match="CoordinationRequest"):
            await coordinator.coordinate(object())  # type: ignore[arg-type]

    asyncio.run(scenario())


def test_coordinate_twice_for_same_execution_id_raises_transition_error() -> None:
    async def scenario() -> None:
        env = _Environment()
        grant = _grant(grantee=env.grantee)
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=grant))
        coordinator = env.coordinator(resolver)
        request = env.coordination_request()

        first = await coordinator.coordinate(request)
        assert first.outcome is CoordinationOutcome.READY

        with pytest.raises(ExecutionTransitionError):
            await coordinator.coordinate(request)

    asyncio.run(scenario())


def test_construction_requires_no_running_event_loop() -> None:
    # Deliberately constructed with no `asyncio.run`/event loop active at
    # all: construction must never require or start one.
    env = _Environment()
    resolver = ImmediateSecurityContextResolver(None)
    coordinator = ExecutionCoordinator(resolver, env.arbiter)
    assert coordinator is not None
