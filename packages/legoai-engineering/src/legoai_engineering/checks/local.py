"""Known checks for trusted workspaces; NOT safe untrusted-code execution."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from legoai_engineering.checks._commands import _arguments, _tool
from legoai_engineering.checks._process import _capture
from legoai_engineering.checks.values import (
    CheckPolicy,
    CheckRequest,
    CheckResult,
)
from legoai_engineering.repository.errors import WorkspaceError, WorkspaceFailure
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy


@dataclass(frozen=True, slots=True)
class LocalCheckTools:
    """Trusted host configuration; no discovery or executable access at construction.

    The host provisions authentic tools. Checking the filename is not attestation.
    Missing tools are detected only when their operation is explicitly invoked.
    """

    pytest: Path = field(repr=False)
    ruff: Path = field(repr=False)
    mypy: Path = field(repr=False)

    def __post_init__(self) -> None:
        for name, path in (
            ("pytest", self.pytest),
            ("ruff", self.ruff),
            ("mypy", self.mypy),
        ):
            if type(path) is not type(Path()):
                raise TypeError("check executable requires a native Path")
            if (
                not path.is_absolute()
                or ".." in path.parts
                or path.drive.startswith("\\\\")
            ):
                raise ValueError("check executable requires an absolute local path")
            expected = name + (".exe" if os.name == "nt" else "")
            if path.name != expected:
                raise ValueError("check executable must have its known tool filename")


class LocalEngineeringChecks:
    """Inert binding; check validates explicit targets through the public M2 API."""

    __slots__ = ("_root", "_tools", "_policy")

    def __init__(
        self, root: LocalWorkspaceRoot, tools: LocalCheckTools, policy: CheckPolicy
    ) -> None:
        if type(root) is not LocalWorkspaceRoot or type(tools) is not LocalCheckTools:
            raise TypeError("checks require LocalWorkspaceRoot and LocalCheckTools")
        if type(policy) is not CheckPolicy:
            raise TypeError("checks require CheckPolicy")
        self._root = root
        self._tools = tools
        self._policy = policy

    def check(self, request: CheckRequest) -> CheckResult:
        if type(request) is not CheckRequest:
            raise TypeError("check requires CheckRequest")
        workspace = LocalRepositoryWorkspace(
            self._root,
            WorkspacePolicy(262_144, 65_536, 4096, 32, (".git", ".venv")),
        )
        targets: list[str] = []
        for target in request.targets:
            if any(
                part.casefold() in {".git", ".venv"} for part in target.value.split("/")
            ):
                raise WorkspaceError(WorkspaceFailure.EXCLUDED)
            prefix = target.value.rpartition("/")[0]
            parent = RepositoryPath(prefix) if prefix else None
            entries = workspace.list_entries(parent)
            if not any(entry.path == target for entry in entries):
                raise WorkspaceError(WorkspaceFailure.MISSING)
            # Absolute argv also neutralizes option-like names and @argfiles.
            targets.append(str(self._root.path / target.value))
        tool = _tool(request.kind)
        executable = (
            self._tools.pytest
            if tool == "pytest"
            else self._tools.mypy
            if tool == "mypy"
            else self._tools.ruff
        )
        arguments = _arguments(request.kind, os.devnull)
        code, stdout, stderr = _capture(
            executable, [*arguments, "--", *targets], self._root.path, self._policy
        )
        return CheckResult(request.kind, code, stdout, stderr)
