"""Local-only personal-image transfer (ADR-020 §7-8) and regressions."""

import asyncio
import dataclasses
from pathlib import Path
from typing import Any

import pytest
from legoai.kernel.effects import EffectExtent
from media_support import (
    FakeHTTP,
    FakeV2,
    Transports,
    make_png,
    workflow,
    write_workflow,
)

from legoai_generative_media.comfyui import ComfyUIConfig, LocalComfyUIAdapter
from legoai_generative_media.config import parse_config
from legoai_generative_media.drivers import legacy, v2
from legoai_generative_media.drivers.legacy import LegacyDriver
from legoai_generative_media.service import ProviderError, open_image_transfer
from legoai_generative_media.transfer import ImageTransfer
from legoai_generative_media.values import (
    ImageInput,
    ProviderJobRef,
    ReconciliationStatus,
    TextToImageRequest,
)

PERSON = ImageInput(make_png())
GARMENT = ImageInput(make_png(color=6))
LOCAL, PROXY = "http://127.0.0.1:8188", "http://127.0.0.1:8189"
REMOTE, CLOUD = "https://comfy.example.org", "https://cloud.comfy.org"


def config(tmp_path: Path, **provider: Any) -> Any:
    path, sha = write_workflow(tmp_path)
    return parse_config(
        {
            "provider": {"type": "comfyui", **provider},
            "workflow": {
                "path": str(path),
                "sha256": sha,
                "checkpoint": "test.safetensors",
            },
        },
        tmp_path,
    )


def remote(endpoint: str, family: str) -> dict[str, Any]:
    return {
        "endpoint": endpoint,
        "api_family": family,
        "deployment": "remote",
        "allowed_origins": [endpoint],
        "auth": {"type": "bearer", "secret_ref": "env:COMFY_API_KEY"},
    }


@pytest.mark.parametrize(
    "endpoint,family,fake",
    [(REMOTE, "legacy", "legacy"), (CLOUD, "v2", "v2")],
)
def test_remote_and_cloud_refused_before_any_io(
    tmp_path: Path, endpoint: str, family: str, fake: str
) -> None:
    server: Any = FakeHTTP() if fake == "legacy" else FakeV2()
    transports = Transports({endpoint: server})
    with pytest.raises(ProviderError, match="credentialled_provider_unsupported"):
        asyncio.run(
            open_image_transfer(
                config(tmp_path, **remote(endpoint, family)),
                environ={"COMFY_API_KEY": "sk-test"},
                transports=transports,
            )
        )
    assert transports.opened == []
    assert server.calls == []  # Zero upload requests, zero requests at all.


def test_local_driver_without_upload_capability_refused(tmp_path: Path) -> None:
    fake = FakeV2()
    transfer = asyncio.run(
        open_image_transfer(
            config(tmp_path, endpoint=PROXY, api_family="v2"),
            transports=Transports({PROXY: fake}),
        )
    )
    result = asyncio.run(transfer.upload((PERSON,)))
    assert result.reason == "capability_missing" and fake.calls == []


def test_local_legacy_config_uploads(tmp_path: Path) -> None:
    fake = FakeHTTP()
    transfer = asyncio.run(
        open_image_transfer(
            config(tmp_path, endpoint=LOCAL, api_family="legacy"),
            transports=Transports({LOCAL: fake}),
        )
    )
    assert transfer.local
    result = asyncio.run(transfer.upload((PERSON, GARMENT)))
    assert result.disclosure is EffectExtent.COMPLETED and len(fake.uploaded) == 2


def test_capabilities_are_truthful() -> None:
    assert legacy.CAPABILITIES.input_upload is True
    assert legacy.CAPABILITIES.input_byte_deletion is False
    assert v2.CAPABILITIES.input_upload is False
    assert v2.CAPABILITIES.input_byte_deletion is False


def test_remote_opt_in_is_reserved_not_accepted(tmp_path: Path) -> None:
    for table in ("provider", "workflow"):
        path, sha = write_workflow(tmp_path)
        data: dict[str, Any] = {
            "provider": {"type": "comfyui", "endpoint": LOCAL},
            "workflow": {
                "path": str(path),
                "sha256": sha,
                "checkpoint": "test.safetensors",
            },
        }
        data[table]["allow_personal_images_remote"] = True
        with pytest.raises(ValueError):
            parse_config(data, tmp_path)


def test_reconciliation_after_uploads_still_zero_post() -> None:
    fake = FakeHTTP()
    asyncio.run(ImageTransfer(LegacyDriver(fake), local=True).upload((PERSON, GARMENT)))
    posts_before = len([c for c in fake.calls if c[0] == "POST"])
    adapter = LocalComfyUIAdapter(ComfyUIConfig(workflow()), fake)
    result = asyncio.run(
        adapter.reconcile(ProviderJobRef("comfyui", "comfyui-local", "job-1"))
    )
    assert result.status is ReconciliationStatus.COMPLETED
    assert len([c for c in fake.calls if c[0] == "POST"]) == posts_before
    assert len(fake.uploaded) == 2  # No re-upload.


def test_text_to_image_reports_no_disclosure_and_request_unchanged() -> None:
    fake = FakeHTTP()
    result = asyncio.run(
        LocalComfyUIAdapter(ComfyUIConfig(workflow()), fake).generate(
            TextToImageRequest("red mug", 42)
        )
    )
    assert result.input_disclosure is EffectExtent.NONE
    assert [f.name for f in dataclasses.fields(TextToImageRequest)] == [
        "prompt",
        "seed",
    ]
    assert not any(c[1] == "/upload/image" for c in fake.calls)


def test_legacy_driver_refuses_remote_transport_structurally() -> None:
    from legoai_generative_media.http import RemoteHTTPS

    driver = LegacyDriver(RemoteHTTPS("https://comfy.example.org"))
    # Even if wired with local=True by mistake, nothing is sent.
    result = asyncio.run(ImageTransfer(driver, local=True).upload((PERSON,)))
    assert result.disclosure is EffectExtent.NONE and result.uploaded == ()
