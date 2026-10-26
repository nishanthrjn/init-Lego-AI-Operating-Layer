"""ForgeAI offline demonstration: the reviewed fixture task end to end.

Test-harness code, not part of the ForgeAI package. It provisions a fresh
committed fixture repository (ForgeAI itself never creates, commits or
cleans repositories), then runs the `forgeai` CLI with the deterministic
replay model (one Coding Agent output, one reviewer output). Checks run in
the real Docker sandbox. Each proposal is shown and needs your explicit "y"
(stdin) before anything is written. Usage:

    python demo.py           # review #1 accepts (2 model calls)
    python demo.py rework    # review #1 requires changes; one rework (4 calls)
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from forgeai.cli import main as forgeai

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "stock_task"
OBJECTIVE = (
    "Add input validation to inventory.stock.reserve: reject negative available "
    "stock, non-positive requests and requests above the available stock with "
    "ValueError, and update its tests."
)
TARGETS = ("src/inventory/stock.py", "tests/test_stock.py")


def git_environment() -> dict[str, str]:
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    }
    if os.name == "nt":
        environment["SystemRoot"] = os.environ["SystemRoot"]
    return environment


def git(repository: Path, executable: Path, *arguments: str) -> None:
    subprocess.run(
        [str(executable), *arguments],
        cwd=repository,
        env=git_environment(),
        check=True,
        capture_output=True,
        timeout=30,
        shell=False,
    )


def create_repository(target: Path, executable: Path) -> Path:
    """Copy the fixture into `target` and commit it; returns the root."""
    shutil.copytree(FIXTURE / "repository", target)
    git(target, executable, "init", "--initial-branch=main", "--template=")
    git(target, executable, "add", "--all")
    git(
        target,
        executable,
        "-c",
        "user.name=ForgeAI fixture",
        "-c",
        "user.email=fixture@forgeai.invalid",
        "commit",
        "--quiet",
        "--no-gpg-sign",
        "-m",
        "fixture",
    )
    return target


SCENARIOS = {
    "accept": ("proposal.json", "review_accept.json"),
    "rework": (
        "proposal.json",
        "review_changes_required.json",
        "proposal_rework.json",
        "review_accept.json",
    ),
}


def main(argv: list[str] | None = None) -> int:
    scenario = (argv if argv is not None else sys.argv[1:]) or ["accept"]
    if scenario[0] not in SCENARIOS:
        raise SystemExit("usage: python demo.py [accept|rework]")
    executable = shutil.which("git")
    if executable is None:
        raise SystemExit("Git is required")
    with TemporaryDirectory(prefix="forgeai-demo-") as temporary:
        repository = create_repository(Path(temporary) / "repo", Path(executable))
        arguments = ["run", "--repo", str(repository), "--task", OBJECTIVE]
        arguments += ["--binding", "replay"]
        # Recorded outputs in strict call order (Coding Agent, reviewer, ...).
        for name in SCENARIOS[scenario[0]]:
            arguments += ["--replay", str(FIXTURE / name)]
        for target in TARGETS:
            arguments += ["--target", target]
        return forgeai(arguments + scenario[1:])


if __name__ == "__main__":
    sys.exit(main())
