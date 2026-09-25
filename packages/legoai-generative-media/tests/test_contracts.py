import hashlib
from dataclasses import FrozenInstanceError

import pytest
from media_support import png, workflow

from legoai_generative_media.http import Endpoint
from legoai_generative_media.values import (
    ApprovedWorkflowRef,
    GeneratedImage,
    ProviderJobRef,
    TextToImageRequest,
)
from legoai_generative_media.workflow import ApprovedWorkflow


def test_request_and_image() -> None:
    request = TextToImageRequest("red mug", 12)
    with pytest.raises(FrozenInstanceError):
        # Deliberately violate the frozen contract to verify runtime enforcement.
        request.prompt = "changed"  # type: ignore[misc]
    image = GeneratedImage(
        png(), ProviderJobRef("comfyui", "local", "job"), workflow().reference, 12
    )
    assert image.sha256 == hashlib.sha256(image.content).hexdigest()
    assert image.byte_length == len(image.content)
    assert "red mug" not in repr(request)
    assert "PNG" not in repr(image)


@pytest.mark.parametrize("prompt", ["", " ", "x" * 4097, "é" * 2049, "a\0b"])
def test_prompt_bound(prompt: str) -> None:
    with pytest.raises(ValueError):
        TextToImageRequest(prompt)


@pytest.mark.parametrize("seed", [-1, 2**63, True, "1", 1.5])
def test_seed(seed: object) -> None:
    with pytest.raises(ValueError):
        TextToImageRequest("x", seed)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com:8188",
        "http://192.168.1.2:8188",
        "http://localhost:8188",
        "http://user@127.0.0.1:8188",
        "http://127.0.0.1:8188/?",
        "http://127.0.0.1:8188/#",
        "https://127.0.0.1:8188",
        "http://127.0.0.1:8188/path",
    ],
)
def test_endpoint(url: str) -> None:
    with pytest.raises(ValueError):
        Endpoint(url)


def test_workflow_digest_and_shape() -> None:
    approved = workflow()
    with pytest.raises(ValueError):
        ApprovedWorkflow(
            approved.reference, approved.checkpoint, approved.content + b" "
        )
    content = approved.content.replace(b'"steps": 20', b'"steps": 21')
    ref = ApprovedWorkflowRef("test", "1", hashlib.sha256(content).hexdigest())
    with pytest.raises(ValueError):
        ApprovedWorkflow(ref, approved.checkpoint, content)
    bound = approved.bind(TextToImageRequest("a safe prompt", 17))
    assert b"a safe prompt" in bound and b"a safe prompt" not in approved.content


def test_invalid_png() -> None:
    for content in (
        b"not png",
        png()[:-1],
        png() + b"extra",
        b"x" * (16 * 1024 * 1024 + 1),
    ):
        with pytest.raises(ValueError):
            GeneratedImage(
                content,
                ProviderJobRef("comfyui", "local", "job"),
                workflow().reference,
                1,
            )
