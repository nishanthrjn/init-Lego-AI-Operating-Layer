"""CR-1b validation: ADR-014 public local governed host; orchestration only.

Run from the repository root:

    uv run python .\\validate_consumer_readiness_cr1b.py

Offline and deterministic: every Model provider is a trusted fake or a mocked
Ollama transport; no provider service, Docker, CUDA or network is used. Phase
"consumer environments" runs `uv sync --locked` for the engineering pack (with
its existing `analyst` extra) and DocuMind, exactly as their M8.x/v0.1 scripts
do: locked, no new dependency resolution. Streams output, stops at the first
failed phase, exits non-zero on failure.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINEERING = ROOT / "packages" / "legoai-engineering"
DOCUMIND = ROOT / "examples" / "documind"
SELF = ROOT / "validate_consumer_readiness_cr1b.py"
HOST_TESTS = "tests/integration/composition/test_local_host.py"
PINNED = {
    "legoai-reference": "0.1.0.dev0",
    "pytest": "9.1.1",
    "mypy": "2.3.1",
    "ruff": "0.16.8",
    "hatchling": "1.32.3",
    "editables": "0.5",
}
CORE_STATIC = [
    "src/legoai/runtime",
    "src/legoai/reference/execution.py",
    HOST_TESTS,
    "tests/architecture/test_local_host.py",
    "tests/architecture/test_import_boundaries.py",
    "tests/architecture/test_package_install.py",
    "examples/local_host.py",
    str(SELF),
]
# CR-1b-owned engineering files. Other engineering files (M8.3) carry their own
# pending formatting handoff and are linted/formatted by the M8.3 script.
ENGINEERING_FILES = [
    "examples/governed_demo.py",
    "examples/repository_analyst.py",
    "tests/test_reviewer.py",
    "tests/test_analyst.py",
]
DOCUMIND_FILES = [
    "src/documind_app/composition.py",
    "tests/unit/test_public_composition.py",
]
GROUPS = {
    "6 configuration validation": [
        "test_grant_window_must_be_aware_and_ordered",
        "test_grant_text_is_bounded",
        "test_capacity_bounds",
        "test_grant_and_binding_counts_are_bounded",
        "test_duplicate_grants_conflict",
        "test_duplicate_binding_conflicts",
        "test_selection_data_is_closed",
        "test_selection_revision_and_binding_are_pinned",
        "test_contribution_purposes_are_closed_and_chat_anchored",
        "test_invalid_builtin_settings_fail_at_open",
    ],
    "7 local host composition": [
        "test_open_is_inert_and_constructs_only_selected_once",
        "test_builtin_ollama_open_makes_no_request",
        "test_constructor_failure_returns_no_host",
        "test_constructor_must_supply_model_port",
        "test_same_consumer_code_under_changed_selection",
    ],
    "8 governance / authority": [
        "test_missing_grant_fails_before_registration",
        "test_configured_but_invalid_grant_is_denied_before_provider",
        "test_authorization_is_current_at_dispatch_not_at_minting",
        "test_security_context_selects_only_exact_configured_grants",
        "test_security_context_subject_scope",
        "test_model_output_cannot_manufacture_authority",
    ],
    "9 chat / effect semantics": [
        "test_chat_success_uses_existing_semantics",
        "test_chat_failures_keep_effect_mapping_without_retry",
        "test_elapsed_deadline_rejects_before_provider",
    ],
    "10 embedding": [
        "test_embedding_uses_the_same_selected_binding",
        "test_embedding_unavailable_has_no_fallback",
        "test_embedding_uncertainty_is_unknown",
        "test_builtin_embedding_through_mocked_transport",
    ],
    "11 Agent runtime": [
        "test_agent_runtime_public_path_calls_model_once",
        "test_agent_routing_miss_and_uncertainty",
        "test_agent_refuses_foreign_context",
    ],
    "12 capacity / event-loop confinement": [
        "test_capacity_is_a_hard_lifetime_bound_without_release",
        "test_rejected_allocations_do_not_consume_capacity",
        "test_same_loop_use_and_cross_loop_refusal",
        "test_other_thread_is_refused",
    ],
    "13 host isolation / context ownership": [
        "test_foreign_and_wrong_purpose_contexts_are_refused",
        "test_two_hosts_share_no_state",
    ],
}


def main() -> int:
    uv = shutil.which("uv")
    git = shutil.which("git")
    python = sys.executable
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    # Consumer projects use their own locked environments, never this one.
    consumer_environment = environment.copy()
    consumer_environment.pop("VIRTUAL_ENV", None)
    completed: list[str] = []
    phase = "environment"
    with tempfile.TemporaryDirectory(prefix="legoai-cr1b-") as temporary:
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

        def consumer(name: str, project: Path, *arguments: str) -> None:
            assert uv is not None
            run(
                name,
                [uv, "run", "--locked", "--no-sync", *arguments],
                cwd=project,
                env=consumer_environment,
            )

        def pytest_args(name: str) -> list[str]:
            slug = name.split()[0]
            return [
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(base / slug),
                "-q",
            ]

        def core_tests(name: str, *targets: str) -> None:
            run(name, [python, *pytest_args(name), *targets])

        try:
            phase = "1 environment / toolchain"
            if uv is None:
                raise RuntimeError("uv is required: https://docs.astral.sh/uv/")
            if git is None:
                raise RuntimeError("git is required")
            if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
                raise RuntimeError(
                    "run through the locked root environment: "
                    "uv run python .\\validate_consumer_readiness_cr1b.py"
                )
            run(
                "1 environment / toolchain",
                [
                    python,
                    "-c",
                    "import importlib.metadata as m, subprocess, sys;"
                    " assert sys.version_info[:2] == (3, 14), sys.version;"
                    f" expected={PINNED!r};"
                    " bad=[k for k, v in expected.items() if m.version(k) != v];"
                    " assert not bad, bad; print(sys.version);"
                    f" subprocess.run([{uv!r}, '--version'], check=True)",
                ],
            )
            run(
                "1b engineering environment (locked sync, analyst extra)",
                [uv, "sync", "--locked", "--extra", "analyst"],
                cwd=ENGINEERING,
                env=consumer_environment,
            )
            # Same two-step order as run_tests_documind.ps1: build tools first.
            run(
                "1c DocuMind environment (locked sync, tools)",
                [uv, "sync", "--locked", "--group", "dev", "--no-install-project"],
                cwd=DOCUMIND,
                env=consumer_environment,
            )
            run(
                "1d DocuMind environment (locked sync, project)",
                [uv, "sync", "--locked", "--group", "dev", "--no-build-isolation"],
                cwd=DOCUMIND,
                env=consumer_environment,
            )
            run(
                "2a typing (Core)",
                [
                    python,
                    "-m",
                    "mypy",
                    "--cache-dir",
                    str(base / "mypy"),
                    "src",
                    *CORE_STATIC[2:],
                ],
            )
            consumer(
                "2b typing (engineering)",
                ENGINEERING,
                "python",
                "-m",
                "mypy",
                "--cache-dir",
                str(base / "mypy-eng"),
                "src",
                "tests",
                "examples",
            )
            consumer(
                "2c typing (DocuMind)",
                DOCUMIND,
                "python",
                "-m",
                "mypy",
                "--cache-dir",
                str(base / "mypy-dm"),
                "src",
                "tests",
            )
            run(
                "3a Ruff lint (Core)",
                [python, "-m", "ruff", "check", "--no-cache", *CORE_STATIC],
            )
            consumer(
                "3b Ruff lint (engineering CR-1b files)",
                ENGINEERING,
                "python",
                "-m",
                "ruff",
                "check",
                "--no-cache",
                *ENGINEERING_FILES,
                "tests/test_architecture.py",
            )
            consumer(
                "3c Ruff lint (DocuMind)",
                DOCUMIND,
                "python",
                "-m",
                "ruff",
                "check",
                "--no-cache",
                "src",
                "tests",
            )
            run(
                "4a Ruff format (Core)",
                [python, "-m", "ruff", "format", "--check", "--no-cache", *CORE_STATIC],
            )
            consumer(
                "4b Ruff format (engineering CR-1b files)",
                ENGINEERING,
                "python",
                "-m",
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *ENGINEERING_FILES,
            )
            consumer(
                "4c Ruff format (DocuMind CR-1b files)",
                DOCUMIND,
                "python",
                "-m",
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *DOCUMIND_FILES,
            )
            core_tests(
                "5 runtime API contracts",
                "tests/architecture/test_local_host.py::test_runtime_api_is_contract_only",
                "tests/architecture/test_local_host.py::test_runtime_api_may_use_owner_contracts",
                "tests/architecture/test_local_host.py::test_model_purposes_are_closed_and_match_existing_capabilities",
                "tests/architecture/test_local_host.py::test_host_failure_vocabulary_is_closed",
                "tests/architecture/test_local_host.py::test_host_members_accept_no_authority_or_code",
            )
            for name, tests in GROUPS.items():
                core_tests(name, *(f"{HOST_TESTS}::{test}" for test in tests))
            consumer(
                "14a engineering consumer migration (tests)",
                ENGINEERING,
                "python",
                *pytest_args("14a"),
                "tests/test_reviewer.py",
                "tests/test_analyst.py",
                "tests/test_coding.py",
                "tests/test_coding_m4.py",
                "tests/test_architecture.py",
                "tests/test_package_install.py",
            )
            consumer(
                "14b engineering example (analyst)",
                ENGINEERING,
                "python",
                "examples/repository_analyst.py",
            )
            consumer(
                "14c engineering example (reviewer)",
                ENGINEERING,
                "python",
                "examples/independent_reviewer.py",
            )
            consumer(
                "14d engineering example (coding)",
                ENGINEERING,
                "python",
                "examples/bounded_coding.py",
            )
            consumer(
                "15 DocuMind consumer migration",
                DOCUMIND,
                "python",
                *pytest_args("15"),
                "tests/unit",
                "tests/integration",
                "tests/evaluation",
            )
            core_tests(
                "16 architecture / private-import boundaries",
                "tests/architecture/test_local_host.py",
                "tests/architecture/test_import_boundaries.py",
                "tests/architecture/test_agent.py",
                "tests/architecture/test_model_routing.py",
            )
            core_tests(
                "17 ADR-019 / model-selection regressions",
                "tests/integration/composition/test_model_selection.py",
                "tests/integration/composition/test_model_governed.py",
                "tests/unit/reference/test_model.py",
                "tests/unit/reference/test_model_routing.py",
            )
            core_tests(
                "18a package build / clean install",
                "tests/architecture/test_package_install.py",
            )
            run("18b public example", [python, "examples/local_host.py"])
            core_tests(
                "19 affected existing runtime tests",
                "tests/integration/composition/test_agent.py",
                "tests/unit/execution/test_agent.py",
                "tests/unit/reference/test_coordinator.py",
                "tests/unit/reference/test_execution.py",
                "tests/unit/reference/test_static_security_context_registry.py",
                "tests/integration/composition/test_import_inertness.py",
                "tests/integration/composition/test_governed_direct.py",
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
        "CR-1b DETERMINISTIC VALIDATION PASSED - OFFLINE ONLY; "
        "NO LIVE PROVIDER, DOCKER OR NETWORK USED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
