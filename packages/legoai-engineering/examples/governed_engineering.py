"""Offline governed engineering path through public APIs only (CR-3).

The composition root below opens the public local host, then wires authorized
reads, the Coding Agent, an authorized mutation and an authorized check. Each
effect has its own operator grant and is re-authorized immediately before it
runs. The check adapter is chosen here: `StaticChecks` is a deterministic
demonstration stand-in; real applications select `LocalEngineeringChecks`
(trusted code) or `SandboxedEngineeringChecks` (contained untrusted code).
"""

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from governed_demo import NOW, WORKSPACE, StaticModel, create_governed_demo

from legoai_engineering.analyst.authorized import (
    REPOSITORY_READ_ACTION,
    AuthorizedRepositoryEvidence,
)
from legoai_engineering.checks.authorized import (
    ENGINEERING_CHECK_ACTION,
    AuthorizedEngineeringChecks,
)
from legoai_engineering.checks.ports import EngineeringCheckPort
from legoai_engineering.checks.values import CheckKind, CheckRequest, CheckResult
from legoai_engineering.coding.api import CodingAgent
from legoai_engineering.coding.authorized import AuthorizedCodingEvidence
from legoai_engineering.coding.values import CodingRequest, CodingTarget
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


class StaticChecks:
    """Demonstration-only EngineeringCheckPort; runs nothing, always exit 0."""

    def __init__(self) -> None:
        self.requests: list[CheckRequest] = []

    def check(self, request: CheckRequest) -> CheckResult:
        self.requests.append(request)
        return CheckResult(request.kind, 0, b"", b"")


@dataclass(frozen=True)
class GovernedEngineering:
    agent: CodingAgent
    request: CodingRequest
    mutation: RepositoryMutationPort
    checks: EngineeringCheckPort
    model: StaticModel


def create_engineering_demo(
    root: Path,
    output: str,
    targets: tuple[CodingTarget, ...],
    *,
    checks: EngineeringCheckPort | None = None,
    read_allowed: bool = True,
    write_allowed: bool = True,
    check_allowed: bool = True,
    clock: Callable[[], datetime] = lambda: NOW,
) -> GovernedEngineering:
    demo = create_governed_demo(
        output,
        read_allowed=read_allowed,
        write_allowed=write_allowed,
        check_allowed=check_allowed,
    )
    host = demo.host
    workspace_reference = replace(demo.configuration, instance=WORKSPACE)
    policy = WorkspacePolicy(8192, 8192, 16, 8, (".git", ".venv"))
    reads = AuthorizedRepositoryEvidence(
        workspace_reference,
        LocalRepositoryWorkspace(LocalWorkspaceRoot(root), policy),
        host.security_context(workspace_reference, REPOSITORY_READ_ACTION, WORKSPACE),
        host.authorization,
        tuple(target.path for target in targets),
        clock,
    )
    mutation = AuthorizedRepositoryMutation(
        workspace_reference,
        LocalRepositoryMutation(LocalWorkspaceRoot(root), policy),
        host.security_context(
            workspace_reference, REPOSITORY_MUTATION_ACTION, WORKSPACE
        ),
        host.authorization,
        clock,
    )
    authorized_checks = AuthorizedEngineeringChecks(
        workspace_reference,
        checks if checks is not None else StaticChecks(),
        host.security_context(workspace_reference, ENGINEERING_CHECK_ACTION, WORKSPACE),
        host.authorization,
        clock,
    )
    request = CodingRequest(
        "Change the greeting to hello LegoAI.",
        targets,
        ("Return a proposal only.",),
        demo.context,
    )
    return GovernedEngineering(
        CodingAgent(AuthorizedCodingEvidence(reads), demo.runtime),
        request,
        mutation,
        authorized_checks,
        demo.model,
    )


async def main() -> None:
    with TemporaryDirectory(prefix="legoai-governed-engineering-") as temporary:
        root = Path(temporary)
        (root / "greeting.py").write_bytes(b"GREETING = 'hello'\n")
        output = json.dumps(
            {
                "summary": "Update the greeting.",
                "changes": [
                    {
                        "path": "greeting.py",
                        "operation": "update",
                        "content": "GREETING = 'hello LegoAI'\n",
                        "reason": "Match the requested greeting.",
                    }
                ],
                "risks": [],
                "unknowns": ["Generated source was not executed."],
            }
        )
        demo = create_engineering_demo(
            root,
            output,
            (CodingTarget(RepositoryPath("greeting.py"), FileChangeKind.UPDATE),),
        )
        result = await demo.agent.propose(demo.request)
        assert result.proposal is not None and demo.model.calls == 1
        applied = demo.mutation.apply(result.proposal.changeset)
        check = demo.checks.check(
            CheckRequest(CheckKind.RUFF_CHECK, (RepositoryPath("greeting.py"),))
        )
        print(result.status.value)
        print(f"applied {applied.applied[0].path.value}")
        print((root / "greeting.py").read_text(encoding="utf-8").strip())
        print(f"{check.kind.value} {check.outcome.value}")


if __name__ == "__main__":
    asyncio.run(main())
