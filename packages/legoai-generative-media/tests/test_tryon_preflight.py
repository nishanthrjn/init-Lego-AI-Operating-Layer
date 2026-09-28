"""Preflight before personal-image disclosure (ADR-020): fail with nothing sent."""

import asyncio

import pytest
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory
from media_support import FakeHTTP, FakeV2, tryon_adapter, tryon_request

from legoai_generative_media.drivers.v2 import V2Driver
from legoai_generative_media.values import GenerationResult, Outcome

NODES = {
    "UNETLoader",
    "CLIPLoader",
    "VAELoader",
    "ModelSamplingAuraFlow",
    "CFGNorm",
    "LoadImage",
    "ImageScale",
    "SaveImage",
    "VAEEncode",
    "TextEncodeQwenImageEditPlus",
    "KSampler",
    "VAEDecode",
}


def run(http: FakeHTTP, **options: object) -> GenerationResult:
    result: GenerationResult = asyncio.run(
        tryon_adapter(http, **options).try_on(tryon_request())  # type: ignore[arg-type]
    )
    return result


def assert_nothing_disclosed(http: FakeHTTP, result: GenerationResult) -> None:
    assert result.outcome is Outcome.FAILED
    assert result.effect is EffectExtent.NONE
    assert result.input_disclosure is EffectExtent.NONE
    assert http.uploads() == 0 and http.prompts() == []


@pytest.mark.parametrize("node", sorted(NODES))
def test_missing_node_fails_before_upload(node: str) -> None:
    http = FakeHTTP()
    http.missing_nodes = {node}
    assert_nothing_disclosed(http, run(http))


@pytest.mark.parametrize("field", ["unet_name", "clip_name", "vae_name"])
def test_missing_model_file_fails_before_upload(field: str) -> None:
    http = FakeHTTP()
    http.models[field] = ("some_other_file.safetensors",)
    result = run(http)
    assert_nothing_disclosed(http, result)


def test_remote_deployment_fails_before_any_io() -> None:
    http = FakeHTTP()
    result = run(http, local=False)
    assert_nothing_disclosed(http, result)
    assert result.error is ErrorCategory.POLICY_VIOLATION
    assert result.reason == "remote_personal_images_forbidden"
    assert http.calls == []  # Not even preflight.


def test_provider_without_upload_capability_fails_before_any_io() -> None:
    fake = FakeV2()
    result: GenerationResult = asyncio.run(
        tryon_adapter(FakeHTTP(), driver=V2Driver(fake)).try_on(tryon_request())
    )
    assert result.effect is EffectExtent.NONE
    assert result.input_disclosure is EffectExtent.NONE
    assert result.reason == "capability_missing" and fake.calls == []


def test_successful_preflight_precedes_uploads() -> None:
    http = FakeHTTP()
    result = run(http)
    assert result.outcome is Outcome.SUCCESS
    paths = [c[1] for c in http.calls]
    checked = {p.rsplit("/", 1)[-1] for p in paths if p.startswith("/object_info/")}
    assert checked == NODES
    last_preflight = max(
        i for i, p in enumerate(paths) if p.startswith("/object_info/")
    )
    first_upload = paths.index("/upload/image")
    assert last_preflight < first_upload
