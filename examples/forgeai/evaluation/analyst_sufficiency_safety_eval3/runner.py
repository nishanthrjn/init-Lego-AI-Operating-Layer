"""Offline qualification of revision 3 through the real governed Agent path.

The procedure matches revision 2:
- one initial assessment through the unchanged EvidenceSequence;
- a valid SUFFICIENT is accepted and anything else declined;
- no acquisition, retry or repair.

Scripted replies (fixed Replay model) exercise the scorer and are never
quality evidence.
"""

import asyncio
import json
from enum import Enum

from analyst_design_eval2.runner import Workspace
from analyst_evidence_loop.sequence import EvidenceSequence, OperatorReview, Stage
from analyst_sufficiency_safety_eval1.runner import Row
from content_discovery1.wiring import NOW, Replay, host_for
from legoai_engineering.analyst.authorized import (
    REPOSITORY_READ_ACTION,
    AuthorizedRepositoryEvidence,
)
from legoai_engineering.analyst.sufficiency import SufficiencyDisposition
from legoai_engineering.analyst.sufficiency_agent import EvidenceSufficiencyAgent
from legoai_engineering.repository.workspace import RepositoryPath

from analyst_sufficiency_safety_eval3.data import (
    Case,
    Criterion,
    Oracle,
    input_facts,
    load,
    manifest,
)
from legoai.runtime.api import ModelPurpose

__all__ = ["Fault", "Row", "replay", "run", "scripted"]


class Fault(Enum):
    CORRECT = "correct"
    FALSE_SUFFICIENT = "false_sufficient"
    ABSTAIN = "abstain"  # unrelated role request
    INVALID = "invalid"
    SECRET_REQUEST = "secret_request"  # requests a forbidden path
    FABRICATE = "fabricate"  # invented named path
    GUESS_FOR_ROLE = "guess_for_role"  # named path in place of a role


def _request(
    kind: str, description: str, path: str | None = None, choices: tuple[str, ...] = ()
) -> dict[str, object]:
    return {
        "kind": kind,
        "description": description,
        "path": path,
        "choices": list(choices),
    }


def _correct(c: Criterion) -> dict[str, object]:
    if c.kind == "named_evidence":
        return _request(c.kind, "governing source", c.path)
    if c.kind == "source_role":
        return _request(c.kind, f"the governing {c.label} source")
    return _request(
        c.kind, "Which one is meant?", None, tuple(i.label for i in c.intents)
    )


def _reply(disposition: str, sources: list[str], requests: list[object]) -> str:
    return json.dumps(
        {
            "disposition": disposition,
            "explanation": "Scripted reply.",
            "governing_sources": sources,
            "requests": requests,
        }
    )


def scripted(case: Case, o: Oracle, fault: Fault) -> str:
    supplied = sorted(case.files)
    if fault is Fault.INVALID:
        return "The evidence looks fine to me."
    if fault is Fault.FALSE_SUFFICIENT:
        return _reply("sufficient", supplied[:1], [])
    if fault is Fault.ABSTAIN:
        return _reply(
            "missing_governing_evidence",
            [],
            [_request("source_role", "additional context")],
        )
    if fault is Fault.SECRET_REQUEST:
        target = (*o.sensitive_paths, *o.edit_target_paths, "keys/unlisted.pem")[0]
        return _reply(
            "missing_governing_evidence",
            [],
            [_request("named_evidence", "requested file", target)],
        )
    if fault is Fault.FABRICATE:
        return _reply(
            "missing_governing_evidence",
            [],
            [_request("named_evidence", "likely file", "invented/guessed_values.json")],
        )
    if fault is Fault.GUESS_FOR_ROLE:
        return _reply(
            "missing_governing_evidence",
            [],
            [_request("named_evidence", "the role's file", o.governing[0])],
        )
    if o.expected_disposition == "sufficient":
        return _reply("sufficient", list(o.governing), [])
    return _reply(o.expected_disposition, [], [_correct(c) for c in o.policy.required])


async def _replay(case: Case, o: Oracle, reply: str) -> Row:
    workspace = Workspace(dict(case.files))
    reader_host, ref = host_for(Replay("must never be called"))
    facts = input_facts(case.id)
    allowed = tuple(RepositoryPath(p) for p in facts.selected_paths)
    reader = AuthorizedRepositoryEvidence(
        ref,
        workspace,
        reader_host.security_context(ref, REPOSITORY_READ_ACTION, ref.instance),
        reader_host.authorization,
        allowed,
        lambda: NOW,
    )
    tenant = reader.security_context.tenant_context
    evidence = await reader.acquire(allowed, tenant)
    m = manifest(facts, evidence)
    sequence = EvidenceSequence(m, reader, tenant)
    model = Replay(reply)
    host, _ = host_for(model)
    context = host.model_execution(ModelPurpose.CHAT)
    result = await EvidenceSufficiencyAgent(host.agent_runtime()).assess(
        context, m, current_manifest=lambda: sequence.observe().manifest
    )
    sequence.assess(context.execution_id, result)
    obs = sequence.observe()
    if obs.stage is Stage.REVIEW:
        assert obs.assessment is not None
        accept = obs.assessment.disposition is SufficiencyDisposition.SUFFICIENT
        sequence.progress(
            OperatorReview(obs.manifest.identity(), obs.assessment_ids[-1], accept),
            obs.manifest,
        )
    final = sequence.observe()
    a = result.assessment
    payload = model.requests[0].messages[1].content if model.requests else ""
    return Row(
        case.id,
        a.disposition.value if a else None,
        a.requests if a else (),
        tuple(p.value for p in a.governing_sources) if a else (),
        result.failure is None,
        result.failure.value if result.failure else None,
        final.stage is Stage.ELIGIBLE_FOR_ANALYSIS,
        sum(p not in {x.value for x in allowed} for p in workspace.reads),
        len(model.requests),
        payload,
    )


def replay(case: Case, o: Oracle, reply: str) -> Row:
    return asyncio.run(_replay(case, o, reply))


def run(faults: dict[str, Fault] | None = None) -> tuple[Row, ...]:
    faults = faults or {}
    return tuple(
        replay(case, o, scripted(case, o, faults.get(case.id, Fault.CORRECT)))
        for case, o in load()
    )
