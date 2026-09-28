"""Application-facing image generation boundary."""

from typing import Protocol

from .values import (
    GenerationResult,
    ProviderJobRef,
    ReconciliationResult,
    TextToImageRequest,
    TryOnRequest,
)


class TextToImagePort(Protocol):
    async def generate(self, request: TextToImageRequest) -> GenerationResult:
        """One bounded attempt; cancellation may retain unknown external effects."""
        ...


class JobReconciliationPort(Protocol):
    async def reconcile(self, job: ProviderJobRef) -> ReconciliationResult:
        """Inspect one existing job; never submits, retries or cancels work."""
        ...


class VirtualTryOnPort(Protocol):
    async def try_on(self, request: TryOnRequest) -> GenerationResult:
        """Two local uploads then at most one submission; nothing is retried.

        `input_disclosure` reports image transfer separately from job effect.
        """
        ...

    async def reconcile(self, job: ProviderJobRef) -> ReconciliationResult:
        """Inspect an existing try-on job; never uploads or submits."""
        ...
