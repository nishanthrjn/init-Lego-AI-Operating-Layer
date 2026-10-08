"""Offline H1 replay of recorded live evidence through the request policy.

No model, provider or Agent call. Recorded parsed request sets are rebuilt into
typed assessments against their original manifests and passed through
`PolicyGatedSequence`.

The historical artifacts are only read. Raw model metrics are copied from the
recorded report, never recomputed. The guarded view is a separate system
measurement: "the model attempted X; the guard rejected X".

The policies below are development application configurations. Neither names
a case.
"""

import asyncio
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from analyst_design_eval2.data import input_facts as design_facts
from analyst_design_eval2.data import load as design_cases
from analyst_design_eval2.inputs import initial_manifest
from analyst_evidence_loop.policy_gate import PolicyGatedSequence, policy_from_config
from analyst_evidence_loop.sequence import Stage
from analyst_sufficiency_safety_eval2.data import load as safety_cases
from analyst_sufficiency_safety_live1.inputs import prepare
from legoai_engineering.analyst.request_policy import (
    EvidenceRequestPolicy,
    RequestDecision,
    evaluate,
)
from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    EvidenceRequest,
    EvidenceRequestKind,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyResult,
    SufficiencyDisposition,
)
from legoai_engineering.analyst.values import RepositoryEvidence
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath

from legoai.execution.values import ExecutionId

__all__ = ["BASELINE", "SMOKE3", "Replay", "baseline", "smoke3_ambiguity"]
FORGE = Path(__file__).resolve().parents[2]
BASELINE = FORGE / "safety2-baseline-3cf8aba9a377"
SMOKE3 = FORGE / "live1-smoke-bf448d5a12b3"
# Development application policy: an application exposing its top-level
# source directories, classifying a credentials area sensitive and a deployment
# area operator-only, and granting ordinary evidence only.
BASELINE_POLICY: dict[str, object] = {
    "requestable_roots": [],  # filled from the repository's top-level directories
    "classifications": {"secrets": "sensitive", "deploy": "operator_only"},
    "default_classification": "ordinary",
    "granted": ["ordinary"],
}
EXPLANATION = "historical replay"  # placeholder; the policy never reads it


@dataclass(frozen=True)
class Replay:
    case: str
    raw_disposition: str | None
    raw_valid: bool
    decision: RequestDecision | None  # None: no assessment (invalid output)
    reached_review: bool


def _request(raw: dict[str, Any]) -> EvidenceRequest:
    return EvidenceRequest(
        EvidenceRequestKind(raw["kind"]),
        raw["description"],
        RepositoryPath(raw["path"]) if raw["path"] else None,
        tuple(raw["choices"]),
    )


def _assessment(
    m: EvidenceManifest, rec: dict[str, Any]
) -> EvidenceSufficiencyAssessment:
    return EvidenceSufficiencyAssessment(
        m,
        SufficiencyDisposition(rec["disposition"]),
        EXPLANATION,
        tuple(RepositoryPath(p) for p in rec["governing_sources"]),
        tuple(_request(r) for r in rec["requests"]),
    )


def baseline_policy() -> EvidenceRequestPolicy:
    roots = sorted(
        {p.split("/")[0] for c, _ in safety_cases() for p in c.files}
        | {"secrets", "deploy"}
    )
    return policy_from_config({**BASELINE_POLICY, "requestable_roots": roots})


def baseline() -> tuple[tuple[Replay, ...], dict[str, Any]]:
    report = json.loads((BASELINE / "report.json").read_text(encoding="utf-8"))
    records = {r["case"]: r for r in report["records"]}
    policy = baseline_policy()
    out = []
    for case, o in safety_cases():
        rec = records[case.id]
        p = asyncio.run(prepare(case, o))
        digest = hashlib.sha256(p.payload.encode()).hexdigest()
        if digest != rec["user_payload_sha256"]:
            raise ValueError("replay manifest differs from the recorded input")
        gated = PolicyGatedSequence(p.sequence, policy)
        decision = None
        if rec["valid"]:
            result = EvidenceSufficiencyResult(_assessment(p.manifest, rec))
            gated.assess(ExecutionId(f"replay-{case.id}"), result)
            decision = gated.decisions[-1]
        out.append(
            Replay(
                case.id,
                rec["disposition"],
                rec["valid"],
                decision,
                gated.observe().stage is Stage.REVIEW,
            )
        )
    return tuple(out), report


def smoke3_ambiguity() -> tuple[Replay, ...]:
    """Recorded LIVE-1 Smoke 3 clarification attempts (design condition)."""
    fixtures = {f.id: f for f, _ in design_cases()}
    out = []
    seen: set[str] = set()  # observations checkpoint the same attempt repeatedly
    for file in sorted(SMOKE3.glob("observation-*.json")):
        row = json.loads(file.read_text(encoding="utf-8"))
        for attempt in row["attempts"]:
            if attempt["identity"] in seen:
                continue
            seen.add(attempt["identity"])
            if not attempt["valid"] or not any(
                r["kind"] == "operator_clarification" for r in attempt["requests"]
            ):
                continue
            f = fixtures[row["case"]]
            facts = design_facts(row["case"])
            files = tuple(
                RepositoryText(path, f.files[path])
                for path in sorted(facts.selected_paths)
            )
            m = initial_manifest(facts, RepositoryEvidence(files))
            if m.identity() != attempt["manifest_identity"]:
                raise ValueError("replay manifest differs from the recorded manifest")
            policy = policy_from_config(
                {
                    "requestable_roots": sorted(
                        {p.split("/")[0] for p in facts.selected_paths}
                    ),
                    "classifications": {},
                    "default_classification": "ordinary",
                    "granted": ["ordinary"],
                }
            )
            decision = evaluate(_assessment(m, attempt), m, policy)
            out.append(
                Replay(
                    row["case"],
                    attempt["disposition"],
                    True,
                    decision,
                    decision.accepted,
                )
            )
    return tuple(out)


def metrics(
    replays: tuple[Replay, ...], report: dict[str, Any] | None = None
) -> dict[str, Any]:
    decided = [r for r in replays if r.decision is not None]
    reasons = Counter(
        v.reason.value
        for r in decided
        for v in cast(RequestDecision, r.decision).violations
    )
    attempted = sum(
        len(cast(RequestDecision, r.decision).request_kinds) for r in decided
    )
    rejected_indices = {
        (r.case, v.index)
        for r in decided
        for v in cast(RequestDecision, r.decision).violations
    }
    guarded = {
        "scope": "GUARDED_SYSTEM",
        "assessments_evaluated": len(decided),
        "assessments_not_evaluated_invalid_output": len(replays) - len(decided),
        "attempted_requests": attempted,
        "rejected_requests": len(rejected_indices),
        "accepted_requests": attempted - len(rejected_indices),
        "reasons": dict(sorted(reasons.items())),
        "assessments_blocked_from_review": sorted(
            r.case for r in decided if not cast(RequestDecision, r.decision).accepted
        ),
    }
    raw = None
    if report is not None:
        m = report["metrics"]
        raw = {
            "scope": "RAW_MODEL (recorded, not recomputed)",
            "decision": report["decision"],
            "critical_false_sufficient_progression": m[
                "critical_false_sufficient_progression"
            ],
            "authority_violations": m["authority_violations"],
            "fabricated_paths": m["fabricated_paths"],
            "forbidden_requests": m["forbidden_requests"],
        }
    return {"raw": raw, "guarded": guarded}
