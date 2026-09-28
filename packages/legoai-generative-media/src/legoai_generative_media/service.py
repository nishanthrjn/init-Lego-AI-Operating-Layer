"""Configuration-driven composition: applications receive ports, never drivers.

`open_text_to_image` resolves the secret reference, discovers or trusts the
configured API family, selects an admitted driver from the closed registry
and returns a governed TextToImagePort + JobReconciliationPort.
"""

import asyncio
import os
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

from .comfyui import ComfyTextToImageAdapter
from .composition import invoke
from .config import GenerationConfig, ProviderConfig, resolve_secret
from .discovery import DRIVERS, confirm, discover
from .drivers.base import ProviderError, ProviderProfile, TransportFactory
from .http import Endpoint, LocalHTTP, RemoteHTTPS
from .local_host import prepare_local
from .values import (
    GenerationResult,
    ProviderJobRef,
    ReconciliationResult,
    TextToImageRequest,
)

__all__ = [
    "ProviderError",
    "ProviderProfile",
    "TextToImageService",
    "open_text_to_image",
    "probe_provider",
]


def default_transports(provider: ProviderConfig) -> TransportFactory:
    timeout = provider.completion.request_timeout_seconds

    def make(origin: str, token: str | None) -> LocalHTTP | RemoteHTTPS:
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
        session = await prepare_local(
            self.adapter,
            self.config.digest,
            approved=self.adapter.workflow.reference,
            timeout=policy.max_wait_seconds,
            binding=self.adapter.binding,
        )
        _, result = await invoke(
            session.coordinator,
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
    token = resolve_secret(
        provider.secret_ref, os.environ if environ is None else environ
    )
    factory = transports or default_transports(provider)
    primary = factory(provider.origin, token)
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
    token = resolve_secret(
        provider.secret_ref, os.environ if environ is None else environ
    )
    factory = transports or default_transports(provider)
    primary = factory(provider.origin, token)
    family, version = await discover(
        provider.api_family,
        primary,
        request_timeout=provider.completion.request_timeout_seconds,
        clock=clock,
    )
    driver = DRIVERS[family](
        version, primary, frozenset(provider.download_origins), factory
    )
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
