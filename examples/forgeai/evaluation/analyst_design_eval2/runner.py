"""Scripted evaluator qualification through the unchanged authorized evidence loop."""

import asyncio
from dataclasses import dataclass, replace
from enum import Enum

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
    EvidenceRequest,
    EvidenceRequestKind,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyError,
    EvidenceSufficiencyResult,
    SufficiencyDisposition,
    SufficiencyFailure,
)
from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath, WorkspaceEntry

from analyst_design_eval2.data import Criterion, Fixture, Oracle, input_facts, load
from analyst_design_eval2.inputs import initial_manifest
from analyst_design_eval2.requests import (
    normalize,
    score_requests,
    unresolved_mixed,
)
from legoai.execution.values import ExecutionId


class Fault(Enum):
    CORRECT = "correct"
    FALSE_SUFFICIENT = "false_sufficient"
    ABSTAIN = "abstain"
    INVALID = "invalid"
    MODEL_FAILURE = "model_failure"
    REPAIR = "repair"
    AUTHORITY = "authority"
    BAD_GROUNDING = "bad_grounding"


@dataclass(frozen=True)
class Attempt:
    identity: str
    phase: str
    disposition: str | None
    requests: tuple[EvidenceRequest, ...]
    governing_sources: tuple[RepositoryPath, ...]
    manifest_identity: str
    valid: bool
    failure: str | None


@dataclass(frozen=True)
class Grounding:
    produced: bool = False
    current_identity: bool = False
    citation_membership: bool = False
    governing_coverage: bool = False
    facts_correct: bool = False


@dataclass(frozen=True)
class Row:
    case: str
    variant: str
    attempts: tuple[Attempt, ...]
    eligible: bool
    progress_phase: str
    failure: str | None
    stop: str | None
    rounds: int
    accepted_request: int
    corrected_request: int
    operator_clarification: int
    operator_rejection: int
    operator_answer: int
    unauthorized_reads: int
    unauthorized_edits: int
    target_expansion: int
    profile_unresolved: bool
    grounding: Grounding


class Workspace:
    def __init__(self, files: dict[str, str]) -> None:
        self.files = files
        self.reads: list[str] = []

    def read_text(self, path: RepositoryPath) -> RepositoryText:
        self.reads.append(path.value)
        if path.value not in self.files:
            raise WorkspaceError(WorkspaceFailure.MISSING)
        return RepositoryText(path.value, self.files[path.value])

    def list_entries(
        self, directory: RepositoryPath | None
    ) -> tuple[WorkspaceEntry, ...]:
        raise AssertionError("no discovery")


def scripted_request(c: Criterion) -> EvidenceRequest:
    return EvidenceRequest(
        EvidenceRequestKind(c.kind),
        c.alternatives[0]
        if c.alternatives
        else "Supply the referenced governing source",
        RepositoryPath(c.path) if c.path else None,
    )


def grounding(
    o: Oracle,
    m: EvidenceManifest,
    identity: str,
    citations: tuple[str, ...],
    facts: dict[str, str],
) -> Grounding:
    return Grounding(
        True,
        identity == m.identity(),
        set(citations) <= {f.path for f in m.evidence.files},
        set(o.required_answer_evidence) <= set(citations),
        bool(o.facts) and facts == o.facts,
    )


def replay(
    f: Fixture,
    o: Oracle,
    variant: str,
    fault: Fault = Fault.CORRECT,
    *,
    initial_requests: tuple[EvidenceRequest, ...] | None = None,
) -> Row:
    return asyncio.run(_replay(f, o, variant, fault, initial_requests))


async def _replay(
    f: Fixture,
    o: Oracle,
    variant: str,
    fault: Fault,
    initial_requests: tuple[EvidenceRequest, ...] | None,
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
    accepted = corrected = clarified = rejected = 0
    blocked = False

    def submit(phase: str) -> None:
        current = sequence.observe().manifest
        expected = o.initial if phase == "initial" else o.expected[variant]
        requests = (
            tuple(scripted_request(c) for c in o.at(phase, variant).required)
            if expected != "sufficient"
            else ()
        )
        predicted: str | None = expected
        if phase == "initial" and initial_requests is not None:
            requests = initial_requests
        if fault is Fault.FALSE_SUFFICIENT:
            predicted, requests = "sufficient", ()
        elif fault is Fault.ABSTAIN:
            predicted, requests = (
                "missing_governing_evidence",
                (
                    EvidenceRequest(
                        EvidenceRequestKind.SOURCE_ROLE, "Unspecified context"
                    ),
                ),
            )
        elif fault is Fault.REPAIR and phase == "initial":
            requests = (EvidenceRequest(EvidenceRequestKind.SOURCE_ROLE, "Wrong role"),)
        failure = (
            f.failure if f.failure in {"stale_assessment", "budget_exhausted"} else None
        )
        if fault is Fault.INVALID:
            failure = "invalid_output"
        if fault is Fault.MODEL_FAILURE:
            failure = "model_failure"
        sources: tuple[RepositoryPath, ...] = (
            RepositoryPath(current.evidence.files[0].path),
        )
        if failure:
            result = EvidenceSufficiencyResult(failure=SufficiencyFailure(failure))
            predicted = None
            requests = ()
            sources = ()
        else:
            try:
                result = EvidenceSufficiencyResult(
                    assessment=EvidenceSufficiencyAssessment(
                        current,
                        SufficiencyDisposition(predicted),
                        "Scripted observation; no live quality evidence",
                        sources,
                        requests,
                    )
                )
            except EvidenceSufficiencyError as error:
                failure = error.reason.value
                result = EvidenceSufficiencyResult(failure=error.reason)
                predicted = None
        identity = f"{f.id}-{variant}-{phase}"
        sequence.assess(ExecutionId(identity), result)
        attempts.append(
            Attempt(
                identity,
                phase,
                predicted,
                requests,
                sources,
                current.identity(),
                failure != "invalid_output",
                failure,
            )
        )

    def review(accepted: bool = True) -> OperatorReview:
        obs = sequence.observe()
        return OperatorReview(obs.manifest.identity(), obs.assessment_ids[-1], accepted)

    submit("initial")
    obs = sequence.observe()
    action = variant == "resolved" or f.category in {"multi_step", "operational"}
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
            if blocked or (not good and fault is not Fault.REPAIR):
                rejected += 1
                sequence.progress(review(False), obs.manifest)
            else:
                # Never rewrite the stored model assessment. Repair is explicit.
                if fault is Fault.REPAIR:
                    corrected += 1
                elif f.clarification:
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
                    submit("final")
                    if sequence.observe().stage is Stage.REVIEW:
                        sequence.progress(review(), sequence.observe().manifest)
        else:
            rejected += 1
            sequence.progress(review(False), obs.manifest)
    obs = sequence.observe()
    eligible = obs.stage is Stage.ELIGIBLE_FOR_ANALYSIS
    g = Grounding()
    if eligible:
        sequence.claim_scripted_analysis(
            ExecutionId(f"{f.id}-{variant}-analysis"), obs.manifest
        )
        g = grounding(
            o,
            obs.manifest,
            "stale" if fault is Fault.BAD_GROUNDING else obs.manifest.identity(),
            tuple(
                p
                for p in o.required_answer_evidence
                if p in {f.path for f in obs.manifest.evidence.files}
            ),
            o.facts,
        )
    assert not model.requests
    unauthorized = sum(
        p not in {x.value for x in action_allowed} for p in workspace.reads
    )
    # Denied selections are refused by the wrapper and never appear in reads.
    return Row(
        f.id,
        variant,
        tuple(attempts),
        eligible,
        attempts[-1].phase,
        obs.failure.value if obs.failure else None,
        obs.stop_reason.value if obs.stop_reason else None,
        obs.rounds,
        accepted,
        corrected,
        clarified,
        rejected,
        0,
        unauthorized + int(fault is Fault.AUTHORITY),
        int(fault is Fault.AUTHORITY),
        int(fault is Fault.AUTHORITY),
        blocked,
        g,
    )


def run(faults: dict[str, Fault] | None = None) -> tuple[Row, ...]:
    faults = faults or {}
    return tuple(
        replay(f, o, v, faults.get(f.id, Fault.CORRECT))
        for f, o in load()
        for v in f.variants
    )
