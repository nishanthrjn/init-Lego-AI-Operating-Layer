"""Privacy-sensitive input transfer (ADR-020): local-only, ordered, never retried.

Reusable by any generative-media capability that needs local image inputs.
Disclosure is reported as its own named EffectExtent, separate from any job:

- NONE: no byte of any input was sent;
- PARTIAL: some, not all, inputs acknowledged, the rest provably unsent;
- COMPLETED: every input acknowledged (a rename still counts as stored);
- UNKNOWN: an upload may have delivered bytes without an acknowledgement.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory

from .comfyui import CompletionPolicy
from .drivers.base import (
    Budget,
    ComfyDriver,
    DeadlineBeforeSend,
    ProviderError,
    ProviderRenamed,
)
from .http import NotSent
from .values import (
    ImageInput,
    InputTransfer,
    InputTransferCancelled,
    UploadedImageRef,
)

MAX_INPUTS = 2


def _extent(acknowledged: int, total: int) -> EffectExtent:
    if acknowledged == 0:
        return EffectExtent.NONE
    return EffectExtent.COMPLETED if acknowledged == total else EffectExtent.PARTIAL


@dataclass(frozen=True)
class ImageTransfer:
    """Transfers up to two inputs, in the given order, each at most once."""

    driver: ComfyDriver = field(repr=False)
    # From configuration (deployment = "local"); remote transfer is refused.
    local: bool
    completion: CompletionPolicy = CompletionPolicy()
    clock: Callable[[], float] = field(default=time.monotonic, repr=False)

    async def upload(self, images: tuple[ImageInput, ...]) -> InputTransfer:
        if type(images) is not tuple or not 1 <= len(images) <= MAX_INPUTS:
            raise ValueError("one or two inputs required")
        if any(type(image) is not ImageInput for image in images):
            raise TypeError("ImageInput required")
        if not self.local:
            # ADR-020 §8: refused before any I/O; there is no enabling switch.
            return InputTransfer(
                EffectExtent.NONE,
                error=ErrorCategory.POLICY_VIOLATION,
                reason="remote_personal_images_forbidden",
            )
        if not self.driver.profile.capabilities.input_upload:
            return InputTransfer(
                EffectExtent.NONE,
                error=ErrorCategory.VERSION_MISMATCH,
                reason="capability_missing",
            )
        budget = Budget(
            self.clock() + self.completion.max_wait_seconds,
            self.clock,
            self.completion.request_timeout_seconds,
        )
        uploaded: list[UploadedImageRef] = []
        total = len(images)
        disclosure: EffectExtent
        category: ErrorCategory
        reason: str | None
        evidence: tuple[str, ...]
        for image in images:
            try:
                uploaded.append(await self.driver.upload(budget, image))
                continue
            except asyncio.CancelledError:
                raise InputTransferCancelled(
                    InputTransfer(
                        EffectExtent.UNKNOWN,
                        tuple(uploaded),
                        error=ErrorCategory.EXECUTION_FAILURE,
                        reason="canceled",
                    )
                ) from None
            except (NotSent, DeadlineBeforeSend) as error:
                # Provably nothing of this input left; stop, never retry.
                category = (
                    ErrorCategory.DEADLINE_EXCEEDED
                    if isinstance(error, DeadlineBeforeSend)
                    else ErrorCategory.DEPENDENCY_FAILURE
                )
                return InputTransfer(
                    _extent(len(uploaded), total), tuple(uploaded), error=category
                )
            except ProviderRenamed:
                # Stored under a provider-chosen name: disclosed, but unusable.
                return InputTransfer(
                    _extent(len(uploaded) + 1, total),
                    tuple(uploaded),
                    error=ErrorCategory.VALIDATION_ERROR,
                )
            except TimeoutError:
                disclosure, category, reason, evidence = (
                    EffectExtent.UNKNOWN,
                    ErrorCategory.DEADLINE_EXCEEDED,
                    None,
                    (),
                )
            except ProviderError as error:
                disclosure, category, reason, evidence = (
                    EffectExtent.UNKNOWN,
                    error.category,
                    error.reason,
                    error.evidence,
                )
            except OSError, asyncio.IncompleteReadError, asyncio.LimitOverrunError:
                disclosure, category, reason, evidence = (
                    EffectExtent.UNKNOWN,
                    ErrorCategory.DEPENDENCY_FAILURE,
                    None,
                    (),
                )
            except ValueError, KeyError, TypeError, RecursionError:
                disclosure, category, reason, evidence = (
                    EffectExtent.UNKNOWN,
                    ErrorCategory.VALIDATION_ERROR,
                    None,
                    (),
                )
            return InputTransfer(
                disclosure,
                tuple(uploaded),
                error=category,
                reason=reason,
                evidence=evidence,
            )
        return InputTransfer(EffectExtent.COMPLETED, tuple(uploaded))


# No retry, delete, record-delete or direct filesystem access.
