"""Maintainer-only bounded-task qualification; replay and fake sandbox only."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from validate_forgeai_remote_model_profile_1 import LOCAL_TESTS, REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
FORGEAI = ROOT / "examples/forgeai"
ENGINEERING = ROOT / "packages/legoai-engineering"
BASE = "dca0cb999298b9ccfaea97ff318635fe2b9a4b45"
SELF = "validate_forgeai_v0_2_bounded_task_qualification_1.py"
TARGETS = ("tests/test_bounded_task_qualification.py",)
ALLOWED = frozenset("examples/forgeai/" + name for name in TARGETS) | frozenset(
    {
        SELF,
        "examples/forgeai/README.md",
        "planning/FORGEAI-CONTEXT-CONFIRMATION-1.md",
    }
)


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        print("FAIL: uv required; existing locked project environments required")
        return 1
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.pop("LEGOAI_QUALIFY_PROJECT_CHECKS", None)
    env.pop("LEGOAI_QUALIFY_FORGEAI_REMOTE", None)
    env["UV_OFFLINE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    phase = "qualification-only scope; all production and frozen evaluation preserved"

    def git(*args: str) -> set[str]:
        return set(
            subprocess.check_output(
                ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
            ).splitlines()
        )

    def run(name: str, command: list[str], cwd: Path = ROOT) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + name, flush=True)
        subprocess.run(command, cwd=cwd, env=env, check=True)

    def project(name: str, cwd: Path, *args: str) -> None:
        assert uv is not None
        run(
            name,
            [uv, "run", "--locked", "--offline", "--no-sync", "python", *args],
            cwd,
        )

    try:
        print("[PHASE] " + phase, flush=True)
        changed = (
            git("diff", "--name-only", BASE)
            | git("diff", "--cached", "--name-only", BASE)
            | git("ls-files", "--others", "--exclude-standard")
        )
        if changed - ALLOWED:
            raise ValueError(
                "outside bounded-task qualification scope: "
                + repr(sorted(changed - ALLOWED))
            )
        project(
            "complete bounded lifecycle, exact confirmation and preflight controls",
            FORGEAI,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_bounded_task_qualification.py",
            "tests/test_context_confirmation.py",
            "tests/test_repository_context.py",
            "tests/test_v01_context.py",
            "-k",
            "not real_sandbox",
        )
        project(
            "ForgeAI pipeline, PROJECT, LOCAL/REMOTE and authority regressions",
            FORGEAI,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests",
            "--ignore=tests/test_end_to_end.py",
            "--ignore=tests/test_clean_install.py",
            "-k",
            "not real_docker and not real_sandbox",
        )
        project(
            "Engineering path, acquisition, coding and architecture contracts",
            ENGINEERING,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_workspace.py",
            "tests/test_coding.py",
            "tests/test_coding_context.py",
            "tests/test_architecture.py",
        )
        for name, paths in (
            ("REMOTE custody and disclosure", REMOTE_TESTS),
            ("LOCAL model preservation", LOCAL_TESTS),
            (
                "KiSSKI synthetic compatibility regressions",
                (
                    "scripts/tests/test_kisski_saia_qualification.py",
                    "scripts/tests/test_kisski_saia_receive_diagnostics.py",
                    "scripts/tests/test_kisski_saia_function_call_shapes.py",
                ),
            ),
            ("architecture boundaries", ("tests/architecture",)),
        ):
            run(
                name,
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    *paths,
                ],
            )
        project("typing ForgeAI", FORGEAI, "-m", "mypy", *TARGETS)
        run("typing validator", [sys.executable, "-m", "mypy", SELF])
        project("lint ForgeAI", FORGEAI, "-m", "ruff", "check", "--no-cache", *TARGETS)
        project(
            "format ForgeAI",
            FORGEAI,
            "-m",
            "ruff",
            "format",
            "--check",
            "--no-cache",
            *TARGETS,
        )
        run(
            "lint validator",
            [sys.executable, "-m", "ruff", "check", "--no-cache", SELF],
        )
        run(
            "format validator",
            [sys.executable, "-m", "ruff", "format", "--check", "--no-cache", SELF],
        )
        run("working whitespace", ["git", "diff", "--check", BASE])
        run("staged whitespace", ["git", "diff", "--cached", "--check"])
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL: {phase}: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-V0.2-BOUNDED-TASK-QUALIFICATION-1 LOCAL CHECKS PASSED; "
        "CONFIRMED-CONTEXT TASK LIFECYCLE LOCALLY QUALIFIED; "
        "REPLAY MODELS AND FAKE SANDBOX ONLY; "
        "NO LIVE MODEL QUALITY, REAL SANDBOX OR GLOBAL V0.2 QUALIFICATION; "
        "NO LIVE EXECUTION OR DEPLOYMENT AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
