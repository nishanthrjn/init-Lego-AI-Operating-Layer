"""The one private fixed-command table shared by every EngineeringCheckPort adapter.

Host (M5) and sandbox (CR-2b) execution derive tool and options only from the
closed CheckKind here, so their semantics cannot drift. Callers never supply
executables, argv, environment or working directories.
"""

from legoai_engineering.checks.values import CheckKind


def _tool(kind: CheckKind) -> str:
    """The fixed tool name for one CheckKind: pytest, ruff or mypy."""
    if kind is CheckKind.PYTEST:
        return "pytest"
    if kind is CheckKind.MYPY:
        return "mypy"
    return "ruff"


def _arguments(kind: CheckKind, null_device: str) -> list[str]:
    """Fixed options placed before `--` and the absolute targets.

    `null_device` is the executing platform's null device, used only to disable
    mypy's persistent cache (host `os.devnull`, container `/dev/null`).
    """
    if kind is CheckKind.PYTEST:
        return ["-q", "-o", "addopts=", "-p", "no:cacheprovider"]
    if kind is CheckKind.RUFF_CHECK:
        return ["check", "--no-fix", "--no-fix-only", "--no-cache"]
    if kind is CheckKind.RUFF_FORMAT_CHECK:
        return ["format", "--check", "--no-cache"]
    return ["--no-incremental", "--cache-dir", null_device]
