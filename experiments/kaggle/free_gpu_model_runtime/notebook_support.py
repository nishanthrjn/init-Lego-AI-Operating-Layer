"""Canonical thin-notebook bootstrap helpers; mirrored verbatim in its first cell."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


def discover_source(root: Path, manifest_digest: str) -> Path:
    pending = [(root, 0)]
    matches: list[Path] = []
    visited = 0
    while pending:
        directory, depth = pending.pop(0)
        for child in directory.iterdir():
            visited += 1
            if visited > 4096:
                raise RuntimeError("SOURCE_DISCOVERY_LIMIT")
            if child.is_symlink():
                continue
            if child.is_dir() and depth < 6:
                pending.append((child, depth + 1))
            if child.name != "source-manifest.json" or not child.is_file():
                continue
            if child.stat().st_size > 16384:
                continue
            raw = child.read_bytes().replace(b"\r\n", b"\n")
            if hashlib.sha256(raw).hexdigest() != manifest_digest:
                continue
            manifest = json.loads(raw)
            if manifest["experiment"] != "FREE-GPU-MODEL-RUNTIME-KAGGLE-1D":
                continue
            valid = True
            for name, digest in manifest["files"].items():
                relative = Path(name)
                if relative.is_absolute() or ".." in relative.parts:
                    raise RuntimeError("SOURCE_IDENTITY_FAILED")
                file = child.parent / relative
                if (
                    not file.is_file()
                    or file.is_symlink()
                    or file.stat().st_size > 1048576
                ):
                    valid = False
                    break
                if (
                    hashlib.sha256(
                        file.read_bytes().replace(b"\r\n", b"\n")
                    ).hexdigest()
                    != digest
                ):
                    valid = False
                    break
            if valid:
                matches.append(child.parent)
    if len(matches) != 1:
        raise RuntimeError("SOURCE_NOT_UNIQUE")
    return matches[0]


def bounded_diagnostics(text: str) -> str:
    # Runtime phase messages are closed. Do not print unexpected tracebacks,
    # paths or package diagnostics into a saved notebook output.
    lines = []
    for line in text[:4096].splitlines()[:32]:
        if re.fullmatch(r"(?:[a-z_]+: )?[A-Z][A-Z0-9_]+(?: / [A-Z][A-Z0-9_]+)?", line):
            lines.append(line)
        else:
            lines.append("INTERNAL_BOUNDED_FAILURE")
    return "\n".join(lines)


def run_phase(source: Path, mode: str, timeout: int) -> None:
    if mode not in ("inspect", "bootstrap", "run"):
        raise ValueError("unsupported phase")
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(source / "runtime_probe.py"),
                mode,
                "--confirm-free-session",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        print("stdout:\n" + bounded_diagnostics(result.stdout))
        print("stderr:\n" + bounded_diagnostics(result.stderr))
        print(f"return code: {result.returncode}")
        if result.returncode:
            raise RuntimeError("PHASE_FAILED; preserve evidence and stop")
    except subprocess.TimeoutExpired:
        print("stdout:\nstderr:\nINTERNAL_BOUNDED_FAILURE\nreturn code: TIMEOUT")
        raise RuntimeError("PHASE_TIMEOUT; preserve evidence and stop") from None
