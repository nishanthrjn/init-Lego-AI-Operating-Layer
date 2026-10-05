"""Operator command: recorded fold, replay, or the same-condition live diagnostic.

recorded: folds the immutable r2 report (verified by SHA-256); no model call,
          and no clause split, because r2 never recorded the counts.
live:     the exact r2 preflight (Analyst 1.0.1 identity, preregistered model
          and digest, clean checkout at the expected branch/commit, LQ1.1
          Ollama preflight), refusing before any call. condition.json is
          written before the first call. No retry, fallback or partial report.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from analyst_quality1q import cli as cq
from analyst_quality1q import data as q
from analyst_quality1q.data import Case
from analyst_quality1q_r2 import cli as r2cli
from analyst_quality1q_r2 import data as r2
from forgeai.cli import ReplayModel, ollama_binding, replay_binding
from forgeai_eval.preflight import PreflightError, verify_ollama

from analyst_insufficient_diag1 import report
from analyst_insufficient_diag1.runner import run_call
from legoai.runtime.api import ModelBindingConfig

PREDECLARATION = "planning/FORGEAI-ANALYST-INSUFFICIENT-DIAGNOSTIC.md"
MARKER = "<!-- END INSUFFICIENT-DIAG-1 PREDECLARATION -->"
PREDECLARATION_DIGEST = (
    "82679c17daacb23bf960f1a7442e76488584c147c597d2cedf7234d05c992c98"
)


class RecordedReportError(ValueError):
    """The supplied r2 report is not the immutable recorded r2 report."""


def predeclaration_digest() -> str:
    doc = (q.ROOT / PREDECLARATION).read_text(encoding="utf-8-sig")
    prefix, found, _ = doc.partition(MARKER)
    if not found:
        raise ValueError("diagnostic predeclaration marker missing")
    return hashlib.sha256((prefix + MARKER + "\n").encode()).hexdigest()


def freeze() -> dict[str, str]:
    digests = r2.freeze()
    if predeclaration_digest() != PREDECLARATION_DIGEST:
        raise ValueError("diagnostic predeclaration changed after freeze")
    return {**digests, "diagnostic_predeclaration": PREDECLARATION_DIGEST}


def recorded_records(path: Path) -> list[dict[str, object]]:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != report.LINKAGE["r2_report_sha256"]:
        raise RecordedReportError("not the recorded CONTENT-DISCOVERY-1Q-R2 report")
    value = json.loads(raw.decode("utf-8"))
    if (
        value["schema"] != "forgeai-analyst-quality-report/2"
        or value["mode"] != "live"
        or value["condition_digest"] != report.LINKAGE["r2_condition_digest"]
    ):
        raise RecordedReportError("r2 report identity mismatch")
    return [report.from_r2(r) for r in value["records"]]


def condition(
    mode: str,
    digests: dict[str, str],
    checkout: dict[str, object],
    model: dict[str, object],
    hardware: str,
) -> dict[str, object]:
    return {
        "schema": report.CONDITION_SCHEMA,
        "mode": mode,
        "git": checkout,
        "analyst": r2cli.analyst(),
        "model": model,
        "hardware_class": hardware,
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "fixtures": digests,
        "plan": cq.plan_counts(q.plan()),
        "linkage": report.LINKAGE,
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
            f"[{index}/{len(plan)}] {case.id} rep {repetition}: {record['stage']}"
            f" / {record['refined'] or record['abstention']}"
        )
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analyst-insufficient-diag-1")
    parser.add_argument("mode", choices=("recorded", "replay", "live"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--r2-report", type=Path)
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
    digests = freeze()
    plan = q.plan()
    if args.mode == "recorded":
        if args.r2_report is None:
            parser.error("recorded mode requires --r2-report")
        try:
            records = recorded_records(args.r2_report)
        except (OSError, RecordedReportError) as error:
            parser.error(str(error))
        frozen = condition(
            "recorded",
            digests,
            {"head": "recorded", "branch": "recorded", "tracked_clean": False},
            {"provider": "recorded", "name": "CONTENT-DISCOVERY-1Q-R2 live records"},
            "recorded",
        )
        args.output.mkdir(parents=True)
        (args.output / "condition.json").write_text(
            json.dumps(frozen, indent=2) + "\n", encoding="utf-8"
        )
        for path in report.write(report.build(frozen, records), args.output):
            print(f"report: {path}")
        return 0
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
            r2.require_live_identity()
            r2cli.require_model(args.model, args.model_digest)
            checkout = cq.git_state(cq.git, args.expect_branch, args.expect_commit)
            identity = verify_ollama(args.ollama_url, args.model, args.model_digest)
        except ValueError as error:
            parser.error(str(error))
        except (
            r2.AnalystIdentityError,
            r2cli.ModelConditionError,
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
