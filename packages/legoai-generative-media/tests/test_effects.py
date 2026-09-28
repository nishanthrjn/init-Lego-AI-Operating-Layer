import asyncio

import pytest
from legoai.kernel.effects import EffectExtent
from media_support import FakeHTTP, workflow

from legoai_generative_media.comfyui import (
    ComfyUIConfig,
    CompletionPolicy,
    LocalComfyUIAdapter,
)
from legoai_generative_media.values import (
    Cessation,
    GenerationCancelled,
    Outcome,
    TextToImageRequest,
)


@pytest.mark.parametrize("stage", ["/object_info", "/prompt", "/history", "/view"])
def test_cancellation(stage: str) -> None:
    async def run() -> None:
        http = FakeHTTP()
        http.wait_at = stage
        adapter = LocalComfyUIAdapter(ComfyUIConfig(workflow()), http)
        task = asyncio.create_task(adapter.generate(TextToImageRequest("x")))
        await http.entered.wait()
        task.cancel()
        with pytest.raises(GenerationCancelled) as caught:
            await task
        result = caught.value.result
        assert result.cessation is Cessation.UNKNOWN
        expected = (
            EffectExtent.NONE
            if stage == "/object_info"
            else EffectExtent.COMPLETED
            if stage == "/view"
            else EffectExtent.UNKNOWN
        )
        assert result.effect is expected
        if stage in ("/history", "/view"):
            assert result.job is not None and result.job.job_id == "job-1"
        assert all("interrupt" not in c[1] and "queue" not in c[1] for c in http.calls)
        assert len([c for c in http.calls if c[0] == "POST"]) <= 1

    asyncio.run(run())


def test_total_deadline() -> None:
    async def run() -> None:
        http = FakeHTTP()
        http.wait_at = "/history"
        # Request bound equals the total wait, so the total deadline expires first.
        policy = CompletionPolicy(0.5, 0.05, 0.5)
        result = await LocalComfyUIAdapter(
            ComfyUIConfig(workflow(), completion=policy), http
        ).generate(TextToImageRequest("x"))
        assert result.outcome is Outcome.DEADLINE
        assert result.job is not None and result.effect is EffectExtent.UNKNOWN
        assert result.cessation is Cessation.UNKNOWN

    asyncio.run(run())
