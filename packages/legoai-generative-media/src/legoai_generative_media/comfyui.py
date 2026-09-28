"""Single-submit local ComfyUI workflow execution; no runtime management."""

import asyncio
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import quote, urlencode

from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory

from .http import Endpoint, LocalHTTP, Response
from .png import MAX_IMAGE_BYTES
from .values import (
    Cessation,
    GeneratedImage,
    GenerationCancelled,
    GenerationResult,
    Outcome,
    ProviderJobRef,
    ReconciliationResult,
    ReconciliationStatus,
    TextToImageRequest,
    identifier,
)
from .workflow import ApprovedWorkflow, json_object, template

# Observed fixed-workflow CPU run: ~640 s. 1800 s admits ~2.8x that variance
# (throttling, concurrent load) while keeping every wait finite.
HARD_MAX_WAIT_SECONDS = 1800
MAX_POLL_INTERVAL_SECONDS = 30
MAX_REQUEST_TIMEOUT_SECONDS = 60

FAILURES = (
    OSError,
    ValueError,
    TypeError,
    KeyError,
    IndexError,
    RecursionError,
    asyncio.IncompleteReadError,
    asyncio.LimitOverrunError,
)


class Transport(Protocol):
    async def request(
        self, method: str, path: str, body: bytes = b"", *, limit: int
    ) -> Response: ...


def _bounded(value: float, lower: float, upper: float, name: str) -> None:
    if (
        type(value) not in (float, int)
        or not math.isfinite(value)
        or not lower <= value <= upper
    ):
        raise ValueError(f"invalid {name}")


@dataclass(frozen=True, slots=True)
class CompletionPolicy:
    """Operator-side waiting bounds; never part of the application request.

    max_wait bounds one call from start to result. request_timeout bounds each
    HTTP exchange separately, so no single call can consume the whole wait.
    The poll count is derived, never coordinated by hand.
    """

    max_wait_seconds: float = 300
    poll_interval_seconds: float = 1
    request_timeout_seconds: float = 10

    def __post_init__(self) -> None:
        _bounded(self.max_wait_seconds, 0.5, HARD_MAX_WAIT_SECONDS, "total wait")
        _bounded(
            self.poll_interval_seconds,
            0.05,
            min(MAX_POLL_INTERVAL_SECONDS, self.max_wait_seconds / 10),
            "poll interval",
        )
        _bounded(
            self.request_timeout_seconds,
            0.01,
            min(MAX_REQUEST_TIMEOUT_SECONDS, self.max_wait_seconds),
            "request timeout",
        )

    @classmethod
    def for_wait(cls, max_wait_seconds: float) -> CompletionPolicy:
        """One operator setting; interval and request bounds are derived."""
        _bounded(max_wait_seconds, 0.5, HARD_MAX_WAIT_SECONDS, "total wait")
        return cls(
            max_wait_seconds,
            min(1, max_wait_seconds / 10),
            min(10, max_wait_seconds),
        )

    @property
    def max_polls(self) -> int:
        # Termination backstop even if an injected clock never advances.
        return int(self.max_wait_seconds // self.poll_interval_seconds) + 1


@dataclass(frozen=True, slots=True)
class ComfyUIConfig:
    workflow: ApprovedWorkflow
    endpoint: Endpoint = Endpoint()
    binding: str = "comfyui-local"
    completion: CompletionPolicy = CompletionPolicy()

    def __post_init__(self) -> None:
        if (
            type(self.workflow) is not ApprovedWorkflow
            or type(self.endpoint) is not Endpoint
            or type(self.completion) is not CompletionPolicy
        ):
            raise TypeError("validated workflow, endpoint and policy required")
        identifier(self.binding)


class RequestTimeout(OSError):
    """One exchange exceeded its own bound before the total deadline."""


class ReadOnlyTransport:
    """Reconciliation transport: structurally incapable of submitting work."""

    def __init__(self, inner: Transport) -> None:
        self.inner = inner

    async def request(
        self, method: str, path: str, body: bytes = b"", *, limit: int
    ) -> Response:
        if method != "GET" or body:
            # Not an OSError: a violated invariant must never become a result.
            raise RuntimeError("reconciliation must never submit")
        return await self.inner.request(method, path, body, limit=limit)


def safe_location(filename: object, subfolder: object) -> tuple[str, str]:
    if type(filename) is not str or type(subfolder) is not str:
        raise ValueError("invalid output location")
    if not filename or len(filename) > 255 or len(subfolder) > 512:
        raise ValueError("invalid output location")
    for value in (filename, subfolder):
        if any(ord(c) < 32 or ord(c) == 127 for c in value) or any(
            c in value for c in "\\:%"
        ):
            raise ValueError("unsafe output location")
    if "/" in filename or filename in (".", "..") or not filename.endswith(".png"):
        raise ValueError("unsafe filename")
    if subfolder and any(part in ("", ".", "..") for part in subfolder.split("/")):
        raise ValueError("unsafe subfolder")
    return filename, subfolder


def object_response(response: Response) -> dict[str, Any]:
    if (
        response.status != 200
        or response.content_type.split(";")[0].strip() != "application/json"
    ):
        raise ValueError("unexpected JSON response")
    if len(response.body) > 1024 * 1024:
        raise ValueError("JSON response oversized")
    return json_object(response.body)


def history_status(item: dict[str, Any]) -> str:
    """'success' or 'error'; anything else is malformed, never inferred."""
    status = item.get("status")
    if type(status) is not dict:
        raise ValueError("malformed history")
    if status.get("status_str") == "error":
        return "error"
    if status.get("completed") is not True or status.get("status_str") != "success":
        raise ValueError("nonterminal malformed history")
    return "success"


def output_location(item: dict[str, Any]) -> tuple[str, str]:
    """Exactly node 9 with one safe output PNG locator."""
    outputs = item.get("outputs")
    if type(outputs) is not dict or set(outputs) != {"9"}:
        raise ValueError("unexpected output nodes")
    output = outputs["9"]
    if type(output) is not dict or set(output) != {"images"}:
        raise ValueError("unexpected output fields")
    images = output["images"]
    if type(images) is not list or len(images) != 1 or type(images[0]) is not dict:
        raise ValueError("expected exactly one image")
    image = images[0]
    if set(image) != {"filename", "subfolder", "type"} or image["type"] != "output":
        raise ValueError("unexpected image descriptor")
    return safe_location(image["filename"], image["subfolder"])


def queued_entry(queue: dict[str, Any], job: ProviderJobRef) -> list[Any] | None:
    if not {"queue_running", "queue_pending"} <= set(queue):
        raise ValueError("malformed queue")
    found: list[Any] | None = None
    for key in ("queue_running", "queue_pending"):
        entries = queue[key]
        if type(entries) is not list:
            raise ValueError("malformed queue")
        for entry in entries:
            if type(entry) is not list or len(entry) < 3:
                raise ValueError("malformed queue entry")
            if entry[1] == job.job_id:
                if found is not None:
                    raise ValueError("duplicate queue entry")
                found = entry
    return found


@dataclass(frozen=True)
class LocalComfyUIAdapter:
    config: ComfyUIConfig
    transport: Transport | None = field(default=None, repr=False)
    # Monotonic clock/sleep are injectable so long jobs are testable without waiting.
    clock: Callable[[], float] = field(default=time.monotonic, repr=False)
    sleep: Callable[[float], Awaitable[None]] = field(default=asyncio.sleep, repr=False)
    _busy: bool = field(default=False, init=False, repr=False)

    def _http(self) -> Transport:
        if self.transport is not None:
            return self.transport
        return LocalHTTP(
            self.config.endpoint, self.config.completion.request_timeout_seconds
        )

    async def _call(
        self,
        http: Transport,
        deadline: float,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        limit: int,
    ) -> Response:
        remaining = deadline - self.clock()
        if remaining <= 0:
            raise TimeoutError
        bound = self.config.completion.request_timeout_seconds
        try:
            async with asyncio.timeout(min(bound, remaining)):
                return await http.request(method, path, body, limit=limit)
        except TimeoutError:
            if bound < remaining:
                raise RequestTimeout("request timeout") from None
            raise

    async def _pause(self, deadline: float) -> None:
        remaining = deadline - self.clock()
        if remaining <= 0:
            raise TimeoutError
        await self.sleep(min(self.config.completion.poll_interval_seconds, remaining))

    async def _history(
        self, http: Transport, deadline: float, job: ProviderJobRef
    ) -> dict[str, Any] | None:
        history = object_response(
            await self._call(
                http,
                deadline,
                "GET",
                "/history/" + quote(job.job_id, safe=""),
                limit=1024 * 1024,
            )
        )
        if not history:
            return None
        if set(history) != {job.job_id}:
            raise ValueError("history job mismatch")
        item = history[job.job_id]
        if type(item) is not dict:
            raise ValueError("malformed history")
        return item

    async def _fetch(
        self, http: Transport, deadline: float, location: tuple[str, str]
    ) -> Response:
        filename, folder = location
        return await self._call(
            http,
            deadline,
            "GET",
            "/view?"
            + urlencode({"filename": filename, "subfolder": folder, "type": "output"}),
            limit=MAX_IMAGE_BYTES,
        )

    def _image(self, raw: Response, job: ProviderJobRef, seed: int) -> GeneratedImage:
        if raw.status != 200 or raw.content_type.split(";")[0].strip() != "image/png":
            raise ValueError("PNG response required")
        return GeneratedImage(raw.body, job, self.config.workflow.reference, seed)

    async def _preflight(self, http: Transport, deadline: float) -> None:
        for node in sorted(
            {
                v["class_type"]
                for v in template(self.config.workflow.checkpoint).values()
            }
        ):
            response = object_response(
                await self._call(
                    http,
                    deadline,
                    "GET",
                    "/object_info/" + quote(node, safe=""),
                    limit=1024 * 1024,
                )
            )
            if node not in response or type(response[node]) is not dict:
                raise ValueError("missing required node")
            if node == "CheckpointLoaderSimple":
                choices = response[node]["input"]["required"]["ckpt_name"][0]
                if (
                    type(choices) is not list
                    or self.config.workflow.checkpoint not in choices
                ):
                    raise ValueError("missing approved checkpoint")

    async def generate(self, request: TextToImageRequest) -> GenerationResult:
        if type(request) is not TextToImageRequest:
            raise TypeError("TextToImageRequest required")
        if self._busy:
            return GenerationResult(
                Outcome.FAILED, EffectExtent.NONE, error=ErrorCategory.CONFLICT
            )
        object.__setattr__(self, "_busy", True)
        effect = EffectExtent.NONE
        job: ProviderJobRef | None = None
        category = ErrorCategory.DEPENDENCY_FAILURE
        policy = self.config.completion
        http = self._http()
        deadline = self.clock() + policy.max_wait_seconds
        try:
            # Real-time backstop even if an injected clock misbehaves.
            async with asyncio.timeout(policy.max_wait_seconds):
                payload = self.config.workflow.bind(request)
                await self._preflight(http, deadline)
                # Conservative from the instant dispatch might occur: never resubmit.
                effect = EffectExtent.UNKNOWN
                response = object_response(
                    await self._call(
                        http, deadline, "POST", "/prompt", payload, limit=1024 * 1024
                    )
                )
                job = ProviderJobRef(
                    "comfyui", self.config.binding, response["prompt_id"]
                )
                if response.get("node_errors") not in ({}, None):
                    raise ValueError("submission node errors")
                for attempt in range(policy.max_polls):
                    if attempt:
                        await self._pause(deadline)
                    item = await self._history(http, deadline, job)
                    if item is None:
                        continue
                    if history_status(item) == "error":
                        category = ErrorCategory.EXECUTION_FAILURE
                        raise ValueError("generation failed")
                    effect = EffectExtent.COMPLETED
                    category = ErrorCategory.VALIDATION_ERROR
                    location = output_location(item)
                    category = ErrorCategory.DEPENDENCY_FAILURE
                    raw = await self._fetch(http, deadline, location)
                    category = ErrorCategory.VALIDATION_ERROR
                    generated = self._image(
                        raw, job, request.seed if request.seed is not None else 0
                    )
                    return GenerationResult(Outcome.SUCCESS, effect, job, generated)
                raise TimeoutError("poll bound exceeded")
        except asyncio.CancelledError:
            raise GenerationCancelled(
                GenerationResult(
                    Outcome.CANCELLED, effect, job, cessation=Cessation.UNKNOWN
                )
            ) from None
        except TimeoutError:
            return GenerationResult(
                Outcome.DEADLINE,
                effect,
                job,
                error=ErrorCategory.DEADLINE_EXCEEDED,
                cessation=Cessation.UNKNOWN,
            )
        except FAILURES:
            return GenerationResult(Outcome.FAILED, effect, job, error=category)
        finally:
            object.__setattr__(self, "_busy", False)

    async def reconcile(self, job: ProviderJobRef) -> ReconciliationResult:
        """Inspect one existing job; never submits, retries, interrupts or deletes.

        Order history -> queue -> history closes the running->done race: the
        provider moves a job from running to history under one lock, so a job
        absent from the queue is either in the recheck or no longer exposed.
        Cancellation propagates unchanged: reconciliation has no effect to retain.
        """
        if type(job) is not ProviderJobRef:
            raise TypeError("ProviderJobRef required")
        if job.provider != "comfyui" or job.binding != self.config.binding:
            raise ValueError("job not owned by this binding")
        http = ReadOnlyTransport(self._http())
        wait = self.config.completion.max_wait_seconds
        deadline = self.clock() + wait
        completed = False
        category = ErrorCategory.DEPENDENCY_FAILURE
        try:
            async with asyncio.timeout(wait):
                item = await self._history(http, deadline, job)
                if item is None:
                    queue = object_response(
                        await self._call(
                            http, deadline, "GET", "/queue", limit=1024 * 1024
                        )
                    )
                    category = ErrorCategory.VALIDATION_ERROR
                    entry = queued_entry(queue, job)
                    if entry is not None:
                        self.config.workflow.attribute(entry[2])
                        return ReconciliationResult(job, ReconciliationStatus.PENDING)
                    category = ErrorCategory.DEPENDENCY_FAILURE
                    item = await self._history(http, deadline, job)
                    if item is None:
                        # Absence is not evidence of non-execution or failure.
                        return ReconciliationResult(job, ReconciliationStatus.NOT_FOUND)
                category = ErrorCategory.VALIDATION_ERROR
                prompt = item.get("prompt")
                if (
                    type(prompt) is not list
                    or len(prompt) < 3
                    or prompt[1] != job.job_id
                ):
                    raise ValueError("history lacks job attribution")
                request = self.config.workflow.attribute(prompt[2])
                if history_status(item) == "error":
                    return ReconciliationResult(
                        job,
                        ReconciliationStatus.FAILED,
                        error=ErrorCategory.EXECUTION_FAILURE,
                    )
                # Completion is now established; later faults cannot retract it.
                completed = True
                location = output_location(item)
                category = ErrorCategory.DEPENDENCY_FAILURE
                raw = await self._fetch(http, deadline, location)
                category = ErrorCategory.VALIDATION_ERROR
                image = self._image(
                    raw, job, request.seed if request.seed is not None else 0
                )
                return ReconciliationResult(
                    job, ReconciliationStatus.COMPLETED, image=image
                )
        except TimeoutError:
            category = ErrorCategory.DEADLINE_EXCEEDED
        except FAILURES:
            pass
        return ReconciliationResult(
            job,
            ReconciliationStatus.COMPLETED
            if completed
            else ReconciliationStatus.UNRESOLVED,
            error=category,
        )


# No global interrupt, queue clear, deletion, retry or output-directory access.
