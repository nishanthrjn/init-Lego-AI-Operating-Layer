"""A/M. TaskRequest, TaskResult and TaskEvidence contracts."""

import annotationlib
import dataclasses

import pytest
from forgeai_support import task
from legoai_engineering.checks.values import CheckKind, CheckRequest, CheckResult
from legoai_engineering.coding.values import CodingTarget
from legoai_engineering.git.values import (
    GitCommitId,
    GitHead,
    GitHeadKind,
    GitRepositoryState,
)
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.workspace import RepositoryPath

from forgeai.domain import (
    CheckRecord,
    TaskDisposition,
    TaskEvidence,
    TaskFailure,
    TaskRequest,
    TaskResult,
)

TARGET = CodingTarget(RepositoryPath("src/a.py"), FileChangeKind.UPDATE)
CHECK = CheckRequest(CheckKind.PYTEST, (RepositoryPath("tests"),))
HEAD = GitHead(GitHeadKind.ATTACHED, "main", GitCommitId("ab" * 20))


def test_task_request_carries_intent_only() -> None:
    names = {item.name for item in dataclasses.fields(TaskRequest)}
    assert names == {"objective", "targets", "constraints"}
    assert "objective" not in repr(task())


@pytest.mark.parametrize(
    ("objective", "targets", "constraints"),
    [
        ("", (TARGET,), ()),
        ("   ", (TARGET,), ()),
        ("x" * 2049, (TARGET,), ()),
        ("fix", (), ()),
        ("fix", (TARGET,) * 9, ()),
        ("fix", (TARGET, TARGET), ()),
        (
            "fix",
            (
                CodingTarget(RepositoryPath("src/A.py"), FileChangeKind.UPDATE),
                CodingTarget(RepositoryPath("src/a.py"), FileChangeKind.CREATE),
            ),
            (),
        ),
        (
            "fix",
            (
                CodingTarget(RepositoryPath("src"), FileChangeKind.UPDATE),
                TARGET,
            ),
            (),
        ),
        ("fix", (TARGET,), ("c",) * 9),
        ("fix", (TARGET,), ("",)),
    ],
)
def test_task_request_bounds(
    objective: str, targets: tuple[CodingTarget, ...], constraints: tuple[str, ...]
) -> None:
    with pytest.raises(ValueError):
        TaskRequest(objective, targets, constraints)


def test_task_request_types() -> None:
    with pytest.raises(TypeError):
        TaskRequest(b"fix", (TARGET,))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        TaskRequest("fix", ("src/a.py",))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        TaskRequest("fix", [TARGET])  # type: ignore[arg-type]


def evidence(**changes: object) -> TaskEvidence:
    return dataclasses.replace(
        TaskEvidence("run-1", planned_checks=(CHECK,)),
        **changes,  # type: ignore[arg-type]
    )


def test_result_disposition_matches_failure_step() -> None:
    TaskResult(task(), TaskDisposition.REJECTED, TaskFailure.DIRTY_START, evidence())
    with pytest.raises(ValueError):
        TaskResult(task(), TaskDisposition.FAILED, TaskFailure.DIRTY_START, evidence())
    with pytest.raises(ValueError):
        TaskResult(
            task(), TaskDisposition.REJECTED, TaskFailure.CHECKS_FAILED, evidence()
        )
    with pytest.raises(TypeError):
        TaskResult(task(), TaskDisposition.FAILED, None, evidence())


def test_success_cannot_be_claimed_without_passed_checks() -> None:
    state = GitRepositoryState(HEAD, ())
    failing = CheckRecord(CHECK, CheckResult(CheckKind.PYTEST, 1, b"", b""))
    for record in ((), (failing,)):
        with pytest.raises(ValueError):
            TaskResult(
                task(),
                TaskDisposition.SUCCEEDED,
                None,
                evidence(start=state, final=state, checks=record),
            )


def test_rejection_cannot_carry_effect_evidence() -> None:
    record = CheckRecord(CHECK, CheckResult(CheckKind.PYTEST, 0, b"", b""))
    with pytest.raises(ValueError):
        TaskResult(
            task(),
            TaskDisposition.REJECTED,
            TaskFailure.DIRTY_START,
            evidence(checks=(record,)),
        )


def test_evidence_is_bounded_and_ordered() -> None:
    with pytest.raises(ValueError):
        TaskEvidence("run", planned_checks=(CHECK,) * 9)
    other = CheckRequest(CheckKind.MYPY, (RepositoryPath("src"),))
    with pytest.raises(ValueError):
        TaskEvidence(
            "run",
            planned_checks=(CHECK,),
            checks=(CheckRecord(other, CheckResult(CheckKind.MYPY, 0, b"", b"")),),
        )
    with pytest.raises(ValueError):
        TaskEvidence("", planned_checks=(CHECK,))
    with pytest.raises(ValueError):
        CheckRecord(CHECK, None)
    with pytest.raises(ValueError):
        CheckRecord(CHECK, CheckResult(CheckKind.MYPY, 0, b"", b""))


def test_evidence_holds_only_values_not_runtime_objects() -> None:
    allowed = (
        "str",
        "GitRepositoryState | None",
        "GitFailure | None",
        "CodingStatus | None",
        "AcquisitionFailure | None",
        "AgentExecutionStatus | None",
        "EffectExtent | None",
        "CodingProposal | None",
        "RepositoryMutationResult | None",
        "EffectAuthorizationFailure | None",
        "MutationConflictReason | None",
        "RepositoryPath | None",
        "tuple[RepositoryPath, ...]",
        "tuple[CheckRequest, ...]",
        "tuple[CheckRecord, ...]",
        "tuple[str, ...]",
        "ReviewInputFailure | None",
        "tuple[tuple[str, RepositoryPath], ...]",
        "ReviewResult | None",
    )
    annotations = annotationlib.get_annotations(
        TaskEvidence, format=annotationlib.Format.STRING
    )
    assert set(annotations) == {item.name for item in dataclasses.fields(TaskEvidence)}
    for name, annotation in annotations.items():
        assert annotation in allowed, name


def passed_evidence(**changes: object) -> TaskEvidence:
    from legoai_engineering.git.values import GitChange, GitStatusEntry
    from legoai_engineering.repository.mutation import (
        FileChangeKind as Kind,
    )
    from legoai_engineering.repository.mutation import (
        FileChangeResult,
        RepositoryMutationResult,
        digest_text,
    )

    path = RepositoryPath("src/a.py")
    applied = RepositoryMutationResult(
        (FileChangeResult(path, Kind.UPDATE, digest_text("a"), digest_text("b")),)
    )
    entry = GitStatusEntry(path, GitChange.UNCHANGED, GitChange.MODIFIED, False)
    return evidence(
        start=GitRepositoryState(HEAD, ()),
        final=GitRepositoryState(HEAD, (entry,)),
        applied=applied,
        checks=(CheckRecord(CHECK, CheckResult(CheckKind.PYTEST, 0, b"", b"")),),
        **changes,
    )


def test_success_requires_a_completed_accept_review() -> None:
    gated = passed_evidence()
    assert gated.gates_passed and gated.review_decision is None
    with pytest.raises(ValueError):
        TaskResult(task(), TaskDisposition.SUCCEEDED, None, gated)


def test_review_evidence_requires_every_deterministic_gate() -> None:
    from forgeai.domain import ReviewInputFailure

    failure = ReviewInputFailure.MATERIAL_BOUNDS
    TaskResult(
        task(),
        TaskDisposition.FAILED,
        TaskFailure.REVIEW_INPUT_FAILED,
        passed_evidence(review_input_failure=failure),
    )
    with pytest.raises(ValueError):
        TaskResult(
            task(),
            TaskDisposition.FAILED,
            TaskFailure.REVIEW_INPUT_FAILED,
            evidence(review_input_failure=failure),
        )
