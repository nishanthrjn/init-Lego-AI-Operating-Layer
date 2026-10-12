"""Maintainer-only offline SAIA qualification; synthetic loopback TLS, no Docker."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_forgeai_remote_model_profile_1 import LOCAL_TESTS, REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
BASELINE = "c01df354d1987a498dd8af27286ce6c00c04d106"
RUNNER = "scripts/kisski_saia_qualification.py"
TESTS = "scripts/tests/test_kisski_saia_qualification.py"
FORGEAI_TEST = "examples/forgeai/tests/test_kisski_saia_profile.py"
SELF = "validate_forgeai_kisski_saia_provider_qualification_1.py"
DOCUMENT = "planning/FORGEAI-KISSKI-SAIA-PROVIDER-QUALIFICATION-1.md"
PYTHON_FILES = (RUNNER, TESTS, FORGEAI_TEST, SELF)
ALLOWED = {*PYTHON_FILES, DOCUMENT}


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
            "outside five-file qualification scope: " + repr(changed - ALLOWED)
        )
    for name in ALLOWED:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or symlinked qualification file")
        content = path.read_text(encoding="utf-8")
        if not content.endswith("\n") or content.endswith("\n\n"):
            raise ValueError("final newline violation: " + name)
        if any(line != line.rstrip(" \t") for line in content.splitlines()):
            raise ValueError("trailing whitespace: " + name)


def main() -> int:
    phase = "five-file scope; production, dependencies, exports and ADRs unchanged"
    uv = shutil.which("uv")
    if uv is None:
        print("FAIL: existing uv environments required")
        return 1
    env = os.environ.copy()
    for key in (
        "VIRTUAL_ENV",
        "LEGOAI_QUALIFY_FORGEAI_REMOTE",
        "LEGOAI_QUALIFY_PROJECT_CHECKS",
    ):
        env.pop(key, None)
    env.update(UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")

    def run(name: str, command: list[str], cwd: Path = ROOT) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + phase, flush=True)
        subprocess.run(command, cwd=cwd, env=env, check=True, timeout=1200)

    with tempfile.TemporaryDirectory(prefix="saia-offline-") as temporary:
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

        def project(name: str, directory: str, args: list[str]) -> None:
            assert uv is not None
            run(
                name,
                [uv, "run", "--locked", "--offline", "--no-sync", "python", *args],
                ROOT / directory,
            )

        try:
            print("[PHASE] " + phase, flush=True)
            scope()
            run(
                "inert default plan",
                [sys.executable, "-m", "scripts.kisski_saia_qualification"],
            )
            tests(
                "qualification stages and existing KiSSKI discovery",
                (
                    TESTS,
                    "scripts/tests/test_kisski_compatibility_probe.py",
                    "tests/integration/composition/test_provider_discovery.py",
                ),
            )
            tests(
                "REMOTE SRCP-1, disclosure, custody and protected transport", REMOTE_TESTS
            )
            tests("LOCAL and Ollama preservation", LOCAL_TESTS)
            tests(
                "architecture boundaries",
                (
                    "tests/architecture/test_openai_compatible_remote.py",
                    "tests/architecture/test_remote_disclosure.py",
                    "tests/architecture/test_remote_attempts.py",
                    "tests/architecture/test_credential_https.py",
                    "tests/architecture/test_consumer_private_boundaries.py",
                ),
            )
            project(
                "ForgeAI SAIA config, real proposal parser and remote regressions",
                "examples/forgeai",
                [
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "--basetemp",
                    str(temp / "forgeai"),
                    "tests/test_kisski_saia_profile.py",
                    "tests/test_remote_profile.py",
                    "tests/test_architecture.py",
                    "-k",
                    "not real_docker_remote_profile_independence",
                ],
            )
            project(
                "Engineering structured output contracts",
                "packages/legoai-engineering",
                [
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "--basetemp",
                    str(temp / "engineering"),
                    "tests/test_coding_m4.py",
                    "tests/test_coding_context.py",
                    "tests/test_agent_output.py",
                ],
            )
            run(
                "typing qualification runner",
                [sys.executable, "-m", "mypy", RUNNER, TESTS, SELF],
            )
            project(
                "typing ForgeAI profile tests",
                "examples/forgeai",
                ["-m", "mypy", "tests/test_kisski_saia_profile.py"],
            )
            for mode in ("check", "format"):
                command = [sys.executable, "-m", "ruff", mode, "--no-cache"]
                if mode == "format":
                    command.append("--check")
                run("ruff " + mode, [*command, *PYTHON_FILES])
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
        "FORGEAI-KISSKI-SAIA-PROVIDER-QUALIFICATION-1 LOCAL CHECKS PASSED; "
        "KISSKI-SAIA PROVIDER PROFILE LOCALLY QUALIFIED; "
        "NO LIVE CONNECTIVITY OR CODING QUALITY QUALIFIED; "
        "LIVE EXECUTION REQUIRES SEPARATE AUTHORIZATION"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
