r"""Offline SECRET-SOURCE-S1 qualification: uv run python .\validate_secret_source_s1.py.

Operator-provisioned immutable process-local Secret material behind the
existing exact-use mechanism (ADR-023 §8). Synthetic test canaries only: no
credential, provider, network, Docker or environment source. REMOTE stays
refused. Existing installed project environments are required; never syncs.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_secret_use_durable_custody_1 import IMPLEMENTATION_TEST_DIRECTORIES

ROOT = Path(__file__).resolve().parent
BASE = "c1ab168"  # disclosure gate qualified; last commit before this slice
PRODUCTION = (
    "src/legoai/reference/secret.py",
    "src/legoai/runtime/_composition/secret.py",
)
TESTS = (
    "tests/unit/reference/test_secret_source_s1.py",
    "tests/architecture/test_secret_source_s1.py",
    "tests/architecture/test_secret_ref.py",
    "tests/support/secret_ref_scenario.py",
)
SELF = "validate_secret_source_s1.py"
PYTHON_FILES = (*PRODUCTION, *TESTS, SELF)
ALLOWED = set(PYTHON_FILES) | {
    "docs/secret-ref-1a.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
}
UNIT = "tests/unit/reference/test_secret_source_s1.py"
ARCH = "tests/architecture/test_secret_source_s1.py"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, encoding="utf-8", check=True
    ).stdout


def scope() -> None:
    changed = set(git("diff", "--name-only", BASE).splitlines())
    changed.update(
        git(
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            ".",
            ":(exclude)examples/forgeai/.lq13-test-temp/**",
            ":(exclude)examples/forgeai/aq1q-r4-qwen2.5-coder-14b/**",
            *(f":(exclude){name}/**" for name in IMPLEMENTATION_TEST_DIRECTORIES),
        ).splitlines()
    )
    if changed - ALLOWED:
        raise RuntimeError("unexpected scope: " + repr(sorted(changed - ALLOWED)))


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
    completed: list[str] = []
    phase = "1 scope guard (Secret owner only; no adapter, runtime API or consumer)"
    cache = ROOT / ".pytest_cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="secret-s1-", dir=cache) as tmp:
        temp = Path(tmp)

        def run(name: str, args: list[str], cwd: Path = ROOT) -> None:
            nonlocal phase
            phase = name
            print("[PHASE] " + phase, flush=True)
            command = (
                [sys.executable, "-B", "-m"]
                if cwd == ROOT
                else [
                    "uv",
                    "run",
                    "--locked",
                    "--no-sync",
                    "--offline",
                    "python",
                    "-B",
                    "-m",
                ]
            )
            subprocess.run([*command, *args], cwd=cwd, env=env, check=True)
            completed.append(name)

        def tests(name: str, *selectors: str, cwd: Path = ROOT) -> None:
            run(
                name,
                [
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "--basetemp",
                    str(temp / name.split()[0]),
                    *selectors,
                ],
                cwd,
            )

        def focused(number: int, name: str, *names: str) -> None:
            tests(f"{number} {name}", *(UNIT + "::" + n for n in names))

        try:
            print("[PHASE] " + phase, flush=True)
            scope()
            completed.append(phase)
            focused(
                2,
                "provisioning returns a reference only; bounded material",
                "test_provisioning_returns_only_a_reference",
                "test_invalid_material_is_rejected_without_echo",
                "test_bounds_admit_ordinary_bearer_keys",
            )
            focused(
                3,
                "immutable revisions; replacement is a new revision",
                "test_replacement_is_a_new_revision_and_retires_the_old",
                "test_other_identities_are_independent",
                "test_close_overwrites_owned_buffers_best_effort",
            )
            focused(
                4,
                "authorized exact use realizes the revision; synthetic unchanged",
                "test_authorized_exact_use_realizes_the_provisioned_revision",
                "test_synthetic_stage_a_is_unchanged",
            )
            focused(
                5,
                "stale, retired, closed, wrong reference/purpose/consumer refused",
                "test_ineligible_revision_never_yields_material",
                "test_closed_source_refuses_new_provisioning",
                "test_wrong_reference_purpose_or_consumer_is_ineligible",
                "test_wrong_class_or_foreign_domain_is_rejected_at_composition",
                "test_unauthorized_use_never_receives_material",
            )
            focused(
                6,
                "retirement and close ordered against use",
                "test_retirement_and_close_are_ordered_against_use",
                "test_close_preserves_historical_attribution",
            )
            focused(
                7,
                "no leak to logs, files or environment",
                "test_no_material_in_logs",
                "test_no_ambient_environment_source",
                "test_provisioning_creates_no_files",
            )
            focused(
                8,
                "hidden interactive bootstrap",
                "test_hidden_input_provisions_directly_into_the_source",
                "test_hidden_input_refuses_without_an_interactive_terminal",
                "test_hidden_input_rejection_does_not_echo",
            )
            tests("9 all S1 tests", UNIT)
            tests("10 S1 boundaries", ARCH)
            tests(
                "11 SECRET-REF-1A regressions",
                "tests/unit/reference/test_secret_ref.py",
                "tests/architecture/test_secret_ref.py",
            )
            tests(
                "12 SECRET-USE-DURABLE-CUSTODY-1 regressions",
                "tests/unit/reference/test_secret_durable_custody.py",
                "tests/architecture/test_secret_durable_custody.py",
            )
            tests(
                "13 governance and import boundaries",
                "tests/unit/governance",
                "tests/architecture/test_import_boundaries.py",
                "tests/architecture/test_local_host.py",
                "tests/architecture/test_remote_disclosure.py",
            )
            tests(
                "14 Core unit, integration and contract regressions",
                "tests/unit",
                "tests/integration",
                "tests/contract",
            )
            tests(
                "15 DocuMind regressions",
                "tests/unit",
                "tests/integration",
                cwd=ROOT / "examples/documind",
            )
            tests(
                "16 ForgeAI regressions",
                "tests/test_architecture.py",
                "tests/test_worker.py",
                "tests/test_review.py",
                "tests/test_rework.py",
                cwd=ROOT / "examples/forgeai",
            )
            run(
                "17 mypy",
                [
                    "mypy",
                    "--cache-dir",
                    str(temp / "mypy"),
                    "src",
                    UNIT,
                    ARCH,
                    "tests/support/secret_ref_scenario.py",
                    str(Path(__file__).resolve()),
                ],
            )
            run("18 Ruff lint", ["ruff", "check", "--no-cache", *PYTHON_FILES])
            run(
                "19 Ruff format",
                ["ruff", "format", "--check", "--no-cache", *PYTHON_FILES],
            )
            phase = "20 git diff check"
            print("[PHASE] " + phase, flush=True)
            git("diff", "--check", BASE)
            completed.append(phase)
        except (subprocess.CalledProcessError, RuntimeError, OSError) as error:
            for name in completed:
                print("PASS " + name)
            print("FAIL " + phase + ": " + str(error))
            return 1
    for name in completed:
        print("PASS " + name)
    print(
        "SECRET-SOURCE-S1 LOCAL VALIDATION PASSED - offline; synthetic canaries; "
        "no credential transport, provider, network or environment source"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
