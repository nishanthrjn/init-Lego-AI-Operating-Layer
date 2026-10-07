r"""Operator qualification: uv run python .\validate_secret_use_durable_custody_1.py.

No external provider, credentials or Docker. Existing credential-free regression
fixtures may use loopback fake HTTP. New custody qualification uses local files
and explicitly terminated child processes only. No dependency installation.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "ffc221b"
PRODUCTION = (
    "src/legoai/governance/secret.py",
    "src/legoai/evidence/custody.py",
    "src/legoai/reference/_custody_codec.py",
    "src/legoai/reference/_custody_sqlite.py",
    "src/legoai/reference/_secret_domain.py",
    "src/legoai/reference/_durable_evidence.py",
    "src/legoai/reference/_secret_ledger.py",
)
UNIT = "tests/unit/reference/test_secret_durable_custody.py"
ARCH = "tests/architecture/test_secret_durable_custody.py"
PYTHON = (
    *PRODUCTION,
    UNIT,
    ARCH,
    "tests/support/custody_scenario.py",
    "tests/architecture/test_import_boundaries.py",
    Path(__file__).name,
)
ALLOWED = set(PYTHON) | {
    "planning/LEGOAI-SECRET-USE-DURABLE-CUSTODY-DECISION.md",
    "planning/LEGOAI-SECRET-REF-1A-ARBITRATION-DECISION.md",
    "planning/LEGOAI-SECRET-REF-1-DECISION.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
}
# Exact implementation-test artifacts only. Windows sandbox ACLs prevented
# cleanup; these paths are never implementation input or qualification evidence.
IMPLEMENTATION_TEST_DIRECTORIES = (
    ".custody-test-temp",
    ".custody-test-temp-2",
    ".custody-test-temp-3",
    ".custody-regression-temp",
    ".custody-forgeai-temp",
    ".custody-documind-temp",
    ".custody-final-test-temp",
    ".custody-verified-test-temp",
    ".custody-crash-verified-temp",
    ".custody-final-static-temp",
    ".custody-scope-final-temp",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
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
            *(f":(exclude){name}/**" for name in IMPLEMENTATION_TEST_DIRECTORIES),
        ).splitlines()
    )
    if changed - ALLOWED:
        raise RuntimeError("unexpected scope: " + repr(sorted(changed - ALLOWED)))
    if git(
        "diff",
        "--name-only",
        BASE,
        "src/legoai/reference/application",
        "src/legoai/application",
        "src/legoai/runtime",
        "src/legoai/reference/governance.py",
        "src/legoai/reference/catalog.py",
        "src/legoai/reference/execution.py",
        "adrs",
    ):
        raise RuntimeError("protected existing production scope changed")


def main() -> int:
    completed: list[str] = []
    phase = "scope precheck"
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
    try:
        scope()
        with tempfile.TemporaryDirectory(
            prefix=".custody-validation-", dir=ROOT
        ) as directory:
            temp = Path(directory)
            # Reused requirements cite a previously executed exact test selector;
            # they do not run the same disk/crash test repeatedly.
            executed: set[tuple[str, ...]] = set()

            def run(
                number: int, label: str, selectors: tuple[str, ...], *, cwd: Path = ROOT
            ) -> None:
                nonlocal phase
                phase = f"{number} {label}"
                print("[PHASE] " + phase, flush=True)
                key = (str(cwd), *selectors)
                if key not in executed:
                    python = (
                        Path(sys.executable)
                        if cwd == ROOT
                        else cwd
                        / ".venv"
                        / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
                    )
                    subprocess.run(
                        [
                            str(python),
                            "-B",
                            "-m",
                            "pytest",
                            "-q",
                            "-p",
                            "no:cacheprovider",
                            "--basetemp",
                            str(temp / str(number)),
                            *selectors,
                        ],
                        cwd=cwd,
                        env=env,
                        check=True,
                    )
                    executed.add(key)
                else:
                    print("Covered by identical passing selector earlier in this run.")
                completed.append(phase)

            def test(number: int, label: str, name: str, file: str = UNIT) -> None:
                run(number, label, (file + "::" + name,))

            test(1, "accepted decision identity", "test_accepted_decision", ARCH)
            phase = "2 scope guard"
            print("[PHASE] " + phase)
            completed.append(phase)  # scope() passed before allocating temp files
            for number, label, name, file in (
                (3, "owner separation", "test_owner_separation", ARCH),
                (4, "public API guard", "test_public_surface", ARCH),
                (5, "separate stores", "test_owners_separate", UNIT),
                (6, "ConfigurationStore unchanged", "test_owner_separation", ARCH),
                (7, "no generic transaction API", "test_public_surface", ARCH),
                (8, "schema/version guards", "test_corruption_is_gap[schema]", UNIT),
                (9, "SQLite profile", "test_storage_profile_and_one_writer", UNIT),
                (10, "one writer", "test_storage_profile_and_one_writer", UNIT),
                (11, "source preparation", "test_source_duplicate_conflict", UNIT),
                (12, "pre-use durable receipt", "test_receipt_and_repair", UNIT),
                (
                    13,
                    "unacknowledged pre-use refusal",
                    "test_preuse_refusal_and_domain",
                    UNIT,
                ),
                (14, "atomic acceptance", "test_source_atomic_acceptance", UNIT),
                (
                    15,
                    "no independent callback",
                    "test_no_independent_consumer_callback",
                    ARCH,
                ),
                (16, "exact-use uniqueness", "test_source_atomic_acceptance", UNIT),
                (
                    17,
                    "source equivalent duplicate",
                    "test_source_duplicate_conflict",
                    UNIT,
                ),
                (18, "source conflict", "test_source_duplicate_conflict", UNIT),
                (19, "outstanding source duty", "test_source_atomic_acceptance", UNIT),
                (20, "Evidence custody", "test_receipt_and_repair", UNIT),
                (21, "receipt recovery", "test_crash_matrix[10]", UNIT),
                (22, "Evidence equivalent duplicate", "test_receipt_and_repair", UNIT),
                (23, "Evidence conflict", "test_evidence_conflict", UNIT),
                (
                    24,
                    "matching receipt/revision",
                    "test_matching_receipt_and_revision",
                    UNIT,
                ),
                (25, "prepared-only", "test_prepared_intervention_and_no_replay", UNIT),
                (26, "accepted/outstanding", "test_source_atomic_acceptance", UNIT),
                (27, "accepted/attributed", "test_receipt_and_repair", UNIT),
                (28, "intervention", "test_prepared_intervention_and_no_replay", UNIT),
                (29, "UNKNOWN/corrupt", "test_corruption_is_gap", UNIT),
                (30, "no replay from recovery", "test_crash_matrix[2]", UNIT),
                (
                    31,
                    "no authority restoration",
                    "test_readonly_inspection_cannot_mutate",
                    UNIT,
                ),
                (32, "Approval partial consumption", "test_crash_matrix[4]", UNIT),
            ):
                test(number, label, name, file)
            for point in range(1, 14):
                test(32 + point, f"crash point {point}", f"test_crash_matrix[{point}]")
            for number, label, name, file in (
                (46, "source lost acknowledgment", "test_crash_matrix[7]", UNIT),
                (47, "Evidence lost receipt", "test_crash_matrix[10]", UNIT),
                (48, "duty-close lost acknowledgment", "test_crash_matrix[13]", UNIT),
                (49, "missing history", "test_corruption_is_gap[missing]", UNIT),
                (50, "corrupt store", "test_corruption_is_gap", UNIT),
                (51, "schema mismatch", "test_corruption_is_gap[schema]", UNIT),
                (52, "tenant/disclosure", "test_disclosure_scope", UNIT),
                (53, "source material canary", "test_material_canary", UNIT),
                (54, "Evidence material canary", "test_material_canary", UNIT),
                (55, "journal canary", "test_material_canary", UNIT),
                (56, "output/log canary", "test_material_canary", UNIT),
                (
                    57,
                    "no environment source",
                    "test_no_provider_environment_or_network",
                    ARCH,
                ),
                (58, "no credential header", "test_public_surface", ARCH),
                (59, "no custody network and full focused suite", "", UNIT),
            ):
                if name:
                    test(number, label, name, file)
                else:
                    run(
                        number,
                        label,
                        (UNIT, ARCH, "tests/architecture/test_import_boundaries.py"),
                    )
            run(
                60,
                "existing Evidence",
                ("tests/unit/evidence", "tests/unit/reference/test_evidence.py"),
            )
            run(
                61,
                "Governance",
                (
                    "tests/unit/governance",
                    "tests/unit/reference/test_governance_registries.py",
                ),
            )
            run(
                62,
                "Execution",
                (
                    "tests/unit/reference/test_execution.py",
                    "tests/unit/reference/test_coordinator.py",
                ),
            )
            run(63, "Catalog", ("tests/contract/test_catalog.py",))
            run(
                64,
                "ConfigurationStore",
                (
                    "tests/unit/application",
                    "tests/contract/test_configuration_store.py",
                ),
            )
            run(
                65,
                "runtime hosts",
                (
                    "tests/integration/composition/test_local_host.py",
                    "tests/integration/composition/test_model_governed.py",
                    "tests/integration/composition/test_model_selection.py",
                ),
            )
            run(
                66,
                "OpenAI-compatible credential-free",
                (
                    "tests/unit/reference/test_openai_compatible.py",
                    "tests/integration/composition/test_openai_compatible.py",
                ),
            )
            run(
                67,
                "Ollama credential-free",
                (
                    "tests/unit/reference/test_model.py",
                    "tests/unit/reference/test_model_foundation.py",
                ),
            )
            run(
                68,
                "ForgeAI regressions",
                (
                    "tests/test_architecture.py",
                    "tests/test_worker.py",
                    "tests/test_review.py",
                    "tests/test_rework.py",
                ),
                cwd=ROOT / "examples/forgeai",
            )
            # Same phase includes the lightweight credential-free DocuMind suites.
            run(
                68,
                "DocuMind regressions",
                ("tests/unit", "tests/integration"),
                cwd=ROOT / "examples/documind",
            )
            completed.pop()  # one numbered phase covers both consumers
            completed[-1] = "68 ForgeAI and DocuMind regressions"
            for number, label, args in (
                (
                    69,
                    "mypy",
                    [
                        "mypy",
                        "--cache-dir",
                        str(temp / "mypy"),
                        "src",
                        str(Path(__file__).resolve()),
                    ],
                ),
                (70, "Ruff lint", ["ruff", "check", "--no-cache", *PYTHON]),
                (
                    71,
                    "Ruff format",
                    ["ruff", "format", "--check", "--no-cache", *PYTHON],
                ),
            ):
                phase = f"{number} {label}"
                print("[PHASE] " + phase, flush=True)
                subprocess.run(
                    [sys.executable, "-B", "-m", *args], cwd=ROOT, env=env, check=True
                )
                completed.append(phase)
            phase = "72 git diff check"
            print("[PHASE] " + phase, flush=True)
            git("diff", "--check", BASE)
            completed.append(phase)
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        for name in completed:
            print("PASS " + name)
        print("FAIL " + phase + ": " + str(error))
        return 1
    for name in completed:
        print("PASS " + name)
    print(
        "SECRET-USE-DURABLE-CUSTODY-1 LOCALLY QUALIFIED — intact local-storage crash/restart only; Stage A not resumed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
