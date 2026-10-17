"""Combined confirmed-context lifecycle qualification, with no live inference.

Real public host, authorized repository reads/mutations and temporary Git repos;
recorded model responses and a fake sandbox. These prove ordering/effect bounds,
not generated-code correctness or provider/model quality.
"""

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    REVIEW_CHANGES,
    REVIEW_INSUFFICIENT,
    REWORK,
    LoggedMutation,
    LoggedReplay,
    LoggedSandbox,
    config,
    proposal,
    repository,
    snapshot,
    task,
)

from forgeai.composition import prepare_run
from forgeai.domain import (
    OperatorDecision,
    ProposalReview,
    TaskDisposition,
    TaskFailure,
    TaskRequest,
)
from forgeai.guard import WorkspaceGuard
from forgeai.repository_context import ContextPreflight


@pytest.mark.parametrize("rework", [False, True])
def test_confirmed_task_complete_order_and_exact_scope(
    tmp_path: Path, rework: bool
) -> None:
    root = repository(tmp_path)
    log: list[str] = []
    outputs = (
        (proposal(), REVIEW_CHANGES, REWORK, REVIEW_ACCEPT)
        if rework
        else (proposal(), REVIEW_ACCEPT)
    )
    model = LoggedReplay(log, *outputs)
    sandbox = LoggedSandbox(log)
    inventories: list[ContextPreflight] = []

    def confirm(inventory: ContextPreflight) -> bool:
        log.append("context")
        inventories.append(inventory)
        return True

    def approve(review: ProposalReview) -> OperatorDecision:
        log.append("approval")
        return OperatorDecision.approve(review)

    def admit(request: TaskRequest) -> bool:
        log.append("disclosure")
        return True

    cfg = config(root, model, context=("pyproject.toml",))
    prepared = prepare_run(
        cfg,
        WorkspaceGuard(),
        approve=approve,
        confirm_context=confirm,
        sandbox=sandbox,
    )
    selected = replace(task(), context=cfg.context_paths)
    mutation = LoggedMutation(log, prepared.worker.mutation)
    worker = replace(prepared.worker, mutation=mutation, admit_model=admit)
    start = worker.git.inspect()
    reference_before = (root / "pyproject.toml").read_bytes()
    result = asyncio.run(worker.run(selected, prepared.context))
    cycle = ["model", "approval", "apply", "check", "check", "check", "model"]
    assert log == [
        "context",
        "disclosure",
        *cycle,
        *(["context", *cycle] if rework else []),
    ]
    count = 2 if rework else 1
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert result.failure is None and result.evidence.gates_passed
    assert len(result.evidence.attempts) == mutation.calls == count
    assert model.calls == 2 * count and sandbox.calls == 3 * count
    decisions = result.evidence.context_confirmations
    assert len(inventories) == len(decisions) == count
    assert all(decision.confirmed for decision in decisions)
    assert len({decision.binding.identity.value for decision in decisions}) == count
    expected = {target.path for target in selected.targets} | set(selected.context)
    assert all(
        {item.path for item in value.inventory} == expected for value in inventories
    )
    final = worker.git.inspect()
    assert final.head == start.head
    assert {entry.path for entry in final.entries} == set(result.evidence.changed_paths)
    editable = {target.path for target in selected.targets}
    assert set(result.evidence.changed_paths) <= editable
    assert (root / "pyproject.toml").read_bytes() == reference_before
    for index in range(0, model.calls, 2):
        payload = json.loads(model.requests[index].messages[-1].content)
        assert payload["read_only_context"] == [
            {"path": "pyproject.toml", "text": reference_before.decode("utf-8")}
        ]
    assert worker.guard.acquire(worker.workspace)
    worker.guard.release(worker.workspace)


@pytest.mark.parametrize(
    ("stop", "failure", "models", "applies"),
    [
        ("context", TaskFailure.CONTEXT_DECLINED, 0, 0),
        ("disclosure", TaskFailure.MODEL_DISCLOSURE_REFUSED, 0, 0),
        ("mutation", TaskFailure.PROPOSAL_DECLINED, 1, 0),
        ("review", TaskFailure.REVIEW_INSUFFICIENT_EVIDENCE, 2, 1),
        ("rework_context", TaskFailure.CONTEXT_DECLINED, 2, 1),
        ("rework_mutation", TaskFailure.PROPOSAL_DECLINED, 3, 1),
        ("terminal_review", TaskFailure.REVIEW_CHANGES_REQUIRED, 4, 2),
    ],
)
def test_each_gate_stops_without_replay_and_preserves_prior_effects(
    tmp_path: Path, stop: str, failure: TaskFailure, models: int, applies: int
) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    log: list[str] = []
    first_review = REVIEW_INSUFFICIENT if stop == "review" else REVIEW_CHANGES
    model = LoggedReplay(log, proposal(), first_review, REWORK, REVIEW_CHANGES)
    sandbox = LoggedSandbox(log)
    confirmations = 0
    approvals = 0

    def confirm(inventory: ContextPreflight) -> bool:
        nonlocal confirmations
        confirmations += 1
        log.append("context")
        return stop != "context" and not (
            stop == "rework_context" and confirmations == 2
        )

    def approve(review: ProposalReview) -> OperatorDecision:
        nonlocal approvals
        approvals += 1
        log.append("approval")
        if stop == "mutation" or (stop == "rework_mutation" and approvals == 2):
            return OperatorDecision.decline(review)
        return OperatorDecision.approve(review)

    def admit(request: TaskRequest) -> bool:
        log.append("disclosure")
        return stop != "disclosure"

    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        approve=approve,
        confirm_context=confirm,
        sandbox=sandbox,
    )
    mutation = LoggedMutation(log, prepared.worker.mutation)
    worker = replace(prepared.worker, mutation=mutation, admit_model=admit)
    result = asyncio.run(worker.run(task(), prepared.context))
    assert result.failure is failure
    assert model.calls == models and mutation.calls == applies
    assert sandbox.calls == 3 * applies
    assert result.disposition is (
        TaskDisposition.REJECTED if models == 0 else TaskDisposition.FAILED
    )
    assert len(result.evidence.attempts) <= 2
    assert len(result.evidence.context_confirmations) <= 2
    assert confirmations == (2 if stop.startswith("rework") or applies == 2 else 1)
    assert log.count("disclosure") == (0 if stop == "context" else 1)
    assert sum(item.applied is not None for item in result.evidence.attempts) == applies
    if applies == 0:
        assert snapshot(root) == before
        assert not result.evidence.changed_paths
    else:
        assert result.evidence.changed_paths
        assert worker.git.inspect().entries  # no automatic rollback
    assert worker.guard.acquire(worker.workspace)
    worker.guard.release(worker.workspace)
