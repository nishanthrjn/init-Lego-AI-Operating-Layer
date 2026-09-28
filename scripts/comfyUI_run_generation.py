"""Run the reviewed workflow once and preserve the helper's diagnostics."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Define your generation variables
workflow_path = r".\comfyui-proof\workflow.json"
checkpoint = "v1-5-pruned-emaonly.safetensors"
# sha256 = "APPROVED_SHA256"
sha256 = "866cac365049f11c819f547d3a2e0bf4272f73b015f7664d958ef10223deb8a8"
prompt = "a cute white bunny sleeping inside a teacup, flowers around it, pastel colors, cozy, whimsical, soft lighting, highly detailed, 8k, cinematic lighting, photorealistic, trending on artstation"
seed = "42"
output_path = r".\comfyui-proof\mug.png"
# Operator completion wait in seconds (max 1800). CPU runs observed ~640 s.
timeout_seconds = "900"


def main() -> int:
    if re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
        print("Configuration error: replace APPROVED_SHA256 with the reviewed workflow's lowercase SHA-256.")
        print("Inspect comfyui-proof/workflow.json, then use Get-FileHash -Algorithm SHA256 to obtain its digest.")
        print("No generation was submitted.")
        return 1
    command = [
        sys.executable, "-u", str(ROOT / "examples/comfyui-text-to-image/generate.py"),
        "--workflow", str(ROOT / workflow_path),
        "--sha256", sha256,
        "--checkpoint", checkpoint,
        "--prompt", prompt,
        "--seed", seed,
        "--output", str(ROOT / output_path),
        "--timeout", timeout_seconds,
    ]
    print(f"Generating image with seed {seed}...", flush=True)
    try:
        # Inherit both streams: failures may be reported on stdout, not stderr.
        result = subprocess.run(command, cwd=ROOT, check=False)
    except OSError:
        print("Could not start the generation helper. Check the active Python environment.")
        return 1
    if result.returncode == 0:
        print("Generation successful!")
    else:
        print(f"Generation helper exited with code {result.returncode}. See diagnostics above; no automatic retry.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
