"""CREDENTIAL-HTTPS-T2 transport: verified TLS, bounded HTTP framing.

Direct transport tests against the process-local synthetic TLS server, with a
synthetic token. No Secret owner here (the composition tests cover the gated
handoff); no external network, proxy or provider.
"""

import socket
import ssl
from pathlib import Path

import pytest

from legoai.reference._credential_https import (
    HandoffObservation,
    HttpsTarget,
    SendProgress,
    TransportError,
    TransportFailure,
    _CredentialFlight,
    tls_context,
)
from tests.support.tls_server import TEST_CA, TlsServer

TOKEN = "t2-token-CANARY-DO-NOT-LEAK-55021"
BODY = b'{"model":"m","messages":[{"role":"user","content":"PROMPT-CANARY-91"}]}'


def target(port: int, host: str = "localhost") -> HttpsTarget:
    origin = f"https://{host}" + ("" if port == 443 else f":{port}")
    return HttpsTarget.for_endpoint(origin, "/v1", "/chat/completions")


def flight(port: int, *, timeout: float = 5.0, body: bytes = BODY) -> _CredentialFlight:
    return _CredentialFlight(target(port), tls_context(TEST_CA), body, timeout=timeout)


def run(
    server: TlsServer, *, timeout: float = 5.0
) -> tuple[_CredentialFlight, HandoffObservation]:
    """Ungated direct drive of one flight (the gate is tested elsewhere)."""
    f = flight(server.port, timeout=timeout)
    try:
        f.open()
        f._begin(TOKEN.encode())
        f._send_once()
        while f._flight_pending:
            f._wait_writable()
            f._send_once()
        response = f.receive()
        return f, f.observe(response)
    finally:
        f.close()


def test_tls_context_is_verified_and_never_key_logs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SSLKEYLOGFILE", str(tmp_path / "keys.log"))
    for context in (tls_context(), tls_context(TEST_CA)):
        assert context.check_hostname is True
        assert context.verify_mode is ssl.CERT_REQUIRED
        assert context.minimum_version is ssl.TLSVersion.TLSv1_2
        assert context.keylog_filename is None
    with TlsServer(expected=TOKEN) as server:
        run(server)
    assert not (tmp_path / "keys.log").exists()


def test_unverified_contexts_are_refused() -> None:
    weak = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    weak.check_hostname = False
    weak.verify_mode = ssl.CERT_NONE
    with pytest.raises(TransportError) as raised:
        _CredentialFlight(target(443), weak, BODY, timeout=1)
    assert raised.value.failure is TransportFailure.TLS


@pytest.mark.parametrize(
    ("origin", "api_root", "path"),
    [
        ("http://localhost:8443", "/v1", "/chat/completions"),
        ("https://localhost:8443", "/v1/", "/chat/completions"),
        ("https://Localhost:8443", "/v1", "/chat/completions"),
        ("https://localhost:8443", "/v1", "/admin"),
        ("https://user@localhost:8443", "/v1", "/chat/completions"),
    ],
    ids=["plaintext", "root", "case", "path", "userinfo"],
)
def test_targets_are_exact_https_only(origin: str, api_root: str, path: str) -> None:
    with pytest.raises(TransportError) as raised:
        HttpsTarget.for_endpoint(origin, api_root, path)
    assert raised.value.failure is TransportFailure.ORIGIN


def test_target_shape() -> None:
    t = HttpsTarget.for_endpoint("https://models.example.org", "/v1", "/embeddings")
    assert (t.host, t.port, t.origin, t.request_path) == (
        "models.example.org",
        443,
        "https://models.example.org",
        "/v1/embeddings",
    )


@pytest.mark.parametrize(
    ("cert", "failure"),
    [("untrusted.pem", TransportFailure.TLS), ("wrong-host.pem", TransportFailure.TLS)],
    ids=["untrusted", "hostname-mismatch"],
)
def test_bad_certificates_fail_before_any_request(
    cert: str, failure: TransportFailure
) -> None:
    with TlsServer(cert=cert, expected=TOKEN) as server:
        f = flight(server.port)
        with pytest.raises(TransportError) as raised:
            f.open()
        f.close()
        assert raised.value.failure is failure
        assert server.requests == 0
        assert f.progress() is SendProgress.NONE


def test_connection_refused_is_a_connect_failure() -> None:
    probe = socket.create_server(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    f = flight(port, timeout=2)
    with pytest.raises(TransportError) as raised:
        f.open()
    f.close()
    assert raised.value.failure in (TransportFailure.CONNECT, TransportFailure.TIMEOUT)


def test_no_credential_before_the_handshake() -> None:
    f = flight(443)
    with pytest.raises(TransportError):
        f._begin(TOKEN.encode())  # no verified TLS session exists yet
    f.close()


def test_exact_minimal_request_shape() -> None:
    with TlsServer(expected=TOKEN) as server:
        _, observation = run(server)
    assert observation.progress is SendProgress.ALL
    assert observation.response is not None and observation.response.status == 200
    assert server.paths == ["POST /v1/chat/completions"]
    assert server.hosts == [f"localhost:{server.port}"]
    assert server.authorized == [True]
    # Host, Content-Type, Accept, Authorization, Content-Length, Connection.
    assert server.header_lines == [6]
    assert server.bodies == [BODY]
    assert server.connections == 1


@pytest.mark.parametrize("mode", ["401", "403", "429", "500", "302"])
def test_complete_non_success_responses_are_returned_not_followed(mode: str) -> None:
    with TlsServer(mode, expected=TOKEN) as server:
        _, observation = run(server)
    assert observation.response is not None
    assert observation.response.status == int(mode)
    assert server.connections == 1  # a redirect is never followed


@pytest.mark.parametrize(
    "mode",
    ["truncated", "malformed", "malformed-chunk", "oversized", "close-before-request"],
)
def test_incomplete_or_unsupported_responses_are_not_complete(mode: str) -> None:
    with TlsServer(mode, expected=TOKEN) as server:
        _, observation = run(server)
    assert observation.response is None


def test_response_timeout_is_bounded_and_incomplete() -> None:
    with TlsServer("timeout", expected=TOKEN) as server:
        _, observation = run(server, timeout=1.0)
    assert observation.progress is SendProgress.ALL
    assert observation.response is None


def test_oversized_request_body_refused() -> None:
    with pytest.raises(TransportError) as raised:
        flight(443, body=b"x" * (1_048_577))
    assert raised.value.failure is TransportFailure.PROTOCOL


def test_resources_are_released_on_every_path() -> None:
    with TlsServer(cert="untrusted.pem") as server:
        for _ in range(10):
            f = flight(server.port)
            with pytest.raises(TransportError):
                f.open()
            f.close()
            f.close()  # idempotent
            assert f._sock is None and f._selector is None


def test_flight_repr_and_errors_never_carry_the_token() -> None:
    with TlsServer(expected=TOKEN) as server:
        f, observation = run(server)
    text = repr(f) + repr(observation) + str(TransportError(TransportFailure.TLS))
    assert TOKEN not in text and "PROMPT-CANARY" not in text
    assert not f._pending
