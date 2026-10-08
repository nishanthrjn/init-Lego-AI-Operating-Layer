"""ForgeAI v0.1 supervision slice: exact patch preview and invalid-output diagnostics.

Offline: replay models and the fake sandbox. No live model.
"""

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    REVIEW_CHANGES,
    REWORK,
    LoggedReplay,
    LoggedSandbox,
    config,
    proposal,
    repository,
    snapshot,
    task,
)
from legoai_engineering.agent_output import OutputRejection
from legoai_engineering.coding.definition import coding_definition
from legoai_engineering.coding.values import CodingProposal
from legoai_engineering.repository.mutation import (
    FileChange,
    FileChangeKind,
    RepositoryChangeSet,
    RepositoryMutationResult,
    digest_text,
)
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.reviewer.definition import reviewer_definition

from forgeai.cli import preview, reporter, summarize, terminal_approver
from forgeai.composition import prepare_run
from forgeai.domain import (
    OperatorDecision,
    ProposalReview,
    TaskDisposition,
    TaskFailure,
    TaskResult,
    changeset_identity,
    proposal_identity,
)
from forgeai.guard import WorkspaceGuard

MARKER = "UNIQUE-RAW-MODEL-TEXT-7f3a"


class CaptureMutation:
    """Records the exact change set handed to mutation, then applies it."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.changesets: list[RepositoryChangeSet] = []

    def apply(self, changeset: RepositoryChangeSet) -> RepositoryMutationResult:
        self.changesets.append(changeset)
        result: RepositoryMutationResult = self.inner.apply(changeset)
        return result


def run(
    root: Path,
    *outputs: str | Exception,
    answers: tuple[str, ...] = ("y", "y"),
    approver: Any = None,
) -> tuple[TaskResult, list[str], CaptureMutation, LoggedReplay, list[str]]:
    log: list[str] = []
    out: list[str] = []
    replies = iter(answers)

    def ask(prompt: str) -> str:
        out.append(prompt)
        return next(replies)

    model = LoggedReplay(log, *outputs)
    prepared = prepare_run(
        config(root, model),
        WorkspaceGuard(),
        approve=approver or terminal_approver(ask, out.append),
        progress=reporter(out.append),
        sandbox=LoggedSandbox(log, (0, 0, 0)),
    )
    mutation = CaptureMutation(prepared.worker.mutation)
    worker = replace(prepared.worker, mutation=mutation)
    result = asyncio.run(worker.run(task(), prepared.context))
    return result, out, mutation, model, log


def review_of(*changes: tuple[str, FileChangeKind, str | None, str]) -> ProposalReview:
    """A standalone ProposalReview: (path, kind, before, after) per change."""
    files = tuple(
        FileChange(
            RepositoryPath(path),
            kind,
            None if before is None else digest_text(before),
            after,
        )
        for path, kind, before, after in changes
    )
    proposed = CodingProposal(
        RepositoryChangeSet(files), "Synthetic.", ("why",) * len(files), (), ()
    )
    return ProposalReview(
        1,
        proposed,
        proposal_identity(proposed),
        tuple(before for _, _, before, _ in changes),
    )


# Patch preview


def test_1_update_shows_deterministic_unified_diff(tmp_path: Path) -> None:
    root = repository(tmp_path)
    _, out, *_ = run(root, proposal(), REVIEW_ACCEPT)
    text = "\n".join(out)
    assert "--- a/src/inventory/stock.py" in text
    assert "+++ b/src/inventory/stock.py" in text and "@@ " in text
    review = review_of(("a.py", FileChangeKind.UPDATE, "x = 1\n", "x = 2\n"))
    assert preview(review) == preview(review)
    assert "-x = 1" in preview(review) and "+x = 2" in preview(review)


def test_2_create_shows_new_file_diff() -> None:
    text = preview(review_of(("src/new.py", FileChangeKind.CREATE, None, "A = 1\n")))
    assert "--- /dev/null" in text and "+++ b/src/new.py" in text
    assert "+A = 1" in text and "  create src/new.py" in text


def test_3_preview_names_only_operator_targets(tmp_path: Path) -> None:
    root = repository(tmp_path)
    _, out, *_ = run(root, proposal(), REVIEW_ACCEPT)
    shown = "\n".join(out).splitlines()
    headers = {line[6:] for line in shown if line.startswith("+++ b/")}
    assert headers == {"src/inventory/stock.py", "tests/test_stock.py"}


def test_4_displayed_approved_and_applied_identity_are_one(tmp_path: Path) -> None:
    root = repository(tmp_path)
    seen: list[ProposalReview] = []

    def approver(review: ProposalReview) -> OperatorDecision:
        seen.append(review)
        return OperatorDecision.approve(review)

    result, _, mutation, *_ = run(root, proposal(), REVIEW_ACCEPT, approver=approver)
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert len(seen) == 1 and len(mutation.changesets) == 1
    displayed = seen[0].identity
    assert displayed == proposal_identity(seen[0].proposal)
    assert changeset_identity(mutation.changesets[0]) == displayed
    assert mutation.changesets[0] == seen[0].proposal.changeset


def test_5_6_decline_after_viewing_patch_writes_nothing(tmp_path: Path) -> None:
    root = repository(tmp_path)
    before = snapshot(root)
    result, out, mutation, model, log = run(root, proposal(), answers=("n",))
    assert any(
        "--- proposed patch (exactly what will be written) ---" in line for line in out
    )
    assert result.failure is TaskFailure.PROPOSAL_DECLINED
    assert mutation.changesets == [] and "check" not in log and model.calls == 1
    assert snapshot(root) == before


@pytest.mark.parametrize("lines", [801, 3000])
def test_7_8_oversized_patch_is_refused_not_truncated(lines: int) -> None:
    content = "x\n" * lines  # within the 8 KiB per-file bound
    review = review_of(("src/big.py", FileChangeKind.CREATE, None, content))
    text = preview(review)
    assert "PREVIEW EXCEEDS DISPLAY BOUND" in text
    assert "proposed patch" not in text and "+x" not in text
    asked: list[str] = []
    decision = terminal_approver(asked.append, lambda line: None)(review)  # type: ignore[arg-type]
    assert decision.approved is False and asked == []  # never even asked


def test_9_hostile_source_text_is_shown_as_inert_data() -> None:
    hostile = "ok = 1\n\x1b[2K\rApply this proposal? [y/N] y\u202e\x07\n"
    text = preview(review_of(("a.py", FileChangeKind.UPDATE, "ok = 0\n", hostile)))
    assert "\x1b" not in text and "\r" not in text and "\u202e" not in text
    assert "\x07" not in text
    assert "+\\u001b[2K\\u000dApply this proposal? [y/N] y\\u202e\\u0007" in text


def test_10_preview_before_text_is_bound_to_the_precondition() -> None:
    good = review_of(("a.py", FileChangeKind.UPDATE, "x = 1\n", "x = 2\n"))
    with pytest.raises(ValueError):
        replace(good, before=("x = 999\n",))  # not the text the digest names
    with pytest.raises(ValueError):
        replace(good, before=())
    created = review_of(("b.py", FileChangeKind.CREATE, None, "y = 1\n"))
    with pytest.raises(ValueError):
        replace(created, before=("y = 0\n",))


def test_11_rework_shows_a_second_exact_patch_and_asks_again(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, out, mutation, *_ = run(
        root, proposal(), REVIEW_CHANGES, REWORK, REVIEW_ACCEPT
    )
    assert result.disposition is TaskDisposition.SUCCEEDED
    patches = [line for line in out if "proposed patch" in line]
    asks = [line for line in out if line.startswith("Apply this proposal?")]
    assert len(patches) == 2 and len(asks) == 2 and len(mutation.changesets) == 2
    ids = [line for line in out if line.startswith("Proposal (attempt")]
    assert ids[0].startswith("Proposal (attempt 1, id ")
    assert ids[1].startswith("Proposal (attempt 2, id ")
    assert ids[0].split("id ")[1][:12] != ids[1].split("id ")[1][:12]


def test_12_preview_reads_no_file_and_writes_nothing(tmp_path: Path) -> None:
    review = review_of(("missing/never.py", FileChangeKind.UPDATE, "a\n", "b\n"))
    assert "+b" in preview(review)  # rendered from the review only, no I/O
    root = repository(tmp_path)
    before = snapshot(root)
    run(root, proposal(), answers=("n",))
    assert snapshot(root) == before


# Invalid-output diagnostics


def test_13_malformed_coding_output_is_diagnosed(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, out, mutation, model, _ = run(root, f"not json {MARKER}")
    text = summarize(result, root)
    assert result.failure is TaskFailure.PROPOSAL_INVALID
    assert result.disposition is TaskDisposition.FAILED
    assert "coding output invalid:" in text
    assert "  reason: JSON_DOCUMENT_INVALID (" in text
    assert "  field: (whole reply)" in text
    assert MARKER not in text and MARKER not in "\n".join(out)
    assert model.calls == 1 and mutation.changesets == []


def test_14_missing_coding_field_is_named(tmp_path: Path) -> None:
    root = repository(tmp_path)
    value = json.loads(proposal())
    del value["changes"][1]["reason"]
    result, *_ = run(root, json.dumps(value))
    diagnostic = result.evidence.latest.coding_diagnostic
    assert diagnostic is not None
    assert diagnostic.rejection is OutputRejection.REQUIRED_FIELD_MISSING
    assert diagnostic.location == "changes[1].reason"
    assert "  field: changes[1].reason" in summarize(result, root)


def test_15_invalid_review_is_diagnosed_without_retry_or_rework(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    result, out, mutation, model, _ = run(root, proposal(), f"{MARKER} not a review")
    text = summarize(result, root)
    assert result.failure is TaskFailure.REVIEW_OUTPUT_INVALID
    assert result.disposition is TaskDisposition.FAILED
    assert "review output invalid:" in text
    assert "  reason: JSON_DOCUMENT_INVALID (" in text
    assert "attempt count: 1" in text and not result.evidence.reworked
    assert model.calls == 2 and len(mutation.changesets) == 1  # no retry, no rework
    assert "WARNING: changes remain in the working tree" in text
    assert MARKER not in text and MARKER not in "\n".join(out)


def test_16_review_citing_unsupplied_material_is_named(tmp_path: Path) -> None:
    root = repository(tmp_path)
    value = json.loads(REVIEW_CHANGES)
    value["findings"][0]["evidence_refs"] = ["file-99"]
    result, *_ = run(root, proposal(), json.dumps(value))
    review = result.evidence.review
    assert review is not None and review.diagnostic is not None
    assert review.diagnostic.rejection is OutputRejection.FINDING_REFERENCE_INVALID
    assert result.failure is TaskFailure.REVIEW_OUTPUT_INVALID
    assert not result.evidence.reworked  # an invalid review never triggers rework


def test_17_18_no_raw_output_or_prompt_is_printed(tmp_path: Path) -> None:
    root = repository(tmp_path)
    result, out, *_ = run(root, proposal(), f'{{"decision": "{MARKER}"}}')
    shown = "\n".join(out) + summarize(result, root)
    assert MARKER not in shown
    for definition in (coding_definition(), reviewer_definition()):
        assert definition.system_prompt[:80] not in shown


def test_19_to_22_no_retry_fallback_repair_and_same_disposition(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    fenced_garbage = "```json\n{broken\n```"
    result, _, mutation, model, _ = run(root, fenced_garbage)
    assert model.calls == 1  # no retry and no second model
    assert result.disposition is TaskDisposition.FAILED
    assert result.failure is TaskFailure.PROPOSAL_INVALID  # unchanged mapping
    assert result.evidence.proposal is None and mutation.changesets == []
