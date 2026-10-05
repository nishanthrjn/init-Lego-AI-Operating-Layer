"""Operator command: the frozen CONTENT-DISCOVERY-1Q condition, re-run for diagnosis.

Same frozen inputs, plan (91 calls), request path, model condition and
preflight as 1Q. Only the in-memory diagnosis and the report schema differ.
"""

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from analyst_quality1q import cli as cq
from analyst_quality1q import data
from analyst_quality1q.data import Case
from forgeai.cli import ReplayModel, ollama_binding, replay_binding
from forgeai_eval.preflight import PreflightError, verify_ollama

from analyst_contract_diag1 import report
from analyst_contract_diag1.runner import run_call
from legoai.runtime.api import ModelBindingConfig


def condition(
    mode: str,
    digests: dict[str, str],
    checkout: dict[str, object],
    model: dict[str, object],
    hardware: str,
) -> dict[str, object]:
    frozen = cq.condition(mode, digests, data.plan(), checkout, model, hardware)
    return {**frozen, "schema": report.CONDITION_SCHEMA, "linkage": report.LINKAGE}


def execute(
    plan: tuple[tuple[Case, int], ...],
    binding: Callable[[Case, int], ModelBindingConfig],
    progress: Callable[[str], None] = lambda _: None,
) -> list[dict[str, object]]:
    records = []
    for index, (case, repetition) in enumerate(plan, 1):
        record = run_call(case, repetition, binding(case, repetition))
        records.append(record)
        progress(f"[{index}/{len(plan)}] {case.id} rep {repetition}: {record['stage']}")
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analyst-contract-diag-1")
    parser.add_argument("mode", choices=("replay", "live"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model")
    parser.add_argument("--model-digest")
    parser.add_argument("--hardware")
    parser.add_argument("--expect-branch")
    parser.add_argument("--expect-commit")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--replay-output", help="replay mode: one reply for every call")
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("output directory already exists; it is never overwritten")
    digests = data.freeze()
    plan = data.plan()
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
            checkout = cq.git_state(cq.git, args.expect_branch, args.expect_commit)
            identity = verify_ollama(args.ollama_url, args.model, args.model_digest)
        except ValueError as error:
            parser.error(str(error))
        except (
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

        hardware = str(args.hardware)
    else:
        checkout = {"head": "replay", "branch": "replay", "tracked_clean": False}
        model = {"provider": "replay", "name": "scripted replay"}
        fixed = args.replay_output

        def binding(case: Case, repetition: int) -> ModelBindingConfig:
            output = fixed if fixed is not None else cq.replay_output(case)
            return replay_binding(ReplayModel(output))

        hardware = args.hardware or "replay"
    frozen = condition(args.mode, digests, checkout, model, hardware)
    args.output.mkdir(parents=True)
    (args.output / "condition.json").write_text(
        json.dumps(frozen, indent=2) + "\n", encoding="utf-8"
    )
    records = execute(plan, binding, lambda line: print(line, flush=True))
    for path in report.write(report.build(frozen, records), args.output):
        print(f"report: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
