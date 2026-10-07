"""Oracle-aware scripted evaluator tests; never a model or production workflow."""

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
    EvidenceClarification,
    EvidenceManifest,
    EvidenceRequest,
    EvidenceRequestKind,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyError,
    EvidenceSufficiencyResult,
    GoverningSourceExpectation,
    SufficiencyDisposition,
    SufficiencyFailure,
)
from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath, WorkspaceEntry

from analyst_design_eval1.data import Fixture, Oracle, load
from legoai.execution.values import ExecutionId


class Fault(Enum):
    CORRECT = "correct"
    FALSE_SUFFICIENT = "false_sufficient"
    ABSTAIN = "abstain"
    WRONG_KIND = "wrong_kind"
    INVENTED_PATH = "invented_path"
    STALE = "stale"
    STALE_EVIDENCE = "stale_evidence"
    STALE_CLARIFICATION = "stale_clarification"
    INVALID = "invalid"
    MODEL_FAILURE = "model_failure"
    OPERATOR_REPAIR = "operator_repair"
    OPERATOR_ANSWER = "operator_answer"
    AUTHORITY = "authority"
    BAD_GROUNDING = "bad_grounding"


@dataclass(frozen=True)
class Attempt:
    identity: str
    phase: str
    predicted: str | None
    valid: bool
    request_kind: str | None
    named_match: bool
    role_match: bool
    clarification_match: bool
    operational: str | None


@dataclass(frozen=True)
class Grounding:
    produced: bool
    current_identity: bool
    citation_membership: bool
    governing_coverage: bool
    facts_correct: bool


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
    grounding: Grounding


class Workspace:
    def __init__(self, files: dict[str, str]) -> None:
        self.files = files
        self.reads: list[str] = []

    def list_entries(
        self, directory: RepositoryPath | None
    ) -> tuple[WorkspaceEntry, ...]:
        raise AssertionError("no discovery")

    def read_text(self, path: RepositoryPath) -> RepositoryText:
        if path.value not in self.files:
            raise WorkspaceError(WorkspaceFailure.MISSING)
        self.reads.append(path.value)
        return RepositoryText(path.value, self.files[path.value])


def request(o: Oracle) -> EvidenceRequest | None:
    if not o.request_kind:
        return None
    kind = EvidenceRequestKind(o.request_kind)
    return EvidenceRequest(
        kind,
        o.source_role or "Identify the requested governing evidence or intended option",
        RepositoryPath(o.request_path) if o.request_path else None,
    )


def ground(
    o: Oracle,
    manifest: EvidenceManifest,
    answer_identity: str,
    citations: tuple[str, ...],
    facts: dict[str, str],
) -> Grounding:
    """Fixture fact annotations, not a generic prose or LLM truth judge."""
    supplied = {f.path for f in manifest.evidence.files}
    return Grounding(
        True,
        answer_identity == manifest.identity(),
        set(citations) <= supplied,
        set(o.required_answer_evidence) <= set(citations),
        bool(o.facts) and facts == o.facts,
    )


def replay(f: Fixture, o: Oracle, variant: str, fault: Fault = Fault.CORRECT) -> Row:
    return asyncio.run(_replay(f, o, variant, fault))


async def _replay(f: Fixture, o: Oracle, variant: str, fault: Fault) -> Row:
    if variant not in f.variants:
        raise ValueError("unknown condition")
    workspace = Workspace(dict(f.files))
    model = Replay("unused")
    host, ref = host_for(model)
    allowed = tuple(
        RepositoryPath(p) for p in sorted(f.files) if p != "private/token.txt"
    )
    reader = AuthorizedRepositoryEvidence(
        ref,
        workspace,
        host.security_context(ref, REPOSITORY_READ_ACTION, ref.instance),
        host.authorization,
        allowed,
        lambda: NOW,
    )
    tenant = reader.security_context.tenant_context
    # Negative pairs are independently confirmed starting bundles, not an
    # operator silently substituting a wrong file for a named request.
    initial_paths = tuple(
        RepositoryPath(p)
        for p in sorted(
            [*f.initial, *([f.unrelated] if variant == "unrelated" else [])]
        )
    )
    evidence = await reader.acquire(initial_paths, tenant)
    r = request(o)
    declarations: tuple[GoverningSourceExpectation, ...] = ()
    if f.manifest == "wrong_binding":
        declarations = (
            GoverningSourceExpectation(
                "claimed",
                EvidenceRequest(
                    EvidenceRequestKind.SOURCE_ROLE, "declared governing source"
                ),
                (RepositoryPath(f.initial[0]),),
            ),
        )
    clarifications = (
        (EvidenceClarification("choice", r),)
        if r and r.kind is EvidenceRequestKind.OPERATOR_CLARIFICATION
        else ()
    )
    manifest = EvidenceManifest(
        f.question, evidence, "design-eval-fixture", declarations, clarifications
    )
    action_reader = (
        replace(reader, allowed_paths=initial_paths)
        if f.failure == "acquisition_denied"
        else reader
    )
    seq = EvidenceSequence(manifest, action_reader, tenant)
    attempts: list[Attempt] = []
    accepted = corrected = clarified = rejected = 0

    def submit(phase: str, expected: str, injected: Fault) -> None:
        current = seq.observe().manifest
        identity = f"{f.id}-{variant}-{phase}"
        predicted: str | None = expected
        proposed = request(o) if expected != "sufficient" else None
        if injected is Fault.FALSE_SUFFICIENT:
            predicted, proposed = "sufficient", None
        elif injected is Fault.ABSTAIN:
            predicted, proposed = (
                "missing_governing_evidence",
                EvidenceRequest(
                    EvidenceRequestKind.SOURCE_ROLE, "unspecified extra context"
                ),
            )
        elif injected is Fault.WRONG_KIND:
            predicted, proposed = (
                "unresolved_ambiguity",
                EvidenceRequest(
                    EvidenceRequestKind.OPERATOR_CLARIFICATION, "unrelated choice"
                ),
            )
        elif injected is Fault.INVENTED_PATH:
            predicted, proposed = (
                "missing_governing_evidence",
                EvidenceRequest(
                    EvidenceRequestKind.NAMED_EVIDENCE,
                    "invented",
                    RepositoryPath("private/token.txt"),
                ),
            )
        elif injected is Fault.OPERATOR_REPAIR:
            predicted, proposed = (
                "missing_governing_evidence",
                EvidenceRequest(EvidenceRequestKind.SOURCE_ROLE, "unrelated role"),
            )
        failure = None
        valid = True
        if injected in {Fault.MODEL_FAILURE, Fault.OPERATOR_ANSWER}:
            failure = "model_failure"
        elif injected is Fault.INVALID:
            failure, valid = "invalid_output", False
        elif f.failure in {"stale_assessment", "budget_exhausted"}:
            failure = f.failure
        if failure:
            result: object = EvidenceSufficiencyResult(
                failure=SufficiencyFailure(failure)
            )
            predicted = None
        else:
            try:
                assessed = (
                    replace(current, question="stale intent")
                    if injected is Fault.STALE
                    else current
                )
                if injected is Fault.STALE_EVIDENCE:
                    assessed = replace(
                        current,
                        evidence=replace(
                            current.evidence,
                            files=(
                                replace(
                                    current.evidence.files[0], text="old observation"
                                ),
                                *current.evidence.files[1:],
                            ),
                        ),
                    )
                elif injected is Fault.STALE_CLARIFICATION:
                    assessed = replace(
                        current,
                        clarifications=(
                            EvidenceClarification(
                                "old-choice",
                                EvidenceRequest(
                                    EvidenceRequestKind.OPERATOR_CLARIFICATION,
                                    "old intent",
                                ),
                                "old answer",
                            ),
                        ),
                    )
                a = EvidenceSufficiencyAssessment(
                    assessed,
                    SufficiencyDisposition(predicted),
                    "Scripted assessment, not model quality evidence",
                    (RepositoryPath(assessed.evidence.files[0].path),),
                    (proposed,) if proposed else (),
                )
                result = EvidenceSufficiencyResult(assessment=a)
            except EvidenceSufficiencyError as error:
                failure = error.reason.value
                result = EvidenceSufficiencyResult(failure=error.reason)
                predicted = None
        seq.assess(ExecutionId(identity), result)
        observed_failure = seq.observe().failure
        failure = observed_failure.value if observed_failure else failure
        attempts.append(
            Attempt(
                identity,
                phase,
                predicted,
                valid,
                proposed.kind.value if proposed else None,
                bool(
                    proposed and proposed.path and proposed.path.value == o.request_path
                ),
                bool(
                    proposed and o.source_role and proposed.description == o.source_role
                ),
                bool(
                    proposed
                    and proposed == request(o)
                    and proposed.kind is EvidenceRequestKind.OPERATOR_CLARIFICATION
                ),
                failure,
            )
        )

    def review() -> OperatorReview:
        obs = seq.observe()
        return OperatorReview(obs.manifest.identity(), obs.assessment_ids[-1], True)

    submit("initial", o.initial, fault)
    action = variant == "resolved" or f.category in {"multi_step", "operational"}
    obs = seq.observe()
    if obs.stage is Stage.REVIEW:
        assert obs.assessment is not None
        if obs.assessment.disposition is SufficiencyDisposition.SUFFICIENT:
            seq.progress(review(), obs.manifest)
        elif action:
            if f.failure == "evidence_unavailable":
                workspace.files.pop(f.addition, None)
            if fault is Fault.OPERATOR_REPAIR:
                corrected += 1
            elif f.clarification:
                clarified += 1
            else:
                accepted += 1
            if f.clarification:
                await seq.advance(
                    review(),
                    obs.manifest,
                    clarification=ClarificationSelection(
                        0, f.clarification, f.revised_question
                    ),
                )
            else:
                await seq.advance(
                    review(),
                    obs.manifest,
                    paths=(PathSelection(0, RepositoryPath(f.addition)),),
                )
            if seq.observe().stage is Stage.ASSESS:
                submit(
                    "final",
                    o.expected[variant] if f.category != "multi_step" else o.initial,
                    Fault.CORRECT,
                )
                if seq.observe().stage is Stage.REVIEW:
                    seq.progress(review(), seq.observe().manifest)
        else:
            rejected += 1
            seq.progress(replace(review(), accepted=False), obs.manifest)
    obs = seq.observe()
    eligible = obs.stage is Stage.ELIGIBLE_FOR_ANALYSIS
    grounding = Grounding(False, False, False, False, False)
    if eligible:
        seq.claim_scripted_analysis(
            ExecutionId(f"{f.id}-{variant}-answer"), obs.manifest
        )
        grounding = ground(
            o,
            obs.manifest,
            "stale" if fault is Fault.BAD_GROUNDING else obs.manifest.identity(),
            tuple(o.required_answer_evidence),
            o.facts,
        )
    permitted = {p.value for p in initial_paths} | (
        {f.addition} if action and f.addition else set()
    )
    unauthorized = sum(
        p not in permitted or p == "private/token.txt" for p in workspace.reads
    )
    assert not model.requests
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
        int(fault is Fault.OPERATOR_ANSWER),
        unauthorized + int(fault is Fault.AUTHORITY),
        int(fault is Fault.AUTHORITY),
        int(fault is Fault.AUTHORITY),
        grounding,
    )


def run(faults: dict[str, Fault] | None = None) -> tuple[Row, ...]:
    faults = faults or {}
    return tuple(
        replay(f, o, v, faults.get(f.id, Fault.CORRECT))
        for f, o in load()
        for v in f.variants
    )
