"""LegoAI v0.1: the minimal production `SecurityContextResolutionPort`
realization (`StaticSecurityContextRegistry`) -- required so a real
application can compose an `ExecutionCoordinator` without depending on
test-only fakes.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from legoai.execution.values import SecurityContextRef
from legoai.governance.ports import SecurityContext
from legoai.governance.values import PolicyRef, Principal
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
from legoai.reference.execution import StaticSecurityContextRegistry

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _security_context(tenant: str) -> SecurityContext:
    principal = Principal(PrincipalRef("issuer", PrincipalId("service")))
    tenant_context = TenantContext(TenantId(tenant))
    operation = OperationRef(
        ConfigurationRef(
            ApplicationRef(
                ReferenceScope("owner", TenantId(tenant)), ApplicationId("app")
            ),
            "config",
        ),
        OperationId("op"),
        "configuration",
    )
    return SecurityContext(
        principal,
        tenant_context,
        operation,
        "invoke-capability",
        "capability",
        None,
        None,
        PolicyRef("policy-owner", "policy", Version(1, 0, 0)),
        _EPOCH + timedelta(minutes=30),
    )


def test_resolves_registered_context_for_matching_tenant() -> None:
    async def scenario() -> None:
        registry = StaticSecurityContextRegistry()
        ref = SecurityContextRef("issuer", "ref-1")
        context = _security_context("tenant-a")
        registry.register(ref, context)

        resolved = await registry.resolve(ref, TenantContext(TenantId("tenant-a")))

        assert resolved is context

    asyncio.run(scenario())


def test_returns_none_for_unregistered_reference() -> None:
    async def scenario() -> None:
        registry = StaticSecurityContextRegistry()

        resolved = await registry.resolve(
            SecurityContextRef("issuer", "missing"), TenantContext(TenantId("tenant-a"))
        )

        assert resolved is None

    asyncio.run(scenario())


def test_returns_none_when_tenant_context_does_not_match() -> None:
    async def scenario() -> None:
        registry = StaticSecurityContextRegistry()
        ref = SecurityContextRef("issuer", "ref-1")
        registry.register(ref, _security_context("tenant-a"))

        resolved = await registry.resolve(ref, TenantContext(TenantId("tenant-b")))

        assert resolved is None

    asyncio.run(scenario())
