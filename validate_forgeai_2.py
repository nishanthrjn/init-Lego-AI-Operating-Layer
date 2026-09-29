"""ForgeAI-2 validation: independent review gate over the ForgeAI-1 worker.

Run from the repository root (Windows, Docker Desktop Linux engine, context
desktop-linux, with the CR-2a PYTHON_CHECKS image already built locally):

    uv run python .\\validate_forgeai_2.py

Offline: both model calls (Coding Agent, then IndependentReviewer) use
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
SELF = ROOT / "validate_forgeai_2.py"
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
    with tempfile.TemporaryDirectory(prefix="forgeai-2-") as temporary:
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
                    "uv run python .\\validate_forgeai_2.py"
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
            tests("5 domain-contract extensions", "tests/test_domain.py")
            tests(
                "6 review-input construction / bounds / disclosure",
                *select(
                    "test_review",
                    "test_review_material_is_deterministic_and_bounded",
                    "test_oversized_changed_file_is_review_input_failure",
                    "test_serialized_review_over_budget_is_review_input_failure",
                    "test_producer_is_the_coding_agent_not_the_reviewer",
                    "test_reviewer_sees_authorized_file_reads_and_no_git_state",
                    "test_denied_review_read_is_review_input_failure",
                ),
            )
            tests(
                "7 reviewer gating / order",
                *select(
                    "test_review",
                    "test_review_runs_last_once_and_accept_succeeds",
                    "test_no_review_when_proposal_invalid",
                    "test_no_review_when_mutation_denied",
                    "test_no_review_when_checks_fail",
                    "test_no_review_when_final_git_integrity_fails",
                ),
            )
            tests(
                "8 ACCEPT path",
                *select(
                    "test_worker",
                    "test_success_applies_once_checks_in_order_and_records_state",
                ),
                *select("test_cli", "test_summary_is_bounded_and_omits_contents"),
            )
            tests(
                "9 CHANGES_REQUIRED path",
                *select(
                    "test_review",
                    "test_changes_required_stops_without_rework_and_keeps_changes",
                ),
            )
            tests(
                "10 INSUFFICIENT_EVIDENCE path",
                *select(
                    "test_review", "test_insufficient_evidence_stops_without_rework"
                ),
            )
            tests(
                "11 reviewer execution failures",
                *select(
                    "test_review",
                    "test_review_provider_failure_is_review_failed",
                    "test_review_model_denial_is_review_failed_without_provider_call",
                    "test_invalid_or_uncited_review_output_is_output_invalid",
                ),
            )
            tests(
                "12 no-rework / no-retry assertions",
                *select(
                    "test_architecture",
                    "test_review_stage_cannot_mutate_check_or_rework",
                    "test_reviewer_is_composed_from_the_agent_runtime_only",
                ),
                *select(
                    "test_worker",
                    "test_conflict_and_partial_apply_are_reported_without_retry",
                ),
            )
            tests(
                "13 evidence / result invariants",
                *select(
                    "test_domain",
                    "test_success_requires_a_completed_accept_review",
                    "test_review_evidence_requires_every_deterministic_gate",
                    "test_evidence_holds_only_values_not_runtime_objects",
                    "test_result_disposition_matches_failure_step",
                ),
            )
            tests("14 architecture / import boundaries", "tests/test_architecture.py")
            tests(
                "15 full replay + real-Docker ACCEPT end-to-end",
                *select(
                    "test_end_to_end", "test_fixture_task_succeeds_in_the_real_sandbox"
                ),
            )
            tests(
                "16 real-Docker pre-review failure paths",
                *select(
                    "test_end_to_end",
                    "test_sandbox_finding_fails_the_task",
                    "test_missing_docker_is_check_infrastructure_error",
                ),
            )
            tests("17 clean-install execution", "tests/test_clean_install.py")
            tests(
                "18 M8.2 reviewer regressions",
                "tests/test_reviewer.py",
                "tests/test_analyst_architecture.py",
                cwd=ENGINEERING,
            )
            tests(
                "19 ForgeAI-1 regressions",
                "tests/test_worker.py",
                "tests/test_cli.py",
            )
            project("19b README demo execution", FORGEAI, "python", "demo.py")
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
        "FORGEAI-2 LOCAL VALIDATION PASSED - replay coding + review, real sandbox "
        "checks, public LegoAI only; no build, pull or network"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
