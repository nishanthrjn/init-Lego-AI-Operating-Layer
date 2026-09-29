"""CR-2a validation: qualified Python engineering-check sandbox image.

Run from the repository root in the reference environment (Windows, Docker
Desktop Linux engine, context desktop-linux):

    uv run python .\\validate_consumer_readiness_cr2a.py

Part A is static/deterministic (no Docker). Part B is REAL Docker
qualification: it BUILDS the image from
packages/legoai-engineering/sandbox-images/python-checks (operator build step;
the build needs network to download the hash-locked wheels), captures the exact
local image ID and qualifies that ID. Sandbox runtime stays network=none.

The candidate ID is passed to the qualification tests only through
LEGOAI_SANDBOX_CHECKS_IMAGE; production configuration stays fail-closed until
the qualified ID is reviewed and recorded. Streams output, stops at the first
failed phase and exits non-zero on failure.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINEERING = ROOT / "packages" / "legoai-engineering"
IMAGE_CONTEXT = ENGINEERING / "sandbox-images" / "python-checks"
SELF = ROOT / "validate_consumer_readiness_cr2a.py"
BASE = "python@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56"
CANDIDATE_TAG = "legoai-python-checks:candidate"
CHECKS_TESTS = "tests/test_sandbox_checks_docker.py"
ENGINEERING_FILES = [
    "src/legoai_engineering/sandbox/docker.py",
    "tests/test_sandbox.py",
    "tests/test_sandbox_checks_docker.py",
    "tests/test_package_install.py",
    "tests/test_architecture.py",
]


def main() -> int:
    uv = shutil.which("uv")
    git = shutil.which("git")
    docker = shutil.which("docker")
    python = sys.executable
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    engineering_environment = environment.copy()
    engineering_environment.pop("VIRTUAL_ENV", None)
    completed: list[str] = []
    phase = "environment"
    candidate = ""
    with tempfile.TemporaryDirectory(prefix="legoai-cr2a-") as temporary:
        base = Path(temporary)

        def run(
            name: str,
            command: list[str],
            cwd: Path = ROOT,
            env: dict[str, str] = environment,
            capture: bool = False,
        ) -> str:
            nonlocal phase
            phase = name
            print("\n[PHASE] " + name, flush=True)
            print(subprocess.list2cmdline(command), flush=True)
            result = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                check=True,
                shell=False,
                capture_output=capture,
                text=capture,
            )
            completed.append(name)
            if capture:
                print(result.stdout, end="", flush=True)
                return str(result.stdout)
            return ""

        def engineering(name: str, *arguments: str) -> None:
            assert uv is not None
            run(
                name,
                [uv, "run", "--locked", "--no-sync", *arguments],
                cwd=ENGINEERING,
                env=engineering_environment,
            )

        def tests(name: str, *targets: str, show: bool = False) -> None:
            slug = name.split()[0]
            engineering(
                name,
                "python",
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(base / slug),
                "-q",
                "-rs",
                *(["-s"] if show else []),
                *targets,
            )

        try:
            phase = "A1 environment / toolchain"
            for tool, value in (("uv", uv), ("git", git), ("docker", docker)):
                if value is None:
                    raise RuntimeError(f"{tool} is required on PATH")
            if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
                raise RuntimeError(
                    "run through the locked root environment: "
                    "uv run python .\\validate_consumer_readiness_cr2a.py"
                )
            if os.name != "nt":
                raise RuntimeError("reference scope is Windows + Docker Desktop Linux")
            assert uv is not None and git is not None and docker is not None
            run(
                "A1 environment / toolchain",
                [
                    python,
                    "-c",
                    "import subprocess, sys; assert sys.version_info[:2] == (3, 14);"
                    f" print(sys.version); subprocess.run([{uv!r}, '--version'],"
                    " check=True)",
                ],
            )
            run(
                "A2 engineering environment (locked sync, analyst extra)",
                [uv, "sync", "--locked", "--extra", "analyst"],
                cwd=ENGINEERING,
                env=engineering_environment,
            )
            engineering(
                "A3 typing (engineering)",
                "python",
                "-m",
                "mypy",
                "--cache-dir",
                str(base / "mypy"),
                "src",
                "tests",
                "examples",
            )
            run(
                "A3b typing (validator)",
                [python, "-m", "mypy", "--cache-dir", str(base / "mypy-v"), str(SELF)],
            )
            engineering(
                "A4 Ruff lint (CR-2a files)",
                "python",
                "-m",
                "ruff",
                "check",
                "--no-cache",
                *ENGINEERING_FILES,
            )
            engineering(
                "A5 Ruff format (CR-2a files)",
                "python",
                "-m",
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *ENGINEERING_FILES,
            )
            run(
                "A5b Ruff lint/format (validator)",
                [python, "-m", "ruff", "check", "--no-cache", str(SELF)],
            )
            run(
                "A5c Ruff format (validator)",
                [python, "-m", "ruff", "format", "--check", "--no-cache", str(SELF)],
            )
            tests(
                "A6 deterministic image-profile tests (no Docker)",
                "tests/test_sandbox.py",
            )
            tests(
                "A7 architecture / package inventory",
                "tests/test_architecture.py",
                "tests/test_package_install.py",
            )

            print(
                "\n========== PART B: REAL DOCKER QUALIFICATION ==========", flush=True
            )
            run(
                "B1 Docker availability (desktop-linux, Linux engine)",
                [
                    docker,
                    "--context",
                    "desktop-linux",
                    "info",
                    "--format",
                    "{{.OSType}}/{{.Architecture}} cgroup={{.CgroupVersion}}",
                ],
            )
            run(
                "B2 pinned base image present",
                [
                    docker,
                    "--context",
                    "desktop-linux",
                    "image",
                    "inspect",
                    "--format",
                    "{{.Os}}/{{.Architecture}} {{json .RepoTags}}",
                    BASE,
                ],
            )
            run(
                "B3 build python-checks image (operator build; network for wheels)",
                [
                    docker,
                    "--context",
                    "desktop-linux",
                    "build",
                    "--platform",
                    "linux/amd64",
                    "--tag",
                    CANDIDATE_TAG,
                    str(IMAGE_CONTEXT),
                ],
            )
            candidate = run(
                "B4 capture exact image ID",
                [
                    docker,
                    "--context",
                    "desktop-linux",
                    "image",
                    "inspect",
                    "--format",
                    "{{.Id}}",
                    CANDIDATE_TAG,
                ],
                capture=True,
            ).strip()
            if not candidate.startswith("sha256:") or len(candidate) != 71:
                raise RuntimeError(f"unexpected image ID {candidate!r}")
            engineering_environment["LEGOAI_SANDBOX_CHECKS_IMAGE"] = candidate
            tests(
                "B5 tool versions and image contents",
                f"{CHECKS_TESTS}::test_toolchain_versions_and_contents",
                show=True,
            )
            tests(
                "B6 runtime confinement (network, secrets, mounts, privilege, limits)",
                f"{CHECKS_TESTS}::test_checks_image_keeps_m6_confinement",
            )
            tests(
                "B7 pytest / Ruff / mypy outcomes and memory evidence",
                f"{CHECKS_TESTS}::test_tool_outcomes_within_fixed_memory",
                show=True,
            )
            tests(
                "B8 timeout, output limit, PID limit, OOM, cleanup",
                f"{CHECKS_TESTS}::test_timeout_is_enforced",
                f"{CHECKS_TESTS}::test_output_limit_is_enforced",
                f"{CHECKS_TESTS}::test_pid_limit_applies_to_tool_processes",
                f"{CHECKS_TESTS}::test_memory_limit_is_never_silent_success",
                show=True,
            )
            tests(
                "B9 existing stdlib sandbox regression (M6)",
                "tests/test_sandbox_docker.py",
            )
            run("B10 git diff --check", [git, "diff", "--check"])
        except Exception as error:
            for item in completed:
                print("PASS " + item)
            print(f"FAIL {phase}; later phases NOT RUN")
            if candidate:
                print(f"candidate image ID (not qualified): {candidate}")
            if not isinstance(error, subprocess.CalledProcessError):
                print(f"reason: {error}")
                return 1
            return error.returncode if error.returncode > 0 else 1
    for item in completed:
        print("PASS " + item)
    print(f"\nQUALIFIED CANDIDATE IMAGE ID: {candidate}")
    print(
        "CR-2a DOCKER QUALIFICATION PASSED for this exact image ID. Record it in "
        "sandbox.docker._approved_image only after review; a rebuild needs "
        "requalification."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
