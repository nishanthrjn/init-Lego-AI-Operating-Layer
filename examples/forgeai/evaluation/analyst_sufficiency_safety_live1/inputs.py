"""Authorized initial inputs and the pre-dispatch payload leakage guard.

The model-visible payload is the frozen SAFETY-EVAL-2 input facts serialized
exactly as the Agent serializes a manifest. Nothing from the oracle, gates,
taxonomy or ordering metadata is added. The guard is evaluator custody, not a
model-side filter: it never alters a payload, it only refuses to dispatch.
"""

import json
from dataclasses import dataclass
from typing import Any

from analyst_design_eval2.inputs import expected_payload
from analyst_design_eval2.runner import Workspace
from analyst_evidence_loop.sequence import EvidenceSequence
from analyst_sufficiency_safety_eval2.data import (
    Case,
    Oracle,
    input_facts,
    manifest,
)
from analyst_sufficiency_safety_eval2.metrics import leaks
from analyst_sufficiency_safety_eval2.runner import Row
from content_discovery1.wiring import NOW, Replay, host_for
from legoai_engineering.analyst.authorized import (
    REPOSITORY_READ_ACTION,
    AuthorizedRepositoryEvidence,
)
from legoai_engineering.analyst.sufficiency import EvidenceManifest
from legoai_engineering.repository.workspace import RepositoryPath

__all__ = ["Prepared", "expected_payload", "guard", "prepare", "serialize"]


@dataclass
class Prepared:
    case: Case
    oracle: Oracle
    workspace: Workspace
    allowed: tuple[str, ...]
    manifest: EvidenceManifest
    sequence: EvidenceSequence
    expected: dict[str, Any]
    payload: str


def serialize(expected: dict[str, Any]) -> str:
    """The Agent's manifest serialization (verified by payload digest per call)."""
    return json.dumps(expected, ensure_ascii=False, separators=(",", ":"))


async def prepare(case: Case, o: Oracle) -> Prepared:
    """Operator-selected evidence only; the model never widens this grant."""
    workspace = Workspace(dict(case.files))
    host, ref = host_for(Replay("must never be called"))
    facts = input_facts(case.id)
    allowed = tuple(RepositoryPath(p) for p in facts.selected_paths)
    reader = AuthorizedRepositoryEvidence(
        ref,
        workspace,
        host.security_context(ref, REPOSITORY_READ_ACTION, ref.instance),
        host.authorization,
        allowed,
        lambda: NOW,
    )
    tenant = reader.security_context.tenant_context
    evidence = await reader.acquire(allowed, tenant)
    m = manifest(facts, evidence)
    expected = expected_payload(facts, evidence)
    return Prepared(
        case,
        o,
        workspace,
        tuple(p.value for p in allowed),
        m,
        EvidenceSequence(m, reader, tenant),
        expected,
        serialize(expected),
    )


def guard(p: Prepared) -> None:
    """Refuse dispatch unless the payload is exactly the frozen visible facts."""
    facts = input_facts(p.case.id)
    m = p.manifest
    if {f.path for f in m.evidence.files} != set(facts.selected_paths):
        raise ValueError("LEAKAGE_PATHS")
    if any(f.text != p.case.files[f.path] for f in m.evidence.files):
        raise ValueError("LEAKAGE_CONTENT")
    if (
        m.question != facts.question
        or m.expectations != facts.expectations
        or m.clarifications
        or m.unknowns
    ):
        raise ValueError("LEAKAGE_DECLARATION")
    if p.expected != expected_payload(facts, m.evidence):
        raise ValueError("LEAKAGE_PAYLOAD")
    if p.payload != serialize(p.expected):
        raise ValueError("LEAKAGE_SERIALIZATION")
    probe = Row(p.case.id, None, (), (), False, None, False, 0, 0, p.payload)
    found = leaks(probe, p.case, p.oracle)
    if found:
        raise ValueError("PAYLOAD_LEAKAGE: " + ",".join(found))
