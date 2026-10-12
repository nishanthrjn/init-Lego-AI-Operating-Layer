"""Trusted single-operator composition through the public execution facade."""

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import TracebackType
from uuid import uuid4

from legoai.capabilities.values import CapabilityOffer
from legoai.execution.ports import CoordinationResult
from legoai.execution.values import ExecutionContext, ExecutionId
from legoai.governance.values import GrantId, PolicyRef
from legoai.kernel.errors import ErrorCategory
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
from legoai.runtime.api import (
    GovernedExecutionConfig,
    HostError,
    HostFailure,
    OperatorGrant,
)
from legoai.runtime.local import GovernedExecution, open_governed_execution

from .comfyui import HARD_MAX_WAIT_SECONDS
from .composition import OFFER, TRY_ON_OFFER, Contribution
from .drivers.base import ProviderError
from .ports import TextToImagePort, VirtualTryOnPort
from .values import ApprovedWorkflowRef


def _refusal(failure: HostError) -> ProviderError:
    if failure.failure is HostFailure.DEADLINE_EXCEEDED:
        category = ErrorCategory.DEADLINE_EXCEEDED
    elif failure.failure in {
        HostFailure.STALE_CONFIGURATION,
        HostFailure.UNKNOWN_BINDING,
        HostFailure.CLOSED,
        HostFailure.DUPLICATE_CLAIM,
        HostFailure.WRONG_EXECUTION_STATE,
    }:
        category = ErrorCategory.CONFLICT
    else:
        category = ErrorCategory.POLICY_VIOLATION
    return ProviderError(category, "media_execution_refused")


class _UnsettledExecution(ProviderError):
    """Owner-local custody on failed close; never a clean shutdown receipt.

    The handle and original failure stay private to media. In-memory custody
    lasts only as long as this exception; there is no durable repair service.
    Unclaimed READY work cannot be fabricated into settled facts.
    """

    def __init__(
        self,
        execution: GovernedExecution,
        unresolved: tuple[ExecutionId, ...] | None,
        owner_failure: BaseException | None,
        *,
        close_failure: BaseException | None = None,
    ) -> None:
        super().__init__(ErrorCategory.EXECUTION_FAILURE, "media_execution_unsettled")
        self._execution = execution
        self._unresolved = unresolved
        self._owner_failure = owner_failure
        self._close_failure = close_failure


async def _close(
    execution: GovernedExecution, failure: BaseException | None = None
) -> None:
    try:
        unresolved = await execution.close()
    except BaseException as close_failure:
        # Failed/interrupted close is not evidence of settled obligations.
        raise _UnsettledExecution(
            execution, None, failure, close_failure=close_failure
        ) from None
    if unresolved:
        raise _UnsettledExecution(execution, unresolved, failure) from None


@dataclass(frozen=True)
class LocalSession:
    execution: GovernedExecution
    ready: CoordinationResult
    context: ExecutionContext
    contribution: Contribution

    async def __aenter__(self) -> LocalSession:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await _close(self.execution, exc)
        if isinstance(exc, HostError):
            raise _refusal(exc) from None


_NAMES = {OFFER: "text-to-image", TRY_ON_OFFER: "virtual-try-on"}


async def prepare_local(
    adapter: TextToImagePort | VirtualTryOnPort,
    revision_digest: str,
    *,
    approved: ApprovedWorkflowRef,
    timeout: float = 300,
    binding: str = "comfyui-local",
    offer: CapabilityOffer = OFFER,
) -> LocalSession:
    """Prepare one explicit operator invocation; use the session with async with.

    Trusted composition pins revision, workflow and adapter. Request/provider
    data cannot supply authority. No credential or provider operation occurs.
    """
    if (
        type(timeout) not in (float, int)
        or not math.isfinite(timeout)
        or not 0 < timeout <= HARD_MAX_WAIT_SECONDS
    ):
        raise ValueError("invalid execution timeout")
    if offer not in _NAMES:
        raise ValueError("unsupported capability offer")
    now = datetime.now(UTC)
    target = ConfigurationRef(
        ApplicationRef(
            ReferenceScope("local-host", TenantId("local-operator")),
            ApplicationId(_NAMES[offer]),
        ),
        "generation",
    )
    revision = ConfigurationRevisionRef(target, revision_digest, Version(1, 0, 0))
    config = GovernedExecutionConfig(
        configuration=revision,
        principal=PrincipalRef("local-host", PrincipalId("operator")),
        policy=PolicyRef("local-host", "operator-generation", Version(1, 0, 0)),
        grant=OperatorGrant(
            GrantId(uuid4().hex),
            "invoke-capability",
            offer.capability.value,
            now,
            now + timedelta(seconds=timeout + 30),
        ),
        declaration=PluginDeclaration(
            PluginId("legoai", "local-comfyui"), Version(1, 0, 0), (offer,)
        ),
        offer=offer,
        max_executions=1,
        execution_timeout=timedelta(seconds=timeout),
        preparation_timeout=timedelta(seconds=5),
        shutdown_timeout=timedelta(seconds=5),
    )
    try:
        execution = open_governed_execution(config)
    except HostError as failure:
        raise _refusal(failure) from None
    try:
        contribution = Contribution(
            binding, revision, execution.contribution, approved, adapter
        )
        context = execution.establish(deadline=now + timedelta(seconds=timeout))
        ready = await execution.coordinate(context)
        return LocalSession(execution, ready, context, contribution)
    except BaseException as failure:
        await _close(execution, failure)
        if isinstance(failure, HostError):
            raise _refusal(failure) from None
        raise
