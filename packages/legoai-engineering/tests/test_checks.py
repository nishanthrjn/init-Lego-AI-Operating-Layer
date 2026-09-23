"""M5 semantic, containment, process-budget and real-tool qualification."""

import os
import shutil
import subprocess
import sys
import time
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from legoai_engineering.checks._process import _capture, _environment
from legoai_engineering.checks.errors import CheckError, CheckFailure
from legoai_engineering.checks.local import LocalCheckTools, LocalEngineeringChecks
from legoai_engineering.checks.ports import EngineeringCheckPort
from legoai_engineering.checks.values import (
    CheckKind,
    CheckOutcome,
    CheckPolicy,
    CheckRequest,
    CheckResult,
)
from legoai_engineering.git.local import (
    GitReadPolicy,
    LocalGitExecutable,
    LocalGitRepository,
)
from legoai_engineering.repository.errors import (
    WorkspaceBoundaryError,
    WorkspaceError,
    WorkspaceFailure,
)
from legoai_engineering.repository.local import LocalWorkspaceRoot
from legoai_engineering.repository.mutation import (
    FileChange,
    FileChangeKind,
    RepositoryChangeSet,
    digest_text,
)
from legoai_engineering.repository.mutation_local import LocalRepositoryMutation
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy


def tools_at(base: Path) -> LocalCheckTools:
    suffix = ".exe" if os.name == "nt" else ""
    return LocalCheckTools(
        base / ("pytest" + suffix),
        base / ("ruff" + suffix),
        base / ("mypy" + suffix),
    )


@pytest.fixture
def tools() -> LocalCheckTools:
    configured = tools_at(Path(sys.executable).parent)
    for executable in (configured.pytest, configured.ruff, configured.mypy):
        assert executable.is_file(), "M5 requires local dev tools; run uv sync --locked"
    return configured


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "trusted project café"
    root.mkdir()
    # Explicit fixture configuration prevents ancestor/user config drift.
    (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (root / "ruff.toml").write_text('lint.select = ["F"]\n', encoding="utf-8")
    (root / "mypy.ini").write_text("[mypy]\n", encoding="utf-8")
    return root


def runner(
    root: Path, tools: LocalCheckTools, policy: CheckPolicy | None = None
) -> EngineeringCheckPort:
    return LocalEngineeringChecks(
        LocalWorkspaceRoot(root), tools, policy if policy is not None else CheckPolicy()
    )


def request(kind: CheckKind, *paths: str) -> CheckRequest:
    return CheckRequest(kind, tuple(RepositoryPath(path) for path in paths))


@pytest.mark.parametrize(
    ("content", "code", "outcome"),
    [
        ("def test_ok():\n    assert True\n", 0, CheckOutcome.PASSED),
        ("def test_bad():\n    assert False\n", 1, CheckOutcome.FAILED),
        ("value = 1\n", 5, CheckOutcome.NO_TESTS),
        ("def invalid(:\n", 2, CheckOutcome.INTERRUPTED),
        ("import legoai_missing_fixture_module\n", 2, CheckOutcome.INTERRUPTED),
    ],
)
def test_real_pytest_exit_semantics(
    project: Path,
    tools: LocalCheckTools,
    content: str,
    code: int,
    outcome: CheckOutcome,
) -> None:
    source = project / "test_sample.py"
    source.write_text(content, encoding="utf-8")
    before = source.read_bytes()
    result = runner(project, tools).check(request(CheckKind.PYTEST, source.name))
    assert result.exit_code == code
    assert result.outcome is outcome
    assert result.stdout
    assert source.read_bytes() == before
    assert not (project / ".pytest_cache").exists()
    assert not (project / "__pycache__").exists()


@pytest.mark.parametrize(
    ("kind", "content", "outcome"),
    [
        (CheckKind.RUFF_CHECK, "value: int = 1\n", CheckOutcome.PASSED),
        (CheckKind.RUFF_CHECK, "import os\n", CheckOutcome.FAILED),
        (CheckKind.RUFF_FORMAT_CHECK, "value: int = 1\n", CheckOutcome.PASSED),
        (CheckKind.RUFF_FORMAT_CHECK, "value=  1\n", CheckOutcome.FAILED),
        (CheckKind.MYPY, "value: int = 1\n", CheckOutcome.PASSED),
        (CheckKind.MYPY, 'value: int = "bad"\n', CheckOutcome.FAILED),
    ],
)
def test_real_lint_format_and_typecheck_do_not_change_source(
    project: Path,
    tools: LocalCheckTools,
    kind: CheckKind,
    content: str,
    outcome: CheckOutcome,
) -> None:
    source = project / "sample.py"
    source.write_text(content, encoding="utf-8")
    before = source.read_bytes()
    # Even host/project fix settings cannot turn checks into source mutation.
    (project / "ruff.toml").write_text(
        'fix = true\nfix-only = true\nlint.select = ["F"]\n', encoding="utf-8"
    )
    result = runner(project, tools).check(request(kind, source.name))
    assert result.outcome is outcome, (result.exit_code, result.stdout, result.stderr)
    assert source.read_bytes() == before
    assert not (project / ".ruff_cache").exists()
    assert not (project / ".mypy_cache").exists()


@pytest.mark.parametrize(
    "name", ["space café.py", "; echo owned.py", "@args.py", "--help.py"]
)
def test_targets_are_plain_paths(
    project: Path, tools: LocalCheckTools, name: str
) -> None:
    source = project / name
    source.write_text("value = 1\n", encoding="utf-8")
    result = runner(project, tools).check(request(CheckKind.RUFF_CHECK, name))
    assert result.outcome is CheckOutcome.PASSED, result.stderr
    assert not (project / "owned.py").exists()


def test_cwd_is_bound_and_directory_target_supported(
    project: Path, tools: LocalCheckTools, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project / "tests").mkdir()
    (project / "tests" / "test_cwd.py").write_text(
        "from pathlib import Path\n"
        "def test_cwd():\n"
        "    assert Path('pytest.ini').is_file()\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(project.parent)
    assert (
        runner(project, tools).check(request(CheckKind.PYTEST, "tests")).outcome
        is CheckOutcome.PASSED
    )


def test_unavailable_is_distinct_from_tool_failure(project: Path) -> None:
    (project / "sample.py").write_bytes(b"value = 1\n")
    with pytest.raises(CheckError) as caught:
        runner(project, tools_at(project / "absent")).check(
            request(CheckKind.RUFF_CHECK, "sample.py")
        )
    assert caught.value.reason is CheckFailure.UNAVAILABLE
    assert isinstance(caught.value.__cause__, FileNotFoundError)
    assert str(project) not in str(caught.value)


@pytest.mark.parametrize("path", ["../outside", "/absolute", "C:/outside", "a\\..\\b"])
def test_invalid_path_never_starts_process(path: str) -> None:
    with pytest.raises(WorkspaceBoundaryError):
        request(CheckKind.PYTEST, path)


def test_all_targets_checked_before_dispatch(project: Path) -> None:
    (project / "sample.py").write_bytes(b"value = 1\n")
    checks = runner(project, tools_at(project / "absent"))
    for path, reason in (
        ("missing", WorkspaceFailure.MISSING),
        (".git/config", WorkspaceFailure.EXCLUDED),
        (".venv/a.py", WorkspaceFailure.EXCLUDED),
    ):
        with pytest.raises(WorkspaceError) as caught:
            checks.check(request(CheckKind.RUFF_CHECK, "sample.py", path))
        assert caught.value.reason is reason


def test_command_mapping_has_only_fixed_check_options(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from legoai_engineering.checks import local

    (project / "@args.py").write_bytes(b"value = 1\n")
    tools = tools_at(project / "trusted tools")
    calls: list[tuple[Path, list[str]]] = []

    def capture(
        executable: Path, arguments: list[str], root: Path, policy: CheckPolicy
    ) -> tuple[int, bytes, bytes]:
        assert root == project and policy == CheckPolicy()
        calls.append((executable, arguments))
        return 0, b"", b""

    monkeypatch.setattr(local, "_capture", capture)
    for kind in CheckKind:
        runner(project, tools).check(request(kind, "@args.py"))
    assert [call[0] for call in calls] == [
        tools.pytest,
        tools.ruff,
        tools.ruff,
        tools.mypy,
    ]
    assert "--no-fix" in calls[1][1] and "--no-fix-only" in calls[1][1]
    assert calls[2][1][:2] == ["format", "--check"]
    for _, arguments in calls:
        assert arguments[-2:] == ["--", str(project / "@args.py")]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction boundary")
def test_windows_junction_check_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "a.py").write_bytes(b"value = 1\n")
    junction = root / "junction"
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    try:
        with pytest.raises(WorkspaceBoundaryError):
            runner(root, tools_at(tmp_path / "absent")).check(
                request(CheckKind.PYTEST, "junction/a.py")
            )
    finally:
        junction.rmdir()


def test_symlink_target_parent_and_root_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "a.py").write_bytes(b"value = 1\n")
    try:
        (root / "linked.py").symlink_to(outside / "a.py")
        (root / "linked-dir").symlink_to(outside, target_is_directory=True)
        (tmp_path / "linked-root").symlink_to(root, target_is_directory=True)
    except OSError as error:
        if sys.platform == "win32" and error.winerror == 1314:
            pytest.skip("Windows symlink privilege unavailable; enable Developer Mode")
        raise
    for bound, target in (
        (root, "linked.py"),
        (root, "linked-dir/a.py"),
        (tmp_path / "linked-root", "linked.py"),
    ):
        with pytest.raises(WorkspaceBoundaryError):
            runner(bound, tools_at(tmp_path / "absent")).check(
                request(CheckKind.PYTEST, target)
            )


def test_private_capture_bounds_both_streams_and_preserves_bytes(
    tmp_path: Path,
) -> None:
    result = _capture(
        Path(sys.executable),
        ["-I", "-c", "import os; os.write(1, b'\\xffabc'); os.write(2, b'err!')"],
        tmp_path,
        CheckPolicy(10, 4),
    )
    assert result == (0, b"\xffabc", b"err!")
    for descriptor in (1, 2):
        with pytest.raises(CheckError) as caught:
            _capture(
                Path(sys.executable),
                ["-I", "-c", f"import os; os.write({descriptor}, b'x' * 4096)"],
                tmp_path,
                CheckPolicy(10, 128),
            )
        assert caught.value.reason is CheckFailure.OUTPUT_LIMIT


def test_private_capture_drains_dual_pipe_pressure(tmp_path: Path) -> None:
    result = _capture(
        Path(sys.executable),
        [
            "-I",
            "-c",
            "import os\nfor _ in range(64):\n"
            " os.write(1, b'x' * 4096)\n os.write(2, b'y' * 4096)\n",
        ],
        tmp_path,
        CheckPolicy(10, 262_144),
    )
    assert result == (0, b"x" * 262_144, b"y" * 262_144)


def test_private_capture_stdin_is_closed(tmp_path: Path) -> None:
    code, stdout, stderr = _capture(
        Path(sys.executable),
        ["-I", "-c", "import sys; print(repr(sys.stdin.read()))"],
        tmp_path,
        CheckPolicy(10, 128),
    )
    assert code == 0 and stdout.strip() == b"''" and stderr == b""


@pytest.mark.parametrize("fault", ["timeout", "io", "interrupt"])
def test_failure_kills_and_reaps_direct_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    original = subprocess.Popen
    children: list[subprocess.Popen[bytes]] = []

    def start(
        args: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        stdin: int,
        stdout: int,
        stderr: int,
        shell: bool,
        bufsize: int,
    ) -> subprocess.Popen[bytes]:
        assert stdin == subprocess.DEVNULL and shell is False
        child = original(
            args,
            cwd=cwd,
            env=env,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            shell=shell,
            bufsize=bufsize,
        )
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", start)
    if fault != "timeout":

        def stop(descriptor: int, blocking: bool) -> None:
            if fault == "io":
                raise OSError("synthetic pipe setup failure")
            raise KeyboardInterrupt()

        monkeypatch.setattr(os, "set_blocking", stop)
    before = time.monotonic()
    expected = KeyboardInterrupt if fault == "interrupt" else CheckError
    with pytest.raises(expected) as caught:
        _capture(
            Path(sys.executable),
            ["-I", "-c", "import time; time.sleep(30)"],
            tmp_path,
            CheckPolicy(1, 128),
        )
    if isinstance(caught.value, CheckError):
        reason = CheckFailure.TIMEOUT if fault == "timeout" else CheckFailure.IO
        assert caught.value.reason is reason
        if fault == "io":
            assert isinstance(caught.value.__cause__, OSError)
    assert time.monotonic() - before < 10
    assert len(children) == 1 and children[0].poll() is not None
    assert children[0].stdout is not None and children[0].stdout.closed
    assert children[0].stderr is not None and children[0].stderr.closed


def test_environment_is_filtered_without_global_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("PYTHONPATH", "PYTEST_ADDOPTS", "MYPYPATH", "RUFF_OUTPUT_FILE"):
        monkeypatch.setenv(name, "private-fixture-value")
    before = dict(os.environ)
    environment = _environment()
    assert environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert environment["PYTHONDONTWRITEBYTECODE"] == "1"
    assert "private-fixture-value" not in environment.values()
    assert dict(os.environ) == before


def test_values_and_configuration_are_closed_and_bounded(tmp_path: Path) -> None:
    proposal = request(CheckKind.PYTEST, "tests")
    with pytest.raises(FrozenInstanceError):
        proposal.kind = CheckKind.MYPY  # type: ignore[misc]
    with pytest.raises(ValueError):
        request(CheckKind.PYTEST)
    with pytest.raises(ValueError):
        request(CheckKind.PYTEST, "a", "A")
    with pytest.raises(ValueError):
        request(CheckKind.PYTEST, *(str(i) for i in range(33)))
    with pytest.raises(TypeError):
        CheckRequest("pytest", ())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        CheckRequest(CheckKind.PYTEST, [])  # type: ignore[arg-type]
    for policy in (CheckPolicy(), CheckPolicy(3600, 1_048_576)):
        with pytest.raises(TypeError):
            replace(policy, timeout_seconds=True)
        with pytest.raises(ValueError):
            replace(policy, timeout_seconds=0)
        with pytest.raises(ValueError):
            replace(policy, max_output_bytes=1_048_577)
    with pytest.raises(ValueError):
        replace(tools_at(tmp_path), pytest=tmp_path / "cmd.exe")
    with pytest.raises(ValueError):
        replace(tools_at(tmp_path), ruff=Path("ruff"))
    with pytest.raises(TypeError):
        CheckResult(CheckKind.PYTEST, True, b"", b"")
    with pytest.raises(ValueError):
        CheckResult(CheckKind.PYTEST, 0, b"x" * 1_048_577, b"")
    assert "secret" not in repr(CheckResult(CheckKind.PYTEST, 0, b"secret", b"secret"))


@pytest.mark.parametrize("kind", list(CheckKind))
def test_completed_exit_mapping(kind: CheckKind) -> None:
    assert CheckResult(kind, 0, b"", b"").outcome is CheckOutcome.PASSED
    assert CheckResult(kind, 1, b"", b"").outcome is CheckOutcome.FAILED
    for code in (-9, 3, 4, 17):
        assert CheckResult(kind, code, b"", b"").outcome is CheckOutcome.ERROR
    if kind is not CheckKind.PYTEST:
        assert CheckResult(kind, 2, b"", b"").outcome is CheckOutcome.ERROR
        assert CheckResult(kind, 5, b"", b"").outcome is CheckOutcome.ERROR


def test_m4_changes_are_observed_by_m5(project: Path, tools: LocalCheckTools) -> None:
    path = project / "sample.py"
    old = "value: int = 1\n"
    path.write_bytes(old.encode())
    checks = runner(project, tools)
    assert (
        checks.check(request(CheckKind.MYPY, path.name)).outcome is CheckOutcome.PASSED
    )
    mutation = LocalRepositoryMutation(
        LocalWorkspaceRoot(project), WorkspacePolicy(4096, 4096, 128, 8, (".git",))
    )
    new = 'value: int = "bad"\n'
    mutation.apply(
        RepositoryChangeSet(
            (
                FileChange(
                    RepositoryPath(path.name),
                    FileChangeKind.UPDATE,
                    digest_text(old),
                    new,
                ),
            )
        )
    )
    assert (
        checks.check(request(CheckKind.MYPY, path.name)).outcome is CheckOutcome.FAILED
    )
    assert path.read_bytes() == new.encode()


def test_m3_state_preserved_by_known_nonmutating_fixture(
    project: Path, tools: LocalCheckTools
) -> None:
    git = shutil.which("git")
    assert git is not None, "M5 coexistence qualification requires Git"
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    }
    if os.name == "nt":
        environment["SystemRoot"] = os.environ["SystemRoot"]
    subprocess.run(
        [git, "init", "--initial-branch=main", "--template="],
        cwd=project,
        env=environment,
        capture_output=True,
        check=True,
        timeout=15,
    )
    (project / "test_sample.py").write_text(
        "def test_ok() -> None:\n    assert True\n", encoding="utf-8"
    )
    reader = LocalGitRepository(
        LocalWorkspaceRoot(project),
        LocalGitExecutable(Path(git)),
        GitReadPolicy(10, 262_144, 128, 4096),
    )
    before = reader.inspect()
    for kind in CheckKind:
        result = runner(project, tools).check(request(kind, "test_sample.py"))
        assert result.outcome is CheckOutcome.PASSED, result.stderr
    assert reader.inspect() == before


def test_check_example(tmp_path: Path, tools: LocalCheckTools) -> None:
    example = Path(__file__).resolve().parents[1] / "examples" / "check_intake.py"
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(example)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "ruff_check: passed"
    assert list(tmp_path.iterdir()) == []
