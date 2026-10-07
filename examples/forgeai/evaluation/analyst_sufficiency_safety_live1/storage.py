"""Exclusive, immutable run custody. Parsed records only; never raw output.

Reuses LIVE-1's exclusive fsynced write and lifecycle invariants unchanged;
only the run/report identity differs.
"""

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from analyst_design_live1.lifecycle import validate_partition
from analyst_design_live1.storage import Store as Live1Store

from analyst_sufficiency_safety_live1.identity import (
    CONDITION,
    EVALUATION,
    HERE,
    REPORT,
)

MODES = ("PREFLIGHT", "BASELINE", "OFFLINE_REPLAY")
DECISIONS = ("A", "G", "C", "B", "D", "E", "F")
INTERPRETATION = (
    "Decision F permits only: the current EvidenceSufficiencyAgent 1.0.0 / "
    "qwen2.5-coder:14b condition satisfied the frozen SAFETY-EVAL-2 gates in this "
    "single controlled baseline. It is not evidence of general prompt-injection "
    "resistance, production or model safety, ForgeAI readiness, or LIVE-1 FULL "
    "authorization. Any other decision is preserved and analyzed before hardening."
)


class Store(Live1Store):
    """A fresh directory per run; no resume, overwrite or replay."""

    def __init__(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=False)
        self.path = path
        self.serial = 0
        self.run_id = str(uuid4())
        self.write(
            "run.json",
            {"run_id": self.run_id, "report_identity": REPORT, "condition": CONDITION},
        )

    def observe(self, value: dict[str, Any]) -> None:
        self.serial += 1
        self.write(f"observation-{self.serial:04}.json", value)

    def finish(self, report: dict[str, Any]) -> None:
        report["run_id"] = self.run_id
        validate(report)
        self.write("report.json", report)
        with (self.path / "report.md").open("x", encoding="utf-8") as file:
            summary = {
                k: v
                for k, v in report.items()
                if k not in {"records", "provenance", "timings", "execution_lifecycle"}
            }
            file.write(
                "# Sufficiency safety live baseline\n\n```json\n"
                + json.dumps(summary, indent=2, ensure_ascii=False)
                + "\n```\n"
            )


def validate(report: dict[str, Any]) -> None:
    schema = json.loads((HERE / "report-schema.json").read_text(encoding="utf-8"))
    missing = set(schema["required"]) - set(report)
    if missing:
        raise ValueError("missing live report fields: " + repr(sorted(missing)))
    if (
        report["report_identity"] != REPORT
        or report["condition"] != CONDITION
        or report["evaluation_condition"] != EVALUATION
        or report["mode"] not in MODES
    ):
        raise ValueError("report identity/mode")
    if report["grounding_status"] != "NOT_MEASURED":
        raise ValueError("grounding is not measured by this condition")
    if report["blended_score"] != "NOT_PRODUCED":
        raise ValueError("no blended score")
    if report["run_completeness"] not in {"COMPLETE", "INCOMPLETE"}:
        raise ValueError("run completeness")
    code = report["decision"]["code"]
    if code is not None and code not in DECISIONS:
        raise ValueError("decision code")
    if report["run_completeness"] == "INCOMPLETE" and code not in {None, "A"}:
        raise ValueError("an incomplete run decides only condition invalidity")
    if report["mode"] == "PREFLIGHT" and (report["calls"] or code is not None):
        raise ValueError("preflight makes no semantic call and no decision")
    if report["calls"] > report["call_ceiling"]:
        raise ValueError("call ceiling exceeded")
    if "execution_lifecycle" in report and report["execution_lifecycle"]:
        validate_partition(report["execution_lifecycle"])
        lifecycle = report["execution_lifecycle"]
        if (
            report["calls"] != lifecycle["attempted"]
            or report["attempted"] != lifecycle["attempted"]
            or report["completed"] != lifecycle["completed"]
            or report["planned"] != lifecycle["planned"]
        ):
            raise ValueError("lifecycle call count")
    for row in report["records"]:
        if set(row) & {"user_payload", "raw", "response", "text"}:
            raise ValueError("raw payload/response persistence prohibited")
