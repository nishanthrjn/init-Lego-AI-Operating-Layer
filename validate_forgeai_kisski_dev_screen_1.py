"""Maintainer-only offline checks; never provisions or calls a live provider.

Typing/lint invocation mirrors validate_forgeai_kisski_coding_model_evaluation_1.py:
sys.executable -m mypy on explicit script, test and validator paths from root.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.kisski_coding_eval.frozen import verify

ROOT = Path(__file__).resolve().parent
BASE = "53e8245399dac55feb6d74e5cf0459ce15e906f9"
DIRECTORY = "scripts/kisski_dev_screen"
TEST = "scripts/tests/test_kisski_dev_screen.py"
DOCUMENT = "planning/FORGEAI-KISSKI-CODING-MODEL-EVALUATION-1.md"
TARGETS = (
    f"{DIRECTORY}/__init__.py",
    f"{DIRECTORY}/diagnostics.py",
    f"{DIRECTORY}/invocation.py",
    f"{DIRECTORY}/runner.py",
    TEST,
    "validate_forgeai_kisski_dev_screen_1.py",
)
ALLOWED = frozenset((*TARGETS, DOCUMENT, f"{DIRECTORY}/candidates.json"))
PRESERVED = (
    "scripts/kisski_coding_eval",
    "experiments",
    "packages",
    "src",
    "examples",
    "scripts/forgeai_kisski_bounded_live_pilot.py",
    ":(glob)**/pyproject.toml",
    ":(glob)**/uv.lock",
    "pyproject.toml",
    "uv.lock",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout


def scope() -> None:
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


def main() -> int:
    phase = "scope"

    def run(name: str, command: list[str]) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + phase, flush=True)
        subprocess.run(command, cwd=ROOT, check=True, timeout=1200)

    try:
        print("[PHASE] scope", flush=True)
        scope()
        phase = "preservation"
        print("\n[PHASE] " + phase, flush=True)
        git("diff", "--quiet", BASE, "--", *PRESERVED)
        git("diff", "--cached", "--quiet", BASE, "--", *PRESERVED)
        phase = "frozen manifest"
        print("\n[PHASE] " + phase, flush=True)
        print(verify())
        with tempfile.TemporaryDirectory(prefix="kisski-dev-screen-") as temporary:
            run(
                "development screen and unchanged evaluation regressions",
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "--basetemp",
                    str(Path(temporary) / "tests"),
                    TEST,
                    "scripts/tests/test_kisski_coding_evaluation.py",
                    "scripts/tests/test_kisski_saia_qualification.py",
                    "scripts/tests/test_kisski_saia_receive_diagnostics.py",
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
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL [{phase}]: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-KISSKI-DEV-SCREEN-1 LOCAL CHECKS PASSED; "
        "FROZEN EVALUATION UNCHANGED; NO PROVIDER CALLS; NO ADMISSION EFFECT"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
