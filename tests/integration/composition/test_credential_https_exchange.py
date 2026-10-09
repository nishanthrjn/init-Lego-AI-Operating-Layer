"""CREDENTIAL-HTTPS-T2 end to end (private offline seam, not REMOTE support).

durable INTENDED -> claim_for_handoff -> S1 exact-use handoff under the
shared ordering domain -> nonblocking TLS writes to a synthetic local server ->
bounded observation -> the invocation plane settles the attempt. Synthetic
canaries only; no external network, provider or KISSKI.
"""

import logging
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from legoai.execution.values import ExecutionId
from legoai.governance.secret import UseRecoveryCategory
from legoai.kernel.effects import EffectExtent
from legoai.reference._credential_https import (
    HttpsTarget,
    SendProgress,
    _CredentialFlight,
    tls_context,
)
from legoai.reference._custody_sqlite import _ScopeDenied
from legoai.reference._remote_attempts import (
    AttemptObservation,
    AttemptState,
    IntendedReceipt,
    RemoteAttemptId,
    _RemoteAttemptStore,
)
from legoai.reference._secret_domain import _OrderingDomain
from legoai.reference.secret import _ProvisionedSecretSource
from legoai.runtime._composition.credential_https import effect, exchange
from tests.support.remote_attempt_scenario import attempt
from tests.support.secret_ref_scenario import scenario
from tests.support.tls_server import TEST_CA, TlsServer

CANARY = "kisski-secret-CANARY-DO-NOT-LEAK-938427"
BODY = b'{"model":"model-a","messages":[{"role":"user","content":"PROMPT-CANARY-31"}]}'
MARGIN = timedelta(minutes=5)


@dataclass
class Setup:
    s: Any
    store: _RemoteAttemptStore
    receipt: IntendedReceipt
    target: HttpsTarget
    directory: Path


@contextmanager
def setup(tmp_path: Path, server: TlsServer) -> Iterator[Setup]:
    with scenario(tmp_path, material=CANARY) as s:
        plan = s._request.plan
        origin = f"https://localhost:{server.port}"
        value = replace(
            attempt(),
            attempt_id=RemoteAttemptId(plan.use_id.value),
            execution_id=ExecutionId("exec-t2"),
            configuration=plan.configuration,
            endpoint_origin=origin,
            secret=plan.secret,
        )
        path = tmp_path / "attempts.db"
        _RemoteAttemptStore.provision(path)
        store = _RemoteAttemptStore(path, _OrderingDomain(), lambda: plan.prepared_at)
        try:
            receipt = store.intend(value)
            target = HttpsTarget.for_endpoint(origin, "/v1", "/chat/completions")
            yield Setup(s, store, receipt, target, tmp_path)
        finally:
            store.close()


def go(x: Setup, **options: Any) -> Any:
    return exchange(
        x.store,
        options.pop("receipt", x.receipt),
        x.s,
        x.s._request,
        options.pop("target", x.target),
        tls_context(TEST_CA),
        BODY,
        timeout=options.pop("timeout", 5.0),
        margin=options.pop("margin", MARGIN),
    )


def leak_free(directory: Path, *values: object, log: str = "") -> None:
    for file in directory.rglob("*"):
        if file.is_file():
            data = file.read_bytes()
            assert CANARY.encode() not in data, file
            assert b"PROMPT-CANARY" not in data, file
    for value in values:
        text = (
            "".join(traceback.format_exception(value))
            if isinstance(value, BaseException)
            else repr(value) + str(value)
        )
        assert CANARY not in text and "Bearer" not in text
    assert CANARY not in log


# Outcomes


def test_complete_success_is_completed_and_attributed(tmp_path: Path) -> None:
    with TlsServer(expected=CANARY) as server, setup(tmp_path, server) as x:
        observation, status = go(x)
        assert server.authorized == [True] and server.bodies == [BODY]
        assert observation.progress is SendProgress.ALL
        assert observation.response is not None and observation.response.status == 200
        assert status.state is AttemptState.COMPLETED
        assert effect(status.state) is EffectExtent.COMPLETED
        secret_status = x.s._inspect(x.s._request)
        assert secret_status.category is UseRecoveryCategory.ACCEPTED_ATTRIBUTED
        leak_free(x.directory, observation, status)


@pytest.mark.parametrize("mode", ["401", "403", "429", "500"])
def test_complete_rejection_is_provider_rejected(tmp_path: Path, mode: str) -> None:
    with TlsServer(mode, expected=CANARY) as server, setup(tmp_path, server) as x:
        observation, status = go(x)
        assert observation.response.status == int(mode)
        assert status.state is AttemptState.PROVIDER_REJECTED
        assert effect(status.state) is EffectExtent.NONE
        assert server.connections == 1  # no retry


@pytest.mark.parametrize("mode", ["truncated", "malformed", "close-before-request"])
def test_sent_without_complete_response_is_unknown(tmp_path: Path, mode: str) -> None:
    with TlsServer(mode, expected=CANARY) as server, setup(tmp_path, server) as x:
        observation, status = go(x)
        assert observation.response is None
        assert status.state is AttemptState.UNKNOWN
        assert effect(status.state) is EffectExtent.UNKNOWN


def test_response_timeout_stays_unknown(tmp_path: Path) -> None:
    with TlsServer("timeout", expected=CANARY) as server, setup(tmp_path, server) as x:
        observation, status = go(x, timeout=1.0)
        assert observation.progress is SendProgress.ALL
        assert status.state is AttemptState.UNKNOWN
        assert AttemptObservation.RESPONSE_INCOMPLETE in status.observations


@pytest.mark.parametrize("cert", ["untrusted.pem", "wrong-host.pem"])
def test_tls_failure_is_not_sent_without_realizing_the_secret(
    tmp_path: Path, cert: str
) -> None:
    with (
        TlsServer(cert=cert, expected=CANARY) as server,
        setup(tmp_path, server) as x,
        patch.object(_ProvisionedSecretSource, "_realize") as realize,
    ):
        observation, status = go(x)
        realize.assert_not_called()
        assert server.requests == 0
        assert observation.progress is SendProgress.NONE
        assert status.state is AttemptState.NOT_SENT
        # The receipt was never claimed and the Secret never used.
        assert x.s._inspect(x.s._request) is None


# Final-gate currentness before H


@pytest.mark.parametrize("kind", ["retire", "close", "cancel", "grant", "margin"])
def test_refused_at_the_final_gate_sends_nothing(tmp_path: Path, kind: str) -> None:
    with TlsServer(expected=CANARY) as server, setup(tmp_path, server) as x:
        source = x.s._state._source
        margin = MARGIN
        if kind == "retire":
            source.retire(x.s._request.plan.secret)
        elif kind == "close":
            source.close()
        elif kind == "cancel":
            x.s._state.cancel()
        elif kind == "grant":
            x.s._authorization.grant_state.revoke(x.s._request.plan.grant_id)
        else:
            margin = timedelta(hours=2)  # less than the margin remains
        observation, status = go(x, margin=margin)
        assert server.requests == 0
        assert observation.progress is SendProgress.NONE
        assert status.state is AttemptState.NOT_SENT
        assert status.observations == frozenset({AttemptObservation.SENT_NONE})


# Partial writes and continuations


class Throttle:
    """Accept at most `limit` bytes per nonblocking send; optionally block once."""

    def __init__(self, limit: int, *, block_first: bool = False) -> None:
        self.limit, self.block_first, self.calls = limit, block_first, 0
        self.original = _CredentialFlight._send_some

    def __call__(self, flight: _CredentialFlight, data: bytes) -> int:
        self.calls += 1
        if self.block_first and self.calls == 1:
            raise BlockingIOError
        return self.original(flight, data[: self.limit])

    def method(self) -> Any:
        def send(flight: _CredentialFlight, data: bytes) -> int:
            return self(flight, data)

        return send


def test_partial_and_would_block_writes_complete_under_the_gate(tmp_path: Path) -> None:
    throttle = Throttle(97, block_first=True)
    with (
        TlsServer(expected=CANARY) as server,
        setup(tmp_path, server) as x,
        patch.object(_CredentialFlight, "_send_some", throttle.method()),
    ):
        observation, status = go(x)
        # One forced would-block, then one gated continuation per 97 bytes.
        assert throttle.calls >= 4
        assert observation.progress is SendProgress.ALL
        assert status.state is AttemptState.COMPLETED
        assert server.authorized == [True]


@pytest.mark.parametrize("kind", ["retire", "close", "cancel", "grant"])
def test_invalidation_between_partial_writes_stops_and_stays_unknown(
    tmp_path: Path, kind: str
) -> None:
    throttle = Throttle(97)
    waits = {"n": 0}
    with TlsServer(expected=CANARY) as server, setup(tmp_path, server) as x:
        original_wait = _CredentialFlight._wait_writable

        def wait(flight: _CredentialFlight) -> None:
            # Outside the domain, while waiting for writability.
            waits["n"] += 1
            if waits["n"] == 2:
                if kind == "retire":
                    x.s._state._source.retire(x.s._request.plan.secret)
                elif kind == "close":
                    x.s._state._source.close()
                elif kind == "cancel":
                    x.s._state.cancel()
                else:
                    x.s._authorization.grant_state.revoke(x.s._request.plan.grant_id)
            original_wait(flight)

        with (
            patch.object(_CredentialFlight, "_send_some", throttle.method()),
            patch.object(_CredentialFlight, "_wait_writable", wait),
        ):
            observation, status = go(x)
        assert observation.progress is SendProgress.PARTIAL
        assert observation.stopped is True
        assert throttle.calls == 2  # no continuation after the invalidation won
        assert status.state is AttemptState.UNKNOWN
        assert AttemptObservation.SENT_PARTIAL in status.observations
        # Already-accepted bytes are never denied: the Secret use stays accepted.
        assert x.s._inspect(x.s._request).accepted_fact is not None


def test_wall_clock_violation_after_h_is_detected_not_prevented(tmp_path: Path) -> None:
    with TlsServer(expected=CANARY) as server, setup(tmp_path, server) as x:
        original = _CredentialFlight._send_some
        expires = x.s._request.plan.expires_at

        def late(flight: _CredentialFlight, data: bytes) -> int:
            sent = original(flight, data)
            x.s._clock._instant = expires  # the wall clock passed E during H
            return sent

        with patch.object(_CredentialFlight, "_send_some", late):
            observation, status = go(x)
        assert observation.time_violation is True
        assert AttemptObservation.TIME_VALIDITY_VIOLATION in status.observations
        assert status.state is AttemptState.COMPLETED


# Receipt / claim adversarial


def test_forged_or_reused_receipts_never_realize_or_send(tmp_path: Path) -> None:
    with (
        TlsServer(expected=CANARY) as server,
        setup(tmp_path, server) as x,
        patch.object(_ProvisionedSecretSource, "_realize") as realize,
    ):
        forged = IntendedReceipt(
            x.store, replace(x.receipt.attempt, binding_id="other")
        )
        with pytest.raises(_ScopeDenied):
            go(x, receipt=forged)
        with pytest.raises(TypeError):
            go(x, receipt=object())
        realize.assert_not_called()
        assert server.requests == 0


def test_receipt_is_single_use(tmp_path: Path) -> None:
    with TlsServer(expected=CANARY) as server, setup(tmp_path, server) as x:
        go(x)
        with pytest.raises(_ScopeDenied):
            go(x)
        assert server.requests == 1


def test_recovered_attempt_cannot_be_claimed(tmp_path: Path) -> None:
    with TlsServer(expected=CANARY) as server, setup(tmp_path, server) as x:
        x.store.close()
        recovered = _RemoteAttemptStore(
            tmp_path / "attempts.db",
            _OrderingDomain(),
            lambda: x.receipt.attempt.created_at,
        )
        x.store = recovered
        with pytest.raises(_ScopeDenied):
            go(x, receipt=IntendedReceipt(recovered, x.receipt.attempt))
        assert server.requests == 0


def test_recipient_mismatch_refused_before_connecting(tmp_path: Path) -> None:
    with TlsServer(expected=CANARY) as server, setup(tmp_path, server) as x:
        other = HttpsTarget.for_endpoint(
            f"https://localhost:{server.port + 1}", "/v1", "/chat/completions"
        )
        with pytest.raises(PermissionError):
            go(x, target=other)
        assert server.connections == 0


# Leaks and ambient inputs


def test_no_canary_anywhere(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    errors: list[BaseException] = []
    with TlsServer("401", expected=CANARY) as server, setup(tmp_path, server) as x:
        observation, status = go(x)
        try:
            go(x)
        except BaseException as error:
            errors.append(error)
    leak_free(tmp_path, observation, status, *errors, log=caplog.text)


def test_ambient_proxy_ca_and_keylog_inputs_are_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.setenv(name, "http://127.0.0.1:9")
    monkeypatch.setenv("NO_PROXY", "")
    monkeypatch.setenv("SSLKEYLOGFILE", str(tmp_path / "keys.log"))
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(tmp_path / "missing.pem"))
    monkeypatch.setenv("CURL_CA_BUNDLE", str(tmp_path / "missing.pem"))
    monkeypatch.setenv("KISSKI_API_KEY", "ambient-should-never-be-used")
    monkeypatch.setenv("OPENAI_API_KEY", "ambient-should-never-be-used")
    with TlsServer(expected=CANARY) as server, setup(tmp_path, server) as x:
        _, status = go(x)
        assert status.state is AttemptState.COMPLETED
        assert server.authorized == [True]  # the provisioned credential only
    assert not (tmp_path / "keys.log").exists()
