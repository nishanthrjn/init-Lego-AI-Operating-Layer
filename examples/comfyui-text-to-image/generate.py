# ruff: noqa: E402
"""Explicit operator live helper. Never starts or modifies ComfyUI.

The provider comes from --config (any admitted profile) or, for the validated
local workflow, from --workflow/--sha256/--checkpoint/--endpoint flags. Either
way this helper sees only the application-facing ports.
"""

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

# Repository example bootstrap only; wheel consumers import the installed package.
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "packages" / "legoai-generative-media" / "src"),
    str(ROOT / "src"),
]

from legoai_generative_media.config import GenerationConfig, load_config, local_config
from legoai_generative_media.service import (
    ProviderError,
    TextToImageService,
    open_text_to_image,
)
from legoai_generative_media.values import (
    GeneratedImage,
    GenerationCancelled,
    TextToImageRequest,
)
from legoai_generative_media.workflow import template


def save(image: GeneratedImage, output: Path | None) -> None:
    if output is not None:
        # Explicit output only; exclusive creation prevents overwriting another result.
        with output.open("xb") as destination:
            destination.write(image.content)
    print("PNG bytes:", image.byte_length, "SHA-256:", image.sha256)


def describe(service: TextToImageService) -> None:
    for key, value in service.describe().items():
        print(f"{key}: {value}")


async def reconcile(
    service: TextToImageService, job_id: str, output: Path | None
) -> int:
    job = service.job(job_id)
    print("mode: reconcile existing job (read-only)")
    result = await service.reconcile(job)
    # Structural: reconciliation uses a GET-only budget that refuses any POST.
    print("submission performed: NO")
    print("job:", job.job_id)
    print("status:", result.status.value.upper(), "effect:", result.effect.value)
    if result.error is not None:
        print("category:", result.error.value, "reason:", result.reason or "-")
    if result.image is None:
        return 1
    save(result.image, output)
    return 0


async def run(args: argparse.Namespace, config: GenerationConfig) -> int:
    service = await open_text_to_image(config)
    describe(service)
    if args.reconcile is not None:
        return await reconcile(service, args.reconcile, args.output)
    print(
        "completion policy: max wait", config.provider.completion.max_wait_seconds, "s"
    )
    task = asyncio.create_task(
        service.generate(TextToImageRequest(args.prompt, args.seed))
    )
    timer = None
    if args.cancel_after is not None:
        timer = asyncio.get_running_loop().call_later(args.cancel_after, task.cancel)
    try:
        result = await task
    except GenerationCancelled as cancelled:
        result = cancelled.result
    finally:
        if timer is not None:
            timer.cancel()
    print(
        "outcome:",
        result.outcome.value,
        "effect:",
        result.effect.value,
        "cessation:",
        result.cessation.value,
    )
    print("job:", result.job.job_id if result.job else "unknown/not submitted")
    if result.image is None:
        print("category:", result.error.value if result.error else "cancelled")
        print("reason:", result.reason or "-")
        if result.job is not None:
            print(
                "Reconcile later without resubmitting: --reconcile", result.job.job_id
            )
        return 1
    save(result.image, args.output)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, help="Provider configuration (TOML)")
    parser.add_argument("--checkpoint", help="Operator-selected installed basename")
    parser.add_argument("--workflow", type=Path)
    parser.add_argument(
        "--prepare-template",
        action="store_true",
        help="Write original fixed graph for operator review only; no network",
    )
    parser.add_argument("--sha256")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8188")
    parser.add_argument("--prompt")
    parser.add_argument("--seed", type=int)
    parser.add_argument(
        "--timeout",
        type=float,
        default=300,
        help="Total completion wait in seconds for flag-based local runs (max 1800)",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cancel-after", type=float)
    parser.add_argument(
        "--reconcile",
        metavar="JOB_ID",
        help="Inspect an existing job and retrieve its image; never submits",
    )
    args = parser.parse_args()
    if args.prepare_template:
        if not args.checkpoint or args.workflow is None:
            parser.error("--prepare-template needs --checkpoint and --workflow")
        content = json.dumps(template(args.checkpoint), indent=2).encode() + b"\n"
        with args.workflow.open("xb") as destination:
            destination.write(content)
        print(
            "Review template before approving. SHA-256:",
            hashlib.sha256(content).hexdigest(),
        )
        return 0
    if args.output is not None and args.output.exists():
        parser.error("output already exists")
    try:
        if args.config is not None:
            if args.workflow or args.sha256 or args.checkpoint:
                parser.error("--config replaces --workflow/--sha256/--checkpoint")
            config = load_config(args.config)
        else:
            if args.workflow is None or not args.sha256 or not args.checkpoint:
                parser.error("--config or --workflow/--sha256/--checkpoint required")
            config = local_config(
                args.workflow, args.sha256, args.checkpoint, args.endpoint, args.timeout
            )
    except ValueError as error:
        # Configuration errors name keys and references, never secret values.
        parser.error(str(error))
    if args.reconcile is not None:
        if args.prompt is not None or args.seed is not None or args.cancel_after:
            parser.error("--reconcile takes no --prompt, --seed or --cancel-after")
    else:
        if not args.prompt or args.output is None:
            parser.error("--prompt and --output are required for generation")
        if args.cancel_after is not None and not 0 < args.cancel_after <= 1800:
            parser.error("cancel-after must be in (0,1800]")
    try:
        return asyncio.run(run(args, config))
    except ProviderError as error:
        print("provider:", error.reason, "category:", error.category.value)
    except ValueError, OSError, TypeError:
        print("Local configuration/output failure; no automatic retry.")
    if args.reconcile is not None:
        print("submission performed: NO")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
