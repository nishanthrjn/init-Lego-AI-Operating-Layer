"""N-application reuse: consumers depend on ports + configuration only."""

import ast
import asyncio
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from legoai.kernel.effects import EffectExtent
from media_support import V2_JOB, FakeHTTP, FakeTime, FakeV2, Transports, write_workflow

from legoai_generative_media.config import GenerationConfig, parse_config
from legoai_generative_media.service import TextToImageService, open_text_to_image
from legoai_generative_media.values import Outcome

REPO = Path(__file__).resolve().parents[3]
CONSUMERS = [
    REPO / "examples" / "generative-media-minimal" / "app.py",
    REPO / "examples" / "comfyui-text-to-image" / "generate.py",
    REPO / "examples" / "comfyui-text-to-image" / "probe_provider.py",
]
ALLOWED = {
    "legoai_generative_media.config",
    "legoai_generative_media.service",
    "legoai_generative_media.ports",
    "legoai_generative_media.values",
    "legoai_generative_media.workflow",
}
LOCAL, PROXY = "http://127.0.0.1:8188", "http://127.0.0.1:8189"


def load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("consumer_" + path.parent.name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("path", CONSUMERS)
def test_consumers_import_no_provider_specific_code(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("legoai")
    }
    assert imported and imported <= ALLOWED
    source = path.read_text(encoding="utf-8")
    for forbidden in (
        "LocalComfyUIAdapter",
        "ComfyTextToImageAdapter",
        "LegacyDriver",
        "V2Driver",
        "cloud.comfy.org",
        "api_family ==",
        "deployment ==",
        "cuda",
    ):
        assert forbidden not in source


def config(tmp_path: Path, family: str, endpoint: str) -> GenerationConfig:
    path, sha = write_workflow(tmp_path)
    return parse_config(
        {
            "provider": {"type": "comfyui", "endpoint": endpoint, "api_family": family},
            "workflow": {
                "path": str(path),
                "sha256": sha,
                "checkpoint": "test.safetensors",
            },
        },
        tmp_path,
    )


def service(tmp_path: Path, family: str) -> tuple[TextToImageService, Any]:
    fake: Any = FakeHTTP() if family == "legacy" else FakeV2()
    endpoint = LOCAL if family == "legacy" else PROXY
    time = FakeTime()
    built = asyncio.run(
        open_text_to_image(
            config(tmp_path, family, endpoint),
            transports=Transports({endpoint: fake}),
            clock=time.clock,
            sleep=time.sleep,
        )
    )
    return built, fake


@pytest.mark.parametrize("family", ["legacy", "v2"])
def test_same_consumer_code_any_provider(tmp_path: Path, family: str) -> None:
    minimal = load(CONSUMERS[0])
    port, fake = service(tmp_path, family)
    result = asyncio.run(minimal.consume(port, "red mug", 42))
    assert result.outcome is Outcome.SUCCESS and result.effect is EffectExtent.COMPLETED
    assert result.image is not None and result.image.seed == 42
    assert fake.posts() == 1
    assert port.profile.family == family


@pytest.mark.parametrize("family", ["legacy", "v2"])
def test_second_consumer_reconciles_on_any_provider(
    tmp_path: Path, family: str, capsys: pytest.CaptureFixture[str]
) -> None:
    operator = load(CONSUMERS[1])
    port, fake = service(tmp_path, family)
    job_id = "job-1" if family == "legacy" else V2_JOB
    assert asyncio.run(operator.reconcile(port, job_id, None)) == 0
    output = capsys.readouterr().out
    assert "submission performed: NO" in output and "status: COMPLETED" in output
    assert fake.posts() == 0


def test_legacy_profile_through_config_matches_validated_flow(tmp_path: Path) -> None:
    port, fake = service(tmp_path, "legacy")
    result = asyncio.run(load(CONSUMERS[0]).consume(port, "red mug", 42))
    assert result.outcome is Outcome.SUCCESS
    paths = [c[1].split("?")[0].rsplit("/", 1)[0] for c in fake.calls]
    # Same shape as the qualified local run: preflight, one POST, poll, view.
    assert paths.count("/object_info") == 6
    assert [c[1] for c in fake.calls if c[0] == "POST"] == ["/prompt"]
    assert fake.calls[-1][1].startswith("/view?")
