"""Try-on reconciliation: attributed to TRY_ON, never uploads or submits."""

import asyncio

import pytest
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory
from media_support import FakeHTTP, FakeTime, tryon_adapter, tryon_graph, workflow
from media_support import graph as text_to_image_graph

from legoai_generative_media.comfyui import ComfyUIConfig, LocalComfyUIAdapter
from legoai_generative_media.values import (
    ProviderJobRef,
    ReconciliationResult,
    ReconciliationStatus,
)

JOB = ProviderJobRef("comfyui", "comfyui-local", "job-1")


def reconcile(http: FakeHTTP) -> ReconciliationResult:
    result: ReconciliationResult = asyncio.run(tryon_adapter(http).reconcile(JOB))
    # Zero upload POSTs, zero /prompt POSTs: every request is a GET.
    assert all(c[0] == "GET" for c in http.calls)
    assert http.uploads() == 0 and http.prompts() == []
    return result


def test_completed_job_returns_existing_output() -> None:
    http = FakeHTTP()
    http.use_tryon_job(seed=11)
    result = reconcile(http)
    assert result.status is ReconciliationStatus.COMPLETED
    assert result.effect is EffectExtent.COMPLETED
    assert result.image is not None and result.image.seed == 11
    assert (result.image.width, result.image.height) == (768, 1024)


def test_pending_failed_and_missing() -> None:
    http, time = FakeHTTP(), FakeTime()
    http.use_tryon_job()
    http.time, http.ready_at = time, 100
    assert asyncio.run(tryon_adapter(http, time).reconcile(JOB)).status is (
        ReconciliationStatus.PENDING
    )
    failed = FakeHTTP()
    failed.use_tryon_job()
    failed.history["job-1"]["status"] = {"status_str": "error", "completed": False}
    assert reconcile(failed).status is ReconciliationStatus.FAILED
    missing = FakeHTTP()
    missing.history = {}
    assert reconcile(missing).status is ReconciliationStatus.NOT_FOUND


@pytest.mark.parametrize("change", ["instruction", "user filename", "text-to-image"])
def test_graph_attribution_mismatch_rejected(change: str) -> None:
    http = FakeHTTP()
    http.use_tryon_job()
    graph = http.history["job-1"]["prompt"][2]
    if change == "instruction":
        graph["11"]["inputs"]["prompt"] = "Something else."
    elif change == "user filename":
        graph["6"]["inputs"]["image"] = "alice.png [temp]"
    else:
        http.history["job-1"]["prompt"][2] = text_to_image_graph()
    result = reconcile(http)
    assert result.status is ReconciliationStatus.UNRESOLVED
    assert result.error is ErrorCategory.VALIDATION_ERROR
    assert not any(c[1].startswith("/view") for c in http.calls)


def test_repeated_reconcile_same_digest() -> None:
    http = FakeHTTP()
    http.use_tryon_job()
    first, second = reconcile(http), reconcile(http)
    assert first.image is not None and second.image is not None
    assert first.image.sha256 == second.image.sha256


def test_text_to_image_adapter_does_not_attribute_try_on_jobs() -> None:
    http = FakeHTTP()
    http.use_tryon_job()
    result = asyncio.run(
        LocalComfyUIAdapter(ComfyUIConfig(workflow()), http).reconcile(JOB)
    )
    assert result.status is ReconciliationStatus.UNRESOLVED
    assert tryon_graph()["11"]["class_type"] == "TextEncodeQwenImageEditPlus"
