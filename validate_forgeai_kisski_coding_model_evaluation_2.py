"""Maintainer-only offline v2 gate; no credential or provider operations."""

import os
import subprocess
import sys
from pathlib import Path

from scripts.kisski_coding_eval import frozen as v1
from scripts.kisski_coding_eval_v2 import ENGINEERING_SRC, frozen

ROOT = Path(__file__).resolve().parent
BASE = "8edc557f05a3c2ae412b67c08dbe3a7eea678b5a"
DIRECTORY = "scripts/kisski_coding_eval_v2"
TEST = "scripts/tests/test_kisski_coding_evaluation_v2.py"
DOCUMENT = "planning/FORGEAI-KISSKI-CODING-MODEL-EVALUATION-2.md"
TARGETS = (
    f"{DIRECTORY}/__init__.py",
    f"{DIRECTORY}/pack.py",
    f"{DIRECTORY}/scoring.py",
    f"{DIRECTORY}/frozen.py",
    f"{DIRECTORY}/invocation.py",
    f"{DIRECTORY}/runner.py",
    TEST,
    "validate_forgeai_kisski_coding_model_evaluation_2.py",
)
ALLOWED = frozenset((*TARGETS, DOCUMENT, f"{DIRECTORY}/manifest.json"))
PRESERVED = (
    "scripts/kisski_coding_eval",
    "scripts/kisski_dev_screen",
    "experiments",
    "packages",
    "src",
    "examples",
    "scripts/forgeai_kisski_bounded_live_pilot.py",
    "scripts/tests/test_kisski_coding_evaluation.py",
    "scripts/tests/test_kisski_dev_screen.py",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True, timeout=30
    ).stdout


def main() -> int:
    phase = "scope"

    def run(name: str, command: list[str]) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + phase, flush=True)
        environment = dict(os.environ)
        for variable in ("PYTHONPATH", "MYPYPATH"):
            existing = environment.get(variable)
            environment[variable] = str(ENGINEERING_SRC) + (
                os.pathsep + existing if existing else ""
            )
        subprocess.run(command, cwd=ROOT, env=environment, check=True, timeout=1200)

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
        phase = "v1 frozen manifest"
        print("\n[PHASE] " + phase, flush=True)
        actual = v1.verify()
        if actual != frozen.V1_DIGEST:
            raise ValueError("v1 identity changed")
        print(actual)
        run(
            "v2, v1 and dev-screen contracts",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                TEST,
                "scripts/tests/test_kisski_coding_evaluation.py",
                "scripts/tests/test_kisski_dev_screen.py",
            ],
        )
        run("strict typing", [sys.executable, "-m", "mypy", *TARGETS])
        run("lint", [sys.executable, "-m", "ruff", "check", "--no-cache", *TARGETS])
        run(
            "format",
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *TARGETS,
            ],
        )
        phase = "whitespace"
        print("\n[PHASE] " + phase, flush=True)
        git("diff", "--check", BASE)
        git("diff", "--cached", "--check", BASE)
        print("\n[PHASE] manifest report", flush=True)
        try:
            frozen.verify()
        except frozen.ManifestNotFrozen:
            print("V2 MANIFEST FROZEN: NO")
        else:
            print("V2 MANIFEST FROZEN: YES")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL [{phase}]: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-KISSKI-CODING-MODEL-EVALUATION-2 LOCAL CHECKS PASSED; "
        "V1 AND DEV SCREEN UNCHANGED; NO PROVIDER CALLS; NO ADMISSION EFFECT"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
