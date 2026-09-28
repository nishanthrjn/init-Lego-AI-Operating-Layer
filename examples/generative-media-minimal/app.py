# ruff: noqa: E402
"""Minimal consumer: a configuration file in, a TextToImagePort out.

Switching local <-> Cloud <-> v2 changes only --config; this source never
branches on provider, endpoint, API family, credentials or hardware.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Repository example bootstrap only; wheel consumers import the installed package.
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "packages" / "legoai-generative-media" / "src"),
    str(ROOT / "src"),
]

from legoai_generative_media.config import load_config
from legoai_generative_media.ports import TextToImagePort
from legoai_generative_media.service import open_text_to_image
from legoai_generative_media.values import (
    GenerationCancelled,
    GenerationResult,
    TextToImageRequest,
)


async def consume(
    port: TextToImagePort, prompt: str, seed: int | None
) -> GenerationResult:
    """The whole application-side dependency: the port and the request."""
    try:
        return await port.generate(TextToImageRequest(prompt, seed))
    except GenerationCancelled as cancelled:
        return cancelled.result


async def run(args: argparse.Namespace) -> int:
    port = await open_text_to_image(load_config(args.config))
    result = await consume(port, args.prompt, args.seed)
    print("outcome:", result.outcome.value, "effect:", result.effect.value)
    print("job:", result.job.job_id if result.job else "unknown/not submitted")
    if result.image is None:
        print("category:", result.error.value if result.error else "cancelled")
        print("reason:", result.reason or "-")
        return 1
    with args.output.open("xb") as destination:
        destination.write(result.image.content)
    print("PNG bytes:", result.image.byte_length, "SHA-256:", result.image.sha256)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists")
    try:
        return asyncio.run(run(args))
    except ValueError, OSError, TypeError:
        print("Configuration/provider failure; no automatic retry.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
