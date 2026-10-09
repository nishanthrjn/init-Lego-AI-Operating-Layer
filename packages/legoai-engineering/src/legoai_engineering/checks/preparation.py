"""Explicit trusted uv-lock/wheel preparation, separate from sandbox execution.

Metadata only is copied to a private host directory for offline uv export.
A dedicated bounded container installs wheels; no repository code/build context
is supplied. Commit happens only after that container exits successfully.
"""

import hashlib
import json
import re
import sys
import tempfile
import time
import tomllib
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from legoai_engineering.checks._prepare_program import _INSTALL
from legoai_engineering.checks._process import _capture
from legoai_engineering.checks.errors import CheckError, CheckFailure
from legoai_engineering.checks.values import CheckPolicy
from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.ports import RepositoryWorkspacePort
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.sandbox._process import _Cli
from legoai_engineering.sandbox.docker import (
    DockerSandbox,
    DockerSandboxConfig,
    SandboxImage,
    _control,
    _preflight,
    _state,
)
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure
from legoai_engineering.sandbox.prepared import (
    PreparationError,
    PreparationFailure,
    PreparedCheckEnvironment,
    _mint,
)
from legoai_engineering.sandbox.values import SandboxRequest


@dataclass(frozen=True, slots=True)
class ProjectCheckMetadata:
    python_requirement: str
    manifest: str = field(repr=False)
    lock: str = field(repr=False)

    def __post_init__(self) -> None:
        for text, maximum in (
            (self.python_requirement, 128),
            (self.manifest, 65536),
            (self.lock, 262144),
        ):
            if type(text) is not str or not 1 <= len(text.encode("utf-8")) <= maximum:
                raise ValueError("invalid bounded project metadata")
        if any(ord(c) < 32 or ord(c) > 126 for c in self.python_requirement):
            raise ValueError("invalid Python requirement")


def inspect_check_project(workspace: RepositoryWorkspacePort) -> ProjectCheckMetadata:
    """Read bounded metadata through the existing workspace safety boundary."""
    try:
        manifest = workspace.read_text(RepositoryPath("pyproject.toml")).text
        for name in ("src", "tests"):
            workspace.list_entries(RepositoryPath(name))
    except WorkspaceError as error:
        raise PreparationError(PreparationFailure.UNSUPPORTED_PROJECT) from error
    try:
        lock = workspace.read_text(RepositoryPath("uv.lock")).text
    except WorkspaceError as error:
        reason = (
            PreparationFailure.LOCK_REQUIRED
            if error.reason is WorkspaceFailure.MISSING
            else PreparationFailure.LOCK_INVALID
        )
        raise PreparationError(reason) from error
    if len(manifest.encode()) > 65536 or len(lock.encode()) > 262144:
        raise PreparationError(PreparationFailure.UNSUPPORTED_PROJECT)
    try:
        locked = tomllib.loads(lock)
    except ValueError as error:
        raise PreparationError(PreparationFailure.LOCK_INVALID) from error
    try:
        project = tomllib.loads(manifest)
        metadata = project["project"]
        requirement = metadata["requires-python"]
        if (
            type(requirement) is not str
            or not 1 <= len(requirement) <= 128
            or any(ord(c) < 32 or ord(c) > 126 for c in requirement)
        ):
            raise ValueError("Python requirement")
        if metadata.get("dynamic") or metadata.get("optional-dependencies"):
            raise ValueError("dynamic metadata/extras unsupported")
        uv = project.get("tool", {}).get("uv", {})
        if uv not in ({}, {"package": False}):
            raise ValueError("custom uv configuration unsupported")
        groups = project.get("dependency-groups", {})
        if set(groups) - {"dev"}:
            raise ValueError("only dev group supported")
        for deps in (metadata.get("dependencies", []), groups.get("dev", [])):
            if type(deps) is not list or len(deps) > 64:
                raise ValueError("dependency bound")
            for dep in deps:
                if (
                    type(dep) is not str
                    or len(dep) > 512
                    or any(c in dep for c in "@:/\\\r\n")
                    or not dep.isascii()
                ):
                    raise ValueError("only named registry requirements supported")
        packages = locked["package"]
        if locked.get("version") != 1 or not 1 <= len(packages) <= 128:
            raise ValueError("unsupported lock")
        roots = 0
        for package in packages:
            source = package["source"]
            if source in ({"virtual": "."}, {"editable": "."}):
                roots += 1
                if package["name"] != metadata["name"]:
                    raise ValueError("root mismatch")
            elif source != {"registry": "https://pypi.org/simple"}:
                raise ValueError("only PyPI registry dependencies supported")
            elif not package.get("wheels"):
                raise PreparationError(PreparationFailure.DEPENDENCY_UNAVAILABLE)
        if roots != 1:
            raise ValueError("one local root required")
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise PreparationError(PreparationFailure.UNSUPPORTED_PROJECT) from error
    return ProjectCheckMetadata(requirement, manifest, lock)


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _export(metadata: ProjectCheckMetadata, uv: Path, directory: Path) -> str:
    if not uv.is_absolute() or uv.name.casefold() != "uv.exe":
        raise PreparationError(PreparationFailure.PREPARATION_TOOL_FAILED)
    (directory / "pyproject.toml").write_text(
        metadata.manifest, encoding="utf-8", newline=""
    )
    (directory / "uv.lock").write_text(metadata.lock, encoding="utf-8", newline="")
    code, version, _ = _capture(uv, ["--version"], directory, CheckPolicy(30))
    if code or not version.startswith(b"uv 0.11.19 "):
        raise PreparationError(PreparationFailure.PREPARATION_TOOL_FAILED)
    code, output, _ = _capture(
        uv,
        [
            "export",
            "--locked",
            "--offline",
            "--no-config",
            "--no-sources",
            "--no-build",
            "--no-python-downloads",
            "--no-managed-python",
            "--python",
            sys.executable,
            "--no-cache",
            "--no-emit-project",
            "--no-header",
            "--no-annotate",
            "--format",
            "requirements.txt",
        ],
        directory,
        CheckPolicy(30, 262144),
    )
    if code or (directory / "uv.lock").read_text("utf-8", newline="") != metadata.lock:
        raise PreparationError(PreparationFailure.LOCK_INVALID)
    text = output.decode("utf-8").replace("\r\n", "\n")
    # Defense against requirements-file options, URL/path dependencies or unpinned output.
    for line in text.replace("\\\n", " ").splitlines():
        if line.strip() and not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]*(?:\[[A-Za-z0-9_,.-]+\])?==[A-Za-z0-9_.+!-]+"
            r"(?: ; [A-Za-z0-9_ .<>=!\"'()~-]+)?(?:\s+--hash=sha256:[0-9a-f]{64})+\s*",
            line,
        ):
            raise PreparationError(PreparationFailure.LOCK_INVALID)
    return text


def prepare_check_environment(
    metadata: ProjectCheckMetadata,
    docker: Path,
    uv: Path,
) -> PreparedCheckEnvironment:
    """Explicit acquisition effect. No retries or persistent custom cache.

    uv has a 30-second deadline per call; Docker preparation has 300 seconds;
    cleanup has its own 30 seconds. Control/cleanup errors retain causal chains.
    Successful derived images remain local for this run; no tag is execution authority.
    """
    if type(metadata) is not ProjectCheckMetadata:
        raise TypeError("preparation requires inspected ProjectCheckMetadata")
    config = DockerSandboxConfig(docker, SandboxImage.PYTHON_CHECKS)
    # Test the actual base Python before export/acquisition; no network or project code.
    script = (
        "import sys\nfrom packaging.specifiers import SpecifierSet\n"
        "print('compatible' if sys.version.split()[0] == '3.14.7' and SpecifierSet("
        + repr(metadata.python_requirement)
        + ").contains(sys.version.split()[0]) else 'incompatible')"
    )
    result = DockerSandbox(config).execute(SandboxRequest(script))
    if result.exit_code or result.stdout.strip() != b"compatible":
        raise PreparationError(PreparationFailure.PYTHON_INCOMPATIBLE)
    try:
        with tempfile.TemporaryDirectory(prefix="legoai-check-prepare-") as temporary:
            directory = Path(temporary)
            requirements = _export(metadata, uv, directory)
            return _prepare(
                _Cli(docker, directory), config.image, metadata, requirements
            )
    except CheckError as error:
        raise PreparationError(
            PreparationFailure.PREPARATION_TIMEOUT
            if error.reason is CheckFailure.TIMEOUT
            else PreparationFailure.PREPARATION_TOOL_FAILED
        ) from error
    except OSError as error:
        raise PreparationError(PreparationFailure.PREPARATION_TOOL_FAILED) from error


def _prepare(
    cli: _Cli, base: str, metadata: ProjectCheckMetadata, requirements: str
) -> PreparedCheckEnvironment:
    deadline = time.monotonic() + 300
    _preflight(cli, base, deadline, None)
    name = "legoai-m6-prep-" + uuid.uuid4().hex
    identity = {
        "base": base,
        "lock": _sha(metadata.lock),
        "manifest": _sha(metadata.manifest),
        "profile": "uv-wheels-1",
    }
    payload = (
        json.dumps(
            {
                "python": metadata.python_requirement,
                "requirements": requirements,
                "identity": identity,
            }
        ).encode()
        + b"\n"
    )
    if len(payload) > 524288:
        raise PreparationError(PreparationFailure.UNSUPPORTED_PROJECT)
    uncertain = True
    try:
        _control(
            cli,
            [
                "create",
                "--name",
                name,
                "--pull=never",
                "--network=bridge",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--pids-limit=32",
                "--memory=512m",
                "--memory-swap=512m",
                "--cpus=1",
                "--restart=no",
                "--no-healthcheck",
                "--log-driver=none",
                "--interactive",
                "--tmpfs",
                "/tmp:rw,size=256m,nr_inodes=16384,nosuid,nodev,noexec",
                "--entrypoint=/usr/local/bin/python",
                base,
                "-I",
                "-B",
                "-c",
                _INSTALL,
            ],
            deadline,
        )
        uncertain = False
        code, stdout, _ = cli._run(
            ["start", "--attach", "--interactive", name], deadline, payload=payload
        )
        state = _state(cli, name, deadline, None)
        if state.get("Status") != "exited" or state.get("OOMKilled"):
            raise PreparationError(PreparationFailure.PREPARATION_TOOL_FAILED)
        try:
            status = json.loads(stdout)["status"]
            if code or state.get("ExitCode") != 0 or status != "prepared":
                raise PreparationError(PreparationFailure(status))
        except (ValueError, KeyError, TypeError) as error:
            raise PreparationError(
                PreparationFailure.PREPARATION_TOOL_FAILED
            ) from error
        # No repository Dockerfile/build context; commit only our stopped installer.
        image = _control(cli, ["commit", name], deadline).decode("ascii").strip()
        prepared = _mint(base, identity["lock"], identity["manifest"], image)
        _preflight(cli, prepared.image, deadline, None)
        return prepared
    except SandboxError as error:
        reason = (
            PreparationFailure.PREPARATION_TIMEOUT
            if error.reason is SandboxFailure.TIMEOUT
            else PreparationFailure.PREPARED_IMAGE_UNAVAILABLE
            if error.reason is SandboxFailure.ENVIRONMENT_UNAVAILABLE
            else PreparationFailure.PREPARATION_TOOL_FAILED
        )
        raise PreparationError(reason) from error
    finally:
        _cleanup_preparation(cli, name, uncertain)


def _cleanup_preparation(cli: _Cli, name: str, uncertain: bool) -> None:
    try:
        cleanup = time.monotonic() + 30
        # Reconcile only this generated resource, including uncertain create outcomes.
        present = _control(
            cli,
            [
                "container",
                "ls",
                "--all",
                "--filter",
                f"name=^/{name}$",
                "--format",
                "{{.Names}}",
            ],
            cleanup,
        )
        if present.strip():
            _control(cli, ["container", "rm", "--force", name], cleanup)
        remaining = _control(
            cli,
            [
                "container",
                "ls",
                "--all",
                "--filter",
                f"name=^/{name}$",
                "--format",
                "{{.Names}}",
            ],
            cleanup,
        )
        if remaining.strip() or uncertain:
            raise SandboxError(SandboxFailure.CLEANUP, (name,))
    except SandboxError as error:
        raise SandboxError(SandboxFailure.CLEANUP, (name,)) from error
