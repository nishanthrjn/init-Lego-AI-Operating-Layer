"""Maintainer-only offline shape diagnostics validation; no provider calls."""

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.kisski_coding_eval.frozen import verify
from validate_forgeai_kisski_saia_chat_contract_diagnostic_1 import definitions, git
from validate_forgeai_remote_model_profile_1 import LOCAL_TESTS, REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
BASELINE = "023a6cf403831c478cc886544a926cac3a4bc953"
ADAPTER = "src/legoai/reference/model_openai_compatible.py"
TEST = "scripts/tests/test_openai_finish_reason_diagnostics.py"
SELF = "validate_openai_compat_finish_reason_shape_diagnostic_1.py"
DOCUMENT = "planning/OPENAI-COMPAT-FINISH-REASON-SHAPE-DIAGNOSTIC-1.md"
RUNNER = "scripts/kisski_coding_eval/runner.py"
MANIFEST = "scripts/kisski_coding_eval/manifest.json"
CALL_TEST = "scripts/tests/test_kisski_saia_function_call_shapes.py"
TARGETS = (ADAPTER, RUNNER, TEST, CALL_TEST, SELF)
ALLOWED = {*TARGETS, DOCUMENT, MANIFEST}


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
    reset = ast.dump(ast.parse("self._finish_category = None").body[0])
    observation = ast.dump(
        ast.parse(
            "try:\n    self._record_finish_category(choice)\n"
            "except Exception:\n    self._finish_category = None\n"
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
        raise ValueError(
            "outside seven-file finish diagnostic scope: " + repr(changed - ALLOWED)
        )
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
    prior_pins = json.loads(git("show", f"{BASELINE}:{MANIFEST}"))
    current_pins = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))
    if set(prior_pins) != set(current_pins) or any(
        current_pins[name] != value
        for name, value in prior_pins.items()
        if name != RUNNER
    ):
        raise ValueError("frozen task/scoring or contract pins changed")
    verify()
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
    phase = "seven-file scope; acceptance, tasks, scoring, T2 and custody preserved"

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
                ("finish categories, acceptance and evaluation projection", (TEST,)),
                ("function_call null and safe qualification runner", (CALL_TEST,)),
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
        "OPENAI-COMPAT-FINISH-REASON-SHAPE-DIAGNOSTIC-1 LOCALLY QUALIFIED; "
        "DIAGNOSTICS ONLY; FINISH_REASON ACCEPTANCE UNCHANGED; "
        "NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
