"""Experiment-owned acquisition helpers; importing performs no I/O.

Adapted from free_gpu_model_runtime/runtime_probe.py: UV_VERSION (33),
uv_version (865), verify_uv (888), resolve_uv (893-943). The new experiment
alone uses 0.11.13 and requires the published Linux wheel digest.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import BinaryIO

UV_VERSION = "0.11.13"
UV_SHA256 = "e23ddb47f7a317979cf1945cf9ed89d2639f60f7d06164f9ff1ad292c4cc5b3c"
UV_WHEEL = (
    "https://files.pythonhosted.org/packages/e3/ad/"
    "dfb82224e73031c71dc70eb4513a6f4f6af66da35c3c955e28d75fe03d1c/"
    "uv-0.11.13-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
)
PYTHON_VERSION = "3.14.5"
PYTHON_TARGET = "cpython-3.14.5-linux-x86_64-gnu"
SCRATCH = Path("/tmp/legoai-c1")
SYSTEM_UV = Path("/usr/local/bin/uv")
TAIL_BYTES = 8192
PROCESS_ERRORS = (OSError, subprocess.SubprocessError)


def environment() -> dict[str, str]:
    """Explicit child environment, following 1G; never dump ambient values."""
    result = {
        "PATH": "/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/bin:/usr/bin:/bin",
        "HOME": str(SCRATCH / "home"),
        "TMPDIR": str(SCRATCH),
        "LANG": "C.UTF-8",
        "UV_PYTHON_INSTALL_DIR": str(SCRATCH / "pythons"),
        "UV_PYTHON_BIN_DIR": str(SCRATCH / "bin"),
        "UV_CACHE_DIR": str(SCRATCH / "uv-cache"),
        "UV_HTTP_RETRIES": "0",
        "UV_HTTP_TIMEOUT": "30",
        "PYTHONUNBUFFERED": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    value = os.environ.get("LD_LIBRARY_PATH")
    if value is not None:
        entries = value.split(":")
        allowed = {"/usr/local/nvidia/lib64", "/usr/local/cuda/lib64"}
        if (
            len(value) > 512
            or len(entries) > 8
            or any(x not in allowed for x in entries)
        ):
            raise ValueError("BOOTSTRAP_FAILED")
        result["LD_LIBRARY_PATH"] = ":".join(dict.fromkeys(entries))
    return result


def drain(stream: BinaryIO, tail: bytearray) -> None:
    with stream:
        while chunk := stream.read(4096):
            tail.extend(chunk)
            del tail[:-TAIL_BYTES]


def stop_process(process: subprocess.Popen[bytes]) -> None:
    """Kill the owned session, including descendants, and reap its leader."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=10)


def command(
    argv: list[str], timeout: float, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Drain both pipes continuously; never buffer unbounded process output."""
    if timeout <= 0:
        raise subprocess.TimeoutExpired(argv, timeout)
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    assert process.stdout is not None and process.stderr is not None
    tails = (bytearray(), bytearray())
    readers = [
        threading.Thread(target=drain, args=(stream, tail), daemon=True)
        for stream, tail in zip((process.stdout, process.stderr), tails, strict=True)
    ]
    for reader in readers:
        reader.start()
    try:
        process.wait(timeout=timeout)
    finally:
        stop_process(process)
        for reader in readers:
            reader.join(timeout=5)
        if any(reader.is_alive() for reader in readers):
            raise RuntimeError("BOOTSTRAP_FAILED")
    assert process.returncode is not None
    return subprocess.CompletedProcess(
        argv,
        process.returncode,
        tails[0].decode("utf-8", errors="replace"),
        tails[1].decode("utf-8", errors="replace"),
    )


def uv_version(executable: Path, timeout: float = 15) -> str:
    result = command([str(executable), "--version"], timeout)
    parts = result.stdout.split()
    if (
        result.returncode
        or len(result.stdout) > 128
        or len(parts) < 2
        or parts[0] != "uv"
        or re.fullmatch(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", parts[1]) is None
    ):
        raise ValueError("BOOTSTRAP_FAILED")
    return parts[1]


def verify_uv(executable: Path, timeout: float = 15) -> None:
    if uv_version(executable, timeout) != UV_VERSION:
        raise ValueError("BOOTSTRAP_FAILED")


def pip_uv_argv(requirements: Path, tooling: Path) -> list[str]:
    return [
        sys.executable,
        "-I",
        "-m",
        "pip",
        "--isolated",
        "install",
        "--no-input",
        "--target",
        str(tooling),
        "--index-url",
        "https://pypi.org/simple",
        "--only-binary=:all:",
        "--no-deps",
        "--retries",
        "0",
        "--timeout",
        "30",
        "--no-cache-dir",
        "--disable-pip-version-check",
        "--require-hashes",
        "-r",
        str(requirements),
    ]


def resolve_uv(deadline: float = float("inf")) -> Path:
    if (
        SYSTEM_UV.is_file()
        and uv_version(SYSTEM_UV, min(15, deadline - time.monotonic())) == UV_VERSION
    ):
        return SYSTEM_UV
    tooling = SCRATCH / "tools"
    if tooling.exists() or tooling.is_symlink():
        raise ValueError("BOOTSTRAP_FAILED")
    requirements = SCRATCH / "uv-requirements.txt"
    with requirements.open("x", encoding="utf-8") as file:
        file.write(f"uv @ {UV_WHEEL} --hash=sha256:{UV_SHA256}\n")
    result = command(
        pip_uv_argv(requirements, tooling), min(180, deadline - time.monotonic())
    )
    uv = tooling / "bin/uv"
    if (
        result.returncode
        or not uv.is_file()
        or uv.is_symlink()
        or not uv.resolve().is_relative_to(tooling.resolve())
    ):
        raise ValueError("BOOTSTRAP_FAILED")
    verify_uv(uv, min(15, deadline - time.monotonic()))
    return uv
