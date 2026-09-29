"""Hidden acceptance tests: an evaluation-owned oracle run after ForgeAI.

The evaluated repository is never modified. An in-memory overlay presents the
repository plus a virtual `acceptance/` directory holding the hidden tests to
the existing SandboxedEngineeringChecks adapter, which copies them into one
ephemeral sandbox execution. Hidden tests never run on the host.
"""

from dataclasses import dataclass
from enum import Enum

from legoai_engineering.checks.errors import CheckError
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
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.ports import RepositoryWorkspacePort
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import (
    RepositoryPath,
    WorkspaceEntry,
    WorkspaceEntryKind,
)
from legoai_engineering.sandbox.ports import SandboxExecutionPort

from forgeai_eval.fixtures import HIDDEN_ROOT


class HiddenOutcome(Enum):
    PASSED = "passed"
    FAILED = "failed"  # the hidden tests ran and did not pass
    ERROR = "error"  # the hidden tests could not complete (infrastructure)
    NOT_RUN = "not_run"  # ForgeAI applied no change, so nothing to evaluate


@dataclass(frozen=True, slots=True)
class HiddenResult:
    outcome: HiddenOutcome
    result: CheckResult | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        if (self.result is not None) != (
            self.outcome in {HiddenOutcome.PASSED, HiddenOutcome.FAILED}
        ):
            raise ValueError("hidden result must match its outcome")


class HiddenOverlay:
    """RepositoryWorkspacePort: repository plus virtual hidden-test files."""

    def __init__(self, inner: RepositoryWorkspacePort, files: dict[str, str]) -> None:
        if any(
            entry.path.value.casefold() == HIDDEN_ROOT
            for entry in inner.list_entries(None)
        ):
            raise ValueError(f"evaluated repository already contains {HIDDEN_ROOT}/")
        if not files or any(not p.startswith(HIDDEN_ROOT + "/") for p in files):
            raise ValueError("hidden files must live under the virtual root")
        self.inner = inner
        self.files = dict(files)

    def list_entries(
        self, directory: RepositoryPath | None
    ) -> tuple[WorkspaceEntry, ...]:
        if directory is None:
            entries = (
                *self.inner.list_entries(None),
                WorkspaceEntry(
                    RepositoryPath(HIDDEN_ROOT), WorkspaceEntryKind.DIRECTORY
                ),
            )
            return tuple(sorted(entries, key=lambda entry: entry.path.value))
        if directory.value == HIDDEN_ROOT:
            return tuple(
                WorkspaceEntry(RepositoryPath(path), WorkspaceEntryKind.FILE)
                for path in sorted(self.files)
            )
        return self.inner.list_entries(directory)

    def read_text(self, path: RepositoryPath) -> RepositoryText:
        if path.value in self.files:
            return RepositoryText(path.value, self.files[path.value])
        return self.inner.read_text(path)


def run_hidden(
    workspace: RepositoryWorkspacePort,
    files: dict[str, str],
    sandbox: SandboxExecutionPort,
    policy: CheckPolicy,
) -> HiddenResult:
    """Run the hidden tests once in the sandbox; never retried."""
    checks = SandboxedEngineeringChecks(
        HiddenOverlay(workspace, files),
        sandbox,
        CheckInputPolicy(
            (RepositoryPath("src"), RepositoryPath(HIDDEN_ROOT)),
            (RepositoryPath("pyproject.toml"),),
        ),
        policy,
    )
    try:
        result = checks.check(
            CheckRequest(CheckKind.PYTEST, (RepositoryPath(HIDDEN_ROOT),))
        )
    except CheckError as error:
        return HiddenResult(HiddenOutcome.ERROR, error=error.reason.name.lower())
    except WorkspaceError as error:
        return HiddenResult(
            HiddenOutcome.ERROR, error="workspace_" + error.reason.name.lower()
        )
    outcome = (
        HiddenOutcome.PASSED
        if result.outcome is CheckOutcome.PASSED
        else HiddenOutcome.FAILED
    )
    return HiddenResult(outcome, result)
