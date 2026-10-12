"""Configuration-driven composition: applications receive ports, never drivers.

`open_text_to_image` admits secret-free scope, discovers or trusts the
configured API family, selects an admitted driver from the closed registry
and returns a governed TextToImagePort + JobReconciliationPort.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

from legoai.kernel.errors import ErrorCategory

from .comfyui import ComfyTextToImageAdapter
from .composition import TRY_ON_OFFER, invoke, invoke_try_on
from .config import GenerationConfig, ProviderConfig, TryOnConfig
from .discovery import DRIVERS, confirm, discover
from .drivers.base import (
    Budget,
    ComfyDriver,
    ProviderError,
    ProviderProfile,
    Transport,
    TransportFactory,
)
from .http import Endpoint, Headers, LocalHTTP, RemoteHTTPS, Response
from .local_host import prepare_local
from .transfer import ImageTransfer
from .values import (
    GenerationResult,
    ProviderJobRef,
    ReconciliationResult,
    TextToImageRequest,
    TryOnRequest,
)
from .virtual_try_on import ComfyVirtualTryOnAdapter

__all__ = [
    "ProviderError",
    "ProviderProfile",
    "PreflightReport",
    "TextToImageService",
    "TryOnService",
    "WriteCounter",
    "default_transports",
    "open_image_transfer",
    "open_text_to_image",
    "open_virtual_try_on",
    "preflight_virtual_try_on",
    "probe_provider",
]


def _require_secret_free(provider: ProviderConfig) -> None:
    if provider.auth != "none" or provider.secret_ref is not None:
        raise ProviderError(
            ErrorCategory.POLICY_VIOLATION, "credentialled_provider_unsupported"
        )


def default_transports(provider: ProviderConfig) -> TransportFactory:
    _require_secret_free(provider)
    timeout = provider.completion.request_timeout_seconds

    def make(origin: str, token: str | None) -> LocalHTTP | RemoteHTTPS:
        if token is not None:
            raise ProviderError(
                ErrorCategory.POLICY_VIOLATION, "credentialled_provider_unsupported"
            )
        if provider.deployment == "local":
            return LocalHTTP(Endpoint(origin), timeout, token=token)
        return RemoteHTTPS(origin, timeout, token=token)

    return make


@dataclass(frozen=True)
class TextToImageService:
    """One configured provider behind the application-facing ports."""

    config: GenerationConfig
    adapter: ComfyTextToImageAdapter = field(repr=False)

    @property
    def profile(self) -> ProviderProfile:
        return self.adapter.profile

    def job(self, job_id: str) -> ProviderJobRef:
        return ProviderJobRef("comfyui", self.adapter.binding, job_id)

    def describe(self) -> dict[str, str]:
        """Safe diagnostics: no credentials, prompts, bytes or raw responses."""
        profile = self.profile
        capabilities = profile.capabilities
        return {
            "api_family": profile.family,
            "version": profile.version or "not observable",
            "origin": self.config.provider.origin,
            "deployment": self.config.provider.deployment,
            "binding": self.adapter.binding,
            "workflow_sha256": self.adapter.workflow.reference.sha256,
            "capabilities": ",".join(
                sorted(n for n in capabilities.names() if capabilities.supports(n))
            ),
        }

    async def generate(self, request: TextToImageRequest) -> GenerationResult:
        policy = self.adapter.completion
        async with await prepare_local(
            self.adapter,
            self.config.digest,
            approved=self.adapter.workflow.reference,
            timeout=policy.max_wait_seconds,
            binding=self.adapter.binding,
        ) as session:
            _, result = await invoke(
                session.execution,
                session.ready,
                session.context,
                session.contribution,
                session.contribution.revision,
                request,
            )
            return result

    async def reconcile(self, job: ProviderJobRef) -> ReconciliationResult:
        return await self.adapter.reconcile(job)


async def probe_provider(
    config: GenerationConfig,
    *,
    environ: Mapping[str, str] | None = None,
    transports: TransportFactory | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> ProviderProfile:
    """Read-only reachability/family/capability check; never submits."""
    provider = config.provider
    _require_secret_free(provider)
    factory = transports or default_transports(provider)
    primary = factory(provider.origin, None)
    timeout = provider.completion.request_timeout_seconds
    if provider.api_family == "auto":
        found, version = await discover(
            "auto", primary, request_timeout=timeout, clock=clock
        )
    else:
        # Explicit family: confirm only that family is reachable and present.
        found = provider.api_family
        version = await confirm(found, primary, request_timeout=timeout, clock=clock)
    return DRIVERS[found](
        version, primary, frozenset(provider.download_origins), factory
    ).profile


async def open_text_to_image(
    config: GenerationConfig,
    *,
    environ: Mapping[str, str] | None = None,
    transports: TransportFactory | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> TextToImageService:
    provider = config.provider
    driver = await _driver(provider, environ, transports, clock)
    adapter = ComfyTextToImageAdapter(
        config.workflow.load(),
        driver,
        provider.binding,
        provider.completion,
        config.workflow.requires,
        clock=clock,
        sleep=sleep,
    )
    return TextToImageService(config, adapter)


async def _driver(
    provider: ProviderConfig,
    environ: Mapping[str, str] | None,
    transports: TransportFactory | None,
    clock: Callable[[], float],
) -> ComfyDriver:
    _require_secret_free(provider)
    factory = transports or default_transports(provider)
    primary = factory(provider.origin, None)
    family, version = await discover(
        provider.api_family,
        primary,
        request_timeout=provider.completion.request_timeout_seconds,
        clock=clock,
    )
    return DRIVERS[family](
        version, primary, frozenset(provider.download_origins), factory
    )


async def open_image_transfer(
    config: GenerationConfig,
    *,
    environ: Mapping[str, str] | None = None,
    transports: TransportFactory | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> ImageTransfer:
    """Configuration-selected input transfer; remote deployments are refused."""
    provider = config.provider
    driver = await _driver(provider, environ, transports, clock)
    return ImageTransfer(
        driver, provider.deployment == "local", provider.completion, clock
    )


@dataclass(frozen=True)
class TryOnService:
    """VirtualTryOnPort for applications: governed, configuration-selected."""

    config: TryOnConfig
    adapter: ComfyVirtualTryOnAdapter = field(repr=False)

    @property
    def profile(self) -> ProviderProfile:
        return self.adapter.profile

    def job(self, job_id: str) -> ProviderJobRef:
        return ProviderJobRef("comfyui", self.adapter.binding, job_id)

    def describe(self) -> dict[str, str]:
        """Safe diagnostics: no image bytes, prompts, credentials or payloads."""
        profile = self.profile
        width, height = self.adapter.workflow.geometry
        return {
            "api_family": profile.family,
            "version": profile.version or "not observable",
            "origin": self.config.provider.origin,
            "deployment": self.config.provider.deployment,
            "binding": self.adapter.binding,
            "template": self.config.workflow.template,
            "workflow_sha256": self.adapter.workflow.reference.sha256,
            "geometry": f"{width}x{height}",
        }

    async def try_on(self, request: TryOnRequest) -> GenerationResult:
        async with await prepare_local(
            self.adapter,
            self.config.digest,
            approved=self.adapter.workflow.reference,
            timeout=self.adapter.completion.max_wait_seconds,
            binding=self.adapter.binding,
            offer=TRY_ON_OFFER,
        ) as session:
            _, result = await invoke_try_on(
                session.execution,
                session.ready,
                session.context,
                session.contribution,
                session.contribution.revision,
                request,
            )
            return result

    async def reconcile(self, job: ProviderJobRef) -> ReconciliationResult:
        return await self.adapter.reconcile(job)


async def open_virtual_try_on(
    config: TryOnConfig,
    *,
    environ: Mapping[str, str] | None = None,
    transports: TransportFactory | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> TryOnService:
    """Refuse unsupported deployment before credentials or driver construction."""
    provider = config.provider
    if provider.deployment != "local":
        raise ProviderError(
            ErrorCategory.POLICY_VIOLATION, "remote_personal_images_forbidden"
        )
    driver = await _driver(provider, environ, transports, clock)
    adapter = ComfyVirtualTryOnAdapter(
        config.workflow.load(),
        driver,
        provider.binding,
        provider.completion,
        config.workflow.requires,
        clock=clock,
        sleep=sleep,
        local=provider.deployment == "local",
    )
    return TryOnService(config, adapter)


class WriteCounter:
    """Operator diagnostics: counts provider write attempts, never their content.

    Wraps a TransportFactory. Every non-GET request is counted when it is
    attempted, as an input upload or otherwise as a submission.
    """

    _UPLOAD_ROUTES = frozenset({"/upload/image"})

    def __init__(self, inner: TransportFactory) -> None:
        self._inner = inner
        self.uploads = 0
        self.submissions = 0

    def __call__(self, origin: str, token: str | None) -> Transport:
        return _CountedTransport(self._inner(origin, token), self)


class _CountedTransport:
    def __init__(self, inner: Transport, counter: WriteCounter) -> None:
        self._inner = inner
        self._counter = counter

    async def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        limit: int,
        headers: Headers = (),
    ) -> Response:
        if method != "GET":
            if path.split("?", 1)[0] in WriteCounter._UPLOAD_ROUTES:
                self._counter.uploads += 1
            else:
                self._counter.submissions += 1
        return await self._inner.request(
            method, path, body, limit=limit, headers=headers
        )


@dataclass(frozen=True, slots=True)
class PreflightReport:
    """Safe, ordered preflight lines; `ok` only if every check passed."""

    ok: bool
    lines: tuple[tuple[str, str], ...]


async def preflight_virtual_try_on(
    config: TryOnConfig,
    *,
    environ: Mapping[str, str] | None = None,
    transports: TransportFactory | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> PreflightReport:
    """Read-only live readiness check: never uploads, submits or mutates.

    All provider I/O goes through read-only budgets, so any POST is
    structurally refused. Checks stop at the first failure.
    """
    provider = config.provider
    lines: list[tuple[str, str]] = []

    def report(ok: bool) -> PreflightReport:
        return PreflightReport(ok, tuple(lines))

    if provider.deployment != "local":
        lines.append(("local-only policy", "FAIL (remote personal images forbidden)"))
        return report(False)
    lines.append(("local-only policy", "PASS"))
    try:
        _require_secret_free(provider)
    except ProviderError as error:
        lines.append(("credential scope", f"FAIL ({error.reason})"))
        return report(False)
    try:
        workflow = config.workflow.load()
    except (OSError, ValueError, TypeError) as error:
        lines.append(("approved template", f"FAIL ({str(error)[:120]})"))
        return report(False)
    width, height = workflow.geometry
    lines.append(("approved template", f"PASS {workflow.kind.value} {width}x{height}"))
    factory = transports or default_transports(provider)
    primary = factory(provider.origin, None)
    timeout = provider.completion.request_timeout_seconds
    try:
        if provider.api_family == "auto":
            family, version = await discover(
                "auto", primary, request_timeout=timeout, clock=clock
            )
        else:
            family = provider.api_family
            version = await confirm(
                family, primary, request_timeout=timeout, clock=clock
            )
    except ProviderError as error:
        lines.append(("provider reachable", f"FAIL ({error.reason})"))
        return report(False)
    lines.append(("provider reachable", "YES"))
    lines.append(("api family", f"{family} {version or ''}".strip()))
    driver = DRIVERS[family](
        version, primary, frozenset(provider.download_origins), factory
    )
    capabilities = driver.profile.capabilities
    if not capabilities.input_upload:
        lines.append(("upload capability", "FAIL"))
        return report(False)
    lines.append(("upload capability", "PASS"))
    if not capabilities.node_preflight:
        lines.append(("node preflight", "FAIL (provider cannot verify nodes/models)"))
        return report(False)
    budget = Budget(
        clock() + provider.completion.max_wait_seconds, clock, timeout, True
    )
    try:
        await driver.preflight(budget, workflow)
    except ProviderError as error:
        lines.append(("node preflight", f"FAIL ({error.reason})"))
        return report(False)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        lines.append(("node preflight", f"FAIL ({str(error)[:120]})"))
        return report(False)
    models = workflow.models
    lines.append(("node preflight", "PASS"))
    lines.append(("diffusion model", f"present ({models.diffusion_model})"))
    lines.append(("text encoder", f"present ({models.text_encoder})"))
    lines.append(("vae", f"present ({models.vae})"))
    return report(True)
