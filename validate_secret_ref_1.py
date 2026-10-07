r"""Operator Stage-A qualification: uv run python .\validate_secret_ref_1.py.



Offline synthetic use only. Existing provider regressions use fake loopback HTTP.

No dependency installation, external provider, credentials or Docker.

"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_secret_use_durable_custody_1 import IMPLEMENTATION_TEST_DIRECTORIES

ROOT = Path(__file__).resolve().parent

BASE = "aab6583"

UNIT = "tests/unit/reference/test_secret_ref.py"

ARCH = "tests/architecture/test_secret_ref.py"

DURABLE = "tests/unit/reference/test_secret_durable_custody.py"

PRODUCTION = (
    "src/legoai/governance/secret.py",
    "src/legoai/governance/ports.py",
    "src/legoai/reference/_secret_domain.py",
    "src/legoai/reference/_secret_ledger.py",
    "src/legoai/reference/governance.py",
    "src/legoai/reference/catalog.py",
    "src/legoai/reference/secret.py",
    "src/legoai/runtime/_composition/secret.py",
)

PYTHON = (
    *PRODUCTION,
    UNIT,
    ARCH,
    "tests/support/secret_ref_scenario.py",
    "tests/architecture/test_import_boundaries.py",
    "validate_secret_ref_1.py",
)

ALLOWED = set(PYTHON) | {
    "docs/secret-ref-1a.md",
    "planning/LEGOAI-SECRET-REF-1-DECISION.md",
    "planning/LEGOAI-SECRET-REF-1A-ARBITRATION-DECISION.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
}


def git(*args: str) -> str:

    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf8",
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


def main() -> int:

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    completed: list[str] = []

    phase = "scope precheck"

    env = os.environ.copy()

    env.pop("VIRTUAL_ENV", None)

    env.update(UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")

    verified: set[tuple[str, tuple[str, ...]]] = set()

    try:
        scope()

        with tempfile.TemporaryDirectory(
            prefix=".custody-validation-secret-ref-",
            dir=ROOT,
            ignore_cleanup_errors=True,
        ) as directory:
            temp = Path(directory)

            def run(
                number: int, label: str, args: tuple[str, ...], cwd: Path = ROOT
            ) -> None:

                nonlocal phase

                phase = f"{number} {label}"

                print("[PHASE] " + phase, flush=True)

                key = (str(cwd), args)

                if key not in verified:
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
                            str(temp / f"phase-{number}"),
                            *args,
                        ],
                        cwd=cwd,
                        env=env,
                        check=True,
                    )

                    verified.add(key)

                else:
                    print(
                        "Previously passed identical test selection in this execution.",
                        flush=True,
                    )

                completed.append(phase)

            run(1, "accepted Secret scope", (ARCH, "-k", "accepted_secret_scope"))

            run(2, "accepted arbitration scope", (ARCH, "-k", "accepted_arbitration"))

            run(
                3,
                "durable prerequisite locally qualified",
                (ARCH, "-k", "qualified_durable_prerequisite"),
            )

            phase = "4 scope guard"

            print("[PHASE] " + phase, flush=True)

            scope()

            completed.append(phase)

            # Full focused suite is executed once. Every subsequent requirement

            # phase references that same successful selection, never a prior run.

            labels = (
                "public reference-only operations",
                "no public material API",
                "exact revision only",
                "SecretRef invariants",
                "exact-use invariants",
                "safe reprs",
                "shared-domain identity",
                "no bypass mutation path",
                "Grant revoke ordering",
                "Policy supersession ordering",
                "Catalog withdrawal ordering",
                "mapping invalidation ordering",
                "revision invalidation ordering",
                "Approval consumption ordering",
                "competing exact uses",
                "expiry before acceptance",
                "expiry after acceptance",
                "cancellation before acceptance",
                "cancellation after acceptance",
                "pre-use custody receipt",
                "forged/wrong receipt refusal",
                "durable acceptance uniqueness",
                "post-use Evidence success",
                "post-use Evidence failure",
                "repair closes exact duty",
                "repair never repeats use",
                "lost acknowledgment recovery",
                "restart accepted-state recovery",
                "restart does not restore authority",
                "restart does not restore material/handles",
                "restart does not repeat use",
                "Approval not refunded",
                "canary absent from DB",
                "canary absent from journals",
                "canary absent from SQL trace",
                "canary absent from logs/errors",
                "canary absent from evidence/reports",
                "wrong tenant denial",
                "wrong requester denial",
                "wrong purpose denial",
                "wrong consumer denial",
                "wrong target/account denial",
                "wrong configuration denial",
                "stale revision denial",
                "missing authority denial",
            )

            for number, label in enumerate(labels, 5):
                run(number, label, (UNIT,))

            run(
                50,
                "owner/import boundaries",
                (
                    ARCH,
                    "tests/architecture/test_import_boundaries.py",
                    "tests/architecture/test_secret_durable_custody.py",
                ),
            )

            run(
                51,
                "credential-free runtime and participating-owner regressions",
                (
                    "tests/unit/governance",
                    "tests/unit/reference/test_governance_registries.py",
                    "tests/unit/reference/test_execution.py",
                    "tests/unit/reference/test_coordinator.py",
                    "tests/contract/test_catalog.py",
                    "tests/integration/composition/test_local_host.py",
                    "tests/integration/composition/test_model_governed.py",
                    "tests/integration/composition/test_model_selection.py",
                ),
            )

            run(
                52,
                "Model regressions",
                (
                    "tests/unit/reference/test_model.py",
                    "tests/unit/reference/test_model_foundation.py",
                ),
            )

            run(
                53,
                "Agent regressions",
                (
                    "tests/unit/execution/test_agent.py",
                    "tests/integration/composition/test_agent.py",
                    "tests/architecture/test_agent.py",
                ),
            )

            run(
                54,
                "OpenAI-compatible regressions",
                (
                    "tests/unit/reference/test_openai_compatible.py",
                    "tests/integration/composition/test_openai_compatible.py",
                ),
            )

            run(
                55,
                "ForgeAI regressions",
                (
                    "tests/test_architecture.py",
                    "tests/test_worker.py",
                    "tests/test_review.py",
                    "tests/test_rework.py",
                ),
                ROOT / "examples/forgeai",
            )

            run(
                56,
                "DocuMind regressions",
                ("tests/unit", "tests/integration"),
                ROOT / "examples/documind",
            )

            run(57, "durable custody regression", (DURABLE,))

            run(58, "crash/recovery regression subset", (DURABLE, "-k", "crash_matrix"))

            for number, label, args in (
                (
                    59,
                    "mypy",
                    (
                        "mypy",
                        "--cache-dir",
                        str(temp / "mypy"),
                        "src",
                        Path(__file__).name,
                    ),
                ),
                (60, "Ruff lint", ("ruff", "check", "--no-cache", *PYTHON)),
                (
                    61,
                    "Ruff format",
                    ("ruff", "format", "--check", "--no-cache", *PYTHON),
                ),
            ):
                phase = f"{number} {label}"

                print("[PHASE] " + phase, flush=True)

                subprocess.run(
                    [sys.executable, "-B", "-m", *args], cwd=ROOT, env=env, check=True
                )

                completed.append(phase)

            phase = "62 git diff check"

            print("[PHASE] " + phase, flush=True)

            git("diff", "--check", BASE)

            completed.append(phase)

    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        for label in completed:
            print("PASS " + label)

        print("FAIL " + phase + ": " + str(error))

        return 1

    for label in completed:
        print("PASS " + label)

    print(
        "SECRET-REF-1A LOCALLY QUALIFIED — synthetic owner-thread acceptance; intact local-storage only; Stage B remains gated"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
