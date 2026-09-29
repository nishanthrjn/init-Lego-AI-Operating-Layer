"""ForgeAI-1 validation: single repository task worker over public LegoAI.

Run from the repository root (Windows, Docker Desktop Linux engine, context
desktop-linux, with the CR-2a PYTHON_CHECKS image already built locally):

    uv run python .\\validate_forgeai_1.py

Offline: the model is a deterministic replay contribution; checks run in the
real Docker sandbox on the recorded image. Nothing is built into an image or
pulled. Every pytest phase uses a fresh --basetemp. Streams output, stops at
the first failed phase and exits non-zero on failure.
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
SELF = ROOT / "validate_forgeai_1.py"
IMAGE = "sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df"
SOURCES = ["src", "tests", "demo.py"]
WORKER = "tests/test_worker.py"


def worker(*names: str) -> list[str]:
    return [f"{WORKER}::{name}" for name in names]


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
    with tempfile.TemporaryDirectory(prefix="forgeai-1-") as temporary:
        base = Path(temporary)

        def run(
            name: str,
            command: list[str],
            cwd: Path = ROOT,
            env: dict[str, str] = environment,
        ) -> None:
            nonlocal phase
            phase = name
            print("\n[PHASE] " + name, flush=True)
            print(subprocess.list2cmdline(command), flush=True)
            subprocess.run(command, cwd=cwd, env=env, check=True, shell=False)
            completed.append(name)

        def project(name: str, cwd: Path, *arguments: str) -> None:
            assert uv is not None
            run(
                name,
                [uv, "run", "--locked", "--no-sync", *arguments],
                cwd=cwd,
                env=project_environment,
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
            phase = "1 environment / package sync"
            for tool, value in (("uv", uv), ("git", git), ("docker", docker)):
                if value is None:
                    raise RuntimeError(f"{tool} is required on PATH")
            if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
                raise RuntimeError(
                    "run through the locked root environment: "
                    "uv run python .\\validate_forgeai_1.py"
                )
            if os.name != "nt":
                raise RuntimeError("reference scope is Windows + Docker Desktop Linux")
            assert uv is not None and git is not None and docker is not None
            run(
                "1 environment: qualified image presence",
                [
                    docker,
                    "--context",
                    "desktop-linux",
                    "image",
                    "inspect",
                    "--format",
                    "{{.Id}} {{.Os}}/{{.Architecture}}",
                    IMAGE,
                ],
            )
            run(
                "1b ForgeAI environment (locked sync)",
                [uv, "sync", "--locked"],
                cwd=FORGEAI,
                env=project_environment,
            )
            run(
                "1c engineering environment (locked sync, analyst extra)",
                [uv, "sync", "--locked", "--extra", "analyst"],
                cwd=ENGINEERING,
                env=project_environment,
            )
            project(
                "2 typing",
                FORGEAI,
                "python",
                "-m",
                "mypy",
                "--cache-dir",
                str(base / "mypy"),
                *SOURCES,
            )
            run(
                "2b typing (validator)",
                [python, "-m", "mypy", "--cache-dir", str(base / "mypy-v"), str(SELF)],
            )
            project(
                "3 Ruff lint",
                FORGEAI,
                "python",
                "-m",
                "ruff",
                "check",
                "--no-cache",
                *SOURCES,
            )
            run("3b Ruff lint (validator)", [python, "-m", "ruff", "check", str(SELF)])
            project(
                "4 Ruff format",
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
                "4b Ruff format (validator)",
                [python, "-m", "ruff", "format", "--check", str(SELF)],
            )
            tests("5 domain / value contracts", "tests/test_domain.py")
            tests(
                "6 clean-start gate",
                *worker(
                    "test_dirty_start_is_rejected_before_model",
                    "test_non_repository_and_unborn_head_are_rejected",
                ),
            )
            tests(
                "7 fake model / CodingAgent",
                *worker(
                    "test_success_applies_once_checks_in_order_and_records_state",
                    "test_invalid_model_output_stops_before_any_write",
                    "test_model_denied_is_model_failure_without_provider_call",
                    "test_read_denial_and_out_of_scope_targets_are_rejected",
                    "test_oversized_target_is_evidence_unavailable",
                ),
            )
            tests(
                "8 authorized mutation",
                *worker(
                    "test_denied_mutation_writes_nothing_and_runs_no_checks",
                    "test_conflict_and_partial_apply_are_reported_without_retry",
                    "test_real_stale_precondition_is_a_conflict",
                ),
            )
            tests(
                "9 check orchestration",
                *worker(
                    "test_check_finding_fails_task_but_keeps_changes_and_runs_all",
                    "test_denied_check_starts_no_sandbox",
                ),
            )
            tests(
                "10 check infrastructure failure paths",
                *worker("test_sandbox_infrastructure_failure_is_check_error"),
            )
            tests(
                "11 final Git state / evidence",
                *worker("test_final_state_integrity"),
            )
            tests(
                "12 run isolation / same-workspace policy",
                *worker(
                    "test_two_workspaces_run_concurrently_and_stay_isolated",
                    "test_same_workspace_second_run_is_refused",
                    "test_guard_is_released_after_every_run",
                ),
            )
            tests("13 architecture / import boundaries", "tests/test_architecture.py")
            tests(
                "14 full offline end-to-end fixture task (real sandbox)",
                "tests/test_end_to_end.py::test_fixture_task_succeeds_in_the_real_sandbox",
            )
            tests(
                "15 real Docker check finding / unavailable paths",
                "tests/test_end_to_end.py::test_sandbox_finding_fails_the_task",
                "tests/test_end_to_end.py::test_missing_docker_is_check_infrastructure_error",
            )
            tests(
                "16 provider / config substitution and CLI",
                *worker("test_binding_switch_is_configuration_only"),
                "tests/test_cli.py",
            )
            tests("17 clean-install package", "tests/test_clean_install.py")
            tests(
                "18 affected LegoAI engineering regressions",
                "tests/test_authorized_effects.py",
                "tests/test_consumer_readiness.py",
                "tests/test_architecture.py",
                cwd=ENGINEERING,
            )
            project("19 README demo execution", FORGEAI, "python", "demo.py")
            run("20 git diff --check", [git, "diff", "--check"])
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
        "FORGEAI-1 LOCAL VALIDATION PASSED - replay model, real sandbox checks, "
        "public LegoAI only; no build, pull or network"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
