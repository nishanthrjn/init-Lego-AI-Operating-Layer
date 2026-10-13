"""Maintainer-only bounded receive diagnostics; synthetic TLS, no live calls."""

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_forgeai_remote_model_profile_1 import REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
BASELINE = "9e0abf40fe2a862f5982fd25a0059d9fae72a9c9"
SELF = "validate_forgeai_kisski_saia_bounded_receive_diagnostics_1.py"
TEST = "scripts/tests/test_kisski_saia_receive_diagnostics.py"
RUNNER = "scripts/kisski_saia_qualification.py"
TRANSPORT = "src/legoai/reference/_credential_https.py"
PLANE = "src/legoai/runtime/_composition/remote_model.py"
LOCAL = "src/legoai/runtime/local.py"
DOCUMENT = "planning/FORGEAI-KISSKI-SAIA-BOUNDED-RECEIVE-DIAGNOSTICS-1.md"
TARGETS = (TRANSPORT, PLANE, LOCAL, RUNNER, TEST, SELF)
ALLOWED = {*TARGETS, DOCUMENT}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, timeout=30
    ).stdout.decode("utf-8")


def functions(source: str) -> dict[str, str]:
    return {
        node.name: ast.dump(node, include_attributes=False)
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef)
    }


def scope() -> None:
    changed = set(git("diff", "--name-only", "--no-renames", BASELINE).splitlines())
    changed.update(
        git("diff", "--cached", "--name-only", "--no-renames", BASELINE).splitlines()
    )
    changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    if changed - ALLOWED:
        raise ValueError("outside seven-file scope: " + repr(changed - ALLOWED))
    for name in ALLOWED:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or symlinked slice file: " + name)
        content = path.read_text(encoding="utf-8")
        if not content.endswith("\n") or content.endswith("\n\n"):
            raise ValueError("final newline violation: " + name)
        if any(line != line.rstrip(" \t") for line in content.splitlines()):
            raise ValueError("trailing whitespace: " + name)
    before = functions(git("show", BASELINE + ":" + TRANSPORT))
    after = functions((ROOT / TRANSPORT).read_text(encoding="utf-8"))
    for name in (
        "_parse",
        "tls_context",
        "_max_request_body",
        "_max_response_body",
        "_max_header_bytes",
        "_max_headers",
        "_max_write",
    ):
        if before[name] != after[name]:
            raise ValueError("protected parser/TLS/bound changed: " + name)


def main() -> int:
    phase = "seven-file scope; parser, bounds, TLS, custody and ADRs preserved"
    env = os.environ.copy()
    env.update(UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")

    def run(name: str, command: list[str]) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + phase, flush=True)
        subprocess.run(command, cwd=ROOT, env=env, check=True, timeout=1200)

    with tempfile.TemporaryDirectory(prefix="saia-receive-offline-") as temporary:

        def tests(name: str, paths: tuple[str, ...]) -> None:
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
                    str(Path(temporary) / name.split()[0]),
                    *paths,
                ],
            )

        try:
            print("[PHASE] " + phase, flush=True)
            scope()
            tests(
                "diagnostics, safety, timings, effects and current framing",
                (TEST, "scripts/tests/test_kisski_saia_chat_interop.py"),
            )
            tests("T2, SRCP-1, custody and adapter regressions", REMOTE_TESTS)
            tests(
                "KiSSKI runner and discovery regressions",
                (
                    "scripts/tests/test_kisski_saia_qualification.py",
                    "scripts/tests/test_kisski_compatibility_probe.py",
                    "tests/integration/composition/test_provider_discovery.py",
                ),
            )
            tests("architecture", ("tests/architecture",))
            run("typing", [sys.executable, "-m", "mypy", *TARGETS])
            run(
                "lint",
                [sys.executable, "-m", "ruff", "check", "--no-cache", *TARGETS],
            )
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
            for name, args in (
                ("working whitespace", ("diff", "--check", BASELINE)),
                ("staged whitespace", ("diff", "--cached", "--check", BASELINE)),
            ):
                phase = name
                print("\n[PHASE] " + phase, flush=True)
                git(*args)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            print(f"FAIL: {phase}: {error}; later phases NOT RUN")
            return 1
    print(
        "FORGEAI-KISSKI-SAIA-BOUNDED-RECEIVE-DIAGNOSTICS-1 LOCALLY QUALIFIED; "
        "SAFE DIAGNOSTICS ONLY; NO LIVE CONNECTIVITY OR CODING QUALITY QUALIFIED; "
        "NO STREAMING OR CHUNKED SUPPORT; NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
