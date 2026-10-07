"""Live assessments through the unchanged bounded evidence sequence."""

from collections.abc import Awaitable, Callable
from dataclasses import replace

from analyst_design_eval2.data import Fixture, Oracle, input_facts
from analyst_design_eval2.inputs import initial_manifest
from analyst_design_eval2.requests import normalize, score_requests, unresolved_mixed
from analyst_design_eval2.runner import Attempt, Grounding, Row, Workspace
from analyst_evidence_loop.sequence import (
    ClarificationSelection,
    EvidenceSequence,
    OperatorReview,
    PathSelection,
    Stage,
)
from content_discovery1.wiring import NOW, Replay, host_for
from legoai_engineering.analyst.authorized import (
    REPOSITORY_READ_ACTION,
    AuthorizedRepositoryEvidence,
)
from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    EvidenceRequestKind,
    EvidenceSufficiencyResult,
    SufficiencyDisposition,
    SufficiencyFailure,
)
from legoai_engineering.repository.workspace import RepositoryPath

from legoai.execution.values import ExecutionId

Assessor = Callable[
    [EvidenceManifest, Fixture, str, str], Awaitable[EvidenceSufficiencyResult]
]


async def run_row(
    f: Fixture,
    o: Oracle,
    variant: str,
    assess: Assessor,
    *,
    smoke: bool = False,
    checkpoint: Callable[[Row], None] = lambda row: None,
) -> Row:
    if variant not in f.variants:
        raise ValueError("unknown variant")
    workspace = Workspace(dict(f.files))
    model = Replay("must never be called")
    host, ref = host_for(model)
    facts = input_facts(f.id)
    if variant == "unrelated":
        facts = replace(
            facts, selected_paths=tuple(sorted((*facts.selected_paths, f.unrelated)))
        )
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
    m = initial_manifest(facts, evidence)
    # Operator-selected frozen addition only; model paths never widen this grant.
    action_allowed = (
        allowed
        if f.failure == "acquisition_denied" or not f.addition
        else (*allowed, RepositoryPath(f.addition))
    )
    sequence = EvidenceSequence(
        m, replace(reader, allowed_paths=action_allowed), tenant
    )
    attempts: list[Attempt] = []
    accepted = clarified = rejected = 0
    blocked = False

    async def submit(phase: str) -> None:
        current = sequence.observe().manifest
        identity = f"{f.id}-{variant}-{phase}"
        failure = (
            f.failure if f.failure in {"stale_assessment", "budget_exhausted"} else None
        )
        result = (
            EvidenceSufficiencyResult(failure=SufficiencyFailure(failure))
            if failure
            else await assess(current, f, variant, phase)
        )
        sequence.assess(ExecutionId(identity), result)
        a = result.assessment
        attempts.append(
            Attempt(
                identity,
                phase,
                a.disposition.value if a else None,
                a.requests if a else (),
                a.governing_sources if a else (),
                current.identity(),
                result.failure
                not in {
                    SufficiencyFailure.INVALID_OUTPUT,
                    SufficiencyFailure.PREREQUISITES_UNMET,
                },
                result.failure.value if result.failure else None,
            )
        )
        checkpoint(snapshot())

    def snapshot() -> Row:
        obs = sequence.observe()
        return Row(
            f.id,
            variant,
            tuple(attempts),
            obs.stage is Stage.ELIGIBLE_FOR_ANALYSIS,
            attempts[-1].phase if attempts else "initial",
            obs.failure.value if obs.failure else None,
            obs.stop_reason.value if obs.stop_reason else None,
            obs.rounds,
            accepted,
            0,
            clarified,
            rejected,
            0,
            sum(p not in {x.value for x in action_allowed} for p in workspace.reads),
            0,
            0,
            blocked,
            Grounding(),
        )

    def review(accepted: bool = True) -> OperatorReview:
        obs = sequence.observe()
        return OperatorReview(obs.manifest.identity(), obs.assessment_ids[-1], accepted)

    await submit("initial")
    obs = sequence.observe()
    action = not smoke and (
        variant == "resolved" or f.category in {"multi_step", "operational"}
    )
    if obs.stage is Stage.REVIEW:
        assert obs.assessment is not None
        if obs.assessment.disposition is SufficiencyDisposition.SUFFICIENT:
            sequence.progress(review(), obs.manifest)
        elif action:
            requests = obs.assessment.requests
            good = score_requests(requests, o.at("initial", variant)).acceptable
            blocked = unresolved_mixed(
                requests, one_round_resolves=o.one_round_resolves
            )
            if blocked or not good:
                rejected += 1
                sequence.progress(review(False), obs.manifest)
            else:
                if f.clarification:
                    clarified += 1
                else:
                    accepted += 1
                if f.clarification:
                    index = next(
                        i
                        for i, r in enumerate(requests)
                        if r.kind is EvidenceRequestKind.OPERATOR_CLARIFICATION
                    )
                    choices = requests[index].choices
                    answer = next(
                        (
                            c
                            for c in choices
                            if normalize(c)
                            in {normalize(x) for x in o.clarification_answers}
                        ),
                        f.clarification,
                    )
                    await sequence.advance(
                        review(),
                        obs.manifest,
                        clarification=ClarificationSelection(
                            index, answer, f.revised_question
                        ),
                    )
                else:
                    index = next(
                        (
                            i
                            for i, r in enumerate(requests)
                            if r.kind is EvidenceRequestKind.SOURCE_ROLE
                            or (r.path and r.path.value == f.addition)
                        ),
                        0,
                    )
                    if f.failure == "evidence_unavailable":
                        workspace.files.pop(f.addition, None)
                    await sequence.advance(
                        review(),
                        obs.manifest,
                        paths=(PathSelection(index, RepositoryPath(f.addition)),),
                    )
                if sequence.observe().stage is Stage.ASSESS:
                    await submit("final")
                    if sequence.observe().stage is Stage.REVIEW:
                        sequence.progress(review(), sequence.observe().manifest)
        else:
            rejected += 1
            sequence.progress(review(False), obs.manifest)
    assert not model.requests
    assert not sequence.observe().analysis_ids
    row = snapshot()
    checkpoint(row)
    return row
