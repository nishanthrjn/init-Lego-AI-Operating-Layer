"""DocuMind CLI composition root over LegoAI's public local governed host.

This module translates `DocuMindConfig` into validated ADR-014 operator
configuration and opens one `GovernedHost` (`legoai.runtime.local`). It then
exposes two governed async callables (`governed_embed`, `governed_chat`)
matching `legoai_document`'s `GovernedEmbed`/`GovernedChat` injection points.
Neither DocuMind nor `legoai_document` sees the Catalog, Coordinator,
registries, reference realizations or a provider adapter.

**Security model (single-operator local example):** one fixed local principal
("documind-cli") holds one bounded operator grant per Model purpose (chat,
embedding), scoped to this process's configured tenant. The grants are
declared here, at the composition boundary, as operator configuration; the
host issues the actual Grant values. No Approval or Policy supersession: an
intentionally minimal, explicitly local-trusted-host posture, never claimed
as production-grade. Every call still passes through real authorization,
dispatch and Coordinator machinery.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from legoai.execution.values import ExecutionResult, ExecutionState
from legoai.governance.values import GrantId, PolicyRef
from legoai.intelligence.model.routing import ModelRequirement
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ProviderId,
)
from legoai.kernel.identity import ApplicationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.runtime.api import (
    HostError,
    LocalHostConfig,
    ModelBindingConfig,
    ModelPurpose,
    OllamaSettings,
    OperatorGrant,
)
from legoai.runtime.local import open_local_host

from documind_app.config import DocuMindConfig

_ISSUER = "documind-cli"
_APPLICATION_ID = ApplicationId("documind")
_PROVIDER_ID = ProviderId("ollama-local")
_POLICY_REF = PolicyRef(_ISSUER, "documind-local-policy", Version(1, 0, 0))
_REVISION = "documind-runtime-1"
_BINDING = "ollama-local"
_PROFILE = ModelRequirement("documind-answering")
# Operator bounds for one CLI process: grant lifetime and lifetime execution
# capacity. These are reference-host controls, not measured scalability limits.
_GRANT_LIFETIME = timedelta(hours=24)
_MAX_EXECUTIONS = 100_000


class GovernedInvocationError(RuntimeError):
    """Raised when a governed capability invocation cannot complete --
    denial, dispatch rejection, host refusal, or a Model provider failure.
    Carries a human-readable message only; the underlying category (when
    available) is appended for `--debug` diagnostics."""


def _host_config(config: DocuMindConfig, now: datetime) -> LocalHostConfig:
    target = ConfigurationRef(
        ApplicationRef(
            ReferenceScope(_ISSUER, TenantId(config.tenant_id)), _APPLICATION_ID
        ),
        "runtime-config",
    )
    grants = tuple(
        OperatorGrant(
            GrantId(f"documind-{purpose.value}"),
            "invoke-capability",
            purpose.capability_id.value,
            now - timedelta(seconds=1),
            now + _GRANT_LIFETIME,
        )
        for purpose in ModelPurpose
    )
    binding = ModelBindingConfig(
        _BINDING,
        _PROFILE,
        OllamaSettings(
            config.base_url,
            config.chat_model,
            config.embedding_model,
            config.timeout_seconds,
            _PROVIDER_ID,
        ),
    )
    return LocalHostConfig(
        ConfigurationRevisionRef(target, _REVISION, Version(1, 0, 0)),
        PrincipalRef(_ISSUER, PrincipalId("documind-cli")),
        _POLICY_REF,
        grants,
        (binding,),
        _MAX_EXECUTIONS,
    )


def _category(execution: ExecutionResult) -> str:
    if execution.error is None:
        return "unknown"
    return execution.error.category.name


class DocuMindRuntime:
    """One process-lifetime governed runtime. Constructing it opens the public
    local host (inert Plugin admission and Catalog publication) -- it does not
    itself contact Ollama."""

    def __init__(self, config: DocuMindConfig) -> None:
        self.config = config
        try:
            self._host = open_local_host(
                _host_config(config, datetime.now(UTC)),
                {"revision": _REVISION, "binding": _BINDING},
            )
        except HostError as error:
            raise GovernedInvocationError(
                f"governed runtime could not be composed ({error.failure.name})"
            ) from error

    async def governed_chat(self, request: ChatRequest) -> ChatResult:
        try:
            context = self._host.model_execution(ModelPurpose.CHAT)
            result = await self._host.governed_chat(context, request)
        except HostError as error:
            raise GovernedInvocationError(
                f"governed chat invocation was refused ({error.failure.name})"
            ) from error
        if result.execution.final_state is ExecutionState.REJECTED:
            raise GovernedInvocationError(
                "governed chat invocation was not authorized for dispatch (REJECTED)"
            )
        if result.response is None:
            raise GovernedInvocationError(
                f"chat invocation failed ({_category(result.execution)})"
            )
        return result.response

    async def governed_embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        try:
            context = self._host.model_execution(ModelPurpose.EMBEDDING)
            result = await self._host.governed_embed(context, request)
        except HostError as error:
            raise GovernedInvocationError(
                f"governed embedding invocation was refused ({error.failure.name})"
            ) from error
        if result.execution.final_state is ExecutionState.REJECTED:
            raise GovernedInvocationError(
                "governed embedding invocation was not authorized for dispatch "
                "(REJECTED)"
            )
        if result.response is None:
            raise GovernedInvocationError(
                f"embedding invocation failed ({_category(result.execution)})"
            )
        return result.response

    def published_capabilities(self) -> tuple[str, str]:
        return (
            ModelPurpose.CHAT.capability_id.value,
            ModelPurpose.EMBEDDING.capability_id.value,
        )
