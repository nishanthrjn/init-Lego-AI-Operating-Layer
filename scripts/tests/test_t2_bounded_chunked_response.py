"""Bounded T2 contracts: synthetic loopback TLS and deterministic parser clocks."""

import ssl
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from legoai.reference._credential_https import (
    SendProgress,
    TransportError,
    TransportFailure,
    _Chunked,
    _CredentialFlight,
)
from scripts import kisski_saia_qualification as probe
from scripts.tests.test_kisski_saia_chat_interop import chat_custody
from scripts.tests.test_kisski_saia_qualification import (
    CANARY,
    CHAT,
    MODELS,
    Runner,
    body,
)
from tests.support.tls_server import TlsServer
from tests.unit.reference.test_credential_https import TOKEN, run

HEAD = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
END = b"0\r\n\r\n"


class ResponseServer(TlsServer):
    def __init__(
        self,
        parts: tuple[bytes, ...],
        *,
        stall: bool = False,
        delay: float = 0,
        expected: str = TOKEN,
    ) -> None:
        self.parts, self.stall, self.delay = parts, stall, delay
        super().__init__(expected=expected)

    def _handle(self, conn: ssl.SSLSocket) -> None:
        path = self._read_request(conn)
        if path == MODELS:
            payload = b'{"data":[{"id":"other-model"},{"id":"selected-model"}]}'
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%s"
                % (len(payload), payload)
            )
            return
        assert path == CHAT
        for part in self.parts:
            if self.delay and self._stop.wait(self.delay):
                return
            conn.sendall(part)
        if self.stall:
            self._stop.wait(10)


@pytest.mark.parametrize(
    "wire,expected",
    [
        (b"1\r\nx\r\n" + END, b"x"),
        (b"1\r\na\r\n2\r\nbc\r\n" + END, b"abc"),
        (b"A\r\n0123456789\r\n" + END, b"0123456789"),
        (b"a\r\n0123456789\r\n" + END, b"0123456789"),
        (END, b""),
        (b"000001\r\nx\r\n000000\r\n\r\n", b"x"),
        (b"4\r\n\r\n\r\n\r\n" + END, b"\r\n\r\n"),
    ],
)
def test_valid_tls_chunked(wire: bytes, expected: bytes) -> None:
    with ResponseServer((HEAD + wire,)) as server:
        _, observation = run(server)
    assert observation.response is not None
    assert observation.response.body == expected
    assert observation.progress is SendProgress.ALL
    assert server.connections == server.requests == 1
    diagnostic = observation.diagnostics
    assert diagnostic is not None and diagnostic.body_complete
    assert diagnostic.terminal_chunk_seen is True
    assert diagnostic.decoded_body_bytes == len(expected)
    assert diagnostic.body_bytes_observed == len(wire)
    assert diagnostic.trailer_present is False


def test_every_byte_segmentation_and_multiple_chunks_per_feed() -> None:
    wire = b"1\r\na\r\n2\r\nbc\r\n" + END
    for size in (1, 2, 3, 7, len(wire)):
        parser = _Chunked(time.monotonic() + 10)
        for start in range(0, len(wire), size):
            complete = parser.feed(wire[start : start + size])
        assert complete and parser.body == b"abc"
        assert parser.chunks == 2
        assert not parser.line
    parts = (HEAD, b"1", b"\r", b"\na", b"\r\n2\r\nb", b"c\r\n", END)
    with ResponseServer(parts) as server:
        _, observation = run(server)
    assert observation.response is not None and observation.response.body == b"abc"


@pytest.mark.parametrize(
    "wire",
    [
        b"\r\n",
        b"+1\r\n",
        b"-1\r\n",
        b"0x1\r\n",
        b" 1\r\n",
        b"1 \r\n",
        b"Z\r\n",
        b"1\n",
        b"1\rX\n",
        b"0000001\r\n",
        b"1;ext=CANARY\r\nx\r\n" + END,
        b"1\r\nx!\n" + END,
        b"2\r\nx",
        b"1\r\nx\r\n",
        b"0\r\n",
        b"0\r\n\r",
        b"0\r\nX-Private: CANARY\r\n\r\n",
        b"0\r\nX: CANARY\r\nY: CANARY\r\n\r\n",
        b"0\r\n\n",
        END + b"surplus",
        b"400001\r\n",
        b"FFFFFF\r\n",
    ],
    ids=[f"refusal-{index}" for index in range(22)],
)
def test_malformed_or_incomplete_tls_is_never_delivered(wire: bytes) -> None:
    with ResponseServer((HEAD + wire,)) as server:
        _, observation = run(server)
    assert observation.response is None
    assert observation.progress is SendProgress.ALL
    assert observation.failure is TransportFailure.PROTOCOL
    assert server.requests == server.connections == 1
    assert "CANARY" not in repr(observation)
    assert observation.diagnostics is not None
    assert "CANARY" not in repr(observation.diagnostics.safe_items())


@pytest.mark.parametrize(
    "fields",
    [
        b"Transfer-Encoding: gzip, chunked",
        b"Transfer-Encoding: chunked, gzip",
        b"Transfer-Encoding: chunked, chunked; x=1",
        b"Transfer-Encoding: chunked, chunked",
        b"Transfer-Encoding: identity, chunked",
        b"Transfer-Encoding: unknown",
        b"Transfer-Encoding:",
        b"Transfer-Encoding: chunked; x=1",
        b"Transfer-Encoding: \vchunked",
        b"Transfer-Encoding: chunked\r\nTransfer-Encoding: chunked",
        b"Transfer-Encoding: chunked\r\nContent-Length: 0",
        b"Content-Length: 0\r\nTransfer-Encoding: chunked",
    ],
)
def test_ambiguous_or_unsupported_coding_refused(fields: bytes) -> None:
    wire = b"HTTP/1.1 200 OK\r\n" + fields + b"\r\n\r\n" + END
    with ResponseServer((wire,)) as server:
        _, observation = run(server)
    assert observation.response is None
    assert observation.failure is TransportFailure.PROTOCOL


def test_te_case_and_safe_ows() -> None:
    head = b"HTTP/1.1 200 OK\r\nTransfer-Encoding:\t ChUnKeD \t\r\n\r\n"
    with ResponseServer((head + END,)) as server:
        _, observation = run(server)
    assert observation.response is not None and observation.response.body == b""


@pytest.mark.parametrize("version", [b"HTTP/1.0", b"HTTP/2"])
def test_chunking_requires_http11(version: bytes) -> None:
    with ResponseServer((HEAD.replace(b"HTTP/1.1", version) + END,)) as server:
        _, observation = run(server)
    assert observation.response is None


@pytest.mark.parametrize("chunked", [False, True])
def test_sse_media_type_refused_even_for_json_body(chunked: bool) -> None:
    fields = b"Transfer-Encoding: chunked" if chunked else b"Content-Length: 2"
    data = b"2\r\n{}\r\n" + END if chunked else b"{}"
    head = b"HTTP/1.1 200 OK\r\nContent-Type: Text/Event-Stream; charset=utf-8\r\n"
    with ResponseServer((head + fields + b"\r\n\r\n" + data,)) as server:
        _, observation = run(server)
    assert observation.response is None


@pytest.mark.parametrize("overflow", [False, True])
def test_decoded_aggregate_boundary(overflow: bool) -> None:
    payload = b"x" * 4194304
    wire = HEAD + b"400000\r\n" + payload + b"\r\n"
    wire += b"1\r\nx\r\n" + END if overflow else END
    with ResponseServer((wire,)) as server:
        _, observation = run(server, timeout=10)
    if overflow:
        assert observation.response is None
        assert observation.diagnostics is not None
        assert observation.diagnostics.cap_reached
    else:
        assert observation.response is not None and observation.response.body == payload
        assert observation.diagnostics is not None
        assert observation.diagnostics.decoded_body_bytes == 4194304
        assert not observation.diagnostics.cap_reached


@pytest.mark.parametrize(
    "extra,count,success",
    [(3, 6552, True), (4, 6552, False), (0, 6553, False)],
)
def test_framing_and_chunk_count_boundaries(
    extra: int, count: int, success: bool
) -> None:
    # 6552 * 5 + terminal 5 = 32765 framing bytes. Add leading zeros
    # to the first valid size line to hit exactly 32768 or exceed by one.
    wire = b"0" * extra + b"1\r\nx\r\n" * count + END
    with ResponseServer((HEAD + wire,)) as server:
        _, observation = run(server)
    assert (observation.response is not None) is success
    diagnostic = observation.diagnostics
    assert diagnostic is not None and diagnostic.chunks_observed == 6552
    assert diagnostic.cap_reached is not success


@pytest.mark.parametrize("prefix", [b"3\r\nx", b"1\r\nx\r\n"])
def test_tls_timeout_mid_data_or_before_terminal(prefix: bytes) -> None:
    with ResponseServer((HEAD + prefix,), stall=True) as server:
        _, observation = run(server, timeout=1)
    assert observation.response is None
    assert observation.failure is TransportFailure.TIMEOUT
    assert observation.progress is SendProgress.ALL
    assert server.requests == 1


def test_slow_drip_cannot_extend_attempt_deadline() -> None:
    parts = (HEAD,) + (b"1\r\nx\r\n",) * 100
    with ResponseServer(parts, delay=0.05) as server:
        _, observation = run(server, timeout=1)
    assert observation.response is None
    assert observation.failure is TransportFailure.TIMEOUT
    assert observation.diagnostics is not None
    assert not observation.diagnostics.terminal_chunk_seen


def test_buffered_parser_continuations_obey_same_deadline() -> None:
    parser = _Chunked(10)
    with patch(
        "legoai.reference._credential_https.time.monotonic", side_effect=[9, 11]
    ):
        with pytest.raises(TransportError) as raised:
            parser.feed(b"1\r\nx\r\n" + END)
    assert raised.value.failure is TransportFailure.TIMEOUT
    assert parser.deadline == 10


@pytest.mark.parametrize("chunked", [False, True])
def test_completed_header_cap_is_enforced(chunked: bool) -> None:
    field = b"Transfer-Encoding: chunked" if chunked else b"Content-Length: 0"
    head = b"HTTP/1.1 200 OK\r\nX: " + b"x" * 32768 + b"\r\n" + field + b"\r\n\r\n"
    with ResponseServer((head + (END if chunked else b""),)) as server:
        _, observation = run(server)
    assert observation.response is None
    assert observation.failure is TransportFailure.PROTOCOL


@pytest.mark.parametrize("overflow", [False, True])
def test_exact_header_size_boundary(overflow: bool) -> None:
    prefix = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nX: "
    suffix = b"\r\n\r\n"
    padding = 32768 - len(prefix) - len(suffix) + int(overflow)
    with ResponseServer((prefix + b"x" * padding + suffix + END,)) as server:
        _, observation = run(server)
    assert (observation.response is None) is overflow


@pytest.mark.parametrize("fields,success", [(64, True), (65, False)])
def test_header_field_count_boundary(fields: int, success: bool) -> None:
    head = HEAD[:-2] + b"X: y\r\n" * (fields - 1) + b"\r\n"
    with ResponseServer((head + END,)) as server:
        _, observation = run(server)
    assert (observation.response is not None) is success


def test_chunk_payload_and_headers_do_not_enter_diagnostics() -> None:
    payload = CANARY.encode()
    head = HEAD[:-2] + b"Private: " + payload + b"\r\n\r\n"
    wire = b"%x\r\n%s\r\n0\r\n\r\n" % (len(payload), payload)
    with ResponseServer((head + wire,)) as server:
        flight, observation = run(server)
    assert observation.response is not None
    assert observation.response.body == payload
    assert observation.diagnostics is not None
    rendered = repr(flight) + repr(observation) + repr(observation.response)
    rendered += repr(observation.diagnostics.safe_items())
    assert CANARY not in rendered and TOKEN not in rendered


@pytest.mark.parametrize(
    "case", ["valid", "extension", "eof", "cap", "timeout", "trailer"]
)
def test_synthetic_adapter_custody_and_diagnostic_isolation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    case: str,
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    payload = body("KISSKI_OK")
    wire = b"%x\r\n%s\r\n0\r\n\r\n" % (len(payload), payload)
    valid = case == "valid"
    refused = {
        "extension": b"1;" + CANARY.encode() + b"\r\nx\r\n" + END,
        "eof": b"3\r\nx",
        "cap": b"400001\r\n",
        "timeout": b"3\r\nx",
        "trailer": b"0\r\nPrivate: " + CANARY.encode() + b"\r\n\r\n",
    }
    wire = refused.get(case, wire)
    with ResponseServer(
        (HEAD + wire,), expected=CANARY, stall=case == "timeout"
    ) as server:
        outcome = runner.invoke(server, ("2", "y", "n"))
        assert server.requests == server.connections == 2  # discovery + one chat
    expected = probe.Outcome.CONNECTIVITY_ONLY if valid else probe.Outcome.INCONCLUSIVE
    assert outcome is expected
    state, facts = chat_custody(runner)
    assert state == ("completed" if valid else "unknown")
    completion = "response_complete" if valid else "response_incomplete"
    assert set(facts) == {"sent_all", completion}
    runner.no_leak(caplog)


@pytest.mark.parametrize("valid", [False, True])
def test_failed_diagnostic_collector_cannot_change_transport(valid: bool) -> None:
    wire = b"1\r\nx\r\n" + END if valid else b"Z\r\n"
    with patch.object(
        _CredentialFlight, "_update_diagnostics", side_effect=ValueError(CANARY)
    ):
        with ResponseServer((HEAD + wire,)) as server:
            _, observation = run(server)
    assert (observation.response is not None) is valid
    assert observation.diagnostics is None and server.requests == 1


@pytest.mark.parametrize("case", ["sse", "alias", "finish"])
def test_chunk_completion_does_not_bypass_application_contracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    payload = body("KISSKI_OK")
    if case == "sse":
        payload = b"data: " + payload + b"\n\n"
    elif case == "alias":
        payload = body("KISSKI_OK", "other-model")
    else:
        payload = payload.replace(b'"stop"', b'"length"')
    wire = b"%x\r\n%s\r\n0\r\n\r\n" % (len(payload), payload)
    runner = Runner(tmp_path, monkeypatch)
    with ResponseServer((HEAD + wire,), expected=CANARY) as server:
        assert runner.invoke(server) is probe.Outcome.CONTRACT_REJECTED
        assert server.requests == 2
    state, facts = chat_custody(runner)
    assert state == "completed"
    assert set(facts) == {"sent_all", "response_complete"}


@pytest.mark.parametrize("mode", ["ok", "truncated", "oversized", "timeout", "chunked"])
def test_existing_fixture_length_contracts_and_new_plain_chunk_body(mode: str) -> None:
    with TlsServer(mode, expected=TOKEN) as server:
        _, observation = run(server, timeout=1)
    assert (observation.response is not None) is (mode in {"ok", "chunked"})
    if mode == "chunked":
        assert observation.response is not None
        assert observation.response.body == b"hello"
    else:
        assert observation.diagnostics is not None
        assert observation.diagnostics.chunks_observed is None
