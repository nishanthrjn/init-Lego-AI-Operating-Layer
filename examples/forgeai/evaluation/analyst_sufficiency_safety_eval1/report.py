"""forgeai-analyst-sufficiency-safety-report/1: content-minimal JSON report.

Persists parsed request sets (untrusted model text, as in LIVE-1), closed
statuses and metrics. It never persists the USER payload or a raw reply; only
the payload's SHA-256.
"""

import hashlib
from typing import cast

from analyst_sufficiency_safety_eval1.data import (
    CONDITION,
    HISTORICAL,
    REPORT,
    freeze,
    read,
)
from analyst_sufficiency_safety_eval1.metrics import evaluate
from analyst_sufficiency_safety_eval1.runner import Row


def record(row: Row) -> dict[str, object]:
    return {
        "case": row.case,
        "disposition": row.disposition,
        "valid": row.valid,
        "failure": row.failure,
        "progressed": row.progressed,
        "governing_sources": list(row.governing_sources),
        "requests": [
            {
                "kind": r.kind.value,
                "path": r.path.value if r.path else None,
                "description": r.description,
                "choices": list(r.choices),
            }
            for r in row.requests
        ],
        "unauthorized_reads": row.unauthorized_reads,
        "model_calls": row.model_calls,
        "user_payload_sha256": hashlib.sha256(row.user_payload.encode()).hexdigest(),
    }


def build(rows: tuple[Row, ...], mode: str = "scripted") -> dict[str, object]:
    evaluation = evaluate(rows)
    return {
        "report_identity": REPORT,
        "condition": CONDITION,
        "mode": mode,
        "records": [record(r) for r in rows],
        "metrics": evaluation["metrics"],
        "gates": evaluation["gates"],
        "decision": evaluation["decision"]
        if mode != "scripted"
        else {
            **cast(dict[str, str], evaluation["decision"]),
            "label": "SCRIPTED - not quality evidence",
        },
        "historical_non_gating": {
            "cases": list(HISTORICAL),
            "source": "forgeai-analyst-design-eval/2",
            "status": "exposed; reported separately; never in the gating denominator",
        },
        "freeze": freeze(),
        "grounding_status": "NOT_MEASURED",
        "notes": "Deterministic frozen scoring; no LLM judge.",
    }


def verify(report: dict[str, object]) -> None:
    schema = read("schema-s1.json")
    missing = set(cast(list[str], schema["required"])) - set(report)
    if missing:
        raise ValueError("report missing fields: " + repr(sorted(missing)))
    if report["report_identity"] != REPORT or report["condition"] != CONDITION:
        raise ValueError("wrong report identity")
    if report["grounding_status"] != "NOT_MEASURED":
        raise ValueError("grounding is not measured by this condition")
    gating = [
        cast(dict[str, object], r)["case"]
        for r in cast(list[object], report["records"])
    ]
    if set(gating) & set(HISTORICAL):
        raise ValueError("historical case in gating records")
