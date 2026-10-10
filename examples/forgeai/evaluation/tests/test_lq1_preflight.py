"""LQ1.1 live-run preflight: verify the serving Ollama before any fixture runs.

A recording in-process HTTP server stands in for Ollama, so every request the
harness makes (method and path) is observed. No real Ollama and no live model
are needed; replay outputs and fake sandboxes stand in for the runs.
"""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import run
from forgeai_support import FakeSandbox, approve, git_executable

from forgeai_eval.fixtures import FixtureSet
from forgeai_eval.preflight import (
    PreflightError,
    PreflightFailure,
    ServingIdentity,
    verify_ollama,
)
from forgeai_eval.runner import FixtureRun, RunSettings, evaluate

MODEL = "llama3.2:latest"
HEX = "a80c4f17acd55265feec403c7aef86be0c25983ab279d83f3bcd3abbcb5b8b72"
DIGEST = f"sha256:{HEX}"
OTHER_HEX = "0" * 64
UNREACHABLE = "http://127.0.0.1:9"
READ_ONLY = [("GET", "/api/version"), ("GET", "/api/tags")]


def tags(*models: tuple[str, str]) -> dict[str, object]:
    return {"models": [{"name": n, "model": n, "digest": d} for n, d in models]}


@dataclass
class OllamaStub:
    """Configured responses; every request is recorded, and only GETs answer."""

    version: object = field(default_factory=lambda: {"version": "0.35.0"})
    tags: object = field(default_factory=lambda: tags((MODEL, HEX)))
    raw: dict[str, bytes] = field(default_factory=dict)
    requests: list[tuple[str, str]] = field(default_factory=list)


@contextmanager
def ollama(stub: OllamaStub) -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def _answer(self) -> None:
            stub.requests.append((self.command, self.path))
            bodies: dict[str, object] = {
                "/api/version": stub.version,
                "/api/tags": stub.tags,
            }
            if self.command != "GET" or self.path not in bodies:
                self.send_error(404)
                return
            body = stub.raw.get(self.path, json.dumps(bodies[self.path]).encode())
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = _answer

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def live_args(url: str, output: Path, *extra: str) -> list[str]:
    return [
        "live",
        "--model",
        MODEL,
        "--model-digest",
        DIGEST,
        "--hardware",
        "self-test",
        "--repetitions",
        "3",
        "--ollama-url",
        url,
        "--git",
        str(git_executable()),
        "--docker",
        str(git_executable()),
        "--output",
        str(output),
        *extra,
    ]


class Evaluations:
    """Stands in for `run.evaluate`; counts ForgeAI evaluations started."""

    def __init__(self) -> None:
        self.calls = 0

    def refuse(
        self, fixtures: FixtureSet, repetitions: int, settings: RunSettings
    ) -> tuple[tuple[FixtureRun, ...], float]:
        self.calls += 1
        raise AssertionError("a ForgeAI evaluation started after a failed preflight")

    def replay(
        self, fixtures: FixtureSet, repetitions: int, settings: RunSettings
    ) -> tuple[tuple[FixtureRun, ...], float]:
        """The real evaluation loop, with replay outputs and fake sandboxes."""
        self.calls += 1
        hidden = FakeSandbox()
        offline = replace(
            settings,
            approve=approve,
            bindings=run.replay_bindings,
            forgeai_sandbox=FakeSandbox(),
            hidden_sandbox=lambda: hidden,
        )
        return evaluate(fixtures, repetitions, offline)


# A. reachable server, exact model and digest: the live run may proceed.
def test_matching_server_yields_the_observed_identity() -> None:
    stub = OllamaStub()
    with ollama(stub) as url:
        identity = verify_ollama(url, MODEL, DIGEST)
    assert identity == ServingIdentity("0.35.0", MODEL, DIGEST)
    assert stub.requests == READ_ONLY


# F. the report records the observed version, never operator text.
def test_live_report_records_the_observed_server_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub = OllamaStub(version={"version": "0.35.0"})
    evaluations = Evaluations()
    monkeypatch.setattr(run, "evaluate", evaluations.replay)
    with ollama(stub) as url:
        assert run.main(live_args(url, tmp_path / "out")) == 0
    report = json.loads((tmp_path / "out" / "report.json").read_text("utf-8"))
    metadata = report["metadata"]
    assert metadata["mode"] == "live"
    assert metadata["ollama_version"] == "0.35.0"
    assert (metadata["model_name"], metadata["model_digest"]) == (MODEL, DIGEST)
    assert metadata["hardware_class"] == "self-test"  # still operator-supplied
    assert evaluations.calls == 1 and len(report["runs"]) == 12
    assert "0.35.0" in (tmp_path / "out" / "report.md").read_text("utf-8")
    # G. preflight was read-only; replay stood in, so no chat reached Ollama.
    assert stub.requests == READ_ONLY


def test_operator_cannot_supply_the_ollama_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evaluations = Evaluations()
    monkeypatch.setattr(run, "evaluate", evaluations.refuse)
    with pytest.raises(SystemExit) as exit_info:
        run.main(live_args(UNREACHABLE, tmp_path / "out", "--ollama-version", "0.34.4"))
    assert exit_info.value.code == 2
    assert evaluations.calls == 0 and not (tmp_path / "out").exists()


SERVERS = {
    # C. requested model missing, including near misses that are never used.
    "model-missing": (
        OllamaStub(tags=tags(("nomic-embed-text:latest", OTHER_HEX))),
        PreflightFailure.MODEL_NOT_INSTALLED,
    ),
    "other-tag-only": (
        OllamaStub(tags=tags(("llama3.2:3b", HEX))),
        PreflightFailure.MODEL_NOT_INSTALLED,
    ),
    "untagged-name-only": (
        OllamaStub(tags=tags(("llama3.2", HEX))),
        PreflightFailure.MODEL_NOT_INSTALLED,
    ),
    # D. digest mismatch, including a different build under the same name.
    "digest-mismatch": (
        OllamaStub(tags=tags((MODEL, OTHER_HEX))),
        PreflightFailure.MODEL_DIGEST_MISMATCH,
    ),
    "partial-observed-digest": (
        OllamaStub(tags=tags((MODEL, HEX[:12]))),
        PreflightFailure.OLLAMA_RESPONSE_INVALID,
    ),
    "no-version": (
        OllamaStub(version={}),
        PreflightFailure.OLLAMA_RESPONSE_INVALID,
    ),
    "not-json": (
        OllamaStub(raw={"/api/tags": b"<html>"}),
        PreflightFailure.OLLAMA_RESPONSE_INVALID,
    ),
}


@pytest.mark.parametrize("case", sorted(SERVERS))
def test_mismatched_server_fails_closed(case: str) -> None:
    stub, failure = SERVERS[case]
    stub = replace(stub, requests=[])
    with ollama(stub) as url, pytest.raises(PreflightError) as error:
        verify_ollama(url, MODEL, DIGEST)
    assert error.value.failure is failure
    assert all(method == "GET" for method, _ in stub.requests)
    assert set(stub.requests) <= set(READ_ONLY)


# B. server unreachable.
def test_unreachable_server_fails_closed() -> None:
    with pytest.raises(PreflightError) as error:
        verify_ollama(UNREACHABLE, MODEL, DIGEST, timeout=5.0)
    assert error.value.failure is PreflightFailure.OLLAMA_UNREACHABLE


# B, C, D through the command: zero ForgeAI runs and no report.
@pytest.mark.parametrize("case", ["unreachable", "model-missing", "digest-mismatch"])
def test_failed_preflight_runs_nothing_and_writes_no_report(
    case: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    evaluations = Evaluations()
    monkeypatch.setattr(run, "evaluate", evaluations.refuse)
    output = tmp_path / "out"
    if case == "unreachable":
        code = run.main(live_args(UNREACHABLE, output))
        expected = PreflightFailure.OLLAMA_UNREACHABLE
    else:
        stub, expected = SERVERS[case]
        stub = replace(stub, requests=[])
        with ollama(stub) as url:
            code = run.main(live_args(url, output))
        assert stub.requests == READ_ONLY
    assert code == run.PREFLIGHT_FAILED
    assert evaluations.calls == 0
    assert not output.exists()
    assert expected.name in capsys.readouterr().err


@pytest.mark.parametrize(
    "digest",
    [HEX, "sha256:" + HEX[:12], "sha256:" + HEX.upper(), "sha256:" + HEX + "0"],
    ids=["no-prefix", "partial", "uppercase", "too-long"],
)
def test_malformed_requested_digest_is_refused_before_any_request(
    digest: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evaluations = Evaluations()
    monkeypatch.setattr(run, "evaluate", evaluations.refuse)
    stub = OllamaStub()
    with ollama(stub) as url:
        args = live_args(url, tmp_path / "out")
        args[args.index(DIGEST)] = digest
        with pytest.raises(SystemExit) as exit_info:
            run.main(args)
    assert exit_info.value.code == 2
    assert stub.requests == [] and evaluations.calls == 0
    assert not (tmp_path / "out").exists()


# H. replay mode never contacts Ollama.
def test_replay_mode_skips_the_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_preflight(*args: object, **kwargs: object) -> ServingIdentity:
        raise AssertionError("replay mode must not run the Ollama preflight")

    evaluations = Evaluations()
    monkeypatch.setattr(run, "verify_ollama", no_preflight)
    monkeypatch.setattr(run, "evaluate", evaluations.replay)
    argv = ["replay", "--output", str(tmp_path / "out")]
    argv += ["--git", str(git_executable()), "--docker", str(git_executable())]
    assert run.main(argv) == 0
    report = json.loads((tmp_path / "out" / "report.json").read_text("utf-8"))
    assert report["metadata"]["ollama_version"] == "not-applicable"
    assert evaluations.calls == 1
