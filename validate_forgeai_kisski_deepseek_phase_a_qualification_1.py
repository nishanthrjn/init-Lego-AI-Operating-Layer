"""Maintainer-only current-baseline checks; no live evaluation or admission."""

import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.kisski_coding_eval.frozen import verify
from validate_forgeai_kisski_coding_model_evaluation_1 import TARGETS, TEST, git
from validate_forgeai_remote_model_profile_1 import REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
BASELINE = "201c4294c4e443ae56f0252a974e5e0e3a5f98ce"
SELF = "validate_forgeai_kisski_deepseek_phase_a_qualification_1.py"
DOCUMENT = "planning/FORGEAI-KISSKI-DEEPSEEK-PHASE-A-QUALIFICATION-1.md"
ALLOWED = {SELF, DOCUMENT}


def scope() -> None:
    changed = set(git("diff", "--name-only", "--no-renames", BASELINE).splitlines())
    changed.update(
        git("diff", "--cached", "--name-only", "--no-renames", BASELINE).splitlines()
    )
    changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    if changed - ALLOWED:
        raise ValueError("outside readiness scope: " + repr(changed - ALLOWED))
    for name in ALLOWED:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or symlinked readiness file: " + name)
        content = path.read_text(encoding="utf-8")
        if not content.endswith("\n") or content.endswith("\n\n"):
            raise ValueError("final newline violation: " + name)
        if any(line.rstrip() != line for line in content.splitlines()):
            raise ValueError("trailing whitespace: " + name)


def main() -> int:
    phase = "two-file readiness scope; frozen harness and pilot admission preserved"

    def run(name: str, command: list[str]) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + phase, flush=True)
        subprocess.run(command, cwd=ROOT, check=True, timeout=1200)

    try:
        print("[PHASE] " + phase, flush=True)
        scope()
        phase = "existing frozen source and canonical contract integrity"
        print("\n[PHASE] " + phase, flush=True)
        print("Frozen source manifest: " + verify())
        suites = (
            ("host lifecycle, exact selection, scoring and partial evidence", (TEST,)),
            (
                "frozen model-quality regressions",
                ("experiments/kaggle/forgeai_model_quality_1/tests",),
            ),
            ("REMOTE custody, disclosure and model regressions", REMOTE_TESTS),
            (
                "safe qualification and finish-reason diagnostics",
                (
                    "scripts/tests/test_kisski_saia_qualification.py",
                    "scripts/tests/test_kisski_saia_contract_diagnostics.py",
                    "scripts/tests/test_openai_finish_reason_diagnostics.py",
                ),
            ),
            ("architecture boundaries", ("tests/architecture",)),
        )
        with tempfile.TemporaryDirectory(prefix="deepseek-readiness-offline-") as tmp:
            for index, (name, paths) in enumerate(suites):
                run(
                    name,
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "-q",
                        "-p",
                        "no:cacheprovider",
                        "--basetemp",
                        str(Path(tmp) / str(index)),
                        *paths,
                    ],
                )
            targets = (*TARGETS, SELF)
            run("typing", [sys.executable, "-m", "mypy", *targets])
            run("lint", [sys.executable, "-m", "ruff", "check", "--no-cache", *targets])
            run(
                "format",
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    "--no-cache",
                    *targets,
                ],
            )
        for phase, args in (
            ("working whitespace", ("diff", "--check", BASELINE)),
            ("staged whitespace", ("diff", "--cached", "--check", BASELINE)),
        ):
            print("\n[PHASE] " + phase, flush=True)
            git(*args)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL: {phase}: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-KISSKI-DEEPSEEK-PHASE-A-QUALIFICATION-1 LOCAL CHECKS PASSED; "
        "NO MODEL QUALITY QUALIFIED; FRESH DISCOVERY STILL REQUIRED; "
        "NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
