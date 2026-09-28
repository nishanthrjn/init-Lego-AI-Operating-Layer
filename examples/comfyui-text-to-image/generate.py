# ruff: noqa: E402
"""Explicit operator live helper. Never starts or modifies ComfyUI."""

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

from legoai_generative_media.comfyui import (
    HARD_MAX_WAIT_SECONDS,
    ComfyUIConfig,
    CompletionPolicy,
    LocalComfyUIAdapter,
)
from legoai_generative_media.composition import invoke
from legoai_generative_media.http import Endpoint
from legoai_generative_media.local_host import prepare_local
from legoai_generative_media.values import (
    ApprovedWorkflowRef,
    GeneratedImage,
    GenerationCancelled,
    ProviderJobRef,
    TextToImageRequest,
)
from legoai_generative_media.workflow import ApprovedWorkflow, template


def save(image: GeneratedImage, output: Path | None) -> None:
    if output is not None:
        # Explicit output only; exclusive creation prevents overwriting another result.
        with output.open("xb") as destination:
            destination.write(image.content)
    print("PNG bytes:", image.byte_length, "SHA-256:", image.sha256)


def adapter_for(args: argparse.Namespace) -> LocalComfyUIAdapter:
    workflow = ApprovedWorkflow.load(
        args.workflow,
        ApprovedWorkflowRef("local-txt2img", "1", args.sha256),
        args.checkpoint,
    )
    # Operator/runtime setting only; the application request never carries it.
    policy = CompletionPolicy.for_wait(args.timeout)
    return LocalComfyUIAdapter(
        ComfyUIConfig(workflow, Endpoint(args.endpoint), completion=policy)
    )


async def reconcile(args: argparse.Namespace) -> int:
    adapter = adapter_for(args)
    job = ProviderJobRef("comfyui", adapter.config.binding, args.reconcile)
    print("mode: reconcile existing job (read-only)")
    result = await adapter.reconcile(job)
    # Structural: reconcile uses a GET-only transport that refuses any POST.
    print("submission performed: NO")
    print("job:", job.job_id)
    print("status:", result.status.value.upper(), "effect:", result.effect.value)
    if result.error is not None:
        print("category:", result.error.value)
    if result.image is None:
        return 1
    save(result.image, args.output)
    return 0


async def run(args: argparse.Namespace) -> int:
    adapter = adapter_for(args)
    workflow = adapter.config.workflow
    policy = adapter.config.completion
    # All operator-controlled settings participate in the immutable association.
    digest = hashlib.sha256(
        json.dumps(
            {
                "workflow": workflow.reference.sha256,
                "checkpoint": args.checkpoint,
                "endpoint": args.endpoint,
                "max_wait": policy.max_wait_seconds,
                "poll_interval": policy.poll_interval_seconds,
                "request_timeout": policy.request_timeout_seconds,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    session = await prepare_local(
        adapter, digest, approved=workflow.reference, timeout=policy.max_wait_seconds
    )
    print("completion policy: max wait", policy.max_wait_seconds, "s")
    task = asyncio.create_task(
        invoke(
            session.coordinator,
            session.ready,
            session.context,
            session.contribution,
            session.contribution.revision,
            TextToImageRequest(args.prompt, args.seed),
        )
    )
    timer = None
    if args.cancel_after is not None:
        timer = asyncio.get_running_loop().call_later(args.cancel_after, task.cancel)
    try:
        _, result = await task
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
        if result.job is not None:
            print(
                "Reconcile later without resubmitting: --reconcile", result.job.job_id
            )
        return 1
    save(result.image, args.output)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--checkpoint",
        required=True,
        help="Operator-selected installed basename; never downloaded",
    )
    parser.add_argument("--workflow", required=True, type=Path)
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
        help=f"Total completion wait in seconds (max {HARD_MAX_WAIT_SECONDS})",
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
        content = json.dumps(template(args.checkpoint), indent=2).encode() + b"\n"
        with args.workflow.open("xb") as destination:
            destination.write(content)
        print(
            "Review template before approving. SHA-256:",
            hashlib.sha256(content).hexdigest(),
        )
        return 0
    if not args.sha256:
        parser.error("--sha256 is required")
    if args.output is not None and args.output.exists():
        parser.error("output already exists")
    if not 0 < args.timeout <= HARD_MAX_WAIT_SECONDS:
        parser.error(f"timeout must be in (0,{HARD_MAX_WAIT_SECONDS}]")
    if args.reconcile is not None:
        if args.prompt is not None or args.seed is not None or args.cancel_after:
            parser.error("--reconcile takes no --prompt, --seed or --cancel-after")
        operation = reconcile
    else:
        if not args.prompt or args.output is None:
            parser.error("--prompt and --output are required for generation")
        if args.cancel_after is not None and not (
            0 < args.cancel_after <= HARD_MAX_WAIT_SECONDS
        ):
            parser.error(f"cancel-after must be in (0,{HARD_MAX_WAIT_SECONDS}]")
        operation = run
    try:
        return asyncio.run(operation(args))
    except ValueError, OSError, TypeError:
        print(
            "Local configuration/output failure; no automatic retry. Check approved settings."
        )
        if args.reconcile is not None:
            print("submission performed: NO")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
