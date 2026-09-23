"""Contract, protocol and failure-path tests; real isolation is tested separately."""

import ast
import json
import time
from pathlib import Path
from threading import Event
from unittest.mock import patch

import pytest

from legoai_engineering.repository.errors import WorkspaceBoundaryError
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.sandbox._process import _Cli, _check
from legoai_engineering.sandbox.docker import (
    DockerSandbox,
    DockerSandboxConfig,
    _artifacts,
    _cleanup,
    _container,
)
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure
from legoai_engineering.sandbox.ports import CancellationSignal, SandboxExecutionPort
from legoai_engineering.sandbox.values import (
    SandboxArtifact,
    SandboxPolicy,
    SandboxRequest,
    SandboxResult,
)


@pytest.mark.parametrize("path", ["../a", "/a", "C:/a", "a\\b", "a/../b"])
def test_traversal_rejected_without_dispatch(path: str) -> None:
    with pytest.raises((ValueError, WorkspaceBoundaryError)):
        SandboxRequest("pass", artifacts=(RepositoryPath(path),))


@pytest.mark.parametrize(
    "path",
    [
        ".git/config",
        ".VENV/a",
        ".ssh/key",
        ".env",
        ".docker/config.json",
        ".kube/config",
        ".netrc",
        "id_ed25519",
        "__legoai__.py",
    ],
)
def test_administrative_and_secret_paths_excluded(path: str) -> None:
    with pytest.raises(ValueError):
        SandboxRequest("pass", (RepositoryText(path, "x"),))
    with pytest.raises(ValueError):
        SandboxRequest("pass", artifacts=(RepositoryPath(path),))


@pytest.mark.parametrize("names", [("a", "A"), ("a", "a/b"), ("a/b", "A")])
def test_aliases_and_ancestor_overlap_rejected(names: tuple[str, str]) -> None:
    with pytest.raises(ValueError):
        SandboxRequest("pass", tuple(RepositoryText(name, "x") for name in names))


def test_contract_bounds_and_private_representations() -> None:
    for script in ("", "x" * 65_537, "\ud800", "x\0y"):
        with pytest.raises(ValueError):
            SandboxRequest(script)
    with pytest.raises(ValueError):
        SandboxRequest("pass", tuple(RepositoryText(str(i), "x") for i in range(65)))
    with pytest.raises(ValueError):
        SandboxRequest(
            "pass", artifacts=tuple(RepositoryPath(str(i)) for i in range(17))
        )
    with pytest.raises(ValueError):
        SandboxRequest(
            "pass", tuple(RepositoryText(str(i), "x" * 65_536) for i in range(17))
        )
    with pytest.raises(TypeError):
        SandboxPolicy(timeout_seconds=True)
    with pytest.raises(ValueError):
        SandboxPolicy(max_total_artifact_bytes=1)
    request = SandboxRequest(
        "private-script", (RepositoryText("data", "private-input"),)
    )
    result = SandboxResult(
        0,
        b"private-output",
        b"private-error",
        (SandboxArtifact(RepositoryPath("result"), b"private-artifact"),),
    )
    assert "private" not in repr(request) + repr(result)


@pytest.mark.parametrize(
    "value",
    [None, [], [["wrong", "eA=="]], [["a", "***"]], [["a", "eHg="]]],
)
def test_collector_protocol_is_untrusted(value: object) -> None:
    request = SandboxRequest("pass", artifacts=(RepositoryPath("a"),))
    with pytest.raises(SandboxError) as caught:
        _artifacts(
            json.dumps(value).encode(), request, SandboxPolicy(max_artifact_bytes=1)
        )
    assert caught.value.reason is SandboxFailure.ARTIFACT


def test_fixed_runtime_profile_has_no_escape_hatch() -> None:
    for readonly in (False, True):
        arguments = _container("pinned", "generated", "generated-v", readonly, "fixed")
        for required in (
            "--pull=never",
            "--network=none",
            "--user=65534:65534",
            "--cap-drop=ALL",
            "--read-only",
            "--security-opt=no-new-privileges=true",
            "--cpus=1",
            "--memory=128m",
            "--memory-swap=128m",
            "--pids-limit=32",
        ):
            assert required in arguments
        for forbidden in (
            "--privileged", "--cap-add", "--pid", "--publish", "--volume"
        ):
            assert not any(
                argument == forbidden or argument.startswith(forbidden + "=")
                for argument in arguments
            )
        assert "type=bind" not in " ".join(arguments)
        assert "docker.sock" not in " ".join(arguments)
        mount = arguments[arguments.index("--mount") + 1]
        assert mount.endswith(",readonly") is readonly
    root = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "legoai_engineering"
        / "sandbox"
    )
    for name in ("values", "ports", "errors"):
        tree = ast.parse((root / (name + ".py")).read_text("utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(
                    item.name not in {"os", "subprocess", "docker"}
                    for item in node.names
                )
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").endswith((".docker", "._process"))


def test_cancellation_and_deadline_have_distinct_failures() -> None:
    cancelled = Event()
    cancelled.set()
    with pytest.raises(SandboxError) as caught:
        _check(time.monotonic() + 10, cancelled)
    assert caught.value.reason is SandboxFailure.CANCELLED
    with pytest.raises(SandboxError) as caught:
        _check(time.monotonic() - 1, None)
    assert caught.value.reason is SandboxFailure.TIMEOUT


def test_port_consumer_does_not_require_backend_types() -> None:
    class SuppliedResultSandbox:
        def execute(
            self,
            request: SandboxRequest,
            cancellation: CancellationSignal | None = None,
        ) -> SandboxResult:
            return SandboxResult(0, b"supplied", b"")

    port: SandboxExecutionPort = SuppliedResultSandbox()
    assert port.execute(SandboxRequest("pass")).stdout == b"supplied"


def test_pre_cancelled_call_does_not_start_runtime(tmp_path: Path) -> None:
    signal = Event()
    signal.set()
    sandbox = DockerSandbox(DockerSandboxConfig(tmp_path / "docker.exe"))
    with patch.object(_Cli, "_run") as run:
        with pytest.raises(SandboxError) as caught:
            sandbox.execute(SandboxRequest("pass"), signal)
        assert caught.value.reason is SandboxFailure.CANCELLED
        run.assert_not_called()


def test_cleanup_does_not_interpret_daemon_loss_as_absence(tmp_path: Path) -> None:
    cli = _Cli(tmp_path / "docker.exe", tmp_path)
    with patch.object(_Cli, "_run", return_value=(1, b"", b"daemon unavailable")):
        with pytest.raises(SandboxError):
            _cleanup(cli, ("legoai-m6-v", "legoai-m6-w", "legoai-m6-c"))


def test_cleanup_failure_overrides_and_preserves_original_cause(tmp_path: Path) -> None:
    sandbox = DockerSandbox(DockerSandboxConfig(tmp_path / "docker.exe"))
    original = SandboxError(SandboxFailure.TIMEOUT)
    cleanup = SandboxError(SandboxFailure.CONTROL)
    with (
        patch("legoai_engineering.sandbox.docker._preflight"),
        patch.object(_Cli, "_run", side_effect=original),
        patch("legoai_engineering.sandbox.docker._cleanup", side_effect=cleanup),
        pytest.raises(SandboxError) as caught,
    ):
        sandbox._execute(
            _Cli(sandbox.config.executable, tmp_path),
            SandboxRequest("pass"),
            time.monotonic() + 10,
            None,
        )
    assert caught.value.reason is SandboxFailure.CLEANUP
    assert len(caught.value.recovery_ids) == 3
    assert caught.value.__cause__ is cleanup
    assert cleanup.__context__ is original


def test_lost_creation_acknowledgment_remains_uncertain(tmp_path: Path) -> None:
    sandbox = DockerSandbox(DockerSandboxConfig(tmp_path / "docker.exe"))
    with (
        patch("legoai_engineering.sandbox.docker._preflight"),
        patch.object(_Cli, "_run", side_effect=SandboxError(SandboxFailure.TIMEOUT)),
        patch("legoai_engineering.sandbox.docker._cleanup"),
        pytest.raises(SandboxError) as caught,
    ):
        sandbox._execute(
            _Cli(sandbox.config.executable, tmp_path),
            SandboxRequest("pass"),
            time.monotonic() + 10,
            None,
        )
    assert caught.value.reason is SandboxFailure.CLEANUP
    assert isinstance(caught.value.__context__, SandboxError)
