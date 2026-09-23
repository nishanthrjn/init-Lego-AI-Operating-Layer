"""Run locally with Docker Desktop Linux and the preloaded pinned image."""

import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy
from legoai_engineering.sandbox.docker import DockerSandbox, DockerSandboxConfig
from legoai_engineering.sandbox.ports import SandboxExecutionPort
from legoai_engineering.sandbox.values import SandboxRequest


def main() -> None:
    executable = shutil.which("docker")
    if executable is None:
        raise RuntimeError(
            "Docker Desktop Linux is required; no automatic installation"
        )
    sandbox: SandboxExecutionPort = DockerSandbox(DockerSandboxConfig(Path(executable)))
    with TemporaryDirectory(prefix="legoai sandbox example ") as directory:
        root = Path(directory)
        script = (
            "import os, pathlib\n"
            "assert 'LEGOAI_SANDBOX_SECRET' not in os.environ\n"
            "assert os.getuid() == 65534\n"
            "pathlib.Path('result.txt').write_text('hello isolated LegoAI')\n"
        )
        (root / "workload.py").write_text(script, encoding="utf-8")
        workspace = LocalRepositoryWorkspace(
            LocalWorkspaceRoot(root),
            WorkspacePolicy(65_536, 65_536, 16, 8, (".git", ".venv")),
        )
        supplied = workspace.read_text(RepositoryPath("workload.py"))
        previous = os.environ.get("LEGOAI_SANDBOX_SECRET")
        try:
            # Process-local synthetic value only; restored even on failure.
            os.environ["LEGOAI_SANDBOX_SECRET"] = "example-synthetic-value"
            result = sandbox.execute(
                SandboxRequest(supplied.text, artifacts=(RepositoryPath("result.txt"),))
            )
        finally:
            if previous is None:
                os.environ.pop("LEGOAI_SANDBOX_SECRET", None)
            else:
                os.environ["LEGOAI_SANDBOX_SECRET"] = previous
        assert result.exit_code == 0, result.stderr
        assert (root / "workload.py").read_text("utf-8") == script
        assert [path.name for path in root.iterdir()] == ["workload.py"]
        print(result.artifacts[0].content.decode("utf-8"))
        print("source unchanged; synthetic host secret absent")


if __name__ == "__main__":
    main()
