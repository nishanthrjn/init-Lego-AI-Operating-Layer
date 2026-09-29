"""EngineeringCheckPort for repository- or model-written code (CR-2b).

Each `check` copies an operator-bounded text selection into ONE execution of the
injected `SandboxExecutionPort` and runs exactly the fixed tool for the request's
closed CheckKind, using the shared M5 command table. Compose it with the
qualified `SandboxImage.PYTHON_CHECKS` Docker sandbox. The container runner also
verifies the exact qualified tool versions, so any other environment fails as
UNAVAILABLE. There is no host fallback, retry, shell, caller argv, environment,
image or working-directory choice.

Containment is not result integrity: repository code runs inside the tool
process and can influence its own observed outcome. A PASSED result means the
contained execution reported success, not that LegoAI proved the code correct.
"""

import base64
import json
from dataclasses import dataclass

from legoai_engineering.checks._commands import _arguments, _tool
from legoai_engineering.checks.errors import CheckError, CheckFailure
from legoai_engineering.checks.values import CheckPolicy, CheckRequest, CheckResult
from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.ports import RepositoryWorkspacePort
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath, WorkspaceEntryKind
from legoai_engineering.sandbox.errors import SandboxError, SandboxFailure
from legoai_engineering.sandbox.ports import CancellationSignal, SandboxExecutionPort
from legoai_engineering.sandbox.values import SandboxRequest, _path

# Reserved input name carrying the adapter-generated specification.
_SPEC = "__legoai_check__.json"
_SUFFIXES = (".py", ".pyi", ".toml", ".cfg", ".ini")
_NAMES = frozenset({"py.typed"})
# Qualified M6/CR-2a input ceilings; one file is reserved for the specification.
_MAX_FILES = 63
_MAX_FILE_BYTES = 262_144
_MAX_TOTAL_BYTES = 1_040_384

# Trusted container-only runner. Byte-identical for every check; the per-check
# specification arrives as a data file and selects only a fixed known tool.
_RUNNER = r"""
import base64, importlib.metadata, json, os, pathlib, subprocess, sys


def finish(**fields):
    sys.stdout.write(json.dumps(fields, separators=(",", ":")))
    sys.stdout.flush()
    sys.exit(0)


spec_path = pathlib.Path("/work/__legoai_check__.json")
spec = json.loads(spec_path.read_text("utf-8"))
spec_path.unlink()
required = {"pytest": "9.1.1", "ruff": "0.16.8", "mypy": "2.3.1"}
try:
    versions = {name: importlib.metadata.version(name) for name in required}
except importlib.metadata.PackageNotFoundError:
    finish(status="unavailable")
executable = "/usr/local/bin/" + spec["tool"]
if versions != required or spec["tool"] not in required or not os.path.isfile(executable):
    finish(status="unavailable")
argv = [executable, *spec["arguments"], "--"]
argv += ["/work/" + target for target in spec["targets"]]
environment = {
    "PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": "/nonexistent",
    "TMPDIR": "/tmp", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "NO_COLOR": "1",
}
streams = [open("/tmp/legoai-check-" + name, "w+b") for name in ("stdout", "stderr")]
try:
    completed = subprocess.run(
        argv, cwd="/work", env=environment, stdin=subprocess.DEVNULL,
        stdout=streams[0], stderr=streams[1], timeout=spec["timeout"], shell=False,
    )
except subprocess.TimeoutExpired:
    finish(status="timeout")
events = {}
try:
    for row in pathlib.Path("/sys/fs/cgroup/memory.events").read_text().splitlines():
        key, value = row.split()
        events[key] = int(value)
except OSError:
    pass
if events.get("oom_kill", 0) > 0:
    finish(status="resource_limit")
outputs = []
for stream in streams:
    stream.seek(0)
    data = stream.read(spec["max_output"] + 1)
    if len(data) > spec["max_output"]:
        finish(status="output_limit")
    outputs.append(base64.b64encode(data).decode("ascii"))
finish(status="completed", exit=completed.returncode, stdout=outputs[0], stderr=outputs[1])
"""


def _included(path: RepositoryPath) -> bool:
    name = path.value.rpartition("/")[2]
    return name in _NAMES or name.endswith(_SUFFIXES)


def _excluded(path: RepositoryPath) -> bool:
    """Hidden/cache components, the reserved name and sandbox-refused names."""
    parts = path.value.split("/")
    if any(part.startswith(".") or part == "__pycache__" for part in parts):
        return True
    if parts[-1] == _SPEC:
        return True
    try:
        _path(path)
    except ValueError:
        return True
    return False


def _within(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


@dataclass(frozen=True, slots=True)
class CheckInputPolicy:
    """Operator-owned bounded selection of repository text copied into the sandbox.

    `roots` are walked recursively; `files` are explicit extra files such as
    pyproject.toml or conftest.py. Only .py/.pyi/.toml/.cfg/.ini files and
    py.typed are selected. Hidden and cache components and sandbox-refused
    secret names are never copied. Selection is deterministic and fails with
    INPUT_LIMIT instead of dropping files.
    """

    roots: tuple[RepositoryPath, ...]
    files: tuple[RepositoryPath, ...] = ()
    max_scan_entries: int = 4096

    def __post_init__(self) -> None:
        if type(self.roots) is not tuple or type(self.files) is not tuple:
            raise TypeError("check inputs require tuples of RepositoryPath")
        if any(type(path) is not RepositoryPath for path in self.roots + self.files):
            raise TypeError("check inputs require RepositoryPath values")
        if not 1 <= len(self.roots) <= 16 or len(self.files) > 16:
            raise ValueError("check inputs require 1..16 roots and 0..16 files")
        names = [path.value.casefold() for path in self.roots + self.files]
        if len(set(names)) != len(names):
            raise ValueError("duplicate check input path")
        if any(_excluded(path) for path in self.roots + self.files):
            raise ValueError("excluded check input path")
        if any(not _included(path) for path in self.files):
            raise ValueError("check input file type is not selectable")
        if type(self.max_scan_entries) is not int:
            raise TypeError("max_scan_entries requires int")
        if not 1 <= self.max_scan_entries <= 65_536:
            raise ValueError("max_scan_entries outside supported range")


def _mapped(reason: SandboxFailure) -> CheckFailure:
    match reason:
        case SandboxFailure.TIMEOUT:
            return CheckFailure.TIMEOUT
        case SandboxFailure.CANCELLED:
            return CheckFailure.CANCELLED
        case SandboxFailure.RESOURCE_LIMIT:
            return CheckFailure.RESOURCE_LIMIT
        case SandboxFailure.OUTPUT_LIMIT:
            return CheckFailure.OUTPUT_LIMIT
        case SandboxFailure.CLEANUP:
            return CheckFailure.CLEANUP
        case SandboxFailure.UNSUPPORTED:
            return CheckFailure.CONFINEMENT
        case (
            SandboxFailure.RUNTIME_UNAVAILABLE | SandboxFailure.ENVIRONMENT_UNAVAILABLE
        ):
            return CheckFailure.UNAVAILABLE
        case _:
            # PREPARATION, CONTROL, ARTIFACT: the sandbox exchange itself failed.
            return CheckFailure.IO


def _interpret(
    request: CheckRequest, stdout: bytes, exit_code: int, policy: CheckPolicy
) -> CheckResult:
    """Decode the runner envelope; findings are results, not failures."""
    if exit_code != 0:
        raise CheckError(CheckFailure.IO)
    try:
        envelope: object = json.loads(stdout)
    except (ValueError, RecursionError) as error:
        raise CheckError(CheckFailure.IO) from error
    if not isinstance(envelope, dict):
        raise CheckError(CheckFailure.IO)
    status = envelope.get("status")
    failures = {
        "unavailable": CheckFailure.UNAVAILABLE,
        "timeout": CheckFailure.TIMEOUT,
        "output_limit": CheckFailure.OUTPUT_LIMIT,
        "resource_limit": CheckFailure.RESOURCE_LIMIT,
    }
    if status in failures and set(envelope) == {"status"}:
        raise CheckError(failures[status])
    if status != "completed" or set(envelope) != {
        "status",
        "exit",
        "stdout",
        "stderr",
    }:
        raise CheckError(CheckFailure.IO)
    code, out, err = envelope["exit"], envelope["stdout"], envelope["stderr"]
    if type(code) is not int or type(out) is not str or type(err) is not str:
        raise CheckError(CheckFailure.IO)
    try:
        streams = [base64.b64decode(value, validate=True) for value in (out, err)]
        result = CheckResult(request.kind, code, streams[0], streams[1])
    except ValueError as error:
        raise CheckError(CheckFailure.IO) from error
    if max(len(streams[0]), len(streams[1])) > policy.max_output_bytes:
        raise CheckError(CheckFailure.OUTPUT_LIMIT)
    return result


class SandboxedEngineeringChecks:
    """Sandboxed EngineeringCheckPort realization; one sandbox execution per check.

    Construction is inert. The optional cancellation signal is bound for this
    instance (one run): it is checked before input acquisition and before
    dispatch, and is passed to the sandbox, which terminates and cleans up.
    """

    __slots__ = ("_workspace", "_sandbox", "_inputs", "_policy", "_cancellation")

    def __init__(
        self,
        workspace: RepositoryWorkspacePort,
        sandbox: SandboxExecutionPort,
        inputs: CheckInputPolicy,
        policy: CheckPolicy,
        cancellation: CancellationSignal | None = None,
    ) -> None:
        if not callable(getattr(workspace, "list_entries", None)) or not callable(
            getattr(workspace, "read_text", None)
        ):
            raise TypeError("checks require a RepositoryWorkspacePort")
        if not callable(getattr(sandbox, "execute", None)):
            raise TypeError("checks require a SandboxExecutionPort")
        if type(inputs) is not CheckInputPolicy or type(policy) is not CheckPolicy:
            raise TypeError("checks require CheckInputPolicy and CheckPolicy")
        if cancellation is not None and not callable(
            getattr(cancellation, "is_set", None)
        ):
            raise TypeError("cancellation requires an is_set() signal")
        self._workspace = workspace
        self._sandbox = sandbox
        self._inputs = inputs
        self._policy = policy
        self._cancellation = cancellation

    def _check_cancelled(self) -> None:
        if self._cancellation is not None and self._cancellation.is_set():
            raise CheckError(CheckFailure.CANCELLED)

    def _read(self, path: RepositoryPath) -> RepositoryText:
        try:
            return self._workspace.read_text(path)
        except WorkspaceError as error:
            if error.reason is WorkspaceFailure.LIMIT:
                raise CheckError(CheckFailure.INPUT_LIMIT) from error
            raise

    def _select(self) -> tuple[RepositoryText, ...]:
        selected: dict[str, RepositoryText] = {}
        total = 0

        def _add(path: RepositoryPath) -> None:
            nonlocal total
            if path.value in selected:
                return
            if len(selected) >= _MAX_FILES:
                raise CheckError(CheckFailure.INPUT_LIMIT)
            text = self._read(path)
            size = len(text.text.encode("utf-8"))
            total += size
            if size > _MAX_FILE_BYTES or total > _MAX_TOTAL_BYTES:
                raise CheckError(CheckFailure.INPUT_LIMIT)
            selected[path.value] = text

        for path in self._inputs.files:
            _add(path)
        scanned = 0
        pending = sorted(self._inputs.roots, key=lambda path: path.value, reverse=True)
        while pending:
            directory = pending.pop()
            entries = self._workspace.list_entries(directory)
            scanned += len(entries)
            if scanned > self._inputs.max_scan_entries:
                raise CheckError(CheckFailure.INPUT_LIMIT)
            children: list[RepositoryPath] = []
            for entry in entries:
                if _excluded(entry.path):
                    continue
                if entry.kind is WorkspaceEntryKind.DIRECTORY:
                    children.append(entry.path)
                elif _included(entry.path):
                    _add(entry.path)
            pending.extend(sorted(children, key=lambda path: path.value, reverse=True))
        return tuple(selected[name] for name in sorted(selected))

    def _require_targets(
        self, request: CheckRequest, files: tuple[RepositoryText, ...]
    ) -> None:
        names = [item.path for item in files]
        roots = [root.value for root in self._inputs.roots]
        for target in request.targets:
            value = target.value
            if _excluded(target):
                raise WorkspaceError(WorkspaceFailure.EXCLUDED)
            if value in names:
                continue
            if any(_within(value, root) for root in roots) and any(
                name.startswith(value + "/") for name in names
            ):
                continue
            # Absent, excluded, unselectable or outside the operator input policy.
            raise WorkspaceError(WorkspaceFailure.EXCLUDED)

    def check(self, request: CheckRequest) -> CheckResult:
        if type(request) is not CheckRequest:
            raise TypeError("check requires CheckRequest")
        self._check_cancelled()
        files = self._select()
        self._require_targets(request, files)
        specification = RepositoryText(
            _SPEC,
            json.dumps(
                {
                    "tool": _tool(request.kind),
                    "arguments": _arguments(request.kind, "/dev/null"),
                    "targets": [target.value for target in request.targets],
                    "timeout": self._policy.timeout_seconds,
                    "max_output": self._policy.max_output_bytes,
                },
                ensure_ascii=False,
            ),
        )
        try:
            sandbox_request = SandboxRequest(_RUNNER, (*files, specification))
        except ValueError as error:
            raise CheckError(CheckFailure.INPUT_LIMIT) from error
        self._check_cancelled()
        try:
            result = self._sandbox.execute(sandbox_request, self._cancellation)
        except SandboxError as error:
            raise CheckError(_mapped(error.reason)) from error
        return _interpret(request, result.stdout, result.exit_code, self._policy)
