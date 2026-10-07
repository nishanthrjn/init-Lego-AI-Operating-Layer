"""Reproducible content-free records; exclusive-create JSON and Markdown."""

import json
from dataclasses import fields
from pathlib import Path
from typing import cast

from analyst_design_eval1.data import CONDITION, HERE, digest, freeze
from analyst_design_eval1.metrics import evaluate
from analyst_design_eval1.runner import Attempt, Grounding, Row


def build(rows: tuple[Row, ...]) -> dict[str, object]:
    return {
        "schema": "forgeai-analyst-design-report/1",
        "condition": CONDITION,
        "mode": "scripted-offline",
        "model_identity": None,
        "config_identity": "oracle-aware-scripted/1",
        "live_quality_evidence": False,
        "revisions": {"fixture": 1, "oracle": 1, "schema": 1, "gates": 1},
        "digests": freeze(),
        "implementation": {
            name: digest(HERE / name)
            for name in ("data.py", "runner.py", "metrics.py", "report.py")
        },
        "planned_conditions": 56,
        "actual_conditions": len(rows),
        "measurement": evaluate(rows),
    }


def decode(raw: dict[str, object]) -> Row:
    if set(raw) != {f.name for f in fields(Row)}:
        raise ValueError("unexpected row fields")
    attempts = []
    for item in cast(list[dict[str, object]], raw["attempts"]):
        if set(item) != {f.name for f in fields(Attempt)}:
            raise ValueError("unexpected attempt fields")
        for key in ("valid", "named_match", "role_match", "clarification_match"):
            if type(item[key]) is not bool:
                raise ValueError("boolean observation required")
        attempts.append(Attempt(**item))  # type: ignore[arg-type]
    grounding = cast(dict[str, object], raw["grounding"])
    if set(grounding) != {f.name for f in fields(Grounding)} or any(
        type(v) is not bool for v in grounding.values()
    ):
        raise ValueError("invalid grounding observation")
    if type(raw["eligible"]) is not bool:
        raise ValueError("boolean eligibility required")
    for key in (
        "rounds",
        "accepted_request",
        "corrected_request",
        "operator_clarification",
        "operator_rejection",
        "operator_answer",
        "unauthorized_reads",
        "unauthorized_edits",
        "target_expansion",
    ):
        if type(raw[key]) is not int or not 0 <= cast(int, raw[key]) <= 8:
            raise ValueError("bounded observation count required")
    converted = {
        **raw,
        "attempts": tuple(attempts),
        "grounding": Grounding(**grounding),  # type: ignore[arg-type]
    }
    return Row(**converted)  # type: ignore[arg-type]


def verify(report: dict[str, object]) -> None:
    measurement = cast(dict[str, object], report["measurement"])
    rows = tuple(
        decode(r) for r in cast(list[dict[str, object]], measurement["records"])
    )
    # JSON normalization preserves exact numbers and accommodates tuple arrays.
    if json.dumps(report, sort_keys=True) != json.dumps(build(rows), sort_keys=True):
        raise ValueError("report cannot be reproduced from its observations")


def render(report: dict[str, object]) -> str:
    verify(report)
    measurement = cast(dict[str, object], report["measurement"])
    summary = {k: v for k, v in measurement.items() if k != "records"}
    return (
        "# Analyst design evaluation (scripted offline)\n\nNo live quality evidence.\n\n```json\n"
        + json.dumps(summary, indent=2, sort_keys=True)
        + "\n```\n"
    )


def write(report: dict[str, object], directory: Path) -> None:
    verify(report)
    directory.mkdir(parents=True, exist_ok=False)
    with (directory / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    written = cast(
        dict[str, object],
        json.loads((directory / "report.json").read_text(encoding="utf-8")),
    )
    with (directory / "report.md").open("x", encoding="utf-8") as stream:
        stream.write(render(written))
