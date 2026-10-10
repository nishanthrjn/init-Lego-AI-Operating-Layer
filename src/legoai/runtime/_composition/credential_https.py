"""Model invocation plane: one SRCP-1 credential-bearing HTTPS exchange.

Order (ADR-023): admitted disclosure (already decided) -> durable INTENDED
attempt (already committed) -> exact recipient check -> DNS/connect/verified
TLS (no credential yet) -> single-use handoff claim -> Secret exact-use
handoff (currentness-gated nonblocking writes) -> bounded response read ->
the plane maps the observation to the attempt's terminal custody state.

No disclosure policy, retry, fallback, redirect or provider semantics live
here, and the public host does not use this module while REMOTE is refused.
"""

from dataclasses import replace
from datetime import timedelta
from ssl import SSLContext

from legoai.governance.ports import SecretAccessRequest
from legoai.kernel.effects import EffectExtent
from legoai.reference._credential_https import (
    HandoffObservation,
    HttpsTarget,
    SendProgress,
    TransportError,
    _CredentialFlight,
)
from legoai.reference._remote_attempts import (
    AttemptObservation,
    AttemptState,
    AttemptStatus,
    IntendedReceipt,
    ProviderControlAttempt,
    _RemoteAttemptStore,
)
from legoai.runtime._composition.secret import _SyntheticSecretAccess


def settlement(
    observation: HandoffObservation,
) -> tuple[AttemptState, frozenset[AttemptObservation]]:
    """The plane's mapping from transport facts to ADR-023 custody outcomes.

    Never inferred from absence: zero accepted credential bytes is NOT_SENT;
    any accepted bytes without a complete response stay UNKNOWN.
    """
    if type(observation) is not HandoffObservation:
        raise TypeError("transport observation required")
    extra = (
        frozenset({AttemptObservation.TIME_VALIDITY_VIOLATION})
        if observation.time_violation
        else frozenset()
    )
    if observation.progress is SendProgress.NONE:
        return AttemptState.NOT_SENT, frozenset({AttemptObservation.SENT_NONE})
    if observation.progress is SendProgress.PARTIAL:
        return AttemptState.UNKNOWN, frozenset(
            {AttemptObservation.SENT_PARTIAL}
        ) | extra
    if observation.progress is SendProgress.UNKNOWN:
        return AttemptState.UNKNOWN, frozenset(
            {AttemptObservation.SENT_UNKNOWN}
        ) | extra
    response = observation.response
    if response is None:
        return AttemptState.UNKNOWN, frozenset(
            {AttemptObservation.SENT_ALL, AttemptObservation.RESPONSE_INCOMPLETE}
        ) | extra
    complete = (
        frozenset({AttemptObservation.SENT_ALL, AttemptObservation.RESPONSE_COMPLETE})
        | extra
    )
    if 200 <= response.status < 300:
        return AttemptState.COMPLETED, complete
    return AttemptState.PROVIDER_REJECTED, complete


def effect(state: AttemptState) -> EffectExtent:
    """Model effect of a settled attempt; NONE only when nothing was sent."""
    if state is AttemptState.NOT_SENT or state is AttemptState.PROVIDER_REJECTED:
        return EffectExtent.NONE
    if state is AttemptState.COMPLETED:
        return EffectExtent.COMPLETED
    return EffectExtent.UNKNOWN


def exchange(
    store: _RemoteAttemptStore,
    receipt: IntendedReceipt,
    access: _SyntheticSecretAccess,
    request: SecretAccessRequest,
    target: HttpsTarget,
    context: SSLContext,
    body: bytes,
    *,
    timeout: float,
    margin: timedelta,
) -> tuple[HandoffObservation, AttemptStatus]:
    """One exact credential-bearing exchange. Never retries or resends."""
    if type(store) is not _RemoteAttemptStore or type(receipt) is not IntendedReceipt:
        raise TypeError("durable attempt custody required")
    if (
        type(access) is not _SyntheticSecretAccess
        or type(request) is not SecretAccessRequest
    ):
        raise TypeError("Secret exact-use composition required")
    attempt = receipt.attempt
    # Recipient binding before any connection or credential: the credential
    # goes only to the admitted origin, and its use is the attempt's.
    if (
        type(target) is not HttpsTarget
        or (target.origin, target.api_root)
        != (attempt.endpoint_origin, attempt.api_root)
        or attempt.secret is None
        or request.plan.secret != attempt.secret
        or request.plan.use_id.value != attempt.attempt_id.value
    ):
        raise PermissionError("credential recipient mismatch")
    if type(attempt) is ProviderControlAttempt:
        if (
            target.path != "/models"
            or target.discovery_method is not attempt.method
            or body
        ):
            raise PermissionError("provider-control request shape mismatch")
    elif target.discovery_method is not None:
        raise PermissionError("model attempt cannot perform provider control")
    flight = _CredentialFlight(target, context, body, timeout=timeout)
    try:
        try:
            flight.open()  # DNS/TCP/TLS verified; no credential exists yet
        except TransportError as error:
            # Not yet claimed: no credential existed, so zero bytes is proven.
            observation = replace(flight.observe(None), failure=error.failure)
            return observation, store.settle(
                receipt,
                AttemptState.NOT_SENT,
                frozenset({AttemptObservation.SENT_NONE}),
            )
        store.claim_for_handoff(receipt)
        accepted = False
        try:
            access._handoff(request, flight, margin=margin)
            accepted = True
        except PermissionError:
            pass  # refused at the final gate: the flight sent nothing
        response = flight.receive()
        observation = flight.observe(response)
    finally:
        flight.close()
    state, observed = settlement(observation)
    status = store.settle(receipt, state, observed)
    if accepted:
        # ADR-023 §9 attribution: the Secret use is the attempt's (same id).
        access.record_secret_use(request)
    return observation, status
