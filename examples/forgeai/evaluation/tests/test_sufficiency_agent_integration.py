"""External frozen-vocabulary compatibility; never imported by the Agent."""

import asyncio
import json

import pytest
from analyst_design_eval1.data import load
from analyst_design_eval1.runner import request as oracle_request
from analyst_evidence_loop.sequence import EvidenceSequence, OperatorReview, Stage
from content_discovery1.wiring import NOW, Replay, host_for
from legoai.runtime.api import ModelPurpose
from legoai_engineering.analyst.authorized import (
    REPOSITORY_READ_ACTION,
    AuthorizedRepositoryEvidence,
)
from legoai_engineering.analyst.sufficiency import EvidenceManifest
from legoai_engineering.analyst.sufficiency_agent import EvidenceSufficiencyAgent
from legoai_engineering.analyst.values import RepositoryEvidence
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath, WorkspaceEntry


@pytest.mark.parametrize("case", [f.id for f, o in load()])
def test_frozen_vocabulary_representable_without_input_leakage(case: str) -> None:
    f, o = next((f, o) for f, o in load() if f.id == case)
    for variant in f.variants:
        paths = sorted(
            set(
                f.initial
                + ([f.addition] if variant == "resolved" and f.addition else [])
                + ([f.unrelated] if variant == "unrelated" else [])
            )
        )
        m = EvidenceManifest(
            f.revised_question if variant == "resolved" else f.question,
            RepositoryEvidence(tuple(RepositoryText(p, f.files[p]) for p in paths)),
            "synthetic",
        )
        expected = o.expected[variant]
        r = oracle_request(o)
        output = {
            "disposition": expected,
            "explanation": "Scripted contract observation",
            "governing_sources": [paths[0]],
            "requests": []
            if expected == "sufficient"
            else [
                {
                    "kind": r.kind.value,
                    "description": r.description,
                    "path": r.path.value if r.path else None,
                    "choices": r.choices,
                }
            ]
            if r
            else [],
        }
        model = Replay(json.dumps(output))
        host, _ = host_for(model)
        context = host.model_execution(ModelPurpose.CHAT)

        def current_manifest(m: EvidenceManifest = m) -> EvidenceManifest:
            return m

        result = asyncio.run(
            EvidenceSufficiencyAgent(host.agent_runtime()).assess(
                context, m, current_manifest=current_manifest
            )
        )
        assert result.assessment is not None
        assert result.assessment.disposition.value == expected
        assert len(model.requests) == 1
        user = model.requests[0].messages[1].content
        obj = json.loads(user)
        assert obj == {
            "question": m.question,
            "files": [{"path": p, "text": f.files[p]} for p in paths],
            "expectations": [],
            "clarifications": [],
            "unknowns": [],
        }
        assert "SYNTHETIC_FORBIDDEN_TOKEN" not in user
        # Missing sources are not disclosed via fixture.files or oracle.governing.
        for hidden in set(f.files) - set(paths):
            if hidden not in m.question and not any(
                hidden in f.files[p] for p in paths
            ):
                assert hidden not in user


class NoReadWorkspace:
    def read_text(self, path: RepositoryPath) -> RepositoryText:
        raise AssertionError("Agent/result must not acquire")

    def list_entries(
        self, directory: RepositoryPath | None
    ) -> tuple[WorkspaceEntry, ...]:
        raise AssertionError("Agent/result must not discover")


def test_public_result_requires_operator_review_and_grants_no_authority() -> None:
    m = EvidenceManifest(
        "Explain supplied behavior",
        RepositoryEvidence((RepositoryText("a.py", "value=1"),)),
        "synthetic",
    )
    model = Replay(
        json.dumps(
            {
                "disposition": "sufficient",
                "explanation": "Supplied behavior",
                "governing_sources": ["a.py"],
                "requests": [],
            }
        )
    )
    host, ref = host_for(model)
    reader = AuthorizedRepositoryEvidence(
        ref,
        NoReadWorkspace(),
        host.security_context(ref, REPOSITORY_READ_ACTION, ref.instance),
        host.authorization,
        (RepositoryPath("a.py"),),
        lambda: NOW,
    )
    sequence = EvidenceSequence(m, reader, reader.security_context.tenant_context)
    context = host.model_execution(ModelPurpose.CHAT)
    result = asyncio.run(
        EvidenceSufficiencyAgent(host.agent_runtime()).assess(
            context, m, current_manifest=lambda: sequence.observe().manifest
        )
    )
    observed = sequence.assess(context.execution_id, result)
    assert (
        observed.stage is Stage.REVIEW
        and not observed.analysis_ids
        and observed.rounds == 0
    )
    observed = sequence.progress(
        OperatorReview(m.identity(), context.execution_id, True), m
    )
    assert observed.stage is Stage.ELIGIBLE_FOR_ANALYSIS and not observed.analysis_ids
    assert len(model.requests) == 1
