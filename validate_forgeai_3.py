"""ForgeAI-3 validation: bounded one-cycle rework after review CHANGES_REQUIRED.

Run from the repository root (Windows, Docker Desktop Linux engine, context
desktop-linux, with the CR-2a PYTHON_CHECKS image already built locally):

    uv run python .\\validate_forgeai_3.py

Offline: all model calls (coding-1, review-1, coding-2, review-2) use
deterministic replay outputs; checks run in the real Docker sandbox on the
recorded image. Nothing is built into an image or pulled. Every pytest phase
uses a fresh --basetemp. Streams output, stops at the first failed phase and
exits non-zero on failure.
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
SELF = ROOT / "validate_forgeai_3.py"
IMAGE = "sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df"
SOURCES = ["src", "tests", "demo.py"]


def select(module: str, *names: str) -> list[str]:
    return [f"tests/{module}.py::{name}" for name in names]


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
    with tempfile.TemporaryDirectory(prefix="forgeai-3-") as temporary:
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
                    "uv run python .\\validate_forgeai_3.py"
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
                "1c no LegoAI source change in this slice",
                [
                    git,
                    "diff",
                    "--exit-code",
                    "--stat",
                    "HEAD",
                    "--",
                    "src/legoai",
                    "packages",
                ],
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
            tests("5 ForgeAI-3 domain / evidence invariants", "tests/test_domain.py")
            tests(
                "6 rework-context rendering / bounds / scope",
                *select(
                    "test_rework",
                    "test_rework_prompt_carries_findings_as_data_without_git",
                    "test_oversized_findings_fail_rework_input_without_a_third_call",
                    "test_rework_cannot_expand_scope",
                ),
            )
            tests(
                "7 review-1 gating (no rework unless CHANGES_REQUIRED)",
                *select(
                    "test_review",
                    "test_review_runs_last_once_and_accept_succeeds",
                    "test_no_review_when_proposal_invalid",
                    "test_no_review_when_mutation_denied",
                    "test_no_review_when_checks_fail",
                    "test_no_review_when_final_git_integrity_fails",
                ),
                *select(
                    "test_rework",
                    "test_no_rework_after_other_first_review_outcomes",
                    "test_no_rework_after_deterministic_failure",
                ),
            )
            tests(
                "8 no-rework ACCEPT path",
                *select("test_rework", "test_first_review_accept_needs_no_rework"),
                *select(
                    "test_worker",
                    "test_success_applies_once_checks_in_order_and_records_state",
                ),
            )
            tests(
                "9 CHANGES_REQUIRED -> rework path",
                *select(
                    "test_rework",
                    "test_rework_then_accept_succeeds_within_exact_ceilings",
                    "test_rework_reasons_over_current_content",
                ),
            )
            tests(
                "10 terminal second-review paths",
                *select("test_rework", "test_second_review_is_terminal"),
                *select(
                    "test_review",
                    "test_changes_required_after_rework_is_terminal_and_keeps_changes",
                ),
            )
            tests(
                "11 rework proposal failures",
                *select("test_rework", "test_rework_proposal_failure_is_terminal"),
            )
            tests(
                "12 second mutation failures",
                *select("test_rework", "test_second_mutation_failure_is_terminal"),
            )
            tests(
                "13 second check / Git integrity failures",
                *select(
                    "test_rework",
                    "test_second_check_failure_stops_before_review_two",
                    "test_rework_unexpected_change_stops_before_review_two",
                ),
            )
            tests(
                "14 authorization re-evaluation for the rework",
                *select(
                    "test_rework",
                    "test_denied_second_mutation_after_grant_expiry",
                    "test_expired_read_grant_denies_rework_evidence",
                ),
            )
            tests(
                "15 call / attempt ceilings and guard",
                *select(
                    "test_rework",
                    "test_attempt_ceiling_is_a_constant_and_evidence_enforces_it",
                    "test_workspace_guard_held_through_rework",
                ),
                *select(
                    "test_architecture",
                    "test_rework_is_structurally_bounded_to_one_cycle",
                    "test_no_configurable_attempt_or_retry_count",
                    "test_review_findings_never_drive_effects_directly",
                ),
            )
            tests("16 architecture / import boundaries", "tests/test_architecture.py")
            tests(
                "17 real-Docker rework ACCEPT end-to-end and second-pass failure",
                *select(
                    "test_end_to_end",
                    "test_rework_then_accept_in_the_real_sandbox",
                    "test_rework_check_finding_stops_before_second_review",
                ),
            )
            tests("18 clean-install rework execution", "tests/test_clean_install.py")
            tests(
                "19 ForgeAI-1/2 regressions",
                "tests/test_worker.py",
                "tests/test_cli.py",
                "tests/test_review.py",
                *select(
                    "test_end_to_end",
                    "test_fixture_task_succeeds_in_the_real_sandbox",
                    "test_sandbox_finding_fails_the_task",
                    "test_missing_docker_is_check_infrastructure_error",
                ),
            )
            tests(
                "19b M8.2/M8.3 engineering regressions",
                "tests/test_reviewer.py",
                "tests/test_coding.py",
                cwd=ENGINEERING,
            )
            project("19c demo: review #1 accepts", FORGEAI, "python", "demo.py")
            project(
                "19d demo: one bounded rework", FORGEAI, "python", "demo.py", "rework"
            )
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
        "FORGEAI-3 LOCAL VALIDATION PASSED - replay coding/review x2, real sandbox "
        "checks, public LegoAI only; no build, pull or network"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
