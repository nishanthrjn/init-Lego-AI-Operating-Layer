"""FORGEAI-ANALYST-SUFFICIENCY-HARDENING-H2: Agent 1.1.0 composed with H1.

Offline only: a scripted replay model behind the governed host. No provider,
Ollama or live run. SAFETY-EVAL-3 is checked by path only, never opened.
"""

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from analyst_evidence_loop.policy_gate import (
    PolicyGatedSequence,
    RequestPolicyRejected,
)
from analyst_evidence_loop.sequence import Observation, OperatorReview, Stage
from analyst_sufficiency_hardening_h1 import replay
from analyst_sufficiency_hardening_h2 import representation
from analyst_sufficiency_safety_eval2 import data as eval2
from analyst_sufficiency_safety_live1.inputs import Prepared, prepare
from content_discovery1.wiring import Replay, host_for
from legoai_engineering.analyst.request_policy import RequestViolationReason as Reason
from legoai_engineering.analyst.sufficiency import EvidenceSufficiencyResult
from legoai_engineering.analyst.sufficiency_envelope import (
    EnvelopedEvidenceSufficiencyAgent,
    _envelope,
    enveloped_sufficiency_definition,
)

from legoai.runtime.api import ModelPurpose

ROOT = Path(__file__).resolve().parents[4]
BASE = "f5b969a"  # live-probe record committed; H2 starts here
H2 = Path(__file__).resolve().parents[1] / "analyst_sufficiency_hardening_h2"
UNCHANGED = (
    "packages/legoai-engineering/src/legoai_engineering/analyst/request_policy.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency_agent.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency_definition.py",
    "packages/legoai-engineering/src/legoai_engineering/_json_document.py",
    "examples/forgeai/evaluation/analyst_evidence_loop",
    "examples/forgeai/evaluation/analyst_sufficiency_hardening_h1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval2",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval3",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live2",
    "src",
)

pytestmark = pytest.mark.skipif(
    os.environ.get("FORGEAI_LIVE1_OFFLINE") != "1",
    reason="requires the FORGEAI_LIVE1_OFFLINE=1 provider fence",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def reply(*requests: dict[str, object]) -> str:
    return json.dumps(
        {
            "disposition": "missing_governing_evidence",
            "explanation": "Governing source absent.",
            "governing_sources": [],
            "requests": list(requests),
        }
    )


FABRICATED: dict[str, object] = {
    "kind": "named_evidence",
    "description": "file",
    "path": "logistics/invented.py",
    "choices": [],
}
ROLE: dict[str, object] = {
    "kind": "source_role",
    "description": "the routing table owner",
    "path": None,
    "choices": [],
}


def assess(case_id: str, output: str) -> tuple[Prepared, Any, Any, Replay]:
    """One 1.1.0 assessment through the governed host with a scripted model."""
    case, o = next((c, o) for c, o in eval2.load() if c.id == case_id)
    p = asyncio.run(prepare(case, o))
    model = Replay(output)
    host, _ = host_for(model)

    async def once() -> tuple[Any, Any]:
        context = host.model_execution(ModelPurpose.CHAT)
        agent = EnvelopedEvidenceSufficiencyAgent(host.agent_runtime())
        result = await agent.assess(
            context, p.manifest, current_manifest=lambda: p.manifest
        )
        return context, result

    context, result = asyncio.run(once())
    return p, context, result, model


def check_blocked(observation: Observation, gated: PolicyGatedSequence) -> None:
    assert observation.stage is Stage.ASSESS and observation.assessment is None
    assert gated.rejected is not None
    assert [v.reason for v in gated.rejected.violations] == [
        Reason.PATH_NOT_ESTABLISHED
    ]


def test_27_h1_invoked_after_parse_of_1_1_0_output() -> None:
    p, context, result, model = assess("s11", reply(FABRICATED))
    assert type(result) is EvidenceSufficiencyResult and result.assessment is not None
    request = model.requests[0]
    assert request.response_format is None
    assert (
        request.messages[0].content == enveloped_sufficiency_definition().system_prompt
    )
    assert request.messages[1].content == _envelope(p.manifest)
    gated = PolicyGatedSequence(p.sequence, replay.baseline_policy())
    check_blocked(gated.assess(context.execution_id, result), gated)


def test_28_h1_rejection_still_blocks_progression() -> None:
    p, context, result, _ = assess("s11", reply(FABRICATED))
    gated = PolicyGatedSequence(p.sequence, replay.baseline_policy())
    gated.assess(context.execution_id, result)
    m = gated.observe().manifest
    review = OperatorReview(m.identity(), context.execution_id, True)
    with pytest.raises(RequestPolicyRejected):
        gated.progress(review, m)
    with pytest.raises(RequestPolicyRejected):
        gated.assess(context.execution_id, result)


def test_accepted_source_role_reaches_review_unchanged() -> None:
    p, context, result, _ = assess("s11", reply(ROLE))
    gated = PolicyGatedSequence(p.sequence, replay.baseline_policy())
    observation = gated.assess(context.execution_id, result)
    assert observation.stage is Stage.REVIEW
    assert observation.assessment is result.assessment


def test_mutation_h1_bypass_detected() -> None:
    p, context, result, _ = assess("s11", reply(FABRICATED))
    gated = PolicyGatedSequence(p.sequence, replay.baseline_policy())
    bypass = p.sequence.assess(context.execution_id, result)  # no policy gate
    with pytest.raises(AssertionError):
        check_blocked(bypass, gated)


def test_replay_representation_record_reproduced() -> None:
    record = json.loads(representation.RECORD.read_text(encoding="utf-8"))
    assert representation.compare() == record
    summary = record["summary"]
    assert summary["cases"] == 22
    assert summary["v1_0_payloads_reproduced"] == 22  # historical payloads exact
    assert summary["round_trips_exact"] == 22
    assert summary["within_input_limit"] == 22
    assert record["agent_1_0_0"]["prompt_sha256"].startswith("18cab7c84646")
    assert "no behavioral improvement is claimed" in record["interpretation"]
    for case in record["cases"]:
        assert set(case) == {
            "case",
            "files",
            "v1_0_bytes",
            "v1_1_bytes",
            "overhead_bytes",
            "v1_0_sha256",
            "v1_0_matches_recorded_payload",
            "v1_1_sha256",
            "v1_1_zones",
            "evidence_round_trip_exact",
            "v1_1_within_input_limit",
        }  # sizes, digests and structure only; no content or scores


def test_h1_parser_core_and_evaluations_unchanged() -> None:
    for path in UNCHANGED:
        assert git("diff", "--name-only", BASE, "--", path) == "", path
        assert git("status", "--porcelain", "--", path) == "", path


def test_h2_does_not_use_safety_eval3() -> None:
    production = (
        ROOT
        / "packages/legoai-engineering/src/legoai_engineering/analyst"
        / "sufficiency_envelope.py"
    )
    for path in (*H2.glob("*.py"), H2 / "representation.json", production):
        source = path.read_text(encoding="utf-8")
        assert "eval3" not in source and "SAFETY-EVAL-3" not in source, path
