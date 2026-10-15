"""Maintainer-only offline evaluation checks; no provider calls or builds."""

import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.kisski_coding_eval.frozen import verify
from validate_forgeai_remote_model_profile_1 import REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
BASELINE = "18fc8e9b53e96e93717075f1be4d521bc9ef16b5"
DIRECTORY = "scripts/kisski_coding_eval"
TEST = "scripts/tests/test_kisski_coding_evaluation.py"
SELF = "validate_forgeai_kisski_coding_model_evaluation_1.py"
DOCUMENT = "planning/FORGEAI-KISSKI-CODING-MODEL-EVALUATION-1.md"
TARGETS = (
    f"{DIRECTORY}/__init__.py",
    f"{DIRECTORY}/pack.py",
    f"{DIRECTORY}/scoring.py",
    f"{DIRECTORY}/runner.py",
    f"{DIRECTORY}/frozen.py",
    TEST,
    SELF,
)
ALLOWED = {*TARGETS, DOCUMENT, f"{DIRECTORY}/manifest.json"}
PRESERVED_REPORTS = {
    "kisski-phase-a-inconclusive-20261015/evaluation.json": (
        "b8521ed721c083db8f795454e4e8030a48661b0b"
    ),
    "kisski-phase-a-partial-20261015/evaluation.json": (
        "a51d4f0a4ef21658b515aa4781498dc5dd3e9f4a"
    ),
}


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
    changed = set(git("diff", "--name-only", "--no-renames", BASELINE).splitlines())
    changed.update(
        git("diff", "--cached", "--name-only", "--no-renames", BASELINE).splitlines()
    )
    untracked = set(git("ls-files", "--others", "--exclude-standard").splitlines())
    changed.update(untracked)
    # These reports are now tracked historical evidence, not evaluation fixtures.
    # Pin both index and working contents; never exempt their parent directories.
    for name, blob in PRESERVED_REPORTS.items():
        if name not in changed:
            continue
        if (
            name in untracked
            or (ROOT / name).is_symlink()
            or git("rev-parse", ":" + name).strip() != blob
            or git("hash-object", "--", name).strip() != blob
        ):
            raise ValueError("preserved report changed: " + name)
        changed.remove(name)
    if changed - ALLOWED:
        raise ValueError("outside evaluation-only scope: " + repr(changed - ALLOWED))
    for name in ALLOWED:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or symlinked slice file: " + name)
        text = path.read_text(encoding="utf-8")
        if not text.endswith("\n") or text.endswith("\n\n"):
            raise ValueError("final newline violation: " + name)
        if any(line.rstrip() != line for line in text.splitlines()):
            raise ValueError("trailing whitespace: " + name)


def main() -> int:
    phase = "evaluation-only scope; production, APIs, dependencies and ADRs preserved"

    def run(name: str, command: list[str]) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + phase, flush=True)
        subprocess.run(command, cwd=ROOT, check=True, timeout=1200)

    try:
        print("[PHASE] " + phase, flush=True)
        scope()
        phase = "frozen fixtures, scorer and canonical proposal/reviewer contract pins"
        print("\n[PHASE] " + phase, flush=True)
        print("Frozen source manifest: " + verify())
        with tempfile.TemporaryDirectory(prefix="kisski-evaluation-offline-") as tmp:
            suites = (
                (
                    "scoring, schemas, in-memory patches, abstention, review, security, inert runner and guards",
                    (TEST,),
                ),
                (
                    "existing frozen ForgeAI model-quality evaluation regressions",
                    ("experiments/kaggle/forgeai_model_quality_1/tests",),
                ),
                ("REMOTE custody, disclosure and model regressions", REMOTE_TESTS),
                (
                    "KiSSKI qualification and safe diagnostics regressions",
                    (
                        "scripts/tests/test_kisski_saia_qualification.py",
                        "scripts/tests/test_kisski_saia_contract_diagnostics.py",
                    ),
                ),
                ("architecture boundaries", ("tests/architecture",)),
            )
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
            run("typing", [sys.executable, "-m", "mypy", *TARGETS])
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
        "FORGEAI-KISSKI-CODING-MODEL-EVALUATION-1 HARNESS LOCALLY QUALIFIED; "
        "NO MODEL QUALITY QUALIFIED; NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
