"""Operator command: condition first, measurement second, interpretation third.

Live mode refuses before any model call unless every frozen 1Q and R3 input
verifies, the Analyst is exactly the preregistered 1.0.2 identity (version,
fingerprint, sources, parser identity, ancestor commit), the hardware text is a
real description, the model name and digest equal the preregistration, the
tracked tree is clean at the expected branch/commit, and the read-only LQ1.1
preflight confirms the exact model digest. The output directory must not exist;
condition.json is written before the first call. No retry, fallback, prompt
change or partial report.
"""

import argparse
import json
import platform
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from analyst_quality1q import cli as cq
from analyst_quality1q import data as q
from analyst_quality1q.data import Case
from forgeai.cli import ReplayModel, ollama_binding, replay_binding
from forgeai_eval.preflight import PreflightError, verify_ollama

from analyst_quality1q_r3 import data, report
from analyst_quality1q_r3.runner import run_call
from legoai.runtime.api import ModelBindingConfig

PLACEHOLDERS = (
    "placeholder",
    "tbd",
    "todo",
    "unknown",
    "n/a",
    "same hardware class",
    "hardware description",
    "replay",
)


class ModelConditionError(RuntimeError):
    """The requested model is not the preregistered model condition."""


class HardwareError(RuntimeError):
    """The hardware text is blank or an obvious placeholder."""


def require_model(name: str, digest: str) -> None:
    model = cast(dict[str, object], data.read()["model_condition"])
    if name != model["name"] or digest != model["digest"]:
        raise ModelConditionError("model name/digest differs from the preregistration")


def require_hardware(text: str) -> str:
    value = " ".join(text.split())
    folded = value.casefold()
    if (
        len(value) < 3
        or "<" in value
        or ">" in value
        or any(p in folded for p in PLACEHOLDERS)
    ):
        raise HardwareError("hardware must be a real description, not a placeholder")
    return value


def analyst() -> dict[str, object]:
    pinned = cast(dict[str, object], data.read()["analyst"])
    return {
        "agent_id": "repository-analyst",
        "version": q.analyst_version(),
        "definition_fingerprint": q.definition_fingerprint(),
        "implementation_commit": pinned["implementation_commit"],
        "parser_identity": pinned["parser_identity"],
    }


def condition(
    mode: str,
    digests: dict[str, str],
    plan: tuple[tuple[Case, int], ...],
    checkout: dict[str, object],
    model: dict[str, object],
    hardware: str,
) -> dict[str, object]:
    return {
        "schema": report.CONDITION_SCHEMA,
        "mode": mode,
        "git": checkout,
        "analyst": analyst(),
        "model": model,
        "hardware_class": hardware,
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "fixtures": digests,
        "plan": cq.plan_counts(plan),
        "historical_reference": data.read()["historical"],
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def execute(
    plan: tuple[tuple[Case, int], ...],
    binding: Callable[[Case, int], ModelBindingConfig],
    progress: Callable[[str], None] = lambda _: None,
) -> list[dict[str, object]]:
    records = []
    for index, (case, repetition) in enumerate(plan, 1):
        record = run_call(case, repetition, binding(case, repetition))
        records.append(record)
        progress(
            f"[{index}/{len(plan)}] {case.id} rep {repetition}: "
            f"{record['category']} / {record['abstention']}"
        )
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analyst-quality-1q-r3")
    parser.add_argument("mode", choices=("replay", "live"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model")
    parser.add_argument("--model-digest")
    parser.add_argument("--hardware")
    parser.add_argument("--expect-branch")
    parser.add_argument("--expect-commit")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("output directory already exists; it is never overwritten")
    digests = data.freeze()
    plan = q.plan()
    if args.mode == "live":
        missing = [
            flag
            for flag, value in (
                ("--model", args.model),
                ("--model-digest", args.model_digest),
                ("--hardware", args.hardware),
                ("--expect-branch", args.expect_branch),
                ("--expect-commit", args.expect_commit),
            )
            if not value
        ]
        if missing:
            parser.error("live mode requires " + ", ".join(missing))
        try:
            hardware = require_hardware(args.hardware)
            data.require_live_identity()
            require_model(args.model, args.model_digest)
            checkout = cq.git_state(cq.git, args.expect_branch, args.expect_commit)
            identity = verify_ollama(args.ollama_url, args.model, args.model_digest)
        except ValueError as error:
            parser.error(str(error))
        except (
            HardwareError,
            data.AnalystIdentityError,
            ModelConditionError,
            PreflightError,
            cq.CheckoutError,
            subprocess.CalledProcessError,
        ) as error:
            print(f"live preflight failed: {error}", file=sys.stderr)
            print("no call was made and nothing was written", file=sys.stderr)
            return cq.PREFLIGHT_FAILED
        model: dict[str, object] = {
            "provider": "ollama",
            "name": identity.model_name,
            "digest": identity.model_digest,
            "ollama_version": identity.ollama_version,
            "timeout_seconds": cq.TIMEOUT_SECONDS,
            "decoding": "provider defaults; LegoAI sends no sampling options (unobserved)",
            "context_window": "provider default (unobserved)",
            "fallback": "none",
            "retries": "none",
        }
        live = ollama_binding(args.ollama_url, identity.model_name, cq.TIMEOUT_SECONDS)

        def binding(case: Case, repetition: int) -> ModelBindingConfig:
            return live

    else:
        checkout = {"head": "replay", "branch": "replay", "tracked_clean": False}
        model = {"provider": "replay", "name": "oracle-shaped replay"}

        def binding(case: Case, repetition: int) -> ModelBindingConfig:
            return replay_binding(ReplayModel(cq.replay_output(case)))

        hardware = "replay"
    frozen = condition(args.mode, digests, plan, checkout, model, hardware)
    args.output.mkdir(parents=True)
    (args.output / "condition.json").write_text(
        json.dumps(frozen, indent=2) + "\n", encoding="utf-8"
    )
    records = execute(plan, binding, lambda line: print(line, flush=True))
    historical = cast(dict[str, object], data.read()["historical"])
    built = report.build(frozen, records, q.thresholds(), historical)
    for path in report.write(built, args.output):
        print(f"report: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
