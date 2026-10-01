"""LQ1.2 observers never change what ForgeAI receives.

Every scenario runs ForgeAI's real Ollama adapter twice against a scripted
in-process Ollama: once direct, once through `ChatObserver`. The typed
TaskResult projection and the request bytes Ollama received must be equal.
The one documented deviation (refused upstream connection) is pinned exactly.
"""

import asyncio
import json
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from diag_support import part
from eval_support import REVIEW_ACCEPT, fixture, reference
from forgeai_support import FakeSandbox, git_executable
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatResult,
    ChatRole,
    ModelId,
    ProviderId,
)
from legoai.kernel.effects import EffectExtent
from legoai.runtime.api import ModelBindingConfig

from forgeai.cli import ollama_binding
from forgeai.domain import TaskResult
from forgeai_eval.diagnostics import run_diagnostics
from forgeai_eval.fixtures import Fixture
from forgeai_eval.observer import (
    ChatObserver,
    Observation,
    ObservationLog,
    ObservingModel,
    Stage,
    Transport,
)
from forgeai_eval.outputs import proposal_fingerprint, review_fingerprint
from forgeai_eval.runner import FixtureRun, RunSettings, evaluate_run

CLOSED = "http://127.0.0.1:9"


@dataclass
class Reply:
    content: str | None = None
    status: int = 200
    raw: bytes | None = None
    delay: float = 0.0


@dataclass
class Upstream:
    """Scripted Ollama /api/chat; records every request body it receives."""

    replies: list[Reply]
    bodies: list[bytes] = field(default_factory=list)


@contextmanager
def ollama(upstream: Upstream) -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers["Content-Length"]))
            upstream.bodies.append(body)
            reply = upstream.replies[len(upstream.bodies) - 1]
            time.sleep(reply.delay)
            payload = reply.raw
            if payload is None:
                payload = json.dumps(
                    {
                        "model": "test-model",
                        "message": {"role": "assistant", "content": reply.content},
                        "done": True,
                        "prompt_eval_count": 1,
                        "eval_count": 1,
                    }
                ).encode()
            try:
                self.send_response(reply.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except OSError:
                pass  # the client already gave up (timeout scenarios)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def run(
    workdir: Path, url: str, timeout: float, log: ObservationLog | None
) -> FixtureRun:
    binding = ollama_binding(url, "test-model", timeout)

    def bindings(item: Fixture) -> tuple[tuple[ModelBindingConfig, ...], str]:
        return (binding,), "ollama"

    hidden = FakeSandbox()
    settings = RunSettings(
        bindings=bindings,
        git=git_executable(),
        docker=git_executable(),
        workdir=workdir,
        forgeai_sandbox=FakeSandbox(),
        hidden_sandbox=lambda: hidden,
        observations=log,
        observation_wait_seconds=10.0,
    )
    return evaluate_run(fixture("stock-validation"), 1, settings)


def projection(result: TaskResult) -> tuple[object, ...]:
    """Every typed outcome ForgeAI derived from the model calls."""
    attempts = []
    for a in result.evidence.attempts:
        review = a.review
        attempts.append(
            (
                a.number,
                a.coding_status,
                a.agent_status,
                a.model_effect,
                None if a.proposal is None else proposal_fingerprint(a.proposal),
                tuple(
                    (r.request.kind, r.result.exit_code if r.result else None, r.error)
                    for r in a.checks
                ),
                None
                if review is None
                else (
                    review.status,
                    None
                    if review.review is None
                    else review_fingerprint(review.review),
                    None
                    if review.agent_result is None
                    or review.agent_result.model_execution is None
                    else review.agent_result.model_execution.effect,
                ),
            )
        )
    return (result.disposition, result.failure, tuple(attempts))


SCENARIOS = {
    "success": (
        [Reply(reference(fixture("stock-validation"))), Reply(REVIEW_ACCEPT)],
        30.0,
    ),
    "fenced-proposal": ([Reply("```json\n{}\n```")], 30.0),
    "invalid-review": (
        [Reply(reference(fixture("stock-validation"))), Reply("not json")],
        30.0,
    ),
    "provider-http-500": ([Reply(status=500, raw=b'{"error":"boom"}')], 30.0),
    "provider-malformed-json": ([Reply(raw=b"<html>")], 30.0),
    "provider-missing-content": ([Reply(raw=b'{"message":{}}')], 30.0),
    "adapter-timeout": ([Reply("{}", delay=2.0)], 1.0),
}


@pytest.mark.parametrize("case", sorted(SCENARIOS))
def test_observer_does_not_change_forgeai_results(tmp_path: Path, case: str) -> None:
    replies, timeout = SCENARIOS[case]
    direct = Upstream(list(replies))
    with ollama(direct) as url:
        plain = run(tmp_path / "direct", url, timeout, None)
    observed_upstream = Upstream(list(replies))
    log = ObservationLog()
    with (
        ollama(observed_upstream) as url,
        ChatObserver(url, timeout + 0.5, log) as observer,
    ):
        watched = run(tmp_path / "observed", observer.url, timeout, log)
    assert projection(watched.task_result) == projection(plain.task_result)
    assert observed_upstream.bodies == direct.bodies  # byte-identical requests
    assert len(watched.observations) == len(direct.bodies)
    assert watched.observation_complete is True
    diagnostics = run_diagnostics(watched)
    assert diagnostics["anomalies"] == {}
    categories = [e["category"] for e in part(diagnostics, "coding")]
    assert "classifier_disagreement" not in categories


def test_refused_upstream_is_the_one_documented_deviation(tmp_path: Path) -> None:
    plain = run(tmp_path / "direct", CLOSED, 10.0, None)
    log = ObservationLog()
    with ChatObserver(CLOSED, 10.5, log) as observer:
        watched = run(tmp_path / "observed", observer.url, 10.0, log)
    (direct,) = plain.task_result.evidence.attempts
    (observed,) = watched.task_result.evidence.attempts
    assert plain.task_result.failure == watched.task_result.failure
    assert plain.task_result.failure is not None
    assert plain.task_result.failure.name == "MODEL_FAILED"
    assert direct.model_effect is EffectExtent.NONE
    assert observed.model_effect is EffectExtent.UNKNOWN  # the deviation
    assert [o.transport for o in watched.observations] == [
        Transport.UPSTREAM_UNREACHABLE
    ]
    (entry,) = part(run_diagnostics(watched), "coding")
    assert entry["category"] == "model_failure"
    assert entry["transport"] == "upstream_unreachable"


class _Inner:
    def __init__(self, result: ChatResult | Exception) -> None:
        self.result = result

    async def chat(self, request: ChatRequest) -> ChatResult:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    async def embed(self, request: object) -> object:
        raise AssertionError("not used")


def _request() -> ChatRequest:
    return ChatRequest(
        (ChatMessage(ChatRole.SYSTEM, "other"), ChatMessage(ChatRole.USER, "u"))
    )


def test_observing_model_returns_the_original_result_and_error() -> None:
    log = ObservationLog()
    original = ChatResult("reply", ModelId("m"), ProviderId("p"), None)
    observing = ObservingModel(_Inner(original), log)  # type: ignore[arg-type]
    assert asyncio.run(observing.chat(_request())) is original
    error = RuntimeError("provider")
    failing = ObservingModel(_Inner(error), log)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError) as raised:
        asyncio.run(failing.chat(_request()))
    assert raised.value is error
    observations, complete = log.drain()
    assert complete is True
    assert [(o.stage, o.transport) for o in observations] == [
        (Stage.UNKNOWN, Transport.DELIVERED),
        (Stage.UNKNOWN, Transport.PROVIDER_EXCEPTION),
    ]


def test_late_calls_are_never_attributed_to_a_later_run() -> None:
    log = ObservationLog()
    generation = log.begin()
    observations, complete = log.drain(0.0)
    assert observations == () and complete is False
    log.end(generation, Observation(Stage.CODING, Transport.DELIVERED))
    assert log.drain(0.0) == ((), True)
