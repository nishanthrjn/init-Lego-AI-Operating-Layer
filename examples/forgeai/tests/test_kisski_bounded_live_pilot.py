"""Pilot boundaries using replay models and synthetic TLS only; no Docker."""

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    REVIEW_CHANGES,
    REWORK,
    FakeSandbox,
    LoggedReplay,
    config,
    proposal,
    repository,
)
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure
from test_remote_profile import CANARY, body, configured
from tls_server import TlsServer

from forgeai.domain import TaskFailure
from scripts import forgeai_kisski_bounded_live_pilot as pilot
from scripts import kisski_saia_qualification as saia


def forbidden(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("unexpected external operation")


@pytest.mark.parametrize("options", [[], ["--plan"], ["--token", "secret-canary"]])
def test_default_and_invalid_options_inert(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], options: list[str]
) -> None:
    monkeypatch.setattr(pilot, "run_attended", forbidden)
    monkeypatch.setattr("builtins.input", forbidden)
    pilot.main(options)
    assert "secret-canary" not in capsys.readouterr().out


@pytest.mark.parametrize("terminal,answer", [(False, ""), (True, "y"), (True, "")])
def test_exact_authorization_before_work(
    monkeypatch: pytest.MonkeyPatch, terminal: bool, answer: str
) -> None:
    monkeypatch.setattr(pilot.sys.stdin, "isatty", lambda: terminal)
    monkeypatch.setattr(pilot.sys.stdout, "isatty", lambda: terminal)
    monkeypatch.setattr("builtins.input", lambda _: answer)
    monkeypatch.setattr(pilot, "run_attended", forbidden)
    assert pilot.main(["--live"]) == 2


def test_no_current_admissions_before_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    assert pilot.ADMISSIONS == ()
    for name in ("remote_credentials", "discover_models", "sandbox_readiness"):
        monkeypatch.setattr(pilot, name, forbidden)
    output: list[str] = []
    assert pilot.run_attended(forbidden, output.append) == 1
    assert "PILOT_MODEL_NOT_ADMITTED" in output[0]


def test_fixture_and_task_scope() -> None:
    assert pilot.fixture_digest() == pilot.FIXTURE_DIGEST
    request = pilot.task()
    assert len(request.targets) == 2
    assert [p.value for p in request.context] == ["pyproject.toml"]
    assert pilot.plan()["max_provider_calls"] == 5


def admission() -> pilot.Admission:
    return pilot.Admission("model-a", "smoke-1", "smoke-1", "review-1", True, 1024)


@pytest.mark.parametrize(
    "change",
    [
        {"connectivity": ""},
        {"structured_smoke": ""},
        {"quality_review": ""},
        {"protocol_clear": False},
        {"output_tokens": 512},
    ],
)
def test_admission_missing_evidence_refused(
    monkeypatch: pytest.MonkeyPatch, change: dict[str, Any]
) -> None:
    monkeypatch.setattr(pilot, "ADMISSIONS", (replace(admission(), **change),))
    assert not pilot.admitted("model-a", ("model-a",))


@pytest.mark.parametrize("selected", ["model-a ", '"model-a"', "MODEL-A", "model-b"])
def test_exact_selection_no_alias(monkeypatch: pytest.MonkeyPatch, selected: str) -> None:
    monkeypatch.setattr(pilot, "ADMISSIONS", (admission(),))
    assert not pilot.admitted(selected, ("model-a", "model-b"))
    assert not pilot.admitted("model-a", ("model-b",))
    assert pilot.admitted("model-a", ("model-a",))


@pytest.mark.parametrize("stop", ["readiness", "missing", "discovery", "declined"])
def test_outer_guards_precede_repository_and_model_secret(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stop: str
) -> None:
    from test_remote_profile import profile

    monkeypatch.setattr(pilot, "ADMISSIONS", (admission(),))
    monkeypatch.setattr(
        pilot, "load_profile", lambda _: profile(443, pilot.datetime.now(pilot.UTC))
    )
    monkeypatch.setattr(pilot, "check_profile", lambda *_: None)
    monkeypatch.setattr(pilot.shutil, "which", lambda _: str(tmp_path / "git.exe"))
    monkeypatch.setattr(pilot.tempfile, "mkdtemp", lambda **_: str(tmp_path))
    monkeypatch.setattr(
        pilot,
        "sandbox_readiness",
        lambda _: SandboxFailure.RUNTIME_UNAVAILABLE if stop == "readiness" else None,
    )
    discoveries: list[Path] = []

    def discover(path: Path) -> tuple[str, ...] | None:
        assert stop != "readiness"
        discoveries.append(path)
        return (
            None
            if stop == "discovery"
            else ("other",)
            if stop == "missing"
            else ("model-a",)
        )

    monkeypatch.setattr(pilot, "discover_models", discover)
    monkeypatch.setattr(pilot, "remote_credentials", forbidden)
    monkeypatch.setattr(pilot, "create_repository", forbidden)
    answers = iter(["model-a", "profile.toml", "n"])
    assert pilot.run_attended(lambda _: next(answers), lambda _: None) == 1
    value = json.loads((tmp_path / "pilot.json").read_text())
    expected = {
        "readiness": "PILOT_SANDBOX_FAILED",
        "missing": "PILOT_MODEL_NOT_ADMITTED",
        "discovery": "PILOT_DISCOVERY_FAILED",
        "declined": "PILOT_DISCLOSURE_DECLINED",
    }
    assert value["status"] == expected[stop]
    assert len(discoveries) == (0 if stop == "readiness" else 1)
    assert value["repository_effect"] == "NONE"


@pytest.mark.parametrize(
    "scenario,maximum", [("success", 2), ("checks", 3), ("review", 4)]
)
def test_replay_complete_lifecycle_and_projection(
    tmp_path: Path, scenario: str, maximum: int
) -> None:
    outputs = {
        "success": (proposal(), REVIEW_ACCEPT),
        "checks": (proposal(), REWORK, REVIEW_ACCEPT),
        "review": (proposal(), REVIEW_CHANGES, REWORK, REVIEW_ACCEPT),
    }[scenario]
    model = LoggedReplay([], *outputs)
    cfg = config(repository(tmp_path), model, context=("pyproject.toml",))
    sandbox = FakeSandbox((1, 0, 0, 0, 0, 0) if scenario == "checks" else (0, 0, 0))
    report = asyncio.run(
        pilot.execute_task(cfg, ask=lambda _: "y", write=lambda _: None, sandbox=sandbox)
    )
    assert report["status"] == "PILOT_SUCCEEDED"
    assert model.calls == maximum <= 4
    assert report["rework_used"] is (scenario != "success")
    assert report["changes_retained"] is True
    assert report["rollback_performed"] is False
    encoded = json.dumps(report)
    assert "def reserve" not in encoded and "changeset" not in encoded


@pytest.mark.parametrize("gate", ["context", "disclosure", "mutation", "stale"])
def test_separate_remote_gates(tmp_path: Path, gate: str) -> None:
    with TlsServer(expected=CANARY) as server:
        server.responses["/v1/chat/completions"] = body(proposal())
        with configured(tmp_path, server, request=pilot.task()) as (cfg, _):
            sandbox = FakeSandbox()
            output: list[str] = []

            def ask(prompt: str) -> str:
                if prompt.startswith("Confirm"):
                    if gate == "stale":
                        (cfg.repository / "pyproject.toml").write_text("# changed\n")
                    return "n" if gate == "context" else "y"
                if prompt.startswith("Send"):
                    return "n" if gate == "disclosure" else "y"
                return "n"

            report = asyncio.run(
                pilot.execute_task(cfg, ask=ask, write=output.append, sandbox=sandbox)
            )
            expected = {
                "context": TaskFailure.CONTEXT_DECLINED,
                "disclosure": TaskFailure.MODEL_DISCLOSURE_REFUSED,
                "mutation": TaskFailure.PROPOSAL_DECLINED,
                "stale": TaskFailure.CONTEXT_STALE,
            }[gate]
            assert report["task_failure"] == expected.name
            assert sandbox.calls == 0
            assert server.requests == (1 if gate == "mutation" else 0)
            assert CANARY not in json.dumps(report) + "".join(output)


@pytest.mark.parametrize("failure", ["proposal", "sandbox", "model", "exhausted"])
def test_failures_stop_and_retain_effects(tmp_path: Path, failure: str) -> None:
    outputs: tuple[str | Exception, ...] = (proposal(), REVIEW_ACCEPT)
    if failure == "proposal":
        outputs = ("invalid-secret-canary",)
    elif failure == "model":
        outputs = (RuntimeError("exception-secret-canary"),)
    elif failure == "exhausted":
        outputs = (proposal(), REVIEW_CHANGES, REWORK, REVIEW_CHANGES)
    model = LoggedReplay([], *outputs)
    cfg = config(repository(tmp_path), model, context=("pyproject.toml",))
    sandbox = FakeSandbox(
        error=SandboxError(SandboxFailure.RUNTIME_UNAVAILABLE)
        if failure == "sandbox"
        else None
    )
    report = asyncio.run(
        pilot.execute_task(cfg, ask=lambda _: "y", write=lambda _: None, sandbox=sandbox)
    )
    assert report["status"] != "PILOT_SUCCEEDED"
    assert model.calls == (4 if failure == "exhausted" else 1)
    assert report["changes_retained"] is (failure in {"sandbox", "exhausted"})
    assert "secret-canary" not in json.dumps(report)


@pytest.mark.parametrize("fails", [False, True])
def test_discovery_single_call_closes_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fails: bool
) -> None:
    events: list[str] = []
    source = SimpleNamespace(_source=object(), close=lambda: events.append("close"))
    monkeypatch.setattr(saia, "open_credential_source", lambda _: source)

    def provision(*args: Any) -> object:
        events.append("provision")
        return object()

    def discover(*args: Any) -> SimpleNamespace:
        events.append("discovery")
        if fails:
            raise ValueError("synthetic-secret")
        return SimpleNamespace(models=(SimpleNamespace(value="model-a"),))

    monkeypatch.setattr(saia, "_provision_interactively", provision)
    monkeypatch.setattr(saia.legacy, "_discover", discover)
    monkeypatch.setattr(saia.legacy, "classify_discovery", lambda _: None)
    monkeypatch.setattr(saia, "chat_stages", forbidden)
    if fails:
        with pytest.raises(ValueError):
            saia.discover_models(tmp_path)
    else:
        assert saia.discover_models(tmp_path) == ("model-a",)
    assert events == ["provision", "discovery", "close"]


def test_outer_error_never_prints_raw(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(pilot.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(pilot.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: pilot.AUTHORIZATION)

    def fail(*args: Any) -> int:
        raise ValueError("exception-secret-canary")

    monkeypatch.setattr(pilot, "run_attended", fail)
    assert pilot.main(["--live"]) == 1
    assert "exception-secret-canary" not in capsys.readouterr().out


def test_remote_wrapper_complete_bounded_rework(tmp_path: Path) -> None:
    outputs = (proposal(), REVIEW_CHANGES, REWORK, REVIEW_ACCEPT)
    with TlsServer(expected=CANARY) as server:

        def respond() -> None:
            server.responses["/v1/chat/completions"] = body(
                outputs[server.requests - 1]
            )

        server.on_request = respond
        with configured(tmp_path, server, request=pilot.task()) as (cfg, _):
            cfg = replace(cfg, host=replace(cfg.host, max_executions=4))
            sandbox = FakeSandbox()
            report = asyncio.run(
                pilot.execute_task(
                    cfg, ask=lambda _: "y", write=lambda _: None, sandbox=sandbox
                )
            )
            assert report["status"] == "PILOT_SUCCEEDED"
            assert report["disclosure_approved"] is True
            assert report["context_decisions"] == [True, True]
            assert server.requests == 4
            assert sandbox.calls == 6
            assert report["repository_effect"] == "KNOWN"
            assert CANARY not in json.dumps(report)


def test_duplicate_admission_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pilot, "ADMISSIONS", (admission(), admission()))
    assert not pilot.admitted("model-a", ("model-a",))
