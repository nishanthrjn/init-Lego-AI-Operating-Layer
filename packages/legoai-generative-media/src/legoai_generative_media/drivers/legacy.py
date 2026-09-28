"""OSS ComfyUI server API: /prompt, /history, /queue, /view, /object_info.

Semantics: in-memory history (lost on restart/eviction), no idempotent
submission, so a lost acknowledgement stays UNKNOWN. The job-scoped cancel
route present in newer servers is not used until live-qualified.
"""

import json
from typing import Any
from urllib.parse import quote, urlencode

from ..http import Response
from ..png import MAX_IMAGE_BYTES
from ..values import ProviderJobRef, ReconciliationStatus
from ..workflow import MAX_WORKFLOW_BYTES, ApprovedWorkflow, json_object
from .base import (
    Budget,
    Capabilities,
    InvalidOutput,
    JobObservation,
    OutputRef,
    ProviderProfile,
    Submission,
    Transport,
    observed,
)

CAPABILITIES = Capabilities(
    node_preflight=True,
    idempotent_submission=False,
    durable_job_lookup=False,
    job_scoped_cancel=False,
)


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


def history_status(item: dict[str, Any]) -> ReconciliationStatus:
    """COMPLETED or FAILED; anything else is malformed, never inferred."""
    status = item.get("status")
    if type(status) is not dict:
        raise ValueError("malformed history")
    if status.get("status_str") == "error":
        return ReconciliationStatus.FAILED
    if status.get("completed") is not True or status.get("status_str") != "success":
        raise ValueError("nonterminal malformed history")
    return ReconciliationStatus.COMPLETED


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


async def probe(budget: Budget, transport: Transport) -> tuple[str | None, str]:
    """(version, evidence); version None unless /system_stats is legacy-shaped."""
    response = await budget.request(
        transport, "GET", "/system_stats", limit=1024 * 1024
    )
    evidence = observed("legacy probe", response)
    try:
        system = object_response(response).get("system")
    except ValueError, RecursionError:
        return None, evidence
    if type(system) is not dict or type(system.get("comfyui_version")) is not str:
        return None, evidence
    version: str = system["comfyui_version"]
    return version, evidence


class LegacyDriver:
    def __init__(self, transport: Transport, version: str | None = None) -> None:
        self._transport = transport
        self._profile = ProviderProfile("legacy", version, CAPABILITIES)

    @property
    def profile(self) -> ProviderProfile:
        return self._profile

    async def preflight(self, budget: Budget, workflow: ApprovedWorkflow) -> None:
        for node in sorted(workflow.required_nodes):
            response = object_response(
                await budget.request(
                    self._transport,
                    "GET",
                    "/object_info/" + quote(node, safe=""),
                    limit=1024 * 1024,
                )
            )
            if node not in response or type(response[node]) is not dict:
                raise ValueError("missing required node")
            if node == "CheckpointLoaderSimple":
                choices = response[node]["input"]["required"]["ckpt_name"][0]
                if type(choices) is not list or workflow.checkpoint not in choices:
                    raise ValueError("missing approved checkpoint")

    async def submit(self, budget: Budget, graph: dict[str, Any]) -> Submission:
        payload = json.dumps({"prompt": graph}, ensure_ascii=True).encode("utf-8")
        if len(payload) > MAX_WORKFLOW_BYTES:
            raise ValueError("request oversized")
        response = object_response(
            await budget.request(
                self._transport, "POST", "/prompt", payload, limit=1024 * 1024
            )
        )
        return Submission(
            response["prompt_id"], response.get("node_errors") not in ({}, None)
        )

    async def _history(
        self, budget: Budget, job: ProviderJobRef
    ) -> dict[str, Any] | None:
        history = object_response(
            await budget.request(
                self._transport,
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

    async def observe(
        self, budget: Budget, job: ProviderJobRef, *, thorough: bool
    ) -> JobObservation:
        """history -> queue -> history closes the running->done race.

        The server moves a job from running to history under one lock, so a
        job absent from the queue is either found by the recheck or gone.
        Without `thorough`, absence from history is reported as PENDING: the
        caller is waiting for its own submission.
        """
        item = await self._history(budget, job)
        if item is None:
            if not thorough:
                return JobObservation(ReconciliationStatus.PENDING)
            queue = object_response(
                await budget.request(
                    self._transport, "GET", "/queue", limit=1024 * 1024
                )
            )
            entry = queued_entry(queue, job)
            if entry is not None:
                return JobObservation(ReconciliationStatus.PENDING, ("queue", entry))
            item = await self._history(budget, job)
            if item is None:
                return JobObservation(ReconciliationStatus.NOT_FOUND)
        return JobObservation(history_status(item), ("history", item))

    async def recorded_graph(
        self, budget: Budget, job: ProviderJobRef, observation: JobObservation
    ) -> object:
        if type(observation.detail) is not tuple:
            raise ValueError("no recorded graph")
        kind, value = observation.detail
        if kind == "queue":
            return value[2]
        prompt = value.get("prompt")
        if type(prompt) is not list or len(prompt) < 3 or prompt[1] != job.job_id:
            raise ValueError("history lacks job attribution")
        return prompt[2]

    def output(self, observation: JobObservation) -> OutputRef:
        if type(observation.detail) is not tuple or observation.detail[0] != "history":
            raise ValueError("no completed history")
        return OutputRef(output_location(observation.detail[1]))

    async def fetch(self, budget: Budget, output: OutputRef) -> bytes:
        filename, folder = output.locator
        raw = await budget.request(
            self._transport,
            "GET",
            "/view?"
            + urlencode({"filename": filename, "subfolder": folder, "type": "output"}),
            limit=MAX_IMAGE_BYTES,
        )
        if raw.status != 200 or raw.content_type.split(";")[0].strip() != "image/png":
            raise InvalidOutput("PNG response required")
        return raw.body


# No global interrupt, queue clear, deletion, retry or output-directory access.
