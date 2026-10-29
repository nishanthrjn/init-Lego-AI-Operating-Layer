"""Maintainer-only offline v3 gate; historical freezes are preserved, not run."""

import os
import subprocess
import sys
from pathlib import Path

from scripts.kisski_coding_eval_v3 import ENGINEERING_SRC, frozen

ROOT = Path(__file__).resolve().parent
BASE = "3aa7ee0780092266a63c7a16462523e694724624"
DIRECTORY = "scripts/kisski_coding_eval_v3"
TEST = "scripts/tests/test_kisski_coding_evaluation_v3.py"
DOCUMENT = "planning/FORGEAI-KISSKI-CODING-MODEL-EVALUATION-3.md"
RESULTS = "planning/FORGEAI-KISSKI-CODING-MODEL-EVALUATION-2-RESULTS.md"
DEFINITION = "packages/legoai-engineering/src/legoai_engineering/reviewer/definition.py"
ENGINEERING_TEST = "packages/legoai-engineering/tests/test_reviewer.py"
TARGETS = (
    f"{DIRECTORY}/__init__.py",
    f"{DIRECTORY}/pack.py",
    f"{DIRECTORY}/scoring.py",
    f"{DIRECTORY}/frozen.py",
    f"{DIRECTORY}/invocation.py",
    f"{DIRECTORY}/runner.py",
    TEST,
    DEFINITION,
    "validate_forgeai_kisski_coding_model_evaluation_3.py",
)
ALLOWED = frozenset(
    (*TARGETS, DOCUMENT, RESULTS, ENGINEERING_TEST, f"{DIRECTORY}/manifest.json")
)
PRESERVED = (
    "scripts/kisski_coding_eval",
    "scripts/kisski_coding_eval_v2",
    "scripts/kisski_dev_screen",
    "experiments",
    "src",
    "examples",
    "planning/FORGEAI-KISSKI-CODING-MODEL-EVALUATION-2.md",
    "scripts/forgeai_kisski_bounded_live_pilot.py",
    "scripts/tests/test_kisski_coding_evaluation.py",
    "scripts/tests/test_kisski_coding_evaluation_v2.py",
    "scripts/tests/test_kisski_dev_screen.py",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True, timeout=30
    ).stdout


def main() -> int:
    phase = "scope"

    def run(name: str, command: list[str], cwd: Path = ROOT) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + phase, flush=True)
        environment = dict(os.environ)
        python_paths = (
            ENGINEERING_SRC,
            ROOT,
            ROOT / "src",
            ROOT / "packages/legoai-engineering/examples",
            ROOT / "examples/forgeai/src",
        )
        for variable, paths in (
            ("PYTHONPATH", python_paths),
            ("MYPYPATH", (ENGINEERING_SRC,)),
        ):
            existing = environment.get(variable)
            environment[variable] = os.pathsep.join(str(path) for path in paths) + (
                os.pathsep + existing if existing else ""
            )
        subprocess.run(command, cwd=cwd, env=environment, check=True, timeout=1200)

    try:
        print("[PHASE] scope", flush=True)
        changed = set(git("diff", "--name-only", "--no-renames", BASE).splitlines())
        changed.update(
            git("diff", "--cached", "--name-only", "--no-renames", BASE).splitlines()
        )
        changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
        if changed - ALLOWED:
            raise ValueError("outside scope: " + repr(sorted(changed - ALLOWED)))
        for name in ALLOWED:
            path = ROOT / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("missing or linked slice file: " + name)
        phase = "preservation"
        print("\n[PHASE] " + phase, flush=True)
        git("diff", "--quiet", BASE, "--", *PRESERVED)
        git("diff", "--cached", "--quiet", BASE, "--", *PRESERVED)
        # Historical verify() would reject the intentional production change.
        run(
            "Engineering reviewer tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_reviewer.py",
            ],
            ROOT / "packages/legoai-engineering",
        )
        run(
            "v3 contracts",
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", TEST],
        )
        run(
            "ForgeAI reviewer regressions (offline replay only)",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_review.py",
                "tests/test_worker.py",
                "tests/test_rework.py",
                "tests/test_run_report.py",
                "tests/test_architecture.py",
                "-k",
                "not real_docker and not real_sandbox",
            ],
            ROOT / "examples/forgeai",
        )
        run("strict typing", [sys.executable, "-m", "mypy", *TARGETS])
        run("lint", [sys.executable, "-m", "ruff", "check", "--no-cache", *TARGETS])
        run(
            "format",
            [sys.executable, "-m", "ruff", "format", "--check", "--no-cache", *TARGETS],
        )
        phase = "whitespace"
        print("\n[PHASE] " + phase, flush=True)
        git("diff", "--check", BASE)
        git("diff", "--cached", "--check", BASE)
        print("\n[PHASE] manifest report", flush=True)
        try:
            frozen.verify()
        except frozen.ManifestNotFrozen:
            print("V3 MANIFEST FROZEN: NO")
        else:
            print("V3 MANIFEST FROZEN: YES")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL [{phase}]: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-REVIEWER-SECURITY-CATEGORY-1 + "
        "FORGEAI-KISSKI-CODING-MODEL-EVALUATION-3 LOCAL CHECKS PASSED; "
        "V1/V2 HISTORICAL; NO PROVIDER CALLS; NO ADMISSION EFFECT"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
