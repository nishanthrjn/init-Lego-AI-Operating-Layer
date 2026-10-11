"""ADR-026 public facade: deterministic owner fixtures, no providers or media."""

import asyncio
import os
import socket
import threading
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.execution.ports import CoordinationOutcome, CoordinationResult
from legoai.execution.values import (
    ExecutionContext,
    ExecutionResult,
    ExecutionState,
    SecurityContextRef,
)
from legoai.governance.ports import SecurityContext
from legoai.governance.values import GrantId, PolicyRef
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorDetail, Recoverability
from legoai.kernel.identity import ApplicationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.plugins.values import PluginDeclaration, PluginId
from legoai.runtime import local
from legoai.runtime.api import (
    GovernedExecutionConfig,
    HostError,
    HostFailure,
    OperatorGrant,
)
from legoai.runtime.local import GovernedExecution, open_governed_execution

NOW = datetime(2026, 10, 11, tzinfo=UTC)
V1 = Version(1, 0, 0)


def config(
    capability: str = "legoai.intelligence.model.chat",
) -> GovernedExecutionConfig:
    revision = ConfigurationRevisionRef(
        ConfigurationRef(
            ApplicationRef(
                ReferenceScope("operator", TenantId("tenant")), ApplicationId("app")
            ),
            "execution",
        ),
        "r1",
        V1,
    )
    offer = CapabilityOffer(CapabilityId(capability), V1)
    return GovernedExecutionConfig(
        revision,
        PrincipalRef("operator", PrincipalId("principal")),
        PolicyRef("operator", "execution", V1),
        OperatorGrant(
            GrantId("invoke"),
            "invoke-capability",
            capability,
            NOW,
            NOW + timedelta(hours=1),
        ),
        PluginDeclaration(
            PluginId("fixtures", "model" if "intelligence" in capability else "media"),
            V1,
            (offer,),
        ),
        offer,
        8,
        timedelta(minutes=5),
        timedelta(seconds=5),
        timedelta(seconds=1),
    )


def config_with_timeout(field: str, bound: timedelta) -> GovernedExecutionConfig:
    candidate = config()
    if field == "execution_timeout":
        return replace(candidate, execution_timeout=bound)
    if field == "preparation_timeout":
        return replace(candidate, preparation_timeout=bound)
    if field == "shutdown_timeout":
        return replace(candidate, shutdown_timeout=bound)
    raise AssertionError("unknown timeout field in test fixture")


async def claim(
    host: GovernedExecution, context: ExecutionContext, ready: CoordinationResult
) -> None:
    await host.claim(
        context,
        ready,
        configuration=host.configuration,
        contribution=host.contribution,
    )


def test_open_is_inert(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = config()
    forbidden = Mock(side_effect=AssertionError("external work during open"))
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(threading.Thread, "start", forbidden)
    monkeypatch.setattr(os, "getenv", forbidden)
    monkeypatch.setattr(type(os.environ), "__getitem__", forbidden)
    monkeypatch.setattr(
        "legoai.reference.secret._ProvisionedSecretSource._realize", forbidden
    )
    monkeypatch.setattr(
        "legoai.runtime._composition.secret."
        "_SyntheticSecretAccess.resolve_secret_reference",
        forbidden,
    )
    for name in (
        "_provision_interactively",
        "OllamaModelAdapter",
        "OpenAICompatibleModelAdapter",
        "compose_remote_plane",
    ):
        monkeypatch.setattr(local, name, forbidden)
    host = open_governed_execution(candidate, clock=lambda: NOW)
    context = host.establish()
    assert context.operation.subject == candidate.configuration.configuration
    assert host.contribution.offer == candidate.offer
    forbidden.assert_not_called()


def test_context_and_exact_binding() -> None:
    async def scenario() -> None:
        candidate = config()
        host = open_governed_execution(candidate, clock=lambda: NOW)
        context = host.establish()
        assert context.tenant_context == host.contribution.tenant_context
        assert context.deadline == NOW + candidate.execution_timeout
        ready = await host.coordinate(context)
        assert ready.outcome is CoordinationOutcome.READY
        assert ready.permit is not None
        assert ready.permit.resolved_entry == host.contribution
        assert ready.permit.operation == context.operation
        assert (
            ready.permit.security_decision.considered_grant == candidate.grant.grant_id
        )
        with pytest.raises(HostError) as error:
            await host.claim(
                context,
                ready,
                configuration=replace(host.configuration, revision="r2"),
                contribution=host.contribution,
            )
        assert error.value.failure is HostFailure.STALE_CONFIGURATION
        for changed in (
            replace(host.contribution, release=Version(2, 0, 0)),
            replace(host.contribution, plugin_id=PluginId("other", "owner")),
            replace(
                host.contribution,
                tenant_context=replace(context.tenant_context, tenant_id=TenantId("x")),
            ),
        ):
            with pytest.raises(HostError) as error:
                await host.claim(
                    context,
                    ready,
                    configuration=host.configuration,
                    contribution=changed,
                )
            assert error.value.failure is HostFailure.UNKNOWN_BINDING
        await claim(host, context, ready)

    asyncio.run(scenario())


def test_foreign_and_reconstructed_contexts_and_receipts_refuse() -> None:
    async def scenario() -> None:
        host = open_governed_execution(config(), clock=lambda: NOW)
        foreign = open_governed_execution(config(), clock=lambda: NOW)
        context = host.establish()
        for invalid in (replace(context), foreign.establish()):
            with pytest.raises(HostError) as error:
                await host.coordinate(invalid)
            assert error.value.failure is HostFailure.FOREIGN_CONTEXT
        ready = await host.coordinate(context)
        with pytest.raises(HostError) as error:
            await claim(host, context, replace(ready))
        assert error.value.failure is HostFailure.FOREIGN_CONTEXT
        await claim(host, context, ready)
        facts = ExecutionResult(
            context.execution_id, ExecutionState.SUCCEEDED, EffectExtent.COMPLETED, None
        )
        with pytest.raises(HostError):
            await foreign.settle(context, facts)
        with pytest.raises(HostError):
            await host.settle(
                context,
                replace(facts, execution_id=foreign.establish().execution_id),
            )
        assert await host.settle(context, facts) == facts

    asyncio.run(scenario())


def test_concurrent_claim_once_and_guard_retained_after_settlement() -> None:
    async def scenario() -> None:
        host = open_governed_execution(config(), clock=lambda: NOW)
        context = host.establish()
        ready = await host.coordinate(context)
        attempts = await asyncio.gather(
            claim(host, context, ready),
            claim(host, context, ready),
            return_exceptions=True,
        )
        assert attempts.count(None) == 1
        errors = [item for item in attempts if isinstance(item, HostError)]
        assert len(errors) == 1
        assert errors[0].failure is HostFailure.DUPLICATE_CLAIM
        facts = ExecutionResult(
            context.execution_id, ExecutionState.SUCCEEDED, EffectExtent.COMPLETED, None
        )
        await host.settle(context, facts)
        with pytest.raises(HostError) as error:
            await claim(host, context, ready)
        assert error.value.failure is HostFailure.DUPLICATE_CLAIM
        with pytest.raises(HostError):
            await host.settle(context, facts)
        with pytest.raises(HostError):
            await host.coordinate(context)

    asyncio.run(scenario())


@pytest.mark.parametrize("invalidator", ["revoke", "retire", "deadline"])
def test_current_authority_and_contribution_rechecked_at_claim(
    invalidator: str,
) -> None:
    async def scenario() -> None:
        now = NOW
        host = open_governed_execution(config(), clock=lambda: now)
        context = host.establish()
        ready = await host.coordinate(context)
        if invalidator == "revoke":
            host.revoke_authority()
        elif invalidator == "retire":
            host.retire_contribution()
        else:
            now = NOW + timedelta(minutes=5)
        with pytest.raises(HostError) as error:
            await claim(host, context, ready)
        expected = {
            "deadline": HostFailure.DEADLINE_EXCEEDED,
            "retire": HostFailure.UNKNOWN_BINDING,
            "revoke": HostFailure.UNAUTHORIZED,
        }
        assert error.value.failure is expected[invalidator]

    asyncio.run(scenario())


def test_expired_grant_cannot_use_earlier_ready_receipt() -> None:
    async def scenario() -> None:
        now = NOW
        candidate = config()
        candidate = replace(
            candidate,
            grant=replace(candidate.grant, expires_at=NOW + timedelta(seconds=1)),
        )
        host = open_governed_execution(candidate, clock=lambda: now)
        context = host.establish()
        ready = await host.coordinate(context)
        now += timedelta(seconds=2)
        with pytest.raises(HostError) as error:
            await claim(host, context, ready)
        assert error.value.failure is HostFailure.UNAUTHORIZED

    asyncio.run(scenario())


@pytest.mark.parametrize("state", [ExecutionState.CANCELLED, ExecutionState.FAILED])
def test_unknown_owner_effect_survives_deadline_close_and_late_settlement(
    state: ExecutionState,
) -> None:
    async def scenario() -> None:
        now = NOW
        host = open_governed_execution(config(), clock=lambda: now)
        context = host.establish()
        ready = await host.coordinate(context)
        await claim(host, context, ready)
        now += timedelta(hours=2)
        assert await host.close() == (context.execution_id,)
        with pytest.raises(HostError) as error:
            host.establish()
        assert error.value.failure is HostFailure.CLOSED
        with pytest.raises(HostError):
            await claim(host, context, ready)
        facts = ExecutionResult(
            context.execution_id,
            state,
            EffectExtent.UNKNOWN,
            ErrorDetail(ErrorCategory.DEADLINE_EXCEEDED, Recoverability.TERMINAL, ()),
        )
        assert await host.settle(context, facts) == facts
        assert await host.close() == ()

    asyncio.run(scenario())


def test_settlement_requires_claim_and_legal_terminal_transition() -> None:
    async def scenario() -> None:
        host = open_governed_execution(config(), clock=lambda: NOW)
        context = host.establish()
        ready = await host.coordinate(context)
        facts = ExecutionResult(
            context.execution_id, ExecutionState.SUCCEEDED, EffectExtent.COMPLETED, None
        )
        with pytest.raises(HostError):
            await host.settle(context, facts)
        await claim(host, context, ready)
        with pytest.raises(HostError):
            await host.settle(
                context,
                replace(
                    facts,
                    final_state=ExecutionState.REJECTED,
                    effect=EffectExtent.NONE,
                ),
            )
        assert await host.settle(context, facts) == facts

    asyncio.run(scenario())


def test_capacity_never_evicts_claim_history() -> None:
    async def scenario() -> None:
        host = open_governed_execution(
            replace(config(), max_executions=1), clock=lambda: NOW
        )
        context = host.establish()
        ready = await host.coordinate(context)
        await claim(host, context, ready)
        await host.settle(
            context,
            ExecutionResult(
                context.execution_id, ExecutionState.SUCCEEDED, EffectExtent.NONE, None
            ),
        )
        with pytest.raises(HostError) as error:
            host.establish()
        assert error.value.failure is HostFailure.CAPACITY_EXHAUSTED
        with pytest.raises(HostError) as error:
            await claim(host, context, ready)
        assert error.value.failure is HostFailure.DUPLICATE_CLAIM

    asyncio.run(scenario())


def test_event_loop_confinement() -> None:
    host = open_governed_execution(config(), clock=lambda: NOW)
    context = host.establish()
    asyncio.run(host.coordinate(context))
    with pytest.raises(HostError) as error:
        asyncio.run(host.close())
    assert error.value.failure is HostFailure.WRONG_EVENT_LOOP


@dataclass(frozen=True)
class ModelAnswer:
    text: str


@dataclass(frozen=True)
class MediaObservation:
    job: str
    input_disclosure: EffectExtent
    output_available: bool


def test_two_independent_owners_keep_their_result_and_effect_meaning() -> None:
    async def model_owner() -> ModelAnswer:
        host = open_governed_execution(config(), clock=lambda: NOW)
        context = host.establish()
        ready = await host.coordinate(context)
        await claim(host, context, ready)
        answer = ModelAnswer("synthetic answer")
        result = await host.settle(
            context,
            ExecutionResult(
                context.execution_id, ExecutionState.SUCCEEDED, EffectExtent.NONE, None
            ),
        )
        assert result.effect is EffectExtent.NONE
        assert await host.close() == ()
        return answer

    async def media_owner() -> MediaObservation:
        host = open_governed_execution(
            config("legoai.virtual-try-on"), clock=lambda: NOW
        )
        context = host.establish()
        ready = await host.coordinate(context)
        await claim(host, context, ready)
        observation = MediaObservation("job-fixture", EffectExtent.COMPLETED, False)
        result = await host.settle(
            context,
            ExecutionResult(
                context.execution_id, ExecutionState.FAILED, EffectExtent.UNKNOWN, None
            ),
        )
        assert result.effect is EffectExtent.UNKNOWN
        assert await host.close() == ()
        return observation

    assert asyncio.run(model_owner()) == ModelAnswer("synthetic answer")
    media = asyncio.run(media_owner())
    assert (
        media.input_disclosure is EffectExtent.COMPLETED and not media.output_available
    )


@pytest.mark.parametrize("bound", [0, -1, 100_001])
def test_invalid_capacity(bound: int) -> None:
    with pytest.raises(HostError):
        replace(config(), max_executions=bound)


@pytest.mark.parametrize(
    "field", ["execution_timeout", "preparation_timeout", "shutdown_timeout"]
)
def test_zero_lifetime_bounds_refuse(field: str) -> None:
    with pytest.raises(HostError):
        config_with_timeout(field, timedelta(0))


def test_configuration_does_not_create_unrelated_authority() -> None:
    candidate = config()
    with pytest.raises(HostError) as error:
        replace(candidate, grant=replace(candidate.grant, action="secret-use"))
    assert error.value.failure is HostFailure.INVALID_GRANT
    with pytest.raises(HostError) as error:
        config("arbitrary.workflow")
    assert error.value.failure is HostFailure.UNSUPPORTED_COMPOSITION
    with pytest.raises(HostError):
        replace(candidate, declaration=replace(candidate.declaration, offers=()))


@pytest.mark.parametrize("resists_cancellation", [False, True])
def test_close_bounds_preparation_and_reports_unresolved_work(
    monkeypatch: pytest.MonkeyPatch, resists_cancellation: bool
) -> None:
    async def scenario() -> None:
        started = asyncio.Event()
        release = asyncio.Event()

        async def delayed(
            self: object, ref: SecurityContextRef, tenant: TenantContext
        ) -> SecurityContext | None:
            started.set()
            try:
                await release.wait()
            except asyncio.CancelledError:
                if not resists_cancellation:
                    raise
                await release.wait()
            return None

        # Owner-internal fault injection only; public consumers see no resolver.
        monkeypatch.setattr(
            "legoai.runtime.local._HostSecurityContexts.resolve", delayed
        )
        host = open_governed_execution(
            replace(config(), shutdown_timeout=timedelta(milliseconds=10)),
            clock=lambda: NOW,
        )
        context = host.establish()
        work = asyncio.create_task(host.coordinate(context))
        await started.wait()
        try:
            unresolved = await host.close()
            if resists_cancellation:
                assert unresolved == (context.execution_id,)
                assert not work.done()
            else:
                assert unresolved == ()
            with pytest.raises(HostError) as error:
                host.establish()
            assert error.value.failure is HostFailure.CLOSED
        finally:
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await work
        assert await host.close() == ()

    asyncio.run(scenario())


def test_preparation_timeout_has_no_owner_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def delayed(
        self: object, ref: SecurityContextRef, tenant: TenantContext
    ) -> SecurityContext | None:
        await asyncio.Event().wait()
        return None

    monkeypatch.setattr("legoai.runtime.local._HostSecurityContexts.resolve", delayed)

    async def scenario() -> None:
        host = open_governed_execution(
            replace(config(), preparation_timeout=timedelta(milliseconds=10)),
            clock=lambda: NOW,
        )
        context = host.establish()
        result = await host.coordinate(context)
        assert result.outcome is CoordinationOutcome.CANCELLED
        with pytest.raises(HostError):
            await claim(host, context, result)
        assert await host.close() == ()

    asyncio.run(scenario())


def test_owner_cancellation_keeps_unknown_and_is_not_swallowed() -> None:
    async def scenario() -> None:
        host = open_governed_execution(config(), clock=lambda: NOW)
        context = host.establish()
        started = asyncio.Event()
        observations: list[ExecutionResult] = []

        async def owner() -> None:
            ready = await host.coordinate(context)
            await claim(host, context, ready)
            started.set()
            try:
                await asyncio.Event().wait()  # Synthetic lost-acknowledgement window.
            except asyncio.CancelledError:
                observations.append(
                    await host.settle(
                        context,
                        ExecutionResult(
                            context.execution_id,
                            ExecutionState.CANCELLED,
                            EffectExtent.UNKNOWN,
                            None,
                        ),
                    )
                )
                raise

        work = asyncio.create_task(owner())
        await started.wait()
        work.cancel()
        with pytest.raises(asyncio.CancelledError):
            await work
        assert len(observations) == 1
        assert observations[0].effect is EffectExtent.UNKNOWN
        assert await host.close() == ()

    asyncio.run(scenario())


@pytest.mark.parametrize("invalidator", ["revoke", "deadline"])
def test_coordinate_refuses_before_ready(invalidator: str) -> None:
    async def scenario() -> None:
        host = open_governed_execution(config(), clock=lambda: NOW)
        context = host.establish(deadline=NOW if invalidator == "deadline" else None)
        if invalidator == "revoke":
            host.revoke_authority()
        result = await host.coordinate(context)
        assert result.outcome is CoordinationOutcome.REJECTED
        assert result.category is (
            ErrorCategory.DEADLINE_EXCEEDED
            if invalidator == "deadline"
            else ErrorCategory.AUTHORIZATION_DENIED
        )
        with pytest.raises(HostError):
            await claim(host, context, result)
        assert await host.close() == ()

    asyncio.run(scenario())


def test_other_thread_cannot_establish_or_invalidate() -> None:
    host = open_governed_execution(config(), clock=lambda: NOW)
    failures: list[HostFailure] = []

    def other_thread() -> None:
        for operation in (
            host.establish,
            host.revoke_authority,
            host.retire_contribution,
        ):
            try:
                operation()
            except HostError as error:
                failures.append(error.failure)

    worker = threading.Thread(target=other_thread)
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert failures == [HostFailure.WRONG_EVENT_LOOP] * 3


@pytest.mark.parametrize(
    ("field", "bound"),
    [
        ("execution_timeout", timedelta(days=1, microseconds=1)),
        ("preparation_timeout", timedelta(seconds=60, microseconds=1)),
        ("shutdown_timeout", timedelta(seconds=30, microseconds=1)),
    ],
)
def test_upper_time_bounds_refuse(field: str, bound: timedelta) -> None:
    with pytest.raises(HostError):
        config_with_timeout(field, bound)


def test_invalid_input_does_not_spend_context_capacity() -> None:
    host = open_governed_execution(
        replace(config(), max_executions=1), clock=lambda: NOW
    )
    with pytest.raises(HostError):
        host.establish(deadline=NOW + timedelta(days=1))
    assert host.establish().deadline == NOW + timedelta(minutes=5)
    with pytest.raises(TypeError):
        replace(config(), max_executions=True)


def test_only_selected_offer_is_bound_from_multi_offer_declaration() -> None:
    candidate = config()
    embedding = CapabilityOffer(CapabilityId("legoai.intelligence.model.embedding"), V1)
    candidate = replace(
        candidate,
        declaration=replace(candidate.declaration, offers=(candidate.offer, embedding)),
    )
    host = open_governed_execution(candidate, clock=lambda: NOW)
    assert host.contribution.offer == candidate.offer
    with pytest.raises(HostError) as error:
        replace(candidate, offer=embedding)  # Chat grant cannot authorize embedding.
    assert error.value.failure is HostFailure.INVALID_GRANT
