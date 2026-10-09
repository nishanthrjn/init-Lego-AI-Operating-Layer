"""Offline remote-attempt fixtures and a real process-death driver.

Failpoints exist only here (patched commit seam), never in production. No
network, transport, provider or Secret realization is involved.
"""

import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from legoai.capabilities.values import CapabilityId
from legoai.execution.values import ExecutionId
from legoai.governance.secret import SecretRevisionRef
from legoai.intelligence.model.values import ModelId, ProviderId
from legoai.kernel.identity import ApplicationId, OperationId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    OperationRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.reference import _remote_attempts
from legoai.reference._remote_attempts import (
    AttemptObservation,
    AttemptState,
    RemoteAttempt,
    RemoteAttemptId,
    _RemoteAttemptStore,
)
from legoai.reference._secret_domain import _OrderingDomain

NOW = datetime(2026, 10, 9, 12, tzinfo=UTC)
SCOPE = ReferenceScope("operator", TenantId("tenant"))
CONFIGURATION = ConfigurationRevisionRef(
    ConfigurationRef(ApplicationRef(SCOPE, ApplicationId("app")), "config"),
    "r1",
    Version(1, 0, 0),
)
SECRET = SecretRevisionRef(SCOPE, "bearer-key", "s1-revision", "s1-map")


def attempt(name: str = "attempt-1", **changes: Any) -> RemoteAttempt:
    from dataclasses import replace

    value = RemoteAttempt(
        RemoteAttemptId(name),
        ExecutionId(f"exec-{name}"),
        OperationRef(
            CONFIGURATION.configuration, OperationId(f"model-{name}"), "model-chat"
        ),
        CONFIGURATION,
        "admission",
        "a1",
        "processor",
        "r1",
        "remote",
        ProviderId("remote-endpoint"),
        "https://models.example.org",
        "/v1",
        ModelId("model-a"),
        CapabilityId("legoai.intelligence.model.chat"),
        SECRET,
        NOW,
    )
    return replace(value, **changes)


def open_store(path: Path, *, readonly: bool = False) -> _RemoteAttemptStore:
    return _RemoteAttemptStore(path, _OrderingDomain(), lambda: NOW, readonly=readonly)


def die(point: int) -> None:
    print(f"FAILPOINT {point}", flush=True)
    os._exit(73)


def crash(directory: Path, point: int) -> None:
    """Abrupt termination at explicit points around the INTENDED commit."""
    path = directory / "attempts.db"
    store = open_store(path)

    def commit(conn: sqlite3.Connection) -> None:
        if point == 1:
            die(point)  # A: before INTENDED commit
        conn.execute("COMMIT")
        if point == 2:
            die(point)  # B: INTENDED durable, before any send

    with patch.object(_remote_attempts, "_commit", commit):
        receipt = store.intend(attempt())
    if point == 3:
        store.settle(
            receipt,
            AttemptState.NOT_SENT,
            frozenset({AttemptObservation.CANCELLED_BEFORE_SEND}),
        )
        die(point)  # C: NOT_SENT durable
    if point == 4:
        store.claim_for_handoff(receipt)
        store.settle(
            receipt,
            AttemptState.COMPLETED,
            frozenset(
                {AttemptObservation.SENT_ALL, AttemptObservation.RESPONSE_COMPLETE}
            ),
        )
        die(point)  # D: COMPLETED durable
    raise AssertionError("unknown failpoint")


if __name__ == "__main__":
    crash(Path(sys.argv[1]), int(sys.argv[2]))
