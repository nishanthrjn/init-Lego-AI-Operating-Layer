"""Create and update a disposable workspace through typed changesets."""

from pathlib import Path
from tempfile import TemporaryDirectory

from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.mutation import (
    FileChange,
    FileChangeKind,
    RepositoryChangeSet,
    digest_text,
)
from legoai_engineering.repository.mutation_local import LocalRepositoryMutation
from legoai_engineering.repository.mutation_ports import RepositoryMutationPort
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy


def main() -> None:
    with TemporaryDirectory(prefix="legoai-m4-") as directory:
        root = LocalWorkspaceRoot(Path(directory).resolve())
        policy = WorkspacePolicy(4096, 1024, 128, 8, (".git", ".venv"))
        port: RepositoryMutationPort = LocalRepositoryMutation(root, policy)
        path = RepositoryPath("greeting.txt")
        port.apply(
            RepositoryChangeSet(
                (FileChange(path, FileChangeKind.CREATE, None, "hello\n"),)
            )
        )
        reader = LocalRepositoryWorkspace(root, policy)
        original = reader.read_text(path)
        result = port.apply(
            RepositoryChangeSet(
                (
                    FileChange(
                        path,
                        FileChangeKind.UPDATE,
                        digest_text(original.text),
                        "hello LegoAI\n",
                    ),
                )
            )
        )
        print(f"{result.applied[0].kind.value}: {path.value}")
        print(reader.read_text(path).text, end="")


if __name__ == "__main__":
    main()
