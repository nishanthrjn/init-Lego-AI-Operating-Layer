"""ForgeAI-2 independent review gate (A-R): order, decisions, failures, bounds.

Real public host, Git, mutation and authorized reads; the reviewer is the
unchanged M8.2 IndependentReviewer; checks use the fake sandbox. Replay
outputs are consumed in call order: Coding Agent first, reviewer second.
"""

import asyncio
import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from forgeai_support import (
    REVIEW_CHANGES,
    REVIEW_INSUFFICIENT,
    REWORK,
    Clock,
    FakeSandbox,
    LoggedMutation,
    LoggedReplay,
    SpyReader,
    config,
    logged_run,
    proposal,
    replay,
    repository,
    task,
)
from legoai.intelligence.model.ports import (
    ModelPreflightError,
    ModelResponseUncertainError,
)
from legoai.kernel.effects import EffectExtent
from legoai_engineering.analyst.authorized import REPOSITORY_READ_ACTION
from legoai_engineering.coding.definition import coding_definition
from legoai_engineering.git.errors import GitError, GitFailure
from legoai_engineering.git.values import GitRepositoryState
from legoai_engineering.reviewer.definition import reviewer_definition
from legoai_engineering.reviewer.values import (
    FindingSeverity,
    ReviewDecision,
    ReviewStatus,
)

from forgeai.composition import prepare_run
from forgeai.domain import (
    ReviewInputFailure,
    TaskDisposition,
    TaskFailure,
    TaskResult,
)
from forgeai.guard import WorkspaceGuard


def accept(
    root: Path,
) -> tuple[TaskResult, LoggedReplay, list[str], LoggedMutation, SpyReader]:
    model = replay()
    return logged_run(root, *model.outputs)


# --- A/B/G/Q/R. Order, exactly two model calls, ACCEPT --------------------------


def test_review_runs_last_once_and_accept_succeeds(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, model, log, mutation, _ = accept(root)
    assert result.disposition is TaskDisposition.SUCCEEDED, result
    assert log == ["model", "apply", "check", "check", "check", "model"]
    assert model.calls == 2 and mutation.calls == 1
    review = result.evidence.review
    assert review is not None and review.status is ReviewStatus.COMPLETED
    assert result.evidence.review_decision is ReviewDecision.ACCEPT
    assert review.request.context.execution_id.value != result.evidence.run_id


# --- C/D/E/F. No review unless every deterministic gate passed ---------------


def test_no_review_when_proposal_invalid(tmp_path: Path) -> None:
    result, model, _, _, reader = logged_run(repository(tmp_path), "not a proposal")
    assert result.failure is TaskFailure.PROPOSAL_INVALID
    assert model.calls == 1 and result.evidence.review is None
    assert reader.requests == []


def test_no_review_when_mutation_denied(tmp_path: Path) -> None:
    root = repository(tmp_path)
    log: list[str] = []
    model = LoggedReplay(log, *replay().outputs)
    cfg = config(root, model, denied=frozenset({"apply-repository-changes"}))
    result, model, _, _, _ = logged_run(root, *replay().outputs, cfg=cfg)
    assert result.failure is TaskFailure.MUTATION_DENIED
    assert model.calls == 1 and result.evidence.review is None


def test_no_review_when_checks_fail(tmp_path: Path) -> None:
    result, model, log, _, reader = logged_run(
        repository(tmp_path), *replay().outputs, exits=(0, 0, 1)
    )
    assert result.failure is TaskFailure.CHECKS_FAILED
    assert model.calls == 1 and log.count("model") == 1
    assert result.evidence.review is None and reader.requests == []


def test_no_review_when_final_git_integrity_fails(tmp_path: Path) -> None:
    root = repository(tmp_path)
    log: list[str] = []
    model = LoggedReplay(log, *replay().outputs)
    prepared = prepare_run(config(root, model), WorkspaceGuard(), sandbox=FakeSandbox())
    real = prepared.worker.git

    class FailingFinal:
        calls = 0

        def inspect(self) -> GitRepositoryState:
            FailingFinal.calls += 1
            if FailingFinal.calls == 1:
                return real.inspect()
            raise GitError(GitFailure.TIMEOUT)

    worker = replace(prepared.worker, git=FailingFinal())
    result = asyncio.run(worker.run(task(), prepared.context))
    assert result.failure is TaskFailure.FINAL_STATE_UNAVAILABLE
    assert model.calls == 1 and result.evidence.review is None


# --- H/I. Review opinions stop the run: no rework, no rollback ---------------


def test_changes_required_after_rework_is_terminal_and_keeps_changes(
    tmp_path: Path,
) -> None:
    # ForgeAI-3: review #1 CHANGES_REQUIRED starts the single rework; a second
    # CHANGES_REQUIRED is terminal. Nothing is reverted.
    root = repository(tmp_path)
    result, model, log, mutation, _ = logged_run(
        root, proposal(), REVIEW_CHANGES, REWORK, REVIEW_CHANGES
    )
    assert result.disposition is TaskDisposition.FAILED
    assert result.failure is TaskFailure.REVIEW_CHANGES_REQUIRED
    assert model.calls == 4 and mutation.calls == 2 and log.count("check") == 6
    assert log[-1] == "model"
    review = result.evidence.review
    assert review is not None and review.review is not None
    blocking = [
        f for f in review.review.findings if f.severity is FindingSeverity.BLOCKING
    ]
    assert blocking and blocking[0].required_action
    # Applied changes remain; ForgeAI never reverts them.
    text = (root / "src/inventory/stock.py").read_text(encoding="utf-8")
    assert "requested units exceed available stock" in text
    assert "match=message" in (root / "tests/test_stock.py").read_text(encoding="utf-8")
    assert result.evidence.final is not None and len(result.evidence.final.entries) == 2


def test_insufficient_evidence_stops_without_rework(tmp_path: Path) -> None:
    result, model, _, mutation, _ = logged_run(
        repository(tmp_path), proposal(), REVIEW_INSUFFICIENT
    )
    assert result.failure is TaskFailure.REVIEW_INSUFFICIENT_EVIDENCE
    assert model.calls == 2 and mutation.calls == 1
    assert result.evidence.review_decision is ReviewDecision.INSUFFICIENT_EVIDENCE


# --- J/K. Review execution failures are not opinions -------------------------


@pytest.mark.parametrize(
    ("error", "effect"),
    [
        (ModelPreflightError("refused before sending"), EffectExtent.NONE),
        (ModelResponseUncertainError("response lost"), EffectExtent.UNKNOWN),
    ],
    ids=["preflight", "uncertain"],
)
def test_review_provider_failure_is_review_failed(
    tmp_path: Path, error: Exception, effect: EffectExtent
) -> None:
    result, model, _, _, _ = logged_run(repository(tmp_path), proposal(), error)
    assert result.failure is TaskFailure.REVIEW_FAILED
    assert model.calls == 2
    review = result.evidence.review
    assert review is not None and review.status is ReviewStatus.MODEL_FAILURE
    assert result.evidence.review_decision is None
    assert review.agent_result is not None
    execution = review.agent_result.model_execution
    assert execution is not None and execution.effect is effect


def test_review_model_denial_is_review_failed_without_provider_call(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    clock = Clock()
    log: list[str] = []
    cfg = config(root, LoggedReplay(log, "x"))
    grants = tuple(
        replace(
            grant,
            expires_at=clock.now
            + timedelta(hours=1 if grant.action == "invoke-capability" else 3),
        )
        for grant in cfg.host.grants
    )
    cfg = replace(cfg, host=replace(cfg.host, grants=grants))
    result, model, _, _, _ = logged_run(
        root, *replay().outputs, cfg=cfg, clock=clock, advance=True
    )
    assert result.failure is TaskFailure.REVIEW_FAILED
    assert model.calls == 1
    assert result.evidence.review is not None
    assert result.evidence.review.status is ReviewStatus.MODEL_FAILURE


def test_invalid_or_uncited_review_output_is_output_invalid(tmp_path: Path) -> None:
    uncited = json.loads(REVIEW_CHANGES)
    uncited["findings"][0]["evidence_refs"] = ["file-9"]
    for index, output in enumerate(("not json", json.dumps(uncited))):
        result, model, _, _, _ = logged_run(
            repository(tmp_path, f"r{index}"), proposal(), output
        )
        assert result.failure is TaskFailure.REVIEW_OUTPUT_INVALID
        assert model.calls == 2 and result.evidence.review_decision is None


# --- L/N. Review material bounds: explicit failure, never truncation ---------


def test_oversized_changed_file_is_review_input_failure(tmp_path: Path) -> None:
    value = json.loads(proposal())
    value["changes"][0]["content"] += "# " + "x" * 4200 + "\n"
    result, model, _, _, _ = logged_run(
        repository(tmp_path), json.dumps(value), replay().outputs[1]
    )
    assert result.failure is TaskFailure.REVIEW_INPUT_FAILED
    assert result.evidence.review_input_failure is ReviewInputFailure.MATERIAL_BOUNDS
    assert model.calls == 1 and result.evidence.review is None


def test_serialized_review_over_budget_is_review_input_failure(tmp_path: Path) -> None:
    root = repository(tmp_path)
    log: list[str] = []
    cfg = config(root, LoggedReplay(log, "x"))
    # Operator criteria that JSON-escape sixfold exceed the reviewer budget.
    cfg = replace(cfg, review_criteria=("\x01" * 1000,) * 8)
    result, model, _, _, _ = logged_run(root, *replay().outputs, cfg=cfg)
    assert result.failure is TaskFailure.REVIEW_INPUT_FAILED
    assert result.evidence.review_input_failure is ReviewInputFailure.CONTEXT_BUDGET
    assert model.calls == 1


def test_review_material_is_deterministic_and_bounded(tmp_path: Path) -> None:
    requests = []
    for name in ("a", "b"):
        result, _, _, _, _ = accept(repository(tmp_path, name))
        review = result.evidence.review
        assert review is not None
        requests.append(review.request)
        assert [m for m, _ in result.evidence.review_materials] == ["file-1", "file-2"]
    first, second = requests
    assert first.proposal == second.proposal and first.evidence == second.evidence
    assert first.criteria == second.criteria
    assert [m.material_id for m in first.evidence] == ["checks", "file-1", "file-2"]
    assert all(len(m.text.encode()) <= 4096 for m in first.evidence)


# --- M. Producer identity -----------------------------------------------------


def test_producer_is_the_coding_agent_not_the_reviewer(tmp_path: Path) -> None:
    result, _, _, _, _ = accept(repository(tmp_path))
    review = result.evidence.review
    assert review is not None and review.agent_result is not None
    assert review.request.producer == coding_definition().agent_id
    assert review.request.producer != reviewer_definition().agent_id
    assert review.agent_result.definition == reviewer_definition()


# --- O/P. Disclosure boundary: authorized reads only, no Git -----------------


def test_reviewer_sees_authorized_file_reads_and_no_git_state(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, model, _, _, reader = accept(root)
    applied = tuple(result.evidence.changed_paths)
    assert reader.requests == [applied]
    prompt = "\n".join(m.content for m in model.requests[1].messages)
    start = result.evidence.start
    assert start is not None and start.head.commit is not None
    assert start.head.commit.value not in prompt
    assert start.head.commit.value[:7] not in prompt
    for forbidden in ("HEAD", ".git", "branch", "untracked", "notes.txt"):
        assert forbidden not in prompt, forbidden
    final_text = (root / "src/inventory/stock.py").read_text(encoding="utf-8")
    review = result.evidence.review
    assert review is not None
    material = {m.material_id: m.text for m in review.request.evidence}
    assert material["file-1"].endswith(final_text)


def test_denied_review_read_is_review_input_failure(tmp_path: Path) -> None:
    root = repository(tmp_path)
    clock = Clock()
    log: list[str] = []
    cfg = config(root, LoggedReplay(log, "x"))
    grants = tuple(
        replace(
            grant,
            expires_at=clock.now
            + timedelta(hours=1 if grant.action == REPOSITORY_READ_ACTION else 3),
        )
        for grant in cfg.host.grants
    )
    cfg = replace(cfg, host=replace(cfg.host, grants=grants))
    result, model, _, _, reader = logged_run(
        root, *replay().outputs, cfg=cfg, clock=clock, advance=True
    )
    assert result.failure is TaskFailure.REVIEW_INPUT_FAILED
    assert result.evidence.review_input_failure is ReviewInputFailure.READ_DENIED
    assert model.calls == 1 and len(reader.requests) == 1
