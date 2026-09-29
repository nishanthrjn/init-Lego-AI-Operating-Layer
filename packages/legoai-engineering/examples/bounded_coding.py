"""Offline Coding Agent proposes one change; the workspace remains unchanged."""

import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from governed_demo import StaticModel
from repository_analyst import create_demo as create_analyst_demo

from legoai_engineering.analyst.authorized import AuthorizedRepositoryEvidence
from legoai_engineering.coding.api import CodingAgent
from legoai_engineering.coding.authorized import AuthorizedCodingEvidence
from legoai_engineering.coding.values import CodingRequest, CodingTarget
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.workspace import RepositoryPath


def create_demo(
    root: Path,
    output: str,
    targets: tuple[CodingTarget, ...],
    *,
    route_count: int = 1,
    read_allowed: bool = True,
    model_allowed: bool = True,
) -> tuple[CodingAgent, CodingRequest, StaticModel]:
    analyst, source, model = create_analyst_demo(
        root,
        output,
        route_count=route_count,
        read_allowed=read_allowed,
        model_allowed=model_allowed,
        targets=tuple(target.path for target in targets),
    )
    reads = analyst.evidence_reader
    assert isinstance(reads, AuthorizedRepositoryEvidence)
    request = CodingRequest(
        "Change the greeting to hello LegoAI.",
        targets,
        ("Return a proposal only; do not apply or execute it.",),
        source.context,
    )
    return (
        CodingAgent(AuthorizedCodingEvidence(reads), analyst.agent_runtime),
        request,
        model,
    )


async def main() -> None:
    with TemporaryDirectory(prefix="legoai-coding-") as temporary:
        root = Path(temporary)
        file = root / "example.py"
        original = b"GREETING = 'hello'\r\n"
        file.write_bytes(original)
        output = json.dumps(
            {
                "summary": "Update the greeting.",
                "changes": [
                    {
                        "path": "example.py",
                        "operation": "update",
                        "content": "GREETING = 'hello LegoAI'\r\n",
                        "reason": "Match the requested greeting.",
                    }
                ],
                "risks": [],
                "unknowns": ["Generated source was not executed."],
            }
        )
        agent, request, model = create_demo(
            root,
            output,
            (CodingTarget(RepositoryPath("example.py"), FileChangeKind.UPDATE),),
        )
        result = await agent.propose(request)
        assert result.proposal is not None and model.calls == 1
        assert file.read_bytes() == original
        assert tuple(p.name for p in root.iterdir()) == ("example.py",)
        change = result.proposal.changeset.changes[0]
        print(result.status.value)
        print("1 proposed change")
        print(f"{change.path.value} {change.kind.value}")


if __name__ == "__main__":
    asyncio.run(main())
