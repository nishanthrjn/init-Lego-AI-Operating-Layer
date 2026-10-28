"""Maintainer-only manifest emission; verification never refreshes pins.

Source normalization and bounded reads follow v1 frozen.py:21-43.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.kisski_coding_eval import frozen as v1

from .pack import instructions

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = "scripts/kisski_coding_eval_v2"
V1_DIGEST = "3cd0e5a14f6ff9d2beba5cb1af9bcc6ac214637a7b3858ad3282bd0e51691ef6"
SOURCES = (
    f"{DIRECTORY}/__init__.py",
    f"{DIRECTORY}/pack.py",
    f"{DIRECTORY}/scoring.py",
    f"{DIRECTORY}/invocation.py",
    f"{DIRECTORY}/runner.py",
    f"{DIRECTORY}/frozen.py",
    "scripts/kisski_dev_screen/runner.py",
    "scripts/kisski_dev_screen/diagnostics.py",
    "scripts/kisski_dev_screen/invocation.py",
    "scripts/kisski_compatibility_probe.py",
    "scripts/kisski_saia_qualification.py",
    "packages/legoai-engineering/src/legoai_engineering/coding/definition.py",
    "packages/legoai-engineering/src/legoai_engineering/reviewer/definition.py",
    "packages/legoai-engineering/src/legoai_engineering/_json_document.py",
    "planning/FORGEAI-KISSKI-CODING-MODEL-EVALUATION-2.md",
)
ADR = "adrs/ADR-021.md"


class ManifestNotFrozen(ValueError):
    def __init__(self) -> None:
        super().__init__("MANIFEST_NOT_FROZEN")


def content(path: Path) -> bytes:
    if path.is_symlink() or path.stat().st_size > 262144:
        raise ManifestNotFrozen()
    return path.read_bytes().replace(b"\r\n", b"\n")


def emit(root: Path = ROOT) -> dict[str, Any]:
    """Compute only when explicitly executed by the maintainer (or offline tests)."""
    if v1.verify(root) != V1_DIGEST:
        raise ManifestNotFrozen()
    return {
        "sources": {
            name: hashlib.sha256(content(root / name)).hexdigest() for name in SOURCES
        },
        "instructions": {
            role: hashlib.sha256(text.encode("utf-8")).hexdigest()
            for role, text in instructions().items()
        },
        "v1_manifest_digest": V1_DIGEST,
        "adr_021_digest": hashlib.sha256(content(root / ADR)).hexdigest(),
    }


def verify(root: Path = ROOT) -> str:
    try:
        raw = content(root / DIRECTORY / "manifest.json")
        pins = json.loads(raw)
        # Placeholders fail before reading/hashing the full source inventory.
        if type(pins) is not dict or set(pins) != {
            "sources",
            "instructions",
            "v1_manifest_digest",
            "adr_021_digest",
        }:
            raise ManifestNotFrozen()
        if pins != emit(root):
            raise ManifestNotFrozen()
        return hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError, TypeError, RecursionError) as error:
        raise ManifestNotFrozen() from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(emit(), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
