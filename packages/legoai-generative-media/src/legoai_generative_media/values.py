"""Small immutable task values; prompts and bytes never appear in repr."""

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum

from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory


def identifier(value: str) -> None:
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", value):
        raise ValueError("invalid identity")


def digest(value: str) -> None:
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("invalid digest")


@dataclass(frozen=True, slots=True)
class ApprovedWorkflowRef:
    identity: str
    version: str
    sha256: str

    def __post_init__(self) -> None:
        identifier(self.identity)
        identifier(self.version)
        digest(self.sha256)


@dataclass(frozen=True, slots=True)
class TextToImageRequest:
    prompt: str = field(repr=False)
    seed: int | None = None

    def __post_init__(self) -> None:
        if type(self.prompt) is not str or not self.prompt.strip():
            raise ValueError("prompt required")
        if len(self.prompt.encode("utf-8")) > 4096:
            raise ValueError("prompt exceeds UTF-8 limit")
        if any(ord(c) < 32 or ord(c) == 127 for c in self.prompt):
            raise ValueError("prompt contains controls")
        if self.seed is not None and (
            type(self.seed) is not int or not 0 <= self.seed <= 2**63 - 1
        ):
            raise ValueError("seed must be integer in 0..2**63-1")


@dataclass(frozen=True, slots=True)
class ProviderJobRef:
    provider: str
    binding: str
    job_id: str

    def __post_init__(self) -> None:
        for value in (self.provider, self.binding, self.job_id):
            identifier(value)


@dataclass(frozen=True, slots=True)
class GeneratedImage:
    content: bytes = field(repr=False)
    job: ProviderJobRef
    workflow: ApprovedWorkflowRef
    seed: int
    content_type: str = "image/png"
    width: int = 512
    height: int = 512

    def __post_init__(self) -> None:
        from .png import validate_png

        if type(self.content) is not bytes or self.content_type != "image/png":
            raise ValueError("PNG bytes required")
        if (
            type(self.job) is not ProviderJobRef
            or type(self.workflow) is not ApprovedWorkflowRef
        ):
            raise TypeError("exact attribution required")
        if type(self.seed) is not int or not 0 <= self.seed <= 2**63 - 1:
            raise ValueError("invalid seed")
        if type(self.width) is not int or type(self.height) is not int:
            raise TypeError("integer dimensions required")
        validate_png(self.content, self.width, self.height)

    @property
    def byte_length(self) -> int:
        return len(self.content)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


class Outcome(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    DEADLINE = "deadline"
    CANCELLED = "cancelled"


class Cessation(Enum):
    NOT_REQUESTED = "not_requested"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class GenerationResult:
    outcome: Outcome
    effect: EffectExtent
    job: ProviderJobRef | None = None
    image: GeneratedImage | None = field(default=None, repr=False)
    error: ErrorCategory | None = None
    cessation: Cessation = Cessation.NOT_REQUESTED

    def __post_init__(self) -> None:
        if type(self.outcome) is not Outcome or type(self.effect) is not EffectExtent:
            raise TypeError("invalid outcome/effect")
        if type(self.cessation) is not Cessation:
            raise TypeError("invalid cessation")
        if self.job is not None and type(self.job) is not ProviderJobRef:
            raise TypeError("invalid job")
        if self.error is not None and type(self.error) is not ErrorCategory:
            raise TypeError("invalid error")
        if self.outcome is Outcome.SUCCESS:
            if type(self.image) is not GeneratedImage or self.error is not None:
                raise ValueError("success requires image only")
            if self.effect is not EffectExtent.COMPLETED or self.job != self.image.job:
                raise ValueError("success attribution/effect mismatch")
        elif self.image is not None:
            raise ValueError("failed result cannot expose image")


class GenerationCancelled(asyncio.CancelledError):
    """Cancellation propagates while retaining external job/effect facts."""

    def __init__(self, result: GenerationResult) -> None:
        super().__init__("generation cancelled; provider cessation unknown")
        self.result = result
