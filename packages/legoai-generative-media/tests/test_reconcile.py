"""Existing-job reconciliation: read-only, attributable, never resubmits."""

import asyncio
from typing import Any

import pytest
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory
from media_support import FakeHTTP, FakeTime, graph, workflow

from legoai_generative_media.comfyui import (
    ComfyUIConfig,
    CompletionPolicy,
    LocalComfyUIAdapter,
    ReadOnlyTransport,
)
from legoai_generative_media.http import Response
from legoai_generative_media.ports import JobReconciliationPort
from legoai_generative_media.values import (
    Cessation,
    Outcome,
    ProviderJobRef,
    ReconciliationResult,
    ReconciliationStatus,
    TextToImageRequest,
)

JOB = ProviderJobRef("comfyui", "comfyui-local", "job-1")


def make(http: FakeHTTP, time: FakeTime | None = None) -> LocalComfyUIAdapter:
    time = time or FakeTime()
    return LocalComfyUIAdapter(
        ComfyUIConfig(workflow(), completion=CompletionPolicy(300, 1, 10)),
        http,
        clock=time.clock,
        sleep=time.sleep,
    )


def reconcile(http: FakeHTTP, job: ProviderJobRef = JOB) -> ReconciliationResult:
    result = asyncio.run(make(http).reconcile(job))
    # The hard invariant, asserted for every scenario that uses this helper.
    assert http.posts() == 0
    assert all(c[0] == "GET" for c in http.calls)
    assert all("interrupt" not in c[1] for c in http.calls)
    return result


def test_completed_job_retrieves_existing_image() -> None:
    http = FakeHTTP()
    result = reconcile(http)
    assert result.status is ReconciliationStatus.COMPLETED
    assert result.effect is EffectExtent.COMPLETED and result.error is None
    assert result.image is not None and result.image.job == JOB
    assert result.image.seed == 42  # Recovered from provider-recorded graph.
    assert result.image.workflow == workflow().reference
    assert [c[1].split("?")[0] for c in http.calls] == ["/history/job-1", "/view"]


def test_pending_job() -> None:
    http, time = FakeHTTP(), FakeTime()
    http.time, http.ready_at = time, 640
    result = reconcile(http)
    assert result.status is ReconciliationStatus.PENDING
    assert result.effect is EffectExtent.UNKNOWN  # Never NONE, never failure.
    assert result.image is None and result.error is None


def test_pending_in_waiting_queue() -> None:
    http = FakeHTTP()
    http.history = {}
    http.queue = {
        "queue_running": [],
        "queue_pending": [[2, "job-1", graph(), {}, ["9"]]],
    }
    assert reconcile(http).status is ReconciliationStatus.PENDING


def test_failed_job() -> None:
    http = FakeHTTP()
    http.history["job-1"]["status"] = {"status_str": "error", "completed": False}
    result = reconcile(http)
    assert result.status is ReconciliationStatus.FAILED
    assert result.error is ErrorCategory.EXECUTION_FAILURE
    assert result.effect is EffectExtent.UNKNOWN and result.image is None
    assert not any(c[1].startswith("/view") for c in http.calls)


def test_missing_history_is_not_found_not_none() -> None:
    http = FakeHTTP()
    http.history = {}
    result = reconcile(http)
    assert result.status is ReconciliationStatus.NOT_FOUND
    assert result.effect is EffectExtent.UNKNOWN  # Absence never proves NONE.
    paths = [c[1] for c in http.calls]
    assert paths == ["/history/job-1", "/queue", "/history/job-1"]


def test_job_finishing_between_checks_is_found_on_recheck() -> None:
    class Racing(FakeHTTP):
        async def request(
            self,
            method: str,
            path: str,
            body: bytes = b"",
            *,
            limit: int,
            headers: tuple[tuple[str, str], ...] = (),
        ) -> Response:
            first = not any(c[1].startswith("/history") for c in self.calls)
            response = await super().request(method, path, body, limit=limit)
            if path.startswith("/history/") and first:
                return Response(200, "application/json", b"{}")
            return response

    result = reconcile(Racing())
    assert result.status is ReconciliationStatus.COMPLETED


def test_repeated_reconciliation_is_stable() -> None:
    http = FakeHTTP()
    adapter = make(http)
    first = asyncio.run(adapter.reconcile(JOB))
    second = asyncio.run(adapter.reconcile(JOB))
    assert first.image is not None and second.image is not None
    assert first.image.sha256 == second.image.sha256
    assert http.posts() == 0


def test_retrieval_failure_keeps_completion_truthful() -> None:
    http = FakeHTTP()
    http.fail_at = "/view"
    result = reconcile(http)
    assert result.status is ReconciliationStatus.COMPLETED
    assert result.effect is EffectExtent.COMPLETED
    assert result.image is None and result.error is ErrorCategory.DEPENDENCY_FAILURE


@pytest.mark.parametrize(
    "change", ["invalid-png", "two-images", "traversal", "extra-node"]
)
def test_invalid_existing_output_is_validation_failure(change: str) -> None:
    http = FakeHTTP()
    outputs = http.history["job-1"]["outputs"]
    if change == "invalid-png":
        http.image = b"invalid"
    elif change == "two-images":
        outputs["9"]["images"] *= 2
    elif change == "traversal":
        outputs["9"]["images"][0]["subfolder"] = "../secret"
    else:
        outputs["10"] = {}
    result = reconcile(http)
    assert result.status is ReconciliationStatus.COMPLETED
    assert result.image is None and result.error is ErrorCategory.VALIDATION_ERROR


def unattributed(case: str) -> Any:
    altered = graph()
    if case == "steps":
        altered["3"]["inputs"]["steps"] = 50
    elif case == "checkpoint":
        altered["4"]["inputs"]["ckpt_name"] = "other.safetensors"
    elif case == "extra-node":
        altered["10"] = {"class_type": "SaveImage", "inputs": {}}
    elif case == "bool-seed":
        altered["3"]["inputs"]["seed"] = True
    elif case == "control-prompt":
        altered["6"]["inputs"]["text"] = "a\u0000b"
    return altered


@pytest.mark.parametrize(
    "case", ["steps", "checkpoint", "extra-node", "bool-seed", "control-prompt"]
)
def test_unattributable_history_is_unresolved(case: str) -> None:
    http = FakeHTTP()
    http.history["job-1"]["prompt"][2] = unattributed(case)
    result = reconcile(http)
    assert result.status is ReconciliationStatus.UNRESOLVED
    assert result.error is ErrorCategory.VALIDATION_ERROR
    assert result.effect is EffectExtent.UNKNOWN
    assert not any(c[1].startswith("/view") for c in http.calls)


@pytest.mark.parametrize(
    "prompt", [None, [], [1, "other-job", graph()], [1, "job-1"], "job-1"]
)
def test_history_without_job_attribution_is_unresolved(prompt: Any) -> None:
    http = FakeHTTP()
    if prompt is None:
        del http.history["job-1"]["prompt"]
    else:
        http.history["job-1"]["prompt"] = prompt
    result = reconcile(http)
    assert result.status is ReconciliationStatus.UNRESOLVED
    assert not any(c[1].startswith("/view") for c in http.calls)


def test_unattributable_queue_entry_is_unresolved() -> None:
    http = FakeHTTP()
    http.history = {}
    http.queue = {
        "queue_running": [[1, "job-1", unattributed("steps"), {}, ["9"]]],
        "queue_pending": [],
    }
    assert reconcile(http).status is ReconciliationStatus.UNRESOLVED


@pytest.mark.parametrize(
    "history", [[], {"other-job": {}}, {"job-1": []}, {"job-1": {"status": None}}]
)
def test_malformed_history_is_unresolved(history: Any) -> None:
    http = FakeHTTP()
    if history == {"job-1": {"status": None}}:
        http.history["job-1"]["status"] = None
    else:
        http.history = history
    result = reconcile(http)
    assert result.status is ReconciliationStatus.UNRESOLVED
    assert result.effect is EffectExtent.UNKNOWN


@pytest.mark.parametrize("stage", ["/history", "/queue"])
def test_unreachable_provider_is_unresolved(stage: str) -> None:
    http = FakeHTTP()
    http.history = {}
    http.fail_at = stage
    result = reconcile(http)
    assert result.status is ReconciliationStatus.UNRESOLVED
    assert result.error is ErrorCategory.DEPENDENCY_FAILURE


def test_foreign_job_reference_rejected_without_io() -> None:
    for job in (
        ProviderJobRef("other", "comfyui-local", "job-1"),
        ProviderJobRef("comfyui", "other-binding", "job-1"),
    ):
        http = FakeHTTP()
        with pytest.raises(ValueError):
            asyncio.run(make(http).reconcile(job))
        assert http.calls == []


def test_read_only_transport_refuses_submission() -> None:
    http = FakeHTTP()
    guard = ReadOnlyTransport(http)
    with pytest.raises(RuntimeError):
        asyncio.run(guard.request("POST", "/prompt", b"{}", limit=1024))
    with pytest.raises(RuntimeError):
        asyncio.run(guard.request("GET", "/history/x", b"x", limit=1024))
    assert http.calls == []


def test_deadline_unknown_later_refined_to_completed() -> None:
    """UNKNOWN at the deadline and COMPLETED later are both true for their time."""
    http, time = FakeHTTP(), FakeTime()
    http.time, http.ready_at = time, 640
    adapter = make(http, time)
    first = asyncio.run(adapter.generate(TextToImageRequest("red mug", 42)))
    assert first.outcome is Outcome.DEADLINE
    assert first.effect is EffectExtent.UNKNOWN
    assert first.cessation is Cessation.UNKNOWN
    assert first.job == JOB
    assert http.posts() == 1

    early = asyncio.run(adapter.reconcile(first.job))
    assert early.status is ReconciliationStatus.PENDING

    time.now = 700  # The provider kept running after LegoAI stopped waiting.
    later = asyncio.run(adapter.reconcile(first.job))
    assert later.status is ReconciliationStatus.COMPLETED
    assert later.effect is EffectExtent.COMPLETED
    assert later.image is not None and later.image.job == first.job
    assert http.posts() == 1  # Still only the original submission.
    assert first.effect is EffectExtent.UNKNOWN  # Earlier receipt is unchanged.


def test_adapter_satisfies_reconciliation_port() -> None:
    async def consumer(port: JobReconciliationPort) -> ReconciliationResult:
        return await port.reconcile(JOB)

    http = FakeHTTP()
    assert asyncio.run(consumer(make(http))).status is ReconciliationStatus.COMPLETED
    assert http.posts() == 0


@pytest.mark.parametrize(
    "status,error",
    [
        (ReconciliationStatus.COMPLETED, None),
        (ReconciliationStatus.PENDING, ErrorCategory.DEPENDENCY_FAILURE),
        (ReconciliationStatus.NOT_FOUND, ErrorCategory.DEPENDENCY_FAILURE),
        (ReconciliationStatus.FAILED, None),
        (ReconciliationStatus.UNRESOLVED, None),
    ],
)
def test_result_invariants(
    status: ReconciliationStatus, error: ErrorCategory | None
) -> None:
    with pytest.raises(ValueError):
        ReconciliationResult(JOB, status, error=error)


def test_non_completed_result_cannot_expose_image() -> None:
    image = reconcile(FakeHTTP()).image
    assert image is not None
    for status in (ReconciliationStatus.PENDING, ReconciliationStatus.NOT_FOUND):
        with pytest.raises(ValueError):
            ReconciliationResult(JOB, status, image=image)
    with pytest.raises(ValueError):
        ReconciliationResult(
            ProviderJobRef("comfyui", "comfyui-local", "job-2"),
            ReconciliationStatus.COMPLETED,
            image=image,
        )
