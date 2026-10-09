"""Private Secret owner state and the SECRET-SOURCE-S1 material source.

No environment or consumer callback. One admitted exact use per state
instance; material is ephemeral and never serialized. Synthetic Stage-A uses
fresh random material; SECRET-SOURCE-S1 (ADR-023 §8) supplies an
operator-provisioned, immutable, process-local revision instead. Python
privacy is a trusted-host boundary, not isolation from hostile host code, and
no memory erasure is claimed.
"""

from datetime import UTC, datetime
from secrets import token_bytes, token_hex

from legoai.governance.ports import SecretAccessRequest
from legoai.governance.secret import SecretRef, SecretRevisionRef, _time
from legoai.kernel.identity import _validate
from legoai.kernel.references import ReferenceScope
from legoai.reference._secret_domain import _OrderingDomain


def _provisioned_class() -> str:
    """The SecretRef class S1 issues; never a provider or token format."""
    return "operator-provisioned"


def _max_material_bytes() -> int:
    """Bounded like the existing Secret-use material limit (Stage-A ledger)."""
    return 4096


def _material(value: object) -> bytearray:
    """Validate operator input without echoing it in any error.

    Visible ASCII only (0x21-0x7E): admits ordinary Bearer API keys and
    tokens, and rejects empty, whitespace, control and non-ASCII input. No
    provider prefix or format is assumed.
    """
    if type(value) is not str:
        raise TypeError("Secret material must be text")
    if not 1 <= len(value) <= _max_material_bytes() or not all(
        "\x21" <= char <= "\x7e" for char in value
    ):
        raise ValueError("Secret material rejected")
    return bytearray(value.encode("ascii"))


def _wipe(buffer: bytearray) -> None:
    """Best-effort overwrite of the owner's own buffer; not a memory guarantee."""
    for index in range(len(buffer)):
        buffer[index] = 0


class _Provisioned:
    """One immutable revision: its use binding and the owner's private buffer."""

    __slots__ = ("reference", "consumer", "material", "current")

    def __init__(self, reference: SecretRef, consumer: str, material: bytearray):
        self.reference, self.consumer = reference, consumer
        self.material, self.current = material, True

    def __repr__(self) -> str:
        return "_Provisioned(<redacted>)"


class _ProvisionedSecretSource:
    """SECRET-SOURCE-S1: operator-provisioned immutable process-local material.

    An explicit operator act provisions material for one Secret identity, bound
    to its use purpose and consumer, under an owner-issued revision (never a
    digest of the material). Revisions are immutable: provisioning again issues
    a new revision and retires the previous one (no overlap). Retirement and
    close participate in the shared ordering domain. Only `SecretRef` and safe
    revision metadata leave this object; material is released solely to the
    admitted exact-use realization holding that domain. Nothing is persisted;
    a new process must provision again under a new revision.
    """

    def __init__(self, domain: _OrderingDomain, scope: ReferenceScope) -> None:
        if type(domain) is not _OrderingDomain or type(scope) is not ReferenceScope:
            raise TypeError("trusted source composition required")
        self._domain, self._scope = domain, scope
        self._open = True
        self._revisions: dict[SecretRevisionRef, _Provisioned] = {}

    def __repr__(self) -> str:
        return f"_ProvisionedSecretSource(open={self._open})"

    __str__ = __repr__

    def provision(
        self, identity: str, purpose: str, consumer: str, material: object
    ) -> SecretRef:
        """Admit one new immutable revision; returns only its `SecretRef`."""
        self._domain.outside()
        for text in (identity, purpose, consumer):
            _validate(text)
        buffer = _material(material)
        revision = SecretRevisionRef(
            self._scope, identity, f"s1-{token_hex(16)}", f"s1-map-{token_hex(8)}"
        )
        reference = SecretRef(revision, _provisioned_class(), purpose)
        try:
            with self._domain.enter():
                if not self._open:
                    raise PermissionError("Secret source unavailable")
                for prior in self._revisions.values():
                    if prior.reference.exact.identity == identity and prior.current:
                        self._retire(prior)
                self._revisions[revision] = _Provisioned(reference, consumer, buffer)
        except BaseException:
            _wipe(buffer)
            raise
        return reference

    def retire(self, revision: SecretRevisionRef) -> None:
        """Local revocation: the revision never yields material again."""
        with self._domain.enter():
            entry = self._revisions.get(revision)
            if entry is None:
                raise PermissionError("Secret use unavailable")
            self._retire(entry)

    def close(self) -> None:
        """End this source incarnation; safe revision metadata is retained."""
        with self._domain.enter():
            self._open = False
            for entry in self._revisions.values():
                self._retire(entry)

    def status(self, revision: SecretRevisionRef) -> bool:
        """Safe point-in-time eligibility metadata; never material."""
        with self._domain.enter():
            entry = self._revisions.get(revision)
            return self._open and entry is not None and entry.current

    @staticmethod
    def _retire(entry: _Provisioned) -> None:
        entry.current = False
        _wipe(entry.material)

    def _eligible(self, request: SecretAccessRequest) -> bool:
        self._domain.held()
        entry = self._revisions.get(request.plan.secret)
        return (
            self._open
            and entry is not None
            and entry.current
            and entry.reference == request.reference
            and entry.consumer == request.plan.consumer
        )

    def _realize(self, request: SecretAccessRequest) -> bytes:
        """Protected realization for the admitted exact use only (domain held)."""
        if not self._eligible(request):
            raise PermissionError("Secret use unavailable")
        return bytes(self._revisions[request.plan.secret].material)


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
    def __init__(
        self,
        request: SecretAccessRequest,
        domain: _OrderingDomain,
        source: _ProvisionedSecretSource | None = None,
    ):
        self._request, self._domain, self._source = request, domain, source
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

    def current(
        self, request: SecretAccessRequest, now: datetime, *, continuing: bool = False
    ) -> None:
        """`continuing` rechecks a credential handoff already accepted in this
        exact use (CREDENTIAL-HTTPS-T2 continuation writes): every condition
        except the single-acquisition marker, which is then already set."""
        self._domain.held()
        if (
            request != self._request
            or not self._mapping_valid
            or not self._revision_valid
            or self._cancelled
            or (self._attempted and not continuing)
            or (continuing and not self._attempted)
            or not request.plan.prepared_at <= now < request.plan.expires_at
            or (self._source is not None and not self._source._eligible(request))
        ):
            raise PermissionError("Secret use unavailable")

    def acquire(self) -> None:
        # Synthetic entropy is acquired outside the ordering domain. Publication
        # of the ephemeral material participates; cancellation cannot leave a
        # handle. Provisioned material is read under the same domain, so
        # retirement or source close is ordered against it.
        self._domain.outside()
        material = token_bytes(32) if self._source is None else None
        with self._domain.enter():
            if self._cancelled or self._attempted:
                raise PermissionError("Secret use unavailable")
            if material is None:
                assert self._source is not None
                material = self._source._realize(self._request)
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
