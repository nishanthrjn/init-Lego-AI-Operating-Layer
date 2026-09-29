"""Build and isolated wheel use; executed only by the user's local pytest run."""

import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=120, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def test_build_inventory_and_fresh_install(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    artifacts = tmp_path / "artifacts"
    run(
        ["uv", "build", "--no-build-isolation", "--out-dir", str(artifacts)],
        root,
    )
    wheels = list(artifacts.glob("*.whl"))
    archives = list(artifacts.glob("*.tar.gz"))
    assert len(wheels) == len(archives) == 1
    expected = {
        "legoai_engineering/__init__.py",
        "legoai_engineering/py.typed",
        "legoai_engineering/repository/__init__.py",
        "legoai_engineering/repository/values.py",
        "legoai_engineering/repository/api.py",
        "legoai_engineering/repository/errors.py",
        "legoai_engineering/repository/workspace.py",
        "legoai_engineering/repository/ports.py",
        "legoai_engineering/repository/local.py",
        "legoai_engineering/repository/mutation.py",
        "legoai_engineering/repository/mutation_ports.py",
        "legoai_engineering/repository/mutation_errors.py",
        "legoai_engineering/repository/mutation_local.py",
        "legoai_engineering/git/__init__.py",
        "legoai_engineering/git/values.py",
        "legoai_engineering/git/errors.py",
        "legoai_engineering/git/ports.py",
        "legoai_engineering/git/local.py",
        "legoai_engineering/git/_config.py",
        "legoai_engineering/git/_parse.py",
        "legoai_engineering/git/_process.py",
        "legoai_engineering/checks/__init__.py",
        "legoai_engineering/checks/values.py",
        "legoai_engineering/checks/errors.py",
        "legoai_engineering/checks/ports.py",
        "legoai_engineering/checks/local.py",
        "legoai_engineering/checks/_process.py",
        "legoai_engineering/sandbox/__init__.py",
        "legoai_engineering/sandbox/values.py",
        "legoai_engineering/sandbox/errors.py",
        "legoai_engineering/sandbox/ports.py",
        "legoai_engineering/sandbox/docker.py",
        "legoai_engineering/sandbox/_process.py",
        "legoai_engineering/sandbox/_programs.py",
        "legoai_engineering/analyst/__init__.py",
        "legoai_engineering/analyst/values.py",
        "legoai_engineering/analyst/api.py",
        "legoai_engineering/analyst/_composition.py",
        "legoai_engineering/reviewer/__init__.py",
        "legoai_engineering/reviewer/definition.py",
        "legoai_engineering/reviewer/values.py",
        "legoai_engineering/reviewer/api.py",
        "legoai_engineering/coding/__init__.py",
        "legoai_engineering/coding/definition.py",
        "legoai_engineering/coding/values.py",
        "legoai_engineering/coding/api.py",
        "legoai_engineering/coding/_composition.py",
    }
    with zipfile.ZipFile(wheels[0]) as wheel:
        package_files = {name for name in wheel.namelist() if ".dist-info/" not in name}
        assert package_files == expected
        metadata_path = next(
            name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = wheel.read(metadata_path).decode("utf-8")
        requirements = [
            line for line in metadata.splitlines() if line.startswith("Requires-Dist:")
        ]
        assert len(requirements) == 1
        assert "legoai-reference==0.1.0.dev0" in requirements[0]
        assert (
            'extra == "analyst"' in requirements[0]
            or "extra == 'analyst'" in requirements[0]
        )
        assert "Requires-Python: >=3.14,<3.15" in metadata or (
            "Requires-Python: <3.15,>=3.14" in metadata
        )
    with tarfile.open(archives[0]) as archive:
        paths = {name.partition("/")[2] for name in archive.getnames()}
        assert {f"src/{name}" for name in expected} <= paths
        assert "examples/repository_intake.py" in paths
        assert "examples/workspace_intake.py" in paths
        assert "examples/git_intake.py" in paths
        assert "examples/mutation_intake.py" in paths
        assert "examples/check_intake.py" in paths
        assert "examples/sandbox_intake.py" in paths
        assert "examples/repository_analyst.py" in paths
        assert "examples/governed_demo.py" in paths
        assert "examples/independent_reviewer.py" in paths
        assert "tests/test_reviewer.py" in paths
        assert "examples/bounded_coding.py" in paths
        assert "tests/test_coding.py" in paths
        assert "tests/test_coding_m4.py" in paths
        assert "tests/test_analyst.py" in paths
        assert "tests/test_analyst_architecture.py" in paths
        assert "tests/test_sandbox.py" in paths
        assert "tests/test_sandbox_docker.py" in paths
        assert "tests/test_sandbox_checks_docker.py" in paths
        assert "sandbox-images/python-checks/Dockerfile" in paths
        assert "sandbox-images/python-checks/requirements.txt" in paths
        assert "tests/test_checks.py" in paths
        assert "tests/test_mutation.py" in paths
        assert "tests/test_git.py" in paths
        assert "tests/test_repository.py" in paths
    environment = tmp_path / "installed"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / (
        "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    )
    run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--offline",
            "--no-deps",
            str(wheels[0]),
        ],
        tmp_path,
    )
    script = """
import sys
from pathlib import Path
import legoai_engineering
from legoai_engineering.sandbox.docker import DockerSandbox, DockerSandboxConfig
from legoai_engineering.sandbox.ports import SandboxExecutionPort
from legoai_engineering.sandbox.values import SandboxRequest, SandboxPolicy
sandbox: SandboxExecutionPort = DockerSandbox(
    DockerSandboxConfig(Path(sys.executable).parent / 'docker.exe'), SandboxPolicy()
)
assert SandboxRequest('print(1)').files == ()
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure
try:
    sandbox.execute(SandboxRequest('pass'))
except SandboxError as error:
    assert error.reason in {
        SandboxFailure.RUNTIME_UNAVAILABLE, SandboxFailure.UNSUPPORTED,
    }
else:
    raise AssertionError('fresh environment must not contain Docker CLI')
from legoai_engineering.repository.api import inspect_text
from legoai_engineering.repository.values import InspectionRequest, RepositoryText
assert Path(legoai_engineering.__file__).resolve().is_relative_to(Path(sys.prefix))
result = inspect_text(InspectionRequest((RepositoryText('a', 'x\\nx'),), 'x', 1))
assert result.truncated and len(result.matches) == 1
assert result.matches[0].line == result.matches[0].column == 1
from legoai_engineering.repository.local import LocalRepositoryWorkspace, LocalWorkspaceRoot
from legoai_engineering.repository.ports import RepositoryWorkspacePort
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy
root = Path(sys.argv[1])
workspace: RepositoryWorkspacePort = LocalRepositoryWorkspace(
    LocalWorkspaceRoot(root), WorkspacePolicy(128, 128, 10, 3, ())
)
assert workspace.list_entries(None)[0].path.value == 'sample.txt'
assert workspace.read_text(RepositoryPath('sample.txt')).text == 'hello'
import shutil
from legoai_engineering.git.local import GitReadPolicy, LocalGitExecutable, LocalGitRepository
from legoai_engineering.git.ports import GitRepositoryPort
from legoai_engineering.git.errors import GitError, GitFailure
git = shutil.which('git')
assert git is not None, 'M3 qualification requires Git'
port: GitRepositoryPort = LocalGitRepository(
    LocalWorkspaceRoot(root), LocalGitExecutable(Path(git)),
    GitReadPolicy(5, 4096, 10, 128),
)
try:
    port.inspect()
except GitError as error:
    assert error.reason is GitFailure.NOT_REPOSITORY
else:
    raise AssertionError('non-repository accepted')
import os, subprocess
fixture = root / 'git-fixture'
fixture.mkdir()
environment = {
    'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
    'GIT_CONFIG_SYSTEM': os.devnull,
}
if os.name == 'nt':
    environment['SystemRoot'] = os.environ['SystemRoot']
subprocess.run(
    [git, 'init', '--initial-branch=main', '--template='],
    cwd=fixture, env=environment, check=True, capture_output=True, timeout=15,
)
port = LocalGitRepository(
    LocalWorkspaceRoot(fixture), LocalGitExecutable(Path(git)),
    GitReadPolicy(5, 4096, 10, 128),
)
from legoai_engineering.git.values import GitHeadKind
state = port.inspect()
assert state.head.kind is GitHeadKind.UNBORN and state.entries == ()
from legoai_engineering.repository.mutation import (
    FileChange, FileChangeKind, RepositoryChangeSet, digest_text,
)
from legoai_engineering.repository.mutation_local import LocalRepositoryMutation
from legoai_engineering.repository.mutation_ports import RepositoryMutationPort
writer: RepositoryMutationPort = LocalRepositoryMutation(
    LocalWorkspaceRoot(root), WorkspacePolicy(128, 128, 128, 8, ('.git',)),
)
result = writer.apply(RepositoryChangeSet((FileChange(
    RepositoryPath('sample.txt'), FileChangeKind.UPDATE, digest_text('hello'), 'updated',
),)))
assert result.applied[0].after == digest_text('updated')
assert workspace.read_text(RepositoryPath('sample.txt')).text == 'updated'
from legoai_engineering.checks.local import LocalCheckTools, LocalEngineeringChecks
from legoai_engineering.checks.ports import EngineeringCheckPort
from legoai_engineering.checks.values import CheckKind, CheckPolicy, CheckRequest
from legoai_engineering.checks.errors import CheckError, CheckFailure
import importlib.util
assert all(importlib.util.find_spec(name) is None for name in ('pytest', 'ruff', 'mypy'))
assert importlib.util.find_spec('legoai') is None
base = Path(sys.executable).parent
suffix = '.exe' if os.name == 'nt' else ''
checks: EngineeringCheckPort = LocalEngineeringChecks(
    LocalWorkspaceRoot(root),
    LocalCheckTools(*(base / (name + suffix) for name in ('pytest', 'ruff', 'mypy'))),
    CheckPolicy(),
)
try:
    checks.check(CheckRequest(CheckKind.RUFF_CHECK, (RepositoryPath('sample.txt'),)))
except CheckError as error:
    assert error.reason is CheckFailure.UNAVAILABLE
else:
    raise AssertionError('fresh environment unexpectedly contains Ruff')
"""
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    (workspace_root / "sample.txt").write_text("hello", encoding="utf-8")
    run([str(python), "-I", "-B", "-c", script, str(workspace_root)], tmp_path)
    # The base installation above still works without Core. Now install the
    # existing Core wheel offline to qualify the optional Analyst composition.
    core_artifacts = tmp_path / "core-artifacts"
    run(
        ["uv", "build", "--no-build-isolation", "--out-dir", str(core_artifacts)],
        root.parents[1],
    )
    core_wheel = next(core_artifacts.glob("*.whl"))
    run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--offline",
            "--no-deps",
            str(core_wheel),
        ],
        tmp_path,
    )
    example = tmp_path / "repository_analyst.py"
    example.write_bytes((root / "examples" / "repository_analyst.py").read_bytes())
    (tmp_path / "governed_demo.py").write_bytes(
        (root / "examples" / "governed_demo.py").read_bytes()
    )
    # Only the copied example directory is added; no checkout or editable Core.
    runner = (
        "import runpy, sys; sys.path.insert(0, sys.argv[1]); "
        "runpy.run_path(sys.argv[2], run_name='__main__')"
    )
    result = run(
        [str(python), "-I", "-B", "-c", runner, str(tmp_path), str(example)], tmp_path
    )
    assert result.stdout.splitlines() == [
        "succeeded",
        "a.py, b.py",
        "The supplied files define and import greet.",
    ]
    reviewer_example = tmp_path / "independent_reviewer.py"
    reviewer_example.write_bytes(
        (root / "examples" / "independent_reviewer.py").read_bytes()
    )
    result = run(
        [str(python), "-I", "-B", "-c", runner, str(tmp_path), str(reviewer_example)],
        tmp_path,
    )
    assert result.stdout.splitlines() == [
        "changes_required",
        "correctness",
        "The proposal needs a missing-input policy.",
    ]
    coding_example = tmp_path / "bounded_coding.py"
    coding_example.write_bytes((root / "examples" / "bounded_coding.py").read_bytes())
    result = run(
        [str(python), "-I", "-B", "-c", runner, str(tmp_path), str(coding_example)],
        tmp_path,
    )
    assert result.stdout.splitlines() == [
        "succeeded",
        "1 proposed change",
        "example.py update",
    ]
