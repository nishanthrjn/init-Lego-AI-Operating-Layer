"""Comfy API v2 driver behind the same engine: stronger, documented semantics."""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory
from media_support import (
    SIGNED,
    V2_JOB,
    FakeStorage,
    FakeTime,
    FakeV2,
    Transports,
    envelope,
    png,
    workflow,
    write_workflow,
)

from legoai_generative_media.comfyui import ComfyTextToImageAdapter, CompletionPolicy
from legoai_generative_media.config import parse_config
from legoai_generative_media.drivers.v2 import V2Driver
from legoai_generative_media.http import Response
from legoai_generative_media.service import open_text_to_image
from legoai_generative_media.values import (
    Cessation,
    Outcome,
    ProviderJobRef,
    ReconciliationStatus,
    TextToImageRequest,
)

CLOUD = "https://cloud.comfy.org"
STORAGE = "https://storage.googleapis.com"
SECRET = "sk-live-DO-NOT-LEAK-0123456789"
JOB = ProviderJobRef("comfyui", "comfyui-local", V2_JOB)


def engine(
    fake: FakeV2, time: FakeTime | None = None, *, storage: Any = None, **extra: Any
) -> ComfyTextToImageAdapter:
    time = time or FakeTime()
    driver = V2Driver(
        fake,
        download_origins=frozenset({STORAGE}),
        downloads=Transports({STORAGE: storage or FakeStorage(png())}),
    )
    return ComfyTextToImageAdapter(
        workflow(),
        driver,
        completion=CompletionPolicy(300, 1, 10),
        clock=time.clock,
        sleep=time.sleep,
        **extra,
    )


def generate(adapter: ComfyTextToImageAdapter) -> Any:
    return asyncio.run(adapter.generate(TextToImageRequest("red mug", 42)))


def test_submit_inspect_retrieve() -> None:
    fake = FakeV2()
    result = generate(engine(fake))
    assert result.outcome is Outcome.SUCCESS and result.effect is EffectExtent.COMPLETED
    assert result.job is not None and result.job.job_id == V2_JOB
    assert result.image is not None and result.image.seed == 42
    posts = [c for c in fake.calls if c[0] == "POST"]
    assert len(posts) == 1 and posts[0][1] == "/api/v2/jobs"
    body = json.loads(posts[0][2])
    assert set(body) == {"workflow"}  # No extra_data; credentials never in body.
    assert body["workflow"]["6"]["inputs"]["text"] == "red mug"
    key = dict(posts[0][3])["Idempotency-Key"]
    assert str(uuid.UUID(key)) == key
    # v2 documents no node catalogue: no legacy /object_info preflight.
    assert not any(c[1].startswith("/object_info") for c in fake.calls)


def test_long_job_polled_under_policy() -> None:
    fake, time = FakeV2(), FakeTime()
    fake.time, fake.ready_at = time, 640
    adapter = ComfyTextToImageAdapter(
        workflow(),
        V2Driver(fake),
        completion=CompletionPolicy(900, 1, 10),
        clock=time.clock,
        sleep=time.sleep,
    )
    result = generate(adapter)
    assert result.outcome is Outcome.SUCCESS and 640 <= time.now < 900
    assert fake.posts() == 1


def test_deadline_keeps_job_and_unknown_effect() -> None:
    fake, time = FakeV2(), FakeTime()
    fake.time, fake.ready_at = time, 640
    result = generate(engine(fake, time))
    assert result.outcome is Outcome.DEADLINE and result.effect is EffectExtent.UNKNOWN
    assert result.cessation is Cessation.UNKNOWN and result.job == JOB
    assert fake.posts() == 1
    # No cancel is issued: LegoAI cancellation stays local-wait-only.
    assert not any(c[1].endswith("/cancel") for c in fake.calls)


@pytest.mark.parametrize(
    "status,code,category,reason",
    [
        (
            401,
            "unauthorized",
            ErrorCategory.AUTHORIZATION_DENIED,
            "authentication_failed",
        ),
        (403, "forbidden", ErrorCategory.AUTHORIZATION_DENIED, "forbidden"),
        (
            402,
            "insufficient_credits",
            ErrorCategory.DEPENDENCY_FAILURE,
            "insufficient_credits",
        ),
        (422, "invalid_workflow", ErrorCategory.VALIDATION_ERROR, "invalid_workflow"),
        (422, "workflow_format_ui", ErrorCategory.VALIDATION_ERROR, "invalid_workflow"),
        (422, "missing_asset", ErrorCategory.VALIDATION_ERROR, "missing_asset"),
        (429, "queue_full", ErrorCategory.DEPENDENCY_FAILURE, "queue_full"),
        (429, "rate_limited", ErrorCategory.DEPENDENCY_FAILURE, "rate_limited"),
        (
            429,
            "deployment_not_ready",
            ErrorCategory.DEPENDENCY_FAILURE,
            "provider_unavailable",
        ),
    ],
)
def test_documented_rejections_prove_no_job(
    status: int, code: str, category: ErrorCategory, reason: str
) -> None:
    fake = FakeV2()
    fake.submit = envelope(status, code)
    result = generate(engine(fake))
    # Stronger than legacy: the provider documents that no job was created.
    assert result.outcome is Outcome.FAILED and result.effect is EffectExtent.NONE
    assert result.error is category and result.reason == reason
    assert result.job is None and fake.posts() == 1
    # Sanitized evidence: status, media type and code identifier; never messages.
    assert result.evidence == (
        f"v2 submit: status={status} type=application/json code={code}",
    )
    assert "provider text" not in " ".join(result.evidence)


@pytest.mark.parametrize(
    "response",
    [
        envelope(500, "upstream_error"),
        envelope(422, "idempotency_key_reuse"),
        Response(201, "application/json", b"{not json"),
        Response(201, "application/json", b'{"id": "not-a-uuid"}'),
    ],
)
def test_ambiguous_submission_stays_unknown(response: Response) -> None:
    fake = FakeV2()
    fake.submit = response
    result = generate(engine(fake))
    assert result.outcome is Outcome.FAILED and result.effect is EffectExtent.UNKNOWN
    assert fake.posts() == 1  # Never resubmitted, even with an idempotency key.


def test_lost_acknowledgement_is_not_retried() -> None:
    fake = FakeV2()
    fake.fail_at = "/api/v2/jobs"
    result = generate(engine(fake))
    assert result.effect is EffectExtent.UNKNOWN and fake.posts() == 1


@pytest.mark.parametrize("status", ["failed", "canceled"])
def test_provider_failure(status: str) -> None:
    fake = FakeV2()
    fake.status = status
    result = generate(engine(fake))
    assert result.outcome is Outcome.FAILED and result.effect is EffectExtent.UNKNOWN
    assert result.error is ErrorCategory.EXECUTION_FAILURE
    assert result.reason == ("canceled" if status == "canceled" else None)


def test_expired_job_is_not_success() -> None:
    fake = FakeV2()
    fake.status = "expired"
    result = asyncio.run(engine(fake).reconcile(JOB))
    assert (
        result.status is ReconciliationStatus.UNRESOLVED and result.reason == "expired"
    )
    assert fake.posts() == 0


@pytest.mark.parametrize(
    "outputs",
    [
        [],
        [{"node_id": "9", "content_type": "image/png", "id": "x"}],
        [
            {
                "node_id": "7",
                "content_type": "image/png",
                "id": "11111111-2222-4333-8444-555555555555",
            }
        ],
        [
            {
                "node_id": "9",
                "content_type": "image/jpeg",
                "id": "11111111-2222-4333-8444-555555555555",
            }
        ],
    ],
)
def test_output_validation(outputs: Any) -> None:
    fake = FakeV2()
    fake.outputs = outputs
    result = generate(engine(fake))
    assert result.outcome is Outcome.FAILED and result.effect is EffectExtent.COMPLETED
    assert result.error is ErrorCategory.VALIDATION_ERROR


def test_signed_redirect_followed_once_without_credentials() -> None:
    fake, storage = FakeV2(), FakeStorage(png())
    fake.redirect = SIGNED
    transports = Transports({STORAGE: storage})
    adapter = ComfyTextToImageAdapter(
        workflow(),
        V2Driver(fake, download_origins=frozenset({STORAGE}), downloads=transports),
        clock=FakeTime().clock,
    )
    result = generate(adapter)
    assert result.outcome is Outcome.SUCCESS
    assert transports.opened == [(STORAGE, None)]  # No bearer token to storage.
    assert storage.calls == [("GET", "/comfy-assets/x.png?X-Goog-Signature=abc")]


@pytest.mark.parametrize(
    "location",
    [
        "https://evil.example/x.png",
        "http://storage.googleapis.com/x.png",
        "https://user@storage.googleapis.com/x.png",
        "/relative/x.png",
    ],
)
def test_redirect_escape_rejected(location: str) -> None:
    fake, storage = FakeV2(), FakeStorage(png())
    fake.redirect = location
    result = generate(engine(fake, storage=storage))
    assert result.outcome is Outcome.FAILED and result.effect is EffectExtent.COMPLETED
    assert storage.calls == []


def test_reconcile_completed_pending_missing_with_zero_posts() -> None:
    fake, time = FakeV2(), FakeTime()
    fake.time, fake.ready_at = time, 640
    adapter = engine(fake, time)
    assert asyncio.run(adapter.reconcile(JOB)).status is ReconciliationStatus.PENDING
    time.now = 700
    first = asyncio.run(adapter.reconcile(JOB))
    second = asyncio.run(adapter.reconcile(JOB))
    assert (
        first.status is ReconciliationStatus.COMPLETED
        and first.effect is EffectExtent.COMPLETED
    )
    assert first.image is not None and second.image is not None
    assert first.image.sha256 == second.image.sha256
    fake.known = False
    missing = asyncio.run(adapter.reconcile(JOB))
    assert (
        missing.status is ReconciliationStatus.NOT_FOUND
        and missing.effect is EffectExtent.UNKNOWN
    )
    assert fake.posts() == 0


def test_reconcile_requires_executed_api_graph() -> None:
    fake = FakeV2()
    fake.format = "save"
    assert (
        asyncio.run(engine(fake).reconcile(JOB)).status
        is ReconciliationStatus.UNRESOLVED
    )
    fake = FakeV2()
    fake.recorded = {**fake.recorded, "10": {"class_type": "SaveImage", "inputs": {}}}
    result = asyncio.run(engine(fake).reconcile(JOB))
    assert result.status is ReconciliationStatus.UNRESOLVED
    assert result.error is ErrorCategory.VALIDATION_ERROR and fake.posts() == 0


def test_workflow_requirement_fails_closed_before_submission() -> None:
    fake = FakeV2()
    result = generate(engine(fake, requires=frozenset({"node_preflight"})))
    assert result.outcome is Outcome.FAILED and result.effect is EffectExtent.NONE
    assert result.reason == "capability_missing" and fake.calls == []


def cloud_config(tmp_path: Path) -> Any:
    path, sha = write_workflow(tmp_path)
    return parse_config(
        {
            "provider": {
                "type": "comfyui",
                "endpoint": CLOUD,
                "api_family": "v2",
                "deployment": "remote",
                "binding": "comfyui-cloud",
                "allowed_origins": [CLOUD],
                "download_origins": [STORAGE],
                "auth": {"type": "bearer", "secret_ref": "env:COMFY_API_KEY"},
            },
            "workflow": {
                "path": str(path),
                "sha256": sha,
                "checkpoint": "test.safetensors",
            },
        },
        tmp_path,
    )


@pytest.mark.parametrize("environment", [{}, {"COMFY_API_KEY": SECRET}])
def test_cloud_credentials_unsupported_before_io(
    tmp_path: Path, environment: dict[str, str]
) -> None:
    from legoai_generative_media.service import ProviderError

    fake = FakeV2()
    transports = Transports({CLOUD: fake})
    with pytest.raises(ProviderError) as caught:
        asyncio.run(
            open_text_to_image(
                cloud_config(tmp_path), environ=environment, transports=transports
            )
        )
    assert str(caught.value) == "credentialled_provider_unsupported"
    assert caught.value.category is ErrorCategory.POLICY_VIOLATION
    assert transports.opened == [] and fake.calls == []


@pytest.mark.parametrize("code", ["not_found", "job_not_found"])
def test_missing_job_maps_to_not_found_for_both_codes(code: str) -> None:
    fake = FakeV2()
    fake.known, fake.not_found_code = False, code
    result = asyncio.run(engine(fake).reconcile(JOB))
    assert result.status is ReconciliationStatus.NOT_FOUND
    assert result.effect is EffectExtent.UNKNOWN and fake.posts() == 0


def test_unrelated_404_code_is_unresolved_not_absence() -> None:
    fake = FakeV2()
    fake.known, fake.not_found_code = False, "route_not_found"
    result = asyncio.run(engine(fake).reconcile(JOB))
    assert result.status is ReconciliationStatus.UNRESOLVED


def test_reconcile_failure_carries_sanitized_evidence() -> None:
    class Denied(FakeV2):
        async def request(
            self,
            method: str,
            path: str,
            body: bytes = b"",
            *,
            limit: int,
            headers: tuple[tuple[str, str], ...] = (),
        ) -> Response:
            return envelope(403, "forbidden")

    result = asyncio.run(engine(Denied()).reconcile(JOB))
    assert result.status is ReconciliationStatus.UNRESOLVED
    assert result.reason == "forbidden"
    assert result.evidence == (
        "v2 request: status=403 type=application/json code=forbidden",
    )


@pytest.mark.parametrize("evidence", [("x" * 201,), ("a\nb",), ("",), ("a",) * 5])
def test_result_evidence_is_bounded(evidence: tuple[str, ...]) -> None:
    from legoai_generative_media.values import GenerationResult

    with pytest.raises(ValueError):
        GenerationResult(Outcome.FAILED, EffectExtent.NONE, evidence=evidence)
