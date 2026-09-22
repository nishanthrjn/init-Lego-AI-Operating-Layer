"""Gate-2 M11: the central end-to-end governed-invocation proof.

Exercises the complete real path -- deterministic capability declared,
Plugin lifecycle ACTIVE, Catalog publish, requirement resolve, current
authorization, dispatch arbitration, Coordinator READY/RUNNING, then the
first real governed deterministic capability invocation -- using only real
M4-M11 reference realizations (never re-implemented fakes for the pieces
under test), proving the trusted implementation is unreachable except
through this complete governed path.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from legoai.application.values import EffectiveConfiguration
from legoai.capabilities.ports import CatalogEntry
from legoai.capabilities.values import (
    CapabilityId,
    CapabilityOffer,
    CapabilityRequirement,
    CapabilityVersionRange,
)
from legoai.execution.ports import (
    CoordinationOutcome,
    CoordinationRequest,
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
from legoai.kernel.effects import EffectExtent
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
from legoai.reference.application.configuration import compose_configuration
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.deterministic import (
    normalize_text,
    text_normalization_capability_id,
    text_normalization_declaration,
    text_normalization_release,
)
from legoai.reference.evidence import InMemoryEvidenceCustody
from legoai.reference.execution import (
    DeterministicDispatchArbiter,
    ExecutionCoordinator,
)
from legoai.reference.governance import DeterministicAuthorizationEvaluator
from legoai.reference.plugins import activate, admit, initialize, inspect, validate
from legoai.reference.resolution import ResolutionStatus, resolve
from legoai.runtime._composition.governed import invoke_governed_text_normalization
from tests.support.execution import (
    HangingSecurityContextResolver,
    ImmediateSecurityContextResolver,
)
from tests.support.governance import (
    InMemoryApprovalUseFake,
    InMemoryGrantStateFake,
    InMemoryPolicyCurrencyFake,
)

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)
_CONTRACT_VERSION = Version(0, 1, 0)


def _principal(name: str) -> Principal:
    return Principal(PrincipalRef("identity-owner", PrincipalId(name)))


def _target(tenant: str = "tenant") -> ConfigurationRef:
    return ConfigurationRef(
        ApplicationRef(
            ReferenceScope("composition", TenantId(tenant)), ApplicationId("app")
        ),
        "config",
    )


def _operation(tenant: str = "tenant") -> OperationRef:
    return OperationRef(_target(tenant), OperationId("op"), "configuration")


def _policy_ref() -> PolicyRef:
    return PolicyRef("policy-owner", "policy", Version(1, 0, 0))


def _grant(*, tenant: str = "tenant", grantee: Principal) -> Grant:
    return Grant(
        GrantId("grant-1"),
        _principal("issuer"),
        grantee,
        TenantContext(TenantId(tenant)),
        "invoke-capability",
        text_normalization_capability_id().value,
        False,
        _EPOCH,
        _EPOCH + timedelta(days=1),
    )


class _Environment:
    """The complete real M4-M11 pipeline, publishing the *actual* F8b
    text-normalization declaration (never a synthetic stand-in capability
    id) so this test exercises the genuine trusted correspondence."""

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

        declaration = text_normalization_declaration()
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

        self.effective = compose_configuration(
            _target(tenant),
            (),
            contract_version=_CONTRACT_VERSION,
            interpretation_version=_CONTRACT_VERSION,
        ).effective

    def resolve_entry(self) -> CatalogEntry:
        requirement = CapabilityRequirement(
            text_normalization_capability_id(),
            CapabilityVersionRange(text_normalization_release()),
        )
        resolution = resolve(
            requirement,
            self.catalog.snapshot(TenantContext(TenantId(self.tenant))),
            resolved_at=_EPOCH,
        )
        assert resolution.status is ResolutionStatus.RESOLVED
        assert resolution.candidates == (self.entry,)
        return resolution.candidates[0]

    def security_context(
        self, *, grant: Grant | None, approval: ApprovalValue | None = None
    ) -> SecurityContext:
        return SecurityContext(
            self.grantee,
            TenantContext(TenantId(self.tenant)),
            _operation(self.tenant),
            "invoke-capability",
            text_normalization_capability_id().value,
            grant,
            approval,
            _policy_ref(),
            _EPOCH + timedelta(minutes=30),
        )

    def execution_context(
        self, *, execution_id: str = "exec-1", deadline: datetime | None = None
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
        self, *, execution_id: str = "exec-1", deadline: datetime | None = None
    ) -> CoordinationRequest:
        return CoordinationRequest(
            self.execution_context(execution_id=execution_id, deadline=deadline),
            self.resolve_entry(),
        )

    def coordinator(self, resolver: object) -> ExecutionCoordinator:
        return ExecutionCoordinator(resolver, self.arbiter, clock=lambda: _EPOCH)  # type: ignore[arg-type]


def _counting(calls: list[int]) -> Callable[[str, EffectiveConfiguration], str]:
    def implementation(text: str, effective: EffectiveConfiguration) -> str:
        calls.append(1)
        return normalize_text(text, effective)

    return implementation


# --- success: the central Gate-2/M11 proof -----------------------------------------


def test_full_governed_slice_succeeds() -> None:
    async def scenario() -> None:
        env = _Environment()
        grant = _grant(grantee=env.grantee)
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=grant))
        coordinator = env.coordinator(resolver)
        calls: list[int] = []

        coordination = await coordinator.coordinate(env.coordination_request())
        assert coordination.outcome is CoordinationOutcome.READY
        assert coordination.state is ExecutionState.RUNNING

        outcome = await invoke_governed_text_normalization(
            coordinator,
            coordination,
            "  hello   world  ",
            env.effective,
            implementation=_counting(calls),
        )

        assert len(calls) == 1
        assert outcome.execution_result.final_state is ExecutionState.SUCCEEDED
        assert outcome.execution_result.effect is EffectExtent.COMPLETED
        assert outcome.execution_result.error is None
        assert outcome.output == "hello world"
        assert await coordinator.current_state(coordination.execution_id) is (
            ExecutionState.SUCCEEDED
        )

    asyncio.run(scenario())


def test_repeated_invocation_is_deterministic() -> None:
    async def scenario() -> None:
        outputs = []
        for execution_id in ("exec-a", "exec-b"):
            env = _Environment()
            grant = _grant(grantee=env.grantee)
            resolver = ImmediateSecurityContextResolver(
                env.security_context(grant=grant)
            )
            coordinator = env.coordinator(resolver)
            coordination = await coordinator.coordinate(
                env.coordination_request(execution_id=execution_id)
            )
            outcome = await invoke_governed_text_normalization(
                coordinator, coordination, "  same input  ", env.effective
            )
            outputs.append(outcome.output)
        assert outputs[0] == outputs[1] == "same input"

    asyncio.run(scenario())


# --- zero-invocation paths ----------------------------------------------------------


def test_authorization_denied_never_invokes() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=None))
        coordinator = env.coordinator(resolver)
        calls: list[int] = []

        coordination = await coordinator.coordinate(env.coordination_request())
        assert coordination.outcome is CoordinationOutcome.REJECTED
        assert coordination.category is ErrorCategory.AUTHORIZATION_DENIED

        with pytest.raises(ValueError, match="READY"):
            await invoke_governed_text_normalization(
                coordinator,
                coordination,
                "text",
                env.effective,
                implementation=_counting(calls),
            )
        assert calls == []

    asyncio.run(scenario())


def test_stale_catalog_never_invokes() -> None:
    async def scenario() -> None:
        env = _Environment()
        grant = _grant(grantee=env.grantee)
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=grant))
        coordinator = env.coordinator(resolver)
        calls: list[int] = []

        request = env.coordination_request()
        env.catalog.withdraw(
            env.entry.plugin_id,
            env.entry.release,
            env.entry.offer,
            TenantContext(TenantId(env.tenant)),
        )
        coordination = await coordinator.coordinate(request)
        assert coordination.outcome is CoordinationOutcome.REJECTED
        assert coordination.category is ErrorCategory.CONFLICT

        with pytest.raises(ValueError, match="READY"):
            await invoke_governed_text_normalization(
                coordinator,
                coordination,
                "text",
                env.effective,
                implementation=_counting(calls),
            )
        assert calls == []

    asyncio.run(scenario())


def test_approval_exhausted_never_invokes() -> None:
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
        env.approval_use.set_uses(ApprovalIdValue("approval-1"), 1)
        resolver = ImmediateSecurityContextResolver(
            env.security_context(grant=grant, approval=approval)
        )
        coordinator = env.coordinator(resolver)
        calls: list[int] = []

        coordination = await coordinator.coordinate(env.coordination_request())
        assert coordination.outcome is CoordinationOutcome.REJECTED
        assert coordination.category is ErrorCategory.AUTHORIZATION_DENIED

        with pytest.raises(ValueError, match="READY"):
            await invoke_governed_text_normalization(
                coordinator,
                coordination,
                "text",
                env.effective,
                implementation=_counting(calls),
            )
        assert calls == []

    asyncio.run(scenario())


def test_unresolvable_security_context_never_invokes() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = ImmediateSecurityContextResolver(None)
        coordinator = env.coordinator(resolver)
        calls: list[int] = []

        coordination = await coordinator.coordinate(env.coordination_request())
        assert coordination.outcome is CoordinationOutcome.REJECTED
        assert coordination.category is ErrorCategory.DEPENDENCY_FAILURE

        with pytest.raises(ValueError, match="READY"):
            await invoke_governed_text_normalization(
                coordinator,
                coordination,
                "text",
                env.effective,
                implementation=_counting(calls),
            )
        assert calls == []

    asyncio.run(scenario())


def test_deadline_already_expired_never_invokes() -> None:
    async def scenario() -> None:
        env = _Environment()
        grant = _grant(grantee=env.grantee)
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=grant))
        coordinator = env.coordinator(resolver)
        calls: list[int] = []

        request = env.coordination_request(deadline=_EPOCH - timedelta(seconds=1))
        coordination = await coordinator.coordinate(request)
        assert coordination.outcome is CoordinationOutcome.REJECTED
        assert coordination.category is ErrorCategory.DEADLINE_EXCEEDED

        with pytest.raises(ValueError, match="READY"):
            await invoke_governed_text_normalization(
                coordinator,
                coordination,
                "text",
                env.effective,
                implementation=_counting(calls),
            )
        assert calls == []

    asyncio.run(scenario())


def test_cancellation_before_ready_never_invokes() -> None:
    async def scenario() -> None:
        env = _Environment()
        resolver = HangingSecurityContextResolver()
        coordinator = env.coordinator(resolver)
        calls: list[int] = []

        task = asyncio.ensure_future(coordinator.coordinate(env.coordination_request()))
        await resolver.entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert await coordinator.current_state(ExecutionId("exec-1")) is (
            ExecutionState.CANCELLED
        )
        assert calls == []

    asyncio.run(scenario())


# --- implementation mismatch ---------------------------------------------------------


def test_implementation_mismatch_never_invokes_and_fails() -> None:
    async def scenario() -> None:
        env = _Environment()
        grant = _grant(grantee=env.grantee)
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=grant))
        coordinator = env.coordinator(resolver)
        calls: list[int] = []

        # Publish and resolve an *unrelated* second capability/plugin, so
        # the permit's resolved_entry names something this trusted host has
        # no implementation for.
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
        other_entry = env.catalog.publish(
            other_active,
            other_declaration,
            other_declaration.offers[0],
            established_at=_EPOCH,
        )

        mismatched_request = CoordinationRequest(env.execution_context(), other_entry)
        coordination = await coordinator.coordinate(mismatched_request)
        assert coordination.outcome is CoordinationOutcome.READY

        outcome = await invoke_governed_text_normalization(
            coordinator,
            coordination,
            "text",
            env.effective,
            implementation=_counting(calls),
        )

        assert calls == []
        assert outcome.output is None
        assert outcome.execution_result.final_state is ExecutionState.FAILED
        assert outcome.execution_result.effect is EffectExtent.NONE
        assert outcome.execution_result.error is not None
        assert (
            outcome.execution_result.error.category is ErrorCategory.DEPENDENCY_FAILURE
        )

    asyncio.run(scenario())


def test_hostile_plugin_identifier_remains_inert() -> None:
    """A resolved entry whose Plugin identity contains path/import-like
    text must never be treated as anything but an exact-match failure --
    no dynamic loading, no partial match, no special-casing."""

    async def scenario() -> None:
        env = _Environment()
        grant = _grant(grantee=env.grantee)
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=grant))
        coordinator = env.coordinator(resolver)
        calls: list[int] = []

        hostile_declaration = PluginDeclaration(
            PluginId("../../etc", "os.system('rm -rf /')"),
            Version(0, 1, 0),
            (
                CapabilityOffer(
                    CapabilityId("__import__('os').system"), Version(1, 0, 0)
                ),
            ),
            (),
        )
        hostile_discovered = inspect(hostile_declaration)
        hostile_validation = validate(
            hostile_discovered, hostile_declaration, evaluated_at=_EPOCH
        )
        hostile_record = admit(
            hostile_validation,
            TenantContext(TenantId(env.tenant)),
            PluginAdmissionId("admission-hostile"),
            established_at=_EPOCH,
        )
        hostile_active = activate(
            initialize(hostile_record, established_at=_EPOCH), established_at=_EPOCH
        )
        hostile_entry = env.catalog.publish(
            hostile_active,
            hostile_declaration,
            hostile_declaration.offers[0],
            established_at=_EPOCH,
        )

        request = CoordinationRequest(env.execution_context(), hostile_entry)
        coordination = await coordinator.coordinate(request)
        assert coordination.outcome is CoordinationOutcome.READY

        outcome = await invoke_governed_text_normalization(
            coordinator,
            coordination,
            "text",
            env.effective,
            implementation=_counting(calls),
        )

        assert calls == []
        assert outcome.execution_result.final_state is ExecutionState.FAILED
        assert outcome.execution_result.error is not None
        assert (
            outcome.execution_result.error.category is ErrorCategory.DEPENDENCY_FAILURE
        )

    asyncio.run(scenario())


# --- capability failure ---------------------------------------------------------------


def test_capability_failure_invokes_once_and_fails() -> None:
    async def scenario() -> None:
        env = _Environment()
        grant = _grant(grantee=env.grantee)
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=grant))
        coordinator = env.coordinator(resolver)
        calls: list[int] = []

        def failing_implementation(text: str, effective: EffectiveConfiguration) -> str:
            calls.append(1)
            raise ValueError("input exceeds the configured maximum length")

        coordination = await coordinator.coordinate(env.coordination_request())
        assert coordination.outcome is CoordinationOutcome.READY

        outcome = await invoke_governed_text_normalization(
            coordinator,
            coordination,
            "oversize text",
            env.effective,
            implementation=failing_implementation,
        )

        assert len(calls) == 1
        assert outcome.output is None
        assert outcome.execution_result.final_state is ExecutionState.FAILED
        assert outcome.execution_result.effect is EffectExtent.NONE
        assert outcome.execution_result.error is not None
        assert (
            outcome.execution_result.error.category is ErrorCategory.EXECUTION_FAILURE
        )
        assert await coordinator.current_state(coordination.execution_id) is (
            ExecutionState.FAILED
        )

    asyncio.run(scenario())


# --- no task leaks --------------------------------------------------------------------


def test_no_task_leaks_across_success_failure_and_cancellation() -> None:
    async def scenario() -> None:
        before = frozenset(asyncio.all_tasks())

        # success
        env = _Environment()
        grant = _grant(grantee=env.grantee)
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=grant))
        coordinator = env.coordinator(resolver)
        coordination = await coordinator.coordinate(env.coordination_request())
        await invoke_governed_text_normalization(
            coordinator, coordination, "text", env.effective
        )

        # capability failure
        env2 = _Environment()
        grant2 = _grant(grantee=env2.grantee)
        resolver2 = ImmediateSecurityContextResolver(
            env2.security_context(grant=grant2)
        )
        coordinator2 = env2.coordinator(resolver2)
        coordination2 = await coordinator2.coordinate(env2.coordination_request())

        def failing(text: str, effective: EffectiveConfiguration) -> str:
            raise ValueError("boom")

        await invoke_governed_text_normalization(
            coordinator2, coordination2, "text", env2.effective, implementation=failing
        )

        # cancellation before ready
        env3 = _Environment()
        resolver3 = HangingSecurityContextResolver()
        coordinator3 = env3.coordinator(resolver3)
        task = asyncio.ensure_future(
            coordinator3.coordinate(env3.coordination_request())
        )
        await resolver3.entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert set(asyncio.all_tasks()) - before == set()

    asyncio.run(scenario())


def test_invoke_governed_text_normalization_rejects_wrong_type_argument() -> None:
    async def scenario() -> None:
        env = _Environment()
        grant = _grant(grantee=env.grantee)
        resolver = ImmediateSecurityContextResolver(env.security_context(grant=grant))
        coordinator = env.coordinator(resolver)

        bogus_result: object = object()
        with pytest.raises(TypeError, match="CoordinationResult"):
            await invoke_governed_text_normalization(
                coordinator,
                bogus_result,  # type: ignore[arg-type]
                "text",
                env.effective,
            )

    asyncio.run(scenario())
