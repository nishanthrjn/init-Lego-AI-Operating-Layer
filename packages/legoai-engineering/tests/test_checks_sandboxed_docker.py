"""CR-2b real Docker tests: SandboxedEngineeringChecks on the qualified image.

Uses the recorded PYTHON_CHECKS image ID from CR-2a; nothing is built or pulled.
Never mocked away: missing Docker or image fails rather than skips.
"""

import os
import shutil
import sys
import time
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from threading import Event, Timer

import pytest
from governed_demo import NOW, WORKSPACE, create_governed_demo
from python_checks_project import project_files

from legoai_engineering.authorization import (
    EffectAuthorizationError,
    EffectAuthorizationFailure,
)
from legoai_engineering.checks.authorized import (
    ENGINEERING_CHECK_ACTION,
    AuthorizedEngineeringChecks,
)
from legoai_engineering.checks.errors import CheckError, CheckFailure
from legoai_engineering.checks.local import LocalCheckTools, LocalEngineeringChecks
from legoai_engineering.checks.ports import EngineeringCheckPort
from legoai_engineering.checks.sandboxed import (
    CheckInputPolicy,
    SandboxedEngineeringChecks,
)
from legoai_engineering.checks.values import (
    CheckKind,
    CheckOutcome,
    CheckPolicy,
    CheckRequest,
)
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy
from legoai_engineering.sandbox._process import _Cli
from legoai_engineering.sandbox.docker import (
    DockerSandbox,
    DockerSandboxConfig,
    SandboxImage,
    _preflight,
)
from legoai_engineering.sandbox.ports import CancellationSignal
from legoai_engineering.sandbox.values import (
    SandboxPolicy,
    SandboxRequest,
    SandboxResult,
)

pytestmark = pytest.mark.skipif(
    os.name != "nt", reason="Windows Desktop reference scope"
)

INPUTS = CheckInputPolicy(
    (RepositoryPath("src"), RepositoryPath("tests")),
    (RepositoryPath("pyproject.toml"),),
)


def inventory(cli: _Cli) -> tuple[bytes, ...]:
    outputs = []
    for kind, extra, field in (
        ("container", ["--all"], "{{.Names}}"),
        ("volume", [], "{{.Name}}"),
    ):
        code, output, error = cli._run(
            [kind, "ls", *extra, "--filter", "label=legoai.m6=true", "--format", field],
            time.monotonic() + 15,
        )
        assert code == 0, error
        outputs.append(b"\n".join(sorted(output.splitlines())))
    return tuple(outputs)


@pytest.fixture
def docker(tmp_path: Path) -> Iterator[Path]:
    executable = shutil.which("docker")
    assert executable is not None, "CR-2b Docker tests require Docker; no skip"
    config = DockerSandboxConfig(Path(executable), SandboxImage.PYTHON_CHECKS)
    cli = _Cli(config.executable, tmp_path)
    _preflight(cli, config.image, time.monotonic() + 30, None)
    before = inventory(cli)
    try:
        yield Path(executable)
    finally:
        assert inventory(cli) == before, "sandbox resources remain after execution"


def project(tmp_path: Path, variant: str | None = None) -> Path:
    root = tmp_path / "project"
    for item in project_files(variant):
        path = root / item.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item.text, encoding="utf-8", newline="\n")
    return root


def sandboxed(
    docker: Path,
    root: Path,
    *,
    policy: CheckPolicy | None = None,
    image: SandboxImage = SandboxImage.PYTHON_CHECKS,
    cancellation: Event | None = None,
) -> SandboxedEngineeringChecks:
    workspace = LocalRepositoryWorkspace(
        LocalWorkspaceRoot(root),
        WorkspacePolicy(262_144, 65_536, 4096, 32, (".git", ".venv")),
    )
    sandbox = DockerSandbox(
        DockerSandboxConfig(docker, image),
        SandboxPolicy(timeout_seconds=180, max_output_bytes=1_048_576),
    )
    return SandboxedEngineeringChecks(
        workspace,
        sandbox,
        INPUTS,
        policy or CheckPolicy(timeout_seconds=120),
        cancellation,
    )


def request(kind: CheckKind, *targets: str) -> CheckRequest:
    return CheckRequest(kind, tuple(RepositoryPath(t) for t in targets))


@pytest.mark.parametrize(
    ("kind", "targets", "variant", "outcome"),
    [
        (CheckKind.PYTEST, ["tests"], None, CheckOutcome.PASSED),
        (CheckKind.PYTEST, ["tests"], "failing-test", CheckOutcome.FAILED),
        (CheckKind.PYTEST, ["tests"], "collection-error", CheckOutcome.INTERRUPTED),
        (CheckKind.PYTEST, ["src"], None, CheckOutcome.NO_TESTS),
        (CheckKind.RUFF_CHECK, ["src", "tests"], None, CheckOutcome.PASSED),
        (CheckKind.RUFF_CHECK, ["src", "tests"], "lint-finding", CheckOutcome.FAILED),
        (CheckKind.RUFF_FORMAT_CHECK, ["src", "tests"], None, CheckOutcome.PASSED),
        (
            CheckKind.RUFF_FORMAT_CHECK,
            ["src", "tests"],
            "unformatted",
            CheckOutcome.FAILED,
        ),
        (CheckKind.MYPY, ["src"], None, CheckOutcome.PASSED),
        (CheckKind.MYPY, ["src"], "type-error", CheckOutcome.FAILED),
    ],
    ids=[
        "pytest-pass",
        "pytest-fail",
        "pytest-collection-error",
        "pytest-no-tests",
        "ruff-clean",
        "ruff-finding",
        "ruff-format-clean",
        "ruff-format-finding",
        "mypy-clean",
        "mypy-finding",
    ],
)
def test_check_outcomes(
    docker: Path,
    tmp_path: Path,
    kind: CheckKind,
    targets: list[str],
    variant: str | None,
    outcome: CheckOutcome,
) -> None:
    result = sandboxed(docker, project(tmp_path, variant)).check(
        request(kind, *targets)
    )
    assert result.kind is kind
    assert result.outcome is outcome, (result.stdout[-2000:], result.stderr[-2000:])


def test_network_remains_unavailable_to_tests(docker: Path, tmp_path: Path) -> None:
    checks = sandboxed(docker, project(tmp_path, "network-test"))
    result = checks.check(request(CheckKind.PYTEST, "tests/test_network.py"))
    assert result.outcome is CheckOutcome.PASSED, result.stdout[-2000:]


def test_check_timeout(docker: Path, tmp_path: Path) -> None:
    checks = sandboxed(
        docker, project(tmp_path, "slow-test"), policy=CheckPolicy(timeout_seconds=10)
    )
    with pytest.raises(CheckError) as caught:
        checks.check(request(CheckKind.PYTEST, "tests/test_slow.py"))
    assert caught.value.reason is CheckFailure.TIMEOUT


def test_output_limit(docker: Path, tmp_path: Path) -> None:
    checks = sandboxed(
        docker,
        project(tmp_path, "noisy-test"),
        policy=CheckPolicy(timeout_seconds=120, max_output_bytes=16_384),
    )
    with pytest.raises(CheckError) as caught:
        checks.check(request(CheckKind.PYTEST, "tests/test_noisy.py"))
    assert caught.value.reason is CheckFailure.OUTPUT_LIMIT


def test_memory_limit_is_resource_limit(docker: Path, tmp_path: Path) -> None:
    checks = sandboxed(docker, project(tmp_path, "memory-test"))
    with pytest.raises(CheckError) as caught:
        checks.check(request(CheckKind.PYTEST, "tests/test_memory.py"))
    assert caught.value.reason is CheckFailure.RESOURCE_LIMIT


def test_cancellation_before_and_during_execution(docker: Path, tmp_path: Path) -> None:
    root = project(tmp_path, "slow-test")
    signal = Event()
    signal.set()
    with pytest.raises(CheckError) as caught:
        sandboxed(docker, root, cancellation=signal).check(
            request(CheckKind.PYTEST, "tests/test_slow.py")
        )
    assert caught.value.reason is CheckFailure.CANCELLED
    signal = Event()
    timer = Timer(8, signal.set)
    timer.start()
    try:
        with pytest.raises(CheckError) as caught:
            sandboxed(docker, root, cancellation=signal).check(
                request(CheckKind.PYTEST, "tests/test_slow.py")
            )
    finally:
        timer.cancel()
    assert caught.value.reason is CheckFailure.CANCELLED


def test_unqualified_toolchain_is_unavailable(docker: Path, tmp_path: Path) -> None:
    # The stdlib M6 image lacks the qualified tools; no host fallback occurs.
    checks = sandboxed(docker, project(tmp_path), image=SandboxImage.PYTHON_STDLIB)
    with pytest.raises(CheckError) as caught:
        checks.check(request(CheckKind.PYTEST, "tests"))
    assert caught.value.reason is CheckFailure.UNAVAILABLE


def outcomes(
    port: EngineeringCheckPort, requests: list[CheckRequest]
) -> list[CheckOutcome]:
    """Application code: depends on EngineeringCheckPort only."""
    return [port.check(item).outcome for item in requests]


def test_same_consumer_with_host_and_sandboxed_adapters(
    docker: Path, tmp_path: Path
) -> None:
    root = project(tmp_path)
    requests = [
        request(CheckKind.PYTEST, "tests"),
        request(CheckKind.RUFF_CHECK, "src", "tests"),
        request(CheckKind.RUFF_FORMAT_CHECK, "src", "tests"),
        request(CheckKind.MYPY, "src"),
    ]
    base = Path(sys.executable).parent
    suffix = ".exe" if os.name == "nt" else ""
    host = LocalEngineeringChecks(
        LocalWorkspaceRoot(root),
        LocalCheckTools(
            *(base / (name + suffix) for name in ("pytest", "ruff", "mypy"))
        ),
        CheckPolicy(timeout_seconds=120),
    )
    expected = [CheckOutcome.PASSED] * 4
    assert outcomes(host, requests) == expected
    assert outcomes(sandboxed(docker, root), requests) == expected


class CountingDockerSandbox:
    def __init__(self, inner: DockerSandbox) -> None:
        self.inner = inner
        self.calls = 0

    def execute(
        self, request: SandboxRequest, cancellation: CancellationSignal | None = None
    ) -> SandboxResult:
        self.calls += 1
        return self.inner.execute(request, cancellation)


@pytest.mark.parametrize("allowed", [True, False], ids=["allowed", "denied"])
def test_authorized_sandboxed_check(
    docker: Path, tmp_path: Path, allowed: bool
) -> None:
    # CR-3: current authority is evaluated before the real sandbox; a denial
    # starts no container (the fixture also checks no resources remain).
    root = project(tmp_path)
    sandbox = CountingDockerSandbox(
        DockerSandbox(
            DockerSandboxConfig(docker, SandboxImage.PYTHON_CHECKS),
            SandboxPolicy(timeout_seconds=180, max_output_bytes=1_048_576),
        )
    )
    inner = SandboxedEngineeringChecks(
        LocalRepositoryWorkspace(
            LocalWorkspaceRoot(root),
            WorkspacePolicy(262_144, 65_536, 4096, 32, (".git", ".venv")),
        ),
        sandbox,
        INPUTS,
        CheckPolicy(timeout_seconds=120),
    )
    demo = create_governed_demo("{}", check_allowed=allowed)
    reference = replace(demo.configuration, instance=WORKSPACE)
    checks = AuthorizedEngineeringChecks(
        reference,
        inner,
        demo.host.security_context(reference, ENGINEERING_CHECK_ACTION, WORKSPACE),
        demo.host.authorization,
        lambda: NOW,
    )
    if allowed:
        result = checks.check(request(CheckKind.PYTEST, "tests"))
        assert result.outcome is CheckOutcome.PASSED
        assert sandbox.calls == 1
    else:
        with pytest.raises(EffectAuthorizationError) as caught:
            checks.check(request(CheckKind.PYTEST, "tests"))
        assert caught.value.reason is EffectAuthorizationFailure.DENIED
        assert sandbox.calls == 0
