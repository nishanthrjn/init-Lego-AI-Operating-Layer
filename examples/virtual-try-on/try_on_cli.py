# ruff: noqa: E402
"""Operator virtual try-on helper: configuration in, VirtualTryOnPort out.

Modes (exactly one):

- `--preflight`: read-only readiness check; never uploads or submits.
- `--live`: one generation; uploads two local PNGs and submits once.
- `--reconcile JOB_ID`: read-only; retrieves an existing output.

Never starts ComfyUI, downloads models or chooses hardware. Provider, API
family, model files and geometry come from --config. Image paths are local
ingress only and are never sent. Only safe fields are printed.
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Repository example bootstrap only; wheel consumers import the installed package.
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "packages" / "legoai-generative-media" / "src"),
    str(ROOT / "src"),
]

from legoai_generative_media.config import TryOnConfig, load_try_on_config
from legoai_generative_media.service import (
    PreflightReport,
    ProviderError,
    TryOnService,
    WriteCounter,
    default_transports,
    open_virtual_try_on,
    preflight_virtual_try_on,
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
    print("PNG bytes:", image.byte_length)
    print("width:", image.width, "height:", image.height)
    print("SHA-256:", image.sha256)


def show(report: PreflightReport) -> None:
    for key, value in report.lines:
        print(f"{key}: {value}")
    print("preflight:", "PASS" if report.ok else "FAIL")


def writes(counter: WriteCounter) -> None:
    print("uploads performed:", counter.uploads)
    print("submission performed:", "YES" if counter.submissions else "NO")
    print("submissions attempted:", counter.submissions)


async def preflight(config: TryOnConfig, counter: WriteCounter) -> int:
    print("mode: preflight (read-only)")
    report = await preflight_virtual_try_on(config, transports=counter)
    show(report)
    writes(counter)
    return 0 if report.ok else 1


async def reconcile(
    service: TryOnService,
    job_id: str,
    output: Path | None,
    counter: WriteCounter,
    expect: str | None = None,
) -> int:
    job = service.job(job_id)
    print("mode: reconcile existing try-on job (read-only)")
    result = await service.reconcile(job)
    writes(counter)
    print("status:", result.status.value.upper(), "effect:", result.effect.value)
    if result.error is not None:
        print("category:", result.error.value, "reason:", result.reason or "-")
    if result.image is None:
        return 1
    save(result.image, output)
    if expect is not None:
        match = result.image.sha256 == expect.lower()
        print("digest matches generation:", "YES" if match else "NO")
        if not match:
            return 1
    return 0


async def generate(
    args: argparse.Namespace, config: TryOnConfig, counter: WriteCounter
) -> int:
    print("mode: live generation (uploads 2 local PNGs, submits once)")
    person, garment = read_png(args.person), read_png(args.garment)
    report = await preflight_virtual_try_on(config, transports=counter)
    show(report)
    if not report.ok:
        writes(counter)
        print("input_disclosure: none (stopped before any upload)")
        return 1
    service = await open_virtual_try_on(config, transports=counter)
    started = time.monotonic()
    try:
        result = await service.try_on(TryOnRequest(person, garment, args.seed))
    except GenerationCancelled as cancelled:
        result = cancelled.result
    elapsed = time.monotonic() - started
    writes(counter)
    print("job:", result.job.job_id if result.job else "unknown/not submitted")
    print("input_disclosure:", result.input_disclosure.value)
    print("outcome:", result.outcome.value)
    print("effect:", result.effect.value)
    print("cessation:", result.cessation.value)
    print(f"elapsed seconds: {elapsed:.1f}")
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


async def run(args: argparse.Namespace, config: TryOnConfig) -> int:
    counter = WriteCounter(default_transports(config.provider))
    if args.preflight:
        return await preflight(config, counter)
    if args.reconcile is not None:
        service = await open_virtual_try_on(config, transports=counter)
        for key, value in service.describe().items():
            print(f"{key}: {value}")
        return await reconcile(
            service, args.reconcile, args.output, counter, args.expect_sha256
        )
    return await generate(args, config, counter)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true", help="Read-only check")
    mode.add_argument(
        "--live",
        action="store_true",
        help="Confirm one generation: uploads two PNGs and submits once",
    )
    mode.add_argument("--reconcile", metavar="JOB_ID", help="Read-only retrieval")
    parser.add_argument("--person", type=Path, help="Local PNG; never sent by path")
    parser.add_argument("--garment", type=Path, help="Local PNG; never sent by path")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--expect-sha256", help="Reconcile only: digest printed by the generation"
    )
    args = parser.parse_args()
    if args.output is not None and args.output.exists():
        parser.error("output already exists")
    if args.live and (
        args.person is None or args.garment is None or args.output is None
    ):
        parser.error("--live needs --person, --garment and --output")
    if not args.live and (args.person or args.garment or args.seed is not None):
        parser.error("--person/--garment/--seed apply to --live only")
    if args.expect_sha256 is not None and args.reconcile is None:
        parser.error("--expect-sha256 applies to --reconcile only")
    try:
        config = load_try_on_config(args.config)
    except (ValueError, OSError) as error:
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
