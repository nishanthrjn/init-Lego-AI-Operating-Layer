"""DockerSandbox.verify_ready: offline behavior with a simulated Docker CLI.

The real Docker Desktop readiness path is in test_sandbox_docker.py.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from legoai_engineering.sandbox._process import _Cli
from legoai_engineering.sandbox.docker import (
    DockerSandbox,
    DockerSandboxConfig,
    SandboxImage,
)
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure

pytestmark = pytest.mark.skipif(
    os.name != "nt", reason="Windows Desktop reference scope"
)
INFO = json.dumps(
    {
        "OSType": "linux",
        "Architecture": "x86_64",
        "CgroupVersion": "2",
        "MemoryLimit": True,
        "SwapLimit": True,
        "CpuCfsPeriod": True,
        "CpuCfsQuota": True,
        "PidsLimit": True,
        "SecurityOptions": ["name=seccomp,profile=builtin"],
    }
).encode()
IMAGE = json.dumps({"Os": "linux", "Architecture": "amd64", "Config": {}}).encode()
METADATA = {"info", "image", "version"}


def sandbox(tmp_path: Path) -> DockerSandbox:
    return DockerSandbox(
        DockerSandboxConfig(tmp_path / "docker.exe", SandboxImage.PYTHON_CHECKS)
    )


class FakeCli:
    """Scripted (code, stdout, stderr) per call; records every command."""

    def __init__(self, *replies: tuple[int, bytes, bytes]) -> None:
        self.replies = list(replies)
        self.commands: list[list[str]] = []

    def __call__(self, arguments: list[str], *args: object, **kwargs: object) -> object:
        self.commands.append(arguments)
        return self.replies.pop(0)


def ready(tmp_path: Path, cli: FakeCli) -> SandboxFailure | None:
    with patch.object(_Cli, "_run", side_effect=cli):
        try:
            sandbox(tmp_path).verify_ready()
        except SandboxError as error:
            return error.reason
    return None


def test_ready_environment_passes_with_metadata_only(tmp_path: Path) -> None:
    cli = FakeCli((0, INFO, b""), (0, IMAGE, b""))
    assert ready(tmp_path, cli) is None
    assert [c[0] for c in cli.commands] == ["info", "image"]
    assert cli.commands[1][:2] == ["image", "inspect"]
    assert cli.commands[1][-1] == sandbox(tmp_path).config.image


def test_missing_docker_cli_is_runtime_unavailable(tmp_path: Path) -> None:
    with pytest.raises(SandboxError) as caught:
        sandbox(tmp_path / "missing").verify_ready()
    assert caught.value.reason is SandboxFailure.RUNTIME_UNAVAILABLE


def test_unreachable_engine_is_runtime_unavailable(tmp_path: Path) -> None:
    # The adapter always targets the Desktop Linux engine pipe; an unusable
    # context and a stopped daemon both surface as a failed `docker info`.
    cli = FakeCli((1, b"", b"error during connect: open //./pipe/..."))
    assert ready(tmp_path, cli) is SandboxFailure.RUNTIME_UNAVAILABLE
    assert [c[0] for c in cli.commands] == ["info"]


def test_missing_checks_image_is_environment_unavailable(tmp_path: Path) -> None:
    cli = FakeCli(
        (0, INFO, b""),
        (1, b"", b"Error: No such image"),
        (0, b"29.0.0\n", b""),  # the engine is still reachable
    )
    assert ready(tmp_path, cli) is SandboxFailure.ENVIRONMENT_UNAVAILABLE


def test_engine_lost_during_image_check_is_not_missing_image(tmp_path: Path) -> None:
    cli = FakeCli((0, INFO, b""), (1, b"", b"disconnected"), (1, b"", b"disconnected"))
    assert ready(tmp_path, cli) is SandboxFailure.CONTROL


def test_missing_controls_are_unsupported(tmp_path: Path) -> None:
    info = json.loads(INFO)
    info["CgroupVersion"] = "1"
    cli = FakeCli((0, json.dumps(info).encode(), b""))
    assert ready(tmp_path, cli) is SandboxFailure.UNSUPPORTED


@pytest.mark.parametrize(
    "replies",
    [
        ((0, INFO, b""), (0, IMAGE, b"")),
        ((1, b"", b"down"),),
        ((0, INFO, b""), (1, b"", b"missing"), (0, b"29\n", b"")),
    ],
)
def test_never_starts_pulls_builds_or_runs(
    tmp_path: Path, replies: tuple[tuple[int, bytes, bytes], ...]
) -> None:
    cli = FakeCli(*replies)
    ready(tmp_path, cli)
    assert {c[0] for c in cli.commands} <= METADATA
    flat = {word for command in cli.commands for word in command}
    assert not flat & {"pull", "build", "run", "create", "start", "load", "desktop"}


def test_cancelled_before_start_contacts_nothing(tmp_path: Path) -> None:
    class Cancelled:
        def is_set(self) -> bool:
            return True

    cli = FakeCli()
    with patch.object(_Cli, "_run", side_effect=cli):
        with pytest.raises(SandboxError) as caught:
            sandbox(tmp_path).verify_ready(Cancelled())
    assert caught.value.reason is SandboxFailure.CANCELLED and not cli.commands
