"""No-op proposals stop before effects; replay models and FakeSandbox only."""

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    REWORK,
    FakeSandbox,
    LoggedMutation,
    LoggedReplay,
    config,
    git_executable,
    proposal,
    repository,
    snapshot,
    task,
)
from test_batch import inputs
from test_line_endings import fixture

from batch import Git, run_batch
from forgeai.cli import preview, summarize
from forgeai.composition import prepare_run
from forgeai.domain import (
    OperatorDecision,
    ProposalReview,
    TaskDisposition,
    TaskFailure,
)
from forgeai.guard import WorkspaceGuard
from forgeai.report import MAX_REPORT_BYTES, ModelBindingKind, encode_report, run_report


def identical_proposal(root: Path, *, lf: bool = False) -> str:
    value = json.loads(proposal())
    for change in value["changes"]:
        text = (root / change["path"]).read_bytes().decode("utf-8")
        change["content"] = text.replace("\r\n", "\n") if lf else text
    value["summary"] = "Claimed fix PRIVATE_CANARY"
    return json.dumps(value)


@pytest.mark.parametrize("ending", ["\n", "\r\n"])
def test_first_attempt_noop_has_no_effects(tmp_path: Path, ending: str) -> None:
    root = fixture(tmp_path, ending)
    before = snapshot(root)
    model = LoggedReplay([], identical_proposal(root, lf=True))
    sandbox = FakeSandbox()
    approvals: list[ProposalReview] = []

    def approve(review: ProposalReview) -> OperatorDecision:
        approvals.append(review)
        return OperatorDecision.approve(review)

    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        approve=approve,
        confirm_context=lambda inventory: True,
        sandbox=sandbox,
    )
    mutation = LoggedMutation([], prepared.worker.mutation)
    worker = replace(prepared.worker, mutation=mutation)
    result = asyncio.run(worker.run(task(), prepared.context))
    assert result.failure is TaskFailure.PROPOSAL_NO_CHANGE
    assert result.disposition is TaskDisposition.FAILED
    assert approvals == []
    assert mutation.calls == sandbox.calls == 0
    assert model.calls == 1
    assert snapshot(root) == before
    assert Git(git_executable()).run(root, "status", "--porcelain=v1") == ""
    item = result.evidence.latest
    assert item.no_change is True
    assert item.approval is None and item.applied is None
    assert item.checks == () and item.review is None
    report = json.loads(encode_report(run_report(result, ModelBindingKind.REPLAY)))
    assert report["failure"] == "PROPOSAL_NO_CHANGE"
    assert report["attempts"][0]["no_change"] is True
    assert report["repository_effect"] == "NONE"
    encoded = encode_report(report)
    assert "PRIVATE_CANARY" not in encoded
    assert len(encoded.encode("utf-8")) <= MAX_REPORT_BYTES
    assert "proposal claim: unverified" in summarize(result)


def test_rework_noop_retains_candidate_one(tmp_path: Path) -> None:
    root = repository(tmp_path)
    candidate = proposal()
    model = LoggedReplay([], candidate, candidate)
    sandbox = FakeSandbox((1, 0, 0))
    approvals: list[ProposalReview] = []

    def approve(review: ProposalReview) -> OperatorDecision:
        approvals.append(review)
        return OperatorDecision.approve(review)

    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        approve=approve,
        confirm_context=lambda inventory: True,
        sandbox=sandbox,
    )
    mutation = LoggedMutation([], prepared.worker.mutation)
    worker = replace(prepared.worker, mutation=mutation)
    result = asyncio.run(worker.run(task(), prepared.context))
    assert result.failure is TaskFailure.PROPOSAL_NO_CHANGE
    assert len(approvals) == mutation.calls == 1
    assert model.calls == 2
    first, second = result.evidence.attempts
    assert len(first.checks) == sandbox.calls == 3
    assert first.no_change is False and second.no_change is True
    assert second.approval is None and second.applied is None
    assert second.checks == () and second.review is None
    for change in approvals[0].proposal.changeset.changes:
        assert (root / change.path.value).read_bytes() == (change.text or "").encode()
    assert "WARNING: changes remain in the working tree" in summarize(result)
    report = json.loads(encode_report(run_report(result, ModelBindingKind.REPLAY)))
    assert report["failure"] == "PROPOSAL_NO_CHANGE"
    assert report["changes_retained"] is True
    assert [item["no_change"] for item in report["attempts"]] == [False, True]


def test_partial_noop_follows_normal_flow(tmp_path: Path) -> None:
    root = repository(tmp_path)
    candidate = json.loads(proposal())
    value = json.loads(REWORK)
    value["changes"].append(candidate["changes"][0])
    model = LoggedReplay([], proposal(), json.dumps(value), REVIEW_ACCEPT)
    sandbox = FakeSandbox((1, 0, 0, 0, 0, 0))
    approvals: list[ProposalReview] = []

    def approve(review: ProposalReview) -> OperatorDecision:
        approvals.append(review)
        return OperatorDecision.approve(review)

    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        approve=approve,
        confirm_context=lambda inventory: True,
        sandbox=sandbox,
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert len(approvals) == 2
    assert sandbox.calls == 6 and model.calls == 3
    assert result.evidence.latest.no_change is False
    assert "unchanged, content identical to the current file" in preview(approvals[1])


def test_noop_stops_batch_without_commit(tmp_path: Path) -> None:
    root = repository(tmp_path)
    target = "src/inventory/stock.py"
    tasks, policy = inputs(tmp_path, target=target)
    replay_path = tasks.parent / "proposal1.json"
    value = json.loads(replay_path.read_text(encoding="utf-8"))
    value["changes"][0]["content"] = (root / target).read_bytes().decode("utf-8")
    replay_path.write_text(json.dumps(value), encoding="utf-8")
    git = Git(git_executable())
    base = git.run(root, "rev-parse", "HEAD")
    sandbox = FakeSandbox()
    output = tmp_path / "output"
    result = asyncio.run(
        run_batch(
            root,
            tasks,
            policy,
            output,
            git=git,
            docker=git_executable(),
            sandbox=sandbox,
            out=lambda line: None,
        )
    )
    assert result.stopped == "PROPOSAL_NO_CHANGE"
    assert result.commits == ()
    assert result.dispositions == (("T1", "FAILED"),)
    assert sandbox.calls == 0
    assert git.run(output / "workspace", "rev-parse", "HEAD") == base
    assert git.run(output / "workspace", "status", "--porcelain=v1") == ""
    records = (output / "batch-report.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(records) == 1
    report = json.loads(records[0])
    assert report["failure"] == "PROPOSAL_NO_CHANGE"
    assert report["attempts"][0]["no_change"] is True
    assert report["policy_evaluations"] == []
