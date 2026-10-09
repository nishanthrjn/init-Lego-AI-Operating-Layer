r"""Offline qualification: uv run python .\validate_remote_attempt_custody_1.py.

REMOTE-ATTEMPT-CUSTODY-1: durable, content-minimized INTENDED custody for one
exact remote Model attempt before any future credential-bearing handoff
(ADR-007 §6.2, ADR-023 §9); recovery never resends; unsettled means UNKNOWN.
Synthetic canaries only: no transport, provider, network, Docker or credential
use. REMOTE stays refused. Existing installed environments only; never syncs.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_secret_use_durable_custody_1 import IMPLEMENTATION_TEST_DIRECTORIES

ROOT = Path(__file__).resolve().parent
BASE = "3cf6ce8"  # S1 qualified; last commit before this slice
PRODUCTION = (
    "src/legoai/reference/_remote_attempts.py",
    "src/legoai/reference/_custody_codec.py",
    "src/legoai/runtime/_composition/remote_attempt.py",
)
TESTS = (
    "tests/unit/reference/test_remote_attempts.py",
    "tests/integration/composition/test_remote_attempt_custody.py",
    "tests/architecture/test_remote_attempts.py",
    "tests/architecture/test_import_boundaries.py",
    "tests/architecture/test_remote_disclosure.py",
    "tests/support/remote_attempt_scenario.py",
)
SELF = "validate_remote_attempt_custody_1.py"
PYTHON_FILES = (*PRODUCTION, *TESTS, SELF)
ALLOWED = set(PYTHON_FILES) | {
    "docs/model-composition.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
}
UNIT = "tests/unit/reference/test_remote_attempts.py"
PLANE = "tests/integration/composition/test_remote_attempt_custody.py"
ARCH = "tests/architecture/test_remote_attempts.py"


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
    phase = "1 scope guard (invocation-plane store only; no transport or adapter)"
    cache = ROOT / ".pytest_cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="remote-attempt-", dir=cache) as tmp:
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
                "exact INTENDED record, safe identities, no content or material",
                "test_intended_record_persists_exact_safe_identities",
                "test_no_content_or_credential_is_stored",
                "test_credential_free_attempt_is_representable",
                "test_attempt_values_reject_tenant_mismatch_and_bad_types",
            )
            focused(
                3,
                "duplicate attempts and executions refused",
                "test_duplicate_attempt_id_never_admits_a_second_responsibility",
                "test_one_attempt_per_execution",
            )
            focused(
                4,
                "INTENDED receipt required, once, before any handoff",
                "test_handoff_requires_a_durable_intended_receipt_once",
                "test_failed_intended_commit_yields_no_receipt",
                "test_settled_attempt_cannot_be_claimed",
            )
            focused(
                5,
                "terminal outcomes; nothing inferred from missing evidence",
                "test_terminal_outcomes_are_final",
                "test_outcomes_are_never_inferred_from_missing_evidence",
                "test_intended_is_never_a_settlement",
                "test_after_handoff_only_transport_proof_supports_not_sent",
                "test_cancellation_before_intended_records_nothing",
            )
            focused(
                6,
                "recovery is inspection; unsettled is UNKNOWN; never resends",
                "test_restart_reports_unsettled_as_unknown_read_only",
                "test_recovery_never_calls_provider_transport_or_secret",
            )
            focused(
                7,
                "real process-death windows A-D",
                "test_process_death_windows",
            )
            focused(
                8,
                "corruption, capacity, owner thread, canary scans",
                "test_corrupt_row_fails_closed",
                "test_tampered_record_identity_fails_closed",
                "test_capacity_exhaustion_fails_closed",
                "test_owner_thread_and_single_writer",
                "test_errors_logs_and_files_carry_no_canary",
            )
            tests("9 all attempt-custody tests", UNIT)
            tests(
                "10 invocation plane: admitted disclosure only; LOCAL; REMOTE refused",
                PLANE,
            )
            tests(
                "11 ownership and import boundaries",
                ARCH,
                "tests/architecture/test_import_boundaries.py",
                "tests/architecture/test_remote_disclosure.py",
                "tests/architecture/test_local_host.py",
            )
            tests(
                "12 disclosure gate/governance, S1 and Secret regressions",
                "tests/integration/composition/test_remote_disclosure_gate.py",
                "tests/integration/composition/test_remote_disclosure.py",
                "tests/unit/governance/test_disclosure.py",
                "tests/unit/reference/test_secret_source_s1.py",
                "tests/architecture/test_secret_source_s1.py",
                "tests/unit/reference/test_secret_ref.py",
                "tests/architecture/test_secret_ref.py",
            )
            tests(
                "13 durable custody and codec regressions",
                "tests/unit/reference/test_secret_durable_custody.py",
                "tests/architecture/test_secret_durable_custody.py",
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
                    PLANE,
                    ARCH,
                    "tests/support/remote_attempt_scenario.py",
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
        "REMOTE-ATTEMPT-CUSTODY-1 LOCAL VALIDATION PASSED - offline; synthetic "
        "canaries; no transport, provider, network or Secret realization"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
