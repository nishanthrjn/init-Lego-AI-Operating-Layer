"""Maintainer-only T2 checks. Synthetic loopback TLS; no provider or build calls."""

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_forgeai_remote_model_profile_1 import LOCAL_TESTS, REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
BASELINE = "49a047c001be4db300fba077e5b5a1ff7c0e8255"
TRANSPORT = "src/legoai/reference/_credential_https.py"
TEST = "scripts/tests/test_t2_bounded_chunked_response.py"
SELF = "validate_t2_bounded_chunked_response_1.py"
DOCUMENT = "docs/model-composition.md"
TARGETS = (
    TRANSPORT,
    TEST,
    SELF,
    "tests/support/tls_server.py",
    "tests/unit/reference/test_credential_https.py",
    "tests/integration/composition/test_openai_compatible_remote.py",
    "tests/integration/composition/test_provider_discovery.py",
    "scripts/tests/test_kisski_saia_chat_interop.py",
    "scripts/tests/test_kisski_saia_receive_diagnostics.py",
    "scripts/tests/test_kisski_saia_qualification.py",
    "scripts/tests/test_kisski_compatibility_probe.py",
    "scripts/tests/test_hf_inference_compatibility_probe.py",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, timeout=30
    ).stdout.decode("utf-8")


def protected(source: str) -> dict[str, str]:
    result = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name not in {
            "_parse",
            "_response_head",
        }:
            result[node.name] = ast.dump(node, include_attributes=False)
        if isinstance(node, ast.ClassDef) and node.name == "_CredentialFlight":
            for member in node.body:
                if isinstance(member, ast.FunctionDef) and member.name not in {
                    "receive",
                    "_note_chunked",
                    "_update_diagnostics",
                }:
                    result[member.name] = ast.dump(member, include_attributes=False)
    return result


def scope() -> None:
    changed = set(git("diff", "--name-only", "--no-renames", BASELINE).splitlines())
    changed.update(
        git("diff", "--cached", "--name-only", "--no-renames", BASELINE).splitlines()
    )
    changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    allowed = {*TARGETS, DOCUMENT}
    if changed - allowed:
        raise ValueError("outside T2 scope: " + repr(changed - allowed))
    for name in TARGETS:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("expected ordinary slice file: " + name)
    before = protected(git("show", BASELINE + ":" + TRANSPORT))
    after = protected((ROOT / TRANSPORT).read_text(encoding="utf-8"))
    if before != after:
        raise ValueError("protected TLS/send/deadline/bounds/composition changed")


def main() -> int:
    phase = "T2 scope; handoff, APIs, custody, dependencies and ADRs unchanged"
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
        with tempfile.TemporaryDirectory(prefix="t2-chunked-offline-") as temporary:
            suites = (
                ("chunked bounds, deadlines, diagnostics and synthetic adapter", (TEST,)),
                (
                    "receive diagnostics and KiSSKI-like interop",
                    (
                        "scripts/tests/test_kisski_saia_receive_diagnostics.py",
                        "scripts/tests/test_kisski_saia_chat_interop.py",
                    ),
                ),
                ("T2 SRCP-1 Content-Length effects custody and adapters", REMOTE_TESTS),
                (
                    "discovery and runner regressions",
                    (
                        "tests/integration/composition/test_provider_discovery.py",
                        "scripts/tests/test_kisski_saia_qualification.py",
                        "scripts/tests/test_kisski_compatibility_probe.py",
                        "scripts/tests/test_hf_inference_compatibility_probe.py",
                    ),
                ),
                ("LOCAL Ollama and Model regressions", LOCAL_TESTS),
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
        "T2-BOUNDED-CHUNKED-RESPONSE-1 LOCALLY QUALIFIED; "
        "BOUNDED ORDINARY HTTP/1.1 CHUNKED RESPONSES ONLY; "
        "NO LIVE CONNECTIVITY OR CODING QUALITY QUALIFIED; "
        "NO SSE OR HTTP/2; NO LIVE EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
