# ruff: noqa: E402
"""Operator tool: write the TRY_ON template for review and print its digest.

Operator tooling, not an application: it names the template layer so that
applications never have to. No network, no ComfyUI, no model download.
Generating a digest is not approval; review the bytes first.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "packages" / "legoai-generative-media" / "src"),
    str(ROOT / "src"),
]

from legoai_generative_media.tryon import TryOnModels, tryon_template


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--diffusion-model", default="qwen_image_edit_2509_fp8_e4m3fn.safetensors"
    )
    parser.add_argument(
        "--text-encoder", default="qwen_2.5_vl_7b_fp8_scaled.safetensors"
    )
    parser.add_argument("--vae", default="qwen_image_vae.safetensors")
    args = parser.parse_args()
    models = TryOnModels(args.diffusion_model, args.text_encoder, args.vae)
    content = json.dumps(tryon_template(models), indent=2).encode() + b"\n"
    with args.output.open("xb") as destination:
        destination.write(content)
    print(
        "Review the template before approving. SHA-256:",
        hashlib.sha256(content).hexdigest(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
