"""Line-ending, approval and rendering contracts; replay and FakeSandbox only."""

import asyncio
import json
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

import pytest
from forgeai_support import (
    REVIEW_ACCEPT,
    FakeSandbox,
    config,
    git_executable,
    proposal,
    repository,
    snapshot,
    task,
)
from legoai_engineering.coding.values import CodingProposal
from legoai_engineering.repository.mutation import (
    FileChange,
    FileChangeKind,
    RepositoryChangeSet,
    digest_text,
)
from legoai_engineering.repository.workspace import RepositoryPath

from demo import git
from forgeai import line_endings, worker
from forgeai.cli import ReplayModel, patch, preview, summarize
from forgeai.composition import prepare_run
from forgeai.domain import (
    OperatorDecision,
    ProposalReview,
    ReworkTrigger,
    RunStage,
    TaskDisposition,
    TaskFailure,
    TaskResult,
    proposal_identity,
)
from forgeai.guard import WorkspaceGuard
from forgeai.line_endings import is_consistent_crlf, match_line_endings
from forgeai.report import ModelBindingKind, encode_report, run_report
from scripts.forgeai_kisski_bounded_live_pilot import projection


def proposed(before: str | None, after: str, *, create: bool = False) -> CodingProposal:
    change = FileChange(
        RepositoryPath("src/a.py"),
        FileChangeKind.CREATE if create else FileChangeKind.UPDATE,
        None if create else digest_text(before if before is not None else "old"),
        after,
    )
    return CodingProposal(
        RepositoryChangeSet((change,)),
        "Summary.",
        ("Reason.",),
        ("Risk.",),
        ("Unknown.",),
    )


@pytest.mark.parametrize(
    "before,after,expected",
    [
        ("a\r\nb\r\n", "a\nc\n", "a\r\nc\r\n"),
        ("a\nb\n", "a\nc\n", "a\nc\n"),
        ("a\r\nb\n", "a\nc\n", "a\nc\n"),
        ("a\rb\r\n", "a\nc\n", "a\nc\n"),
        ("a\r\nb\r\n", "a\rc\n", "a\rc\n"),
        ("a\r\nb\r\n", "a\r\nc\r\n", "a\r\nc\r\n"),
        ("a\r\nb", "a\nc", "a\r\nc"),
        ("a\r\n", "", ""),
        ("a\r\n", "no newline", "no newline"),
        ("", "a\n", "a\n"),
        (None, "a\n", "a\n"),
    ],
)
def test_rules_and_narrative_preservation(
    before: str | None, after: str, expected: str
) -> None:
    original = proposed(before, after)
    change = original.changeset.changes[0]
    result = match_line_endings(original, {change.path: before})
    assert result == replace(
        original, changeset=RepositoryChangeSet((replace(change, text=expected),))
    )
    assert result.changeset.changes[0].expected is change.expected
    if expected == after:
        assert result is original
    if "\r" not in after:
        # The authorized split/join conversion is byte-equivalent to replacement.
        assert "\r\n".join(after.split("\n")) == after.replace("\n", "\r\n")


def test_create_is_unchanged_even_with_crlf_in_mapping() -> None:
    original = proposed(None, "a\nb\n", create=True)
    path = original.changeset.changes[0].path
    assert match_line_endings(original, {path: "old\r\n"}) is original


@pytest.mark.parametrize("total", [False, True])
def test_bound_failure_returns_entire_original(total: bool) -> None:
    sizes = (2700, 2700, 2700, 2700) if total else (1, 2731)
    changes = tuple(
        FileChange(
            RepositoryPath(f"src/file-{index}.py"),
            FileChangeKind.UPDATE,
            digest_text("old\r\n"),
            "x\n" * size,
        )
        for index, size in enumerate(sizes)
    )
    original = CodingProposal(
        RepositoryChangeSet(changes), "Bound case.", ("Reason.",) * len(changes), (), ()
    )
    assert (
        match_line_endings(
            original, dict.fromkeys((change.path for change in changes), "old\r\n")
        )
        is original
    )


@pytest.mark.parametrize("error", [ValueError, TypeError])
def test_constructor_failure_returns_original(
    monkeypatch: pytest.MonkeyPatch, error: type[Exception]
) -> None:
    original = proposed("old\r\n", "new\n")

    def reject(*args: object, **kwargs: object) -> FileChange:
        raise error("constructor rejected conversion")

    monkeypatch.setattr(line_endings, "FileChange", reject)
    assert (
        match_line_endings(original, {original.changeset.changes[0].path: "old\r\n"})
        is original
    )


def review_of(before: str, after: str) -> ProposalReview:
    value = proposed(before, after)
    return ProposalReview(1, value, proposal_identity(value), (before,))


def test_crlf_rendering_has_note_and_only_real_changes() -> None:
    lines = patch(review_of("a\r\nb\r\n", "a\r\nc\r\n"))
    assert lines == [
        "--- a/src/a.py",
        "+++ b/src/a.py",
        "line endings: CRLF (both versions; not shown per line)",
        "@@ -1,2 +1,2 @@",
        " a",
        "-b",
        "+c",
    ]
    assert "\\u000d" not in "\n".join(lines)


@pytest.mark.parametrize(
    "before,after",
    [
        ("a\r\nb\n", "a\r\nc\n"),
        ("a\rb\n", "a\rc\n"),
        ("a\r\nb\r\n", "a\r\nc\rd\r\n"),
        ("a\r\nb\r\n", "a\nc\n"),
    ],
)
def test_mixed_lone_embedded_and_one_sided_cr_stay_escaped(
    before: str, after: str
) -> None:
    rendered = "\n".join(patch(review_of(before, after)))
    assert "\\u000d" in rendered
    assert "line endings:" not in rendered
    if "c\rd" in after:
        assert "+c\\u000dd\\u000d" in rendered


def test_lf_renderer_bytes_and_missing_newline_marker_are_unchanged() -> None:
    assert "\n".join(patch(review_of("a\nb\n", "a\nc\n"))).encode() == (
        b"--- a/src/a.py\n+++ b/src/a.py\n@@ -1,2 +1,2 @@\n a\n-b\n+c"
    )
    lines = patch(review_of("a\r\nb", "a\r\nc"))
    assert lines[-4:] == [
        "-b",
        "\\ No newline at end of file",
        "+c",
        "\\ No newline at end of file",
    ]


def test_crlf_note_does_not_hide_other_control_characters() -> None:
    rendered = "\n".join(patch(review_of("a\r\n", "b\x1b[2K\u202e\r\n")))
    assert "+b\\u001b[2K\\u202e" in rendered
    assert "\\u000d" not in rendered


@pytest.mark.parametrize("count,refused", [(398, False), (399, True)])
def test_crlf_note_counts_toward_existing_display_bound(
    count: int, refused: bool
) -> None:
    review = review_of("a\r\n" * count, "b\r\n" * count)
    assert ("PREVIEW EXCEEDS DISPLAY BOUND" in preview(review)) is refused


def fixture(tmp_path: Path, ending: str) -> Path:
    root = repository(tmp_path)
    # Explicit bytes and local Git policy: independent of checkout autocrlf.
    git(root, git_executable(), "config", "core.autocrlf", "false")
    for target in task().targets:
        path = root / target.path.value
        text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
        path.write_bytes(text.replace("\n", ending).encode("utf-8"))
    git(root, git_executable(), "add", "--all")
    git(
        root,
        git_executable(),
        "-c",
        "user.name=ForgeAI fixture",
        "-c",
        "user.email=fixture@forgeai.invalid",
        "commit",
        "--allow-empty",
        "--quiet",
        "--no-gpg-sign",
        "-m",
        "explicit line endings",
    )
    return root


def execute(
    root: Path,
    *outputs: str,
    exits: tuple[int, ...] = (0, 0, 0),
    wrong_identity: bool = False,
) -> tuple[TaskResult, list[ProposalReview], list[tuple[RunStage, int]], FakeSandbox]:
    seen: list[ProposalReview] = []
    events: list[tuple[RunStage, int]] = []

    def approve(review: ProposalReview) -> OperatorDecision:
        seen.append(review)
        if wrong_identity:
            original = replace(
                review.proposal,
                changeset=RepositoryChangeSet(
                    tuple(
                        replace(change, text=(change.text or "").replace("\r\n", "\n"))
                        for change in review.proposal.changeset.changes
                    )
                ),
            )
            return OperatorDecision(True, proposal_identity(original))
        return OperatorDecision.approve(review)

    sandbox = FakeSandbox(exits)
    prepared = prepare_run(
        config(root, ReplayModel(*outputs)),
        WorkspaceGuard(),
        approve=approve,
        confirm_context=lambda inventory: True,
        progress=lambda stage, attempt: events.append((stage, attempt)),
        sandbox=sandbox,
    )
    result = asyncio.run(prepared.worker.run(task(), prepared.context))
    return result, seen, events, sandbox


def test_crlf_preview_approved_applied_and_evidence_bytes_match(tmp_path: Path) -> None:
    root = fixture(tmp_path, "\r\n")
    result, seen, _, _ = execute(root, proposal(), REVIEW_ACCEPT)
    assert result.disposition is TaskDisposition.SUCCEEDED
    review = seen[0]
    lines = patch(review)
    removed = [
        line for line in lines if line.startswith("-") and not line.startswith("---")
    ]
    added = [
        line for line in lines if line.startswith("+") and not line.startswith("+++")
    ]
    assert len(removed) == 1 and len(added) == 25
    assert "\\u000d" not in "\n".join(lines)
    assert lines.count("line endings: CRLF (both versions; not shown per line)") == 2
    item = result.evidence.latest
    assert item.proposal == review.proposal and item.applied is not None
    for approved, applied in zip(review.identity, item.applied.applied, strict=True):
        data = (root / applied.path.value).read_bytes()
        assert is_consistent_crlf(data.decode("utf-8"))
        assert applied.after is not None
        assert applied.after == digest_text(data.decode("utf-8"))
        assert applied.after.value == approved[3]


def test_unconverted_identity_does_not_approve(tmp_path: Path) -> None:
    root = fixture(tmp_path, "\r\n")
    before = snapshot(root)
    result, seen, _, sandbox = execute(root, proposal(), wrong_identity=True)
    assert len(seen) == 1
    assert result.failure is TaskFailure.PROPOSAL_DECLINED
    assert result.evidence.latest.approval is False
    assert result.evidence.latest.applied is None
    assert sandbox.calls == 0 and snapshot(root) == before


def test_check_rework_also_converts_and_shows_only_real_changes(tmp_path: Path) -> None:
    root = fixture(tmp_path, "\r\n")
    value = json.loads(proposal())
    value["changes"][0]["content"] = value["changes"][0]["content"].replace(
        "return available - requested", "return (available - requested)"
    )
    value["changes"][1]["content"] = value["changes"][1]["content"].replace(
        "assert reserve(5, 5) == 0", "assert reserve(5, 5) == (0)"
    )
    result, seen, _, sandbox = execute(
        root, proposal(), json.dumps(value), REVIEW_ACCEPT, exits=(1, 0, 0, 0, 0, 0)
    )
    assert result.disposition is TaskDisposition.SUCCEEDED
    assert result.evidence.rework_trigger is ReworkTrigger.CHECK_FINDINGS
    assert len(seen) == 2 and sandbox.calls == 6
    second = seen[1]
    lines = patch(second)
    removed = [
        line for line in lines if line.startswith("-") and not line.startswith("---")
    ]
    added = [
        line for line in lines if line.startswith("+") and not line.startswith("+++")
    ]
    assert len(removed) == 2 and len(added) == 2
    assert "\\u000d" not in "\n".join(lines)
    for change in second.proposal.changeset.changes:
        assert is_consistent_crlf(change.text)
        assert (root / change.path.value).read_bytes() == (change.text or "").encode()
    assert result.evidence.latest.proposal == second.proposal


def test_lf_fixture_matches_prior_behavior_output_report_pilot_and_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = fixture(tmp_path, "\n")
    before = snapshot(root)

    def unconverted(
        value: CodingProposal, current: Mapping[RepositoryPath, str | None]
    ) -> CodingProposal:
        return value

    with monkeypatch.context() as control:
        control.setattr(worker, "match_line_endings", unconverted)
        baseline, reviews_before, events_before, _ = execute(
            root, proposal(), REVIEW_ACCEPT
        )
    applied_before = snapshot(root)
    for name, data in before.items():
        (root / name).write_bytes(data)
    result, reviews, events, _ = execute(root, proposal(), REVIEW_ACCEPT)
    assert result.disposition is baseline.disposition is TaskDisposition.SUCCEEDED
    assert snapshot(root) == applied_before
    assert [preview(item) for item in reviews] == [
        preview(item) for item in reviews_before
    ]
    assert (
        events
        == events_before
        == [
            (RunStage.REPOSITORY_VERIFIED, 0),
            (RunStage.PROPOSAL_GENERATED, 1),
            (RunStage.AWAITING_APPROVAL, 1),
            (RunStage.CHANGES_APPLIED, 1),
            (RunStage.CHECKS_COMPLETED, 1),
            (RunStage.REVIEW_COMPLETED, 1),
        ]
    )
    # Independent executions mint run IDs and lifecycle bindings. Normalize
    # only those fields; scope, task, repository, inventory and decisions match.
    old = baseline.evidence.context_confirmations[0]
    new = result.evidence.context_confirmations[0]
    binding = replace(old.binding, lifecycle=new.binding.lifecycle)
    assert binding == new.binding
    baseline = replace(
        baseline,
        evidence=replace(
            baseline.evidence,
            run_id=result.evidence.run_id,
            context_confirmations=(replace(old, binding=binding),),
        ),
    )
    assert summarize(result) == summarize(baseline)
    assert encode_report(run_report(result, ModelBindingKind.REPLAY)) == encode_report(
        run_report(baseline, ModelBindingKind.REPLAY)
    )
    assert projection(result) == projection(baseline)
