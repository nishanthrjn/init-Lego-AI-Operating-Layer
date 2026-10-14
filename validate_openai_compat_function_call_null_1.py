"""Maintainer-only null compatibility checks; synthetic local transport only."""

import ast
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_forgeai_kisski_saia_chat_contract_diagnostic_1 import git
from validate_forgeai_remote_model_profile_1 import LOCAL_TESTS, REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
BASELINE = "b9c156c02976150b6a297c2250bc0dfe58c91213"
ADAPTER = "src/legoai/reference/model_openai_compatible.py"
FOCUSED = "scripts/tests/test_openai_function_call_null.py"
SHAPES = "scripts/tests/test_kisski_saia_function_call_shapes.py"
CONTRACT = "scripts/tests/test_kisski_saia_contract_diagnostics.py"
SELF = "validate_openai_compat_function_call_null_1.py"
DOCUMENT = "docs/model-composition.md"
TARGETS = (ADAPTER, FOCUSED, SHAPES, CONTRACT, SELF)
ALLOWED = {*TARGETS, DOCUMENT}


def scope() -> None:
    changed = set(git("diff", "--name-only", "--no-renames", BASELINE).splitlines())
    changed.update(
        git("diff", "--cached", "--name-only", "--no-renames", BASELINE).splitlines()
    )
    changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    if changed - ALLOWED:
        raise ValueError("outside null-only scope: " + repr(changed - ALLOWED))
    before = git("show", f"{BASELINE}:{ADAPTER}")
    old = 'if "function_call" in message:'
    new = 'if "function_call" in message and message["function_call"] is not None:'
    if before.count(old) != 1:
        raise ValueError("baseline legacy gate is not unique")
    expected = ast.dump(ast.parse(before.replace(old, new, 1)))
    after = (ROOT / ADAPTER).read_text(encoding="utf-8")
    if ast.dump(ast.parse(after)) != expected:
        raise ValueError("adapter changes exceed the exact null-only condition")
    staged = set(git("diff", "--cached", "--name-only", BASELINE).splitlines())
    if ADAPTER in staged:
        if ast.dump(ast.parse(git("show", ":" + ADAPTER))) != expected:
            raise ValueError("staged adapter exceeds null-only condition")
    for name in TARGETS:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or symlinked file: " + name)
        source = path.read_text(encoding="utf-8")
        if not source.endswith("\n") or source.endswith("\n\n"):
            raise ValueError("final newline violation: " + name)
        if any(line.rstrip() != line for line in source.splitlines()):
            raise ValueError("trailing whitespace: " + name)


def main() -> int:
    phase = "six-file scope; exact null-only condition; all other production preserved"

    def run(name: str, args: list[str]) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + phase, flush=True)
        subprocess.run(args, cwd=ROOT, check=True, timeout=1200)

    try:
        print("[PHASE] " + phase, flush=True)
        scope()
        with tempfile.TemporaryDirectory(prefix="legacy-null-offline-") as temporary:
            suites = (
                ("focused null compatibility and falsey refusals", (FOCUSED,)),
                ("shape diagnostics, custody and runner outcomes", (SHAPES, CONTRACT)),
                ("adapter SRCP-1 custody and effect regressions", REMOTE_TESTS),
                (
                    "KiSSKI runner and receive regressions",
                    (
                        "scripts/tests/test_kisski_saia_qualification.py",
                        "scripts/tests/test_kisski_saia_receive_diagnostics.py",
                        "scripts/tests/test_kisski_saia_chat_interop.py",
                        "scripts/tests/test_kisski_compatibility_probe.py",
                    ),
                ),
                (
                    "chunked T2 regressions",
                    ("scripts/tests/test_t2_bounded_chunked_response.py",),
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
        "OPENAI-COMPAT-FUNCTION-CALL-NULL-1 LOCALLY QUALIFIED; "
        "LEGACY NULL ONLY; NON-NULL FUNCTION_CALL AND ALL TOOL_CALLS PRESENCE REJECTED; "
        "NO LIVE CONNECTIVITY, TOOL SUPPORT, CODING QUALITY OR GLOBAL COMPATIBILITY "
        "QUALIFIED; NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
