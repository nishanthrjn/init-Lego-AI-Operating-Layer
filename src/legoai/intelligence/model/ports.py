"""LegoAI v0.1: `ModelPort` -- the one public, provider-neutral Model
interaction Protocol ADR-002 SS7.3 names ("Model Port... a Model Adapter
imports that Port"). One Port, two operations (`chat`, `embed`): ADR-002
names a single "Model Port," not two -- splitting generation and embedding
into separate Ports would invent structure authority does not ask for, not
avoid combining unrelated concerns for convenience.

M6.5 adds ModelRouterPort for pure configuration selection. It performs no
interaction and leaves ModelPort's two operations unchanged.

**Three exception classes, one per observable effect phase** -- this is the
seam `planning/V0.1-DOCUMIND-IMPLEMENTATION-PLAN.md` SS G requires so a
caller (the composition-layer invocation wiring, never this module) can map
network-call failure honestly instead of reusing Gate-2's pure-deterministic
`failure -> EffectExtent.NONE` rule unchanged:

    ModelPreflightError          -- failed before any request left this
                                     process (config/validation/connection-
                                     refused-before-send): no possible
                                     provider-side effect -> EffectExtent.NONE
    ModelResponseUncertainError  -- request sent, no reliable acknowledged
                                     response (timeout, dropped connection,
                                     truncated body): provider may or may not
                                     have processed it -> EffectExtent.UNKNOWN
    ModelResponseRejectedError   -- a complete response was received, but it
                                     is an explicit provider-declared error
                                     (e.g. model-missing) or fails this
                                     capability's own mandatory validation
                                     (wrong count/dimension/non-finite
                                     numbers): the provider did not produce a
                                     usable result -> EffectExtent.NONE

None of these is a generic `ProviderError` catch-all: each name states
exactly what is and is not known about the attempted effect, so the
composition layer maps it explicitly rather than inferring from "an
exception occurred" (Gate-2's own documented anti-pattern, now genuinely
relevant for the first time).

This module imports only Kernel: SS9.2's I-row foreign-target maximum (K, C,
M, A, G, R, O, X) does not include E (Execution) -- current authority,
dispatch, and Coordinator attribution are composed *around* a `ModelPort`
call by an outer permitted consumer, never imported into this Port itself.
"""

from typing import Protocol

from legoai.intelligence.model.routing import ModelRequirement, ModelRouteDecision
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ModelFailure,
)
from legoai.kernel.context import TenantContext


class _ModelError(Exception):
    def __init__(
        self,
        message: str = "",
        *,
        failure: ModelFailure = ModelFailure.PROVIDER_EXECUTION_FAILURE,
    ) -> None:
        super().__init__(message)
        if type(failure) is not ModelFailure:
            raise TypeError("model failure must be typed")
        self.failure = failure


class ModelPreflightError(_ModelError):
    """No request left this process; no possible provider-side effect
    occurred. Maps to `EffectExtent.NONE` at the composition boundary."""


class ModelResponseUncertainError(_ModelError):
    """A request was sent but no reliable response was received (timeout,
    dropped connection, truncated body). Whether the provider processed it
    is genuinely unknown. Maps to `EffectExtent.UNKNOWN` -- never `NONE`,
    never silently retried inside the same claimed invocation."""


class ModelResponseRejectedError(_ModelError):
    """A complete response was received, but it is an explicit
    provider-declared error or fails this capability's own mandatory
    response validation. The provider did not produce a usable result.
    Maps to `EffectExtent.NONE`."""


class ModelResponseRetryableRejectedError(ModelResponseRejectedError):
    """Complete temporary rejection: NONE / POTENTIALLY_RETRYABLE.

    No usable result; never initiates automatic retry or fallback.
    """


class ModelPort(Protocol):
    """Provider-neutral Model interaction. Both operations are async
    (network-shaped effects, per ADR-015's structured-supervision model);
    neither performs authorization, dispatch, or Catalog lookup itself --
    those remain the calling Coordinator/composition's responsibility,
    exactly as `DispatchArbiterPort` never invokes a capability and
    `ExecutionCoordinator.invoke_governed` never decides *which*
    implementation to call.
    """

    async def chat(self, request: ChatRequest) -> ChatResult: ...

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...


class ModelRouterPort(Protocol):
    """Pure Chat configuration selection, separate from ModelPort invocation.

    Exact logical profile matching returns all candidates in configuration order:
    zero means NO_MATCH, one RESOLVED, more AMBIGUOUS. No default or fallback.
    Implementations validate explicit tenant scope and pin configuration identity.
    Routing performs no I/O, authority decision, dispatch or model call. Invalid
    types/configuration raise TypeError/ValueError; normal misses are results.
    """

    def route(
        self, requirement: ModelRequirement, tenant_context: TenantContext
    ) -> ModelRouteDecision: ...
