"""Gate-2 M10: test-only `SecurityContextResolutionPort` fakes.

These are synthetic supervision fixtures (task's own instruction: "wait
until released", "raise controlled exception", "wait forever until
cancelled") -- never real I/O, never the actual F8b deterministic
capability, and never a production realization.
"""

from __future__ import annotations

import asyncio

from legoai.execution.values import SecurityContextRef
from legoai.governance.ports import SecurityContext
from legoai.kernel.context import TenantContext


class ImmediateSecurityContextResolver:
    """Resolves instantly to a fixed `SecurityContext` (or `None`, to
    simulate an unresolvable reference)."""

    def __init__(self, security_context: SecurityContext | None) -> None:
        self._security_context = security_context

    async def resolve(
        self, ref: SecurityContextRef, tenant_context: TenantContext
    ) -> SecurityContext | None:
        return self._security_context


class ReleasableSecurityContextResolver:
    """ "Wait until released" / "raise controlled exception" fixture.

    `entered` is set the instant this resolver starts waiting, so a test
    can deterministically synchronize on "the supervised child has begun"
    before triggering a deadline/cancellation/release from the driving
    thread -- no sleep-based orchestration.
    """

    def __init__(
        self,
        *,
        release: asyncio.Event,
        security_context: SecurityContext | None = None,
        error: Exception | None = None,
    ) -> None:
        self._release = release
        self._security_context = security_context
        self._error = error
        self.entered = asyncio.Event()

    async def resolve(
        self, ref: SecurityContextRef, tenant_context: TenantContext
    ) -> SecurityContext | None:
        self.entered.set()
        await self._release.wait()
        if self._error is not None:
            raise self._error
        return self._security_context


class HangingSecurityContextResolver:
    """ "Wait forever until cancelled" fixture: never completes on its own."""

    def __init__(self) -> None:
        self.entered = asyncio.Event()

    async def resolve(
        self, ref: SecurityContextRef, tenant_context: TenantContext
    ) -> SecurityContext | None:
        self.entered.set()
        await asyncio.Event().wait()
        raise AssertionError("unreachable: this resolver never completes")
