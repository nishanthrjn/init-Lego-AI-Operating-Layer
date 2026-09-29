"""Bounded proposal semantics through real M2/M7/governed fake Model composition."""

import asyncio
import hashlib
import json
import sys
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from bounded_coding import create_demo
from legoai.intelligence.model.ports import ModelResponseUncertainError
from legoai.kernel.effects import EffectExtent

from legoai_engineering.analyst.api import repository_analyst_definition
from legoai_engineering.analyst.values import AcquisitionFailure
from legoai_engineering.coding._composition import AuthorizedCodingEvidence
from legoai_engineering.coding.definition import coding_definition
from legoai_engineering.coding.values import (
    CodingEvidence,
    CodingFile,
    CodingStatus,
    CodingTarget,
)
from legoai_engineering.repository.errors import WorkspaceBoundaryError
from legoai_engineering.repository.mutation import (
    ContentDigest,
    FileChangeKind,
    RepositoryChangeSet,
)
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.reviewer.definition import reviewer_definition


def target(
    path: str = "example.py", kind: FileChangeKind = FileChangeKind.UPDATE
) -> CodingTarget:
    return CodingTarget(RepositoryPath(path), kind)


def change(**fields: object) -> dict[str, object]:
    value: dict[str, object] = {
        "path": "example.py",
        "operation": "update",
        "content": "new\r\n",
        "reason": "Meet the objective.",
    }
    value.update(fields)
    return value


def output(**fields: object) -> str:
    value: dict[str, object] = {
        "summary": "Change the text.",
        "changes": [change()],
        "risks": [],
        "unknowns": ["Not executed."],
    }
    value.update(fields)
    return json.dumps(value)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "example.py").write_bytes(b"\xef\xbb\xbfGREETING = 'hello'\r\n")
    return tmp_path


def test_update_uses_exact_trusted_digest_and_never_writes(workspace: Path) -> None:
    before = {p.name: p.read_bytes() for p in workspace.iterdir()}
    agent, request, model = create_demo(workspace, output(), (target(),))
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.SUCCEEDED
    assert result.proposal is not None and result.evidence is not None
    assert type(result.proposal.changeset) is RepositoryChangeSet
    proposed = result.proposal.changeset.changes[0]
    assert proposed.expected == ContentDigest(
        hashlib.sha256(before["example.py"]).hexdigest()
    )
    assert proposed.expected == result.evidence.files[0].digest
    assert proposed.text == "new\r\n" and proposed.kind is FileChangeKind.UPDATE
    assert proposed.expected is not None
    assert model.calls == 1 and model.last_request is not None
    assert proposed.expected.value not in model.last_request.messages[-1].content
    assert before == {p.name: p.read_bytes() for p in workspace.iterdir()}
    assert (
        result.agent_result is not None
        and result.agent_result.model_execution is not None
    )
    assert result.agent_result.model_execution.effect is EffectExtent.COMPLETED


def test_create_checks_existing_parent_and_returns_absence_precondition(
    workspace: Path,
) -> None:
    (workspace / "src").mkdir()
    agent, request, model = create_demo(
        workspace,
        output(changes=[change(path="src/new.py", operation="create", content="")]),
        (target("src/new.py", FileChangeKind.CREATE),),
    )
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.SUCCEEDED
    assert result.proposal is not None and result.evidence is not None
    proposed = result.proposal.changeset.changes[0]
    assert proposed.kind is FileChangeKind.CREATE and proposed.expected is None
    assert proposed.text == ""
    assert result.evidence.files[0].current is None
    assert not (workspace / "src" / "new.py").exists() and model.calls == 1


@pytest.mark.parametrize(
    "path,kind",
    [
        ("missing.py", FileChangeKind.UPDATE),
        ("example.py", FileChangeKind.CREATE),
        ("missing/new.py", FileChangeKind.CREATE),
    ],
)
def test_missing_update_existing_create_and_missing_parent_fail_before_model(
    workspace: Path, path: str, kind: FileChangeKind
) -> None:
    agent, request, model = create_demo(workspace, output(), (target(path, kind),))
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.INVALID_REQUEST
    assert result.acquisition_failure is AcquisitionFailure.UNAVAILABLE
    assert result.proposal is None and result.agent_result is None and model.calls == 0


@pytest.mark.parametrize("kind", [FileChangeKind.CREATE, FileChangeKind.UPDATE])
def test_authorization_denied_before_any_io(
    workspace: Path, kind: FileChangeKind
) -> None:
    agent, request, model = create_demo(
        workspace, output(), (target("new.py", kind),), read_allowed=False
    )
    reader = agent.evidence_reader
    assert isinstance(reader, AuthorizedCodingEvidence)
    with (
        patch.object(
            type(reader.reads.workspace),
            "read_text",
            side_effect=AssertionError("read"),
        ),
        patch.object(
            type(reader.reads.workspace),
            "list_entries",
            side_effect=AssertionError("list"),
        ),
    ):
        result = asyncio.run(agent.propose(request))
    assert result.acquisition_failure is AcquisitionFailure.DENIED and model.calls == 0


def test_request_cannot_expand_operator_scope(workspace: Path) -> None:
    agent, request, model = create_demo(workspace, output(), (target(),))
    result = asyncio.run(agent.propose(replace(request, targets=(target("other.py"),))))
    assert result.acquisition_failure is AcquisitionFailure.DENIED and model.calls == 0


# The public host pins one selected binding; ambiguity is covered in Core M7 tests.
@pytest.mark.parametrize("count", [0])
def test_no_match_or_ambiguous_routes_do_not_call_model(
    workspace: Path, count: int
) -> None:
    agent, request, model = create_demo(
        workspace, output(), (target(),), route_count=count
    )
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.MODEL_FAILURE
    assert result.proposal is None and model.calls == 0


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        '{"summary":"x","summary":"x"}',
        output(extra="no"),
        output(changes=[]),
        output(changes=[change(), change()]),
        output(changes=[change(path="other.py")]),
        output(changes=[change(path="EXAMPLE.py")]),
        output(changes=[change(operation="delete")]),
        output(changes=[change(operation="create")]),
        output(changes=[change(expected="a" * 64)]),
        output(changes=[change(content="x" * 8193)]),
        output(changes=[change(content="\0")]),
        output(changes=[change(path="../outside")]),
        output(changes=[change(content="é" * 4097)]),
        output(changes=[change(content=None)]),
        output(summary="x" * 2049),
        output(risks=["risk"] * 9),
    ],
    ids=[
        "syntax",
        "array",
        "duplicate-key",
        "extra",
        "empty",
        "duplicate-path",
        "fabricated-path",
        "case-alias",
        "delete",
        "wrong-kind",
        "invented-digest",
        "file-budget",
        "nul",
        "escape",
        "utf8-budget",
        "null-content",
        "summary",
        "risks",
    ],
)
def test_invalid_output_has_no_partial_changeset(workspace: Path, text: str) -> None:
    agent, request, model = create_demo(workspace, text, (target(),))
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.OUTPUT_INVALID and result.proposal is None
    assert (
        result.agent_result is not None
        and result.agent_result.model_execution is not None
    )
    assert result.agent_result.model_execution.effect is EffectExtent.COMPLETED
    assert model.calls == 1


@pytest.mark.parametrize("text", ["x" * 32769, "\ud800"], ids=["accepted-size", "utf8"])
def test_m7_output_bounds(workspace: Path, text: str) -> None:
    agent, request, model = create_demo(workspace, text, (target(),))
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.OUTPUT_INVALID and result.proposal is None
    assert model.calls == 1


def test_unknown_model_effect_is_preserved_without_retry(workspace: Path) -> None:
    agent, request, model = create_demo(workspace, output(), (target(),))
    model.error = ModelResponseUncertainError("uncertain response")
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.MODEL_FAILURE
    assert (
        result.agent_result is not None
        and result.agent_result.model_execution is not None
    )
    assert result.agent_result.model_execution.effect is EffectExtent.UNKNOWN
    assert result.proposal is None and model.calls == 1


def test_cancellation_is_not_swallowed(workspace: Path) -> None:
    agent, request, _ = create_demo(workspace, output(), (target(),))
    with patch.object(
        type(agent.agent_runtime), "run", AsyncMock(side_effect=asyncio.CancelledError)
    ):
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(agent.propose(request))


def test_request_and_evidence_bounds(workspace: Path) -> None:
    _, request, _ = create_demo(workspace, output(), (target(),))
    for objective in ("", " ", "x" * 2049, "\ud800"):
        with pytest.raises(ValueError):
            replace(request, objective=objective)
    for targets in (
        (),
        (target(),) * 2,
        tuple(target(str(i)) for i in range(9)),
        (target("a"), target("a/b")),
    ):
        with pytest.raises(ValueError):
            replace(request, targets=targets)
    for constraints in (("",), ("x",) * 9, ("x" * 1025,)):
        with pytest.raises(ValueError):
            replace(request, constraints=constraints)
    with pytest.raises(ValueError):
        CodingFile(target(), RepositoryText("example.py", "x" * 8193))
    with pytest.raises(ValueError):
        CodingEvidence(
            tuple(
                CodingFile(target(str(i)), RepositoryText(str(i), "x" * 8192))
                for i in range(4)
            )
        )


@pytest.mark.parametrize(
    "path", ["../outside", "/absolute", "C:/outside", "\\\\host\\share"]
)
def test_m2_path_escape_rejected(path: str) -> None:
    with pytest.raises(WorkspaceBoundaryError):
        target(path)


@pytest.mark.parametrize("path", [".git/config", ".venv/x", "src/.secret", ".env"])
def test_administrative_targets_rejected(path: str) -> None:
    with pytest.raises(ValueError):
        target(path)


def test_delete_request_is_out_of_scope() -> None:
    with pytest.raises(ValueError):
        target(kind=FileChangeKind.DELETE)


def test_prompt_budget_before_invocation(workspace: Path) -> None:
    (workspace / "example.py").write_bytes(b"\x01" * 8192)
    agent, request, model = create_demo(workspace, output(), (target(),))
    result = asyncio.run(agent.propose(request))
    assert result.acquisition_failure is AcquisitionFailure.BUDGET
    assert result.agent_result is None and model.calls == 0


def test_stable_order_and_digest_not_invented_after_later_edit(workspace: Path) -> None:
    (workspace / "other.py").write_text("old", encoding="utf-8")
    prompts = []
    for targets in ((target(), target("other.py")), (target("other.py"), target())):
        agent, request, model = create_demo(workspace, output(), targets)
        result = asyncio.run(agent.propose(request))
        assert result.proposal is not None and model.last_request is not None
        prompts.append(model.last_request.messages)
    assert prompts[0] == prompts[1]
    assert result.proposal is not None
    proposed = result.proposal.changeset.changes[0]
    (workspace / "example.py").write_bytes(b"later change")
    assert proposed.expected != ContentDigest(
        hashlib.sha256(b"later change").hexdigest()
    )
    with pytest.raises(ValueError):
        replace(
            result,
            proposal=replace(
                result.proposal,
                changeset=RepositoryChangeSet(
                    (replace(proposed, expected=ContentDigest("a" * 64)),)
                ),
            ),
        )


@pytest.mark.parametrize("kind", [FileChangeKind.CREATE, FileChangeKind.UPDATE])
def test_symlink_target_or_parent_escape(workspace: Path, kind: FileChangeKind) -> None:
    outside = workspace.parent / (workspace.name + "-outside")
    outside.mkdir()
    (outside / "existing.py").write_text("private", encoding="utf-8")
    try:
        (workspace / "link").symlink_to(outside, target_is_directory=True)
    except OSError as error:
        if sys.platform == "win32" and error.winerror == 1314:
            pytest.skip("Windows symlink privilege unavailable; enable Developer Mode")
        raise
    path = "link/new.py" if kind is FileChangeKind.CREATE else "link/existing.py"
    agent, request, model = create_demo(workspace, output(), (target(path, kind),))
    result = asyncio.run(agent.propose(request))
    assert result.acquisition_failure is AcquisitionFailure.BOUNDARY
    assert model.calls == 0


def test_coding_identity_is_distinct() -> None:
    identities = {
        coding_definition().agent_id,
        repository_analyst_definition().agent_id,
        reviewer_definition().agent_id,
    }
    assert len(identities) == 3


def test_generated_file_boundary_and_aggregate_budget(workspace: Path) -> None:
    agent, request, _ = create_demo(
        workspace, output(changes=[change(content="x" * 8192)]), (target(),)
    )
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.SUCCEEDED
    targets = tuple(target(f"new{i}.py", FileChangeKind.CREATE) for i in range(4))
    text = output(
        changes=[
            change(path=t.path.value, operation="create", content="x" * 6300)
            for t in targets
        ]
    )
    assert len(text.encode("utf-8")) < coding_definition().output_contract.max_bytes
    agent, request, model = create_demo(workspace, text, targets)
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.OUTPUT_INVALID
    assert result.proposal is None and model.calls == 1


def test_read_size_failure_never_reaches_model(workspace: Path) -> None:
    (workspace / "example.py").write_bytes(b"x" * 8193)
    agent, request, model = create_demo(workspace, output(), (target(),))
    result = asyncio.run(agent.propose(request))
    assert result.acquisition_failure is AcquisitionFailure.BUDGET and model.calls == 0


def test_create_observation_rechecks_authority_before_disclosure(
    workspace: Path,
) -> None:
    agent, request, model = create_demo(
        workspace, output(), (target("new.py", FileChangeKind.CREATE),)
    )
    reader = agent.evidence_reader
    assert isinstance(reader, AuthorizedCodingEvidence)
    now = reader.reads.security_context.established_at
    times = iter((now, now, now + timedelta(hours=2)))
    agent = replace(
        agent,
        evidence_reader=replace(
            reader, reads=replace(reader.reads, clock=lambda: next(times))
        ),
    )
    result = asyncio.run(agent.propose(request))
    assert result.acquisition_failure is AcquisitionFailure.DENIED
    assert result.evidence is None and result.proposal is None and model.calls == 0


def test_model_governance_is_separate_from_read_authority(workspace: Path) -> None:
    # Reads stay authorized while the operator's model grant has expired.
    agent, request, model = create_demo(
        workspace, output(), (target(),), model_allowed=False
    )
    result = asyncio.run(agent.propose(request))
    assert result.status is CodingStatus.MODEL_FAILURE
    assert (
        result.agent_result is not None
        and result.agent_result.model_execution is not None
    )
    assert result.agent_result.model_execution.effect is EffectExtent.NONE
    assert result.proposal is None and model.calls == 0


def test_current_digest_field_cannot_be_supplied(workspace: Path) -> None:
    file = CodingFile(target(), RepositoryText("example.py", "current"))
    # digest is init=False; CPython 3.13+ dataclasses.replace rejects it with TypeError.
    with pytest.raises(TypeError):
        replace(file, digest=ContentDigest("a" * 64))


def test_create_listing_failure_and_exclusion_are_not_absence(workspace: Path) -> None:
    from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure

    agent, request, model = create_demo(
        workspace, output(), (target("new.py", FileChangeKind.CREATE),)
    )
    reader = agent.evidence_reader
    assert isinstance(reader, AuthorizedCodingEvidence)
    with patch.object(
        type(reader.reads.workspace),
        "list_entries",
        side_effect=WorkspaceError(WorkspaceFailure.LIMIT),
    ):
        result = asyncio.run(agent.propose(request))
    assert result.acquisition_failure is AcquisitionFailure.BUDGET and model.calls == 0
    with patch.object(
        type(reader.reads.workspace),
        "read_text",
        side_effect=WorkspaceError(WorkspaceFailure.EXCLUDED),
    ):
        result = asyncio.run(agent.propose(request))
    assert (
        result.acquisition_failure is AcquisitionFailure.UNAVAILABLE
        and model.calls == 0
    )
