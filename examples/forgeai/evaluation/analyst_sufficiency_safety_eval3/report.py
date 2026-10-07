"""forgeai-analyst-sufficiency-safety-report/3.

Persists parsed request sets and closed statuses, never the USER payload or a
raw reply (only the payload's SHA-256). There is no blended score.
"""

from typing import cast

from analyst_sufficiency_safety_eval1.report import record

from analyst_sufficiency_safety_eval3.data import CONDITION, REPORT, freeze, read
from analyst_sufficiency_safety_eval3.metrics import SCOPE, evaluate
from analyst_sufficiency_safety_eval3.runner import Row

__all__ = ["build", "record", "verify"]


def build(rows: tuple[Row, ...], mode: str = "scripted") -> dict[str, object]:
    evaluation = evaluate(rows)
    decision = cast(dict[str, str], evaluation["decision"])
    return {
        "report_identity": REPORT,
        "condition": CONDITION,
        "mode": mode,
        "scope": SCOPE,
        "records": [record(r) for r in rows],
        "per_case": evaluation["per_case"],
        "metrics": evaluation["metrics"],
        "gates": evaluation["gates"],
        "decision": decision
        if mode != "scripted"
        else {**decision, "label": "SCRIPTED - not quality evidence"},
        "development_regression": {
            "condition": "forgeai-analyst-sufficiency-safety-eval/2",
            "status": "exposed development benchmark; non-gating continuity metric",
        },
        "freeze": freeze(),
        "grounding_status": "NOT_MEASURED",
        "blended_score": "NOT_PRODUCED",
        "notes": "Deterministic frozen scoring; no LLM judge; model behavior "
        "only, no product guard credited.",
    }


def verify(report: dict[str, object]) -> None:
    schema = read("schema-t3.json")
    missing = set(cast(list[str], schema["required"])) - set(report)
    if missing:
        raise ValueError("report missing fields: " + repr(sorted(missing)))
    if report["report_identity"] != REPORT or report["condition"] != CONDITION:
        raise ValueError("wrong report identity")
    if report["grounding_status"] != "NOT_MEASURED":
        raise ValueError("grounding is not measured by this condition")
    if report["blended_score"] != "NOT_PRODUCED" or report["scope"] != SCOPE:
        raise ValueError("no blended score; model behavior only")
    for row in cast(list[dict[str, object]], report["records"]):
        if set(row) & {"user_payload", "raw", "response"}:
            raise ValueError("raw payload/response persistence prohibited")
