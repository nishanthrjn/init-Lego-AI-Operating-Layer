r"""DISCOVERY-2A qualification. Run: uv run python .\validate_forgeai_discovery_2a.py.

No live model, Docker, network synchronization or production changes.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENGINEERING = ROOT / "packages/legoai-engineering"
BASE = "84da572d8071288980425cd62c7b632cf686dc13"
EVAL = "examples/forgeai/evaluation/"
ALLOWED = {
    EVAL + "discovery2a/__init__.py",
    EVAL + "discovery2a/baseline.py",
    EVAL + "discovery2a/fixtures.py",
    EVAL + "discovery2a/evaluate.py",
    EVAL + "discovery2a/fixtures-v1.json",
    EVAL + "discovery2a/results-v1.json",
    EVAL + "tests/test_discovery_2a.py",
    "planning/FORGEAI-TARGET-SELECTION-EVALUATION.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "validate_forgeai_discovery_2a.py",
}


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
        ).splitlines()
    )
    if changed - ALLOWED:
        raise RuntimeError(
            "unexpected files in slice: " + repr(sorted(changed - ALLOWED))
        )


def main() -> int:
    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["UV_OFFLINE"] = "1"
    phase = "1 scope guard"
    completed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="discovery-2a-") as temporary:
        temp = Path(temporary)

        def run(name: str, cwd: Path, *args: str) -> None:
            nonlocal phase
            phase = name
            print("[PHASE] " + name, flush=True)
            subprocess.run(
                ["uv", "run", "--locked", "--no-sync", "python", "-B", "-m", *args],
                cwd=cwd,
                env=environment,
                check=True,
            )
            completed.append(name)

        def tests(name: str, *selectors: str) -> None:
            run(
                name,
                FORGE,
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                *("evaluation/tests/test_discovery_2a.py::" + s for s in selectors),
            )

        try:
            print("[PHASE] " + phase, flush=True)
            scope()
            completed.append(phase)
            tests("2 fixture schema", "test_fixture_schema")
            tests(
                "3 ground truth",
                "test_ground_truth_schema",
                "test_multiple_acceptable_sets",
            )
            tests(
                "4 deterministic baseline",
                "test_determinism_membership_bound",
                "test_tie_top_k_and_unicode",
            )
            tests("5 candidate membership", "test_unknown_forbidden_directory_rejected")
            tests(
                "6 forbidden invariant",
                "test_determinism_membership_bound",
                "test_unknown_forbidden_directory_rejected",
            )
            tests("7 candidate bound", "test_tie_top_k_and_unicode")
            tests("8 insufficient evidence", "test_insufficient_semantics")
            tests("9 CREATE", "test_create")
            tests(
                "10 metric derivation",
                "test_metric_derivation",
                "test_multiple_acceptable_sets",
            )
            tests(
                "11 fold and frozen report", "test_aggregate_fold", "test_frozen_report"
            )
            tests("12 privacy", "test_privacy")
            phase = "13 production non-interference"
            print("[PHASE] " + phase, flush=True)
            if git(
                "diff",
                "--name-only",
                BASE,
                "--",
                "src",
                "packages",
                "adrs",
                "examples/forgeai/src",
                "examples/forgeai/pyproject.toml",
                "examples/forgeai/uv.lock",
            ).strip():
                raise RuntimeError("production/governance files changed")
            tests(phase, "test_evaluation_boundary")
            run(
                "14 DISCOVERY-1 regression",
                ENGINEERING,
                "pytest",
                "-q",
                "-rs",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temp / "tests"),
                "tests/test_structure.py",
                "tests/test_architecture.py",
            )
            run(
                "15 ForgeAI architecture and full evaluation suite",
                FORGE,
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_architecture.py",
                "evaluation/tests/test_lq1_architecture.py",
                "evaluation/tests/test_discovery_2a.py",
            )
            run(
                "16 mypy",
                FORGE,
                "mypy",
                "--cache-dir",
                str(temp / "mypy"),
                "evaluation/discovery2a",
                "evaluation/tests/test_discovery_2a.py",
                str(ROOT / "validate_forgeai_discovery_2a.py"),
            )
            run(
                "17 Ruff lint",
                FORGE,
                "ruff",
                "check",
                "--no-cache",
                "evaluation/discovery2a",
                "evaluation/tests/test_discovery_2a.py",
                str(ROOT / "validate_forgeai_discovery_2a.py"),
            )
            run(
                "18 Ruff format",
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                "evaluation/discovery2a",
                "evaluation/tests/test_discovery_2a.py",
                str(ROOT / "validate_forgeai_discovery_2a.py"),
            )
            phase = "19 git diff check"
            subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
            completed.append(phase)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
            print(f"FAIL {phase}: {error}; later phases NOT RUN")
            return 1
    for name in completed:
        print("PASS " + name)
    print("DISCOVERY-2A LOCAL VALIDATION PASSED — no live model; no Docker")
    return 0


if __name__ == "__main__":
    sys.exit(main())
