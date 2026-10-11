"""Closed transfer inventory, normalized text hashes and bounded manual packaging."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from .contracts import VERSION, Rejected

SOURCE = Path(__file__).resolve().parent
FILES = (
    "__init__.py",
    "README.md",
    "DECISION.md",
    "contracts.py",
    "scenarios.py",
    "safety.py",
    "evaluator.py",
    "package.py",
    "quality_probe.py",
    "runtime_worker.py",
    "result.schema.json",
    "result_contract.py",
    "requirements-evaluation.txt",
    "kaggle_quality.ipynb",
    "fixtures/PROVENANCE.md",
)


def normalized(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 131072:
        raise Rejected("PACKAGE_INVALID")
    return path.read_bytes().replace(b"\r\n", b"\n")


def identity(source: Path = SOURCE) -> str:
    manifest_bytes = normalized(source / "manifest.json")
    manifest: Any = json.loads(manifest_bytes)
    if set(manifest) != {"evaluation_version", "files"}:
        raise Rejected("PACKAGE_INVALID")
    if manifest["evaluation_version"] != VERSION or set(manifest["files"]) != set(
        FILES
    ):
        raise Rejected("PACKAGE_INVALID")
    for name in FILES:
        content = normalized(source / name)
        if hashlib.sha256(content).hexdigest() != manifest["files"][name]:
            raise Rejected("PACKAGE_INVALID")
    return hashlib.sha256(manifest_bytes).hexdigest()


def build(destination: Path) -> str:
    """Explicit maintainer packaging only; never called by the live runner."""
    package_digest = identity()
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in (*FILES, "manifest.json"):
            info = zipfile.ZipInfo("forgeai_model_quality_1/" + name)
            info.date_time = (2026, 10, 11, 0, 0, 0)
            info.external_attr = 0o100644 << 16
            archive.writestr(info, normalized(SOURCE / name))
    return package_digest
