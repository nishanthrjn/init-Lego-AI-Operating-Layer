"""Bounded receive observations, synthetic loopback only; no provider access."""

import ssl
from dataclasses import replace
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from legoai.reference._credential_https import ReceiveDiagnostics, _CredentialFlight
from scripts import kisski_saia_qualification as probe
from scripts.tests.test_kisski_saia_chat_interop import WireServer, chat_custody
from scripts.tests.test_kisski_saia_qualification import CANARY, CHAT, MODELS, Runner
from tests.unit.reference.test_credential_https import run


class DiagnosticServer(WireServer):
    def _handle(self, conn: ssl.SSLSocket) -> None:
        if self.case not in {"partial-headers", "partial-body", "malformed", "cap"}:
            super()._handle(conn)
            return
        path = self._read_request(conn)
        if path == MODELS:
            payload = b'{"data":[{"id":"other-model"},{"id":"selected-model"}]}'
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%s"
                % (len(payload), payload)
            )
        elif path == CHAT:
            if self.case == "partial-headers":
                conn.sendall(b"HTTP/1.1 200 OK\r\nX-Private: " + CANARY.encode())
                self._stop.wait(10)
            elif self.case == "partial-body":
                conn.sendall(
                    b"HTTP/1.1 200 OK\r\nContent-Length: 4096\r\n\r\n" + CANARY.encode()
                )
                self._stop.wait(10)
            elif self.case == "malformed":
                conn.sendall(
                    b"HTTP/1.1 200 OK\r\nBroken-Header\r\n\r\n" + CANARY.encode()
                )
            else:
                conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 4194305\r\n\r\n")


def observations(lines: list[str]) -> dict[str, str]:
    prefix = "chat receive "
    result: dict[str, str] = {}
    for line in lines:
        if line.startswith(prefix):
            name, _, value = line.removeprefix(prefix).partition(": ")
            result[name] = value
    return result


@pytest.mark.parametrize(
    "case,stage,first,headers",
    [
        ("timeout", "wait_first_byte", "false", "false"),
        ("partial-headers", "read_headers", "true", "false"),
        ("partial-body", "read_body", "true", "true"),
    ],
)
def test_timeout_stage_is_observed_without_changing_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    case: str,
    stage: str,
    first: str,
    headers: str,
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    with DiagnosticServer(case) as server:
        assert runner.invoke(server) is probe.Outcome.INCONCLUSIVE
        assert server.requests == 2
    facts = observations(runner.lines)
    assert facts["receive_stage"] == facts["deadline_stage"] == stage
    assert facts["first_byte_seen"] == first
    assert facts["headers_complete"] == headers
    assert facts["failure_category"] == "timeout"
    assert facts["request_fully_sent"] == "true"
    assert facts["connected"] == facts["tls_completed"] == "true"
    assert facts["body_complete"] == "false"
    assert 0 <= int(facts["total_receive_ms"]) <= 3_600_000
    if first == "false":
        assert facts["send_to_first_byte_ms"] == "unknown"
    if case == "partial-body":
        assert facts["header_status_code"] == "200"
        assert facts["body_bytes_observed"] == str(len(CANARY))
        assert facts["content_length_declared"] == "4096"
    assert "chat HTTP status: 200" not in runner.lines
    state, recorded = chat_custody(runner)
    assert state == "unknown" and set(recorded) == {"sent_all", "response_incomplete"}
    runner.no_leak(caplog)


@pytest.mark.parametrize(
    "case,framing,eof,cap,rejected",
    [
        ("truncated", "content_length", "true", "false", "false"),
        ("chunked", "chunked", "false", "false", "true"),
        ("close-delimited", "close_delimited", "false", "false", "true"),
        ("length-and-transfer", "cl_and_te", "false", "false", "true"),
        ("malformed", "unknown", "false", "false", "true"),
        ("cap", "unknown", "false", "true", "true"),
    ],
)
def test_refused_framing_reports_only_bounded_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    case: str,
    framing: str,
    eof: str,
    cap: str,
    rejected: str,
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    with DiagnosticServer(case) as server:
        assert runner.invoke(server) is probe.Outcome.INCONCLUSIVE
        assert server.requests == 2
    facts = observations(runner.lines)
    assert facts["framing"] == framing
    assert facts["eof_seen"] == eof
    assert facts["cap_reached"] == cap
    assert facts["parser_rejected"] == rejected
    assert facts["header_status_code"] == "200"
    assert facts["protocol_version"] == "http_1_1"
    assert facts["body_complete"] == "false"
    assert facts["deadline_stage"] == "unknown"
    assert "chat HTTP status: 200" not in runner.lines
    assert "chat effect: unknown" in runner.lines
    assert 0 <= int(facts["body_bytes_observed"]) <= 4_194_304
    runner.no_leak(caplog)


@pytest.mark.parametrize("case", ["complete", "delayed"])
def test_complete_receive_has_safe_timing_and_no_printable_raw_data(case: str) -> None:
    with DiagnosticServer(case) as server:
        _, result = run(server)
    diagnostic = result.diagnostics
    assert diagnostic is not None
    facts = dict(diagnostic.safe_items())
    assert facts["receive_stage"] == "complete"
    assert facts["body_complete"] == "true"
    assert facts["header_status_code"] == "200"
    assert facts["framing"] == "content_length"
    for name in (
        "send_to_first_byte_ms",
        "first_byte_to_headers_ms",
        "headers_to_body_complete_ms",
        "total_receive_ms",
    ):
        assert 0 <= int(facts[name]) <= 3_600_000
    printable = repr(diagnostic) + repr(diagnostic.safe_items()) + repr(result)
    assert CANARY not in printable and "KISSKI_OK" not in printable
    assert "X-Synthetic-Canary" not in printable


@pytest.mark.parametrize("fault", ["collection", "projection", "accessor"])
def test_diagnostic_failure_cannot_replay_or_change_custody(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    fault: str,
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    owner: Any
    if fault == "collection":
        owner, attribute = _CredentialFlight, "_update_diagnostics"
    elif fault == "projection":
        owner, attribute = ReceiveDiagnostics, "safe_items"
    else:
        owner, attribute = probe, "_remote_chat_receive_diagnostics"
    with patch.object(owner, attribute, side_effect=ValueError(CANARY)):
        with DiagnosticServer("chunked") as server:
            assert runner.invoke(server) is probe.Outcome.INCONCLUSIVE
            assert server.requests == 2
    assert "chat receive diagnostics: unavailable" in runner.lines
    assert "chat model failure: protocol_incompatible" in runner.lines
    state, recorded = chat_custody(runner)
    assert state == "unknown" and set(recorded) == {"sent_all", "response_incomplete"}
    runner.no_leak(caplog)


def test_raw_data_injected_into_projection_is_rejected() -> None:
    diagnostic = replace(ReceiveDiagnostics(), framing=cast(Any, CANARY))
    with pytest.raises(ValueError, match="^invalid receive diagnostic$"):
        diagnostic.safe_items()
    assert CANARY not in repr(diagnostic)


def test_exact_safe_runner_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    expected = ReceiveDiagnostics().safe_items()
    with patch.object(probe, "_remote_chat_receive_diagnostics", return_value=expected):
        with DiagnosticServer("chunked") as server:
            assert runner.invoke(server) is probe.Outcome.INCONCLUSIVE
    assert [line for line in runner.lines if line.startswith("chat receive ")] == [
        f"chat receive {name}: {value}" for name, value in expected
    ]


@pytest.mark.parametrize("selection", ["selected-model", "2", "absent"])
def test_diagnostic_mode_uses_exact_id_and_never_runs_json_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selection: str
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    answers = iter((selection, "y"))
    with DiagnosticServer("complete") as server:
        outcome = probe.run(
            runner.config(server),
            ask=lambda _: next(answers),
            write=runner.lines.append,
            diagnostic_only=True,
        )
        if selection == "selected-model":
            assert outcome is probe.Outcome.CONNECTIVITY_ONLY
            assert server.requests == 2
        else:
            assert outcome is probe.Outcome.DECLINED
            assert server.requests == 1


def test_diagnostic_plan_is_inert_and_requires_separate_authorization() -> None:
    with (
        patch("socket.socket", side_effect=AssertionError("network")),
        patch.object(probe, "open_credential_source", side_effect=AssertionError("S1")),
        patch("builtins.input", side_effect=AssertionError("input")),
    ):
        assert probe.main(["--receive-diagnostic"]) == 0
    lines = probe.plan_lines(diagnostic_only=True)
    assert any("Stage 3: disabled" in line for line in lines)
    assert any("Maximum: 1 discovery + 1 chat;" in line for line in lines)
    assert lines[-1].endswith(probe.DIAGNOSTIC_AUTHORIZATION)


@pytest.mark.parametrize("authorization", ["", probe.AUTHORIZATION])
def test_original_authorization_does_not_authorize_diagnostic_mode(
    authorization: str,
) -> None:
    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.stdout.isatty", return_value=True),
        patch("builtins.input", return_value=authorization),
        patch("tempfile.mkdtemp", side_effect=AssertionError("custody")),
        patch.object(probe, "run", side_effect=AssertionError("live")),
    ):
        assert probe.main(["--live", "--receive-diagnostic"]) == 2


@pytest.mark.parametrize("fault", ["collection", "projection"])
def test_diagnostic_failure_preserves_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    owner: Any
    if fault == "collection":
        owner, attribute = _CredentialFlight, "_update_diagnostics"
    else:
        owner, attribute = ReceiveDiagnostics, "safe_items"
    with patch.object(owner, attribute, side_effect=ValueError(CANARY)):
        with DiagnosticServer("complete") as server:
            outcome = runner.invoke(server, ("2", "y", "n"))
            assert outcome is probe.Outcome.CONNECTIVITY_ONLY
            assert server.requests == 2
    state, recorded = chat_custody(runner)
    assert state == "completed"
    assert set(recorded) == {"sent_all", "response_complete"}
