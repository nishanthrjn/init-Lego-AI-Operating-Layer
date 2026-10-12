"""SAIA staged qualification uses loopback TLS and synthetic S1 material only."""

import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from legoai.governance.secret import SecretRef
from legoai.reference.secret import _ProvisionedSecretSource
from legoai.runtime._composition.secret import _provision_interactively
from legoai.runtime.api import HostError, RemoteDisclosureConfig
from scripts import kisski_saia_qualification as probe
from scripts.kisski_compatibility_probe import ProbeConfig
from tests.support.tls_server import TEST_CA, TlsServer

CANARY = "saia-SYNTHETIC-secret-canary-90174"
MODELS = "/v1/models"
CHAT = "/v1/chat/completions"


def body(content: str, model: str = "selected-model") -> bytes:
    return json.dumps(
        {
            "model": model,
            "choices": [
                {
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
        }
    ).encode()


def server() -> TlsServer:
    return TlsServer(
        expected=CANARY,
        methods={MODELS: "POST", CHAT: "POST"},
        responses={
            MODELS: json.dumps(
                {"data": [{"id": "other-model"}, {"id": "selected-model"}]}
            ).encode(),
            CHAT: body("KISSKI_OK"),
        },
    )


class Runner:
    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root = root
        self.lines: list[str] = []
        self.purposes: list[str] = []

        def provision(
            source: _ProvisionedSecretSource, identity: str, purpose: str, consumer: str
        ) -> SecretRef:
            self.purposes.append(purpose)
            return _provision_interactively(
                source,
                identity,
                purpose,
                consumer,
                read=lambda _: CANARY,
                interactive=lambda: True,
            )

        monkeypatch.setattr(probe, "_provision_interactively", provision)
        monkeypatch.setattr("legoai.runtime.local._provision_interactively", provision)

    def config(self, remote: TlsServer) -> ProbeConfig:
        return replace(
            probe.live_config(self.root),
            origin=f"https://localhost:{remote.port}",
            trust_anchor=TEST_CA,
            timeout_seconds=1.0,
        )

    def invoke(
        self, remote: TlsServer, answers: tuple[str, ...] = ("2", "y", "y")
    ) -> probe.Outcome:
        choices = iter(answers)
        return probe.run(
            self.config(remote), ask=lambda _: next(choices), write=self.lines.append
        )

    def no_leak(self, caplog: pytest.LogCaptureFixture) -> None:
        assert CANARY not in "\n".join(self.lines) + caplog.text
        for path in self.root.rglob("*"):
            if path.is_file():
                assert CANARY.encode() not in path.read_bytes()


@pytest.mark.parametrize("args", [[], ["--plan"]])
def test_default_and_plan_have_no_io(args: list[str]) -> None:
    with (
        patch("socket.getaddrinfo", side_effect=AssertionError("DNS")),
        patch("socket.socket", side_effect=AssertionError("network")),
        patch("builtins.input", side_effect=AssertionError("input")),
        patch.object(probe, "open_credential_source", side_effect=AssertionError("S1")),
        patch.object(tempfile, "mkdtemp", side_effect=AssertionError("custody")),
    ):
        assert probe.main(args) == 0


@pytest.mark.parametrize(
    "option", ["--token", "--api-key", "--model", "--config", "--li"]
)
def test_invalid_arguments_are_not_echoed(
    option: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as error:
        probe.main([option, CANARY])
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert CANARY not in captured.out + captured.err


@pytest.mark.parametrize("terminal", [False, True])
def test_live_requires_terminal_and_exact_authorization(terminal: bool) -> None:
    with (
        patch.object(sys.stdin, "isatty", return_value=terminal),
        patch.object(sys.stdout, "isatty", return_value=terminal),
        patch("builtins.input", return_value="no"),
        patch.object(tempfile, "mkdtemp", side_effect=AssertionError("custody")),
        patch.object(probe, "run", side_effect=AssertionError("live")),
    ):
        assert probe.main(["--live"]) == 2


def test_three_stages_exact_model_protected_bearer_and_no_raw_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    for name in ("KISSKI_API_KEY", "OPENAI_API_KEY", "SAIA_API_KEY"):
        monkeypatch.setenv(name, "wrong-SYNTHETIC-ambient-value")
    runner = Runner(tmp_path, monkeypatch)
    with server() as remote:

        def respond() -> None:
            if remote.requests == 3:
                remote.responses[CHAT] = body(probe.EXPECTED_JSON)

        remote.on_request = respond
        assert runner.invoke(remote) is probe.Outcome.PASS
        assert remote.paths == ["POST " + MODELS, "POST " + CHAT, "POST " + CHAT]
        assert remote.authorized == [True, True, True]
        assert runner.purposes == ["provider-model-discovery", "remote-model-bearer"]
        assert remote.bodies[0] == b""
        for raw, prompt in zip(
            remote.bodies[1:], (probe.TINY_PROMPT, probe.STRUCTURED_PROMPT), strict=True
        ):
            assert json.loads(raw) == {
                "model": "selected-model",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "max_tokens": 512,
            }
            assert CANARY.encode() not in raw
        assert "synthetic.txt" not in "\n".join(runner.lines)
    runner.no_leak(caplog)


@pytest.mark.parametrize("status", [400, 401, 403, 404, 408, 429, 500, 503])
def test_complete_chat_rejection_stops_without_retry_or_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    status: int,
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    with server() as remote:

        def reject_chat() -> None:
            if remote.requests == 2:
                remote.mode = str(status)
                remote.responses[CHAT] = CANARY.encode()

        remote.on_request = reject_chat
        assert runner.invoke(remote) is probe.Outcome.PROVIDER_REJECTED
        assert remote.requests == 2 and remote.authorized == [True, True]
        assert f"chat HTTP status: {status}" in runner.lines
        assert "chat effect: none" in runner.lines
        recoverability = "potentially retryable" if status in (429, 503) else "terminal"
        assert f"chat error: DependencyFailure / {recoverability}" in runner.lines
    runner.no_leak(caplog)


@pytest.mark.parametrize("mode", ["truncated", "chunked", "timeout"])
def test_incomplete_chat_is_unknown_and_not_replayed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    with server() as remote:

        def incomplete() -> None:
            if remote.requests == 2:
                remote.mode = mode

        remote.on_request = incomplete
        assert runner.invoke(remote) is probe.Outcome.INCONCLUSIVE
        assert remote.requests == 2
        assert "chat effect: unknown" in runner.lines
        assert "chat attempt state: unknown" in runner.lines


@pytest.mark.parametrize("fault", ["json", "model", "finish", "content"])
def test_complete_bad_response_never_advances(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    fault: str,
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    with server() as remote:
        if fault == "json":
            remote.responses[CHAT] = CANARY.encode()
        elif fault == "model":
            remote.responses[CHAT] = body("KISSKI_OK", "other-model")
        elif fault == "finish":
            remote.responses[CHAT] = body("KISSKI_OK").replace(b'"stop"', b'"length"')
        else:
            remote.responses[CHAT] = body(CANARY)
        expected = (
            probe.Outcome.CONTENT_REJECTED
            if fault == "content"
            else probe.Outcome.CONTRACT_REJECTED
        )
        assert runner.invoke(remote) is expected
        assert remote.requests == 2
    runner.no_leak(caplog)


def test_discovery_failure_precedes_second_provision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    with server() as remote:
        remote.mode = "403"
        assert runner.invoke(remote) is probe.Outcome.DISCOVERY_FAILED
        assert remote.requests == 1
        assert runner.purposes == ["provider-model-discovery"]


@pytest.mark.parametrize(
    "answers,calls,outcome",
    [
        (("",), 1, probe.Outcome.DECLINED),
        (("3",), 1, probe.Outcome.DECLINED),
        (("2", "n"), 1, probe.Outcome.DECLINED),
        (("2", "y", "n"), 2, probe.Outcome.CONNECTIVITY_ONLY),
    ],
)
def test_each_stage_requires_explicit_choice(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    answers: tuple[str, ...],
    calls: int,
    outcome: probe.Outcome,
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    with server() as remote:
        assert runner.invoke(remote, answers) is outcome
        assert remote.requests == calls
        assert len(runner.purposes) == calls


def test_disclosure_refuses_before_chat_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    original = probe.host_config
    with server() as remote:
        with patch.object(
            probe,
            "host_config",
            side_effect=lambda *args: replace(
                original(*args), disclosure=RemoteDisclosureConfig((), ())
            ),
        ):
            with pytest.raises(HostError):
                runner.invoke(remote)
        assert remote.requests == 1


@pytest.mark.parametrize(
    "content",
    [
        "{}",
        "```json\n" + probe.EXPECTED_JSON + "\n```",
        probe.EXPECTED_JSON.replace('"create"', '"delete"'),
        probe.EXPECTED_JSON.replace('"risks":[]', '"risks":[],"risks":[]'),
        probe.EXPECTED_JSON.replace("synthetic.txt", "other.txt"),
        "x" * 4097,
        "\ud800",
    ],
    ids=["empty", "markdown", "operation", "duplicate", "path", "bound", "unicode"],
)
def test_fixed_structured_fixture_refuses_changes(content: str) -> None:
    assert not probe.structured_matches(content)


def test_structured_failure_is_not_quality_or_full_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = Runner(tmp_path, monkeypatch)
    with server() as remote:
        assert runner.invoke(remote) is probe.Outcome.STRUCTURED_REJECTED
        assert remote.requests == 3


def test_main_suppresses_raw_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with (
        patch.object(sys.stdin, "isatty", return_value=True),
        patch.object(sys.stdout, "isatty", return_value=True),
        patch("builtins.input", return_value=probe.AUTHORIZATION),
        patch.object(tempfile, "mkdtemp", return_value=str(tmp_path)),
        patch.object(probe, "run", side_effect=RuntimeError(CANARY)),
    ):
        assert probe.main(["--live"]) == 1
    captured = capsys.readouterr()
    assert CANARY not in captured.out + captured.err
    assert "RESULT_INCONCLUSIVE" in captured.out
    assert "PLAN; no credential prompt or I/O" not in captured.out
