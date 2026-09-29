"""CR-3 structural readiness: an independent first consumer slice can compose.

A dependency and composition proof only. It shows that a governed engineering
application can assemble the Coding Agent, authorized mutation, authorized
checks, operator-facing Git observation and the public governed host from
public modules. It defines no task model, worker or application package.
"""

import ast
import asyncio
import json
import shutil
from dataclasses import replace
from pathlib import Path

from governed_demo import NOW, WORKSPACE, create_governed_demo

from legoai_engineering.analyst.authorized import (
    REPOSITORY_READ_ACTION,
    AuthorizedRepositoryEvidence,
)
from legoai_engineering.checks.authorized import (
    ENGINEERING_CHECK_ACTION,
    AuthorizedEngineeringChecks,
)
from legoai_engineering.checks.ports import EngineeringCheckPort
from legoai_engineering.checks.sandboxed import (
    CheckInputPolicy,
    SandboxedEngineeringChecks,
)
from legoai_engineering.checks.values import (
    CheckKind,
    CheckOutcome,
    CheckPolicy,
    CheckRequest,
)
from legoai_engineering.coding.api import CodingAgent
from legoai_engineering.coding.authorized import AuthorizedCodingEvidence
from legoai_engineering.coding.values import CodingRequest, CodingTarget
from legoai_engineering.git.local import (
    GitReadPolicy,
    LocalGitExecutable,
    LocalGitRepository,
)
from legoai_engineering.git.ports import GitRepositoryPort
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.mutation_authorized import (
    REPOSITORY_MUTATION_ACTION,
    AuthorizedRepositoryMutation,
)
from legoai_engineering.repository.mutation_local import LocalRepositoryMutation
from legoai_engineering.repository.mutation_ports import RepositoryMutationPort
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy
from legoai_engineering.sandbox.ports import CancellationSignal
from legoai_engineering.sandbox.values import SandboxRequest, SandboxResult


class RecordingSandbox:
    """SandboxExecutionPort stand-in answering a completed clean run."""

    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self, request: SandboxRequest, cancellation: CancellationSignal | None = None
    ) -> SandboxResult:
        self.calls += 1
        body = {"status": "completed", "exit": 0, "stdout": "", "stderr": ""}
        return SandboxResult(0, json.dumps(body).encode(), b"")


def test_first_consumer_slice_composes_from_public_modules(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "greeting.py").write_bytes(b"GREETING = 'hello'\n")
    output = json.dumps(
        {
            "summary": "Update the greeting.",
            "changes": [
                {
                    "path": "pkg/greeting.py",
                    "operation": "update",
                    "content": "GREETING = 'hello LegoAI'\n",
                    "reason": "Requested.",
                }
            ],
            "risks": [],
            "unknowns": ["Not executed."],
        }
    )
    # --- composition root: operator configuration and adapter selection ---
    demo = create_governed_demo(output)
    host = demo.host
    reference = replace(demo.configuration, instance=WORKSPACE)
    policy = WorkspacePolicy(8192, 8192, 16, 8, (".git", ".venv"))
    targets = (CodingTarget(RepositoryPath("pkg/greeting.py"), FileChangeKind.UPDATE),)
    reads = AuthorizedRepositoryEvidence(
        reference,
        LocalRepositoryWorkspace(LocalWorkspaceRoot(root), policy),
        host.security_context(reference, REPOSITORY_READ_ACTION, WORKSPACE),
        host.authorization,
        tuple(t.path for t in targets),
        lambda: NOW,
    )
    agent = CodingAgent(AuthorizedCodingEvidence(reads), host.agent_runtime())
    mutation: RepositoryMutationPort = AuthorizedRepositoryMutation(
        reference,
        LocalRepositoryMutation(LocalWorkspaceRoot(root), policy),
        host.security_context(reference, REPOSITORY_MUTATION_ACTION, WORKSPACE),
        host.authorization,
        lambda: NOW,
    )
    sandbox = RecordingSandbox()
    checks: EngineeringCheckPort = AuthorizedEngineeringChecks(
        reference,
        SandboxedEngineeringChecks(
            LocalRepositoryWorkspace(LocalWorkspaceRoot(root), policy),
            sandbox,
            CheckInputPolicy((RepositoryPath("pkg"),)),
            CheckPolicy(),
        ),
        host.security_context(reference, ENGINEERING_CHECK_ACTION, WORKSPACE),
        host.authorization,
        lambda: NOW,
    )
    executable = shutil.which("git")
    assert executable is not None, "operator Git observation requires Git"
    git: GitRepositoryPort = LocalGitRepository(
        LocalWorkspaceRoot(root),
        LocalGitExecutable(Path(executable)),
        GitReadPolicy(5, 4096, 10, 128),
    )
    # --- application flow: depends on Ports and values only ---
    request = CodingRequest(
        "Change the greeting.", targets, ("Proposal only.",), demo.context
    )
    result = asyncio.run(agent.propose(request))
    assert result.proposal is not None
    mutation.apply(result.proposal.changeset)
    check = checks.check(CheckRequest(CheckKind.RUFF_CHECK, (RepositoryPath("pkg"),)))
    assert check.outcome is CheckOutcome.PASSED and sandbox.calls == 1
    assert (root / "pkg" / "greeting.py").read_bytes() == b"GREETING = 'hello LegoAI'\n"
    assert callable(git.inspect)


def test_readiness_proof_itself_imports_only_public_modules() -> None:
    tree = ast.parse(Path(__file__).read_text("utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            assert not any(part.startswith("_") for part in parts), node.module
            assert not node.module.startswith(("legoai.reference", "forgeai"))
            assert not any(alias.name.startswith("_") for alias in node.names)
        elif isinstance(node, ast.Import):
            assert not any(
                part.startswith("_")
                for alias in node.names
                for part in alias.name.split(".")
            )
