"""PROVIDER-MODEL-DISCOVERY-1: one governed credentialed model-catalog query.

An operator/provider-setup operation (ADR-024 §22), not a Model invocation:
it is outside ModelPort, every request type, disclosure policy and every
application. It discloses no model-visible content. In order:

    ProviderDiscoveryAdmission evaluated now -> credential purpose check ->
    exact `/models` target -> durable INTENDED ProviderControlAttempt ->
    a new exact Secret use (purpose provider-model-discovery, use id =
    attempt id) and current Secret authority -> T2: verified TLS, one
    claim, final currentness with the SRCP-1 margin, `POST {root}/models`
    with an empty body -> settlement -> bounded model-list parsing.

Exactly one request at most; no retry or fallback. The returned ids are an
observation of what was advertised at that moment. They change no binding,
admission, Catalog or route. The raw response is neither kept nor logged.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from secrets import token_hex
from ssl import SSLContext

from legoai.execution.values import ExecutionId
from legoai.governance.provider_control import (
    DiscoveryRefusal,
    ProviderDiscoveryAdmission,
    ProviderOperation,
    evaluate_discovery,
)
from legoai.governance.secret import SecretRef
from legoai.governance.values import Grant, PolicyRef, Principal
from legoai.intelligence.model.ports import ModelResponseRejectedError
from legoai.intelligence.model.values import ModelId, ProviderId
from legoai.kernel.identity import OperationId
from legoai.kernel.references import ConfigurationRevisionRef, OperationRef
from legoai.reference._credential_https import HttpsTarget, TransportError
from legoai.reference._remote_attempts import (
    AttemptObservation,
    AttemptState,
    ProviderControlAttempt,
    RemoteAttemptId,
    _RemoteAttemptStore,
)
from legoai.reference.model_openai_compatible import parse_model_list
from legoai.runtime._composition.credential_https import exchange
from legoai.runtime._composition.remote_model import (
    exact_use_request,
    record_fault,
)
from legoai.runtime._composition.secret import _SecretUses


def discovery_purpose() -> str:
    """The Secret-use purpose of a model-catalog query; never chat/embedding."""
    return "provider-model-discovery"


def discovery_consumer() -> str:
    """The protected consumer an S1 revision must be provisioned for."""
    return "legoai.provider.model-discovery"


def _path() -> str:
    """The one fixed provider-control path; never caller-supplied."""
    return "/models"


class DiscoveryOutcome(Enum):
    """One closed result category per discovery call."""

    REFUSED = "refused"  # before custody: no attempt, Secret use or network
    NOT_SENT = "not_sent"
    UNKNOWN = "unknown"
    PROVIDER_REJECTED = "provider_rejected"
    MALFORMED = "malformed"  # complete 2xx outside the model-list contract
    LISTED = "listed"


@dataclass(frozen=True, slots=True)
class ModelDiscovery:
    """Safe result: categories, identities and advertised model ids only."""

    outcome: DiscoveryOutcome
    refusal: DiscoveryRefusal | None = None
    attempt_id: RemoteAttemptId | None = None
    state: AttemptState | None = None
    status: int | None = None
    models: tuple[ModelId, ...] = field(default=(), repr=False)


@dataclass(frozen=True, slots=True)
class DiscoveryEndpoint:
    """Trusted operator facts: the exact recipient and its credential."""

    provider_id: str = field(repr=False)
    endpoint_origin: str = field(repr=False)
    api_root: str = field(repr=False)
    credential: SecretRef = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.credential) is not SecretRef:
            raise TypeError("discovery endpoint requires SecretRef")


def discover_remote_models(
    admission: ProviderDiscoveryAdmission | None,
    endpoint: DiscoveryEndpoint,
    *,
    consumer: str,
    attempts: _RemoteAttemptStore,
    uses: _SecretUses,
    configuration: ConfigurationRevisionRef,
    principal: Principal,
    grant: Grant,
    policy: PolicyRef,
    tls: SSLContext,
    timeout: float,
    margin: timedelta,
    clock: Callable[[], datetime],
) -> ModelDiscovery:
    """Retrieve one provider's advertised model ids under exact authority."""
    if type(endpoint) is not DiscoveryEndpoint:
        raise TypeError("trusted discovery endpoint required")
    if type(attempts) is not _RemoteAttemptStore or type(uses) is not _SecretUses:
        raise TypeError("qualified custody participants required")
    credential = endpoint.credential
    now = clock()
    refusal = evaluate_discovery(
        admission,
        provider_id=endpoint.provider_id,
        endpoint_origin=endpoint.endpoint_origin,
        api_root=endpoint.api_root,
        operation=ProviderOperation.MODEL_DISCOVERY,
        consumer=consumer,
        credential=credential.exact,
        at=now,
    )
    if refusal is None and credential.use_requirement != discovery_purpose():
        refusal = DiscoveryRefusal.CREDENTIAL_MISMATCH
    if refusal is not None:
        return ModelDiscovery(DiscoveryOutcome.REFUSED, refusal)
    assert admission is not None
    try:
        target = HttpsTarget.for_endpoint(
            endpoint.endpoint_origin, endpoint.api_root, _path()
        )
    except TransportError:
        return ModelDiscovery(
            DiscoveryOutcome.REFUSED, DiscoveryRefusal.ENDPOINT_MISMATCH
        )
    token = token_hex(16)
    operation = OperationId(f"provider-control-{token}")
    attempt = ProviderControlAttempt(
        RemoteAttemptId(f"attempt-{token}"),
        ExecutionId(f"provider-control-{token}"),
        OperationRef(configuration.configuration, operation, discovery_purpose()),
        configuration,
        ProviderOperation.MODEL_DISCOVERY,
        admission.admission_id,
        admission.revision,
        ProviderId(endpoint.provider_id),
        endpoint.endpoint_origin,
        endpoint.api_root,
        credential.exact,
        now,
    )
    # No INTENDED receipt: no Secret use, no connection. Failures propagate.
    receipt = attempts.intend(attempt)
    try:
        request = exact_use_request(
            credential=credential,
            attempt_id=attempt.attempt_id,
            operation=operation,
            purpose=discovery_purpose(),
            consumer=discovery_consumer(),
            target_mapping=admission.admission_id,
            configuration=configuration,
            principal=principal,
            grant=grant,
            policy=policy,
            now=clock(),
            deadline=None,
        )
        access = uses.admit(request)
        access.authorize_secret_use(request)
    except Exception:
        status = attempts.settle(
            receipt,
            AttemptState.NOT_SENT,
            frozenset({AttemptObservation.REFUSED_AT_GATE}),
        )
        return ModelDiscovery(
            DiscoveryOutcome.NOT_SENT, None, attempt.attempt_id, status.state
        )
    try:
        observation, settled = exchange(
            attempts,
            receipt,
            access,
            request,
            target,
            tls,
            b"",
            timeout=timeout,
            margin=margin,
        )
    except Exception as error:
        claimed, _ = record_fault(attempts, receipt)
        raise RuntimeError(
            "model discovery uncertain; inspect the attempt"
            if claimed
            else "model discovery not sent"
        ) from error
    state = settled.state
    if state is AttemptState.NOT_SENT:
        return ModelDiscovery(
            DiscoveryOutcome.NOT_SENT, None, attempt.attempt_id, state
        )
    if state is AttemptState.UNKNOWN:
        return ModelDiscovery(DiscoveryOutcome.UNKNOWN, None, attempt.attempt_id, state)
    response = observation.response
    assert response is not None  # COMPLETED/PROVIDER_REJECTED are complete
    if state is AttemptState.PROVIDER_REJECTED:
        return ModelDiscovery(
            DiscoveryOutcome.PROVIDER_REJECTED,
            None,
            attempt.attempt_id,
            state,
            response.status,
        )
    try:
        models = parse_model_list(response.body)
    except ModelResponseRejectedError:
        # Transport truth stays COMPLETED; only the model-list contract failed.
        return ModelDiscovery(
            DiscoveryOutcome.MALFORMED,
            None,
            attempt.attempt_id,
            state,
            response.status,
        )
    return ModelDiscovery(
        DiscoveryOutcome.LISTED,
        None,
        attempt.attempt_id,
        state,
        response.status,
        models,
    )
