"""Agent 1.1.0 inputs: frozen SAFETY-EVAL-2 facts, then the H2 envelope.

The authorized manifest is built exactly as the qualified live/1 harness
builds it, and the live/1 guard still verifies the frozen facts. The model-
visible payload is the Agent 1.1.0 envelope of that manifest. The guard here is
evaluator custody: it never alters a payload, it only refuses to dispatch.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, cast

from analyst_sufficiency_safety_eval2.data import Case, Oracle, gates
from analyst_sufficiency_safety_eval2.metrics import leaks
from analyst_sufficiency_safety_eval2.runner import Row
from analyst_sufficiency_safety_live1.inputs import Prepared as Base
from analyst_sufficiency_safety_live1.inputs import guard as base_guard
from analyst_sufficiency_safety_live1.inputs import prepare as base_prepare
from legoai_engineering.analyst.sufficiency_envelope import _envelope

from analyst_sufficiency_h2_development_live1.comparison import HISTORICAL_RUN_ID

__all__ = ["ZONES", "Prepared", "facts", "guard", "prepare"]
ZONES = ["trusted_application_facts", "trusted_task", "untrusted_repository_evidence"]


@dataclass
class Prepared:
    base: Base
    payload: str  # the exact Agent 1.1.0 user message; in memory only
    expected: dict[str, Any]


async def prepare(case: Case, o: Oracle) -> Prepared:
    base = await base_prepare(case, o)
    payload = _envelope(base.manifest)
    return Prepared(base, payload, json.loads(payload))


def facts(p: Prepared) -> dict[str, Any]:
    """Pre-dispatch digest and structural facts; never the payload itself."""
    evidence = p.expected["untrusted_repository_evidence"]
    return {
        "case": p.base.case.id,
        "agent_version": "1.1.0",
        "payload_sha256": hashlib.sha256(p.payload.encode()).hexdigest(),
        "zones": sorted(p.expected),
        "evidence_files": len(evidence),
        "evidence_round_trip_exact": [x["content"] for x in evidence]
        == [f.text for f in p.base.manifest.evidence.files],
    }


def guard(p: Prepared) -> None:
    base_guard(p.base)  # frozen facts, declarations and the 1.0.0 leakage sweep
    m = p.base.manifest
    if p.payload != _envelope(m) or json.loads(p.payload) != p.expected:
        raise ValueError("LEAKAGE_ENVELOPE")
    if sorted(p.expected) != ZONES:
        raise ValueError("LEAKAGE_ENVELOPE_ZONES")
    if p.expected["trusted_task"] != {"question": m.question}:
        raise ValueError("LEAKAGE_TRUSTED_TASK")
    trusted = p.expected["trusted_application_facts"]
    if trusted["expectations"] or trusted["clarifications"] or trusted["unknowns"]:
        raise ValueError("LEAKAGE_DECLARATION")  # none of the frozen 22 declares one
    if not facts(p)["evidence_round_trip_exact"]:
        raise ValueError("LEAKAGE_EVIDENCE")
    probe = Row(p.base.case.id, None, (), (), False, None, False, 0, 0, p.payload)
    found = leaks(probe, p.base.case, p.base.oracle) + evaluator_tokens(p)
    if found:
        raise ValueError("PAYLOAD_LEAKAGE: " + ",".join(found))


def evaluator_tokens(p: Prepared) -> list[str]:
    """Supplementary H2 sweep for evaluator vocabulary absent from the inputs."""
    o = p.base.oracle
    visible = p.base.manifest.question + "\n" + "\n".join(p.base.case.files.values())
    limits = gates()
    tokens = [
        *o.pairs,
        "expected_disposition",
        "progression_allowed",
        "benign_control",
        "critical_cases",
        "gating_cases",
        HISTORICAL_RUN_ID,
        *cast(dict[str, str], limits["decisions"]).values(),
    ]
    return ["evaluator_token" for t in tokens if t in p.payload and t not in visible][
        :1
    ]
