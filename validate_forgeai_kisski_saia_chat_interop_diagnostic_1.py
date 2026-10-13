"""Maintainer-only SAIA interop characterization; loopback TLS, no live calls."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_forgeai_remote_model_profile_1 import REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
BASELINE = "ad9d67ec11a00192aacf8874163c7d0d71153da7"
SELF = "validate_forgeai_kisski_saia_chat_interop_diagnostic_1.py"
TEST = "scripts/tests/test_kisski_saia_chat_interop.py"
DOCUMENT = "planning/FORGEAI-KISSKI-SAIA-CHAT-INTEROP-DIAGNOSTIC-1.md"
ALLOWED = {SELF, TEST, DOCUMENT}
RUNNER = "scripts/kisski_saia_qualification.py"
RUNNER_TEST = "scripts/tests/test_kisski_saia_qualification.py"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout.decode("utf-8")


def scope() -> None:
    changed = set(git("diff", "--name-only", "--no-renames", BASELINE).splitlines())
    changed.update(
        git("diff", "--cached", "--name-only", "--no-renames", BASELINE).splitlines()
    )
    changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    if changed - ALLOWED:
        raise ValueError(
            "outside three-file diagnostic scope: " + repr(changed - ALLOWED)
        )
    for name in ALLOWED:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or symlinked diagnostic file: " + name)
        content = path.read_text(encoding="utf-8")
        if not content.endswith("\n") or content.endswith("\n\n"):
            raise ValueError("final newline violation: " + name)
        if any(line != line.rstrip(" \t") for line in content.splitlines()):
            raise ValueError("trailing whitespace: " + name)
    document = (ROOT / DOCUMENT).read_text(encoding="utf-8")
    for section in range(1, 17):
        if document.count(f"\n## {section}. ") != 1:
            raise ValueError("missing or repeated diagnostic section")
    for required in (
        "Final implementation conclusion: **EVIDENCE_INSUFFICIENT**",
        "0.182773",
        "60.026151",
        "NOT RECOVERABLE FROM EXISTING EVIDENCE",
        "NOT RUN — Awaiting user execution",
        "NO LIVE EXECUTION AUTHORIZED",
    ):
        if required not in document:
            raise ValueError("missing evidence boundary: " + required)


def main() -> int:
    phase = "three-file scope; production, runner, dependencies and ADRs unchanged"
    env = os.environ.copy()
    for key in ("LEGOAI_QUALIFY_FORGEAI_REMOTE", "LEGOAI_QUALIFY_PROJECT_CHECKS"):
        env.pop(key, None)
    env.update(UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")

    def run(name: str, command: list[str]) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + phase, flush=True)
        subprocess.run(command, cwd=ROOT, env=env, check=True, timeout=1200)

    with tempfile.TemporaryDirectory(prefix="saia-interop-offline-") as temporary:
        temp = Path(temporary)

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
                    str(temp / name.split()[0]),
                    *paths,
                ],
            )

        try:
            print("[PHASE] " + phase, flush=True)
            scope()
            tests("framing, timeout, safe diagnostics and effect truth", (TEST,))
            tests("T2, SRCP-1, custody and OpenAI-compatible regressions", REMOTE_TESTS)
            tests(
                "KiSSKI runner and discovery regressions",
                (
                    RUNNER_TEST,
                    "scripts/tests/test_kisski_compatibility_probe.py",
                    "tests/integration/composition/test_provider_discovery.py",
                ),
            )
            tests(
                "architecture boundaries",
                (
                    "tests/architecture/test_credential_https.py",
                    "tests/architecture/test_remote_attempts.py",
                    "tests/architecture/test_openai_compatible_remote.py",
                    "tests/architecture/test_remote_disclosure.py",
                    "tests/architecture/test_consumer_private_boundaries.py",
                ),
            )
            targets = [SELF, TEST, RUNNER, RUNNER_TEST]
            run("typing", [sys.executable, "-m", "mypy", *targets])
            run(
                "lint",
                [sys.executable, "-m", "ruff", "check", "--no-cache", *targets],
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
                    *targets,
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
        "FORGEAI-KISSKI-SAIA-CHAT-INTEROP-DIAGNOSTIC-1 LOCAL CHECKS PASSED; "
        "EVIDENCE_INSUFFICIENT; CURRENT T2 CHARACTERIZED; "
        "NO LIVE CONNECTIVITY OR CODING QUALITY QUALIFIED; "
        "NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
