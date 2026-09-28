# ruff: noqa: E402
"""Operator virtual try-on helper: configuration in, VirtualTryOnPort out.

Never starts ComfyUI, downloads models or chooses hardware. The provider, API
family, model files and geometry come from --config; this file only reads two
local PNGs (their paths are never sent) and prints safe diagnostics.
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

from legoai_generative_media.config import TryOnConfig, load_try_on_config
from legoai_generative_media.service import (
    ProviderError,
    TryOnService,
    open_virtual_try_on,
)
from legoai_generative_media.values import (
    GeneratedImage,
    GenerationCancelled,
    ImageInput,
    TryOnRequest,
)

MAX_READ = 16 * 1024 * 1024 + 1


def read_png(path: Path) -> ImageInput:
    """Bounded local read; validation and metadata stripping happen in ImageInput."""
    with path.open("rb") as source:
        return ImageInput(source.read(MAX_READ))


def save(image: GeneratedImage, output: Path | None) -> None:
    if output is not None:
        with output.open("xb") as destination:
            destination.write(image.content)
    print(
        f"PNG {image.width}x{image.height} bytes:",
        image.byte_length,
        "SHA-256:",
        image.sha256,
    )


async def reconcile(service: TryOnService, job_id: str, output: Path | None) -> int:
    job = service.job(job_id)
    print("mode: reconcile existing try-on job (read-only)")
    result = await service.reconcile(job)
    print("submission performed: NO")
    print("uploads performed: NO")
    print("status:", result.status.value.upper(), "effect:", result.effect.value)
    if result.error is not None:
        print("category:", result.error.value, "reason:", result.reason or "-")
    if result.image is None:
        return 1
    save(result.image, output)
    return 0


async def run(args: argparse.Namespace, config: TryOnConfig) -> int:
    service = await open_virtual_try_on(config)
    for key, value in service.describe().items():
        print(f"{key}: {value}")
    if args.reconcile is not None:
        return await reconcile(service, args.reconcile, args.output)
    request = TryOnRequest(read_png(args.person), read_png(args.garment), args.seed)
    try:
        result = await service.try_on(request)
    except GenerationCancelled as cancelled:
        result = cancelled.result
    print(
        "outcome:",
        result.outcome.value,
        "effect:",
        result.effect.value,
        "input_disclosure:",
        result.input_disclosure.value,
        "cessation:",
        result.cessation.value,
    )
    print("job:", result.job.job_id if result.job else "unknown/not submitted")
    if result.image is None:
        print("category:", result.error.value if result.error else "cancelled")
        print("reason:", result.reason or "-")
        for line in result.evidence:
            print("evidence", line)
        if result.job is not None:
            print(
                "Reconcile later without resubmitting: --reconcile", result.job.job_id
            )
        return 1
    save(result.image, args.output)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--person", type=Path, help="Local PNG; never sent by path")
    parser.add_argument("--garment", type=Path, help="Local PNG; never sent by path")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reconcile", metavar="JOB_ID")
    args = parser.parse_args()
    if args.output is not None and args.output.exists():
        parser.error("output already exists")
    if args.reconcile is None and (
        args.person is None or args.garment is None or args.output is None
    ):
        parser.error("--person, --garment and --output are required")
    try:
        config = load_try_on_config(args.config)
    except ValueError as error:
        parser.error(str(error))
    try:
        return asyncio.run(run(args, config))
    except ProviderError as error:
        print("provider:", error.reason, "category:", error.category.value)
    except ValueError, OSError, TypeError:
        print("Configuration, input or provider failure; no automatic retry.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
