"""External test-driver M4 handoff; the Coding Agent itself never calls apply."""

import asyncio
import json
from pathlib import Path

import pytest
from bounded_coding import create_demo

from legoai_engineering.coding.values import CodingTarget
from legoai_engineering.repository.local import LocalWorkspaceRoot
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.mutation_errors import MutationConflict, MutationConflictReason
from legoai_engineering.repository.mutation_local import LocalRepositoryMutation
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy


@pytest.mark.parametrize("kind", [FileChangeKind.CREATE, FileChangeKind.UPDATE])
def test_m4_rechecks_proposal_preconditions_at_external_apply(tmp_path: Path, kind: FileChangeKind) -> None:
    file = tmp_path / "target.py"
    if kind is FileChangeKind.UPDATE:
        file.write_bytes(b"original\r\n")
    text = json.dumps({
        "summary": "Propose replacement.",
        "changes": [{"path": "target.py", "operation": kind.value, "content": "new\n", "reason": "Requested."}],
        "risks": [], "unknowns": [],
    })
    agent, request, _ = create_demo(tmp_path, text, (CodingTarget(RepositoryPath("target.py"), kind),))
    before = file.read_bytes() if file.exists() else None
    result = asyncio.run(agent.propose(request))
    assert (file.read_bytes() if file.exists() else None) == before
    assert result.proposal is not None
    # Simulate a later independent edit. Only this test driver calls M4; no
    # production auto-apply path, grant or Workflow is introduced by this test.
    file.write_bytes(b"later edit")
    writer = LocalRepositoryMutation(LocalWorkspaceRoot(tmp_path), WorkspacePolicy(8192, 8192, 16, 8, (".git", ".venv")))
    with pytest.raises(MutationConflict) as failure:
        writer.apply(result.proposal.changeset)
    expected = MutationConflictReason.EXISTS if kind is FileChangeKind.CREATE else MutationConflictReason.STALE
    assert failure.value.reason is expected
    assert file.read_bytes() == b"later edit"
