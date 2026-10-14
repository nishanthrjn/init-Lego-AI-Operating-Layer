"""Maintainer-only offline shape diagnostics validation; no provider calls."""

import ast
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_forgeai_kisski_saia_chat_contract_diagnostic_1 import definitions, git
from validate_forgeai_remote_model_profile_1 import LOCAL_TESTS, REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
BASELINE = "dc79ba1495a7865fb042229ec7eedef1f909544f"
ADAPTER = "src/legoai/reference/model_openai_compatible.py"
TEST = "scripts/tests/test_kisski_saia_function_call_shapes.py"
SELF = "validate_forgeai_kisski_saia_function_call_shape_diagnostic_1.py"
DOCUMENT = "planning/FORGEAI-KISSKI-SAIA-FUNCTION-CALL-SHAPE-DIAGNOSTIC-1.md"
TARGETS = (ADAPTER, TEST, SELF)
ALLOWED = {*TARGETS, DOCUMENT}


def acceptance(source: str) -> str:
    """Remove only the new observation/reset statements from the chat method."""
    tree = ast.parse(source)
    owner = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "OpenAICompatibleModelAdapter"
    )
    chat = next(
        node
        for node in owner.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "chat"
    )
    reset = ast.dump(ast.parse("self._call_shapes = None").body[0])
    observation = ast.dump(
        ast.parse(
            "try:\n    self._record_call_shapes(message)\n"
            "except Exception:\n    self._call_shapes = None\n"
        ).body[0]
    )
    chat.body = [
        node for node in chat.body if ast.dump(node) not in {reset, observation}
    ]
    return ast.dump(chat)


def scope() -> None:
    changed = set(git("diff", "--name-only", "--no-renames", BASELINE).splitlines())
    changed.update(
        git("diff", "--cached", "--name-only", "--no-renames", BASELINE).splitlines()
    )
    changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    if changed - ALLOWED:
        raise ValueError("outside four-file shape scope: " + repr(changed - ALLOWED))
    before = git("show", f"{BASELINE}:{ADAPTER}")
    after = (ROOT / ADAPTER).read_text(encoding="utf-8")
    if acceptance(before) != acceptance(after):
        raise ValueError("chat acceptance logic changed")
    prior, current = definitions(before), definitions(after)
    permitted = {
        "OpenAICompatibleModelAdapter",
        "OpenAICompatibleModelAdapter.__init__",
        "OpenAICompatibleModelAdapter.chat",
        "OpenAICompatibleModelAdapter._chat_contract_items",
    }
    for name, value in prior.items():
        if name not in permitted and current.get(name) != value:
            raise ValueError("existing adapter contract changed: " + name)
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
    phase = "four-file scope; acceptance, T2, custody, APIs and ADRs preserved"

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
                ("function_call and tool_calls shapes; safe runner", (TEST,)),
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
        "FORGEAI-KISSKI-SAIA-FUNCTION-CALL-SHAPE-DIAGNOSTIC-1 LOCAL CHECKS PASSED; "
        "FUNCTION_CALL_SHAPE_DIAGNOSTIC_READY; ACCEPTANCE UNCHANGED; "
        "NO LIVE CONNECTIVITY OR CODING QUALITY QUALIFIED; "
        "NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
