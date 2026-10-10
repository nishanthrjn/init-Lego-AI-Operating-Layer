"""Provider-control operation authority (ADR-024 §22; PROVIDER-MODEL-DISCOVERY-1).

A credentialed provider-control operation discloses no model-visible content,
so it is outside `model-disclosure/1`. It still needs its own explicit,
time-bounded operator admission. The only operation is an
operator-initiated model-catalog query.

`ProviderDiscoveryAdmission` is structurally distinct from `DisclosureAdmission`:
neither type derives from, converts into or is accepted in place of the other.
This module holds immutable values and one pure decision function only. It
performs no I/O and realizes no Secret; construction grants no authority.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from legoai.governance.disclosure import endpoint_parts
from legoai.governance.secret import SecretRevisionRef
from legoai.kernel.identity import _validate


class ProviderOperation(Enum):
    """The closed set of admitted provider-control operations."""

    MODEL_DISCOVERY = "model-discovery"


class ProviderDiscoveryMethod(Enum):
    """Closed, body-free model-catalog request shapes, selected by the operator."""

    GET = "get"
    POST_EMPTY = "post_empty"


class DiscoveryRefusal(Enum):
    """Closed refusal taxonomy for provider-control admission."""

    NO_ADMISSION = "no_admission"
    NOT_YET_VALID = "not_yet_valid"
    EXPIRED = "expired"
    PROVIDER_MISMATCH = "provider_mismatch"
    ENDPOINT_MISMATCH = "endpoint_mismatch"
    API_ROOT_MISMATCH = "api_root_mismatch"
    OPERATION_MISMATCH = "operation_mismatch"
    CONSUMER_MISMATCH = "consumer_mismatch"
    CREDENTIAL_MISMATCH = "credential_mismatch"
    METHOD_MISMATCH = "method_mismatch"


def _exact(value: object) -> None:
    """Bounded operator identity text with no wildcard or padding."""
    if type(value) is not str:
        raise TypeError("provider-control identity must be str")
    if (
        not 1 <= len(value) <= 256
        or value != value.strip()
        or "*" in value
        or "?" in value
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError("provider-control identity must be exact")


def _aware(value: object) -> datetime:
    if type(value) is not datetime or value.utcoffset() is None:
        raise ValueError("admission window requires aware datetimes")
    return value


@dataclass(frozen=True, slots=True)
class ProviderDiscoveryAdmission:
    """Operator authority for one exact provider-control operation.

    Binds the exact provider, normalized https origin and API root, operation,
    operator-control consumer and credential revision, valid only within
    [not_before, not_after). It authorizes no model-visible content, model,
    binding or path other than the operation's fixed one.
    """

    admission_id: str = field(repr=False)
    revision: str = field(repr=False)
    provider_id: str = field(repr=False)
    endpoint_origin: str = field(repr=False)
    api_root: str = field(repr=False)
    operation: ProviderOperation
    consumer: str = field(repr=False)
    credential: SecretRevisionRef = field(repr=False)
    not_before: datetime
    not_after: datetime
    method: ProviderDiscoveryMethod = ProviderDiscoveryMethod.POST_EMPTY

    def __post_init__(self) -> None:
        if type(self.method) is not ProviderDiscoveryMethod:
            raise TypeError("closed discovery method required")
        _validate(self.admission_id)
        _validate(self.revision)
        _exact(self.provider_id)
        _exact(self.endpoint_origin)
        _exact(self.api_root)
        root = "" if self.api_root == "/" else self.api_root
        if endpoint_parts(self.endpoint_origin + root) != (
            self.endpoint_origin,
            self.api_root,
        ):
            raise ValueError("endpoint must be a normalized https origin and API root")
        if type(self.operation) is not ProviderOperation:
            raise TypeError("admission requires ProviderOperation")
        _exact(self.consumer)
        if type(self.credential) is not SecretRevisionRef:
            raise TypeError("admission requires the exact SecretRevisionRef")
        if _aware(self.not_after) <= _aware(self.not_before):
            raise ValueError("admission validity window must be ordered")


def evaluate_discovery(
    admission: ProviderDiscoveryAdmission | None,
    *,
    provider_id: str,
    endpoint_origin: str,
    api_root: str,
    operation: ProviderOperation,
    consumer: str,
    credential: SecretRevisionRef,
    at: datetime,
    method: ProviderDiscoveryMethod = ProviderDiscoveryMethod.POST_EMPTY,
) -> DiscoveryRefusal | None:
    """Pure decision: may this exact provider-control operation run now?

    None means admitted. Only a `ProviderDiscoveryAdmission` is ever
    considered; any other value, including a disclosure admission, is
    NO_ADMISSION.
    """
    if type(admission) is not ProviderDiscoveryAdmission:
        return DiscoveryRefusal.NO_ADMISSION
    if type(method) is not ProviderDiscoveryMethod or method is not admission.method:
        return DiscoveryRefusal.METHOD_MISMATCH
    now = _aware(at)
    if now < admission.not_before:
        return DiscoveryRefusal.NOT_YET_VALID
    if now >= admission.not_after:
        return DiscoveryRefusal.EXPIRED
    if provider_id != admission.provider_id:
        return DiscoveryRefusal.PROVIDER_MISMATCH
    if endpoint_origin != admission.endpoint_origin:
        return DiscoveryRefusal.ENDPOINT_MISMATCH
    if api_root != admission.api_root:
        return DiscoveryRefusal.API_ROOT_MISMATCH
    if operation is not admission.operation:
        return DiscoveryRefusal.OPERATION_MISMATCH
    if consumer != admission.consumer:
        return DiscoveryRefusal.CONSUMER_MISMATCH
    if credential != admission.credential:
        return DiscoveryRefusal.CREDENTIAL_MISMATCH
    return None
