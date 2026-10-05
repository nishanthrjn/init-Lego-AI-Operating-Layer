"""Operator command: smoke, full condition, or comparison. One model per run.

smoke:   frozen 3-call subset; compatibility and latency only, never quality.
live:    the full frozen 91-call R3 plan for one pinned candidate; no early stop.
replay:  harness self-test with oracle-shaped replies (never quality evidence).
compare: no model call; verifies the recorded R3 control and each candidate
         report by identity and SHA-256, then applies the predeclared rule.

smoke/live refuse before any model call unless: the hardware text is real, the
Analyst is exactly R3's 1.0.2, the model is a registered candidate whose digest
equals the committed pin, the tracked tree is clean at the expected branch and
commit, and the read-only Ollama preflight confirms that exact digest. The
output directory must never exist. No routing, fallback, retry or repair.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from analyst_quality1q import cli as cq
from analyst_quality1q import data as q
from analyst_quality1q.data import Case
from analyst_quality1q_r3 import cli as r3cli
from analyst_quality1q_r3 import data as r3data
from forgeai.cli import ReplayModel, ollama_binding, replay_binding
from forgeai_eval.preflight import PreflightError, verify_ollama

from analyst_model_compare1 import data, report
from legoai.runtime.api import ModelBindingConfig

CONTROL_REPORT_SHA256 = (
    "025f4717b2479812823068196f00cdf587ba3fcb40b083ea7ebd23e69dd0d367"
)
LIMITATIONS = [
    "N=3 per held-out case: differences of a few calls are run-to-run variation.",
    "The control is the recorded R3 run, not a fresh paired sample.",
    "Held-out cases are synthetic; results are specific to this workload and host.",
    "A favourable outcome justifies a model condition only; it authorizes no "
    "routing, fallback or integration.",
]


class IdentityError(ValueError):
    """A report is not a verified comparison input."""


def condition(
    mode: str,
    digests: dict[str, str],
    plan: tuple[tuple[Case, int], ...],
    checkout: dict[str, object],
    model: dict[str, object],
    candidate: dict[str, object],
    hardware: str,
) -> dict[str, object]:
    return {
        "schema": report.CONDITION_SCHEMA,
        "mode": mode,
        "git": checkout,
        "analyst": r3cli.analyst(),
        "model": model,
        "candidate": candidate,
        "hardware_class": hardware,
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "fixtures": digests,
        "plan": cq.plan_counts(plan),
        "control_reference": data.read()["control"],
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_control(path: Path) -> dict[str, object]:
    if _sha256(path) != CONTROL_REPORT_SHA256:
        raise IdentityError("control is not the recorded R3 report")
    value = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
    if value["schema"] != "forgeai-analyst-quality-report/3" or value["mode"] != "live":
        raise IdentityError("control report identity mismatch")
    return value


def verify_candidate(value: dict[str, object], digests: dict[str, str]) -> None:
    """Identity and exact re-folding of one full candidate report."""
    if value.get("schema") != report.REPORT_SCHEMA or value.get("mode") != "live":
        raise IdentityError("candidate report schema/mode mismatch")
    cond = cast(dict[str, object], value["condition"])
    pinned = cast(dict[str, object], data.read()["analyst"])
    analyst = cast(dict[str, object], cond["analyst"])
    if (
        analyst["definition_fingerprint"] != pinned["definition_fingerprint"]
        or analyst["parser_identity"] != pinned["parser_identity"]
        or analyst["version"] != pinned["version"]
    ):
        raise IdentityError("candidate was not measured with Analyst 1.0.2")
    if cond["fixtures"] != digests:
        raise IdentityError("candidate workload digests differ from the freeze")
    if cast(dict[str, object], cond["plan"])["total_calls"] != 91:
        raise IdentityError("candidate did not run the full 91-call plan")
    model = cast(dict[str, object], cond["model"])
    if data.pins().get(str(model["name"])) != model["digest"]:
        raise IdentityError("candidate model digest differs from the committed pin")
    records = cast(list[dict[str, object]], value["records"])
    rebuilt = report.build(
        cond,
        records,
        q.thresholds(),
        cast(dict[str, object], data.read()["historical"]),
    )
    if any(rebuilt[k] != value[k] for k in rebuilt if k != "records"):
        raise IdentityError("candidate report does not re-fold from its records")


def run_compare(args: argparse.Namespace, digests: dict[str, str]) -> int:
    control = report.summary(verify_control(args.control))
    inputs: dict[str, object] = {"control": _sha256(args.control)}
    failures: list[str] = []
    candidates = []
    for path in args.candidate or []:
        inputs[str(path.name) + ":" + str(path.parent.name)] = _sha256(path)
        value = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
        try:
            verify_candidate(value, digests)
        except (IdentityError, KeyError) as error:
            failures.append(f"{path.parent.name}: {error}")
            continue
        candidates.append(report.summary(value))
    smokes = []
    for path in args.smoke or []:
        inputs[str(path.name) + ":" + str(path.parent.name)] = _sha256(path)
        value = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
        if value.get("schema") != report.SMOKE_SCHEMA:
            failures.append(f"{path.parent.name}: not a smoke report")
            continue
        smokes.append(value)
    margins = cast(dict[str, float], data.read()["margins"])
    outcome = report.compare(control, candidates, smokes, failures, margins)
    built: dict[str, object] = {
        "schema": report.COMPARISON_SCHEMA,
        "outcome": outcome,
        "models": [control, *candidates],
        "smokes": [
            {
                k: s[k]
                for k in (
                    "calls",
                    "stages",
                    "model_failures",
                    "timing",
                    "projected_full_hours",
                    "fits_host",
                )
            }  # fmt: skip
            for s in smokes
        ],
        "inputs": inputs,
        "limitations": LIMITATIONS,
    }
    args.output.mkdir(parents=True)
    for path in report.write(
        args.output, "comparison", built, report.render_comparison
    ):
        print(f"report: {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analyst-model-compare-1")
    parser.add_argument("mode", choices=("replay", "smoke", "live", "compare"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model")
    parser.add_argument("--model-digest")
    parser.add_argument("--hardware")
    parser.add_argument("--expect-branch")
    parser.add_argument("--expect-commit")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--control", type=Path)
    parser.add_argument("--candidate", type=Path, action="append")
    parser.add_argument("--smoke", type=Path, action="append")
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("output directory already exists; it is never overwritten")
    digests = data.freeze()
    if args.mode == "compare":
        if args.control is None:
            parser.error("compare requires --control")
        try:
            return run_compare(args, digests)
        except (IdentityError, ValueError, OSError) as error:
            parser.error(str(error))
    plan = data.smoke_plan() if args.mode == "smoke" else q.plan()
    if args.mode == "replay":
        checkout = {"head": "replay", "branch": "replay", "tracked_clean": False}
        model: dict[str, object] = {
            "provider": "replay",
            "name": "oracle-shaped replay",
        }
        candidate: dict[str, object] = {"id": "replay", "role": "harness self-test"}
        hardware = "replay"

        def binding(case: Case, repetition: int) -> ModelBindingConfig:
            return replay_binding(ReplayModel(cq.replay_output(case)))

    else:
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
            parser.error(f"{args.mode} mode requires " + ", ".join(missing))
        try:
            hardware = r3cli.require_hardware(args.hardware)
            data.require_live_identity()
            row = data.require_candidate(args.model, args.model_digest)
            checkout = cq.git_state(cq.git, args.expect_branch, args.expect_commit)
            identity = verify_ollama(args.ollama_url, args.model, args.model_digest)
        except ValueError as error:
            parser.error(str(error))
        except (
            r3cli.HardwareError,
            r3data.AnalystIdentityError,
            data.CandidateError,
            PreflightError,
            cq.CheckoutError,
            subprocess.CalledProcessError,
        ) as error:
            print(f"{args.mode} preflight failed: {error}", file=sys.stderr)
            print("no call was made and nothing was written", file=sys.stderr)
            return cq.PREFLIGHT_FAILED
        model = {
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
        candidate = {"id": row["id"], "role": row["role"]}
        live = ollama_binding(args.ollama_url, identity.model_name, cq.TIMEOUT_SECONDS)

        def binding(case: Case, repetition: int) -> ModelBindingConfig:
            return live

    frozen = condition(args.mode, digests, plan, checkout, model, candidate, hardware)
    args.output.mkdir(parents=True)
    (args.output / "condition.json").write_text(
        json.dumps(frozen, indent=2) + "\n", encoding="utf-8"
    )
    # Every planned call runs; nothing stops early on interim results.
    records = r3cli.execute(plan, binding, lambda line: print(line, flush=True))
    if args.mode == "smoke":
        written = report.write(
            args.output, "smoke", report.smoke(frozen, records), report.render_smoke
        )
    else:
        historical = cast(dict[str, object], data.read()["historical"])
        built = report.build(frozen, records, q.thresholds(), historical)
        written = report.write(args.output, "report", built, report.render_model)
    for path in written:
        print(f"report: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
