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
BASE = "3993320"  # last commit before the v0.1 product slices
# Scope audits describe the original slice, not every subsequent platform change.
# All typing, lint, tests and demos below still exercise the current checkout.
SLICE_END = "03d2c6eda0e74793f68720f36b0a5033edf7e2e1"  # read-only context slice
IMAGE = "sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df"
SOURCES = ["src", "tests", "demo.py"]
ENGINEERING_PREFIX = "packages/legoai-engineering/"
# Engineering seams added by v0.1 slices: Docker readiness, safe
# rejected-output diagnostics for the Coding Agent and Reviewer, then
# operator-selected read-only Coding Agent context.
READINESS = [
    "src/legoai_engineering/sandbox/docker.py",
    "tests/test_sandbox_readiness.py",
    "src/legoai_engineering/agent_output.py",
    "src/legoai_engineering/coding/api.py",
    "src/legoai_engineering/coding/values.py",
    "src/legoai_engineering/reviewer/api.py",
    "src/legoai_engineering/reviewer/values.py",
    "tests/test_agent_output.py",
    "src/legoai_engineering/coding/authorized.py",
    "src/legoai_engineering/coding/definition.py",
    "tests/test_coding_context.py",
    "tests/test_coding_prompt.py",
]
ENGINEERING_ALLOWED = {
    ENGINEERING_PREFIX + name
    for name in (
        *READINESS,
        "tests/test_sandbox_docker.py",
        "tests/test_architecture.py",
    )
}


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
                "2 historical v0.1 scope: no LegoAI Core source change",
                [git, "diff", "--exit-code", "--stat", BASE, SLICE_END, "--", "src"],
            )
            phase = "2b historical v0.1 scope: Engineering readiness, diagnostics and context seams"
            changed = set(
                subprocess.run(
                    [git, "diff", "--name-only", BASE, SLICE_END, "--", "packages"],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.split()
            )
            if changed - ENGINEERING_ALLOWED:
                raise RuntimeError(
                    "unexpected Engineering change: "
                    + ", ".join(sorted(changed - ENGINEERING_ALLOWED))
                )
            print("\n[PHASE] " + phase, flush=True)
            completed.append(phase)
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
                "6 v0.1 product: CLI, approval, readiness refusal, result, exclusion",
                "tests/test_v01_product.py",
            )
            tests(
                "6b v0.1 supervision: exact patch preview, invalid-output diagnostics",
                "tests/test_v01_supervision.py",
            )
            tests(
                "6c v0.1 check-feedback bounded rework (incl. real-Docker B011 regression)",
                "tests/test_v01_check_rework.py",
            )
            tests(
                "6d v0.1 read-only Coding context: disclosure is never write "
                "scope (incl. real-Docker create-only regression)",
                "tests/test_v01_context.py",
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
                "10b Engineering sandbox readiness (offline) and sandbox regressions",
                "tests/test_sandbox_readiness.py",
                "tests/test_sandbox.py",
                "tests/test_architecture.py",
                cwd=ENGINEERING,
            )
            tests(
                "10c real Docker Desktop readiness (metadata only)",
                "tests/test_sandbox_docker.py::test_real_checks_environment_is_ready",
                cwd=ENGINEERING,
            )
            project(
                "10d typing (Engineering seams)",
                ENGINEERING,
                "python",
                "-m",
                "mypy",
                "--cache-dir",
                str(base / "mypy-e"),
                *READINESS,
            )
            project(
                "10e Ruff lint (Engineering seams)",
                ENGINEERING,
                "python",
                "-m",
                "ruff",
                "check",
                "--no-cache",
                *READINESS,
            )
            project(
                "10f Ruff format (Engineering seams)",
                ENGINEERING,
                "python",
                "-m",
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *READINESS,
            )
            tests(
                "11 Engineering Coding context, Coding/Reviewer diagnostics "
                "and regressions",
                "tests/test_coding_context.py",
                "tests/test_agent_output.py",
                "tests/test_coding.py",
                "tests/test_coding_m4.py",
                "tests/test_coding_prompt.py",
                "tests/test_reviewer.py",
                "tests/test_json_document.py",
                "tests/test_consumer_readiness.py",
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
