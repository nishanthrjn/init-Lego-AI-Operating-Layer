"""Offline controls for the attended fixed-model diagnostic."""

import json
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from scripts import kisski_saia_qualification as saia
from scripts import openai_finish_reason_live_diagnostic as diagnostic
from scripts.tests.test_kisski_saia_qualification import CANARY, Runner
from tests.support.tls_server import TlsServer


@pytest.mark.parametrize("options", [[], ["--plan"]])
def test_plan_is_inert(options: list[str]) -> None:
    with (
        patch("builtins.input", side_effect=AssertionError("input")),
        patch.object(saia, "run", side_effect=AssertionError("provider")),
        patch.object(tempfile, "mkdtemp", side_effect=AssertionError("custody")),
    ):
        assert diagnostic.main(options) == 0


@pytest.mark.parametrize(
    "answer", ["", "yes", saia.AUTHORIZATION, diagnostic.AUTHORIZATION + " "]
)
def test_wrong_authorization_precedes_all_io(answer: str) -> None:
    with (
        patch.object(sys.stdin, "isatty", return_value=True),
        patch.object(sys.stdout, "isatty", return_value=True),
        patch("builtins.input", return_value=answer),
        patch.object(saia, "run", side_effect=AssertionError("provider")),
        patch.object(tempfile, "mkdtemp", side_effect=AssertionError("custody")),
    ):
        assert diagnostic.main(["--live"]) == 2


@pytest.mark.parametrize("option", ["--token", "--model", "--config", "--li"])
def test_cli_does_not_accept_secrets_or_model_override(
    option: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit):
        diagnostic.main([option, CANARY])
    assert CANARY not in capsys.readouterr().err


@pytest.mark.parametrize("category", sorted(diagnostic.CATEGORIES))
def test_closed_projection(category: str) -> None:
    line = "chat contract finish_reason_category: " + category
    assert diagnostic.safe_line(line) == "finish_reason_category: " + category


@pytest.mark.parametrize(
    "line",
    [
        "chat contract finish_reason_category: " + CANARY,
        "chat contract rejection_reason: " + CANARY,
        "chat execution: " + CANARY,
        "chat HTTP status: 200 " + CANARY,
        "chat receive body_complete: " + CANARY,
        "message: " + CANARY,
        "1. " + CANARY,
    ],
)
def test_unknown_output_is_discarded(line: str) -> None:
    assert diagnostic.safe_line(line) is None


@pytest.mark.parametrize(
    "case", ["stop", "length", "unknown", "missing", "decline", "discovery"]
)
def test_real_probe_flow_stays_one_discovery_one_chat(
    case: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fixture = Runner(tmp_path, monkeypatch)
    models = [] if case == "missing" else [{"id": diagnostic.MODEL}]
    finish = CANARY if case == "unknown" else "length" if case == "length" else "stop"
    payload = {
        "model": diagnostic.MODEL,
        "choices": [
            {
                "finish_reason": finish,
                "message": {"role": "assistant", "content": "KISSKI_OK"},
            }
        ],
    }
    responses = {
        "/v1/models": json.dumps({"data": models}).encode(),
        "/v1/chat/completions": json.dumps(payload).encode(),
    }
    with TlsServer(
        "503" if case == "discovery" else "ok",
        expected=CANARY,
        methods={"/v1/models": "POST", "/v1/chat/completions": "POST"},
        responses=responses,
    ) as server:
        outcome = diagnostic.run(
            fixture.config(server),
            ask=lambda _: "n" if case == "decline" else "y",
            write=fixture.lines.append,
        )
        chat_expected = case in {"stop", "length", "unknown"}
        assert server.paths == ["POST /v1/models"] + (
            ["POST /v1/chat/completions"] if chat_expected else []
        )
        assert server.requests == (2 if chat_expected else 1)
        if chat_expected:
            sent = json.loads(server.bodies[-1])
            assert sent["model"] == diagnostic.MODEL
            assert sent["messages"] == [{"role": "user", "content": saia.TINY_PROMPT}]
            assert sent["stream"] is False
            assert sent["max_tokens"] == 512
    if case == "stop":
        assert outcome is saia.Outcome.CONNECTIVITY_ONLY
    if case in {"length", "unknown"}:
        assert outcome is saia.Outcome.CONTRACT_REJECTED
        category = "LENGTH" if case == "length" else "OTHER_STRING"
        assert "finish_reason_category: " + category in fixture.lines
    assert fixture.purposes == ["provider-model-discovery"] + (
        ["remote-model-bearer"] if chat_expected else []
    )
    fixture.no_leak(caplog)


def test_uncertain_exception_is_suppressed_and_not_retried(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with (
        patch.object(sys.stdin, "isatty", return_value=True),
        patch.object(sys.stdout, "isatty", return_value=True),
        patch("builtins.input", return_value=diagnostic.AUTHORIZATION),
        patch.object(tempfile, "mkdtemp", return_value=str(tmp_path)),
        patch.object(diagnostic, "run", side_effect=RuntimeError(CANARY)) as call,
    ):
        assert diagnostic.main(["--live"]) == 1
    assert call.call_count == 1
    output = capsys.readouterr().out
    assert "INCONCLUSIVE" in output
    assert CANARY not in output


def test_unexpected_continuation_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected(config: Any, **kwargs: Any) -> Any:
        assert kwargs["diagnostic_only"] is True
        kwargs["ask"]("Approve another model?")
        raise AssertionError("continuation reached")

    monkeypatch.setattr(saia, "run", unexpected)
    with pytest.raises(ValueError, match="unexpected diagnostic stage"):
        diagnostic.run(
            saia.live_config(tmp_path), ask=lambda _: "y", write=lambda _: None
        )
