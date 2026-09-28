"""Input disclosure is its own named effect (ADR-020 §4-6): ordered, never retried."""

import asyncio
import re
from collections.abc import Callable

import pytest
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory
from media_support import FakeHTTP, FakeTime, make_png

from legoai_generative_media.comfyui import CompletionPolicy
from legoai_generative_media.drivers.legacy import LegacyDriver
from legoai_generative_media.transfer import ImageTransfer
from legoai_generative_media.values import (
    GenerationResult,
    ImageInput,
    InputTransfer,
    InputTransferCancelled,
    Outcome,
    UploadedImageRef,
)

PERSON = ImageInput(make_png(64, 96))
GARMENT = ImageInput(make_png(80, 64, color=6))
NAME = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.png"
)


def transfer(http: FakeHTTP, clock: Callable[[], float] | None = None) -> ImageTransfer:
    return ImageTransfer(
        LegacyDriver(http),
        local=True,
        completion=CompletionPolicy(60, 1, 5),
        clock=clock or FakeTime().clock,
    )


def run(
    http: FakeHTTP, *modes: str, images: tuple[ImageInput, ...] = (PERSON, GARMENT)
) -> InputTransfer:
    http.upload_modes = list(modes)
    return asyncio.run(transfer(http).upload(images))


def uploads(http: FakeHTTP) -> int:
    return len([c for c in http.calls if c[:2] == ("POST", "/upload/image")])


def test_both_acknowledged_completed() -> None:
    http = FakeHTTP()
    result = run(http)
    assert result.ok and result.disclosure is EffectExtent.COMPLETED
    assert len(result.uploaded) == 2 and uploads(http) == 2
    names = [ref.provider_name for ref in result.uploaded]
    assert all(NAME.fullmatch(n) for n in names) and names[0] != names[1]
    assert all(ref.storage == "temp" for ref in result.uploaded)
    # Order: person first, garment second (stripped bytes, in that order).
    assert PERSON.content in http.uploaded[0] and GARMENT.content in http.uploaded[1]


def test_single_input_completed() -> None:
    http = FakeHTTP()
    result = run(http, images=(PERSON,))
    assert result.disclosure is EffectExtent.COMPLETED and uploads(http) == 1


@pytest.mark.parametrize(
    "modes,disclosure,refs,attempts,category",
    [
        (("not_sent",), EffectExtent.NONE, 0, 1, ErrorCategory.DEPENDENCY_FAILURE),
        (("lost",), EffectExtent.UNKNOWN, 0, 1, ErrorCategory.DEPENDENCY_FAILURE),
        (("status500",), EffectExtent.UNKNOWN, 0, 1, ErrorCategory.DEPENDENCY_FAILURE),
        (("malformed",), EffectExtent.UNKNOWN, 0, 1, ErrorCategory.VALIDATION_ERROR),
        (("oversized",), EffectExtent.UNKNOWN, 0, 1, ErrorCategory.VALIDATION_ERROR),
        (("rename",), EffectExtent.PARTIAL, 0, 1, ErrorCategory.VALIDATION_ERROR),
        (
            ("ok", "not_sent"),
            EffectExtent.PARTIAL,
            1,
            2,
            ErrorCategory.DEPENDENCY_FAILURE,
        ),
        (("ok", "lost"), EffectExtent.UNKNOWN, 1, 2, ErrorCategory.DEPENDENCY_FAILURE),
        (
            ("ok", "status500"),
            EffectExtent.UNKNOWN,
            1,
            2,
            ErrorCategory.DEPENDENCY_FAILURE,
        ),
        (
            ("ok", "rename"),
            EffectExtent.COMPLETED,
            1,
            2,
            ErrorCategory.VALIDATION_ERROR,
        ),
    ],
)
def test_disclosure_cases_and_no_retry(
    modes: tuple[str, ...],
    disclosure: EffectExtent,
    refs: int,
    attempts: int,
    category: ErrorCategory,
) -> None:
    http = FakeHTTP()
    result = run(http, *modes)
    assert not result.ok
    assert result.disclosure is disclosure and result.error is category
    assert len(result.uploaded) == refs
    # Each input attempted at most once; nothing after the first failure.
    assert uploads(http) == attempts


def test_provider_error_evidence_is_sanitized() -> None:
    result = run(FakeHTTP(), "status500")
    assert result.reason == "upstream_error"
    assert result.evidence == (
        "legacy upload: status=500 type=application/json code=boom",
    )


def test_deadline_before_send_is_no_disclosure() -> None:
    ticks = iter([0.0] + [10_000.0] * 10)
    http = FakeHTTP()
    result = asyncio.run(
        transfer(http, clock=lambda: next(ticks)).upload((PERSON, GARMENT))
    )
    assert result.disclosure is EffectExtent.NONE
    assert result.error is ErrorCategory.DEADLINE_EXCEEDED and uploads(http) == 0


def test_cancellation_mid_upload_keeps_unknown_disclosure() -> None:
    async def scenario() -> None:
        http = FakeHTTP()
        http.wait_at = "/upload/image"
        task = asyncio.create_task(transfer(http).upload((PERSON, GARMENT)))
        await http.entered.wait()
        task.cancel()
        with pytest.raises(InputTransferCancelled) as caught:
            await task
        assert caught.value.transfer.disclosure is EffectExtent.UNKNOWN
        assert uploads(http) == 1

    asyncio.run(scenario())


def test_input_count_and_type_bounds() -> None:
    http = FakeHTTP()
    for images in ((), (PERSON, GARMENT, PERSON)):
        with pytest.raises(ValueError):
            asyncio.run(transfer(http).upload(images))
    with pytest.raises(TypeError):
        asyncio.run(transfer(http).upload((make_png(),)))  # type: ignore[arg-type]
    assert http.calls == []


def test_disclosure_independent_of_job_effect() -> None:
    for disclosure in (EffectExtent.UNKNOWN, EffectExtent.PARTIAL):
        result = GenerationResult(
            Outcome.FAILED,
            EffectExtent.NONE,
            error=ErrorCategory.DEPENDENCY_FAILURE,
            input_disclosure=disclosure,
        )
        assert (
            result.effect is EffectExtent.NONE and result.input_disclosure is disclosure
        )


def test_transfer_invariants() -> None:
    ref = UploadedImageRef("0b7c6f2e-9d4a-4b1e-8c3d-2f5a6b7c8d9e.png")
    with pytest.raises(ValueError):
        InputTransfer(EffectExtent.PARTIAL)  # Success needs every input acknowledged.
    with pytest.raises(ValueError):
        InputTransfer(EffectExtent.NONE, (ref,), error=ErrorCategory.CONFLICT)
    for name in ("photo.png", "../x.png", "0B7C6F2E-9D4A-4B1E-8C3D-2F5A6B7C8D9E.png"):
        with pytest.raises(ValueError):
            UploadedImageRef(name)
    with pytest.raises(ValueError):
        UploadedImageRef(ref.provider_name, storage="persistent")
