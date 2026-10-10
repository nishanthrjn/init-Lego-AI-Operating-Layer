"""Python 1A correction contracts; no interpreter acquisition or GPU execution."""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from experiments.kaggle.free_gpu_model_runtime import notebook_support as notebook
from experiments.kaggle.free_gpu_model_runtime import runtime_probe as probe


def observed() -> dict[str, Any]:
    return {
        "cuda_available": True,
        "device_count": 2,
        "driver_visible_cuda": "13.0",
        "devices": [
            {
                "name": "Tesla T4",
                "capability": [7, 5],
                "total_memory_bytes": 15636037632,
            }
            for _ in range(2)
        ],
    }


def test_observed_hardware() -> None:
    probe.require_hardware(observed())


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("cuda_available", False, "CUDA_UNAVAILABLE"),
        ("device_count", 1, "GPU_COUNT_UNSUPPORTED"),
        ("driver_visible_cuda", "12.4", "DRIVER_CUDA_UNSUPPORTED"),
        ("name", "P100", "GPU_MODEL_UNSUPPORTED"),
        ("capability", [7, 0], "GPU_CAPABILITY_UNSUPPORTED"),
        ("total_memory_bytes", 2**30, "GPU_MEMORY_UNSUPPORTED"),
    ],
)
def test_hardware_reason(field: str, value: Any, reason: str) -> None:
    data = observed()
    if field in data:
        data[field] = value
    else:
        data["devices"][0][field] = value
    with pytest.raises(probe.Stop) as error:
        probe.require_hardware(data)
    assert error.value.reason == reason


def test_interpreter_version_and_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "bin/python"
    (tmp_path / "pyvenv.cfg").write_text("include-system-site-packages = false\n")
    info = {
        "version": [3, 12, 12],
        "implementation": "cpython",
        "venv": True,
        "user_site": False,
    }

    def run(*args: Any, **kwargs: Any) -> Any:
        assert "-I" in args[0]
        return subprocess.CompletedProcess(args[0], 0, json.dumps(info), "")

    monkeypatch.setattr(subprocess, "run", run)
    assert probe.inspect_interpreter(executable, isolated=True) == "3.12.12"
    info["version"] = [3, 13, 15]
    with pytest.raises(probe.Stop) as error:
        probe.inspect_interpreter(executable, isolated=True)
    assert error.value.reason == "RUNTIME_PYTHON_VERSION_MISMATCH"
    info["version"] = [3, 12, 12]
    (tmp_path / "pyvenv.cfg").write_text("include-system-site-packages = true\n")
    with pytest.raises(probe.Stop) as error:
        probe.inspect_interpreter(executable, isolated=True)
    assert error.value.reason == "RUNTIME_ISOLATION_FAILED"


def test_missing_interpreter_has_closed_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(*args: Any, **kwargs: Any) -> Any:
        raise FileNotFoundError("PRIVATE-CANARY")

    monkeypatch.setattr(subprocess, "run", missing)
    with pytest.raises(probe.Stop) as error:
        probe.inspect_interpreter(Path("missing"))
    assert error.value.reason == "RUNTIME_PYTHON_NOT_FOUND"
    assert "CANARY" not in str(error.value)


@pytest.mark.parametrize("system", [True, False])
def test_model_venv_uses_only_frozen_interpreter(
    monkeypatch: pytest.MonkeyPatch, system: bool, tmp_path: Path
) -> None:
    monkeypatch.setattr(probe, "SCRATCH", tmp_path)
    monkeypatch.setattr(probe, "PYTHON", tmp_path / "venv/bin/python")
    monkeypatch.setattr(probe, "resolve_uv", lambda: Path("/usr/local/bin/uv"))
    interpreter = Path("/usr/bin/python3.12")
    monkeypatch.setattr(probe, "system_python", lambda: interpreter if system else None)
    monkeypatch.setattr(sys, "version_info", (3, 13, 15))
    events: list[Any] = []

    def command(args: list[str], timeout: int) -> None:
        events.append(args)
        if "venv" in args:
            probe.PYTHON.parent.mkdir(parents=True)
            probe.PYTHON.touch()

    def inspect(path: Path, *, isolated: bool = False, pristine: bool = False) -> str:
        events.append((str(path), isolated, pristine))
        return "3.12.12"

    monkeypatch.setattr(probe, "bounded_process", command)
    monkeypatch.setattr(probe, "inspect_interpreter", inspect)
    monkeypatch.setattr(probe, "save", lambda result: None)
    result = probe.fresh_result()
    probe.create_runtime(result)
    commands = [event for event in events if isinstance(event, list)]
    venv = next(args for args in commands if args[-1] == str(probe.SCRATCH / "venv"))
    assert "python3.12" in venv[venv.index("--python") + 1]
    assert venv[0] == str(Path("/usr/local/bin/uv"))
    assert "--seed" in venv and "--no-python-downloads" in venv
    assert "--system-site-packages" not in venv
    assert events[-1] == (str(probe.PYTHON), True, True)
    assert result["runtime_versions"]["python"] == "3.12.12"
    if not system:
        assert any("cpython-3.12.12-linux-x86_64-gnu" in args for args in commands)


def test_inspect_accepts_base_313_and_preserves_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(probe, "WORK", tmp_path)
    monkeypatch.setattr(probe, "RESULT", tmp_path / "result.json")
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(platform, "python_version", lambda: "3.13.15")
    monkeypatch.setattr(sys, "version_info", (3, 13, 15))
    original = Path.is_dir
    monkeypatch.setattr(
        Path,
        "is_dir",
        lambda path: (
            True if str(path).replace("\\", "/") == "/kaggle/input" else original(path)
        ),
    )
    monkeypatch.setattr(probe, "hardware", observed)
    monkeypatch.setattr(probe, "system_python", lambda: None)
    monkeypatch.setattr(sys, "argv", ["probe", "inspect", "--confirm-free-session"])
    assert probe.main() == 0
    before = probe.RESULT.read_bytes()
    assert json.loads(before)["base_versions"]["python"] == "3.13.15"
    assert probe.main() == 1
    assert probe.RESULT.read_bytes() == before
    assert "EXISTING_EVIDENCE" in capsys.readouterr().out


def test_notebook_discovery_identity_and_ambiguity(tmp_path: Path) -> None:
    digest = hashlib.sha256(
        (probe.SOURCE / "source-manifest.json").read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()
    target = tmp_path / "datasets/owner/dataset/free_gpu_model_runtime"
    shutil.copytree(probe.SOURCE, target)
    assert notebook.discover_source(tmp_path, digest) == target
    shutil.copytree(probe.SOURCE, tmp_path / "second")
    with pytest.raises(RuntimeError, match="SOURCE_NOT_UNIQUE"):
        notebook.discover_source(tmp_path, digest)


def test_notebook_failure_diagnostics_before_raise(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(
            [],
            1,
            "inspect: RESULT_INCONCLUSIVE / RUNTIME_PYTHON_NOT_FOUND\n",
            "PRIVATE/path/trace\n",
        ),
    )
    with pytest.raises(RuntimeError):
        notebook.run_phase(Path("source"), "inspect", 120)
    output = capsys.readouterr().out
    assert "stdout:" in output and "stderr:" in output and "return code: 1" in output
    assert "RUNTIME_PYTHON_NOT_FOUND" in output and "PRIVATE" not in output


def test_dependency_contract_unchanged() -> None:
    text = (probe.SOURCE / "requirements-kaggle.txt").read_text()
    for pin in ("vllm==0.9.2", "torch==2.7.0+cu128", "transformers==4.51.3"):
        assert pin in text
    assert (probe.RUNTIME_PYTHON_MAJOR, probe.RUNTIME_PYTHON_MINOR) == (3, 12)


def test_notebook_and_manifest_match_canonical_sources() -> None:
    document = json.loads((probe.SOURCE / "kaggle_runtime.ipynb").read_text())
    first = next(c for c in document["cells"] if c["cell_type"] == "code")
    source = "".join(first["source"])
    assert source.startswith((probe.SOURCE / "notebook_support.py").read_text())
    raw = (probe.SOURCE / "source-manifest.json").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() in source
    manifest = json.loads(raw)
    for name, digest in manifest["files"].items():
        assert (
            hashlib.sha256(
                (probe.SOURCE / name).read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest()
            == digest
        )


def test_incomplete_companions_are_not_selected(tmp_path: Path) -> None:
    raw = (probe.SOURCE / "source-manifest.json").read_bytes().replace(b"\r\n", b"\n")
    (tmp_path / "source-manifest.json").write_bytes(raw)
    with pytest.raises(RuntimeError, match="SOURCE_NOT_UNIQUE"):
        notebook.discover_source(tmp_path, hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize("package", ["vllm", "torch", "transformers"])
def test_runtime_packages_checked_independently(package: str) -> None:
    result = probe.fresh_result()
    result["base_versions"] = {
        "python": "3.13.15",
        "torch": "2.11.0+cu128",
        "transformers": "5.16.1",
    }
    result["runtime_versions"] = {
        "vllm": "0.9.2",
        "torch": "2.7.0+cu128",
        "transformers": "4.51.3",
    }
    probe.require_packages(result["runtime_versions"])
    result["runtime_versions"][package] = "999"
    with pytest.raises(probe.Stop) as error:
        probe.require_packages(result["runtime_versions"])
    assert error.value.reason == "RUNTIME_PACKAGE_VERSION_MISMATCH"
