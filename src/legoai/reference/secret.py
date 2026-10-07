"""Private synthetic Secret owner state. No environment or consumer callback.

One admitted exact use per instance; material is ephemeral and never serialized.
Python privacy is a trusted-host boundary, not isolation from hostile host code.
"""

from datetime import UTC, datetime
from secrets import token_bytes

from legoai.governance.ports import SecretAccessRequest
from legoai.governance.secret import _time
from legoai.reference._secret_domain import _OrderingDomain


class _SecretClock:
    """Qualified local clock or explicit deterministic clock, never a callback.

    Time is sampled at the final gate; no hard realtime commit deadline claim.
    """

    def __init__(self, domain: _OrderingDomain, instant: datetime | None = None):
        if instant is not None:
            _time(instant)
        self._domain, self._instant = domain, instant

    def now(self) -> datetime:
        return datetime.now(UTC) if self._instant is None else self._instant

    def advance(self, instant: datetime) -> None:
        _time(instant)
        with self._domain.enter():
            if self._instant is None or instant < self._instant:
                raise ValueError("deterministic monotone clock required")
            self._instant = instant


class _SecretState:
    def __init__(self, request: SecretAccessRequest, domain: _OrderingDomain):
        self._request, self._domain = request, domain
        self._mapping_valid = True
        self._revision_valid = True
        self._cancelled = False
        self._attempted = False
        self._material: bytes | None = None

    def invalidate_mapping(self) -> None:
        with self._domain.enter():
            self._mapping_valid = False
            self._material = None

    def invalidate_revision(self) -> None:
        with self._domain.enter():
            self._revision_valid = False
            self._material = None

    def cancel(self) -> None:
        with self._domain.enter():
            self._cancelled = True
            self._material = None

    def current(self, request: SecretAccessRequest, now: datetime) -> None:
        self._domain.held()
        if (
            request != self._request
            or not self._mapping_valid
            or not self._revision_valid
            or self._cancelled
            or self._attempted
            or not request.plan.prepared_at <= now < request.plan.expires_at
        ):
            raise PermissionError("Secret use unavailable")

    def acquire(self) -> None:
        # Entropy acquisition is outside the ordering domain. Publication of the
        # ephemeral material participates; cancellation cannot leave a handle.
        self._domain.outside()
        material = token_bytes(32)
        with self._domain.enter():
            if self._cancelled or self._attempted:
                raise PermissionError("Secret use unavailable")
            self._material = material

    def take(self) -> bytes:
        self._domain.held()
        material = self._material
        self._material = None
        self._attempted = True
        if material is None:
            raise PermissionError("Secret use unavailable")
        return material

    def discard(self) -> None:
        with self._domain.enter():
            self._material = None
            self._attempted = True
