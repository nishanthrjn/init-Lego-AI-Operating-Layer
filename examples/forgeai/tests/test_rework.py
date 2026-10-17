"""ForgeAI-3 bounded one-cycle rework (A-R): trigger, ceilings, terminal review.

Real public host, Git, mutation, authorized reads, Coding Agent and reviewer;
fake sandbox. Replay outputs are consumed strictly in call order:
coding-1, review-1, coding-2, review-2. A fifth call has no recorded output
and would fail loudly.
"""

import asyncio
import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    REVIEW_CHANGES,
    REVIEW_INSUFFICIENT,
    REWORK,
    Clock,
    FakeSandbox,
    LoggedReplay,
    approve,
    config,
    logged_run,
    proposal,
    repository,
    task,
)
from legoai.intelligence.model.ports import ModelPreflightError
from legoai.kernel.effects import EffectExtent
from legoai_engineering.analyst.authorized import REPOSITORY_READ_ACTION
from legoai_engineering.repository.mutation import (
    FileChangeKind,
    RepositoryChangeSet,
    RepositoryMutationResult,
    digest_text,
)
from legoai_engineering.repository.mutation_authorized import (
    REPOSITORY_MUTATION_ACTION,
)
from legoai_engineering.repository.mutation_errors import (
    MutationConflict,
    MutationConflictReason,
)
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.reviewer.values import ReviewDecision

from forgeai.composition import prepare_run
from forgeai.domain import (
    MAX_ATTEMPTS,
    AttemptEvidence,
    TaskDisposition,
    TaskEvidence,
    TaskFailure,
)
from forgeai.guard import WorkspaceGuard

REWORKED = (proposal(), REVIEW_CHANGES, REWORK)
TESTS = "tests/test_stock.py"


def calls(log: list[str]) -> dict[str, int]:
    return {name: log.count(name) for name in ("model", "apply", "check")}


# --- A/S. ACCEPT on review #1: unchanged ForgeAI-2 path, no rework -----------


def test_first_review_accept_needs_no_rework(tmp_path: Path) -> None:
    result, model, log, _, _ = logged_run(
        repository(tmp_path), proposal(), REVIEW_ACCEPT
    )
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert calls(log) == {"model": 2, "apply": 1, "check": 3}
    assert len(result.evidence.attempts) == 1 and not result.evidence.reworked


# --- B/P/R. CHANGES_REQUIRED then ACCEPT: exactly four calls -----------------


def test_rework_then_accept_succeeds_within_exact_ceilings(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, model, log, _, _ = logged_run(root, *REWORKED, REVIEW_ACCEPT)
    assert result.disposition is TaskDisposition.SUCCEEDED, result
    assert calls(log) == {"model": 4, "apply": 2, "check": 6}
    assert log == [
        "model",
        "apply",
        *["check"] * 3,
        "model",
        "model",
        "apply",
        *["check"] * 3,
        "model",
    ]
    first, second = result.evidence.attempts
    assert (first.number, second.number) == (1, 2)
    assert first.review_decision is ReviewDecision.CHANGES_REQUIRED
    assert second.review_decision is ReviewDecision.ACCEPT
    assert first.applied is not None and second.applied is not None
    assert [c.path.value for c in second.applied.applied] == [TESTS]
    # One run id; each model call used its own execution context.
    assert first.review is not None and second.review is not None
    contexts = {
        result.evidence.run_id,
        first.review.request.context.execution_id.value,
        second.review.request.context.execution_id.value,
    }
    assert len(contexts) == 3
    assert "match=message" in (root / TESTS).read_text(encoding="utf-8")
    assert [p.value for p in result.evidence.changed_paths] == [
        "src/inventory/stock.py",
        TESTS,
    ]


# --- C/D/Q. Review #2 is terminal: no fifth call ------------------------------


@pytest.mark.parametrize(
    ("final", "failure"),
    [
        (REVIEW_CHANGES, TaskFailure.REVIEW_CHANGES_REQUIRED),
        (REVIEW_INSUFFICIENT, TaskFailure.REVIEW_INSUFFICIENT_EVIDENCE),
        ("not json", TaskFailure.REVIEW_OUTPUT_INVALID),
        (ModelPreflightError("refused"), TaskFailure.REVIEW_FAILED),
    ],
    ids=["changes-required", "insufficient", "invalid", "model-failure"],
)
def test_second_review_is_terminal(
    tmp_path: Path, final: str | Exception, failure: TaskFailure
) -> None:
    root = repository(tmp_path)
    result, model, log, _, _ = logged_run(root, *REWORKED, final)
    assert result.disposition is TaskDisposition.FAILED
    assert result.failure is failure
    assert model.calls == 4 and calls(log)["apply"] == 2
    assert result.evidence.reworked
    # Nothing reverted: both attempts' changes stay in the working tree.
    assert "match=message" in (root / TESTS).read_text(encoding="utf-8")


# --- E/F. No rework unless review #1 completed with CHANGES_REQUIRED ----------


@pytest.mark.parametrize(
    ("review", "failure"),
    [
        (REVIEW_INSUFFICIENT, TaskFailure.REVIEW_INSUFFICIENT_EVIDENCE),
        ("not json", TaskFailure.REVIEW_OUTPUT_INVALID),
        (ModelPreflightError("refused"), TaskFailure.REVIEW_FAILED),
    ],
    ids=["insufficient", "invalid", "model-failure"],
)
def test_no_rework_after_other_first_review_outcomes(
    tmp_path: Path, review: str | Exception, failure: TaskFailure
) -> None:
    result, model, log, _, _ = logged_run(
        repository(tmp_path), proposal(), review, REWORK
    )
    assert result.failure is failure
    assert model.calls == 2 and calls(log)["apply"] == 1
    assert len(result.evidence.attempts) == 1


def test_no_rework_after_deterministic_failure(tmp_path: Path) -> None:
    # A check execution failure (mypy exit 2 = ERROR), not a code finding:
    # never a rework (v0.1 reworks only on completed code findings).
    result, model, log, _, _ = logged_run(
        repository(tmp_path), *REWORKED, REVIEW_ACCEPT, exits=(0, 2, 0)
    )
    assert result.failure is TaskFailure.CHECKS_FAILED
    assert model.calls == 1 and len(result.evidence.attempts) == 1
    assert result.evidence.rework_trigger is None


# --- G/H. Rework proposal failures are terminal --------------------------------


@pytest.mark.parametrize(
    ("rework", "failure", "effect"),
    [
        ("not a proposal", TaskFailure.PROPOSAL_INVALID, EffectExtent.COMPLETED),
        (ModelPreflightError("refused"), TaskFailure.MODEL_FAILED, EffectExtent.NONE),
    ],
    ids=["invalid", "model-failure"],
)
def test_rework_proposal_failure_is_terminal(
    tmp_path: Path, rework: str | Exception, failure: TaskFailure, effect: EffectExtent
) -> None:
    root = repository(tmp_path)
    result, model, log, _, _ = logged_run(
        root, proposal(), REVIEW_CHANGES, rework, REVIEW_ACCEPT
    )
    assert result.failure is failure and result.disposition is TaskDisposition.FAILED
    assert model.calls == 3 and calls(log) == {"model": 3, "apply": 1, "check": 3}
    second = result.evidence.attempts[1]
    assert second.model_effect is effect and second.applied is None
    # Attempt 1's applied changes remain; nothing was reverted.
    stock = (root / "src/inventory/stock.py").read_text(encoding="utf-8")
    assert "requested units must be positive" in stock
    assert "match=message" not in (root / TESTS).read_text(encoding="utf-8")


# --- I. Second mutation failure is terminal -------------------------------------


def test_second_mutation_failure_is_terminal(tmp_path: Path) -> None:
    root = repository(tmp_path)
    log: list[str] = []
    model = LoggedReplay(log, *REWORKED, REVIEW_ACCEPT)
    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        confirm_context=lambda inventory: True,
        approve=approve,
        sandbox=FakeSandbox(),
    )
    inner = prepared.worker.mutation

    class FailSecond:
        calls = 0

        def apply(self, changeset: RepositoryChangeSet) -> RepositoryMutationResult:
            FailSecond.calls += 1
            if FailSecond.calls == 2:
                raise MutationConflict(
                    MutationConflictReason.STALE, RepositoryPath(TESTS)
                )
            return inner.apply(changeset)

    worker = replace(prepared.worker, mutation=FailSecond())
    result = asyncio.run(worker.run(task(), prepared.context))
    assert result.failure is TaskFailure.MUTATION_CONFLICT
    assert FailSecond.calls == 2 and model.calls == 3
    assert result.evidence.attempts[1].conflict is MutationConflictReason.STALE
    assert result.evidence.attempts[1].final is not None


def test_denied_second_mutation_after_grant_expiry(tmp_path: Path) -> None:
    root = repository(tmp_path)
    clock = Clock()
    cfg = _expiring(root, clock, REPOSITORY_MUTATION_ACTION)
    result, model, log, _, _ = logged_run(
        root,
        *REWORKED,
        REVIEW_ACCEPT,
        cfg=cfg,
        clock=clock,
        advance=True,
        advance_after=2,
    )
    assert result.failure is TaskFailure.MUTATION_DENIED
    assert model.calls == 3 and calls(log)["apply"] == 2
    second = result.evidence.attempts[1]
    assert second.mutation_denial is not None and second.applied is None


# --- J. Second checks fail: no review #2 ---------------------------------------


def test_second_check_failure_stops_before_review_two(tmp_path: Path) -> None:
    result, model, log, _, _ = logged_run(
        repository(tmp_path),
        *REWORKED,
        REVIEW_ACCEPT,
        exits=(0, 0, 0, 0, 0, 1),
    )
    assert result.failure is TaskFailure.CHECKS_FAILED
    assert model.calls == 3 and calls(log)["check"] == 6
    assert result.evidence.attempts[1].review is None


# --- K. Final Git integrity failure after rework: no review #2 ------------------


def test_rework_unexpected_change_stops_before_review_two(tmp_path: Path) -> None:
    root = repository(tmp_path)
    log: list[str] = []
    model = LoggedReplay(log, *REWORKED, REVIEW_ACCEPT)
    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        confirm_context=lambda inventory: True,
        approve=approve,
        sandbox=FakeSandbox(),
    )
    inner = prepared.worker.mutation

    class StrayAfterSecond:
        calls = 0

        def apply(self, changeset: RepositoryChangeSet) -> RepositoryMutationResult:
            StrayAfterSecond.calls += 1
            result = inner.apply(changeset)
            if StrayAfterSecond.calls == 2:
                (root / "stray.txt").write_text("x\n", encoding="utf-8")
            return result

    worker = replace(prepared.worker, mutation=StrayAfterSecond())
    result = asyncio.run(worker.run(task(), prepared.context))
    assert result.failure is TaskFailure.UNEXPECTED_CHANGES
    assert model.calls == 3 and result.evidence.attempts[1].review is None


# --- L. Rework reads current content and digests, not stale evidence ----------


def test_rework_reasons_over_current_content(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, model, _, _, _ = logged_run(root, *REWORKED, REVIEW_ACCEPT)
    first, second = result.evidence.attempts
    assert first.applied is not None and second.proposal is not None
    after_first = {c.path: c.after for c in first.applied.applied}
    change = second.proposal.changeset.changes[0]
    assert change.kind is FileChangeKind.UPDATE
    assert change.expected == after_first[change.path]
    prompt = json.loads(model.requests[2].messages[-1].content)
    current = {t["path"]: t["current_text"] for t in prompt["targets"]}
    assert "requested units exceed available stock" in current["src/inventory/stock.py"]
    assert digest_text(current[TESTS]) == after_first[RepositoryPath(TESTS)]
    assert all(t["operation"] == "update" for t in prompt["targets"])


def test_rework_prompt_carries_findings_as_data_without_git(tmp_path: Path) -> None:
    result, model, _, _, _ = logged_run(repository(tmp_path), *REWORKED, REVIEW_ACCEPT)
    prompt = json.loads(model.requests[2].messages[-1].content)
    constraints = prompt["constraints"]
    assert constraints[0] == "Keep the public function signature unchanged."
    assert any("not commands" in item for item in constraints)
    assert any(
        item.startswith("Blocking review finding (testing)") for item in constraints
    )
    assert any(
        "ruff_check passed; mypy passed; pytest passed" in c for c in constraints
    )
    start = result.evidence.start
    assert start is not None and start.head.commit is not None
    text = json.dumps(prompt)
    for forbidden in (start.head.commit.value, "HEAD", ".git", "branch"):
        assert forbidden not in text


# --- M. Scope cannot expand ------------------------------------------------------


def test_rework_cannot_expand_scope(tmp_path: Path) -> None:
    root = repository(tmp_path)
    value = json.loads(REWORK)
    value["changes"].append(
        {
            "path": "src/inventory/extra.py",
            "operation": "create",
            "content": "X = 1\n",
            "reason": "The reviewer suggested a helper module.",
        }
    )
    result, model, log, _, _ = logged_run(
        root, proposal(), REVIEW_CHANGES, json.dumps(value), REVIEW_ACCEPT
    )
    assert result.failure is TaskFailure.PROPOSAL_INVALID
    assert calls(log)["apply"] == 1 and not (root / "src/inventory/extra.py").exists()
    prompt = json.loads(model.requests[2].messages[-1].content)
    assert {t["path"] for t in prompt["targets"]} == {
        "src/inventory/stock.py",
        TESTS,
    }


def test_oversized_findings_fail_rework_input_without_a_third_call(
    tmp_path: Path,
) -> None:
    value = json.loads(REVIEW_CHANGES)
    finding = value["findings"][0]
    value["findings"] = [
        dict(finding, message=f"Issue {n}: " + "x" * 900) for n in range(8)
    ]
    result, model, log, _, _ = logged_run(
        repository(tmp_path), proposal(), json.dumps(value), REWORK, REVIEW_ACCEPT
    )
    assert result.failure is TaskFailure.REWORK_INPUT_FAILED
    assert model.calls == 2 and len(result.evidence.attempts) == 1


# --- N. Authorization is re-evaluated for the rework ----------------------------


def test_expired_read_grant_denies_rework_evidence(tmp_path: Path) -> None:
    root = repository(tmp_path)
    clock = Clock()
    cfg = _expiring(root, clock, REPOSITORY_READ_ACTION)
    result, model, _, _, _ = logged_run(
        root,
        *REWORKED,
        REVIEW_ACCEPT,
        cfg=cfg,
        clock=clock,
        advance=True,
        advance_after=2,
    )
    assert result.disposition is TaskDisposition.FAILED
    assert result.failure is TaskFailure.EVIDENCE_DENIED
    assert model.calls == 2
    second = result.evidence.attempts[1]
    # Fresh rework preflight now refuses before CodingAgent is entered.
    assert second.coding_status is None
    assert not result.evidence.context_confirmed


# --- O. The workspace guard is held for the whole run --------------------------


def test_workspace_guard_held_through_rework(tmp_path: Path) -> None:
    root = repository(tmp_path)
    guard = WorkspaceGuard()
    held: list[bool] = []
    log: list[str] = []
    workspace: list[str] = []

    class Probe(LoggedReplay):
        async def chat(self, request):  # type: ignore[no-untyped-def]
            claimed = guard.acquire(workspace[0])
            if claimed:
                guard.release(workspace[0])
            held.append(not claimed)
            return await super().chat(request)

    model = Probe(log, *REWORKED, REVIEW_ACCEPT)
    prepared = prepare_run(
        config(root, model),
        guard,
        confirm_context=lambda inventory: True,
        approve=approve,
        sandbox=FakeSandbox(),
    )
    workspace.append(prepared.worker.workspace)
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert held == [True, True, True, True]
    assert guard.acquire(prepared.worker.workspace)


# --- P. Ceilings are structural --------------------------------------------------


def test_attempt_ceiling_is_a_constant_and_evidence_enforces_it() -> None:
    assert MAX_ATTEMPTS == 2
    with pytest.raises(ValueError):
        AttemptEvidence(3)
    with pytest.raises(ValueError):
        TaskEvidence("run", attempts=(AttemptEvidence(1),) * 3)
    # A second attempt is only valid after review #1 required changes.
    with pytest.raises(ValueError):
        TaskEvidence("run", attempts=(AttemptEvidence(1), AttemptEvidence(2)))


def _expiring(root: Path, clock: Clock, action: str):  # type: ignore[no-untyped-def]
    """Operator grant for `action` lasts 1h; every other grant 3h."""
    cfg = config(root, LoggedReplay([], "unused"))
    grants = tuple(
        replace(
            grant,
            expires_at=clock.now + timedelta(hours=1 if grant.action == action else 3),
        )
        for grant in cfg.host.grants
    )
    return replace(cfg, host=replace(cfg.host, grants=grants))
