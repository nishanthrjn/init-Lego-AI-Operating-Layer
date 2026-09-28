# ruff: noqa: E402
"""Operator tool: write the TRY_ON template for review and print its digest.

Operator tooling, not an application: it names the template layer so that
applications never have to. No network, no ComfyUI, no model download.
Never overwrites. Generating a digest is not approval: review the bytes,
then put the digest in the configuration.
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

from legoai_generative_media.config import load_try_on_config
from legoai_generative_media.tryon import (
    HEIGHT,
    TEMPLATE_ID,
    WIDTH,
    TryOnModels,
    tryon_template,
)
from legoai_generative_media.workflow import TemplateKind

DEFAULTS = TryOnModels(
    "qwen_image_edit_2509_fp8_e4m3fn.safetensors",
    "qwen_2.5_vl_7b_fp8_scaled.safetensors",
    "qwen_image_vae.safetensors",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, help="Try-on config: model files and default output"
    )
    parser.add_argument("--output", type=Path, help="Defaults to try_on.path")
    parser.add_argument("--diffusion-model")
    parser.add_argument("--text-encoder")
    parser.add_argument("--vae")
    args = parser.parse_args(argv)
    flags = (args.diffusion_model, args.text_encoder, args.vae)
    if args.config is not None:
        if any(flags):
            parser.error("--config supplies the model files; omit model flags")
        workflow = load_try_on_config(args.config).workflow
        models, output = workflow.models(), args.output or workflow.path
    else:
        if args.output is None:
            parser.error("--output is required without --config")
        models = TryOnModels(
            args.diffusion_model or DEFAULTS.diffusion_model,
            args.text_encoder or DEFAULTS.text_encoder,
            args.vae or DEFAULTS.vae,
        )
        output = args.output
    content = json.dumps(tryon_template(models), indent=2).encode() + b"\n"
    try:
        with output.open("xb") as destination:
            destination.write(content)
    except FileExistsError:
        parser.error(f"refusing to overwrite existing {output.name}")
    print("template kind:", TemplateKind.TRY_ON.value, f"({TEMPLATE_ID})")
    print(f"fixed geometry: {WIDTH}x{HEIGHT}")
    print("diffusion model:", models.diffusion_model)
    print("text encoder:", models.text_encoder)
    print("vae:", models.vae)
    print("written:", output)
    print("SHA-256:", hashlib.sha256(content).hexdigest())
    print("Review the template, then set try_on.sha256 to this digest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
