"""Read a selected local file through the Port and reuse M1 literal inspection."""

import argparse
from pathlib import Path

from legoai_engineering.repository.api import inspect_text
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.ports import RepositoryWorkspacePort
from legoai_engineering.repository.values import InspectionRequest, InspectionResult
from legoai_engineering.repository.workspace import (
    RepositoryPath,
    WorkspaceEntryKind,
    WorkspacePolicy,
)


def inspect_project(workspace: RepositoryWorkspacePort) -> InspectionResult:
    """Consumer depends only on the replaceable Port and M1 contracts."""
    selected = RepositoryPath("pyproject.toml")
    entries = workspace.list_entries(None)
    if not any(
        entry.path == selected and entry.kind is WorkspaceEntryKind.FILE
        for entry in entries
    ):
        raise ValueError("workspace must contain pyproject.toml")
    text = workspace.read_text(selected)
    return inspect_text(InspectionRequest((text,), "requires-python", 10))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="explicit absolute local workspace root")
    arguments = parser.parse_args()
    policy = WorkspacePolicy(
        max_read_bytes=262_144,
        max_text_chars=65_536,
        max_entries=512,
        max_depth=16,
        excluded_names=(".git", ".venv", "__pycache__", "build", "dist"),
    )
    try:
        workspace = LocalRepositoryWorkspace(LocalWorkspaceRoot(arguments.root), policy)
        result = inspect_project(workspace)
    except (WorkspaceError, ValueError) as error:
        parser.exit(1, f"workspace intake failed: {error}\n")
    for match in result.matches:
        print(f"{match.path}:{match.line}:{match.column}")


if __name__ == "__main__":
    main()
