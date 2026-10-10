"""CUDA environment contracts; no GPU, torch import or external processes."""

from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from typing import Any

import pytest

from experiments.kaggle.free_gpu_model_runtime import runtime_probe as probe

LIBRARIES = "/usr/local/nvidia/lib64:/usr/local/cuda/lib64"


@pytest.mark.parametrize(
    "value",
    [
        "",
        ":",
        "relative",
        "/tmp/inject",
        "/kaggle/input/lib",
        "/kaggle/working/lib",
        "/home/user/lib",
        "/repo/lib",
        "/usr/lib",
        LIBRARIES + ":",
        LIBRARIES + ":/tmp/inject",
        "/usr/local/cuda/lib64/..",
        "/usr/local/cuda/lib64\x00",
        "x" * 513,
        ":".join(["/usr/local/cuda/lib64"] * 9),
    ],
)
def test_invalid_library_path_is_closed(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The OS rejects NUL before validation; model the environment-read boundary
    # without inserting invalid bytes into the actual process environment.
    monkeypatch.setattr(
        probe, "os", SimpleNamespace(environ={"LD_LIBRARY_PATH": value})
    )
    with pytest.raises(probe.Stop) as error:
        probe.clean_environment()
    assert error.value.reason == "CUDA_PLATFORM_ENV_INVALID"
    assert error.value.outcome == "RESULT_INCONCLUSIVE"


def test_library_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LD_LIBRARY_PATH", LIBRARIES + ":/usr/local/cuda/lib64")
    child = probe.clean_environment()
    assert child["LD_LIBRARY_PATH"] == LIBRARIES
    assert probe.fresh_result().get("LD_LIBRARY_PATH") is None
    assert LIBRARIES not in json.dumps(probe.fresh_result())


@pytest.mark.parametrize("nvidia", ["all", "0,1", "PRIVATE-CANARY"])
def test_secrets_proxies_and_device_selectors_excluded(
    nvidia: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    names = (
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
        "KAGGLE_KEY",
        "KAGGLE_USERNAME",
        "AWS_SECRET_ACCESS_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "NOTEBOOK_ONLY",
        "OPERATOR_VARIABLE",
        "CUDA_VISIBLE_DEVICES",
    )
    for name in names:
        monkeypatch.setenv(name, "PRIVATE-CANARY")
    monkeypatch.setenv("NVIDIA_VISIBLE_DEVICES", nvidia)
    child = probe.clean_environment()
    assert not set(names).intersection(child)
    assert "NVIDIA_VISIBLE_DEVICES" not in child
    assert "PRIVATE-CANARY" not in json.dumps(child)
    assert child["HF_HUB_OFFLINE"] == "1"
    assert child["VLLM_USE_V1"] == "0"


@pytest.mark.parametrize("libraries", [False, True])
@pytest.mark.parametrize("nvidia", [False, True])
def test_mocked_child_visibility_boundary(
    libraries: bool, nvidia: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Deterministic loader fixture, not evidence of real Kaggle CUDA behavior.
    if libraries:
        monkeypatch.setenv("LD_LIBRARY_PATH", LIBRARIES)
    else:
        monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    if nvidia:
        monkeypatch.setenv("NVIDIA_VISIBLE_DEVICES", "all")
    else:
        monkeypatch.delenv("NVIDIA_VISIBLE_DEVICES", raising=False)
    child = probe.clean_environment()
    visible = child.get("LD_LIBRARY_PATH") == LIBRARIES
    observed = {
        "cuda_available": visible,
        "device_count": 2 if visible else 0,
        "devices": [
            {"name": "Tesla T4", "capability": [7, 5], "total_memory_bytes": 15 * 2**30}
            for _ in range(2 if visible else 0)
        ],
        "driver_visible_cuda": "12.8",
    }
    events: list[str] = []
    monkeypatch.setattr(probe, "inspect_interpreter", lambda *a, **k: "3.12.3")
    monkeypatch.setattr(
        probe,
        "versions",
        lambda: {"torch": "2.7.0+cu128", "vllm": "0.9.2", "transformers": "4.51.3"},
    )

    def hardware() -> dict[str, Any]:
        events.append("preflight")
        return observed

    monkeypatch.setattr(probe, "hardware", hardware)
    monkeypatch.setattr(probe, "save", lambda result: None)
    monkeypatch.setattr(probe, "phase", lambda *a, **k: None)
    monkeypatch.setattr(
        probe, "serve_and_probe", lambda result: events.append("server")
    )
    if libraries:
        probe.worker(probe.fresh_result())
        assert events == ["preflight", "server"]
    else:
        with pytest.raises(probe.Stop) as error:
            probe.worker(probe.fresh_result())
        assert error.value.reason == "CUDA_CHILD_ENV_UNAVAILABLE"
        assert events == ["preflight"]


def test_no_broad_environment_inheritance() -> None:
    source = (probe.SOURCE / "runtime_probe.py").read_text(encoding="utf-8")
    for forbidden in ("os.environ.copy()", "env=os.environ", "dict(os.environ)"):
        assert forbidden not in source
    assert probe.RUNTIME_PYTHON_MINOR == 12
    assert probe.UV_VERSION == "0.9.5"
    assert probe.MODEL == "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ"
    assert probe.REVISION == "eb3172f06a6d6b3a15f08947b0668d782e4d2d2c"


def test_worker_launch_receives_validated_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LD_LIBRARY_PATH", LIBRARIES)
    monkeypatch.setenv("HF_TOKEN", "PRIVATE-CANARY")
    captured: dict[str, Any] = {}

    def launch(args: list[str], **kwargs: Any) -> Any:
        captured.update(kwargs)
        assert args[0] == str(probe.PYTHON)
        assert "_worker" in args
        return SimpleNamespace(wait=lambda timeout: 0)

    monkeypatch.setattr(subprocess, "Popen", launch)
    monkeypatch.setattr(probe, "stop_process", lambda process: None)
    probe.bounded_process([str(probe.PYTHON), "runtime_probe.py", "_worker"], 10)
    assert captured["env"]["LD_LIBRARY_PATH"] == LIBRARIES
    assert "HF_TOKEN" not in captured["env"]
