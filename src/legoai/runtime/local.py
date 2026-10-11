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

ADR-026 adds `open_governed_execution` for shared controls only. It constructs
no provider or owner adapter; owner invocation stays outside its concrete facade.

OPENAI-COMPATIBLE-REMOTE-1: the one supported REMOTE profile is a credentialed
OpenAI-compatible binding under ADR-023 SRCP-1 and ADR-024: admitted by the
remote-disclosure configuration, https only, a `bearer_credential` issued by
this host's own credential source, a configured Secret-use Grant and the
trusted `RemoteModelRuntime` participants. Every other REMOTE configuration is
refused at open, before admission or construction. Opening such a host reads
local trust configuration and opens owner-local SQLite custody only.
"""

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from legoai.capabilities.ports import CatalogEntry
from legoai.capabilities.values import (
    CapabilityId,
    CapabilityOffer,
    CapabilityRequirement,
    CapabilityVersionRange,
)
from legoai.execution.agent.ports import AgentChatResult, AgentRuntimePort
from legoai.execution.ports import (
    CoordinationOutcome,
    CoordinationRequest,
    CoordinationResult,
    ExecutionTransitionError,
)
from legoai.execution.values import (
    ExecutionContext,
    ExecutionId,
    ExecutionResult,
    ExecutionState,
    SecurityContextRef,
)
from legoai.governance.disclosure import endpoint_parts
from legoai.governance.ports import AuthorizationPort, SecurityContext
from legoai.governance.secret import SecretRef
from legoai.governance.values import Grant, Principal
from legoai.intelligence.model.ports import ModelPort, ModelPreflightError
from legoai.intelligence.model.routing import ModelBinding, ModelRouteDecision
from legoai.intelligence.model.values import (
    ChatRequest,
    EmbeddingRequest,
    ModelFailure,
    ModelId,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, ErrorDetail, Recoverability
from legoai.kernel.identity import CorrelationId, OperationId
from legoai.kernel.references import (
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    ReferenceScope,
)
from legoai.plugins.ports import PluginAdmissionId
from legoai.plugins.values import PluginDeclaration
from legoai.reference._secret_domain import _OrderingDomain
from legoai.reference.agent import OneStepAgentRuntime
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.evidence import InMemoryEvidenceCustody
from legoai.reference.execution import (
    DeterministicDispatchArbiter,
    ExecutionCoordinator,
    _BoundExecutionSupervisor,
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
    openai_compatible_plugin_id,
    openai_compatible_release,
)
from legoai.reference.model_routing import DeterministicModelRouter
from legoai.reference.plugins import activate, admit, initialize, inspect, validate
from legoai.reference.resolution import resolve
from legoai.reference.secret import _provisioned_class, _ProvisionedSecretSource
from legoai.runtime._composition.agent import GovernedAgentChat
from legoai.runtime._composition.disclosure import (
    DisclosureCheck,
    RemoteDisclosureGate,
    RemoteEndpointFacts,
)
from legoai.runtime._composition.model_governed import invoke_routed_embedding
from legoai.runtime._composition.model_selection import (
    CompositionFailure,
    ModelCompositionError,
    ModelContribution,
    capture_model_selection,
    compose_model,
)
from legoai.runtime._composition.remote_model import (
    CredentialAssociation,
    RemoteModelPlane,
    compose_remote_plane,
    credential_consumer,
    credential_consumer_version,
    credential_purpose,
)
from legoai.runtime._composition.secret import _provision_interactively
from legoai.runtime.api import (
    CredentialSource,
    ExecutionDisclosure,
    GovernedChatResult,
    GovernedEmbeddingResult,
    GovernedExecutionConfig,
    GovernedHost,
    HostError,
    HostFailure,
    LocalHostConfig,
    ModelBindingConfig,
    ModelDeployment,
    ModelPurpose,
    OllamaSettings,
    OpenAICompatibleSettings,
    OperatorGrant,
    RemoteModelRuntime,
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


class _CredentialSource:
    """`CredentialSource` realization: SECRET-SOURCE-S1 bound to the REMOTE
    Model credential purpose and consumer. Owns the ordering domain that the
    hosts using its revisions join (ADR-023 §15 gate 4)."""

    def __init__(self, scope: ReferenceScope) -> None:
        self._source = _ProvisionedSecretSource(_OrderingDomain(), scope)

    def __repr__(self) -> str:
        return "CredentialSource(<redacted>)"

    __str__ = __repr__

    def provision(self, identity: str) -> SecretRef:
        return _provision_interactively(
            self._source, identity, credential_purpose(), credential_consumer()
        )

    def retire(self, credential: SecretRef) -> None:
        if type(credential) is not SecretRef:
            raise TypeError("retire requires SecretRef")
        self._source.retire(credential.exact)

    def close(self) -> None:
        self._source.close()


def open_credential_source(scope: ReferenceScope) -> CredentialSource:
    """Open one process-local operator credential source (ADR-023 §8).

    Inert: nothing is read until the operator provisions a credential through
    hidden interactive input. No environment, file or argument source exists.
    """
    if type(scope) is not ReferenceScope:
        raise TypeError("credential source requires ReferenceScope")
    return _CredentialSource(scope)


def _remote_profile(
    config: LocalHostConfig,
    selected: ModelBindingConfig,
    remote: RemoteModelRuntime | None,
) -> OperatorGrant | None:
    """Admit the selected binding as the SRCP-1 REMOTE profile, or refuse.

    Returns the Secret-use grant for an admitted credentialed REMOTE binding,
    None for every non-REMOTE binding. Admission here authorizes no request:
    each invocation independently passes disclosure and Secret checks.
    """
    provider = selected.provider
    if not isinstance(provider, OpenAICompatibleSettings):
        return None
    credential = provider.bearer_credential
    if provider.deployment is ModelDeployment.LOCAL:
        if credential is not None:
            # ADR-014 §14.18 item 1: credentialed LOCAL stays unsupported.
            raise HostError(HostFailure.UNSUPPORTED_COMPOSITION)
        return None
    disclosure = config.disclosure
    admitted = disclosure is not None and any(
        selected.binding_id in admission.bindings for admission in disclosure.admissions
    )
    if (
        not admitted
        or credential is None
        or remote is None
        or type(remote.credentials) is not _CredentialSource
        or credential.secret_class != _provisioned_class()
    ):
        raise HostError(HostFailure.UNSUPPORTED_COMPOSITION)
    tenant = config.configuration.configuration.application.scope.tenant_id
    if (
        endpoint_parts(provider.base_url) is None
        or credential.exact.scope.tenant_id != tenant
        or credential.use_requirement != credential_purpose()
        or not remote.custody.is_dir()
        or (remote.trust_anchor is not None and not remote.trust_anchor.is_file())
    ):
        raise HostError(HostFailure.INVALID_CONFIGURATION)
    grant = next(
        (
            g
            for g in config.grants
            if g.action == "secret-use"
            and g.resource_scope == credential.exact.identity
        ),
        None,
    )
    if grant is None:
        raise HostError(HostFailure.INVALID_CONFIGURATION)
    # Safe eligibility metadata only; no material is realized at open.
    if not remote.credentials._source.status(credential.exact):
        raise HostError(HostFailure.STALE_CONFIGURATION)
    return grant


def _offer(purpose: ModelPurpose) -> CapabilityOffer:
    return (
        model_chat_offer() if purpose is ModelPurpose.CHAT else model_embedding_offer()
    )


def _requirement(offer: CapabilityOffer) -> CapabilityRequirement:
    return CapabilityRequirement(
        offer.capability, CapabilityVersionRange(offer.version)
    )


def _ungoverned(path: str, body: bytes) -> tuple[int, bytes]:
    """A REMOTE binding's adapter outside the governed plane sends nothing."""
    raise ModelPreflightError("REMOTE requires the governed invocation plane")


def _openai_config(provider: OpenAICompatibleSettings) -> OpenAICompatibleModelConfig:
    return OpenAICompatibleModelConfig(
        provider.base_url,
        provider.chat_model,
        provider.embedding_model,
        provider.timeout_seconds,
        provider.max_output_tokens,
        provider.deterministic,
    )


def _realization(
    selected: ModelBindingConfig, *, remote_admitted: bool = False
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
            remote = provider.deployment is ModelDeployment.REMOTE
            if remote and not remote_admitted:
                raise HostError(HostFailure.UNSUPPORTED_COMPOSITION)
            openai_settings = _openai_config(provider)
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
                if remote:
                    # Never local HTTP: only the governed plane supplies the
                    # one exchange of an admitted invocation.
                    return OpenAICompatibleModelAdapter(
                        openai_settings, openai_provider_id, exchange=_ungoverned
                    )
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


def _remote_chat_http_status(host: GovernedHost, execution: ExecutionId) -> int | None:
    """Private trusted inspection, not a GovernedHost/ModelPort contract.

    Ephemeral complete-response status only. No custody recovery or HTTP data
    is exposed. Foreign/local/incomplete executions have no observation.
    """
    if type(host) is not _LocalGovernedHost or type(execution) is not ExecutionId:
        raise TypeError("local host and exact execution identity required")
    host._require_thread()
    if execution not in host._minted or host._remote is None:
        return None
    return host._remote._chat_http_status(execution)


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
        gate: RemoteDisclosureGate | None = None,
        remote: RemoteModelPlane | None = None,
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
        # The REMOTE disclosure gate and invocation plane: both present only
        # for an admitted credentialed REMOTE binding. LOCAL invocations never
        # consult disclosure policy, Secret custody or the credential transport.
        if (gate is None) != (remote is None):
            raise ValueError("REMOTE requires both its gate and its plane")
        self._gate = gate
        self._remote = remote
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
        diagnostics: list[ModelFailure] = []
        outcome = await self._chat.invoke(
            context, self._route, request, check, diagnostics
        )
        return GovernedChatResult(
            outcome.execution, outcome.response, diagnostics[0] if diagnostics else None
        )

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
            self._remote,
        )
        return GovernedEmbeddingResult(result, response)


def open_local_host(
    config: LocalHostConfig,
    model_selection: Mapping[str, object],
    *,
    clock: Callable[[], datetime] = _utc_now,
    remote: RemoteModelRuntime | None = None,
) -> GovernedHost:
    """Open one independent local governed host (ADR-014 §3.4).

    Raises `HostError` with a closed category on any open-time failure; no
    partially usable host is ever returned. Wrong Python types raise TypeError.
    `remote` supplies the trusted participants of a credentialed REMOTE
    binding (OPENAI-COMPATIBLE-REMOTE-1); it is ignored for other bindings.
    """
    if type(config) is not LocalHostConfig:
        raise TypeError("open_local_host requires LocalHostConfig")
    if not isinstance(model_selection, Mapping):
        raise TypeError("model selection must be a mapping")
    if not callable(clock):
        raise TypeError("clock must be callable")
    if remote is not None and type(remote) is not RemoteModelRuntime:
        raise TypeError("remote must be RemoteModelRuntime or None")
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
    secret_grant = _remote_profile(config, selected, remote)
    binding, declaration, purposes, construct = _realization(
        selected, remote_admitted=secret_grant is not None
    )
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

    # A credentialed REMOTE host joins its credential source's ordering domain:
    # every local invalidator of a Secret use is ordered against the handoff.
    domain = None
    if secret_grant is not None:
        assert remote is not None and type(remote.credentials) is _CredentialSource
        domain = remote.credentials._source._domain
    grant_registry = InMemoryGrantRegistry(_domain=domain)
    policies = InMemoryPolicyRegistry(_domain=domain)
    approvals = InMemoryApprovalRegistry(_domain=domain)
    authorization = DeterministicAuthorizationEvaluator(
        grant_registry, approvals, policies
    )
    evidence = InMemoryEvidenceCustody()
    arbiter = DeterministicDispatchArbiter(authorization, catalog, evidence, approvals)
    contexts = _HostSecurityContexts(clock)
    coordinator = ExecutionCoordinator(contexts, arbiter, clock=clock)
    gate = plane = None
    if secret_grant is not None:
        assert remote is not None
        provider = selected.provider
        assert isinstance(provider, OpenAICompatibleSettings)
        credential = provider.bearer_credential
        disclosure = config.disclosure
        parts = endpoint_parts(provider.base_url)
        assert credential is not None and disclosure is not None and parts is not None
        gate = RemoteDisclosureGate(
            RemoteEndpointFacts(
                selected.binding_id,
                provider.provider_id.value,
                parts[0],
                parts[1],
                provider.chat_model,
                provider.embedding_model,
            ),
            disclosure.declarations,
            disclosure.admissions,
            evidence,
            principal,
            clock,
        )
        plane = _remote_plane(
            config,
            selected.binding_id,
            provider,
            credential,
            remote,
            grants[(secret_grant.action, secret_grant.resource_scope)],
            (grant_registry, policies, approvals),
            tenant,
            clock,
            now,
        )
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
        chat=GovernedAgentChat(coordinator, composed.configured, plane),
        route=composed.route,
        embedding_entry=embedding_entry,
        adapter=composed.configured.adapter,
        gate=gate,
        remote=plane,
    )


class GovernedExecution:
    """ADR-026 concrete bound control facade, not a provider/callback executor.

    Public methods use canonical owner contracts only. Context identity is a
    process-local lineage guard, not a hostile-code security boundary. Keep this
    handle in trusted invoking-plane code; model/task data cannot settle it.
    """

    def __init__(
        self,
        config: GovernedExecutionConfig,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if type(config) is not GovernedExecutionConfig:
            raise TypeError("governed execution requires GovernedExecutionConfig")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._config = config
        self._clock = clock
        now = self._now()
        self._thread = current_thread_ident()
        self._loop: object | None = None
        self._closed = False
        self._tenant = TenantContext(
            config.configuration.configuration.application.scope.tenant_id
        )
        self._principal = Principal(config.principal)
        self._grant = Grant(
            config.grant.grant_id,
            self._principal,
            self._principal,
            self._tenant,
            config.grant.action,
            config.grant.resource_scope,
            False,
            config.grant.not_before,
            config.grant.expires_at,
        )
        self._catalog = InMemoryCatalog()
        try:
            declaration = config.declaration
            record = admit(
                validate(inspect(declaration), declaration, evaluated_at=now),
                self._tenant,
                PluginAdmissionId(f"execution-{uuid4().hex}"),
                established_at=now,
            )
            active = activate(
                initialize(record, established_at=now), established_at=now
            )
            self._entry = self._catalog.publish(
                active, declaration, config.offer, established_at=now
            )
        except TypeError, ValueError:
            raise HostError(HostFailure.UNSUPPORTED_COMPOSITION) from None
        self._grants = InMemoryGrantRegistry()
        approvals = InMemoryApprovalRegistry()
        authorization = DeterministicAuthorizationEvaluator(
            self._grants, approvals, InMemoryPolicyRegistry()
        )
        arbiter = DeterministicDispatchArbiter(
            authorization, self._catalog, InMemoryEvidenceCustody(), approvals
        )
        self._contexts = _HostSecurityContexts(self._now)
        self._coordinator = ExecutionCoordinator(
            self._contexts, arbiter, clock=self._now
        )
        self._supervisor = _BoundExecutionSupervisor(
            self._coordinator,
            arbiter,
            self._now,
            config.preparation_timeout.total_seconds(),
            config.shutdown_timeout.total_seconds(),
        )
        self._minted: dict[ExecutionId, ExecutionContext] = {}
        self._attempted: set[ExecutionId] = set()
        self._ready: dict[ExecutionId, CoordinationResult] = {}
        self._claimed: set[ExecutionId] = set()
        self._settled: dict[ExecutionId, ExecutionResult] = {}

    def _now(self) -> datetime:
        now = self._clock()
        if type(now) is not datetime or now.utcoffset() is None:
            raise TypeError("clock must return a timezone-aware datetime")
        return now

    def _thread_check(self) -> None:
        if current_thread_ident() != self._thread:
            raise HostError(HostFailure.WRONG_EVENT_LOOP)

    def _enter(self) -> None:
        self._thread_check()
        loop = running_event_loop()
        if self._loop is None:
            self._loop = loop
        elif self._loop is not loop:
            raise HostError(HostFailure.WRONG_EVENT_LOOP)

    def _accepting(self) -> None:
        if self._closed:
            raise HostError(HostFailure.CLOSED)

    def _require(self, context: ExecutionContext) -> None:
        if type(context) is not ExecutionContext:
            raise TypeError("execution requires ExecutionContext")
        if self._minted.get(context.execution_id) is not context:
            raise HostError(HostFailure.FOREIGN_CONTEXT)

    def _security(self, context: ExecutionContext) -> SecurityContext:
        return SecurityContext(
            self._principal,
            self._tenant,
            context.operation,
            self._grant.action,
            self._grant.resource_scope,
            self._grant,
            None,
            self._config.policy,
            self._now(),
        )

    @property
    def configuration(self) -> ConfigurationRevisionRef:
        return self._config.configuration

    @property
    def contribution(self) -> CatalogEntry:
        return self._entry

    def establish(
        self,
        *,
        deadline: datetime | None = None,
        correlation: CorrelationId | None = None,
    ) -> ExecutionContext:
        """Mint a scoped context; callers may shorten, never extend its bound."""
        self._thread_check()
        self._accepting()
        now = self._now()
        maximum = now + self._config.execution_timeout
        if deadline is not None:
            if type(deadline) is not datetime or deadline.utcoffset() is None:
                raise TypeError("deadline must be timezone-aware datetime")
            if deadline > maximum:
                raise HostError(HostFailure.INVALID_CONFIGURATION)
        if correlation is not None and type(correlation) is not CorrelationId:
            raise TypeError("correlation requires CorrelationId")
        if len(self._minted) >= self._config.max_executions:
            raise HostError(HostFailure.CAPACITY_EXHAUSTED)
        token = uuid4().hex
        context = ExecutionContext(
            ExecutionId(f"exec-{token}"),
            OperationRef(
                self.configuration.configuration,
                OperationId(f"invoke-{token}"),
                "invoke-capability",
            ),
            self._tenant,
            SecurityContextRef("legoai.runtime.local", token),
            correlation if correlation is not None else CorrelationId(f"corr-{token}"),
            None,
            deadline if deadline is not None else maximum,
            None,
        )
        self._contexts.register(context.security_context_ref, self._security(context))
        self._minted[context.execution_id] = context
        return context

    async def coordinate(self, context: ExecutionContext) -> CoordinationResult:
        self._enter()
        self._accepting()
        self._require(context)
        identity = context.execution_id
        if identity in self._attempted:
            raise HostError(HostFailure.WRONG_EXECUTION_STATE)
        self._attempted.add(identity)
        result = await self._supervisor.coordinate(
            CoordinationRequest(context, self._entry)
        )
        if result.outcome is CoordinationOutcome.READY:
            self._ready[identity] = result
        return result

    async def claim(
        self,
        context: ExecutionContext,
        ready: CoordinationResult,
        *,
        configuration: ConfigurationRevisionRef,
        contribution: CatalogEntry,
    ) -> None:
        """Claim one owner attempt; never permission for a later protected send."""
        self._enter()
        self._accepting()
        self._require(context)
        if type(configuration) is not ConfigurationRevisionRef:
            raise TypeError("claim requires ConfigurationRevisionRef")
        if (
            type(contribution) is not CatalogEntry
            or type(ready) is not CoordinationResult
        ):
            raise TypeError("claim requires canonical contribution and coordination")
        if configuration != self.configuration:
            raise HostError(HostFailure.STALE_CONFIGURATION)
        if contribution != self._entry:
            raise HostError(HostFailure.UNKNOWN_BINDING)
        identity = context.execution_id
        if self._ready.get(identity) is not ready:
            raise HostError(HostFailure.FOREIGN_CONTEXT)
        if identity in self._claimed:
            raise HostError(HostFailure.DUPLICATE_CLAIM)
        try:
            category = await self._supervisor.claim(
                CoordinationRequest(context, self._entry), self._security(context)
            )
        except ExecutionTransitionError:
            raise HostError(HostFailure.WRONG_EXECUTION_STATE) from None
        if category is not None:
            if category is ErrorCategory.DEADLINE_EXCEEDED:
                failure = HostFailure.DEADLINE_EXCEEDED
            elif category is ErrorCategory.CONFLICT:
                failure = HostFailure.UNKNOWN_BINDING
            else:
                failure = HostFailure.UNAUTHORIZED
            raise HostError(failure)
        self._claimed.add(identity)

    async def settle(
        self, context: ExecutionContext, observed: ExecutionResult
    ) -> ExecutionResult:
        """Record trusted owner facts, including UNKNOWN; allowed after close."""
        self._enter()
        self._require(context)
        if type(observed) is not ExecutionResult:
            raise TypeError("settlement requires ExecutionResult")
        identity = context.execution_id
        if observed.execution_id != identity:
            raise HostError(HostFailure.FOREIGN_CONTEXT)
        if (
            identity not in self._claimed
            or identity in self._settled
            or observed.final_state is ExecutionState.REJECTED
        ):
            raise HostError(HostFailure.WRONG_EXECUTION_STATE)
        try:
            result = await self._coordinator.settle(
                self._ready[identity],
                final_state=observed.final_state,
                effect=observed.effect,
                error=observed.error,
            )
        except ExecutionTransitionError:
            raise HostError(HostFailure.WRONG_EXECUTION_STATE) from None
        self._settled[identity] = result
        return result

    def revoke_authority(self) -> None:
        """Operator invalidator for the sole bound grant; no grant issuance API."""
        self._thread_check()
        self._grants.revoke(self._grant.grant_id)

    def retire_contribution(self) -> None:
        """Operator invalidator; no replacement, refresh or reselection."""
        self._thread_check()
        entry = self._entry
        self._catalog.withdraw(
            entry.plugin_id, entry.release, entry.offer, entry.tenant_context
        )

    async def close(self) -> tuple[ExecutionId, ...]:
        """Bounded preparation shutdown, reporting unresolved control obligations.

        No owner operation is supervised by this facade. Report ready/unsettled
        and still-preparing executions without inferring cessation or effects.
        Keep lineage/claim history, permitting late owner settlement and re-close.
        """
        self._enter()
        self._closed = True
        pending = await self._supervisor.close()
        unresolved = set(pending) | (self._ready.keys() - self._settled.keys())
        return tuple(sorted(unresolved, key=lambda identity: identity.value))


def open_governed_execution(
    config: GovernedExecutionConfig,
    *,
    clock: Callable[[], datetime] = _utc_now,
) -> GovernedExecution:
    """Explicit trusted local admission; inert with respect to all owner I/O."""
    return GovernedExecution(config, clock=clock)


def _remote_plane(
    config: LocalHostConfig,
    binding_id: str,
    provider: OpenAICompatibleSettings,
    credential: SecretRef,
    remote: RemoteModelRuntime,
    grant: Grant,
    registries: tuple[
        InMemoryGrantRegistry, InMemoryPolicyRegistry, InMemoryApprovalRegistry
    ],
    tenant: TenantContext,
    clock: Callable[[], datetime],
    now: datetime,
) -> RemoteModelPlane:
    """Compose the REMOTE invocation plane. Local resources only, no provider
    I/O: the protected consumer's Catalog entry, owner-local custody and the
    credential association this binding is configured with."""
    parts = endpoint_parts(provider.base_url)
    assert parts is not None
    source = remote.credentials
    assert type(source) is _CredentialSource
    offer = CapabilityOffer(
        CapabilityId(credential_consumer()), credential_consumer_version()
    )
    declaration = PluginDeclaration(
        openai_compatible_plugin_id(), openai_compatible_release(), (offer,)
    )
    catalog = InMemoryCatalog(_domain=source._source._domain)
    settings = _openai_config(provider)
    provider_id = provider.provider_id

    def adapter(exchange: Callable[[str, bytes], tuple[int, bytes]]) -> ModelPort:
        return OpenAICompatibleModelAdapter(settings, provider_id, exchange=exchange)

    try:
        record = admit(
            validate(inspect(declaration), declaration, evaluated_at=now),
            tenant,
            PluginAdmissionId(f"secret-consumer-{uuid4().hex}"),
            established_at=now,
        )
        entry = catalog.publish(
            activate(initialize(record, established_at=now), established_at=now),
            declaration,
            offer,
            established_at=now,
        )
        return compose_remote_plane(
            association=CredentialAssociation(
                credential, binding_id, provider_id.value, parts[0], parts[1]
            ),
            source=source._source,
            custody=remote.custody,
            trust_anchor=remote.trust_anchor,
            margin=remote.validity_margin,
            timeout=float(provider.timeout_seconds),
            clock=clock,
            configuration=config.configuration,
            principal=Principal(config.principal),
            grant=grant,
            policy=config.policy,
            registries=registries,
            consumer=(catalog, entry),
            adapter=adapter,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise HostError(HostFailure.INITIALIZATION_FAILURE) from error
