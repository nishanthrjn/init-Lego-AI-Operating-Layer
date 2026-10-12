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


# Closed, provider-neutral diagnostic codes; never raw provider payloads.
REASONS = frozenset(
    {
        "authentication_failed",
        "forbidden",
        "insufficient_credits",
        "invalid_workflow",
        "missing_asset",
        "rate_limited",
        "queue_full",
        "provider_unavailable",
        "upstream_error",
        "unsupported_api",
        "capability_missing",
        "output_unavailable",
        "canceled",
        "expired",
        "remote_personal_images_forbidden",
        "media_execution_refused",
        "media_execution_unsettled",
    }
)


def reason_code(value: str | None) -> None:
    if value is not None and value not in REASONS:
        raise ValueError("unknown reason")


def evidence_lines(value: tuple[str, ...]) -> None:
    """Bounded, printable, already-sanitized provider observations."""
    if type(value) is not tuple or len(value) > 4:
        raise ValueError("invalid evidence")
    for line in value:
        if type(line) is not str or not 1 <= len(line) <= 200:
            raise ValueError("invalid evidence")
        if any(not 0x20 <= ord(c) <= 0x7E for c in line):
            raise ValueError("invalid evidence")


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
    reason: str | None = None
    evidence: tuple[str, ...] = ()
    # ADR-020 §4: input transfer is its own named effect, never the job effect.
    input_disclosure: EffectExtent = EffectExtent.NONE

    def __post_init__(self) -> None:
        if type(self.outcome) is not Outcome or type(self.effect) is not EffectExtent:
            raise TypeError("invalid outcome/effect")
        if type(self.input_disclosure) is not EffectExtent:
            raise TypeError("invalid input disclosure")
        if type(self.cessation) is not Cessation:
            raise TypeError("invalid cessation")
        if self.job is not None and type(self.job) is not ProviderJobRef:
            raise TypeError("invalid job")
        if self.error is not None and type(self.error) is not ErrorCategory:
            raise TypeError("invalid error")
        reason_code(self.reason)
        evidence_lines(self.evidence)
        if self.outcome is Outcome.SUCCESS:
            if type(self.image) is not GeneratedImage or self.error is not None:
                raise ValueError("success requires image only")
            if self.effect is not EffectExtent.COMPLETED or self.job != self.image.job:
                raise ValueError("success attribution/effect mismatch")
        elif self.image is not None:
            raise ValueError("failed result cannot expose image")


class ReconciliationStatus(Enum):
    """Provider observation of one existing job; not a Core lifecycle state."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_FOUND = "not_found"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    """Knowledge at inspection time; may refine an earlier UNKNOWN effect.

    Only a provider-confirmed success establishes COMPLETED. Pending, failed,
    missing and unresolved observations never collapse the effect to NONE.
    A COMPLETED status may carry a retrieval error instead of an image.
    """

    job: ProviderJobRef
    status: ReconciliationStatus
    image: GeneratedImage | None = field(default=None, repr=False)
    error: ErrorCategory | None = None
    reason: str | None = None
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.job) is not ProviderJobRef:
            raise TypeError("exact job required")
        if type(self.status) is not ReconciliationStatus:
            raise TypeError("invalid status")
        if self.error is not None and type(self.error) is not ErrorCategory:
            raise TypeError("invalid error")
        reason_code(self.reason)
        evidence_lines(self.evidence)
        if self.image is not None:
            if type(self.image) is not GeneratedImage or self.image.job != self.job:
                raise ValueError("image attribution mismatch")
            if self.status is not ReconciliationStatus.COMPLETED:
                raise ValueError("only completed jobs expose images")
        if self.status is ReconciliationStatus.COMPLETED:
            if (self.image is None) == (self.error is None):
                raise ValueError("completed requires image or retrieval error")
        elif self.status in (
            ReconciliationStatus.FAILED,
            ReconciliationStatus.UNRESOLVED,
        ):
            if self.error is None:
                raise ValueError("failure requires category")
        elif self.error is not None:
            raise ValueError("pending/not-found carry no error")

    @property
    def effect(self) -> EffectExtent:
        if self.status is ReconciliationStatus.COMPLETED:
            return EffectExtent.COMPLETED
        return EffectExtent.UNKNOWN


class GenerationCancelled(asyncio.CancelledError):
    """Cancellation propagates while retaining external job/effect facts."""

    def __init__(self, result: GenerationResult) -> None:
        super().__init__("generation cancelled; provider cessation unknown")
        self.result = result


@dataclass(frozen=True, slots=True)
class ImageInput:
    """Privacy-sensitive PNG input, held only in stripped form (ADR-020).

    Construction validates the PNG exactly and replaces `content` with the
    metadata-free rebuild; the original bytes are not retained. No filename,
    path, URL or provider field exists by design. Bytes never enter repr.
    """

    content: bytes = field(repr=False)
    width: int = field(init=False)
    height: int = field(init=False)

    def __post_init__(self) -> None:
        from .png import strip_png

        stripped, width, height = strip_png(self.content)
        object.__setattr__(self, "content", stripped)
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)

    @property
    def byte_length(self) -> int:
        return len(self.content)

    @property
    def sha256(self) -> str:
        """Digest of the stripped PNG, for local diagnostics only."""
        return hashlib.sha256(self.content).hexdigest()


_UPLOAD_NAME = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.png"
)


@dataclass(frozen=True, slots=True)
class UploadedImageRef:
    """Provider locator for one transferred input; not storage or ownership.

    `provider_name` is a fresh random UUID name, never user-derived. `storage`
    names the provider lifecycle ("temp"); it is not a deletion guarantee.
    """

    provider_name: str
    storage: str = "temp"

    def __post_init__(self) -> None:
        if type(self.provider_name) is not str or not _UPLOAD_NAME.fullmatch(
            self.provider_name
        ):
            raise ValueError("generated provider name required")
        if self.storage != "temp":
            raise ValueError("unsupported storage kind")


@dataclass(frozen=True, slots=True)
class InputTransfer:
    """Outcome of transferring inputs: disclosure truth plus acknowledged refs."""

    disclosure: EffectExtent
    uploaded: tuple[UploadedImageRef, ...] = ()
    error: ErrorCategory | None = None
    reason: str | None = None
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.disclosure) is not EffectExtent:
            raise TypeError("invalid disclosure")
        if type(self.uploaded) is not tuple or len(self.uploaded) > 2:
            raise ValueError("at most two uploads")
        if any(type(u) is not UploadedImageRef for u in self.uploaded):
            raise TypeError("uploaded references required")
        if self.error is not None and type(self.error) is not ErrorCategory:
            raise TypeError("invalid error")
        reason_code(self.reason)
        evidence_lines(self.evidence)
        if self.error is None and (
            self.disclosure is not EffectExtent.COMPLETED or not self.uploaded
        ):
            raise ValueError("success requires every input acknowledged")
        if self.disclosure is EffectExtent.NONE and self.uploaded:
            raise ValueError("acknowledged uploads imply disclosure")

    @property
    def ok(self) -> bool:
        return self.error is None


class InputTransferCancelled(asyncio.CancelledError):
    """Cancellation propagates while retaining the known disclosure facts."""

    def __init__(self, transfer: InputTransfer) -> None:
        super().__init__("input transfer cancelled; disclosure retained")
        self.transfer = transfer


@dataclass(frozen=True, slots=True)
class TryOnRequest:
    """Virtual try-on input: two privacy-sensitive PNGs and an optional seed.

    No prompt, model, provider, hardware, geometry, mask, filename or consent
    field: the approved template and operator configuration own all of those.
    """

    person: ImageInput = field(repr=False)
    garment: ImageInput = field(repr=False)
    seed: int | None = None

    def __post_init__(self) -> None:
        if type(self.person) is not ImageInput or type(self.garment) is not ImageInput:
            raise TypeError("ImageInput required")
        if self.seed is not None and (
            type(self.seed) is not int or not 0 <= self.seed <= 2**63 - 1
        ):
            raise ValueError("seed must be integer in 0..2**63-1")
