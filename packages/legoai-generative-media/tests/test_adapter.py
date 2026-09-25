import asyncio
import json
from typing import Any

import pytest
from legoai.kernel.effects import EffectExtent
from media_support import FakeHTTP, workflow

from legoai_generative_media.comfyui import (
    ComfyUIConfig,
    LocalComfyUIAdapter,
    safe_location,
)
from legoai_generative_media.ports import TextToImagePort
from legoai_generative_media.values import GenerationResult, Outcome, TextToImageRequest


def execute(http: FakeHTTP) -> GenerationResult:
    return asyncio.run(
        LocalComfyUIAdapter(
            ComfyUIConfig(workflow(), poll_interval=0.001, max_polls=2), http
        ).generate(TextToImageRequest("red mug", 42))
    )


def test_success_once() -> None:
    http = FakeHTTP()
    result = execute(http)
    assert result.outcome is Outcome.SUCCESS and result.image is not None
    assert result.image.seed == 42
    posts = [c for c in http.calls if c[0] == "POST"]
    assert len(posts) == 1 and posts[0][1] == "/prompt"
    graph = json.loads(posts[0][2])["prompt"]
    assert graph["6"]["inputs"]["text"] == "red mug"
    assert graph["3"]["inputs"]["seed"] == 42


@pytest.mark.parametrize(
    "failure,effect",
    [
        ("/object_info", EffectExtent.NONE),
        ("/prompt", EffectExtent.UNKNOWN),
        ("/history", EffectExtent.UNKNOWN),
        ("/view", EffectExtent.COMPLETED),
    ],
)
def test_transport_effects(failure: str, effect: EffectExtent) -> None:
    http = FakeHTTP()
    http.fail_at = failure
    result = execute(http)
    assert result.outcome is Outcome.FAILED and result.effect is effect
    assert len([c for c in http.calls if c[0] == "POST"]) <= 1


def test_missing_dependency() -> None:
    http = FakeHTTP()
    http.missing = True
    assert execute(http).effect is EffectExtent.NONE
    assert all(c[0] == "GET" for c in http.calls)


@pytest.mark.parametrize(
    "submission",
    [
        {},
        {"prompt_id": []},
        {"prompt_id": "../../bad"},
        {"prompt_id": "job-1", "node_errors": {"x": "bad"}},
    ],
)
def test_bad_submission(submission: Any) -> None:
    http = FakeHTTP()
    http.submission = submission
    assert execute(http).effect is EffectExtent.UNKNOWN
    assert len([c for c in http.calls if c[0] == "POST"]) == 1


@pytest.mark.parametrize(
    "history",
    [[], {"other-job": {}}, {"job-1": []}, {"job-1": {"status": {"completed": False}}}],
)
def test_history(history: Any) -> None:
    http = FakeHTTP()
    http.history = history
    assert execute(http).outcome is Outcome.FAILED


def test_poll_bound() -> None:
    http = FakeHTTP()
    http.history = {}
    result = execute(http)
    assert result.outcome is Outcome.DEADLINE and result.effect is EffectExtent.UNKNOWN
    assert result.job is not None
    assert len([c for c in http.calls if c[1].startswith("/history")]) == 2


@pytest.mark.parametrize(
    "change", ["extra-node", "two-images", "traversal", "invalid-png", "oversize"]
)
def test_outputs(change: str) -> None:
    http = FakeHTTP()
    outputs = http.history["job-1"]["outputs"]
    if change == "extra-node":
        outputs["10"] = {}
    elif change == "two-images":
        outputs["9"]["images"] *= 2
    elif change == "traversal":
        outputs["9"]["images"][0]["subfolder"] = "../secret"
    elif change == "invalid-png":
        http.image = b"invalid"
    else:
        http.image = b"x" * (16 * 1024 * 1024 + 1)
    result = execute(http)
    assert result.outcome is Outcome.FAILED and result.effect is EffectExtent.COMPLETED


@pytest.mark.parametrize(
    "name,folder",
    [
        ("../x.png", ""),
        ("C:x.png", ""),
        ("x.png", "/tmp"),
        ("x.png", "a/../b"),
        ("x.png", "a\\b"),
        ("x.png", "%2e%2e"),
        ("x\0.png", ""),
    ],
)
def test_paths(name: str, folder: str) -> None:
    with pytest.raises(ValueError):
        safe_location(name, folder)


def test_same_consumer() -> None:
    async def consumer(port: TextToImagePort) -> GenerationResult:
        return await port.generate(TextToImageRequest("red mug"))

    real = LocalComfyUIAdapter(ComfyUIConfig(workflow()), FakeHTTP())
    expected = asyncio.run(consumer(real))

    class Fixed:
        async def generate(self, request: TextToImageRequest) -> GenerationResult:
            return expected

    assert asyncio.run(consumer(Fixed())) == expected


def test_missing_checkpoint_before_submission() -> None:
    from legoai_generative_media.http import Response

    class MissingCheckpoint(FakeHTTP):
        async def request(
            self, method: str, path: str, body: bytes = b"", *, limit: int
        ) -> Response:
            response = await super().request(method, path, body, limit=limit)
            if path.endswith("CheckpointLoaderSimple"):
                return Response(
                    200,
                    "application/json",
                    b'{"CheckpointLoaderSimple":{"input":{"required":{"ckpt_name":[[]]}}}}',
                )
            return response

    http = MissingCheckpoint()
    assert execute(http).effect is EffectExtent.NONE
    assert all(call[0] == "GET" for call in http.calls)


def test_runtime_failure_does_not_invent_partial_effect() -> None:
    http = FakeHTTP()
    http.history = {"job-1": {"status": {"status_str": "error", "completed": False}}}
    result = execute(http)
    assert result.outcome is Outcome.FAILED and result.effect is EffectExtent.UNKNOWN
