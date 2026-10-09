"""ADR-014: the one public composition module permitted to use internals.

`open_local_host` composes the existing reference owners (Catalog, Plugin
lifecycle, authorization, dispatch arbiter, Coordinator), ADR-019 model
selection and the M7 Agent runtime, and returns only the public `GovernedHost`
contract. No reference or private-composition type appears in a public
signature, and nothing here adds authorization, dispatch or effect semantics.

Opening performs no provider call. Only the selected binding is admitted,
published and constructed (its constructor exactly once); unselected bindings
are validated as configuration only. There is no global state: each call
returns an independent host.
"""

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from legoai.capabilities.ports import CatalogEntry
from legoai.capabilities.values import (
    CapabilityOffer,
    CapabilityRequirement,
    CapabilityVersionRange,
)
from legoai.execution.agent.ports import AgentChatResult, AgentRuntimePort
from legoai.execution.ports import CoordinationOutcome, CoordinationRequest
from legoai.execution.values import (
    ExecutionContext,
    ExecutionId,
    ExecutionResult,
    SecurityContextRef,
)
from legoai.governance.disclosure import endpoint_parts
from legoai.governance.ports import AuthorizationPort, SecurityContext
from legoai.governance.values import Grant, Principal
from legoai.intelligence.model.ports import ModelPort
from legoai.intelligence.model.routing import ModelBinding, ModelRouteDecision
from legoai.intelligence.model.values import ChatRequest, EmbeddingRequest, ModelId
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorDetail, Recoverability
from legoai.kernel.identity import CorrelationId, OperationId
from legoai.kernel.references import ConfigurationRef, OperationRef
from legoai.plugins.ports import PluginAdmissionId
from legoai.plugins.values import PluginDeclaration
from legoai.reference.agent import OneStepAgentRuntime
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.evidence import InMemoryEvidenceCustody
from legoai.reference.execution import (
    DeterministicDispatchArbiter,
    ExecutionCoordinator,
    current_thread_ident,
    running_event_loop,
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
    ollama_declaration,
)
from legoai.reference.model_capabilities import (
    model_capability_version,
    model_chat_offer,
    model_embedding_offer,
)
from legoai.reference.model_openai_compatible import (
    OpenAICompatibleModelAdapter,
    OpenAICompatibleModelConfig,
    openai_compatible_declaration,
)
from legoai.reference.model_routing import DeterministicModelRouter
from legoai.reference.plugins import activate, admit, initialize, inspect, validate
from legoai.reference.resolution import resolve
from legoai.runtime._composition.agent import GovernedAgentChat
from legoai.runtime._composition.disclosure import (
    DisclosureCheck,
    RemoteDisclosureGate,
)
from legoai.runtime._composition.model_governed import invoke_routed_embedding
from legoai.runtime._composition.model_selection import (
    CompositionFailure,
    ModelCompositionError,
    ModelContribution,
    capture_model_selection,
    compose_model,
)
from legoai.runtime.api import (
    ExecutionDisclosure,
    GovernedChatResult,
    GovernedEmbeddingResult,
    GovernedHost,
    HostError,
    HostFailure,
    LocalHostConfig,
    ModelBindingConfig,
    ModelDeployment,
    ModelPurpose,
    OllamaSettings,
    OpenAICompatibleSettings,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _composition_failure(failure: CompositionFailure) -> HostFailure:
    match failure:
        case CompositionFailure.INVALID_CONFIGURATION:
            return HostFailure.INVALID_CONFIGURATION
        case CompositionFailure.UNKNOWN_BINDING:
            return HostFailure.UNKNOWN_BINDING
        case CompositionFailure.STALE_CONFIGURATION:
            return HostFailure.STALE_CONFIGURATION
        case CompositionFailure.UNAVAILABLE_PROVIDER:
            return HostFailure.UNAVAILABLE_PROVIDER
        case CompositionFailure.INCOMPATIBLE_PROVIDER:
            return HostFailure.INCOMPATIBLE_PROVIDER
        case CompositionFailure.MISSING_DEPENDENCY:
            return HostFailure.MISSING_DEPENDENCY
        case CompositionFailure.INITIALIZATION_FAILURE:
            return HostFailure.INITIALIZATION_FAILURE
        case _:
            # INACTIVE_PLUGIN / ACTIVATION_MISMATCH: the host activates its own
            # contribution, so either means the composition itself is unsupported.
            return HostFailure.UNSUPPORTED_COMPOSITION


def _validate_disclosure(config: LocalHostConfig) -> None:
    """ADR-024 configuration consistency only; it admits and enables nothing.

    Every admission must pin an existing exact declaration revision and name
    only existing REMOTE-declared OpenAI-compatible bindings whose provider,
    https endpoint and models match. REMOTE stays refused by `_realization`.
    """
    disclosure = config.disclosure
    if disclosure is None:
        return
    bindings = {binding.binding_id: binding for binding in config.bindings}
    declarations = {d.declaration_id: d for d in disclosure.declarations}
    purposes = {purpose.value for purpose in ModelPurpose}
    for admission in disclosure.admissions:
        declaration = declarations.get(admission.declaration_id)
        if (
            declaration is None
            or declaration.revision != admission.declaration_revision
            or declaration.provider_id != admission.provider_id
            or declaration.endpoint_origin != admission.endpoint_origin
            or declaration.api_root != admission.api_root
            or not admission.purposes <= purposes
        ):
            raise HostError(HostFailure.INVALID_CONFIGURATION)
        for binding_id in admission.bindings:
            binding = bindings.get(binding_id)
            if binding is None:
                raise HostError(HostFailure.INVALID_CONFIGURATION)
            provider = binding.provider
            if (
                not isinstance(provider, OpenAICompatibleSettings)
                or provider.deployment is not ModelDeployment.REMOTE
                or provider.provider_id.value != admission.provider_id
                or endpoint_parts(provider.base_url)
                != (admission.endpoint_origin, admission.api_root)
            ):
                raise HostError(HostFailure.INVALID_CONFIGURATION)
            served = {provider.chat_model, provider.embedding_model} - {None}
            if not admission.models <= served or (
                ModelPurpose.EMBEDDING.value in admission.purposes
                and provider.embedding_model is None
            ):
                raise HostError(HostFailure.INVALID_CONFIGURATION)


def _offer(purpose: ModelPurpose) -> CapabilityOffer:
    return (
        model_chat_offer() if purpose is ModelPurpose.CHAT else model_embedding_offer()
    )


def _requirement(offer: CapabilityOffer) -> CapabilityRequirement:
    return CapabilityRequirement(
        offer.capability, CapabilityVersionRange(offer.version)
    )


def _realization(
    selected: ModelBindingConfig,
) -> tuple[
    ModelBinding, PluginDeclaration, frozenset[ModelPurpose], Callable[[], ModelPort]
]:
    provider = selected.provider
    try:
        # ModelBindingConfig already enforced the exact closed provider types.
        if isinstance(provider, OllamaSettings):
            settings = OllamaModelConfig(
                provider.base_url,
                provider.chat_model,
                provider.embedding_model,
                provider.timeout_seconds,
            )
            provider_id = provider.provider_id
            binding = ModelBinding(
                selected.binding_id,
                selected.requirement,
                ModelId(provider.chat_model),
                provider_id,
                structured_output=True,  # the Ollama adapter maps ADR-022
            )

            def construct() -> ModelPort:
                return OllamaModelAdapter(settings, provider_id)

            return binding, ollama_declaration(), frozenset(ModelPurpose), construct
        if isinstance(provider, OpenAICompatibleSettings):
            if provider.deployment is ModelDeployment.REMOTE:
                raise HostError(HostFailure.UNSUPPORTED_COMPOSITION)
            openai_settings = OpenAICompatibleModelConfig(
                provider.base_url,
                provider.chat_model,
                provider.embedding_model,
                provider.timeout_seconds,
                provider.max_output_tokens,
            )
            openai_provider_id = provider.provider_id
            binding = ModelBinding(
                selected.binding_id,
                selected.requirement,
                ModelId(provider.chat_model),
                openai_provider_id,
            )
            purposes = frozenset({ModelPurpose.CHAT})
            if provider.embedding_model is not None:
                purposes = frozenset(ModelPurpose)

            def construct_openai() -> ModelPort:
                return OpenAICompatibleModelAdapter(openai_settings, openai_provider_id)

            return (
                binding,
                openai_compatible_declaration(
                    embedding=provider.embedding_model is not None
                ),
                purposes,
                construct_openai,
            )
        binding = ModelBinding(
            selected.binding_id,
            selected.requirement,
            provider.model_id,
            provider.provider_id,
            structured_output=provider.structured_output,
        )
        declaration = PluginDeclaration(
            provider.plugin_id,
            model_capability_version(),
            tuple(_offer(p) for p in ModelPurpose if p in provider.purposes),
        )
        return binding, declaration, provider.purposes, provider.construct
    except (TypeError, ValueError) as error:
        raise HostError(HostFailure.INVALID_CONFIGURATION) from error


class _HostSecurityContexts:
    """Host-private `SecurityContextResolutionPort`.

    Registration never overwrites. Resolution re-stamps `established_at` with the
    host clock, so grant validity is evaluated at dispatch time (current
    authorization), matching the engineering authorized readers' discipline.
    """

    def __init__(self, clock: Callable[[], datetime]) -> None:
        self._clock = clock
        self._contexts: dict[tuple[str, str], SecurityContext] = {}

    def register(self, ref: SecurityContextRef, context: SecurityContext) -> None:
        key = (ref.issuer, ref.reference)
        if key in self._contexts:
            raise ValueError("security context reference already registered")
        self._contexts[key] = context

    async def resolve(
        self, ref: SecurityContextRef, tenant_context: TenantContext
    ) -> SecurityContext | None:
        context = self._contexts.get((ref.issuer, ref.reference))
        if context is None or context.tenant_context != tenant_context:
            return None
        return replace(context, established_at=self._clock())


class _HostAgentChat:
    """`AgentChatPort` guard: confinement and context ownership, then delegate."""

    def __init__(self, host: _LocalGovernedHost, chat: GovernedAgentChat) -> None:
        self._host = host
        self._chat = chat

    async def invoke(
        self, context: ExecutionContext, route: ModelRouteDecision, request: ChatRequest
    ) -> AgentChatResult:
        self._host._enter_async()
        disclosure = self._host._require(context, ModelPurpose.CHAT)
        check = self._host._check(context, ModelPurpose.CHAT, disclosure)
        return await self._chat.invoke(context, route, request, check)


class _LocalGovernedHost:
    """Single-operator reference realization of `GovernedHost`."""

    def __init__(
        self,
        *,
        config: LocalHostConfig,
        tenant: TenantContext,
        principal: Principal,
        grants: dict[tuple[str, str], Grant],
        purposes: frozenset[ModelPurpose],
        clock: Callable[[], datetime],
        contexts: _HostSecurityContexts,
        coordinator: ExecutionCoordinator,
        authorization: AuthorizationPort,
        chat: GovernedAgentChat,
        route: ModelRouteDecision,
        embedding_entry: CatalogEntry | None,
        adapter: ModelPort,
    ) -> None:
        self._config = config
        self._subject = config.configuration.configuration
        self._tenant = tenant
        self._principal = principal
        self._grants = grants
        self._purposes = purposes
        self._clock = clock
        self._contexts = contexts
        self._coordinator = coordinator
        self._authorization = authorization
        self._chat = chat
        self._route = route
        self._embedding_entry = embedding_entry
        self._adapter = adapter
        # ADR-024 carrier: each minted execution's trusted declaration lives
        # here, bound to its exact ExecutionId and context, never mutated.
        self._minted: dict[
            ExecutionId,
            tuple[ModelPurpose, ExecutionContext, ExecutionDisclosure | None],
        ] = {}
        # The REMOTE disclosure gate. None while REMOTE bindings are refused
        # at open: LOCAL invocations never consult disclosure policy.
        self._gate: RemoteDisclosureGate | None = None
        self._thread = current_thread_ident()
        self._loop: object | None = None
        assert route.selected is not None
        self._agent_runtime = OneStepAgentRuntime(
            DeterministicModelRouter(config.configuration, (route.selected,)),
            _HostAgentChat(self, chat),
        )

    @property
    def authorization(self) -> AuthorizationPort:
        return self._authorization

    def _require_thread(self) -> None:
        if current_thread_ident() != self._thread:
            raise HostError(HostFailure.WRONG_EVENT_LOOP)

    def _enter_async(self) -> None:
        self._require_thread()
        loop = running_event_loop()
        if self._loop is None:
            self._loop = loop
        elif self._loop is not loop:
            raise HostError(HostFailure.WRONG_EVENT_LOOP)

    def _require(
        self, context: ExecutionContext, purpose: ModelPurpose
    ) -> ExecutionDisclosure | None:
        if type(context) is not ExecutionContext:
            raise TypeError("host invocation requires ExecutionContext")
        minted = self._minted.get(context.execution_id)
        if minted is None or minted[:2] != (purpose, context):
            raise HostError(HostFailure.FOREIGN_CONTEXT)
        return minted[2]

    def _check(
        self,
        context: ExecutionContext,
        purpose: ModelPurpose,
        disclosure: ExecutionDisclosure | None,
    ) -> DisclosureCheck | None:
        """Bind the REMOTE gate to this exact execution's own declaration."""
        if self._gate is None:
            return None
        return DisclosureCheck(
            self._gate,
            context,
            purpose.value,
            disclosure.consumer if disclosure is not None else None,
            disclosure.declaration if disclosure is not None else None,
        )

    def _security(self, operation: OperationRef, grant: Grant) -> SecurityContext:
        return SecurityContext(
            self._principal,
            self._tenant,
            operation,
            grant.action,
            grant.resource_scope,
            grant,
            None,
            self._config.policy,
            self._clock(),
        )

    def model_execution(
        self,
        purpose: ModelPurpose,
        *,
        deadline: datetime | None = None,
        correlation: CorrelationId | None = None,
        causation: OperationRef | None = None,
        disclosure: ExecutionDisclosure | None = None,
    ) -> ExecutionContext:
        self._require_thread()
        if type(purpose) is not ModelPurpose:
            raise TypeError("model execution requires ModelPurpose")
        if correlation is not None and type(correlation) is not CorrelationId:
            raise TypeError("correlation must be CorrelationId or None")
        if disclosure is not None and type(disclosure) is not ExecutionDisclosure:
            raise TypeError("disclosure must be ExecutionDisclosure or None")
        if purpose not in self._purposes:
            raise HostError(HostFailure.PURPOSE_UNAVAILABLE)
        grant = self._grants.get(("invoke-capability", purpose.capability_id.value))
        if grant is None:
            raise HostError(HostFailure.GRANT_NOT_CONFIGURED)
        if len(self._minted) >= self._config.max_executions:
            raise HostError(HostFailure.CAPACITY_EXHAUSTED)
        token = uuid4().hex
        operation = OperationRef(
            self._subject, OperationId(f"model-{token}"), f"model-{purpose.value}"
        )
        # Validation (deadline, causation tenant) precedes registration, so a
        # rejected request consumes no capacity and registers nothing.
        context = ExecutionContext(
            ExecutionId(f"exec-{token}"),
            operation,
            self._tenant,
            SecurityContextRef("legoai.runtime.local", token),
            correlation if correlation is not None else CorrelationId(f"corr-{token}"),
            None,
            deadline,
            causation,
        )
        self._contexts.register(
            context.security_context_ref, self._security(operation, grant)
        )
        self._minted[context.execution_id] = (purpose, context, disclosure)
        return context

    def security_context(
        self, subject: ConfigurationRef, action: str, resource_scope: str
    ) -> SecurityContext:
        self._require_thread()
        if type(subject) is not ConfigurationRef:
            raise TypeError("security context requires ConfigurationRef subject")
        if type(action) is not str or type(resource_scope) is not str:
            raise TypeError("security context requires text action and scope")
        if subject.application != self._subject.application:
            raise HostError(HostFailure.SUBJECT_OUT_OF_SCOPE)
        grant = self._grants.get((action, resource_scope))
        if grant is None:
            raise HostError(HostFailure.GRANT_NOT_CONFIGURED)
        operation = OperationRef(
            subject, OperationId(f"authority-{uuid4().hex}"), action
        )
        return self._security(operation, grant)

    def agent_runtime(self) -> AgentRuntimePort:
        self._require_thread()
        return self._agent_runtime

    async def governed_chat(
        self, context: ExecutionContext, request: ChatRequest
    ) -> GovernedChatResult:
        self._enter_async()
        if type(request) is not ChatRequest:
            raise TypeError("governed chat requires ChatRequest")
        disclosure = self._require(context, ModelPurpose.CHAT)
        check = self._check(context, ModelPurpose.CHAT, disclosure)
        outcome = await self._chat.invoke(context, self._route, request, check)
        return GovernedChatResult(outcome.execution, outcome.response)

    async def governed_embed(
        self, context: ExecutionContext, request: EmbeddingRequest
    ) -> GovernedEmbeddingResult:
        self._enter_async()
        if type(request) is not EmbeddingRequest:
            raise TypeError("governed embedding requires EmbeddingRequest")
        disclosure = self._require(context, ModelPurpose.EMBEDDING)
        check = self._check(context, ModelPurpose.EMBEDDING, disclosure)
        entry = self._embedding_entry
        assert entry is not None  # EMBEDDING contexts are minted only when published
        coordination = await self._coordinator.coordinate(
            CoordinationRequest(context, entry)
        )
        if coordination.outcome is not CoordinationOutcome.READY:
            error = None
            if coordination.category is not None:
                error = ErrorDetail(coordination.category, Recoverability.TERMINAL, ())
            execution = ExecutionResult(
                coordination.execution_id, coordination.state, EffectExtent.NONE, error
            )
            return GovernedEmbeddingResult(execution, None)
        result, response = await invoke_routed_embedding(
            self._coordinator,
            coordination,
            request,
            entry,
            self._adapter,
            self._config.configuration,
            check,
        )
        return GovernedEmbeddingResult(result, response)


def open_local_host(
    config: LocalHostConfig,
    model_selection: Mapping[str, object],
    *,
    clock: Callable[[], datetime] = _utc_now,
) -> GovernedHost:
    """Open one independent local governed host (ADR-014 §3.4).

    Raises `HostError` with a closed category on any open-time failure; no
    partially usable host is ever returned. Wrong Python types raise TypeError.
    """
    if type(config) is not LocalHostConfig:
        raise TypeError("open_local_host requires LocalHostConfig")
    if not isinstance(model_selection, Mapping):
        raise TypeError("model selection must be a mapping")
    if not callable(clock):
        raise TypeError("clock must be callable")
    now = clock()
    if type(now) is not datetime or now.utcoffset() is None:
        raise TypeError("clock must return a timezone-aware datetime")
    _validate_disclosure(config)
    try:
        desired = capture_model_selection(
            model_selection, pinned_revision=config.configuration
        )
    except ModelCompositionError as error:
        raise HostError(_composition_failure(error.failure)) from error
    selected = next(
        (b for b in config.bindings if b.binding_id == desired.binding_id), None
    )
    if selected is None:
        raise HostError(HostFailure.UNKNOWN_BINDING)
    binding, declaration, purposes, construct = _realization(selected)
    if ModelPurpose.CHAT not in purposes:
        # ADR-019 composition is anchored on the v1 Chat offer.
        raise HostError(HostFailure.UNSUPPORTED_COMPOSITION)

    configuration = config.configuration
    tenant = TenantContext(configuration.configuration.application.scope.tenant_id)
    principal = Principal(config.principal)
    try:
        grants = {
            (grant.action, grant.resource_scope): Grant(
                grant.grant_id,
                principal,
                principal,
                tenant,
                grant.action,
                grant.resource_scope,
                False,
                grant.not_before,
                grant.expires_at,
            )
            for grant in config.grants
        }
    except (TypeError, ValueError) as error:
        raise HostError(HostFailure.INVALID_GRANT) from error

    offers = declaration.offers
    catalog = InMemoryCatalog()
    try:
        record = admit(
            validate(inspect(declaration), declaration, evaluated_at=now),
            tenant,
            PluginAdmissionId(f"host-{uuid4().hex}"),
            established_at=now,
        )
        activation = activate(
            initialize(record, established_at=now), established_at=now
        )
        entries = {
            offer: catalog.publish(activation, declaration, offer, established_at=now)
            for offer in offers
        }
    except (TypeError, ValueError) as error:
        raise HostError(HostFailure.UNSUPPORTED_COMPOSITION) from error

    chat_offer = model_chat_offer()
    try:
        composed = compose_model(
            _requirement(chat_offer),
            desired,
            catalog=catalog,
            contributions=(
                ModelContribution(
                    configuration, binding, entries[chat_offer], activation, construct
                ),
            ),
            resolved_at=now,
        )
    except ModelCompositionError as error:
        raise HostError(_composition_failure(error.failure)) from error

    embedding_entry = entries.get(model_embedding_offer())
    if embedding_entry is not None:
        resolution = resolve(
            _requirement(model_embedding_offer()),
            catalog.snapshot(tenant),
            resolved_at=now,
        )
        if embedding_entry not in resolution.candidates:
            raise HostError(HostFailure.INCOMPATIBLE_PROVIDER)

    approvals = InMemoryApprovalRegistry()
    authorization = DeterministicAuthorizationEvaluator(
        InMemoryGrantRegistry(), approvals, InMemoryPolicyRegistry()
    )
    arbiter = DeterministicDispatchArbiter(
        authorization, catalog, InMemoryEvidenceCustody(), approvals
    )
    contexts = _HostSecurityContexts(clock)
    coordinator = ExecutionCoordinator(contexts, arbiter, clock=clock)
    return _LocalGovernedHost(
        config=config,
        tenant=tenant,
        principal=principal,
        grants=grants,
        purposes=purposes,
        clock=clock,
        contexts=contexts,
        coordinator=coordinator,
        authorization=authorization,
        chat=GovernedAgentChat(coordinator, composed.configured),
        route=composed.route,
        embedding_entry=embedding_entry,
        adapter=composed.configured.adapter,
    )
