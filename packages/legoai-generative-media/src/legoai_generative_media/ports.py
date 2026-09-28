"""Application-facing image generation boundary."""

from typing import Protocol

from .values import (
    GenerationResult,
    ProviderJobRef,
    ReconciliationResult,
    TextToImageRequest,
)


class TextToImagePort(Protocol):
    async def generate(self, request: TextToImageRequest) -> GenerationResult:
        """One bounded attempt; cancellation may retain unknown external effects."""
        ...


class JobReconciliationPort(Protocol):
    async def reconcile(self, job: ProviderJobRef) -> ReconciliationResult:
        """Inspect one existing job; never submits, retries or cancels work."""
        ...
