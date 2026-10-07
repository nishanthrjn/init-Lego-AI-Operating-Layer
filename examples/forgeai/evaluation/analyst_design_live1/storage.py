"""Exclusive run custody. Parsed observations only; never raw model output."""

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from analyst_design_eval2.report import decode, record
from analyst_design_eval2.runner import Row

from analyst_design_live1.identity import HERE, PROFILE, REPORT, SMOKE
from analyst_design_live1.lifecycle import validate_partition
from analyst_design_live1.measurement import interpret


def parsed(row: Row) -> dict[str, Any]:
    result = record(row)
    result.pop("grounding")
    return result


class Store:
    def __init__(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=False)
        self.path = path
        self.serial = 0
        self.run_id = str(uuid4())
        self.write("run.json", {"run_id": self.run_id, "report_identity": REPORT})

    def write(self, name: str, value: dict[str, Any]) -> None:
        with (self.path / name).open("x", encoding="utf-8") as file:
            json.dump(value, file, indent=2, ensure_ascii=False)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

    def checkpoint(self, row: Row) -> None:
        self.serial += 1
        self.write(f"observation-{self.serial:04}.json", parsed(row))

    def finish(self, report: dict[str, Any]) -> None:
        report.update(
            {
                "run_id": self.run_id,
                "sufficiency_profile_identity": PROFILE,
                "revision_2_condition_identity": "forgeai-analyst-design-eval/2",
            }
        )
        defaults: dict[str, Any] = {
            "records": [],
            "planned_slots": [],
            "timings": [],
            "smoke_status": None,
            "stop_reason": None,
            "in_flight_disposition": "NOT_STARTED",
            "approval_reference": None,
        }
        for key, value in defaults.items():
            report.setdefault(key, value)
        validate(report)
        self.write("report.json", report)
        with (self.path / "report.md").open("x", encoding="utf-8") as file:
            summary = {
                k: v for k, v in report.items() if k not in {"records", "provenance"}
            }
            file.write(
                "# Sufficiency-only live profile\n\n```json\n"
                + json.dumps(summary, indent=2)
                + "\n```\n"
            )


def validate(report: dict[str, Any]) -> None:
    # Additive LIVE-1 custody fields; historical reports remain readable.
    if "execution_lifecycle" in report:
        validate_partition(report["execution_lifecycle"])
        if report["calls"] != report["execution_lifecycle"]["attempted"]:
            raise ValueError("lifecycle call count")
    schema = json.loads((HERE / "report-schema.json").read_text())
    if not set(schema["required"]) <= set(report):
        raise ValueError("missing live report fields")
    if report["report_identity"] != REPORT or report["mode"] not in {
        "PREFLIGHT",
        "SMOKE",
        "FULL",
    }:
        raise ValueError("report identity/mode")
    if (
        report["grounding_status"] != "NOT_MEASURED"
        or report["final_answer_grounding"] != "NOT_MEASURED"
        or report["revision_2_aggregate_verdict"] != "NOT_APPLICABLE"
    ):
        raise ValueError("unmeasured/aggregate boundary")
    allowed = {
        "UNSAFE",
        "RUNTIME_FAILED",
        "CONTRACT_FAILED",
        "INCOMPLETE",
        "USEFULNESS_FAILED",
        "SUPPORTED",
    }
    if report["sufficiency_profile_outcome"] not in {
        "SUFFICIENCY_PROFILE_" + x for x in allowed
    }:
        raise ValueError("profile outcome")
    if report["mode"] != "FULL" and report["sufficiency_profile_outcome"].endswith(
        "SUPPORTED"
    ):
        raise ValueError("smoke/preflight cannot support full profile")
    if report["run_completeness"] not in {"COMPLETE", "INCOMPLETE"}:
        raise ValueError("run completeness")
    if any("grounding" in row for row in report["records"]):
        raise ValueError("numeric grounding prohibited")


def verify_smoke(report: dict[str, Any], provenance: dict[str, Any]) -> None:
    validate(report)
    if (
        report["mode"] != "SMOKE"
        or report["provenance"] != provenance
        or report["run_completeness"] != "COMPLETE"
        or report["calls"] != 6
        or report["smoke_status"]
        != "SMOKE_PASS — FULL RUN STILL REQUIRES EXPLICIT APPROVAL"
        or report["sufficiency_profile_outcome"] != "SUFFICIENCY_PROFILE_INCOMPLETE"
    ):
        raise ValueError("smoke identity/status mismatch")
    # Empty offline grounding is an internal record-shape adapter only; it is
    # never measured, emitted, or fed to aggregate evaluate.
    empty = {
        k: False
        for k in (
            "produced",
            "current_identity",
            "citation_membership",
            "governing_coverage",
            "facts_correct",
        )
    }
    rows = tuple(decode({**r, "grounding": empty}) for r in report["records"])
    if tuple(r.case for r in rows) != SMOKE or any(
        r.variant != "initial"
        or len(r.attempts) != 1
        or r.rounds != 0
        or not r.attempts[0].valid
        or r.attempts[0].failure is not None
        or r.corrected_request
        or r.operator_answer
        for r in rows
    ):
        raise ValueError("smoke record mismatch")
    if len({r.attempts[0].disposition for r in rows}) < 2:
        raise ValueError("uniform smoke")
    derived = interpret(rows, complete=True, smoke=True)
    if derived["sufficiency_profile_outcome"] != "SUFFICIENCY_PROFILE_INCOMPLETE":
        raise ValueError("smoke unsafe/failed")
    for key, value in derived.items():
        if report[key] != value:
            raise ValueError("smoke measurement mismatch")
