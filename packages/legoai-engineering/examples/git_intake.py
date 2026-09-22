"""Observe an explicitly supplied local root; never initialize or change it."""

import argparse
import shutil
from pathlib import Path

from legoai_engineering.git.errors import GitError, GitFailure
from legoai_engineering.git.local import (
    GitReadPolicy,
    LocalGitExecutable,
    LocalGitRepository,
)
from legoai_engineering.git.ports import GitRepositoryPort
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.local import LocalWorkspaceRoot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="explicit absolute workspace root")
    args = parser.parse_args()
    executable = shutil.which("git")  # Host choice belongs in composition only.
    if executable is None:
        parser.exit(1, "Git executable unavailable\n")
    try:
        port: GitRepositoryPort = LocalGitRepository(
            LocalWorkspaceRoot(args.root),
            LocalGitExecutable(Path(executable)),
            GitReadPolicy(10, 1_048_576, 4096, 65_536),
        )
        state = port.inspect()
    except GitError as error:
        if error.reason is GitFailure.NOT_REPOSITORY:
            print("repository: absent at supplied root")
            return
        parser.exit(1, f"Git inspection failed: {error.reason.value}\n")
    except WorkspaceError as error:
        parser.exit(1, f"Workspace inspection failed: {error.reason.value}\n")
    except (TypeError, ValueError):
        parser.exit(1, "Invalid local Git configuration\n")
    print(f"head: {state.head.kind.value}")
    print(f"branch: {state.head.branch or '-'}")
    print(f"commit: {state.head.commit.value if state.head.commit else '-'}")
    print(f"changes: {len(state.entries)}")
    for entry in state.entries:
        code = "??" if entry.untracked else entry.index.value + entry.worktree.value
        print(f"{code} {entry.path.value}")


if __name__ == "__main__":
    main()
