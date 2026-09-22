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
    }
    with zipfile.ZipFile(wheels[0]) as wheel:
        package_files = {name for name in wheel.namelist() if ".dist-info/" not in name}
        assert package_files == expected
        metadata_path = next(
            name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = wheel.read(metadata_path).decode("utf-8")
        assert "Requires-Dist:" not in metadata
        assert "Requires-Python: >=3.14,<3.15" in metadata or (
            "Requires-Python: <3.15,>=3.14" in metadata
        )
    with tarfile.open(archives[0]) as archive:
        paths = {name.partition("/")[2] for name in archive.getnames()}
        assert {f"src/{name}" for name in expected} <= paths
        assert "examples/repository_intake.py" in paths
        assert "examples/workspace_intake.py" in paths
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
"""
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    (workspace_root / "sample.txt").write_text("hello", encoding="utf-8")
    run([str(python), "-I", "-B", "-c", script, str(workspace_root)], tmp_path)
