"""Private remote-attempt custody for the Model invocation plane (ADR-023 §9).

One durable, content-minimized record per exact prospective remote Model
invocation, committed as INTENDED before any future credential-bearing
handoff (ADR-007 §6.2). This owner records responsibility only: it never
decides disclosure, never realizes a Secret, never sends, retries or resends.
Recovery is inspection; an unsettled INTENDED attempt is effectively UNKNOWN.

Reuses the qualified custody SQLite mechanics (explicit provisioning, one
admitted writer incarnation, integrity/schema checks, single commit seam).
No durability is claimed beyond that intact-local-storage profile.
"""

import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from legoai.capabilities.values import CapabilityId
from legoai.execution.values import ExecutionId
from legoai.governance.secret import SecretRevisionRef, _time
from legoai.intelligence.model.values import ModelId, ProviderId
from legoai.kernel.identity import _validate
from legoai.kernel.references import ConfigurationRevisionRef, OperationRef
from legoai.reference import _custody_codec as codec
from legoai.reference._custody_sqlite import (
    _admit,
    _check,
    _commit,
    _Conflict,
    _connect,
    _provision,
    _ScopeDenied,
    _StorageGap,
)
from legoai.reference._secret_domain import _OrderingDomain


def _owner() -> str:
    return "remote-attempt-v1"


def _capacity() -> int:
    """Retained attempts; exhaustion refuses new work, never deletes."""
    return 4096


def _schema() -> str:
    return """
CREATE TABLE attempts(
 attempt_id TEXT PRIMARY KEY,
 execution_id TEXT NOT NULL UNIQUE,
 record TEXT NOT NULL CHECK(length(record)<=32768),
 state TEXT NOT NULL CHECK(state IN ('intended','not_sent','provider_rejected','completed','unknown')),
 observations TEXT NOT NULL CHECK(length(observations)<=1024),
 settled_at TEXT,
 CHECK((state='intended')=(settled_at IS NULL))
);
"""


@dataclass(frozen=True, slots=True)
class RemoteAttemptId:
    """Single-use identity of one prospective external invocation."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate(self.value)


class AttemptState(Enum):
    """ADR-023 §9: INTENDED, then exactly one terminal category."""

    INTENDED = "intended"
    NOT_SENT = "not_sent"
    PROVIDER_REJECTED = "provider_rejected"
    COMPLETED = "completed"
    UNKNOWN = "unknown"


class AttemptObservation(Enum):
    """ADR-023 §9 safe observations; categories only, never offsets or bytes."""

    REFUSED_AT_GATE = "refused_at_gate"
    CANCELLED_BEFORE_SEND = "cancelled_before_send"
    SENT_NONE = "sent_none"
    SENT_PARTIAL = "sent_partial"
    SENT_ALL = "sent_all"
    SENT_UNKNOWN = "sent_unknown"
    RESPONSE_COMPLETE = "response_complete"
    RESPONSE_INCOMPLETE = "response_incomplete"
    TIME_VALIDITY_VIOLATION = "time_validity_violation"


def _no_send() -> frozenset[AttemptObservation]:
    """Observations that each positively prove zero credential bytes left."""
    return frozenset(
        {
            AttemptObservation.REFUSED_AT_GATE,
            AttemptObservation.CANCELLED_BEFORE_SEND,
            AttemptObservation.SENT_NONE,
        }
    )


def _admissible(
    state: AttemptState, observations: frozenset[AttemptObservation]
) -> bool:
    """Which terminal category the observations can justify. Never inferred
    from absence: NOT_SENT needs positive proof, a provider outcome needs a
    complete response, and UNKNOWN is always truthful."""
    if state is AttemptState.UNKNOWN:
        return True
    if state is AttemptState.NOT_SENT:
        return bool(observations) and observations <= _no_send()
    if state in (AttemptState.PROVIDER_REJECTED, AttemptState.COMPLETED):
        return (
            AttemptObservation.RESPONSE_COMPLETE in observations
            and not observations & _no_send()
            and AttemptObservation.RESPONSE_INCOMPLETE not in observations
        )
    return False


@dataclass(frozen=True, slots=True)
class RemoteAttempt:
    """Exact identity of one intended remote invocation. No content, ever.

    Answers which invocation was going to use which credential revision
    against which admitted remote processor, and nothing about what it said.
    """

    attempt_id: RemoteAttemptId
    execution_id: ExecutionId
    operation: OperationRef
    configuration: ConfigurationRevisionRef
    admission_id: str = field(repr=False)
    admission_revision: str = field(repr=False)
    declaration_id: str = field(repr=False)
    declaration_revision: str = field(repr=False)
    binding_id: str = field(repr=False)
    provider_id: ProviderId
    endpoint_origin: str = field(repr=False)
    api_root: str = field(repr=False)
    model: ModelId
    capability: CapabilityId
    secret: SecretRevisionRef | None
    created_at: datetime

    def __post_init__(self) -> None:
        for value, kind in (
            (self.attempt_id, RemoteAttemptId),
            (self.execution_id, ExecutionId),
            (self.operation, OperationRef),
            (self.configuration, ConfigurationRevisionRef),
            (self.provider_id, ProviderId),
            (self.model, ModelId),
            (self.capability, CapabilityId),
        ):
            if type(value) is not kind:
                raise TypeError(f"attempt requires {kind.__name__}")
        for text in (
            self.admission_id,
            self.admission_revision,
            self.declaration_id,
            self.declaration_revision,
            self.binding_id,
            self.endpoint_origin,
            self.api_root,
        ):
            _validate(text)
        if self.secret is not None and type(self.secret) is not SecretRevisionRef:
            raise TypeError("attempt credential must be a SecretRevisionRef or None")
        _time(self.created_at)
        tenant = self.configuration.configuration.application.scope.tenant_id
        if self.operation.scope.tenant_id != tenant or (
            self.secret is not None and self.secret.scope.tenant_id != tenant
        ):
            raise ValueError("attempt tenant mismatch")


@dataclass(frozen=True, slots=True)
class AttemptStatus:
    """Safe inspection projection. `effective` is UNKNOWN for anything unsettled."""

    attempt: RemoteAttempt
    state: AttemptState
    observations: frozenset[AttemptObservation]
    settled_at: datetime | None

    @property
    def effective(self) -> AttemptState:
        return (
            AttemptState.UNKNOWN if self.state is AttemptState.INTENDED else self.state
        )


class IntendedReceipt:
    """Proof that this store incarnation durably committed INTENDED.

    Unforgeable in practice only within the trusted host: it is checked by
    identity against the issuing store. Carries no material.
    """

    __slots__ = ("_store", "attempt")

    def __init__(self, store: _RemoteAttemptStore, attempt: RemoteAttempt) -> None:
        self._store, self.attempt = store, attempt

    def __repr__(self) -> str:
        return "IntendedReceipt(<attempt>)"


def _encode(attempt: RemoteAttempt) -> str:
    record = {
        "attempt_id": attempt.attempt_id.value,
        "execution_id": attempt.execution_id.value,
        "operation": codec.encode(attempt.operation),
        "configuration": codec.encode(attempt.configuration),
        "admission_id": attempt.admission_id,
        "admission_revision": attempt.admission_revision,
        "declaration_id": attempt.declaration_id,
        "declaration_revision": attempt.declaration_revision,
        "binding_id": attempt.binding_id,
        "provider_id": attempt.provider_id.value,
        "endpoint_origin": attempt.endpoint_origin,
        "api_root": attempt.api_root,
        "model": attempt.model.value,
        "capability": attempt.capability.value,
        "secret": None if attempt.secret is None else codec.encode(attempt.secret),
        "created_at": attempt.created_at.isoformat(),
    }
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _decode(text: str) -> RemoteAttempt:
    value = json.loads(text)
    if not isinstance(value, dict) or len(value) != 16:
        raise ValueError("attempt representation")
    operation = codec.decode(value["operation"])
    configuration = codec.decode(value["configuration"])
    secret = None if value["secret"] is None else codec.decode(value["secret"])
    if (
        type(operation) is not OperationRef
        or type(configuration) is not ConfigurationRevisionRef
        or (secret is not None and type(secret) is not SecretRevisionRef)
    ):
        raise ValueError("attempt representation")
    return RemoteAttempt(
        RemoteAttemptId(value["attempt_id"]),
        ExecutionId(value["execution_id"]),
        operation,
        configuration,
        value["admission_id"],
        value["admission_revision"],
        value["declaration_id"],
        value["declaration_revision"],
        value["binding_id"],
        ProviderId(value["provider_id"]),
        value["endpoint_origin"],
        value["api_root"],
        ModelId(value["model"]),
        CapabilityId(value["capability"]),
        secret,
        datetime.fromisoformat(value["created_at"]),
    )


def _observations(text: str) -> frozenset[AttemptObservation]:
    items = json.loads(text)
    if not isinstance(items, list):
        raise ValueError("observation representation")
    return frozenset(AttemptObservation(item) for item in items)


class _RemoteAttemptStore:
    """Owner-local SQLite custody of remote attempts; one writer incarnation.

    Only the Model invocation plane holds this object. Adapters, transports,
    the Secret source and consumers never receive it; a future transport may
    only hand back a bounded observation for the plane to record.
    """

    @staticmethod
    def provision(path: Path) -> None:
        _provision(path, _owner(), _schema())

    def __init__(
        self,
        path: Path,
        domain: _OrderingDomain,
        clock: Callable[[], datetime],
        *,
        readonly: bool = False,
    ) -> None:
        if type(domain) is not _OrderingDomain or not callable(clock):
            raise TypeError("trusted attempt-store composition required")
        domain.outside()
        self._domain, self._clock, self._readonly = domain, clock, readonly
        self._thread = domain.thread_identity()
        # Attempts committed by THIS incarnation and not yet claimed/settled.
        self._live: dict[str, RemoteAttempt] = {}
        self._claimed: set[str] = set()
        self._admission = None if readonly else _admit(path, _owner())
        try:
            self._conn = _connect(path, readonly=readonly)
            _check(self._conn, _owner())
            self._verify()
        except BaseException:
            if hasattr(self, "_conn"):
                self._conn.close()
            if self._admission is not None:
                self._admission.close()
            raise

    def __repr__(self) -> str:
        return f"_RemoteAttemptStore(readonly={self._readonly})"

    def close(self) -> None:
        self._owner_thread()
        self._conn.close()
        if self._admission is not None:
            self._admission.close()
        self._live.clear()

    def _owner_thread(self) -> None:
        self._domain.outside()
        if self._domain.thread_identity() != self._thread:
            raise _ScopeDenied("attempt store owner thread required")

    def _verify(self) -> None:
        try:
            rows = self._conn.execute(
                "SELECT attempt_id,execution_id,record,state,observations,settled_at FROM attempts LIMIT ?",
                (_capacity() + 1,),
            ).fetchall()
            if len(rows) > _capacity():
                raise ValueError("capacity")
            for row in rows:
                self._status(row)
        except sqlite3.Error, ValueError, TypeError, KeyError, RecursionError:
            raise _StorageGap("attempt history gap") from None

    @staticmethod
    def _status(row: tuple[object, ...]) -> AttemptStatus:
        key, execution, record, state, observed, settled = row
        if not all(type(v) is str for v in (key, execution, record, state, observed)):
            raise ValueError("attempt row")
        assert isinstance(record, str) and isinstance(state, str)
        assert isinstance(observed, str)
        attempt = _decode(record)
        if attempt.attempt_id.value != key or attempt.execution_id.value != execution:
            raise ValueError("attempt identity")
        status = AttemptStatus(
            attempt,
            AttemptState(state),
            _observations(observed),
            None if settled is None else datetime.fromisoformat(str(settled)),
        )
        if (status.state is AttemptState.INTENDED) != (status.settled_at is None) or (
            status.state is not AttemptState.INTENDED
            and not _admissible(status.state, status.observations)
        ):
            raise ValueError("attempt state")
        return status

    def intend(self, attempt: RemoteAttempt) -> IntendedReceipt:
        """Durably commit INTENDED. Only a returned receipt permits a handoff.

        Any duplicate attempt or execution identity is refused; nothing is
        overwritten. A failure or uncertain commit yields no receipt.
        """
        self._owner_thread()
        if self._readonly:
            raise _ScopeDenied("inspection cannot intend")
        if type(attempt) is not RemoteAttempt:
            raise TypeError("exact RemoteAttempt required")
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            count = self._conn.execute("SELECT count(*) FROM attempts").fetchone()[0]
            if count >= _capacity():
                raise _StorageGap("attempt capacity exhausted")
            self._conn.execute(
                "INSERT INTO attempts VALUES (?,?,?,'intended','[]',NULL)",
                (
                    attempt.attempt_id.value,
                    attempt.execution_id.value,
                    _encode(attempt),
                ),
            )
            _commit(self._conn)
        except sqlite3.IntegrityError:
            raise _Conflict("attempt identity already recorded") from None
        except sqlite3.Error:
            raise _StorageGap("attempt commit requires inspection") from None
        finally:
            if self._conn.in_transaction:
                self._conn.execute("ROLLBACK")
        self._live[attempt.attempt_id.value] = attempt
        return IntendedReceipt(self, attempt)

    def claim_for_handoff(self, receipt: IntendedReceipt) -> RemoteAttempt:
        """The seam a future credential-bearing transport must pass, once.

        Requires a receipt issued by this incarnation for a durable, still
        INTENDED attempt. Single use: a second claim is refused.
        """
        self._owner_thread()
        attempt = self._receipt(receipt)
        if attempt.attempt_id.value in self._claimed:
            raise _ScopeDenied("attempt already claimed")
        status = self.inspect(attempt.attempt_id)
        if status is None or status.state is not AttemptState.INTENDED:
            raise _ScopeDenied("attempt not durably intended")
        if status.attempt != attempt:
            raise _Conflict("attempt identity mismatch")
        self._claimed.add(attempt.attempt_id.value)
        return attempt

    def settle(
        self,
        receipt: IntendedReceipt,
        state: AttemptState,
        observations: frozenset[AttemptObservation],
    ) -> AttemptStatus:
        """Record the one terminal category this incarnation can justify."""
        self._owner_thread()
        attempt = self._receipt(receipt)
        if (
            attempt.attempt_id.value in self._claimed
            and state is AttemptState.NOT_SENT
            and observations != frozenset({AttemptObservation.SENT_NONE})
        ):
            # Once handed to a transport, only its positive zero-send proof
            # supports NOT_SENT; refusal or cancellation no longer does.
            raise _Conflict("observations do not justify that outcome")
        result = self._settle(attempt.attempt_id, state, observations)
        del self._live[attempt.attempt_id.value]
        return result

    def reconcile_unknown(self, attempt_id: RemoteAttemptId) -> AttemptStatus:
        """Recovery of an attempt left INTENDED by an earlier incarnation.

        Without its observation nothing can be proven, so the only permitted
        terminal category is UNKNOWN. Never resends or realizes anything.
        """
        self._owner_thread()
        if type(attempt_id) is not RemoteAttemptId:
            raise TypeError("exact RemoteAttemptId required")
        if attempt_id.value in self._live:
            raise _ScopeDenied("live attempts are settled by their receipt")
        return self._settle(attempt_id, AttemptState.UNKNOWN, frozenset())

    def _receipt(self, receipt: IntendedReceipt) -> RemoteAttempt:
        if (
            type(receipt) is not IntendedReceipt
            or receipt._store is not self
            or self._live.get(receipt.attempt.attempt_id.value) != receipt.attempt
        ):
            raise _ScopeDenied("attempt receipt unavailable")
        return receipt.attempt

    def _settle(
        self,
        attempt_id: RemoteAttemptId,
        state: AttemptState,
        observations: frozenset[AttemptObservation],
    ) -> AttemptStatus:
        if self._readonly:
            raise _ScopeDenied("inspection cannot settle")
        if type(state) is not AttemptState or state is AttemptState.INTENDED:
            raise ValueError("a terminal attempt state is required")
        if type(observations) is not frozenset or any(
            type(item) is not AttemptObservation for item in observations
        ):
            raise TypeError("attempt observations required")
        if not _admissible(state, observations):
            raise _Conflict("observations do not justify that outcome")
        now = self._clock()
        _time(now)
        try:
            self._conn.execute("BEGIN IMMEDIATE")
            updated = self._conn.execute(
                "UPDATE attempts SET state=?,observations=?,settled_at=? "
                "WHERE attempt_id=? AND state='intended'",
                (
                    state.value,
                    json.dumps(sorted(item.value for item in observations)),
                    now.isoformat(),
                    attempt_id.value,
                ),
            )
            if updated.rowcount != 1:
                raise _Conflict("attempt is not intended")
            _commit(self._conn)
        except sqlite3.Error:
            raise _StorageGap("attempt settlement requires inspection") from None
        finally:
            if self._conn.in_transaction:
                self._conn.execute("ROLLBACK")
        status = self.inspect(attempt_id)
        assert status is not None
        return status

    def inspect(self, attempt_id: RemoteAttemptId) -> AttemptStatus | None:
        self._owner_thread()
        if type(attempt_id) is not RemoteAttemptId:
            raise TypeError("exact RemoteAttemptId required")
        try:
            row = self._conn.execute(
                "SELECT attempt_id,execution_id,record,state,observations,settled_at "
                "FROM attempts WHERE attempt_id=?",
                (attempt_id.value,),
            ).fetchone()
            return None if row is None else self._status(row)
        except sqlite3.Error, ValueError, TypeError, KeyError, RecursionError:
            raise _StorageGap("attempt history gap") from None

    def unsettled(self) -> tuple[AttemptStatus, ...]:
        """Read-only recovery inspection: attempts still INTENDED."""
        self._owner_thread()
        try:
            rows = self._conn.execute(
                "SELECT attempt_id,execution_id,record,state,observations,settled_at "
                "FROM attempts WHERE state='intended' ORDER BY attempt_id"
            ).fetchall()
            return tuple(self._status(row) for row in rows)
        except sqlite3.Error, ValueError, TypeError, KeyError, RecursionError:
            raise _StorageGap("attempt history gap") from None


def _inspect_attempts(
    path: Path, domain: _OrderingDomain, clock: Callable[[], datetime]
) -> tuple[AttemptStatus, ...] | None:
    """Read-only restart inspection; None means the history cannot be trusted."""
    try:
        store = _RemoteAttemptStore(path, domain, clock, readonly=True)
        try:
            return store.unsettled()
        finally:
            store.close()
    except _StorageGap, sqlite3.Error, OSError:
        return None
