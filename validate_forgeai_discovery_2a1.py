r"""DISCOVERY-2A.1 offline validator. Run uv run python .\validate_forgeai_discovery_2a1.py."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENGINEERING = ROOT / "packages/legoai-engineering"
BASE = "6b9c44110edaea12be4906afd8547c36b0f3a3da"
PREFIX = "examples/forgeai/evaluation/discovery2a_holdout/"
ALLOWED = {
    PREFIX + name
    for name in (
        "__init__.py",
        "data.py",
        "metrics.py",
        "evaluate.py",
        "fixtures-v1.json",
        "truth-v1.json",
        "thresholds-v1.json",
        "preregistration-v1.json",
        "manifest-v1.json",
        "results-v1.json",
        "results-v1.md",
    )
} | {
    "examples/forgeai/evaluation/tests/test_discovery_2a1.py",
    "planning/FORGEAI-TARGET-SELECTION-HELDOUT-EVALUATION.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "validate_forgeai_discovery_2a1.py",
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
        raise RuntimeError("unexpected scope: " + repr(sorted(changed - ALLOWED)))
    protected = (
        "src",
        "packages",
        "adrs",
        "examples/forgeai/src",
        "examples/forgeai/evaluation/discovery2a",
        "examples/forgeai/evaluation/fixtures",
        "examples/forgeai/evaluation/hidden",
        "planning/FORGEAI-TARGET-SELECTION-EVALUATION.md",
    )
    if git("diff", "--name-only", BASE, "--", *protected).strip():
        raise RuntimeError("frozen or production files changed")


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(PYTHONDONTWRITEBYTECODE="1", UV_OFFLINE="1")
    phase = "1 scope guard / production non-interference"
    completed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="discovery-2a1-") as temporary:
        temp = Path(temporary)

        def run(name: str, cwd: Path, *args: str) -> None:
            nonlocal phase
            phase = name
            print("[PHASE] " + name, flush=True)
            subprocess.run(
                ["uv", "run", "--locked", "--no-sync", "python", "-B", "-m", *args],
                cwd=cwd,
                env=env,
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
                *("evaluation/tests/test_discovery_2a1.py::" + s for s in selectors),
            )

        try:
            print("[PHASE] " + phase, flush=True)
            scope()
            completed.append(phase)
            tests("2 original DISCOVERY-2A immutability", "test_frozen_condition")
            tests("3 held-out fixture schema", "test_schema_and_manifest")
            tests("4 fixture non-reuse", "test_non_reuse")
            tests("5 ground truth", "test_ground_truth")
            tests("6 frozen thresholds", "test_frozen_condition")
            tests(
                "7 frozen baseline identity",
                "test_frozen_condition",
                "test_architecture",
            )
            tests("8 deterministic execution", "test_deterministic_security")
            tests("9 candidate membership", "test_adversarial_membership")
            tests(
                "10 security invariants",
                "test_deterministic_security",
                "test_adversarial_membership",
            )
            tests(
                "11 correction calculations",
                "test_correction_operations",
                "test_create",
                "test_p90",
            )
            tests("12 false sufficient", "test_false_sufficient")
            tests("13 acceptable sets", "test_minimal_alternatives")
            tests("14 per-difficulty folding", "test_folding")
            tests("15 aggregate folding", "test_folding")
            tests("16 report consistency", "test_reproduction_rendering")
            tests("17 privacy", "test_privacy")
            run(
                "18 DISCOVERY-1 regressions",
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
                "19 DISCOVERY-2A regressions",
                FORGE,
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "evaluation/tests/test_discovery_2a.py",
            )
            run(
                "20 ForgeAI architecture / evaluation regressions",
                FORGE,
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_architecture.py",
                "evaluation/tests/test_lq1_architecture.py",
                "evaluation/tests/test_discovery_2a1.py",
            )
            run(
                "21 mypy",
                FORGE,
                "mypy",
                "--cache-dir",
                str(temp / "mypy"),
                "evaluation/discovery2a_holdout",
                "evaluation/tests/test_discovery_2a1.py",
                str(ROOT / "validate_forgeai_discovery_2a1.py"),
            )
            run(
                "22 Ruff lint",
                FORGE,
                "ruff",
                "check",
                "--no-cache",
                "evaluation/discovery2a_holdout",
                "evaluation/tests/test_discovery_2a1.py",
                str(ROOT / "validate_forgeai_discovery_2a1.py"),
            )
            run(
                "23 Ruff format",
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                "evaluation/discovery2a_holdout",
                "evaluation/tests/test_discovery_2a1.py",
                str(ROOT / "validate_forgeai_discovery_2a1.py"),
            )
            phase = "24 git diff check"
            subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
            completed.append(phase)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
            print(f"FAIL {phase}: {error}; later phases NOT RUN")
            return 1
    for item in completed:
        print("PASS " + item)
    print("DISCOVERY-2A.1 LOCAL VALIDATION PASSED - no live model; no Docker")
    return 0


if __name__ == "__main__":
    sys.exit(main())
