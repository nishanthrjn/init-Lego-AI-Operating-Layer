"""Maintainer-only offline test-strength gate; no provider or Docker execution."""

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / "examples/forgeai"
BASE = "8cfe7ad401e0f1f4ab45bb475e2294513b30ba8f"
ALLOWED = frozenset(
    {
        "validate_forgeai_test_strength_1.py",
        "examples/forgeai/src/forgeai/domain.py",
        "examples/forgeai/src/forgeai/worker.py",
        "examples/forgeai/src/forgeai/review.py",
        "examples/forgeai/src/forgeai/composition.py",
        "examples/forgeai/src/forgeai/cli.py",
        "examples/forgeai/src/forgeai/report.py",
        "examples/forgeai/src/forgeai/policy.py",
        "examples/forgeai/batch.py",
        "examples/forgeai/tests/test_test_strength.py",
        "examples/forgeai/tests/test_run_report.py",
        "examples/forgeai/tests/test_domain.py",
        "examples/forgeai/README.md",
    }
)
PRESERVED = (
    "packages",
    "src",
    "scripts",
    "experiments",
    "adrs",
    "planning",
    "examples/forgeai/evaluation",
    "examples/forgeai/fixtures",
    "examples/forgeai/src/forgeai/line_endings.py",
    "examples/forgeai/src/forgeai/guidance.py",
    "examples/forgeai/tests/test_architecture.py",
)
EXCLUDED = (
    "tests/test_end_to_end.py",
    "tests/test_clean_install.py",
    "evaluation/tests/test_lq1_fixtures_docker.py",
    "evaluation/tests/test_lq1_diagnostics_docker.py",
)
SELECTION = "not real_docker and not real_sandbox"


def main() -> int:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key != "VIRTUAL_ENV" and not key.startswith(("LEGOAI_QUALIFY_", "GIT_"))
    }
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["UV_OFFLINE"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(ROOT), str(PROJECT), str(PROJECT / "src"))
    )
    environment["MYPYPATH"] = str(ROOT)
    phase = "setup"

    def git(*arguments: str) -> str:
        return subprocess.check_output(
            ["git", *arguments],
            cwd=ROOT,
            env=environment,
            text=True,
            encoding="utf-8",
            timeout=30,
        )

    def announce(name: str) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + phase, flush=True)

    def project(name: str, *arguments: str) -> None:
        announce(name)
        executable = shutil.which("uv")
        if executable is None:
            raise ValueError("uv and existing locked environments are required")
        subprocess.run(
            [
                executable,
                "run",
                "--locked",
                "--offline",
                "--no-sync",
                "python",
                *arguments,
            ],
            cwd=PROJECT,
            env=environment,
            check=True,
        )

    try:
        announce("scope")
        changed = (
            set(git("diff", "--no-renames", "--name-only", BASE).splitlines())
            | set(
                git(
                    "diff", "--cached", "--no-renames", "--name-only", BASE
                ).splitlines()
            )
            | set(git("ls-files", "--others", "--exclude-standard").splitlines())
        )
        if changed - ALLOWED:
            raise ValueError("outside scope: " + repr(sorted(changed - ALLOWED)))
        announce("preservation")
        git("diff", "--quiet", BASE, "--", *PRESERVED)
        git("diff", "--cached", "--quiet", BASE, "--", *PRESERVED)
        pytest = ("-m", "pytest", "-q", "-p", "no:cacheprovider")
        project(
            "test-strength contracts",
            *pytest,
            "tests/test_test_strength.py",
            "-k",
            SELECTION,
        )
        project(
            "architecture, worker, rework, report and batch regressions",
            *pytest,
            "tests/test_architecture.py",
            "tests/test_cli.py",
            "tests/test_worker.py",
            "tests/test_rework.py",
            "tests/test_run_report.py",
            "tests/test_batch.py",
            "tests/test_policy.py",
            "-k",
            SELECTION,
        )
        for path in EXCLUDED:
            if not (PROJECT / path).is_file():
                raise ValueError("missing exclusion: " + path)
        print("Offline exclusions: " + ", ".join(EXCLUDED))
        print(
            "EXCLUDED: evaluation/tests (historical harnesses; unchanged). "
            "Product offline regressions only; not full integration or "
            "clean-install qualification."
        )
        project(
            "product suite, offline regressions only",
            *pytest,
            "tests",
            *("--ignore=" + path for path in EXCLUDED),
            "-k",
            SELECTION,
        )
        validator = str(Path(__file__).resolve())
        project("strict typing", "-m", "mypy", "src", "tests", "batch.py", validator)
        project(
            "lint",
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "--config",
            "pyproject.toml",
            "--config",
            'lint.isort.known-first-party = ["forgeai", "forgeai_eval", "scripts"]',
            "src",
            "tests",
            "demo.py",
            "batch.py",
        )
        project(
            "lint validator",
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "--config",
            str(ROOT / "pyproject.toml"),
            validator,
        )
        project(
            "format",
            "-m",
            "ruff",
            "format",
            "--check",
            "--no-cache",
            "--config",
            "pyproject.toml",
            "src",
            "tests",
            "demo.py",
            "batch.py",
        )
        project(
            "format validator",
            "-m",
            "ruff",
            "format",
            "--check",
            "--no-cache",
            "--config",
            str(ROOT / "pyproject.toml"),
            validator,
        )
        announce("whitespace")
        git("diff", "--check")
        git("diff", "--cached", "--check")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL [{phase}]: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-TEST-STRENGTH-1 LOCAL CHECKS PASSED; "
        "REPLAY MODELS AND FAKE SANDBOX ONLY; "
        "MODEL QUALITY NOT QUALIFIED; NO LIVE EXECUTION"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
