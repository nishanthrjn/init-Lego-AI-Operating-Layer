"""Scripted end-to-end operator flows over the real authorized evidence wrapper."""

import ast
import asyncio
from dataclasses import replace
from pathlib import Path

import pytest
from analyst_evidence_loop import sequence
from analyst_evidence_loop.sequence import (
    ClarificationSelection,
    EvidenceSequence,
    OperatorReview,
    PathSelection,
    Stage,
    StopReason,
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

from legoai.execution.values import ExecutionId
from legoai.governance.ports import (
    AuthorizationDecision,
    AuthorizationOutcome,
    AuthorizationPort,
    SecurityContext,
)
from legoai.kernel.errors import ErrorCategory


class Workspace:
    def __init__(self, files: dict[str, str], events: list[str]) -> None:
        self.files = files
        self.events = events
        self.error: Exception | None = None

    def list_entries(
        self, directory: RepositoryPath | None
    ) -> tuple[WorkspaceEntry, ...]:
        raise AssertionError("no discovery is permitted")

    def read_text(self, path: RepositoryPath) -> RepositoryText:
        self.events.append("read:" + path.value)
        if self.error is not None:
            raise self.error
        if path.value not in self.files:
            raise WorkspaceError(WorkspaceFailure.MISSING)
        return RepositoryText(path.value, self.files[path.value])


class Authority:
    def __init__(self, inner: AuthorizationPort, events: list[str]) -> None:
        self.inner, self.events = inner, events
        self.calls = 0
        self.deny_at: int | None = None
        self.contexts: list[SecurityContext] = []

    def evaluate(self, context: SecurityContext) -> AuthorizationDecision:
        self.calls += 1
        self.events.append("authorize")
        self.contexts.append(context)
        if self.deny_at == self.calls:
            return AuthorizationDecision(
                AuthorizationOutcome.DENIED,
                context.operation,
                context.established_at,
                ErrorCategory.AUTHORIZATION_DENIED,
                None,
                None,
                context.policy_ref,
            )
        return self.inner.evaluate(context)


def setup(
    files: dict[str, str] | None = None,
    initial: tuple[str, ...] = ("caller.py",),
    *,
    expectations: tuple[GoverningSourceExpectation, ...] = (),
    clarifications: tuple[EvidenceClarification, ...] = (),
    allowed: tuple[str, ...] | None = None,
) -> tuple[EvidenceSequence, Workspace, Authority, Replay]:
    files = files or {
        "caller.py": "Messages live in a catalog",
        "catalog.json": "declined",
        "extra.py": "other",
    }
    events: list[str] = []
    workspace = Workspace(files, events)
    replay = Replay("not called")
    host, ref = host_for(replay)
    authority = Authority(host.authorization, events)
    reader = AuthorizedRepositoryEvidence(
        ref,
        workspace,
        host.security_context(ref, REPOSITORY_READ_ACTION, ref.instance),
        authority,
        tuple(RepositoryPath(p) for p in (allowed or tuple(sorted(files)))),
        lambda: NOW,
    )
    tenant = reader.security_context.tenant_context
    evidence = asyncio.run(
        reader.acquire(tuple(RepositoryPath(p) for p in initial), tenant)
    )
    manifest = EvidenceManifest(
        "Make the timeout longer",
        evidence,
        "scripted-workspace",
        expectations,
        clarifications,
    )
    events.clear()
    authority.calls = 0
    authority.contexts.clear()
    return EvidenceSequence(manifest, reader, tenant), workspace, authority, replay


def role() -> EvidenceRequest:
    return EvidenceRequest(
        EvidenceRequestKind.SOURCE_ROLE,
        "Catalog governing declined-card customer messages",
    )


def named(path: str = "catalog.json") -> EvidenceRequest:
    return EvidenceRequest(
        EvidenceRequestKind.NAMED_EVIDENCE,
        "Governing implementation",
        RepositoryPath(path),
    )


def ambiguity() -> EvidenceRequest:
    return EvidenceRequest(
        EvidenceRequestKind.OPERATOR_CLARIFICATION,
        "Which timeout?",
        choices=("database pool", "network read"),
    )


def assess(
    s: EvidenceSequence,
    disposition: SufficiencyDisposition = SufficiencyDisposition.SUFFICIENT,
    requests: tuple[EvidenceRequest, ...] = (),
    identity: str = "a1",
) -> None:
    m = s.observe().manifest
    try:
        a = EvidenceSufficiencyAssessment(
            m,
            disposition,
            "Scripted unverified claim",
            (RepositoryPath(m.evidence.files[0].path),),
            requests,
        )
        result = EvidenceSufficiencyResult(assessment=a)
    except EvidenceSufficiencyError as error:
        result = EvidenceSufficiencyResult(failure=error.reason)
    s.assess(ExecutionId(identity), result)


def review(s: EvidenceSequence, accepted: bool = True) -> OperatorReview:
    o = s.observe()
    return OperatorReview(o.manifest.identity(), o.assessment_ids[-1], accepted)


def acquire(s: EvidenceSequence, *paths: str) -> None:
    asyncio.run(
        s.advance(
            review(s),
            s.observe().manifest,
            paths=tuple(
                PathSelection(i, RepositoryPath(p)) for i, p in enumerate(paths)
            ),
        )
    )


def finish(s: EvidenceSequence) -> None:
    s.progress(review(s), s.observe().manifest)


def test_directly_sufficient() -> None:
    s, w, _, model = setup()
    assess(s)
    assert s.observe().stage is Stage.REVIEW
    finish(s)
    o = s.observe()
    assert o.stage is Stage.ELIGIBLE_FOR_ANALYSIS and o.rounds == 0
    assert len(o.reviews) == 1 and o.reviews[0].accepted
    assert not w.events and not model.requests
    assert not o.analysis_ids  # eligibility does not dispatch analysis


def test_source_role_acquisition() -> None:
    request = role()
    s, w, auth, model = setup(
        expectations=(GoverningSourceExpectation("catalog", request),)
    )
    initial = s.observe().manifest
    assess(s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (request,))
    old = s.observe().assessment
    assert old is not None and old.requests[0].path is None and not w.events
    acquire(s, "catalog.json")
    revised = s.observe().manifest
    assert revised.identity() != initial.identity()
    assert (
        initial.missing_expectations() == ("catalog",)
        and not revised.missing_expectations()
    )
    with pytest.raises(EvidenceSufficiencyError, match="stale_assessment"):
        old.validate_for(revised)
    assert w.events == ["authorize", "read:catalog.json", "authorize"]
    assert all(c.action == REPOSITORY_READ_ACTION for c in auth.contexts)
    assess(s, identity="a2")
    assert s.observe().stage is Stage.REVIEW
    finish(s)
    o = s.observe()
    assert o.stage is Stage.ELIGIBLE_FOR_ANALYSIS and o.rounds == 1
    assert len(o.assessments) == 2 and len(o.reviews) == 2
    assert o.round_record is not None and o.round_record.before == initial.identity()
    assert o.round_record.paths[0].path.value == "catalog.json"
    assert not model.requests


def test_operator_clarification() -> None:
    request = ambiguity()
    s, w, _, _ = setup(clarifications=(EvidenceClarification("timeout", request),))
    initial = s.observe().manifest
    assess(s, SufficiencyDisposition.UNRESOLVED_AMBIGUITY, (request,))
    asyncio.run(
        s.advance(
            review(s),
            initial,
            clarification=ClarificationSelection(
                0, "database pool", "Make the database pool timeout longer"
            ),
        )
    )
    revised = s.observe().manifest
    assert (
        revised.question != initial.question
        and revised.identity() != initial.identity()
    )
    assert revised.clarifications[0].answer == "database pool"
    assert initial.clarifications[0].answer is None
    assess(s, identity="a2")
    finish(s)
    assert s.observe().stage is Stage.ELIGIBLE_FOR_ANALYSIS and not w.events


@pytest.mark.parametrize(
    "deny_at,reads",
    [(1, []), (2, ["read:catalog.json"]), (3, ["read:catalog.json", "read:extra.py"])],
)
def test_current_authority_each_read_and_release(
    deny_at: int, reads: list[str]
) -> None:
    s, w, auth, _ = setup()
    initial = s.observe().manifest
    assess(
        s,
        SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE,
        (named(), named("extra.py")),
    )
    auth.deny_at = deny_at
    acquire(s, "catalog.json", "extra.py")
    o = s.observe()
    assert (
        o.failure is SufficiencyFailure.ACQUISITION_DENIED and o.stage is Stage.STOPPED
    )
    assert o.manifest == initial and len(o.assessment_ids) == 1
    assert [e for e in w.events if e.startswith("read:")] == reads
    previous = list(w.events)
    acquire(s, "catalog.json")
    assert w.events == previous


def test_named_request_no_authority() -> None:
    s, w, _, _ = setup(allowed=("caller.py",))
    assess(s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (named(),))
    assert not w.events
    acquire(s, "catalog.json")
    assert s.observe().failure is SufficiencyFailure.ACQUISITION_DENIED and not w.events


@pytest.mark.parametrize(
    "failure,expected",
    [
        (WorkspaceFailure.MISSING, SufficiencyFailure.EVIDENCE_UNAVAILABLE),
        (WorkspaceFailure.BOUNDARY, SufficiencyFailure.AUTHORIZATION_FAILURE),
        (WorkspaceFailure.LIMIT, SufficiencyFailure.BUDGET_EXHAUSTED),
    ],
)
def test_acquisition_failures(
    failure: WorkspaceFailure, expected: SufficiencyFailure
) -> None:
    s, w, _, _ = setup()
    assess(s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (named(),))
    w.error = WorkspaceError(failure)
    acquire(s, "catalog.json")
    assert s.observe().failure is expected and w.events == [
        "authorize",
        "read:catalog.json",
    ]


def test_still_insufficient_stops() -> None:
    s, w, _, _ = setup()
    assess(s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (named(),))
    acquire(s, "catalog.json")
    assess(
        s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (named("extra.py"),), "a2"
    )
    assert (
        s.observe().stage is Stage.STOPPED
        and s.observe().stop_reason is StopReason.UNRESOLVED
    )
    before = list(w.events)
    acquire(s, "extra.py")
    assert w.events == before and s.observe().rounds == 1


def test_second_round_forbidden() -> None:
    s, w, _, _ = setup()
    assess(s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (named(),))
    acquire(s, "catalog.json")
    before = list(w.events)
    acquire(s, "extra.py")
    assert (
        s.observe().failure is SufficiencyFailure.BUDGET_EXHAUSTED
        and w.events == before
    )


@pytest.mark.parametrize("change", ["question", "content", "evidence"])
def test_stale_progression(change: str) -> None:
    s, w, _, _ = setup()
    assess(s)
    current = s.observe().manifest
    fresh_file = replace(
        current.evidence.files[0],
        text="changed",
        path="other.py" if change == "evidence" else "caller.py",
    )
    changed = (
        replace(current, question="Different intent")
        if change == "question"
        else replace(current, evidence=replace(current.evidence, files=(fresh_file,)))
    )
    s.progress(review(s), changed)
    assert s.observe().failure is SufficiencyFailure.STALE_ASSESSMENT and not w.events


def test_stale_reassessment_and_review() -> None:
    s, _, _, _ = setup()
    assess(s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (named(),))
    old, consent = s.observe().assessment, review(s)
    acquire(s, "catalog.json")
    s.assess(ExecutionId("a2"), EvidenceSufficiencyResult(assessment=old))
    assert s.observe().failure is SufficiencyFailure.STALE_ASSESSMENT
    s2, _, _, _ = setup()
    assess(s2)
    s2.progress(
        replace(consent, assessment_id=ExecutionId("unrelated")), s2.observe().manifest
    )
    assert s2.observe().failure is SufficiencyFailure.STALE_ASSESSMENT


def test_unrelated_evidence_cannot_resolve_ambiguity() -> None:
    request = ambiguity()
    s, _, _, _ = setup(clarifications=(EvidenceClarification("timeout", request),))
    assess(s, SufficiencyDisposition.UNRESOLVED_AMBIGUITY, (named("extra.py"), request))
    acquire(s, "extra.py")
    assert s.observe().manifest.clarifications[0].answer is None
    assess(s, identity="a2")
    assert s.observe().failure is SufficiencyFailure.PREREQUISITES_UNMET


def test_cumulative_file_limit() -> None:
    # Seven selected plus two requested; reader itself remains limited to eight.
    files = {f"{i}.py": "x" for i in range(9)}
    s, w, _, _ = setup(
        files,
        tuple(f"{i}.py" for i in range(7)),
        allowed=tuple(f"{i}.py" for i in range(8)),
    )
    assess(
        s,
        SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE,
        (named("7.py"), named("8.py")),
    )
    acquire(s, "7.py", "8.py")
    assert s.observe().failure is SufficiencyFailure.BUDGET_EXHAUSTED and not w.events


@pytest.mark.parametrize("extra", ["x" * 1000, "x" * 8193, "é" * 4097])
def test_cumulative_byte_limit(extra: str) -> None:
    files = {
        "a.py": "x" * 8000,
        "b.py": "x" * 8000,
        "c.py": "x" * 8000,
        "extra.py": extra,
    }
    s, _, _, _ = setup(files, ("a.py", "b.py", "c.py"))
    before = s.observe().manifest
    assess(s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (named("extra.py"),))
    acquire(s, "extra.py")
    assert (
        s.observe().failure is SufficiencyFailure.BUDGET_EXHAUSTED
        and s.observe().manifest == before
    )


def test_question_bound() -> None:
    for question in ("", "x" * 2049, "é" * 1025, "\ud800"):
        with pytest.raises(ValueError):
            ClarificationSelection(0, "answer", question)
    assert len(ClarificationSelection(0, "answer", "x" * 2048).question) == 2048


def test_cumulative_exact_limits_and_unselected_files() -> None:
    files = {f"{i}.py": "x" * 3072 for i in range(8)}
    files["hidden.py"] = "never selected"
    selected = tuple(f"{i}.py" for i in range(8))
    s, w, _, _ = setup(files, selected[:7], allowed=selected)
    assess(s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (named("7.py"),))
    acquire(s, "7.py")
    assess(s, identity="a2")
    finish(s)
    o = s.observe()
    assert o.stage is Stage.ELIGIBLE_FOR_ANALYSIS
    assert len(o.manifest.evidence.files) == 8
    assert sum(len(f.text.encode()) for f in o.manifest.evidence.files) == 24576
    assert w.events == ["authorize", "read:7.py", "authorize"]


def test_assessment_call_ceiling() -> None:
    s, _, _, _ = setup()
    assess(s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (named(),))
    acquire(s, "catalog.json")
    assess(s, identity="a2")
    assess(s, identity="a3")
    assert (
        len(s.observe().assessment_ids) == 2
        and s.observe().failure is SufficiencyFailure.BUDGET_EXHAUSTED
    )


def test_analysis_call_ceiling() -> None:
    s, _, _, model = setup()
    assess(s)
    finish(s)
    s.claim_scripted_analysis(ExecutionId("final1"), s.observe().manifest)
    s.claim_scripted_analysis(ExecutionId("final2"), s.observe().manifest)
    assert (
        len(s.observe().analysis_ids) == 1
        and s.observe().failure is SufficiencyFailure.BUDGET_EXHAUSTED
    )
    assert not model.requests


@pytest.mark.parametrize("at", ["assessment", "analysis"])
def test_duplicate_invocation_rejected(at: str) -> None:
    s, _, _, _ = setup()
    if at == "assessment":
        assess(s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (named(),))
        acquire(s, "catalog.json")
        assess(s, identity="a1")
    else:
        assess(s)
        finish(s)
        s.claim_scripted_analysis(ExecutionId("a1"), s.observe().manifest)
    assert s.observe().stop_reason is StopReason.DUPLICATE_INVOCATION
    assert (
        s.observe().assessment_ids == (ExecutionId("a1"),)
        and not s.observe().analysis_ids
    )


@pytest.mark.parametrize("failure", list(SufficiencyFailure))
def test_operational_failure_no_retry(failure: SufficiencyFailure) -> None:
    s, w, _, _ = setup()
    s.assess(ExecutionId("a1"), EvidenceSufficiencyResult(failure=failure))
    assess(s, identity="a2")
    assert s.observe().failure is failure and s.observe().stage is Stage.STOPPED
    assert len(s.observe().assessment_ids) == 1 and not w.events


def test_invalid_assessment_output() -> None:
    s, _, _, _ = setup()
    s.assess(ExecutionId("a1"), {"sufficient": True})
    assert s.observe().failure is SufficiencyFailure.INVALID_OUTPUT


@pytest.mark.parametrize(
    "case",
    [
        "role_without_path",
        "named_wrong_path",
        "clarification_read",
        "mixed",
        "unrequested",
        "existing",
        "duplicate",
    ],
)
def test_operator_selection_validation(case: str) -> None:
    s, w, _, _ = setup()
    requests = (
        (ambiguity(),)
        if case == "clarification_read"
        else (role(),)
        if case in {"role_without_path", "existing"}
        else (named(),)
    )
    assess(
        s,
        SufficiencyDisposition.UNRESOLVED_AMBIGUITY
        if case == "clarification_read"
        else SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE,
        requests,
    )
    paths: tuple[PathSelection, ...] = (
        ()
        if case == "role_without_path"
        else (
            PathSelection(
                7 if case == "unrequested" else 0,
                RepositoryPath(
                    "extra.py"
                    if case == "named_wrong_path"
                    else "caller.py"
                    if case == "existing"
                    else "catalog.json"
                ),
            ),
        )
    )
    if case == "duplicate":
        paths *= 2
    asyncio.run(
        s.advance(
            review(s),
            s.observe().manifest,
            paths=paths,
            clarification=ClarificationSelection(0, "answer", "question")
            if case == "mixed"
            else None,
        )
    )
    assert s.observe().stop_reason is StopReason.INVALID_REVIEW and not w.events


def test_operator_decline_and_final_review_required() -> None:
    s, w, _, _ = setup()
    assess(s)
    s.progress(review(s, False), s.observe().manifest)
    assert s.observe().stop_reason is StopReason.OPERATOR_DECLINED and not w.events
    s2, _, _, _ = setup()
    assess(s2)
    s2.claim_scripted_analysis(ExecutionId("final"), s2.observe().manifest)
    assert s2.observe().stage is Stage.STOPPED and not s2.observe().analysis_ids


def test_no_target_promotion_and_safe_observation() -> None:
    s, _, _, _ = setup()
    assess(s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (named(),))
    acquire(s, "catalog.json")
    assess(s, identity="a2")
    finish(s)
    o = s.observe()
    for name in (
        "targets",
        "edit_targets",
        "changeset",
        "mutation",
        "coding",
        "reviewer",
    ):
        assert not hasattr(o, name) and not hasattr(s, name)
    assert "catalog" not in repr(o) and "timeout" not in repr(o)


@pytest.mark.parametrize(
    "error", [RuntimeError("adapter bug"), TypeError("adapter contract bug")]
)
def test_unexpected_read_failure_stops_and_preserves_cause(error: Exception) -> None:
    s, w, _, _ = setup()
    assess(s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (named(),))
    w.error = error
    with pytest.raises(type(error)) as caught:
        acquire(s, "catalog.json")
    assert caught.value is error and s.observe().stage is Stage.STOPPED


def test_architecture_guards() -> None:
    tree = ast.parse(Path(sequence.__file__).read_text(encoding="utf-8"))
    modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert modules == {
        "dataclasses",
        "enum",
        "legoai.execution.values",
        "legoai.kernel.context",
        "legoai_engineering.analyst.api",
        "legoai_engineering.analyst.authorized",
        "legoai_engineering.analyst.sufficiency",
        "legoai_engineering.analyst.values",
        "legoai_engineering.repository.workspace",
    }
    assert not any(isinstance(n, (ast.Import, ast.While)) for n in ast.walk(tree))
    forbidden = {
        "open",
        "eval",
        "exec",
        "__import__",
        "walk",
        "glob",
        "rglob",
        "read_text",
        "list_entries",
        "chat",
        "analyze",
        "mutate",
        "apply",
    }
    assert not any(
        isinstance(n, ast.Call)
        and (
            (isinstance(n.func, ast.Name) and n.func.id in forbidden)
            or (isinstance(n.func, ast.Attribute) and n.func.attr in forbidden)
        )
        for n in ast.walk(tree)
    )
    assert (
        sum(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "acquire"
            for n in ast.walk(tree)
        )
        == 1
    )
    assert not any(
        isinstance(n, ast.ClassDef) and n.name in {"Workflow", "Team", "Planner"}
        for n in ast.walk(tree)
    )


def test_stale_action_and_analysis_claim() -> None:
    s, w, _, _ = setup()
    assess(s, SufficiencyDisposition.MISSING_GOVERNING_EVIDENCE, (named(),))
    changed = replace(s.observe().manifest, question="Changed intent")
    asyncio.run(
        s.advance(
            review(s),
            changed,
            paths=(PathSelection(0, RepositoryPath("catalog.json")),),
        )
    )
    assert s.observe().failure is SufficiencyFailure.STALE_ASSESSMENT and not w.events
    s2, _, _, _ = setup()
    assess(s2)
    finish(s2)
    s2.claim_scripted_analysis(ExecutionId("final"), changed)
    assert s2.observe().failure is SufficiencyFailure.STALE_ASSESSMENT
    assert not s2.observe().analysis_ids


def test_cannot_bypass_authorized_composition() -> None:
    s, w, _, _ = setup()
    from legoai.kernel.context import TenantContext
    from legoai.kernel.identity import TenantId

    with pytest.raises(TypeError, match="authorized evidence"):
        EvidenceSequence(s.observe().manifest, w, TenantContext(TenantId("test")))  # type: ignore[arg-type]
