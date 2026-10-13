"""Characterize current T2 over loopback TLS; never contact a real provider."""

import gzip
import json
import sqlite3
import ssl
from pathlib import Path

import pytest

from scripts import kisski_saia_qualification as probe
from scripts.tests.test_kisski_saia_qualification import (
    CANARY,
    CHAT,
    MODELS,
    Runner,
    body,
)
from tests.support.tls_server import TlsServer


class WireServer(TlsServer):
    """Discovery always succeeds; only the chat response varies.

    Reuses the existing synthetic TLS/canary boundary. Responses are literal
    protocol fixtures, independent of the production parser. Delays wait on
    the server shutdown event so failed cases do not leave sleeping threads.
    """

    def __init__(self, case: str) -> None:
        self.case = case
        self.negotiated: list[str | None] = []
        super().__init__(expected=CANARY)
        self.context.set_alpn_protocols(["h2", "http/1.1"])

    def _handle(self, conn: ssl.SSLSocket) -> None:
        self.negotiated.append(conn.selected_alpn_protocol())
        path = self._read_request(conn)
        if path is None:
            return
        if path == MODELS:
            payload = b'{"data":[{"id":"other-model"},{"id":"selected-model"}]}'
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%s"
                % (len(payload), payload)
            )
            return
        if path != CHAT:
            raise AssertionError("unexpected synthetic path")
        payload = body("KISSKI_OK")
        if self.case == "alias":
            payload = body("KISSKI_OK", "resolved-model")
        elif self.case == "finish":
            payload = payload.replace(b'"stop"', b'"length"')
        elif self.case == "compressed":
            payload = gzip.compress(payload, mtime=0)
        elif self.case == "delayed":
            self._stop.wait(0.05)
        elif self.case == "timeout":
            self._stop.wait(10)
            return

        head = b"HTTP/1.1 200 OK\r\n"
        if self.case == "http10":
            head = b"HTTP/1.0 200 OK\r\n"
        elif self.case == "http2-status":
            head = b"HTTP/2 200 OK\r\n"
        elif self.case == "interim":
            head = b"HTTP/1.1 100 Continue\r\n\r\n" + head
        # These peer-controlled values must never appear in runner output.
        head += b"X-Synthetic-Canary: " + CANARY.encode() + b"\r\n"
        if self.case in {"chunked", "malformed-chunk", "length-and-transfer"}:
            head += b"Transfer-Encoding: chunked\r\n"
            if self.case == "length-and-transfer":
                head += b"Content-Length: %d\r\n" % len(payload)
            chunks = b"%x\r\n%s\r\n0\r\n\r\n" % (len(payload), payload)
            if self.case == "malformed-chunk":
                chunks = b"not-a-size\r\n" + payload
            conn.sendall(head + b"\r\n" + chunks)
            return
        if self.case == "close-delimited":
            conn.sendall(head + b"Connection: close\r\n\r\n" + payload)
            return
        if self.case == "compressed":
            head += b"Content-Encoding: gzip\r\n"
        if self.case == "keepalive":
            head += b"Connection: keep-alive\r\n"
        length = len(payload) + (100 if self.case == "truncated" else 0)
        head += b"Content-Length: %d\r\n\r\n" % length
        if self.case == "headers-stall":
            conn.sendall(head)
            self._stop.wait(10)
            return
        conn.sendall(head + payload)
        if self.case == "keepalive":
            self._stop.wait(10)


def chat_custody(runner: Runner) -> tuple[str, list[str]]:
    prefix = "chat execution: "
    executions = [
        line.removeprefix(prefix) for line in runner.lines if line.startswith(prefix)
    ]
    assert len(executions) == 1
    path = runner.root / "remote-attempts.db"
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        rows = connection.execute(
            "SELECT state, observations FROM attempts WHERE execution_id = ?",
            (executions[0],),
        ).fetchall()
    finally:
        connection.close()
    assert len(rows) == 1
    state, encoded = rows[0]
    observations = json.loads(encoded)
    assert isinstance(state, str) and isinstance(observations, list)
    assert all(isinstance(value, str) for value in observations)
    return state, observations


@pytest.mark.parametrize(
    "case", ["complete", "delayed", "keepalive", "http10", "chunked"]
)
def test_complete_ordinary_response_without_waiting_for_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    case: str,
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    remote = WireServer(case)
    with remote:
        outcome = runner.invoke(remote, ("2", "y", "n"))
        assert outcome is probe.Outcome.CONNECTIVITY_ONLY
        assert remote.paths == ["POST " + MODELS, "POST " + CHAT]
        assert remote.connections == 2 and remote.authorized == [True, True]
        assert remote.negotiated == [None, None]
        assert remote.bodies[0] == b""
        assert json.loads(remote.bodies[1]) == {
            "model": "selected-model",
            "messages": [{"role": "user", "content": probe.TINY_PROMPT}],
            "stream": False,
            "max_tokens": 512,
        }
    assert "chat HTTP status: 200" in runner.lines
    assert "chat effect: completed" in runner.lines
    state, observations = chat_custody(runner)
    assert state == "completed"
    assert set(observations) == {"sent_all", "response_complete"}
    runner.no_leak(caplog)


@pytest.mark.parametrize(
    "case,failure",
    [
        ("timeout", "timeout"),
        ("headers-stall", "timeout"),
        ("malformed-chunk", "protocol_incompatible"),
        ("close-delimited", "protocol_incompatible"),
        ("length-and-transfer", "protocol_incompatible"),
        ("interim", "protocol_incompatible"),
        ("http2-status", "protocol_incompatible"),
        ("truncated", "provider_execution_failure"),
    ],
)
def test_discovery_success_does_not_establish_chat_framing_or_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    case: str,
    failure: str,
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    with WireServer(case) as remote:
        assert runner.invoke(remote) is probe.Outcome.INCONCLUSIVE
        assert remote.paths == ["POST " + MODELS, "POST " + CHAT]
        assert remote.connections == 2 and remote.authorized == [True, True]
    assert "discovery HTTP status: 200" in runner.lines
    assert "chat effect: unknown" in runner.lines
    assert "chat attempt state: unknown" in runner.lines
    assert f"chat model failure: {failure}" in runner.lines
    assert not any(line.startswith("chat HTTP status:") for line in runner.lines)
    state, observations = chat_custody(runner)
    assert state == "unknown"
    assert set(observations) == {"sent_all", "response_incomplete"}
    runner.no_leak(caplog)


@pytest.mark.parametrize("case", ["alias", "finish", "compressed"])
def test_complete_http_rejection_is_distinct_from_transport_incomplete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    case: str,
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    with WireServer(case) as remote:
        assert runner.invoke(remote) is probe.Outcome.CONTRACT_REJECTED
        assert remote.paths == ["POST " + MODELS, "POST " + CHAT]
    assert "chat HTTP status: 200" in runner.lines
    assert "chat attempt state: completed" in runner.lines
    assert "chat model failure: protocol_incompatible" in runner.lines
    state, observations = chat_custody(runner)
    assert state == "completed"
    assert set(observations) == {"sent_all", "response_complete"}
    runner.no_leak(caplog)
