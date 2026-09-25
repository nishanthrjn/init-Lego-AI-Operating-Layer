"""Trusted host composition, not a global provider registry or new owner."""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

from legoai.capabilities.ports import CatalogEntry, CatalogPort
from legoai.capabilities.values import (
    CapabilityId,
    CapabilityOffer,
    CapabilityRequirement,
)
from legoai.execution.ports import CoordinationOutcome, CoordinationResult
from legoai.execution.values import ExecutionContext, ExecutionResult, ExecutionState
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorDetail, Recoverability
from legoai.kernel.references import ConfigurationRevisionRef
from legoai.kernel.versions import Version
from legoai.observability.ports import ObservationSinkPort
from legoai.observability.values import Observation, ObservationEventCode
from legoai.plugins.ports import PluginLifecycleRecord, PluginLifecycleState
from legoai.reference.execution import ExecutionCoordinator
from legoai.reference.resolution import resolve

from .ports import TextToImagePort
from .values import (
    ApprovedWorkflowRef,
    Cessation,
    GenerationCancelled,
    GenerationResult,
    Outcome,
    TextToImageRequest,
    identifier,
)

OFFER = CapabilityOffer(CapabilityId("legoai.text-to-image"), Version(1, 0, 0))


@dataclass(frozen=True, slots=True)
class Contribution:
    binding: str
    revision: ConfigurationRevisionRef
    entry: CatalogEntry
    activation: PluginLifecycleRecord
    workflow: ApprovedWorkflowRef
    adapter: TextToImagePort = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        identifier(self.binding)
        if type(self.workflow) is not ApprovedWorkflowRef:
            raise TypeError("approved workflow required")
        if type(self.revision) is not ConfigurationRevisionRef:
            raise TypeError("exact configuration revision required")
        if (
            type(self.entry) is not CatalogEntry
            or type(self.activation) is not PluginLifecycleRecord
        ):
            raise TypeError("admitted contribution required")
        if (
            self.revision.configuration.application.scope.tenant_id
            != self.entry.tenant_context.tenant_id
        ):
            raise ValueError("tenant mismatch")
        if (
            self.activation.plugin_id,
            self.activation.release,
            self.activation.admission_id,
            self.activation.tenant_context,
        ) != (
            self.entry.plugin_id,
            self.entry.release,
            self.entry.admission_id,
            self.entry.tenant_context,
        ):
            raise ValueError("activation mismatch")


def select(
    requirement: CapabilityRequirement,
    binding: str,
    revision: ConfigurationRevisionRef,
    contributions: tuple[Contribution, ...],
    catalog: CatalogPort,
    now: datetime,
) -> Contribution:
    identifier(binding)
    if type(contributions) is not tuple or not 1 <= len(contributions) <= 16:
        raise ValueError("bounded contributions required")
    matches = [c for c in contributions if c.binding == binding]
    if len(matches) != 1:
        raise ValueError("unknown or ambiguous binding")
    chosen = matches[0]
    if chosen.revision != revision:
        raise ValueError("stale configuration")
    if chosen.activation.state is not PluginLifecycleState.ACTIVE:
        raise ValueError("inactive plugin")
    snapshot = catalog.snapshot(chosen.entry.tenant_context)
    resolution = resolve(requirement, snapshot, resolved_at=now)
    if chosen.entry not in resolution.candidates or chosen.entry.offer != OFFER:
        raise ValueError("unavailable or incompatible contribution")
    return chosen


async def invoke(
    coordinator: ExecutionCoordinator,
    ready: CoordinationResult,
    context: ExecutionContext,
    chosen: Contribution,
    expected_revision: ConfigurationRevisionRef,
    request: TextToImageRequest,
    *,
    sink: ObservationSinkPort | None = None,
) -> tuple[ExecutionResult, GenerationResult]:
    if ready.outcome is not CoordinationOutcome.READY or ready.permit is None:
        raise ValueError("governed READY result required")
    if context.execution_id != ready.execution_id:
        raise ValueError("execution mismatch")
    await coordinator.claim_invocation(ready.execution_id)
    if (
        chosen.revision != expected_revision
        or chosen.activation.state is not PluginLifecycleState.ACTIVE
        or ready.permit.resolved_entry != chosen.entry
        or ready.permit.operation != context.operation
        or context.operation.subject != expected_revision.configuration
        or context.tenant_context != chosen.entry.tenant_context
    ):
        output = GenerationResult(
            Outcome.FAILED, EffectExtent.NONE, error=ErrorCategory.CONFLICT
        )
    else:
        started = False
        cancelled_receipt: GenerationResult | None = None
        try:
            remaining = (
                None
                if context.deadline is None
                else (context.deadline - datetime.now(UTC)).total_seconds()
            )
            if remaining is not None and remaining <= 0:
                raise TimeoutError
            async with asyncio.timeout(remaining):
                started = True
                try:
                    output = await chosen.adapter.generate(request)
                except GenerationCancelled as cancelled:
                    cancelled_receipt = cancelled.result
                    # asyncio.timeout recognizes the base cancellation type. Keep
                    # the receipt locally while preserving its timeout translation.
                    raise asyncio.CancelledError from None
                if type(output) is not GenerationResult:
                    raise TypeError("generation result required")
                if (
                    output.job is not None
                    and (
                        output.job.provider != "comfyui"
                        or output.job.binding != chosen.binding
                    )
                ) or (
                    output.image is not None
                    and (
                        output.image.workflow != chosen.workflow
                        or output.image.seed
                        != (request.seed if request.seed is not None else 0)
                    )
                ):
                    output = GenerationResult(
                        Outcome.FAILED,
                        output.effect,
                        error=ErrorCategory.VALIDATION_ERROR,
                    )
        except asyncio.CancelledError:
            output = cancelled_receipt or GenerationResult(
                Outcome.CANCELLED,
                EffectExtent.UNKNOWN if started else EffectExtent.NONE,
                cessation=Cessation.UNKNOWN,
            )
            await coordinator.settle(
                ready,
                final_state=ExecutionState.CANCELLED,
                effect=output.effect,
                error=None,
            )
            raise GenerationCancelled(output) from None
        except TimeoutError:
            output = GenerationResult(
                Outcome.DEADLINE,
                cancelled_receipt.effect
                if cancelled_receipt is not None
                else (EffectExtent.UNKNOWN if started else EffectExtent.NONE),
                job=None if cancelled_receipt is None else cancelled_receipt.job,
                error=ErrorCategory.DEADLINE_EXCEEDED,
                cessation=Cessation.UNKNOWN,
            )
        except Exception:
            output = GenerationResult(
                Outcome.FAILED,
                EffectExtent.UNKNOWN if started else EffectExtent.NONE,
                error=ErrorCategory.EXECUTION_FAILURE,
            )
    state = (
        ExecutionState.SUCCEEDED
        if output.outcome is Outcome.SUCCESS
        else ExecutionState.FAILED
    )
    if output.outcome is Outcome.CANCELLED:
        state = ExecutionState.CANCELLED
    error = (
        None
        if output.error is None
        else ErrorDetail(output.error, Recoverability.REQUIRES_INTERVENTION, ())
    )
    execution = await coordinator.settle(
        ready, final_state=state, effect=output.effect, error=error
    )
    if sink is not None:
        try:
            sink.emit(
                Observation(
                    1,
                    ObservationEventCode("generation." + output.outcome.value),
                    "generative-media",
                    correlation_id=context.correlation_id,
                    operation=context.operation,
                    configuration_revision=expected_revision,
                    error_category=output.error,
                    size_bytes=None
                    if output.image is None
                    else output.image.byte_length,
                )
            )
        except Exception:
            # Diagnostic delivery never changes an already settled external effect.
            pass
    return execution, output
