"""CR-2b deterministic contract tests: fake workspace and fake sandbox, no Docker."""

import ast
import base64
import json
import os
from pathlib import Path
from threading import Event
from unittest.mock import patch

import pytest

from legoai_engineering.checks import sandboxed
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
    CheckResult,
)
from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.local import LocalWorkspaceRoot
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import (
    RepositoryPath,
    WorkspaceEntry,
    WorkspaceEntryKind,
)
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure
from legoai_engineering.sandbox.ports import CancellationSignal
from legoai_engineering.sandbox.values import SandboxRequest, SandboxResult

PROJECT = {
    "pyproject.toml": "[tool.pytest.ini_options]\n",
    "src/pkg/__init__.py": "",
    "src/pkg/core.py": "VALUE = 1\n",
    "src/pkg/core.pyi": "VALUE: int\n",
    "src/pkg/py.typed": "",
    "src/pkg/README.md": "not selected\n",
    "src/pkg/data.json": "{}\n",
    "src/.hidden/x.py": "hidden = 1\n",
    "src/pkg/__pycache__/core.py": "cache = 1\n",
    "src/pkg/credentials": "secret\n",
    "tests/test_core.py": "def test_value() -> None:\n    assert True\n",
    "tests/conftest.py": "",
    "docs/notes.py": "outside roots\n",
}
INPUTS = CheckInputPolicy(
    (RepositoryPath("src"), RepositoryPath("tests")),
    (RepositoryPath("pyproject.toml"),),
)


class FakeWorkspace:
    """In-memory RepositoryWorkspacePort; directories are inferred from paths."""

    def __init__(self, files: dict[str, str], failures: dict[str, WorkspaceFailure]):
        self.files = files
        self.failures = failures
        self.reads: list[str] = []
        self.on_read: Event | None = None

    def list_entries(
        self, directory: RepositoryPath | None
    ) -> tuple[WorkspaceEntry, ...]:
        prefix = "" if directory is None else directory.value + "/"
        if directory is not None and not any(p.startswith(prefix) for p in self.files):
            raise WorkspaceError(WorkspaceFailure.MISSING)
        entries: dict[str, WorkspaceEntryKind] = {}
        for path in self.files:
            if not path.startswith(prefix):
                continue
            head, _, rest = path[len(prefix) :].partition("/")
            kind = WorkspaceEntryKind.DIRECTORY if rest else WorkspaceEntryKind.FILE
            entries[prefix + head] = kind
        return tuple(
            WorkspaceEntry(RepositoryPath(name), kind)
            for name, kind in sorted(entries.items())
        )

    def read_text(self, path: RepositoryPath) -> RepositoryText:
        self.reads.append(path.value)
        if self.on_read is not None:
            self.on_read.set()
        if path.value in self.failures:
            raise WorkspaceError(self.failures[path.value])
        if path.value not in self.files:
            raise WorkspaceError(WorkspaceFailure.MISSING)
        return RepositoryText(path.value, self.files[path.value])


def envelope(**fields: object) -> bytes:
    return json.dumps(fields).encode()


def completed(exit_code: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> bytes:
    return envelope(
        status="completed",
        exit=exit_code,
        stdout=base64.b64encode(stdout).decode(),
        stderr=base64.b64encode(stderr).decode(),
    )


class FakeSandbox:
    def __init__(self, stdout: bytes = b"", *, exit_code: int = 0) -> None:
        self.stdout = stdout or completed()
        self.exit_code = exit_code
        self.error: SandboxError | None = None
        self.calls: list[tuple[SandboxRequest, CancellationSignal | None]] = []

    def execute(
        self, request: SandboxRequest, cancellation: CancellationSignal | None = None
    ) -> SandboxResult:
        self.calls.append((request, cancellation))
        if self.error is not None:
            raise self.error
        return SandboxResult(self.exit_code, self.stdout, b"")


def adapter(
    sandbox: FakeSandbox | None = None,
    *,
    files: dict[str, str] | None = None,
    failures: dict[str, WorkspaceFailure] | None = None,
    inputs: CheckInputPolicy = INPUTS,
    policy: CheckPolicy | None = None,
    cancellation: Event | None = None,
) -> tuple[SandboxedEngineeringChecks, FakeWorkspace, FakeSandbox]:
    workspace = FakeWorkspace(PROJECT if files is None else files, failures or {})
    sandbox = sandbox or FakeSandbox()
    checks = SandboxedEngineeringChecks(
        workspace, sandbox, inputs, policy or CheckPolicy(), cancellation
    )
    return checks, workspace, sandbox


def request(kind: CheckKind = CheckKind.PYTEST, *targets: str) -> CheckRequest:
    return CheckRequest(kind, tuple(RepositoryPath(t) for t in targets or ("tests",)))


def specification(sandbox: FakeSandbox) -> dict[str, object]:
    spec = sandbox.calls[-1][0].files[-1]
    assert spec.path == "__legoai_check__.json"
    value: dict[str, object] = json.loads(spec.text)
    return value


# --- A/B. CheckKind selection and shared command semantics --------------------


@pytest.mark.parametrize(
    ("kind", "tool", "arguments"),
    [
        (
            CheckKind.PYTEST,
            "pytest",
            ["-q", "-o", "addopts=", "-p", "no:cacheprovider"],
        ),
        (
            CheckKind.RUFF_CHECK,
            "ruff",
            ["check", "--no-fix", "--no-fix-only", "--no-cache"],
        ),
        (CheckKind.RUFF_FORMAT_CHECK, "ruff", ["format", "--check", "--no-cache"]),
        (CheckKind.MYPY, "mypy", ["--no-incremental", "--cache-dir", "/dev/null"]),
    ],
)
def test_kind_selects_only_its_fixed_tool(
    kind: CheckKind, tool: str, arguments: list[str]
) -> None:
    checks, _, sandbox = adapter()
    checks.check(request(kind, "src", "tests"))
    assert specification(sandbox) == {
        "tool": tool,
        "arguments": arguments,
        "targets": ["src", "tests"],
        "timeout": 60,
        "max_output": 262_144,
    }


@pytest.mark.parametrize("kind", list(CheckKind))
def test_host_and_sandbox_options_are_identical(
    tmp_path: Path, kind: CheckKind
) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.py").write_text("", encoding="utf-8")
    suffix = ".exe" if os.name == "nt" else ""
    tools = LocalCheckTools(
        *(tmp_path / (name + suffix) for name in ("pytest", "ruff", "mypy"))
    )
    local = LocalEngineeringChecks(LocalWorkspaceRoot(tmp_path), tools, CheckPolicy())
    with patch(
        "legoai_engineering.checks.local._capture", return_value=(0, b"", b"")
    ) as capture:
        local.check(CheckRequest(kind, (RepositoryPath("tests"),)))
    executable, argv, _, _ = capture.call_args.args
    host = argv[: argv.index("--")]
    checks, _, sandbox = adapter()
    checks.check(request(kind))
    spec = specification(sandbox)
    assert executable.stem == spec["tool"]
    null = os.devnull
    assert [a if a != null else "/dev/null" for a in host] == spec["arguments"]


def test_single_private_command_table() -> None:
    root = Path(__file__).resolve().parents[1] / "src"
    owners = set()
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text("utf-8"))):
            if isinstance(node, ast.Constant) and node.value in {
                "--no-fix-only",
                "no:cacheprovider",
                "--no-incremental",
            }:
                owners.add(path.name)
    assert owners == {"_commands.py"}


def test_runner_is_one_constant_and_takes_no_caller_command() -> None:
    first, _, sandbox = adapter()
    first.check(request(CheckKind.PYTEST))
    first.check(request(CheckKind.MYPY, "src"))
    scripts = {call[0].script for call in sandbox.calls}
    assert scripts == {sandboxed._RUNNER}
    tree = ast.parse(sandboxed._RUNNER)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    runs = [c for c in calls if getattr(c.func, "attr", "") == "run"]
    assert len(runs) == 1
    keywords = {k.arg: k.value for k in runs[0].keywords}
    shell = keywords["shell"]
    assert isinstance(shell, ast.Constant) and shell.value is False
    assert (
        "shell=True" not in sandboxed._RUNNER and "os.system" not in sandboxed._RUNNER
    )


# --- C. Input acquisition --------------------------------------------------------


def test_selection_is_deterministic_and_bounded_to_text_types() -> None:
    checks, _, sandbox = adapter()
    checks.check(request())
    paths = [item.path for item in sandbox.calls[0][0].files]
    assert paths == [
        "pyproject.toml",
        "src/pkg/__init__.py",
        "src/pkg/core.py",
        "src/pkg/core.pyi",
        "src/pkg/py.typed",
        "tests/conftest.py",
        "tests/test_core.py",
        "__legoai_check__.json",
    ]
    texts = {item.path: item.text for item in sandbox.calls[0][0].files[:-1]}
    assert all(texts[path] == PROJECT[path] for path in texts)


@pytest.mark.parametrize(
    "target",
    [
        "docs/notes.py",
        "src/pkg/README.md",
        "src/.hidden/x.py",
        "missing",
        "src/pkg/credentials",
    ],
)
def test_target_outside_selection_is_refused(target: str) -> None:
    checks, _, sandbox = adapter()
    with pytest.raises(WorkspaceError) as caught:
        checks.check(request(CheckKind.PYTEST, target))
    assert caught.value.reason is WorkspaceFailure.EXCLUDED
    assert sandbox.calls == []


def test_missing_root_and_unreadable_input_fail_closed() -> None:
    checks, _, sandbox = adapter(inputs=CheckInputPolicy((RepositoryPath("absent"),)))
    with pytest.raises(WorkspaceError) as caught:
        checks.check(request())
    assert caught.value.reason is WorkspaceFailure.MISSING
    checks, _, sandbox = adapter(failures={"src/pkg/core.py": WorkspaceFailure.BINARY})
    with pytest.raises(WorkspaceError) as caught:
        checks.check(request())
    assert caught.value.reason is WorkspaceFailure.BINARY
    assert sandbox.calls == []


@pytest.mark.parametrize(
    "files",
    [
        {f"tests/test_{i:02}.py": "" for i in range(64)},
        # RepositoryText caps each file at 65,536 code points (<= 262,144 bytes),
        # so the aggregate bound is the reachable byte limit: 5 x 240,000 bytes.
        {f"tests/m{i}.py": "\U00010348" * 60_000 for i in range(5)},
    ],
    ids=["file-count", "total-bytes"],
)
def test_overflow_is_input_limit_never_truncation(files: dict[str, str]) -> None:
    checks, _, sandbox = adapter(
        files=files, inputs=CheckInputPolicy((RepositoryPath("tests"),))
    )
    with pytest.raises(CheckError) as caught:
        checks.check(request())
    assert caught.value.reason is CheckFailure.INPUT_LIMIT
    assert sandbox.calls == []


def test_workspace_limit_and_scan_limit_are_input_limits() -> None:
    checks, _, sandbox = adapter(failures={"src/pkg/core.py": WorkspaceFailure.LIMIT})
    with pytest.raises(CheckError) as caught:
        checks.check(request())
    assert caught.value.reason is CheckFailure.INPUT_LIMIT
    checks, _, sandbox = adapter(
        inputs=CheckInputPolicy((RepositoryPath("src"),), max_scan_entries=2)
    )
    with pytest.raises(CheckError) as caught:
        checks.check(request(CheckKind.MYPY, "src"))
    assert caught.value.reason is CheckFailure.INPUT_LIMIT
    assert sandbox.calls == []


def test_input_policy_validation() -> None:
    with pytest.raises(ValueError):
        CheckInputPolicy(())
    with pytest.raises(ValueError):
        CheckInputPolicy((RepositoryPath("src"), RepositoryPath("SRC")))
    for excluded in (".git", ".venv", "src/__pycache__", "__legoai_check__.json"):
        with pytest.raises(ValueError):
            CheckInputPolicy((RepositoryPath(excluded),))
    with pytest.raises(ValueError):
        CheckInputPolicy((RepositoryPath("src"),), (RepositoryPath("README.md"),))
    with pytest.raises(TypeError):
        CheckInputPolicy((RepositoryPath("src"),), max_scan_entries=True)
    with pytest.raises(ValueError):
        CheckInputPolicy((RepositoryPath("src"),), max_scan_entries=0)


# --- D. Sandbox request ---------------------------------------------------------


def test_one_execution_per_check_with_bound_cancellation() -> None:
    signal = Event()
    checks, _, sandbox = adapter(cancellation=signal)
    for kind in CheckKind:
        checks.check(request(kind, "src"))
    assert len(sandbox.calls) == len(CheckKind)
    assert all(call[1] is signal for call in sandbox.calls)


def test_constructor_rejects_wrong_types() -> None:
    workspace = FakeWorkspace(PROJECT, {})
    with pytest.raises(TypeError):
        SandboxedEngineeringChecks(object(), FakeSandbox(), INPUTS, CheckPolicy())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        SandboxedEngineeringChecks(workspace, object(), INPUTS, CheckPolicy())  # type: ignore[arg-type]
    not_a_signal: object = object()
    with pytest.raises(TypeError):
        SandboxedEngineeringChecks(
            workspace,
            FakeSandbox(),
            INPUTS,
            CheckPolicy(),
            not_a_signal,  # type: ignore[arg-type]
        )


# --- E. Result mapping ------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "code", "outcome"),
    [
        (CheckKind.PYTEST, 0, CheckOutcome.PASSED),
        (CheckKind.PYTEST, 1, CheckOutcome.FAILED),
        (CheckKind.PYTEST, 2, CheckOutcome.INTERRUPTED),
        (CheckKind.PYTEST, 5, CheckOutcome.NO_TESTS),
        (CheckKind.RUFF_CHECK, 1, CheckOutcome.FAILED),
        (CheckKind.RUFF_FORMAT_CHECK, 1, CheckOutcome.FAILED),
        (CheckKind.MYPY, 1, CheckOutcome.FAILED),
        (CheckKind.MYPY, 2, CheckOutcome.ERROR),
    ],
)
def test_findings_are_results_not_failures(
    kind: CheckKind, code: int, outcome: CheckOutcome
) -> None:
    checks, _, _ = adapter(FakeSandbox(completed(code, b"out", b"err")))
    result = checks.check(request(kind, "src"))
    assert result == CheckResult(kind, code, b"out", b"err")
    assert result.outcome is outcome


# --- F. Infrastructure failures ----------------------------------------------------


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        (SandboxFailure.TIMEOUT, CheckFailure.TIMEOUT),
        (SandboxFailure.CANCELLED, CheckFailure.CANCELLED),
        (SandboxFailure.RESOURCE_LIMIT, CheckFailure.RESOURCE_LIMIT),
        (SandboxFailure.OUTPUT_LIMIT, CheckFailure.OUTPUT_LIMIT),
        (SandboxFailure.CLEANUP, CheckFailure.CLEANUP),
        (SandboxFailure.UNSUPPORTED, CheckFailure.CONFINEMENT),
        (SandboxFailure.RUNTIME_UNAVAILABLE, CheckFailure.UNAVAILABLE),
        (SandboxFailure.ENVIRONMENT_UNAVAILABLE, CheckFailure.UNAVAILABLE),
        (SandboxFailure.PREPARATION, CheckFailure.IO),
        (SandboxFailure.CONTROL, CheckFailure.IO),
        (SandboxFailure.ARTIFACT, CheckFailure.IO),
    ],
)
def test_every_sandbox_failure_maps_explicitly(
    reason: SandboxFailure, expected: CheckFailure
) -> None:
    sandbox = FakeSandbox()
    sandbox.error = SandboxError(reason)
    checks, _, _ = adapter(sandbox)
    with pytest.raises(CheckError) as caught:
        checks.check(request())
    assert caught.value.reason is expected
    assert caught.value.__cause__ is sandbox.error
    assert str(caught.value) == expected.value
    assert len(sandbox.calls) == 1


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("unavailable", CheckFailure.UNAVAILABLE),
        ("timeout", CheckFailure.TIMEOUT),
        ("output_limit", CheckFailure.OUTPUT_LIMIT),
        ("resource_limit", CheckFailure.RESOURCE_LIMIT),
    ],
)
def test_runner_reported_failures(status: str, expected: CheckFailure) -> None:
    checks, _, _ = adapter(FakeSandbox(envelope(status=status)))
    with pytest.raises(CheckError) as caught:
        checks.check(request())
    assert caught.value.reason is expected


@pytest.mark.parametrize(
    "stdout",
    [
        b"not json",
        b"[]",
        envelope(status="completed", exit=0),
        envelope(status="completed", exit="0", stdout="", stderr=""),
        envelope(status="completed", exit=0, stdout="***", stderr=""),
        envelope(status="timeout", exit=0),
        envelope(status="passed"),
    ],
)
def test_malformed_runner_protocol_is_io(stdout: bytes) -> None:
    checks, _, _ = adapter(FakeSandbox(stdout))
    with pytest.raises(CheckError) as caught:
        checks.check(request())
    assert caught.value.reason is CheckFailure.IO


def test_nonzero_runner_exit_is_io_not_a_check_result() -> None:
    checks, _, _ = adapter(FakeSandbox(completed(0), exit_code=1))
    with pytest.raises(CheckError) as caught:
        checks.check(request())
    assert caught.value.reason is CheckFailure.IO


def test_decoded_output_beyond_policy_is_output_limit() -> None:
    checks, _, _ = adapter(
        FakeSandbox(completed(0, b"x" * 33)), policy=CheckPolicy(max_output_bytes=32)
    )
    with pytest.raises(CheckError) as caught:
        checks.check(request())
    assert caught.value.reason is CheckFailure.OUTPUT_LIMIT


# --- G. Cancellation ---------------------------------------------------------------


def test_cancelled_before_execution_reads_and_dispatches_nothing() -> None:
    signal = Event()
    signal.set()
    checks, workspace, sandbox = adapter(cancellation=signal)
    with pytest.raises(CheckError) as caught:
        checks.check(request())
    assert caught.value.reason is CheckFailure.CANCELLED
    assert workspace.reads == [] and sandbox.calls == []


def test_cancelled_during_input_acquisition_is_not_dispatched() -> None:
    signal = Event()
    checks, workspace, sandbox = adapter(cancellation=signal)
    workspace.on_read = signal
    with pytest.raises(CheckError) as caught:
        checks.check(request())
    assert caught.value.reason is CheckFailure.CANCELLED
    assert sandbox.calls == []


def test_cancelled_during_execution_maps_sandbox_cancellation() -> None:
    sandbox = FakeSandbox()
    sandbox.error = SandboxError(SandboxFailure.CANCELLED)
    checks, _, _ = adapter(sandbox, cancellation=Event())
    with pytest.raises(CheckError) as caught:
        checks.check(request())
    assert caught.value.reason is CheckFailure.CANCELLED


# --- H. Substitutability ------------------------------------------------------------


def outcomes(
    port: EngineeringCheckPort, requests: list[CheckRequest]
) -> list[CheckOutcome]:
    """Application code: depends on EngineeringCheckPort only."""
    return [port.check(item).outcome for item in requests]


def test_consumer_is_indifferent_to_the_adapter(tmp_path: Path) -> None:
    for path, text in PROJECT.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    suffix = ".exe" if os.name == "nt" else ""
    tools = LocalCheckTools(
        *(tmp_path / (name + suffix) for name in ("pytest", "ruff", "mypy"))
    )
    local = LocalEngineeringChecks(LocalWorkspaceRoot(tmp_path), tools, CheckPolicy())
    requests = [request(kind, "src", "tests") for kind in CheckKind]
    with patch("legoai_engineering.checks.local._capture", return_value=(0, b"", b"")):
        host = outcomes(local, requests)
    checks, _, _ = adapter()
    assert host == outcomes(checks, requests) == [CheckOutcome.PASSED] * 4
