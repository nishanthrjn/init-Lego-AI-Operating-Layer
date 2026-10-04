"""Operator command: condition first, measurement second, interpretation third.

Live mode refuses to start unless every frozen input verifies, the tracked tree
is clean, the branch and commit equal the operator's expectation, the output
directory does not exist and the read-only LQ1.1 preflight confirms the exact
model digest. It then writes `condition.json` before the first model call.
No retry, fallback, prompt change or partial report.
"""

import argparse
import json
import platform
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from forgeai.cli import ReplayModel, ollama_binding, replay_binding
from forgeai_eval.preflight import PreflightError, verify_ollama

from analyst_quality1q import data, report
from analyst_quality1q.data import Case
from analyst_quality1q.harness import run_call
from analyst_quality1q.metrics import score
from legoai.runtime.api import ModelBindingConfig

TIMEOUT_SECONDS = 600.0
PREFLIGHT_FAILED = 3
GitRunner = Callable[[list[str]], str]


class CheckoutError(RuntimeError):
    """The evaluated checkout is not the expected clean commit."""


def git(arguments: list[str]) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=data.ROOT,
        capture_output=True,
        encoding="utf-8",
        check=True,
    ).stdout.strip()


def git_state(run: GitRunner, branch: str, commit: str) -> dict[str, object]:
    """Exact identity of the evaluated checkout; refuses any mismatch."""
    head = run(["rev-parse", "HEAD"])
    current = run(["branch", "--show-current"])
    dirty = run(["status", "--porcelain", "--untracked-files=no"])
    if dirty:
        raise CheckoutError("tracked working tree is not clean")
    if current != branch:
        raise CheckoutError(f"branch is {current!r}, expected {branch!r}")
    if head != commit:
        raise CheckoutError("HEAD does not equal --expect-commit")
    return {"head": head, "branch": current, "tracked_clean": True}


def plan_counts(plan: tuple[tuple[Case, int], ...]) -> dict[str, int]:
    counts: dict[str, int] = {"total_calls": len(plan)}
    for case, _ in plan:
        counts[case.partition + "_calls"] = counts.get(case.partition + "_calls", 0) + 1
    counts["heldout_cases"] = len({c.id for c, _ in plan if c.partition == "heldout"})
    counts["heldout_repetitions"] = data.HELDOUT_REPETITIONS
    counts["cd1_repetitions"] = data.CD1_REPETITIONS
    return dict(sorted(counts.items()))


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
        "analyst": {
            "agent_id": "repository-analyst",
            "version": "1.0.0",
            "definition_fingerprint": data.definition_fingerprint(),
        },
        "model": model,
        "hardware_class": hardware,
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "fixtures": digests,
        "plan": plan_counts(plan),
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def replay_output(case: Case) -> str:
    """Oracle-shaped replay for harness self-tests only (never quality evidence)."""
    o = case.oracle
    answered = o.expected == "succeeded"
    relevant = sorted(sorted(o.acceptable, key=len)[0] | o.context) if answered else []
    return json.dumps(
        {
            "status": o.expected,
            "summary": "Replay output for harness qualification only.",
            "relevant_files": relevant,
            "findings": [],
            "risks": [],
            "unknowns": [] if answered else ["The supplied files do not decide this."],
        }
    )


def execute(
    plan: tuple[tuple[Case, int], ...],
    binding: Callable[[Case, int], ModelBindingConfig],
    progress: Callable[[str], None] = lambda _: None,
) -> list[dict[str, object]]:
    records = []
    for index, (case, repetition) in enumerate(plan, 1):
        call = run_call(case, binding(case, repetition))
        records.append(score(case, repetition, call))
        progress(
            f"[{index}/{len(plan)}] {case.id} rep {repetition}: {call.category.value}"
        )
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analyst-quality-1q")
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
            checkout = git_state(git, args.expect_branch, args.expect_commit)
            identity = verify_ollama(args.ollama_url, args.model, args.model_digest)
        except ValueError as error:
            parser.error(str(error))
        except (PreflightError, CheckoutError, subprocess.CalledProcessError) as error:
            print(f"live preflight failed: {error}", file=sys.stderr)
            print("no call was made and nothing was written", file=sys.stderr)
            return PREFLIGHT_FAILED
        model: dict[str, object] = {
            "provider": "ollama",
            "name": identity.model_name,
            "digest": identity.model_digest,
            "ollama_version": identity.ollama_version,
            "timeout_seconds": TIMEOUT_SECONDS,
            "decoding": "provider defaults; LegoAI sends no sampling options (unobserved)",
            "context_window": "provider default (unobserved)",
            "fallback": "none",
            "retries": "none",
        }
        live = ollama_binding(args.ollama_url, identity.model_name, TIMEOUT_SECONDS)

        def binding(case: Case, repetition: int) -> ModelBindingConfig:
            return live

        hardware = str(args.hardware)
    else:
        checkout = {"head": "replay", "branch": "replay", "tracked_clean": False}
        model = {"provider": "replay", "name": "oracle-shaped replay"}

        def binding(case: Case, repetition: int) -> ModelBindingConfig:
            return replay_binding(ReplayModel(replay_output(case)))

        hardware = args.hardware or "replay"
    frozen = condition(args.mode, digests, plan, checkout, model, hardware)
    args.output.mkdir(parents=True)
    (args.output / "condition.json").write_text(
        json.dumps(frozen, indent=2) + "\n", encoding="utf-8"
    )
    records = execute(plan, binding, lambda line: print(line, flush=True))
    paths = report.write(report.build(frozen, records, data.thresholds()), args.output)
    for path in paths:
        print(f"report: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
