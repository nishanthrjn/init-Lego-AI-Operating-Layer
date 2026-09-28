"""Internal ComfyUI provider-driver boundary; infrastructure, not a Core concept.

A driver owns one API family's routes, wire formats and error vocabulary and
translates them into these provider-neutral observations. Deadlines, effects,
attribution and PNG validation stay in the engine above it.
"""

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass, fields
from typing import Any, Protocol

from legoai.kernel.errors import ErrorCategory

from ..http import Headers, Response
from ..values import REASONS, ProviderJobRef, ReconciliationStatus, reason_code
from ..workflow import ApprovedWorkflow, json_object


class Transport(Protocol):
    async def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        limit: int,
        headers: Headers = (),
    ) -> Response: ...


TransportFactory = Callable[[str, str | None], Transport]
"""(origin, bearer token or None) -> transport bound to exactly that origin."""


class ProviderError(OSError):
    """Normalized provider failure; carries a category and closed reason code."""

    def __init__(
        self, category: ErrorCategory, reason: str, evidence: tuple[str, ...] = ()
    ) -> None:
        if reason not in REASONS:
            raise ValueError("unknown reason")
        super().__init__(reason)
        self.category = category
        self.reason = reason
        # Sanitized observations (see `observed`) for operator diagnosis only.
        self.evidence = evidence


_MEDIA = re.compile(r"[a-z0-9.+-]{1,32}/[a-z0-9.+-]{1,64}")
_CODE = re.compile(r"[A-Za-z0-9_.-]{1,64}")


def error_code(response: Response) -> str | None:
    """The provider's structured error code, if it is a short identifier."""
    if response.content_type.split(";")[0].strip() != "application/json":
        return None
    if len(response.body) > 64 * 1024:
        return None
    try:
        error = json_object(response.body).get("error")
    except ValueError, RecursionError:
        return None
    code = error.get("code") if type(error) is dict else None
    return code if type(code) is str and _CODE.fullmatch(code) else None


def observed(label: str, response: Response) -> str:
    """Status, media type and error-code identifier only: never bodies or messages."""
    media = response.content_type.split(";")[0].strip().lower()
    return (
        f"{label}: status={response.status}"
        f" type={media if _MEDIA.fullmatch(media) else 'other'}"
        f" code={error_code(response) or '-'}"
    )


class SubmissionRejected(ProviderError):
    """Provider documents that this rejection created no job: effect NONE."""


class InvalidOutput(ValueError):
    """Provider answered, but not with an acceptable output representation."""


class RequestTimeout(OSError):
    """One exchange exceeded its own bound before the total deadline."""


class ReadOnlyTransport:
    """Reconciliation/probe transport: structurally incapable of submitting work."""

    def __init__(self, inner: Transport) -> None:
        self.inner = inner

    async def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        limit: int,
        headers: Headers = (),
    ) -> Response:
        if method != "GET" or body:
            # Not an OSError: a violated invariant must never become a result.
            raise RuntimeError("read-only operation must never submit")
        return await self.inner.request(method, path, body, limit=limit)


@dataclass(frozen=True, slots=True)
class Budget:
    """Monotonic deadline shared by every exchange of one operation."""

    deadline: float
    clock: Callable[[], float]
    request_timeout: float
    read_only: bool = False

    async def request(
        self,
        transport: Transport,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        limit: int,
        headers: Headers = (),
    ) -> Response:
        if self.read_only:
            transport = ReadOnlyTransport(transport)
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            raise TimeoutError
        try:
            async with asyncio.timeout(min(self.request_timeout, remaining)):
                if headers:
                    return await transport.request(
                        method, path, body, limit=limit, headers=headers
                    )
                return await transport.request(method, path, body, limit=limit)
        except TimeoutError:
            if self.request_timeout < remaining:
                raise RequestTimeout("request timeout") from None
            raise


@dataclass(frozen=True, slots=True)
class Capabilities:
    """Only what current behavior branches on; never inferred from versions."""

    node_preflight: bool
    idempotent_submission: bool
    durable_job_lookup: bool
    job_scoped_cancel: bool

    @classmethod
    def names(cls) -> frozenset[str]:
        return frozenset(f.name for f in fields(cls))

    def supports(self, name: str) -> bool:
        if name not in self.names():
            raise ValueError("unknown capability")
        return bool(getattr(self, name))


@dataclass(frozen=True, slots=True)
class ProviderProfile:
    family: str
    version: str | None
    capabilities: Capabilities

    def __post_init__(self) -> None:
        if self.family not in ("legacy", "v2"):
            raise ValueError("unsupported API family")
        if self.version is not None and (
            type(self.version) is not str
            or not 1 <= len(self.version) <= 64
            or any(not 0x21 <= ord(c) <= 0x7E for c in self.version)
        ):
            raise ValueError("invalid version")


@dataclass(frozen=True, slots=True)
class Submission:
    job_id: str
    problem: bool = False  # Job known, but the provider reported submission errors.


@dataclass(frozen=True, slots=True)
class JobObservation:
    """Provider state for one job; `detail` is private to the producing driver."""

    status: ReconciliationStatus
    detail: Any = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status is ReconciliationStatus.UNRESOLVED:
            raise ValueError("drivers raise instead of reporting unresolved")
        reason_code(self.reason)


@dataclass(frozen=True, slots=True)
class OutputRef:
    """Validated locator for exactly one PNG output; meaningful to its driver only."""

    locator: tuple[str, ...]


class ComfyDriver(Protocol):
    @property
    def profile(self) -> ProviderProfile: ...

    async def preflight(self, budget: Budget, workflow: ApprovedWorkflow) -> None:
        """Workflow compatibility checks; only called with node_preflight."""
        ...

    async def submit(self, budget: Budget, graph: dict[str, Any]) -> Submission:
        """Exactly one submission attempt; never retried."""
        ...

    async def observe(
        self, budget: Budget, job: ProviderJobRef, *, thorough: bool
    ) -> JobObservation:
        """thorough distinguishes pending from absent where that costs extra calls."""
        ...

    async def recorded_graph(
        self, budget: Budget, job: ProviderJobRef, observation: JobObservation
    ) -> object:
        """Provider-recorded API graph for attribution, or ValueError."""
        ...

    def output(self, observation: JobObservation) -> OutputRef:
        """Exactly one PNG output of a completed job, or ValueError."""
        ...

    async def fetch(self, budget: Budget, output: OutputRef) -> bytes:
        """Output bytes; PNG validation happens above the driver."""
        ...
