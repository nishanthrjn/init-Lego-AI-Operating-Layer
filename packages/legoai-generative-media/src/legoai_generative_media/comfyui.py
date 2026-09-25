"""Single-submit local ComfyUI workflow execution; no runtime management."""

import asyncio
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
    TextToImageRequest,
    identifier,
)
from .workflow import ApprovedWorkflow, json_object, template


class Transport(Protocol):
    async def request(
        self, method: str, path: str, body: bytes = b"", *, limit: int
    ) -> Response: ...


@dataclass(frozen=True, slots=True)
class ComfyUIConfig:
    workflow: ApprovedWorkflow
    endpoint: Endpoint = Endpoint()
    binding: str = "comfyui-local"
    timeout_seconds: float = 300
    poll_interval: float = 1
    max_polls: int = 300

    def __post_init__(self) -> None:
        if (
            type(self.workflow) is not ApprovedWorkflow
            or type(self.endpoint) is not Endpoint
        ):
            raise TypeError("validated workflow and endpoint required")
        identifier(self.binding)
        for value, lower, upper in (
            (self.timeout_seconds, 0.01, 300),
            (self.poll_interval, 0.001, 5),
        ):
            if type(value) not in (float, int) or not lower <= value <= upper:
                raise ValueError("invalid time bound")
        if type(self.max_polls) is not int or not 1 <= self.max_polls <= 300:
            raise ValueError("invalid poll bound")


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


@dataclass(frozen=True)
class LocalComfyUIAdapter:
    config: ComfyUIConfig
    transport: Transport | None = field(default=None, repr=False)
    _busy: bool = field(default=False, init=False, repr=False)

    async def _preflight(self, http: Transport) -> None:
        for node in sorted(
            {
                v["class_type"]
                for v in template(self.config.workflow.checkpoint).values()
            }
        ):
            response = object_response(
                await http.request(
                    "GET", "/object_info/" + quote(node, safe=""), limit=1024 * 1024
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
        http = (
            self.transport
            if self.transport is not None
            else LocalHTTP(self.config.endpoint)
        )
        try:
            async with asyncio.timeout(self.config.timeout_seconds):
                payload = self.config.workflow.bind(request)
                await self._preflight(http)
                # Conservative from the instant dispatch might occur: never resubmit.
                effect = EffectExtent.UNKNOWN
                response = object_response(
                    await http.request("POST", "/prompt", payload, limit=1024 * 1024)
                )
                job = ProviderJobRef(
                    "comfyui", self.config.binding, response["prompt_id"]
                )
                if response.get("node_errors") not in ({}, None):
                    raise ValueError("submission node errors")
                for attempt in range(self.config.max_polls):
                    if attempt:
                        await asyncio.sleep(self.config.poll_interval)
                    history = object_response(
                        await http.request(
                            "GET",
                            "/history/" + quote(job.job_id, safe=""),
                            limit=1024 * 1024,
                        )
                    )
                    if not history:
                        continue
                    if set(history) != {job.job_id}:
                        raise ValueError("history job mismatch")
                    item = history[job.job_id]
                    if type(item) is not dict or type(item.get("status")) is not dict:
                        raise ValueError("malformed history")
                    status = item["status"]
                    if status.get("status_str") == "error":
                        category = ErrorCategory.EXECUTION_FAILURE
                        raise ValueError("generation failed")
                    if (
                        status.get("completed") is not True
                        or status.get("status_str") != "success"
                    ):
                        raise ValueError("nonterminal malformed history")
                    effect = EffectExtent.COMPLETED
                    outputs = item.get("outputs")
                    category = ErrorCategory.VALIDATION_ERROR
                    if type(outputs) is not dict or set(outputs) != {"9"}:
                        raise ValueError("unexpected output nodes")
                    output = outputs["9"]
                    if type(output) is not dict or set(output) != {"images"}:
                        raise ValueError("unexpected output fields")
                    images = output["images"]
                    if (
                        type(images) is not list
                        or len(images) != 1
                        or type(images[0]) is not dict
                    ):
                        raise ValueError("expected exactly one image")
                    image = images[0]
                    if (
                        set(image) != {"filename", "subfolder", "type"}
                        or image["type"] != "output"
                    ):
                        raise ValueError("unexpected image descriptor")
                    filename, folder = safe_location(
                        image["filename"], image["subfolder"]
                    )
                    category = ErrorCategory.DEPENDENCY_FAILURE
                    raw = await http.request(
                        "GET",
                        "/view?"
                        + urlencode(
                            {
                                "filename": filename,
                                "subfolder": folder,
                                "type": "output",
                            }
                        ),
                        limit=MAX_IMAGE_BYTES,
                    )
                    category = ErrorCategory.VALIDATION_ERROR
                    if (
                        raw.status != 200
                        or raw.content_type.split(";")[0].strip() != "image/png"
                    ):
                        raise ValueError("PNG response required")
                    generated = GeneratedImage(
                        raw.body,
                        job,
                        self.config.workflow.reference,
                        request.seed if request.seed is not None else 0,
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
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            RecursionError,
            asyncio.IncompleteReadError,
            asyncio.LimitOverrunError,
        ):
            return GenerationResult(Outcome.FAILED, effect, job, error=category)
        finally:
            object.__setattr__(self, "_busy", False)


# No global interrupt, queue clear, deletion, retry or output-directory access.
