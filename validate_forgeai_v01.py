"""ForgeAI v0.1 validation: supervised CLI with pre-mutation operator approval.

Run from the repository root (Windows, Docker Desktop Linux engine, context
desktop-linux, with the CR-2a PYTHON_CHECKS image already built locally):

    uv run python .\\validate_forgeai_v01.py

Offline: every model call uses deterministic replay outputs; checks run in the
real Docker sandbox on the recorded image. No live model, build, pull or
network. The demo phases answer the approval prompt with an explicit "y" on
stdin. Stops at the first failed phase and exits non-zero on failure.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGEAI = ROOT / "examples" / "forgeai"
ENGINEERING = ROOT / "packages" / "legoai-engineering"
SELF = ROOT / "validate_forgeai_v01.py"
BASE = "3993320"  # last commit before the v0.1 product slice
IMAGE = "sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df"
SOURCES = ["src", "tests", "demo.py"]


def main() -> int:
    uv = shutil.which("uv")
    git = shutil.which("git")
    docker = shutil.which("docker")
    python = sys.executable
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    project_environment = environment.copy()
    project_environment.pop("VIRTUAL_ENV", None)
    project_environment.pop("LEGOAI_SANDBOX_CHECKS_IMAGE", None)
    completed: list[str] = []
    phase = "environment"
    with tempfile.TemporaryDirectory(prefix="forgeai-v01-") as temporary:
        base = Path(temporary)

        def run(
            name: str,
            command: list[str],
            cwd: Path = ROOT,
            env: dict[str, str] = environment,
            answers: str | None = None,
        ) -> None:
            nonlocal phase
            phase = name
            print("\n[PHASE] " + name, flush=True)
            print(subprocess.list2cmdline(command), flush=True)
            subprocess.run(
                command,
                cwd=cwd,
                env=env,
                check=True,
                shell=False,
                input=answers,
                text=answers is not None,
            )
            completed.append(name)

        def project(
            name: str, cwd: Path, *arguments: str, answers: str | None = None
        ) -> None:
            assert uv is not None
            run(
                name,
                [uv, "run", "--locked", "--no-sync", *arguments],
                cwd=cwd,
                env=project_environment,
                answers=answers,
            )

        def tests(name: str, *targets: str, cwd: Path = FORGEAI) -> None:
            project(
                name,
                cwd,
                "python",
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(base / name.split()[0]),
                "-q",
                "-rs",
                *targets,
            )

        try:
            phase = "1 environment"
            for tool, value in (("uv", uv), ("git", git), ("docker", docker)):
                if value is None:
                    raise RuntimeError(f"{tool} is required on PATH")
            if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
                raise RuntimeError(
                    "run through the locked root environment: "
                    "uv run python .\\validate_forgeai_v01.py"
                )
            if os.name != "nt":
                raise RuntimeError("reference scope is Windows + Docker Desktop Linux")
            assert uv is not None and git is not None and docker is not None
            run(
                "1 qualified checks image present",
                [docker, "--context", "desktop-linux", "image", "inspect", IMAGE],
            )
            run(
                "1b ForgeAI environment (locked sync)",
                [uv, "sync", "--locked"],
                cwd=FORGEAI,
                env=project_environment,
            )
            run(
                "2 no LegoAI or Engineering source change in this slice",
                [git, "diff", "--exit-code", "--stat", BASE, "--", "src", "packages"],
            )
            project(
                "3 typing",
                FORGEAI,
                "python",
                "-m",
                "mypy",
                "--cache-dir",
                str(base / "mypy"),
                *SOURCES,
            )
            run(
                "3b typing (validator)",
                [python, "-m", "mypy", "--cache-dir", str(base / "mypy-v"), str(SELF)],
            )
            project(
                "4 Ruff lint",
                FORGEAI,
                "python",
                "-m",
                "ruff",
                "check",
                "--no-cache",
                *SOURCES,
            )
            run("4b Ruff lint (validator)", [python, "-m", "ruff", "check", str(SELF)])
            project(
                "5 Ruff format",
                FORGEAI,
                "python",
                "-m",
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *SOURCES,
            )
            run(
                "5b Ruff format (validator)",
                [python, "-m", "ruff", "format", "--check", str(SELF)],
            )
            tests(
                "6 v0.1 product: CLI, approval boundary, final result, exclusion",
                "tests/test_v01_product.py",
            )
            tests("7 architecture / import boundaries", "tests/test_architecture.py")
            tests(
                "8 ForgeAI-1/2/3 regressions",
                "tests/test_domain.py",
                "tests/test_worker.py",
                "tests/test_review.py",
                "tests/test_rework.py",
                "tests/test_cli.py",
            )
            tests("9 real-Docker end-to-end", "tests/test_end_to_end.py")
            tests(
                "10 clean install with explicit approval", "tests/test_clean_install.py"
            )
            tests(
                "11 Engineering Coding/Reviewer regressions",
                "tests/test_coding.py",
                "tests/test_reviewer.py",
                cwd=ENGINEERING,
            )
            project(
                "12 demo: approve, review #1 accepts",
                FORGEAI,
                "python",
                "demo.py",
                answers="y\n",
            )
            project(
                "12b demo: approve both proposals, one bounded rework",
                FORGEAI,
                "python",
                "demo.py",
                "rework",
                answers="y\ny\n",
            )
            run("13 git diff --check", [git, "diff", "--check"])
        except Exception as error:
            for item in completed:
                print("PASS " + item)
            print(f"FAIL {phase}; later phases NOT RUN")
            if not isinstance(error, subprocess.CalledProcessError):
                print(f"reason: {error}")
                return 1
            return error.returncode if error.returncode > 0 else 1
    for item in completed:
        print("PASS " + item)
    print(
        "FORGEAI v0.1 LOCAL VALIDATION PASSED - replay models, explicit approval, "
        "real sandbox checks; no live model, build, pull or network"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
