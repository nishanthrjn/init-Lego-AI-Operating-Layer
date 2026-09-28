"""Comfy API v2 (beta): Comfy Cloud, Comfy API deployments, comfy-api-proxy.

Documented semantics used here (docs.comfy.org/api-reference/v2):
- POST /api/v2/jobs {"workflow": <API graph>} -> 201 Job; Idempotency-Key is
  single-use reject-on-duplicate and is released when a submission definitively
  fails without creating a job (validation, out-of-credits, queue-full).
- GET /api/v2/jobs/{id}: authoritative, resumable status until expires_at.
- GET /api/v2/jobs/{id}/workflow: {"format": "api"|"save", "workflow": {...}}.
- GET /api/v2/assets/{id}/content: bytes on self-hosted; 302 to a signed
  storage URL on Cloud/serverless.
- Errors: {"error": {"code", "message"}}; messages are never propagated.
Cancellation is documented (capability recorded) but not wired: it does not
guarantee cessation and LegoAI cancellation stays local-wait-only.
"""

import json
import uuid
from typing import Any
from urllib.parse import quote, urlsplit

from legoai.kernel.errors import ErrorCategory

from ..http import Response, https_origin
from ..png import MAX_IMAGE_BYTES
from ..values import ProviderJobRef, ReconciliationStatus
from ..workflow import MAX_WORKFLOW_BYTES, ApprovedWorkflow, json_object
from .base import (
    Budget,
    Capabilities,
    InvalidOutput,
    JobObservation,
    OutputRef,
    ProviderError,
    ProviderProfile,
    Submission,
    SubmissionRejected,
    Transport,
    TransportFactory,
)

CAPABILITIES = Capabilities(
    node_preflight=False,
    idempotent_submission=True,
    durable_job_lookup=True,
    job_scoped_cancel=True,
)
# Well-formed id that no job has; used only for read-only family detection.
PROBE_JOB_ID = "00000000-0000-4000-8000-000000000000"

_STATUS = {
    "queued": ReconciliationStatus.PENDING,
    "running": ReconciliationStatus.PENDING,
    "canceling": ReconciliationStatus.PENDING,
    "succeeded": ReconciliationStatus.COMPLETED,
    "failed": ReconciliationStatus.FAILED,
    "canceled": ReconciliationStatus.FAILED,
}
_REJECTED_422 = {
    "invalid_workflow": "invalid_workflow",
    "workflow_format_ui": "invalid_workflow",
    "missing_asset": "missing_asset",
}
_429 = {
    "queue_full": "queue_full",
    "deployment_not_ready": "provider_unavailable",
    "deployment_unavailable": "provider_unavailable",
    "rate_limited": "rate_limited",
}


def canonical_uuid(value: object) -> str:
    if type(value) is not str or str(uuid.UUID(value)) != value:
        raise ValueError("canonical UUID required")
    return value


def envelope_code(response: Response) -> str | None:
    if response.content_type.split(";")[0].strip() != "application/json":
        return None
    if len(response.body) > 64 * 1024:
        return None
    try:
        error = json_object(response.body).get("error")
    except ValueError:
        return None
    if type(error) is dict and type(error.get("code")) is str:
        code: str = error["code"]
        return code
    return None


def provider_error(response: Response, *, submit: bool) -> Exception:
    """Map a non-success response; only documented no-job rejections are NONE."""
    status, code = response.status, envelope_code(response)
    if 300 <= status < 400:
        return ValueError("redirect forbidden")
    kind = SubmissionRejected if submit else ProviderError
    if status == 401:
        return kind(ErrorCategory.AUTHORIZATION_DENIED, "authentication_failed")
    if status == 403:
        return kind(ErrorCategory.AUTHORIZATION_DENIED, "forbidden")
    if status == 402:
        return kind(ErrorCategory.DEPENDENCY_FAILURE, "insufficient_credits")
    if status == 422 and code in _REJECTED_422:
        return kind(ErrorCategory.VALIDATION_ERROR, _REJECTED_422[code])
    if status == 429:
        return kind(
            ErrorCategory.DEPENDENCY_FAILURE, _429.get(code or "", "rate_limited")
        )
    if status >= 500 or status == 422:
        # Includes idempotency_key_reuse: the job may exist; never NONE.
        return ProviderError(ErrorCategory.DEPENDENCY_FAILURE, "upstream_error")
    return ValueError("unexpected provider response")


def json_body(response: Response, status: int) -> dict[str, Any]:
    if (
        response.status != status
        or response.content_type.split(";")[0].strip() != "application/json"
    ):
        raise ValueError("unexpected JSON response")
    if len(response.body) > 1024 * 1024:
        raise ValueError("JSON response oversized")
    return json_object(response.body)


async def probe(budget: Budget, transport: Transport) -> bool:
    """v2 evidence is a structured not_found envelope for a well-formed id."""
    response = await budget.request(
        transport, "GET", "/api/v2/jobs/" + PROBE_JOB_ID, limit=64 * 1024
    )
    code = envelope_code(response)
    if response.status in (401, 403) and code in ("unauthorized", "forbidden"):
        raise provider_error(response, submit=False)
    return response.status == 404 and code == "not_found"


class V2Driver:
    def __init__(
        self,
        transport: Transport,
        *,
        download_origins: frozenset[str] = frozenset(),
        downloads: TransportFactory | None = None,
    ) -> None:
        self._transport = transport
        self._download_origins = frozenset(https_origin(o) for o in download_origins)
        self._downloads = downloads
        self._profile = ProviderProfile("v2", None, CAPABILITIES)

    @property
    def profile(self) -> ProviderProfile:
        return self._profile

    async def preflight(self, budget: Budget, workflow: ApprovedWorkflow) -> None:
        # v2 documents no node/model catalogue; compatibility is proven by the
        # provider rejecting (422, no job created) or accepting the submission.
        raise ProviderError(ErrorCategory.VERSION_MISMATCH, "capability_missing")

    async def submit(self, budget: Budget, graph: dict[str, Any]) -> Submission:
        body = json.dumps({"workflow": graph}, ensure_ascii=True).encode("utf-8")
        if len(body) > MAX_WORKFLOW_BYTES:
            raise ValueError("request oversized")
        response = await budget.request(
            self._transport,
            "POST",
            "/api/v2/jobs",
            body,
            limit=1024 * 1024,
            headers=(("Idempotency-Key", str(uuid.uuid4())),),
        )
        if response.status != 201:
            raise provider_error(response, submit=True)
        job = json_body(response, 201)
        return Submission(canonical_uuid(job.get("id")))

    async def observe(
        self, budget: Budget, job: ProviderJobRef, *, thorough: bool
    ) -> JobObservation:
        response = await budget.request(
            self._transport,
            "GET",
            "/api/v2/jobs/" + quote(job.job_id, safe=""),
            limit=1024 * 1024,
        )
        if response.status == 404 and envelope_code(response) == "not_found":
            return JobObservation(ReconciliationStatus.NOT_FOUND)
        if response.status != 200:
            raise provider_error(response, submit=False)
        item = json_body(response, 200)
        if item.get("id") != job.job_id:
            raise ValueError("job mismatch")
        state = item.get("status")
        if state == "expired":
            raise ProviderError(ErrorCategory.DEPENDENCY_FAILURE, "expired")
        if state not in _STATUS:
            raise ValueError("unknown job status")
        return JobObservation(
            _STATUS[state], item, "canceled" if state == "canceled" else None
        )

    async def recorded_graph(
        self, budget: Budget, job: ProviderJobRef, observation: JobObservation
    ) -> object:
        response = await budget.request(
            self._transport,
            "GET",
            "/api/v2/jobs/" + quote(job.job_id, safe="") + "/workflow",
            limit=1024 * 1024,
        )
        if response.status != 200:
            raise provider_error(response, submit=False)
        body = json_body(response, 200)
        if body.get("format") != "api":
            raise ValueError("authoring-format workflow is not attributable")
        return body.get("workflow")

    def output(self, observation: JobObservation) -> OutputRef:
        item = observation.detail
        outputs = item.get("outputs") if type(item) is dict else None
        if (
            type(outputs) is not list
            or len(outputs) != 1
            or type(outputs[0]) is not dict
        ):
            raise ValueError("expected exactly one output")
        output = outputs[0]
        if output.get("node_id") != "9" or output.get("content_type") != "image/png":
            raise ValueError("unexpected output")
        size = output.get("size_bytes")
        if size is not None and (
            type(size) is not int or not 0 < size <= MAX_IMAGE_BYTES
        ):
            raise ValueError("output size out of bounds")
        return OutputRef((canonical_uuid(output.get("id")),))

    async def fetch(self, budget: Budget, output: OutputRef) -> bytes:
        (asset,) = output.locator
        response = await budget.request(
            self._transport,
            "GET",
            "/api/v2/assets/" + quote(asset, safe="") + "/content",
            limit=MAX_IMAGE_BYTES,
        )
        if response.status == 200:
            if response.content_type.split(";")[0].strip() != "image/png":
                raise InvalidOutput("PNG response required")
            return response.body
        if response.status == 404:
            raise ProviderError(ErrorCategory.DEPENDENCY_FAILURE, "output_unavailable")
        if response.status not in (302, 303, 307) or response.location is None:
            raise provider_error(response, submit=False)
        return await self._signed(budget, response.location)

    async def _signed(self, budget: Budget, location: str) -> bytes:
        """One redirect hop to an allowlisted storage origin, without credentials."""
        parsed = urlsplit(location)
        origin = https_origin(f"{parsed.scheme}://{parsed.netloc}")
        if origin not in self._download_origins or self._downloads is None:
            raise ValueError("redirect to unapproved origin")
        path = (parsed.path or "/") + ("?" + parsed.query if parsed.query else "")
        response = await budget.request(
            self._downloads(origin, None), "GET", path, limit=MAX_IMAGE_BYTES
        )
        if response.status != 200:
            raise ProviderError(ErrorCategory.DEPENDENCY_FAILURE, "output_unavailable")
        # Object stores may label bytes generically; PNG bytes are validated above.
        if response.content_type.split(";")[0].strip() not in (
            "image/png",
            "application/octet-stream",
        ):
            raise InvalidOutput("PNG response required")
        return response.body
