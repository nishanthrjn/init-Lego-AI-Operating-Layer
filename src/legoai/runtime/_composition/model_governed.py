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

M6.5 adds explicit routed Chat wiring to an operator-associated Catalog entry
and adapter. That path accepts the existing Chat capability from any admitted
Plugin and shares the original Chat invocation claim and phase mapping.

**Effect-phase mapping, the actual point of this module beyond correspondence
checking:** `ModelPreflightError`/`ModelResponseUncertainError`/
`ModelResponseRejectedError` (declared by `legoai.intelligence.model.ports`)
are mapped explicitly to `EffectExtent`/`ErrorCategory`/`Recoverability`, per
`planning/V0.1-DOCUMIND-IMPLEMENTATION-PLAN.md` SS G -- never Gate-2's
deterministic `failure -> EffectExtent.NONE` rule reused unmodified for a
network call.

**Replay:** invocation paths call `coordinator.claim_invocation` (not the
weaker `_require_running`) before ever calling the `ModelPort`, so two
concurrent callers for the same `execution_id` cannot both reach the
provider -- see `ExecutionCoordinator.claim_invocation`'s own docstring for
the exact guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from legoai.capabilities.ports import CatalogEntry
from legoai.execution.ports import CoordinationOutcome, CoordinationResult
from legoai.execution.values import ExecutionResult, ExecutionState
from legoai.intelligence.model.ports import (
    ModelPort,
    ModelPreflightError,
    ModelResponseRejectedError,
    ModelResponseUncertainError,
)
from legoai.intelligence.model.routing import ModelBinding, ModelRouteDecision
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
)
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorDetail, Recoverability
from legoai.kernel.references import ConfigurationRevisionRef
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

    return await _invoke_chat(coordinator, result, request, adapter, None)


async def _invoke_chat(
    coordinator: ExecutionCoordinator,
    result: CoordinationResult,
    request: ChatRequest,
    adapter: ModelPort,
    expected_binding: ModelBinding | None,
) -> tuple[ExecutionResult, ChatResult | None]:
    """One shared invocation claim and phase mapping for both composition paths."""
    await coordinator.claim_invocation(result.execution_id)
    try:
        chat_result = await adapter.chat(request)
        if expected_binding is not None and (
            type(chat_result) is not ChatResult
            or chat_result.model_identity != expected_binding.model_id
            or chat_result.provider_identity != expected_binding.provider_id
        ):
            raise ModelResponseRejectedError("response does not match model binding")
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


@dataclass(frozen=True, slots=True)
class ConfiguredModelBinding:
    """Private trusted composition association, never a public routing value.

    The operator binds an already configured adapter once. Changing its settings
    requires a new revision/association; mutating an adapter behind this record is
    unsupported. This is not attestation of hostile code or provider model weights.
    The v1 chat offer is the existing provider-independent capability contract;
    its historical helper name does not require an Ollama Plugin identity here.
    """

    configuration_revision: ConfigurationRevisionRef
    binding: ModelBinding
    entry: CatalogEntry
    adapter: ModelPort = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.configuration_revision) is not ConfigurationRevisionRef:
            raise TypeError("configured model requires ConfigurationRevisionRef")
        if type(self.binding) is not ModelBinding:
            raise TypeError("configured model requires ModelBinding")
        if type(self.entry) is not CatalogEntry:
            raise TypeError("configured model requires CatalogEntry")
        scope = self.configuration_revision.configuration.application.scope
        if self.entry.tenant_context.tenant_id != scope.tenant_id:
            raise ValueError("configured model tenant mismatch")
        if self.entry.offer != ollama_chat_offer():
            raise ValueError("configured model requires the v1 chat capability")


async def invoke_routed_chat(
    coordinator: ExecutionCoordinator,
    result: CoordinationResult,
    request: ChatRequest,
    route: ModelRouteDecision,
    configured: ConfiguredModelBinding,
) -> tuple[ExecutionResult, ChatResult | None]:
    """Match the pinned selection to explicit wiring, then use governed Chat.

    No lookup, adapter construction, retry or fallback occurs. A route is not a
    permit: only this Coordinator's real READY execution can claim invocation.
    Current authorization/catalog checks remain the existing dispatch contract,
    with its documented trusted-process and admission-to-call limitations.
    """
    if type(result) is not CoordinationResult:
        raise TypeError("routed chat requires CoordinationResult")
    if result.outcome is not CoordinationOutcome.READY:
        raise ValueError("routed chat requires a READY CoordinationResult")
    if type(request) is not ChatRequest:
        raise TypeError("routed chat requires ChatRequest")
    if type(route) is not ModelRouteDecision:
        raise TypeError("routed chat requires ModelRouteDecision")
    if type(configured) is not ConfiguredModelBinding:
        raise TypeError("routed chat requires ConfiguredModelBinding")
    permit = result.permit
    assert permit is not None
    if (
        route.selected != configured.binding
        or route.configuration_revision != configured.configuration_revision
        or permit.resolved_entry != configured.entry
        or permit.operation.subject != configured.configuration_revision.configuration
    ):
        # A rejected binding must not settle another concurrent caller's already
        # claimed invocation. Consume the same claim before a no-call failure.
        await coordinator.claim_invocation(result.execution_id)
        return await _settle_mismatch(coordinator, result), None
    return await _invoke_chat(
        coordinator, result, request, configured.adapter, configured.binding
    )


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

    return await _invoke_embedding(coordinator, result, request, adapter)


async def invoke_routed_embedding(
    coordinator: ExecutionCoordinator,
    result: CoordinationResult,
    request: EmbeddingRequest,
    entry: CatalogEntry,
    adapter: ModelPort,
    configuration_revision: ConfigurationRevisionRef,
) -> tuple[ExecutionResult, EmbeddingResult | None]:
    """ADR-014 §3.5: embedding through the same pinned selected binding.

    The operator associates the selected contribution's own published v1
    embedding entry and adapter; there is no second selection, lookup, retry or
    fallback. Effect mapping is the shared embedding mapping below.
    """
    if type(result) is not CoordinationResult:
        raise TypeError("routed embedding requires CoordinationResult")
    if result.outcome is not CoordinationOutcome.READY:
        raise ValueError("routed embedding requires a READY CoordinationResult")
    if type(request) is not EmbeddingRequest:
        raise TypeError("routed embedding requires EmbeddingRequest")
    if type(entry) is not CatalogEntry:
        raise TypeError("routed embedding requires CatalogEntry")
    if type(configuration_revision) is not ConfigurationRevisionRef:
        raise TypeError("routed embedding requires ConfigurationRevisionRef")
    permit = result.permit
    assert permit is not None
    scope = configuration_revision.configuration.application.scope
    if (
        entry.offer != ollama_embedding_offer()
        or entry.tenant_context.tenant_id != scope.tenant_id
        or permit.resolved_entry != entry
        or permit.operation.subject != configuration_revision.configuration
    ):
        # Same no-call discipline as routed Chat: consume the claim first.
        await coordinator.claim_invocation(result.execution_id)
        return await _settle_mismatch(coordinator, result), None
    return await _invoke_embedding(coordinator, result, request, adapter)


async def _invoke_embedding(
    coordinator: ExecutionCoordinator,
    result: CoordinationResult,
    request: EmbeddingRequest,
    adapter: ModelPort,
) -> tuple[ExecutionResult, EmbeddingResult | None]:
    """One shared embedding invocation claim and phase mapping."""
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
