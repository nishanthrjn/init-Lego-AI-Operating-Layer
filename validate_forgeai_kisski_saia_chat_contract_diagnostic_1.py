"""Maintainer-only safe contract diagnostics; synthetic TLS, no provider calls."""

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_forgeai_remote_model_profile_1 import LOCAL_TESTS, REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
BASELINE = "b258e55e8cc55f4e0689e5e838a24730edf205b8"
ADAPTER = "src/legoai/reference/model_openai_compatible.py"
PLANE = "src/legoai/runtime/_composition/remote_model.py"
LOCAL = "src/legoai/runtime/local.py"
RUNNER = "scripts/kisski_saia_qualification.py"
TEST = "scripts/tests/test_kisski_saia_contract_diagnostics.py"
SELF = "validate_forgeai_kisski_saia_chat_contract_diagnostic_1.py"
DOCUMENT = "planning/FORGEAI-KISSKI-SAIA-CHAT-CONTRACT-DIAGNOSTIC-1.md"
TARGETS = (ADAPTER, PLANE, LOCAL, RUNNER, TEST, SELF)
ALLOWED = {*TARGETS, DOCUMENT}
# Independently committed instruction edits; not part of the diagnostic slice.
PINNED_INSTRUCTIONS = {
    "AGENTS.md": "f088b2208ddae119ac79f8b9de1789a8f82f0a35",
    "CLAUDE.md": "2dda046c4bf89de4261bc0459a21a9a43921203c",
}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, timeout=30
    ).stdout.decode("utf-8")


def definitions(source: str) -> dict[str, str]:
    result = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result[node.name] = ast.dump(node, include_attributes=False)
            if isinstance(node, ast.ClassDef):
                for member in node.body:
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        result[f"{node.name}.{member.name}"] = ast.dump(
                            member, include_attributes=False
                        )
    return result


def scope() -> None:
    for name, blob in PINNED_INSTRUCTIONS.items():
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or symlinked instruction file: " + name)
        working = git("hash-object", "--path=" + name, name).strip()
        staged = git("rev-parse", ":" + name).strip()
        if working != blob or staged != blob:
            raise ValueError("pinned instruction content changed: " + name)
    changed = set(git("diff", "--name-only", "--no-renames", BASELINE).splitlines())
    changed.update(
        git("diff", "--cached", "--name-only", "--no-renames", BASELINE).splitlines()
    )
    changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    changed.difference_update(PINNED_INSTRUCTIONS)
    if changed - ALLOWED:
        raise ValueError("outside seven-file diagnostic scope: " + repr(changed - ALLOWED))
    preserved = {
        ADAPTER: (
            "_reject",
            "_optional_tokens",
            "_json_object",
            "_invalid_constant",
            "OpenAICompatibleModelConfig",
            "OpenAICompatibleModelAdapter.embed",
            "parse_model_list",
            "parse_model_catalog",
        ),
        PLANE: ("_Invocation", "RemoteModelPlane.embed"),
        LOCAL: (
            "_LocalGovernedHost",
            "_remote_chat_http_status",
            "_remote_chat_receive_diagnostics",
        ),
        RUNNER: ("chat_failure", "chat_stages", "run", "main", "plan_lines"),
    }
    for name, members in preserved.items():
        before = definitions(git("show", f"{BASELINE}:{name}"))
        after = definitions((ROOT / name).read_text(encoding="utf-8"))
        for member in members:
            if before[member] != after[member]:
                raise ValueError(f"protected path changed: {name}:{member}")
    for name in ALLOWED:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or symlinked slice file: " + name)
        source = path.read_text(encoding="utf-8")
        if not source.endswith("\n") or source.endswith("\n\n"):
            raise ValueError("final newline violation: " + name)
        if any(line.rstrip() != line for line in source.splitlines()):
            raise ValueError("trailing whitespace: " + name)
    document = (ROOT / DOCUMENT).read_text(encoding="utf-8")
    if not document.endswith("Final conclusion: SAFE_CONTRACT_DIAGNOSTICS_REQUIRED\n"):
        raise ValueError("diagnostic conclusion missing")


def main() -> int:
    phase = "seven-file diagnostic scope; T2, custody, Secret, APIs and ADRs unchanged"
    env = os.environ.copy()
    env.update(UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")

    def run(name: str, args: list[str]) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + phase, flush=True)
        subprocess.run(args, cwd=ROOT, env=env, check=True, timeout=1200)

    try:
        print("[PHASE] " + phase, flush=True)
        scope()
        with tempfile.TemporaryDirectory(prefix="saia-contract-offline-") as temporary:
            suites = (
                ("contract diagnostics, canaries and effect isolation", (TEST,)),
                ("adapter SRCP-1 custody and effect regressions", REMOTE_TESTS),
                (
                    "chunked T2 regression",
                    ("scripts/tests/test_t2_bounded_chunked_response.py",),
                ),
                (
                    "KiSSKI runner and receive regressions",
                    (
                        "scripts/tests/test_kisski_saia_qualification.py",
                        "scripts/tests/test_kisski_saia_chat_interop.py",
                        "scripts/tests/test_kisski_saia_receive_diagnostics.py",
                        "scripts/tests/test_kisski_compatibility_probe.py",
                    ),
                ),
                ("LOCAL Ollama and Model preservation", LOCAL_TESTS),
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
        "FORGEAI-KISSKI-SAIA-CHAT-CONTRACT-DIAGNOSTIC-1 LOCAL CHECKS PASSED; "
        "SAFE_CONTRACT_DIAGNOSTICS_REQUIRED; SAFE DIAGNOSTICS ONLY; "
        "NO LIVE CONNECTIVITY OR CODING QUALITY QUALIFIED; "
        "NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
