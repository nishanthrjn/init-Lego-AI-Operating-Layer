"""Text-normalized source pins for the frozen evaluation and reused contracts."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = "scripts/kisski_coding_eval"
CONTRACTS = "experiments/kaggle/forgeai_model_quality_1"
SOURCES = (
    f"{DIRECTORY}/pack.py",
    f"{DIRECTORY}/scoring.py",
    f"{DIRECTORY}/runner.py",
    f"{DIRECTORY}/frozen.py",
    f"{CONTRACTS}/contracts.py",
    f"{CONTRACTS}/safety.py",
    f"{CONTRACTS}/contract-baseline.json",
)


def verify(root: Path = ROOT) -> str:
    manifest = root / DIRECTORY / "manifest.json"
    if manifest.is_symlink() or manifest.stat().st_size > 16384:
        raise ValueError("invalid frozen manifest")
    raw = manifest.read_bytes().replace(b"\r\n", b"\n")
    pins = json.loads(raw)
    if type(pins) is not dict or set(pins) != set(SOURCES):
        raise ValueError("frozen inventory mismatch")
    for name, expected in pins.items():
        path = root / name
        if path.is_symlink() or path.stat().st_size > 131072:
            raise ValueError("invalid frozen source")
        content = path.read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError("frozen evaluation changed; review and version required")
    baseline = json.loads((root / CONTRACTS / "contract-baseline.json").read_bytes())
    for name, expected in baseline.items():
        content = (root / name).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError("canonical schema drift; review the reused snapshot")
    return hashlib.sha256(raw).hexdigest()
