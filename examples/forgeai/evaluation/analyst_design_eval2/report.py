"""Revision-2 complete bounded request records and reproducible offline reports."""

import json
from dataclasses import asdict, fields
from pathlib import Path
from typing import cast

from legoai_engineering.analyst.sufficiency import EvidenceRequest, EvidenceRequestKind
from legoai_engineering.repository.workspace import RepositoryPath

from analyst_design_eval2.data import CONDITION, HERE, digest, freeze, read
from analyst_design_eval2.metrics import evaluate
from analyst_design_eval2.runner import Attempt, Grounding, Row


def record(row: Row) -> dict[str, object]:
    obj = asdict(row)
    obj["attempts"] = [
        {
            **asdict(a),
            "requests": [
                {
                    "kind": r.kind.value,
                    "path": r.path.value if r.path else None,
                    "description": r.description,
                    "choices": list(r.choices),
                }
                for r in a.requests
            ],
            "governing_sources": [p.value for p in a.governing_sources],
        }
        for a in row.attempts
    ]
    return obj


def decode(obj: dict[str, object]) -> Row:
    if set(obj) != {f.name for f in fields(Row)}:
        raise ValueError("row fields")
    for key in ("eligible", "profile_unresolved"):
        if type(obj[key]) is not bool:
            raise ValueError("boolean observation required")
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
        if type(obj[key]) is not int or not 0 <= cast(int, obj[key]) <= 8:
            raise ValueError("bounded observation count required")
    attempts = []
    for a in cast(list[dict[str, object]], obj["attempts"]):
        if set(a) != {f.name for f in fields(Attempt)}:
            raise ValueError("attempt fields")
        if type(a["valid"]) is not bool:
            raise ValueError("validity type")
        if type(a["requests"]) is not list or type(a["governing_sources"]) is not list:
            raise ValueError("observation arrays required")
        if a["disposition"] not in {
            None,
            "sufficient",
            "missing_governing_evidence",
            "unresolved_ambiguity",
        }:
            raise ValueError("closed disposition required")
        raw = cast(list[dict[str, object]], a["requests"])
        if len(raw) > 8:
            raise ValueError("request bound")
        requests = []
        for r in raw:
            if set(r) != {"kind", "path", "description", "choices"}:
                raise ValueError("request fields")
            if type(r["choices"]) is not list or type(r["kind"]) is not str:
                raise ValueError("request types")
            requests.append(
                EvidenceRequest(
                    EvidenceRequestKind(r["kind"]),
                    cast(str, r["description"]),
                    None if r["path"] is None else RepositoryPath(cast(str, r["path"])),
                    tuple(cast(list[str], r["choices"])),
                )
            )
        attempts.append(
            Attempt(
                **{  # type: ignore[arg-type]
                    **a,
                    "requests": tuple(requests),
                    "governing_sources": tuple(
                        RepositoryPath(p)
                        for p in cast(list[str], a["governing_sources"])
                    ),
                }
            )
        )
    g = cast(dict[str, bool], obj["grounding"])
    if any(type(v) is not bool for v in g.values()):
        raise ValueError("grounding type")
    return Row(**{**obj, "attempts": tuple(attempts), "grounding": Grounding(**g)})  # type: ignore[arg-type]


def build(rows: tuple[Row, ...]) -> dict[str, object]:
    schema = read("schema-v2.json")
    return {
        "schema": schema["report"],
        "condition": CONDITION,
        "mode": "scripted-offline",
        "model_identity": None,
        "digests": freeze(),
        "implementation": {
            name: digest(HERE / name)
            for name in (
                "data.py",
                "inputs.py",
                "requests.py",
                "runner.py",
                "metrics.py",
                "report.py",
            )
        },
        "live_repetitions": schema["live_repetitions"],
        "live_final_analysis": schema["live_final_analysis"],
        "measurement": {**evaluate(rows), "records": [record(r) for r in rows]},
    }


def verify(report: dict[str, object]) -> None:
    measurement = cast(dict[str, object], report["measurement"])
    rows = tuple(
        decode(r) for r in cast(list[dict[str, object]], measurement["records"])
    )
    if json.dumps(build(rows), sort_keys=True) != json.dumps(report, sort_keys=True):
        raise ValueError("report does not refold")


def write(report: dict[str, object], directory: Path) -> None:
    verify(report)
    directory.mkdir(parents=True, exist_ok=False)
    with (directory / "report.json").open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write("\n")
    persisted = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    verify(persisted)
    summary = {k: v for k, v in persisted["measurement"].items() if k != "records"}
    with (directory / "report.md").open("x", encoding="utf-8") as file:
        file.write(
            "# Revision-2 scripted offline evaluation\n\nNo live quality evidence.\n\n```json\n"
            + json.dumps(summary, indent=2)
            + "\n```\n"
        )
