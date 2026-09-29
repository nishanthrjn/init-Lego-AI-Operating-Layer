"""CR-2b validation: SandboxedEngineeringChecks over the qualified image.

Run from the repository root (Windows, Docker Desktop Linux engine, context
desktop-linux, with the CR-2a PYTHON_CHECKS image already built locally):

    uv run python .\\validate_consumer_readiness_cr2b.py

Does NOT build, pull or requalify any image; the recorded CR-2a image ID is
used (LEGOAI_SANDBOX_CHECKS_IMAGE is removed from the test environment). Every
pytest phase uses a fresh --basetemp. Streams output, stops at the first failed
phase and exits non-zero on failure.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINEERING = ROOT / "packages" / "legoai-engineering"
SELF = ROOT / "validate_consumer_readiness_cr2b.py"
IMAGE = "sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df"
UNIT = "tests/test_checks_sandboxed.py"
DOCKER = "tests/test_checks_sandboxed_docker.py"
FILES = [
    "src/legoai_engineering/checks",
    "examples/python_checks_project.py",
    "tests/test_checks_sandboxed.py",
    "tests/test_checks_sandboxed_docker.py",
    "tests/test_sandbox_checks_docker.py",
    "tests/test_package_install.py",
]


def unit(*names: str) -> list[str]:
    return [f"{UNIT}::{name}" for name in names]


def docker_cases(*ids: str) -> list[str]:
    return [f"{DOCKER}::test_check_outcomes[{case}]" for case in ids]


def main() -> int:
    uv = shutil.which("uv")
    git = shutil.which("git")
    docker = shutil.which("docker")
    python = sys.executable
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    engineering_environment = environment.copy()
    engineering_environment.pop("VIRTUAL_ENV", None)
    engineering_environment.pop("LEGOAI_SANDBOX_CHECKS_IMAGE", None)
    completed: list[str] = []
    phase = "environment"
    with tempfile.TemporaryDirectory(prefix="legoai-cr2b-") as temporary:
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

        def engineering(name: str, *arguments: str) -> None:
            assert uv is not None
            run(
                name,
                [uv, "run", "--locked", "--no-sync", *arguments],
                cwd=ENGINEERING,
                env=engineering_environment,
            )

        def tests(name: str, *targets: str) -> None:
            basetemp = base / name.split()[0]
            engineering(
                name,
                "python",
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(basetemp),
                "-q",
                "-rs",
                *targets,
            )

        try:
            phase = "1 environment / qualified image presence"
            for tool, value in (("uv", uv), ("git", git), ("docker", docker)):
                if value is None:
                    raise RuntimeError(f"{tool} is required on PATH")
            if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
                raise RuntimeError(
                    "run through the locked root environment: "
                    "uv run python .\\validate_consumer_readiness_cr2b.py"
                )
            if os.name != "nt":
                raise RuntimeError("reference scope is Windows + Docker Desktop Linux")
            assert uv is not None and git is not None and docker is not None
            run(
                "1 environment / qualified image presence",
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
                "1b engineering environment (locked sync, analyst extra)",
                [uv, "sync", "--locked", "--extra", "analyst"],
                cwd=ENGINEERING,
                env=engineering_environment,
            )
            engineering(
                "2 typing (engineering)",
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
                "2b typing (validator)",
                [python, "-m", "mypy", "--cache-dir", str(base / "mypy-v"), str(SELF)],
            )
            engineering(
                "3 Ruff lint", "python", "-m", "ruff", "check", "--no-cache", *FILES
            )
            run("3b Ruff lint (validator)", [python, "-m", "ruff", "check", str(SELF)])
            engineering(
                "4 Ruff format",
                "python",
                "-m",
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *FILES,
            )
            run(
                "4b Ruff format (validator)",
                [python, "-m", "ruff", "format", "--check", str(SELF)],
            )
            tests(
                "5 deterministic adapter unit tests",
                *unit(
                    "test_kind_selects_only_its_fixed_tool",
                    "test_one_execution_per_check_with_bound_cancellation",
                    "test_constructor_rejects_wrong_types",
                    "test_consumer_is_indifferent_to_the_adapter",
                ),
            )
            tests(
                "6 CheckFailure contract",
                *unit(
                    "test_every_sandbox_failure_maps_explicitly",
                    "test_runner_reported_failures",
                    "test_malformed_runner_protocol_is_io",
                    "test_nonzero_runner_exit_is_io_not_a_check_result",
                    "test_decoded_output_beyond_policy_is_output_limit",
                ),
            )
            tests(
                "7 input acquisition and bounds",
                *unit(
                    "test_selection_is_deterministic_and_bounded_to_text_types",
                    "test_target_outside_selection_is_refused",
                    "test_missing_root_and_unreadable_input_fail_closed",
                    "test_overflow_is_input_limit_never_truncation",
                    "test_workspace_limit_and_scan_limit_are_input_limits",
                    "test_input_policy_validation",
                ),
            )
            tests(
                "8 shared command parity / trusted runner",
                *unit(
                    "test_host_and_sandbox_options_are_identical",
                    "test_single_private_command_table",
                    "test_runner_is_one_constant_and_takes_no_caller_command",
                ),
            )
            tests(
                "9 cancellation (deterministic)",
                *unit(
                    "test_cancelled_before_execution_reads_and_dispatches_nothing",
                    "test_cancelled_during_input_acquisition_is_not_dispatched",
                    "test_cancelled_during_execution_maps_sandbox_cancellation",
                ),
            )
            tests(
                "10 sandbox result mapping",
                *unit("test_findings_are_results_not_failures"),
            )
            tests(
                "11 real Docker pytest cases",
                *docker_cases(
                    "pytest-pass",
                    "pytest-fail",
                    "pytest-collection-error",
                    "pytest-no-tests",
                ),
            )
            tests(
                "12 real Docker Ruff cases",
                *docker_cases(
                    "ruff-clean",
                    "ruff-finding",
                    "ruff-format-clean",
                    "ruff-format-finding",
                ),
            )
            tests(
                "13 real Docker mypy cases",
                *docker_cases("mypy-clean", "mypy-finding"),
            )
            tests(
                "14 timeout / output / resource / cancellation / unavailable",
                f"{DOCKER}::test_check_timeout",
                f"{DOCKER}::test_output_limit",
                f"{DOCKER}::test_memory_limit_is_resource_limit",
                f"{DOCKER}::test_cancellation_before_and_during_execution",
                f"{DOCKER}::test_unqualified_toolchain_is_unavailable",
            )
            tests(
                "15 confinement / network / cleanup / adapter substitution",
                f"{DOCKER}::test_network_remains_unavailable_to_tests",
                f"{DOCKER}::test_same_consumer_with_host_and_sandboxed_adapters",
                "tests/test_sandbox_checks_docker.py::"
                "test_checks_image_keeps_m6_confinement",
            )
            tests("16 LocalEngineeringChecks regressions", "tests/test_checks.py")
            tests(
                "17 M6 / CR-2a affected regressions",
                "tests/test_sandbox.py",
                "tests/test_sandbox_checks_docker.py",
            )
            tests("18 architecture", "tests/test_architecture.py")
            tests("19 wheel / clean install", "tests/test_package_install.py")
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
        "CR-2b LOCAL DOCKER VALIDATION PASSED - recorded PYTHON_CHECKS image only; "
        "no build, pull or network"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
