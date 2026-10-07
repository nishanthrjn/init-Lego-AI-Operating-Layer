"""Live/2 operator entry: the unchanged live/1 controller under live/2 identity.

Only preflight (exact Ollama 0.40.0 pin), pre-call revalidation and custody
differ; membership, order, budgets, guard, scoring, stops and the report are
live/1's (analyst_sufficiency_safety_live1.harness.execute).
"""

import time
from pathlib import Path
from typing import Any

from analyst_sufficiency_safety_live1.harness import execute, refusal

from analyst_sufficiency_safety_live2.identity import preflight, verify_before_call
from analyst_sufficiency_safety_live2.storage import Store

__all__ = ["execute", "run"]


def run(mode: str, directory: Path, approval: str) -> dict[str, Any]:
    """PREFLIGHT (zero semantic calls) or BASELINE (separately authorized)."""
    if mode not in {"PREFLIGHT", "BASELINE"}:
        raise ValueError("unknown mode")
    if not approval.strip():
        raise ValueError("operator authorization reference required")
    started = time.monotonic()
    try:
        provenance = preflight(directory)
    except (ValueError, OSError) as error:
        if directory.exists():
            raise
        store = Store(directory)
        refused = refusal(mode, approval)
        refused["stop_reason"] = (
            str(error).split(":")[0]
            if isinstance(error, ValueError)
            else type(error).__name__
        )
        store.finish(refused)
        return refused
    store = Store(directory)
    if mode == "PREFLIGHT":
        report = refusal(mode, approval)
        report.update(
            {
                "provenance": provenance,
                "git_head": provenance["commit"],
                "clean_tracked_tree": True,
                "evaluation_report_identity": provenance["evaluation_report"],
                "stop_reason": None,
                "decision": {"code": None, "label": "PREFLIGHT - NO MEASUREMENT"},
            }
        )
        store.finish(report)
        return report
    return execute(
        store,
        provenance,
        approval,
        started=started,
        before_call=lambda: verify_before_call(provenance),
    )
