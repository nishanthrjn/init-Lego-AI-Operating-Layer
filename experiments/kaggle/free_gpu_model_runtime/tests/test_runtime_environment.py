"""1B environment creation contracts; all process execution is mocked."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from experiments.kaggle.free_gpu_model_runtime import runtime_probe as probe


@pytest.mark.parametrize("output", ["uv 0.9.5\n", "uv 0.9.5 (build)\n", "uv 0.9.6\n"])
def test_uv_exact_version_policy(output: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess([], 0, output, ""),
    )
    if output.startswith("uv 0.9.5"):
        probe.verify_uv(Path("uv"))
    else:
        with pytest.raises(probe.Stop) as error:
            probe.verify_uv(Path("uv"))
        assert error.value.reason == "UV_VERSION_MISMATCH"


@pytest.mark.parametrize("approved", [True, False])
def test_existing_uv_preferred_or_pinned_tooling(
    approved: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    system = tmp_path / "system-uv"
    system.touch()
    monkeypatch.setattr(probe, "SYSTEM_UV", system)
    monkeypatch.setattr(probe, "SCRATCH", tmp_path)
    commands: list[list[str]] = []
    verified: list[Path] = []

    def verify(path: Path) -> None:
        verified.append(path)
        if path == system and not approved:
            raise probe.Stop("RESULT_INCONCLUSIVE", "UV_VERSION_MISMATCH")

    monkeypatch.setattr(probe, "verify_uv", verify)
    monkeypatch.setattr(
        probe, "bounded_process", lambda args, timeout: commands.append(args)
    )
    selected = probe.resolve_uv()
    if approved:
        assert selected == system and commands == []
    else:
        assert selected == tmp_path / "bootstrap-tools/bin/uv"
        assert verified == [system, selected]
        assert any("uv==0.9.5" in args for args in commands)


def test_partial_venv_is_not_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    python = tmp_path / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("incomplete")
    monkeypatch.setattr(probe, "SCRATCH", tmp_path)
    monkeypatch.setattr(probe, "PYTHON", python)
    with pytest.raises(probe.Stop) as error:
        probe.create_runtime(probe.fresh_result())
    assert error.value.reason == "RUNTIME_ENV_CREATION_FAILED"
    assert python.read_text() == "incomplete"


@pytest.mark.parametrize("fail", [False, True])
def test_valid_python_without_ensurepip_uses_uv(
    fail: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(probe, "SCRATCH", tmp_path)
    monkeypatch.setattr(probe, "PYTHON", tmp_path / "venv/bin/python")
    monkeypatch.setattr(probe, "system_python", lambda: Path("/usr/bin/python3.12"))
    monkeypatch.setattr(probe, "resolve_uv", lambda: Path("/usr/local/bin/uv"))
    commands: list[list[str]] = []

    def command(args: list[str], timeout: int) -> None:
        commands.append(args)
        assert args[0] == str(Path("/usr/local/bin/uv"))
        assert args[args.index("--python") + 1] == str(Path("/usr/bin/python3.12"))
        assert "--seed" in args
        assert "-m" not in args  # No stdlib venv, hence no ensurepip dependency.
        if fail:
            raise probe.Stop("RESULT_INCONCLUSIVE")
        probe.PYTHON.parent.mkdir(parents=True)
        probe.PYTHON.touch()

    def inspect(path: Path, *, isolated: bool = False, pristine: bool = False) -> str:
        if isolated:
            assert pristine is True
        return "3.12.3"

    monkeypatch.setattr(probe, "bounded_process", command)
    monkeypatch.setattr(probe, "inspect_interpreter", inspect)
    monkeypatch.setattr(probe, "save", lambda result: None)
    result = probe.fresh_result()
    if fail:
        with pytest.raises(probe.Stop) as error:
            probe.create_runtime(result)
        assert error.value.reason == "RUNTIME_ENV_CREATION_FAILED"
    else:
        probe.create_runtime(result)
        assert result["runtime_versions"]["python"] == "3.12.3"
    assert len(commands) == 1


def test_inherited_packages_rejected_before_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyvenv.cfg").write_text("include-system-site-packages = false\n")
    info = {
        "version": [3, 12, 3],
        "implementation": "cpython",
        "venv": True,
        "user_site": False,
        "inherited": True,
    }

    def run(*args: Any, **kwargs: Any) -> Any:
        assert "ensurepip" not in args[0][-1]
        return subprocess.CompletedProcess([], 0, json.dumps(info), "")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(probe.Stop) as error:
        probe.inspect_interpreter(tmp_path / "bin/python", isolated=True, pristine=True)
    assert error.value.reason == "RUNTIME_ISOLATION_FAILED"
    info["inherited"] = False
    assert (
        probe.inspect_interpreter(tmp_path / "bin/python", isolated=True, pristine=True)
        == "3.12.3"
    )


def test_no_base_mutation_commands() -> None:
    source = (probe.SOURCE / "runtime_probe.py").read_text()
    for forbidden in ("sudo", "apt-get", "apt install", "--system-site-packages"):
        assert forbidden not in source
