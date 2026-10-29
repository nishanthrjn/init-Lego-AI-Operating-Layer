"""Independent v3 freeze; historical v2 identity is recorded, never verified."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.kisski_coding_eval.frozen import SOURCES as V1_SOURCES
from scripts.kisski_coding_eval_v2.frozen import ADR as ADR
from scripts.kisski_coding_eval_v2.frozen import SOURCES as V2_SOURCES
from scripts.kisski_coding_eval_v2.frozen import ManifestNotFrozen as ManifestNotFrozen
from scripts.kisski_coding_eval_v2.frozen import content as content

from .pack import instructions

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = "scripts/kisski_coding_eval_v3"
V2_DIGEST = "a5038d5a7a357c06f9ae0c3487b71a0663ffc0430dae06b9eeab56825920a1e9"
SOURCES = tuple(
    dict.fromkeys(
        (
            f"{DIRECTORY}/__init__.py",
            f"{DIRECTORY}/pack.py",
            f"{DIRECTORY}/scoring.py",
            f"{DIRECTORY}/invocation.py",
            f"{DIRECTORY}/runner.py",
            f"{DIRECTORY}/frozen.py",
            "planning/FORGEAI-KISSKI-CODING-MODEL-EVALUATION-3.md",
            *V2_SOURCES,
            *V1_SOURCES,
            "scripts/kisski_coding_eval/__init__.py",
            "scripts/kisski_dev_screen/__init__.py",
        )
    )
)


def emit(root: Path = ROOT) -> dict[str, Any]:
    """V2 emit shape; intentionally no historical verify call at changed HEAD."""
    return {
        "sources": {
            name: hashlib.sha256(content(root / name)).hexdigest() for name in SOURCES
        },
        "instructions": {
            role: hashlib.sha256(text.encode("utf-8")).hexdigest()
            for role, text in instructions().items()
        },
        "v2_manifest_digest": V2_DIGEST,
        "adr_021_digest": hashlib.sha256(content(root / ADR)).hexdigest(),
    }


def verify(root: Path = ROOT) -> str:
    # V2 frozen.verify:66-85, with v3 inventory and historical recorded identity.
    try:
        raw = content(root / DIRECTORY / "manifest.json")
        pins = json.loads(raw)
        if type(pins) is not dict or set(pins) != {
            "sources",
            "instructions",
            "v2_manifest_digest",
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
