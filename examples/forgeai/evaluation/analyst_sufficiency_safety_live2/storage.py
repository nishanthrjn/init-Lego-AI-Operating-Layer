"""Live/2 custody: the live/1 store and report semantics under the live/2 identity.

The report is produced by the unchanged live/1 controller; this store stamps
the live/2 condition/report identity and validates it with the unchanged
live/1 rules (schema, lifecycle, decision, no raw text, no blended score).
"""

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from analyst_sufficiency_safety_live1 import identity as live1
from analyst_sufficiency_safety_live1 import storage as live1_storage

from analyst_sufficiency_safety_live2.identity import CONDITION, REPORT


class Store(live1_storage.Store):
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

    def finish(self, report: dict[str, Any]) -> None:
        report.update(
            {"run_id": self.run_id, "report_identity": REPORT, "condition": CONDITION}
        )
        validate(report)
        self.write("report.json", report)
        with (self.path / "report.md").open("x", encoding="utf-8") as file:
            summary = {
                k: v
                for k, v in report.items()
                if k not in {"records", "provenance", "timings", "execution_lifecycle"}
            }
            file.write(
                "# Sufficiency safety live baseline (runtime revision 2)\n\n```json\n"
                + json.dumps(summary, indent=2, ensure_ascii=False)
                + "\n```\n"
            )


def validate(report: dict[str, Any]) -> None:
    if report["report_identity"] != REPORT or report["condition"] != CONDITION:
        raise ValueError("report identity/condition")
    provenance = report["provenance"]
    if provenance.get("preflight_verified", True) and (
        provenance.get("condition") != CONDITION
        or provenance.get("ollama_version") != "0.40.0"
    ):
        raise ValueError("live/2 provenance required")
    # Identical semantics: the unchanged live/1 rules on the same report.
    live1_storage.validate(
        {**report, "report_identity": live1.REPORT, "condition": live1.CONDITION}
    )
