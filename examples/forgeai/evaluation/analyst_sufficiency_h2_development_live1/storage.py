"""Exclusive, immutable development-run custody. Parsed records only.

Reuses LIVE-1's exclusive fsynced write and lifecycle invariants unchanged.
A fresh directory per run: no resume, overwrite or replay.
"""

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from analyst_design_live1.lifecycle import validate_partition
from analyst_design_live1.storage import Store as Live1Store

from analyst_sufficiency_h2_development_live1.comparison import LABELS
from analyst_sufficiency_h2_development_live1.identity import (
    CALL_CEILING,
    CONDITION,
    EVALUATION,
    REPORT,
)

MODES = ("PREFLIGHT", "DEVELOPMENT", "OFFLINE_REPLAY")
RAW_FIELDS = frozenset(
    {"user_payload", "payload", "prompt", "raw", "response", "text", "content"}
)
REQUIRED = (
    "report_identity",
    "condition",
    "evaluation_condition",
    "run_id",
    "mode",
    "approval_reference",
    "provenance",
    "git_head",
    "clean_tracked_tree",
    "membership",
    "call_ceiling",
    "call_seconds",
    "total_seconds",
    "calls",
    "planned",
    "attempted",
    "completed",
    "execution_lifecycle",
    "records",
    "raw_metrics",
    "raw_dimensions",
    "guarded",
    "guarded_metrics",
    "comparator",
    "per_case_delta",
    "development_decision",
    "safety_decision",
    "h3_status",
    "invalid_outputs",
    "operational_failures",
    "timings",
    "elapsed_seconds",
    "in_flight_disposition",
    "stop_reason",
    "run_completeness",
    "blended_score",
    "interpretation",
)
INTERPRETATION = (
    "Development measurement only. The H2 decision compares raw Agent 1.1.0 with "
    "the historical raw Agent 1.0.0 baseline under rules frozen before execution; "
    "H1 enforcement is reported separately and is never H2 model improvement. "
    "Not a safety qualification, not a SAFETY-EVAL-3 result, not live "
    "qualification of Agent 1.1.0, and not evidence of production readiness."
)


def _no_raw(value: object) -> None:
    if isinstance(value, dict):
        if set(value) & RAW_FIELDS:
            raise ValueError("raw payload/response persistence prohibited")
        for item in value.values():
            _no_raw(item)
    elif isinstance(value, list):
        for item in value:
            _no_raw(item)


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

    def write(self, name: str, value: dict[str, Any]) -> None:
        _no_raw(value)
        super().write(name, value)

    def observe(self, value: dict[str, Any]) -> None:
        self.serial += 1
        self.write(f"observation-{self.serial:04}.json", value)

    def finish(self, report: dict[str, Any]) -> None:
        report["run_id"] = self.run_id
        validate(report)
        self.write("report.json", report)
        with (self.path / "report.md").open("x", encoding="utf-8") as file:
            summary = {
                k: report[k]
                for k in (
                    "mode",
                    "run_completeness",
                    "stop_reason",
                    "calls",
                    "development_decision",
                    "raw_dimensions",
                    "guarded_metrics",
                    "h3_status",
                )
            }
            file.write(
                "# H2 development live measurement (Agent 1.1.0 + H1)\n\n"
                + INTERPRETATION
                + "\n\n```json\n"
                + json.dumps(summary, indent=2, ensure_ascii=False)
                + "\n```\n"
            )


def validate(report: dict[str, Any]) -> None:
    missing = set(REQUIRED) - set(report)
    if missing:
        raise ValueError("missing report fields: " + repr(sorted(missing)))
    if (
        report["report_identity"] != REPORT
        or report["condition"] != CONDITION
        or report["evaluation_condition"] != EVALUATION
        or report["mode"] not in MODES
    ):
        raise ValueError("report identity/mode")
    if not str(report["approval_reference"]).strip():
        raise ValueError("approval reference required")
    if report["blended_score"] != "NOT_PRODUCED":
        raise ValueError("no blended score")
    if report["safety_decision"] != "NOT_PRODUCED":
        raise ValueError("a development run never produces a safety decision")
    if report["run_completeness"] not in {"COMPLETE", "INCOMPLETE"}:
        raise ValueError("run completeness")
    label = report["development_decision"]["label"]
    if label is not None and label not in LABELS:
        raise ValueError("development decision label")
    if report["run_completeness"] == "INCOMPLETE" and label not in {None, LABELS[4]}:
        raise ValueError("an incomplete run decides only measurement invalidity")
    if report["mode"] == "PREFLIGHT" and (report["calls"] or label is not None):
        raise ValueError("preflight makes no semantic call and no decision")
    if report["calls"] > min(report["call_ceiling"], CALL_CEILING):
        raise ValueError("call ceiling exceeded")
    if report["h3_status"] not in {"ABSENT", "VIOLATED", "NOT_OBSERVED"}:
        raise ValueError("h3 status")
    provenance = report["provenance"]
    if provenance.get("preflight_verified", True) and (
        provenance.get("condition") != CONDITION
        or provenance.get("agent_version") != "1.1.0"
        or provenance.get("credentials") != "NONE"
        or provenance.get("response_format") is not None
    ):
        raise ValueError("development provenance required")
    lifecycle = report["execution_lifecycle"]
    if lifecycle:
        validate_partition(lifecycle)
        if (
            report["calls"] != lifecycle["attempted"]
            or report["attempted"] != lifecycle["attempted"]
            or report["completed"] != lifecycle["completed"]
            or report["planned"] != lifecycle["planned"]
        ):
            raise ValueError("lifecycle call count")
    _no_raw(report)
