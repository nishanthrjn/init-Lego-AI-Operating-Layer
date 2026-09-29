"""CR-3 validation: authorized engineering effects and the consumer guide.

Run from the repository root (Windows, Docker Desktop Linux engine, context
desktop-linux, with the CR-2a PYTHON_CHECKS image already built locally):

    uv run python .\\validate_consumer_readiness_cr3.py

Focused, affected validation only. Real Docker is used for the authorized
sandboxed-check composition alone; CR-2a/2b are not requalified. Nothing is
built or pulled. Every pytest phase uses a fresh --basetemp. Streams output,
stops at the first failed phase and exits non-zero on failure.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINEERING = ROOT / "packages" / "legoai-engineering"
SELF = ROOT / "validate_consumer_readiness_cr3.py"
IMAGE = "sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df"
EFFECTS = "tests/test_authorized_effects.py"
SOURCES = ["src", "tests", "examples"]


def effects(*names: str) -> list[str]:
    return [f"{EFFECTS}::{name}" for name in names]


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
    with tempfile.TemporaryDirectory(prefix="legoai-cr3-") as temporary:
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
                    "uv run python .\\validate_consumer_readiness_cr3.py"
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
                *SOURCES,
            )
            run(
                "2b typing (validator)",
                [python, "-m", "mypy", "--cache-dir", str(base / "mypy-v"), str(SELF)],
            )
            engineering(
                "3 Ruff lint", "python", "-m", "ruff", "check", "--no-cache", *SOURCES
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
                *SOURCES,
            )
            run(
                "4b Ruff format (validator)",
                [python, "-m", "ruff", "format", "--check", str(SELF)],
            )
            tests(
                "5 shared authorization helper",
                *effects(
                    "test_helper_denies_approvals_without_evaluating",
                    "test_unavailable_authority_is_distinct_and_fails_closed",
                    "test_unrelated_or_stale_decision_is_denied",
                    "test_non_decision_is_a_contract_error_not_an_allow",
                ),
            )
            tests(
                "6 authorized mutation",
                *effects(
                    "test_mutation_requires_changeset_before_authorization",
                    "test_allowed_mutation_error_propagates_once",
                    "test_denied_write_leaves_proposal_unapplied",
                    "test_read_write_and_check_grants_are_independent",
                ),
            )
            tests(
                "7 authorized checks",
                *effects(
                    "test_check_requires_request_before_authorization",
                    "test_allowed_check_error_propagates_once",
                    "test_constructor_rejects_wrong_types",
                ),
            )
            tests(
                "8 denial-before-effect ordering",
                *effects(
                    "test_mutation_allowed_authorizes_then_applies_exactly_once",
                    "test_mutation_denied_never_calls_inner_and_writes_nothing",
                    "test_check_allowed_authorizes_then_checks_exactly_once",
                    "test_check_denied_never_reaches_workspace_or_sandbox",
                ),
            )
            tests(
                "9 expiry / revocation / current policy",
                *effects(
                    "test_grant_valid_at_construction_but_expired_before_effect",
                    "test_allow_is_never_cached",
                    "test_revocation_and_policy_supersession_deny_the_next_effect",
                ),
            )
            tests(
                "10 tenant / workspace scope",
                *effects(
                    "test_wrong_tenant_grant_is_denied_before_effect",
                    "test_wrong_workspace_or_action_scope_is_refused_at_composition",
                ),
            )
            tests(
                "11 approval fail-closed",
                *effects("test_approval_bearing_context_is_refused_before_any_effect"),
            )
            tests(
                "12 wrapper over LocalEngineeringChecks and fake-sandbox adapter",
                *effects("test_same_consumer_over_local_and_sandboxed_inner_adapters"),
            )
            tests(
                "13 wrapper over real Docker SandboxedEngineeringChecks",
                "tests/test_checks_sandboxed_docker.py::test_authorized_sandboxed_check",
            )
            tests(
                "14 M4 regressions",
                "tests/test_mutation.py",
                "tests/test_coding_m4.py",
                *effects("test_m4_preconditions_still_apply_behind_authorization"),
            )
            tests(
                "15 M5 / CR-2b deterministic regressions",
                "tests/test_checks.py",
                "tests/test_checks_sandboxed.py",
            )
            tests(
                "16 M8.1-M8.3 authorized-read and coding regressions",
                "tests/test_analyst.py",
                "tests/test_reviewer.py",
                "tests/test_coding.py",
                "tests/test_analyst_architecture.py",
            )
            tests("17 public-import architecture", "tests/test_architecture.py")
            tests("18 clean-install consumer proof", "tests/test_package_install.py")
            tests(
                "19 ForgeAI structural readiness proof",
                "tests/test_consumer_readiness.py",
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
        "CR-3 LOCAL VALIDATION PASSED - authorized effects, public wiring and "
        "consumer proof; no build, pull or network"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
