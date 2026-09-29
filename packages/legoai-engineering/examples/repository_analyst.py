"""Offline Repository Analyst composition; read authority comes from the host."""

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from governed_demo import NOW, READ_ACTION, WORKSPACE, StaticModel, create_governed_demo

from legoai_engineering.analyst.api import RepositoryAnalyst
from legoai_engineering.analyst.authorized import AuthorizedRepositoryEvidence
from legoai_engineering.analyst.values import RepositoryAnalysisRequest
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy


def create_demo(
    root: Path,
    output: str,
    *,
    route_count: int = 1,
    read_allowed: bool = True,
    model_allowed: bool = True,
    targets: tuple[RepositoryPath, ...] = (
        RepositoryPath("a.py"),
        RepositoryPath("b.py"),
    ),
) -> tuple[RepositoryAnalyst, RepositoryAnalysisRequest, StaticModel]:
    demo = create_governed_demo(
        output,
        route_count=route_count,
        read_allowed=read_allowed,
        model_allowed=model_allowed,
    )
    workspace_reference = replace(demo.configuration, instance=WORKSPACE)
    reader = AuthorizedRepositoryEvidence(
        workspace_reference,
        LocalRepositoryWorkspace(
            LocalWorkspaceRoot(root),
            WorkspacePolicy(8192, 8192, 16, 8, (".git", ".venv")),
        ),
        demo.host.security_context(workspace_reference, READ_ACTION, WORKSPACE),
        demo.host.authorization,
        targets,
        lambda: NOW,
    )
    request = RepositoryAnalysisRequest(
        "Which files implement the supplied behavior?",
        targets,
        demo.context,
    )
    return RepositoryAnalyst(reader, demo.runtime), request, demo.model


async def main() -> None:
    with TemporaryDirectory(prefix="legoai-analyst-") as temporary:
        root = Path(temporary)
        (root / "a.py").write_text("def greet(): return 'hello'\n", encoding="utf-8")
        (root / "b.py").write_text("from a import greet\n", encoding="utf-8")
        output = json.dumps(
            {
                "status": "succeeded",
                "summary": "The supplied files define and import greet.",
                "relevant_files": ["a.py", "b.py"],
                "findings": [{"text": "greet is defined here.", "paths": ["a.py"]}],
                "risks": [],
                "unknowns": ["Runtime behavior was not executed."],
            }
        )
        analyst, request, model = create_demo(root, output)
        result = await analyst.analyze(request)
        assert result.analysis is not None and model.calls == 1
        print(result.status.value)
        print(", ".join(p.value for p in result.analysis.relevant_files))
        print(result.analysis.summary)


if __name__ == "__main__":
    asyncio.run(main())
