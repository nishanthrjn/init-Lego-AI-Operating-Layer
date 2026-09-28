"""TryOnRequest / VirtualTryOnPort contract: provider- and model-neutral."""

import asyncio
import dataclasses

import pytest
from legoai.kernel.effects import EffectExtent
from media_support import FakeHTTP, make_png, tryon_adapter, tryon_request

from legoai_generative_media.ports import TextToImagePort, VirtualTryOnPort
from legoai_generative_media.values import (
    GenerationResult,
    ImageInput,
    Outcome,
    ProviderJobRef,
    ReconciliationResult,
    ReconciliationStatus,
    TextToImageRequest,
    TryOnRequest,
)


def test_request_fields_are_exactly_person_garment_seed() -> None:
    assert [f.name for f in dataclasses.fields(TryOnRequest)] == [
        "person",
        "garment",
        "seed",
    ]


def test_seed_default_and_bounds() -> None:
    person, garment = ImageInput(make_png()), ImageInput(make_png(color=6))
    assert TryOnRequest(person, garment).seed is None
    assert TryOnRequest(person, garment, 2**63 - 1).seed == 2**63 - 1
    for seed in (-1, 2**63, True, "1", 1.5):
        with pytest.raises(ValueError):
            TryOnRequest(person, garment, seed)  # type: ignore[arg-type]


def test_inputs_must_be_validated_image_inputs() -> None:
    for person in (make_png(), bytearray(make_png()), "person.png"):
        with pytest.raises(TypeError):
            TryOnRequest(person, ImageInput(make_png()))  # type: ignore[arg-type]


def test_repr_never_exposes_images() -> None:
    text = repr(tryon_request())
    assert "PNG" not in text and "IDAT" not in text and "ImageInput" not in text


def test_text_to_image_contract_unchanged() -> None:
    assert [f.name for f in dataclasses.fields(TextToImageRequest)] == [
        "prompt",
        "seed",
    ]
    assert [n for n in vars(TextToImagePort) if not n.startswith("_")] == ["generate"]


def test_port_is_substitutable() -> None:
    async def consumer(
        port: VirtualTryOnPort,
    ) -> tuple[GenerationResult, ReconciliationResult]:
        request = tryon_request()
        return await port.try_on(request), await port.reconcile(
            ProviderJobRef("comfyui", "comfyui-local", "job-1")
        )

    class Fake:
        async def try_on(self, request: TryOnRequest) -> GenerationResult:
            return GenerationResult(Outcome.FAILED, EffectExtent.NONE)

        async def reconcile(self, job: ProviderJobRef) -> ReconciliationResult:
            return ReconciliationResult(job, ReconciliationStatus.NOT_FOUND)

    fake_result, _ = asyncio.run(consumer(Fake()))
    assert fake_result.outcome is Outcome.FAILED
    real_result, reconciled = asyncio.run(consumer(tryon_adapter(FakeHTTP())))
    assert real_result.outcome is Outcome.SUCCESS
    assert isinstance(reconciled, ReconciliationResult)


def test_adapter_rejects_foreign_requests_and_workflows() -> None:
    from media_support import workflow

    from legoai_generative_media.drivers.legacy import LegacyDriver
    from legoai_generative_media.virtual_try_on import ComfyVirtualTryOnAdapter

    adapter = tryon_adapter(FakeHTTP())
    with pytest.raises(TypeError):
        asyncio.run(adapter.try_on(TextToImageRequest("x")))
    with pytest.raises(TypeError):
        ComfyVirtualTryOnAdapter(workflow(), LegacyDriver(FakeHTTP()))  # type: ignore[arg-type]
