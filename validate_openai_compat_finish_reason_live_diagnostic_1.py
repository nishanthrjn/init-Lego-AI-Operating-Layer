"""Maintainer-only offline shape diagnostics validation; no provider calls."""

import subprocess
import sys
import tempfile
from pathlib import Path

from validate_forgeai_kisski_saia_chat_contract_diagnostic_1 import git
from validate_forgeai_remote_model_profile_1 import LOCAL_TESTS, REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
BASELINE = "174f2f32cb366123648facbce8e90e3e9db4d21d"
RUNNER = "scripts/openai_finish_reason_live_diagnostic.py"
TEST = "scripts/tests/test_openai_finish_reason_live_diagnostic.py"
SELF = "validate_openai_compat_finish_reason_live_diagnostic_1.py"
DOCUMENT = "planning/OPENAI-COMPAT-FINISH-REASON-LIVE-DIAGNOSTIC-1.md"
TARGETS = (RUNNER, TEST, SELF)
ALLOWED = {*TARGETS, DOCUMENT}


def scope() -> None:
    changed = set(git("diff", "--name-only", "--no-renames", BASELINE).splitlines())
    changed.update(
        git("diff", "--cached", "--name-only", "--no-renames", BASELINE).splitlines()
    )
    changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    if changed - ALLOWED:
        raise ValueError(
            "outside four-file live diagnostic scope: " + repr(changed - ALLOWED)
        )
    for name in ALLOWED:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or symlinked file: " + name)
        source = path.read_text(encoding="utf-8")
        if not source.endswith("\n") or source.endswith("\n\n"):
            raise ValueError("final newline violation: " + name)
        if any(line.rstrip() != line for line in source.splitlines()):
            raise ValueError("trailing whitespace: " + name)


def main() -> int:
    phase = "four-file tooling scope; adapter, acceptance and evaluation unchanged"

    def run(name: str, args: list[str]) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + phase, flush=True)
        subprocess.run(args, cwd=ROOT, check=True, timeout=1200)

    try:
        print("[PHASE] " + phase, flush=True)
        scope()
        with tempfile.TemporaryDirectory(prefix="saia-shapes-offline-") as temporary:
            suites = (
                ("attended diagnostic bounds and safe synthetic flow", (TEST,)),
                (
                    "finish category and acceptance regressions",
                    ("scripts/tests/test_openai_finish_reason_diagnostics.py",),
                ),
                (
                    "evaluation lifecycle and report regressions",
                    ("scripts/tests/test_kisski_coding_evaluation.py",),
                ),
                (
                    "current acceptance and diagnostic fault isolation",
                    ("scripts/tests/test_kisski_saia_contract_diagnostics.py",),
                ),
                ("adapter SRCP-1 custody and effect regressions", REMOTE_TESTS),
                (
                    "chunked T2 regressions",
                    ("scripts/tests/test_t2_bounded_chunked_response.py",),
                ),
                (
                    "KiSSKI runner and receive regressions",
                    (
                        "scripts/tests/test_kisski_saia_qualification.py",
                        "scripts/tests/test_kisski_saia_receive_diagnostics.py",
                        "scripts/tests/test_kisski_saia_chat_interop.py",
                        "scripts/tests/test_kisski_compatibility_probe.py",
                    ),
                ),
                ("LOCAL Ollama preservation", LOCAL_TESTS),
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
                        str(Path(temporary) / str(index)),
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
        "OPENAI-COMPAT-FINISH-REASON-LIVE-DIAGNOSTIC-1 LOCALLY QUALIFIED; "
        "SAFE LIVE DIAGNOSTIC ONLY; FINISH_REASON ACCEPTANCE UNCHANGED; "
        "NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
