"""DocuMind CLI composition root -- the first real application to wire
LegoAI's governed runtime end to end.

This module constructs the Catalog, the Ollama Plugin admission/
activation/publication, the deterministic authorization/dispatch/
coordination stack, and exposes two governed async callables
(`governed_embed`, `governed_chat`) matching `legoai_document`'s own
`GovernedEmbed`/`GovernedChat` injection points -- `legoai_document` never
sees `ExecutionCoordinator`, `Catalog`, or `ModelPort` directly (ADR-002's
Internal-vs-Public distinction).

**Security model (task SS58, single-operator local example):** one fixed
local principal ("documind-cli") holds a single, non-expiring-in-practice
Grant per published capability (chat, embedding), scoped to this process's
one configured tenant. No Approval, no Policy supersession -- an
intentionally minimal, explicitly local-trusted-host security posture
(never claimed as production-grade; see the release-readiness known-
limitations list). Every governed call still passes through real
authorization/dispatch/Coordinator machinery -- this composition narrows
*who* is authorized, not *whether* authorization/dispatch runs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from legoai.capabilities.ports import CatalogEntry
from legoai.capabilities.values import (
    CapabilityId,
    CapabilityRequirement,
    CapabilityVersionRange,
)
from legoai.execution.ports import CoordinationOutcome, CoordinationRequest
from legoai.execution.values import (
    ExecutionContext,
    ExecutionId,
    ExecutionResult,
    SecurityContextRef,
)
from legoai.governance.ports import SecurityContext
from legoai.governance.values import Grant, GrantId, PolicyRef, Principal
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ProviderId,
)
from legoai.kernel.context import TenantContext
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
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.evidence import InMemoryEvidenceCustody
from legoai.reference.execution import (
    DeterministicDispatchArbiter,
    ExecutionCoordinator,
    StaticSecurityContextRegistry,
)
from legoai.reference.governance import (
    DeterministicAuthorizationEvaluator,
    InMemoryApprovalRegistry,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
)
from legoai.reference.model import (
    OllamaModelAdapter,
    OllamaModelConfig,
    ollama_chat_capability_id,
    ollama_declaration,
    ollama_embedding_capability_id,
)
from legoai.reference.plugins import activate, admit, initialize, inspect, validate
from legoai.reference.resolution import ResolutionStatus, resolve
from legoai.runtime._composition.model_governed import (
    invoke_governed_chat,
    invoke_governed_embedding,
)

from documind_app.config import DocuMindConfig

_ISSUER = "documind-cli"
_APPLICATION_ID = ApplicationId("documind")
_PROVIDER_ID = ProviderId("ollama-local")
_POLICY_REF = PolicyRef(_ISSUER, "documind-local-policy", Version(1, 0, 0))


class GovernedInvocationError(RuntimeError):
    """Raised when a governed capability invocation cannot complete --
    denial, dispatch rejection, or a Model provider failure. Carries a
    human-readable message only; the underlying `ErrorCategory` (when
    available) is appended for `--debug` diagnostics."""


class DocuMindRuntime:
    """One process-lifetime governed runtime instance. Constructing this
    performs Plugin admission/activation/Catalog publication (all inert,
    no network I/O) -- it does not itself contact Ollama."""

    def __init__(self, config: DocuMindConfig) -> None:
        self.config = config
        self._tenant_context = TenantContext(TenantId(config.tenant_id))
        self._principal = Principal(PrincipalRef(_ISSUER, PrincipalId("documind-cli")))

        grant_state = InMemoryGrantRegistry()
        approval_use = InMemoryApprovalRegistry()
        policy_currency = InMemoryPolicyRegistry()
        authorization = DeterministicAuthorizationEvaluator(
            grant_state, approval_use, policy_currency
        )
        self._catalog = InMemoryCatalog()
        evidence = InMemoryEvidenceCustody()
        arbiter = DeterministicDispatchArbiter(
            authorization, self._catalog, evidence, approval_use
        )
        self._security_contexts = StaticSecurityContextRegistry()
        self._coordinator = ExecutionCoordinator(
            self._security_contexts, arbiter, clock=lambda: datetime.now(UTC)
        )

        established_at = datetime.now(UTC)
        declaration = ollama_declaration()
        discovered = inspect(declaration)
        validation = validate(discovered, declaration, evaluated_at=established_at)
        record = admit(
            validation,
            self._tenant_context,
            PluginAdmissionId(f"admission-{uuid.uuid4()}"),
            established_at=established_at,
        )
        active_record = activate(
            initialize(record, established_at=established_at),
            established_at=established_at,
        )
        self._chat_entry = self._catalog.publish(
            active_record,
            declaration,
            declaration.offers[0],
            established_at=established_at,
        )
        self._embedding_entry = self._catalog.publish(
            active_record,
            declaration,
            declaration.offers[1],
            established_at=established_at,
        )

        adapter_config = OllamaModelConfig(
            config.base_url,
            config.chat_model,
            config.embedding_model,
            config.timeout_seconds,
        )
        self._adapter = OllamaModelAdapter(adapter_config, provider_id=_PROVIDER_ID)

        self._grant_ids = {
            ollama_chat_capability_id(): GrantId(f"grant-chat-{uuid.uuid4()}"),
            ollama_embedding_capability_id(): GrantId(f"grant-embed-{uuid.uuid4()}"),
        }

    def _resolve(self, capability_id: CapabilityId) -> CatalogEntry:
        requirement = CapabilityRequirement(
            capability_id, CapabilityVersionRange(Version(1, 0, 0))
        )
        resolution = resolve(
            requirement,
            self._catalog.snapshot(self._tenant_context),
            resolved_at=datetime.now(UTC),
        )
        if resolution.status is not ResolutionStatus.RESOLVED:
            raise GovernedInvocationError(
                f"capability {capability_id.value!r} is not currently resolvable "
                f"({resolution.status.name})"
            )
        return resolution.candidates[0]

    def _prepare(
        self, capability_id: CapabilityId
    ) -> tuple[CatalogEntry, ExecutionContext]:
        entry = self._resolve(capability_id)
        now = datetime.now(UTC)

        scope = ReferenceScope(_ISSUER, self._tenant_context.tenant_id)
        target = ConfigurationRef(
            ApplicationRef(scope, _APPLICATION_ID), "runtime-config"
        )
        operation = OperationRef(
            target, OperationId(f"op-{uuid.uuid4()}"), "invocation"
        )

        grant = Grant(
            self._grant_ids[capability_id],
            self._principal,
            self._principal,
            self._tenant_context,
            "invoke-capability",
            capability_id.value,
            False,
            now - timedelta(seconds=1),
            now + timedelta(hours=1),
        )
        security_context = SecurityContext(
            self._principal,
            self._tenant_context,
            operation,
            "invoke-capability",
            capability_id.value,
            grant,
            None,
            _POLICY_REF,
            now,
        )

        execution_id = ExecutionId(f"exec-{uuid.uuid4()}")
        security_context_ref = SecurityContextRef(_ISSUER, execution_id.value)
        self._security_contexts.register(security_context_ref, security_context)

        execution_context = ExecutionContext(
            execution_id,
            operation,
            self._tenant_context,
            security_context_ref,
            CorrelationId(f"corr-{uuid.uuid4()}"),
            None,
            None,
            None,
        )
        return entry, execution_context

    async def governed_chat(self, request: ChatRequest) -> ChatResult:
        entry, execution_context = self._prepare(ollama_chat_capability_id())
        coordination = await self._coordinator.coordinate(
            CoordinationRequest(execution_context, entry)
        )
        if coordination.outcome is not CoordinationOutcome.READY:
            raise GovernedInvocationError(
                "governed chat invocation was not authorized for dispatch "
                f"({coordination.outcome.name})"
            )
        execution_result, chat_result = await invoke_governed_chat(
            self._coordinator, coordination, request, self._adapter
        )
        if chat_result is None:
            raise GovernedInvocationError(
                f"chat invocation failed ({_error_category(execution_result)})"
            )
        return chat_result

    async def governed_embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        entry, execution_context = self._prepare(ollama_embedding_capability_id())
        coordination = await self._coordinator.coordinate(
            CoordinationRequest(execution_context, entry)
        )
        if coordination.outcome is not CoordinationOutcome.READY:
            raise GovernedInvocationError(
                "governed embedding invocation was not authorized for dispatch "
                f"({coordination.outcome.name})"
            )
        execution_result, embedding_result = await invoke_governed_embedding(
            self._coordinator, coordination, request, self._adapter
        )
        if embedding_result is None:
            raise GovernedInvocationError(
                f"embedding invocation failed ({_error_category(execution_result)})"
            )
        return embedding_result

    def published_capabilities(self) -> tuple[str, str]:
        return (
            self._chat_entry.offer.capability.value,
            self._embedding_entry.offer.capability.value,
        )


def _error_category(execution_result: ExecutionResult) -> str:
    if execution_result.error is None:
        return "unknown"
    return execution_result.error.category.name
