"""forgeai-analyst-sufficiency-safety-report/2; records reuse revision 1's format.

Persists parsed request sets and closed statuses, never the USER payload or a
raw reply (only the payload's SHA-256).
"""

from typing import cast

from analyst_sufficiency_safety_eval1.report import record

from analyst_sufficiency_safety_eval2.data import (
    CONDITION,
    HISTORICAL,
    REPORT,
    freeze,
    read,
)
from analyst_sufficiency_safety_eval2.metrics import evaluate
from analyst_sufficiency_safety_eval2.runner import Row

__all__ = ["build", "record", "verify"]


def build(rows: tuple[Row, ...], mode: str = "scripted") -> dict[str, object]:
    evaluation = evaluate(rows)
    decision = cast(dict[str, str], evaluation["decision"])
    return {
        "report_identity": REPORT,
        "condition": CONDITION,
        "mode": mode,
        "records": [record(r) for r in rows],
        "metrics": evaluation["metrics"],
        "gates": evaluation["gates"],
        "decision": decision
        if mode != "scripted"
        else {**decision, "label": "SCRIPTED - not quality evidence"},
        "historical_non_gating": {
            "cases": list(HISTORICAL),
            "source": "forgeai-analyst-design-eval/2",
            "status": "exposed; reported separately; never in the gating denominator",
        },
        "freeze": freeze(),
        "grounding_status": "NOT_MEASURED",
        "notes": "Deterministic frozen scoring; no LLM judge; exact paths must be "
        "model-visible.",
    }


def verify(report: dict[str, object]) -> None:
    schema = read("schema-s2.json")
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
