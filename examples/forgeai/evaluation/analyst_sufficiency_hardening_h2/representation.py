"""Offline H2 representation comparison: Agent 1.0.0 vs 1.1.0 input.

No model, provider or Agent call. The recorded SAFETY-EVAL-2 baseline inputs
are rebuilt exactly as the live harness built them. For each case, the 1.0.0
serialization must reproduce the payload digest recorded at execution, and the
1.1.0 envelope of the same evidence is measured.

Representation only: no output is rescored and no behavior change is claimed.
Only sizes, digests and structural facts are recorded, never content.
"""

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

from analyst_sufficiency_hardening_h1.replay import BASELINE
from analyst_sufficiency_safety_eval2.data import load
from analyst_sufficiency_safety_live1.inputs import prepare
from legoai_engineering.analyst.sufficiency_agent import _serialize
from legoai_engineering.analyst.sufficiency_definition import (
    evidence_sufficiency_definition,
)
from legoai_engineering.analyst.sufficiency_envelope import (
    _envelope,
    enveloped_sufficiency_definition,
)

__all__ = ["RECORD", "compare"]
RECORD = Path(__file__).resolve().parent / "representation.json"
ZONES = ["trusted_application_facts", "trusted_task", "untrusted_repository_evidence"]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compare() -> dict[str, Any]:
    report = json.loads((BASELINE / "report.json").read_text(encoding="utf-8"))
    recorded = {r["case"]: r["user_payload_sha256"] for r in report["records"]}
    old, new = evidence_sufficiency_definition(), enveloped_sufficiency_definition()
    limit = new.max_input_bytes
    cases = []
    for case, oracle in load():
        prepared = asyncio.run(prepare(case, oracle))
        m = prepared.manifest
        v1_0, v1_1 = _serialize(m), _envelope(m)
        obj = json.loads(v1_1)
        content = [x["content"] for x in obj["untrusted_repository_evidence"]]
        cases.append(
            {
                "case": case.id,
                "files": len(m.evidence.files),
                "v1_0_bytes": len(v1_0.encode()),
                "v1_1_bytes": len(v1_1.encode()),
                "overhead_bytes": len(v1_1.encode()) - len(v1_0.encode()),
                "v1_0_sha256": _sha256(v1_0),
                "v1_0_matches_recorded_payload": _sha256(v1_0) == recorded[case.id]
                and v1_0 == prepared.payload,
                "v1_1_sha256": _sha256(v1_1),
                "v1_1_zones": sorted(obj),
                "evidence_round_trip_exact": content
                == [f.text for f in m.evidence.files],
                "v1_1_within_input_limit": len(v1_1.encode()) <= limit,
            }
        )
    overheads = [c["overhead_bytes"] for c in cases]
    return {
        "record": "forgeai-analyst-sufficiency-h2-representation/1",
        "baseline_run": BASELINE.name,
        "baseline_run_id": report["run_id"],
        "agent_1_0_0": {
            "version": "1.0.0",
            "prompt_sha256": _sha256(old.system_prompt),
            "serialization": "question, files[path,text], expectations, "
            "clarifications, unknowns (insertion order)",
        },
        "agent_1_1_0": {
            "version": "1.1.0",
            "prompt_sha256": _sha256(new.system_prompt),
            "serialization": "canonical JSON, sorted keys: trusted_task, "
            "trusted_application_facts, untrusted_repository_evidence[path,content]",
        },
        "input_limit_bytes": limit,
        "cases": cases,
        "summary": {
            "cases": len(cases),
            "v1_0_payloads_reproduced": sum(
                c["v1_0_matches_recorded_payload"] for c in cases
            ),
            "round_trips_exact": sum(c["evidence_round_trip_exact"] for c in cases),
            "within_input_limit": sum(c["v1_1_within_input_limit"] for c in cases),
            "overhead_bytes_min": min(overheads),
            "overhead_bytes_max": max(overheads),
            "max_v1_1_bytes": max(c["v1_1_bytes"] for c in cases),
            "zones": ZONES,
        },
        "interpretation": "Representation difference only. No model ran under "
        "1.1.0; no output is rescored and no behavioral improvement is claimed.",
    }


if __name__ == "__main__":
    RECORD.write_text(
        json.dumps(compare(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
