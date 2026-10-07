"""Revision-2 offline qualification through the real governed Agent path.

Identical procedure to revision 1 (one initial assessment, unchanged
EvidenceSequence, a valid SUFFICIENT accepted and anything else declined, no
acquisition, retry or repair), bound to revision-2 inputs. Scripted replies
are reused from revision 1; IMPORT_GUESS adds the revision-1 defect shape: a
named path guessed from an import. Scripted runs are never quality evidence.
"""

import asyncio
import json
import re
from enum import Enum

from analyst_design_eval2.runner import Workspace
from analyst_evidence_loop.sequence import EvidenceSequence, OperatorReview, Stage
from analyst_sufficiency_safety_eval1.runner import Fault as Fault1
from analyst_sufficiency_safety_eval1.runner import Row
from analyst_sufficiency_safety_eval1.runner import scripted as scripted1
from content_discovery1.wiring import NOW, Replay, host_for
from legoai_engineering.analyst.authorized import (
    REPOSITORY_READ_ACTION,
    AuthorizedRepositoryEvidence,
)
from legoai_engineering.analyst.sufficiency import SufficiencyDisposition
from legoai_engineering.analyst.sufficiency_agent import EvidenceSufficiencyAgent
from legoai_engineering.repository.workspace import RepositoryPath

from analyst_sufficiency_safety_eval2.data import (
    Case,
    Oracle,
    input_facts,
    load,
    manifest,
)
from legoai.runtime.api import ModelPurpose

__all__ = ["Fault", "Row", "import_guess", "replay", "run", "scripted"]
_MODULE = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M)


class Fault(Enum):
    CORRECT = "correct"
    FALSE_SUFFICIENT = "false_sufficient"
    ABSTAIN = "abstain"
    INVALID = "invalid"
    SECRET_REQUEST = "secret_request"
    FABRICATE = "fabricate"
    KEYWORD_FILTER = "keyword_filter"
    IMPORT_GUESS = "import_guess"  # named path guessed from an import


def import_guess(case: Case) -> str | None:
    """The conventional `.py` path a module reference suggests (never evidence)."""
    for text in case.files.values():
        for match in _MODULE.finditer(text):
            module = match.group(1) or match.group(2)
            return module.replace(".", "/") + ".py"
    return None


def scripted(case: Case, o: Oracle, fault: Fault) -> str:
    if fault is not Fault.IMPORT_GUESS:
        return scripted1(case, o, Fault1(fault.value))
    guess = import_guess(case) or "unknown/module.py"
    return json.dumps(
        {
            "disposition": "missing_governing_evidence",
            "explanation": "Scripted import-derived path guess.",
            "governing_sources": [],
            "requests": [
                {
                    "kind": "named_evidence",
                    "description": "imported module",
                    "path": guess,
                    "choices": [],
                }
            ],
        }
    )


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


def replay(case: Case, o: Oracle, fault: Fault = Fault.CORRECT) -> Row:
    return asyncio.run(_replay(case, o, scripted(case, o, fault)))


def run(faults: dict[str, Fault] | None = None) -> tuple[Row, ...]:
    faults = faults or {}
    return tuple(
        replay(case, o, faults.get(case.id, Fault.CORRECT)) for case, o in load()
    )
