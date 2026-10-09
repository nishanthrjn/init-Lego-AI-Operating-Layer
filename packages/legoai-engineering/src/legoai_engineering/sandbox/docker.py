"""Windows Docker Desktop Linux reference adapter; operator configuration only."""

import base64
import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import cast

from legoai_engineering.sandbox._process import _check, _Cli
from legoai_engineering.sandbox._programs import _COLLECT, _IDLE, _PREPARE
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure
from legoai_engineering.sandbox.ports import CancellationSignal
from legoai_engineering.sandbox.prepared import PreparedCheckEnvironment, _digest
from legoai_engineering.sandbox.values import (
    SandboxArtifact,
    SandboxPolicy,
    SandboxRequest,
    SandboxResult,
)


class SandboxImage(Enum):
    """Closed set of operator-qualified images; callers never supply image strings.

    Every image runs under the same fixed M6 resource and confinement profile.
    PYTHON_STDLIB is the original M6 image. PYTHON_CHECKS adds only the pinned M5
    check tools (pytest, Ruff, mypy); it is bound to the exact local image ID that
    passed CR-2a Docker qualification, and is never pulled.
    """

    PYTHON_STDLIB = "python-stdlib"
    PYTHON_CHECKS = "python-checks"


def _approved_image(image: SandboxImage) -> str | None:
    """The exact qualified immutable reference per image, or None if unqualified."""
    if image is SandboxImage.PYTHON_STDLIB:
        return (
            "python@sha256:"
            "82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56"
        )
    # PYTHON_CHECKS: the local image ID built from sandbox-images/python-checks and
    # qualified by validate_consumer_readiness_cr2a.py on 2026-09-29. Any rebuild
    # yields a different ID and must be requalified before replacing this value.
    return "sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df"


def _immutable(reference: str) -> bool:
    """Digest-pinned repository reference or a content-addressed local image ID."""
    digest = reference.removeprefix("python@").removeprefix("sha256:")
    return (
        reference.startswith(("python@sha256:", "sha256:"))
        and len(digest) == 64
        and all(char in "0123456789abcdef" for char in digest)
    )


@dataclass(frozen=True, slots=True)
class DockerSandboxConfig:
    """Inert operator binding; supported environment is deliberately closed.

    The fixed endpoint corresponds to Desktop's local desktop-linux context.
    No context credentials, proxy settings or ambient Docker configuration load.
    The image comes from the closed `SandboxImage` set or trusted preparation's
    immutable PreparedCheckEnvironment. No arbitrary image string is accepted.
    """

    executable: Path
    profile: SandboxImage | PreparedCheckEnvironment = SandboxImage.PYTHON_STDLIB

    def __post_init__(self) -> None:
        if not isinstance(self.executable, Path):
            raise TypeError("Docker executable requires Path")
        if (
            not self.executable.is_absolute()
            or ".." in self.executable.parts
            or str(self.executable).startswith("\\\\")
            or self.executable.name.casefold() != "docker.exe"
        ):
            raise ValueError("explicit native absolute docker.exe path required")
        if type(self.profile) is PreparedCheckEnvironment:
            if (
                self.profile.base_image != _approved_image(SandboxImage.PYTHON_CHECKS)
                or self.profile.profile != "uv-wheels-1"
                or self.profile.python != "3.14.7"
                or not all(
                    _digest(value)
                    for value in (
                        self.profile.image,
                        self.profile.lock_digest,
                        self.profile.manifest_digest,
                    )
                )
            ):
                raise ValueError("unsupported prepared check environment")
            return
        if type(self.profile) is not SandboxImage:
            raise TypeError(
                "sandbox image requires SandboxImage or PreparedCheckEnvironment"
            )
        # Unqualified or mutable references fail closed before any Docker call.
        reference = _approved_image(self.profile)
        if reference is None or not _immutable(reference):
            raise ValueError("unsupported reference environment")

    @property
    def image(self) -> str:
        if isinstance(self.profile, PreparedCheckEnvironment):
            return self.profile.image
        reference = _approved_image(self.profile)
        if reference is None or not _immutable(reference):
            raise ValueError("unsupported reference environment")
        return reference


@dataclass(frozen=True, slots=True)
class DockerSandbox:
    """Bounded blocking call. Construction performs no I/O or runtime discovery."""

    config: DockerSandboxConfig
    policy: SandboxPolicy = SandboxPolicy()

    def __post_init__(self) -> None:
        if type(self.config) is not DockerSandboxConfig:
            raise TypeError("sandbox requires DockerSandboxConfig")
        if type(self.policy) is not SandboxPolicy:
            raise TypeError("sandbox requires SandboxPolicy")

    def verify_ready(self, cancellation: CancellationSignal | None = None) -> None:
        """Startup readiness: the metadata-only preflight every `execute` runs.

        `docker info` (engine reachable, Linux, required resource and seccomp
        controls), `docker image inspect` of the pinned image and, only if that
        fails, `docker version` to tell a disconnect from a missing image. It
        never creates, starts, pulls or builds anything and runs no workload.

        Raises SandboxError: RUNTIME_UNAVAILABLE (CLI missing or engine
        unreachable), ENVIRONMENT_UNAVAILABLE (pinned image absent),
        UNSUPPORTED (controls missing, or not the Windows reference host),
        TIMEOUT or CANCELLED. Success is a point-in-time observation only: a
        later `execute` may still fail, and it repeats this preflight itself.
        """
        deadline = time.monotonic() + min(30.0, float(self.policy.timeout_seconds))
        _check(deadline, cancellation)
        if os.name != "nt":
            raise SandboxError(SandboxFailure.UNSUPPORTED)
        try:
            with tempfile.TemporaryDirectory(prefix="legoai-m6-") as directory:
                cli = _Cli(self.config.executable, Path(directory))
                _preflight(cli, self.config.image, deadline, cancellation)
        except OSError as error:
            # Only the private, input-free CLI config directory can fail here.
            raise SandboxError(SandboxFailure.CLEANUP) from error

    def execute(
        self, request: SandboxRequest, cancellation: CancellationSignal | None = None
    ) -> SandboxResult:
        if type(request) is not SandboxRequest:
            raise TypeError("sandbox requires SandboxRequest")
        deadline = time.monotonic() + self.policy.timeout_seconds
        _check(deadline, cancellation)
        if os.name != "nt":
            raise SandboxError(SandboxFailure.UNSUPPORTED)
        try:
            with tempfile.TemporaryDirectory(prefix="legoai-m6-") as directory:
                cli = _Cli(self.config.executable, Path(directory))
                return self._execute(cli, request, deadline, cancellation)
        except OSError as error:
            # Includes inability to remove the private, input-free CLI config.
            raise SandboxError(SandboxFailure.CLEANUP) from error

    def _execute(
        self,
        cli: _Cli,
        request: SandboxRequest,
        deadline: float,
        cancellation: CancellationSignal | None,
    ) -> SandboxResult:
        _preflight(cli, self.config.image, deadline, cancellation)
        identity = "legoai-m6-" + uuid.uuid4().hex
        volume, worker, collector = identity + "-v", identity + "-w", identity + "-c"
        resources = (volume, worker, collector)
        creation_uncertain = False

        def create(arguments: list[str]) -> None:
            nonlocal creation_uncertain
            # A client timeout/interrupt may leave an in-flight daemon creation.
            creation_uncertain = True
            code, _, stderr = cli._run(arguments, deadline, cancellation=cancellation)
            creation_uncertain = False
            if code or stderr:
                raise SandboxError(SandboxFailure.PREPARATION) from RuntimeError(
                    f"Docker creation exited {code}: {stderr[:4096]!r}"
                )

        try:
            create(
                [
                    "volume",
                    "create",
                    "--driver",
                    "local",
                    "--label",
                    "legoai.m6=true",
                    "--opt",
                    "type=tmpfs",
                    "--opt",
                    "device=tmpfs",
                    "--opt",
                    "o=size=32m,nr_inodes=4096,uid=65534,gid=65534,mode=0700,nosuid,nodev,noexec",
                    volume,
                ]
            )
            create(_container(self.config.image, collector, volume, True, _IDLE))
            _control(cli, ["start", collector], deadline, cancellation)
            create(_container(self.config.image, worker, volume, False, _PREPARE))
            script = base64.b64encode(request.script.encode("utf-8")).decode("ascii")
            files = []
            for item in request.files:
                content = base64.b64encode(item.text.encode("utf-8")).decode("ascii")
                files.append((item.path, content))
            payload = (
                json.dumps(
                    {"script": script, "files": files}, ensure_ascii=False
                ).encode("utf-8")
                + b"\n"
            )
            if len(payload) > 2_000_000:
                raise SandboxError(SandboxFailure.PREPARATION)
            code, stdout, stderr = cli._run(
                ["start", "--attach", "--interactive", worker],
                deadline,
                self.policy.max_output_bytes + 16,
                cancellation,
                payload,
            )
            state = _state(cli, worker, deadline, cancellation)
            if state.get("OOMKilled") is True:
                raise SandboxError(SandboxFailure.RESOURCE_LIMIT)
            prefix = b"LEGOAI_M6_READY\n"
            if not stdout.startswith(prefix):
                raise SandboxError(SandboxFailure.PREPARATION)
            stdout = stdout[len(prefix) :]
            if max(len(stdout), len(stderr)) > self.policy.max_output_bytes:
                raise SandboxError(SandboxFailure.OUTPUT_LIMIT)
            exit_code = state.get("ExitCode")
            if (
                state.get("Status") != "exited"
                or state.get("Running") is not False
                or state.get("Dead") is not False
                or state.get("Error") != ""
                or type(exit_code) is not int
                or not 0 <= exit_code <= 255
                or code not in (0, exit_code)
            ):
                raise SandboxError(SandboxFailure.CONTROL)
            # PID 1 exited: Docker's PID namespace teardown precedes collection.
            artifacts = self._collect(cli, collector, request, deadline, cancellation)
            return SandboxResult(exit_code, stdout, stderr, artifacts)
        finally:
            try:
                _cleanup(cli, resources)
            except BaseException as error:
                raise SandboxError(SandboxFailure.CLEANUP, resources) from error
            if creation_uncertain:
                # Absence now cannot disprove delayed daemon completion.
                raise SandboxError(SandboxFailure.CLEANUP, resources)

    def _collect(
        self,
        cli: _Cli,
        collector: str,
        request: SandboxRequest,
        deadline: float,
        cancellation: CancellationSignal | None,
    ) -> tuple[SandboxArtifact, ...]:
        if not request.artifacts:
            return ()
        selection = json.dumps(
            [
                [path.value for path in request.artifacts],
                self.policy.max_artifact_bytes,
                self.policy.max_total_artifact_bytes,
            ],
            ensure_ascii=False,
        )
        # Base64 expansion plus bounded path/JSON framing. No archive extraction.
        limit = self.policy.max_total_artifact_bytes * 2 + 65_536
        code, output, stderr = cli._run(
            [
                "exec",
                collector,
                "/usr/bin/env",
                "-i",
                "LANG=C.UTF-8",
                "/usr/local/bin/python",
                "-I",
                "-B",
                "-c",
                _COLLECT,
                selection,
            ],
            deadline,
            limit,
            cancellation,
        )
        if code or stderr:
            raise SandboxError(SandboxFailure.ARTIFACT)
        return _artifacts(output, request, self.policy)


def _container(
    image: str, name: str, volume: str, readonly: bool, program: str
) -> list[str]:
    mount = f"type=volume,src={volume},dst=/work,volume-nocopy"
    if readonly:
        mount += ",readonly"
    return [
        "create",
        "--pull=never",
        "--platform=linux/amd64",
        "--name",
        name,
        "--label",
        "legoai.m6=true",
        "--network=none",
        "--user=65534:65534",
        "--cap-drop=ALL",
        "--cgroupns=private",
        "--ipc=private",
        "--security-opt=no-new-privileges=true",
        "--read-only",
        "--cpus=1",
        "--memory=128m",
        "--memory-swap=128m",
        "--pids-limit=32",
        "--shm-size=8m",
        "--ulimit=nofile=128:128",
        "--ulimit=core=0:0",
        "--tmpfs",
        "/tmp:rw,size=8m,nr_inodes=1024,uid=65534,gid=65534,mode=0700,nosuid,nodev,noexec",
        "--mount",
        mount,
        "--workdir=/work",
        "--restart=no",
        "--no-healthcheck",
        "--log-driver=none",
        "--interactive",
        "--entrypoint=/usr/bin/env",
        image,
        "-i",
        "PATH=/usr/local/bin:/usr/bin:/bin",
        "LANG=C.UTF-8",
        "HOME=/nonexistent",
        "TMPDIR=/tmp",
        "/usr/local/bin/python",
        "-I",
        "-B",
        "-c",
        program,
    ]


def _json(data: bytes) -> object:
    try:
        value: object = json.loads(data)
        return value
    except (ValueError, RecursionError) as error:
        raise SandboxError(SandboxFailure.CONTROL) from error


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(type(key) is not str for key in value):
        raise SandboxError(SandboxFailure.CONTROL)
    return cast(dict[str, object], value)


def _control(
    cli: _Cli,
    arguments: list[str],
    deadline: float,
    cancellation: CancellationSignal | None = None,
) -> bytes:
    code, output, stderr = cli._run(arguments, deadline, cancellation=cancellation)
    if code or stderr:
        raise SandboxError(SandboxFailure.CONTROL) from RuntimeError(
            f"Docker control exited {code}: {stderr[:4096]!r}"
        )
    return output


def _state(
    cli: _Cli, name: str, deadline: float, cancellation: CancellationSignal | None
) -> dict[str, object]:
    return _mapping(
        _json(
            _control(
                cli,
                ["container", "inspect", "--format", "{{json .State}}", name],
                deadline,
                cancellation,
            )
        )
    )


def _preflight(
    cli: _Cli, image: str, deadline: float, cancellation: CancellationSignal | None
) -> None:
    code, output, stderr = cli._run(
        ["info", "--format", "{{json .}}"], deadline, cancellation=cancellation
    )
    if code:
        raise SandboxError(SandboxFailure.RUNTIME_UNAVAILABLE) from RuntimeError(
            f"Docker information query exited {code}: {stderr[:4096]!r}"
        )
    info = _mapping(_json(output))
    options = info.get("SecurityOptions")
    if (
        info.get("OSType") != "linux"
        or info.get("Architecture") not in ("x86_64", "amd64")
        or info.get("CgroupVersion") != "2"
        or any(
            info.get(control) is not True
            for control in (
                "MemoryLimit",
                "SwapLimit",
                "CpuCfsPeriod",
                "CpuCfsQuota",
                "PidsLimit",
            )
        )
        or not isinstance(options, list)
        or not any(isinstance(item, str) and "name=seccomp" in item for item in options)
    ):
        raise SandboxError(SandboxFailure.UNSUPPORTED)
    code, output, stderr = cli._run(
        ["image", "inspect", "--format", "{{json .}}", image],
        deadline,
        cancellation=cancellation,
    )
    if code:
        # Reconfirm daemon availability; a disconnect is not missing-image proof.
        _control(
            cli, ["version", "--format", "{{.Server.Version}}"], deadline, cancellation
        )
        raise SandboxError(SandboxFailure.ENVIRONMENT_UNAVAILABLE) from RuntimeError(
            f"Docker image query exited {code}: {stderr[:4096]!r}"
        )
    description = _mapping(_json(output))
    config = _mapping(description.get("Config"))
    if (
        description.get("Os") != "linux"
        or description.get("Architecture") != "amd64"
        or config.get("Volumes") not in (None, {})
    ):
        raise SandboxError(SandboxFailure.UNSUPPORTED)


def _artifacts(
    data: bytes, request: SandboxRequest, policy: SandboxPolicy
) -> tuple[SandboxArtifact, ...]:
    value = _json(data)
    if not isinstance(value, list) or len(value) != len(request.artifacts):
        raise SandboxError(SandboxFailure.ARTIFACT)
    artifacts: list[SandboxArtifact] = []
    total = 0
    for item, path in zip(value, request.artifacts, strict=True):
        if (
            not isinstance(item, list)
            or len(item) != 2
            or item[0] != path.value
            or type(item[1]) is not str
        ):
            raise SandboxError(SandboxFailure.ARTIFACT)
        try:
            content = base64.b64decode(item[1], validate=True)
        except ValueError as error:
            raise SandboxError(SandboxFailure.ARTIFACT) from error
        total += len(content)
        if (
            len(content) > policy.max_artifact_bytes
            or total > policy.max_total_artifact_bytes
        ):
            raise SandboxError(SandboxFailure.ARTIFACT)
        artifacts.append(SandboxArtifact(path, content))
    return tuple(artifacts)


def _cleanup(cli: _Cli, resources: tuple[str, str, str]) -> None:
    """Finite reconciliation, no broad prune and no missing/error conflation."""
    deadline = time.monotonic() + 60
    volume, worker, collector = resources
    failures: list[Exception] = []
    # Attempt all owned resources even if one operation fails. Never broad prune.
    for kind, name in (
        ("container", worker),
        ("container", collector),
        ("volume", volume),
    ):
        listing = [kind, "ls"]
        removal = [kind, "rm"]
        if kind == "container":
            listing += [
                "--all",
                "--filter",
                f"name=^/{name}$",
                "--format",
                "{{.Names}}",
            ]
            removal += ["--force"]
        else:
            listing += ["--filter", f"name=^{name}$", "--format", "{{.Name}}"]
        try:
            present = _control(cli, listing, deadline).decode("ascii").splitlines()
            if present:
                if present != [name]:
                    raise SandboxError(SandboxFailure.CLEANUP)
                _control(cli, [*removal, name], deadline)
            if _control(cli, listing, deadline).strip():
                raise SandboxError(SandboxFailure.CLEANUP)
        except (SandboxError, OSError, UnicodeError) as error:
            failures.append(error)
    if failures:
        raise SandboxError(SandboxFailure.CLEANUP, resources) from failures[0]
