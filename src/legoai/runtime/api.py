"""ADR-014 public local-host contract: types and a Protocol, never a factory.

Applications import this module, owner values/Ports, and (from their
composition root only) `legoai.runtime.local.open_local_host`. Nothing here
imports a reference realization or private composition wiring (ADR-002 §12).

Configuration values are trusted operator input. They are validated on
construction; semantic invalidity raises the closed `HostError`, while wrong
Python types raise `TypeError`. A `TrustedModelContribution` is composition-root
code, never data: nothing in this module parses, imports or loads code.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Protocol

from legoai.capabilities.values import CapabilityId
from legoai.execution.agent.ports import AgentRuntimePort
from legoai.execution.values import ExecutionContext, ExecutionResult, ExecutionState
from legoai.governance.disclosure import (
    DisclosureAdmission,
    DisclosureDeclaration,
    ProcessorDeclaration,
)
from legoai.governance.ports import AuthorizationPort, SecurityContext
from legoai.governance.secret import SecretRef
from legoai.governance.values import GrantId, PolicyRef
from legoai.intelligence.model.ports import ModelPort
from legoai.intelligence.model.routing import ModelRequirement
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ModelFailure,
    ModelId,
    ProviderId,
)
from legoai.kernel.identity import CorrelationId
from legoai.kernel.references import (
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    PrincipalRef,
)
from legoai.plugins.values import PluginId


class HostFailure(Enum):
    """Closed ADR-014 failure vocabulary; ADR-019 names reused where they exist."""

    # Open-time.
    INVALID_CONFIGURATION = "invalid_configuration"
    STALE_CONFIGURATION = "stale_configuration"
    UNKNOWN_BINDING = "unknown_binding"
    CONTRIBUTION_CONFLICT = "contribution_conflict"
    UNAVAILABLE_PROVIDER = "unavailable_provider"
    INCOMPATIBLE_PROVIDER = "incompatible_provider"
    INVALID_GRANT = "invalid_grant"
    UNSUPPORTED_COMPOSITION = "unsupported_composition"
    MISSING_DEPENDENCY = "missing_dependency"
    INITIALIZATION_FAILURE = "initialization_failure"
    # Use-time, always before registration, dispatch or provider work.
    GRANT_NOT_CONFIGURED = "grant_not_configured"
    SUBJECT_OUT_OF_SCOPE = "subject_out_of_scope"
    PURPOSE_UNAVAILABLE = "purpose_unavailable"
    FOREIGN_CONTEXT = "foreign_context"
    CAPACITY_EXHAUSTED = "capacity_exhausted"
    WRONG_EVENT_LOOP = "wrong_event_loop"


class HostError(Exception):
    """Safe category only; any chained cause is a restricted diagnostic."""

    def __init__(self, failure: HostFailure) -> None:
        if type(failure) is not HostFailure:
            raise TypeError("host error requires HostFailure")
        self.failure = failure
        super().__init__(failure.value)


class ModelPurpose(Enum):
    """The closed set of currently proven purposes (ADR-014 §3.5).

    Each maps to exactly one existing provider-neutral v1 capability. This is
    not a purpose-extension mechanism; application data cannot add members.
    """

    CHAT = "chat"
    EMBEDDING = "embedding"

    @property
    def capability_id(self) -> CapabilityId:
        if self is ModelPurpose.CHAT:
            return CapabilityId("legoai.intelligence.model.chat")
        return CapabilityId("legoai.intelligence.model.embedding")


class ModelDeployment(Enum):
    """Operator declaration of processing location, never inferred from a URL."""

    LOCAL = "local"
    REMOTE = "remote"


def _text(value: object, failure: HostFailure) -> None:
    if type(value) is not str:
        raise TypeError("host configuration text must be str")
    if (
        not 1 <= len(value) <= 256
        or value.isspace()
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise HostError(failure)


def _aware(value: object) -> bool:
    if type(value) is not datetime:
        raise TypeError("host configuration time must be datetime")
    return value.tzinfo is not None and value.utcoffset() is not None


@dataclass(frozen=True, slots=True)
class OperatorGrant:
    """Operator-declared bounded authority; the host issues the actual Grant."""

    grant_id: GrantId
    action: str = field(repr=False)
    resource_scope: str = field(repr=False)
    not_before: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if type(self.grant_id) is not GrantId:
            raise TypeError("operator grant requires GrantId")
        _text(self.action, HostFailure.INVALID_GRANT)
        _text(self.resource_scope, HostFailure.INVALID_GRANT)
        if not _aware(self.not_before) or not _aware(self.expires_at):
            raise HostError(HostFailure.INVALID_GRANT)
        if self.expires_at <= self.not_before:
            raise HostError(HostFailure.INVALID_GRANT)


@dataclass(frozen=True, slots=True)
class OllamaSettings:
    """Closed built-in provider settings (credential-free local Ollama).

    Full URL/model validation happens when the host opens, using the existing
    adapter configuration rules; failures become INVALID_CONFIGURATION.
    """

    base_url: str = field(repr=False)
    chat_model: str
    embedding_model: str
    timeout_seconds: float
    provider_id: ProviderId

    def __post_init__(self) -> None:
        for value in (self.base_url, self.chat_model, self.embedding_model):
            if type(value) is not str:
                raise TypeError("Ollama settings require text")
        if type(self.timeout_seconds) not in (int, float):
            raise TypeError("Ollama settings require a numeric timeout")
        if type(self.provider_id) is not ProviderId:
            raise TypeError("Ollama settings require ProviderId")


@dataclass(frozen=True, slots=True)
class OpenAICompatibleSettings:
    """OpenAI-compatible endpoint; base_url includes the API version prefix.

    Full URL/model/bound validation happens at host open. `bearer_credential`
    (ADR-014 §14.18) is a governed reference only, never material. Absent, the
    binding is credential-free. Present, it is admissible only for
    `deployment=REMOTE` over https under ADR-023 SRCP-1, with the remote
    disclosure configuration and `RemoteModelRuntime` participants; every
    other REMOTE or credentialed configuration is refused at open.
    """

    base_url: str = field(repr=False)
    chat_model: str
    embedding_model: str | None
    timeout_seconds: float
    max_output_tokens: int | None
    provider_id: ProviderId
    deployment: ModelDeployment
    bearer_credential: SecretRef | None = field(default=None, repr=False)

    deterministic: bool = False

    def __post_init__(self) -> None:
        if type(self.deterministic) is not bool:
            raise TypeError("deterministic must be bool")
        if (
            self.bearer_credential is not None
            and type(self.bearer_credential) is not SecretRef
        ):
            raise TypeError("bearer_credential must be SecretRef or None")
        for value in (self.base_url, self.chat_model):
            if type(value) is not str:
                raise TypeError("OpenAI-compatible settings require text")
        if self.embedding_model is not None and type(self.embedding_model) is not str:
            raise TypeError("embedding model must be text or None")
        if type(self.timeout_seconds) not in (int, float):
            raise TypeError("settings require a numeric timeout")
        if (
            self.max_output_tokens is not None
            and type(self.max_output_tokens) is not int
        ):
            raise TypeError("max_output_tokens must be an exact int or None")
        if type(self.provider_id) is not ProviderId:
            raise TypeError("settings require ProviderId")
        if type(self.deployment) is not ModelDeployment:
            raise TypeError("settings require ModelDeployment")


@dataclass(frozen=True, slots=True)
class TrustedModelContribution:
    """Trusted composition-root code supplying a `ModelPort` (ADR-014 §3.6).

    Never deserialized, never produced from task/model data, never handed to
    domain logic. Constructors must be bounded local construction; the host
    calls the selected one exactly once when it opens and does not supervise it.
    """

    plugin_id: PluginId
    provider_id: ProviderId
    model_id: ModelId
    purposes: frozenset[ModelPurpose]
    construct: Callable[[], ModelPort] = field(repr=False, compare=False)
    # ADR-022: the operator declares that this ModelPort honors
    # ChatRequest.response_format. It is a capability fact, never authority.
    structured_output: bool = False

    def __post_init__(self) -> None:
        if type(self.plugin_id) is not PluginId:
            raise TypeError("contribution requires PluginId")
        if type(self.provider_id) is not ProviderId:
            raise TypeError("contribution requires ProviderId")
        if type(self.model_id) is not ModelId:
            raise TypeError("contribution requires ModelId")
        if type(self.purposes) is not frozenset or any(
            type(purpose) is not ModelPurpose for purpose in self.purposes
        ):
            raise TypeError("contribution purposes require frozenset[ModelPurpose]")
        if not self.purposes:
            raise HostError(HostFailure.INVALID_CONFIGURATION)
        if not callable(self.construct):
            raise TypeError("contribution requires an operator-supplied constructor")
        if type(self.structured_output) is not bool:
            raise TypeError("structured_output must be bool")


@dataclass(frozen=True, slots=True)
class ModelBindingConfig:
    """One selectable candidate; ADR-019 selection data names it by binding_id."""

    binding_id: str = field(repr=False)
    requirement: ModelRequirement
    provider: OllamaSettings | OpenAICompatibleSettings | TrustedModelContribution

    def __post_init__(self) -> None:
        _text(self.binding_id, HostFailure.INVALID_CONFIGURATION)
        if type(self.requirement) is not ModelRequirement:
            raise TypeError("binding requires ModelRequirement")
        if type(self.provider) not in (
            OllamaSettings,
            OpenAICompatibleSettings,
            TrustedModelContribution,
        ):
            raise TypeError("binding requires a supported provider contribution")


@dataclass(frozen=True, slots=True)
class RemoteDisclosureConfig:
    """Operator remote-disclosure configuration (ADR-024 §5–6).

    Processor declarations and disclosure admissions, validated for
    consistency when the host opens and evaluated at every REMOTE invocation.
    Configuring them authorizes no request. A REMOTE binding opens only as
    the credentialed OpenAI-compatible SRCP-1 profile with this configuration
    admitting it and `RemoteModelRuntime` participants supplied.
    """

    declarations: tuple[ProcessorDeclaration, ...]
    admissions: tuple[DisclosureAdmission, ...]

    def __post_init__(self) -> None:
        if type(self.declarations) is not tuple or any(
            type(item) is not ProcessorDeclaration for item in self.declarations
        ):
            raise TypeError("disclosure requires tuple[ProcessorDeclaration, ...]")
        if type(self.admissions) is not tuple or any(
            type(item) is not DisclosureAdmission for item in self.admissions
        ):
            raise TypeError("disclosure requires tuple[DisclosureAdmission, ...]")
        # Bounds: 1–16 declarations and 1–16 admissions when configured.
        if not 1 <= len(self.declarations) <= 16 or not 1 <= len(self.admissions) <= 16:
            raise HostError(HostFailure.INVALID_CONFIGURATION)
        # One current revision per declaration and per admission identity, and
        # at most one admission per binding: evaluation never has to choose.
        declared = [item.declaration_id for item in self.declarations]
        admitted = [item.admission_id for item in self.admissions]
        bound = [b for item in self.admissions for b in item.bindings]
        if (
            len(set(declared)) != len(declared)
            or len(set(admitted)) != len(admitted)
            or len(set(bound)) != len(bound)
        ):
            raise HostError(HostFailure.CONTRIBUTION_CONFLICT)


class CredentialSource(Protocol):
    """Operator credential source (ADR-023 §8, SECRET-SOURCE-S1).

    Material enters only as hidden interactive input read by the source
    itself, bound to the REMOTE Model credential purpose; callers receive a
    `SecretRef` and never the material. Each provisioning is a new immutable
    revision that retires the previous one for that identity. Nothing is
    persisted: a new process provisions again.
    """

    def provision(self, identity: str) -> SecretRef: ...

    def retire(self, credential: SecretRef) -> None: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class RemoteModelRuntime:
    """Trusted runtime participants of one credentialed REMOTE binding (SRCP-1).

    Not operator data and not serializable configuration: the host's own
    credential source, the local directory for owner-local durable custody
    (remote attempts and Secret-use attribution), the SRCP-1 validity margin,
    and an optional explicit trust anchor that replaces (never extends or
    disables) the system trust store. Supplying them authorizes no request.
    """

    credentials: CredentialSource = field(repr=False, compare=False)
    custody: Path = field(repr=False)
    validity_margin: timedelta
    trust_anchor: Path | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.custody, Path):
            raise TypeError("remote custody requires a directory Path")
        if self.trust_anchor is not None and not isinstance(self.trust_anchor, Path):
            raise TypeError("trust anchor must be a Path or None")
        if type(self.validity_margin) is not timedelta:
            raise TypeError("validity margin must be timedelta")
        # Bounds: a positive margin of at most one hour (the per-use window
        # is at most one day; ADR-023 §7.4 leaves the value to the operator).
        if not timedelta(0) < self.validity_margin <= timedelta(hours=1):
            raise HostError(HostFailure.INVALID_CONFIGURATION)


@dataclass(frozen=True, slots=True)
class LocalHostConfig:
    """Trusted operator configuration for one local governed host.

    `configuration` pins the revision and is the sole source of tenant and
    application scope. `max_executions` is a reference-host lifetime control,
    not a measured scalability limit. `disclosure` is optional operator
    remote-disclosure configuration (ADR-024); absent, behavior is unchanged.
    """

    configuration: ConfigurationRevisionRef
    principal: PrincipalRef
    policy: PolicyRef
    grants: tuple[OperatorGrant, ...]
    bindings: tuple[ModelBindingConfig, ...]
    max_executions: int
    disclosure: RemoteDisclosureConfig | None = None

    def __post_init__(self) -> None:
        if type(self.configuration) is not ConfigurationRevisionRef:
            raise TypeError("host configuration requires ConfigurationRevisionRef")
        if type(self.principal) is not PrincipalRef:
            raise TypeError("host configuration requires PrincipalRef")
        if type(self.policy) is not PolicyRef:
            raise TypeError("host configuration requires PolicyRef")
        if type(self.grants) is not tuple or any(
            type(grant) is not OperatorGrant for grant in self.grants
        ):
            raise TypeError("host grants require tuple[OperatorGrant, ...]")
        if type(self.bindings) is not tuple or any(
            type(binding) is not ModelBindingConfig for binding in self.bindings
        ):
            raise TypeError("host bindings require tuple[ModelBindingConfig, ...]")
        if type(self.max_executions) is not int:
            raise TypeError("max_executions must be an exact int")
        # Bounds: 1–64 grants, 1–16 bindings, 1–100,000 lifetime executions.
        if not 1 <= len(self.grants) <= 64:
            raise HostError(HostFailure.INVALID_CONFIGURATION)
        if not 1 <= len(self.bindings) <= 16:
            raise HostError(HostFailure.INVALID_CONFIGURATION)
        if not 1 <= self.max_executions <= 100_000:
            raise HostError(HostFailure.INVALID_CONFIGURATION)
        grant_ids = {grant.grant_id for grant in self.grants}
        pairs = {(grant.action, grant.resource_scope) for grant in self.grants}
        binding_ids = {binding.binding_id for binding in self.bindings}
        if (
            len(grant_ids) != len(self.grants)
            or len(pairs) != len(self.grants)
            or len(binding_ids) != len(self.bindings)
        ):
            raise HostError(HostFailure.CONTRIBUTION_CONFLICT)
        if (
            self.disclosure is not None
            and type(self.disclosure) is not RemoteDisclosureConfig
        ):
            raise TypeError("disclosure must be RemoteDisclosureConfig or None")


@dataclass(frozen=True, slots=True)
class ExecutionDisclosure:
    """Trusted ADR-024 declaration for one minted model execution.

    Supplied only by the composition that assembles the request, from
    provenance it knows; never from model output, content or responses. Bound
    to exactly one execution at minting and immutable thereafter: different
    classes need a different execution. Ignored for LOCAL bindings; a REMOTE
    invocation without one is UNCLASSIFIED and refused.
    """

    consumer: str = field(repr=False)
    declaration: DisclosureDeclaration

    def __post_init__(self) -> None:
        _text(self.consumer, HostFailure.INVALID_CONFIGURATION)
        if type(self.declaration) is not DisclosureDeclaration:
            raise TypeError("execution disclosure requires DisclosureDeclaration")


@dataclass(frozen=True, slots=True)
class GovernedChatResult:
    """Existing governed Chat outcome; response present iff SUCCEEDED."""

    execution: ExecutionResult
    response: ChatResult | None = field(repr=False)

    failure: ModelFailure | None = None

    def __post_init__(self) -> None:
        if type(self.execution) is not ExecutionResult:
            raise TypeError("governed chat result requires ExecutionResult")
        if self.response is not None and type(self.response) is not ChatResult:
            raise TypeError("governed chat response must be ChatResult or None")
        if self.failure is not None and type(self.failure) is not ModelFailure:
            raise TypeError("failure must be ModelFailure")
        success = self.execution.final_state is ExecutionState.SUCCEEDED
        if success and self.failure is not None:
            raise ValueError("successful chat has no failure")
        if success != (self.response is not None):
            raise ValueError("governed chat response must correspond to success")


@dataclass(frozen=True, slots=True)
class GovernedEmbeddingResult:
    """Existing governed embedding outcome; response present iff SUCCEEDED."""

    execution: ExecutionResult
    response: EmbeddingResult | None = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.execution) is not ExecutionResult:
            raise TypeError("governed embedding result requires ExecutionResult")
        if self.response is not None and type(self.response) is not EmbeddingResult:
            raise TypeError("governed embedding response must be EmbeddingResult")
        success = self.execution.final_state is ExecutionState.SUCCEEDED
        if success != (self.response is not None):
            raise ValueError("governed embedding response must correspond to success")


class GovernedHost(Protocol):
    """Public local governed host (ADR-014 §3.2). Returns public contracts only.

    Confined to the thread that opened it and to the event loop of its first
    async use (reference-host limitation, not a domain contract).
    """

    @property
    def authorization(self) -> AuthorizationPort: ...

    def model_execution(
        self,
        purpose: ModelPurpose,
        *,
        deadline: datetime | None = None,
        correlation: CorrelationId | None = None,
        causation: OperationRef | None = None,
        disclosure: ExecutionDisclosure | None = None,
    ) -> ExecutionContext: ...

    def security_context(
        self, subject: ConfigurationRef, action: str, resource_scope: str
    ) -> SecurityContext: ...

    def agent_runtime(self) -> AgentRuntimePort: ...

    async def governed_chat(
        self, context: ExecutionContext, request: ChatRequest
    ) -> GovernedChatResult: ...

    async def governed_embed(
        self, context: ExecutionContext, request: EmbeddingRequest
    ) -> GovernedEmbeddingResult: ...
