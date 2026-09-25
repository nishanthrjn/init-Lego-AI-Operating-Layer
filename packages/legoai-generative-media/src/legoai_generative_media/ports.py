"""Application-facing image generation boundary."""

from typing import Protocol

from .values import GenerationResult, TextToImageRequest


class TextToImagePort(Protocol):
    async def generate(self, request: TextToImageRequest) -> GenerationResult:
        """One bounded attempt; cancellation may retain unknown external effects."""
        ...
