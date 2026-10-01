"""Evaluation-only observation of model replies (LQ1.2): observers, not transformers.

Two observers feed one content-free stream of `Observation` values:

- `ChatObserver`, for live runs. LegoAI exposes no public seam to wrap the
  admitted Ollama ModelPort (the adapter is a private reference realization
  built inside the host), so the observer sits at the transport. It is a
  local HTTP pass-through between ForgeAI's real, unchanged Ollama adapter and
  Ollama: it forwards `POST /api/chat` bytes unchanged and returns the
  provider's status and body unchanged. It never originates a request.
- `ObservingModel`, for harness-owned ModelPorts (replay). It delegates and
  returns the original `ChatResult` object, or re-raises the original error.

Neither alters, repairs, strips, retries or truncates anything. Each reply is
classified in memory (`outputs.py`) and only the content-free `Diagnosis` is
kept; reply text, prompts and request bodies are discarded.

Documented deviation (ChatObserver only). A refused connection to Ollama
reaches the adapter as a dropped connection, so the adapter records an
UNKNOWN model effect instead of the NONE it records for a refused direct
connection. Every such case is recorded as an `upstream_*` transport anomaly.
The live preflight makes it rare; it is never silent.
"""

import json
import threading
from dataclasses import dataclass
from enum import StrEnum
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from legoai.intelligence.model.ports import ModelPort
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    ChatRole,
    EmbeddingRequest,
    EmbeddingResult,
)
from legoai_engineering.coding.definition import coding_definition
from legoai_engineering.reviewer.definition import reviewer_definition

from forgeai_eval.outputs import (
    Diagnosis,
    classify_coding,
    classify_review,
    coding_targets,
)

CHAT_PATH = "/api/chat"  # forwarded only; the harness never originates a chat
MAX_REQUEST_BYTES = 8_388_608
MAX_REPLY_BYTES = 16_777_216


class Stage(StrEnum):
    CODING = "coding"
    REVIEW = "review"
    UNKNOWN = "unknown"


class Transport(StrEnum):
    DELIVERED = "delivered"
    PROVIDER_REJECTED = "provider_rejected"
    PROVIDER_EXCEPTION = "provider_exception"
    CLIENT_DISCONNECTED = "client_disconnected"
    UPSTREAM_UNREACHABLE = "upstream_unreachable"
    UPSTREAM_TIMEOUT = "upstream_timeout"
    UPSTREAM_TRANSPORT_ERROR = "upstream_transport_error"
    REQUEST_REJECTED = "request_rejected"


@dataclass(frozen=True, slots=True)
class Observation:
    """One observed model call: content-free stage, transport and diagnosis."""

    stage: Stage
    transport: Transport
    diagnosis: Diagnosis | None = None


def identify(system: str | None) -> Stage:
    """Which Agent sent a request: exact match of its fixed system prompt."""
    if system == coding_definition().system_prompt:
        return Stage.CODING
    if system == reviewer_definition().system_prompt:
        return Stage.REVIEW
    return Stage.UNKNOWN


def diagnose(stage: Stage, user: str | None, reply: str) -> Diagnosis | None:
    """Classify a reply in memory; None when its request cannot be read."""
    try:
        if stage is Stage.CODING and user is not None:
            return classify_coding(reply, coding_targets(user))
        if stage is Stage.REVIEW:
            return classify_review(reply)
    except KeyError, TypeError, ValueError, RecursionError:
        return None
    return None


class ObservationLog:
    """Thread-safe observations for the current run.

    `drain` closes the current run: it waits (bounded) for in-flight calls,
    returns their observations and starts a new generation, so a late call
    from an earlier run can never be attributed to a later one.
    """

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._generation = 0
        self._in_flight = 0
        self._observations: list[Observation] = []

    def begin(self) -> int:
        with self._condition:
            self._in_flight += 1
            return self._generation

    def end(self, generation: int, observation: Observation) -> None:
        with self._condition:
            self._in_flight -= 1
            if generation == self._generation:
                self._observations.append(observation)
            self._condition.notify_all()

    def drain(self, wait_seconds: float = 0.0) -> tuple[tuple[Observation, ...], bool]:
        """Observations of the closing run, and whether none was still in flight."""
        with self._condition:
            complete = self._condition.wait_for(
                lambda: self._in_flight == 0, timeout=wait_seconds
            )
            observations = tuple(self._observations)
            self._observations.clear()
            self._generation += 1
            return observations, complete


class ObservingModel:
    """ModelPort observer for harness-owned models; returns originals unchanged."""

    def __init__(self, inner: ModelPort, log: ObservationLog) -> None:
        self.inner = inner
        self.log = log

    async def chat(self, request: ChatRequest) -> ChatResult:
        system = next(
            (m.content for m in request.messages if m.role is ChatRole.SYSTEM), None
        )
        user = next(
            (m.content for m in request.messages if m.role is ChatRole.USER), None
        )
        stage = identify(system)
        generation = self.log.begin()
        try:
            result = await self.inner.chat(request)
        except BaseException:
            self.log.end(generation, Observation(stage, Transport.PROVIDER_EXCEPTION))
            raise
        diagnosis = diagnose(stage, user, result.content)
        self.log.end(generation, Observation(stage, Transport.DELIVERED, diagnosis))
        return result

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        return await self.inner.embed(request)


def _request_roles(body: bytes) -> tuple[str | None, str | None]:
    try:
        value = json.loads(body)
        messages = value["messages"]
        system = next(m["content"] for m in messages if m["role"] == "system")
        user = next(m["content"] for m in messages if m["role"] == "user")
    except KeyError, TypeError, ValueError, StopIteration, RecursionError:
        return None, None
    if type(system) is not str or type(user) is not str:
        return None, None
    return system, user


def _reply_text(reply: bytes) -> str | None:
    """The content the adapter accepts from a 200 reply, else None (rejected)."""
    try:
        value = json.loads(reply)
    except ValueError, UnicodeError, RecursionError:
        return None
    message = value.get("message") if isinstance(value, dict) else None
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    return content if type(content) is str else None


class _ProxyServer(ThreadingHTTPServer):
    daemon_threads = True


class ChatObserver:
    """Local pass-through to Ollama `/api/chat` that observes replies.

    `upstream_timeout` should exceed the adapter's own timeout slightly, so the
    adapter's timeout semantics are what ForgeAI records.
    """

    def __init__(
        self,
        upstream: str,
        upstream_timeout: float,
        log: ObservationLog | None = None,
    ) -> None:
        location = urlsplit(upstream)
        if location.scheme not in {"http", "https"} or not location.hostname:
            raise ValueError("observer upstream must be an http(s) URL")
        self._scheme = location.scheme
        self._host = location.hostname
        self._port = location.port
        self._base = location.path.rstrip("/")
        self._timeout = upstream_timeout
        self.log = log if log is not None else ObservationLog()
        self._server: _ProxyServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        if self._server is None:
            raise RuntimeError("observer is not running")
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def _forward(self, body: bytes, content_type: str) -> tuple[int, str, str, bytes]:
        connection_type = HTTPSConnection if self._scheme == "https" else HTTPConnection
        connection = connection_type(self._host, self._port, timeout=self._timeout)
        try:
            connection.request(
                "POST",
                self._base + CHAT_PATH,
                body=body,
                headers={"Content-Type": content_type},
            )
            response = connection.getresponse()
            reply = response.read(MAX_REPLY_BYTES + 1)
            if len(reply) > MAX_REPLY_BYTES:
                raise HTTPException("reply exceeds the observer bound")
            return (
                response.status,
                response.reason,
                response.getheader("Content-Type", "application/json"),
                reply,
            )
        finally:
            connection.close()

    def _relay(self, handler: BaseHTTPRequestHandler) -> Observation:
        if handler.command != "POST" or handler.path != CHAT_PATH:
            handler.send_error(404)
            return Observation(Stage.UNKNOWN, Transport.REQUEST_REJECTED)
        try:
            length = int(handler.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if not 0 <= length <= MAX_REQUEST_BYTES:
            handler.close_connection = True
            return Observation(Stage.UNKNOWN, Transport.REQUEST_REJECTED)
        body = handler.rfile.read(length)
        system, user = _request_roles(body)
        stage = identify(system)
        content_type = handler.headers.get("Content-Type", "application/json")
        try:
            status, reason, reply_type, reply = self._forward(body, content_type)
        except TimeoutError:
            failure = Transport.UPSTREAM_TIMEOUT
        except ConnectionRefusedError:
            failure = Transport.UPSTREAM_UNREACHABLE
        except OSError, HTTPException:
            failure = Transport.UPSTREAM_TRANSPORT_ERROR
        else:
            try:
                handler.send_response(status, reason)
                handler.send_header("Content-Type", reply_type)
                handler.send_header("Content-Length", str(len(reply)))
                handler.end_headers()
                handler.wfile.write(reply)
                handler.wfile.flush()
            except OSError:
                return Observation(stage, Transport.CLIENT_DISCONNECTED)
            text = _reply_text(reply) if status == 200 else None
            if text is None:
                return Observation(stage, Transport.PROVIDER_REJECTED)
            return Observation(stage, Transport.DELIVERED, diagnose(stage, user, text))
        # No response is written: the adapter sees a dropped connection.
        handler.close_connection = True
        return Observation(stage, failure)

    def start(self) -> None:
        observer = self

        class Handler(BaseHTTPRequestHandler):
            def _observe(self) -> None:
                generation = observer.log.begin()
                observation = Observation(Stage.UNKNOWN, Transport.REQUEST_REJECTED)
                try:
                    observation = observer._relay(self)
                finally:
                    observer.log.end(generation, observation)

            do_POST = do_GET = do_PUT = do_DELETE = do_HEAD = _observe

            def log_message(self, format: str, *args: object) -> None:
                pass

        self._server = _ProxyServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join()
        self._server = self._thread = None

    def __enter__(self) -> ChatObserver:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
