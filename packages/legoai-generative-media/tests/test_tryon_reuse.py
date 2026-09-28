"""N-application reuse: try-on consumers see only VirtualTryOnPort + config."""

import ast
import asyncio
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from legoai.kernel.effects import EffectExtent
from media_support import (
    TRYON_MODELS,
    FakeHTTP,
    FakeTime,
    Transports,
    make_png,
    write_tryon_workflow,
)

from legoai_generative_media.config import (
    TryOnConfig,
    load_try_on_config,
    parse_try_on_config,
)
from legoai_generative_media.service import (
    TryOnService,
    WriteCounter,
    open_virtual_try_on,
)
from legoai_generative_media.values import Outcome

REPO = Path(__file__).resolve().parents[3]
CONSUMERS = [
    REPO / "examples" / "virtual-try-on-minimal" / "minimal_tryon.py",
    REPO / "examples" / "virtual-try-on" / "try_on_cli.py",
]
ALLOWED = {
    "legoai_generative_media.config",
    "legoai_generative_media.service",
    "legoai_generative_media.ports",
    "legoai_generative_media.values",
}
LOCAL = "http://127.0.0.1:8188"


def load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("consumer_" + path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("path", CONSUMERS)
def test_consumers_import_no_provider_or_workflow_code(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    imported = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("legoai")
    }
    assert imported and imported <= ALLOWED
    for forbidden in (
        "LegacyDriver",
        "V2Driver",
        "ComfyVirtualTryOnAdapter",
        "tryon_template",
        "UNETLoader",
        "TextEncodeQwenImageEditPlus",
        "qwen_image",
        "/upload/image",
        "[temp]",
        "cuda",
        "unet_name",
    ):
        assert forbidden not in source, forbidden


def config(tmp_path: Path, **provider: Any) -> TryOnConfig:
    path, sha = write_tryon_workflow(tmp_path)
    return parse_try_on_config(
        {
            "provider": {
                "type": "comfyui",
                "endpoint": LOCAL,
                "api_family": "legacy",
                **provider,
            },
            "try_on": {
                "path": str(path),
                "sha256": sha,
                "diffusion_model": TRYON_MODELS.diffusion_model,
                "text_encoder": TRYON_MODELS.text_encoder,
                "vae": TRYON_MODELS.vae,
            },
        },
        tmp_path,
    )


def service(tmp_path: Path, http: FakeHTTP) -> TryOnService:
    time = FakeTime()
    return asyncio.run(
        open_virtual_try_on(
            config(tmp_path),
            transports=Transports({LOCAL: http}),
            clock=time.clock,
            sleep=time.sleep,
        )
    )


def test_minimal_consumer_runs_through_governed_service(tmp_path: Path) -> None:
    http = FakeHTTP()
    http.image = make_png(768, 1024)
    port = service(tmp_path, http)
    minimal = load(CONSUMERS[0])
    result = asyncio.run(
        minimal.consume(port, make_png(96, 128), make_png(80, 80, color=6), 3)
    )
    assert result.outcome is Outcome.SUCCESS
    assert result.input_disclosure is EffectExtent.COMPLETED
    assert http.uploads() == 2 and len(http.prompts()) == 1
    assert port.describe()["geometry"] == "768x1024"


def test_second_consumer_reconciles_without_uploads(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    http = FakeHTTP()
    http.use_tryon_job()
    operator = load(CONSUMERS[1])
    counter = WriteCounter(Transports({LOCAL: http}))
    built = asyncio.run(open_virtual_try_on(config(tmp_path), transports=counter))
    assert asyncio.run(operator.reconcile(built, "job-1", None, counter)) == 0
    out = capsys.readouterr().out
    assert "uploads performed: 0" in out and "submission performed: NO" in out
    assert "status: COMPLETED" in out
    assert http.uploads() == 0 and http.prompts() == []


def test_remote_config_builds_but_never_transfers(tmp_path: Path) -> None:
    remote = "https://comfy.example.org"
    http = FakeHTTP()
    built = asyncio.run(
        open_virtual_try_on(
            config(
                tmp_path,
                endpoint=remote,
                deployment="remote",
                allowed_origins=[remote],
                auth={"type": "bearer", "secret_ref": "env:COMFY_API_KEY"},
            ),
            environ={"COMFY_API_KEY": "sk-test"},
            transports=Transports({remote: http}),
        )
    )
    result = asyncio.run(
        load(CONSUMERS[0]).consume(built, make_png(), make_png(color=6), None)
    )
    assert result.reason == "remote_personal_images_forbidden"
    assert http.calls == []


def test_shipped_config_parses_and_pins_models() -> None:
    parsed = load_try_on_config(
        REPO / "examples" / "virtual-try-on" / "configs" / "tryon-local.toml"
    )
    assert parsed.provider.deployment == "local"
    assert parsed.workflow.template == "qwen-image-edit-2509"
    assert parsed.workflow.models().diffusion_model.endswith(".safetensors")


@pytest.mark.parametrize(
    "change",
    [
        {"template": "flux-kontext"},
        {"diffusion_model": "../escape.safetensors"},
        {"prompt": "wear a hat"},
        {"width": 512},
    ],
)
def test_try_on_config_is_strict(tmp_path: Path, change: dict[str, Any]) -> None:
    good = config(tmp_path)
    table = {
        "path": str(good.workflow.path),
        "sha256": good.workflow.sha256,
        "diffusion_model": good.workflow.diffusion_model,
        "text_encoder": good.workflow.text_encoder,
        "vae": good.workflow.vae,
        **change,
    }
    with pytest.raises(ValueError):
        parse_try_on_config(
            {"provider": {"type": "comfyui", "endpoint": LOCAL}, "try_on": table},
            tmp_path,
        )
