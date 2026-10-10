"""Trusted driver tool and reason preservation; all platform I/O mocked."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from experiments.kaggle.free_gpu_model_runtime import runtime_probe as probe


@pytest.mark.parametrize(
    "failure",
    [None, "relative", "location", "missing", "symlink", "resolved", "execute"],
)
def test_trusted_tool_policy(
    failure: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = Path("/opt/bin/nvidia-smi")
    monkeypatch.setattr(
        probe,
        "NVIDIA_SMI",
        expected if failure != "location" else Path("/tmp/nvidia-smi"),
    )
    monkeypatch.setattr(Path, "is_absolute", lambda path: failure != "relative")
    monkeypatch.setattr(Path, "is_file", lambda path: failure != "missing")
    monkeypatch.setattr(Path, "is_symlink", lambda path: failure == "symlink")
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda path, **kwargs: Path("/tmp/other") if failure == "resolved" else path,
    )
    monkeypatch.setattr(os, "access", lambda *args: failure != "execute")
    if failure is None:
        assert probe.trusted_nvidia_smi() == str(expected)
    else:
        with pytest.raises(probe.Stop) as error:
            probe.trusted_nvidia_smi()
        assert error.value.reason == "DRIVER_OBSERVATION_UNAVAILABLE"


def gpu_observation() -> dict[str, Any]:
    return {
        "cuda_available": True,
        "device_count": 2,
        "devices": [
            {
                "name": "Tesla T4",
                "capability": [7, 5],
                "total_memory_bytes": 15636037632,
            }
            for _ in range(2)
        ],
        "driver_visible_cuda": "13.0",
    }


@pytest.mark.parametrize(
    "failure", [None, "missing", "execution", "malformed", "banner", "unsupported"]
)
def test_absolute_driver_observations(
    failure: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    fake = SimpleNamespace(
        cuda=SimpleNamespace(
            is_available=lambda: True,
            device_count=lambda: 2,
            get_device_properties=lambda index: SimpleNamespace(
                name="Tesla T4", total_memory=15636037632
            ),
            get_device_capability=lambda index: (7, 5),
        ),
        version=SimpleNamespace(cuda="12.8"),
    )
    monkeypatch.setattr(
        probe, "importlib", SimpleNamespace(import_module=lambda name: fake)
    )

    def trusted() -> str:
        if failure == "missing":
            raise probe.Stop("RESULT_INCONCLUSIVE", "DRIVER_OBSERVATION_UNAVAILABLE")
        return "/opt/bin/nvidia-smi"

    monkeypatch.setattr(probe, "trusted_nvidia_smi", trusted)
    commands: list[list[str]] = []

    def run(args: list[str], **kwargs: Any) -> Any:
        commands.append(args)
        assert args[0] == "/opt/bin/nvidia-smi"
        assert "/opt/bin" not in kwargs["env"]["PATH"].split(":")
        assert kwargs["timeout"] == 10
        if failure == "execution":
            raise OSError("PRIVATE-CANARY")
        if len(args) > 1:
            output = "bad" if failure == "malformed" else "580.178.04\n580.178.04\n"
        else:
            output = (
                "CUDA Version: 12.4"
                if failure == "unsupported"
                else "CUDA Version: 13.0"
            )
            if failure == "banner":
                output = "PRIVATE-CANARY"
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr(subprocess, "run", run)
    observed = probe.hardware()
    assert observed["cuda_available"] is True
    if failure is None:
        assert commands == [
            [
                "/opt/bin/nvidia-smi",
                "--query-gpu=driver_version",
                "--format=csv,noheader",
            ],
            ["/opt/bin/nvidia-smi"],
        ]
        assert observed["driver_versions"] == ["580.178.04", "580.178.04"]
        probe.require_hardware(observed)
    else:
        with pytest.raises(probe.Stop) as error:
            probe.require_hardware(observed)
        assert error.value.reason == (
            "DRIVER_CUDA_UNSUPPORTED"
            if failure == "unsupported"
            else "DRIVER_OBSERVATION_UNAVAILABLE"
        )
        assert "PRIVATE" not in str(observed)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("cuda_available", False, "CUDA_CHILD_ENV_UNAVAILABLE"),
        ("device_count", 1, "GPU_COUNT_UNSUPPORTED"),
        ("name", "P100", "GPU_MODEL_UNSUPPORTED"),
        ("capability", [7, 0], "GPU_CAPABILITY_UNSUPPORTED"),
        ("total_memory_bytes", 1, "GPU_MEMORY_UNSUPPORTED"),
        ("driver_visible_cuda", "12.4", "DRIVER_CUDA_UNSUPPORTED"),
        ("driver_visible_cuda", None, "DRIVER_OBSERVATION_UNAVAILABLE"),
    ],
)
def test_worker_preserves_reasons(
    field: str, value: Any, reason: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed = gpu_observation()
    if field in observed:
        observed[field] = value
    else:
        observed["devices"][0][field] = value
    monkeypatch.setattr(probe, "inspect_interpreter", lambda *a, **k: "3.12.3")
    monkeypatch.setattr(
        probe,
        "versions",
        lambda: {"torch": "2.7.0+cu128", "vllm": "0.9.2", "transformers": "4.51.3"},
    )
    monkeypatch.setattr(probe, "hardware", lambda: observed)
    monkeypatch.setattr(probe, "save", lambda result: None)

    def forbidden(result: Any) -> None:
        pytest.fail("server must not start after a rejected hardware gate")

    monkeypatch.setattr(probe, "serve_and_probe", forbidden)
    with pytest.raises(probe.Stop) as error:
        probe.worker(probe.fresh_result())
    assert error.value.reason == reason


def test_path_and_cuda_environment_remain_narrow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    monkeypatch.setenv("PATH", "/opt/bin:/tmp")
    environment = probe.clean_environment()
    assert (
        environment["PATH"]
        == "/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin"
    )
    assert not any(name.startswith("NVIDIA_") for name in environment)
    for name in ("CUDA_HOME", "CUDA_VERSION", "LIBRARY_PATH"):
        assert name not in environment
