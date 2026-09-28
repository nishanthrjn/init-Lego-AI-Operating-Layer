# ruff: noqa: E402
"""Minimal try-on consumer: depends only on VirtualTryOnPort and a config file.

No provider, API family, CUDA, model, workflow or upload knowledge here.
"""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "packages" / "legoai-generative-media" / "src"),
    str(ROOT / "src"),
]

from legoai_generative_media.config import load_try_on_config
from legoai_generative_media.ports import VirtualTryOnPort
from legoai_generative_media.service import open_virtual_try_on
from legoai_generative_media.values import (
    GenerationCancelled,
    GenerationResult,
    ImageInput,
    TryOnRequest,
)


async def consume(
    port: VirtualTryOnPort, person: bytes, garment: bytes, seed: int | None
) -> GenerationResult:
    """The whole application-side dependency: the port and two PNGs."""
    request = TryOnRequest(ImageInput(person), ImageInput(garment), seed)
    try:
        return await port.try_on(request)
    except GenerationCancelled as cancelled:
        return cancelled.result


def read(path: Path) -> bytes:
    with path.open("rb") as source:
        return source.read(16 * 1024 * 1024 + 1)  # ImageInput rejects anything larger.


async def run(args: argparse.Namespace) -> int:
    port = await open_virtual_try_on(load_try_on_config(args.config))
    result = await consume(port, read(args.person), read(args.garment), args.seed)
    print(
        "outcome:",
        result.outcome.value,
        "effect:",
        result.effect.value,
        "input_disclosure:",
        result.input_disclosure.value,
    )
    if result.image is None:
        print("category:", result.error.value if result.error else "cancelled")
        return 1
    with args.output.open("xb") as destination:
        destination.write(result.image.content)
    print("SHA-256:", result.image.sha256)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--person", required=True, type=Path)
    parser.add_argument("--garment", required=True, type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists")
    try:
        return asyncio.run(run(args))
    except ValueError, OSError, TypeError:
        print("Configuration, input or provider failure; no automatic retry.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
