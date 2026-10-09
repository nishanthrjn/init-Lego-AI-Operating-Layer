"""Prepared environment contracts: deterministic tests never acquire dependencies."""

import dataclasses
import json
import shutil
from pathlib import Path

import pytest

from legoai_engineering.checks import preparation
from legoai_engineering.checks.preparation import inspect_check_project
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.workspace import WorkspacePolicy
from legoai_engineering.sandbox.docker import DockerSandboxConfig, SandboxImage
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure
from legoai_engineering.sandbox.prepared import (
    PreparationError,
    PreparationFailure,
    PreparedCheckEnvironment,
    _mint,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "examples/forgeai/fixtures/project_checks"
BASE = "sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df"


def workspace(root: Path) -> LocalRepositoryWorkspace:
    return LocalRepositoryWorkspace(
        LocalWorkspaceRoot(root),
        WorkspacePolicy(262144, 65536, 4096, 32, (".git", ".venv")),
    )


def fixture(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(FIXTURE, root)
    return root


def test_metadata_and_locked_export(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    metadata = inspect_check_project(workspace(root))
    assert metadata == inspect_check_project(workspace(root))
    assert metadata.python_requirement == ">=3.14,<3.15"
    assert "idna" not in repr(metadata)
    uv = shutil.which("uv")
    assert uv
    export = tmp_path / "export"
    export.mkdir()
    requirements = preparation._export(metadata, Path(uv), export)
    assert "idna==3.20" in requirements and "--hash=sha256:" in requirements
    assert "forgeai-project-check-fixture" not in requirements


def test_missing_lock(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    (root / "uv.lock").unlink()
    with pytest.raises(PreparationError) as failure:
        inspect_check_project(workspace(root))
    assert failure.value.reason is PreparationFailure.LOCK_REQUIRED


def test_invalid_lock_and_source_only_dependency(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    lock = root / "uv.lock"
    original = lock.read_text()
    lock.write_text("[invalid")
    with pytest.raises(PreparationError, match="lock_invalid"):
        inspect_check_project(workspace(root))
    lock.write_text(original.replace("wheels = [", "ignored = ["))
    with pytest.raises(PreparationError, match="dependency_unavailable"):
        inspect_check_project(workspace(root))


@pytest.mark.parametrize(
    "extra",
    [
        '\n[tool.uv.sources]\nidna = { path = "../other" }\n',
        '\n[dependency-groups]\ntest = ["idna"]\n',
    ],
)
def test_unsupported_configuration(tmp_path: Path, extra: str) -> None:
    root = fixture(tmp_path)
    path = root / "pyproject.toml"
    path.write_text(path.read_text() + extra)
    with pytest.raises(PreparationError, match="unsupported_project"):
        inspect_check_project(workspace(root))


def test_inconsistent_lock_is_not_resolved(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    path = root / "pyproject.toml"
    path.write_text(path.read_text().replace("idna==3.20", "idna==1.0"))
    metadata = inspect_check_project(workspace(root))
    uv = shutil.which("uv")
    assert uv
    export = tmp_path / "export"
    export.mkdir()
    with pytest.raises(PreparationError, match="lock_invalid"):
        preparation._export(metadata, Path(uv), export)


def test_repository_commands_and_dockerfile_are_not_exported(tmp_path: Path) -> None:
    root = fixture(tmp_path)
    (root / "Dockerfile").write_text("RUN touch /evil")
    (root / "setup.py").write_text("raise RuntimeError('must not execute')")
    path = root / "pyproject.toml"
    path.write_text(path.read_text() + '\n[tool.untrusted]\nsetup = "touch /evil"\n')
    metadata = inspect_check_project(workspace(root))
    uv = shutil.which("uv")
    assert uv
    export = tmp_path / "export"
    export.mkdir()
    assert "evil" not in preparation._export(metadata, Path(uv), export)
    assert {p.name for p in export.iterdir()} == {"uv.lock", "pyproject.toml"}


def test_prepared_identity_is_not_an_image_string(tmp_path: Path) -> None:
    executable = tmp_path / "docker.exe"
    with pytest.raises(TypeError):
        PreparedCheckEnvironment()
    for image in ("latest", "sha256:" + "a" * 64):
        with pytest.raises(TypeError):
            DockerSandboxConfig(executable, image)  # type: ignore[arg-type]
    with pytest.raises(PreparationError):
        _mint(BASE, BASE, BASE, "latest")
    value = _mint(BASE, BASE, BASE, "sha256:" + "b" * 64)
    assert DockerSandboxConfig(executable, value).image == value.image
    assert DockerSandboxConfig(executable, SandboxImage.PYTHON_CHECKS).image == BASE
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.image = "latest"  # type: ignore[misc]
    assert not any(
        "path" in f.name or "command" in f.name for f in dataclasses.fields(value)
    )


class FakeCli:
    def __init__(self, status: str = "prepared") -> None:
        self.status = status
        self.calls: list[list[str]] = []
        self.payload = b""

    def _run(
        self,
        args: list[str],
        deadline: float,
        limit: int = 65536,
        cancellation: object = None,
        payload: bytes | None = None,
    ) -> tuple[int, bytes, bytes]:
        self.calls.append(args)
        if args[0] == "start":
            self.payload = payload or b""
            return (
                int(self.status != "prepared"),
                json.dumps({"status": self.status}).encode(),
                b"",
            )
        if args[0] == "commit":
            return 0, ("sha256:" + "b" * 64).encode(), b""
        if args[:2] == ["container", "ls"]:
            return 0, b"", b""
        return 0, b"", b""


@pytest.mark.parametrize("status", ["prepared", *[r.value for r in PreparationFailure]])
def test_preparation_failure_never_mints_or_commits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
) -> None:
    metadata = inspect_check_project(workspace(fixture(tmp_path)))
    cli = FakeCli(status)
    monkeypatch.setattr(preparation, "_preflight", lambda *args: None)
    monkeypatch.setattr(
        preparation,
        "_state",
        lambda *args: {"Status": "exited", "ExitCode": int(status != "prepared")},
    )
    if status == "prepared":
        result = preparation._prepare(cli, BASE, metadata, "idna==3.20")  # type: ignore[arg-type]
        assert result.image == "sha256:" + "b" * 64
    else:
        with pytest.raises(PreparationError, match=status):
            preparation._prepare(cli, BASE, metadata, "idna==3.20")  # type: ignore[arg-type]
        assert not any(args[0] == "commit" for args in cli.calls)
    create = cli.calls[0]
    assert "--network=bridge" in create and "--pull=never" in create
    assert not any(args[0] in {"build", "pull"} for args in cli.calls)
    data = json.loads(cli.payload)
    assert set(data) == {"python", "requirements", "identity"}
    assert metadata.manifest not in cli.payload.decode()


def test_timeout_is_terminal_and_cleanup_is_attempted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    metadata = inspect_check_project(workspace(fixture(tmp_path)))
    cli = FakeCli()
    original = cli._run

    def timed_out(args, *positional, **keywords):  # type: ignore[no-untyped-def]
        if args[0] == "start":
            raise SandboxError(SandboxFailure.TIMEOUT)
        return original(args, *positional, **keywords)

    monkeypatch.setattr(cli, "_run", timed_out)
    monkeypatch.setattr(preparation, "_preflight", lambda *args: None)
    with pytest.raises(PreparationError, match="preparation_timeout"):
        preparation._prepare(cli, BASE, metadata, "")  # type: ignore[arg-type]
    assert any(args[:2] == ["container", "ls"] for args in cli.calls)
    assert not any(args[0] == "commit" for args in cli.calls)


def test_cleanup_failure_retains_resource_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli = FakeCli()

    def unavailable(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise SandboxError(SandboxFailure.CONTROL)

    monkeypatch.setattr(cli, "_run", unavailable)
    with pytest.raises(SandboxError) as failure:
        preparation._cleanup_preparation(cli, "legoai-m6-prep-test", False)  # type: ignore[arg-type]
    assert failure.value.reason is SandboxFailure.CLEANUP
    assert failure.value.__cause__ is not None
