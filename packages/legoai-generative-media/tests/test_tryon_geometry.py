"""Workflow-declared output geometry: try-on 768x1024, text-to-image 512x512."""

import asyncio

import pytest
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory
from media_support import (
    FakeHTTP,
    make_png,
    png,
    tryon_adapter,
    tryon_request,
    workflow,
)

from legoai_generative_media.comfyui import ComfyUIConfig, LocalComfyUIAdapter
from legoai_generative_media.values import (
    GeneratedImage,
    Outcome,
    ProviderJobRef,
    TextToImageRequest,
)

JOB = ProviderJobRef("comfyui", "comfyui-local", "job-1")


def test_approved_portrait_geometry_accepted() -> None:
    http = FakeHTTP()
    http.image = make_png(768, 1024)
    result = asyncio.run(tryon_adapter(http).try_on(tryon_request()))
    assert result.outcome is Outcome.SUCCESS and result.image is not None
    assert (result.image.width, result.image.height) == (768, 1024)


@pytest.mark.parametrize(
    "image",
    [
        png(),  # 512x512: text-to-image size, not the approved try-on size.
        make_png(768, 768),
        make_png(1024, 1024),
        make_png(1024, 768),  # Landscape swap.
        make_png(832, 1216),  # A provider-variable Kontext-style size.
    ],
)
def test_other_output_sizes_rejected(image: bytes) -> None:
    http = FakeHTTP()
    adapter = tryon_adapter(http)
    http.image = image  # After construction: the helper defaults to 768x1024.
    result = asyncio.run(adapter.try_on(tryon_request()))
    assert result.outcome is Outcome.FAILED
    assert result.effect is EffectExtent.COMPLETED
    assert result.error is ErrorCategory.VALIDATION_ERROR


def test_text_to_image_geometry_not_regressed() -> None:
    ok = asyncio.run(
        LocalComfyUIAdapter(ComfyUIConfig(workflow()), FakeHTTP()).generate(
            TextToImageRequest("red mug", 1)
        )
    )
    assert ok.image is not None and (ok.image.width, ok.image.height) == (512, 512)
    http = FakeHTTP()
    http.image = make_png(768, 1024)
    wrong = asyncio.run(
        LocalComfyUIAdapter(ComfyUIConfig(workflow()), http).generate(
            TextToImageRequest("red mug", 1)
        )
    )
    assert wrong.outcome is Outcome.FAILED and wrong.effect is EffectExtent.COMPLETED


def test_png_byte_ceiling_still_enforced() -> None:
    http = FakeHTTP()
    http.image = make_png(768, 1024) + b"\0" * (16 * 1024 * 1024)
    result = asyncio.run(tryon_adapter(http).try_on(tryon_request()))
    assert result.outcome is Outcome.FAILED and result.effect is EffectExtent.COMPLETED


def test_generated_image_checks_declared_dimensions() -> None:
    ref = workflow().reference
    GeneratedImage(make_png(768, 1024), JOB, ref, 0, width=768, height=1024)
    with pytest.raises(ValueError):
        GeneratedImage(make_png(768, 1024), JOB, ref, 0)  # Default 512x512.
