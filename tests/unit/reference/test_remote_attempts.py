"""REMOTE-ATTEMPT-CUSTODY-1: durable INTENDED responsibility, no resend.

Synthetic canaries only. No network, transport, provider or Secret
realization: the store records identities and outcomes, nothing else.
"""

import asyncio
import logging
import sqlite3
import subprocess
import sys
import traceback
from dataclasses import replace
from pathlib import Path
from threading import Thread
from typing import Any
from unittest.mock import patch

import pytest

from legoai.capabilities.values import CapabilityId
from legoai.governance.secret import SecretRevisionRef
from legoai.intelligence.model.values import ModelId
from legoai.reference import _remote_attempts
from legoai.reference._custody_sqlite import _Conflict, _ScopeDenied, _StorageGap
from legoai.reference._remote_attempts import (
    AttemptObservation,
    AttemptState,
    IntendedReceipt,
    RemoteAttemptId,
    _inspect_attempts,
    _RemoteAttemptStore,
)
from legoai.reference._secret_domain import _OrderingDomain
from legoai.reference.secret import _ProvisionedSecretSource
from tests.support.remote_attempt_scenario import (
    NOW,
    SCOPE,
    attempt,
    open_store,
)

SECRET_CANARY = "kisski-secret-CANARY-DO-NOT-LEAK-938427"
PROMPT_CANARY = "PROMPT-CANARY-77aa def repository_source(): pass"
HEADER_CANARY = "Authorization: Bearer " + SECRET_CANARY
CANARIES = (SECRET_CANARY, PROMPT_CANARY, HEADER_CANARY, "repository_source")
SENT = frozenset({AttemptObservation.SENT_ALL, AttemptObservation.RESPONSE_COMPLETE})


@pytest.fixture
def path(tmp_path: Path) -> Path:
    db = tmp_path / "attempts.db"
    _RemoteAttemptStore.provision(db)
    return db


def no_leak(directory: Path, *values: object) -> None:
    for file in directory.rglob("*"):
        if file.is_file():
            data = file.read_bytes()
            for canary in CANARIES:
                assert canary.encode() not in data, (file, canary)
    for value in values:
        text = (
            "".join(traceback.format_exception(value))
            if isinstance(value, BaseException)
            else repr(value) + str(value)
        )
        for canary in CANARIES:
            assert canary not in text


# INTENDED persistence and content minimization


def test_intended_record_persists_exact_safe_identities(path: Path) -> None:
    store = open_store(path)
    value = attempt()
    receipt = store.intend(value)
    assert type(receipt) is IntendedReceipt and receipt.attempt == value
    status = store.inspect(value.attempt_id)
    assert status is not None
    assert status.state is AttemptState.INTENDED
    assert status.effective is AttemptState.UNKNOWN
    assert status.attempt == value
    assert status.attempt.secret == value.secret
    assert (status.attempt.admission_id, status.attempt.admission_revision) == (
        "admission",
        "a1",
    )
    assert (status.attempt.declaration_id, status.attempt.declaration_revision) == (
        "processor",
        "r1",
    )
    store.close()
    reopened = open_store(path, readonly=True)
    assert reopened.inspect(value.attempt_id) == status
    reopened.close()


def test_no_content_or_credential_is_stored(tmp_path: Path, path: Path) -> None:
    # A real S1 credential exists in this process; the attempt binds only its
    # revision reference and never realizes it.
    source = _ProvisionedSecretSource(_OrderingDomain(), SCOPE)
    reference = source.provision(
        "bearer-key", "remote-model-bearer", "c", SECRET_CANARY
    )
    with patch.object(_ProvisionedSecretSource, "_realize") as realize:
        store = open_store(path)
        receipt = store.intend(attempt(secret=reference.exact))
        store.claim_for_handoff(receipt)
        status = store.settle(receipt, AttemptState.COMPLETED, SENT)
        store.close()
    realize.assert_not_called()
    assert status.attempt.secret == reference.exact
    no_leak(tmp_path, status, receipt, store)
    fields = set(_remote_attempts.RemoteAttempt.__slots__)
    for word in ("prompt", "content", "message", "response", "header", "material"):
        assert not any(word in name for name in fields)


def test_credential_free_attempt_is_representable(path: Path) -> None:
    store = open_store(path)
    receipt = store.intend(attempt(secret=None))
    assert receipt.attempt.secret is None
    store.close()


# Duplicates


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"binding_id": "other-binding"},
        {"secret": SecretRevisionRef(SCOPE, "bearer-key", "s1-other", "s1-map")},
        {"admission_id": "other-admission"},
        {"model": ModelId("model-b")},
    ],
    ids=["identical", "binding", "secret", "admission", "model"],
)
def test_duplicate_attempt_id_never_admits_a_second_responsibility(
    path: Path, changes: dict[str, Any]
) -> None:
    store = open_store(path)
    store.intend(attempt())
    with pytest.raises(_Conflict):
        store.intend(attempt(**changes))
    status = store.inspect(RemoteAttemptId("attempt-1"))
    assert status is not None and status.attempt == attempt()
    store.close()


def test_one_attempt_per_execution(path: Path) -> None:
    store = open_store(path)
    store.intend(attempt())
    with pytest.raises(_Conflict):
        store.intend(attempt("attempt-2", execution_id=attempt().execution_id))
    store.close()


# The future-send seam


def test_handoff_requires_a_durable_intended_receipt_once(path: Path) -> None:
    store = open_store(path)
    receipt = store.intend(attempt())
    assert store.claim_for_handoff(receipt) == attempt()
    with pytest.raises(_ScopeDenied):
        store.claim_for_handoff(receipt)  # single use
    forged = IntendedReceipt(store, attempt("attempt-9"))
    with pytest.raises(_ScopeDenied):
        store.claim_for_handoff(forged)
    other = open_store_shared(path)
    with pytest.raises(_ScopeDenied):
        other.claim_for_handoff(receipt)
    store.close()


def open_store_shared(path: Path) -> _RemoteAttemptStore:
    """A read-only second incarnation cannot honor this incarnation's receipt."""
    return open_store(path, readonly=True)


def test_failed_intended_commit_yields_no_receipt(path: Path) -> None:
    store = open_store(path)

    def failing(conn: Any) -> None:
        raise sqlite3.OperationalError("disk I/O error")

    with patch.object(_remote_attempts, "_commit", failing):
        with pytest.raises(_StorageGap) as raised:
            store.intend(attempt())
    assert store.inspect(attempt().attempt_id) is None
    forged = IntendedReceipt(store, attempt())
    with pytest.raises(_ScopeDenied):
        store.claim_for_handoff(forged)
    no_leak(path.parent, raised.value)
    store.close()


def test_settled_attempt_cannot_be_claimed(path: Path) -> None:
    store = open_store(path)
    receipt = store.intend(attempt())
    store.settle(
        receipt,
        AttemptState.NOT_SENT,
        frozenset({AttemptObservation.CANCELLED_BEFORE_SEND}),
    )
    with pytest.raises(_ScopeDenied):
        store.claim_for_handoff(receipt)
    store.close()


# Terminal outcomes and transitions


@pytest.mark.parametrize(
    ("state", "observations"),
    [
        (AttemptState.NOT_SENT, {AttemptObservation.REFUSED_AT_GATE}),
        (AttemptState.NOT_SENT, {AttemptObservation.CANCELLED_BEFORE_SEND}),
        (
            AttemptState.PROVIDER_REJECTED,
            {AttemptObservation.SENT_ALL, AttemptObservation.RESPONSE_COMPLETE},
        ),
        (
            AttemptState.COMPLETED,
            {AttemptObservation.SENT_ALL, AttemptObservation.RESPONSE_COMPLETE},
        ),
        (AttemptState.UNKNOWN, set()),
        (AttemptState.UNKNOWN, {AttemptObservation.SENT_PARTIAL}),
    ],
    ids=["refused", "cancelled", "rejected", "completed", "unknown", "partial"],
)
def test_terminal_outcomes_are_final(
    path: Path, state: AttemptState, observations: set[AttemptObservation]
) -> None:
    store = open_store(path)
    receipt = store.intend(attempt())
    status = store.settle(receipt, state, frozenset(observations))
    assert status.state is state and status.effective is state
    assert status.settled_at == NOW
    for later in AttemptState:
        with pytest.raises((_ScopeDenied, _Conflict, ValueError)):
            store.settle(receipt, later, frozenset())
    with pytest.raises(_Conflict):
        store.reconcile_unknown(attempt().attempt_id)
    store.close()


@pytest.mark.parametrize(
    ("state", "observations"),
    [
        (AttemptState.NOT_SENT, set()),
        (AttemptState.NOT_SENT, {AttemptObservation.SENT_PARTIAL}),
        (AttemptState.NOT_SENT, {AttemptObservation.SENT_UNKNOWN}),
        (AttemptState.COMPLETED, set()),
        (AttemptState.COMPLETED, {AttemptObservation.SENT_ALL}),
        (
            AttemptState.COMPLETED,
            {AttemptObservation.RESPONSE_COMPLETE, AttemptObservation.SENT_NONE},
        ),
        (
            AttemptState.COMPLETED,
            {
                AttemptObservation.RESPONSE_COMPLETE,
                AttemptObservation.RESPONSE_INCOMPLETE,
            },
        ),
        (AttemptState.PROVIDER_REJECTED, {AttemptObservation.RESPONSE_INCOMPLETE}),
    ],
    ids=[
        "not-sent-without-proof",
        "not-sent-partial",
        "not-sent-unknown",
        "completed-without-response",
        "completed-sent-only",
        "completed-but-none-sent",
        "completed-incomplete",
        "rejected-incomplete",
    ],
)
def test_outcomes_are_never_inferred_from_missing_evidence(
    path: Path, state: AttemptState, observations: set[AttemptObservation]
) -> None:
    store = open_store(path)
    receipt = store.intend(attempt())
    with pytest.raises(_Conflict):
        store.settle(receipt, state, frozenset(observations))
    status = store.inspect(attempt().attempt_id)
    assert status is not None and status.state is AttemptState.INTENDED
    assert status.effective is AttemptState.UNKNOWN
    store.close()


def test_intended_is_never_a_settlement(path: Path) -> None:
    store = open_store(path)
    receipt = store.intend(attempt())
    with pytest.raises(ValueError):
        store.settle(receipt, AttemptState.INTENDED, frozenset())
    store.close()


def test_after_handoff_only_transport_proof_supports_not_sent(path: Path) -> None:
    store = open_store(path)
    receipt = store.intend(attempt())
    store.claim_for_handoff(receipt)
    with pytest.raises(_Conflict):
        store.settle(
            receipt,
            AttemptState.NOT_SENT,
            frozenset({AttemptObservation.CANCELLED_BEFORE_SEND}),
        )
    status = store.settle(
        receipt, AttemptState.NOT_SENT, frozenset({AttemptObservation.SENT_NONE})
    )
    assert status.state is AttemptState.NOT_SENT
    store.close()


def test_cancellation_before_intended_records_nothing(path: Path) -> None:
    store = open_store(path)

    def cancelled(conn: Any) -> None:
        raise asyncio.CancelledError

    with patch.object(_remote_attempts, "_commit", cancelled):
        with pytest.raises(asyncio.CancelledError):
            store.intend(attempt())
    assert store.inspect(attempt().attempt_id) is None
    assert store.unsettled() == ()
    store.close()


# Recovery: inspection only, never a resend


def test_restart_reports_unsettled_as_unknown_read_only(path: Path) -> None:
    store = open_store(path)
    store.intend(attempt())
    store.close()
    before = path.read_bytes()
    unsettled = _inspect_attempts(path, _OrderingDomain(), lambda: NOW)
    assert unsettled is not None and len(unsettled) == 1
    assert unsettled[0].state is AttemptState.INTENDED
    assert unsettled[0].effective is AttemptState.UNKNOWN
    assert path.read_bytes() == before  # inspection wrote nothing
    # A new writer incarnation can only reconcile to UNKNOWN, never claim.
    recovered = open_store(path)
    with pytest.raises(_ScopeDenied):
        recovered.claim_for_handoff(IntendedReceipt(recovered, attempt()))
    for state, observations in (
        (AttemptState.NOT_SENT, frozenset({AttemptObservation.SENT_NONE})),
        (AttemptState.COMPLETED, SENT),
    ):
        with pytest.raises(_ScopeDenied):
            recovered.settle(IntendedReceipt(recovered, attempt()), state, observations)
    status = recovered.reconcile_unknown(attempt().attempt_id)
    assert status.state is AttemptState.UNKNOWN
    assert recovered.unsettled() == ()
    recovered.close()


def test_recovery_never_calls_provider_transport_or_secret(path: Path) -> None:
    store = open_store(path)
    store.intend(attempt())
    store.close()
    with (
        patch.object(_ProvisionedSecretSource, "_realize") as realize,
        patch("socket.socket") as sock,
        patch("urllib.request.urlopen") as urlopen,
    ):
        _inspect_attempts(path, _OrderingDomain(), lambda: NOW)
        recovered = open_store(path)
        recovered.reconcile_unknown(attempt().attempt_id)
        recovered.close()
    realize.assert_not_called()
    sock.assert_not_called()
    urlopen.assert_not_called()


@pytest.mark.parametrize(
    ("point", "expected"),
    [
        (1, None),
        (2, AttemptState.INTENDED),
        (3, AttemptState.NOT_SENT),
        (4, AttemptState.COMPLETED),
    ],
    ids=["A-before-intended", "B-intended-before-send", "C-not-sent", "D-completed"],
)
def test_process_death_windows(
    tmp_path: Path, point: int, expected: AttemptState | None
) -> None:
    _RemoteAttemptStore.provision(tmp_path / "attempts.db")
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "tests.support.remote_attempt_scenario",
            str(tmp_path),
            str(point),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 73, completed.stderr
    store = open_store(tmp_path / "attempts.db")
    status = store.inspect(attempt().attempt_id)
    if expected is None:
        assert status is None  # A: no durable attempt, no claimable effect
    else:
        assert status is not None and status.state is expected
        if expected is AttemptState.INTENDED:
            assert status.effective is AttemptState.UNKNOWN
            assert store.reconcile_unknown(attempt().attempt_id).state is (
                AttemptState.UNKNOWN
            )
    store.close()


def test_corrupt_row_fails_closed(path: Path) -> None:
    store = open_store(path)
    store.intend(attempt())
    store.close()
    conn = sqlite3.connect(path)
    conn.execute(
        "UPDATE attempts SET state='completed', settled_at=? ", (NOW.isoformat(),)
    )
    conn.commit()
    conn.close()
    # COMPLETED without any observation is not a trustworthy outcome.
    with pytest.raises(_StorageGap):
        open_store(path)
    assert _inspect_attempts(path, _OrderingDomain(), lambda: NOW) is None


def test_tampered_record_identity_fails_closed(path: Path) -> None:
    store = open_store(path)
    store.intend(attempt())
    store.close()
    conn = sqlite3.connect(path)
    conn.execute("UPDATE attempts SET attempt_id='other'")
    conn.commit()
    conn.close()
    with pytest.raises(_StorageGap):
        open_store(path)


def test_capacity_exhaustion_fails_closed(path: Path) -> None:
    store = open_store(path)
    with patch.object(_remote_attempts, "_capacity", lambda: 2):
        store.intend(attempt("a1"))
        store.intend(attempt("a2"))
        with pytest.raises(_StorageGap):
            store.intend(attempt("a3"))
    # Nothing was deleted to make room.
    assert store.inspect(RemoteAttemptId("a1")) is not None
    assert store.inspect(RemoteAttemptId("a3")) is None
    store.close()


def test_owner_thread_and_single_writer(path: Path) -> None:
    store = open_store(path)
    errors: list[BaseException] = []

    def foreign() -> None:
        try:
            store.intend(attempt())
        except BaseException as error:
            errors.append(error)

    thread = Thread(target=foreign)
    thread.start()
    thread.join(5)
    assert len(errors) == 1 and isinstance(errors[0], _ScopeDenied)
    with pytest.raises(_StorageGap):
        open_store(path)  # a second writer incarnation is not admitted
    store.close()


def test_errors_logs_and_files_carry_no_canary(
    tmp_path: Path, path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    store = open_store(path)
    errors: list[BaseException] = []
    receipt = store.intend(attempt())
    for call in (
        lambda: store.intend(attempt()),
        lambda: store.settle(receipt, AttemptState.COMPLETED, frozenset()),
        lambda: store.claim_for_handoff(IntendedReceipt(store, attempt("x"))),
    ):
        try:
            call()
        except BaseException as error:
            errors.append(error)
    store.settle(receipt, AttemptState.UNKNOWN, frozenset())
    store.close()
    assert len(errors) == 3
    no_leak(tmp_path, *errors, receipt, store, store.__repr__())
    for canary in CANARIES:
        assert canary not in caplog.text


def test_attempt_values_reject_tenant_mismatch_and_bad_types() -> None:
    from legoai.kernel.identity import TenantId
    from legoai.kernel.references import ReferenceScope

    foreign = SecretRevisionRef(
        ReferenceScope("operator", TenantId("other")), "k", "r", "m"
    )
    with pytest.raises(ValueError):
        attempt(secret=foreign)
    with pytest.raises(TypeError):
        attempt(capability="legoai.intelligence.model.chat")
    with pytest.raises(ValueError):  # the shared aware-time check
        replace(attempt(), created_at="now")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        replace(attempt(), created_at=NOW.replace(tzinfo=None))
    assert attempt().capability == CapabilityId("legoai.intelligence.model.chat")
