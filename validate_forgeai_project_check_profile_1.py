"""PROJECT v1 qualification: one labelled registry acquisition, offline checks.

Run: uv run python .\validate_forgeai_project_check_profile_1.py
Windows + Docker Desktop Linux, local qualified checks image, uv 0.11.19.
No live Model provider. Stops at first failure; historical validator unchanged.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINEERING = ROOT / "packages/legoai-engineering"
FORGEAI = ROOT / "examples/forgeai"
ENGINEERING_SCOPE = [
    "src/legoai_engineering/checks",
    "src/legoai_engineering/sandbox",
    "tests/test_check_preparation.py",
    "tests/test_check_preparation_docker.py",
    "tests/test_architecture.py",
]


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        print("FAIL: uv required")
        return 1
    phase = "prerequisites"

    def run(
        name: str, args: list[str], cwd: Path = ROOT, *, network: bool = False
    ) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + name, flush=True)
        environment = os.environ.copy()
        environment.pop("VIRTUAL_ENV", None)
        environment.pop("LEGOAI_QUALIFY_PROJECT_CHECKS", None)
        if network:
            environment["LEGOAI_QUALIFY_PROJECT_CHECKS"] = "1"
        subprocess.run(args, cwd=cwd, env=environment, check=True, shell=False)

    def project(name: str, cwd: Path, *args: str, network: bool = False) -> None:
        assert uv is not None
        run(
            name,
            [uv, "run", "--locked", "--no-sync", "python", *args],
            cwd,
            network=network,
        )

    try:
        run(
            "locked offline Engineering environment",
            [uv, "sync", "--locked", "--offline", "--extra", "analyst"],
            ENGINEERING,
        )
        run(
            "locked offline ForgeAI environment",
            [uv, "sync", "--locked", "--offline"],
            FORGEAI,
        )
        project(
            "preparation contracts/security and sandbox regressions (offline)",
            ENGINEERING,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_check_preparation.py",
            "tests/test_checks.py",
            "tests/test_checks_sandboxed.py",
            "tests/test_sandbox.py",
            "tests/test_sandbox_readiness.py",
            "tests/test_architecture.py",
        )
        project(
            "ForgeAI profile and pre-model failure ordering (offline)",
            FORGEAI,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_project_check_profile.py",
        )
        project(
            "ONE real Docker dependency acquisition (PyPI network); subsequent checks OFFLINE",
            ENGINEERING,
            "-m",
            "pytest",
            "-q",
            "-s",
            "-p",
            "no:cacheprovider",
            "tests/test_check_preparation_docker.py",
            network=True,
        )
        project(
            "Engineering prepared boundary typing",
            ENGINEERING,
            "-m",
            "mypy",
            "src/legoai_engineering/checks",
            "src/legoai_engineering/sandbox",
            "tests/test_check_preparation.py",
            "tests/test_check_preparation_docker.py",
        )
        project(
            "Engineering lint", ENGINEERING, "-m", "ruff", "check", *ENGINEERING_SCOPE
        )
        project(
            "Engineering formatting",
            ENGINEERING,
            "-m",
            "ruff",
            "format",
            "--check",
            *ENGINEERING_SCOPE,
        )
        run(
            "validator typing",
            [sys.executable, "-m", "mypy", str(Path(__file__).resolve())],
        )
        run(
            "validator lint",
            [sys.executable, "-m", "ruff", "check", str(Path(__file__).resolve())],
        )
        run(
            "validator formatting",
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                str(Path(__file__).resolve()),
            ],
        )
        run(
            "affected Core composition regressions",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/integration/composition/test_agent.py",
                "tests/integration/composition/test_local_host.py",
                "tests/integration/composition/test_model_selection.py",
            ],
        )
        run(
            "full historical ForgeAI v0.1 regression validator (current checkout)",
            [sys.executable, str(ROOT / "validate_forgeai_v01.py")],
        )
        run("diff whitespace", ["git", "diff", "--check"])
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"FAIL {phase}: {error}; later phases NOT RUN")
        return 1
    print(
        "PROJECT CHECK PROFILE LOCAL VALIDATION PASSED: explicit registry preparation, offline checks, no live models"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
