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

from legoai_generative_media.comfyui import ComfyUIConfig, LocalComfyUIAdapter
from legoai_generative_media.composition import invoke
from legoai_generative_media.http import Endpoint
from legoai_generative_media.local_host import prepare_local
from legoai_generative_media.values import (
    ApprovedWorkflowRef,
    GenerationCancelled,
    TextToImageRequest,
)
from legoai_generative_media.workflow import ApprovedWorkflow, template


async def run(args: argparse.Namespace) -> int:
    workflow = ApprovedWorkflow.load(
        args.workflow,
        ApprovedWorkflowRef("local-txt2img", "1", args.sha256),
        args.checkpoint,
    )
    config = ComfyUIConfig(
        workflow, Endpoint(args.endpoint), timeout_seconds=args.timeout
    )
    adapter = LocalComfyUIAdapter(config)
    # All operator-controlled settings participate in the immutable association.
    digest = hashlib.sha256(
        json.dumps(
            {
                "workflow": workflow.reference.sha256,
                "checkpoint": args.checkpoint,
                "endpoint": args.endpoint,
                "timeout": args.timeout,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    session = await prepare_local(
        adapter, digest, approved=workflow.reference, timeout=args.timeout
    )
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
        return 1
    # Explicit output only; exclusive creation prevents overwriting another result.
    with args.output.open("xb") as destination:
        destination.write(result.image.content)
    print("PNG bytes:", result.image.byte_length, "SHA-256:", result.image.sha256)
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
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cancel-after", type=float)
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
    if not args.sha256 or not args.prompt or args.output is None:
        parser.error("--sha256, --prompt and --output are required for generation")
    if args.output.exists():
        parser.error("output already exists")
    if args.cancel_after is not None and not 0 < args.cancel_after <= 300:
        parser.error("cancel-after must be in (0,300]")
    try:
        return asyncio.run(run(args))
    except ValueError, OSError, TypeError:
        print(
            "Local configuration/output failure; no automatic retry. Check approved settings."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
