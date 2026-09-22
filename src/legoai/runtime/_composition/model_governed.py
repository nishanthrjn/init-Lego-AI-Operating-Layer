"""LegoAI v0.1: private composition wiring for governed Model invocation
(chat, embedding) -- the effectful counterpart to `legoai.runtime.
_composition.governed`'s pure-fixture wiring.

Same ADR-002 split as `governed.py`, for the same two reasons: SS9.2's I-row
foreign-target maximum for `legoai.intelligence.model`/`legoai.reference.
model` is K, C, M, A, G, R, O, X -- no E (Execution) -- and "no reference
owner implementation imports another reference owner implementation"
separately forbids `legoai.reference.execution` importing `legoai.reference.
model`. The correspondence check (does the resolved Catalog entry name the
one known Ollama Adapter?) and the actual `ModelPort` call both belong here.

**Effect-phase mapping, the actual point of this module beyond correspondence
checking:** `ModelPreflightError`/`ModelResponseUncertainError`/
`ModelResponseRejectedError` (declared by `legoai.intelligence.model.ports`)
are mapped explicitly to `EffectExtent`/`ErrorCategory`/`Recoverability`, per
`planning/V0.1-DOCUMIND-IMPLEMENTATION-PLAN.md` SS G -- never Gate-2's
deterministic `failure -> EffectExtent.NONE` rule reused unmodified for a
network call.

**Replay:** both functions call `coordinator.claim_invocation` (not the
weaker `_require_running`) before ever calling the `ModelPort`, so two
concurrent callers for the same `execution_id` cannot both reach the
provider -- see `ExecutionCoordinator.claim_invocation`'s own docstring for
the exact guarantee.
"""

from __future__ import annotations

from legoai.capabilities.ports import CatalogEntry
from legoai.execution.ports import CoordinationOutcome, CoordinationResult
from legoai.execution.values import ExecutionResult, ExecutionState
from legoai.intelligence.model.ports import (
    ModelPort,
    ModelPreflightError,
    ModelResponseRejectedError,
    ModelResponseUncertainError,
)
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
)
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorDetail, Recoverability
from legoai.reference.execution import ExecutionCoordinator
from legoai.reference.model import (
    ollama_chat_offer,
    ollama_embedding_offer,
    ollama_plugin_id,
    ollama_release,
)


def _matches_known_offer(entry: CatalogEntry, expected_offer: object) -> bool:
    return (
        entry.plugin_id == ollama_plugin_id()
        and entry.release == ollama_release()
        and entry.offer == expected_offer
    )


async def _settle_mismatch(
    coordinator: ExecutionCoordinator, result: CoordinationResult
) -> ExecutionResult:
    return await coordinator.settle(
        result,
        final_state=ExecutionState.FAILED,
        effect=EffectExtent.NONE,
        error=ErrorDetail(
            ErrorCategory.DEPENDENCY_FAILURE, Recoverability.TERMINAL, ()
        ),
    )


async def _settle_preflight_error(
    coordinator: ExecutionCoordinator, result: CoordinationResult
) -> ExecutionResult:
    return await coordinator.settle(
        result,
        final_state=ExecutionState.FAILED,
        effect=EffectExtent.NONE,
        error=ErrorDetail(
            ErrorCategory.DEPENDENCY_FAILURE, Recoverability.POTENTIALLY_RETRYABLE, ()
        ),
    )


async def _settle_uncertain_error(
    coordinator: ExecutionCoordinator, result: CoordinationResult
) -> ExecutionResult:
    return await coordinator.settle(
        result,
        final_state=ExecutionState.FAILED,
        effect=EffectExtent.UNKNOWN,
        error=ErrorDetail(
            ErrorCategory.DEPENDENCY_FAILURE, Recoverability.REQUIRES_INTERVENTION, ()
        ),
    )


async def _settle_rejected_error(
    coordinator: ExecutionCoordinator, result: CoordinationResult
) -> ExecutionResult:
    return await coordinator.settle(
        result,
        final_state=ExecutionState.FAILED,
        effect=EffectExtent.NONE,
        error=ErrorDetail(
            ErrorCategory.DEPENDENCY_FAILURE, Recoverability.TERMINAL, ()
        ),
    )


async def invoke_governed_chat(
    coordinator: ExecutionCoordinator,
    result: CoordinationResult,
    request: ChatRequest,
    adapter: ModelPort,
) -> tuple[ExecutionResult, ChatResult | None]:
    """The narrow, explicitly-named v0.1 governed chat invocation boundary.
    Requires `result.outcome is READY` (via `coordinator.settle`/
    `claim_invocation`'s own structural enforcement); never manufactures a
    permit or bypasses `DispatchArbiterPort`.
    """
    if type(result) is not CoordinationResult:
        raise TypeError("invoke_governed_chat requires CoordinationResult")
    if result.outcome is not CoordinationOutcome.READY:
        raise ValueError("invoke_governed_chat requires a READY CoordinationResult")
    permit = result.permit
    assert permit is not None  # CoordinationResult's own invariant guarantees this

    if not _matches_known_offer(permit.resolved_entry, ollama_chat_offer()):
        return await _settle_mismatch(coordinator, result), None

    await coordinator.claim_invocation(result.execution_id)
    try:
        chat_result = await adapter.chat(request)
    except ModelPreflightError:
        return await _settle_preflight_error(coordinator, result), None
    except ModelResponseUncertainError:
        return await _settle_uncertain_error(coordinator, result), None
    except ModelResponseRejectedError:
        return await _settle_rejected_error(coordinator, result), None

    execution_result = await coordinator.settle(
        result,
        final_state=ExecutionState.SUCCEEDED,
        effect=EffectExtent.COMPLETED,
        error=None,
    )
    return execution_result, chat_result


async def invoke_governed_embedding(
    coordinator: ExecutionCoordinator,
    result: CoordinationResult,
    request: EmbeddingRequest,
    adapter: ModelPort,
) -> tuple[ExecutionResult, EmbeddingResult | None]:
    """The narrow, explicitly-named v0.1 governed embedding invocation
    boundary -- same structure as `invoke_governed_chat`, distinct
    correspondence target (the embedding offer, not the chat offer)."""
    if type(result) is not CoordinationResult:
        raise TypeError("invoke_governed_embedding requires CoordinationResult")
    if result.outcome is not CoordinationOutcome.READY:
        raise ValueError(
            "invoke_governed_embedding requires a READY CoordinationResult"
        )
    permit = result.permit
    assert permit is not None

    if not _matches_known_offer(permit.resolved_entry, ollama_embedding_offer()):
        return await _settle_mismatch(coordinator, result), None

    await coordinator.claim_invocation(result.execution_id)
    try:
        embedding_result = await adapter.embed(request)
    except ModelPreflightError:
        return await _settle_preflight_error(coordinator, result), None
    except ModelResponseUncertainError:
        return await _settle_uncertain_error(coordinator, result), None
    except ModelResponseRejectedError:
        return await _settle_rejected_error(coordinator, result), None

    execution_result = await coordinator.settle(
        result,
        final_state=ExecutionState.SUCCEEDED,
        effect=EffectExtent.COMPLETED,
        error=None,
    )
    return execution_result, embedding_result
